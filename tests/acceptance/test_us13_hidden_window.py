"""US-13 sliders when the window is not drawn on screen — acceptance tests.

Found in the pre-submission check: Tk runs a Scale's command only when the
slider is redrawn, so a gain change made while the window was minimized,
hidden or on a locked screen was not applied until the window was shown
again. A gain change must apply from the next step whether or not the
window is drawn (DESIGN_f351eee.md OQ-36, ARCHITECTURE_899eaea.md App).

Window tests that need Tk to deliver mouse or key events skip with the
reason shown when the window is not visible (operator, same as AQ-21).
"""

import pytest

from gui_helpers import FakeClock


def hidden_app(root):
    from kuava_sim import app

    a = app.App(root, clock=FakeClock(0.0))
    root.withdraw()  # not drawn on screen, like a minimized window
    root.update()
    assert not a.sliders["kp"].winfo_viewable()
    return a


@pytest.mark.parametrize("name, value", [("kp", 8.0), ("ki", 2.5), ("kd", 0.0)])
def test_gain_slider_applies_while_the_window_is_not_drawn(tk_root, name, value):
    a = hidden_app(tk_root)
    a.sliders[name].set(value)
    tk_root.update()
    assert a.session.values[name] == value
    assert getattr(a.session.sim.controller, name) == value
    a.close()


def test_every_gain_change_while_hidden_is_applied_in_order(tk_root):
    a = hidden_app(tk_root)
    for value in (5.0, 6.5, 7.0, 12.3):
        a.sliders["kp"].set(value)
        tk_root.update()
        assert a.session.sim.controller.kp == value
    a.close()


def test_setpoint_slider_still_waits_for_release_while_hidden(tk_root):
    a = hidden_app(tk_root)
    a.sliders["setpoint"].set(40.0)
    tk_root.update()
    assert a.session.sim.controller.setpoint == 10.0
    assert len(a.session.sim.step_metrics()) == 1
    a.close()


def test_event_tests_skip_with_the_reason_when_the_window_is_not_visible(tk_root):
    from gui_helpers import require_visible

    a = hidden_app(tk_root)
    with pytest.raises(pytest.skip.Exception) as info:
        require_visible(tk_root, a.sliders["setpoint"])
    assert "window not visible on screen" in str(info.value)
    a.close()


def test_event_tests_run_when_the_window_is_visible(tk_root):
    from gui_helpers import require_visible
    from kuava_sim import app

    a = app.App(tk_root, clock=FakeClock(0.0))
    tk_root.update()
    if not a.sliders["setpoint"].winfo_viewable():  # this machine cannot show it now
        a.close()
        pytest.skip("window not visible on screen; cannot check the visible case")
    require_visible(tk_root, a.sliders["setpoint"])  # must not skip
    a.close()
