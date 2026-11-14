"""Helpers for the Round 3 GUI tests (no fixtures here; see conftest.py)."""

import struct
import time

import pytest


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


def require_visible(root, widget):
    """Skip a window test that needs mouse or key events if the window is not shown.

    Tk does not deliver mouse and key events to a window that is not drawn on
    screen (minimized, hidden, locked screen), so such a test cannot run then.
    The reason is printed in the pytest summary (-rs), as for AQ-21.
    """
    root.update()
    if not widget.winfo_viewable():
        pytest.skip("window not visible on screen: Tk does not deliver mouse and key events to it")


def record_bytes(sim):
    return [struct.pack("<6d", *r) for r in sim.records]
