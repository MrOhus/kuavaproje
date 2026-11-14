"""The live desktop window (Tkinter, ARCHITECTURE_899eaea.md D-16).

The window holds no simulation state: it draws the LiveSession and forwards
the user's input to it. Everything runs in the Tk thread (D-17).
"""

import time
import tkinter as tk

from .live import SLIDER_RESOLUTION, SLIDERS, LiveSession

FRAME_INTERVAL_MS = 16  # target about 60 fps

SLIDER_LABELS = {
    "kp": "Kp (N/m)",
    "ki": "Ki (N/(m·s))",
    "kd": "Kd (N·s/m)",
    "setpoint": "Setpoint (m)",
}


class App:
    def __init__(self, root: tk.Tk, clock=time.perf_counter):
        self.root = root
        self.clock = clock
        self.session = LiveSession(clock())
        root.title("Drone altitude — live PID simulation")
        root.protocol("WM_DELETE_WINDOW", self.close)
        self._build_sliders()
        self._job = root.after(FRAME_INTERVAL_MS, self._loop)

    def _build_sliders(self) -> None:
        panel = tk.Frame(self.root)
        panel.pack(side=tk.TOP, fill=tk.X, padx=8, pady=4)
        self.sliders = {}
        for column, (name, (low, high, start)) in enumerate(SLIDERS.items()):
            scale = tk.Scale(
                panel, from_=low, to=high, resolution=SLIDER_RESOLUTION,
                orient=tk.HORIZONTAL, label=SLIDER_LABELS[name], showvalue=1, length=220,
            )
            scale.set(start)
            if name == "setpoint":  # applies only when let go (OQ-36)
                scale.bind("<ButtonRelease-1>", self._on_setpoint_release)
                scale.bind("<KeyRelease>", self._on_setpoint_release)
            else:  # gains apply while dragging
                scale.configure(command=lambda value, n=name: self.session.set_gain(n, value))
            scale.grid(row=0, column=column, padx=6)
            self.sliders[name] = scale

    def _on_setpoint_release(self, event=None) -> None:
        self.session.release_setpoint(self.sliders["setpoint"].get())

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
