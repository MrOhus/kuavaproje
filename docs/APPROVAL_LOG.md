# Approval Log

> Single file shared by the **entire pipeline** (`requirement-analysis`, `solution-architect`, and any future stage). Exactly **one active entry** exists at a time, regardless of which stage/skill created it, with status `Pending Approval`. Update it in place as decisions accumulate during a session — never create a second pending entry. Once a human operator explicitly sets it to `Approved` or `Rejected` and the associated commit/PR lands, move it to History below and leave the active slot empty for the next stage to use.

## Active Entry

_No active entry. The next pipeline stage (implementation) opens a new `Pending Approval` entry here._

---

## History

<!-- Move closed (Approved/Rejected) entries here, most recent first, once their commit/PR has landed. Keep the Stage field so it's clear which pipeline phase each entry belonged to. -->

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
