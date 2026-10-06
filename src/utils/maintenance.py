"""One-off and periodic maintenance (run inside the container).

  python -m src.utils.maintenance link-fits --start 2025-01-01 --end 2026-10-05
  python -m src.utils.maintenance refresh-derived
  python -m src.utils.maintenance backfill        # everything, in the right order
  python -m src.utils.maintenance drop-orphan-tables --yes   # backs up first

Execution scores / lap markers: see `python -m src.utils.reanalyze --help`.
"""
from __future__ import annotations

import argparse
from datetime import date

from src.storage.database import WorkoutDatabase
from src.storage.workout_matching import link_fit_files
from src.utils import training_load


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    link = sub.add_parser("link-fits", help="link workouts to FIT files over a date range")
    link.add_argument("--start", required=True)
    link.add_argument("--end", default=date.today().isoformat())
    sub.add_parser("refresh-derived", help="recompute training load, power bests and progression")
    sub.add_parser("backfill", help="link FIT files, add lap markers, rescore executions, refresh derived data")
    drop = sub.add_parser("drop-orphan-tables", help="drop leftover *_old/*_backup tables (backs up the DB first)")
    drop.add_argument("--yes", action="store_true", help="actually drop (otherwise just list)")
    args = parser.parse_args()

    db = WorkoutDatabase()  # applies pending schema migrations
    if args.cmd == "link-fits":
        print(f"Linked {link_fit_files(db.db_path, args.start, args.end)} workouts to FIT files")
    elif args.cmd == "refresh-derived":
        print(training_load.refresh_all(db.db_path))
    elif args.cmd == "backfill":
        from src.utils import reanalyze
        from src.storage.workout_matching import fix_double_linked_fit_files
        fixed = fix_double_linked_fit_files(db.db_path, apply=True)
        print(f"Unlinked {len(fixed)} wrong FIT links (one ride file attached to several workouts)")
        print(f"Linked {link_fit_files(db.db_path, '2000-01-01', date.today().isoformat())} workouts to FIT files")
        ids = reanalyze._workout_ids(db, "2000-01-01", date.today().isoformat())
        import sqlite3
        conn = sqlite3.connect(db.db_path)
        fit_ids = {r[0] for r in conn.execute("SELECT fit_file_id FROM workouts WHERE fit_file_id IS NOT NULL")}
        conn.close()
        print(f"Added lap markers to {sum(reanalyze.refresh_laps(f, db) for f in fit_ids)} FIT files")
        scored = sum(1 for wid in ids if reanalyze.recompute_execution_only(wid, db))
        print(f"Computed execution scores for {scored} matched workouts")
        print(training_load.refresh_all(db.db_path))
    elif args.cmd == "drop-orphan-tables":
        drop_orphan_tables(db.db_path, confirm=args.yes)


ORPHAN_TABLES = ("workouts_old", "fit_files_old", "proposed_workouts_backup",
                 "daily_plans_backup", "workout_performance_backup")


def drop_orphan_tables(db_path: str, confirm: bool = False) -> None:
    import sqlite3
    from datetime import datetime
    conn = sqlite3.connect(db_path)
    try:
        present = [t for (t,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                   if t in ORPHAN_TABLES]
        for t in present:
            print(f"  {t}: {conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]} rows")
        if not present or not confirm:
            print("Nothing dropped." + (" Re-run with --yes to drop." if present else ""))
            return
        backup_path = f"{db_path}.pre_drop_{datetime.now():%Y%m%d_%H%M%S}"
        backup = sqlite3.connect(backup_path)
        conn.backup(backup)
        backup.close()
        print(f"Backed up to {backup_path}")
        for t in present:
            conn.execute(f"DROP TABLE {t}")
        conn.commit()
        conn.execute("VACUUM")
        print(f"Dropped {len(present)} tables and vacuumed.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
