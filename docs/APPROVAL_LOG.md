# Approval Log

> Single file shared by the **entire pipeline** (`requirement-analysis`, `solution-architect`, and any future stage). Exactly **one active entry** exists at a time, regardless of which stage/skill created it, with status `Pending Approval`. Update it in place as decisions accumulate during a session — never create a second pending entry. Once a human operator explicitly sets it to `Approved` or `Rejected` and the associated commit/PR lands, move it to History below and leave the active slot empty for the next stage to use.

## Active Entry

_No active entry. The next pipeline stage (solution-architect) opens a new `Pending Approval` entry here._

---

## History

<!-- Move closed (Approved/Rejected) entries here, most recent first, once their commit/PR has landed. Keep the Stage field so it's clear which pipeline phase each entry belonged to. -->

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
