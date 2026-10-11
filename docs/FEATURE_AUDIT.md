# Feature audit - October 11, 2026

| Feature | Source and definition | Current implementation |
|---|---|---|
| Targets and target share | nflverse weekly player stats | Prior 3 and up to 8 active/recorded games |
| Offensive snap participation | PFR snap counts via nflreadpy, offense_pct | Prior 3/8 games. This is not route participation |
| Catch rate | Prior catches / prior targets | Aggregate over up to 8 games |
| Receiving efficiency | Receiving yards / targets, YAC / catch | Aggregate over prior games |
| Air yards and air-yard share | nflverse weekly player stats | Prior usage and depth of opportunity |
| Drops | PFR weekly advanced receiving stats | Drops / targets over covered prior games |
| Red-zone targets | nflverse play-by-play targets inside opponent 20 | Prior receiver targets and share of team targets inside 20 |
| Defense strength | nflverse passing plays and WR statistics | Opponent's prior passing EPA per attempt and WR PPR allowed per game |
| Recent performance | Last 3 versus up to 8 games | Target and snap trends. Learned feature effects, no arbitrary multiplier |
| Route participation / targets per route | Absent from selected weekly datasets | Unavailable. Do not substitute snaps or invent values |
| Weather | Game schedules contain observed conditions, not archived forecasts | Observed target-game weather excluded to prevent hindsight |
| Pregame injuries and teammate absences | Requires reliable dated reports and availability modeling | Not integrated in this version |

Snap coverage: 96.03%. Drop coverage: 77.13% of 11,616 active/recorded receiver
appearances in this snapshot. Advanced source data is not assumed complete.
Missing values receive training-set medians with missing indicators inside the
model. The comparison table shows unavailable values rather than imputed values.

The app is conditional on the receiver playing. It does not forecast whether he
will play. Positive offensive snaps identify 1,184 games with no statistical
row, which the enhanced feature table includes as observed zero-event games.
It does not infer zeros for injured/inactive players or byes.

Red-zone share uses all identifiable team receiving targets inside the 20 as
the denominator for the receiver's included prior appearances. It is not a
season-wide team percentage. Two-point attempts and no-play records are excluded.
Drop rate uses targets from games that have a nonmissing PFR drop count, with
the nflverse targets as denominator. Small samples can yield unstable rates.

Sources:
- https://nflreadpy.nflverse.com/api/load_functions/
- https://github.com/nflverse/nflverse-data
- https://nflreadr.nflverse.com/articles/nflverse_data_schedule.html

The nflverse schedule documents that recent participation data is released
after the season, which limits its use as a current-season route source.
Future work should verify source licensing, definitions, and pregame availability
before adding route participation, forecasts, or injury adjustments.
