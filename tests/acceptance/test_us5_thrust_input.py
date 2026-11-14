"""US-5 Open-loop thrust input (no controller) — acceptance tests.

Expected behaviour comes from docs/design/DESIGN.md (US-5 Gherkin ACs) and
the Simulation model in docs/architecture/ARCHITECTURE.md: the raw last
accepted command is held and capped to [0, max_thrust] each time it is used;
a rejected command changes nothing; step(thrust) holds the new command;
run(n, thrust) applies it to the first step and then holds it.
"""

import math

import pytest

from kuava_sim import SimConfig, Simulation


def make(**cfg):
    cfg.setdefault("mass", 1.0)
    cfg.setdefault("gravity", 9.81)
    cfg.setdefault("max_thrust", 30.0)
    cfg.setdefault("initial_altitude", 50.0)
    return Simulation(SimConfig(**cfg))


def used(sim):
    """Thrust used in steps 1, 2, … (the time-0 record is not a step)."""
    return list(sim.records.column("thrust_used")[1:])


# --- Scenario: Held thrust command starts at 0 --------------------------------


def test_held_thrust_command_starts_at_zero():
    sim = make()
    assert sim.held_thrust == 0.0
    sim.step()
    assert used(sim) == [0.0]
    sim.run(3)
    assert used(sim) == [0.0, 0.0, 0.0, 0.0]
    assert sim.altitude < 50.0  # with 0 N the drone really falls


# --- Scenario: The last command is held when no new command is given ----------


def test_last_command_is_held_when_no_new_command_is_given():
    sim = make(max_thrust=30.0)
    sim.step(15.0)
    sim.step()
    sim.step()
    assert used(sim) == [15.0, 15.0, 15.0]
    assert sim.held_thrust == 15.0


def test_run_applies_the_command_to_the_first_step_and_then_holds_it():
    sim = make()
    sim.run(3, thrust=7.0)
    sim.run(2)
    assert used(sim) == [7.0] * 5


# --- Scenario: A new command replaces the held command ------------------------


def test_new_command_replaces_the_held_command():
    sim = make()
    sim.step(15.0)
    sim.run(4)
    sim.step(10.0)
    sim.run(3)
    assert used(sim) == [15.0] * 5 + [10.0] * 4
    assert sim.held_thrust == 10.0


def test_new_zero_command_replaces_the_held_command():
    sim = make()
    sim.step(15.0)
    sim.step(0.0)
    sim.step()
    assert used(sim) == [15.0, 0.0, 0.0]


# --- Scenario: A held command outside the limits keeps being limited ----------


def test_held_command_outside_limits_keeps_being_limited():
    sim = make(max_thrust=20.0)
    sim.step(25.0)
    sim.step()
    assert sim.held_thrust == 25.0  # the raw command is held (ARCHITECTURE.md)
    sim.step(-3.0)
    sim.step()
    assert sim.held_thrust == -3.0
    assert used(sim) == [20.0, 20.0, 0.0, 0.0]


@pytest.mark.parametrize(
    "cmd, expected",
    [
        (math.nextafter(20.0, math.inf), 20.0),
        (20.0, 20.0),
        (math.nextafter(20.0, 0.0), math.nextafter(20.0, 0.0)),
        (math.nextafter(0.0, 1.0), math.nextafter(0.0, 1.0)),
        (0.0, 0.0),
        (math.nextafter(0.0, -1.0), 0.0),
    ],
    ids=["20+eps", "20", "20-eps", "0+eps", "0", "0-eps"],
)
def test_held_command_at_the_limits_is_used_the_same_on_every_step(cmd, expected):
    sim = make(max_thrust=20.0)
    sim.step(cmd)
    sim.run(4)
    assert used(sim) == [expected] * 5


# --- Scenario: Commanded thrust within limits is applied regardless of state --

STATES = {
    "on the ground at rest": dict(initial_altitude=0.0, initial_velocity=0.0),
    "on the ground moving up": dict(initial_altitude=0.0, initial_velocity=3.0),
    "high and falling fast": dict(initial_altitude=500.0, initial_velocity=-40.0),
    "high and rising fast": dict(initial_altitude=500.0, initial_velocity=40.0),
    "about to land": dict(initial_altitude=0.01, initial_velocity=-10.0),
}


@pytest.mark.parametrize("state", STATES, ids=list(STATES))
@pytest.mark.parametrize("thrust", [0.0, 0.001, 12.5, 29.999, 30.0])
def test_thrust_within_limits_is_used_exactly_whatever_the_state(state, thrust):
    sim = make(max_thrust=30.0, drag_coeff=0.5, **STATES[state])
    sim.run(20, thrust=thrust)
    assert used(sim) == [thrust] * 20


# --- Scenario: The simulation does not react to its own state -----------------


def test_simulation_does_not_react_to_its_own_state():
    sim = make(mass=1.0, gravity=9.81, initial_altitude=100.0)
    sim.run(1000, thrust=5.0)
    assert used(sim) == [5.0] * 1000
    altitude = sim.records.column("altitude")
    assert all(b < a for a, b in zip(altitude, altitude[1:]))  # loses altitude
    assert altitude[-1] < 100.0 - 50.0  # about 60 m lost in 5 s


# --- Scenario: Rejected command does not replace the held command -------------


@pytest.mark.parametrize(
    "bad, error",
    [(math.nan, ValueError), (math.inf, ValueError), (-math.inf, ValueError), (True, TypeError), ("12", TypeError)],
    ids=["nan", "+inf", "-inf", "bool", "str"],
)
def test_rejected_command_does_not_replace_the_held_command(bad, error):
    sim = make()
    sim.step(12.0)
    with pytest.raises(error):
        sim.step(bad)
    with pytest.raises(error):
        sim.run(2, thrust=bad)
    assert sim.held_thrust == 12.0
    sim.step()
    assert used(sim) == [12.0, 12.0]
