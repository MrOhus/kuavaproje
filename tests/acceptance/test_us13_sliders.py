"""US-13 Tune the controller with sliders — acceptance tests.

Expected behaviour comes from docs/design/DESIGN_f351eee.md (US-13, OQ-36,
OQ-33) and docs/architecture/ARCHITECTURE_899eaea.md (SLIDERS,
LiveSession.set_gain / release_setpoint, App sliders: gains on every change,
setpoint on <ButtonRelease-1> and <KeyRelease>).
"""

import tkinter as tk

import pytest

from gui_helpers import FakeClock, require_visible

M, G = 1.0, 9.81
DT = 0.005

RANGES = [
    ("kp", 0.0, 50.0, 4.0),
    ("ki", 0.0, 20.0, 1.0),
    ("kd", 0.0, 20.0, 3.0),
    ("setpoint", 0.0, 100.0, 10.0),
]
NAMES = [r[0] for r in RANGES]


def make_app(root, clock=None):
    from kuava_sim import app

    a = app.App(root, clock=clock or FakeClock(0.0))
    root.update()  # map the window so events reach the sliders
    return a


def drag(root, scale, value):
    """Move a slider without letting go (the value change fires its command)."""
    scale.set(value)
    root.update()


def let_go(root, scale, how="mouse"):
    if how == "mouse":
        scale.event_generate("<ButtonRelease-1>", x=1, y=1)
    else:  # key events go to the widget with keyboard focus
        scale.focus_force()
        root.update()
        scale.event_generate("<KeyRelease>", keysym="Right")
    root.update()


def next_thrust(sim, kp, ki, kd, setpoint):
    """The controlled-step formula (ARCHITECTURE_3dbd8e9.md) for the next step."""
    h, v = sim.altitude, sim.velocity
    e = setpoint - h
    integral = sim.controller.integral + (ki * e) * DT
    return min(max(((M * G + kp * e) + integral) - kd * v, 0.0), 30.0)


def walk(a, clock, seconds):
    """Advance the fake clock frame by frame (1/32 s per frame)."""
    for _ in range(int(seconds * 32)):
        clock.now += 1 / 32
        a.frame()


# --- Scenario Outline: Slider ranges, steps and start values ------------------


@pytest.mark.parametrize("name, low, high, start", RANGES, ids=NAMES)
def test_slider_range_step_and_start_value(tk_root, name, low, high, start):
    a = make_app(tk_root)
    scale = a.sliders[name]
    assert float(scale.cget("from")) == low
    assert float(scale.cget("to")) == high
    assert float(scale.cget("resolution")) == 0.1
    assert scale.get() == start
    assert int(scale.cget("showvalue")) == 1  # the current value is shown next to it
    assert a.session.values[name] == start
    a.close()


# --- Scenario Outline: A slider cannot go outside its range -------------------


@pytest.mark.parametrize("name, low, high, start", RANGES, ids=NAMES)
def test_slider_cannot_go_outside_its_range(tk_root, name, low, high, start):
    a = make_app(tk_root)
    scale = a.sliders[name]
    if name == "setpoint":  # needs the release event
        require_visible(tk_root, scale)
    for target, expected in ((low - 5.0, low), (high + 5.0, high)):
        drag(tk_root, scale, target)
        if name == "setpoint":
            let_go(tk_root, scale)
        assert scale.get() == expected
        assert a.session.values[name] == expected
        assert getattr(a.session.sim.controller, name) == expected  # used, not rejected
    assert a.session.sim.controller.on is True
    a.close()


# --- Scenario: A gain takes effect while its slider is dragged ----------------


def test_gain_takes_effect_while_dragging_and_adds_no_metrics_row(tk_root):
    clock = FakeClock(0.0)
    a = make_app(tk_root, clock)
    walk(a, clock, 1.0)
    scale = a.sliders["kp"]
    drag(tk_root, scale, 5.0)
    assert a.session.sim.controller.kp == 5.0
    drag(tk_root, scale, 6.0)  # still dragging
    sim = a.session.sim
    assert sim.controller.kp == 6.0
    assert scale.get() == 6.0 == a.session.values["kp"]  # shown value is the value in use
    expected = next_thrust(sim, 6.0, 1.0, 3.0, 10.0)
    old_gain = next_thrust(sim, 4.0, 1.0, 3.0, 10.0)
    assert expected != old_gain
    clock.now += 1 / 128  # exactly one more step is due (0.005 would round down to 0)
    a.frame()  # exactly one new step
    assert sim.records[-1].thrust_used == pytest.approx(expected, rel=1e-12, abs=1e-12)
    assert len(sim.step_metrics()) == 1
    a.close()


def test_session_set_gain_applies_from_the_next_step():
    from kuava_sim import live

    s = live.LiveSession(0.0)
    s.tick(0.5)
    before = len(s.sim.records)
    s.set_gain("kd", 7.5)
    assert len(s.sim.records) == before  # applying a gain takes no step
    assert s.sim.controller.kd == 7.5
    assert s.values["kd"] == 7.5
    assert len(s.sim.step_metrics()) == 1


# --- Scenario: The setpoint changes only when the slider is released ----------


@pytest.mark.parametrize("how", ["mouse", "key"])
def test_setpoint_changes_only_when_the_slider_is_released(tk_root, how):
    clock = FakeClock(0.0)
    a = make_app(tk_root, clock)
    walk(a, clock, 1.0)
    scale = a.sliders["setpoint"]
    require_visible(tk_root, scale)
    for value in (14.0, 19.5, 25.0):  # dragging through several values
        drag(tk_root, scale, value)
        assert a.session.sim.controller.setpoint == 10.0
        assert len(a.session.sim.step_metrics()) == 1
    let_go(tk_root, scale, how)
    sim = a.session.sim
    assert sim.controller.setpoint == 25.0
    results = sim.step_metrics()
    assert len(results) == 2  # exactly one new metrics row
    assert results[1].change_index == sim.step_count and results[1].setpoint == 25.0
    expected = next_thrust(sim, 4.0, 1.0, 3.0, 25.0)
    clock.now += 1 / 128  # exactly one more step is due (0.005 would round down to 0)
    a.frame()
    assert sim.records[-1].thrust_used == pytest.approx(expected, rel=1e-12, abs=1e-12)
    a.close()


def test_session_release_setpoint_makes_one_setpoint_change():
    from kuava_sim import live

    s = live.LiveSession(0.0)
    s.tick(0.5)
    s.release_setpoint(25.0)
    assert s.sim.controller.setpoint == 25.0
    assert s.values["setpoint"] == 25.0
    assert [r.setpoint for r in s.sim.step_metrics()] == [10.0, 25.0]


# --- Scenario: Releasing the setpoint slider at the current setpoint ----------


def test_releasing_at_the_current_setpoint_changes_nothing(tk_root):
    clock = FakeClock(0.0)
    a = make_app(tk_root, clock)
    walk(a, clock, 0.5)
    scale = a.sliders["setpoint"]
    require_visible(tk_root, scale)  # otherwise the release never arrives and nothing is checked
    drag(tk_root, scale, 30.0)
    drag(tk_root, scale, 10.0)
    let_go(tk_root, scale)
    assert a.session.sim.controller.setpoint == 10.0
    assert len(a.session.sim.step_metrics()) == 1
    a.close()


def test_session_release_at_the_current_setpoint_changes_nothing():
    from kuava_sim import live

    s = live.LiveSession(0.0)
    s.tick(0.5)
    s.release_setpoint(10.0)
    assert len(s.sim.step_metrics()) == 1


# --- Scenario: The GUI has no manual thrust -----------------------------------


def all_widgets(widget):
    yield widget
    for child in widget.winfo_children():
        yield from all_widgets(child)


def test_the_window_has_no_thrust_control_and_the_controller_stays_on(tk_root):
    clock = FakeClock(0.0)
    a = make_app(tk_root, clock)
    scales = [w for w in all_widgets(tk_root) if isinstance(w, tk.Scale)]
    assert sorted(a.sliders) == sorted(NAMES)
    assert len(scales) == 4
    assert not any("thrust" in str(s.cget("label")).lower() for s in scales)
    walk(a, clock, 3.0)
    assert a.session.sim.controller.on is True
    a.close()
