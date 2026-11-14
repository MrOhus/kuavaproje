"""US-7 Turn on a PID altitude controller — acceptance tests.

Expected behaviour comes from docs/design/DESIGN_0bfd04e.md (US-7, OQ-31,
OQ-32, OQ-33) and docs/architecture/ARCHITECTURE_3dbd8e9.md (controller state,
D-8 API with RuntimeError for state conflicts, D-14 lifecycle).
Scenarios that needed a later story were strict xfail until it landed (IQ-9).
"""

import math
import struct

import pytest

from kuava_sim import SimConfig, Simulation


GAINS = dict(kp=4.0, ki=1.0, kd=3.0, setpoint=10.0)
SETTINGS = ["kp", "ki", "kd", "setpoint"]


def make(**cfg):
    cfg.setdefault("mass", 1.0)
    cfg.setdefault("max_thrust", 30.0)
    cfg.setdefault("initial_altitude", 100.0)
    return Simulation(SimConfig(**cfg))


def snapshot(sim):
    """Everything a rejected call must leave unchanged."""
    return (
        [struct.pack("<6d", *r) for r in sim.records],
        struct.pack("<d", sim.held_thrust),
        sim.controller.on,
        struct.pack("<5d", *sim.controller[1:]),
    )


def enable(sim, **overrides):
    sim.enable_controller(**{**GAINS, **overrides})


# --- Scenario: Valid gains and setpoint are accepted --------------------------


def test_valid_gains_and_setpoint_are_accepted_and_reported_back():
    sim = make()
    enable(sim)
    status = sim.controller
    assert status.on is True
    assert (status.kp, status.ki, status.kd, status.setpoint) == (4.0, 1.0, 3.0, 10.0)
    assert status.integral == 0.0


def test_controller_is_off_with_no_settings_before_it_is_turned_on():
    status = make().controller
    assert status.on is False
    assert all(math.isnan(x) for x in (status.kp, status.ki, status.kd, status.setpoint))
    assert status.integral == 0.0


def test_turning_on_does_not_step_or_change_records():
    sim = make()
    before = [struct.pack("<6d", *r) for r in sim.records]
    enable(sim)
    assert [struct.pack("<6d", *r) for r in sim.records] == before
    assert sim.step_count == 0


# --- Scenario Outline: Gains and setpoint at their lower limit are accepted ---


@pytest.mark.parametrize("setting", SETTINGS)
def test_zero_is_accepted_for_each_setting(setting):
    sim = make()
    enable(sim, **{setting: 0.0})
    assert sim.controller.on is True
    assert getattr(sim.controller, setting) == 0.0


@pytest.mark.parametrize("setting", SETTINGS)
def test_smallest_positive_value_is_accepted_for_each_setting(setting):
    sim = make()
    tiny = math.nextafter(0.0, 1.0)
    enable(sim, **{setting: tiny})
    assert getattr(sim.controller, setting) == tiny


# --- Scenario Outline: Negative gains or setpoint below ground are rejected ---


@pytest.mark.parametrize("value", [-0.001, -1.0, math.nextafter(0.0, -1.0)])
@pytest.mark.parametrize("setting", SETTINGS)
def test_negative_value_is_rejected_with_clear_error(setting, value):
    sim = make()
    before = snapshot(sim)
    with pytest.raises(ValueError) as info:
        enable(sim, **{setting: value})
    message = str(info.value)
    assert setting in message and "must not be below 0" in message
    assert snapshot(sim) == before
    assert sim.controller.on is False


# --- Scenario Outline: Non-finite gains or setpoint are rejected --------------


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf], ids=["nan", "+inf", "-inf"])
@pytest.mark.parametrize("setting", SETTINGS)
def test_non_finite_value_is_rejected_with_clear_error(setting, value):
    sim = make()
    before = snapshot(sim)
    with pytest.raises(ValueError, match=setting):
        enable(sim, **{setting: value})
    assert snapshot(sim) == before


@pytest.mark.parametrize("value", [True, "4", None], ids=["bool", "str", "None"])
@pytest.mark.parametrize("setting", SETTINGS)
def test_non_number_value_is_rejected_with_clear_error(setting, value):
    sim = make()
    before = snapshot(sim)
    with pytest.raises(TypeError, match=setting):
        enable(sim, **{setting: value})
    assert snapshot(sim) == before


# --- Scenario: Turning on without a setpoint is rejected ----------------------


@pytest.mark.parametrize("missing", SETTINGS)
def test_turning_on_without_a_setting_is_rejected(missing):
    sim = make()
    kwargs = dict(GAINS)
    del kwargs[missing]
    with pytest.raises(TypeError, match=missing):
        sim.enable_controller(**kwargs)
    assert sim.controller.on is False


# --- Scenario: Large setpoints are accepted -----------------------------------


def test_large_setpoint_is_accepted():
    sim = make()
    enable(sim, setpoint=100000.0)
    assert sim.controller.setpoint == 100000.0


# --- Scenario: Turning on counts as the first setpoint change -----------------


def test_turning_on_counts_as_the_first_setpoint_change():
    sim = make()
    sim.run(40, thrust=0.0)
    h40 = sim.records[40].altitude
    enable(sim)
    results = sim.step_metrics()
    assert len(results) == 1
    r = results[0]
    assert r.change_index == 40
    assert abs(r.change_time - 0.2) <= 1e-12
    assert r.start_altitude == h40
    assert r.setpoint == 10.0


# --- Scenario: Taking off from the ground under control -----------------------


def test_taking_off_from_the_ground_under_control():
    sim = make(gravity=9.81, initial_altitude=0.0)
    enable(sim, kp=4.0, ki=0.0, kd=3.0, setpoint=10.0)
    sim.run(200)
    assert sim.altitude > 0.0


# --- Scenario: Manual thrust is rejected while the controller is on -----------


@pytest.mark.parametrize(
    "call",
    [
        lambda s: s.step(12.0),
        lambda s: s.run(5, thrust=12.0),
        lambda s: s.run(0, thrust=12.0),
        lambda s: s.step(math.nan),
    ],
    ids=["step", "run", "run-0", "step-nan"],
)
def test_manual_thrust_is_rejected_while_the_controller_is_on(call):
    sim = make()
    enable(sim)
    before = snapshot(sim)
    with pytest.raises(RuntimeError, match="controller is on"):
        call(sim)
    assert snapshot(sim) == before


# --- Scenario: Turning the controller off returns Round 1 behaviour -----------


def test_turning_off_accepts_manual_commands_again():
    sim = make()
    enable(sim)
    sim.disable_controller()
    status = sim.controller
    assert status.on is False
    assert all(math.isnan(x) for x in (status.kp, status.ki, status.kd, status.setpoint))
    assert status.integral == 0.0
    record = sim.step(12.0)
    assert record.thrust_used == 12.0


def test_turning_off_keeps_the_last_controller_command_as_held_thrust():
    sim = make(gravity=9.81, max_thrust=30.0, initial_altitude=5.0)
    enable(sim)
    sim.run(50)
    last_command = sim.held_thrust
    assert last_command != 0.0  # the controller really commanded something
    sim.disable_controller()
    assert sim.held_thrust == last_command
    record = sim.step()
    assert record.thrust_used == min(max(last_command, 0.0), 30.0)


# --- ARCHITECTURE D-14: lifecycle ---------------------------------------------


def test_turning_on_while_on_is_rejected():
    sim = make()
    enable(sim)
    before = snapshot(sim)
    with pytest.raises(RuntimeError, match="already on"):
        enable(sim, setpoint=20.0)
    assert snapshot(sim) == before


def test_turning_off_while_off_does_nothing():
    sim = make()
    sim.run(3, thrust=7.0)
    before = snapshot(sim)
    sim.disable_controller()
    assert snapshot(sim) == before


def test_controller_can_be_turned_on_again_after_off():
    sim = make()
    enable(sim)
    sim.disable_controller()
    enable(sim, kp=1.0, ki=0.0, kd=0.0, setpoint=50.0)
    status = sim.controller
    assert (status.on, status.kp, status.setpoint, status.integral) == (True, 1.0, 50.0, 0.0)
