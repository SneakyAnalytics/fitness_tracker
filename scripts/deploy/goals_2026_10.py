"""One-time goals cleanup agreed on 2026-10-05 (safe to re-run).

Runs inside the API container after the first deploy of the overhaul:
  docker exec fitness-tracker-api python scripts/deploy/goals_2026_10.py
"""
import json
import sqlite3
import sys

sys.path.insert(0, "/app")
sys.path.insert(0, ".")
from src.config import get_db_path  # noqa: E402
from src.storage import goals as goals_store  # noqa: E402
from src.storage.database import WorkoutDatabase  # noqa: E402

WorkoutDatabase()
goals_store.list_goals()  # imports coaching_notes.json goals the first time
conn = sqlite3.connect(get_db_path())


def find(fragment):
    return conn.execute("SELECT id FROM goals WHERE LOWER(description) LIKE ?", (f"%{fragment.lower()}%",)).fetchone()


def ensure(description, category, priority, status, target_date, note):
    if find(description[:30]):
        return
    conn.execute(
        "INSERT INTO goals (description, category, priority, status, target_date, added_date, progress_notes) "
        "VALUES (?, ?, ?, ?, ?, date('now'), ?)",
        (description, category, priority, status, target_date, json.dumps([note])))
    print("added:", description)


ensure("Complete a 100-mile (century) ride before the season ends", "event", 1, "completed", "2026-09-12",
       "2026-09-12: completed (~7.6h elapsed), felt good the next day")
ensure("Gifford Pinchot Gravel — 54 mi / 5,200 ft", "event", 2, "active", "2026-10-10",
       "Biggest gravel day of the year so far; fueling: gels on climbs, carb bottles, gummies")

# Merge the two FTP goals into one with the concrete target from the old profile list.
ftp = find("improve ftp progressively")
if ftp:
    conn.execute("UPDATE goals SET description = ?, priority = 2 WHERE id = ?",
                 ("Raise Zwift FTP to 320W+ (≈4.0 W/kg at ~80 kg)", ftp[0]))
    print("updated FTP goal")
conn.commit()

for g in goals_store.list_goals(include_inactive=True):
    print(f"  #{g['id']} [{g['status']}] P{g['priority']} {g['target_date'] or '':10} {g['description']}")
