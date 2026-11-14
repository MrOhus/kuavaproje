# Design Session — split from DESIGN.md at commit `0bfd04e`

> Linked from [DESIGN.md](DESIGN.md). This file holds requirement-analysis output produced in a single working session that would otherwise have made the central atlas too large. It is a **permanent linked record** — once a commit/PR lands for this session, its atlas row simply changes from `Active` to `Merged`/`Closed`; this file is never folded back into `DESIGN.md`.

## Scope — Round 2: PID altitude controller and step-response metrics

**In scope (only):**
- A PID controller that sets the drone's thrust from the altitude error, on top of the Round 1 simulation.
- Proportional, integral and derivative gains (Kp, Ki, Kd) and the altitude setpoint, all changeable while the simulation runs.
- Step-response metrics computed after every setpoint change: rise time, overshoot (%), settling time and steady-state error.
- Those metrics match python-control's `step_info` within 2 %.

**Out of scope (explicitly, operator 2026-11-14):** GUI; plots; wind or any disturbance; pause and reset; anti-windup (the integral keeps accumulating while thrust is capped); sensor noise (the controller sees the exact simulated altitude). Wind, pause, reset and the plots are planned for Round 3 together with the GUI. Everything listed as out of scope in Round 1 stays out of scope unless named above.

**Unchanged from Round 1 (applies to this round too):** SI units; fixed 200 Hz step; runs as fast as possible; deterministic on the same machine and code; thrust capped silently to `[0, T_max]`; the ground floor; invalid settings are rejected with a clear error naming the setting; non-finite values are invalid.

### Facts used from python-control (checked against version 0.10.2)

- `step_info(yout, timepts)` takes the **last sample** of the given signal as the steady-state value, and assumes the signal **starts at 0**.
- Defaults: rise time from 10 % to 90 % of the steady-state value; settling time when the signal stays within 2 % of it; overshoot is the peak above the steady-state value in percent of it.
- A value that is never reached is returned as `NaN`.
- It reports a steady-state value but **no steady-state error**.

These facts shaped OQ-26, OQ-29 and OQ-30.

### Units of the gains

With altitude error in m and thrust in N: Kp in N/m, Ki in N/(m·s), Kd in N·s/m.

## User Stories

### US-7: Turn on a PID altitude controller
As a simulation user
I want to turn on a PID controller with gains Kp, Ki, Kd and an altitude setpoint
So that the drone's thrust is set automatically to reach and hold that altitude

### US-8: Change the gains and the setpoint while the simulation runs
As a simulation user
I want to change Kp, Ki, Kd and the setpoint between any two steps
So that I can tune the controller and test new targets without restarting

### US-9: Closed-loop thrust every step
As a simulation user
I want the controller to compute the thrust for every step from the altitude error, within the Round 1 thrust limits
So that the simulated drone flies under feedback control, deterministically

### US-10: Step-response metrics after every setpoint change
As a simulation user
I want rise time, overshoot (%), settling time and steady-state error computed for the response to each setpoint change
So that I can judge and compare controller tunings

### US-11: Metrics agree with python-control
As a simulation user
I want the metrics to match python-control's `step_info` within 2 %
So that I can trust them against a standard reference

### Controller model (from resolved Open Questions)

- The controller is optional. While it is on, it sets the thrust every step and manual thrust commands are rejected (OQ-31).
- Every step (200 Hz), using the altitude `h` and vertical velocity `v` at the start of the step (OQ-28):
  - error `e = setpoint − h`
  - integral contribution `I` accumulates `Ki × e × dt` (N); a Ki change affects only later accumulation (OQ-28)
  - thrust command `T_cmd = m·g + Kp·e + I − Kd·v` (hover feed-forward, OQ-27; derivative on altitude, OQ-28)
  - thrust used `= min(max(T_cmd, 0), T_max)`, capped silently as in Round 1
- No anti-windup: `I` keeps accumulating while the thrust is capped (scope).
- Valid settings (OQ-33): `Kp, Ki, Kd ≥ 0`, setpoint `≥ 0` m, all finite; no upper limits.
- Turning the controller on requires gains and a setpoint and counts as the first setpoint change (OQ-32). Setting the setpoint to its current value does nothing. A gain change never starts a new metrics result (OQ-33).
- Turning the controller off: the held thrust command becomes the controller's last command, and Round 1 open-loop behaviour returns (OQ-31).

### Metrics model (from resolved Open Questions)

- One metrics result per setpoint change (OQ-29). If the change is made after step `k`, the result covers records `k, k+1, …` up to the record of the next change, or up to the latest record if there is no next change yet. It can be read at any time and is recomputed from the records so far.
- The signal is the altitude measured from the altitude at the change, `y = h − h_k`, against the time since the change, `t − t_k`, so it starts at 0 as `step_info` assumes (OQ-30).
- The definitions are `step_info`'s defaults on that signal (OQ-30): final value = last sample; rise time from 10 % to 90 % of the final value; settling time = the time after which the signal stays within 2 % of the final value; overshoot = the peak beyond the final value, in % of the final value.
- Steady-state error = setpoint − final altitude, in m, signed (OQ-30).
- A metric that is never reached is reported as `NaN`, as `step_info` does (OQ-30). Downward steps use the same rules on the negative change.
- Comparison with python-control (OQ-26):
  - (a) Always: each metric matches `step_info` run on the same signal.
  - (b) Only for cases where the thrust never hits a limit and the drone never touches the ground: rise time, overshoot, settling time and steady-state value match `step_info` of a python-control closed-loop model of the same plant and controller.
  - "Within 2 %" means a relative difference of at most 2 % per metric. Steady-state values are compared instead of the error, because `step_info` has no steady-state error.

### Deferred to the next stage (solution-architect)

These are noted here instead of opening new Open Questions (house rule):
- The exact discrete formulation and order of operations of the controller step, for example whether `I` is updated before or after it is used in the same step.
- Metrics for a zero-size step, such as turning on with the setpoint equal to the current altitude. The final change is 0, so the percentages are undefined.
- How "within 2 %" is applied when the reference value is 0 (for example 0 % overshoot) or `NaN`.
- How the continuous python-control model for OQ-26 (b) relates to the 200 Hz semi-implicit Euler simulation.
- Turning the controller on while it is already on, and changing gains or the setpoint while it is off.

## Gherkin Acceptance Criteria

```gherkin
Feature: US-7 Turn on a PID altitude controller

  Scenario: Valid gains and setpoint are accepted
    Given a valid Round 1 simulation
    When the controller is turned on with Kp 4 N/m, Ki 1 N/(m·s), Kd 3 N·s/m and setpoint 10 m
    Then the controller is on
    And it reports exactly those gains and that setpoint back

  Scenario Outline: Gains and setpoint at their lower limit are accepted
    Given a valid Round 1 simulation
    When the controller is turned on with <setting> set to 0 and everything else valid
    Then the controller is on

    Examples:
      | setting  |
      | Kp       |
      | Ki       |
      | Kd       |
      | setpoint |

  Scenario Outline: Negative gains or a setpoint below the ground are rejected with a clear error
    Given a valid Round 1 simulation
    When the controller is turned on with <setting> set to <value> and everything else valid
    Then the request is rejected with an error message that names <setting> and states it must not be below 0
    And the controller stays off and the simulation state and records are unchanged

    Examples:
      | setting  | value  |
      | Kp       | -0.001 |
      | Ki       | -1     |
      | Kd       | -0.001 |
      | setpoint | -0.001 |

  Scenario Outline: Non-finite gains or setpoint are rejected with a clear error
    Given a valid Round 1 simulation
    When the controller is turned on with <setting> set to <value> and everything else valid
    Then the request is rejected with an error message that names <setting>
    And the controller stays off and the simulation state and records are unchanged

    Examples:
      | setting  | value |
      | Kp       | NaN   |
      | Ki       | +Inf  |
      | Kd       | -Inf  |
      | setpoint | NaN   |

  Scenario: Turning on without a setpoint is rejected
    Given a valid Round 1 simulation
    When the controller is turned on with gains but no setpoint
    Then the request is rejected with an error message that names the setpoint
    And the controller stays off

  Scenario: Large setpoints are accepted
    Given a valid Round 1 simulation
    When the controller is turned on with setpoint 100000 m
    Then the controller is on

  Scenario: Turning on counts as the first setpoint change
    Given a simulation that has run 40 steps open-loop and is at altitude h40
    When the controller is turned on with setpoint 10 m
    Then there is exactly 1 metrics result
    And it names the change time 0.2 s, the altitude h40 at that moment and the setpoint 10 m

  Scenario: Taking off from the ground under control
    Given a simulation on the ground at rest, mass 1 kg, gravity 9.81 m/s², maximum thrust 30 N
    When the controller is turned on with Kp 4, Ki 0, Kd 3 and setpoint 10 m, and 200 steps are run
    Then the altitude is above 0 m

  Scenario: Manual thrust is rejected while the controller is on
    Given the controller is on
    When a manual thrust command of 12 N is supplied, by a single step or by "run N steps"
    Then the command is rejected with an error message stating that the controller is on
    And the simulation state, the records and the controller settings are unchanged

  Scenario: Turning the controller off returns Round 1 open-loop behaviour
    Given the controller is on and its last thrust command was C
    When the controller is turned off and a step is performed without a manual command
    Then the held thrust command is C and the thrust used is C capped to the thrust limits
    And manual thrust commands are accepted again
```

```gherkin
Feature: US-8 Change the gains and the setpoint while the simulation runs

  Scenario: Gains can be changed between steps
    Given the controller is on with Kp 4, Ki 1, Kd 3
    When Kp is changed to 6 after step 100
    Then from step 101 on the controller uses Kp 6, and Ki 1 and Kd 3 are unchanged
    And steps 1 to 100 and their records are unchanged

  Scenario: The setpoint can be changed between steps
    Given the controller is on with setpoint 10 m
    When the setpoint is changed to 20 m after step 400
    Then from step 401 on the controller works toward 20 m
    And a new metrics result starts at record 400

  Scenario: Changing Ki affects only the future
    Given the controller is on and its integral contribution is I after step 300
    When Ki is changed to 0 after step 300
    Then the integral contribution used in step 301 is still I
    And it does not change in later steps

  Scenario: A gain change does not start a new metrics result
    Given the controller is on with 1 metrics result
    When Kp, Ki or Kd is changed
    Then there is still exactly 1 metrics result

  Scenario: Setting the same setpoint again does nothing
    Given the controller is on with setpoint 10 m and 1 metrics result
    When the setpoint is set to 10 m again
    Then there is still exactly 1 metrics result and the controller's state is unchanged

  Scenario Outline: An invalid change is rejected and nothing changes
    Given the controller is on with Kp 4 and setpoint 10 m
    When <setting> is changed to <value>
    Then the change is rejected with an error message that names <setting>
    And the gains, the setpoint, the integral, the metrics, the simulation state and the records are unchanged

    Examples:
      | setting  | value |
      | Kp       | NaN   |
      | Ki       | -0.5  |
      | Kd       | +Inf  |
      | setpoint | -1    |
      | setpoint | +Inf  |

  Scenario: Changes take effect from the next step
    Given the controller is on
    When a change is made between two steps
    Then it takes effect from the next step on, and no step is computed with a mix of old and new values
```

```gherkin
Feature: US-9 Closed-loop thrust every step

  Scenario: Thrust follows the controller formula
    Given mass 1 kg, gravity 9.81 m/s², maximum thrust 30 N, the drone at altitude 8 m moving up at 0.5 m/s
    And the controller turned on with Kp 4, Ki 0, Kd 3 and setpoint 10 m
    When one step is computed
    Then the thrust used is 9.81 + 4 × 2 − 3 × 0.5 = 16.31 N within rounding tolerance ε

  Scenario: Holding at the setpoint uses exactly the hover thrust
    Given mass 1.5 kg, gravity 9.81 m/s², the drone at rest at 100 m
    And the controller turned on with Kp 4, Ki 1, Kd 3 and setpoint 100 m
    When 2000 steps are run
    Then after every step the altitude is 100 m and the thrust used is 1.5 × 9.81 N, within rounding tolerance ε

  Scenario: A setpoint change gives no derivative spike
    Given the drone at rest at 100 m with the controller on at setpoint 100 m, Kp 0, Ki 0, Kd 3
    When the setpoint is changed to 110 m and one step is computed
    Then the thrust used in that step is the hover thrust m·g within rounding tolerance ε

  Scenario: The controller's thrust is capped silently at the maximum
    Given maximum thrust 20 N and the controller on with a setpoint far above the drone
    When the controller asks for more than 20 N in a step
    Then the thrust used and recorded in that step is 20 N
    And no warning or error is produced

  Scenario: The controller cannot ask for negative thrust
    Given the controller on with a setpoint far below the drone (but not below the ground)
    When the controller asks for less than 0 N in a step
    Then the thrust used and recorded in that step is 0 N
    And no warning or error is produced

  Scenario: No anti-windup in Round 2
    Given the controller on with Ki 1 and the thrust held at the 20 N limit for 400 steps
    Then the integral contribution after those steps equals the sum of Ki × error × dt over all 400 steps
    And it was never clamped or reset

  Scenario: Closed-loop runs are deterministic
    Given two simulations with identical configuration, controller settings and change sequence
    When both are run 10000 steps
    Then their records and metrics are bit-for-bit identical

  Scenario: The controller sees the exact simulated altitude
    Given the controller on
    When a step is computed
    Then the error used is the setpoint minus the exact altitude at the start of that step (no noise, no delay)
```

```gherkin
Feature: US-10 Step-response metrics after every setpoint change

  Scenario: Each setpoint change gets its own metrics
    Given the controller is turned on with setpoint 10 m
    When the setpoint is later changed to 20 m and then to 15 m
    Then there are three metrics results, one per change, in the order of the changes
    And each result names the time of the change, the altitude at that moment and the new setpoint

  Scenario: A result covers the samples from its change to the next change
    Given setpoint changes after step 100 and after step 900
    Then the first result is computed from records 100 to 900
    And the second from record 900 to the latest record

  Scenario: The latest result can be read at any time and is recomputed
    Given the controller turned on with setpoint 10 m after step 0
    When the result is read after 200 steps and again after 4000 steps
    Then each reading is computed from the records available at that moment, with the last altitude as the final value

  Scenario: Metrics follow step_info's definitions on the relative altitude
    Given a result whose relative altitude signal y = h − h_k is known
    Then rise time is the time from 10 % to 90 % of the final value of y
    And settling time is the time after which y stays within 2 % of its final value
    And overshoot is the peak of y beyond its final value, in % of the final value
    And steady-state error is the setpoint minus the final altitude, in m, signed

  Scenario: A downward step uses the same rules
    Given the controller holding at 20 m
    When the setpoint is changed to 10 m and the drone settles
    Then the result uses y = h − 20 m (a negative change) with the same definitions
    And the steady-state error is 10 m minus the final altitude

  Scenario: A metric that is never reached is reported as NaN
    Given a result whose samples never reach a metric's threshold
    Then that metric is reported as NaN, as step_info reports it
    And the steady-state error is still reported

  Scenario: Metrics are reported in fixed units
    Given a metrics result
    Then rise time and settling time are in s, overshoot is in %, and steady-state error is in m

  Scenario: Rejected setpoint changes create no metrics
    Given the controller on with 2 metrics results
    When a setpoint change is rejected
    Then there are still exactly 2 metrics results and they are unchanged
```

```gherkin
Feature: US-11 Metrics agree with python-control

  Scenario: Metrics match step_info on the same signal
    Given a metrics result
    When python-control's step_info is run on the same relative altitude signal and times
    Then rise time, overshoot and settling time each match step_info within 2 % relative difference
    And the final altitude minus the altitude at the change matches step_info's steady-state value within 2 %

  Scenario: Metrics match a python-control closed-loop model where the model applies
    Given mass 1 kg, gravity 9.81 m/s², drag 0.5 N·s/m, maximum thrust 30 N, and the drone held at 50 m by the controller with Kp 4, Ki 1, Kd 3
    And a setpoint change to 52 m during which the thrust stays strictly between 0 N and 30 N and the drone never touches the ground
    When 30 s are simulated after the change
    Then rise time, overshoot, settling time and steady-state value each match step_info of a python-control closed-loop model of the same plant and controller within 2 %

  Scenario: The model comparison is not claimed where the model does not apply
    Given a setpoint change during which the thrust hits a limit or the drone touches the ground
    Then only the same-signal comparison applies to that result

  Scenario: A difference larger than 2 % fails the check
    Given a metrics result and the matching python-control reference value
    When they differ by more than 2 %
    Then the check fails and names the metric
```

## Open Questions

Most important first. All answered by the operator on 2026-11-14; each answer chose the recommended option.

| ID | Question | Raised By | Status | Resolution |
|---|---|---|---|---|
| OQ-26 | **What does "match python-control's step_info within 2 %" compare?** (a) The same recorded response: our metrics, computed from the simulated altitude after a change, must match `step_info` run on that same altitude signal; (b) the simulation against a model: our metrics must match `step_info` of a python-control closed-loop model (plant 1/(m s² + b s) with the PID) within 2 %; (c) both — (a) always, and (b) only in test cases where the thrust never hits a limit and the drone never touches the ground, because limits and the floor make the real response differ from the linear model. "Within 2 %" means each metric's relative difference is at most 2 %; the steady-state values are compared because `step_info` has no steady-state error. **Recommendation: (c).** (a) proves our calculation is right; (b) proves the simulated loop behaves like the textbook model, which is only fair where the model applies. | requirement-analysis | Resolved | "OQ-26 c" → controller and metrics model above; US-7 … US-11 |
| OQ-27 | **Does the thrust include a hover feed-forward?** (a) Thrust = m·g + PID output, then capped to [0, T_max]; (b) thrust = PID output only, then capped, so the integral has to learn the hover thrust. **Recommendation: (a).** The drone holds altitude without a lasting error even with Ki = 0, and the loop matches the linear python-control model needed for OQ-26 (b). | requirement-analysis | Resolved | "OQ-27 a" → controller and metrics model above; US-7 … US-11 |
| OQ-28 | **The exact PID formula.** (a) Runs every step (200 Hz) on the altitude at the start of the step; derivative on the **altitude** (−Kd × vertical velocity), so a setpoint change gives no thrust spike; the integral accumulates Ki × error × dt, so a Ki change only affects the future; (b) derivative on the **error** (textbook form; a setpoint step gives a one-step spike of Kd × step / 0.005 s, which usually hits the thrust limit); integral as in (a); (c) as (a) but the integral is Ki × (sum of error × dt), so a Ki change also rescales the past. **Recommendation: (a).** No spike, smooth tuning while running, and python-control can still model it exactly. | requirement-analysis | Resolved | "OQ-28 a" → controller and metrics model above; US-7 … US-11 |
| OQ-29 | **When is a metrics result computed, over which samples?** (a) The result for a change covers every step from that change until the next change; it can be read at any time and is recomputed from the samples so far, using the last altitude as the final value (as `step_info` does), so it is only final once enough time has passed; (b) a fixed window after each change (a setting, e.g. 10 s); the result appears when the window ends, and a change before then ends it early, marked incomplete; (c) the result is computed once, at the next setpoint change only. **Recommendation: (a).** Simplest, always available, and identical to running `step_info` on the same samples; the caller decides how long to wait. | requirement-analysis | Resolved | "OQ-29 a" → controller and metrics model above; US-7 … US-11 |
| OQ-30 | **Exact metric definitions.** (a) Use `step_info`'s definitions on altitude measured from the altitude at the change (so the signal starts at 0): rise time 10 %→90 %, settling within 2 %, overshoot as % of the final change; steady-state error = setpoint − final altitude (m, signed); a metric that is never reached is reported as "not reached" (`NaN`, like `step_info`); downward steps use the same rules on the negative change; (b) the same, but rise, overshoot and settling measured relative to the setpoint instead of the final altitude; (c) as (a) but "not reached" is `None`. **Recommendation: (a).** It is exactly what `step_info` does, so OQ-26 (a) can match. | requirement-analysis | Resolved | "OQ-30 a" → controller and metrics model above; US-7 … US-11 |
| OQ-31 | **Turning the controller on and off, and manual thrust.** (a) The controller is optional. While it is on, it sets the thrust every step and a manual thrust command is rejected with a clear error. It can be turned off; the held thrust then stays at the last controller value until a new manual command, and the Round 1 open-loop behaviour returns; (b) while on, a manual command overrides the controller for one step; (c) once on it stays on for the life of the simulation. **Recommendation: (a).** One clear owner of the thrust at any time, and Round 1 behaviour is kept unchanged. | requirement-analysis | Resolved | "OQ-31 a" → controller and metrics model above; US-7 … US-11 |
| OQ-32 | **Does turning the controller on count as a setpoint change?** (a) Yes: turning on requires a setpoint and starts the first metrics result, measured from the altitude at that moment; (b) no: when turned on, the setpoint is the current altitude and the first metrics come with the first change. **Recommendation: (a).** "Turn on with setpoint 10 m" is the natural step test, including a take-off from the ground. | requirement-analysis | Resolved | "OQ-32 a" → controller and metrics model above; US-7 … US-11 |
| OQ-33 | **Valid ranges and repeats.** (a) Gains must be ≥ 0 (negative rejected with a clear error); the setpoint must be ≥ 0 m (below the ground rejected), with no upper limit; setting the same setpoint again does nothing (no new metrics); changing a gain never starts a new metrics result; (b) as (a) but negative gains are allowed; (c) as (a) but setting the same setpoint again starts a new metrics result. **Recommendation: (a).** Negative gains make the loop unstable for this plant, and a repeat setpoint has no step to measure. | requirement-analysis | Resolved | "OQ-33 a" → controller and metrics model above; US-7 … US-11 |
