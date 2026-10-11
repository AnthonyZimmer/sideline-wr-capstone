"""Build lagged football features and train an explainable component projection."""
import csv
from datetime import datetime,timezone
import json
from pathlib import Path
import sqlite3
import joblib
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from projections import ROSTER,metrics

ROOT=Path(__file__).resolve().parent
MODEL_PATH=ROOT/'data'/'enhanced_model.joblib'
FEATURES=['targets_3','targets_8','target_share_3','target_share_8','snap_share_3',
 'snap_share_8','catch_rate_8','yards_per_target_8','air_yards_3','air_share_8',
 'yac_per_catch_8','drop_rate_8','red_zone_targets_3','red_zone_share_8',
 'rec_tds_8','ppr_3','ppr_8','target_trend','snap_trend','def_wr_ppr_8',
 'def_pass_epa_8','history_games','current_season_games','home']
METRIC_FIELDS=['targets','target_share','snap_share','receiving_tds','ppr','air_yards','air_share']

def average(rows,key):
    values=[r[key] for r in rows if r[key] is not None and np.isfinite(r[key])]
    return float(np.mean(values)) if values else None

class FeatureStore:
    def __init__(self,db=None):
        self.conn=sqlite3.connect(db or ROOT/'data'/'receivers.sqlite')
        self.conn.row_factory=sqlite3.Row
    def history(self,pid,season,week):
        return [dict(r) for r in self.conn.execute('''SELECT * FROM appearances
            WHERE player_id=? AND (season=? OR (season=? AND week<?))
            ORDER BY season DESC,week DESC LIMIT 8''',(pid,season-1,season,week))]
    def features(self,pid,season,week,team=None):
        hist=self.history(pid,season,week)
        if len(hist)<3:raise ValueError('At least three earlier active/recorded games are required. This receiver needs more history.')
        # Team assignment is a pregame context assumption. UI can override it
        # for trades. Historical evaluation uses known game team, never output stats.
        team=team or hist[0]['team']
        game=self.conn.execute('''SELECT * FROM games WHERE season=? AND week=?
            AND (home_team=? OR away_team=?)''',(season,week,team,team)).fetchone()
        if game is None:raise ValueError(f'No scheduled game for {team} in this week (possible bye).')
        opp=game['away_team'] if game['home_team']==team else game['home_team']
        defense=[dict(r) for r in self.conn.execute('''SELECT * FROM defense_context
            WHERE team=? AND (season=? OR (season=? AND week<?))
            ORDER BY season DESC,week DESC LIMIT 8''',(opp,season-1,season,week))]
        recent=hist[:3]
        f={}
        for prefix,key in [('targets','targets'),('target_share','target_share'),
                           ('snap_share','snap_share'),('ppr','ppr')]:
            f[prefix+'_3']=average(recent,key);f[prefix+'_8']=average(hist,key)
        targets=sum(r['targets'] for r in hist);rec=sum(r['receptions'] for r in hist)
        yards=sum(r['receiving_yards'] for r in hist)
        f['catch_rate_8']=rec/targets if targets else 0
        f['yards_per_target_8']=yards/targets if targets else 0
        f['air_yards_3']=average(recent,'air_yards');f['air_share_8']=average(hist,'air_share')
        f['yac_per_catch_8']=sum(r['yac'] for r in hist)/rec if rec else 0
        drop_hist=[r for r in hist if r['drops'] is not None]
        drop_targets=sum(r['targets'] for r in drop_hist)
        f['drop_rate_8']=sum(r['drops'] for r in drop_hist)/drop_targets if drop_targets else None
        f['red_zone_targets_3']=average(recent,'red_zone_targets')
        team_rz=sum(r['team_red_zone_targets'] for r in hist)
        f['red_zone_share_8']=sum(r['red_zone_targets'] for r in hist)/team_rz if team_rz else 0
        f['rec_tds_8']=average(hist,'receiving_tds')
        f['target_trend']=f['targets_3']-f['targets_8']
        f['snap_trend']=(f['snap_share_3']-f['snap_share_8']) if f['snap_share_3'] is not None and f['snap_share_8'] is not None else None
        f['def_wr_ppr_8']=average(defense,'wr_ppr_allowed')
        f['def_pass_epa_8']=average(defense,'pass_epa_allowed')
        f['history_games']=len(hist);f['current_season_games']=sum(r['season']==season for r in hist)
        f['home']=int(game['home_team']==team)
        context={'team':team,'opponent':opp,'game_date':game['game_date'],
            'history_weeks':[f"{r['season']}-W{r['week']}" for r in hist],
            'defense_weeks':[f"{r['season']}-W{r['week']}" for r in defense],
            'team_assignment':'User override or most recent prior team',
            'availability':'Conditional on playing. Injury status is not modeled.'}
        return f,context

def matrix(features):
    return np.array([[f.get(k) if f.get(k) is not None else np.nan for k in FEATURES] for f in features],dtype=float)

def score_components(pred):
    targets=np.maximum(pred[:,0],0);rec=np.maximum(pred[:,1],0)
    yards=np.maximum(pred[:,2],0);td=np.maximum(pred[:,3],0);other=pred[:,4]
    return targets,rec,yards,td,other,rec+0.1*yards+6*td+other

def training_data(store):
    rows=[];fs=[];ys=[]
    for row in store.conn.execute('SELECT * FROM appearances WHERE season BETWEEN 2023 AND 2026 ORDER BY season,week,player_id').fetchall():
        r=dict(row)
        try:f,_=store.features(r['player_id'],r['season'],r['week'],r['team'])
        except ValueError:continue
        rows.append(r);fs.append(f)
        other=r['ppr']-(r['receptions']+0.1*r['receiving_yards']+6*r['receiving_tds'])
        ys.append([r['targets'],r['receptions'],r['receiving_yards'],r['receiving_tds'],other])
    return rows,fs,np.array(ys)

def train():
    store=FeatureStore();rows,fs,y=training_data(store);x=matrix(fs)
    seasons=np.array([r['season'] for r in rows]);train_mask=seasons<=2024
    # Parameters fixed before validation. No target season retraining/tuning.
    pipe=Pipeline([('imputer',SimpleImputer(strategy='median',add_indicator=True)),
        ('forest',RandomForestRegressor(n_estimators=240,min_samples_leaf=15,
            max_depth=12,max_features=0.8,random_state=440,n_jobs=2))])
    pipe.fit(x[train_mask],y[train_mask])
    pred=score_components(pipe.predict(x))[-1]
    results=[]
    names={r['player_id']:r['display_name'] for r in store.conn.execute('SELECT * FROM players')}
    for r,f,p in zip(rows,fs,pred):
        if r['season']<=2024:continue
        results.append({'player_id':r['player_id'],'player':names.get(r['player_id'],r['player_id']),
            'season':r['season'],'week':r['week'],'actual_ppr':r['ppr'],
            'projected_ppr':round(float(p),2),'baseline_ppr':round(f['ppr_8'],2)})
    val=[r for r in results if r['season']==2025]
    q=float(np.quantile([abs(r['projected_ppr']-r['actual_ppr']) for r in val],0.8))
    groups={}
    for label,subset in [('2025_validation',val),('2026_weeks_1_4',[r for r in results if r['season']==2026 and r['week']<=4]),
                          ('user_roster_2026_weeks_1_4',[r for r in results if r['season']==2026 and r['week']<=4 and r['player_id'] in ROSTER.values()])]:
        baseline=[{**r,'projected_ppr':r['baseline_ppr']} for r in subset]
        groups[label]={'enhanced':metrics(subset),'active_game_average_baseline':metrics(baseline)}
    importance=pipe.named_steps['forest'].feature_importances_
    fn=pipe.named_steps['imputer'].get_feature_names_out(FEATURES)
    report={'model':'random_forest_component_model_v1','built_at_utc':datetime.now(timezone.utc).isoformat(),
        'training_seasons':[2023,2024],'training_rows':int(train_mask.sum()),'features':FEATURES,
        'parameters':{'trees':240,'min_leaf':15,'max_depth':12,'random_seed':440},
        'validation_absolute_residual_p80':q,'evaluations':groups,
        'feature_importance':sorted([{'feature':str(k),'importance':float(v)} for k,v in zip(fn,importance)],key=lambda x:-x['importance']),
        'limits':['Conditional on active/recorded games; inactive players are not forecast.',
                  '2026 outcomes were previously inspected, so this is a diagnostic replay, not an untouched test.',
                  'Historical modern snapshots can contain later stat corrections.',
                  'Game roster team is assumed known before kickoff for retrospective evaluation.',
                  'Routes, archived weather forecasts, and pregame injury feeds are not integrated.']}
    joblib.dump({'pipeline':pipe,'report':report},MODEL_PATH)
    out=ROOT/'results'/'enhanced';out.mkdir(exist_ok=True,parents=True)
    (out/'evaluation.json').write_text(json.dumps(report,indent=2)+'\n')
    with (out/'predictions.csv').open('w',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=list(results[0]));writer.writeheader();writer.writerows(results)
    print(json.dumps({'training_rows':report['training_rows'],'evaluations':groups},indent=2))
    store.conn.close()

def predict_player(pid,season,week,team=None,bundle=None,store=None):
    bundle=bundle or joblib.load(MODEL_PATH);own_store=store is None;store=store or FeatureStore()
    f,context=store.features(pid,season,week,team)
    components=score_components(bundle['pipeline'].predict(matrix([f])))
    points=float(components[-1][0]);q=bundle['report']['validation_absolute_residual_p80']
    result={'player_id':pid,'season':season,'week':week,'projection':round(points,2),
        'baseline':round(f['ppr_8'],2),'expected_targets':round(float(components[0][0]),2),
        'expected_receptions':round(float(components[1][0]),2),
        'expected_receiving_yards':round(float(components[2][0]),2),
        'expected_receiving_tds':round(float(components[3][0]),2),
        'other_ppr':round(float(components[4][0]),2),
        'uncertainty_low':round(max(0,points-q),2),'uncertainty_high':round(points+q,2),
        'uncertainty_note':'Illustrative range using 80th percentile of absolute 2025 validation errors. Not a calibrated player-specific interval.',
        'features':f,'context':context,
        'not_available':['Route participation','Targets per route','Archived pregame weather forecast','Verified pregame injury status']}
    if own_store:store.conn.close()
    return result

if __name__=='__main__':train()
