"""US-10 Step-response metrics after every setpoint change — acceptance tests.

Expected behaviour comes from docs/design/DESIGN_0bfd04e.md (US-10, OQ-29,
OQ-30) and docs/architecture/ARCHITECTURE_3dbd8e9.md (StepMetrics, window
k..next change, D-11 degenerate windows). Each metric is checked against its
written definition by scanning the recorded altitude, not against
python-control (that is US-11).
"""

import math
import struct

import pytest

from kuava_sim import SimConfig, Simulation

FIELDS = (
    "change_index", "change_time", "start_altitude", "setpoint", "samples",
    "rise_time", "overshoot", "settling_time", "steady_state_value", "steady_state_error",
)


def make(**cfg):
    cfg.setdefault("mass", 1.0)
    cfg.setdefault("gravity", 9.81)
    cfg.setdefault("max_thrust", 30.0)
    cfg.setdefault("drag_coeff", 0.5)
    return Simulation(SimConfig(**cfg))


def within_eps(actual, expected):
    return abs(actual - expected) <= 1e-12 * max(1.0, abs(expected))


def hovering(altitude, **gains):
    sim = make(initial_altitude=altitude)
    sim.enable_controller(**{**dict(kp=4.0, ki=1.0, kd=3.0), **gains, "setpoint": altitude})
    return sim


def window(sim, result):
    k = result.change_index
    h = sim.records.column("altitude")[k : k + result.samples]
    return [x - h[0] for x in h], h


def check_definitions(sim, result):
    """Check one result against the DESIGN definitions."""
    y, h = window(sim, result)
    final = y[-1]
    assert final != 0.0
    up = final > 0
    reached = (lambda i, frac: y[i] >= frac * final) if up else (lambda i, frac: y[i] <= frac * final)
    low = next(i for i in range(len(y)) if reached(i, 0.1))
    high = next(i for i in range(len(y)) if reached(i, 0.9))
    assert within_eps(result.rise_time, (high - low) / 200)
    outside = [i for i in range(len(y)) if abs(y[i] / final - 1) >= 0.02]
    settled = outside[-1] + 1 if outside else 0
    assert within_eps(result.settling_time, settled / 200)
    peak = max(y) if up else min(y)
    beyond = abs(peak) - abs(final)
    assert within_eps(result.overshoot, abs(100 * beyond / final) if beyond > 0 else 0.0)
    assert result.steady_state_value == final
    assert result.steady_state_error == result.setpoint - h[-1]


# --- Scenario: Each setpoint change gets its own metrics ----------------------


def test_each_setpoint_change_gets_its_own_result_in_order():
    sim = hovering(5.0)
    sim.run(2000)
    sim.set_setpoint(20.0)
    sim.run(2000)
    sim.set_setpoint(15.0)
    sim.run(2000)
    results = sim.step_metrics()
    assert [r.change_index for r in results] == [0, 2000, 4000]
    assert [r.setpoint for r in results] == [5.0, 20.0, 15.0]
    for r in results:
        assert within_eps(r.change_time, r.change_index / 200)
        assert r.start_altitude == sim.records[r.change_index].altitude


def test_no_results_before_the_controller_is_ever_turned_on():
    sim = make(initial_altitude=10.0)
    sim.run(50, thrust=5.0)
    assert sim.step_metrics() == ()


# --- Scenario: A result covers the samples from its change to the next --------


def test_a_result_covers_its_change_up_to_the_next_change():
    sim = hovering(10.0)
    sim.run(100)
    sim.set_setpoint(20.0)
    sim.run(800)
    sim.set_setpoint(15.0)
    sim.run(600)
    first, second, third = sim.step_metrics()
    assert (first.change_index, first.samples) == (0, 101)  # records 0..100
    assert (second.change_index, second.samples) == (100, 801)  # records 100..900
    assert (third.change_index, third.samples) == (900, 601)  # records 900..1500


# --- Scenario: The latest result can be read at any time and is recomputed ----


def test_the_latest_result_is_recomputed_from_the_records_so_far():
    sim = hovering(50.0)
    sim.set_setpoint(52.0)
    sim.run(200)
    early = sim.step_metrics()[-1]
    sim.run(3800)
    late = sim.step_metrics()[-1]
    assert (early.samples, late.samples) == (201, 4001)
    assert early.steady_state_value == sim.records[200].altitude - 50.0
    assert late.steady_state_value == sim.records[4000].altitude - 50.0
    assert early.steady_state_value != late.steady_state_value


def test_reading_the_metrics_changes_nothing():
    sim = hovering(50.0)
    sim.set_setpoint(52.0)
    sim.run(300)
    before = [struct.pack("<6d", *r) for r in sim.records], sim.controller
    first = sim.step_metrics()
    assert ([struct.pack("<6d", *r) for r in sim.records], sim.controller) == before
    assert sim.step_metrics() == first


# --- Scenario: Metrics follow step_info's definitions on the relative altitude -


def test_metrics_of_an_upward_step_follow_the_definitions():
    sim = hovering(50.0)
    sim.set_setpoint(52.0)
    sim.run(6000)
    result = sim.step_metrics()[-1]
    check_definitions(sim, result)
    assert result.overshoot > 1.0  # this tuning really overshoots
    assert 0.0 < result.rise_time < result.settling_time


# --- Scenario: A downward step uses the same rules ----------------------------


def test_metrics_of_a_downward_step_follow_the_same_definitions():
    sim = hovering(20.0)
    sim.set_setpoint(10.0)
    sim.run(6000)
    result = sim.step_metrics()[-1]
    assert result.steady_state_value < 0.0
    check_definitions(sim, result)
    assert result.steady_state_error == 10.0 - sim.altitude
    assert result.overshoot > 1.0


# --- Scenario: A metric that is never reached is NaN (D-11 degenerate windows) -


def test_a_zero_size_step_gives_nan_metrics():
    sim = hovering(100.0)  # turned on at its own altitude: no step
    sim.run(200)
    result = sim.step_metrics()[0]
    assert math.isnan(result.rise_time)
    assert math.isnan(result.overshoot)
    assert math.isnan(result.settling_time)
    assert result.steady_state_value == 0.0
    assert result.steady_state_error == 0.0


def test_a_single_sample_window_gives_nan_metrics():
    sim = hovering(50.0)
    sim.run(10)
    sim.set_setpoint(60.0)
    result = sim.step_metrics()[-1]
    assert result.samples == 1
    assert math.isnan(result.rise_time) and math.isnan(result.overshoot)
    assert math.isnan(result.settling_time)
    assert result.steady_state_error == 60.0 - sim.altitude


def test_a_change_with_a_tiny_but_non_zero_final_change_is_measured():
    sim = hovering(50.0)
    sim.set_setpoint(50.001)
    sim.run(2000)
    result = sim.step_metrics()[-1]
    check_definitions(sim, result)


# --- Scenario: Metrics are reported in fixed units ----------------------------


def test_metrics_fields_and_types():
    sim = hovering(50.0)
    sim.set_setpoint(52.0)
    sim.run(400)
    result = sim.step_metrics()[-1]
    assert result._fields == FIELDS
    assert type(result.change_index) is int and type(result.samples) is int
    for name in FIELDS[1:4] + FIELDS[5:]:
        assert type(getattr(result, name)) is float, name


# --- Scenario: Rejected setpoint changes create no metrics --------------------


@pytest.mark.parametrize("bad", [-1.0, math.nan, "12"], ids=["negative", "nan", "str"])
def test_rejected_setpoint_change_creates_no_metrics(bad):
    sim = hovering(50.0)
    sim.set_setpoint(52.0)
    sim.run(100)
    before = sim.step_metrics()
    assert len(before) == 2
    with pytest.raises((ValueError, TypeError)):
        sim.set_setpoint(bad)
    after = sim.step_metrics()
    assert len(after) == 2
    assert [struct.pack("<9d", *r[1:4], *r[5:]) for r in after] == [
        struct.pack("<9d", *r[1:4], *r[5:]) for r in before
    ]
