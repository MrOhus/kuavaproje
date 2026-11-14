"""Helpers for the Round 3 GUI tests (no fixtures here; see conftest.py)."""

import struct
import time


class FakeClock:
    """A wall clock the test moves by hand (seconds)."""

    def __init__(self, now=100.0):
        self.now = now

    def __call__(self):
        return self.now


def pump(root, seconds):
    """Let the real Tk event loop run for the given wall-clock time."""
    end = time.perf_counter() + seconds
    while time.perf_counter() < end:
        root.update()
        time.sleep(0.001)


def record_bytes(sim):
    return [struct.pack("<6d", *r) for r in sim.records]
