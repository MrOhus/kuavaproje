# LEARNING

| Open Question | What it means | My answer |
|---|---|---|
| Which drag model? | How should the drag be calculated | Linear. The drone is slow so simple is enough. |
| What if thrust is too high? | What happens if you ask for a thrust that the motors are incapable of | Output it as maximum. No warnings, they would stack. |
| Real time or simulated time? | Should real time or a simulated time be used as baseline | Simulated one. Because the test results are always the same . |
| How accurate must tests be? | How close counts as correct | 0.6% checked after 1 second. |
| Speed first or height first? | The order of calculation | Speed first, then height. Keeps bounces realistic by not adding energy. |
| What happens at the ground? | The things happening while touching ground | Its height can't be negative and speed is 0 while simulation still runs |