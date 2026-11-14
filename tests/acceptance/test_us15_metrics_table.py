"""US-15 Metrics after each setpoint change — acceptance tests.

Expected behaviour comes from docs/design/DESIGN_f351eee.md (US-15, OQ-39)
and docs/architecture/ARCHITECTURE_899eaea.md (last_step_metrics(), frozen
rows plus a live newest row refreshed at most every 0.5 s (D-21), display
rounding: time 2 dp, altitudes 1 dp, rise 2 dp, overshoot 1 dp, settling
2 dp, error 3 dp; NaN shown as "not reached").
"""

import math

import pytest

from gui_helpers import FakeClock
from kuava_sim import SimConfig, Simulation, StepMetrics

FRAME = 0.0625  # s per frame in the fake-clock runs (12.5 steps)


def same(a, b):
    """Field-by-field equality where NaN equals NaN."""
    return len(a) == len(b) and all(
        x == y or (isinstance(x, float) and math.isnan(x) and math.isnan(y))
        for x, y in zip(a, b)
    )


def run_frames(session, first, last):
    for k in range(first, last + 1):
        session.tick(k * FRAME)


def three_changes():
    from kuava_sim import live

    s = live.LiveSession(0.0)
    run_frames(s, 1, 32)  # 2 s
    s.release_setpoint(25.0)
    run_frames(s, 33, 64)  # 4 s
    s.release_setpoint(5.0)
    run_frames(s, 65, 96)  # 6 s
    return s


# --- core: last_step_metrics() ------------------------------------------------


def test_last_step_metrics_is_none_before_the_controller_was_ever_on():
    sim = Simulation(SimConfig(mass=1.0, max_thrust=30.0))
    sim.run(10, thrust=5.0)
    assert sim.last_step_metrics() is None


@pytest.mark.parametrize("steps_after", [0, 1, 2, 750, 3000])
def test_last_step_metrics_equals_the_newest_step_metrics_result(steps_after):
    sim = Simulation(SimConfig(mass=1.0, drag_coeff=0.5, max_thrust=30.0))
    sim.enable_controller(kp=4.0, ki=1.0, kd=3.0, setpoint=10.0)
    sim.run(1500)
    sim.set_setpoint(20.0)
    sim.run(1500)
    sim.set_setpoint(12.0)  # a downward step
    sim.run(steps_after)
    assert same(sim.last_step_metrics(), sim.step_metrics()[-1])


def test_last_step_metrics_follows_a_zero_size_change():
    sim = Simulation(SimConfig(mass=1.0, max_thrust=30.0, initial_altitude=10.0))
    sim.enable_controller(kp=4.0, ki=1.0, kd=3.0, setpoint=10.0)  # hover: final change 0
    sim.run(400)
    result = sim.last_step_metrics()
    assert same(result, sim.step_metrics()[-1])
    assert math.isnan(result.rise_time)


# --- Scenario: One row per setpoint change, newest on top ---------------------


def test_one_row_per_setpoint_change_newest_on_top():
    s = three_changes()
    rows = s.metrics_rows()
    assert [r.setpoint for r in rows] == [5.0, 25.0, 10.0]
    assert [r.change_index for r in rows] == [800, 400, 0]


def test_display_columns_and_rounding():
    from kuava_sim import live

    row = StepMetrics(400, 2.0, 9.87654, 25.0, 10, 1.23456, 12.345, 3.4567, 15.1, -0.01234)
    assert live.format_row(row) == ("2.00", "9.9 → 25.0", "1.23", "12.3", "3.46", "-0.012")


def test_window_table_has_the_six_columns_and_one_row_per_change(tk_root):
    from kuava_sim import app, live

    clock = FakeClock(0.0)
    a = app.App(tk_root, clock=clock)
    headings = [a.table.heading(c)["text"] for c in a.table["columns"]]
    assert headings == [
        "Time of change (s)", "From → to (m)", "Rise time (s)",
        "Overshoot (%)", "Settling time (s)", "Steady-state error (m)",
    ]
    for k in range(1, 33):
        clock.now = k * FRAME
        a.frame()
    a.session.release_setpoint(25.0)
    for k in range(33, 65):
        clock.now = k * FRAME
        a.frame()
    items = a.table.get_children()
    assert len(items) == 2
    columns = a.table["columns"]
    shown = [tuple(a.table.set(i, c) for c in columns) for i in items]  # the shown text
    expected = [live.format_row(r) for r in a.session.metrics_rows()]
    assert shown == expected
    a.close()


# --- Scenario: The newest row updates live ------------------------------------


def test_newest_row_is_recomputed_at_most_every_half_second():
    from kuava_sim import live

    s = live.LiveSession(0.0)
    run_frames(s, 1, 7)  # 0.4375 s: no refresh yet
    assert s.metrics_rows()[0].samples == 1
    run_frames(s, 8, 8)  # 0.5 s: refresh
    assert s.metrics_rows()[0].samples == 101
    run_frames(s, 9, 15)  # 0.9375 s: too soon for the next one
    assert s.metrics_rows()[0].samples == 101
    run_frames(s, 16, 16)  # 1.0 s
    assert s.metrics_rows()[0].samples == 201


def test_older_rows_keep_their_finished_values():
    s = three_changes()
    finished = s.sim.step_metrics()[:2]  # windows ended at the later changes
    run_frames(s, 97, 160)  # 4 s more
    rows = s.metrics_rows()
    assert same(rows[2], finished[0]) and same(rows[1], finished[1])


# --- Scenario: The shown metrics equal the simulation's metrics ---------------


def test_rows_equal_step_metrics_right_after_a_refresh():
    s = three_changes()  # the last frame (6 s) was a refresh moment
    expected = list(reversed(s.sim.step_metrics()))
    rows = s.metrics_rows()
    assert len(rows) == 3
    assert all(same(r, e) for r, e in zip(rows, expected))
    assert not math.isnan(rows[0].rise_time)  # a real, measured response


# --- Scenario: A metric that is not reached is shown as such ------------------


def test_nan_is_shown_as_not_reached():
    from kuava_sim import live

    row = StepMetrics(0, 0.0, 0.0, 10.0, 1, math.nan, math.nan, math.nan, 0.0, 10.0)
    shown = live.format_row(row)
    assert shown[2:5] == ("not reached", "not reached", "not reached")
    assert shown[5] == "10.000"


def test_a_fresh_change_shows_not_reached_never_nan_zero_or_blank():
    from kuava_sim import live

    s = live.LiveSession(0.0)
    run_frames(s, 1, 32)
    s.release_setpoint(25.0)
    newest = live.format_row(s.metrics_rows()[0])
    for text in newest[2:5]:
        assert text == "not reached"
        assert text not in ("nan", "0", "0.00", "")


# --- Scenario: Reset clears the metrics table ---------------------------------


@pytest.mark.xfail(strict=True, reason="reset arrives with US-17 (IQ-9 practice)")
def test_reset_leaves_only_the_new_start_row():
    s = three_changes()
    s.reset(10.0)
    rows = s.metrics_rows()
    assert len(rows) == 1
    assert (rows[0].change_index, rows[0].setpoint) == (0, 5.0)
