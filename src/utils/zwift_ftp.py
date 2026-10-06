"""Zwift's FTP, read from what its ERG mode actually asked for.

Zwift scales every .zwo by its own FTP (it ignores <ftpOverride>), and that FTP
only changes after a Zwift FTP/ramp test or a race. Zwift records the ERG target
in each FIT record (`target_power`), and we know the FTP fraction each interval
was written with, so:   zwift_ftp ≈ avg target watts / avg fraction.

Keeping the app's FTP equal to Zwift's makes plan watts and Zwift watts match,
and a long-unchanged Zwift FTP means a test is due.
"""
from __future__ import annotations

import json
import sqlite3
import statistics
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from src.config import get_db_path
from src.utils.erg_execution import _align_laps

FTP_TEST_DUE_WEEKS = 6
TEST_WORDS = ("ramp test", "ftp test", "ftp builder", "race", "zrl", "crit")
NOT_A_TEST = ("simulation", "race pace", "race-pace", "pre-race", "race prep", "openers")


def _fraction(power_target: Dict[str, Any], plan_ftp: float) -> Optional[float]:
    """Average FTP fraction the .zwo used for an interval (mirrors the generator)."""
    if not power_target:
        return None
    if power_target.get("type") == "range":
        lo, hi = float(power_target.get("min", 0)), float(power_target.get("max", 0))
        if power_target.get("unit", "watts") == "watts":
            return (lo + hi) / 2 / plan_ftp if plan_ftp else None
        return (lo + hi) / 2 / 100
    if "start" in power_target and "end" in power_target:
        s, e = power_target["start"], power_target["end"]
        def frac(p):
            v = float(p.get("value", 0))
            return v / 100 if p.get("type") == "percent_ftp" else (v / plan_ftp if plan_ftp else None)
        a, b = frac(s), frac(e)
        return (a + b) / 2 if a and b else None
    if power_target.get("type") == "percent_ftp":
        return float(power_target.get("value", 0)) / 100
    return None


def infer_from_ride(fit_data: Dict[str, Any], intervals: List[Dict[str, Any]], plan_ftp: float) -> Optional[Dict[str, Any]]:
    """Zwift FTP implied by one structured ride, or None if it can't be read."""
    durations = [int(iv.get("duration", 0) or 0) for iv in intervals]
    laps = _align_laps(fit_data.get("laps") or [], [d for d in durations if d > 0])
    if laps is None:
        return None
    estimates = []
    for iv, lap in zip([iv for iv in intervals if int(iv.get("duration", 0) or 0) > 0], laps):
        target = lap.get("avg_target_power")
        fraction = _fraction(iv.get("powerTarget") or {}, plan_ftp)
        # Short or very easy segments carry too much rounding (Zwift targets are 5W steps).
        if target and fraction and fraction >= 0.5 and (lap.get("total_elapsed_time") or 0) >= 60:
            estimates.append(target / fraction)
    if len(estimates) < 2:
        return None
    return {"ftp": int(round(statistics.median(estimates))), "intervals_used": len(estimates)}


def refresh_observations(db_path: Optional[str] = None) -> int:
    """Recompute Zwift FTP for every matched structured Zwift ride with lap targets."""
    conn = sqlite3.connect(db_path or get_db_path())
    try:
        rows = conn.execute("""
            SELECT w.id, w.workout_day, f.fit_data, pw.intervals, COALESCE(pw.prescribed_ftp, wp.ftp)
            FROM workouts w
            JOIN fit_files f ON f.id = w.fit_file_id
            JOIN proposed_workouts pw ON pw.id = w.proposed_workout_id
            LEFT JOIN daily_plans dp ON dp.id = pw.dailyPlanId
            LEFT JOIN weekly_plans wp ON wp.weekNumber = dp.weekNumber
            WHERE f.file_name LIKE '%zwift%' AND pw.intervals IS NOT NULL AND pw.intervals NOT IN ('', '[]')
        """).fetchall()
        conn.execute("DELETE FROM zwift_ftp_observations")
        count = 0
        for wid, day, fit_json, intervals_json, plan_ftp in rows:
            try:
                fit = json.loads(fit_json) or {}
                intervals = json.loads(intervals_json) or []
            except ValueError:
                continue
            result = infer_from_ride(fit, intervals, float(plan_ftp or 0))
            if result:
                conn.execute(
                    "INSERT INTO zwift_ftp_observations (workout_id, ride_date, ftp, intervals_used) VALUES (?, ?, ?, ?)",
                    (wid, day, result["ftp"], result["intervals_used"]))
                count += 1
        conn.commit()
        return count
    finally:
        conn.close()


def history(db_path: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(db_path or get_db_path())
    try:
        rows = conn.execute(
            "SELECT ride_date, ftp FROM zwift_ftp_observations ORDER BY ride_date").fetchall()
    finally:
        conn.close()
    return [{"date": d, "ftp": f} for d, f in rows]


def current(db_path: Optional[str] = None, today: Optional[date] = None) -> Dict[str, Any]:
    """Latest Zwift FTP, when it last changed, and whether a test is due."""
    today = today or date.today()
    obs = history(db_path)
    out: Dict[str, Any] = {"ftp": None, "observed": None, "changed_on": None, "weeks_since_change": None,
                           "last_test_or_race": _last_test_or_race(db_path), "test_due": False}
    if not obs:
        return out
    # Ignore one-off wobble from 5W target rounding: current = median of the
    # last 3 rides, and a "change" is >= 3W.
    latest = {"date": obs[-1]["date"], "ftp": int(statistics.median(o["ftp"] for o in obs[-3:]))}
    changed_on = obs[0]["date"]
    for prev, cur in zip(obs, obs[1:]):
        if abs(cur["ftp"] - prev["ftp"]) >= 3:
            changed_on = cur["date"]
    out.update(ftp=latest["ftp"], observed=latest["date"], changed_on=changed_on)
    reference = max(filter(None, [changed_on, out["last_test_or_race"]]))
    weeks = (today - datetime.strptime(reference[:10], "%Y-%m-%d").date()).days / 7
    out["weeks_since_change"] = round(weeks, 1)
    out["test_due"] = weeks >= FTP_TEST_DUE_WEEKS
    return out


def _last_test_or_race(db_path: Optional[str]) -> Optional[str]:
    """Most recent ride that would move Zwift's FTP (a test or a real race)."""
    conn = sqlite3.connect(db_path or get_db_path())
    try:
        rows = conn.execute(
            "SELECT workout_day, LOWER(COALESCE(proposed_workout_name, '') || ' ' || workout_title) "
            "FROM workouts ORDER BY workout_day DESC").fetchall()
    finally:
        conn.close()
    for day, text in rows:
        if any(w in text for w in TEST_WORDS) and not any(n in text for n in NOT_A_TEST):
            return day
    return None


def sync_settings_ftp(db_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Make the app's FTP follow Zwift's. Returns the change, if any."""
    from src.storage.database import WorkoutDatabase
    from src.storage.events import record_event

    info = current(db_path)
    if not info["ftp"]:
        return None
    db = WorkoutDatabase(db_path) if db_path else WorkoutDatabase()
    settings = db.get_athlete_settings() or {}
    old = settings.get("ftp")
    if old and abs(float(old) - info["ftp"]) < 3:
        return None
    settings["ftp"] = info["ftp"]
    db.save_athlete_settings("default", settings)
    change = {"from": old, "to": info["ftp"], "observed": info["observed"]}
    record_event("info", "zwift_ftp", f"FTP set to Zwift's {info['ftp']}W (was {old}W), from ride on {info['observed']}",
                 change, db_path=db_path)
    return change
