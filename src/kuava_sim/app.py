"""The live desktop window (Tkinter, ARCHITECTURE_899eaea.md D-16).

The window holds no simulation state: it draws the LiveSession and forwards
the user's input to it. Everything runs in the Tk thread (D-17).
"""

import time
import tkinter as tk

from .live import LiveSession

FRAME_INTERVAL_MS = 16  # target about 60 fps


class App:
    def __init__(self, root: tk.Tk, clock=time.perf_counter):
        self.root = root
        self.clock = clock
        self.session = LiveSession(clock())
        root.title("Drone altitude — live PID simulation")
        root.protocol("WM_DELETE_WINDOW", self.close)
        self._job = root.after(FRAME_INTERVAL_MS, self._loop)

    def frame(self) -> None:
        """One frame: take the due steps and redraw."""
        self.session.tick(self.clock())

    def _loop(self) -> None:
        start = self.clock()
        self.frame()
        elapsed_ms = (self.clock() - start) * 1000.0
        self._job = self.root.after(max(1, int(FRAME_INTERVAL_MS - elapsed_ms)), self._loop)

    def close(self) -> None:
        self.root.after_cancel(self._job)
        self.root.destroy()
