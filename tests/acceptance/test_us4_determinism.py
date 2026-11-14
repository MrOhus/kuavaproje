"""US-4 Deterministic runs (same machine, same code) — acceptance tests.

Expected behaviour comes from docs/design/DESIGN.md (US-4 Gherkin ACs) and
ARCHITECTURE.md D-2/D-3 (plain floats, fixed operation order) and D-7 (run
the same script twice with subprocess and compare the bytes). "Bit-for-bit"
is checked on the raw IEEE-754 bytes of every record field.

The choices marked IQ-4 … IQ-7 were confirmed by the operator as option a
(see the US-4 pass in docs/implementation/IMPLEMENTATION_LOG.md).
"""

import os
import pathlib
import struct
import subprocess
import sys
import threading
import time

import us4_scenario as sc

RECORD = struct.Struct("<6d")
SRC = pathlib.Path(__file__).resolve().parents[2] / "src"
SCRIPT = pathlib.Path(sc.__file__).resolve()


def per_record(raw):
    return [raw[i : i + RECORD.size] for i in range(0, len(raw), RECORD.size)]


def assert_scenario_is_not_trivial(sim):
    """The sequence must really exercise the model, so identical output means something."""
    used = sim.records.column("thrust_used")
    altitude = sim.records.column("altitude")
    assert 30.0 in used and 0.0 in used  # capping and zeroing happened
    assert min(altitude) > 0.0  # stayed airborne
    assert max(altitude) - min(altitude) > 1.0  # really moved
    assert len(set(sim.records.column("velocity"))) > 1000


# --- Scenario: Identical inputs yield identical outputs in one process --------


def test_identical_inputs_give_identical_records_in_one_process():
    a = sc.run(sc.make())
    b = sc.run(sc.make())
    assert len(a.records) == sc.STEPS + 1
    assert per_record(sc.record_bytes(a)) == per_record(sc.record_bytes(b))
    assert_scenario_is_not_trivial(a)


# --- Scenario: Repeated executions yield identical outputs (IQ-5) -------------


def run_in_separate_process(hash_seed):
    env = {**os.environ, "PYTHONPATH": str(SRC), "PYTHONHASHSEED": str(hash_seed)}
    done = subprocess.run(
        [sys.executable, str(SCRIPT)], env=env, capture_output=True, check=True
    )
    return done.stdout


def test_repeated_executions_in_separate_processes_give_identical_records():
    first = run_in_separate_process(hash_seed=1)
    second = run_in_separate_process(hash_seed=2)
    assert len(first) == (sc.STEPS + 1) * RECORD.size
    assert first == second
    # Also identical to the run inside this test process.
    assert first == sc.record_bytes(sc.run(sc.make()))


# --- Scenario: Output does not depend on host timing or load (IQ-6) -----------


def test_records_do_not_depend_on_wall_clock_delays_or_load():
    steps = 300
    calm = sc.run(sc.make(), steps=steps)

    stop = threading.Event()

    def busy():  # competes for the interpreter while the simulation runs
        x = 0
        while not stop.is_set():
            x += 1

    loader = threading.Thread(target=busy, daemon=True)
    loader.start()
    try:
        loaded = sc.make()
        for k in range(1, steps + 1):
            loaded.step(sc.command(k))
            time.sleep(0.005)
    finally:
        stop.set()
        loader.join()

    assert per_record(sc.record_bytes(loaded)) == per_record(sc.record_bytes(calm))
    assert len(loaded.records) == steps + 1


# --- Scenario: Single steps and "run N steps" give identical outputs ----------


def test_single_steps_and_run_n_give_identical_records():
    single, batch = sc.make(), sc.make()
    for _ in range(1000):
        single.step(15.0)
    batch.run(1000, thrust=15.0)
    assert len(batch.records) == 1001
    assert per_record(sc.record_bytes(batch)) == per_record(sc.record_bytes(single))
    assert single.altitude != sc.CONFIG["initial_altitude"]  # it really moved


# --- Scenario: A changed input changes the output only from that step on (IQ-7)


def test_changed_input_changes_output_only_from_that_step_on():
    steps = 1000
    ten = per_record(sc.record_bytes(sc.run(sc.make(), steps, override={500: 10.0})))
    twelve = per_record(sc.record_bytes(sc.run(sc.make(), steps, override={500: 12.0})))
    assert sc.command(501) is not None  # the next step gives a new command
    assert len(ten) == len(twelve) == steps + 1
    # Records for time 0 up to step 499 are identical ...
    assert ten[:500] == twelve[:500]
    # ... and every record from step 500 on differs.
    for k in range(500, steps + 1):
        assert ten[k] != twelve[k], f"record {k} should differ"
