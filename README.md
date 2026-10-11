# Wide Receiver Fantasy Football Capstone - Data Foundation

This project connects **Python and SQL**. Python downloads selected nflverse
datasets and builds a SQLite database containing **wide receivers only**, with
regular-season game logs for **2022-2026**, as available in the October 11, 2026
snapshot. The included database works offline. A **full-PPR historical baseline**
now generates projections for the student's five receivers in 2026 Weeks 1-4.
The local **Flask web comparison interface** now runs with an enhanced
component model. Read `docs/METHODOLOGY.md` for its evaluation and limitations.

## Open the web app

On Windows, double-click **start_app.bat** after extracting the ZIP. This creates
a Python 3.12 environment, installs the pinned requirements, and starts the app.
First-time setup needs internet access and Python 3.12. If the browser opens
before the server is ready, refresh it when the terminal says it is running.

For manual setup, use the environment commands below and then run:

```bat
python app.py
```

Open **http://127.0.0.1:5000** in your browser. Select two receivers, a season,
and a week, then click Compare receivers. Leave the terminal open while using
the app. Press Ctrl+C in the terminal to stop it. The included data and trained
model let you use it offline after installation. This version is local software,
not a publicly hosted website.

The saved model expects the pinned scikit-learn version. Only load the supplied
model file or one you trained yourself. Rebuild it with `python model.py` if
needed. This capstone server binds to your computer only.

## Start here (Windows)

1. Install Python 3.12 from https://www.python.org/downloads/ if needed.
2. Extract this ZIP. Open the extracted `wr_capstone` folder.
3. Click the File Explorer address bar, type `cmd`, and press Enter.
4. Run these commands one at a time:

```bat
py -3.12 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python inspect_data.py
python inspect_data.py --player "Ja'Marr Chase" --season 2024
python projections.py
python -m unittest discover -s tests -v
```

The inspection and projection commands query the included SQL database. They do not download
data. Package installation needs internet access.

## Import or rebuild

```bat
python import_data.py
```

This downloads 2022-2026 stats, schedules, and player information; keeps WR
regular-season records; validates them; and replaces `data/receivers.sqlite`.
It rebuilds the database instead of appending, preventing duplicate imports.
Failed data validation leaves the previous database intact. Keep your own
analysis in another database: this command rebuilds all tables in this one.

After rebuilding the base database, regenerate the advanced tables and model:

```bat
python build_advanced.py
python model.py
```

`build_advanced.py --offline` rebuilds from the included advanced snapshots.
The enhanced model trains only on 2023-2024 and evaluates 2025 chronologically.
2026 comparisons are diagnostic replay results. The original baseline's frozen
prediction files remain separate.

To rebuild from the included source snapshots without downloading:

```bat
python import_data.py --offline
```

To request different seasons, pass them explicitly:

```bat
python import_data.py --seasons 2023 2024
```

The imported data is historical, not live. Additional seasons should be added
deliberately after validation. The included tests expect 2024 to be present.

On macOS/Linux, use `python3 -m venv .venv`, then
`source .venv/bin/activate`, followed by the same `python` commands.

## What SQL stores

| Table/view | Purpose |
|---|---|
| `players` | Stable GSIS player ID, display name, WR designation, rookie season |
| `games` | Game ID, season/week, date, kickoff time in ET, teams, location |
| `weekly_stats` | WR game stats, historical team/opponent, standard/PPR/half-PPR points |
| `receiver_game_log` | Joined player names, weekly stats, dates, and venue |

Keys prevent duplicate player-season-week rows. Foreign keys prevent orphaned
players or games. `example_queries.sql` includes SQL you can run in a SQLite
editor. Python uses SQLite's built-in driver; no separate SQL server is needed.

## PPR baseline and league comparison

Our current league comparison uses **full PPR**, following the student's latest
instruction. Run `python projections.py` to see the precomputed baseline.
Each projection is the mean PPR score from the last eight **recorded** games,
restricted to the previous season and earlier weeks of the target season.
Week 1 uses 2025 history only; later weeks can include earlier 2026 outcomes.
This is a reconstructed historical test, not a prediction actually issued
before kickoff. The formula does not adjust for opponents, injuries, offseason
role changes, or a player's probability of playing.

Results are in `results/2026_ppr_baseline/`:
- `projections.csv`: 20 projections, without actual outcomes.
- `frozen_projections.json`: projections and the history weeks used.
- `nflverse_comparison.csv`: preliminary comparison with nflverse PPR totals.
- `evaluation.json`: overall, weekly, and player-level error metrics.
- `league_scores.csv`: blank template for the student's actual fantasy scores.

Open `league_scores.csv` in Excel and enter your scores in `actual_ppr`. Keep
IDs, seasons, and week numbers unchanged, save as CSV, then run:

```bat
python projections.py --league-scores results/2026_ppr_baseline/league_scores.csv
```

A numeric 0 means an actual zero score; a blank means a score is not entered.
League results go into separate files and do not overwrite the preliminary
nflverse comparison. Any league bonuses or different yardage rules need to be
identified before interpreting errors as projection error rather than a scoring
mismatch.

Mean absolute error (MAE) means the average miss in PPR points; lower is better.
RMSE weights large misses more strongly. Signed error is projection minus
actual: positive means overprojection; negative means underprojection.

Frozen predictions cannot be silently changed. New formulas or corrected-data
experiments must use another `--output-dir`. Our initial test has only 20
outcomes and is not evidence of general model accuracy. The baseline and next
model should also be evaluated on a larger historical WR sample.

## Stored scoring and interpretation

Half-PPR points = nflverse `fantasy_points` + 0.5 x receptions.
This preserves nflverse's standard fantasy scoring, including WR rushing and
other scoring contributions. We also keep nflverse full-PPR totals and check
that they equal standard points plus receptions. These columns represent
**actual outcomes**, never pregame features for that same game.

Missing player-week rows do **not** automatically mean zero points. A player
may have a bye, be inactive, or have no recorded statistical events. This first
version does not create a complete participation/availability table. We will
address that before evaluating start/sit recommendations. Nullable advanced
statistics stay missing instead of being silently filled with zero.

Player metadata is downloaded at import time. Historical team membership comes
from weekly stats, not a player's current team. Player names are labels; SQL
joins use stable player IDs. Schedule kickoff values are ET, not UTC timestamps.

## Reproducibility and attribution

`data/import_manifest.json` records the download time, package version, seasons,
record counts, and SHA-256 hashes of the filtered Parquet snapshots. The
snapshots preserve all downloaded columns for the selected WR/game/player rows;
the SQL database retains only the project fields. `validation_summary.json`
records database checks. Preserve a copy before importing newer corrected data.

Data: nflverse contributors, https://github.com/nflverse/nflverse-data,
CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/).
Python loader: https://github.com/nflverse/nflreadpy.
Official game-log checks and validation limits are in `docs/VALIDATION.md`.

## Next milestone

Compare the frozen PPR baseline against the student's league scores. Then build
an enhanced model and evaluate it on a broader later-week test set. Preliminary
baseline errors are in `results/2026_ppr_baseline/evaluation.json`.
The application is implemented locally. GitHub publication, user acceptance
testing, the student's recorded presentation, and Week 2-4 league-score
confirmation remain outstanding. Assignment documents and presentation
materials accompany the project as a reviewable draft of the current version.

## Assignment materials

Open `deliverables/Sideline_Presentation.pptx` for the 12-slide bullet-point
presentation with actual interface screenshots and speaker notes. Review
`deliverables/Recording_Guide.md` before recording with your face visible.
The same folder contains six PDFs covering functional decomposition, technical
and operational flows, Gantt/PERT/critical path, screenshot evidence and findings.
`docs/SUBMISSION_CHECKLIST.md` identifies the unfinished student activities.
`docs/AI_USAGE.md` contains a partial log of actual student-authored messages.
The public repository and separate-computer check are not yet complete.
