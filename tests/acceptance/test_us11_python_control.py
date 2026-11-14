"""US-11 Metrics agree with python-control — acceptance tests.

Expected behaviour comes from docs/design/DESIGN_0bfd04e.md (US-11, OQ-26 c)
and docs/architecture/ARCHITECTURE_3dbd8e9.md (D-9 equal results on the same
signal, D-11 degenerate windows left out, D-12 the 2 % rule, D-13 the
continuous closed-loop model). python-control is a test-only dependency.
"""

import math

import pytest

from kuava_sim import SimConfig, Simulation
from pc_compare import (
    PAIRS,
    mismatches,
    model_applies,
    model_reference,
    ours,
    same_signal_reference,
)

pytestmark = pytest.mark.filterwarnings("ignore::RuntimeWarning")

US11 = dict(mass=1.0, drag_coeff=0.5, kp=4.0, ki=1.0, kd=3.0)
LIGHT = dict(mass=1.0, drag_coeff=0.2, kp=9.0, ki=2.0, kd=1.0)
STIFF = dict(mass=1.2, drag_coeff=0.3, kp=20.0, ki=5.0, kd=6.0)  # hits the 30 N limit


def hover_then_step(case, start, target, seconds=30.0):
    sim = Simulation(
        SimConfig(mass=case["mass"], gravity=9.81, drag_coeff=case["drag_coeff"],
                  max_thrust=30.0, initial_altitude=start)
    )
    sim.enable_controller(kp=case["kp"], ki=case["ki"], kd=case["kd"], setpoint=start)
    sim.run(400)
    sim.set_setpoint(target)
    sim.run(int(round(seconds * 200)))
    return sim, sim.step_metrics()[-1]


# --- Scenario: Metrics match step_info on the same signal ---------------------


@pytest.mark.parametrize(
    "case, start, target",
    [(US11, 50.0, 52.0), (US11, 52.0, 50.0), (LIGHT, 50.0, 50.5), (STIFF, 50.0, 51.0)],
    ids=["us11-up", "us11-down", "light", "stiff-saturated"],
)
def test_metrics_match_step_info_on_the_same_signal(case, start, target):
    sim, result = hover_then_step(case, start, target)
    reference = same_signal_reference(sim, result)
    assert mismatches(ours(result), reference) == []
    # D-9: same operations, so the values are equal, not only within 2 %.
    for pc, mine in PAIRS.items():
        assert getattr(result, mine) == reference[pc], pc


def test_every_result_of_a_longer_run_matches_step_info():
    sim = Simulation(SimConfig(mass=1.0, drag_coeff=0.5, max_thrust=30.0, initial_altitude=0.0))
    sim.enable_controller(kp=4.0, ki=1.0, kd=3.0, setpoint=10.0)
    for target in (20.0, 15.0, 15.5, 3.0):
        sim.run(3000)
        sim.set_setpoint(target)
    sim.run(3000)
    results = sim.step_metrics()
    assert len(results) == 5
    for result in results:
        assert result.samples > 1 and result.steady_state_value != 0.0
        assert mismatches(ours(result), same_signal_reference(sim, result)) == []


# --- Scenario: Metrics match a python-control closed-loop model ---------------


@pytest.mark.parametrize(
    "case, start, target",
    [(US11, 50.0, 52.0), (US11, 52.0, 50.0), (LIGHT, 50.0, 50.5)],
    ids=["us11-up", "us11-down", "light"],
)
def test_metrics_match_the_closed_loop_model_where_it_applies(case, start, target):
    sim, result = hover_then_step(case, start, target)
    assert model_applies(sim, result)  # thrust strictly inside (0, 30) N, never on the ground
    assert result.rise_time >= 0.25  # D-13: one 5 ms sample is then at most 2 %
    reference = model_reference(sim, result, case["kp"], case["ki"], case["kd"])
    assert mismatches(ours(result), reference) == []


# --- Scenario: The model comparison is not claimed where it does not apply ----


def test_model_comparison_is_not_claimed_when_the_thrust_hits_a_limit():
    sim, result = hover_then_step(STIFF, 50.0, 51.0)
    assert not model_applies(sim, result)
    assert 30.0 in sim.records.column("thrust_used")  # it really hit the limit
    assert mismatches(ours(result), same_signal_reference(sim, result)) == []


def test_model_comparison_is_not_claimed_when_the_drone_touches_the_ground():
    sim = Simulation(SimConfig(mass=1.0, drag_coeff=0.5, max_thrust=30.0, initial_altitude=0.0))
    sim.enable_controller(kp=4.0, ki=1.0, kd=3.0, setpoint=5.0)
    sim.run(3000)
    result = sim.step_metrics()[0]
    assert not model_applies(sim, result)


# --- Scenario: A difference larger than 2 % fails the check (D-12 rule) -------


@pytest.mark.parametrize(
    "value, ok",
    [(102.0, True), (math.nextafter(102.0, 200.0), False), (98.0, True),
     (math.nextafter(98.0, 0.0), False), (100.0, True)],
    ids=["+2%", "+2%+eps", "-2%", "-2%-eps", "equal"],
)
def test_the_two_percent_rule_at_its_limit(value, ok):
    assert (mismatches({"Overshoot": value}, {"Overshoot": 100.0}) == []) is ok


@pytest.mark.parametrize(
    "value, ok",
    [(0.02, True), (math.nextafter(0.02, 1.0), False), (-0.02, True), (0.0, True)],
    ids=["0.02", "0.02+eps", "-0.02", "0"],
)
def test_a_zero_reference_allows_0_02_in_the_metric_unit(value, ok):
    assert (mismatches({"Overshoot": value}, {"Overshoot": 0.0}) == []) is ok


def test_nan_matches_only_nan():
    assert mismatches({"RiseTime": math.nan}, {"RiseTime": math.nan}) == []
    assert mismatches({"RiseTime": 1.0}, {"RiseTime": math.nan}) == ["RiseTime"]
    assert mismatches({"RiseTime": math.nan}, {"RiseTime": 1.0}) == ["RiseTime"]


def test_a_failed_check_names_every_metric_that_differs():
    reference = {"RiseTime": 1.0, "Overshoot": 10.0, "SettlingTime": 5.0, "SteadyStateValue": 2.0}
    values = {"RiseTime": 1.03, "Overshoot": 10.1, "SettlingTime": 5.2, "SteadyStateValue": 2.0}
    assert mismatches(values, reference) == ["RiseTime", "SettlingTime"]
