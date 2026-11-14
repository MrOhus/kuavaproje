"""US-9 Closed-loop thrust every step — acceptance tests.

Expected behaviour comes from docs/design/DESIGN_0bfd04e.md (US-9, OQ-27,
OQ-28) and the controlled-step predicate in
docs/architecture/ARCHITECTURE_3dbd8e9.md:
    e = setpoint - h;  I = I + (Ki*e)*dt;  cmd = ((m*g + Kp*e) + I) - Kd*v
then the unchanged Round 1 step caps cmd to [0, max_thrust].
"""

import struct
import warnings

import pytest

from kuava_sim import SimConfig, Simulation


DT = 0.005


def make(**cfg):
    cfg.setdefault("mass", 1.0)
    cfg.setdefault("gravity", 9.81)
    cfg.setdefault("max_thrust", 30.0)
    return Simulation(SimConfig(**cfg))


def within_eps(actual, expected):
    return abs(actual - expected) <= 1e-12 * max(1.0, abs(expected))


def record_bytes(sim):
    return [struct.pack("<6d", *r) for r in sim.records]


# --- Scenario: Thrust follows the controller formula --------------------------


def test_thrust_follows_the_controller_formula():
    sim = make(initial_altitude=8.0, initial_velocity=0.5)
    sim.enable_controller(kp=4.0, ki=0.0, kd=3.0, setpoint=10.0)
    record = sim.step()
    # 9.81 + 4 * (10 - 8) - 3 * 0.5 = 16.31
    assert within_eps(record.thrust_used, 16.31)
    assert record == sim.records[1]


def test_integral_is_updated_with_the_current_error_before_it_is_used():
    # ARCHITECTURE D-10: I = 0 + 2 * (10 - 8) * 0.005 = 0.02, used in the same step.
    sim = make(initial_altitude=8.0)
    sim.enable_controller(kp=0.0, ki=2.0, kd=0.0, setpoint=10.0)
    record = sim.step()
    assert within_eps(sim.controller.integral, 0.02)
    assert within_eps(record.thrust_used, 9.83)


def test_every_step_follows_the_formula_from_the_exact_state_at_its_start():
    sim = make(drag_coeff=0.5, initial_altitude=50.0)
    kp, ki, kd, sp = 4.0, 1.0, 3.0, 52.0
    sim.enable_controller(kp=kp, ki=ki, kd=kd, setpoint=sp)
    integral = 0.0
    for _ in range(600):
        h, v = sim.altitude, sim.velocity
        e = sp - h
        integral = integral + (ki * e) * DT
        expected = ((1.0 * 9.81 + kp * e) + integral) - kd * v
        assert 0.0 < expected < 30.0  # unsaturated, so the command is used as is
        record = sim.step()
        assert within_eps(record.thrust_used, expected)
    assert within_eps(sim.controller.integral, integral)
    assert abs(sim.altitude - 50.0) > 1.0  # it really moved toward 52 m


# --- Scenario: Holding at the setpoint uses exactly the hover thrust ----------


def test_holding_at_the_setpoint_uses_the_hover_thrust():
    sim = make(mass=1.5, drag_coeff=0.2, initial_altitude=100.0)
    sim.enable_controller(kp=4.0, ki=1.0, kd=3.0, setpoint=100.0)
    for _ in range(2000):
        record = sim.step()
        assert within_eps(record.altitude, 100.0)
        assert within_eps(record.thrust_used, 1.5 * 9.81)


def test_holding_at_the_setpoint_is_bit_exact():
    # ARCHITECTURE: at e = 0, I = 0, v = 0 the command is exactly m*g.
    sim = make(mass=1.5, drag_coeff=0.2, initial_altitude=100.0)
    sim.enable_controller(kp=4.0, ki=1.0, kd=3.0, setpoint=100.0)
    sim.run(2000)
    assert set(sim.records.column("altitude")) == {100.0}
    assert set(sim.records.column("thrust_used")[1:]) == {1.5 * 9.81}


# --- Scenario: A setpoint change gives no derivative spike --------------------


def test_a_setpoint_change_gives_no_derivative_spike():
    sim = make(initial_altitude=100.0)
    sim.enable_controller(kp=0.0, ki=0.0, kd=3.0, setpoint=100.0)
    sim.run(10)
    sim.set_setpoint(110.0)
    record = sim.step()
    assert record.thrust_used == 1.0 * 9.81


# --- Scenarios: thrust is capped silently -------------------------------------


def test_controller_thrust_is_capped_silently_at_the_maximum():
    sim = make(max_thrust=20.0, initial_altitude=10.0)
    sim.enable_controller(kp=50.0, ki=0.0, kd=0.0, setpoint=1000.0)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        record = sim.step()
    assert caught == []
    assert record.thrust_used == 20.0
    assert sim.held_thrust > 20.0  # the command itself was above the limit


def test_controller_cannot_ask_for_negative_thrust():
    sim = make(initial_altitude=100.0)
    sim.enable_controller(kp=50.0, ki=0.0, kd=0.0, setpoint=0.0)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        record = sim.step()
    assert caught == []
    assert record.thrust_used == 0.0
    assert sim.held_thrust < 0.0


# --- Scenario: No anti-windup in Round 2 --------------------------------------


def test_no_anti_windup_the_integral_keeps_growing_at_the_limit():
    sim = make(max_thrust=20.0, initial_altitude=10.0)
    sim.enable_controller(kp=50.0, ki=1.0, kd=0.0, setpoint=1000.0)
    expected = 0.0
    for k in range(1, 401):
        expected = expected + (1.0 * (1000.0 - sim.records[k - 1].altitude)) * DT
        sim.step()
    assert set(sim.records.column("thrust_used")[1:]) == {20.0}  # held at the limit
    assert within_eps(sim.controller.integral, expected)
    assert sim.controller.integral > 9.0  # roughly 400 * 0.005 * 980, never clamped


# --- Scenario: Closed-loop runs are deterministic -----------------------------


def closed_loop_run():
    sim = make(drag_coeff=0.5, initial_altitude=0.0)
    sim.enable_controller(kp=4.0, ki=1.0, kd=3.0, setpoint=10.0)
    for k in range(10000):
        if k == 2500:
            sim.set_gains(kp=6.0)
        if k == 5000:
            sim.set_setpoint(25.0)
        if k == 7500:
            sim.set_setpoint(5.0)
        sim.step()
    return sim


def test_closed_loop_runs_give_identical_records():
    a, b = closed_loop_run(), closed_loop_run()
    assert record_bytes(a) == record_bytes(b)
    assert len(set(a.records.column("thrust_used"))) > 1000  # really controlled


def test_closed_loop_runs_give_identical_metrics():
    a, b = closed_loop_run(), closed_loop_run()
    assert [struct.pack("<9d", *r[1:]) for r in a.step_metrics()] == [
        struct.pack("<9d", *r[1:]) for r in b.step_metrics()
    ]


def test_run_n_under_control_equals_n_single_steps():
    single = make(drag_coeff=0.5, initial_altitude=3.0)
    batch = make(drag_coeff=0.5, initial_altitude=3.0)
    for sim in (single, batch):
        sim.enable_controller(kp=4.0, ki=1.0, kd=3.0, setpoint=10.0)
    for _ in range(1000):
        single.step()
    batch.run(1000)
    assert record_bytes(batch) == record_bytes(single)
    assert batch.altitude > 5.0  # climbed from 3 m with no manual thrust: really controlled
