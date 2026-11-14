"""US-18 Clear error messages instead of crashes — acceptance tests.

Expected behaviour comes from docs/design/DESIGN_f351eee.md (US-18, OQ-41)
and docs/architecture/ARCHITECTURE_899eaea.md D-23: every error while the
app runs goes to session.fail(exc), which pauses and sets a plain message
(str(exc) for ValueError / TypeError / RuntimeError, otherwise
"Unexpected error: <message>" or "Unexpected error (<type>)"); the window
shows it in red; no pop-ups; nothing is printed anywhere; Resume or Reset
clears it.
"""

import pytest

from gui_helpers import FakeClock


def make_app(root, clock):
    from kuava_sim import app

    a = app.App(root, clock=clock)
    root.update()
    return a


# --- the plain message itself (session.fail) ----------------------------------


@pytest.mark.parametrize(
    "exc, message",
    [
        (ValueError("setpoint must not be below 0 (got -1.0)"),
         "setpoint must not be below 0 (got -1.0)"),
        (TypeError("kp must be a number (got '4')"), "kp must be a number (got '4')"),
        (RuntimeError("the controller is off; turn it on first"),
         "the controller is off; turn it on first"),
        (ZeroDivisionError("float division by zero"), "Unexpected error: float division by zero"),
        (KeyError(), "Unexpected error (KeyError)"),
    ],
    ids=["ValueError", "TypeError", "RuntimeError", "other", "other-no-message"],
)
def test_fail_pauses_and_sets_a_plain_message(exc, message, capfd):
    from kuava_sim import live

    s = live.LiveSession(0.0)
    s.tick(0.25)
    s.fail(exc)
    assert s.paused is True
    assert s.message == message
    assert "Traceback" not in s.message
    out, err = capfd.readouterr()
    assert (out, err) == ("", "")  # nothing printed anywhere


def test_no_message_before_any_error():
    from kuava_sim import live

    assert live.LiveSession(0.0).message == ""


# --- Scenario: An unexpected error is reported, not a crash -------------------


def test_an_error_during_a_frame_is_shown_in_red_and_pauses(tk_root, capfd):
    clock = FakeClock(0.0)
    a = make_app(tk_root, clock)
    clock.now = 0.25
    a.frame()

    def broken_step(thrust=None):
        raise ZeroDivisionError("float division by zero")

    a.session.sim.step = broken_step
    clock.now = 0.5
    a._loop()  # the real frame loop, which must catch it
    assert tk_root.winfo_exists()  # the app stays open
    assert a.session.paused is True
    assert a.error_label.cget("text") == "Unexpected error: float division by zero"
    assert str(a.error_label.cget("fg")) == "red"
    assert a.pause_button.cget("text") == "Resume"
    out, err = capfd.readouterr()
    assert (out, err) == ("", "")
    a.close()


def test_an_error_in_a_button_callback_is_shown_and_pauses(tk_root, capfd):
    a = make_app(tk_root, FakeClock(0.0))

    def broken_gust():
        raise OSError("the gust could not start")

    a.session.press_gust = broken_gust
    a.gust_button.invoke()  # Tk reports callback errors through report_callback_exception
    tk_root.update()
    assert tk_root.winfo_exists()
    assert a.session.paused is True
    assert a.error_label.cget("text") == "Unexpected error: the gust could not start"
    out, err = capfd.readouterr()
    assert (out, err) == ("", "")  # no traceback printed, no pop-up
    a.close()


def test_a_repeated_error_does_not_pile_up(tk_root):
    a = make_app(tk_root, FakeClock(0.0))
    for _ in range(5):
        a.session.fail(ValueError("kp must not be below 0 (got -1.0)"))
    a.frame()
    assert a.error_label.cget("text") == "kp must not be below 0 (got -1.0)"
    a.close()


# --- Scenario: A rejected simulation request is shown with its message --------


def test_a_rejected_request_shows_the_simulation_message(tk_root, capfd):
    clock = FakeClock(0.0)
    a = make_app(tk_root, clock)
    a.session.sim.disable_controller()  # now a setpoint change is rejected
    scale = a.sliders["setpoint"]
    scale.set(20.0)
    tk_root.update()
    scale.event_generate("<ButtonRelease-1>", x=1, y=1)
    tk_root.update()
    a.frame()
    assert a.error_label.cget("text") == "the controller is off; turn it on first"
    assert a.session.paused is True
    assert tk_root.winfo_exists()
    out, err = capfd.readouterr()
    assert (out, err) == ("", "")
    a.close()


# --- Scenario: The user can continue after an error ---------------------------


def test_reset_after_an_error_restarts_from_time_0_and_clears_the_message(tk_root):
    clock = FakeClock(0.0)
    a = make_app(tk_root, clock)
    clock.now = 1.0
    a.frame()
    a.session.fail(ZeroDivisionError("float division by zero"))
    a.frame()
    a.reset_button.invoke()
    a.frame()
    assert a.session.sim.time == 0.0
    assert a.session.message == ""
    assert a.error_label.cget("text") == ""
    assert a.session.paused is True  # reset keeps the pause state (US-17)
    a.close()


def test_resume_after_an_error_clears_the_message():
    from kuava_sim import live

    s = live.LiveSession(0.0)
    s.fail(RuntimeError("the controller is off; turn it on first"))
    s.resume(1.0)
    assert s.message == ""
    assert s.paused is False
