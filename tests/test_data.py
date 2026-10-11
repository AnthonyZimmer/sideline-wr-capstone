import sqlite3
import unittest
from pathlib import Path
from import_data import half_ppr, validate_database

class ScoringTests(unittest.TestCase):
    def test_half_ppr_keeps_rushing_and_fumble_points(self):
        # 40 receiving yards + 20 rushing yards + 1 rushing TD - 1 lost fumble.
        standard = 4 + 2 + 6 - 2
        self.assertEqual(half_ppr(standard, 3), 11.5)

class SnapshotTests(unittest.TestCase):
    def setUp(self):
        db = Path(__file__).resolve().parents[1] / 'data' / 'receivers.sqlite'
        self.conn = sqlite3.connect(f'{db.as_uri()}?mode=ro', uri=True)
    def tearDown(self):
        self.conn.close()
    def test_integrity_and_game_links(self):
        self.assertGreater(validate_database(self.conn)['receiver_game_records'], 0)
    def test_official_week_one_spot_checks(self):
        for name, expected in [('Justin Jefferson',(4,59,1,13.9)), ("Ja'Marr Chase",(6,62,0,9.2))]:
            actual = self.conn.execute('''SELECT receptions, receiving_yards, receiving_tds,
                fantasy_points_half_ppr FROM receiver_game_log
                WHERE display_name=? AND season=2024 AND week=1''',(name,)).fetchone()
            self.assertEqual(actual, expected)
    def test_duplicate_rejected(self):
        conn = sqlite3.connect(':memory:')
        self.conn.backup(conn)
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute('INSERT INTO weekly_stats SELECT * FROM weekly_stats LIMIT 1')
        conn.close()

if __name__ == '__main__':
    unittest.main()
