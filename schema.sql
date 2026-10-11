PRAGMA foreign_keys = ON;
CREATE TABLE players (
    player_id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    position TEXT NOT NULL CHECK (position = 'WR'),
    rookie_season INTEGER
);
CREATE TABLE games (
    game_id TEXT PRIMARY KEY,
    season INTEGER NOT NULL,
    week INTEGER NOT NULL,
    game_date TEXT NOT NULL,
    kickoff_time_et TEXT,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    location TEXT
);
CREATE TABLE weekly_stats (
    player_id TEXT NOT NULL REFERENCES players(player_id),
    game_id TEXT NOT NULL REFERENCES games(game_id),
    season INTEGER NOT NULL,
    week INTEGER NOT NULL,
    team TEXT NOT NULL,
    opponent TEXT NOT NULL,
    receptions INTEGER NOT NULL CHECK (receptions >= 0),
    targets INTEGER NOT NULL CHECK (targets >= receptions),
    receiving_yards REAL NOT NULL,
    receiving_tds INTEGER NOT NULL,
    carries INTEGER NOT NULL,
    rushing_yards REAL NOT NULL,
    rushing_tds INTEGER NOT NULL,
    receiving_fumbles_lost INTEGER NOT NULL,
    rushing_fumbles_lost INTEGER NOT NULL,
    receiving_air_yards REAL,
    receiving_yards_after_catch REAL,
    target_share REAL,
    air_yards_share REAL,
    fantasy_points_standard REAL NOT NULL,
    fantasy_points_ppr REAL NOT NULL,
    fantasy_points_half_ppr REAL NOT NULL,
    PRIMARY KEY (player_id, season, week)
);
CREATE INDEX stats_game_idx ON weekly_stats(game_id);
CREATE VIEW receiver_game_log AS
SELECT p.display_name, s.*, g.game_date, g.kickoff_time_et,
       CASE WHEN g.location = 'Neutral' THEN 'neutral'
            WHEN s.team = g.home_team THEN 'home' ELSE 'away' END AS venue
FROM weekly_stats s JOIN players p USING(player_id) JOIN games g USING(game_id);
