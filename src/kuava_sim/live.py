"""The live app's logic, without any window (ARCHITECTURE_899eaea.md, D-18).

LiveSession runs one Simulation in real time. Every method takes the
wall-clock time from its caller, so tests can drive it with a fake clock.
Single-threaded, like Simulation (D-17).
"""

import math
import time
from collections import deque

from .simulation import STEP_RATE_HZ, SimConfig, Simulation

# Slider (low, high, start), resolution 0.1 (OQ-36).
SLIDERS = {
    "kp": (0.0, 50.0, 4.0),
    "ki": (0.0, 20.0, 1.0),
    "kd": (0.0, 20.0, 3.0),
    "setpoint": (0.0, 100.0, 10.0),
}
SLIDER_RESOLUTION = 0.1

# The fixed drone of the app (OQ-36): 1 kg, on the ground at rest.
APP_CONFIG = SimConfig(mass=1.0, gravity=9.81, drag_coeff=0.5, max_thrust=30.0)

MAX_STEPS_PER_FRAME = 50  # 0.25 s; more than this is dropped (AQ-16)

PLOT_WINDOW = 20.0  # s shown in the plots (OQ-38)
PLOT_EVERY = 4  # steps per plotted point (20 ms)
THRUST_Y_RANGE = (-1.0, 31.0)  # N, fixed thrust axis
_PLOT_LEN = int(PLOT_WINDOW * STEP_RATE_HZ) // PLOT_EVERY + 1  # 1001 points

METRICS_REFRESH = 0.5  # s, the shortest time between newest-row refreshes (AQ-20)
_REFRESH_COST_FACTOR = 20  # wait 20 x the last refresh cost: metrics stay under ~5 %
NOT_REACHED = "not reached"


def _shown(value: float, decimals: int) -> str:
    return NOT_REACHED if math.isnan(value) else f"{value:.{decimals}f}"


def format_row(m) -> tuple:
    """One metrics row as shown: values rounded for display only, NaN as "not reached"."""
    return (
        f"{m.change_time:.2f}",
        f"{m.start_altitude:.1f} → {m.setpoint:.1f}",
        _shown(m.rise_time, 2),
        _shown(m.overshoot, 1),
        _shown(m.settling_time, 2),
        _shown(m.steady_state_error, 3),
    )


class LiveSession:
    """One live run: the simulation plus everything the window shows."""

    def __init__(self, now: float):
        self.values = {name: start for name, (_, _, start) in SLIDERS.items()}
        self._frame_times = deque()  # frame times within the last second
        self._start(now)

    def _start(self, now: float) -> None:
        sim = Simulation(APP_CONFIG)
        v = self.values
        sim.enable_controller(kp=v["kp"], ki=v["ki"], kd=v["kd"], setpoint=v["setpoint"])
        self._sim = sim
        first = sim.records[0]
        self._plot = deque(
            [(first.time, first.altitude, v["setpoint"], first.thrust_used)], maxlen=_PLOT_LEN
        )
        self._rows = []  # finished rows, frozen, oldest first
        self._newest = sim.last_step_metrics()
        self._next_refresh = now + METRICS_REFRESH
        self._anchor(now)

    def _anchor(self, now: float) -> None:
        self._anchor_time = now
        self._anchor_step = self._sim.step_count

    @property
    def sim(self) -> Simulation:
        return self._sim

    def set_gain(self, name: str, value) -> None:
        """A gain slider moved: use the new gain from the next step (no metrics row)."""
        value = float(value)
        self._sim.set_gains(**{name: value})
        self.values[name] = value

    def release_setpoint(self, value) -> None:
        """The setpoint slider was let go: one setpoint change, unless it is unchanged."""
        value = float(value)
        sim = self._sim
        before = sim.controller.setpoint
        finished = sim.last_step_metrics()  # final: its window ends at this record
        sim.set_setpoint(value)  # the same value again does nothing (OQ-33)
        self.values["setpoint"] = value
        if sim.controller.setpoint != before:
            self._rows.append(finished)
            self._newest = sim.last_step_metrics()

    def tick(self, now: float) -> int:
        """Take the steps due by the wall clock (pacing predicate); return how many."""
        frames = self._frame_times
        frames.append(now)
        while frames[0] <= now - 1.0:
            frames.popleft()
        sim = self._sim
        due = int((now - self._anchor_time) * STEP_RATE_HZ) - (
            sim.step_count - self._anchor_step
        )
        behind = due > MAX_STEPS_PER_FRAME
        n = MAX_STEPS_PER_FRAME if behind else max(due, 0)
        setpoint = sim.controller.setpoint  # the setpoint used for these steps
        plot = self._plot
        for _ in range(n):
            record = sim.step()
            if sim.step_count % PLOT_EVERY == 0:
                plot.append((record.time, record.altitude, setpoint, record.thrust_used))
        if behind:  # drop the rest: carry on at real speed from now
            self._anchor(now)
        if now >= self._next_refresh:
            self._refresh(now)
        return n

    def _refresh(self, now: float) -> None:
        """Recompute only the newest row; wait longer if that was slow (D-21)."""
        start = time.perf_counter()
        self._newest = self._sim.last_step_metrics()
        cost = time.perf_counter() - start
        self._next_refresh = now + max(METRICS_REFRESH, _REFRESH_COST_FACTOR * cost)

    def plot_points(self) -> tuple:
        """(time s, altitude m, setpoint m, thrust used N), the last 20 s."""
        return tuple(self._plot)

    def plot_x_range(self) -> tuple:
        """The time axis: [0, 20] s until 20 s have passed, then [t - 20, t]."""
        t = self._sim.time
        return (0.0, PLOT_WINDOW) if t <= PLOT_WINDOW else (t - PLOT_WINDOW, t)

    def altitude_y_range(self) -> tuple:
        """The altitude axis: 0 to 1.1 x the largest altitude or setpoint in view."""
        top = max(max(p[1], p[2]) for p in self._plot)
        return (0.0, max(1.0, 1.1 * top))

    def fps(self, now: float) -> int:
        """Frames in the last second."""
        return sum(1 for t in self._frame_times if t > now - 1.0)

    def metrics_rows(self) -> list:
        """One StepMetrics per setpoint change, newest first (the newest one live)."""
        return [self._newest] + self._rows[::-1]
