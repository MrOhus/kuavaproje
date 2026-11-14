"""US-14 Live plots — acceptance tests.

Expected behaviour comes from docs/design/DESIGN_f351eee.md (US-14, OQ-38,
OQ-40) and docs/architecture/ARCHITECTURE_899eaea.md (PLOT_WINDOW = 20 s,
PLOT_EVERY = 4, plot buffer, x axis [0, 20] then [t - 20, t], thrust axis
fixed at [-1, 31] with lines at 0 and 30 N, fps shown in the window,
D-22 frame-rate test).
"""

import re

import pytest

from gui_check import frame_rate_failure
from gui_helpers import FakeClock


def session_after(seconds, frame=0.0625):
    from kuava_sim import live

    s = live.LiveSession(0.0)
    for k in range(1, int(round(seconds / frame)) + 1):
        s.tick(k * frame)
    return s


def make_app(root, clock):
    from kuava_sim import app

    a = app.App(root, clock=clock)
    root.update()
    return a


# --- Scenario: The plots show setpoint, altitude and the thrust used ----------


def test_plot_points_are_altitude_setpoint_and_thrust_used_every_4_steps():
    from kuava_sim import live

    s = live.LiveSession(0.0)
    for k in range(1, 33):  # 2 s
        s.tick(k * 0.0625)
    s.release_setpoint(25.0)  # after record 400
    for k in range(33, 49):  # 1 s more
        s.tick(k * 0.0625)
    sim = s.sim
    points = s.plot_points()
    assert len(points) == 601 // 4 + 1  # records 0, 4, 8, ..., 600
    for i, (t, h, setpoint, thrust) in enumerate(points):
        record = sim.records[4 * i]
        assert (t, h, thrust) == (record.time, record.altitude, record.thrust_used)
        assert setpoint == (10.0 if 4 * i <= 400 else 25.0)  # setpoint used for that step


def test_window_draws_altitude_setpoint_and_thrust_on_a_shared_time_axis(tk_root):
    clock = FakeClock(0.0)
    a = make_app(tk_root, clock)
    for k in range(1, 33):
        clock.now = k / 16  # 2 s
        a.frame()
    points = a.session.plot_points()
    for name in ("altitude", "setpoint"):
        coords = a.altitude_plot.coords(a.lines[name])
        assert len(coords) == 2 * len(points)
    thrust = a.thrust_plot.coords(a.lines["thrust"])
    altitude = a.altitude_plot.coords(a.lines["altitude"])
    assert len(thrust) == 2 * len(points)
    assert thrust[0::2] == altitude[0::2]  # same x for the same moments
    a.close()


def test_thrust_plot_marks_the_0_and_30_newton_limits(tk_root):
    a = make_app(tk_root, FakeClock(0.0))
    plot = a.thrust_plot
    y0 = plot.coords(a.limit_lines[0])
    y30 = plot.coords(a.limit_lines[1])
    assert y0[1] == y0[3] == pytest.approx(a.thrust_y(0.0))  # horizontal lines
    assert y30[1] == y30[3] == pytest.approx(a.thrust_y(30.0))
    assert a.thrust_y(30.0) < a.thrust_y(0.0)  # 30 N is drawn above 0 N
    a.close()


# --- Scenario: The plots show the last 20 s, scrolling ------------------------


def test_after_35_s_the_axis_shows_15_to_35_s_and_older_points_are_gone():
    s = session_after(35.0)
    assert s.sim.time == 35.0
    assert s.plot_x_range() == (15.0, 35.0)
    times = [p[0] for p in s.plot_points()]
    assert min(times) == 15.0 and max(times) == 35.0
    assert len(s.sim.records) == 7001  # every record since time 0 is still kept


# --- Scenario: Before 20 s the time axis shows 0 to 20 s ----------------------


@pytest.mark.parametrize("seconds", [0.0, 5.0, 20.0])
def test_before_20_s_the_axis_shows_0_to_20_s(seconds):
    s = session_after(seconds)
    assert s.plot_x_range() == (0.0, 20.0)


def test_just_after_20_s_the_axis_starts_scrolling():
    s = session_after(20.5)
    assert s.sim.time == 20.5
    assert s.plot_x_range() == (0.5, 20.5)


# --- Scenario: The plotted thrust is the capped thrust ------------------------


def test_plotted_thrust_is_capped_at_30_and_never_below_0():
    from kuava_sim import live

    s = live.LiveSession(0.0)
    for k in range(1, 161):  # 10 s, settled near 10 m
        s.tick(k * 0.0625)
    s.release_setpoint(100.0)
    s.tick(161 * 0.0625)
    assert s.sim.held_thrust > 30.0  # the controller really asked for more than 30 N
    for k in range(162, 241):
        s.tick(k * 0.0625)
    thrusts = [p[3] for p in s.plot_points()]
    assert max(thrusts) == 30.0
    assert min(thrusts) >= 0.0


# --- Scenario: The frame rate is shown ----------------------------------------


def test_session_measures_the_frame_rate_over_the_last_second():
    from kuava_sim import live

    s = live.LiveSession(0.0)
    for k in range(1, 65):  # 64 frames, 32 per second, for 2 s
        s.tick(k / 32)
    assert s.fps(2.0) == 32
    assert s.fps(2.5) == 16  # only frames in the last second count


def test_window_shows_the_measured_frame_rate(tk_root):
    clock = FakeClock(0.0)
    a = make_app(tk_root, clock)
    for k in range(1, 65):
        clock.now = k / 32
        a.frame()
    text = a.fps_label.cget("text")
    assert re.fullmatch(r"32 fps", text), text
    a.close()


# --- Scenario: The average frame rate over 5 s is above 30 fps ----------------


def test_live_app_averages_above_30_fps_over_5_seconds(tk_root):
    from kuava_sim import app

    a = app.App(tk_root)  # real clock
    stamps = []
    tick = a.session.tick

    def recording_tick(now):
        stamps.append(now)
        return tick(now)

    a.session.tick = recording_tick
    tk_root.after(5000, tk_root.quit)
    tk_root.mainloop()
    assert len(stamps) > 150
    failure = frame_rate_failure(stamps)
    assert failure is None, failure
    assert a.session.sim.step_count > 900  # it really simulated while drawing
    drawn = a.altitude_plot.coords(a.lines["altitude"])
    assert len(drawn) >= 2 * 250  # the plots were really redrawn during the run
    a.close()


# --- Scenario: One slow frame does not fail the frame-rate check --------------


def test_one_slow_frame_does_not_fail_the_check():
    stamps = [k / 60 for k in range(0, 151)]  # 60 fps for 2.5 s
    stamps += [stamps[-1] + 0.2 + k / 60 for k in range(0, 151)]  # one 200 ms frame
    assert max(b - a for a, b in zip(stamps, stamps[1:])) > 1 / 30
    assert frame_rate_failure(stamps) is None


# --- Scenario Outline: An average of 30 fps or less fails the check -----------


@pytest.mark.parametrize("fps", [30.0, 29.9])
def test_an_average_of_30_fps_or_less_fails_and_states_the_average(fps):
    stamps = [k / fps for k in range(0, 151)]  # 150 frame intervals
    failure = frame_rate_failure(stamps)
    assert failure is not None
    assert f"{fps:.1f} fps" in failure


def test_an_average_just_above_30_fps_passes():
    stamps = [k / 30.1 for k in range(0, 151)]
    assert frame_rate_failure(stamps) is None


# --- Scenario: The plots stop changing while paused ---------------------------


@pytest.mark.xfail(strict=True, reason="pause arrives with US-17 (IQ-9 practice)")
def test_plots_stop_changing_while_paused():
    from kuava_sim import live

    s = live.LiveSession(0.0)
    s.tick(1.0)
    s.pause()
    before = s.plot_points()
    s.tick(2.0)
    s.tick(3.0)
    assert s.plot_points() == before
