# Design Session — split from DESIGN.md at commit `f351eee`

> Linked from [DESIGN.md](DESIGN.md). This file holds requirement-analysis output produced in a single working session that would otherwise have made the central atlas too large. It is a **permanent linked record** — once a commit/PR lands for this session, its atlas row simply changes from `Active` to `Merged`/`Closed`; this file is never folded back into `DESIGN.md`.

## Scope — Round 3: live desktop GUI, wind gust, pause and reset

**In scope (only, operator 2026-11-14):**
- A simple desktop GUI that runs the simulation live with the Round 2 PID controller.
- Sliders for Kp, Ki, Kd and the setpoint.
- Live plots of the setpoint, the altitude and the controller output, redrawn at more than 30 frames per second.
- The step-response metrics (Round 2) shown after each setpoint change.
- A wind gust button that disturbs the drone.
- Pause and reset.
- A README with setup instructions and the metric definitions.
- One command to start the app and one command to run all tests.
- Clear error messages instead of crashes.

**Out of scope (explicitly):** all bonus items. Everything listed as out of scope in Rounds 1 and 2 stays out of scope unless named above (for example anti-windup, sensor noise, horizontal motion, file export, determinism across machines).

**Unchanged (applies to this round too):** SI units; the fixed 200 Hz step; deterministic on the same machine and code for the same inputs; thrust capped silently to `[0, T_max]`; the ground floor; the controller formula and the metric definitions of Round 2; invalid settings rejected with a clear error naming the setting.

## User Stories

### US-12: Start the app and watch the drone fly under PID control
As a simulation user
I want to start a desktop app with one command and see the simulation running live with the PID controller
So that I can watch how the controller behaves without writing code

### US-13: Tune the controller with sliders
As a simulation user
I want sliders for Kp, Ki, Kd and the setpoint that take effect while the app runs
So that I can tune the controller and try new targets interactively

### US-14: Live plots
As a simulation user
I want live plots of the setpoint, the altitude and the controller output, redrawn at more than 30 frames per second
So that I can see the response as it happens

### US-15: Metrics after each setpoint change
As a simulation user
I want rise time, overshoot, settling time and steady-state error shown after each setpoint change
So that I can judge a tuning by numbers, not only by eye

### US-16: Wind gust disturbance
As a simulation user
I want a button that hits the drone with a wind gust
So that I can see how well the controller rejects a disturbance

### US-17: Pause and reset
As a simulation user
I want to pause and resume the simulation, and to reset it to the start
So that I can study a moment closely and start a new experiment cleanly

### US-18: Clear error messages instead of crashes
As a simulation user
I want every problem reported as a clear message, while the app stays open where possible
So that a mistake or a missing install never ends in a crash or a raw traceback

### US-19: README and one-command start and test
As a new user of the repository
I want a README with setup steps, the metric definitions, one command to start the app and one command to run all tests
So that I can install, use and check the project without reading the code

### Round 3 model (from resolved Open Questions)

- **Speed (OQ-34):** the app runs in real time, so one simulated second takes one wall-clock second. Each frame takes as many whole 200 Hz steps as real time has passed since the last frame. If the computer falls behind, the missed time is dropped and the simulation slows down; it never jumps ahead to catch up. The step itself is the unchanged deterministic Round 2 step.
- **Wind gust (OQ-35):** there is one gust button. Each press adds a fixed downward force of 5 N for 0.5 s (100 steps).
  - The force starts with the next step and acts on top of gravity, thrust and drag.
  - A press during a gust restarts the 100 steps; the two forces are not added together.
  - The gust is part of the simulation core, so it is deterministic and can be tested without the GUI.
  - The controller is not told about the gust.
  - The thrust cap and the ground floor are unchanged.
- **Sliders and the drone (OQ-36):**

  | Slider | Range | Step | Start value |
  |---|---|---|---|
  | Kp | 0–50 N/m | 0.1 | 4 |
  | Ki | 0–20 N/(m·s) | 0.1 | 1 |
  | Kd | 0–20 N·s/m | 0.1 | 3 |
  | Setpoint | 0–100 m | 0.1 | 10 m |

  - The current value is shown next to each slider.
  - The drone is fixed: mass 1 kg, gravity 9.81 m/s², drag 0.5 N·s/m, maximum thrust 30 N. It starts on the ground at rest.
  - The controller is on from the start, and the GUI has no manual thrust.
  - A gain takes effect while its slider is dragged.
  - The setpoint takes effect only when its slider is released, so one drag is one setpoint change and gives one metrics result.
- **Pause and reset (OQ-37):** one Pause/Resume button.
  - While paused, the sliders still work and take effect when stepping resumes. A setpoint change made while paused counts at the paused step.
  - The gust button is disabled while paused.
  - Reset returns to time 0 with the start state. It keeps the current slider values and turns the controller on with them. It clears the plots, the metrics and the records, and cancels any gust. The pause state stays as it was.
- **Plots (OQ-38):** two plots share a time axis showing the last 20 s, scrolling.
  - The first plot shows altitude and setpoint (m).
  - The second shows the controller output, which is the thrust actually used after capping (N), with the 0 N and 30 N limits marked.
  - Before 20 s have passed, the axis shows 0 to 20 s.
  - Points older than 20 s leave the plot, but all records are kept (about 35 MB per simulated hour, the limit deferred from OQ-22).
- **Metrics (OQ-39):** a table with one row per setpoint change (including the start), newest on top.
  - Columns: time of the change (s), from → to altitude (m), rise time (s), overshoot (%), settling time (s), steady-state error (m).
  - The newest row updates live, as in Round 2 OQ-29.
  - A metric that is not reached (NaN) is shown as "not reached". Values are rounded for display only.
  - A gust during a result also disturbs that result's metrics.
- **Frame rate (OQ-40):** the app measures its own frame rate and shows it in the window.
  - An automated test runs the live app for 5 s and requires an **average** above 30 frames per second.
  - A single slow frame does not fail the test as long as the average is above 30.
- **Errors and commands (OQ-41):**
  - An error inside the running app is shown in the window as a short plain message saying what happened. The simulation pauses, the app stays open, and no traceback is shown to the user.
  - A startup problem (a missing dependency, no display) prints one plain line saying what is missing and how to fix it, then exits with code 1, again with no traceback.
  - The commands are:

    | Purpose | Command |
    |---|---|
    | Setup | `python -m pip install -e ".[dev]"` |
    | Start | `python -m kuava_sim` |
    | All tests, including GUI tests | `python -m pytest` |

### Deferred to the next stage (solution-architect)

Noted here instead of opening Open Questions (house rule):
- Which GUI and plotting technology to use, and whether it is a runtime dependency.
- How the GUI drives the simulation (thread or event-loop timer) and stays responsive.
- How gust, pause and reset are split between the simulation core and the GUI.
- When the app counts as "behind" in OQ-34, for example the most steps one frame may take before the rest is dropped.
- How the frame rate is measured in a test, and whether GUI tests need a visible window.
- Whether the gust force appears in the records (Round 2 kept six record fields, D-15), and how the gust is offered in the core API.

## Gherkin Acceptance Criteria

```gherkin
Feature: US-12 Start the app and watch the drone fly under PID control

  Scenario: The app starts with one command and the drone takes off under control
    Given the project is set up with "python -m pip install -e .[dev]"
    When the user runs "python -m kuava_sim"
    Then a desktop window opens
    And the drone starts on the ground at rest with mass 1 kg, gravity 9.81 m/s², drag 0.5 N·s/m and maximum thrust 30 N
    And the controller is on with Kp 4, Ki 1, Kd 3 and setpoint 10 m
    And the plotted altitude rises toward 10 m

  Scenario: The app runs in real time
    Given the app is running and not paused, and the computer keeps up
    When some wall-clock time passes
    Then the simulated time has advanced by the same amount, apart from the steps of the frame not yet drawn
    And the simulation always advances in whole 200 Hz steps

  Scenario: The app slows down instead of jumping ahead when the computer falls behind
    Given the app is running and a frame is delayed by much more than one frame time
    When the next frame is drawn
    Then the missed time is dropped and the simulation does not take a burst of extra steps to catch up
    And the simulated time is now behind the wall-clock time

  Scenario: The live simulation is the same deterministic simulation as without the GUI
    Given the app has applied a sequence of slider changes and gust presses at known steps
    When the same sequence is applied at the same steps to a new simulation without the GUI, with the same start values
    Then the records are bit-identical

  Scenario Outline: The app cannot start
    Given <problem>
    When the user runs "python -m kuava_sim"
    Then it prints one plain line saying what is missing and how to fix it
    And no traceback is printed
    And it exits with code 1

    Examples:
      | problem                                   |
      | a required dependency is not installed    |
      | no display is available                   |

Feature: US-13 Tune the controller with sliders

  Scenario Outline: Slider ranges, steps and start values
    When the app starts
    Then the <slider> slider has range <low> to <high>, step 0.1 and start value <start>
    And its current value is shown next to it

    Examples:
      | slider   | low | high | start |
      | Kp       | 0   | 50   | 4     |
      | Ki       | 0   | 20   | 1     |
      | Kd       | 0   | 20   | 3     |
      | setpoint | 0   | 100  | 10    |

  Scenario Outline: A slider cannot go outside its range
    Given the app is running
    When the user moves the <slider> slider to its lowest and then to its highest position
    Then the values used are exactly <low> and <high>
    And no error is shown and nothing is rejected

    Examples:
      | slider   | low | high |
      | Kp       | 0   | 50   |
      | Ki       | 0   | 20   |
      | Kd       | 0   | 20   |
      | setpoint | 0   | 100  |

  Scenario: A gain takes effect while its slider is dragged
    Given the app is running
    When the user drags the Kp slider from 4 to 6 without releasing it
    Then the controller uses each new Kp value from the next simulation step
    And the value shown next to the slider is the value in use
    And no new metrics row is added

  Scenario: The setpoint changes only when the slider is released
    Given the app is running with setpoint 10 m
    When the user drags the setpoint slider through several values without releasing it
    Then the controller's setpoint stays 10 m
    And no new metrics row is added
    When the user releases the slider at 25 m
    Then the setpoint becomes 25 m from the next step
    And exactly one new metrics row is added

  Scenario: Releasing the setpoint slider at the current setpoint changes nothing
    Given the app is running with setpoint 10 m
    When the user drags the setpoint slider away and releases it at 10 m
    Then no setpoint change is made and no metrics row is added (Round 2, OQ-33)

  Scenario: The GUI has no manual thrust
    Then the window has no control for setting the thrust directly
    And the controller stays on for the whole session

Feature: US-14 Live plots

  Scenario: The plots show setpoint, altitude and the thrust used
    Given the app is running
    Then the first plot shows altitude and setpoint in m
    And the second plot shows the thrust actually used in N, with lines at 0 N and 30 N
    And both plots share a time axis

  Scenario: The plots show the last 20 s, scrolling
    Given the app has run for 35 s of simulated time
    Then the time axis shows 15 s to 35 s
    And points from before 15 s are no longer drawn
    But the simulation still holds all records from time 0

  Scenario: Before 20 s the time axis shows 0 to 20 s
    Given the app has run for 5 s of simulated time
    Then the time axis shows 0 s to 20 s

  Scenario: The plotted thrust is the capped thrust, never the raw command
    Given a setpoint change large enough that the controller commands more than 30 N
    Then the thrust plot shows 30 N for those steps, never more
    And it never shows less than 0 N

  Scenario: The frame rate is shown
    Given the app is running
    Then the window shows the measured frame rate

  Scenario: The average frame rate over 5 s is above 30 fps
    Given the live app on the development machine
    When it runs for 5 s
    Then the average frame rate is above 30 frames per second

  Scenario: One slow frame does not fail the frame-rate check
    Given a 5 s run in which one frame takes longer than 1/30 s
    And the average frame rate is above 30 frames per second
    Then the frame-rate check passes

  Scenario Outline: An average of 30 fps or less fails the frame-rate check
    Given a 5 s run with an average frame rate of <fps> frames per second
    Then the frame-rate check fails and states the measured average

    Examples:
      | fps  |
      | 30   |
      | 29.9 |

  Scenario: The plots stop changing while paused
    Given the app is running
    When the user pauses
    Then no new points are added to the plots until the user resumes

Feature: US-15 Metrics after each setpoint change

  Scenario: One row per setpoint change, newest on top
    Given the app started with setpoint 10 m
    When the user later releases the setpoint slider at 25 m and then at 5 m
    Then the metrics table has three rows, in this order: the change to 5 m, the change to 25 m, the start with 10 m
    And each row shows the time of the change, from → to altitude, rise time (s), overshoot (%), settling time (s) and steady-state error (m)

  Scenario: The newest row updates live
    Given a setpoint change has just been made
    When the response develops
    Then the newest row is recomputed as new steps arrive (Round 2, OQ-29)
    And older rows keep the values of their finished results

  Scenario: The shown metrics equal the simulation's metrics
    Given the app has made several setpoint changes
    Then every shown value equals the matching Round 2 step_metrics() value, rounded for display only

  Scenario: A metric that is not reached is shown as such, not as a number
    Given a setpoint change whose response has not reached a metric (NaN in Round 2)
    Then that metric is shown as "not reached"
    And it is never shown as "nan", 0 or blank

  Scenario: Reset clears the metrics table
    Given the metrics table has rows
    When the user resets
    Then the table holds only the new start row

Feature: US-16 Wind gust disturbance

  Scenario: A gust is a 5 N downward force for 100 steps
    Given the app is running
    When the user presses the gust button
    Then the next 100 steps (0.5 s) each include an extra downward force of 5 N on top of gravity, thrust and drag
    And the step after those 100 has no extra force

  Scenario: A press during a gust restarts it instead of adding to it
    Given a gust started 40 steps ago
    When the user presses the gust button again
    Then the extra force stays 5 N, never 10 N
    And it lasts for 100 steps from the second press

  Scenario: The controller recovers after a gust
    Given the drone is holding 10 m
    When the user presses the gust button
    Then at the end of the gust the altitude is lower than in an identical run without the gust
    And after 30 s the distance to the setpoint is smaller than the largest distance during the gust

  Scenario: A gust on the ground does not push the drone below the ground
    Given the drone is on the ground
    When a gust acts on it
    Then the altitude stays 0 and the Round 1 floor rule applies

  Scenario: Gusts are deterministic
    Given two simulations with the same start values, slider changes and gust presses at the same steps
    Then their records are bit-identical

  Scenario: Without a gust press there is no disturbance
    Given the gust button has not been pressed
    Then every step follows the Round 2 controlled step exactly

  Scenario: The gust button does nothing while paused
    Given the app is paused
    Then the gust button is disabled
    And pressing it starts no gust, either now or after resuming

Feature: US-17 Pause and reset

  Scenario: Pause and resume
    Given the app is running
    When the user pauses
    Then the simulation takes no more steps
    When the user resumes
    Then it continues from exactly the paused state, with no jump in time or altitude

  Scenario: Sliders work while paused and apply on resume
    Given the app is paused after step k
    When the user moves the Kd slider to 5 and releases the setpoint slider at 20 m
    Then the shown values are 5 and 20 m
    And the setpoint change counts at step k: its metrics row has its change at the paused time
    And the first step after resuming uses Kd 5 and setpoint 20 m

  Scenario: Reset returns to the start and keeps the slider values
    Given the app has run with sliders changed to Kp 6, Ki 0.5, Kd 2, setpoint 20 m, with a gust in progress
    When the user resets
    Then the simulated time is 0 and the drone is on the ground at rest
    And the controller is on with Kp 6, Ki 0.5, Kd 2 and setpoint 20 m, with its integral at 0
    And the plots, the earlier metrics rows and the earlier records are cleared
    And no gust is acting

  Scenario Outline: Reset keeps the pause state
    Given the app is <state>
    When the user resets
    Then the app is still <state>

    Examples:
      | state   |
      | running |
      | paused  |

Feature: US-18 Clear error messages instead of crashes

  Scenario: An unexpected error is reported, not a crash
    Given the app is running
    When an unexpected error happens inside it
    Then a short plain message saying what happened is shown in the window
    And no traceback is shown to the user
    And the simulation pauses and the app stays open

  Scenario: A rejected simulation request is shown with its message
    Given the simulation rejects a request with an error that names the setting (Rounds 1 and 2)
    When that happens in the app
    Then the user sees that message in the window
    And the simulation pauses and the app stays open

  Scenario: The user can continue after an error
    Given an error message is shown and the simulation is paused
    When the user presses Reset
    Then the app restarts from time 0 as in US-17

Feature: US-19 README and one-command start and test

  Scenario: The README covers setup, start, tests and the metrics
    Given a fresh clone of the repository
    Then the README states the supported Python version (3.12 or newer)
    And it gives the setup command "python -m pip install -e .[dev]", the start command "python -m kuava_sim" and the test command "python -m pytest"
    And it defines rise time, overshoot, settling time and steady-state error exactly as Round 2 does (DESIGN_0bfd04e.md, OQ-30), including "not reached"

  Scenario: One command runs every test
    Given the project is set up
    When the user runs "python -m pytest"
    Then every test in the repository runs, including the GUI tests and the python-control comparisons

  Scenario: The test command reports a failing test
    Given one test is broken on purpose
    When the user runs "python -m pytest"
    Then it reports the failure and exits with a non-zero code
```

## Open Questions

Most important first. All answered by the operator on 2026-11-14 ("All a"); each answer chose the recommended option.

| ID | Question | Raised By | Status | Resolution |
|---|---|---|---|---|
| OQ-34 | **How fast does the live simulation run?** (a) Real time: one simulated second per wall-clock second. Each frame takes as many whole 200 Hz steps as real time has passed since the last frame; if the computer falls behind, the backlog is dropped (the simulation slows down) instead of jumping ahead; (b) as fast as possible, as in Rounds 1 and 2; (c) a speed choice (for example 0.5×, 1×, 2×). **Recommendation: (a).** Gusts and slider changes are only meaningful to watch at real speed; (c) is extra. The step itself stays fixed at 200 Hz and deterministic. | requirement-analysis | Resolved | "OQ-34 a" — real time so I can watch it → Round 3 model above; US-12 … US-19 |
| OQ-35 | **What is a wind gust?** (a) One button. Each press adds a fixed downward force of 5 N for 0.5 s (100 steps), starting with the next step, on top of gravity, thrust and drag; a press during a gust restarts the 0.5 s instead of adding a second force; the gust is part of the simulation core, so it is deterministic and testable without the GUI; the controller is not told about it; (b) as (a) but the force is upward; (c) as (a) but size, duration and direction are settings in the GUI; (d) a vertical wind speed acting through the drag, `D = −b·(v − w)`, so it has no effect when the drag is 0. **Recommendation: (a).** A downward push is easy to see with the 1 kg default drone (about half its weight) and the controller can still recover within the 30 N limit. | requirement-analysis | Resolved | "OQ-35 a" — one 5 N push down for 0.5 s → Round 3 model above; US-12 … US-19 |
| OQ-36 | **Sliders, start values and the drone.** (a) Ranges Kp 0–50 N/m, Ki 0–20 N/(m·s), Kd 0–20 N·s/m, setpoint 0–100 m, all in steps of 0.1, with the current value shown next to each slider; start values Kp 4, Ki 1, Kd 3, setpoint 10 m; the drone is fixed (mass 1 kg, gravity 9.81 m/s², drag 0.5 N·s/m, maximum thrust 30 N, start on the ground at rest); the controller is on from the start and the GUI has no manual thrust; gains apply live while a slider is dragged; the setpoint applies once when the slider is released, so one drag is one setpoint change and one metrics result; (b) as (a) but the setpoint also applies live while dragging (every value passed is a setpoint change with its own metrics result); (c) as (a) plus inputs for mass, drag and maximum thrust. **Recommendation: (a).** These are the Round 2 test values; live setpoint dragging would flood the metrics with tiny changes. | requirement-analysis | Resolved | "OQ-36 a" — setpoint only changes when I let go → Round 3 model above; US-12 … US-19 |
| OQ-37 | **Pause and reset.** (a) One Pause/Resume button. While paused, sliders can still be moved and take effect when stepping resumes (a setpoint change counts at the paused step); the gust button is disabled. Reset returns to time 0 with the start state, keeps the current slider values, turns the controller on with them, clears plots and metrics, cancels any gust, and leaves the pause state as it was; (b) as (a) but reset also puts the sliders back to their start values; (c) as (a) but every control except Resume and Reset is disabled while paused. **Recommendation: (a).** It lets you set up the next experiment while paused and repeat it after a reset. | requirement-analysis | Resolved | "OQ-37 a" — sliders work while paused, reset keeps them → Round 3 model above; US-12 … US-19 |
| OQ-38 | **What do the plots show?** (a) Two plots on a shared time axis showing the last 20 s, scrolling: altitude and setpoint (m), and controller output = the thrust actually used after capping (N), with the 0 N and 30 N limits marked. Older points leave the plot, but all records are kept (about 35 MB per simulated hour, the limit deferred from OQ-22); reset clears them; (b) as (a) but the plots show the whole run since the last reset; (c) as (a) but the controller output is the command before capping (it can go below 0 N or above 30 N). **Recommendation: (a).** A fixed window keeps redraws fast enough for 30 fps; the used thrust is what the drone really gets. | requirement-analysis | Resolved | "OQ-38 a" — last 20 s and real thrust → Round 3 model above; US-12 … US-19 |
| OQ-39 | **How are the metrics shown?** (a) A table with one row per setpoint change (including the start), newest at the top: time of the change, from → to altitude, rise time (s), overshoot (%), settling time (s), steady-state error (m). The newest row updates live as the response develops (Round 2 OQ-29), "not reached" is shown for NaN, and values are rounded for display only; reset clears the table; (b) only the latest result; (c) a row appears only at the next setpoint change, with its final values. **Recommendation: (a).** Matches Round 2 directly and lets you compare tunings side by side. Note: a gust during a result also disturbs that result's metrics. | requirement-analysis | Resolved | "OQ-39 a" — one row per change, newest on top → Round 3 model above; US-12 … US-19 |
| OQ-40 | **How is "above 30 fps" checked?** (a) The app measures its own frame rate and shows it in the window; an automated test runs the live app for 5 s on the development machine and requires an average above 30 frames per second, with every frame containing all steps due; (b) only the on-screen counter, checked by hand; (c) as (a) and also no single frame may take longer than 1/30 s. **Recommendation: (a).** Automated and repeatable; (c) fails on occasional pauses the operating system causes and that the user cannot see. | requirement-analysis | Resolved | "OQ-40 a" — measure the average, one slow frame shouldn't fail it → Round 3 model above; US-12 … US-19 |
| OQ-41 | **Errors and the two commands.** (a) Errors: any error inside the running app is shown in the window as a short message (what happened, in plain words), the simulation pauses and the app stays open; startup problems (missing dependency, no display) print one plain line saying what is missing and how to fix it, and exit with code 1, no traceback. Commands: setup `python -m pip install -e ".[dev]"`, start `python -m kuava_sim`, all tests `python -m pytest` (including GUI tests); (b) as (a) but errors in the running app are shown with the full traceback; (c) as (a) but the app has its own named start command (`kuava-sim`) instead of `python -m`. **Recommendation: (a).** Plain messages for the user; `python -m` works the same on every machine without PATH setup. | requirement-analysis | Resolved | "OQ-41 a" — plain messages and python -m → Round 3 model above; US-12 … US-19 |
