# LEARNING

| Open Question | What it means | My answer |
|---|---|---|
| OQ-4: Which drag model? | How should the drag be calculated | Linear. The drone is slow so simple is enough. |
| OQ-7: What if thrust is too high? | What happens if you ask for a thrust that the motors are incapable of | Output it as maximum. No warnings, they would stack. |
| OQ-2: Real time or simulated time? | Should real time or a simulated time be used as baseline | Simulated one. Because the test results are always the same. |
| OQ-9: How accurate must tests be? | How close counts as correct | 0.6% checked after 1 second. |
| OQ-12: Speed first or height first? | The order of calculation | Speed first, then height. Keeps bounces realistic by not adding energy. |
| OQ-11: What happens at the ground? | The things happening while touching ground | Its height can't be negative and speed is 0 while simulation still runs |
| AQ-1: When does the ground stop the drone? | What counts as hitting the ground | When it's at 0 or below and still moving down. Otherwise it could land exactly on 0 and the old rule would miss it. |
| AQ-4: Normal numbers or NumPy? | Which kind of math to use for each step | Normal Python numbers. Each step needs the last step's answer, so NumPy can't speed it up. |
| AQ-3: Where does python-control go? | Is it needed to fly, or only to check answers | Only for testing. The drone doesn't need it to run. |
| IQ-1: A test needs features from later stories | What to do with a test that can't pass yet | Mark it "expected to fail". It warns me when it starts passing, so I don't forget it. |
| A planted bug was not caught | Breaking the code on purpose to see if the tests notice | The test only checked for the word "mass", so it passed on the wrong error. Made it stricter to check "greater than 0" too. |
| IQ-4: What if a story's tests pass before any code is written? | No red phase is possible because earlier code already does the job | Break the code on purpose and show the tests catch it. Proves the tests can fail. |
| OQ-27: Hover feed-forward? | Give the drone its hover thrust for free, PID only corrects | Yes. Otherwise the PID has to learn the weight and the drone sags at first. |
| OQ-28: Derivative on error or on altitude? | What the D part looks at | Altitude. On error, a setpoint change causes a one-step thrust spike (derivative kick). |
| OQ-30: Metric definitions | How rise time, overshoot, settling time and steady-state error are measured | python-control's: rise 10% to 90%, settle within 2% for good, overshoot past the final value, error = setpoint minus final altitude. |
| AQ-12: Which python-control model is the reference? | An independent ideal model of the drone to compare against | The smooth continuous model. Worst difference was 0.6%, inside the 2% rule. |