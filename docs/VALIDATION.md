# Initial validation

Official NFL.com checks completed October 11, 2026:

| Player | Season/week | Catches | Receiving yards | Receiving TDs | Calculated half-PPR |
|---|---|---:|---:|---:|---:|
| Justin Jefferson | 2024 / 1 | 4 | 59 | 1 | 13.9 |
| Ja'Marr Chase | 2024 / 1 | 6 | 62 | 0 | 9.2 |

The receiving totals match downloaded nflverse records and official game logs:
- https://www.nfl.com/players/justin-jefferson/stats/logs/2024/
- https://www.nfl.com/players/ja-marr-chase/stats/logs/2024/

The half-PPR values are our calculations, not NFL.com fantasy scores.

Automated checks cover SQLite integrity, foreign keys, unique player/week
records, team/opponent schedule joins, and scoring arithmetic across every
imported row. The scoring unit test checks that adding half-PPR receptions
retains an example's rushing production and lost-fumble penalty.

These checks do not establish the accuracy of every source statistic. Before
modeling, expand official comparisons to a player with rushing production, a
lost fumble, and a missed game. Examine inactive/zero-event players separately
from byes. Source snapshots and counts are in `data/import_manifest.json`.

## PPR projection milestone (October 11, 2026)

The database now includes 2025 and available 2026 regular-season stats.
2026 Week 1 receiving totals for Matthew Golden (6 catches, 95 yards, 0 TD)
and Davante Adams (3 catches, 26 yards, 0 TD) were checked against NFL.com:
- https://www.nfl.com/players/matthew-golden/stats/logs/2026/
- https://www.nfl.com/players/davante-adams/stats/logs/2026/

Both match nflverse. Calculated full-PPR totals are 15.5 and 5.6 respectively.
These are source-data checks, not validation of the projection formula.

A last-eight-recorded-games PPR baseline is now implemented for the student's
five players in Weeks 1-4 of 2026. Actual outcomes are retrieved separately from
the projection inputs. Tests mutate target-week and future statistics to very
large numbers and verify that the predictions remain unchanged. Tests also
check that Week 1 uses only 2025 and Week 2 can use Week 1, and that a league
zero is included while a missing score is excluded.

The initial 20 nflverse comparisons yield MAE 6.913, RMSE 8.955, and average
signed error -1.936 PPR points. User league scores have not been provided yet.
This is a historical reconstruction from a corrected modern data snapshot,
not a prospectively recorded experiment. Source corrections may differ from
the data available at the time. There is no injury or availability model yet.

## User-confirmed Week 1 scores

The student supplied all five 2026 Week 1 league scores on October 11, 2026:
Adams 5.6, Burden 9.5, Egbuka 11.3, Harrison 4.3, Golden 15.5. All five match
the nflverse PPR totals. Comparing these confirmed outcomes with the unchanged
baseline yields MAE 7.424 and RMSE 8.501 across five player-games. Week 2-4
league scores remain pending; their current comparisons are nflverse only.
