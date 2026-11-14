# Architecture Atlas

Central index of solution-architect output for this repository. Only requirements `Approved` (Stage: Requirement Analysis) in [docs/APPROVAL_LOG.md](../APPROVAL_LOG.md) may be modeled here (see [solution-architect SKILL.md](../../.claude/skills/solution-architect/SKILL.md)). Individual sessions may split their work into `ARCHITECTURE_<commit-id>.md` files when this file grows too large; every such file must be listed below.

## Linked Architecture Documents

| File | Scope / Topic | Started (commit) | Status |
|---|---|---|---|
| (this file) | Core: Round 1 — deterministic fixed-step altitude simulation (Python) | c8c3271 | Merged |
| [ARCHITECTURE_3dbd8e9.md](ARCHITECTURE_3dbd8e9.md) | Round 2 — PID altitude controller and step-response metrics (D-8 … D-15, AQ-7 … AQ-14) | 3dbd8e9 | Merged |
| [ARCHITECTURE_899eaea.md](ARCHITECTURE_899eaea.md) | Round 3 — live Tk GUI, gust, pause/reset, real-time pacing (D-16 … D-23, AQ-15 … AQ-22) | 899eaea | Merged |

**Input:** [docs/design/DESIGN.md](../design/DESIGN.md), Round 1 (US-1 … US-6), approved by Ohus on 13.11.2026 (APPROVAL_LOG History: "Requirement Analysis — Round 1 altitude simulation").

## Summary

- One pure-Python package, `kuava_sim`, standard library only at runtime. One public class: `Simulation`.
- Numbers are Python `float` (IEEE-754 binary64). The step is a fixed sequence of separately rounded operations (D-3), so results are bit-identical on the same machine with the same code.
- Records are stored in one flat `array('d')`, 6 doubles per record (D-5).
- python-control is a **test-only** dependency. It is used to check the trajectory against an exact discrete-time model of the same plant, and later metrics against the continuous plant (D-7).
- Requirement analysis deferred two items. The exact floating-point formulation is decided in D-3. The floor condition (D-4) was decided by the operator in AQ-1.
- D-1, D-2 and D-4 … D-7 were decided by the operator in AQ-1 … AQ-6, on 2026-11-14. Every answer chose the recommended option, so the models below needed no other changes.

## Data Models

### Constants (module level, not configurable)
Traces to: US-1, US-2

| Name | Type | Unit | Value |
|---|---|---|---|
| `STEP_RATE_HZ` | `int` | Hz | `200` |
| `DT` | `float` | s | `1 / 200` (nearest double to 0.005) |
| `MIN_THRUST` | `float` | N | `0.0` |
| `DEFAULT_GRAVITY` | `float` | m/s² | `9.81` |

**Invariants:** these values never change at runtime. `SimConfig` has no field for step rate, step length or minimum thrust, so passing one is a `TypeError` for an unexpected keyword. This satisfies the US-1 "cannot be changed" ACs through the "no such option exists" branch.

### Entity: SimConfig
Traces to: US-1

Frozen dataclass (`@dataclass(frozen=True, slots=True)`), validated in `__post_init__`. A `SimConfig` that exists is always valid.

| Field | Type | Unit | Constraints |
|---|---|---|---|
| `mass` | `float` | kg | required; finite; `> 0` |
| `max_thrust` | `float` | N | required; finite; `≥ 0` |
| `gravity` | `float` | m/s² | default `9.81`; finite; `> 0` |
| `drag_coeff` | `float` | N·s/m | default `0.0`; finite; `≥ 0`; `< STEP_RATE_HZ * mass` |
| `initial_altitude` | `float` | m | default `0.0`; finite; `≥ 0` |
| `initial_velocity` | `float` | m/s | default `0.0`; finite; if `initial_altitude == 0` then `≥ 0` |

`mass` and `max_thrust` have no defaults. The US-1 "Defaults" AC sets only these two, so both are treated as required.

**Invariants:**
- Every field is a finite `float`. Accepted `int` values are converted with `float()`. `bool` and non-numbers are rejected with `TypeError`.
- `drag_coeff < 200.0 * mass` (equivalent to `b·dt/m < 1`). The test uses the multiplication form so the error can state the limit exactly (`200 × 2.5 = 500.0` exactly).
- `not (initial_altitude == 0.0 and initial_velocity < 0.0)`.

**Validation order and messages** (`ValueError` unless noted; error types per AQ-6). Fields are checked in table order, and each field's finiteness is checked before its range. The first failure raises an error. Each message names the parameter, the rule and the value received, for example:
- `"gravity must be greater than 0 m/s² (got 0.0)"`
- `"drag_coeff must be below 200 × mass = 200.0 N·s/m (got 200.0); larger values make the simulation unstable"`
- `"initial_altitude must not be below 0 m (got -0.001)"`
- `"the drone cannot start on the ground while moving down (initial_altitude 0, initial_velocity -0.001)"`
- `"mass must be a finite number (got nan)"`

**Boundary Behavior:**
- Min/Max: `gravity = 0.001` accepted, `0` rejected. `max_thrust = 0` accepted, `-0.001` rejected. `drag_coeff = 199.999` with mass 1 accepted, `200` and `200.001` rejected. `initial_altitude = 0` accepted, `-0.001` rejected.
- Empty/Null/Zero: omitted optional fields take their defaults. `None` is rejected as a non-number. `-0.0` counts as 0 (`-0.0 >= 0` is true), so `initial_altitude=0, initial_velocity=-0.0` is accepted as "at rest".
- Overflow: for `mass > ~8.9e305`, `200.0 * mass` is `inf`, so every finite `drag_coeff` passes. That matches the real condition `b·dt/m < 1`, so nothing special is done.

**Concurrency / Race-Scenario Analysis:**
- The object is immutable and holds no shared state, so any number of threads can read it safely. It is never changed after construction.

### Entity: Record
Traces to: US-6, US-3

A read-only `NamedTuple`, built on demand from the record log (see `RecordLog`).

| Field | Type | Unit | Constraints |
|---|---|---|---|
| `time` | `float` | s | `= index / STEP_RATE_HZ` |
| `altitude` | `float` | m | `≥ 0` |
| `velocity` | `float` | m/s | positive upward |
| `acceleration` | `float` | m/s² | positive upward |
| `thrust_used` | `float` | N | `0 ≤ thrust_used ≤ max_thrust` |
| `drag` | `float` | N | `= -(drag_coeff * v_start)`, or `0.0` on a floor or rest record |

**Invariants:**
- `altitude ≥ 0` in every record.
- `altitude == 0 ⇒ velocity ≥ 0` in every record (AQ-1). This is the same rule as the configuration rule for the starting state (see D-4).
- A floor record has `altitude == velocity == acceleration == drag == 0.0`, stored as the literal `+0.0`.
- `time` of record `i` is `i / 200`. It is computed from the integer step count, never by adding up `DT`, so it cannot drift.

**Time-0 record (I-3):** `thrust_used = 0.0`. If `initial_altitude == 0 and initial_velocity == 0`, the record stores `altitude = velocity = acceleration = drag = +0.0`. Otherwise it stores `drag = -(b*v0)` and `acceleration = ((0.0 - m*g) + drag) / m`, using the same formulation as D-3.

**Boundary Behavior:**
- Min/Max: values are whatever the step produced. No per-step clamping or warnings, except the floor rule.
- Empty/Null/Zero: `-0.0` can appear in `drag` when `v_start == +0.0` and `b > 0`. It compares equal to `0`, and it is reproduced identically on every run, so it is left as is.
- Overflow: see "Noted for a later stage".

**Concurrency / Race-Scenario Analysis:**
- A `Record` is an immutable tuple, so it is safe to share.

### Entity: RecordLog
Traces to: US-6, US-4

Storage per AQ-5: one `array.array('d')`, with record `i` at positions `[6i, 6i+6)` in field order `time, altitude, velocity, acceleration, thrust_used, drag`. It is exposed read-only as `Simulation.records`, a `Sequence[Record]` view that supports `len()`, indexing, slicing and iteration, plus `column(name) -> tuple[float, ...]` to get one field as a series (for python-control comparisons).

| Field | Type | Unit | Constraints |
|---|---|---|---|
| `_data` | `array('d')` | mixed (per field above) | `len(_data) % 6 == 0`; `len(_data) ≥ 6` |

**Invariants:**
- `len(records) == step_count + 1`, and is always at least 1.
- Records are only ever appended. An existing record is never changed or removed.
- Each record is appended with one `_data.extend(six_tuple)` call. A step therefore adds all 6 values or none, and the columns can never get out of line.

**Boundary Behavior:**
- Min/Max: no upper limit (OQ-22). The 720,000-step AC uses about 35 MB (720,001 × 48 bytes).
- Empty/Null/Zero: never empty, because the time-0 record is written in the constructor. `run(0)` appends nothing.
- Overflow: memory exhaustion raises Python's `MemoryError`. Limiting records is deferred to GUI work (OQ-22).

**Concurrency / Race-Scenario Analysis:**
- Reading `records` while another thread calls `step` or `run` on the same instance is unsupported (see `Simulation`). In a single thread, a view taken earlier sees new records, because it reads the live array.

### Entity: Simulation (state and operations)
Traces to: US-1 … US-6

| Field | Type | Unit | Constraints |
|---|---|---|---|
| `config` | `SimConfig` | — | read-only |
| `_log` | `RecordLog` | — | single source of truth for time, altitude and velocity |
| `_held_thrust` | `float` | N | the raw last accepted command (finite); starts at `0.0` |

Read-only properties derived from the last record: `step_count` (`int`, steps), `time` (s), `altitude` (m), `velocity` (m/s), plus `held_thrust` (N). It also exposes `step_rate_hz` / `step_length` / `min_thrust`, which return the constants.

**Operations** (API shape per AQ-6):
- `Simulation(config: SimConfig)`: writes the time-0 record.
- `step(thrust: float | None = None) -> Record`: if `thrust` is given, validate it (finite `int`/`float`, not `bool`), then make it the held command. Perform one step with `T_used = min(max(held, 0.0), max_thrust)` and return the new record.
- `run(n: int, thrust: float | None = None) -> None`: validate `n` (an `int`, not `bool`, and `≥ 0`; `TypeError` for 2.5, `ValueError` for −1) and `thrust`, then do exactly what `n` calls to `step()` would do. `thrust`, if given, applies to the first of the `n` steps and is then held. `run(0, thrust=x)` validates `x` but does **not** change the held command, so `run(0)` stays a pure no-op as US-2 requires ("state … unchanged").

The raw command is held and capping happens at use time. Because capping gives the same result every time, this is the same as holding the capped value, and it satisfies "A held command outside the limits keeps being limited".

**Invariants:**
- Each operation is all-or-nothing: every argument is validated before anything changes. A rejected call (non-finite thrust, bad `n`) leaves the records, state and held command unchanged.
- There is no wall-clock access anywhere (no `time.sleep`, no `time.time`). Results depend only on the configuration and the sequence of commands.
- There is no global mutable state, so two `Simulation` instances never affect each other.

**Boundary Behavior:**
- Min/Max: thrust is capped silently to `[0, max_thrust]`, with no warning. `max_thrust = 0` means every step uses 0 N.
- Empty/Null/Zero: `step()` / `step(None)` uses the held command. `run(0)` is a no-op.
- Overflow: `step_count` is a Python `int` and has no limit.

**Concurrency / Race-Scenario Analysis:**
- Two threads calling `step`/`run` on one instance → **unsupported, no locking**. The house rule asks for simplicity, Round 1 has no concurrent caller, and the later GUI can drive the simulation from a single thread. This is documented in the class docstring.
- Separate instances in separate threads or processes → safe, because they share no state. This is what the US-4 multi-instance ACs rely on.
- `KeyboardInterrupt` during `run(n)` → the run stops at a step boundary. Each record is appended in one call, and state is read from the last record, so the instance stays consistent and has performed some number `k < n` of steps.

## Technology / Design Decisions

### D-1: Language runtime and version

**Status: Decided by the operator (AQ-2). ✅ marks the chosen option.**

| Option | Benefits | Drawbacks | Chosen |
|---|---|---|---|
| CPython, `requires-python >= 3.12`, developed on the installed 3.15.2 | Standard library only at runtime. Works on the operator's machine today. python-control 0.10.2 and numpy/scipy have cp315 Windows wheels (checked with `pip install --dry-run`). | 3.12 to 3.14 are allowed but not tested in CI | ✅ |
| Pin to exactly 3.15 | Only one interpreter to reason about | Rejects older interpreters for no technical reason, because the code uses no 3.13+ features | ❌ |
| `>= 3.10` | Widest reach | 3.10 and 3.11 are near end of life; small typing differences need extra care | ❌ |

**Why ≥ 3.12:** the oldest version that is still supported and needs no workarounds. Determinism only has to hold on the same machine with the same code (OQ-13), so one tested interpreter is enough.
**Why not exactly 3.15:** nothing in the design needs it, and pinning adds friction.
**Why not ≥ 3.10:** it adds test burden for interpreters that will soon be end-of-life, and nothing here needs them.

### D-2: Numeric representation and step loop

**Status: Decided by the operator (AQ-4). ✅ marks the chosen option.**

| Option | Benefits | Drawbacks | Chosen |
|---|---|---|---|
| Python `float` scalars in a plain loop | IEEE-754 binary64. Every `+ − × ÷` is rounded separately, and CPython never fuses `a*b+c` into FMA, so the order of operations fixes the result bit for bit. No dependencies. | About 1 µs per step, so 720,000 steps take under a second. Fine for "as fast as possible". | ✅ |
| NumPy scalars/arrays | Familiar for numerical code | The step depends on the previous step, so it cannot be vectorized and NumPy gives no speedup. Adds a runtime dependency. SIMD/FMA code paths make bit-exact reasoning harder. | ❌ |
| `fractions.Fraction` / `decimal` | Exact or decimal-faithful arithmetic | Fractions grow without limit (orders of magnitude slower over 720k steps). Not comparable with python-control floats. | ❌ |

**Why float:** it is the simplest option that is deterministic by construction.
**Why not NumPy:** no speed gain for a dependent per-step loop, plus a dependency and FMA ambiguity at runtime.
**Why not Fraction/Decimal:** far too slow, and exactness beyond ε is not required.

### D-3: Exact floating-point formulation (deferred item 2)

Per step, using `m, g, b, T_max` from the configuration and `h, v` from the last record:

```text
T  = min(max(held, 0.0), T_max)       # capping
D  = -(b * v)                         # drag from the velocity at the start of the step
a  = ((T - m * g) + D) / m            # this exact grouping, true division
vn = v + a * DT
hn = h + vn * DT
if hn <= 0.0 and vn < 0.0:            # floor (D-4)
    record(t, 0.0, 0.0, 0.0, T, 0.0)
else:
    record(t, hn, vn, a, T, D)
t  = step_count_after / STEP_RATE_HZ  # integer step count ÷ 200
```

| Option | Benefits | Drawbacks | Chosen |
|---|---|---|---|
| `a = ((T − m·g) + D) / m`, time `= n / 200` | When the caller passes `m*g` (I-4), `T − m*g` is exactly `0.0`, so hover is **bit-exact** and does not drift. Division matches the hand calculations. `n/200` is the double closest to the true time. | Callers must compute hover thrust as `m * g`, the same product in the same order (this is how I-4 is worded) | ✅ |
| `a = T/m − g − (b/m)·v` | Looks like the textbook equation | `T/m − g` is generally not exactly 0 at hover, so altitude drifts by rounding steps. Three roundings instead of one before the subtraction. | ❌ |
| Precomputed `1/m` and `a = F · inv_m` | One fewer division | Adds a rounding step, so hand-calculated values can differ in the last bit. The speed gain does not matter. | ❌ |
| Time `+= DT` | Simple | Accumulates error over 720,000 steps. Rejected by the "no drift" AC intent. | ❌ |

**Verified in a scratch run with this formulation:** hover stays at exactly 100.0 m and 0.0 m/s for 2000 steps. The US-6 hand-calculated record (`100.01010475`, `2.02095`, `4.19`) and the US-3 single-step free-fall values match within ε. Time `720000/200 == 3600.0`. Terminal speed rises monotonically to 19.619999999999294 (within 0.6 %, never above 19.62). Resting on the ground gives floor records.
**Why not the textbook form:** it breaks the bit-exact hover that I-4 relies on.
**Why not the reciprocal:** an extra rounding for no measurable gain.
**Why not accumulated time:** it drifts.

### D-4: Floor condition (deferred item 1)

**Status: Decided by the operator (AQ-1). ✅ marks the chosen option.**

| Option | Benefits | Drawbacks | Chosen |
|---|---|---|---|
| `hn <= 0.0 and vn < 0.0` | Covers `hn == 0` with `vn < 0`, so no record can show "on the ground, moving down", which is the state US-1 rejects at start. Includes every case `hn < 0` already covers: since `h ≥ 0`, `hn < 0` is only possible when `vn < 0`. | One extra comparison | ✅ |
| `hn < 0.0` (as written in DESIGN.md) | Literal reading of the requirement | Allows a record `(h = 0, v < 0)` when `h + vn·DT` happens to round to exactly 0. The next step then applies the floor anyway, so the record is briefly inconsistent. | ❌ |
| `hn <= 0.0` | Simplest | Also triggers on `hn == 0, vn == 0` (for example hover thrust on the ground). That gives the same values, but it calls a non-landing step a floor event. A future `vn > 0` case is impossible but not clearly excluded. | ❌ |

**Why `hn <= 0 and vn < 0`:** it keeps the invariant "altitude 0 ⇒ velocity ≥ 0" true for every record, and changes no AC (DESIGN.md says so explicitly).
**Why not `hn < 0`:** it allows a transient record that contradicts the starting-state rule.
**Why not `hn <= 0`:** it labels non-landing steps as floor steps for no benefit.

### D-5: Record storage

**Status: Decided by the operator (AQ-5). ✅ marks the chosen option.**

| Option | Benefits | Drawbacks | Chosen |
|---|---|---|---|
| One flat `array('d')`, 6 doubles per record, plus a `Sequence[Record]` view | About 48 B per record (35 MB per simulated hour). Stores doubles exactly. One `extend` per step keeps it atomic. `column()` is cheap for python-control. | A small view class (about 30 lines) | ✅ |
| `list[Record]` (NamedTuple objects) | The most direct option | About 250 B per record (6 boxed floats + tuple), roughly 180 MB per simulated hour. Records grow without limit (OQ-22), so this matters. | ❌ |
| Six separate `array('d')` columns | Natural column access | Six appends per step can get out of line if interrupted. Six objects to keep in sync. | ❌ |
| Growable NumPy array | Vector-friendly | Runtime NumPy dependency (rejected in D-2). Resizing logic. | ❌ |

**Why the flat array:** 5× less memory than objects for unlimited growth, with atomic appends.
**Why not list of tuples:** memory cost under OQ-22.
**Why not six columns:** risk of getting out of line, more code.
**Why not NumPy:** a runtime dependency we otherwise avoid.

### D-6: API shape and error types

**Status: Decided by the operator (AQ-6). ✅ marks the chosen option.**

| Option | Benefits | Drawbacks | Chosen |
|---|---|---|---|
| `Simulation(SimConfig)` with `step(thrust=None)` / `run(n, thrust=None)`; built-in `ValueError` / `TypeError` with messages that name the parameter | Command and step happen in one call, so a rejected command cannot leave things half-applied. Idiomatic Python errors. Nothing extra to learn. | Callers cannot catch "simulation errors" as their own type | ✅ |
| Separate `set_thrust()` and `step()` | Mirrors a hardware interface | Two calls per step. Harder to keep "command for step k" atomic. | ❌ |
| Custom exception hierarchy (`SimConfigError`, …) | Callers can catch them specifically | Adds classes the requirements do not ask for. The AC is "a clear error". | ❌ |

**Why:** it is the smallest interface that covers every AC.
**Why not set/step:** more calls and a non-atomic window.
**Why not custom exceptions:** not needed (house rule: simplicity). A subclass of `ValueError` can be added later without breaking callers.

### D-7: Tests and python-control

**Status: Decided by the operator (AQ-3). ✅ marks the chosen option.**

| Option | Benefits | Drawbacks | Chosen |
|---|---|---|---|
| pytest; `control` (python-control 0.10.x) as a dev-only extra (`pip install -e .[dev]`) | The runtime stays dependency-free. Tests can check against an **exact discrete model** and the continuous plant. | The dev install pulls numpy, scipy and matplotlib | ✅ |
| python-control as a runtime dependency | The model could be built inside the simulation | Heavy runtime dependencies for nothing the simulation itself needs | ❌ |
| unittest only, closed-form formulas only | No dependencies at all | Does not meet the "checked against python-control" requirement for later metrics | ❌ |

**How python-control is used:**
- **Discrete cross-check, valid away from the floor.** The step in D-3 is exactly an LTI system with `x = [h, v]`, `u = T_used − m·g`, `α = 1 − b·DT/m`:
  `A = [[1, DT·α], [0, α]]`, `B = [[DT²/m], [DT/m]]`, `C = I`, `D = 0`, `dt = DT`.
  `control.forced_response(control.ss(A, B, C, 0, DT), ...)` must match the records to a tight per-step tolerance. The grouping differs only by rounding. The configuration limit `b < 200·m` makes `0 < α ≤ 1`, so the model is stable. That limit is the reason for OQ-24.
- **Continuous reference:** `G_v(s) = 1/(m s + b)` and `G_h(s) = 1/(s (m s + b))`. These are used for the 0.6 % long-run checks and for the later controller metrics (rise time, overshoot, and so on).
- **Why not runtime:** the simulation itself does not need it.
- **Why not closed-form only:** the operator requires python-control for metrics.

**Layout:**

```text
pyproject.toml              # name kuava-sim, requires-python >=3.12, extra [dev] = pytest, control
src/kuava_sim/__init__.py   # exports Simulation, SimConfig, Record, constants
src/kuava_sim/simulation.py
tests/acceptance/test_us1_config.py … test_us6_records.py   # one file per user story (ATDD)
tests/reference/test_python_control.py
```

The US-4 "separate processes" AC runs the same script twice with `subprocess` and compares `records._data.tobytes()`.

## Noted for a later stage (not Open Questions)

These are edge cases, recorded here instead of opening new questions (house rule):
- Extreme but valid configurations (for example `max_thrust = 1e308`, `mass = 1e-300`) can overflow to `inf`/`nan` during a run. No per-step checks are made.
- Thread-safe access is needed if the GUI reads records from a different thread than the one stepping.
- Real-time pacing will wrap `run()`/`step()` from outside (OQ-2). It needs no change inside the simulation.

## Open Questions

Most important first. All answered by the operator in chat on 2026-11-14.

| ID | Question | Raised By | Status | Resolution |
|---|---|---|---|---|
| AQ-1 | **When does the ground stop the drone (D-4)?** (a) when the new height is below 0 (the rule in DESIGN.md as written); (b) when the new height is 0 or below **and** the drone is moving down; (c) when the new height is 0 or below, whatever the speed. **Recommendation: (b).** With (a), a step can now and then end exactly at height 0 while still moving down, which is the state the setup refuses at the start. (b) never allows that and changes no test. | solution-architect | Resolved | "AQ-1 b" → D-4 floor condition `hn <= 0 and vn < 0`; Record invariant updated |
| AQ-2 | **Which language and Python version (D-1)?** (a) Python 3.12 or newer, developed on your 3.15.2; (b) only Python 3.15; (c) Python 3.10 or newer. **Recommendation: (a).** It runs on your machine now, python-control installs on it, and it doesn't refuse newer-but-not-latest Pythons for no reason. (c) adds old versions nobody needs. | solution-architect | Resolved | "AQ-2 a" → D-1 CPython `>= 3.12`, developed on 3.15.2 |
| AQ-3 | **How do we test, and where does python-control go (D-7)?** (a) pytest for tests; python-control installed only for testing; (b) python-control needed to run the simulation itself; (c) only Python's built-in unittest and hand formulas, no python-control. **Recommendation: (a).** The simulation stays light and has no extra installs, and tests can still compare every step with python-control. (c) would not meet your python-control requirement. | solution-architect | Resolved | "AQ-3 a" → D-7 pytest; python-control as a dev-only extra |
| AQ-4 | **What kind of numbers does the step use (D-2)?** (a) normal Python numbers; (b) NumPy; (c) exact fractions or decimals. **Recommendation: (a).** Each step depends on the one before, so NumPy can't speed it up, and normal numbers give the same bits every run with no extra install. (c) is far too slow over long runs. | solution-architect | Resolved | "AQ-4 a" → D-2 Python `float` scalar loop |
| AQ-5 | **How are the saved records stored (D-5)?** (a) one compact block of numbers, 6 per record, read as normal records (about 35 MB per simulated hour); (b) a plain list of record objects (about 180 MB per hour); (c) six separate number columns; (d) a NumPy array. **Recommendation: (a).** Records grow without a limit, so 5× less memory matters, and each record is saved in one go so it can't be half-written. (b) is simplest to write but uses much more memory. | solution-architect | Resolved | "AQ-5 a" → D-5 flat `array('d')`, 6 doubles per record; RecordLog updated |
| AQ-6 | **What does using the simulation look like, and what errors does it give (D-6)?** (a) `step(thrust)` and `run(n, thrust)` (thrust is optional), with Python's normal error types (`ValueError`, `TypeError`) whose messages name the bad setting; (b) separate `set_thrust()` then `step()` calls; (c) like (a) but with our own error types. **Recommendation: (a).** One call per step means a bad thrust can't leave things half-changed, and normal error types are enough for "a clear error". | solution-architect | Resolved | "AQ-6 a" → D-6 `step(thrust)` / `run(n, thrust)`, built-in `ValueError`/`TypeError`; Simulation and SimConfig updated |
