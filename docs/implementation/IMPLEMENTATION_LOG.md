# Implementation Log

Append one entry per implementation pass (one story per pass), **most recent first**. Never edit or delete a previous pass's entry — this file is a traceable history, not a living document.

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
