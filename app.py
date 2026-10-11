"""Local Python/SQL receiver comparison application."""
import argparse
import json
from pathlib import Path
import sqlite3
from flask import Flask,render_template,request,jsonify
import joblib
from model import ROOT,MODEL_PATH,FeatureStore,predict_player

app=Flask(__name__)
bundle=None

def get_bundle():
    global bundle
    if bundle is None:bundle=joblib.load(MODEL_PATH)
    return bundle

@app.get('/')
def index():
    with sqlite3.connect(ROOT/'data'/'receivers.sqlite') as c:
        players=[{'id':r[0],'name':r[1]} for r in c.execute('SELECT player_id,display_name FROM players ORDER BY display_name')]
    return render_template('index.html',players=players)

@app.post('/api/compare')
def compare():
    body=request.get_json(silent=True) or {}
    try:
        season=int(body.get('season',2026));week=int(body.get('week',1))
        if season not in [2025,2026] or not 1<=week<=18:raise ValueError('Select 2025 or 2026 and a week from 1 to 18.')
        ids=[body.get('player_a'),body.get('player_b')]
        if not all(isinstance(x,str) and x for x in ids) or ids[0]==ids[1]:raise ValueError('Select two different receivers.')
        store=FeatureStore()
        try:
            names=dict(store.conn.execute('SELECT player_id,display_name FROM players'))
            if any(pid not in names for pid in ids):raise ValueError('Receiver not found in the database.')
            forecasts=[]
            for idx,pid in enumerate(ids):
                team=body.get('team_a' if idx==0 else 'team_b') or None
                if team is not None:
                    valid={r[0] for r in store.conn.execute('SELECT home_team FROM games UNION SELECT away_team FROM games')}
                    if team not in valid:raise ValueError('Unknown team abbreviation.')
                f=predict_player(pid,season,week,team,get_bundle(),store)
                forecasts.append({'name':names[pid],**f})
            a,b=forecasts;gap=abs(a['projection']-b['projection']);best=a if a['projection']>=b['projection'] else b
            if gap<2:
                recommendation=f"Close comparison: {best['name']} has a slight projected edge. Review availability before deciding."
            else:
                recommendation=f"Projected edge: {best['name']} by {gap:.2f} PPR points, conditional on both receivers playing."
            drivers=[]
            for label,key in [('Recent targets per game','targets_3'),('Target share','target_share_3'),
                              ('Offensive snap participation','snap_share_3'),('Red-zone target share','red_zone_share_8')]:
                av=a['features'][key];bv=b['features'][key]
                if av is not None and bv is not None and abs(av-bv)>0.001:
                    drivers.append({'label':label,'higher_player':a['name'] if av>bv else b['name'],
                        'note':'Observed preweek context, not a causal attribution of the model output.'})
            return jsonify({'players':forecasts,'recommendation':recommendation,'gap':round(gap,2),
                'close_comparison':gap<2,'context_highlights':drivers,'scoring':'Full PPR',
                'model_validation':get_bundle()['report']['evaluations']['2025_validation'],
                'data_snapshot':'October 11, 2026. Historical replay with corrected source data.',
                'availability_warning':'Projections assume the receiver plays. Verify injury and lineup status yourself.',
                'missing_data_note':'Routes, archived forecasts, and pregame injury feeds are not integrated. No artificial boost multiplier is applied.'})
        finally:store.conn.close()
    except (ValueError,TypeError) as e:return jsonify({'error':str(e)}),400
    except FileNotFoundError:return jsonify({'error':'Model files are missing. Run build_advanced.py then model.py.'}),503

@app.get('/api/methodology')
def methodology():
    return jsonify(get_bundle()['report'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--port',type=int,default=5000)
    args=p.parse_args();app.run(host='127.0.0.1',port=args.port,debug=False)
