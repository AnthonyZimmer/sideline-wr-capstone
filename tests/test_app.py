import unittest
from app import app
from projections import ROSTER
from model import FeatureStore,FEATURES,predict_player

class AppTests(unittest.TestCase):
    def setUp(self):self.client=app.test_client()
    def test_page_and_comparison(self):
        self.assertEqual(self.client.get('/').status_code,200)
        r=self.client.post('/api/compare',json={'player_a':ROSTER['Davante Adams'],
            'player_b':ROSTER['Matthew Golden'],'season':2026,'week':1})
        self.assertEqual(r.status_code,200)
        self.assertEqual(len(r.json['players']),2)
        self.assertEqual(r.json['scoring'],'Full PPR')
        for p in r.json['players']:
            self.assertTrue(all(w.startswith('2025-') for w in p['context']['history_weeks']))
    def test_same_player_and_invalid_input(self):
        pid=ROSTER['Davante Adams']
        for body in [{'player_a':pid,'player_b':pid},
                     {'player_a':pid,'player_b':'unknown'},
                     {'player_a':pid,'player_b':ROSTER['Matthew Golden'],'week':99}]:
            self.assertEqual(self.client.post('/api/compare',json=body).status_code,400)
    def test_bye_or_invalid_team_has_no_forecast(self):
        store=FeatureStore()
        try:
            with self.assertRaises(ValueError):store.features(ROSTER['Davante Adams'],2026,1,'BAD')
        finally:store.conn.close()
    def test_advanced_features_ignore_target_and_future_stats(self):
        store=FeatureStore()
        pid=ROSTER['Davante Adams']
        before,_=store.features(pid,2026,2)
        store.conn.execute('SAVEPOINT test_leakage')
        try:
            store.conn.execute('UPDATE appearances SET targets=9999,drops=9999,red_zone_targets=9999,snap_share=9999,ppr=9999 WHERE season=2026 AND week>=2')
            store.conn.execute('UPDATE defense_context SET pass_epa_allowed=9999,wr_ppr_allowed=9999 WHERE season=2026 AND week>=2')
            after,_=store.features(pid,2026,2)
            self.assertEqual(before,after)
        finally:
            store.conn.execute('ROLLBACK TO test_leakage');store.conn.execute('RELEASE test_leakage');store.conn.close()

if __name__=='__main__':unittest.main()
