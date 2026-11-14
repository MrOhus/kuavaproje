"""Shared US-4 scenario: a fixed configuration and a fixed thrust sequence.

Used in-process by test_us4_determinism.py, and run as a script in a
separate process, where it writes the raw record bytes to stdout.
"""

import math
import struct
import sys

from kuava_sim import SimConfig, Simulation

CONFIG = dict(
    mass=1.2,
    gravity=9.81,
    drag_coeff=0.3,
    max_thrust=30.0,
    initial_altitude=100.0,
    initial_velocity=0.0,
)
HOVER = 1.2 * 9.81
STEPS = 10000


def command(k):
    """Thrust command for step k (1-based): varied, sometimes held, capped or zeroed.

    Keeps the drone airborne for 10000 steps (it slowly climbs).
    """
    if k % 7 == 0:
        return None  # keep the held command
    if k % 97 == 0:
        return 35.0  # above max_thrust: capped to 30 N
    if k % 131 == 0:
        return -2.0  # negative: set to 0 N
    return HOVER + 3.0 * math.sin(k * 0.01)


def make():
    return Simulation(SimConfig(**CONFIG))


def run(sim, steps=STEPS, override=None):
    """Step through the sequence; override maps step number to a replacement command."""
    for k in range(1, steps + 1):
        cmd = override[k] if override and k in override else command(k)
        sim.step(cmd)
    return sim


def record_bytes(sim):
    """All records as raw little-endian IEEE-754 bytes, in order."""
    return b"".join(
        struct.pack(
            "<6d", r.time, r.altitude, r.velocity, r.acceleration, r.thrust_used, r.drag
        )
        for r in sim.records
    )


if __name__ == "__main__":
    sys.stdout.buffer.write(record_bytes(run(make())))
