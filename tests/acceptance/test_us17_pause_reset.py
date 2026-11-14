"""US-17 Pause and reset — acceptance tests.

Expected behaviour comes from docs/design/DESIGN_f351eee.md (US-17, OQ-37)
and docs/architecture/ARCHITECTURE_899eaea.md (LiveSession.pause / resume /
reset: resume and reset re-anchor the clock; reset builds a new Simulation
with the current slider values and keeps the pause state (D-18); the
Pause/Resume and Reset buttons).
"""

import pytest

from gui_helpers import FakeClock, record_bytes

M, G = 1.0, 9.81
DT = 0.005


def running(seconds=1.0):
    from kuava_sim import live

    s = live.LiveSession(0.0)
    for frame in range(1, int(seconds * 16) + 1):
        s.tick(frame / 16)
    return s


def next_thrust(sim, kp, ki, kd, setpoint):
    h, v = sim.altitude, sim.velocity
    e = setpoint - h
    integral = sim.controller.integral + (ki * e) * DT
    return min(max(((M * G + kp * e) + integral) - kd * v, 0.0), 30.0)


# --- Scenario: Pause and resume -----------------------------------------------


def test_paused_session_takes_no_steps():
    s = running(1.0)
    assert s.sim.step_count == 200
    s.pause()
    assert s.paused is True
    assert s.tick(1.5) == 0
    assert s.tick(30.0) == 0
    assert s.sim.step_count == 200


def test_resume_continues_from_exactly_the_paused_state():
    paused, straight = running(1.0), running(1.0)
    paused.pause()
    paused.tick(2.0)
    paused.resume(7.0)  # 6 s later
    assert paused.paused is False
    for frame in range(1, 5):
        paused.tick(7.0 + frame / 16)
        straight.tick(1.0 + frame / 16)
    assert paused.sim.step_count == straight.sim.step_count == 250
    assert record_bytes(paused.sim) == record_bytes(straight.sim)  # no jump at all


def test_toggle_pause_switches_both_ways():
    s = running(0.5)
    s.toggle_pause(0.5)
    assert s.paused is True
    s.toggle_pause(2.0)
    assert s.paused is False
    assert s.tick(2.0625) == 12  # real time from the moment of resuming


# --- Scenario: Sliders work while paused and apply on resume ------------------


def test_sliders_work_while_paused_and_apply_on_resume():
    s = running(1.0)
    s.pause()
    s.set_gain("kd", 5.0)
    s.release_setpoint(20.0)
    assert (s.values["kd"], s.values["setpoint"]) == (5.0, 20.0)
    assert (s.sim.controller.kd, s.sim.controller.setpoint) == (5.0, 20.0)
    change = s.sim.step_metrics()[-1]
    assert (change.change_index, change.change_time) == (200, 1.0)  # at the paused step
    assert s.sim.step_count == 200  # still no steps while paused
    expected = next_thrust(s.sim, 4.0, 1.0, 5.0, 20.0)
    s.resume(9.0)
    s.tick(9.0 + 1 / 128)  # exactly one step
    assert s.sim.step_count == 201
    assert s.sim.records[-1].thrust_used == pytest.approx(expected, rel=1e-12, abs=1e-12)


def test_window_pause_button_and_sliders_while_paused(tk_root):
    from kuava_sim import app

    clock = FakeClock(0.0)
    a = app.App(tk_root, clock=clock)
    tk_root.update()
    clock.now = 0.25
    a.frame()
    assert a.pause_button.cget("text") == "Pause"
    a.pause_button.invoke()
    a.frame()
    assert a.session.paused is True
    assert a.pause_button.cget("text") == "Resume"
    scale = a.sliders["setpoint"]
    scale.set(30.0)
    tk_root.update()
    scale.event_generate("<ButtonRelease-1>", x=1, y=1)
    tk_root.update()
    assert a.session.sim.controller.setpoint == 30.0
    clock.now = 3.0
    a.frame()
    assert a.session.sim.step_count == 50  # paused: nothing more
    a.pause_button.invoke()
    a.frame()
    assert a.pause_button.cget("text") == "Pause"
    clock.now = 3.25
    a.frame()
    assert a.session.sim.step_count == 100
    a.close()


# --- Scenario: Reset returns to the start and keeps the slider values ---------


def test_reset_returns_to_the_start_with_the_current_slider_values():
    s = running(2.0)
    s.set_gain("kp", 6.0)
    s.set_gain("ki", 0.5)
    s.set_gain("kd", 2.0)
    s.release_setpoint(20.0)
    s.press_gust()
    s.tick(2.0 + 1 / 16)  # the gust is in progress
    old_sim = s.sim
    s.reset(10.0)
    sim = s.sim
    assert sim is not old_sim  # a new simulation
    assert (sim.time, sim.altitude, sim.velocity, len(sim.records)) == (0.0, 0.0, 0.0, 1)
    status = sim.controller
    assert (status.on, status.kp, status.ki, status.kd, status.setpoint, status.integral) == (
        True, 6.0, 0.5, 2.0, 20.0, 0.0,
    )
    assert s.values == {"kp": 6.0, "ki": 0.5, "kd": 2.0, "setpoint": 20.0}
    assert len(s.plot_points()) == 1
    rows = s.metrics_rows()
    assert len(rows) == 1 and (rows[0].change_index, rows[0].setpoint) == (0, 20.0)
    for frame in range(1, 9):  # 0.5 s after the reset
        s.tick(10.0 + frame / 16)
    assert sim.step_count == 100  # real time counted from the reset
    for r in sim.records[1:]:
        assert r.acceleration == ((r.thrust_used - M * G) + r.drag) / M  # no gust left


def test_window_reset_button_clears_plots_and_table(tk_root):
    from kuava_sim import app

    clock = FakeClock(0.0)
    a = app.App(tk_root, clock=clock)
    for frame in range(1, 33):
        clock.now = frame / 16
        a.frame()
    a.session.release_setpoint(25.0)
    clock.now = 2.5
    a.frame()
    assert len(a.table.get_children()) == 2
    a.reset_button.invoke()
    a.frame()
    assert a.session.sim.step_count == 0
    assert len(a.table.get_children()) == 1
    assert len(a.altitude_plot.coords(a.lines["altitude"])) == 4  # one point, drawn twice
    a.close()


# --- Scenario Outline: Reset keeps the pause state ----------------------------


@pytest.mark.parametrize("paused", [False, True], ids=["running", "paused"])
def test_reset_keeps_the_pause_state(paused):
    s = running(1.0)
    if paused:
        s.pause()
    s.reset(5.0)
    assert s.paused is paused
    taken = s.tick(5.25)
    assert taken == (0 if paused else 50)
