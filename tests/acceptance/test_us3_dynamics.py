"""US-3 Vertical dynamics from gravity, thrust and drag — acceptance tests.

Expected values come from docs/design/DESIGN.md (US-3 Gherkin ACs, the
0.6 % long-run tolerance, rounding tolerance ε from I-1, hover per I-4) and
from ARCHITECTURE.md D-3 (formulation) and D-4 (floor: hn <= 0 and vn < 0).
Hand calculations are in the comments. Thrust validation follows the
Simulation model (non-finite gives ValueError, non-number gives TypeError).
"""

import math
import struct
import warnings

import pytest

from kuava_sim import SimConfig, Simulation

DT = 0.005
G = 9.81

needs_records = pytest.mark.xfail(
    strict=True,
    reason="needs records (acceleration, drag, thrust used) from US-6; "
    "remove this marker when US-6 lands",
)


def make(**cfg):
    cfg.setdefault("mass", 1.0)
    cfg.setdefault("max_thrust", 30.0)
    return Simulation(SimConfig(**cfg))


def within_eps(actual, expected):
    """Rounding tolerance ε from DESIGN.md I-1."""
    return abs(actual - expected) <= 1e-12 * max(1.0, abs(expected))


def within_0_6_percent(actual, expected):
    return abs(actual - expected) <= 0.006 * abs(expected)


def state_bits(sim):
    return (
        sim.step_count,
        struct.pack("<3d", sim.time, sim.altitude, sim.velocity),
    )


# --- Scenario: Free fall matches the formula within 0.6 % after 1 s ----------


def test_free_fall_after_1_s_within_0_6_percent():
    sim = make(gravity=G, drag_coeff=0.0, initial_altitude=1000.0)
    sim.run(200, thrust=0.0)
    assert within_0_6_percent(sim.velocity, -9.81)
    assert within_0_6_percent(1000.0 - sim.altitude, 4.905)


# --- Scenario: Free fall stays within 0.6 % for longer durations --------------


def test_free_fall_after_2_s_within_0_6_percent():
    sim = make(gravity=G, drag_coeff=0.0, initial_altitude=1000.0)
    sim.run(400, thrust=0.0)
    assert within_0_6_percent(sim.velocity, -19.62)
    assert within_0_6_percent(1000.0 - sim.altitude, 19.62)


# --- Scenario: Velocity is updated before altitude (semi-implicit Euler) ------


def test_one_step_updates_velocity_before_altitude():
    sim = make(gravity=G, drag_coeff=0.0, initial_altitude=1000.0)
    sim.step(0.0)
    # v1 = 0 - 9.81 * 0.005 = -0.04905; h1 = 1000 + v1 * 0.005 = 999.99975475
    assert within_eps(sim.velocity, -0.04905)
    assert within_eps(sim.altitude, 999.99975475)
    assert sim.altitude != 1000.0  # what an altitude-first update would give


# --- Scenario: Hover keeps the same height ------------------------------------

HOVER = dict(mass=1.5, gravity=G, drag_coeff=0.2, max_thrust=30.0, initial_altitude=100.0)


def test_hover_keeps_the_same_height_for_2000_steps():
    sim = make(**HOVER)
    hover = 1.5 * 9.81
    for _ in range(2000):
        sim.step(hover)
        assert within_eps(sim.altitude, 100.0)
        assert within_eps(sim.velocity, 0.0)
    # Control: 1 N more than hover must lift the drone, so a frozen state fails.
    lifted = make(**HOVER)
    lifted.step(hover + 1.0)
    assert lifted.altitude > 100.0


def test_hover_is_bit_exact_when_thrust_is_mass_times_gravity():
    # ARCHITECTURE.md D-3: (T - m*g) is exactly 0, so nothing drifts.
    sim = make(**HOVER)
    sim.run(2000, thrust=1.5 * 9.81)
    assert sim.altitude == 100.0
    assert sim.velocity == 0.0
    assert sim.step_count == 2000
    # Control: 1 N more than hover must lift the drone, so a frozen state fails.
    lifted = make(**HOVER)
    lifted.run(2000, thrust=1.5 * 9.81 + 1.0)
    assert lifted.altitude > 100.0


# --- Scenario: Excess thrust accelerates the drone upward ---------------------


def test_excess_thrust_accelerates_upward():
    sim = make(gravity=G, drag_coeff=0.0, initial_altitude=100.0)
    sim.run(200, thrust=20.0)
    assert within_0_6_percent(sim.velocity, (20.0 / 1.0 - 9.81) * 1.0)  # 10.19


# --- Scenario: Heavier drone accelerates less for the same thrust -------------


@pytest.mark.parametrize("mass, expected", [(1.0, 15.19), (2.0, 2.69)])
def test_heavier_drone_accelerates_less(mass, expected):
    sim = make(mass=mass, gravity=G, drag_coeff=0.0, initial_altitude=100.0)
    sim.run(200, thrust=25.0)
    assert within_0_6_percent(sim.velocity, expected)


# --- Scenario: Linear drag opposes motion and is proportional to velocity -----


@pytest.mark.parametrize("v0, drag", [(4.0, -2.0), (-4.0, 2.0), (0.0, 0.0)])
def test_drag_used_in_a_step_is_minus_b_times_start_velocity(v0, drag):
    # With thrust = m*g + 1 N the net force is 1 N + drag, so
    # drag = m * (v1 - v0) / dt - 1. A state that does not change gives -1.
    sim = make(gravity=G, drag_coeff=0.5, initial_altitude=100.0, initial_velocity=v0)
    sim.step(1.0 * 9.81 + 1.0)
    measured = 1.0 * (sim.velocity - v0) / DT - 1.0
    assert within_eps(measured, drag)


# --- Scenario: Linear drag limits falling speed to m·g/b ----------------------


def test_drag_limits_falling_speed_to_m_g_over_b():
    sim = make(gravity=G, drag_coeff=0.5, initial_altitude=100000.0)
    sim.step(0.0)
    previous = -sim.velocity
    assert previous > 0.0
    for _ in range(19999):
        sim.step()
        speed = -sim.velocity
        assert speed >= previous  # increases monotonically
        assert speed <= 19.62  # never exceeds m*g/b
        previous = speed
    assert sim.step_count == 20000
    assert within_0_6_percent(previous, 19.62)


# --- Thrust limits: capping is silent (AC: above max, negative, at/inside) ----

THRUST_CFG = dict(gravity=G, drag_coeff=0.0, max_thrust=20.0, initial_altitude=100.0)


def velocity_after_one_step(thrust):
    sim = make(**THRUST_CFG)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        sim.step(thrust)
    assert caught == [], "no warning may be produced"
    return sim


@pytest.mark.parametrize("cmd", [25.0, 20.001, math.nextafter(20.0, math.inf)])
def test_thrust_above_maximum_is_capped_silently(cmd):
    capped = velocity_after_one_step(cmd)
    at_max = velocity_after_one_step(20.0)
    assert within_eps(capped.velocity, (20.0 - 9.81) * DT)  # 0.05095
    assert state_bits(capped) == state_bits(at_max)


@pytest.mark.parametrize("cmd", [-5.0, -0.001, math.nextafter(0.0, -math.inf)])
def test_negative_thrust_is_set_to_zero_silently(cmd):
    zeroed = velocity_after_one_step(cmd)
    at_zero = velocity_after_one_step(0.0)
    assert within_eps(zeroed.velocity, -9.81 * DT)  # -0.04905
    assert state_bits(zeroed) == state_bits(at_zero)


@pytest.mark.parametrize("cmd", [20.0, 19.999, 0.001, 0.0])
def test_thrust_at_and_inside_limits_is_used_as_commanded(cmd):
    sim = velocity_after_one_step(cmd)
    assert within_eps(sim.velocity, (cmd - 9.81) * DT)


def test_thrust_just_inside_limits_is_not_capped():
    # 19.999 N must give a different result from 20 N (not capped early).
    assert state_bits(velocity_after_one_step(19.999)) != state_bits(
        velocity_after_one_step(20.0)
    )


@needs_records
@pytest.mark.parametrize("cmd, used", [(25.0, 20.0), (-5.0, 0.0), (19.999, 19.999)])
def test_thrust_used_is_recorded_after_limits(cmd, used):
    sim = make(**THRUST_CFG)
    sim.step(cmd)
    assert sim.records[-1].thrust_used == used


# --- Scenario: Non-finite thrust command is rejected --------------------------


def held_5_n():
    sim = make(gravity=G, drag_coeff=0.5, initial_altitude=100.0)
    sim.run(10, thrust=5.0)
    return sim


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf], ids=["nan", "+inf", "-inf"])
def test_non_finite_thrust_is_rejected_and_nothing_changes(bad):
    sim = held_5_n()
    before = state_bits(sim)
    with pytest.raises(ValueError, match="thrust") as info:
        sim.step(bad)
    assert "finite" in str(info.value)
    with pytest.raises(ValueError, match="thrust"):
        sim.run(3, thrust=bad)
    assert state_bits(sim) == before
    assert sim.held_thrust == 5.0


@pytest.mark.parametrize("bad", [True, "5", [5.0]], ids=["bool", "str", "list"])
def test_non_number_thrust_is_rejected_and_nothing_changes(bad):
    sim = held_5_n()
    before = state_bits(sim)
    with pytest.raises(TypeError, match="thrust"):
        sim.step(bad)
    with pytest.raises(TypeError, match="thrust"):
        sim.run(3, thrust=bad)
    assert state_bits(sim) == before
    assert sim.held_thrust == 5.0


@needs_records
def test_non_finite_thrust_leaves_records_unchanged():
    sim = held_5_n()
    before = list(sim.records)
    with pytest.raises(ValueError):
        sim.step(math.nan)
    assert list(sim.records) == before


# --- Scenario: Resting on the ground with insufficient thrust -----------------

GROUND = dict(gravity=G, drag_coeff=0.5)


def test_resting_on_ground_with_insufficient_thrust():
    sim = make(**GROUND)
    sim.step(5.0)
    for _ in range(200):
        assert sim.altitude == 0.0
        assert sim.velocity == 0.0
        sim.step()
    assert within_eps(sim.time, 201 * DT)
    # Control: the same thrust high above the ground must let the drone sink.
    high = make(**GROUND, initial_altitude=100.0)
    high.run(200, thrust=5.0)
    assert high.altitude < 100.0


@needs_records
def test_resting_on_ground_records_zero_acceleration_and_drag():
    sim = make(**GROUND)
    sim.run(200, thrust=5.0)
    assert within_eps(sim.time, 1.0)
    for r in sim.records[1:]:
        assert (r.altitude, r.velocity, r.acceleration, r.drag, r.thrust_used) == (
            0.0, 0.0, 0.0, 0.0, 5.0,
        )


# --- Scenario: Taking off from the ground -------------------------------------


def test_taking_off_from_the_ground():
    sim = make(gravity=G, max_thrust=30.0)
    sim.step(19.62)
    # v1 = (19.62 - 9.81) * 0.005 = 0.04905; h1 = v1 * 0.005 = 0.00024525
    assert sim.altitude > 0.0 and sim.velocity > 0.0
    assert within_eps(sim.velocity, 0.04905)
    assert within_eps(sim.altitude, 0.00024525)


# --- Scenario: Landing stops at the floor and the run continues ---------------


def test_landing_stops_at_floor_and_run_continues():
    # h_k = 1 - 9.81 * 0.005² * k(k+1)/2 first goes below 0 at k = 90
    # (k = 89: +0.0178 m; k = 90: -0.0043 m).
    sim = make(gravity=G, drag_coeff=0.0, initial_altitude=1.0)
    sim.step(0.0)
    for k in range(1, 201):
        assert sim.altitude >= 0.0
        if k < 90:
            assert sim.altitude > 0.0 and sim.velocity < 0.0
        else:
            assert sim.altitude == 0.0 and sim.velocity == 0.0
        if k < 200:
            sim.step()
    assert sim.step_count == 200
    assert within_eps(sim.time, 1.0)


@needs_records
def test_landing_step_records_zero_acceleration_and_drag():
    sim = make(gravity=G, drag_coeff=0.0, initial_altitude=1.0)
    sim.run(200, thrust=0.0)
    landing = sim.records[90]
    assert (landing.altitude, landing.velocity, landing.acceleration, landing.drag) == (
        0.0, 0.0, 0.0, 0.0,
    )


# --- Scenario: Landing at speed does not bounce -------------------------------


def test_landing_at_speed_does_not_bounce():
    # Step 1: a = (0 - 9.81 + 5) / 1 = -4.81, v1 = -10.02405,
    # h1 = 0.01 - 0.0501 < 0, so the drone lands on step 1.
    sim = make(gravity=G, drag_coeff=0.5, initial_altitude=0.01, initial_velocity=-10.0)
    for _ in range(10):
        sim.step(0.0)
        assert sim.altitude == 0.0
        assert sim.velocity == 0.0


@needs_records
def test_landing_at_speed_records_zero_acceleration_and_drag():
    sim = make(gravity=G, drag_coeff=0.5, initial_altitude=0.01, initial_velocity=-10.0)
    sim.run(10, thrust=0.0)
    for r in sim.records[1:]:
        assert (r.altitude, r.velocity, r.acceleration, r.drag) == (0.0, 0.0, 0.0, 0.0)


# --- ARCHITECTURE.md D-4: floor condition hn <= 0 and vn < 0 -----------------
# With drag 0 and thrust = m*g, a = 0 exactly, so vn = v0 = -1 and
# hn = h0 - 0.005. At h0 = 0.005, hn is exactly 0 while still moving down.


def floor_case(h0):
    sim = make(gravity=G, drag_coeff=0.0, initial_altitude=h0, initial_velocity=-1.0)
    sim.step(1.0 * 9.81)
    return sim


def test_floor_applies_when_landing_exactly_on_zero_while_moving_down():
    sim = floor_case(0.005)
    assert sim.altitude == 0.0
    assert sim.velocity == 0.0


def test_floor_applies_just_below_the_limit():
    sim = floor_case(math.nextafter(0.005, 0.0))
    assert sim.altitude == 0.0
    assert sim.velocity == 0.0


def test_floor_does_not_apply_just_above_the_limit():
    sim = floor_case(math.nextafter(0.005, 1.0))
    assert 0.0 < sim.altitude < 1e-15
    assert sim.velocity == -1.0


def test_no_record_is_on_the_ground_while_moving_down():
    for h0 in (0.005, math.nextafter(0.005, 0.0), 0.0049, 0.0051, 1.0):
        sim = make(gravity=G, drag_coeff=0.0, initial_altitude=h0, initial_velocity=-1.0)
        for _ in range(300):
            sim.step(1.0 * 9.81 if sim.step_count == 0 else None)
            assert sim.altitude >= 0.0
            assert not (sim.altitude == 0.0 and sim.velocity < 0.0)
        assert sim.altitude == 0.0  # it did land
