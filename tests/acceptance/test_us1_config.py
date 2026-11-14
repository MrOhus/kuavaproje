"""US-1 Configure the simulation — acceptance tests.

Expected values come from docs/design/DESIGN.md (US-1 Gherkin ACs) and the
SimConfig / Simulation / constants models in docs/architecture/ARCHITECTURE.md.
Boundary tests use the exact limit and the neighbouring doubles
(math.nextafter) as epsilon, per the meaningful-tests skill.
"""

import math
import re

import pytest

from kuava_sim import (
    DEFAULT_GRAVITY,
    DT,
    MIN_THRUST,
    STEP_RATE_HZ,
    SimConfig,
    Simulation,
)

INF = math.inf
NAN = math.nan


def below(x):
    """Next double below x."""
    return math.nextafter(x, -INF)


def above(x):
    """Next double above x."""
    return math.nextafter(x, INF)


# The valid configuration from the first US-1 scenario.
VALID = dict(
    mass=1.5,
    gravity=9.81,
    max_thrust=30.0,
    drag_coeff=0.2,
    initial_altitude=10.0,
    initial_velocity=1.0,
)


def create(**overrides):
    """Create a simulation from VALID with some fields replaced."""
    return Simulation(SimConfig(**{**VALID, **overrides}))


def assert_rejected(exc_type, overrides, *must_contain):
    """Creation must raise exc_type, and the message must contain every phrase."""
    with pytest.raises(exc_type) as info:
        create(**overrides)
    message = str(info.value)
    for phrase in must_contain:
        assert phrase in message, f"{phrase!r} not in error message {message!r}"
    return message


# --- Scenario: Valid configuration is accepted --------------------------------


def test_valid_configuration_reports_exact_values_back():
    sim = create()
    cfg = sim.config
    assert cfg.mass == 1.5
    assert cfg.gravity == 9.81
    assert cfg.max_thrust == 30.0
    assert cfg.drag_coeff == 0.2
    assert cfg.initial_altitude == 10.0
    assert cfg.initial_velocity == 1.0


def test_valid_configuration_reports_fixed_step_rate_length_and_min_thrust():
    sim = create()
    assert sim.step_rate_hz == 200
    assert sim.step_length == 0.005
    assert sim.min_thrust == 0.0


def test_module_constants_have_specified_values():
    assert STEP_RATE_HZ == 200 and isinstance(STEP_RATE_HZ, int)
    assert DT == 0.005
    assert MIN_THRUST == 0.0
    assert DEFAULT_GRAVITY == 9.81


def test_integer_inputs_are_stored_as_floats():
    sim = create(mass=2, max_thrust=30, initial_altitude=10)
    assert type(sim.config.mass) is float and sim.config.mass == 2.0
    assert type(sim.config.max_thrust) is float and sim.config.max_thrust == 30.0
    assert type(sim.config.initial_altitude) is float


def test_configuration_cannot_be_changed_after_creation():
    sim = create()
    with pytest.raises(AttributeError):
        sim.config.mass = 3.0
    assert sim.config.mass == 1.5


# --- Scenario: Defaults are applied when optional values are omitted ----------


def test_defaults_are_applied_when_only_mass_and_max_thrust_are_set():
    sim = Simulation(SimConfig(mass=1.5, max_thrust=30.0))
    assert sim.config.gravity == 9.81
    assert sim.config.initial_altitude == 0.0
    assert sim.config.initial_velocity == 0.0
    assert sim.config.drag_coeff == 0.0
    assert sim.held_thrust == 0.0


@pytest.mark.parametrize("missing", ["mass", "max_thrust"])
def test_mass_and_max_thrust_are_required(missing):
    kwargs = {"mass": 1.5, "max_thrust": 30.0}
    del kwargs[missing]
    with pytest.raises(TypeError, match=missing):
        SimConfig(**kwargs)


# --- Scenario: Gravity can be changed from the default ------------------------


def test_gravity_can_be_changed_from_the_default():
    assert create(gravity=3.71).config.gravity == 3.71


# --- Scenario Outline: Gravity of 0 or less is rejected -----------------------


@pytest.mark.parametrize("g", [0.0, -9.81, below(0.0)])
def test_gravity_zero_or_less_is_rejected_with_clear_error(g):
    assert_rejected(ValueError, {"gravity": g}, "gravity", "greater than 0")


# --- Scenario: Smallest positive gravity is accepted --------------------------


@pytest.mark.parametrize("g", [0.001, above(0.0)])
def test_small_positive_gravity_is_accepted(g):
    assert create(gravity=g).config.gravity == g


# --- Scenario: The step rate cannot be changed by the user --------------------


@pytest.mark.parametrize(
    "option, value",
    [("step_rate_hz", 400), ("step_rate", 400), ("step_length", 0.0025), ("dt", 0.0025)],
)
def test_step_rate_or_length_is_not_a_configuration_option(option, value):
    assert_rejected(TypeError, {option: value}, option)


def test_step_rate_cannot_be_changed_on_a_running_simulation():
    sim = create()
    with pytest.raises(AttributeError):
        sim.step_rate_hz = 400
    with pytest.raises(AttributeError):
        sim.step_length = 0.0025
    assert sim.step_rate_hz == 200
    assert sim.step_length == 0.005


# --- Scenario: The minimum thrust cannot be changed by the user ---------------


@pytest.mark.parametrize("option", ["min_thrust", "minimum_thrust"])
def test_minimum_thrust_is_not_a_configuration_option(option):
    assert_rejected(TypeError, {option: 2.0}, option)


def test_minimum_thrust_cannot_be_changed_on_a_running_simulation():
    sim = create()
    with pytest.raises(AttributeError):
        sim.min_thrust = 2.0
    assert sim.min_thrust == 0.0


# --- Scenario Outline: Non-positive mass is rejected --------------------------


@pytest.mark.parametrize("mass", [0.0, -1.0, below(0.0)])
def test_non_positive_mass_is_rejected(mass):
    assert_rejected(ValueError, {"mass": mass, "drag_coeff": 0.0}, "mass", "greater than 0")


def test_smallest_positive_mass_is_accepted():
    tiny = above(0.0)
    assert create(mass=tiny, drag_coeff=0.0).config.mass == tiny


# --- Scenario: Maximum thrust of 0 N is accepted ------------------------------


def test_max_thrust_zero_is_accepted():
    assert create(max_thrust=0.0).config.max_thrust == 0.0


def test_max_thrust_zero_keeps_drone_on_ground_with_zero_thrust_used():
    sim = create(max_thrust=0.0, initial_altitude=0.0, initial_velocity=0.0)
    sim.run(200, thrust=50.0)
    assert len(sim.records) == 201
    assert all(r.altitude == 0.0 for r in sim.records)
    assert all(r.thrust_used == 0.0 for r in sim.records)


# --- Scenario: Negative maximum thrust is rejected ----------------------------


@pytest.mark.parametrize("t", [-0.001, below(0.0)])
def test_negative_max_thrust_is_rejected(t):
    assert_rejected(ValueError, {"max_thrust": t}, "max_thrust")


def test_smallest_positive_max_thrust_is_accepted():
    assert create(max_thrust=above(0.0)).config.max_thrust == above(0.0)


# --- Scenario: Negative drag coefficient is rejected --------------------------


@pytest.mark.parametrize("b", [-0.1, below(0.0)])
def test_negative_drag_coefficient_is_rejected(b):
    assert_rejected(ValueError, {"drag_coeff": b}, "drag_coeff")


# --- Scenario Outline: Drag coefficient below 200 × mass is accepted ----------


@pytest.mark.parametrize("b", [0.0, 199.999, below(200.0)])
def test_drag_coefficient_below_200_times_mass_is_accepted(b):
    assert create(mass=1.0, drag_coeff=b).config.drag_coeff == b


def test_drag_just_below_limit_is_accepted_for_mass_2_5():
    assert create(mass=2.5, drag_coeff=below(500.0)).config.drag_coeff == below(500.0)


# --- Scenario Outline: Drag coefficient of 200 × mass or more is rejected ------


@pytest.mark.parametrize(
    "m, b, limit",
    [
        (1.0, 200.0, 200.0),
        (1.0, above(200.0), 200.0),
        (1.0, 200.001, 200.0),
        (2.5, 500.0, 500.0),
    ],
)
def test_drag_coefficient_at_or_above_limit_is_rejected_with_clear_error(m, b, limit):
    message = assert_rejected(
        ValueError, {"mass": m, "drag_coeff": b}, "drag_coeff", "200 × mass", "unstable"
    )
    stated = re.search(r"200 × mass = ([0-9.]+) N·s/m", message)
    assert stated is not None, f"limit not stated in {message!r}"
    assert float(stated.group(1)) == limit


# --- Scenario Outline: Valid initial altitude and velocity are accepted -------


@pytest.mark.parametrize(
    "h0, v0",
    [(0.0, 0.0), (0.0, 3.0), (10.0, -5.0), (0.0, -0.0), (above(0.0), -5.0)],
)
def test_valid_initial_altitude_and_velocity_are_accepted(h0, v0):
    cfg = create(initial_altitude=h0, initial_velocity=v0).config
    assert cfg.initial_altitude == h0
    assert cfg.initial_velocity == v0


# --- Scenario Outline: Starting below the ground is rejected ------------------


@pytest.mark.parametrize("h0", [-0.001, -10.0, below(0.0)])
def test_starting_below_ground_is_rejected_with_clear_error(h0):
    assert_rejected(
        ValueError,
        {"initial_altitude": h0, "initial_velocity": 0.0},
        "initial_altitude",
        "not be below 0",
    )


# --- Scenario: Starting on the ground while moving down is rejected -----------


@pytest.mark.parametrize("v0", [-0.001, below(0.0)])
def test_starting_on_ground_moving_down_is_rejected_with_clear_error(v0):
    assert_rejected(
        ValueError,
        {"initial_altitude": 0.0, "initial_velocity": v0},
        "cannot start on the ground while moving down",
    )


# --- Scenario Outline: Non-finite parameters are rejected ---------------------

FIELDS = ["mass", "gravity", "max_thrust", "drag_coeff", "initial_altitude", "initial_velocity"]


@pytest.mark.parametrize("value", [NAN, INF, -INF], ids=["nan", "+inf", "-inf"])
@pytest.mark.parametrize("field", FIELDS)
def test_non_finite_parameter_is_rejected(field, value):
    assert_rejected(ValueError, {field: value}, field, "finite")


# --- Wrong types are rejected (ARCHITECTURE.md: SimConfig invariants) ---------


@pytest.mark.parametrize("value", [True, None, "1.5"], ids=["bool", "None", "str"])
@pytest.mark.parametrize("field", FIELDS)
def test_non_number_parameter_is_rejected(field, value):
    assert_rejected(TypeError, {field: value}, field)
