"""The live desktop window (Tkinter, ARCHITECTURE_899eaea.md D-16).

The window holds no simulation state: it draws the LiveSession and forwards
the user's input to it. Everything runs in the Tk thread (D-17).
"""

import math
import time
import tkinter as tk
from tkinter import ttk

from .live import SLIDER_RESOLUTION, SLIDERS, THRUST_Y_RANGE, LiveSession, format_row

FRAME_INTERVAL_MS = 16  # target about 60 fps

SLIDER_LABELS = {
    "kp": "Kp (N/m)",
    "ki": "Ki (N/(m·s))",
    "kd": "Kd (N·s/m)",
    "setpoint": "Setpoint (m)",
}

# Plot geometry (pixels): canvas size and the margins around the plot area.
PLOT_W, PLOT_H = 900, 220
LEFT, RIGHT, TOP, BOTTOM = 56, 14, 12, 24

ALTITUDE_COLOR = "#1f6fb4"
SETPOINT_COLOR = "#d62728"
THRUST_COLOR = "#2b2b2b"
GRID_COLOR = "#9a9a9a"

TABLE_COLUMNS = (
    ("time", "Time of change (s)", 120),
    ("change", "From → to (m)", 130),
    ("rise", "Rise time (s)", 110),
    ("overshoot", "Overshoot (%)", 110),
    ("settling", "Settling time (s)", 120),
    ("error", "Steady-state error (m)", 150),
)


def _x(t, x0, x1):
    return LEFT + (t - x0) / (x1 - x0) * (PLOT_W - LEFT - RIGHT)


def _y(value, y0, y1):
    return TOP + (y1 - value) / (y1 - y0) * (PLOT_H - TOP - BOTTOM)


def _ticks(low, high, count=5):
    """Round tick values covering [low, high]."""
    raw = (high - low) / count
    magnitude = 10 ** math.floor(math.log10(raw))
    step = next(m * magnitude for m in (1, 2, 5, 10) if m * magnitude >= raw)
    first = math.ceil(low / step) * step
    return [first + i * step for i in range(int((high - first) / step + 1e-9) + 1)]


class App:
    def __init__(self, root: tk.Tk, clock=time.perf_counter):
        self.root = root
        self.clock = clock
        self.session = LiveSession(clock())
        root.title("Drone altitude — live PID simulation")
        root.protocol("WM_DELETE_WINDOW", self.close)
        self._build_sliders()
        self._build_plots()
        self._build_table()
        self._build_status()
        self._job = root.after(FRAME_INTERVAL_MS, self._loop)

    # --- layout ---------------------------------------------------------------

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

    def _build_plots(self) -> None:
        self.altitude_plot = self._canvas("Altitude (blue) and setpoint (red), m")
        self.thrust_plot = self._canvas("Thrust used, N")
        self.lines = {
            "setpoint": self.altitude_plot.create_line(
                0, 0, 0, 0, fill=SETPOINT_COLOR, width=2, dash=(6, 3)),
            "altitude": self.altitude_plot.create_line(0, 0, 0, 0, fill=ALTITUDE_COLOR, width=2),
            "thrust": self.thrust_plot.create_line(0, 0, 0, 0, fill=THRUST_COLOR, width=2),
        }
        self.limit_lines = tuple(
            self.thrust_plot.create_line(
                LEFT, self.thrust_y(value), PLOT_W - RIGHT, self.thrust_y(value),
                fill=GRID_COLOR, dash=(2, 2))
            for value in (0.0, 30.0)
        )

    def _canvas(self, title: str) -> tk.Canvas:
        canvas = tk.Canvas(self.root, width=PLOT_W, height=PLOT_H, bg="white",
                           highlightthickness=0)
        canvas.pack(side=tk.TOP, padx=8, pady=2)
        canvas.create_rectangle(LEFT, TOP, PLOT_W - RIGHT, PLOT_H - BOTTOM, outline=GRID_COLOR)
        canvas.create_text(LEFT + 6, TOP + 4, text=title, anchor="nw", fill="#444444")
        return canvas

    def _build_table(self) -> None:
        self.table = ttk.Treeview(
            self.root, columns=[c[0] for c in TABLE_COLUMNS], show="headings", height=5
        )
        for key, title, width in TABLE_COLUMNS:
            self.table.heading(key, text=title)
            self.table.column(key, width=width, anchor="e")
        self.table.pack(side=tk.TOP, padx=8, pady=4, fill=tk.X)
        self._shown_rows = None

    def _build_status(self) -> None:
        status = tk.Frame(self.root)
        status.pack(side=tk.BOTTOM, fill=tk.X, padx=8, pady=4)
        self.fps_label = tk.Label(status, text="0 fps", width=8, anchor="w")
        self.fps_label.pack(side=tk.LEFT)

    # --- input ----------------------------------------------------------------

    def _on_setpoint_release(self, event=None) -> None:
        self.session.release_setpoint(self.sliders["setpoint"].get())

    # --- drawing --------------------------------------------------------------

    def thrust_y(self, value: float) -> float:
        """Canvas y of a thrust value on the fixed thrust axis."""
        return _y(value, *THRUST_Y_RANGE)

    def frame(self) -> None:
        """One frame: take the due steps and redraw."""
        now = self.clock()
        session = self.session
        session.tick(now)
        self._draw_plots()
        self._draw_table()
        self.fps_label.configure(text=f"{session.fps(now)} fps")

    def _draw_table(self) -> None:
        rows = [format_row(m) for m in self.session.metrics_rows()]
        if rows == self._shown_rows:
            return
        self.table.delete(*self.table.get_children())
        for row in rows:  # newest first, so newest on top
            self.table.insert("", tk.END, values=row)
        self._shown_rows = rows

    def _draw_plots(self) -> None:
        session = self.session
        points = session.plot_points()
        if len(points) == 1:
            points = points * 2  # a line needs two points
        x0, x1 = session.plot_x_range()
        a0, a1 = session.altitude_y_range()
        xs = [_x(p[0], x0, x1) for p in points]
        self._set_line(self.altitude_plot, "altitude", xs, [_y(p[1], a0, a1) for p in points])
        self._set_line(self.altitude_plot, "setpoint", xs, [_y(p[2], a0, a1) for p in points])
        self._set_line(self.thrust_plot, "thrust", xs, [self.thrust_y(p[3]) for p in points])
        self._draw_axes(self.altitude_plot, x0, x1, a0, a1)
        self._draw_axes(self.thrust_plot, x0, x1, *THRUST_Y_RANGE, y_ticks=[0, 10, 20, 30])

    def _set_line(self, canvas, name, xs, ys) -> None:
        flat = [v for pair in zip(xs, ys) for v in pair]
        canvas.coords(self.lines[name], *flat)

    def _draw_axes(self, canvas, x0, x1, y0, y1, y_ticks=None) -> None:
        canvas.delete("axis")
        for t in _ticks(x0, x1):
            x = _x(t, x0, x1)
            canvas.create_text(x, PLOT_H - BOTTOM + 4, text=f"{t:g} s", anchor="n",
                               fill="#444444", tags="axis")
        for value in y_ticks if y_ticks is not None else _ticks(y0, y1):
            y = _y(value, y0, y1)
            canvas.create_text(LEFT - 6, y, text=f"{value:g}", anchor="e",
                               fill="#444444", tags="axis")

    def _loop(self) -> None:
        start = self.clock()
        self.frame()
        elapsed_ms = (self.clock() - start) * 1000.0
        self._job = self.root.after(max(1, int(FRAME_INTERVAL_MS - elapsed_ms)), self._loop)

    def close(self) -> None:
        self.root.after_cancel(self._job)
        self.root.destroy()
