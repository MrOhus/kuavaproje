"""The live app's logic, without any window (ARCHITECTURE_899eaea.md, D-18).

LiveSession runs one Simulation in real time. Every method takes the
wall-clock time from its caller, so tests can drive it with a fake clock.
Single-threaded, like Simulation (D-17).
"""

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


class LiveSession:
    """One live run: the simulation plus everything the window shows."""

    def __init__(self, now: float):
        self.values = {name: start for name, (_, _, start) in SLIDERS.items()}
        self._start(now)

    def _start(self, now: float) -> None:
        sim = Simulation(APP_CONFIG)
        v = self.values
        sim.enable_controller(kp=v["kp"], ki=v["ki"], kd=v["kd"], setpoint=v["setpoint"])
        self._sim = sim
        self._anchor(now)

    def _anchor(self, now: float) -> None:
        self._anchor_time = now
        self._anchor_step = self._sim.step_count

    @property
    def sim(self) -> Simulation:
        return self._sim

    def tick(self, now: float) -> int:
        """Take the steps due by the wall clock (pacing predicate); return how many."""
        sim = self._sim
        due = int((now - self._anchor_time) * STEP_RATE_HZ) - (
            sim.step_count - self._anchor_step
        )
        behind = due > MAX_STEPS_PER_FRAME
        n = MAX_STEPS_PER_FRAME if behind else max(due, 0)
        for _ in range(n):
            sim.step()
        if behind:  # drop the rest: carry on at real speed from now
            self._anchor(now)
        return n
