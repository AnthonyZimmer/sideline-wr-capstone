"""Build a reproducible WR-only SQLite snapshot from selected nflverse datasets."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sqlite3
import tempfile

ROOT = Path(__file__).resolve().parent
STAT_FIELDS = ['receptions', 'targets', 'receiving_yards', 'receiving_tds',
               'carries', 'rushing_yards', 'rushing_tds', 'receiving_fumbles_lost',
               'rushing_fumbles_lost', 'receiving_air_yards',
               'receiving_yards_after_catch', 'target_share', 'air_yards_share',
               'fantasy_points', 'fantasy_points_ppr']

def half_ppr(standard_points, receptions):
    """Retain nflverse standard scoring and add 0.5 points per reception."""
    return round(float(standard_points) + 0.5 * int(receptions), 4)

def require_columns(df, fields, label):
    missing = set(fields) - set(df.columns)
    if missing:
        raise ValueError(f'{label} missing required columns: {sorted(missing)}')

def validate_database(conn):
    if conn.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
        raise ValueError('SQLite integrity check failed')
    if conn.execute('PRAGMA foreign_key_check').fetchall():
        raise ValueError('Orphaned player/game records')
    bad = conn.execute('''SELECT COUNT(*) FROM weekly_stats s JOIN games g USING(game_id)
        WHERE s.season != g.season OR s.week != g.week
        OR NOT ((s.team = g.home_team AND s.opponent = g.away_team)
             OR (s.team = g.away_team AND s.opponent = g.home_team))
        OR ABS(s.fantasy_points_half_ppr - (s.fantasy_points_standard + 0.5*s.receptions)) > 0.0001
        OR ABS(s.fantasy_points_ppr - (s.fantasy_points_standard + s.receptions)) > 0.0001''').fetchone()[0]
    if bad:
        raise ValueError(f'{bad} inconsistent game/scoring records')
    count = conn.execute('SELECT COUNT(*) FROM weekly_stats').fetchone()[0]
    if not count:
        raise ValueError('No receiver records imported')
    return {'players': conn.execute('SELECT COUNT(*) FROM players').fetchone()[0],
            'games': conn.execute('SELECT COUNT(*) FROM games').fetchone()[0],
            'receiver_game_records': count,
            'records_per_season': dict(conn.execute('SELECT season, COUNT(*) FROM weekly_stats GROUP BY season'))}

def build(seasons, output_dir, offline=False):
    import nflreadpy as nfl
    import polars as pl
    output_dir.mkdir(parents=True, exist_ok=True)
    names = ('player_stats', 'schedules', 'players')
    # Offline rebuild uses the existing complete snapshots; no network needed.
    if offline:
        manifest = json.loads((output_dir / 'import_manifest.json').read_text())
        for n in names:
            digest = hashlib.sha256((output_dir / f'{n}.parquet').read_bytes()).hexdigest()
            if digest != manifest['sha256'][n]:
                raise ValueError(f'{n} snapshot differs from its recorded hash')
        datasets = [pl.read_parquet(output_dir / f'{n}.parquet') for n in names]
    else:
        print(f'Downloading nflverse datasets for {seasons}...', flush=True)
        datasets = [nfl.load_player_stats(seasons), nfl.load_schedules(seasons), nfl.load_players()]
    stats, schedules, players = datasets
    require_columns(stats, ['position', 'season_type', 'season', 'week', 'team',
                            'opponent_team', 'player_id', 'player_display_name'] + STAT_FIELDS, 'Player stats')
    require_columns(schedules, ['game_id', 'season', 'week', 'game_type', 'gameday',
                                'gametime', 'home_team', 'away_team', 'location'], 'Schedules')
    require_columns(players, ['gsis_id', 'display_name', 'rookie_season'], 'Players')
    stats = stats.filter((pl.col('position') == 'WR') & (pl.col('season_type') == 'REG') & pl.col('season').is_in(seasons))
    schedules = schedules.filter((pl.col('game_type') == 'REG') & pl.col('season').is_in(seasons))
    if set(stats['season'].unique().to_list()) != set(seasons):
        raise ValueError('Requested season has no WR data')
    if set(schedules['season'].unique().to_list()) != set(seasons):
        raise ValueError('Requested season has no schedule data')
    stat_rows = stats.to_dicts()
    ids = {r['player_id'] for r in stat_rows}
    players = players.filter(pl.col('gsis_id').is_in(list(ids)))
    player_info = {r['gsis_id']: r for r in players.to_dicts()}
    game_rows = schedules.to_dicts()
    game_lookup = {}
    for g in game_rows:
        for team in (g['home_team'], g['away_team']):
            key = (g['season'], g['week'], team)
            if key in game_lookup:
                raise ValueError(f'Ambiguous schedule: {key}')
            game_lookup[key] = g['game_id']
    # Build in a temporary file: validation failures leave the prior DB intact.
    fd, temp_name = tempfile.mkstemp(suffix='.sqlite', dir=output_dir)
    import os
    os.close(fd)
    temp_path = Path(temp_name)
    try:
        with sqlite3.connect(temp_path) as conn:
            conn.executescript((ROOT / 'schema.sql').read_text())
            with conn:
                names_by_id = {r['player_id']: r['player_display_name'] for r in stat_rows}
                conn.executemany('INSERT INTO players VALUES (?,?,?,?)', [
                    (pid, names_by_id[pid], 'WR', player_info.get(pid, {}).get('rookie_season')) for pid in sorted(ids)])
                conn.executemany('INSERT INTO games VALUES (?,?,?,?,?,?,?,?)', [
                    (g['game_id'], g['season'], g['week'], g['gameday'], g['gametime'],
                     g['home_team'], g['away_team'], g['location']) for g in game_rows])
                values = []
                for r in stat_rows:
                    game_id = game_lookup[(r['season'], r['week'], r['team'])]
                    values.append((r['player_id'], game_id, r['season'], r['week'], r['team'],
                                   r['opponent_team'], *(r[f] for f in STAT_FIELDS),
                                   half_ppr(r['fantasy_points'], r['receptions'])))
                marks = ','.join('?' for _ in values[0]) if values else ''
                if values:
                    conn.executemany(f'INSERT INTO weekly_stats VALUES ({marks})', values)
            summary = validate_database(conn)
        temp_path.replace(output_dir / 'receivers.sqlite')
    finally:
        temp_path.unlink(missing_ok=True)
    if not offline:
        for name, df in zip(names, (stats, schedules, players)):
            df.write_parquet(output_dir / f'{name}.parquet')
        manifest = {'downloaded_at_utc': datetime.now(timezone.utc).isoformat(),
                    'seasons': seasons, 'season_type': 'REG', 'position': 'WR',
                    'nflreadpy_version': importlib.metadata.version('nflreadpy'),
                    'source': 'https://github.com/nflverse/nflverse-data',
                    'sha256': {n: hashlib.sha256((output_dir / f'{n}.parquet').read_bytes()).hexdigest() for n in names},
                    'summary': summary}
        (output_dir / 'import_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (output_dir / 'validation_summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))
    return summary

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seasons', nargs='+', type=int, default=[2022, 2023, 2024, 2025, 2026])
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'data')
    parser.add_argument('--offline', action='store_true', help='Rebuild using downloaded Parquet snapshots')
    args = parser.parse_args()
    try:
        build(sorted(set(args.seasons)), args.output_dir, args.offline)
    except Exception as error:
        parser.exit(1, f'Import failed: {error}\n')
