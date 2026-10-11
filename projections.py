"""Reconstruct a simple preweek PPR baseline; evaluate outcomes separately."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parent
ROSTER = {
    'Matthew Golden': '00-0040667',
    'Davante Adams': '00-0031381',
    'Emeka Egbuka': '00-0040129',
    'Luther Burden III': '00-0040735',
    'Marvin Harrison Jr.': '00-0039849',
}
MODEL = 'mean_last_8_recorded_games_ppr_v1'
WINDOW = 8

def project(conn, player_id, season, week):
    # A deliberate whole-week cutoff excludes ALL target-week outcomes.
    # Use only the previous season and earlier weeks of the target season.
    rows = conn.execute('''SELECT season, week, fantasy_points_ppr, targets,
        receptions, receiving_yards, receiving_tds
        FROM weekly_stats WHERE player_id = ? AND
        (season = ? OR (season = ? AND week < ?))
        ORDER BY season DESC, week DESC LIMIT ?''',
        (player_id, season-1, season, week, WINDOW)).fetchall()
    if not rows:
        raise ValueError(f'No earlier recorded games for {player_id}; no projection issued')
    if any((r[0],r[1]) >= (season,week) for r in rows):
        raise ValueError('Target/future data entered the projection')
    n = len(rows)
    return {'player_id': player_id, 'season': season, 'week': week,
            'projected_ppr': round(sum(r[2] for r in rows)/n, 2),
            'history_games': n,
            'history_weeks': [f'{r[0]}-W{r[1]}' for r in rows],
            'prior_average_targets': round(sum(r[3] for r in rows)/n,2),
            'prior_average_receptions': round(sum(r[4] for r in rows)/n,2),
            'prior_average_receiving_yards': round(sum(r[5] for r in rows)/n,2),
            'prior_average_receiving_tds': round(sum(r[6] for r in rows)/n,2),
            'model': MODEL}

def metrics(rows):
    if not rows:
        return {'comparisons': 0}
    errors = [float(r['projected_ppr'])-float(r['actual_ppr']) for r in rows]
    return {'comparisons':len(errors),
            'mae':round(sum(abs(e) for e in errors)/len(errors),3),
            'rmse':round(math.sqrt(sum(e*e for e in errors)/len(errors)),3),
            'bias_projected_minus_actual':round(sum(errors)/len(errors),3)}

def write_csv(path, rows, fields):
    with path.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)

def evaluate(conn, predictions):
    evaluated=[]
    for p in predictions:
        # Actual outcomes are fetched only AFTER the projection has been made.
        actual=conn.execute('''SELECT fantasy_points_ppr FROM weekly_stats
            WHERE player_id=? AND season=? AND week=?''',
            (p['player_id'],p['season'],p['week'])).fetchone()
        if actual is None:
            continue  # Missing source row is not a zero-point game.
        error=round(p['projected_ppr']-actual[0],2)
        evaluated.append({**p,'actual_ppr':round(actual[0],2),
                          'error_projected_minus_actual':error,'absolute_error':abs(error)})
    return evaluated

def generate(season, weeks, db, output):
    output.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(f'{db.resolve().as_uri()}?mode=ro',uri=True) as conn:
        if not conn.execute('SELECT 1 FROM weekly_stats WHERE season=? LIMIT 1',(season-1,)).fetchone():
            raise ValueError(f'Import {season-1} history before projecting {season}')
        predictions=[]
        for week in weeks:
            for name,pid in ROSTER.items():
                predictions.append({'player':name,**project(conn,pid,season,week)})
        results=evaluate(conn,predictions)
    # Freeze projections before user league scores are supplied. Avoid silently
    # changing a prior prediction file after seeing the outcomes.
    frozen=output/'frozen_projections.json'
    payload={'season':season,'weeks':weeks,'model':MODEL,'scoring':'PPR',
             'predictions':predictions}
    if frozen.exists():
        old=json.loads(frozen.read_text())
        if old != payload:
            raise ValueError('Frozen predictions differ. Use another output directory for a new model/run.')
    else:
        frozen.write_text(json.dumps(payload,indent=2)+'\n')
    fields=['player','player_id','season','week','projected_ppr','history_games',
            'actual_ppr','error_projected_minus_actual','absolute_error']
    write_csv(output/'nflverse_comparison.csv',results,fields)
    write_csv(output/'projections.csv',predictions,fields[:6])
    template=output/'league_scores.csv'
    if not template.exists():
        write_csv(template,[{**p,'actual_ppr':''} for p in predictions],
                  ['player','player_id','season','week','actual_ppr'])
    manifest_path=db.parent/'import_manifest.json'
    report={'generated_at_utc':datetime.now(timezone.utc).isoformat(),
            'source_manifest':json.loads(manifest_path.read_text()) if manifest_path.exists() else None,
            'frozen_projections_sha256':hashlib.sha256(frozen.read_bytes()).hexdigest(),
            'model':MODEL,'scoring':'PPR','outcome_source':'nflverse; not user league scores',
            'overall':metrics(results),
            'by_week':{str(w):metrics([r for r in results if r['week']==w]) for w in weeks},
            'by_player':{name:metrics([r for r in results if r['player']==name]) for name in ROSTER},
            'missing_actual_rows':len(predictions)-len(results)}
    (output/'evaluation.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Week  Player                 Projected PPR  Actual nflverse PPR  Error')
    for r in results:
        print(f"{r['week']:>4}  {r['player']:<22} {r['projected_ppr']:>13.2f} {r['actual_ppr']:>20.2f} {r['error_projected_minus_actual']:>7.2f}")
    print('Overall:',json.dumps(report['overall']))
    return predictions,results

def compare_league(output, scores):
    frozen=json.loads((output/'frozen_projections.json').read_text())
    lookup={(p['player_id'],p['season'],p['week']):p for p in frozen['predictions']}
    rows=[]
    seen=set()
    with scores.open(newline='',encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            if not row['actual_ppr'].strip():
                continue
            key=(row['player_id'],int(row['season']),int(row['week']))
            if key not in lookup or key in seen:
                raise ValueError(f'Unknown or duplicate score key: {key}')
            seen.add(key)
            actual=float(row['actual_ppr'])
            if not math.isfinite(actual):
                raise ValueError('League scores must be finite numbers')
            p=lookup[key]
            error=round(p['projected_ppr']-actual,2)
            rows.append({**p,'actual_ppr':actual,
                         'error_projected_minus_actual':error,'absolute_error':abs(error)})
    if not rows:
        raise ValueError('No league scores entered yet')
    write_csv(output/'league_comparison.csv',rows,
              ['player','season','week','projected_ppr','actual_ppr','error_projected_minus_actual','absolute_error'])
    report={'outcome_source':'user league scores','scoring':'PPR',
            'overall':metrics(rows),'missing_scores':len(lookup)-len(rows),
            'by_week':{str(w):metrics([r for r in rows if r['week']==w]) for w in frozen['weeks']}}
    (output/'league_evaluation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--season',type=int,default=2026)
    parser.add_argument('--weeks',type=int,nargs='+',default=[1,2,3,4])
    parser.add_argument('--db',type=Path,default=ROOT/'data'/'receivers.sqlite')
    parser.add_argument('--output-dir',type=Path,default=ROOT/'results'/'2026_ppr_baseline')
    parser.add_argument('--league-scores',type=Path,help='Compare supplied CSV against frozen predictions')
    args=parser.parse_args()
    if any(w<1 or w>18 for w in args.weeks):
        parser.error('Regular-season weeks must be between 1 and 18')
    try:
        if args.league_scores:
            compare_league(args.output_dir,args.league_scores)
        else:
            generate(args.season,sorted(set(args.weeks)),args.db,args.output_dir)
    except Exception as e:
        parser.exit(1,f'Projection failed: {e}\n')
