-- Use a SQLite editor (such as DB Browser for SQLite) with data/receivers.sqlite.
SELECT season, COUNT(*) AS receiver_game_records FROM weekly_stats GROUP BY season;

SELECT display_name, week, opponent, targets, receptions, receiving_yards,
       receiving_tds, fantasy_points_half_ppr
FROM receiver_game_log
WHERE display_name IN ('Justin Jefferson', 'Ja''Marr Chase') AND season = 2024
ORDER BY week, display_name;

-- Only PRIOR games belong in features for a prediction of Week 8.
SELECT display_name, AVG(targets) AS prior_average_targets,
       AVG(fantasy_points_half_ppr) AS prior_average_points
FROM receiver_game_log WHERE season = 2024 AND week < 8
GROUP BY player_id ORDER BY prior_average_points DESC;
