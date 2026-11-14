# Architecture Session — split from ARCHITECTURE.md at commit `3dbd8e9`

> Linked from [ARCHITECTURE.md](ARCHITECTURE.md). This file holds solution-architect output produced in a single working session that would otherwise have made the central atlas too large. It is a **permanent linked record** — once a commit/PR lands for this session, its atlas row simply changes from `Active` to `Merged`/`Closed`; this file is never folded back into `ARCHITECTURE.md`.

**Input:** [DESIGN_0bfd04e.md](../design/DESIGN_0bfd04e.md), Round 2 (US-7 … US-11, OQ-26 … OQ-33), approved by Ohus on 14.11.2026 (APPROVAL_LOG History: "Requirement Analysis — Round 2 PID altitude controller").
**Builds on:** the approved Round 1 architecture in [ARCHITECTURE.md](ARCHITECTURE.md) (D-1 … D-7 still hold: standard library only at runtime, plain floats, records as the single source of truth, built-in error types, python-control test-only).

## Summary

- The controller lives inside `Simulation`, with five new methods (AQ-7). There's no new runtime dependency.
- Each controlled step updates the integral first, then computes `T_cmd = ((m·g + Kp·e) + I) − Kd·v` and hands it to the unchanged Round 1 step as the held command (AQ-9). At the setpoint and at rest this is exactly `m·g`, so hovering under control is bit-exact, like Round 1 hover.
- Metrics are computed in pure Python with the same algorithm as python-control 0.10.2's `step_info`, operation for operation, so the same-signal comparison (OQ-26 a) matches exactly, not just within 2 % (AQ-8).
- Records keep their six Round 1 fields. Setpoint changes are kept in a separate list (AQ-14).
- Prototype check (scratch, not committed): for the US-11 example, our metrics against python-control's continuous closed-loop model differ by at most 0.6 % (rise time 0 %, overshoot 0.6 %, settling time 0 %, steady-state value 0.002 %). A downward step, a briefly saturated stiff tuning (1.45 %) and a lightly damped tuning (1.28 %) also stayed within 2 %.

## Facts used from python-control 0.10.2 `step_info` (time-series input)

Read from the installed source:
- The final value `InfValue` is the last sample (no `final_output` given); `sgn = sign(InfValue)`.
- Rise time = `T[first i with sgn·(y_i − 0.9·Inf) ≥ 0] − T[first i with sgn·(y_i − 0.1·Inf) ≥ 0]`, using sample times with no interpolation.
- Settling time = `T[last i with |y_i/Inf − 1| ≥ 0.02, plus 1]`, or `T[0]` if no sample is outside the band.
- Overshoot = `|100·(max(sgn·y) − |Inf|)/Inf|` if positive, otherwise `0`.
- Everything is `NaN` only if `Inf` is `NaN` or infinite. With `Inf = 0` it returns rise time 0, overshoot 0, and a settling time computed from `y/0`, which is meaningless (this matters for AQ-10).

## Data Models

### Constants (module level)
Traces to: US-10, US-11

| Name | Type | Unit | Value |
|---|---|---|---|
| `RISE_LIMITS` | `tuple[float, float]` | — (fraction of final value) | `(0.1, 0.9)` |
| `SETTLING_BAND` | `float` | — (fraction of final value) | `0.02` |

**Invariants:** they equal python-control's `step_info` defaults and are never configurable in Round 2.

### Entity: Controller state (inside `Simulation`)
Traces to: US-7, US-8, US-9

| Field | Type | Unit | Constraints |
|---|---|---|---|
| `_ctrl_on` | `bool` | — | starts `False` |
| `_kp` | `float` | N/m | finite, `≥ 0`; meaningful only while on |
| `_ki` | `float` | N/(m·s) | finite, `≥ 0` |
| `_kd` | `float` | N·s/m | finite, `≥ 0` |
| `_setpoint` | `float` | m | finite, `≥ 0`; no upper limit |
| `_integral` | `float` | N | the integral contribution `I`; set to `0.0` when the controller is turned on (AQ-13) |
| `_changes` | `list[tuple[int, float]]` | (record index, m) | one entry per setpoint change, in order; record indices never decrease |

A read-only snapshot is available as `Simulation.controller`. It is a `ControllerStatus` named tuple `(on, kp, ki, kd, setpoint, integral)`; while off, the gains and setpoint are `NaN`.

**Invariants:**
- While on, every step's held thrust command is the controller's `T_cmd` for that step; a manual command is rejected (OQ-31).
- `_changes` gains exactly one entry when the controller is turned on, and one for each accepted setpoint change to a *different* value (OQ-32, OQ-33). Gain changes never add one.
- Each operation checks all of its arguments before changing anything, as in Round 1. A rejected call leaves the gains, setpoint, integral, changes, records and held thrust unchanged.
- No anti-windup: `_integral` is never clamped or reset while on (scope).

**Boundary Behavior:**
- Min/Max: gains and setpoint at `0` are accepted; `−5e-324` (the next double below 0) is rejected with `ValueError` naming the setting and "must not be below 0"; no upper limit. A setpoint of `0` asks the drone to sit on the ground.
- Empty/Null/Zero: `enable_controller` without a setpoint raises `TypeError` naming `setpoint` (all four arguments are required keywords). `set_gains()` with no gain given raises `TypeError`. `None`, `bool` and non-numbers are rejected as in Round 1.
- Overflow: over very long saturated runs `_integral` can grow without limit (no anti-windup). It stays finite for any realistic run; `inf`/`nan` from extreme settings is noted for a later stage, as in Round 1.

**Concurrency / Race-Scenario Analysis:**
- Same as Round 1: not thread-safe, no locking; drive one instance from a single thread. A setting change between two steps takes effect from the next step, because each step reads the settings once at its start. A step can never see a mix of old and new values, since nothing changes them during a step.

### Entity: StepMetrics
Traces to: US-10, US-11

A read-only `NamedTuple`, recomputed every time `step_metrics()` is called (OQ-29).

| Field | Type | Unit | Constraints |
|---|---|---|---|
| `change_index` | `int` | record index | `k`, the record at which the setpoint changed |
| `change_time` | `float` | s | `k / 200` |
| `start_altitude` | `float` | m | `h_k` |
| `setpoint` | `float` | m | the new setpoint |
| `samples` | `int` | — | number of records in the window, `≥ 1` |
| `rise_time` | `float` | s | `≥ 0`, or `NaN` |
| `overshoot` | `float` | % | `≥ 0`, or `NaN` |
| `settling_time` | `float` | s | `≥ 0`, or `NaN` |
| `steady_state_value` | `float` | m | `y_end = h_end − h_k` |
| `steady_state_error` | `float` | m | `setpoint − h_end`, signed |

**Window:** for change `j` at record `k_j`, records `k_j … k_{j+1}` (both included), or `k_j …` the latest record for the last change. The signal is `y_i = h_i − h_k`, and its times are `(i − k)/200` (exact, from integer indices).

**Invariants:**
- `rise_time`, `overshoot` and `settling_time` are computed with the same operations, in the same order, as `step_info`. The same-signal comparison (OQ-26 a) is therefore equal, not just within 2 %, except for the degenerate windows in AQ-10.
- `steady_state_error == setpoint − (start_altitude + steady_state_value)`.
- `step_metrics()` returns one result per entry in `_changes`, in order. Reading it changes nothing.

**Boundary Behavior:**
- Degenerate windows (a window of 1 record, or a final change of exactly `0`): see AQ-10.
- Downward steps: `sgn = −1` handles them, exactly as `step_info` does.
- Resolution: times are multiples of 0.005 s. Rise and settling times can differ from a continuous model by up to one step, so the model comparison (OQ-26 b) is only reliable when rise time ≥ 0.25 s (one step is then at most 2 %). Example scenarios are chosen with that in mind; a faster tuning is not a defect.
- Cost: each call is O(records). Over a 720,000-record run with a few changes it stays well under a second.

**Concurrency / Race-Scenario Analysis:**
- Results are computed from the live records at the moment of the call. A result read later reflects later records, as OQ-29 intends.

### Predicate: Controlled step (extends Round 1 D-3)
Traces to: US-9

Before each Round 1 step while the controller is on, with `h, v` from the last record:

```text
e   = setpoint - h
I   = I + (Ki * e) * DT                  # integral first (AQ-9)
cmd = ((m * g + Kp * e) + I) - Kd * v    # this exact grouping
held_thrust = cmd                        # then the unchanged Round 1 step caps it and advances
```

- `m * g` is the same product, with the same operands in the same order, as in D-3. At `e = 0`, `I = 0` and `v = 0` this gives `cmd == m*g` exactly, so `T − m·g` is exactly `0` and hovering at the setpoint is bit-exact.
- The US-9 formula AC: `((9.81 + 4·2) + 0) − 3·0.5 = 16.31` (within ε).
- No derivative spike: changing the setpoint changes `e` only; the D term uses `v`.

## Technology / Design Decisions

All the decisions below were decided by the operator through AQ-7 … AQ-14 ("all a", 2026-11-14). ✅ marks the chosen option.

### D-8: Where the controller lives (AQ-7)

| Option | Benefits | Drawbacks | Chosen |
|---|---|---|---|
| Inside `Simulation`: `enable_controller(*, kp, ki, kd, setpoint)`, `disable_controller()`, `set_gains(*, kp=None, ki=None, kd=None)`, `set_setpoint(value)`, `step_metrics()`, `controller` | One object owns the thrust, so "manual thrust rejected while on" is easy to enforce. Fits the Round 1 API. Fewest new types. | `Simulation` grows | ✅ |
| Separate `PIDController` attached to the simulation | The controller is reusable on its own | `step()` must still know about it in order to reject manual thrust; two objects to keep in step | ❌ |
| `ClosedLoop` wrapper that owns a `Simulation` | Clean separation | "Turning off returns Round 1 behaviour" means handing control back to the inner object; the records and changes would be split across two objects | ❌ |

**Why inside:** OQ-31 needs a single owner of the thrust. **Why not attached:** coupling without independence. **Why not a wrapper:** it splits state and makes turning off awkward.

A state conflict (manual thrust while on, or changing settings while off) raises `RuntimeError` with a message naming the state ("the controller is on"). Bad values still raise `ValueError` or `TypeError` (D-6).

### D-9: How metrics are computed (AQ-8)

| Option | Benefits | Drawbacks | Chosen |
|---|---|---|---|
| Pure-Python copy of `step_info`'s algorithm (about 30 lines), tested against python-control | No runtime dependency (D-1, D-7 still hold). Same operations, so the results are equal. | Must be kept in line with python-control (pinned `<0.11` in the dev extra) | ✅ |
| Make python-control a runtime dependency and call `step_info` | Nothing to re-implement | Pulls in numpy, scipy and matplotlib at runtime. Reverses the approved D-7. | ❌ |
| Own definitions, compared only within 2 % | Free design | Pointless differences from the reference the operator chose | ❌ |

### D-10: Order inside the controlled step (AQ-9)

| Option | Benefits | Drawbacks | Chosen |
|---|---|---|---|
| Update `I` with the current error, then use it | Standard discrete PID: the thrust reacts to the current error in all three terms. Prototype: 0.6 % from the model. | — | ✅ |
| Use the previous `I`, then update it | Also valid; prototype: 0.5 % from the model | The I term lags one step behind P | ❌ |

Both satisfy every AC, including "a Ki change affects only the future". This is a matter of convention, so it's raised as a question.

### D-11: Degenerate metric windows (AQ-10)

| Option | Benefits | Drawbacks | Chosen |
|---|---|---|---|
| If the window has 1 record or its final change is exactly `0`: `rise_time`, `overshoot`, `settling_time` = `NaN`; the steady-state value and error are still reported; such results are left out of the same-signal comparison | Honest: there is no step to measure. Follows the OQ-30 rule that "never reached" is `NaN`. | Differs from `step_info`'s raw output in this one case | ✅ |
| Return whatever the `step_info` algorithm gives | Always equal to `step_info` | Rise time 0 and overshoot 0 for a step that never happened look like a perfect response, and settling time depends on `y/0` | ❌ |

### D-12: "Within 2 %" when the reference is 0 or NaN (AQ-11)

| Option | Benefits | Drawbacks | Chosen |
|---|---|---|---|
| Reference ≠ 0: `|ours − ref| ≤ 0.02·|ref|`. Reference = 0: `|ours| ≤ 0.02` in the metric's own unit (s or %). Both `NaN`: match. Only one `NaN`: mismatch. | Simple, and never divides by 0 | The absolute 0.02 floor is a convention | ✅ |
| Reference = 0 needs ours exactly 0 | Strict | Fails on harmless discretisation effects (for example 0.001 % overshoot against 0 %) | ❌ |
| Skip the comparison whenever the reference is 0 or `NaN` | Simplest | Hides real problems | ❌ |

### D-13: The python-control model for OQ-26 (b) (AQ-12)

| Option | Benefits | Drawbacks | Chosen |
|---|---|---|---|
| Continuous closed loop `H(s) = (Kp s + Ki) / (m s³ + (b + Kd) s² + Kp s + Ki)` (feed-forward cancels gravity, PI on the error, D on the altitude), scaled by the step size and run on the same time points | It is the textbook model the requirement means. The prototype was within 0.6 % for the US-11 example. | Differences of one sample (0.005 s) in rise and settling times, so the tuning needs rise time ≥ 0.25 s | ✅ |
| Exact discrete 200 Hz model of the same loop | Matches to rounding | Essentially compares the simulation with itself; proves little about the physics | ❌ |

### D-14: Controller lifecycle (AQ-13)

| Option | Benefits | Drawbacks | Chosen |
|---|---|---|---|
| `enable_controller` only while off: sets everything, `I = 0`, adds a change. While on it raises `RuntimeError`; use `set_gains`/`set_setpoint` instead. `set_*` while off raise `RuntimeError`. `disable_controller` while on: `I` discarded, held thrust stays at the last command; while off it does nothing. | One clear way to do each thing. Turning on always starts fresh. | Turning on twice is an error, not a reset | ✅ |
| Calling `enable_controller` while on re-applies the settings (and adds a change if the setpoint differs) | Forgiving | Two ways to change settings; unclear whether `I` resets | ❌ |
| Settings may be changed while off and are remembered for the next enable | Pre-configuration | Hidden state; contradicts "turning on requires gains and a setpoint" (OQ-32) | ❌ |

### D-15: Record layout (AQ-14)

| Option | Benefits | Drawbacks | Chosen |
|---|---|---|---|
| Keep the six Round 1 record fields; setpoint changes kept in `_changes` | No change to Round 1 records or their approved tests (`Record._fields` is checked) | The setpoint at each step has to be derived from the changes | ✅ |
| Add `setpoint` (and `controller_on`) as record fields | Everything per step in one place; handy for the Round 3 plots | Changes D-5 and the US-6 tests; 8 doubles per record; `NaN` setpoints while off | ❌ |

## Open Questions

Most important first. All answered by the operator on 2026-11-14: "all a" (the recommended option each time).

| ID | Question | Raised By | Status | Resolution |
|---|---|---|---|---|
| AQ-7 | **Where does the controller live? (D-8)** (a) Inside `Simulation` with `enable_controller`, `disable_controller`, `set_gains`, `set_setpoint`, `step_metrics()` and a read-only `controller` status; state conflicts raise `RuntimeError`; (b) a separate controller object attached to the simulation; (c) a wrapper object that owns a simulation. | solution-architect | Resolved | "all a" (operator, 2026-11-14) → option (a) applied |
| AQ-8 | **How are the metrics computed? (D-9)** (a) A pure-Python copy of `step_info`'s algorithm, with no new runtime dependency, giving equal results; (b) python-control as a runtime dependency; (c) our own definitions. | solution-architect | Resolved | "all a" (operator, 2026-11-14) → option (a) applied |
| AQ-9 | **Order inside a controlled step (D-10).** (a) Update the integral with the current error first, then compute the thrust; (b) compute the thrust with the previous integral, then update it. | solution-architect | Resolved | "all a" (operator, 2026-11-14) → option (a) applied |
| AQ-10 | **Metrics when there is nothing to measure (D-11),** i.e. a window of 1 record or a final change of exactly 0. (a) Rise time, overshoot and settling time are `NaN`, the steady-state values are still given, and such results are left out of the same-signal comparison; (b) give whatever the `step_info` algorithm outputs (rise 0, overshoot 0, settling from a division by 0). | solution-architect | Resolved | "all a" (operator, 2026-11-14) → option (a) applied |
| AQ-11 | **"Within 2 %" when the reference is 0 or NaN (D-12).** (a) 2 % relative; when the reference is exactly 0, ours must be within 0.02 in the metric's own unit; both `NaN` = match; one `NaN` = mismatch; (b) a reference of 0 requires ours to be exactly 0; (c) skip those comparisons. | solution-architect | Resolved | "all a" (operator, 2026-11-14) → option (a) applied |
| AQ-12 | **Which python-control model for OQ-26 (b)? (D-13)** (a) The continuous closed loop `(Kp s + Ki)/(m s³ + (b+Kd) s² + Kp s + Ki)` on the same time points, which needs tunings with rise time ≥ 0.25 s; (b) an exact discrete 200 Hz model. | solution-architect | Resolved | "all a" (operator, 2026-11-14) → option (a) applied |
| AQ-13 | **Controller lifecycle (D-14).** (a) Turning on is allowed only while off and always starts the integral at 0; turning on again while on is an error; changing settings while off is an error; turning off discards the integral and keeps the last command as the held thrust; (b) turning on while on re-applies the settings; (c) settings can be changed while off and are remembered. | solution-architect | Resolved | "all a" (operator, 2026-11-14) → option (a) applied |
| AQ-14 | **Record layout (D-15).** (a) Records keep their six Round 1 fields; setpoint changes are a separate list; (b) add `setpoint` and `controller_on` to every record. | solution-architect | Resolved | "all a" (operator, 2026-11-14) → option (a) applied |
