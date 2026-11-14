# Design & Requirements Atlas

Central index of requirement analysis output for this repository. Individual sessions may split their work into `DESIGN_<commit-id>.md` files (see [requirement-analysis SKILL.md](../../.claude/skills/requirement-analysis/SKILL.md)) when this file grows too large; every such file must be listed below.

## Linked Design Documents

| File | Scope / Topic | Started (commit) | Status |
|---|---|---|---|
| (this file) | Core: Round 1 — deterministic fixed-step altitude simulation | 74c72ce | Active |
| [DESIGN_0bfd04e.md](DESIGN_0bfd04e.md) | Round 2 — PID altitude controller and step-response metrics (US-7 … US-11, OQ-26 … OQ-33) | 0bfd04e | Merged |
| [DESIGN_f351eee.md](DESIGN_f351eee.md) | Round 3 — live desktop GUI, wind gust, pause and reset, README (US-12 … US-19, OQ-34 … OQ-41) | f351eee | Active |

## Scope — Round 1

**In scope (only):**
- A one-dimensional (vertical / altitude) simulation of a drone.
- Physics: gravity, vehicle mass, thrust bounded by thrust limits, linear aerodynamic drag, ground floor at altitude 0.
- Integration on a **fixed time step of exactly 200 steps per second** (`dt` = 0.005 s), not user-changeable (OQ-1).
- Runs **as fast as possible**, never paced to the wall clock (OQ-2).
- **Deterministic**: same machine + same code + same configuration + same inputs ⇒ bit-identical outputs (OQ-13).
- **No controller**: thrust is supplied by the caller each step (OQ-14).
- Output records kept in memory: the initial state plus one record after every step (OQ-15, OQ-21).

**Out of scope (explicitly):** any controller (PID, altitude hold, etc.); real-time pacing / slowing to wall clock (a later app concern, OQ-2); horizontal/3-D motion; attitude/rotation; sensors and noise; estimation/filters; wind/turbulence; battery/energy; motor dynamics, thrust slew rate or lag (OQ-6); reversible/negative thrust (OQ-5, OQ-19); file export of outputs (OQ-15); limiting or pruning stored records (later GUI work, OQ-22); determinism across different machines, OSes, compilers or code versions (OQ-13); visualization/GUI; hardware-in-the-loop; networking/telemetry; multiple vehicles. Technology/language choices are deferred to the solution-architect stage.

### Conventions and model (from resolved Open Questions)

- Units: SI (kg, m, s, N) (OQ-3).
- Altitude `h` is measured upward from the ground; vertical velocity `v` is positive upward.
- `dt` = 1/200 s = 0.005 s, fixed (OQ-1).
- Valid configuration (OQ-3, 5, 10, 16, 17, 24, 25):
  - mass `m > 0`
  - gravity `g > 0` (default 9.81 m/s²)
  - maximum thrust `T_max ≥ 0`; minimum thrust fixed at 0 N
  - drag coefficient `0 ≤ b < 200·m` (i.e. `b·dt/m < 1`)
  - initial altitude `h0 ≥ 0`; if `h0 = 0` then initial velocity `v0 ≥ 0` (defaults `h0 = 0`, `v0 = 0`)
  - all values finite
- Thrust actually used: `T = min(max(T_cmd, 0), T_max)`; values outside the limits are capped silently, no warning or error (OQ-7, OQ-19).
- Drag force: `D = −b · v` (OQ-4).
- Net acceleration: `a = (T − m·g + D) / m`.
- Update order per step — semi-implicit (symplectic) Euler (OQ-12):
  1. `v_next = v + a · dt`
  2. `h_next = h + v_next · dt`
- Ground floor: if `h_next < 0`, then `h_next = 0` and `v_next = 0`; the simulation keeps running (OQ-11). On such a step the record shows what really happened: acceleration 0 and the forces actually acting (OQ-18; see Interpretation I-2).
- Simulated time after `n` steps is `n · dt`.
- Tolerances (OQ-9, OQ-20):
  - **Long-run tolerance**: 0.6 % relative error against the closed-form formula, checked at ≥ 1 s of simulated time (free fall, thrust-driven acceleration, terminal speed).
  - **Rounding tolerance ε**: for values calculable by hand (single steps, simulated time, hover): `|actual − expected| ≤ 1e-12 × max(1, |expected|)` (see Interpretation I-1).

### Interpretations made this round (please check when approving)

No new Open Questions were raised for these, at the operator's request. They are written into the ACs as stated; the operator can correct them at approval.

| ID | Interpretation | Based on |
|---|---|---|
| I-1 | "Tiny computer rounding" is quantified as `ε = 1e-12 × max(1, |expected|)`. Simulated time after many steps uses this tolerance, not 0.6 %, because it is calculable by hand. | OQ-20 |
| I-2 | On a floor step (and when resting on the ground), "the forces actually acting" means: thrust used = the thrust actually applied, drag = `−b × 0 = 0` (the recorded velocity is 0), acceleration = 0. | OQ-18 |
| I-3 | The time-0 record holds the initial altitude and velocity, thrust used 0 N (the initial held command), drag `−b·v0`, and acceleration `(0 − m·g − b·v0)/m`, except that when starting on the ground at rest it holds acceleration 0 and drag 0 (same "what really happens" rule as I-2). | OQ-18, OQ-21 |
| I-4 | "Hovering should stay at the same height" is checked with the rounding tolerance ε, with the hover thrust supplied as `m × g`. | OQ-20 |

### Deferred to the next stage (solution-architect)

- If a step lands with `h_next` exactly 0 and `v_next < 0`, the floor rule (`h_next < 0`) does not trigger on that step. The architect should decide whether the floor condition is `< 0` or `≤ 0 with v < 0`. This does not change any AC below.
- Exact floating-point formulation and order of operations (needed for bit-identical determinism and for hover to stay within ε).

## User Stories

### US-1: Configure the simulation
As a simulation user
I want to set the drone's mass, gravity, maximum thrust, drag coefficient, initial altitude and initial vertical velocity before a run
So that I can simulate a specific vehicle under known conditions

### US-2: Advance the simulation in fixed time steps
As a simulation user
I want the simulation to advance only in fixed 5 ms steps (200 Hz), as fast as possible, for as many steps as I decide
So that results are reproducible and independent of host timing

### US-3: Compute vertical dynamics from gravity, thrust and drag
As a simulation user
I want each step to update vertical velocity and then altitude from gravity, the limited thrust and linear drag acting on the drone's mass, with the ground acting as a floor
So that the simulated altitude behaves physically plausibly

### US-4: Deterministic runs
As a simulation user
I want two runs on the same machine with the same code, configuration and thrust inputs to produce exactly the same numbers
So that I can reproduce, compare and regression-test simulation output

### US-5: Open-loop thrust input (no controller)
As a simulation user
I want to supply the thrust command myself each step, with the last command held if I give none, and no controller in the simulation
So that the plant model can be validated in isolation before any controller is added

### US-6: Output records
As a simulation user
I want the starting state and the state after every step (time, altitude, velocity, acceleration, thrust used, drag) saved in memory
So that I can inspect and test the simulated trajectory

## Gherkin Acceptance Criteria

```gherkin
Feature: US-1 Configure the simulation

  Scenario: Valid configuration is accepted
    Given a configuration with mass 1.5 kg, gravity 9.81 m/s², maximum thrust 30 N, drag coefficient 0.2 N·s/m, initial altitude 10 m and initial vertical velocity 1 m/s
    When the simulation is created with this configuration
    Then the simulation is created successfully
    And it reports exactly those values back
    And it reports a step rate of 200 Hz and a step length of 0.005 s
    And it reports a minimum thrust of 0 N

  Scenario: Defaults are applied when optional values are omitted
    Given a configuration that sets only mass 1.5 kg and maximum thrust 30 N
    When the simulation is created
    Then gravity is 9.81 m/s²
    And initial altitude is 0 m and initial vertical velocity is 0 m/s
    And the held thrust command is 0 N

  Scenario: Gravity can be changed from the default
    Given a configuration with gravity 3.71 m/s²
    When the simulation is created
    Then it reports gravity 3.71 m/s²

  Scenario Outline: Gravity of 0 or less is rejected with a clear error
    Given a configuration that is otherwise valid
    When the simulation is created with gravity <g> m/s²
    Then creation is rejected with an error message that names gravity and states it must be greater than 0
    And no simulation instance is produced

    Examples:
      | g     |
      | 0     |
      | -9.81 |

  Scenario: Smallest positive gravity is accepted
    Given a configuration that is otherwise valid
    When the simulation is created with gravity 0.001 m/s²
    Then the simulation is created successfully

  Scenario: The step rate cannot be changed by the user
    Given a configuration that attempts to set a step rate of 400 Hz (or a step length other than 0.005 s)
    When the simulation is created
    Then no such configuration option exists or creation is rejected with an error identifying the step rate
    And no simulation instance runs at any rate other than 200 Hz

  Scenario: The minimum thrust cannot be changed by the user
    Given a configuration that attempts to set a minimum thrust of 2 N
    When the simulation is created
    Then no such configuration option exists or creation is rejected with an error identifying the minimum thrust

  Scenario Outline: Non-positive mass is rejected
    Given a configuration that is otherwise valid
    When the simulation is created with mass <mass> kg
    Then creation is rejected with an error identifying the mass parameter
    And no simulation instance is produced

    Examples:
      | mass |
      | 0    |
      | -1.0 |

  Scenario: Maximum thrust of 0 N is accepted
    Given a configuration that is otherwise valid, with initial altitude 0 and initial velocity 0
    When the simulation is created with maximum thrust 0 N
    Then the simulation is created successfully
    And after 200 steps with a commanded thrust of 50 N, altitude is still 0 m and thrust used is 0 N in every record

  Scenario: Negative maximum thrust is rejected
    Given a configuration that is otherwise valid
    When the simulation is created with maximum thrust -0.001 N
    Then creation is rejected with an error identifying the maximum thrust
    And no simulation instance is produced

  Scenario: Negative drag coefficient is rejected
    Given a configuration that is otherwise valid
    When the simulation is created with drag coefficient -0.1 N·s/m
    Then creation is rejected with an error identifying the drag parameter
    And no simulation instance is produced

  Scenario Outline: Drag coefficient below 200 × mass is accepted
    Given a configuration with mass 1 kg that is otherwise valid
    When the simulation is created with drag coefficient <b> N·s/m
    Then the simulation is created successfully

    Examples:
      | b       |
      | 0       |
      | 199.999 |

  Scenario Outline: Drag coefficient of 200 × mass or more is rejected with a clear error
    Given a configuration with mass <m> kg that is otherwise valid
    When the simulation is created with drag coefficient <b> N·s/m
    Then creation is rejected with an error message that names the drag coefficient, states that it must be below 200 × mass (<limit> N·s/m) and says the simulation would become unstable
    And no simulation instance is produced

    Examples:
      | m   | b       | limit |
      | 1   | 200     | 200   |
      | 1   | 200.001 | 200   |
      | 2.5 | 500     | 500   |

  Scenario Outline: Valid initial altitude and velocity combinations are accepted
    Given a configuration that is otherwise valid
    When the simulation is created with initial altitude <h0> m and initial velocity <v0> m/s
    Then the simulation is created successfully

    Examples:
      | h0  | v0  |
      | 0   | 0   |
      | 0   | 3   |
      | 10  | -5  |

  Scenario Outline: Starting below the ground is rejected with a clear error
    Given a configuration that is otherwise valid
    When the simulation is created with initial altitude <h0> m
    Then creation is rejected with an error message that names the initial altitude and states it must not be below 0
    And no simulation instance is produced

    Examples:
      | h0     |
      | -0.001 |
      | -10    |

  Scenario: Starting on the ground while moving down is rejected with a clear error
    Given a configuration that is otherwise valid
    When the simulation is created with initial altitude 0 m and initial velocity -0.001 m/s
    Then creation is rejected with an error message stating that the drone cannot start on the ground while moving down
    And no simulation instance is produced

  Scenario Outline: Non-finite parameters are rejected
    Given a configuration that is otherwise valid
    When the simulation is created with <parameter> set to <value>
    Then creation is rejected with an error identifying <parameter>
    And no simulation instance is produced

    Examples:
      | parameter                  | value |
      | mass                       | NaN   |
      | gravity                    | NaN   |
      | gravity                    | +Inf  |
      | maximum thrust             | +Inf  |
      | drag coefficient           | NaN   |
      | initial altitude           | +Inf  |
      | initial vertical velocity  | -Inf  |
```

```gherkin
Feature: US-2 Advance the simulation in fixed time steps

  Scenario: Each step advances simulated time by exactly one fixed step
    Given a valid simulation starting at simulated time 0
    When the simulation is advanced by 1 step
    Then the simulated time is 0.005 s within rounding tolerance ε

  Scenario: Simulated time is derived from the step count without drift
    Given a valid simulation starting at simulated time 0
    When the simulation is advanced by 720000 steps
    Then the simulated time is 3600 s within rounding tolerance ε

  Scenario: The simulation never stops by itself
    Given a valid simulation that has already been advanced 720000 steps
    When the caller requests one more step
    Then the step is performed and simulated time increases by 0.005 s within rounding tolerance ε

  Scenario: Run N steps shortcut
    Given a valid simulation in a known state
    When the caller uses "run N steps" with N = 200
    Then the resulting state and output records are bit-for-bit identical to calling single step 200 times with the same thrust command

  Scenario: Running 0 steps does nothing and is not an error
    Given a valid simulation in a known state with 11 records
    When the caller uses "run N steps" with N = 0
    Then no error is produced
    And state, simulated time and the 11 records are unchanged

  Scenario Outline: Invalid N for "run N steps" is rejected
    Given a valid simulation in a known state
    When the caller uses "run N steps" with N = <n>
    Then the request is rejected with an error
    And state, simulated time and output records are unchanged

    Examples:
      | n   |
      | -1  |
      | 2.5 |

  Scenario: Step length cannot vary between steps
    Given a valid simulation
    When the caller attempts to advance with a step length other than 0.005 s
    Then no such operation is available or it is rejected
    And the simulation state is unchanged

  Scenario: Simulation runs as fast as possible, not paced to the wall clock
    Given a valid simulation
    When 200000 steps (1000 s of simulated time) are run back-to-back
    Then the call completes without waiting on the wall clock between steps
    And the wall-clock duration is not bounded below by the simulated duration

  Scenario: Simulated time is independent of wall-clock time
    Given two identical simulations
    When one is advanced 1000 steps back-to-back and the other 1000 steps with a 10 ms wall-clock pause between steps
    Then both report simulated time 5.000 s within rounding tolerance ε
```

```gherkin
Feature: US-3 Vertical dynamics from gravity, thrust and drag

  Scenario: Free fall matches the formula within 0.6 % after 1 s
    Given mass 1 kg, gravity 9.81 m/s², drag coefficient 0, initial altitude 1000 m, initial vertical velocity 0
    When thrust 0 N is commanded for 200 steps (1.0 s)
    Then vertical velocity is within 0.6 % of −9.81 m/s
    And distance fallen (1000 m − altitude) is within 0.6 % of ½ × 9.81 × 1.0² = 4.905 m

  Scenario: Free fall stays within 0.6 % for longer durations
    Given the same configuration as above
    When thrust 0 N is commanded for 400 steps (2.0 s)
    Then vertical velocity is within 0.6 % of −19.62 m/s
    And distance fallen is within 0.6 % of 19.62 m

  Scenario: Velocity is updated before altitude (semi-implicit Euler)
    Given mass 1 kg, gravity 9.81 m/s², drag coefficient 0, initial altitude 1000 m, initial vertical velocity 0
    When thrust 0 N is commanded for exactly 1 step
    Then vertical velocity is −0.04905 m/s within rounding tolerance ε
    And altitude is 999.99975475 m within rounding tolerance ε
    And altitude is not 1000 m (which an altitude-first update would give)

  Scenario: Hover keeps the same height
    Given mass 1.5 kg, gravity 9.81 m/s², drag coefficient 0.2 N·s/m, maximum thrust 30 N, initial altitude 100 m, initial vertical velocity 0
    When thrust 1.5 × 9.81 N is commanded for 2000 steps
    Then after every step altitude is 100 m and vertical velocity is 0 m/s within rounding tolerance ε

  Scenario: Excess thrust accelerates the drone upward
    Given mass 1 kg, gravity 9.81 m/s², drag coefficient 0, maximum thrust 30 N, initial altitude 100 m, initial vertical velocity 0
    When thrust 20 N is commanded for 200 steps (1.0 s)
    Then vertical velocity is within 0.6 % of (20 / 1 − 9.81) × 1.0 = 10.19 m/s

  Scenario: Heavier drone accelerates less for the same thrust
    Given two simulations identical except that mass is 1 kg in one and 2 kg in the other, both with gravity 9.81 m/s², drag 0, maximum thrust 30 N and initial altitude 100 m
    When thrust 25 N is commanded to both for 200 steps (1.0 s)
    Then vertical velocity is within 0.6 % of 15.19 m/s for the 1 kg drone
    And within 0.6 % of 2.69 m/s for the 2 kg drone

  Scenario: Linear drag opposes motion and is proportional to velocity
    Given drag coefficient b = 0.5 N·s/m, mass 1 kg and initial altitude 100 m
    When the drone has vertical velocity +4 m/s, −4 m/s and 0 m/s at the start of a step
    Then the drag used in that step is −2 N, +2 N and 0 N respectively, within rounding tolerance ε

  Scenario: Linear drag limits falling speed to m·g/b
    Given mass 1 kg, gravity 9.81 m/s², drag coefficient 0.5 N·s/m, initial altitude 100000 m, initial vertical velocity 0
    When thrust 0 N is commanded for 20000 steps (100 s)
    Then the falling speed increases monotonically
    And never exceeds m·g/b = 19.62 m/s
    And at the end is within 0.6 % of 19.62 m/s

  Scenario: Thrust above the maximum is capped silently
    Given maximum thrust 20 N
    When a thrust of 25 N is commanded for a step
    Then the thrust used and recorded in that step is 20 N
    And no warning or error is produced

  Scenario: Negative thrust command is set to 0 silently
    Given maximum thrust 20 N and initial altitude 100 m
    When a thrust of -5 N is commanded for a step
    Then the thrust used and recorded in that step is 0 N
    And no warning or error is produced

  Scenario Outline: Thrust at and inside the limits is used as commanded
    Given maximum thrust 20 N
    When a thrust of <cmd> N is commanded for a step
    Then the thrust used and recorded is <cmd> N

    Examples:
      | cmd    |
      | 20     |
      | 19.999 |
      | 0.001  |
      | 0      |

  Scenario: Non-finite thrust command is rejected
    Given a valid simulation in a known state with a held thrust command of 5 N
    When a thrust command of NaN, +Inf or −Inf is supplied
    Then the command is rejected with an error
    And altitude, vertical velocity, simulated time and output records are unchanged
    And the held thrust command remains 5 N

  Scenario: Resting on the ground with insufficient thrust
    Given mass 1 kg, gravity 9.81 m/s², drag 0.5 N·s/m and the default initial state (altitude 0, vertical velocity 0)
    When thrust 5 N is commanded for 200 steps
    Then after every step altitude is 0 m, vertical velocity is 0 m/s, acceleration is 0 m/s², drag is 0 N and thrust used is 5 N
    And simulated time is 1.0 s within rounding tolerance ε

  Scenario: Taking off from the ground
    Given mass 1 kg, gravity 9.81 m/s², maximum thrust 30 N and the default initial state
    When thrust 19.62 N is commanded for 1 step
    Then altitude is greater than 0 m and vertical velocity is greater than 0 m/s

  Scenario: Landing stops at the floor and the run continues
    Given mass 1 kg, gravity 9.81 m/s², drag 0, initial altitude 1 m, initial vertical velocity 0
    When thrust 0 N is commanded for 200 steps
    Then no recorded altitude is below 0 m
    And on the first step whose update would give altitude below 0, the record shows altitude exactly 0 m, vertical velocity exactly 0 m/s, acceleration 0 m/s² and drag 0 N
    And every later step is performed (time keeps advancing) with altitude 0 m and vertical velocity 0 m/s

  Scenario: Landing at speed does not bounce
    Given mass 1 kg, gravity 9.81 m/s², drag 0.5 N·s/m, initial altitude 0.01 m, initial vertical velocity −10 m/s
    When thrust 0 N is commanded for 10 steps
    Then from the landing step on, every record shows altitude 0 m, vertical velocity 0 m/s, acceleration 0 m/s² and drag 0 N
```

```gherkin
Feature: US-4 Deterministic runs (same machine, same code)

  Scenario: Identical inputs yield identical outputs in one process
    Given two simulations with identical configuration and initial state
    When both are advanced 10000 steps with the identical thrust sequence
    Then their output records are bit-for-bit identical at every step

  Scenario: Repeated executions yield identical outputs
    Given a fixed configuration and a fixed thrust sequence
    When the simulation is executed twice in separate processes on the same machine with the same code
    Then the output records of the two executions are bit-for-bit identical

  Scenario: Output does not depend on host timing or load
    Given two identical simulations
    When one runs back-to-back and the other with artificial wall-clock delays between steps
    Then their output records are bit-for-bit identical

  Scenario: Single steps and "run N steps" give identical outputs
    Given two identical simulations and a constant thrust command
    When one is advanced with 1000 single steps and the other with "run N steps" N = 1000
    Then their output records are bit-for-bit identical

  Scenario: A changed input changes the output only from that step on
    Given two simulations with identical configuration, initial altitude 100 m and maximum thrust 30 N
    When both receive the same thrust sequence except that the command at step 500 is 10 N in one and 12 N in the other
    Then output records for times 0 to step 499 are bit-for-bit identical
    And output records from step 500 onward differ
```

```gherkin
Feature: US-5 Open-loop thrust input (no controller)

  Scenario: Held thrust command starts at 0
    Given a newly created simulation with initial altitude 50 m
    When a step is performed without any thrust command having been supplied
    Then the thrust used and recorded in that step is 0 N

  Scenario: The last command is held when no new command is given
    Given maximum thrust 30 N and initial altitude 50 m
    When 15 N is commanded for step 1 and steps 2 and 3 are performed without a new command
    Then the thrust used and recorded in steps 1, 2 and 3 is 15 N

  Scenario: A new command replaces the held command
    Given 15 N has been commanded and held for several steps
    When 10 N is commanded for the next step
    Then the thrust used in that step and in following steps without a new command is 10 N

  Scenario: A held command outside the limits keeps being limited
    Given maximum thrust 20 N and initial altitude 50 m
    When 25 N is commanded for step 1 and step 2 is performed without a new command
    And then -3 N is commanded for step 3 and step 4 is performed without a new command
    Then the thrust used and recorded in steps 1 and 2 is 20 N
    And in steps 3 and 4 it is 0 N

  Scenario: Commanded thrust within limits is applied regardless of state
    Given maximum thrust T_max
    When a thrust T with 0 ≤ T ≤ T_max is commanded
    Then exactly T is used, whatever the altitude or vertical velocity

  Scenario: The simulation does not react to its own state
    Given mass 1 kg, gravity 9.81 m/s², initial altitude 100 m and a constant commanded thrust of 5 N
    When the drone loses altitude over 1000 steps
    Then the thrust used stays 5 N in every step

  Scenario: Rejected command does not replace the held command
    Given a held thrust command of 12 N
    When a non-finite thrust command is supplied and rejected
    And a step is then performed without a new command
    Then the thrust used in that step is 12 N
```

```gherkin
Feature: US-6 Output records

  Scenario: The starting moment is the first record
    Given mass 1 kg, gravity 9.81 m/s², drag 0.5 N·s/m, initial altitude 100 m, initial vertical velocity 2 m/s
    When the simulation is created and no step has been performed
    Then exactly 1 record exists
    And it shows time 0 s, altitude 100 m, vertical velocity 2 m/s, thrust used 0 N, drag −1 N and acceleration (0 − 9.81 − 1) / 1 = −10.81 m/s², within rounding tolerance ε

  Scenario: Starting record on the ground at rest
    Given the default initial state (altitude 0, vertical velocity 0)
    When the simulation is created
    Then the first record shows time 0 s, altitude 0 m, vertical velocity 0 m/s, thrust used 0 N, drag 0 N and acceleration 0 m/s²

  Scenario: One record is added after every step
    Given a valid simulation
    When 250 steps are performed
    Then 251 records are available in memory, in time order, the first at time 0 s and the last at 1.25 s

  Scenario: Each record contains the required fields
    Given a valid simulation
    When a step is performed
    Then the record for that step contains simulated time, altitude, vertical velocity, acceleration, thrust used and drag

  Scenario: Record values match a hand calculation
    Given mass 1 kg, gravity 9.81 m/s², drag coefficient 0.5 N·s/m, maximum thrust 20 N, initial altitude 100 m, initial vertical velocity 2 m/s
    When 15 N is commanded for one step
    Then the second record shows, within rounding tolerance ε:
      | field            | value          |
      | time             | 0.005 s        |
      | thrust used      | 15 N           |
      | drag             | −1 N           |
      | acceleration     | 4.19 m/s²      |
      | vertical velocity| 2.02095 m/s    |
      | altitude         | 100.01010475 m |

  Scenario: Limited thrust is recorded as the thrust actually used
    Given maximum thrust 20 N and initial altitude 100 m
    When 25 N is commanded for one step and −5 N for the next
    Then the records show thrust used 20 N and 0 N, not 25 N and −5 N

  Scenario: Records keep growing without a limit
    Given a valid simulation
    When 720000 steps are performed
    Then 720001 records are available and none have been dropped

  Scenario: Rejected operations add no records
    Given a valid simulation with 10 records
    When a non-finite thrust command is supplied, or "run N steps" with N = −1 is requested
    Then there are still exactly 10 records and they are unchanged
```

## Open Questions

| ID | Question | Raised By | Status | Resolution |
|---|---|---|---|---|
| OQ-1 | Is the step rate user-configurable (any value ≥ 200 Hz), or a single fixed rate (e.g. exactly 200 Hz, 250 Hz, 1 kHz)? If configurable, is there an upper bound, and must 1/rate be exact in binary (e.g. powers of two)? | requirement-analysis | Resolved | "Keep it at 200 steps per second. Users can't change it." → US-1, US-2 |
| OQ-2 | Does "running at 200 Hz" mean real-time pacing against the wall clock (each step every 5 ms of real time), or only that the simulated step is ≤ 5 ms while running as fast as possible? | requirement-analysis | Resolved | "Don't use the real clock. Run as fast as possible. The app will slow it down later." → US-2; pacing out of scope |
| OQ-3 | Is gravity configurable or a fixed constant? If fixed, which value (9.80665 m/s², 9.81 m/s², other)? Are all quantities in SI units (kg, N, m, s)? | requirement-analysis | Resolved | "Gravity can be changed, starting at 9.81. Use normal units: kg, meters, seconds, newtons." → US-1, conventions |
| OQ-4 | Which drag model: linear (F = −b·v), quadratic (F = −½ρC_dA·v·\|v\|, or −k·v·\|v\|), or something else? Which parameters are exposed (single coefficient vs. ρ, C_d, A)? | requirement-analysis | Resolved | "Air resistance is simple: faster means more resistance, in a straight line (drag = -b times speed)." → linear D = −b·v, US-3 |
| OQ-5 | What are the thrust limits' semantics: is minimum thrust always 0, may it be > 0 (idle thrust), may it be negative (reversible props)? | requirement-analysis | Resolved | "Thrust can't go below 0. The maximum can be set." → min fixed at 0, max configurable, US-1 |
| OQ-6 | Does "thrust limits" include only magnitude limits, or also a rate limit / motor response lag (thrust slew rate, first-order delay)? | requirement-analysis | Resolved | "Motors react instantly. Only min and max limits." → no motor dynamics; out of scope |
| OQ-7 | When the commanded thrust is outside the limits, should it be saturated (clamped) silently, clamped with a warning/flag, or rejected as an error? | requirement-analysis | Resolved | "Too much thrust: just cap it at the max, no warnings. But save the thrust actually used." → US-3, US-6 |
| OQ-8 | How is a run bounded: a configured duration, a configured step count, or stepped indefinitely by the caller? | requirement-analysis | Resolved | "It never stops by itself. Whoever runs it decides when to stop. Add a 'run N steps' shortcut for tests." → US-2 |
| OQ-9 | What numerical tolerances are acceptable for the physics ACs (e.g. absolute/relative error on altitude, velocity, time)? | requirement-analysis | Resolved | "Free fall must be within 0.6% of the formula, checked after 1 second or more." → US-3 (extended by OQ-20) |
| OQ-10 | Are initial altitude and initial vertical velocity configurable? What are the defaults (e.g. on the ground at rest)? | requirement-analysis | Resolved | "Start height and speed can be set. Default is on the ground, not moving." → US-1 |
| OQ-11 | What happens at the ground (altitude 0)? Options: hard floor (altitude clamped at 0, velocity zeroed), no ground at all (altitude may go negative), crash/terminate the run, or something else. Does the drone start on the ground? | requirement-analysis | Resolved | "The ground is a floor. It can't go below 0. Speed becomes 0 when it lands, and it keeps running." → US-3 |
| OQ-12 | Is a specific integration method required (explicit Euler, semi-implicit/symplectic Euler, RK4, exact analytic), or is it the architect's choice subject to the tolerances in OQ-9? | requirement-analysis | Resolved | "Each step, update the speed first, then the height (semi-implicit Euler)." → conventions, US-3 |
| OQ-13 | What scope does "fully deterministic" cover: same process, same machine/build, or bit-identical across OSes, CPUs and compilers? | requirement-analysis | Resolved | "Same computer and same code must give exactly the same numbers." → US-4; cross-platform out of scope |
| OQ-14 | How is the open-loop thrust supplied: per-step programmatic input, a predefined time profile (e.g. file/table), or both? If a step is requested without a new command, should it be rejected, hold the last value, or default to 0? | requirement-analysis | Resolved | "I give the thrust each step. If I don't, keep the last one. Start at 0." → US-5 |
| OQ-15 | What does the simulation output (altitude, velocity, acceleration, applied thrust, drag force, time?), at what rate (every step?), and in what form (in-memory API, CSV, other)? | requirement-analysis | Resolved | "After every step, save time, height, speed, acceleration, thrust used and drag, in memory." → US-6 |
| OQ-16 | Which gravity values are valid? Should gravity = 0 and negative gravity be accepted or rejected? Is there an upper bound? | requirement-analysis | Resolved | "Gravity of 0 or less isn't allowed. Show a clear error." → US-1 (no upper bound beyond finite) |
| OQ-17 | How should an initial altitude below 0 be handled (reject the configuration, or clamp to 0)? If the drone starts at altitude 0 with a downward initial velocity, should that be rejected or should the velocity be zeroed? | requirement-analysis | Resolved | "Starting below the ground isn't allowed, and neither is starting on the ground while moving down. Show a clear error." → US-1 |
| OQ-18 | On a step where the ground floor is applied, what is recorded as acceleration and drag: the values computed from forces before the floor (e.g. −g at rest with zero thrust), or the effective values after the floor (acceleration 0)? | requirement-analysis | Resolved | "When it hits the floor, save what really happened: acceleration 0, and the forces that are actually acting." → US-3, US-6 (Interpretations I-2, I-3) |
| OQ-19 | A negative thrust command (e.g. −5 N): should it be capped to 0 N silently (like the maximum), or rejected as an error? | requirement-analysis | Resolved | "If the thrust command is negative, just make it 0. Don't show an error, because the PID will do this a lot." → US-3, US-5, US-6 |
| OQ-20 | Your 0.6 % tolerance covers free fall. What tolerances apply to the other checks: hover equilibrium, thrust-driven acceleration, terminal speed, single-step values, and simulated time after many steps? Should those be exact, or within some error? | requirement-analysis | Resolved | "Use the same 0.6% for anything that runs over a long time, like free fall. For a single step that I can calculate by hand, it should match almost exactly, with only tiny computer rounding allowed. Hovering should stay at the same height." → conventions (Interpretations I-1, I-4) |
| OQ-21 | Should the initial state (time 0, initial altitude and velocity) also be saved as a record, or only the states after each step? | requirement-analysis | Resolved | "Yes, save the starting moment at time 0 as the first record." → US-6 (Interpretation I-3) |
| OQ-22 | The run never stops by itself, but every step is saved in memory, so memory grows without limit (≈ 17 million records per day of simulated time). Should there be a limit or a way to clear or read off old records, or is unlimited growth acceptable for this round? | requirement-analysis | Resolved | "Letting the records grow is fine for now. We can limit it later in the GUI part." → US-6; limiting out of scope |
| OQ-23 | "Run N steps" with N = 0: do nothing, or reject as an error? | requirement-analysis | Resolved | "Running 0 steps just does nothing. It's not an error." → US-2 |
| OQ-24 | With linear drag and semi-implicit Euler at dt = 0.005 s, velocity oscillates if b·dt/m ≥ 1 (b ≥ 200·m) and becomes unstable if b·dt/m ≥ 2. Should such configurations be rejected, accepted with that behaviour, or otherwise handled? | requirement-analysis | Resolved | "If air resistance is set way too high (200 x mass or more), show a clear error, because the simulation breaks." → US-1 |
| OQ-25 | Is a maximum thrust of exactly 0 N a valid configuration (drone can never produce thrust), or must it be greater than 0? | requirement-analysis | Resolved | "Max thrust of 0 is allowed. The drone just can't fly." → US-1 |
