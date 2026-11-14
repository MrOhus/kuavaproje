# Implementation Log

Append one entry per implementation pass (one story per pass), **most recent first**. Never edit or delete a previous pass's entry — this file is a traceable history, not a living document.

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
