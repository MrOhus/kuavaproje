# LEARNING

| Open Question | What it means, in my own words | My final answer |
|---|---|---|
| OQ-12: Is a specific integration method required (explicit Euler, semi-implicit/symplectic Euler, RK4, exact analytic), or is it the architect's choice subject to the tolerances in OQ-9? | How the sim calculates each tiny step | Speed first, then height. It's simple and stays accurate. |
| OQ-13: What scope does "fully deterministic" cover: same process, same machine/build, or bit-identical across OSes, CPUs and compilers? | How exactly two runs must match | Same computer and same code give the exact same numbers. |
| OQ-24: With linear drag and semi-implicit Euler at dt = 0.005 s, velocity oscillates if b·dt/m ≥ 1 (b ≥ 200·m) and becomes unstable if b·dt/m ≥ 2. Should such configurations be rejected, accepted with that behaviour, or otherwise handled? | Too much drag makes the speed unstable, what to do? | Show an error if drag is 200 × mass or more. |
| OQ-26: What does "match python-control's step_info within 2 %" compare? | What results are checked against | The math against python-control on the same flight, and the drone against python-control's ideal drone. |
| OQ-27: Does the thrust include a hover feed-forward? | Should the drone be given enough thrust to float for free | Yes. Otherwise the drone sinks first while the PID figures it out. |
| OQ-28: The exact PID formula. | Which PID to use | The drone's height, not the error. Using the error gives a big thrust spike when the target changes. |
| OQ-30: Exact metric definitions. | How to measure how well the drone reaches its target | The same way python-control does: how fast it gets there, how far it overshoots, when it settles, and how far off it ends. |
| AQ-4: What kind of numbers does the step use? | Normal Python numbers or NumPy | Normal numbers. Each step needs the last one, so NumPy can't speed it up. |
| AQ-5: How are the saved records stored? | How the saved data is kept | One tight block of numbers. It uses less memory. |
| AQ-9: Order inside a controlled step. | Which part of the PID is calculated first | Add the new error first, then calculate thrust, so it isn't one step late. |
| AQ-11: "Within 2 %" when the reference is 0 or NaN. | What happens when the reference is NaN or zero | If it's zero, being within 0.02 is fine. If both say "no answer", that counts as a match. |
| AQ-12: Which python-control model for OQ-26? | Which ideal drone we compare against | The smooth one. It only matches when the drone moves slowly, so the tests use slow settings. |
| IQ-5: How should the separate-process test run and compare? | How to prove a fresh run gives the same results | Run it twice with Python's hidden randomness set differently. If the results are identical, nothing depends on luck. |