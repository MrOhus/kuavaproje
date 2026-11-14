# Architecture Session — split from ARCHITECTURE.md at commit `899eaea`

> Linked from [ARCHITECTURE.md](ARCHITECTURE.md). This file holds solution-architect output produced in a single working session that would otherwise have made the central atlas too large. It is a **permanent linked record** — once a commit/PR lands for this session, its atlas row simply changes from `Active` to `Merged`/`Closed`; this file is never folded back into `ARCHITECTURE.md`.

**Input:** [DESIGN_f351eee.md](../design/DESIGN_f351eee.md), Round 3 (US-12 … US-19, OQ-34 … OQ-41), approved by Ohus on 14.11.2026 (APPROVAL_LOG History: "Requirement Analysis — Round 3 live GUI, wind gust, pause and reset").

**Builds on:** [ARCHITECTURE.md](ARCHITECTURE.md) (D-1 … D-7) and [ARCHITECTURE_3dbd8e9.md](ARCHITECTURE_3dbd8e9.md) (D-8 … D-15). All of those still hold:
- standard library only at runtime
- plain floats
- records as the single source of truth, with six fields
- built-in error types
- python-control is a test-only dependency
- `Simulation` is single-threaded

## Summary

The app is built in three layers (AQ-17):

| Layer | Module | What it adds or does | Testable without a window |
|---|---|---|---|
| Core | `Simulation` | Gains one method, `gust()` (AQ-18), and `last_step_metrics()`, used for the live table | Yes |
| Session | `LiveSession` (`kuava_sim/live.py`) | Real-time pacing, pause, reset, slider handling, plot buffer, metrics rows | Yes, with a fake clock |
| Window | `App` (`kuava_sim/app.py`) | A thin Tkinter window that only draws the session and forwards clicks | No |

- **Technology (AQ-15):** Tkinter with hand-drawn `Canvas` plots. It is in the standard library, so there is no new runtime dependency.
- **Thread and pacing (AQ-16):** everything runs in the Tk thread. Each frame takes the 200 Hz steps that are due by the wall clock, at most 50 (0.25 s). Anything beyond that is dropped.
- **Records (AQ-19):** they keep their six fields. The gust shows in the recorded acceleration.
- **Metrics (AQ-20):** only the newest metrics row is recomputed, at most every 0.5 s and less often if a recompute is slow.
- **GUI tests (AQ-21):** they skip with a reason when there is no display.
- **Error display (AQ-22):** every error while the app runs becomes a short red message in the window and pauses the simulation. There are no pop-ups, and the full error is not printed anywhere.

Prototype measurements (scratch, not committed; this machine, Python 3.15.2, Tk 9.0):

| Measurement | Result |
|---|---|
| Tk `Canvas`, two plots, three 1000-point lines, live controlled simulation, a frame requested every 5 ms | 65 fps average, slowest frame 36 ms |
| The same, a frame requested every 15 ms | 41 fps average (Windows timer granularity is about 15 ms) |
| matplotlib (TkAgg), full redraw every frame | 19 fps average |
| `step_metrics()` with 12,000 / 120,000 / 720,000 records | 3 / 30 / 201 ms |
| 12,000 controlled steps (1 simulated minute) | 18 ms |

## Data Models

### Constants
Traces to: US-13, US-14, US-16, OQ-34 … OQ-40

| Name | Module | Type | Unit | Value | Source |
|---|---|---|---|---|---|
| `GUST_FORCE` | core | `float` | N, downward | `5.0` | OQ-35 |
| `GUST_STEPS` | core | `int` | steps | `100` (0.5 s) | OQ-35 |
| `SLIDERS` | live | `dict[str, tuple[float, float, float]]` | per slider | (low, high, start): `kp (0, 50, 4)`, `ki (0, 20, 1)`, `kd (0, 20, 3)`, `setpoint (0, 100, 10)`; resolution `0.1` | OQ-36 |
| `APP_CONFIG` | live | `SimConfig` | — | mass 1.0, gravity 9.81, drag_coeff 0.5, max_thrust 30.0, initial altitude 0.0, initial velocity 0.0 | OQ-36 |
| `PLOT_WINDOW` | live | `float` | s | `20.0` | OQ-38 |
| `MAX_STEPS_PER_FRAME` | live | `int` | steps | `50` (0.25 s) | AQ-16 |
| `METRICS_REFRESH` | live | `float` | s | `0.5` (minimum interval) | AQ-20 |
| `FRAME_INTERVAL_MS` | app | `int` | ms | `16` (target about 60 fps) | coding detail |
| `PLOT_EVERY` | live | `int` | steps | `4` (one plotted point per 20 ms) | coding detail |

**Invariants:**
- None of these values is configurable in Round 3.
- Every slider value lies inside the `Simulation` validity ranges, so a slider can never produce a rejected value.

**Coding details** (decided by the architect under rule 3, recorded here):
- `FRAME_INTERVAL_MS` = 16. The next frame is scheduled after `max(1, 16 − time spent in this frame)` ms. A fixed 15 ms delay measured only 41 fps; scheduling sooner measured 65 fps.
- `PLOT_EVERY` = 4. This plots 1001 points per line over 20 s, the density that was measured at 65 fps.

### Entity: Gust state (inside `Simulation`)
Traces to: US-16

| Field | Type | Unit | Constraints |
|---|---|---|---|
| `_gust_left` | `int` | steps | `0 … GUST_STEPS`, starts at `0` |

**Public API (AQ-18, "just one simple gust button function, nothing extra"):**
- `gust() -> None` takes no arguments and always succeeds.
- It sets `_gust_left = GUST_STEPS`, so a second press restarts the gust and never adds a second force.
- It works whether the controller is on or off.
- There are no read-back properties. Tests observe the gust through the recorded acceleration.

**Invariants:**
- While `_gust_left > 0`, each step applies the force (predicate below) and decrements `_gust_left` by 1.
- With `_gust_left == 0`, the step runs the unchanged Round 2 code path, bit for bit. All Round 1/2 tests and the bit-exact hover still hold.
- The controller never reads gust state (OQ-35).
- The same `gust()` calls at the same step counts give bit-identical records.

**Boundary Behavior:**
- A press after step `k` puts the force on steps `k+1 … k+100`. Step `k+101` has no force.
- A press 40 steps into a gust restarts the count at 100. The force is still 5 N.
- On the ground, the floor rule D-4 holds the drone at altitude 0.
- `run(n)` after `gust()` behaves exactly like `n` calls to `step()`.

**Concurrency:** as D-8. A press between two steps takes effect from the next step.

### Predicate: Step with gust (extends D-3)
Traces to: US-16

```text
if gust_left > 0:
    a = (((t_used - m * g) + drag) - GUST_FORCE) / m
    gust_left -= 1
else:
    a = ((t_used - m * g) + drag) / m        # unchanged Round 1/2 expression
v_next, h_next, floor rule: unchanged (D-3, D-4)
```

**Records (AQ-19):** the six fields are unchanged.
- `acceleration` is the real acceleration, including the gust.
- `drag` is drag only.

### Core addition: `last_step_metrics()`
Traces to: US-15, AQ-20

- `Simulation.last_step_metrics() -> StepMetrics | None` returns exactly `step_metrics()[-1]`, but computes only the newest window. Its cost is O(records since the last change).
- It returns `None` if the controller was never turned on.
- This is a coding detail under rule 3: it is needed so that "only update the newest row" does not recompute every row.

**Invariant:** for any simulation with at least one change, `last_step_metrics() == step_metrics()[-1]`, field by field (NaN matching NaN).

### Entity: LiveSession (`kuava_sim/live.py`, no Tk import)
Traces to: US-12 … US-17

| Field | Type | Unit | Constraints |
|---|---|---|---|
| `sim` | `Simulation` | — | read-only property; replaced by `reset()` |
| `values` | `dict[str, float]` | per slider | the current slider values, always inside `SLIDERS` |
| `paused` | `bool` | — | starts `False` |
| `_anchor_time`, `_anchor_step` | `float`, `int` | s, steps | wall-clock time and step count at the last re-anchor |
| `_plot` | `deque[tuple[float, float, float, float]]` | (s, m, m, N) | time, altitude, setpoint and thrust used, one entry every `PLOT_EVERY` steps; `maxlen = 1001` |
| `_rows` | `list[StepMetrics]` | — | finished rows, frozen, oldest first |
| `_newest`, `_next_refresh` | `StepMetrics`, `float` | —, s | the live newest row and when it may next be recomputed |
| `_frame_times` | `deque[float]` | s | frame timestamps within the last 1 s, for the fps display |
| `message` | `str` | — | the error message currently shown, or `""` |

Every method receives the wall-clock time `now` from its caller, so tests can use a fake clock.

| Method | Behavior |
|---|---|
| `tick(now) -> int` | Applies the pacing predicate, takes the steps that are due, appends plot points, and refreshes the newest row when it is due. Returns the number of steps taken. While paused it takes no steps. |
| `set_gain(name, value)` | Calls `sim.set_gains(...)` immediately; the new gain is used from the next step. No metrics row is added. |
| `release_setpoint(value)` | If the value equals the current setpoint, does nothing (OQ-33). Otherwise it freezes the newest row (recomputed one last time), calls `sim.set_setpoint(value)`, and starts the new newest row. |
| `press_gust()` | Calls `sim.gust()`. Ignored while paused (OQ-37). |
| `pause()` | Pauses. |
| `resume()` | Resumes, re-anchors the clock and clears `message`. |
| `reset(now)` | Builds a new `Simulation(APP_CONFIG)` and calls `enable_controller` with the current `values`. Clears the plot, rows and message, re-anchors the clock, and keeps `paused` as it was. |
| `fail(exc)` | Pauses and sets `message` to the plain text from D-23. Never raises and never prints. |
| `plot_points()`, `metrics_rows()` (newest first), `fps(now)` | Read-only accessors for the window. |

**Invariants:**
- The session is the only caller of `sim`'s mutating methods, and it calls them from one thread.
- Sliders work while paused (OQ-37). A setpoint released while paused counts at the paused record.
- Frozen rows equal the matching `step_metrics()` entries. The newest row equals `last_step_metrics()` as of its last refresh, at most `max(0.5 s, 20 × last cost)` old.
- The plot buffer only holds the last 20 s. The records in `sim` are never trimmed (OQ-38).

**Boundary Behavior:**
- At time 0 the plot holds one point.
- The time axis is `[0, 20]` until 20 s have passed, then `[t − 20, t]`.
- The first row is the start row from `enable_controller` (OQ-32).

**Concurrency:** Tk delivers slider, button and timer callbacks one at a time on the main thread (AQ-16), so no callback can run during a frame's steps and no locks are needed.

### Predicate: Real-time pacing (OQ-34, AQ-16)
Traces to: US-12

```text
due = int((now - anchor_time) * 200) - (sim.step_count - anchor_step)
if due > MAX_STEPS_PER_FRAME:            # behind: catch up 0.25 s, skip the rest
    take 50 steps; anchor_time = now; anchor_step = sim.step_count
else:
    take max(due, 0) steps
```

- Steps are counted from a fixed anchor, so there is no rounding drift. Simulated time never runs ahead of the wall clock.
- While the computer keeps up, simulated time since the anchor trails wall-clock time since the anchor by less than one step.
- Resume and reset re-anchor the clock, so no simulated time passes while paused.

### Entity: App (`kuava_sim/app.py`, Tkinter)
Traces to: US-12 … US-18

**Window contents:**
- Four `tk.Scale` sliders (from `SLIDERS`, resolution 0.1), each with its value label.
  - The gain sliders call `set_gain` on every change.
  - The setpoint slider calls `release_setpoint` on `<ButtonRelease-1>` and `<KeyRelease>`. Keyboard arrows also move a slider, so a key release counts as letting go (operator: fine).
- Two `Canvas` plots.
  - Plot 1: altitude in blue and setpoint in red dashed, in m. The y axis is `[0, max(1, 1.1 × largest value in view)]`.
  - Plot 2: thrust used in N, with the y axis fixed at `[−1, 31]` and grey lines at 0 and 30 N.
- A `ttk.Treeview` metrics table. Values are rounded for display only (operator: fine), and NaN is shown as "not reached".

  | Column | Unit | Rounding |
  |---|---|---|
  | Time of change | s | 2 dp |
  | From → to | m | 1 dp |
  | Rise time | s | 2 dp |
  | Overshoot | % | 1 dp |
  | Settling time | s | 2 dp |
  | Steady-state error | m | 3 dp |

- Buttons: Pause/Resume, Reset, and Wind gust (disabled while paused).
- A status line showing the fps, with a red error message beside it (AQ-22, D-23).

**Errors (D-23):** Tk's `report_callback_exception` and a `try` around each frame both send any exception to `session.fail(exc)`. That pauses the simulation and sets `message`:
- for `ValueError`, `TypeError` and `RuntimeError`, `str(exc)` (Round 1/2 messages already name the setting);
- otherwise, `Unexpected error: <exc message>`, or `Unexpected error (<type name>)` when the exception has no message.

The status line shows `message` in red. Nothing is printed to the terminal or written to a file. A repeated error just sets the same message again, so nothing piles up. Resume or Reset clears it.

**Each frame:**
1. `session.tick(now)`
2. Update the line coordinates.
3. Update the table if it changed.
4. Schedule the next frame.

**Invariants:** the window holds no simulation state. Everything it draws comes from the session.

**Boundary:** closing the window cancels the timer and ends the loop with exit code 0.

**Concurrency:** Tk main thread only (AQ-16).

### Entity: Startup (`kuava_sim/__main__.py`)
Traces to: US-12, US-18, US-19, OQ-41

| Situation | Output (stderr, one line) | Exit code |
|---|---|---|
| `import tkinter` fails | `Cannot start: Tkinter is not installed. Install Python with Tcl/Tk support (on Linux the python3-tk package).` | 1 |
| `tk.Tk()` raises `TclError` | `Cannot start: no display available. Run the app from a desktop session.` | 1 |
| Any other error during start-up | `Cannot start: <message>` | 1 |
| Window closed normally | — | 0 |

No traceback is printed at start-up (OQ-41; AQ-22 concerns only errors while the app runs).

### GUI tests (AQ-21)
Traces to: US-12 … US-19

- Logic tests drive `LiveSession` and `Simulation` with a fake clock. They need no window.
- Window tests open a real Tk window and drive it through widget methods and `event_generate`.
- The frame-rate test runs the real window for 5 s and asserts that the average is above 30 fps. The measured average is included in the failure message (OQ-40).
- When `tk.Tk()` cannot open a display, the window tests are skipped, and the reason "no display available" is printed in the pytest summary. pytest's `-rs` is added to the default options in `pyproject.toml`.

## Technology / Design Decisions

Decided by the operator through AQ-15 … AQ-22 (2026-11-14, answers in the operator's own words in the table below). ✅ marks the chosen option. The other rows are the alternatives considered, with the reason each was not chosen.

### D-16: GUI and plotting technology (AQ-15)

| Option | Benefits | Drawbacks | Chosen |
|---|---|---|---|
| Tkinter + hand-drawn `Canvas` plots | Standard library: no new runtime dependency (D-1 holds); measured 65 fps | Axes and ticks drawn by hand (about 60 lines) | ✅ |
| Tkinter + matplotlib | Ready-made axes | Measured 19 fps; adds numpy and matplotlib at runtime | ❌ |
| Qt + pyqtgraph | Fast plots | Large dependency; not checked on Python 3.15 | ❌ |

**Why Tkinter:** "It comes with Python and it was the only one fast enough (65 fps)." **Why not matplotlib:** below the 30 fps requirement. **Why not Qt:** a heavy dependency that was not verified.

### D-17: Thread and catch-up limit (AQ-16)

| Option | Benefits | Drawbacks | Chosen |
|---|---|---|---|
| One thread (Tk). At most 50 steps (0.25 s) per frame; the rest is skipped | No locks; `Simulation` stays single-threaded; deterministic order of inputs and steps | Redraw time delays stepping, which the 0.25 s catch-up covers | ✅ |
| A separate simulation thread | Steps continue while the window is busy | Locks around every slider change; `Simulation` is not thread-safe | ❌ |

**Why:** "Keep everything in one thread. If the PC lags, catch up a quarter second at most and skip the rest."

### D-18: Layers, pause and reset (AQ-17)

| Option | Benefits | Drawbacks | Chosen |
|---|---|---|---|
| `LiveSession` without Tk holds pacing, pause, reset and sliders; reset builds a new `Simulation` | Testable without a window or a real clock; reset cannot leave stale state | One more module | ✅ |
| Logic inside the window code | Fewer files | Every test needs a display and real time | ❌ |
| `reset()` / `pause()` on `Simulation` | — | Pause is not a simulation concept; a reset method duplicates `__init__` | ❌ |

**Why:** "Keep pause, reset and sliders separate from the window so they can be tested without one. Reset starts a new simulation."

### D-19: Gust API (AQ-18)

| Option | Benefits | Drawbacks | Chosen |
|---|---|---|---|
| `Simulation.gust()` only, with fixed 5 N / 100 steps and no read-back | Exactly OQ-35; nothing to validate | Gust state is only visible through the records | ✅ |
| A general `apply_disturbance(force, steps)` | Reusable | Extra validation for features out of scope | ❌ |
| Gust countdown in the GUI layer | Core unchanged | OQ-35 puts the gust in the core | ❌ |

**Why:** "Just one simple gust button function, nothing extra."

### D-20: Gust in the records (AQ-19)

| Option | Benefits | Drawbacks | Chosen |
|---|---|---|---|
| Six fields unchanged; acceleration includes the gust | No change to D-5/D-15 or to any record test | The force is not its own field | ✅ |
| A seventh field for the disturbance | Visible per step | Changes D-5 and every Round 1/2 record test; +8 bytes per record | ❌ |

**Why:** "Keep the 6 numbers. The gust already shows in the acceleration."

### D-21: Live metrics refresh (AQ-20)

| Option | Benefits | Drawbacks | Chosen |
|---|---|---|---|
| Only the newest row is recomputed, via `last_step_metrics()`; the next refresh comes after `max(0.5 s, 20 × the last recompute time)` | The app stays fast at any run length (metrics never take more than about 5 % of the time) | One new core method | ✅ |
| Recompute every row with `step_metrics()` every frame | No new code | 30 ms per frame after 10 min, which falls below 30 fps | ❌ |

**Why:** "Only update the newest row, every half second or slower so the app stays fast." Making the interval grow with the recompute cost is the "or slower" part, chosen as a coding detail under rule 3.

### D-22: GUI tests without a display (AQ-21)

| Option | Benefits | Drawbacks | Chosen |
|---|---|---|---|
| Skip the window tests and print the reason | `python -m pytest` still runs everything possible and says clearly what was skipped | A headless machine does not check the window | ✅ |
| Fail the window tests | Can't be missed | Fails for an environment reason | ❌ |

**Why:** "If there's no screen, skip the window tests and say why."

### D-23: Error display (AQ-22)

| Option | Benefits | Drawbacks | Chosen |
|---|---|---|---|
| A short red message in the window's status line; the simulation pauses; the full error is not printed anywhere | Plain (OQ-41); never blocks the loop; a repeated error doesn't pile up | No traceback for debugging | ✅ |
| A pop-up dialog | Hard to miss | Stops the Tk loop until closed; repeated errors stack up | ❌ |
| The red message plus the full error printed to the terminal | Easier debugging | Shows a traceback, which US-18 / OQ-41 rule out | ❌ |

**Why:** "Show a short red message in the window and pause. No popups. Don't print the full error anywhere."

## Open Questions

Most important first. Answered by the operator on 2026-11-14 in their own words.

| ID | Question | Raised By | Status | Resolution |
|---|---|---|---|---|
| AQ-15 | **Which GUI toolkit and way of drawing the plots should the app use?** Facts: Tkinter (Tk 9.0) is part of the standard library and installed. The runtime has no dependencies today (D-1). matplotlib 3.11.2 is installed only as a test dependency of python-control. Measured: Tk canvas 65 fps; matplotlib full redraw 19 fps. Requirement: average above 30 fps. Other toolkits (for example Qt) have not been checked on Python 3.15. | solution-architect | Resolved | "Tkinter. It comes with Python and it was the only one fast enough (65 fps)." → D-16 |
| AQ-16 | **Should the simulation run in the same thread as the window or in its own thread, and when the computer falls behind, how much simulated time may one frame catch up before the rest is dropped?** Facts: `Simulation` is not thread-safe (Round 1). One simulated minute takes 18 ms to compute. At 30 fps a frame needs about 6.7 steps, at 60 fps about 3.3. The Windows timer resolution is about 15 ms. Holding the mouse on the window's title bar on Windows stops the Tk event loop until released. OQ-34: when behind, the simulation slows down and never jumps ahead. | solution-architect | Resolved | "Keep everything in one thread. If the PC lags, catch up a quarter second at most and skip the rest." → D-17 |
| AQ-17 | **Where should the real-time pacing, pause, reset and slider handling live: in the window code, in a separate part with no window, or in `Simulation`? Should reset create a new simulation or clear the existing one?** Facts: code without a window can be tested with a fake clock, while code inside the window needs a display and real time. `Simulation` has no reset today. Reset must restore time 0 and the start state with the current slider values, and cancel any gust (OQ-37). | solution-architect | Resolved | "Keep pause, reset and sliders separate from the window so they can be tested without one. Reset starts a new simulation." → D-18 |
| AQ-18 | **How should code start a gust in `Simulation`, and what gust information should it be able to read back?** Facts: OQ-35 fixes 5 N downward for 0.5 s, with a repeat press restarting it, and makes the gust part of the core. All bonus items are out of scope. Every core input so far is checked, with a clear error when invalid. | solution-architect | Resolved | "Just one simple gust button function, nothing extra." → D-19 |
| AQ-19 | **Should the gust force be saved in each record?** Facts: records have six fields (D-5, D-15), and many Round 1/2 tests check exactly six. The acceleration field is the real acceleration, so it already includes a gust; the drag field is drag only. A seventh field would raise memory from 48 to 56 bytes per record (about 35 → 40 MB per simulated hour). | solution-architect | Resolved | "Keep the 6 numbers. The gust already shows in the acceleration." → D-20 |
| AQ-20 | **How often should the newest metrics row be recomputed while its response is still developing?** Facts: one recomputation costs time in proportion to the records since that setpoint change: 3 ms after 1 min, 30 ms after 10 min, 201 ms after 1 h. One frame at 30 fps has 33 ms. Older rows no longer change once the next setpoint change is made. Recomputing every row at once (`step_metrics()`) costs time in proportion to all records. | solution-architect | Resolved | "Only update the newest row, every half second or slower so the app stays fast." → D-21 |
| AQ-21 | **On a machine with no display, what should the GUI tests (including the 5 s frame-rate test) do when `python -m pytest` runs?** Facts: this machine has a display. Tests that need a real window take about 10 s in total. pytest can skip a test and print the reason in the summary. US-19 says the one test command runs every test, including GUI tests. | solution-architect | Resolved | "If there's no screen, skip the window tests and say why." → D-22 |
| AQ-22 | **Where in the window should an error message appear, and should the technical details (traceback) be kept anywhere for debugging?** Facts: OQ-41 requires a plain message, the simulation paused, the app open, and no traceback shown to the user. Round 1/2 errors are `ValueError`, `TypeError` and `RuntimeError` with messages that name the setting. A modal dialog stops the Tk loop until it is closed. An error could repeat on every frame. | solution-architect | Resolved | First answer: "Show a short red message in the window and pause. No popups. Keep the full error in the terminal." That conflicted with US-18 / OQ-41 ("no traceback is shown to the user"), and the conflict was reported. Final answer: "Show a short red message in the window and pause. No popups. Don't print the full error anywhere." → D-23 |
