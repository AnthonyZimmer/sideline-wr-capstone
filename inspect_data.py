"""Display WR game logs from SQL without downloading data."""
import argparse
from pathlib import Path
import sqlite3

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--player', default='Justin Jefferson')
parser.add_argument('--season', type=int, default=2024)
args = parser.parse_args()
db = Path(__file__).resolve().parent / 'data' / 'receivers.sqlite'
if not db.exists():
    parser.exit(1, 'Database missing. Run import_data.py first.\n')
with sqlite3.connect(f'{db.as_uri()}?mode=ro', uri=True) as conn:
    rows = conn.execute('''SELECT week, opponent, receptions, targets, receiving_yards,
        receiving_tds, fantasy_points_half_ppr FROM receiver_game_log
        WHERE display_name = ? AND season = ? ORDER BY week''', (args.player, args.season)).fetchall()
    print(f'{args.player} | {args.season} | actual historical results')
    print('Week  Opp  Rec  Tgt  Yards  TD  Half-PPR')
    for week, opp, rec, tgt, yards, td, points in rows:
        print(f'{week:>4}  {opp:>3}  {rec:>3}  {tgt:>3}  {yards:>5g}  {td:>2}  {points:>8.2f}')
    if not rows:
        parser.exit(1, 'No matching records. Check the exact player name and imported season.\n')
