# Approval Log

> Single file shared by the **entire pipeline** (`requirement-analysis`, `solution-architect`, and any future stage). Exactly **one active entry** exists at a time, regardless of which stage/skill created it, with status `Pending Approval`. Update it in place as decisions accumulate during a session — never create a second pending entry. Once a human operator explicitly sets it to `Approved` or `Rejected` and the associated commit/PR lands, move it to History below and leave the active slot empty for the next stage to use.

## Active Entry

_No active entry. The next pipeline stage (implementation, gain-slider fix) opens a new `Pending Approval` entry here._

---

## History

<!-- Move closed (Approved/Rejected) entries here, most recent first, once their commit/PR has landed. Keep the Stage field so it's clear which pipeline phase each entry belonged to. -->

### Implementation — US-12 … US-19 live GUI, wind gust, pause and reset (Round 3) (Approved 14.11.2026)

- **Status**: Approved
- **Stage**: Implementation
- **Session Started**: 2026-11-14
- **Related Doc(s)**: docs/implementation/IMPLEMENTATION_LOG.md (eight passes 2026-11-14, US-12 to US-19). Input: docs/design/DESIGN_f351eee.md (approved 14.11.2026), docs/architecture/ARCHITECTURE_899eaea.md (approved 14.11.2026)
- **Requested By**: Human operator (Ohus)
- **Landed In**: PRs #19 … #26 (`feature/us12-live-app` … `feature/us19-readme-commands`), merge commits `32e510f`, `faf6f7e`, `b099fa9`, `2a5ae4f`, `7499561`, `950263b`, `e9ebce2`, `3532cfb` on `main`
- **Decisions / Scope Covered**:
  - US-12 live app, real-time pacing, start command and startup messages (`844f48f` red, `a01cdbf` code).
  - US-13 sliders (`6d24095` red, `ef98da2` operator-approved test-setup fix, `7d08521` code).
  - US-14 live plots and the frame-rate check (`9ae2413` red, `9414b2b` code); measured 53.8 fps on average.
  - US-15 metrics table with `last_step_metrics()` (`414e5a0` red, `20ab8d1` code).
  - US-16 wind gust in the core (`1af3b69` red, `7fe36cf` code).
  - US-17 pause, resume and reset (`49b5a67` red, `15a3e33` code).
  - US-18 plain red error messages, no traceback anywhere (`c07a581` red, `a86e63d` code).
  - US-19 README, `python -m kuava_sim`, `python -m pytest` with skip reasons (`0815273` red, `70cd2f4` docs).
  - Red tests committed before code for every story; `git diff` of the tests between each red commit and its code commit is empty. The only test change after a red commit is the approved US-13 setup fix.
  - Small coding details decided under standing rule 3 are listed in each pass.
  - Full suite: 472 passed, 0 xfailed. Branches stacked `feature/us12-live-app` to `feature/us19-readme-commands`.
- **Open Questions Resolved This Session**: none raised (no question changed what the app does or looks like)
- **Approved By**: Ohus
- **Approval Date**: 14.11.2026

### Solution Architecture — Round 3 live GUI, wind gust, pause and reset (Approved 14.11.2026)

- **Status**: Approved
- **Stage**: Solution Architecture
- **Session Started**: 2026-11-14
- **Related Doc(s)**: docs/architecture/ARCHITECTURE_899eaea.md (linked from docs/architecture/ARCHITECTURE.md). Input: docs/design/DESIGN_f351eee.md (History entry "Requirement Analysis — Round 3 live GUI, wind gust, pause and reset", Approved 14.11.2026)
- **Requested By**: Human operator (Ohus)
- **Landed In**: PR #18 (`docs/round3-gui-architecture`), merge commit `6069d65` on `main`
- **Decisions / Scope Covered**:
  - Models: gust constant and state in `Simulation` with the step-with-gust predicate; `last_step_metrics()`; `LiveSession` (no Tk, fake clock) with the real-time pacing predicate; the Tk `App`; startup in `__main__.py`; GUI tests. Each with types and units, invariants, boundary behavior and concurrency analysis.
  - Decisions D-16 … D-23, decided by the operator through AQ-15 … AQ-22 (answers in the operator's own words).
  - All six items deferred by requirement analysis are covered: D-16 technology, D-17 thread and catch-up limit (50 steps), D-18 core/session/window split, D-19 and D-20 gust API and records, D-22 GUI and frame-rate tests.
  - Coding details decided by the architect under standing rule 3 and recorded: frame interval 16 ms, scheduled adaptively; one plotted point per 4 steps; refresh after max(0.5 s, 20 × last recompute time); `last_step_metrics()`.
  - Small UI details approved by the operator: a key release on the setpoint slider counts as letting go; display rounding; axis scaling.
  - Prototype (scratch): Tk canvas 65 fps; matplotlib full redraw 19 fps; `step_metrics()` 30 ms at 120k records, 201 ms at 720k.
- **Open Questions Resolved This Session**:
  - AQ-15 — "Tkinter. It comes with Python and it was the only one fast enough (65 fps)." → D-16.
  - AQ-16 — "Keep everything in one thread. If the PC lags, catch up a quarter second at most and skip the rest." → D-17.
  - AQ-17 — "Keep pause, reset and sliders separate from the window so they can be tested without one. Reset starts a new simulation." → D-18.
  - AQ-18 — "Just one simple gust button function, nothing extra." → D-19.
  - AQ-19 — "Keep the 6 numbers. The gust already shows in the acceleration." → D-20.
  - AQ-20 — "Only update the newest row, every half second or slower so the app stays fast." → D-21.
  - AQ-21 — "If there's no screen, skip the window tests and say why." → D-22.
  - AQ-22 — "Show a short red message in the window and pause. No popups. Don't print the full error anywhere." (The first answer, which kept the full error in the terminal, conflicted with OQ-41 and was replaced.) → D-23.
- **Approved By**: Ohus
- **Approval Date**: 14.11.2026

### Requirement Analysis — Round 3 live GUI, wind gust, pause and reset (Approved 14.11.2026)

- **Status**: Approved
- **Stage**: Requirement Analysis
- **Session Started**: 2026-11-14
- **Related Doc(s)**: docs/design/DESIGN_f351eee.md (linked from docs/design/DESIGN.md)
- **Requested By**: Human operator (Ohus)
- **Landed In**: PR #17 (`docs/round3-gui-requirements`), merge commit `899eaea` on `main`
- **Decisions / Scope Covered**:
  - Round 3 scope: simple desktop GUI running the simulation live with the PID controller; sliders for Kp, Ki, Kd and the setpoint; live plots of setpoint, altitude and controller output above 30 fps; metrics after each setpoint change; wind gust button; pause and reset; README with setup and metric definitions; one start command and one test command; clear error messages instead of crashes.
  - Out of scope: all bonus items, and everything out of scope in Rounds 1 and 2 unless named above.
  - US-12 … US-19 written with full Gherkin ACs (happy and rejection paths); no BLOCKED scenarios remain.
  - Deferred to solution-architect (listed in DESIGN_f351eee.md): GUI and plotting technology, how the GUI drives the simulation, the split of gust/pause/reset between core and GUI, when the app counts as behind (most steps per frame), how the frame rate is measured in tests, whether and how the gust appears in the records and the core API.
- **Open Questions Resolved This Session**:
  - OQ-34 — Real time; whole 200 Hz steps per frame; when behind, drop the missed time instead of jumping ahead (option a).
  - OQ-35 — One gust button: 5 N downward for 0.5 s (100 steps); a press during a gust restarts it; part of the simulation core (option a).
  - OQ-36 — Slider ranges Kp 0–50, Ki 0–20, Kd 0–20, setpoint 0–100 m, step 0.1, start 4/1/3/10 m; fixed drone 1 kg, drag 0.5, max 30 N, from the ground; controller always on; setpoint applies on release only (option a).
  - OQ-37 — Pause/Resume button; sliders work while paused; gust disabled while paused; reset to time 0 keeps the slider values and the pause state (option a).
  - OQ-38 — Two plots, last 20 s scrolling: altitude and setpoint; thrust actually used with 0 N and 30 N limits; all records kept, reset clears them (option a).
  - OQ-39 — Metrics table, one row per setpoint change, newest on top, newest row live, NaN shown as "not reached" (option a).
  - OQ-40 — Frame rate shown in the window; automated 5 s test on the average (> 30 fps); one slow frame does not fail it (option a).
  - OQ-41 — Plain error messages in the window, simulation pauses, app stays open; startup problems one plain line, exit code 1; commands pip install -e ".[dev]", python -m kuava_sim, python -m pytest (option a).
- **Approved By**: Ohus
- **Approval Date**: 14.11.2026

### Implementation — US-7 … US-11 PID controller and step-response metrics (Round 2) (Approved 14.11.2026)

- **Status**: Approved
- **Stage**: Implementation
- **Session Started**: 2026-11-14
- **Related Doc(s)**: docs/implementation/IMPLEMENTATION_LOG.md (five passes 2026-11-14, US-7 to US-11). Input: docs/design/DESIGN_0bfd04e.md (US-7 to US-11, approved 14.11.2026), docs/architecture/ARCHITECTURE_3dbd8e9.md (approved 14.11.2026)
- **Requested By**: Human operator (Ohus)
- **Landed In**: PR #12 (`feature/us7-pid-controller-on`, merge commit `50ef106`), PR #13 (`feature/us8-change-gains-setpoint`, `dc45189`), PR #14 (`feature/us9-closed-loop-thrust`, `e1d36f0`), PR #15 (`feature/us10-step-metrics`, `a77fbcf`) and PR #16 (`feature/us11-python-control-match`, `f351eee`) on `main`
- **Decisions / Scope Covered**:
  - US-7 controller on/off with `ControllerStatus`; manual thrust rejected while on (`99ff794` red, `8bb54cb` code).
  - US-8 `set_gains` and `set_setpoint` (`23dacb6` red, `514a97a` code).
  - US-9 closed-loop PID thrust step, integral first, bit-exact hover at the setpoint, no anti-windup (`22f29ed` red, `f6e77b2` code).
  - US-10 `step_metrics()` with a pure-Python copy of python-control's `step_info` algorithm (`1c90dce` red, `5c5ded1` operator-approved test fix, `7b1acb5` code).
  - US-11 comparison with python-control: same signal equal, closed-loop model within 2 % where it applies; no product code needed, 5 of 5 planted faults caught (`70450f0`).
  - Red tests committed before code for every story; `git diff` of the tests between each red commit and its code commit is empty, except US-10 (the approved one-line format fix).
  - Full suite: 366 passed, 0 xfailed. Branches stacked `feature/us7-pid-controller-on` to `feature/us11-python-control-match`. Done while the operator was away; signed by the operator afterwards.
- **Open Questions Resolved This Session**:
  - IQ-9 — Scenarios that need a later story stay in their own story as strict xfail; the marker is removed in the red commit of the completing story (option a).
  - IQ-10 — Five stacked branches, one History move on the first, one shared Pending entry, all docs in one commit on the last branch (option a).
  - IQ-11 — US-11 needs no product code: tests committed, falsifiability shown with planted faults (option a).
- **Approved By**: Ohus
- **Approval Date**: 14.11.2026

### Solution Architecture — Round 2 PID altitude controller (Approved 14.11.2026)

- **Status**: Approved
- **Stage**: Solution Architecture
- **Session Started**: 2026-11-14
- **Related Doc(s)**: docs/architecture/ARCHITECTURE_3dbd8e9.md (linked from docs/architecture/ARCHITECTURE.md). Input: docs/design/DESIGN_0bfd04e.md (History entry "Requirement Analysis — Round 2 PID altitude controller", Approved 14.11.2026)
- **Requested By**: Human operator (Ohus)
- **Landed In**: PR #11 (`docs/round2-pid-controller-architecture`), merge commit `9e9653b` on `main`
- **Decisions / Scope Covered**:
  - Models: metric constants, controller state inside `Simulation`, `StepMetrics`, and the controlled-step predicate (integral first, `cmd = ((m*g + Kp*e) + I) - Kd*v`, bit-exact hover at the setpoint), each with types and units, invariants, boundary behavior and concurrency analysis.
  - Decisions D-8 … D-15 (API placement, metrics implementation, step order, degenerate windows, 2 % rule for 0/NaN, reference model, lifecycle, record layout), decided by the operator through AQ-7 … AQ-14.
  - The five items deferred by requirement analysis are covered by D-10, D-11, D-12, D-13 and D-14.
  - Prototype (scratch): our metrics against python-control's continuous closed-loop model within 0.6 % for the US-11 example; all four tried tunings within 2 %.
- **Open Questions Resolved This Session**:
  - AQ-7 — Controller inside `Simulation` with enable/disable/set_gains/set_setpoint/step_metrics and a read-only status; state conflicts raise `RuntimeError` (option a) → D-8.
  - AQ-8 — Pure-Python copy of `step_info`'s algorithm, no new runtime dependency (option a) → D-9.
  - AQ-9 — Integral updated with the current error first, then the thrust computed (option a) → D-10.
  - AQ-10 — Degenerate windows give NaN rise/overshoot/settling, steady-state values still reported, excluded from the same-signal check (option a) → D-11.
  - AQ-11 — 2 % relative; reference 0 allows ±0.02 in the metric's unit; both NaN = match (option a) → D-12.
  - AQ-12 — Continuous closed-loop python-control model on the same time points; tunings with rise time ≥ 0.25 s (option a) → D-13.
  - AQ-13 — Turn on only while off (integral 0); turning on again or changing settings while off is an error; turning off keeps the last command (option a) → D-14.
  - AQ-14 — Records keep six fields; setpoint changes in a separate list (option a) → D-15.
- **Approved By**: Ohus
- **Approval Date**: 14.11.2026

### Requirement Analysis — Round 2 PID altitude controller (Approved 14.11.2026)

- **Status**: Approved
- **Stage**: Requirement Analysis
- **Session Started**: 2026-11-14
- **Related Doc(s)**: docs/design/DESIGN_0bfd04e.md (linked from docs/design/DESIGN.md)
- **Requested By**: Human operator (Ohus)
- **Landed In**: PR #10 (`docs/round2-pid-controller-requirements`), merge commit `3dbd8e9` on `main`
- **Decisions / Scope Covered**:
  - Round 2 scope: PID controller with Kp, Ki, Kd and setpoint changeable while running; rise time, overshoot (%), settling time and steady-state error after every setpoint change; match with python-control `step_info` within 2 %.
  - Out of scope: GUI, plots, wind/disturbances, pause and reset, anti-windup, sensor noise (wind, pause, reset and plots planned for Round 3 with the GUI).
  - US-7 … US-11 written with full Gherkin ACs (happy and rejection paths); no BLOCKED scenarios remain.
  - Five items deferred to solution-architect (listed in DESIGN_0bfd04e.md): exact discrete controller step, zero-size step metrics, "within 2 %" when the reference is 0 or NaN, continuous model vs the 200 Hz simulation, turning on while already on.
- **Open Questions Resolved This Session**:
  - OQ-26 — Compare with step_info on the same signal always, and with a python-control closed-loop model where no thrust limit is hit and the ground is not touched (option c).
  - OQ-27 — Thrust = m·g feed-forward + PID output, then capped (option a).
  - OQ-28 — Every step; derivative on altitude (−Kd·v); integral accumulates Ki·e·dt (option a).
  - OQ-29 — A result covers its change up to the next change, readable at any time, last sample as the final value (option a).
  - OQ-30 — step_info definitions on altitude relative to the change; steady-state error = setpoint − final altitude; never reached = NaN (option a).
  - OQ-31 — Controller optional; manual thrust rejected while on; turning off returns Round 1 behaviour (option a).
  - OQ-32 — Turning on requires a setpoint and counts as the first setpoint change (option a).
  - OQ-33 — Gains ≥ 0, setpoint ≥ 0 m, no upper limit; a repeat setpoint does nothing; gain changes never start new metrics (option a).
- **Approved By**: Ohus
- **Approval Date**: 14.11.2026

### Implementation — US-4 Deterministic runs and US-5 Open-loop thrust input (Approved 14.11.2026)

- **Status**: Approved
- **Stage**: Implementation
- **Session Started**: 2026-11-14
- **Related Doc(s)**: docs/implementation/IMPLEMENTATION_LOG.md (passes 2026-11-14, US-4 and US-5). Input: docs/design/DESIGN.md (US-4, US-5, approved 13.11.2026), docs/architecture/ARCHITECTURE.md (approved 14.11.2026)
- **Requested By**: Human operator (Ohus)
- **Landed In**: PR #8 (`feature/us4-deterministic-runs`, merge commit `05cf2db`) and PR #9 (`feature/us5-open-loop-thrust`, merge commit `0bfd04e`) on `main`
- **Decisions / Scope Covered**:
  - US-4 covered by acceptance tests (`fca3b74`, branch `feature/us4-deterministic-runs`). No production code was needed; determinism already follows from US-2/3/6. 4 of 4 planted faults caught in scratch copies.
  - US-5 covered by acceptance tests (`9ae263c`, branch `feature/us5-open-loop-thrust`, stacked on the US-4 branch). No production code was needed; holding, capping and rejecting commands already exist. 5 of 5 planted faults caught.
  - Full suite: 228 passed. `git diff main -- src/` is empty on both branches.
  - One entry covers both stories because US-4 could not be signed before US-5 started (IQ-8). Done while the operator was away. Nothing signed, pushed or merged.
- **Open Questions Resolved This Session**:
  - IQ-4 — No red phase possible: tests committed, falsifiability shown with planted faults, no code commit (option a).
  - IQ-5 — Separate-process test runs the scenario script twice with different hash seeds and compares full record bytes from the public API (option a).
  - IQ-6 — Host load is 300 steps with 5 ms pauses plus a busy background thread (option a).
  - IQ-7 — Every record from step 500 on must differ, with a sequence that keeps the drone airborne (option a).
  - IQ-8 — US-5 stacked on the US-4 branch, one shared Pending entry, docs uncommitted until sign-off (option a).
- **Approved By**: Ohus
- **Approval Date**: 14.11.2026

### Implementation — US-6 Output records (Approved 14.11.2026)

- **Status**: Approved
- **Stage**: Implementation
- **Session Started**: 2026-11-14
- **Related Doc(s)**: docs/implementation/IMPLEMENTATION_LOG.md (pass 2026-11-14, US-6). Input: docs/design/DESIGN.md (US-6, approved 13.11.2026), docs/architecture/ARCHITECTURE.md (approved 14.11.2026)
- **Requested By**: Human operator (Ohus)
- **Landed In**: PR #7 (`feature/us6-output-records`), merge commit `b318805` on `main`
- **Decisions / Scope Covered**:
  - US-6 implemented: `Record` named tuple; records in one flat `array('d')`, 6 doubles per record (D-5); read-only `records` view with `column()`; time-0 record (I-3); floor and rest records with zero acceleration and drag (I-2); `step()` returns the new `Record`; state read from the last record.
  - Red tests committed before code (`cccecfd`), together with removing the 12 strict xfail markers from US-1/2/3. 180 passed, 0 xfailed. No planted-bug check (operator instruction).
  - Story order changed to US-6 before US-4 and US-5 (IQ-3).
- **Open Questions Resolved This Session**:
  - IQ-3 — US-6 next, because it turns the 12 expected failures into real checks and lets US-4 compare records directly.
- **Approved By**: Ohus
- **Approval Date**: 14.11.2026

### Implementation — US-3 Compute vertical dynamics from gravity, thrust and drag (Approved 14.11.2026)

- **Status**: Approved
- **Stage**: Implementation
- **Session Started**: 2026-11-14
- **Related Doc(s)**: docs/implementation/IMPLEMENTATION_LOG.md (pass 2026-11-14, US-3). Input: docs/design/DESIGN.md (US-3, approved 13.11.2026), docs/architecture/ARCHITECTURE.md (approved 14.11.2026)
- **Requested By**: Human operator (Ohus)
- **Landed In**: PR #6 (`feature/us3-vertical-dynamics`), merge commit `2c38ff7` on `main`
- **Decisions / Scope Covered**:
  - US-3 implemented: D-3 step formulation (semi-implicit Euler, linear drag from the start velocity), silent thrust capping to [0, max_thrust] at use time, thrust command checks before any change, D-4 floor (`hn <= 0 and vn < 0`).
  - Red tests committed before code (`1f5fad7`). 142 passed, 12 strict xfail (IQ-1, IQ-2, and 7 US-3 record-field tests waiting for US-6). No planted-bug check (operator instruction).
  - Interim until US-6: no records yet, so record fields are not checked.
- **Open Questions Resolved This Session**: none raised
- **Approved By**: Ohus
- **Approval Date**: 14.11.2026

### Implementation — US-2 Advance the simulation in fixed time steps (Approved 14.11.2026)

- **Status**: Approved
- **Stage**: Implementation
- **Session Started**: 2026-11-14
- **Related Doc(s)**: docs/implementation/IMPLEMENTATION_LOG.md (pass 2026-11-14, US-2). Input: docs/design/DESIGN.md (US-2, approved 13.11.2026), docs/architecture/ARCHITECTURE.md (approved 14.11.2026)
- **Requested By**: Human operator (Ohus)
- **Landed In**: PR #5 (`feature/us2-fixed-time-steps`), merge commit `615d5d4` on `main`
- **Decisions / Scope Covered**:
  - US-2 implemented: `step(thrust=None)`, `run(n, thrust=None)`, `step_count`, drift-free `time = step_count / 200`, N checks before any change, `run(0)` a pure no-op, no step-length option, no wall-clock use.
  - Red tests committed before code (`7583605`). 105 passed, 5 strict xfail (IQ-1, IQ-2). No planted-bug check (operator instruction).
  - Interim until US-3/US-6 (IQ-2): altitude and velocity stay at their start values, and there are no records yet.
- **Open Questions Resolved This Session**:
  - IQ-2 — US-2 implements only its own part; the record comparisons are strict xfail until US-6; dynamics come in US-3 (option a).
- **Approved By**: Ohus
- **Approval Date**: 14.11.2026

### Implementation — US-1 Configure the simulation (Approved 14.11.2026)

- **Status**: Approved
- **Stage**: Implementation
- **Session Started**: 2026-11-14
- **Related Doc(s)**: docs/implementation/IMPLEMENTATION_LOG.md (pass 2026-11-14, US-1). Input: docs/design/DESIGN.md (US-1, approved 13.11.2026), docs/architecture/ARCHITECTURE.md (approved 14.11.2026)
- **Requested By**: Human operator (Ohus)
- **Landed In**: PR #4 (`feature/us1-configure-simulation`), merge commit `15cac03` on `main`
- **Decisions / Scope Covered**:
  - US-1 implemented: constants, validated immutable `SimConfig`, `Simulation` construction with read-only step rate, step length, minimum thrust and held thrust.
  - 86 acceptance tests pass, 1 strict xfail (IQ-1). 18 of 18 planted bugs caught.
  - Project scaffolding: `pyproject.toml` (requires-python >= 3.12, dev extra: pytest, control).
- **Open Questions Resolved This Session**:
  - IQ-1 — The 200-step part of "Maximum thrust of 0 N is accepted" stays in US-1 as a strict xfail until US-2/3/5/6 land (option a).
- **Approved By**: Ohus
- **Approval Date**: 14.11.2026

### Solution Architecture — Round 1 altitude simulation (Approved 14.11.2026)

- **Status**: Approved
- **Stage**: Solution Architecture
- **Session Started**: 2026-11-14
- **Related Doc(s)**: docs/architecture/ARCHITECTURE.md. Input: docs/design/DESIGN.md (History entry "Requirement Analysis — Round 1 altitude simulation", Approved 13.11.2026)
- **Requested By**: Human operator (Ohus)
- **Landed In**: PR #3 (`docs/round1-altitude-sim-architecture`), merge commit `ecb127c` on `main`
- **Decisions / Scope Covered**:
  - Entities: constants (`STEP_RATE_HZ`, `DT`, `MIN_THRUST`, `DEFAULT_GRAVITY`), `SimConfig` (frozen, validated), `Record`, `RecordLog` (flat `array('d')`), `Simulation` (`step(thrust=None)`, `run(n, thrust=None)`), each with types and units, invariants, boundary behavior and concurrency analysis.
  - D-1 CPython `>= 3.12`, developed on 3.15.2; standard library only at runtime.
  - D-2 Python `float` scalar loop (no NumPy at runtime) for bit-exact determinism.
  - D-3 (deferred item) Exact formulation: `D = -(b*v)`, `a = ((T - m*g) + D) / m`, `vn = v + a*DT`, `hn = h + vn*DT`, `time = n / 200`. Hover is bit-exact when thrust is passed as `m*g`.
  - D-4 (deferred item) Floor condition: `hn <= 0 and vn < 0`. Every record satisfies "altitude 0 ⇒ velocity ≥ 0".
  - D-5 Records stored as 6 doubles per record in one array; read-only `Sequence[Record]` view plus `column()`.
  - D-6 Built-in `ValueError`/`TypeError` with messages naming the parameter; command and step happen in one call.
  - D-7 pytest + python-control 0.10.x as a dev-only extra; exact discrete-time state-space cross-check plus continuous plant `1/(s(ms+b))` for metrics.
  - Noted for a later stage: overflow with extreme configurations, thread-safety for the GUI, external real-time pacing.
  - D-1, D-2, D-4, D-5, D-6, D-7 were decided by the operator through AQ-1 … AQ-6 (all recommended options). D-3 is the architect's decision on the deferred formulation item.
- **Open Questions Resolved This Session**:
  - AQ-1 — Ground stops the drone when the new height is ≤ 0 and it is moving down (option b) → D-4.
  - AQ-2 — Python 3.12 or newer, developed on 3.15.2 (option a) → D-1.
  - AQ-3 — pytest; python-control installed only for testing (option a) → D-7.
  - AQ-4 — Normal Python float numbers, no NumPy at runtime (option a) → D-2.
  - AQ-5 — Records in one compact array, 6 numbers per record (option a) → D-5.
  - AQ-6 — `step(thrust)` / `run(n, thrust)` with built-in error types naming the setting (option a) → D-6.
- **Approved By**: Ohus
- **Approval Date**: 14.11.2026

### Requirement Analysis — Round 1 altitude simulation (Approved 13.11.2026)

- **Status**: Approved
- **Stage**: Requirement Analysis
- **Session Started**: 2026-11-13
- **Related Doc(s)**: docs/design/DESIGN.md
- **Requested By**: Human operator (Ohus)
- **Landed In**: PR #1 (`docs/round1-altitude-sim-requirements`), merge commit `5007652` on `main`
- **Decisions / Scope Covered**:
  - Round 1 scope limited to: fixed-time-step, 1-D altitude simulation of a drone with gravity, mass, thrust limits and drag; step rate ≥ 200 Hz; fully deterministic; no controller. Everything else explicitly out of scope (listed in DESIGN.md).
  - US-1 Configure the simulation: mass > 0; gravity configurable (default 9.81 m/s²); max thrust configurable and ≥ 0; min thrust fixed at 0; drag coefficient ≥ 0; initial altitude/velocity configurable (default 0/0); all values finite; step rate not configurable.
  - US-2 Fixed-time-step advance: fixed 200 Hz (dt = 0.005 s), run as fast as possible (no wall-clock pacing), never stops by itself, "run N steps" shortcut.
  - US-3 Vertical dynamics: semi-implicit Euler (velocity then altitude); linear drag D = −b·v; thrust capped silently at max; ground floor at 0 with velocity zeroed and run continuing; free fall within 0.6 % after ≥ 1 s.
  - US-4 Determinism: bit-identical outputs on the same machine with the same code (cross-platform out of scope).
  - US-5 Open-loop thrust input: caller supplies thrust per step; last command held; initial held command 0 N; no controller.
  - US-6 Per-step output records (new): time, altitude, velocity, acceleration, thrust used, drag, saved in memory after every step.
  - Second round of answers: gravity > 0; initial altitude ≥ 0 and no downward start on the ground; drag coefficient < 200 × mass; max thrust 0 allowed; negative thrust silently set to 0; floor steps record acceleration 0 and actual forces; time-0 record saved; records grow without limit; "run 0 steps" is a no-op; tolerances = 0.6 % for long runs, rounding-only for hand-calculable values.
  - All BLOCKED ACs unblocked; all 25 Open Questions resolved. At the operator's request no further Open Questions were opened; four interpretations (I-1 … I-4) are listed in DESIGN.md for checking at approval, and two items are deferred to solution-architect.
- **Open Questions Resolved This Session**:
  - OQ-1 — Step rate fixed at 200 Hz, not user-changeable.
  - OQ-2 — No wall-clock pacing; run as fast as possible.
  - OQ-3 — Gravity configurable, default 9.81; SI units.
  - OQ-4 — Linear drag, D = −b·v.
  - OQ-5 — Minimum thrust 0; maximum configurable.
  - OQ-6 — Instant motor response; only min/max limits.
  - OQ-7 — Thrust above max capped silently; thrust actually used is recorded.
  - OQ-8 — Never stops by itself; caller decides; "run N steps" shortcut.
  - OQ-9 — Free fall within 0.6 % of formula, checked at ≥ 1 s.
  - OQ-10 — Initial altitude/velocity configurable; default on ground at rest.
  - OQ-11 — Ground is a floor at 0; velocity zeroed on landing; run continues.
  - OQ-12 — Semi-implicit Euler (velocity first, then altitude).
  - OQ-13 — Determinism on same machine + same code.
  - OQ-14 — Thrust supplied per step; last value held; starts at 0.
  - OQ-15 — After every step, save time, altitude, velocity, acceleration, thrust used and drag in memory.
  - OQ-16 — Gravity ≤ 0 rejected with a clear error.
  - OQ-17 — Initial altitude < 0, or altitude 0 with downward velocity, rejected with a clear error.
  - OQ-18 — Floor steps record what really happened: acceleration 0 and the forces actually acting.
  - OQ-19 — Negative thrust command silently set to 0, no error.
  - OQ-20 — 0.6 % for long runs; rounding-only for hand-calculable single steps; hover stays at the same height.
  - OQ-21 — Starting moment saved as the first record at time 0.
  - OQ-22 — Unlimited record growth accepted for now; limiting deferred to GUI work.
  - OQ-23 — "Run 0 steps" does nothing, no error.
  - OQ-24 — Drag coefficient ≥ 200 × mass rejected with a clear error.
  - OQ-25 — Maximum thrust 0 N allowed.
- **Approved By**: Ohus
- **Approval Date**: 13.11.2026
