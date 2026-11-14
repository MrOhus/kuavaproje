"""US-6 Output records — acceptance tests.

Expected values come from docs/design/DESIGN.md (US-6 Gherkin ACs, I-2, I-3,
rounding tolerance ε from I-1) and the Record / RecordLog models in
docs/architecture/ARCHITECTURE.md (read-only Sequence[Record] view with
column(), step() returns the new Record, append-only, time = i / 200).
"""

import math
import struct

import pytest

from kuava_sim import SimConfig, Simulation

FIELDS = ("time", "altitude", "velocity", "acceleration", "thrust_used", "drag")

# Config from the US-6 time-0 and hand-calculation scenarios.
HAND = dict(
    mass=1.0,
    gravity=9.81,
    drag_coeff=0.5,
    max_thrust=20.0,
    initial_altitude=100.0,
    initial_velocity=2.0,
)


def make(**overrides):
    return Simulation(SimConfig(**{**HAND, **overrides}))


def within_eps(actual, expected):
    """Rounding tolerance ε from DESIGN.md I-1."""
    return abs(actual - expected) <= 1e-12 * max(1.0, abs(expected))


def bits(record):
    return struct.pack("<6d", *(getattr(record, f) for f in FIELDS))


# --- Scenario: The starting moment is the first record ------------------------


def test_starting_moment_is_the_first_record():
    sim = make()
    assert len(sim.records) == 1
    r = sim.records[0]
    assert r.time == 0.0
    assert r.altitude == 100.0
    assert r.velocity == 2.0
    assert r.thrust_used == 0.0
    assert within_eps(r.drag, -1.0)  # -b * v0 = -0.5 * 2
    assert within_eps(r.acceleration, -10.81)  # (0 - 9.81 - 1) / 1


def test_starting_record_off_the_ground_at_rest_shows_gravity():
    # Just above the ground is not "on the ground": I-3's special case does not apply.
    sim = make(initial_altitude=math.nextafter(0.0, 1.0), initial_velocity=0.0)
    r = sim.records[0]
    assert within_eps(r.acceleration, -9.81)
    assert r.drag == 0.0


def test_starting_record_on_the_ground_moving_up_shows_forces():
    # On the ground but moving up is not "at rest": forces apply (I-3).
    sim = make(initial_altitude=0.0, initial_velocity=3.0)
    r = sim.records[0]
    assert within_eps(r.drag, -1.5)  # -0.5 * 3
    assert within_eps(r.acceleration, -11.31)  # (0 - 9.81 - 1.5) / 1


# --- Scenario: Starting record on the ground at rest --------------------------


@pytest.mark.parametrize("v0", [0.0, -0.0], ids=["0.0", "-0.0"])
def test_starting_record_on_the_ground_at_rest_is_all_zero(v0):
    sim = make(initial_altitude=0.0, initial_velocity=v0)
    assert len(sim.records) == 1
    # Stored as the literal +0.0 (ARCHITECTURE.md, Record time-0 rule).
    assert bits(sim.records[0]) == struct.pack("<6d", *([0.0] * 6))


# --- Scenario: One record is added after every step ---------------------------


def test_one_record_is_added_after_every_step():
    sim = make()
    sim.run(250, thrust=15.0)
    records = sim.records
    assert len(records) == 251
    assert records[0].time == 0.0
    assert within_eps(records[-1].time, 1.25)
    for i, r in enumerate(records):
        assert within_eps(r.time, i / 200)
    times = [r.time for r in records]
    assert all(a < b for a, b in zip(times, times[1:]))


def test_each_single_step_adds_exactly_one_record():
    sim = make()
    for n in range(1, 6):
        sim.step(15.0)
        assert len(sim.records) == n + 1


# --- Scenario: Each record contains the required fields -----------------------


def test_step_returns_the_new_record_with_the_current_state():
    sim = make()
    r = sim.step(15.0)
    assert r == sim.records[-1]
    assert r._fields == FIELDS
    assert (r.time, r.altitude, r.velocity) == (sim.time, sim.altitude, sim.velocity)
    assert r.thrust_used == 15.0


def test_state_always_matches_the_last_record():
    sim = make()
    for cmd in (15.0, None, 0.0, 25.0, None):
        sim.step(cmd)
        last = sim.records[-1]
        assert (sim.time, sim.altitude, sim.velocity) == (
            last.time,
            last.altitude,
            last.velocity,
        )


# --- Scenario: Record values match a hand calculation -------------------------


def test_record_values_match_a_hand_calculation():
    sim = make()
    sim.step(15.0)
    r = sim.records[1]
    # drag = -0.5 * 2 = -1; a = (15 - 9.81 - 1) / 1 = 4.19
    # v1 = 2 + 4.19 * 0.005 = 2.02095; h1 = 100 + 2.02095 * 0.005 = 100.01010475
    assert within_eps(r.time, 0.005)
    assert r.thrust_used == 15.0
    assert within_eps(r.drag, -1.0)
    assert within_eps(r.acceleration, 4.19)
    assert within_eps(r.velocity, 2.02095)
    assert within_eps(r.altitude, 100.01010475)


# --- Scenario: Limited thrust is recorded as the thrust actually used ---------


def test_limited_thrust_is_recorded_as_thrust_actually_used():
    sim = make()
    sim.step(25.0)
    sim.step(-5.0)
    assert sim.records[1].thrust_used == 20.0
    assert sim.records[2].thrust_used == 0.0


# --- Scenario: Records keep growing without a limit ---------------------------


def test_records_keep_growing_without_a_limit():
    sim = make()
    sim.run(720000, thrust=15.0)
    records = sim.records
    assert len(records) == 720001
    for i in range(0, 720001, 1000):
        assert within_eps(records[i].time, i / 200)
    assert within_eps(records[-1].time, 3600.0)


def test_earlier_records_never_change_when_more_are_added():
    sim = make()
    sim.run(100, thrust=15.0)
    before = [bits(r) for r in sim.records]
    sim.run(500, thrust=3.0)
    assert [bits(r) for r in sim.records[:101]] == before


# --- Scenario: Rejected operations add no records -----------------------------


def nine_steps_done():
    sim = make()
    sim.run(9, thrust=15.0)
    assert len(sim.records) == 10
    return sim


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf], ids=["nan", "+inf", "-inf"])
def test_rejected_thrust_adds_no_records(bad):
    sim = nine_steps_done()
    before = [bits(r) for r in sim.records]
    with pytest.raises(ValueError):
        sim.step(bad)
    assert [bits(r) for r in sim.records] == before


def test_rejected_run_adds_no_records():
    sim = nine_steps_done()
    before = [bits(r) for r in sim.records]
    with pytest.raises(ValueError):
        sim.run(-1)
    assert [bits(r) for r in sim.records] == before


# --- RecordLog view (ARCHITECTURE.md): read-only Sequence with column() -------


def test_records_support_negative_index_slicing_and_bounds():
    sim = make()
    sim.run(4, thrust=15.0)
    records = sim.records
    assert records[-1] == records[4]
    assert [bits(r) for r in records[1:3]] == [bits(records[1]), bits(records[2])]
    with pytest.raises(IndexError):
        records[5]
    with pytest.raises(IndexError):
        records[-6]


def test_records_and_record_fields_cannot_be_changed():
    sim = make()
    sim.step(15.0)
    with pytest.raises(TypeError):
        sim.records[0] = sim.records[1]
    with pytest.raises(AttributeError):
        sim.records[0].altitude = 5.0
    assert sim.records[0].altitude == 100.0


def test_a_view_taken_earlier_sees_new_records():
    sim = make()
    view = sim.records
    sim.run(3, thrust=15.0)
    assert len(view) == 4


@pytest.mark.parametrize("name", FIELDS)
def test_column_returns_one_field_as_a_series(name):
    sim = make()
    sim.run(5, thrust=15.0)
    column = sim.records.column(name)
    assert isinstance(column, tuple)
    assert column == tuple(getattr(r, name) for r in sim.records)
    assert len(column) == 6
