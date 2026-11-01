"""Affiche les derniers événements du journal. Usage : python show_events.py [nombre]"""
import sqlite3
import sys
from contextlib import closing

from event_log import DB_PATH

limit = int(sys.argv[1]) if len(sys.argv) > 1 else 20
if not DB_PATH.exists():
    print("Aucun journal : lance d'abord step7_log.py")
    sys.exit(1)

with closing(sqlite3.connect(DB_PATH)) as con:
    rows = con.execute("SELECT ts, track_id, zone, badge, state, reason FROM events "
                       "ORDER BY id DESC LIMIT ?", (limit,)).fetchall()

print(f"{'heure':19} | {'ID':>3} | {'zone':15} | {'badge':11} | {'état':22} | raison")
for ts, tid, zone, badge, state, reason in reversed(rows):
    tid_text = "-" if tid is None else str(tid)
    print(f"{ts:19} | {tid_text:>3} | {zone or '-':15} | {badge or '-':11} | {state:22} | {reason}")
print(f"{len(rows)} événement(s) affiché(s)")
