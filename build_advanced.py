"""Download advanced datasets and build active receiver appearances/context."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import nflreadpy as nfl
import polars as pl

ROOT=Path(__file__).resolve().parent
SEASONS=[2022,2023,2024,2025,2026]
PBP_COLS=['game_id','season','week','season_type','posteam','defteam','yardline_100',
          'pass_attempt','receiver_player_id','play_type','two_point_attempt','epa','receiving_yards',
          'complete_pass','pass_touchdown']

def build(offline=False):
    data=ROOT/'data'
    if not offline:
        print('Downloading receiving drops and snap counts...',flush=True)
        nfl.load_pfr_advstats(SEASONS,stat_type='rec',summary_level='week').write_parquet(data/'advanced.parquet')
        nfl.load_snap_counts(SEASONS).write_parquet(data/'snaps.parquet')
        for season in SEASONS:
            print(f'Downloading passing plays: {season}',flush=True)
            pbp=nfl.load_pbp(season)
            pbp.select(PBP_COLS).filter((pl.col('season_type')=='REG') &
                (pl.col('pass_attempt')==1) & (pl.col('play_type')!='no_play') &
                (pl.col('two_point_attempt')==0)).write_parquet(data/f'passing_plays_{season}.parquet')
    metadata=pl.read_parquet(data/'players.parquet').to_dicts()
    mapping={r['pfr_id']:r['gsis_id'] for r in metadata if r.get('pfr_id')}
    snaps=pl.read_parquet(data/'snaps.parquet').filter(pl.col('game_type')=='REG')
    adv=pl.read_parquet(data/'advanced.parquet').filter(pl.col('game_type')=='REG')
    snap_by_key={}
    for r in snaps.to_dicts():
        pid=mapping.get(r['pfr_player_id'])
        if pid and r['position']=='WR' and r['offense_snaps']>0:
            snap_by_key[(pid,r['season'],r['week'])]=r
    adv_by_key={}
    for r in adv.to_dicts():
        pid=mapping.get(r['pfr_player_id'])
        if pid:
            adv_by_key[(pid,r['season'],r['week'])]=r
    pbp=pl.concat([pl.read_parquet(data/f'passing_plays_{s}.parquet') for s in SEASONS],how='diagonal_relaxed')
    rz=pbp.filter(pl.col('receiver_player_id').is_not_null() & (pl.col('yardline_100')<=20))
    rz_receiver={(r['receiver_player_id'],r['season'],r['week']):r['len'] for r in rz.group_by(['receiver_player_id','season','week']).len().to_dicts()}
    rz_team={(r['posteam'],r['season'],r['week']):r['len'] for r in rz.group_by(['posteam','season','week']).len().to_dicts()}
    defense=pbp.group_by(['defteam','season','week','game_id']).agg([
        pl.col('epa').mean().alias('pass_epa_allowed'),pl.len().alias('dropbacks')]).to_dicts()
    with sqlite3.connect(data/'receivers.sqlite') as c:
        c.row_factory=sqlite3.Row
        rows={ (r['player_id'],r['season'],r['week']):dict(r) for r in c.execute('SELECT * FROM weekly_stats')}
        valid_ids={r[0] for r in c.execute('SELECT player_id FROM players')}
        games={r[0] for r in c.execute('SELECT game_id FROM games')}
        appearances=[]
        for key in sorted(set(rows)|set(snap_by_key)):
            pid,season,week=key
            if pid not in valid_ids:continue
            st=rows.get(key);sn=snap_by_key.get(key);ad=adv_by_key.get(key,{})
            context=st or sn
            if context['game_id'] not in games:continue
            team=context['team'];opponent=context.get('opponent',context.get('opponent_team'))
            stat=lambda field: float(st[field] or 0) if st else 0.0
            appearances.append((pid,season,week,context['game_id'],team,opponent,
                stat('targets'),stat('receptions'),stat('receiving_yards'),stat('receiving_tds'),
                stat('fantasy_points_ppr'),stat('receiving_air_yards'),stat('receiving_yards_after_catch'),
                st.get('target_share') if st else 0.0,st.get('air_yards_share') if st else 0.0,
                sn['offense_pct'] if sn else None,ad.get('receiving_drop'),
                rz_receiver.get(key,0),rz_team.get((team,season,week),0),
                'stats' if st else 'positive_offensive_snaps_zero_stats'))
        c.executescript('''DROP TABLE IF EXISTS appearances; DROP TABLE IF EXISTS defense_context;
        CREATE TABLE appearances(player_id TEXT,season INT,week INT,game_id TEXT,team TEXT,opponent TEXT,
            targets REAL,receptions REAL,receiving_yards REAL,receiving_tds REAL,ppr REAL,
            air_yards REAL,yac REAL,target_share REAL,air_share REAL,snap_share REAL,drops REAL,
            red_zone_targets REAL,team_red_zone_targets REAL,row_source TEXT,
            PRIMARY KEY(player_id,season,week));
        CREATE TABLE defense_context(team TEXT,season INT,week INT,game_id TEXT,pass_epa_allowed REAL,
            dropbacks INT,wr_ppr_allowed REAL,PRIMARY KEY(team,season,week));
        CREATE INDEX appearance_player_history ON appearances(player_id,season,week);
        CREATE INDEX defense_history ON defense_context(team,season,week);''')
        wr_allowed={(r[0],r[1],r[2]):r[3] for r in c.execute('SELECT opponent,season,week,SUM(fantasy_points_ppr) FROM weekly_stats GROUP BY opponent,season,week')}
        with c:
            c.executemany('INSERT INTO appearances VALUES('+','.join('?'*20)+')',appearances)
            c.executemany('INSERT INTO defense_context VALUES(?,?,?,?,?,?,?)',[
                (r['defteam'],r['season'],r['week'],r['game_id'],r['pass_epa_allowed'],r['dropbacks'],
                 wr_allowed.get((r['defteam'],r['season'],r['week']),0)) for r in defense])
        counts={ 'appearances':len(appearances),
            'zero_event_active_games':sum(r[-1]!='stats' for r in appearances),
            'snap_share_coverage':sum(r[15] is not None for r in appearances)/len(appearances),
            'drops_coverage':sum(r[16] is not None for r in appearances)/len(appearances)}
    files=['advanced.parquet','snaps.parquet']+[f'passing_plays_{s}.parquet' for s in SEASONS]
    manifest={'built_at_utc':datetime.now(timezone.utc).isoformat(),'coverage':counts,
        'sha256':{f:hashlib.sha256((data/f).read_bytes()).hexdigest() for f in files},
        'sources':['https://github.com/nflverse/nflverse-data',
            'https://nflreadpy.nflverse.com/api/load_functions/'],
        'routes_status':'Not available in selected weekly datasets. Snap participation is a separate metric.',
        'weather_status':'No archived pregame forecasts imported. Actual game weather is excluded.',
        'injuries_status':'No verified pregame injury snapshots imported.'}
    (data/'advanced_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(counts,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--offline',action='store_true')
    build(p.parse_args().offline)
