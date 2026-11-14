"""US-8 Change the gains and the setpoint while the simulation runs — acceptance tests.

Expected behaviour comes from docs/design/DESIGN_0bfd04e.md (US-8, OQ-28,
OQ-33) and docs/architecture/ARCHITECTURE_3dbd8e9.md (set_gains / set_setpoint,
all-or-nothing checks, D-10 integral first, D-14 lifecycle).
Scenarios that needed a later story were strict xfail until it landed (IQ-9).
"""

import math
import struct

import pytest

from kuava_sim import SimConfig, Simulation


DT = 0.005
M, G = 1.0, 9.81


def make(**cfg):
    cfg.setdefault("mass", M)
    cfg.setdefault("gravity", G)
    cfg.setdefault("max_thrust", 30.0)
    cfg.setdefault("drag_coeff", 0.5)
    cfg.setdefault("initial_altitude", 5.0)
    return Simulation(SimConfig(**cfg))


def controlled(**gains):
    sim = make()
    sim.enable_controller(**{**dict(kp=4.0, ki=1.0, kd=3.0, setpoint=10.0), **gains})
    return sim


def snapshot(sim):
    return (
        [struct.pack("<6d", *r) for r in sim.records],
        struct.pack("<d", sim.held_thrust),
        sim.controller.on,
        struct.pack("<5d", *sim.controller[1:]),
    )


def expected_thrust(sim, kp, ki, kd, setpoint, integral):
    """The US-9 formula for the next step, from the state at its start (ARCHITECTURE)."""
    h, v = sim.altitude, sim.velocity
    e = setpoint - h
    i = integral + (ki * e) * DT
    cmd = ((M * G + kp * e) + i) - kd * v
    return min(max(cmd, 0.0), 30.0)


# --- Scenario: Gains can be changed between steps -----------------------------


def test_gains_can_be_changed_and_are_reported_back():
    sim = controlled()
    sim.set_gains(kp=6.0)
    status = sim.controller
    assert (status.kp, status.ki, status.kd) == (6.0, 1.0, 3.0)
    sim.set_gains(ki=0.5, kd=2.0)
    status = sim.controller
    assert (status.kp, status.ki, status.kd) == (6.0, 0.5, 2.0)


def test_gain_change_leaves_earlier_records_unchanged():
    sim = controlled()
    sim.run(100)
    before = [struct.pack("<6d", *r) for r in sim.records]
    sim.set_gains(kp=6.0)
    sim.run(50)
    assert [struct.pack("<6d", *r) for r in sim.records[:101]] == before


def test_new_gain_is_used_from_the_next_step():
    sim = controlled()
    sim.run(100)
    sim.set_gains(kp=6.0)
    status = sim.controller
    expected = expected_thrust(sim, 6.0, 1.0, 3.0, 10.0, status.integral)
    old_gain = expected_thrust(sim, 4.0, 1.0, 3.0, 10.0, status.integral)
    assert expected != old_gain  # the change is visible in this state
    record = sim.step()
    assert abs(record.thrust_used - expected) <= 1e-12 * max(1.0, abs(expected))


# --- Scenario: The setpoint can be changed between steps ----------------------


def test_setpoint_can_be_changed_and_is_reported_back():
    sim = controlled()
    sim.run(400)
    sim.set_setpoint(20.0)
    assert sim.controller.setpoint == 20.0


def test_after_a_setpoint_change_the_drone_works_toward_the_new_setpoint():
    sim = controlled()
    sim.run(4000)  # settle near 10 m
    sim.set_setpoint(20.0)
    sim.run(4000)
    assert abs(sim.altitude - 20.0) < 0.5


def test_a_setpoint_change_starts_a_new_metrics_result_at_that_record():
    sim = controlled()
    sim.run(400)
    sim.set_setpoint(20.0)
    results = sim.step_metrics()
    assert len(results) == 2
    assert results[1].change_index == 400
    assert results[1].setpoint == 20.0


# --- Scenario: Changing Ki affects only the future ----------------------------


def test_changing_ki_keeps_the_integral_and_stops_its_growth():
    sim = controlled()
    sim.run(300)
    integral = sim.controller.integral
    assert integral != 0.0  # it really accumulated
    sim.set_gains(ki=0.0)
    assert sim.controller.integral == integral
    sim.run(200)
    assert sim.controller.integral == integral


# --- Scenario: A gain change does not start a new metrics result --------------


@pytest.mark.parametrize("gain", ["kp", "ki", "kd"])
def test_a_gain_change_does_not_start_a_new_metrics_result(gain):
    sim = controlled()
    sim.run(10)
    sim.set_gains(**{gain: 2.0})
    assert len(sim.step_metrics()) == 1


# --- Scenario: Setting the same setpoint again does nothing -------------------


def test_setting_the_same_setpoint_again_changes_nothing():
    sim = controlled()
    sim.run(10)
    before = snapshot(sim)
    sim.set_setpoint(10.0)
    assert snapshot(sim) == before


def test_setting_the_same_setpoint_again_adds_no_metrics_result():
    sim = controlled()
    sim.run(10)
    sim.set_setpoint(10.0)
    assert len(sim.step_metrics()) == 1


# --- Scenario Outline: An invalid change is rejected and nothing changes ------

INVALID = [
    ("kp", math.nan, ValueError),
    ("ki", -0.5, ValueError),
    ("kd", math.inf, ValueError),
    ("kp", math.nextafter(0.0, -1.0), ValueError),
    ("ki", True, TypeError),
    ("kd", "3", TypeError),
]


@pytest.mark.parametrize("gain, value, error", INVALID, ids=[f"{g}={v!r}" for g, v, _ in INVALID])
def test_invalid_gain_change_is_rejected_and_nothing_changes(gain, value, error):
    sim = controlled()
    sim.run(20)
    before = snapshot(sim)
    with pytest.raises(error, match=gain):
        sim.set_gains(**{gain: value})
    assert snapshot(sim) == before


def test_partly_invalid_gain_change_applies_nothing():
    sim = controlled()
    before = snapshot(sim)
    with pytest.raises(ValueError, match="ki"):
        sim.set_gains(kp=5.0, ki=-1.0)
    assert snapshot(sim) == before
    assert sim.controller.kp == 4.0


@pytest.mark.parametrize(
    "value, error",
    [(-1.0, ValueError), (math.inf, ValueError), (math.nan, ValueError),
     (math.nextafter(0.0, -1.0), ValueError), ("10", TypeError)],
    ids=["-1", "+inf", "nan", "-eps", "str"],
)
def test_invalid_setpoint_change_is_rejected_and_nothing_changes(value, error):
    sim = controlled()
    sim.run(20)
    before = snapshot(sim)
    with pytest.raises(error, match="setpoint"):
        sim.set_setpoint(value)
    assert snapshot(sim) == before


def test_setpoint_zero_is_accepted():
    sim = controlled()
    sim.set_setpoint(0.0)
    assert sim.controller.setpoint == 0.0


def test_set_gains_without_any_gain_is_rejected():
    sim = controlled()
    with pytest.raises(TypeError):
        sim.set_gains()


# --- ARCHITECTURE D-14: settings cannot be changed while the controller is off -


@pytest.mark.parametrize(
    "call", [lambda s: s.set_gains(kp=1.0), lambda s: s.set_setpoint(5.0)], ids=["gains", "setpoint"]
)
def test_settings_cannot_be_changed_while_the_controller_is_off(call):
    sim = make()
    before = snapshot(sim)
    with pytest.raises(RuntimeError, match="controller is off"):
        call(sim)
    assert snapshot(sim) == before
