# Initial PPR baseline results

Season: 2026. Players: Matthew Golden, Davante Adams, Emeka Egbuka, Luther Burden III, Marvin Harrison Jr.

Method: mean of each player's last eight recorded PPR game scores before the target week. Week 1 uses only 2025 history. Each later week uses earlier completed weeks plus prior-season history.

**These are historical reconstructions and preliminary nflverse comparisons. User league scores have not yet been supplied.**

| Week | Player-games | Average absolute miss (PPR points) |
|---|---:|---:|
| 1 | 5 | 7.42 |
| 2 | 5 | 9.62 |
| 3 | 5 | 6.62 |
| 4 | 5 | 3.99 |

Overall MAE: 6.91. RMSE: 8.96. Average signed error: -1.94 (negative means underprojection).

Interpretation: a simple scoring average can lag changes in playing role and cannot anticipate large touchdown/yardage swings. It does not account for opponents or injuries. These 20 comparisons are a small diagnostic sample, not a general accuracy claim. Missing source game rows are excluded rather than labeled zero, which can bias a recorded-game average.

Next: compare the same frozen projections with the student's league scores and check scoring rules, then evaluate improvements using a separate broader test set.
