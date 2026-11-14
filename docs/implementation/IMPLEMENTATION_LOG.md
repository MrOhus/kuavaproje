# Implementation Log

Append one entry per implementation pass (one story per pass), **most recent first**. Never edit or delete a previous pass's entry — this file is a traceable history, not a living document.

---

## Pass: 2026-11-14 — Fix: gain sliders while the window is not drawn (US-13)

**Branch:** `bugfix/gain-slider-redraw` (from `main` at `3532cfb`)
**Traces to:** `docs/design/DESIGN_f351eee.md` (US-13 "A gain takes effect while its slider is dragged", OQ-36), `docs/architecture/ARCHITECTURE_899eaea.md` (App sliders; D-22 skip rule from AQ-21)
**Approval basis:** Requirement Analysis and Solution Architecture (Round 3) approved 14.11.2026. Fix and test change requested by the operator after the pre-submission check: "fix it the normal way, own branch, failing test first"; "Skip them with the reason shown, the same as AQ-21 when there's no screen."

**Found by:** the pre-submission check. A slider change made by code while the window was not drawn (withdrawn, minimized or a locked screen) was not applied. In a scratch copy with the test window hidden, 9 of the 106 Round 3 tests failed:
- 4 because of this bug;
- 5 because Tk does not deliver mouse and key events to a hidden window.

**Cause:** Tk runs a Scale's `command` only when it redraws the slider on screen. For a user dragging with the mouse, the window is visible, so the effect was mainly on tests run without a visible window.

**Files:**
- `src/kuava_sim/app.py`: the gain sliders now use a `tk.DoubleVar` with a write trace that calls `set_gain`.
- `tests/acceptance/test_us13_hidden_window.py` (new).
- `tests/acceptance/gui_helpers.py`: `require_visible`.
- The event-driven tests in `test_us13_sliders.py`, `test_us17_pause_reset.py` and `test_us18_error_messages.py` now call it.

**Red proof:** the new tests were committed in `362a81d` before any code. 6 failed: 4 showed the bug (the old gain stayed in use), and 2 failed because `require_visible` did not exist yet. 1 passed: the setpoint slider still waits for release. The approved skip change followed in `cc72708`. `git diff cc72708 9cb5cdb -- tests/` is empty.

**Result:**
- Visible window: 479 passed.
- Test window hidden (scratch copy only): 472 passed, 7 skipped with the reason shown, 0 failed.

### Acceptance Criteria Coverage

| Scenario | Status | Test(s) |
|---|---|---|
| A gain takes effect while its slider is dragged, also when the window is not drawn | ✅ Pass | `test_gain_slider_applies_while_the_window_is_not_drawn` (kp, ki, kd), `test_every_gain_change_while_hidden_is_applied_in_order` |
| The setpoint changes only when the slider is released (unchanged while hidden) | ✅ Pass | `test_setpoint_slider_still_waits_for_release_while_hidden` |
| Window tests needing mouse or key events skip with the reason when the window is not visible | ✅ Pass | `test_event_tests_skip_with_the_reason_when_the_window_is_not_visible`, `test_event_tests_run_when_the_window_is_visible` |

### Predicates / Invariants Matched

| Entity/Predicate | Invariant / Boundary / Concurrency Rule | Verified By |
|---|---|---|
| App sliders | The shown gain value is the value in use, from the next step, whether or not the window is drawn | Hidden-window tests; all US-13 tests on a visible window |
| D-17 | Still one thread: the variable trace runs in the Tk thread | No threads added |
| D-22 / AQ-21 | A test that cannot run on this machine skips and prints the reason | Hidden scratch run: 7 skips, each with its reason |

### Open Questions Raised This Pass

None.

### Deviations From Approved DESIGN/ARCHITECTURE

- **Test change after sign-off (operator-approved).** Six existing window tests now call `require_visible()`:
  - US-13: setpoint range, setpoint release (mouse and key), release at the current setpoint;
  - US-17: sliders while paused;
  - US-18: rejected request.

  Their assertions are unchanged, and on a visible window they run as before. The operator approved this for the 5 tests named in the check. The sixth, the release at the current setpoint, was added because, while hidden, it passed without checking anything: the release it expects to "change nothing" never arrived.

### Coding Details Decided (rule 3)

- The Tk variables are kept in `App._gain_vars` so they are not garbage-collected.
- The skip reason is "window not visible on screen: Tk does not deliver mouse and key events to it".

### Version Control Actions

- Branch: `bugfix/gain-slider-redraw` (from `main` at `3532cfb`)
- Commits:
  - `2ae838b` docs(approval): History move of the Round 3 implementation entry, with all index rows marked Merged;
  - `362a81d` test (red);
  - `cc72708` test (operator-approved skip change);
  - `9cb5cdb` fix(app).
- docs(implementation): this entry and the signed approval entry, after the operator signs
- PR: opened against `main` and merged with a merge commit, after the operator signs

---

## Pass: 2026-11-14 — US-19 README and one-command start and test

**Branch:** `feature/us19-readme-commands` (stacked on `feature/us18-error-messages`; IQ-10 practice)
**Traces to:** `docs/design/DESIGN_f351eee.md` (US-19, OQ-41; metric definitions from `DESIGN_0bfd04e.md` OQ-30), `docs/architecture/ARCHITECTURE_899eaea.md` (D-22, GUI tests)
**Approval basis:** Requirement Analysis (Round 3) approved 14.11.2026; Solution Architecture (Round 3) approved 14.11.2026 (see `docs/APPROVAL_LOG.md`)
**Mode:** standing rules: all stories of the round end to end; small coding details decided by the developer and listed below (rule 3).

**Files:** `README.md`, `pyproject.toml` (`addopts = "-rs"`), `tests/acceptance/test_us19_readme_and_commands.py`.

**Red proof:** the tests were committed in `0815273` before the README and config changed. 4 failed (the README was a title only; skip reasons were not printed). 3 checks of the existing setup already held and must keep holding: the dev extra has pytest and control, one command collects every story's tests, and a broken test exits non-zero. `git diff 0815273 70cd2f4 -- tests/` is empty.

**Result:** 472 passed, 0 xfailed (full suite). The editable install was checked in a fresh venv.

### Acceptance Criteria Coverage

| Scenario | Status | Test(s) |
|---|---|---|
| The README covers setup, start, tests and the metrics | ✅ Pass | `test_readme_states_the_python_version_and_the_three_commands`, `test_readme_defines_the_four_metrics_as_round_2_does`, `test_readme_names_what_the_app_shows_and_its_controls`, `test_setup_command_installs_the_test_tools` |
| One command runs every test | ✅ Pass | `test_one_command_collects_the_tests_of_every_story` (US-1 … US-19, including GUI and python-control), `test_skipped_tests_print_their_reason` |
| The test command reports a failing test | ✅ Pass | `test_a_broken_test_is_reported_with_a_non_zero_exit_code` |

### Predicates / Invariants Matched

| Entity/Predicate | Invariant / Boundary / Concurrency Rule | Verified By |
|---|---|---|
| D-22 | Skipped window tests print their reason in the pytest summary | `-rs` in `pyproject.toml`; `test_skipped_tests_print_their_reason` |
| D-1 / D-16 | No runtime dependencies | `test_setup_command_installs_the_test_tools` asserts `dependencies == []` |

### Open Questions Raised This Pass

None.

### Deviations From Approved DESIGN/ARCHITECTURE

None.

### Coding Details Decided (rule 3)

- The README also has a short "Using the simulation from code" example and links to the project documents.
- The test-command checks run the project's pytest configuration on a throw-away test file in `tmp_path`.

### Version Control Actions

- Branch: `feature/us19-readme-commands` (from `feature/us18-error-messages` at `a86e63d`)
- Commits: `0815273` test (red), `70cd2f4` docs(readme), `1685e40` docs(readme): run setup first and activate `.venv` per terminal (operator request after sign-off: `python -m kuava_sim` failed with "No module named kuava_sim" until the setup ran; the US-19 tests still pass)
- docs(implementation): log the Round 3 implementation passes (all eight entries and the signed shared approval entry), after the operator signs
- PR: opened against `main` and merged with a merge commit, in story order (US-12 first), after the operator signs

---

## Pass: 2026-11-14 — US-18 Clear error messages instead of crashes

**Branch:** `feature/us18-error-messages` (stacked on `feature/us17-pause-reset`)
**Traces to:** `docs/design/DESIGN_f351eee.md` (US-18, OQ-41), `docs/architecture/ARCHITECTURE_899eaea.md` (D-23; LiveSession `fail`, `message`; App error routing)
**Approval basis:** as for US-19. **Mode:** as for US-19.

**Files:** `src/kuava_sim/live.py`, `src/kuava_sim/app.py`, `tests/acceptance/test_us18_error_messages.py`.

**Red proof:** the tests were committed in `c07a581` before any code. 12 failed: no `fail`, `message` or error label yet. `git diff c07a581 a86e63d -- tests/` is empty.

**Result:** 465 passed.

### Acceptance Criteria Coverage

| Scenario | Status | Test(s) |
|---|---|---|
| An unexpected error is reported, not a crash | ✅ Pass | `test_an_error_during_a_frame_is_shown_in_red_and_pauses`, `test_an_error_in_a_button_callback_is_shown_and_pauses`, `test_fail_pauses_and_sets_a_plain_message` (5 kinds), `test_a_repeated_error_does_not_pile_up` |
| A rejected simulation request is shown with its message | ✅ Pass | `test_a_rejected_request_shows_the_simulation_message` (real slider release with the controller off) |
| The user can continue after an error | ✅ Pass | `test_reset_after_an_error_restarts_from_time_0_and_clears_the_message`, `test_resume_after_an_error_clears_the_message` |

### Predicates / Invariants Matched

| Entity/Predicate | Invariant / Boundary / Concurrency Rule | Verified By |
|---|---|---|
| D-23 | Errors in the frame loop and in Tk callbacks go to `fail`: the simulation pauses and the window stays open | Frame and button-callback tests |
| D-23 | The message is plain: `str(exc)` for ValueError/TypeError/RuntimeError, otherwise "Unexpected error: …" or "Unexpected error (<type>)"; it is shown in red | Parametrized `fail` test; label text and colour asserted |
| D-23 | Nothing is printed anywhere and there are no pop-ups | `capfd` is empty in every window test |

### Open Questions Raised This Pass

None.

### Deviations From Approved DESIGN/ARCHITECTURE

None.

### Coding Details Decided (rule 3)

- A ValueError, TypeError or RuntimeError with an empty message is shown as "Unexpected error (<type>)", like other errors without a message.
- One `_draw_status()` updates the Pause/Resume text, the gust button state and the error label. It runs on every frame and right after a click or an error.

### Version Control Actions

- Branch: `feature/us18-error-messages` (from `feature/us17-pause-reset` at `15a3e33`)
- Commits: `c07a581` test (red), `a86e63d` feat(app)
- PR: as for US-19

---

## Pass: 2026-11-14 — US-17 Pause and reset

**Branch:** `feature/us17-pause-reset` (stacked on `feature/us16-wind-gust`)
**Traces to:** `docs/design/DESIGN_f351eee.md` (US-17, OQ-37), `docs/architecture/ARCHITECTURE_899eaea.md` (D-18; LiveSession `pause`, `resume`, `toggle_pause`, `reset`; real-time pacing re-anchor)
**Approval basis:** as for US-19. **Mode:** as for US-19.

**Files:** `src/kuava_sim/live.py`, `src/kuava_sim/app.py`, `tests/acceptance/test_us17_pause_reset.py`. The red commit also removes the last three strict xfail markers (US-14 paused plots, US-15 reset table, US-16 paused gust).

**Red proof:** the tests and marker removals were committed in `49b5a67` before any code. 12 failed: no pause, reset or buttons yet. `git diff 49b5a67 15a3e33 -- tests/` is empty.

**Result:** 453 passed, 0 xfailed.

### Acceptance Criteria Coverage

| Scenario | Status | Test(s) |
|---|---|---|
| Pause and resume | ✅ Pass | `test_paused_session_takes_no_steps`, `test_resume_continues_from_exactly_the_paused_state` (records identical to an unpaused run), `test_toggle_pause_switches_both_ways` |
| Sliders work while paused and apply on resume | ✅ Pass | `test_sliders_work_while_paused_and_apply_on_resume` (change at the paused step; next thrust from the formula), `test_window_pause_button_and_sliders_while_paused` |
| Reset returns to the start and keeps the slider values | ✅ Pass | `test_reset_returns_to_the_start_with_the_current_slider_values` (new simulation, integral 0, no gust left), `test_window_reset_button_clears_plots_and_table` |
| Reset keeps the pause state | ✅ Pass | `test_reset_keeps_the_pause_state[running]`, `[paused]` |

**Earlier scenarios now complete** (markers removed in `49b5a67`): US-14 "The plots stop changing while paused"; US-15 "Reset clears the metrics table"; US-16 "The gust button does nothing while paused".

### Predicates / Invariants Matched

| Entity/Predicate | Invariant / Boundary / Concurrency Rule | Verified By |
|---|---|---|
| Real-time pacing | Resume and reset re-anchor the clock, so no simulated time passes while paused | Resume test (250 steps both ways), reset test (100 steps in 0.5 s after the reset) |
| D-18 | Reset builds a new `Simulation` with the current slider values; the pause state is kept | `sim is not old_sim`; controller status; outline test |
| OQ-37 | The gust is ignored and its button disabled while paused | US-16 paused-gust test |

### Open Questions Raised This Pass

None.

### Deviations From Approved DESIGN/ARCHITECTURE

None.

### Coding Details Decided (rule 3)

- `tick` still records the frame time while paused, so the fps display keeps updating.

### Version Control Actions

- Branch: `feature/us17-pause-reset` (from `feature/us16-wind-gust` at `7fe36cf`)
- Commits: `49b5a67` test (red), `15a3e33` feat(app)
- PR: as for US-19

---

## Pass: 2026-11-14 — US-16 Wind gust disturbance

**Branch:** `feature/us16-wind-gust` (stacked on `feature/us15-metrics-table`)
**Traces to:** `docs/design/DESIGN_f351eee.md` (US-16, OQ-35), `docs/architecture/ARCHITECTURE_899eaea.md` (gust state, step-with-gust predicate, D-19, D-20)
**Approval basis:** as for US-19. **Mode:** as for US-19.

**Files:** `src/kuava_sim/simulation.py` (`GUST_FORCE`, `GUST_STEPS`, `gust()`, step with gust), `src/kuava_sim/__init__.py`, `src/kuava_sim/live.py` (`press_gust`), `src/kuava_sim/app.py` (Wind gust button), `tests/acceptance/test_us16_wind_gust.py`. The red commit also removes the US-12 replay xfail marker.

**Red proof:** the tests were committed in `1af3b69` before any code. 12 failed: no gust yet. Two invariant checks already passed and still pass: with no press every step is the Round 2 step, and records keep six fields. `git diff 1af3b69 7fe36cf -- tests/` is empty.

**Result:** 441 passed, 3 xfailed (waiting for US-17).

### Acceptance Criteria Coverage

| Scenario | Status | Test(s) |
|---|---|---|
| A gust is a 5 N downward force for 100 steps | ✅ Pass | `test_constants_are_5_newtons_for_100_steps`, `test_gust_acts_on_exactly_the_next_100_steps` (bit-exact acceleration from the record's own thrust and drag; step k+101 free), `test_gust_changes_the_records_from_the_next_step_only` |
| A press during a gust restarts it instead of adding to it | ✅ Pass | `test_a_second_press_restarts_the_100_steps_and_never_doubles_the_force` |
| The controller recovers after a gust | ✅ Pass | `test_controller_recovers_after_a_gust`, `test_controller_is_not_told_about_the_gust` |
| A gust on the ground does not push the drone below the ground | ✅ Pass | `test_gust_on_the_ground_keeps_the_drone_at_altitude_0` |
| Gusts are deterministic | ✅ Pass | `test_same_presses_at_the_same_steps_give_identical_records`, `test_run_n_after_a_gust_equals_n_single_steps` |
| Without a gust press there is no disturbance | ✅ Pass | `test_without_a_press_every_step_is_the_round_2_step`, `test_records_keep_their_six_fields` |
| The gust button does nothing while paused | ✅ Pass (after US-17) | `test_gust_button_is_disabled_and_ignored_while_paused` |
| Session and button | ✅ Pass | `test_session_press_gust_pushes_the_live_drone`, `test_gust_button_starts_a_gust` |

**Earlier scenario now complete** (marker removed in `1af3b69`): US-12 "The live simulation is the same deterministic simulation as without the GUI" (replay with slider changes and gusts, records bit-identical).

### Predicates / Invariants Matched

| Entity/Predicate | Invariant / Boundary / Concurrency Rule | Verified By |
|---|---|---|
| Step with gust | `a = (((t_used − m·g) + drag) − 5) / m` on steps k+1 … k+100; the Round 2 expression otherwise | Bit-exact acceleration checks |
| Gust state | A press restarts the count; the force is never 10 N | Restart test |
| D-20 | Six record fields; the acceleration includes the gust | Field test; acceleration checks |
| D-4 | The floor holds the drone at 0 during a gust | Ground test |

### Open Questions Raised This Pass

None.

### Deviations From Approved DESIGN/ARCHITECTURE

None.

### Coding Details Decided (rule 3)

- The button calls a private `_on_gust`, so it always reaches the current session.

### Version Control Actions

- Branch: `feature/us16-wind-gust` (from `feature/us15-metrics-table` at `20ab8d1`)
- Commits: `1af3b69` test (red), `7fe36cf` feat(sim)
- PR: as for US-19

---

## Pass: 2026-11-14 — US-15 Metrics after each setpoint change

**Branch:** `feature/us15-metrics-table` (stacked on `feature/us14-live-plots`)
**Traces to:** `docs/design/DESIGN_f351eee.md` (US-15, OQ-39), `docs/architecture/ARCHITECTURE_899eaea.md` (`last_step_metrics()`, LiveSession rows, D-21, display rounding)
**Approval basis:** as for US-19. **Mode:** as for US-19.

**Files:** `src/kuava_sim/simulation.py` (`last_step_metrics()`, shared `_metrics(j)`), `src/kuava_sim/live.py` (`format_row`, `metrics_rows`, refresh), `src/kuava_sim/app.py` (table), `tests/acceptance/test_us15_metrics_table.py`.

**Red proof:** the tests were committed in `414e5a0` before any code. 15 failed: no `last_step_metrics`, `metrics_rows`, `format_row` or table yet. `git diff 414e5a0 20ab8d1 -- tests/` is empty.

**Result:** 427 passed, 3 xfailed.

### Acceptance Criteria Coverage

| Scenario | Status | Test(s) |
|---|---|---|
| One row per setpoint change, newest on top | ✅ Pass | `test_one_row_per_setpoint_change_newest_on_top`, `test_display_columns_and_rounding`, `test_window_table_has_the_six_columns_and_one_row_per_change` |
| The newest row updates live | ✅ Pass | `test_newest_row_is_recomputed_at_most_every_half_second`, `test_older_rows_keep_their_finished_values` |
| The shown metrics equal the simulation's metrics | ✅ Pass | `test_rows_equal_step_metrics_right_after_a_refresh`, `test_last_step_metrics_equals_the_newest_step_metrics_result` (5 cases), `test_last_step_metrics_follows_a_zero_size_change`, `test_last_step_metrics_is_none_before_the_controller_was_ever_on` |
| A metric that is not reached is shown as such | ✅ Pass | `test_nan_is_shown_as_not_reached`, `test_a_fresh_change_shows_not_reached_never_nan_zero_or_blank` |
| Reset clears the metrics table | ✅ Pass (after US-17) | `test_reset_leaves_only_the_new_start_row` |

### Predicates / Invariants Matched

| Entity/Predicate | Invariant / Boundary / Concurrency Rule | Verified By |
|---|---|---|
| `last_step_metrics()` | Equals `step_metrics()[-1]` field by field (NaN = NaN); `None` before the controller was ever on | Core tests |
| D-21 | Finished rows are frozen at the next change; only the newest is recomputed, at most every 0.5 s | Refresh and frozen-row tests |
| Display | Rounding for display only; NaN shown as "not reached" | `format_row` tests |

### Open Questions Raised This Pass

None.

### Deviations From Approved DESIGN/ARCHITECTURE

None.

### Coding Details Decided (rule 3)

- `step_metrics()` and `last_step_metrics()` share `_metrics(j)`, which slices the altitudes straight from the record array instead of copying the whole column. The values are the same floats as before: all Round 2 metric tests still pass with exact equality.
- `release_setpoint` computes the finished row first, then applies the change, and keeps the row only if the setpoint really changed. A rejected value therefore leaves the rows untouched.
- The next refresh comes after `max(0.5 s, 20 × the last recompute time)`.
- The table is rebuilt only when its shown text changes.

### Version Control Actions

- Branch: `feature/us15-metrics-table` (from `feature/us14-live-plots` at `9414b2b`)
- Commits: `414e5a0` test (red), `20ab8d1` feat(app)
- PR: as for US-19

---

## Pass: 2026-11-14 — US-14 Live plots

**Branch:** `feature/us14-live-plots` (stacked on `feature/us13-sliders`)
**Traces to:** `docs/design/DESIGN_f351eee.md` (US-14, OQ-38, OQ-40), `docs/architecture/ARCHITECTURE_899eaea.md` (plot buffer, PLOT_WINDOW, PLOT_EVERY, thrust axis, D-16, D-22)
**Approval basis:** as for US-19. **Mode:** as for US-19.

**Files:** `src/kuava_sim/live.py` (plot buffer, x and y ranges, fps), `src/kuava_sim/app.py` (canvases, axes, fps label), `tests/acceptance/test_us14_live_plots.py`, `tests/acceptance/gui_check.py` (test-only frame-rate check). The red commit also removes the US-12 plotted-altitude xfail marker.

**Red proof:** the tests were committed in `9ae2413` before any code. 13 failed. Before that commit, the 5 s frame-rate test was made to also require that the plots were really redrawn, because it would otherwise have passed with no drawing at all. `git diff 9ae2413 9414b2b -- tests/` is empty.

**Result:** 412 passed, 2 xfailed. Measured on this machine: 53.8 fps on average over 10 s, slowest frame 31 ms.

### Acceptance Criteria Coverage

| Scenario | Status | Test(s) |
|---|---|---|
| The plots show setpoint, altitude and the thrust used | ✅ Pass | `test_plot_points_are_altitude_setpoint_and_thrust_used_every_4_steps`, `test_window_draws_altitude_setpoint_and_thrust_on_a_shared_time_axis`, `test_thrust_plot_marks_the_0_and_30_newton_limits` |
| The plots show the last 20 s, scrolling | ✅ Pass | `test_after_35_s_the_axis_shows_15_to_35_s_and_older_points_are_gone`, `test_just_after_20_s_the_axis_starts_scrolling` |
| Before 20 s the time axis shows 0 to 20 s | ✅ Pass | `test_before_20_s_the_axis_shows_0_to_20_s` (0, 5, 20 s) |
| The plotted thrust is the capped thrust | ✅ Pass | `test_plotted_thrust_is_capped_at_30_and_never_below_0` |
| The frame rate is shown | ✅ Pass | `test_session_measures_the_frame_rate_over_the_last_second`, `test_window_shows_the_measured_frame_rate` |
| The average frame rate over 5 s is above 30 fps | ✅ Pass | `test_live_app_averages_above_30_fps_over_5_seconds` (real window, real clock) |
| One slow frame does not fail the check | ✅ Pass | `test_one_slow_frame_does_not_fail_the_check` |
| An average of 30 fps or less fails | ✅ Pass | `test_an_average_of_30_fps_or_less_fails_and_states_the_average` (30, 29.9), `test_an_average_just_above_30_fps_passes` |
| The plots stop changing while paused | ✅ Pass (after US-17) | `test_plots_stop_changing_while_paused` |

**Earlier scenario now complete** (marker removed in `9ae2413`): US-12 "The plotted altitude rises toward 10 m".

### Predicates / Invariants Matched

| Entity/Predicate | Invariant / Boundary / Concurrency Rule | Verified By |
|---|---|---|
| Plot buffer | One point per 4 steps, holding the setpoint used for that step; only the last 20 s; all records kept | Plot-point and 35 s tests |
| Time axis | `[0, 20]` up to and including 20 s, then `[t − 20, t]` | Axis tests |
| Thrust axis | Fixed `[−1, 31]` N, with lines at 0 and 30 N | Limit-line test |
| OQ-40 | Average above 30 fps over 5 s; a single slow frame allowed | Real 5 s test and check tests |

### Open Questions Raised This Pass

None.

### Deviations From Approved DESIGN/ARCHITECTURE

None.

### Coding Details Decided (rule 3)

- The average frame rate is defined as frame intervals divided by elapsed time: `(n − 1) / (t_last − t_first)`.
- Canvas size is 900 × 220 px. Axis tick labels are redrawn each frame at round values; the thrust ticks are 0, 10, 20 and 30 N.
- When only one point exists, it is drawn twice so that the line item is valid.

### Version Control Actions

- Branch: `feature/us14-live-plots` (from `feature/us13-sliders` at `7d08521`)
- Commits: `9ae2413` test (red), `9414b2b` feat(app)
- PR: as for US-19

---

## Pass: 2026-11-14 — US-13 Tune the controller with sliders

**Branch:** `feature/us13-sliders` (stacked on `feature/us12-live-app`)
**Traces to:** `docs/design/DESIGN_f351eee.md` (US-13, OQ-36, OQ-33), `docs/architecture/ARCHITECTURE_899eaea.md` (SLIDERS, LiveSession `set_gain` / `release_setpoint`, App sliders)
**Approval basis:** as for US-19. **Mode:** as for US-19.

**Files:** `src/kuava_sim/live.py`, `src/kuava_sim/app.py`, `tests/acceptance/test_us13_sliders.py`.

**Red proof:** the tests were committed in `6d24095` before any code. 16 failed: no sliders, `set_gain` or `release_setpoint` yet. The tests then changed once, in `ef98da2` (see Deviations). `git diff ef98da2 7d08521 -- tests/` is empty.

**Result:** 395 passed, 2 xfailed.

### Acceptance Criteria Coverage

| Scenario | Status | Test(s) |
|---|---|---|
| Slider ranges, steps and start values | ✅ Pass | `test_slider_range_step_and_start_value` (4 sliders) |
| A slider cannot go outside its range | ✅ Pass | `test_slider_cannot_go_outside_its_range` (4 sliders, both ends) |
| A gain takes effect while its slider is dragged | ✅ Pass | `test_gain_takes_effect_while_dragging_and_adds_no_metrics_row`, `test_session_set_gain_applies_from_the_next_step` |
| The setpoint changes only when the slider is released | ✅ Pass | `test_setpoint_changes_only_when_the_slider_is_released[mouse]`, `[key]`, `test_session_release_setpoint_makes_one_setpoint_change` |
| Releasing at the current setpoint changes nothing | ✅ Pass | `test_releasing_at_the_current_setpoint_changes_nothing`, `test_session_release_at_the_current_setpoint_changes_nothing` |
| The GUI has no manual thrust | ✅ Pass | `test_the_window_has_no_thrust_control_and_the_controller_stays_on` |

### Predicates / Invariants Matched

| Entity/Predicate | Invariant / Boundary / Concurrency Rule | Verified By |
|---|---|---|
| SLIDERS | Ranges 0–50 / 0–20 / 0–20 / 0–100, resolution 0.1, starts 4 / 1 / 3 / 10 | Range test |
| LiveSession | The shown slider value is the value in use (`float` of the slider value) | `scale.get() == values == controller` |
| OQ-36 | Gains apply on every change; the setpoint only on `<ButtonRelease-1>` / `<KeyRelease>` | Drag and release tests; next thrust checked against the formula |

### Open Questions Raised This Pass

None.

### Deviations From Approved DESIGN/ARCHITECTURE

- **Two test setups fixed after the red commit (operator-approved).**
  - What they were:
    1. "Exactly one more step" advanced the fake clock by 0.005 s. After 1 s of frames, `1.0 + 0.005` is just below 1.005 s in floating point, so no step was due and the tests read the previous record. Affected: `test_gain_takes_effect_while_dragging_and_adds_no_metrics_row` and `test_setpoint_changes_only_when_the_slider_is_released[mouse]`.
    2. The key-release test sent `<KeyRelease>` to a slider without keyboard focus. Tk delivers key events only to the focused widget, so the event never arrived.
  - Why the red phase did not catch them: in red the sliders did not exist, so the tests failed earlier, at `a.sliders`.
  - Why the fix does not weaken the tests: only the setup changed. The clock now advances 1/128 s, which is exactly one step, and the slider is given focus before the key release. Every assertion is unchanged.
  - The tool blocked the first attempt to edit the tests. The operator then approved the fix, and it was committed alone as `ef98da2`.

### Coding Details Decided (rule 3)

- Slider labels show units: "Kp (N/m)", "Ki (N/(m·s))", "Kd (N·s/m)", "Setpoint (m)". The Tk value display (`showvalue`) shows the current value.

### Version Control Actions

- Branch: `feature/us13-sliders` (from `feature/us12-live-app` at `a01cdbf`)
- Commits: `6d24095` test (red), `ef98da2` test-fix (operator-approved), `7d08521` feat(app)
- PR: as for US-19

---

## Pass: 2026-11-14 — US-12 Start the app and watch the drone fly under PID control

**Branch:** `feature/us12-live-app` (from `main` at `6069d65`; first of eight stacked branches)
**Traces to:** `docs/design/DESIGN_f351eee.md` (US-12, OQ-34, OQ-36, OQ-41), `docs/architecture/ARCHITECTURE_899eaea.md` (LiveSession, real-time pacing predicate, App, Startup; D-16, D-17, D-18, D-22)
**Approval basis:** as for US-19. **Mode:** as for US-19.

**Files:**
- New: `src/kuava_sim/live.py`, `src/kuava_sim/app.py`, `src/kuava_sim/__main__.py`.
- Tests and test helpers: `tests/acceptance/test_us12_live_app.py`, `tests/acceptance/conftest.py` (the `tk_root` fixture skips with the reason when there is no display), `tests/acceptance/gui_helpers.py` (`FakeClock`, `pump`, `record_bytes`).

**Red proof:** the tests were committed in `844f48f` before any code. 13 failed: `kuava_sim.live`, `kuava_sim.app` and `kuava_sim.__main__` did not exist. 2 scenarios were strict xfail, waiting for US-14 and US-16 (IQ-9 practice). `git diff 844f48f a01cdbf -- tests/` is empty.

**Result:** 379 passed, 2 xfailed.

### Acceptance Criteria Coverage

| Scenario | Status | Test(s) |
|---|---|---|
| The app starts with one command and the drone takes off under control | ✅ Pass | `test_start_command_opens_the_app_and_keeps_running` (real `python -m kuava_sim`, alive after 3 s, empty stderr), `test_app_starts_with_the_fixed_drone_on_the_ground_and_the_controller_on`, `test_altitude_rises_toward_the_setpoint_frame_by_frame`, `test_plotted_altitude_rises_toward_the_setpoint` (after US-14) |
| The app runs in real time | ✅ Pass | `test_simulated_time_follows_the_wall_clock_in_whole_steps`, `test_no_steps_are_taken_when_no_time_has_passed` |
| The app slows down instead of jumping ahead | ✅ Pass | `test_exactly_a_quarter_second_due_is_taken_in_full` (50), `test_more_than_a_quarter_second_due_takes_50_and_drops_the_rest` (51), `test_a_long_stall_never_causes_a_burst_of_catch_up_steps` |
| The live simulation is the same deterministic simulation as without the GUI | ✅ Pass (after US-16) | `test_live_run_replays_bit_identically_without_the_gui` |
| The app cannot start | ✅ Pass | `test_missing_tkinter_prints_one_plain_line_and_exits_with_1`, `test_no_display_prints_one_plain_line_and_exits_with_1`, `test_any_other_startup_error_prints_one_plain_line_and_exits_with_1`, `test_the_real_start_command_without_tkinter_exits_with_1_and_no_traceback`, `test_closing_the_window_normally_exits_with_0` |

### Predicates / Invariants Matched

| Entity/Predicate | Invariant / Boundary / Concurrency Rule | Verified By |
|---|---|---|
| Real-time pacing | `due = int((now − anchor)·200) − steps since anchor`; never ahead of the wall clock; 50 steps at the limit, 51 → 50 and re-anchor | Pacing tests with a fake clock |
| APP_CONFIG / SLIDERS | 1 kg, 9.81, drag 0.5, 30 N, from the ground at rest; controller on with 4 / 1 / 3 / 10 m | Start-state test |
| Startup | One plain line on stderr, exit 1, no traceback; normal close exits 0 | Startup tests, including the real command in a subprocess |
| D-17 | Everything in the Tk thread | `App` uses `root.after` only; no threads |

### Open Questions Raised This Pass

None.

### Deviations From Approved DESIGN/ARCHITECTURE

None.

### Coding Details Decided (rule 3)

- `__main__` waits with `root.wait_window(root)` instead of `root.mainloop()`. It is the same Tk event loop, but it returns when this window is closed. `mainloop()` keeps running while any other Tk root in the process is open, which made the "normal close exits 0" test hang next to the test fixture's root.
- `App` takes an optional `clock` and has a public `frame()` (one frame without rescheduling), so tests can drive it with a fake clock.
- The window title is "Drone altitude — live PID simulation".

### Version Control Actions

- Branch: `feature/us12-live-app` (from `main` at `6069d65`)
- Commits: `631ae7d` docs(approval) History move of the Round 3 architecture entry, `844f48f` test (red), `a01cdbf` feat(app)
- PR: as for US-19

---

## Pass: 2026-11-14 — US-11 Metrics agree with python-control

**Branch:** `feature/us11-python-control-match` (stacked on `feature/us10-step-metrics`, IQ-10)
**Traces to:** `docs/design/DESIGN_0bfd04e.md` (US-11, OQ-26 c, OQ-30), `docs/architecture/ARCHITECTURE_3dbd8e9.md` (D-9 equal results on the same signal, D-11, D-12 the 2 % rule, D-13 continuous closed-loop model; AQ-8, AQ-10, AQ-11, AQ-12)
**Approval basis:** Requirement Analysis (Round 2) approved 14.11.2026; Solution Architecture (Round 2) approved 14.11.2026 (see `docs/APPROVAL_LOG.md`)
**Mode:** done while the operator was away under the standing rules. Real decisions used the recommended option, marked awaiting operator confirmation; all were later confirmed (IQ-9 to IQ-11 "a").

**Files:** `tests/acceptance/test_us11_python_control.py`, `tests/acceptance/pc_compare.py` (test-only helper: the D-12 rule and the python-control references). No production code changed.
**Red proof:** no red phase was possible: the metrics from US-10 already satisfy US-11 (IQ-11). The tests were committed in `70450f0` before any production code. `git diff --stat 7b1acb5 HEAD -- src/` is empty. Five faults were planted in scratch copies (not committed), and the US-11 tests caught all five:

| Planted fault | Caught by (failing tests) |
|---|---|
| Rise time measured from 15 % instead of 10 % | 9 |
| Settling band 3 % instead of 2 % | 9 |
| Overshoot 5 % too large | 9 |
| Steady-state value from the second-to-last sample | 4 |
| Controller drops the D term | 3 (model comparison) |

**Result:** 366 passed, 0 xfailed (full suite). Python 3.15.2, pytest 9.2.0, python-control 0.10.2.

### Acceptance Criteria Coverage

| Scenario | Status | Test(s) |
|---|---|---|
| Metrics match step_info on the same signal | ✅ Pass | `test_metrics_match_step_info_on_the_same_signal` (up, down, lightly damped, saturated; values equal, not only within 2 %), `test_every_result_of_a_longer_run_matches_step_info` (5 results) |
| Metrics match a python-control closed-loop model where the model applies | ✅ Pass | `test_metrics_match_the_closed_loop_model_where_it_applies` (3 cases; thrust strictly inside (0, 30) N, no ground contact, rise time ≥ 0.25 s asserted) |
| The model comparison is not claimed where the model does not apply | ✅ Pass | `test_model_comparison_is_not_claimed_when_the_thrust_hits_a_limit`, `test_model_comparison_is_not_claimed_when_the_drone_touches_the_ground` |
| A difference larger than 2 % fails the check | ✅ Pass | `test_the_two_percent_rule_at_its_limit` (+2 %, +2 % + one double, −2 %, −2 % − one double, equal), `test_a_zero_reference_allows_0_02_in_the_metric_unit`, `test_nan_matches_only_nan`, `test_a_failed_check_names_every_metric_that_differs` |

### Predicates / Invariants Matched

| Entity/Predicate | Invariant / Boundary / Concurrency Rule | Verified By |
|---|---|---|
| D-9 | The metrics use `step_info`'s operations, so they equal its output on the same signal | Same-signal tests compare with `==` |
| D-12 | 2 % relative; reference 0 allows ±0.02 in the metric's unit; both NaN match; one NaN mismatches | Rule tests at the limit and one double beyond |
| D-13 | Continuous model `(Kp s + Ki)/(m s³ + (b+Kd) s² + Kp s + Ki)` on the same time points | Model tests; worst difference in the prototype 0.6 %, tests allow 2 % |

### Open Questions Raised This Pass

| ID | Question | Status | Resolution |
|---|---|---|---|
| IQ-11 | US-11 is already satisfied by the US-10 code, so its tests cannot fail first and there is no code to write. (a) **Recommended:** commit the tests, prove they can fail with planted faults, no code commit (as IQ-4); (b) commit the tests without that proof; (c) fold US-11 into the US-10 pass. | Resolved | "IQ-11 a" (confirmed by the operator after the pass) |

### Deviations From Approved DESIGN/ARCHITECTURE

- No red phase and no production code for US-11. Caused by IQ-11 (option a, confirmed by the operator).
- The python-control comparison is only made for tunings with rise time ≥ 0.25 s, as ARCHITECTURE D-13 notes (one 5 ms sample is then at most 2 %). The US-11 example (rise time 1.07 s) is well inside.

### Version Control Actions

- Branch: `feature/us11-python-control-match` (from `feature/us10-step-metrics` at `7b1acb5`)
- Commits: `70450f0` test(metrics): add US-11 python-control comparison acceptance tests (no code commit needed)
- docs(implementation): log the Round 2 implementation passes (all five entries, the signed shared approval entry and LEARNING.md)
- PR: opened against `main` and merged with a merge commit, in story order (US-7 first), after the operator signed

---

## Pass: 2026-11-14 — US-10 Step-response metrics after every setpoint change

**Branch:** `feature/us10-step-metrics` (stacked on `feature/us9-closed-loop-thrust`, IQ-10)
**Traces to:** `docs/design/DESIGN_0bfd04e.md` (US-10, OQ-29, OQ-30), `docs/architecture/ARCHITECTURE_3dbd8e9.md` (Entity: StepMetrics, constants; D-9, D-11; AQ-8, AQ-10)
**Approval basis:** as for US-11.
**Mode:** as for US-11.

**Files:** `src/kuava_sim/simulation.py` (`StepMetrics`, `_step_info`, `step_metrics()`, `RISE_LIMITS`, `SETTLING_BAND`), `src/kuava_sim/__init__.py`, `tests/acceptance/test_us10_step_metrics.py`; the last two xfail markers (US-10) removed from the US-7, US-8 and US-9 tests, and the "strict xfail" notes in the US-7 and US-8 docstrings reworded to past tense (comment-only, in the red commit).
**Red proof:** the tests and marker removals were committed in `1c90dce` before any production code (21 failed in the full suite, 14 new US-10 tests, all "no attribute 'step_metrics'"). The tests then changed once, in `5c5ded1` (see Deviations). `git diff --stat 5c5ded1 7b1acb5 -- tests/` is empty.
**Result:** 345 passed, 0 xfailed.

### Acceptance Criteria Coverage

| Scenario | Status | Test(s) |
|---|---|---|
| Each setpoint change gets its own metrics | ✅ Pass | `test_each_setpoint_change_gets_its_own_result_in_order`, `test_no_results_before_the_controller_is_ever_turned_on` |
| A result covers the samples from its change to the next change | ✅ Pass | `test_a_result_covers_its_change_up_to_the_next_change` (records 0–100, 100–900, 900–1500) |
| The latest result can be read at any time and is recomputed | ✅ Pass | `test_the_latest_result_is_recomputed_from_the_records_so_far`, `test_reading_the_metrics_changes_nothing` |
| Metrics follow step_info's definitions on the relative altitude | ✅ Pass | `test_metrics_of_an_upward_step_follow_the_definitions` (each metric re-derived by scanning the recorded altitude) |
| A downward step uses the same rules | ✅ Pass | `test_metrics_of_a_downward_step_follow_the_same_definitions` |
| A metric that is never reached is reported as NaN | ✅ Pass | `test_a_zero_size_step_gives_nan_metrics`, `test_a_single_sample_window_gives_nan_metrics`, `test_a_change_with_a_tiny_but_non_zero_final_change_is_measured` (D-11) |
| Metrics are reported in fixed units | ✅ Pass | `test_metrics_fields_and_types` |
| Rejected setpoint changes create no metrics | ✅ Pass | `test_rejected_setpoint_change_creates_no_metrics` (negative, NaN, str) after the fix below |

**Earlier scenarios now complete** (markers removed in `1c90dce`): US-7 "Turning on counts as the first setpoint change"; US-8 "The setpoint can be changed" (new result at that record), "A gain change does not start a new result", "Setting the same setpoint again does nothing" (no new result); US-9 "Closed-loop runs are deterministic" (identical metrics).

### Predicates / Invariants Matched

| Entity/Predicate | Invariant / Boundary / Concurrency Rule | Verified By |
|---|---|---|
| `StepMetrics` | One result per entry in `_changes`, in order; window records `k … next change`, last window to the latest record; times are `(i − k)/200` | Window and order tests |
| `StepMetrics` | `steady_state_error == setpoint − final altitude`; `steady_state_value == final − start altitude` | `check_definitions` in the definition tests |
| D-11 | A window of 1 record or a final change of exactly 0 gives NaN rise, overshoot and settling time; steady-state values still reported | Degenerate-window tests |
| Reading | `step_metrics()` recomputes from the live records and changes nothing | Recompute and no-side-effect tests |

### Open Questions Raised This Pass

None new (IQ-9 and IQ-10 apply; see the US-7 pass).

### Deviations From Approved DESIGN/ARCHITECTURE

- **Test typo fixed after the red commit (operator-approved).** What it was: `test_rejected_setpoint_change_creates_no_metrics` built its comparison with `struct.pack("<9d", *r[1:4], *r[5:])`, which packs 3 + 5 = 8 values, so the format `"<9d"` was wrong (it should be `"<8d"`) and the test raised `struct.error` before comparing anything. Why the red phase did not catch it: in the red phase `step_metrics()` did not exist yet, so the test failed earlier, with `AttributeError: 'Simulation' object has no attribute 'step_metrics'`, before reaching the `struct.pack` line. It only showed in the green run (3 failures, one per parametrized case), so no production code was involved. Why the fix does not weaken the test: only the format string changed (`"<9d"` to `"<8d"` in two places); the same 8 fields of every result are still compared byte for byte, before and after the rejected change, and the count of results is still asserted to be 2. Checked in a scratch copy first (345 passed) and committed alone as `5c5ded1`, labelled test-fix, with the operator's approval. Note for honesty: this comparison covers 8 of the 10 fields; `change_index` and `samples` are not in it, both before and after the fix. The tuple equality in `test_reading_the_metrics_changes_nothing` covers all fields.

### Version Control Actions

- Branch: `feature/us10-step-metrics` (from `feature/us9-closed-loop-thrust` at `f6e77b2`)
- Commits:
  - `1c90dce` test(metrics): add failing US-10 step-response metrics acceptance tests (red, before code)
  - `5c5ded1` test(metrics): fix struct format in US-10 rejected-change test (test-fix, operator-approved)
  - `7b1acb5` feat(metrics): add step-response metrics after every setpoint change
- PR: opened against `main` and merged with a merge commit, in story order (US-7 first), after the operator signed

---

## Pass: 2026-11-14 — US-9 Closed-loop thrust every step

**Branch:** `feature/us9-closed-loop-thrust` (stacked on `feature/us8-change-gains-setpoint`, IQ-10)
**Traces to:** `docs/design/DESIGN_0bfd04e.md` (US-9, OQ-27, OQ-28), `docs/architecture/ARCHITECTURE_3dbd8e9.md` (Predicate: Controlled step; D-10; AQ-9)
**Approval basis:** as for US-11.
**Mode:** as for US-11.

**Files:** `src/kuava_sim/simulation.py` (`_control()`, used by `step()` and `run()`), `tests/acceptance/test_us9_closed_loop.py`; the five US-9 xfail markers removed from the US-7 and US-8 tests.
**Red proof:** the tests and marker removals were committed in `22f29ed` before any production code (16 failed, 0 of the new US-9 tests passing; one test that first passed against the uncontrolled code, `test_run_n_under_control_equals_n_single_steps`, was strengthened before the red commit to also require that the drone climbs). `git diff --stat 22f29ed f6e77b2 -- tests/` is empty.
**Result:** 324 passed, 7 xfailed (strict: the 7 waiting for US-10).

### Acceptance Criteria Coverage

| Scenario | Status | Test(s) |
|---|---|---|
| Thrust follows the controller formula | ✅ Pass | `test_thrust_follows_the_controller_formula` (16.31 N), `test_integral_is_updated_with_the_current_error_before_it_is_used` (9.83 N), `test_every_step_follows_the_formula_from_the_exact_state_at_its_start` (600 steps) |
| Holding at the setpoint uses exactly the hover thrust | ✅ Pass | `test_holding_at_the_setpoint_uses_the_hover_thrust` (every step within ε), `test_holding_at_the_setpoint_is_bit_exact` |
| A setpoint change gives no derivative spike | ✅ Pass | `test_a_setpoint_change_gives_no_derivative_spike` (thrust used exactly m·g) |
| The controller's thrust is capped silently at the maximum | ✅ Pass | `test_controller_thrust_is_capped_silently_at_the_maximum` (no warnings; held command above the limit) |
| The controller cannot ask for negative thrust | ✅ Pass | `test_controller_cannot_ask_for_negative_thrust` |
| No anti-windup in Round 2 | ✅ Pass | `test_no_anti_windup_the_integral_keeps_growing_at_the_limit` (400 capped steps; integral equals the running sum) |
| Closed-loop runs are deterministic | ⚠️ Partial, then ✅ | Records: `test_closed_loop_runs_give_identical_records`, `test_run_n_under_control_equals_n_single_steps`; metrics test completed in US-10 |
| The controller sees the exact simulated altitude | ✅ Pass | `test_every_step_follows_the_formula_from_the_exact_state_at_its_start` |

**Earlier scenarios now complete:** US-7 "Taking off from the ground under control" and "Turning the controller off returns Round 1 behaviour" (held thrust); US-8 "Gains can be changed" (new gain used next step), "The setpoint can be changed" (works toward the new setpoint), "Changing Ki affects only the future".

### Predicates / Invariants Matched

| Entity/Predicate | Invariant / Boundary / Concurrency Rule | Verified By |
|---|---|---|
| Controlled step (D-10) | `e = setpoint − h`; `I = I + (Ki·e)·dt`; `cmd = ((m·g + Kp·e) + I) − Kd·v`; then the unchanged Round 1 step caps it | Formula tests, bit-exact hover |
| No anti-windup | `I` is never clamped or reset while on | Capped-run test |
| Determinism | Same settings and change sequence give identical records | Two 10000-step runs with gain and setpoint changes compared byte for byte; the run really varies the thrust (over 1000 distinct values) |
| `run(n)` | Under control equals `n` single steps | `test_run_n_under_control_equals_n_single_steps` |

### Open Questions Raised This Pass

None new (IQ-9 and IQ-10 apply; see the US-7 pass).

### Deviations From Approved DESIGN/ARCHITECTURE

- The metrics part of "Closed-loop runs are deterministic" was a strict xfail until US-10 (IQ-9, confirmed by the operator).

### Version Control Actions

- Branch: `feature/us9-closed-loop-thrust` (from `feature/us8-change-gains-setpoint` at `514a97a`)
- Commits:
  - `22f29ed` test(controller): add failing US-9 closed-loop thrust acceptance tests (red, before code; removes 5 xfail markers)
  - `f6e77b2` feat(controller): add the closed-loop PID thrust step
- PR: opened against `main` and merged with a merge commit, in story order (US-7 first), after the operator signed

---

## Pass: 2026-11-14 — US-8 Change the gains and the setpoint while the simulation runs

**Branch:** `feature/us8-change-gains-setpoint` (stacked on `feature/us7-pid-controller-on`, IQ-10)
**Traces to:** `docs/design/DESIGN_0bfd04e.md` (US-8, OQ-28, OQ-33), `docs/architecture/ARCHITECTURE_3dbd8e9.md` (Entity: Controller state; D-8, D-14; AQ-7, AQ-13)
**Approval basis:** as for US-11.
**Mode:** as for US-11.

**Files:** `src/kuava_sim/simulation.py` (`set_gains`, `set_setpoint`), `tests/acceptance/test_us8_change_settings.py`.
**Red proof:** the tests were committed in `23dacb6` before any production code (20 failed, 0 passed, 8 strict xfail; all failures "no attribute 'set_gains'" or "'set_setpoint'"). `git diff --stat 23dacb6 514a97a -- tests/` is empty.
**Result:** 308 passed, 11 xfailed (strict: 3 from US-7, 8 from this story, waiting for US-9 and US-10).

### Acceptance Criteria Coverage

| Scenario | Status | Test(s) |
|---|---|---|
| Gains can be changed between steps | ⚠️ Partial, then ✅ | `test_gains_can_be_changed_and_are_reported_back`, `test_gain_change_leaves_earlier_records_unchanged`; `test_new_gain_is_used_from_the_next_step` completed in US-9 |
| The setpoint can be changed between steps | ⚠️ Partial, then ✅ | `test_setpoint_can_be_changed_and_is_reported_back`; the "works toward the new setpoint" and "new result at that record" tests completed in US-9 and US-10 |
| Changing Ki affects only the future | ⚠️ Partial, then ✅ | `test_changing_ki_keeps_the_integral_and_stops_its_growth`, completed in US-9 |
| A gain change does not start a new metrics result | ⚠️ Partial, then ✅ | `test_a_gain_change_does_not_start_a_new_metrics_result` (kp, ki, kd), completed in US-10 |
| Setting the same setpoint again does nothing | ✅ Pass | `test_setting_the_same_setpoint_again_changes_nothing`; the no-new-result part completed in US-10 |
| An invalid change is rejected and nothing changes | ✅ Pass | `test_invalid_gain_change_is_rejected_and_nothing_changes` (NaN, −0.5, +Inf, next double below 0, bool, str), `test_partly_invalid_gain_change_applies_nothing`, `test_invalid_setpoint_change_is_rejected_and_nothing_changes`, `test_setpoint_zero_is_accepted`, `test_set_gains_without_any_gain_is_rejected` |
| Changes take effect from the next step | ✅ Pass | Covered by `test_new_gain_is_used_from_the_next_step` (US-9 pass) and the settings-read-once design |
| Settings cannot be changed while the controller is off (D-14) | ✅ Pass | `test_settings_cannot_be_changed_while_the_controller_is_off` |

### Predicates / Invariants Matched

| Entity/Predicate | Invariant / Boundary / Concurrency Rule | Verified By |
|---|---|---|
| `set_gains`, `set_setpoint` | All given values are checked before anything changes; errors name the setting; apply from the next step | Rejection and partly-invalid tests |
| `_changes` | A different setpoint adds one change; the same setpoint again and gain changes add none | Same-setpoint and gain-change tests |
| D-14 | `RuntimeError` naming "the controller is off" while off | Off-state test |

### Open Questions Raised This Pass

None new (IQ-9 and IQ-10 apply; see the US-7 pass).

### Deviations From Approved DESIGN/ARCHITECTURE

- Five scenarios were strict xfail until US-9 and US-10 landed (IQ-9, confirmed by the operator).

### Version Control Actions

- Branch: `feature/us8-change-gains-setpoint` (from `feature/us7-pid-controller-on` at `8bb54cb`)
- Commits:
  - `23dacb6` test(controller): add failing US-8 gain and setpoint change acceptance tests (red, before code)
  - `514a97a` feat(controller): add set_gains and set_setpoint
- PR: opened against `main` and merged with a merge commit, in story order (US-7 first), after the operator signed

---

## Pass: 2026-11-14 — US-7 Turn on a PID altitude controller

**Branch:** `feature/us7-pid-controller-on`
**Traces to:** `docs/design/DESIGN_0bfd04e.md` (US-7, OQ-31, OQ-32, OQ-33), `docs/architecture/ARCHITECTURE_3dbd8e9.md` (Entity: Controller state; D-8, D-14; AQ-7, AQ-13)
**Approval basis:** as for US-11.
**Mode:** as for US-11.

**Files:** `src/kuava_sim/simulation.py` (`ControllerStatus`, `enable_controller`, `disable_controller`, `controller`, manual-thrust rejection), `src/kuava_sim/__init__.py`, `tests/acceptance/test_us7_controller_on.py`.
**Red proof:** the tests were committed in `99ff794` before any production code (60 failed, 0 passed, 3 strict xfail; all failures "no attribute 'controller'" or "'enable_controller'"). `git diff --stat 99ff794 8bb54cb -- tests/` is empty.
**Result:** 288 passed, 3 xfailed (strict, waiting for US-9 and US-10).

### Acceptance Criteria Coverage

| Scenario | Status | Test(s) |
|---|---|---|
| Valid gains and setpoint are accepted | ✅ Pass | `test_valid_gains_and_setpoint_are_accepted_and_reported_back`, `test_controller_is_off_with_no_settings_before_it_is_turned_on`, `test_turning_on_does_not_step_or_change_records` |
| Gains and setpoint at their lower limit are accepted | ✅ Pass | `test_zero_is_accepted_for_each_setting`, `test_smallest_positive_value_is_accepted_for_each_setting` |
| Negative gains or a setpoint below the ground are rejected | ✅ Pass | `test_negative_value_is_rejected_with_clear_error` (−0.001, −1, next double below 0; message names the setting and "must not be below 0") |
| Non-finite gains or setpoint are rejected | ✅ Pass | `test_non_finite_value_is_rejected_with_clear_error`, `test_non_number_value_is_rejected_with_clear_error` |
| Turning on without a setpoint is rejected | ✅ Pass | `test_turning_on_without_a_setting_is_rejected` (each of the four) |
| Large setpoints are accepted | ✅ Pass | `test_large_setpoint_is_accepted` |
| Turning on counts as the first setpoint change | ⚠️ Partial, then ✅ | `test_turning_on_counts_as_the_first_setpoint_change`, completed in US-10 |
| Taking off from the ground under control | ⚠️ Partial, then ✅ | `test_taking_off_from_the_ground_under_control`, completed in US-9 |
| Manual thrust is rejected while the controller is on | ✅ Pass | `test_manual_thrust_is_rejected_while_the_controller_is_on` (`step`, `run`, `run(0)`, NaN; `RuntimeError`, nothing changes) |
| Turning the controller off returns Round 1 behaviour | ⚠️ Partial, then ✅ | `test_turning_off_accepts_manual_commands_again`; `test_turning_off_keeps_the_last_controller_command_as_held_thrust` completed in US-9 |
| D-14 lifecycle | ✅ Pass | `test_turning_on_while_on_is_rejected`, `test_turning_off_while_off_does_nothing`, `test_controller_can_be_turned_on_again_after_off` |

### Predicates / Invariants Matched

| Entity/Predicate | Invariant / Boundary / Concurrency Rule | Verified By |
|---|---|---|
| Controller state | Gains and setpoint finite and ≥ 0, all four checked before any change; settings `NaN` while off; integral reset to 0 on turning on | Limit tests (0, smallest positive, next double below 0), status tests |
| `_changes` | Turning on adds the first setpoint change | US-7 and US-10 tests |
| OQ-31 | Manual thrust rejected while on, with all state unchanged | Manual-thrust test |
| Concurrency | Not thread-safe, no locking (as Round 1) | Inspection |

### Open Questions Raised This Pass

All used the recommended option while the operator was away; the operator later confirmed all three. IQ-9 to IQ-11 cover the whole of Round 2.

| ID | Question | Status | Resolution |
|---|---|---|---|
| IQ-9 | Several Round 2 scenarios need a later story's code (the controlled step is US-9, metrics are US-10). (a) **Recommended:** keep each scenario in its own story as a strict xfail (as IQ-1 and IQ-2) and remove the marker in the red commit of the story that completes it, so it joins the red set; (b) implement the controlled step and metrics inside US-7, which makes the US-9 and US-10 red phases meaningless; (c) reorder the stories. | Resolved | "IQ-9 a" (confirmed by the operator after the pass) |
| IQ-10 | Nothing can be signed while the operator is away, so the usual History move and docs commit cannot be done per story. (a) **Recommended:** as IQ-8: stack the five branches (US-7 from `main`, each next one from the previous), do the History move once as the first commit on the US-7 branch, keep one shared Pending entry for US-7 to US-11, and commit all five log entries and the signed entry in one docs commit on the last branch; (b) five independent branches from `main` with five Pending entries; (c) wait for the operator. | Resolved | "IQ-10 a" (confirmed by the operator after the pass) |
| IQ-11 | See the US-11 pass (no red phase and no code for US-11). | Resolved | "IQ-11 a" (confirmed by the operator after the pass) |

### Deviations From Approved DESIGN/ARCHITECTURE

- Three scenarios were strict xfail until US-9 and US-10 landed. Caused by IQ-9 (option a, confirmed by the operator).
- Process: stacked branches and one shared Pending entry for US-7 to US-11. Caused by IQ-10 (option a, confirmed by the operator).

### Version Control Actions

- Branch: `feature/us7-pid-controller-on` (from `main` at `9e9653b`)
- Commits:
  - `e7cd1fb` docs(approval): move round 2 architecture approval to history
  - `99ff794` test(controller): add failing US-7 controller on/off acceptance tests (red, before code)
  - `8bb54cb` feat(controller): add PID controller on/off and its status
- PR: opened against `main` and merged with a merge commit, in story order (US-7 first), after the operator signed

---

## Pass: 2026-11-14 — US-5 Open-loop thrust input (no controller)

**Branch:** `feature/us5-open-loop-thrust` (from `feature/us4-deterministic-runs`, see IQ-8)
**Traces to:** `docs/design/DESIGN.md` (US-5), `docs/architecture/ARCHITECTURE.md` (Entity: Simulation — raw held command capped at use time, all-or-nothing command checks, `step(thrust)` / `run(n, thrust)` semantics; decision D-6)
**Approval basis:** Requirement Analysis entry approved 13.11.2026; Solution Architecture entry approved 14.11.2026 (see `docs/APPROVAL_LOG.md`)
**Mode:** done while the operator was away, under their pre-approval of the Git plan up to the code commit. Real decisions used the recommended option, marked awaiting operator confirmation; all were later confirmed (IQ-4 to IQ-8 "a"). Nothing was signed, pushed or merged.

**Files:** `tests/acceptance/test_us5_thrust_input.py`. No production code changed.
**Red proof:** there was no red phase. The tests pass against the existing code, because holding, capping and rejecting thrust commands already came with US-2, US-3 and US-6 (IQ-4, applied as for US-4). The tests were committed in `9ae263c` before any production code. `git diff main -- src/` on this branch is empty. Five faults were planted in scratch copies of the code (not committed), and the US-5 tests caught all five:

| Planted fault | Caught by (failing tests) |
|---|---|
| Command not held (falls back to 0 after each step) | 34 tests in 8 test functions |
| Held command starts at 1 N | `test_held_thrust_command_starts_at_zero` |
| Rejected command still replaces the held command | `test_rejected_command_does_not_replace_the_held_command` (all 5 cases) |
| Hidden controller adds 1 N while falling | 15 tests in 6 test functions, including `test_simulation_does_not_react_to_its_own_state` |
| Capping applied only on the step that gave the command | `test_held_command_outside_limits_keeps_being_limited` |

**Result:** 228 passed, 0 xfailed (full suite, US-4 and US-5 included). Python 3.15.2, pytest 9.2.0.

### Acceptance Criteria Coverage

All tests are in `tests/acceptance/test_us5_thrust_input.py`. "Thrust used" is read from the records.

| Scenario | Status | Test(s) |
|---|---|---|
| Held thrust command starts at 0 | ✅ Pass | `test_held_thrust_command_starts_at_zero` |
| The last command is held when no new command is given | ✅ Pass | `test_last_command_is_held_when_no_new_command_is_given`, `test_run_applies_the_command_to_the_first_step_and_then_holds_it` |
| A new command replaces the held command | ✅ Pass | `test_new_command_replaces_the_held_command`, `test_new_zero_command_replaces_the_held_command` |
| A held command outside the limits keeps being limited | ✅ Pass | `test_held_command_outside_limits_keeps_being_limited`, `test_held_command_at_the_limits_is_used_the_same_on_every_step` (0 and 20 N, each ± one double) |
| Commanded thrust within limits is applied regardless of state | ✅ Pass | `test_thrust_within_limits_is_used_exactly_whatever_the_state` (5 thrust values × 5 states: resting on the ground, on the ground moving up, falling fast, rising fast, about to land) |
| The simulation does not react to its own state | ✅ Pass | `test_simulation_does_not_react_to_its_own_state` (1000 steps at 5 N; altitude falls every step) |
| Rejected command does not replace the held command | ✅ Pass | `test_rejected_command_does_not_replace_the_held_command` (NaN, ±Inf, bool, str; via `step` and `run`) |

### Predicates / Invariants Matched

| Entity/Predicate | Invariant / Boundary / Concurrency Rule | Verified By |
|---|---|---|
| `Simulation.held_thrust` | Starts at 0 N; the raw last accepted command is held (25 N and −3 N stay held as given) | Start and held-outside-limits tests |
| Thrust capping | `T_used = min(max(held, 0), max_thrust)` on every step, not only the commanding one | Limits tests at 0 and max ± one double over 5 steps |
| `step(thrust)` / `run(n, thrust)` | The command applies to the first step and is then held | Hold and replace tests |
| All-or-nothing | A rejected command leaves the held command unchanged | Rejection tests |
| No controller | Thrust used never depends on altitude or velocity | State-independence tests; the hidden-controller plant was caught |

### Open Questions Raised This Pass

IQ-4 (no red phase) applies to US-5 as well; see the US-4 pass. New this pass:

| ID | Question | Status | Resolution |
|---|---|---|---|
| IQ-8 | US-4 is not signed yet, so its approval entry cannot move to History, the log allows only one active entry, and the US-4 docs stay uncommitted until sign-off. How should US-5 be set up? (a) **Recommended:** branch US-5 from the US-4 branch, skip the History-move commit for US-5, use one Pending entry covering both US-4 and US-5, and keep both stories' docs uncommitted in the working tree until the operator signs; (b) branch US-5 from `main` with its own Pending entry (two active entries, and the US-6 History move repeated on both branches); (c) wait for the operator before starting US-5. | Resolved | "IQ-8 a" (confirmed by the operator after the pass) |

### Deviations From Approved DESIGN/ARCHITECTURE

- No red phase and no production code for US-5: the behaviour already existed. The proof that the tests can fail comes from planted faults instead. Caused by IQ-4 (option a, confirmed by the operator).
- Process: no History-move commit on this branch, the branch is stacked on the US-4 branch, and one Pending approval entry covers both stories. Caused by IQ-8 (option a, confirmed by the operator).

### Version Control Actions

- Branch: `feature/us5-open-loop-thrust` (from `feature/us4-deterministic-runs` at `fca3b74`)
- Commits: `9ae263c` test(thrust): add US-5 open-loop thrust input acceptance tests (before any code; no code commit needed)
- docs(implementation): log the US-4 and US-5 implementation passes (both entries and the shared signed approval entry)
- PR: opened against `main` after the US-4 PR was merged, merged with a merge commit

---

## Pass: 2026-11-14 — US-4 Deterministic runs

**Branch:** `feature/us4-deterministic-runs`
**Traces to:** `docs/design/DESIGN.md` (US-4), `docs/architecture/ARCHITECTURE.md` (decisions D-2 plain floats, D-3 fixed formulation, D-7 separate-process byte comparison; Entity: Simulation — no wall-clock access, no global mutable state)
**Approval basis:** Requirement Analysis entry approved 13.11.2026; Solution Architecture entry approved 14.11.2026 (see `docs/APPROVAL_LOG.md`)
**Mode:** done while the operator was away, under their pre-approval of the Git plan up to the code commit. Real decisions used the recommended option, marked awaiting operator confirmation; all were later confirmed (IQ-4 to IQ-8 "a"). Nothing was signed, pushed or merged.

**Files:** `tests/acceptance/test_us4_determinism.py`, `tests/acceptance/us4_scenario.py` (shared scenario, also run as a script). No production code changed.
**Red proof:** there was no red phase. The tests pass against the existing code, because determinism already follows from US-2, US-3 and US-6 (IQ-4). The tests were committed in `fca3b74` before any production code. `git diff main -- src/` on this branch is empty. To show the tests can fail, four faults were planted in scratch copies of the code (not committed), and the US-4 tests caught all four:

| Planted fault | Caught by |
|---|---|
| Time-based noise in the acceleration | all 5 tests |
| Result depends on the process hash seed | `test_repeated_executions_in_separate_processes_give_identical_records` |
| `run(n)` differs from n single steps | `test_single_steps_and_run_n_give_identical_records` |
| Thrust command takes effect one step late | `test_changed_input_changes_output_only_from_that_step_on`, `test_single_steps_and_run_n_give_identical_records` |

The first attempt at the time-noise fault was itself broken (on Windows `perf_counter_ns()` counts in steps of 100 ns, so `& 1` was always 0); it was fixed and rerun.

**Result:** 185 passed, 0 xfailed (full suite). Python 3.15.2, pytest 9.2.0. The delay-and-load test takes about 5 s.

### Acceptance Criteria Coverage

All tests are in `tests/acceptance/test_us4_determinism.py`.

| Scenario | Status | Test(s) |
|---|---|---|
| Identical inputs yield identical outputs in one process | ✅ Pass | `test_identical_inputs_give_identical_records_in_one_process` (10000 steps, every record compared byte for byte; the scenario is checked to be non-trivial: capping and zeroing happen, the drone moves and stays airborne) |
| Repeated executions yield identical outputs | ✅ Pass | `test_repeated_executions_in_separate_processes_give_identical_records` (IQ-5) |
| Output does not depend on host timing or load | ✅ Pass | `test_records_do_not_depend_on_wall_clock_delays_or_load` (IQ-6) |
| Single steps and "run N steps" give identical outputs | ✅ Pass | `test_single_steps_and_run_n_give_identical_records` (N = 1000) |
| A changed input changes the output only from that step on | ✅ Pass | `test_changed_input_changes_output_only_from_that_step_on` (IQ-7) |

### Predicates / Invariants Matched

| Entity/Predicate | Invariant / Boundary / Concurrency Rule | Verified By |
|---|---|---|
| D-2, D-3 | Same configuration and commands give the same bytes on the same machine | In-process and separate-process byte comparisons |
| D-7 | The same script run twice with `subprocess`, output compared as bytes | Separate-process test (via the public records API, see IQ-5) |
| `Simulation` | No wall-clock access | Delay test with real `time.sleep` pauses between steps |
| `Simulation` | No global mutable state; independent instances | Two instances in one process; a busy thread running alongside |
| Causality | A command affects only its own step and later steps | Changed-input test: records 0–499 byte-identical, every record from 500 on different |

### Open Questions Raised This Pass

All used the recommended option while the operator was away; the operator later confirmed every one.

| ID | Question | Status | Resolution |
|---|---|---|---|
| IQ-4 | US-4 is already satisfied by the code from US-2, US-3 and US-6, so the tests cannot fail first and there is no code to write. How should the story be handled? (a) **Recommended:** commit the tests as usual, prove they can fail by planting faults in scratch copies, and make no code commit; (b) commit the tests without any proof that they can fail; (c) skip US-4 as already covered. | Resolved | "IQ-4 a" (confirmed by the operator after the pass) |
| IQ-5 | How should the separate-process test run and compare? (a) **Recommended:** run `us4_scenario.py` twice as a script with `subprocess`, using different `PYTHONHASHSEED` values (1 and 2); the script writes all record bytes, built through the public records API, to stdout; compare the full bytes with each other and with an in-process run; (b) same, but compare SHA-256 digests only; (c) read the private `records._data.tobytes()` as ARCHITECTURE.md D-7 words it. | Resolved | "IQ-5 a" (confirmed by the operator after the pass) |
| IQ-6 | What counts as "artificial wall-clock delays" and "host load"? (a) **Recommended:** 300 steps with a 5 ms `time.sleep` after each step, while a busy background thread competes for the interpreter (about 5 s); (b) delays only, as the AC literally says; (c) delays plus busy processes on every CPU core. | Resolved | "IQ-6 a" (confirmed by the operator after the pass) |
| IQ-7 | What does "output records from step 500 onward differ" mean, and which thrust sequence is used? (a) **Recommended:** every record from 500 to the end differs, checked over 1000 steps with a fixed sequence (hover ± 3 N sine, held every 7th step, 35 N capped every 97th, −2 N zeroed every 131st) that keeps the drone airborne so the two runs never meet again at the floor; (b) only that the records from 500 on are not all identical. | Resolved | "IQ-7 a" (confirmed by the operator after the pass) |

### Deviations From Approved DESIGN/ARCHITECTURE

- No red phase and no production code for US-4: the behaviour already existed. The proof that the tests can fail comes from planted faults instead. Caused by IQ-4 (option a, confirmed by the operator).
- The separate-process test builds the bytes through the public records API instead of reading `records._data.tobytes()` as ARCHITECTURE.md D-7 words it. Caused by IQ-5 (option a, confirmed by the operator).

### Version Control Actions

- Branch: `feature/us4-deterministic-runs` (from `main` at `b318805`)
- Commits:
  - `a143755` docs(approval): move US-6 implementation approval to history
  - `fca3b74` test(determinism): add US-4 deterministic run acceptance tests (before any code; no code commit needed)
- The docs for US-4 and US-5 (both log entries and the shared signed approval entry) are committed on the US-5 branch (IQ-8, a).
- PR: opened against `main` and merged with a merge commit before the US-5 PR

---

## Pass: 2026-11-14 — US-6 Output records

**Branch:** `feature/us6-output-records`
**Traces to:** `docs/design/DESIGN.md` (US-6, I-1, I-2, I-3), `docs/architecture/ARCHITECTURE.md` (Entity: Record, Entity: RecordLog, Entity: Simulation — records as the single source of truth, `step()` returns the Record; decision D-5 record storage)
**Approval basis:** Requirement Analysis entry approved 13.11.2026; Solution Architecture entry approved 14.11.2026 (see `docs/APPROVAL_LOG.md`)

**Files:** `src/kuava_sim/simulation.py`, `src/kuava_sim/__init__.py`, `tests/acceptance/test_us6_records.py`; the strict xfail markers were removed from `test_us1_config.py`, `test_us2_fixed_steps.py` and `test_us3_dynamics.py`.
**Red proof:** the tests and marker removals were committed in `cccecfd` before any production code (38 failed: 26 new US-6 tests and the 12 former xfails, all with "no attribute 'records'"; 0 US-6 tests passed). `git diff cccecfd -- tests/` is empty after green.
**Result:** 180 passed, 0 xfailed. Python 3.15.2, pytest 9.2.0. As the operator asked, no planted-bug check was run.

### Acceptance Criteria Coverage

All US-6 tests are in `tests/acceptance/test_us6_records.py`.

| Scenario | Status | Test(s) |
|---|---|---|
| The starting moment is the first record | ✅ Pass | `test_starting_moment_is_the_first_record`, plus the I-3 edge cases `test_starting_record_off_the_ground_at_rest_shows_gravity` and `test_starting_record_on_the_ground_moving_up_shows_forces` |
| Starting record on the ground at rest | ✅ Pass | `test_starting_record_on_the_ground_at_rest_is_all_zero` (v0 0.0 and −0.0; bytes equal to six +0.0) |
| One record is added after every step | ✅ Pass | `test_one_record_is_added_after_every_step` (251 records, time i/200, strictly increasing), `test_each_single_step_adds_exactly_one_record` |
| Each record contains the required fields | ✅ Pass | `test_step_returns_the_new_record_with_the_current_state`, `test_state_always_matches_the_last_record` |
| Record values match a hand calculation | ✅ Pass | `test_record_values_match_a_hand_calculation` |
| Limited thrust is recorded as the thrust actually used | ✅ Pass | `test_limited_thrust_is_recorded_as_thrust_actually_used` |
| Records keep growing without a limit | ✅ Pass | `test_records_keep_growing_without_a_limit` (720001 records), `test_earlier_records_never_change_when_more_are_added` |
| Rejected operations add no records | ✅ Pass | `test_rejected_thrust_adds_no_records` (NaN, ±Inf), `test_rejected_run_adds_no_records` |

**Earlier scenarios now complete** (strict xfail markers removed in `cccecfd`; all pass):
- US-1 "Maximum thrust of 0 N is accepted": `test_max_thrust_zero_keeps_drone_on_ground_with_zero_thrust_used` (IQ-1).
- US-2 "Run N steps shortcut", "Running 0 steps does nothing", "Invalid N is rejected": the record comparisons (IQ-2).
- US-3 thrust used recorded after limits, records unchanged after rejected thrust, zero acceleration and drag on rest, landing and no-bounce records (I-2).

### Predicates / Invariants Matched

| Entity/Predicate | Invariant / Boundary / Concurrency Rule | Verified By |
|---|---|---|
| `RecordLog` storage (D-5) | One `array('d')`, 6 doubles per record, one `extend` per step | Code inspection; byte comparisons in US-2/US-6 tests |
| `RecordLog` | `len(records) == step_count + 1`, never empty (time-0 record) | Count tests (1, 251, 720001) |
| `RecordLog` | Append-only: earlier records never change | `test_earlier_records_never_change_when_more_are_added` |
| `RecordLog` view | Read-only `Sequence[Record]`: negative index, slices, `IndexError` out of range, no item assignment; an earlier view sees new records; `column(name)` returns a tuple | View tests and `test_column_returns_one_field_as_a_series` (all 6 fields) |
| `Record` | Immutable `NamedTuple` with fields `time, altitude, velocity, acceleration, thrust_used, drag` | `test_records_and_record_fields_cannot_be_changed`, `_fields` check |
| `Record.time` | `i / 200` from the step count | Every record checked in the 250-step test, sampled every 1000 in the 720000-step test |
| Time-0 record (I-3) | At rest on the ground gives literal +0.0 in every field; otherwise `drag = -(b*v0)`, `a = ((0 - m*g) + drag) / m` | Time-0 tests (hand values, −0.0 case, edge cases) |
| Floor/rest record (I-2) | Altitude, velocity, acceleration and drag exactly 0; thrust used as applied | US-3 rest, landing and no-bounce record tests |
| `Simulation` | Time, altitude and velocity are read from the last record (single source of truth) | `test_state_always_matches_the_last_record` |
| `step()` | Returns the new `Record` | `test_step_returns_the_new_record_with_the_current_state` |
| Concurrency | Not thread-safe, no locking; a step appends all 6 values in one call | Inspection |

### Open Questions Raised This Pass

| ID | Question | Status | Resolution |
|---|---|---|---|
| IQ-3 | After US-3, which story comes next? (a) US-4, following DESIGN.md order; (b) US-6. | Resolved | "US-6 next, because it turns the 12 expected failures into real checks and lets US-4 compare records directly." |

### Deviations From Approved DESIGN/ARCHITECTURE

- Stories are implemented out of DESIGN.md order: US-6 before US-4 and US-5. Caused by IQ-3: "US-6 next, because it turns the 12 expected failures into real checks and lets US-4 compare records directly."
- The interim deviations logged for US-2 and US-3 are now closed. The state is read from the last record, `step()` returns the `Record`, and every scenario that waited for records is fully covered.

### Version Control Actions

- Branch: `feature/us6-output-records`
- Commits:
  - `f5f660d` docs(approval): move US-3 implementation approval to history
  - `cccecfd` test(records): add failing US-6 output record acceptance tests (red, before code; also removes the 12 xfail markers)
  - `03788a4` feat(records): add in-memory output records
  - docs(implementation): log the US-6 implementation pass (this entry and the signed approval entry)
- PR: opened against `main` after the docs commit, merged with a merge commit (pass signed by the operator before the docs commit)

---

## Pass: 2026-11-14 — US-3 Compute vertical dynamics from gravity, thrust and drag

**Branch:** `feature/us3-vertical-dynamics`
**Traces to:** `docs/design/DESIGN.md` (US-3, I-1, I-4), `docs/architecture/ARCHITECTURE.md` (Entity: Simulation — step, thrust checks, all-or-nothing; decisions D-2 floats, D-3 formulation, D-4 floor condition, D-6 errors)
**Approval basis:** Requirement Analysis entry approved 13.11.2026; Solution Architecture entry approved 14.11.2026 (see `docs/APPROVAL_LOG.md`)

**Files:** `src/kuava_sim/simulation.py`, `tests/acceptance/test_us3_dynamics.py`.
**Red proof:** the tests were committed in `1f5fad7` before any production code (37 failed, 0 passed, 7 strict xfail for record fields). `git diff 1f5fad7 -- tests/` is empty after green.
**Result:** 142 passed, 12 xfailed (strict: 1 from IQ-1, 4 from IQ-2, 7 US-3 record-field tests waiting for US-6). Python 3.15.2, pytest 9.2.0. As the operator asked, no planted-bug check was run.

### Acceptance Criteria Coverage

All tests are in `tests/acceptance/test_us3_dynamics.py`.

| Scenario | Status | Test(s) |
|---|---|---|
| Free fall matches the formula within 0.6 % after 1 s | ✅ Pass | `test_free_fall_after_1_s_within_0_6_percent` |
| Free fall stays within 0.6 % for longer durations | ✅ Pass | `test_free_fall_after_2_s_within_0_6_percent` |
| Velocity is updated before altitude (semi-implicit Euler) | ✅ Pass | `test_one_step_updates_velocity_before_altitude` |
| Hover keeps the same height | ✅ Pass | `test_hover_keeps_the_same_height_for_2000_steps` (every step within ε), `test_hover_is_bit_exact_when_thrust_is_mass_times_gravity` (D-3) |
| Excess thrust accelerates the drone upward | ✅ Pass | `test_excess_thrust_accelerates_upward` |
| Heavier drone accelerates less for the same thrust | ✅ Pass | `test_heavier_drone_accelerates_less` (1 kg, 2 kg) |
| Linear drag opposes motion and is proportional to velocity | ✅ Pass | `test_drag_used_in_a_step_is_minus_b_times_start_velocity` (+4, −4, 0 m/s; drag measured from the velocity change) |
| Linear drag limits falling speed to m·g/b | ✅ Pass | `test_drag_limits_falling_speed_to_m_g_over_b` (monotonic, ≤ 19.62 every step, within 0.6 % at the end) |
| Thrust above the maximum is capped silently | ⚠️ Partial | `test_thrust_above_maximum_is_capped_silently` (25, 20.001, next double above 20; no warnings) ✅. The recorded value, `test_thrust_used_is_recorded_after_limits`, is strict xfail until US-6 |
| Negative thrust command is set to 0 silently | ⚠️ Partial | `test_negative_thrust_is_set_to_zero_silently` (−5, −0.001, −5e-324) ✅. Recorded value: strict xfail until US-6 |
| Thrust at and inside the limits is used as commanded | ✅ Pass | `test_thrust_at_and_inside_limits_is_used_as_commanded` (20, 19.999, 0.001, 0), `test_thrust_just_inside_limits_is_not_capped` |
| Non-finite thrust command is rejected | ⚠️ Partial | `test_non_finite_thrust_is_rejected_and_nothing_changes`, `test_non_number_thrust_is_rejected_and_nothing_changes` ✅. `test_non_finite_thrust_leaves_records_unchanged` strict xfail until US-6 |
| Resting on the ground with insufficient thrust | ⚠️ Partial | `test_resting_on_ground_with_insufficient_thrust` (altitude/velocity every step, time) ✅. `test_resting_on_ground_records_zero_acceleration_and_drag` strict xfail until US-6 |
| Taking off from the ground | ✅ Pass | `test_taking_off_from_the_ground` (also the hand values 0.04905 m/s, 0.00024525 m) |
| Landing stops at the floor and the run continues | ⚠️ Partial | `test_landing_stops_at_floor_and_run_continues` (lands on step 90 as hand-calculated) ✅. `test_landing_step_records_zero_acceleration_and_drag` strict xfail until US-6 |
| Landing at speed does not bounce | ⚠️ Partial | `test_landing_at_speed_does_not_bounce` ✅. `test_landing_at_speed_records_zero_acceleration_and_drag` strict xfail until US-6 |

### Predicates / Invariants Matched

| Entity/Predicate | Invariant / Boundary / Concurrency Rule | Verified By |
|---|---|---|
| D-3 formulation | `D = -(b*v_start)`, `a = ((T - m*g) + D) / m`, `vn = v + a*DT`, `hn = h + vn*DT` | Single-step and takeoff hand values within ε; bit-exact hover |
| D-4 floor | Floor when `hn <= 0 and vn < 0`; altitude and velocity set to exactly `0.0` | `test_floor_applies_when_landing_exactly_on_zero_while_moving_down` (L), `…just_below_the_limit` (L−ε), `test_floor_does_not_apply_just_above_the_limit` (L+ε) |
| Record invariant | `altitude ≥ 0` and `altitude == 0 ⇒ velocity ≥ 0` after every step | `test_no_record_is_on_the_ground_while_moving_down`; landing tests check every step |
| Thrust capping | `T_used = min(max(held, 0), max_thrust)`, silent, applied at use time | Capping tests at L and L ± one double, compared byte for byte with the limit value; warnings recorded and asserted empty |
| Thrust command check | Non-finite gives `ValueError`, non-number gives `TypeError`, both naming "thrust"; checked before any change in `step` and `run` | Rejection tests assert unchanged state and held thrust |
| All-or-nothing | `run` checks `n` and `thrust` before changing anything; `run(0, thrust=x)` checks `x` but does not hold it | US-2 and US-3 rejection tests |
| Concurrency | Not thread-safe, no locking; instances share no state | Inspection |

### Open Questions Raised This Pass

None.

### Deviations From Approved DESIGN/ARCHITECTURE

- The record-field parts of six US-3 scenarios (thrust used, acceleration, drag on floor and rest steps, records unchanged after rejection) are strict xfail until US-6. Caused by IQ-2's approach (option a), applied to US-3.
- Interim until US-6: altitude, velocity and the step count are held in fields instead of being derived from the last record, and `step()` returns `None` instead of the new `Record`.

### Process Notes

- Two red-phase tests passed against US-2's frozen altitude and velocity (bit-exact hover, drag at 0 m/s). Before the red commit they were strengthened with checks that the drone actually moves (thrust above hover must lift it; the drag test uses m·g + 1 N). No test changed after the red commit.

### Version Control Actions

- Branch: `feature/us3-vertical-dynamics`
- Commits:
  - `08dc3d4` docs(approval): move US-2 implementation approval to history
  - `1f5fad7` test(dynamics): add failing US-3 vertical dynamics acceptance tests (red, before code)
  - `543347c` feat(dynamics): add vertical dynamics, thrust limits and ground floor
  - docs(implementation): log the US-3 implementation pass (this entry and the signed approval entry)
- PR: opened against `main` after the docs commit, merged with a merge commit (pass signed by the operator before the docs commit)

---

## Pass: 2026-11-14 — US-2 Advance the simulation in fixed time steps

**Branch:** `feature/us2-fixed-time-steps`
**Traces to:** `docs/design/DESIGN.md` (US-2), `docs/architecture/ARCHITECTURE.md` (Entity: Simulation — `step`, `run`, `step_count`, `time`; Constants; decisions D-3 time formula, D-6 API shape)
**Approval basis:** Requirement Analysis entry approved 13.11.2026; Solution Architecture entry approved 14.11.2026 (see `docs/APPROVAL_LOG.md`)

**Files:** `src/kuava_sim/simulation.py`, `tests/acceptance/test_us2_fixed_steps.py`.
**Red proof:** the tests were committed in `7583605` before any production code (19 failed, 4 strict xfail for records). `git diff 7583605 -- tests/` is empty after green.
**Result:** 105 passed, 5 xfailed (strict: 1 from IQ-1, 4 from IQ-2). Python 3.15.2, pytest 9.2.0. The wall-clock pause test takes about 10 s by design. As the operator asked, no planted-bug check was run.

### Acceptance Criteria Coverage

All tests are in `tests/acceptance/test_us2_fixed_steps.py`.

| Scenario | Status | Test(s) |
|---|---|---|
| Each step advances simulated time by exactly one fixed step | ✅ Pass | `test_new_simulation_starts_at_time_zero`, `test_one_step_advances_time_by_one_fixed_step` |
| Simulated time is derived from the step count without drift | ✅ Pass | `test_720000_steps_give_3600_s_without_drift` |
| The simulation never stops by itself | ✅ Pass | `test_simulation_keeps_stepping_after_720000_steps` |
| Run N steps shortcut | ⚠️ Partial | State: `test_run_200_gives_same_state_as_200_single_steps`, `test_run_1_is_exactly_one_step` ✅. Records: `test_run_200_gives_same_records_as_200_single_steps` strict xfail until US-6 (IQ-2) |
| Running 0 steps does nothing and is not an error | ⚠️ Partial | `test_run_0_leaves_state_and_time_unchanged`, `test_run_0_with_thrust_does_not_change_held_command` ✅. `test_run_0_leaves_the_11_records_unchanged` strict xfail until US-6 (IQ-2) |
| Invalid N for "run N steps" is rejected | ⚠️ Partial | `test_invalid_n_is_rejected_and_state_unchanged` (−1, 2.5, 200.0, True, "3", None) ✅. `test_invalid_n_leaves_records_unchanged` strict xfail until US-6 (IQ-2) |
| Step length cannot vary between steps | ✅ Pass | `test_step_length_cannot_be_passed_to_step_or_run` (`dt`, `step_length`, `step_rate_hz`) |
| Simulation runs as fast as possible, not paced to the wall clock | ✅ Pass | `test_200000_steps_run_without_waiting_on_the_wall_clock` (`time.sleep` patched to fail; under 100 s for 1000 s simulated) |
| Simulated time is independent of wall-clock time | ✅ Pass | `test_simulated_time_is_independent_of_wall_clock_pauses` (real 10 ms pauses) |

### Predicates / Invariants Matched

| Entity/Predicate | Invariant / Boundary / Concurrency Rule | Verified By |
|---|---|---|
| `Simulation.time` | `time = step_count / 200` from the integer count, never a running sum of `DT` | 720000- and 720001-step tests within ε; code inspection |
| `Simulation.run(n)` | `n` must be an `int` and not a `bool` (otherwise `TypeError`); `n < 0` gives `ValueError`; checked before any change | Invalid-N tests assert unchanged state and held thrust |
| `Simulation.run(n)` boundary | −1 rejected, 0 pure no-op (a given thrust is not held), 1 equals one `step` | `test_invalid_n_…[-1]`, run-0 tests, `test_run_1_is_exactly_one_step` |
| `Simulation.run(n)` | Same as `n` calls to `step()`: the thrust applies to the first step and is then held | `test_run_200_gives_same_state_as_200_single_steps` (bytes compared) |
| D-6 API | No step-length option on `step`/`run` (unexpected keyword gives `TypeError`) | Step-length test |
| No wall clock | No `time.sleep` or `time.time` in the simulation | Patched `time.sleep`, wall-clock pause test, inspection |
| Concurrency | Not thread-safe, no locking; instances share no state | Two-instance tests; inspection |

### Open Questions Raised This Pass

| ID | Question | Status | Resolution |
|---|---|---|---|
| IQ-2 | Three US-2 scenarios compare records (US-6), the run-N comparison only means much once altitude and velocity change (US-3), and a thrust argument is needed (held command is US-5). Implement only the US-2 part and mark the record tests strict xfail, or add physics and records now? | Resolved | "IQ-2 a": US-2 adds `step`/`run`, step count, time, N checks and a held thrust; record tests are strict xfail until US-6; altitude and velocity stay at their start values until US-3 |

### Deviations From Approved DESIGN/ARCHITECTURE

- The record parts of three US-2 scenarios are strict xfail until US-6. Caused by IQ-2: "IQ-2 a".
- Interim, caused by IQ-2: `altitude` and `velocity` return the configured start values, and `step()` has no dynamics yet (US-3). The step count is held in `_step_count` instead of being derived from the last record as ARCHITECTURE.md describes (RecordLog arrives with US-6). `step()` stores the thrust command without checking it; the non-finite rejection belongs to the US-3/US-5 ACs. `step()` returns `None` instead of the new `Record` (US-6).

### Version Control Actions

- Branch: `feature/us2-fixed-time-steps`
- Commits:
  - `e3b5701` docs(approval): move US-1 implementation approval to history
  - `7583605` test(steps): add failing US-2 fixed time step acceptance tests (red, before code)
  - `7d46d24` feat(steps): add fixed-step step() and run(n)
  - docs(implementation): log the US-2 implementation pass (this entry and the signed approval entry)
- PR: opened against `main` after this commit, merged with a merge commit (pass signed by the operator before the docs commit)

---

## Pass: 2026-11-14 — US-1 Configure the simulation

**Branch:** `feature/us1-configure-simulation`
**Traces to:** `docs/design/DESIGN.md` (US-1), `docs/architecture/ARCHITECTURE.md` (Constants, Entity: SimConfig, Entity: Simulation — construction and read-only properties only; decisions D-1, D-2, D-6, D-7)
**Approval basis:** Requirement Analysis entry approved 13.11.2026; Solution Architecture entry approved 14.11.2026 (see `docs/APPROVAL_LOG.md`)

**Files:** `src/kuava_sim/simulation.py`, `src/kuava_sim/__init__.py`, `tests/acceptance/test_us1_config.py`, `pyproject.toml`.
**Result:** 86 passed, 1 xfailed (strict, IQ-1). Python 3.15.2, pytest 9.2.0.

### Acceptance Criteria Coverage

All tests are in `tests/acceptance/test_us1_config.py`.

| Scenario | Status | Test(s) |
|---|---|---|
| Valid configuration is accepted | ✅ Pass | `test_valid_configuration_reports_exact_values_back`, `test_valid_configuration_reports_fixed_step_rate_length_and_min_thrust`, `test_module_constants_have_specified_values` |
| Defaults are applied when optional values are omitted | ✅ Pass | `test_defaults_are_applied_when_only_mass_and_max_thrust_are_set`, `test_mass_and_max_thrust_are_required` |
| Gravity can be changed from the default | ✅ Pass | `test_gravity_can_be_changed_from_the_default` |
| Gravity of 0 or less is rejected with a clear error | ✅ Pass | `test_gravity_zero_or_less_is_rejected_with_clear_error` (0, −9.81, −5e-324) |
| Smallest positive gravity is accepted | ✅ Pass | `test_small_positive_gravity_is_accepted` (0.001, 5e-324) |
| The step rate cannot be changed by the user | ✅ Pass | `test_step_rate_or_length_is_not_a_configuration_option`, `test_step_rate_cannot_be_changed_on_a_running_simulation` |
| The minimum thrust cannot be changed by the user | ✅ Pass | `test_minimum_thrust_is_not_a_configuration_option`, `test_minimum_thrust_cannot_be_changed_on_a_running_simulation` |
| Non-positive mass is rejected | ✅ Pass | `test_non_positive_mass_is_rejected` (0, −1, −5e-324), `test_smallest_positive_mass_is_accepted` |
| Maximum thrust of 0 N is accepted | ⚠️ Partial | `test_max_thrust_zero_is_accepted` ✅. The "200 steps at 50 N" part, `test_max_thrust_zero_keeps_drone_on_ground_with_zero_thrust_used`, is strict xfail until US-2/3/5/6 (IQ-1) |
| Negative maximum thrust is rejected | ✅ Pass | `test_negative_max_thrust_is_rejected` (−0.001, −5e-324), `test_smallest_positive_max_thrust_is_accepted` |
| Negative drag coefficient is rejected | ✅ Pass | `test_negative_drag_coefficient_is_rejected` (−0.1, −5e-324) |
| Drag coefficient below 200 × mass is accepted | ✅ Pass | `test_drag_coefficient_below_200_times_mass_is_accepted` (0, 199.999, next double below 200), `test_drag_just_below_limit_is_accepted_for_mass_2_5` |
| Drag coefficient of 200 × mass or more is rejected with a clear error | ✅ Pass | `test_drag_coefficient_at_or_above_limit_is_rejected_with_clear_error` (200, next double above 200, 200.001, m 2.5 / b 500) |
| Valid initial altitude and velocity combinations are accepted | ✅ Pass | `test_valid_initial_altitude_and_velocity_are_accepted` (also h0 0 / v0 −0.0, h0 5e-324 / v0 −5) |
| Starting below the ground is rejected with a clear error | ✅ Pass | `test_starting_below_ground_is_rejected_with_clear_error` (−0.001, −10, −5e-324) |
| Starting on the ground while moving down is rejected with a clear error | ✅ Pass | `test_starting_on_ground_moving_down_is_rejected_with_clear_error` (−0.001, −5e-324) |
| Non-finite parameters are rejected | ✅ Pass | `test_non_finite_parameter_is_rejected` (all 6 fields × NaN, +Inf, −Inf) |

### Predicates / Invariants Matched

| Entity/Predicate | Invariant / Boundary / Concurrency Rule | Verified By |
|---|---|---|
| Constants | `STEP_RATE_HZ == 200` (int), `DT == 0.005`, `MIN_THRUST == 0.0`, `DEFAULT_GRAVITY == 9.81`; not configurable | `test_module_constants_have_specified_values`, the "not a configuration option" tests |
| `SimConfig` fields | Every field is a finite `float`; `int` is converted; `bool`, `None` and `str` are rejected with `TypeError` naming the field | `test_integer_inputs_are_stored_as_floats`, `test_non_finite_parameter_is_rejected`, `test_non_number_parameter_is_rejected` |
| `SimConfig.mass`, `max_thrust` | Required, no defaults | `test_mass_and_max_thrust_are_required` |
| `SimConfig.drag_coeff` | `drag_coeff < 200.0 * mass`; the message states the limit and "unstable" | Drag limit tests at L, L ± one double |
| `SimConfig` start state | `not (initial_altitude == 0 and initial_velocity < 0)`; `-0.0` counts as at rest | Ground-rule tests, `(0.0, -0.0)` accepted case |
| `SimConfig` | Immutable after construction | `test_configuration_cannot_be_changed_after_creation` |
| `Simulation` | `held_thrust` starts at 0 N; `step_rate_hz` / `step_length` / `min_thrust` are read-only | Defaults test, read-only property tests |
| `Simulation` concurrency | Not thread-safe, no locking (documented in the module docstring); no global mutable state | Inspection |
| Test strength | 18 planted bugs (boundary flips, removed checks, wrong defaults, unfrozen config), each run against the full suite | 18/18 caught (scratch mutation script, not committed) |

### Open Questions Raised This Pass

| ID | Question | Status | Resolution |
|---|---|---|---|
| IQ-1 | The US-1 scenario "Maximum thrust of 0 N is accepted" ends with a 200-step run, which needs stepping, capping and records from US-2/3/5/6. Keep it in US-1 as a strict xfail, build a minimal step now, or move it to US-3? | Resolved | "IQ-1 a": keep the test in US-1 as strict xfail, and remove the marker once US-2/3/5/6 land |

### Deviations From Approved DESIGN/ARCHITECTURE

- The second half of the US-1 "Maximum thrust of 0 N is accepted" scenario is not yet passing. It is a strict xfail until stepping and records exist. Caused by IQ-1: "IQ-1 a".
- `Simulation(config)` does not yet write the time-0 record that ARCHITECTURE.md describes. That belongs to US-6 and will be added in that pass. No US-1 AC depends on it.

### Process Notes

- After the green phase, a mutation run found one weak test: `mass >= 0` survived, because the drag-limit message also contains "mass". With operator approval, the mass-rejection test now also requires "greater than 0". The tests were otherwise unchanged in green, and the production code was not changed for this.
- In this pass, the tests were committed together with the code, so git history cannot show that they were unchanged in green. From US-2 onward, tests are committed at the end of the red phase, before any production code (operator instruction).

### Version Control Actions

- Branch: `feature/us1-configure-simulation`
- Commits:
  - `f0d5a92` docs(approval): move round 1 architecture approval to history
  - `d4a2350` test(config): add US-1 configuration acceptance tests
  - `4ae69f8` feat(config): add validated SimConfig and Simulation basics
  - docs(implementation): log the US-1 implementation pass (this entry, the signed approval entry and LEARNING.md)
- PR: opened against `main` after this commit, merged with a merge commit (operator instruction)
