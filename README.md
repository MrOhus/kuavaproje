# kuavaproje — drone altitude simulation with a live PID controller

A deterministic simulation of a drone's height above the ground. The drone has gravity, mass, a thrust limit and drag, and it is simulated in fixed 200 Hz steps. A PID controller sets the thrust to reach and hold an altitude setpoint. After every setpoint change, the simulation measures how well the controller did.

A desktop app runs the simulation live. You tune the controller with sliders and watch the response in real time.

## Requirements

- Python 3.12 or newer, with Tkinter (Tcl/Tk). Tkinter is included in the python.org installers for Windows and macOS. On Linux, install your distribution's `python3-tk` package.
- The app itself needs nothing beyond the standard library. The test tools (pytest, python-control) are installed by the setup command below.

## Setup (do this first)

Run the setup once before starting the app or the tests. Without it, `python -m kuava_sim` fails with `No module named kuava_sim`, because Python cannot find the package yet.

1. Open a terminal in the repository folder.
2. Create a virtual environment called `.venv`. Skip this step if the `.venv` folder already exists.

   ```sh
   python -m venv .venv
   ```

3. Activate `.venv`. The command depends on your terminal:

   | Terminal | Command |
   |---|---|
   | Windows PowerShell | `.venv\Scripts\Activate.ps1` |
   | Windows Command Prompt | `.venv\Scripts\activate.bat` |
   | Git Bash on Windows | `source .venv/Scripts/activate` |
   | macOS / Linux | `source .venv/bin/activate` |

   When it is active, the prompt starts with `(.venv)`. If PowerShell refuses to run the script, allow it once for your user with `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then try again.

4. Install the package and the test tools into `.venv`:

   ```sh
   python -m pip install -e ".[dev]"
   ```

Activate `.venv` again (step 3) in every new terminal before running the commands below. Steps 2 and 4 are needed only once.

## Start the app

```sh
python -m kuava_sim
```

The drone starts on the ground at rest, with the controller on (Kp 4, Ki 1, Kd 3, setpoint 10 m). It is a fixed 1 kg drone with drag coefficient 0.5 N·s/m and a 30 N maximum thrust. The simulation runs in real time: one simulated second per second.

If the app cannot start, it prints one line saying what is missing and how to fix it, for example `Cannot start: no display available. Run the app from a desktop session.`, and exits with code 1.

### What the window shows and how to use it

| Part | What it does |
|---|---|
| **Kp, Ki, Kd** sliders | Proportional (N/m), integral (N/(m·s)) and derivative (N·s/m) gains. A new value is used from the next step, even while you drag. |
| **Setpoint** slider | Target altitude, 0–100 m. It changes only when you let go of the slider (mouse button or arrow key released), so one drag is one setpoint change. |
| Upper plot | Altitude (blue) and setpoint (red, dashed) over the last 20 s. |
| Lower plot | Thrust actually used (N), with the 0 N and 30 N limits marked. |
| Metrics table | One row per setpoint change, newest on top: rise time, overshoot, settling time and steady-state error. The newest row updates while the response develops. |
| **Pause** / **Resume** | Stops and continues the simulation. The sliders still work while paused, and changes take effect when you resume. |
| **Reset** | Starts again from the ground at time 0, keeping the current slider values. Clears the plots and the table. |
| **Wind gust** | Pushes the drone down with 5 N for 0.5 s. Pressing again during a gust restarts it. Disabled while paused. |
| Status line | The measured frame rate (fps). If something goes wrong, a short red message appears there and the simulation pauses; press Resume or Reset to continue. |

All sliders have a resolution of 0.1. The gains range from 0 to 50 (Kp) and 0 to 20 (Ki, Kd).

## Metric definitions

The metrics follow python-control's `step_info` with its default settings, applied to the altitude response after each setpoint change:

- The **signal** is the altitude minus the altitude at the moment of the change. It is taken from the change until the next change, or until now for the newest row, so it starts at 0.
- The **final value** is the signal's last sample, as `step_info` uses it.

| Metric | Definition | Unit |
|---|---|---|
| **Rise time** | Time from the signal first reaching 10 % of the final value to first reaching 90 % of it (10 % to 90 %). | s |
| **Overshoot** | How far the peak goes beyond the final value, in percent of the final value. It is 0 if the signal never goes beyond it. | % |
| **Settling time** | Time from the change until the signal stays within 2 % of the final value for good. | s |
| **Steady-state error** | setpoint − final altitude. Positive means the drone is below the setpoint. | m |

A metric that has not happened yet, for example a rise time just after a change, is shown as **not reached**. The same applies to rise time, overshoot and settling time when there is no step to measure (a change of exactly 0 m).

All times are measured from the moment of the change, in steps of 5 ms. The tests check that these metrics equal `step_info` run on the same signal. Where the thrust stays inside its limits and the drone never touches the ground, they also match a python-control closed-loop model within 2 %.

## Run all tests

```sh
python -m pytest
```

This runs every test, including the window tests and the comparisons with python-control. Window tests open a real window for a moment. On a machine without a display, they are skipped, and the reason is printed in the summary.

## Using the simulation from code

```python
from kuava_sim import SimConfig, Simulation

sim = Simulation(SimConfig(mass=1.0, drag_coeff=0.5, max_thrust=30.0))
sim.enable_controller(kp=4.0, ki=1.0, kd=3.0, setpoint=10.0)
sim.run(2000)                 # 10 s at 200 Hz
sim.gust()                    # 5 N down for the next 100 steps
sim.run(2000)
print(sim.altitude, sim.step_metrics()[-1])
```

## Project documents

- Requirements: [docs/design/](docs/design/DESIGN.md)
- Architecture: [docs/architecture/](docs/architecture/ARCHITECTURE.md)
- Implementation log: [docs/implementation/IMPLEMENTATION_LOG.md](docs/implementation/IMPLEMENTATION_LOG.md)
- Approvals: [docs/APPROVAL_LOG.md](docs/APPROVAL_LOG.md)
