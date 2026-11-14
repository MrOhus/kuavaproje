"""Deterministic fixed-step 1-D altitude simulation (Round 1).

See docs/architecture/ARCHITECTURE.md for the data models and decisions.
Not thread-safe: drive one Simulation instance from a single thread.
"""

import math
from array import array
from collections.abc import Sequence
from dataclasses import dataclass
from typing import NamedTuple

STEP_RATE_HZ: int = 200
DT: float = 1 / STEP_RATE_HZ  # s
MIN_THRUST: float = 0.0  # N
DEFAULT_GRAVITY: float = 9.81  # m/s²
GUST_FORCE: float = 5.0  # N, downward (OQ-35)
GUST_STEPS: int = 100  # steps a gust lasts (0.5 s)


class Record(NamedTuple):
    """The state at one moment (SI units, positive upward)."""

    time: float  # s
    altitude: float  # m
    velocity: float  # m/s
    acceleration: float  # m/s²
    thrust_used: float  # N
    drag: float  # N


_WIDTH = len(Record._fields)  # doubles per record


RISE_LIMITS = (0.1, 0.9)  # fractions of the final value (step_info default)
SETTLING_BAND = 0.02  # fraction of the final value (step_info default)


class StepMetrics(NamedTuple):
    """Step-response metrics for one setpoint change (SI units, % for overshoot)."""

    change_index: int  # record at which the setpoint changed
    change_time: float  # s
    start_altitude: float  # m
    setpoint: float  # m
    samples: int  # records in the window
    rise_time: float  # s, or NaN
    overshoot: float  # %, or NaN
    settling_time: float  # s, or NaN
    steady_state_value: float  # m, final altitude minus start altitude
    steady_state_error: float  # m, setpoint minus final altitude


def _step_info(y, times):
    """Rise time, overshoot and settling time, as python-control 0.10 step_info.

    Same operations in the same order (ARCHITECTURE_3dbd8e9.md D-9), with the
    final value taken from the last sample. A window with one sample or a final
    change of exactly 0 has nothing to measure and gives NaN (D-11).
    """
    final = y[-1]
    if len(y) < 2 or final == 0.0:
        return math.nan, math.nan, math.nan
    sign = 1.0 if final > 0.0 else -1.0
    low = next(i for i, yi in enumerate(y) if sign * (yi - RISE_LIMITS[0] * final) >= 0)
    high = next(i for i, yi in enumerate(y) if sign * (yi - RISE_LIMITS[1] * final) >= 0)
    rise_time = times[high] - times[low]
    settled = 0
    for i, yi in enumerate(y):
        if abs(yi / final - 1) >= SETTLING_BAND:
            settled = i + 1
    settling_time = times[settled] if settled < len(times) else math.nan
    beyond = abs(max(sign * yi for yi in y)) - abs(final)
    overshoot = abs(100.0 * beyond / final) if beyond > 0 else 0.0
    return rise_time, overshoot, settling_time


class ControllerStatus(NamedTuple):
    """Read-only snapshot of the PID controller (NaN settings while off)."""

    on: bool
    kp: float  # N/m
    ki: float  # N/(m·s)
    kd: float  # N·s/m
    setpoint: float  # m
    integral: float  # N, the integral contribution I


class RecordLog(Sequence):
    """Read-only view of the records, stored as one flat array('d')."""

    def __init__(self, data: array):
        self._data = data

    def __len__(self) -> int:
        return len(self._data) // _WIDTH

    def __getitem__(self, index):
        if isinstance(index, slice):
            return [self[i] for i in range(*index.indices(len(self)))]
        n = len(self)
        if index < 0:
            index += n
        if not 0 <= index < n:
            raise IndexError("record index out of range")
        start = index * _WIDTH
        return Record(*self._data[start : start + _WIDTH])

    def column(self, name: str) -> tuple:
        """One field of every record, in time order."""
        return tuple(self._data[Record._fields.index(name) :: _WIDTH])


def _finite_float(name, value):
    """Return value as a finite float, or raise an error naming the parameter."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number (got {value!r})")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number (got {value})")
    return value


def _non_negative(name, value):
    """Return value as a finite float that is not below 0."""
    value = _finite_float(name, value)
    if value < 0.0:
        raise ValueError(f"{name} must not be below 0 (got {value})")
    return value


@dataclass(frozen=True, slots=True)
class SimConfig:
    """Validated, immutable simulation settings (SI units)."""

    mass: float  # kg
    max_thrust: float  # N
    gravity: float = DEFAULT_GRAVITY  # m/s²
    drag_coeff: float = 0.0  # N·s/m
    initial_altitude: float = 0.0  # m
    initial_velocity: float = 0.0  # m/s, positive upward

    def __post_init__(self):
        m = self._set("mass")
        if not m > 0.0:
            raise ValueError(f"mass must be greater than 0 kg (got {m})")

        t_max = self._set("max_thrust")
        if t_max < 0.0:
            raise ValueError(f"max_thrust must not be below 0 N (got {t_max})")

        g = self._set("gravity")
        if not g > 0.0:
            raise ValueError(f"gravity must be greater than 0 m/s² (got {g})")

        b = self._set("drag_coeff")
        if b < 0.0:
            raise ValueError(f"drag_coeff must not be below 0 N·s/m (got {b})")
        limit = STEP_RATE_HZ * m
        if not b < limit:
            raise ValueError(
                f"drag_coeff must be below 200 × mass = {limit} N·s/m (got {b}); "
                "larger values make the simulation unstable"
            )

        h0 = self._set("initial_altitude")
        if h0 < 0.0:
            raise ValueError(f"initial_altitude must not be below 0 m (got {h0})")

        v0 = self._set("initial_velocity")
        if h0 == 0.0 and v0 < 0.0:
            raise ValueError(
                "the drone cannot start on the ground while moving down "
                f"(initial_altitude 0, initial_velocity {v0})"
            )

    def _set(self, name):
        value = _finite_float(name, getattr(self, name))
        object.__setattr__(self, name, value)
        return value


class Simulation:
    """One simulated drone. Created from a valid SimConfig.

    The records are the single source of truth: time, altitude and velocity
    are read from the last record.
    """

    def __init__(self, config: SimConfig):
        self._config = config
        self._held_thrust = 0.0  # N, last accepted thrust command
        self._data = array("d")
        self._records = RecordLog(self._data)
        self._data.extend(self._first_record())
        # PID controller (ARCHITECTURE_3dbd8e9.md); settings are NaN while off.
        self._ctrl_on = False
        self._kp = self._ki = self._kd = self._setpoint = math.nan
        self._integral = 0.0  # N
        self._changes = []  # (record index, setpoint) per setpoint change
        self._gust_left = 0  # steps of the current wind gust still to come

    def gust(self) -> None:
        """Wind gust: 5 N downward on the next 100 steps; a new press restarts it."""
        self._gust_left = GUST_STEPS

    def enable_controller(self, *, kp, ki, kd, setpoint) -> None:
        """Turn the PID controller on; this counts as a setpoint change."""
        if self._ctrl_on:
            raise RuntimeError(
                "the controller is already on; use set_gains or set_setpoint"
            )
        kp = _non_negative("kp", kp)
        ki = _non_negative("ki", ki)
        kd = _non_negative("kd", kd)
        setpoint = _non_negative("setpoint", setpoint)
        self._kp, self._ki, self._kd, self._setpoint = kp, ki, kd, setpoint
        self._integral = 0.0
        self._ctrl_on = True
        self._changes.append((self.step_count, setpoint))

    def disable_controller(self) -> None:
        """Turn the controller off; the held thrust stays at its last command."""
        if not self._ctrl_on:
            return
        self._ctrl_on = False
        self._kp = self._ki = self._kd = self._setpoint = math.nan
        self._integral = 0.0

    def _require_controller_on(self) -> None:
        if not self._ctrl_on:
            raise RuntimeError("the controller is off; turn it on first")

    def set_gains(self, *, kp=None, ki=None, kd=None) -> None:
        """Change one or more gains; they apply from the next step."""
        if kp is None and ki is None and kd is None:
            raise TypeError("set_gains needs at least one of kp, ki, kd")
        self._require_controller_on()
        new = {}
        for name, value in (("kp", kp), ("ki", ki), ("kd", kd)):
            if value is not None:
                new[name] = _non_negative(name, value)
        for name, value in new.items():
            setattr(self, "_" + name, value)

    def set_setpoint(self, setpoint) -> None:
        """Change the setpoint; a different value starts a new metrics result."""
        self._require_controller_on()
        setpoint = _non_negative("setpoint", setpoint)
        if setpoint == self._setpoint:
            return
        self._setpoint = setpoint
        self._changes.append((self.step_count, setpoint))

    def step_metrics(self) -> tuple:
        """One StepMetrics per setpoint change, recomputed from the records so far."""
        return tuple(self._metrics(j) for j in range(len(self._changes)))

    def last_step_metrics(self):
        """The newest step_metrics() result, computing only its window (None if none)."""
        return self._metrics(len(self._changes) - 1) if self._changes else None

    def _metrics(self, j: int) -> StepMetrics:
        """The result for change j: records from it up to the next change or the latest."""
        k, setpoint = self._changes[j]
        end = self._changes[j + 1][0] if j + 1 < len(self._changes) else self.step_count
        h = self._data[k * _WIDTH + 1 : end * _WIDTH + 2 : _WIDTH]  # altitudes k..end
        y = [hi - h[0] for hi in h]
        times = [i / STEP_RATE_HZ for i in range(len(y))]
        rise_time, overshoot, settling_time = _step_info(y, times)
        return StepMetrics(
            k, k / STEP_RATE_HZ, h[0], setpoint, len(y),
            rise_time, overshoot, settling_time, y[-1], setpoint - h[-1],
        )

    @property
    def controller(self) -> ControllerStatus:
        return ControllerStatus(
            self._ctrl_on, self._kp, self._ki, self._kd, self._setpoint, self._integral
        )

    def _reject_manual_thrust(self, thrust) -> None:
        if self._ctrl_on and thrust is not None:
            raise RuntimeError(
                "the controller is on; manual thrust commands are rejected"
            )

    def _first_record(self) -> tuple:
        """Time-0 record (DESIGN.md I-3)."""
        cfg = self._config
        h0, v0 = cfg.initial_altitude, cfg.initial_velocity
        if h0 == 0.0 and v0 == 0.0:  # on the ground at rest
            return (0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
        drag = -(cfg.drag_coeff * v0)
        a = ((0.0 - cfg.mass * cfg.gravity) + drag) / cfg.mass
        return (0.0, h0, v0, a, 0.0, drag)

    def step(self, thrust=None) -> Record:
        """Advance one fixed step and return its record.

        A given thrust becomes the held command.
        """
        self._reject_manual_thrust(thrust)
        if thrust is not None:
            self._held_thrust = _finite_float("thrust", thrust)
        if self._ctrl_on:
            self._control()
        return Record(*self._advance())

    def run(self, n: int, thrust=None) -> None:
        """Do exactly what n calls to step() would do; run(0) changes nothing."""
        if isinstance(n, bool) or not isinstance(n, int):
            raise TypeError(f"n must be a whole number of steps (got {n!r})")
        if n < 0:
            raise ValueError(f"n must not be negative (got {n})")
        self._reject_manual_thrust(thrust)
        if thrust is not None:
            thrust = _finite_float("thrust", thrust)
        if n == 0:
            return
        if thrust is not None:
            self._held_thrust = thrust
        if self._ctrl_on:
            for _ in range(n):
                self._control()
                self._advance()
        else:
            for _ in range(n):
                self._advance()

    def _control(self) -> None:
        """Set the held thrust to the PID command (ARCHITECTURE_3dbd8e9.md).

        Integral first (D-10), then this exact grouping, so that at the
        setpoint, at rest and with no integral the command is exactly m*g.
        """
        data = self._data
        h, v = data[-5], data[-4]
        e = self._setpoint - h
        self._integral = self._integral + (self._ki * e) * DT
        cfg = self._config
        self._held_thrust = (
            (cfg.mass * cfg.gravity + self._kp * e) + self._integral
        ) - self._kd * v

    def _advance(self) -> tuple:
        """One fixed step, exactly as ARCHITECTURE.md D-3 and D-4 specify.

        The record is appended in one call, so a step adds all six values
        or none.
        """
        cfg = self._config
        data = self._data
        m = cfg.mass
        h, v = data[-5], data[-4]
        t_used = min(max(self._held_thrust, MIN_THRUST), cfg.max_thrust)
        drag = -(cfg.drag_coeff * v)
        if self._gust_left:  # step with gust (ARCHITECTURE_899eaea.md)
            a = (((t_used - m * cfg.gravity) + drag) - GUST_FORCE) / m
            self._gust_left -= 1
        else:
            a = ((t_used - m * cfg.gravity) + drag) / m
        v_next = v + a * DT
        h_next = h + v_next * DT
        t = (len(data) // _WIDTH) / STEP_RATE_HZ  # new step count / 200
        if h_next <= 0.0 and v_next < 0.0:  # floor (D-4), I-2
            record = (t, 0.0, 0.0, 0.0, t_used, 0.0)
        else:
            record = (t, h_next, v_next, a, t_used, drag)
        data.extend(record)
        return record

    @property
    def config(self) -> SimConfig:
        return self._config

    @property
    def records(self) -> RecordLog:
        """All records so far, read-only, in time order."""
        return self._records

    @property
    def held_thrust(self) -> float:
        return self._held_thrust

    @property
    def step_count(self) -> int:
        return len(self._data) // _WIDTH - 1

    @property
    def time(self) -> float:
        """Simulated time in s (step count / 200, so it cannot drift)."""
        return self._data[-6]

    @property
    def altitude(self) -> float:
        """Altitude in m, never below 0."""
        return self._data[-5]

    @property
    def velocity(self) -> float:
        """Vertical velocity in m/s, positive upward."""
        return self._data[-4]

    @property
    def step_rate_hz(self) -> int:
        return STEP_RATE_HZ

    @property
    def step_length(self) -> float:
        return DT

    @property
    def min_thrust(self) -> float:
        return MIN_THRUST
