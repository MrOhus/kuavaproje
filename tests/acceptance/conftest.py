"""Shared fixtures for the Round 3 GUI tests (ARCHITECTURE_899eaea.md, D-22).

Window tests open a real Tk window. If no display is available they are
skipped and the reason is printed in the pytest summary (AQ-21).
"""

import pytest

from gui_helpers import FakeClock


@pytest.fixture
def tk_root():
    try:
        import tkinter
    except ImportError as exc:  # depends on the Python build
        pytest.skip(f"Tkinter is not installed: {exc}")
    try:
        root = tkinter.Tk()
    except tkinter.TclError as exc:  # depends on the machine
        pytest.skip(f"no display available: {exc}")
    yield root
    try:
        root.destroy()
    except tkinter.TclError:
        pass  # the app already closed the window


@pytest.fixture
def clock():
    return FakeClock()
