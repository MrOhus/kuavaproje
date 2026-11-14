"""US-2 Advance the simulation in fixed time steps — acceptance tests.

Expected values come from docs/design/DESIGN.md (US-2 Gherkin ACs, rounding
tolerance ε from I-1) and the Simulation / RecordLog models in
docs/architecture/ARCHITECTURE.md (time = n / 200; run(n) validation;
run(0) is a pure no-op). "Bit-for-bit" is checked on the raw IEEE-754 bytes,
not with ==, so that 0.0 vs -0.0 or NaN differences are not hidden.
"""

import struct
import time

import pytest

from kuava_sim import SimConfig, Simulation

# Config from the US-6 hand-calculation scenario: the drone is moving, so
# altitude and velocity change every step once dynamics exist.
MOVING = dict(
    mass=1.0,
    gravity=9.81,
    drag_coeff=0.5,
    max_thrust=20.0,
    initial_altitude=100.0,
    initial_velocity=2.0,
)


def make(**overrides):
    return Simulation(SimConfig(**{**MOVING, **overrides}))


def within_eps(actual, expected):
    """Rounding tolerance ε from DESIGN.md I-1."""
    return abs(actual - expected) <= 1e-12 * max(1.0, abs(expected))


def state_bits(sim):
    """Everything observable about the state, as exact bytes."""
    return (
        sim.step_count,
        struct.pack(
            "<4d", sim.time, sim.altitude, sim.velocity, sim.held_thrust
        ),
    )


def record_bits(sim):
    """All records as exact bytes, in order."""
    return [
        struct.pack(
            "<6d",
            r.time,
            r.altitude,
            r.velocity,
            r.acceleration,
            r.thrust_used,
            r.drag,
        )
        for r in sim.records
    ]


# --- Scenario: Each step advances simulated time by exactly one fixed step ----


def test_new_simulation_starts_at_time_zero():
    sim = make()
    assert sim.step_count == 0
    assert sim.time == 0.0


def test_one_step_advances_time_by_one_fixed_step():
    sim = make()
    sim.step()
    assert sim.step_count == 1
    assert within_eps(sim.time, 0.005)


# --- Scenario: Simulated time is derived from the step count without drift ----


def test_720000_steps_give_3600_s_without_drift():
    sim = make()
    sim.run(720000)
    assert sim.step_count == 720000
    assert within_eps(sim.time, 3600.0)


# --- Scenario: The simulation never stops by itself ---------------------------


def test_simulation_keeps_stepping_after_720000_steps():
    sim = make()
    sim.run(720000)
    before = sim.time
    sim.step()
    assert sim.step_count == 720001
    assert within_eps(sim.time - before, 0.005)
    assert within_eps(sim.time, 3600.005)


# --- Scenario: Run N steps shortcut -------------------------------------------


def test_run_200_gives_same_state_as_200_single_steps():
    single, batch = make(), make()
    for _ in range(200):
        single.step(15.0)
    batch.run(200, thrust=15.0)
    assert batch.step_count == 200
    assert state_bits(batch) == state_bits(single)


def test_run_1_is_exactly_one_step():
    single, batch = make(), make()
    single.step(15.0)
    batch.run(1, thrust=15.0)
    assert batch.step_count == 1
    assert state_bits(batch) == state_bits(single)


def test_run_200_gives_same_records_as_200_single_steps():
    single, batch = make(), make()
    for _ in range(200):
        single.step(15.0)
    batch.run(200, thrust=15.0)
    assert len(batch.records) == 201
    assert record_bits(batch) == record_bits(single)


# --- Scenario: Running 0 steps does nothing and is not an error ---------------


def ten_steps_done():
    sim = make()
    sim.run(10, thrust=15.0)
    return sim


def test_run_0_leaves_state_and_time_unchanged():
    sim = ten_steps_done()
    before = state_bits(sim)
    assert sim.run(0) is None
    assert state_bits(sim) == before
    assert sim.step_count == 10


def test_run_0_with_thrust_does_not_change_held_command():
    sim = ten_steps_done()
    sim.run(0, thrust=7.0)
    assert sim.held_thrust == 15.0


def test_run_0_leaves_the_11_records_unchanged():
    sim = ten_steps_done()
    before = record_bits(sim)
    assert len(before) == 11
    sim.run(0)
    assert record_bits(sim) == before


# --- Scenario Outline: Invalid N for "run N steps" is rejected ----------------

INVALID_N = [
    (-1, ValueError),
    (2.5, TypeError),
    (200.0, TypeError),
    (True, TypeError),
    ("3", TypeError),
    (None, TypeError),
]


@pytest.mark.parametrize("n, error", INVALID_N, ids=[repr(n) for n, _ in INVALID_N])
def test_invalid_n_is_rejected_and_state_unchanged(n, error):
    sim = ten_steps_done()
    before = state_bits(sim)
    with pytest.raises(error):
        sim.run(n, thrust=3.0)
    assert state_bits(sim) == before
    assert sim.held_thrust == 15.0


@pytest.mark.parametrize("n", [-1, 2.5])
def test_invalid_n_leaves_records_unchanged(n):
    sim = ten_steps_done()
    before = record_bits(sim)
    with pytest.raises((ValueError, TypeError)):
        sim.run(n)
    assert record_bits(sim) == before


# --- Scenario: Step length cannot vary between steps --------------------------


@pytest.mark.parametrize("option", ["dt", "step_length", "step_rate_hz"])
def test_step_length_cannot_be_passed_to_step_or_run(option):
    sim = ten_steps_done()
    before = state_bits(sim)
    with pytest.raises(TypeError):
        sim.step(**{option: 0.0025})
    with pytest.raises(TypeError):
        sim.run(5, **{option: 0.0025})
    assert state_bits(sim) == before


# --- Scenario: Simulation runs as fast as possible, not paced to the clock ----


def test_200000_steps_run_without_waiting_on_the_wall_clock(monkeypatch):
    def no_sleep(*_):
        raise AssertionError("the simulation must not sleep")

    monkeypatch.setattr(time, "sleep", no_sleep)
    sim = make()
    start = time.perf_counter()
    sim.run(200000)
    elapsed = time.perf_counter() - start
    assert within_eps(sim.time, 1000.0)
    # Far below the 1000 s of simulated time: even pacing at 10x real time fails.
    assert elapsed < 100.0


# --- Scenario: Simulated time is independent of wall-clock time ---------------


def test_simulated_time_is_independent_of_wall_clock_pauses():
    fast, slow = make(), make()
    fast.run(1000)
    for _ in range(1000):
        slow.step()
        time.sleep(0.01)
    assert within_eps(fast.time, 5.0)
    assert within_eps(slow.time, 5.0)
    assert state_bits(slow) == state_bits(fast)
