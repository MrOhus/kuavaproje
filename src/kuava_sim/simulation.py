"""Deterministic fixed-step 1-D altitude simulation (Round 1).

See docs/architecture/ARCHITECTURE.md for the data models and decisions.
Not thread-safe: drive one Simulation instance from a single thread.
"""

import math
from dataclasses import dataclass

STEP_RATE_HZ: int = 200
DT: float = 1 / STEP_RATE_HZ  # s
MIN_THRUST: float = 0.0  # N
DEFAULT_GRAVITY: float = 9.81  # m/s²


def _finite_float(name, value):
    """Return value as a finite float, or raise an error naming the parameter."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number (got {value!r})")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number (got {value})")
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
    """One simulated drone. Created from a valid SimConfig."""

    def __init__(self, config: SimConfig):
        self._config = config
        self._held_thrust = 0.0  # N, last accepted thrust command
        self._step_count = 0

    def step(self, thrust=None) -> None:
        """Advance one fixed step. A given thrust becomes the held command."""
        if thrust is not None:
            self._held_thrust = thrust
        self._step_count += 1

    def run(self, n: int, thrust=None) -> None:
        """Do exactly what n calls to step() would do; run(0) changes nothing."""
        if isinstance(n, bool) or not isinstance(n, int):
            raise TypeError(f"n must be a whole number of steps (got {n!r})")
        if n < 0:
            raise ValueError(f"n must not be negative (got {n})")
        if n == 0:
            return
        self.step(thrust)
        for _ in range(n - 1):
            self.step()

    @property
    def config(self) -> SimConfig:
        return self._config

    @property
    def held_thrust(self) -> float:
        return self._held_thrust

    @property
    def step_count(self) -> int:
        return self._step_count

    @property
    def time(self) -> float:
        """Simulated time in s, from the step count so it cannot drift."""
        return self._step_count / STEP_RATE_HZ

    @property
    def altitude(self) -> float:
        """Altitude in m. Dynamics arrive with US-3 (IQ-2)."""
        return self._config.initial_altitude

    @property
    def velocity(self) -> float:
        """Vertical velocity in m/s, positive upward. Dynamics arrive with US-3 (IQ-2)."""
        return self._config.initial_velocity

    @property
    def step_rate_hz(self) -> int:
        return STEP_RATE_HZ

    @property
    def step_length(self) -> float:
        return DT

    @property
    def min_thrust(self) -> float:
        return MIN_THRUST
