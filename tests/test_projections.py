import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from projections import project, metrics, compare_league, ROSTER

ROOT=Path(__file__).resolve().parents[1]

class ProjectionTests(unittest.TestCase):
    def setUp(self):
        self.conn=sqlite3.connect(':memory:')
        with sqlite3.connect(f'{(ROOT/"data"/"receivers.sqlite").as_uri()}?mode=ro',uri=True) as source:
            source.backup(self.conn)
    def tearDown(self):
        self.conn.close()
    def test_target_and_future_outcomes_cannot_change_projection(self):
        pid=ROSTER['Matthew Golden']
        for week in [1,2,3,4]:
            before=project(self.conn,pid,2026,week)
            self.conn.execute('SAVEPOINT before_mutation')
            self.conn.execute('''UPDATE weekly_stats SET fantasy_points_ppr=9999,
                targets=9999, receptions=9999, receiving_yards=9999
                WHERE season>2026 OR (season=2026 AND week>=?)''',(week,))
            after=project(self.conn,pid,2026,week)
            self.assertEqual(before,after)
            self.conn.execute('ROLLBACK TO before_mutation')
            self.conn.execute('RELEASE before_mutation')
    def test_week_one_has_no_current_season_history(self):
        for pid in ROSTER.values():
            p=project(self.conn,pid,2026,1)
            self.assertTrue(all(w.startswith('2025-') for w in p['history_weeks']))
    def test_week_two_can_use_week_one(self):
        p=project(self.conn,ROSTER['Emeka Egbuka'],2026,2)
        self.assertEqual(p['history_weeks'][0],'2026-W1')
    def test_no_history_does_not_invent_a_projection(self):
        with self.assertRaises(ValueError):
            project(self.conn,'unknown-id',2026,1)
    def test_error_metrics(self):
        result=metrics([{'projected_ppr':10,'actual_ppr':6},
                        {'projected_ppr':8,'actual_ppr':10}])
        self.assertEqual(result,{'comparisons':2,'mae':3.0,'rmse':3.162,
                                 'bias_projected_minus_actual':1.0})
    def test_league_zero_is_scored_blank_is_missing(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)
            preds=[{'player':'Test','player_id':'test','season':2026,'week':w,
                    'projected_ppr':8.0} for w in [1,2]]
            (out/'frozen_projections.json').write_text(json.dumps({'weeks':[1,2],'predictions':preds}))
            scores=out/'scores.csv'
            scores.write_text('player_id,season,week,actual_ppr\ntest,2026,1,0\ntest,2026,2,\n')
            compare_league(out,scores)
            report=json.loads((out/'league_evaluation.json').read_text())
            self.assertEqual(report['overall']['mae'],8.0)
            self.assertEqual(report['overall']['comparisons'],1)
            self.assertEqual(report['missing_scores'],1)

if __name__=='__main__':
    unittest.main()
