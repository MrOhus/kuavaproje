"""US-16 Wind gust disturbance — acceptance tests.

Expected behaviour comes from docs/design/DESIGN_f351eee.md (US-16, OQ-35,
OQ-37) and docs/architecture/ARCHITECTURE_899eaea.md (GUST_FORCE = 5 N,
GUST_STEPS = 100, Simulation.gust() with no read-back (D-19), records keep
six fields and the acceleration includes the gust (D-20), step-with-gust
predicate, LiveSession.press_gust, the gust button).
"""

import pytest

from gui_helpers import FakeClock, record_bytes
from kuava_sim import SimConfig, Simulation

M, G, B = 1.0, 9.81, 0.5
DT = 0.005


def plain(**cfg):
    cfg.setdefault("mass", M)
    cfg.setdefault("gravity", G)
    cfg.setdefault("drag_coeff", B)
    cfg.setdefault("max_thrust", 30.0)
    return Simulation(SimConfig(**cfg))


def with_gust(r):
    """The step-with-gust acceleration, from the record's own thrust and drag."""
    return (((r.thrust_used - M * G) + r.drag) - 5.0) / M


def without_gust(r):
    return ((r.thrust_used - M * G) + r.drag) / M


def assert_forced(sim, first, last):
    for i in range(first, last + 1):
        r, prev = sim.records[i], sim.records[i - 1]
        assert r.acceleration == with_gust(r), i
        assert r.velocity == prev.velocity + r.acceleration * DT, i


def assert_free(sim, first, last):
    for i in range(first, last + 1):
        r = sim.records[i]
        assert r.acceleration == without_gust(r), i


# --- Scenario: A gust is a 5 N downward force for 100 steps -------------------


def test_constants_are_5_newtons_for_100_steps():
    import kuava_sim

    assert kuava_sim.GUST_FORCE == 5.0
    assert kuava_sim.GUST_STEPS == 100


def test_gust_acts_on_exactly_the_next_100_steps():
    sim = plain(initial_altitude=50.0)
    sim.run(20, thrust=12.0)
    sim.gust()
    assert len(sim.records) == 21  # pressing takes no step
    sim.run(110)
    assert_free(sim, 1, 20)
    assert_forced(sim, 21, 120)  # steps k+1 ... k+100
    assert_free(sim, 121, 130)  # step k+101 has no extra force


def test_gust_changes_the_records_from_the_next_step_only():
    a, b = plain(initial_altitude=50.0), plain(initial_altitude=50.0)
    for sim in (a, b):
        sim.run(20, thrust=12.0)
    a.gust()
    a.run(30)
    b.run(30)
    assert record_bytes(a)[:21] == record_bytes(b)[:21]
    assert all(x != y for x, y in zip(record_bytes(a)[21:], record_bytes(b)[21:]))
    assert a.altitude < b.altitude  # pushed down


# --- Scenario: A press during a gust restarts it instead of adding to it ------


def test_a_second_press_restarts_the_100_steps_and_never_doubles_the_force():
    sim = plain(initial_altitude=50.0)
    sim.run(10, thrust=12.0)
    sim.gust()
    sim.run(40)
    sim.gust()  # 40 steps into the gust
    sim.run(110)
    assert_forced(sim, 11, 150)  # 40 steps, then 100 from the second press
    assert_free(sim, 151, 160)
    for i in range(11, 151):
        r = sim.records[i]
        assert r.acceleration != (((r.thrust_used - M * G) + r.drag) - 10.0) / M


# --- Scenario: The controller recovers after a gust ---------------------------


def hover_at_10():
    sim = plain(initial_altitude=10.0)
    sim.enable_controller(kp=4.0, ki=1.0, kd=3.0, setpoint=10.0)
    sim.run(400)
    return sim


def test_controller_is_not_told_about_the_gust():
    sim = hover_at_10()
    integral = sim.controller.integral
    sim.gust()
    for _ in range(100):
        h, v = sim.altitude, sim.velocity
        e = 10.0 - h
        integral = integral + (1.0 * e) * DT
        expected = min(max(((M * G + 4.0 * e) + integral) - 3.0 * v, 0.0), 30.0)
        record = sim.step()
        assert record.thrust_used == expected  # the plain Round 2 controller formula


def test_controller_recovers_after_a_gust():
    gusty, calm = hover_at_10(), hover_at_10()
    gusty.gust()
    gusty.run(100)
    calm.run(100)
    assert gusty.altitude < calm.altitude  # at the end of the gust it is lower
    worst = max(abs(10.0 - r.altitude) for r in gusty.records[400:501])
    assert worst > 0.01  # the gust really moved it
    gusty.run(6000)  # 30 s
    assert abs(10.0 - gusty.altitude) < worst


# --- Scenario: A gust on the ground does not push the drone below the ground --


def test_gust_on_the_ground_keeps_the_drone_at_altitude_0():
    sim = plain()  # on the ground at rest
    sim.gust()
    sim.run(100, thrust=12.0)  # 12 N lifts 1 kg, but not against 9.81 N + 5 N
    for r in sim.records[1:101]:
        assert (r.altitude, r.velocity, r.acceleration) == (0.0, 0.0, 0.0)
    sim.run(50)
    assert sim.altitude > 0.0  # after the gust the same thrust lifts it off


# --- Scenario: Gusts are deterministic ----------------------------------------


def gust_script():
    sim = hover_at_10()
    for k in (10, 60, 250):
        sim.run(k)
        sim.gust()
    sim.run(500)
    return sim


def test_same_presses_at_the_same_steps_give_identical_records():
    assert record_bytes(gust_script()) == record_bytes(gust_script())


def test_run_n_after_a_gust_equals_n_single_steps():
    a, b = hover_at_10(), hover_at_10()
    a.gust()
    b.gust()
    a.run(150)
    for _ in range(150):
        b.step()
    assert record_bytes(a) == record_bytes(b)


# --- Scenario: Without a gust press there is no disturbance -------------------


def test_without_a_press_every_step_is_the_round_2_step():
    sim = hover_at_10()
    sim.set_setpoint(20.0)
    sim.run(2000)
    assert_free(sim, 1, len(sim.records) - 1)


def test_records_keep_their_six_fields():
    from kuava_sim import Record

    assert Record._fields == (
        "time", "altitude", "velocity", "acceleration", "thrust_used", "drag",
    )


# --- The live session and the gust button -------------------------------------


def test_session_press_gust_pushes_the_live_drone():
    from kuava_sim import live

    s = live.LiveSession(0.0)
    for frame in range(1, 33):  # 2 s in frames of 1/16 s, never behind
        s.tick(frame / 16)
    assert s.sim.step_count == 400
    s.press_gust()
    for frame in range(33, 43):  # 0.625 s more
        s.tick(frame / 16)
    assert s.sim.step_count == 525
    assert_forced(s.sim, 401, 500)
    assert_free(s.sim, 501, 525)


def test_gust_button_starts_a_gust(tk_root):
    from kuava_sim import app

    clock = FakeClock(0.0)
    a = app.App(tk_root, clock=clock)
    tk_root.update()
    for frame in range(1, 17):
        clock.now = frame / 16
        a.frame()
    k = a.session.sim.step_count
    a.gust_button.invoke()
    clock.now += 0.25
    a.frame()
    assert a.session.sim.step_count == k + 50
    assert_forced(a.session.sim, k + 1, k + 50)
    a.close()


# --- Scenario: The gust button does nothing while paused ----------------------


@pytest.mark.xfail(strict=True, reason="pause arrives with US-17 (IQ-9 practice)")
def test_gust_button_is_disabled_and_ignored_while_paused(tk_root):
    from kuava_sim import app

    clock = FakeClock(0.0)
    a = app.App(tk_root, clock=clock)
    clock.now = 1.0
    a.frame()
    a.pause_button.invoke()
    a.frame()
    assert str(a.gust_button.cget("state")) == "disabled"
    a.session.press_gust()  # even a direct press is ignored while paused
    a.pause_button.invoke()  # resume
    k = a.session.sim.step_count
    clock.now = 1.25
    a.frame()
    assert_free(a.session.sim, k + 1, a.session.sim.step_count)
    a.close()
