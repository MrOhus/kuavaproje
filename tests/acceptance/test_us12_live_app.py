"""US-12 Start the app and watch the drone fly under PID control — acceptance tests.

Expected behaviour comes from docs/design/DESIGN_f351eee.md (US-12, OQ-34,
OQ-36, OQ-41) and docs/architecture/ARCHITECTURE_899eaea.md (LiveSession,
real-time pacing predicate with MAX_STEPS_PER_FRAME = 50, App, Startup).
Scenarios that need a later story stay strict xfail until it lands (IQ-9
practice).
"""

import os
import pathlib
import subprocess
import sys
import time

import pytest

from gui_helpers import FakeClock, record_bytes
from kuava_sim import SimConfig, Simulation

SRC = pathlib.Path(__file__).resolve().parents[2] / "src"


def child_env():
    env = dict(os.environ)
    env["PYTHONPATH"] = str(SRC) + os.pathsep + env.get("PYTHONPATH", "")
    return env


def new_session(now=0.0):
    from kuava_sim import live

    return live.LiveSession(now)


def stderr_lines(text):
    return [line for line in text.splitlines() if line.strip()]


# --- Scenario: The app starts with one command and the drone takes off --------


def test_start_command_opens_the_app_and_keeps_running(tk_root):
    # tk_root only makes this skip on a machine without a display (AQ-21).
    proc = subprocess.Popen(
        [sys.executable, "-m", "kuava_sim"], env=child_env(),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        time.sleep(3.0)
        still_running = proc.poll() is None
    finally:
        proc.kill()
        _, err = proc.communicate(timeout=30)
    assert still_running, err
    assert err == ""


def test_app_starts_with_the_fixed_drone_on_the_ground_and_the_controller_on(tk_root):
    from kuava_sim import app

    a = app.App(tk_root, clock=FakeClock())
    sim = a.session.sim
    assert sim.config == SimConfig(
        mass=1.0, gravity=9.81, drag_coeff=0.5, max_thrust=30.0,
        initial_altitude=0.0, initial_velocity=0.0,
    )
    assert (sim.time, sim.altitude, sim.velocity) == (0.0, 0.0, 0.0)
    status = sim.controller
    assert (status.on, status.kp, status.ki, status.kd, status.setpoint) == (
        True, 4.0, 1.0, 3.0, 10.0,
    )
    assert tk_root.winfo_exists()
    a.close()


def test_altitude_rises_toward_the_setpoint_frame_by_frame(tk_root):
    from kuava_sim import app

    clock = FakeClock(0.0)
    a = app.App(tk_root, clock=clock)
    heights = []
    for frame in range(1, 33):  # 32 frames of 1/32 s = 1 s
        clock.now = frame / 32
        a.frame()
        heights.append(a.session.sim.altitude)
    assert a.session.sim.step_count == 200
    assert heights[0] > 0.0
    assert all(later > earlier for earlier, later in zip(heights, heights[1:]))
    assert 0.0 < heights[-1] < 10.0  # still on its way up to 10 m
    a.close()


def test_plotted_altitude_rises_toward_the_setpoint():
    s = new_session(0.0)
    for frame in range(1, 33):
        s.tick(frame / 32)
    points = s.plot_points()
    altitudes = [p[1] for p in points]
    assert altitudes[0] == 0.0
    assert altitudes[-1] > 1.0
    assert {p[2] for p in points} == {10.0}


# --- Scenario: The app runs in real time --------------------------------------


def test_simulated_time_follows_the_wall_clock_in_whole_steps():
    start = 100.0
    s = new_session(start)
    now = start
    for gap in [0.004, 0.011, 0.0167, 0.2, 0.25, 0.03, 0.001, 0.1, 0.0333, 0.09, 0.016]:
        now += gap
        s.tick(now)
        expected = int((now - start) * 200)  # every step due so far, never more
        assert s.sim.step_count == expected
        assert s.sim.time == expected / 200
        assert s.sim.time <= now - start


def test_no_steps_are_taken_when_no_time_has_passed():
    s = new_session(5.0)
    assert s.tick(5.0) == 0
    assert s.tick(5.004) == 0  # less than one 5 ms step
    assert s.sim.step_count == 0


# --- Scenario: The app slows down instead of jumping ahead --------------------


def test_exactly_a_quarter_second_due_is_taken_in_full():
    s = new_session(0.0)
    assert s.tick(0.25) == 50  # 50 steps due: at the limit, nothing dropped
    assert s.tick(0.5) == 50
    assert s.sim.step_count == 100


def test_more_than_a_quarter_second_due_takes_50_and_drops_the_rest():
    s = new_session(0.0)
    assert s.tick(0.255) == 50  # 51 due: one step over the limit
    assert s.tick(0.26) == 1  # re-anchored: only the new 5 ms, the dropped step is gone
    assert s.sim.step_count == 51


def test_a_long_stall_never_causes_a_burst_of_catch_up_steps():
    s = new_session(0.0)
    s.tick(0.25)
    assert s.tick(10.25) == 50  # 10 s stall: still only 50 steps
    assert s.sim.time == 0.5
    assert s.sim.time < 10.25  # the simulation is now behind the wall clock
    assert s.tick(10.375) == 25  # then it carries on at real speed from there


# --- Scenario: The live simulation is the same deterministic simulation -------


@pytest.mark.xfail(strict=True, reason="sliders are US-13 and gusts are US-16 (IQ-9 practice)")
def test_live_run_replays_bit_identically_without_the_gui():
    from kuava_sim import live

    s = live.LiveSession(0.0)
    script = {
        40: ("gain", "kp", 6.0), 90: ("setpoint", 25.0), 130: ("gust",),
        170: ("gain", "kd", 2.5), 200: ("setpoint", 5.0), 260: ("gust",),
    }
    log = []
    for frame in range(1, 301):
        s.tick(frame * 0.0625)
        action = script.get(frame)
        if action is None:
            continue
        log.append((s.sim.step_count, action))
        if action[0] == "gain":
            s.set_gain(action[1], action[2])
        elif action[0] == "setpoint":
            s.release_setpoint(action[1])
        else:
            s.press_gust()

    replay = Simulation(live.APP_CONFIG)
    replay.enable_controller(kp=4.0, ki=1.0, kd=3.0, setpoint=10.0)
    for k, action in log:
        replay.run(k - replay.step_count)
        if action[0] == "gain":
            replay.set_gains(**{action[1]: action[2]})
        elif action[0] == "setpoint":
            replay.set_setpoint(action[1])
        else:
            replay.gust()
    replay.run(s.sim.step_count - replay.step_count)
    assert record_bytes(replay) == record_bytes(s.sim)
    assert s.sim.step_count == 3750


# --- Scenario Outline: The app cannot start -----------------------------------


def test_missing_tkinter_prints_one_plain_line_and_exits_with_1(monkeypatch, capsys):
    from kuava_sim import __main__ as entry

    monkeypatch.setitem(sys.modules, "tkinter", None)  # import tkinter now fails
    assert entry.main() == 1
    err = capsys.readouterr().err
    assert stderr_lines(err) == [
        "Cannot start: Tkinter is not installed. Install Python with Tcl/Tk "
        "support (on Linux the python3-tk package)."
    ]
    assert "Traceback" not in err


def test_no_display_prints_one_plain_line_and_exits_with_1(monkeypatch, capsys):
    import tkinter

    from kuava_sim import __main__ as entry

    def no_display(*args, **kwargs):
        raise tkinter.TclError("no display name and no $DISPLAY environment variable")

    monkeypatch.setattr(tkinter, "Tk", no_display)
    assert entry.main() == 1
    err = capsys.readouterr().err
    assert stderr_lines(err) == [
        "Cannot start: no display available. Run the app from a desktop session."
    ]
    assert "Traceback" not in err


def test_any_other_startup_error_prints_one_plain_line_and_exits_with_1(
    tk_root, monkeypatch, capsys
):
    from kuava_sim import __main__ as entry
    from kuava_sim import app

    def broken(*args, **kwargs):
        raise ValueError("the window layout could not be built")

    monkeypatch.setattr(app, "App", broken)
    assert entry.main() == 1
    err = capsys.readouterr().err
    assert stderr_lines(err) == ["Cannot start: the window layout could not be built"]
    assert "Traceback" not in err


def test_the_real_start_command_without_tkinter_exits_with_1_and_no_traceback():
    code = (
        "import sys, runpy; sys.modules['tkinter'] = None; "
        "runpy.run_module('kuava_sim', run_name='__main__')"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code], env=child_env(),
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 1
    assert len(stderr_lines(proc.stderr)) == 1
    assert stderr_lines(proc.stderr)[0].startswith("Cannot start: Tkinter is not installed.")
    assert "Traceback" not in proc.stderr


def test_closing_the_window_normally_exits_with_0(tk_root, monkeypatch, capsys):
    import tkinter

    from kuava_sim import __main__ as entry

    real_tk = tkinter.Tk

    def closing_soon(*args, **kwargs):
        root = real_tk(*args, **kwargs)
        root.after(500, root.destroy)  # the user closes the window
        return root

    monkeypatch.setattr(tkinter, "Tk", closing_soon)
    assert entry.main() == 0
    assert capsys.readouterr().err == ""
