"""US-11 helpers: compare our StepMetrics with python-control (test-only, D-7).

The "within 2 %" rule is ARCHITECTURE_3dbd8e9.md D-12:
- reference not 0: |ours - ref| <= 0.02 * |ref|
- reference exactly 0: |ours| <= 0.02 in the metric's own unit (s or %)
- both NaN: match; only one NaN: mismatch
"""

import math

import control
import numpy as np

PAIRS = {
    "RiseTime": "rise_time",
    "Overshoot": "overshoot",
    "SettlingTime": "settling_time",
    "SteadyStateValue": "steady_state_value",
}


def mismatches(ours, reference, rel=0.02, zero_abs=0.02):
    """Names of the metrics that are not within the D-12 rule."""
    bad = []
    for name, ref in reference.items():
        value = ours[name]
        if math.isnan(ref) or math.isnan(value):
            if not (math.isnan(ref) and math.isnan(value)):
                bad.append(name)
            continue
        limit = zero_abs if ref == 0.0 else rel * abs(ref)
        if not abs(value - ref) <= limit:
            bad.append(name)
    return bad


def ours(result):
    return {pc: getattr(result, mine) for pc, mine in PAIRS.items()}


def signal(sim, result):
    """Relative altitude and times of a result's window, as numpy arrays."""
    k = result.change_index
    h = np.array(sim.records.column("altitude")[k : k + result.samples])
    return h - h[0], np.arange(result.samples) / 200


def same_signal_reference(sim, result):
    y, t = signal(sim, result)
    info = control.step_info(y, t)
    return {name: info[name] for name in PAIRS}


def model_reference(sim, result, kp, ki, kd):
    """step_info of the continuous closed-loop model (D-13) on the same time points."""
    cfg = sim.config
    step = result.setpoint - result.start_altitude
    model = control.tf([kp * step, ki * step], [cfg.mass, cfg.drag_coeff + kd, kp, ki])
    _, t = signal(sim, result)
    info = control.step_info(model, t)
    return {name: info[name] for name in PAIRS}


def model_applies(sim, result):
    """True when the thrust never hit a limit and the drone never touched the ground."""
    k, n = result.change_index, result.samples
    used = sim.records.column("thrust_used")[k + 1 : k + n]
    altitude = sim.records.column("altitude")[k : k + n]
    return all(0.0 < u < sim.config.max_thrust for u in used) and min(altitude) > 0.0
