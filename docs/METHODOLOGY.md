# Sideline methodology and findings

## Project contribution

Sideline brings receiver opportunity, efficiency, and matchup statistics into a
two-player web comparison. It reduces research effort and exposes the evidence
behind a lineup decision. The project does not claim that player comparisons
are unique in the fantasy industry or that more features guarantee better accuracy.

## Data and Python/SQL architecture

Python downloads and validates nflverse data. SQLite stores player and game
identities, WR weekly stats, active/recorded appearances, and defensive context.
Flask serves a local web interface and validates comparison requests. The
feature builder queries only the previous season and earlier target-season
weeks. The browser receives predictions and readable input comparisons.

GSIS IDs join players. PFR IDs map advanced stats and snaps to GSIS using the
player snapshot. Rows with known offensive participation but no statistical
events receive zeros in the enhanced appearance table. Inactive status remains
unknown. Historical team assignment in evaluation assumes the game roster
was known pregame. The app uses the latest earlier team or a user override.

## Projection model

A random forest estimates targets, receptions, receiving yards, receiving
touchdowns, and other PPR contributions from 24 historical features. Full-PPR
points equal predicted catches + 0.1 x receiving yards + 6 x receiving TDs +
other contributions. Other contributions include rushing, passing, conversion,
and fumble effects represented in standard nflverse scoring.

Features cover recent targets, target share, snap share, catch rate, receiving
efficiency, air yards, air share, YAC, drops, red-zone involvement, historical
scores, trends, opponent WR points allowed, opponent passing EPA, history size,
and home/away context. Routes, archived forecasts, and injury status are absent.

Train: 5,168 eligible 2023-2024 receiver appearances with at least three earlier
games. 2022 supplies history. Parameters: 240 trees, minimum 15 samples per leaf,
maximum depth 12, feature fraction 0.8, random seed 440. Median imputation fits
only training data and includes missing indicators. The model is frozen after
training, with no retraining or tuning on the 2025 or 2026 outcomes.

## Chronological evaluation

| Evaluation | Player-games | Enhanced MAE | Average baseline MAE | Enhanced RMSE | Baseline RMSE |
|---|---:|---:|---:|---:|---:|
| 2025 validation | 2,585 | 4.218 | 4.207 | 5.764 | 5.921 |
| 2026 Weeks 1-4 diagnostic replay | 560 | 4.504 | 4.539 | 6.351 | 6.514 |
| Student's 5 receivers, 2026 Weeks 1-4 | 20 | 6.301 | 6.914 | 8.592 | 8.955 |

The evaluation baseline averages the same prior active/recorded games. It can
differ slightly from the original recorded-statistics-only baseline. MAE is the
mean absolute PPR miss. RMSE emphasizes large misses. These are conditional
appearance results, not all rostered player-weeks or an availability forecast.

The enhanced model does not beat the average baseline on 2025 MAE. Its 2025
RMSE is lower. The differences are descriptive, without a significance test.
2026 outcomes were inspected earlier in development, so label that comparison
diagnostic replay, not an untouched test. Modern corrected source snapshots
may differ from data available at the original forecast time.

The student verified all five 2026 Week 1 scores. Week 2-4 league totals are
pending; source-based comparisons remain provisional. The same five Week 1
outcomes can help explain errors but are too small to establish general accuracy.

## Recommendation and uncertainty

The higher projected PPR score receives the edge. Gaps under 2 points get a
close-comparison label. This 2-point display threshold is a product rule,
not a validated probability of winning. Input highlights identify which player
has higher prior usage metrics and do not claim causal model attribution.
The displayed error range uses the 80th percentile of absolute 2025 validation
residuals. It is illustrative, not a calibrated player-specific confidence interval.

## Verification and next work

Tests check data integrity, scoring, duplicate protection, league-score missing
values, request validation, and exclusion of target/future usage and defensive
outcomes. User acceptance tests remain to be completed by the student.

Priorities: verify Week 2-4 league scores, collect task-based user feedback,
model availability, verify weekly routes/forecast feeds, then test a revised
model on new future weeks. Keep the original baseline and current model as
benchmarks. Document improvements without selecting only favorable examples.
