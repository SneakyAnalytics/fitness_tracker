"""Backfill workouts.fit_file_id by matching FIT files for a date range.

Usage (inside container):
  python -m src.utils.backfill_fit_links --start 2026-01-12 --end 2026-01-13
"""
from __future__ import annotations

import argparse
from datetime import datetime
from typing import Optional

from .trainingpeaks_sync import TrainingPeaksSync


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill workouts.fit_file_id by matching FIT files")
    parser.add_argument("--start", required=True, help="Start date (YYYY-MM-DD)")
    parser.add_argument("--end", required=True, help="End date (YYYY-MM-DD)")
    args = parser.parse_args()

    # Validate dates
    try:
        datetime.strptime(args.start, "%Y-%m-%d")
        datetime.strptime(args.end, "%Y-%m-%d")
    except ValueError as exc:
        raise SystemExit("Invalid date format, expected YYYY-MM-DD") from exc

    print(f"🔗 Backfilling fit_file_id for workouts {args.start} to {args.end}...")
    sync = TrainingPeaksSync()
    # Reuse existing matching logic (TSS + duration by day)
    sync._match_workouts_to_fit_files(args.start, args.end)
    print("✅ Backfill complete")


if __name__ == "__main__":
    main()
