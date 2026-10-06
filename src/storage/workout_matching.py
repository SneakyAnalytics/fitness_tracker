"""
Helper functions for manual workout matching workflow
"""
import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from pathlib import Path


def get_unmatched_workouts(db_path: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    Get workouts that haven't been matched to proposed workouts yet
    
    Args:
        db_path: Path to SQLite database
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
    
    Returns:
        List of workout dicts with details for matching
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        c.execute('''
            SELECT 
                w.id,
                w.workout_day,
                w.workout_title,
                w.workout_data,
                w.athlete_comments,
                w.fit_file_id,
                f.file_name,
                f.fit_data
            FROM workouts w
            LEFT JOIN fit_files f ON w.fit_file_id = f.id
            WHERE w.workout_day BETWEEN ? AND ?
              AND w.proposed_workout_name IS NULL
              AND (w.workout_data IS NOT NULL OR w.fit_file_id IS NOT NULL)
            ORDER BY w.workout_day, w.id
        ''', (start_date, end_date))
        
        workouts = []
        for row in c.fetchall():
            workout_id, day, title, workout_data_json, comments, fit_file_id, fit_filename, fit_data_json = row
            
            # Parse workout data
            workout_data = json.loads(workout_data_json) if workout_data_json else {}
            metrics = workout_data.get('metrics', {})
            
            # Parse FIT data if available
            fit_data = json.loads(fit_data_json) if fit_data_json else {}
            fit_metrics = fit_data.get('metrics', {})
            
            workouts.append({
                'id': workout_id,
                'workout_date': day,  # UI expects 'workout_date'
                'title': title,  # UI expects 'title'
                'tss': metrics.get('actual_tss') or fit_metrics.get('tss') or 0,
                'duration_minutes': metrics.get('actual_duration') or fit_metrics.get('duration') or 0,  # UI expects 'duration_minutes'
                'intensity_factor': fit_metrics.get('intensity_factor'),
                'comments': comments,  # UI expects 'comments'
                'fit_file_id': fit_file_id,
                'fit_filename': fit_filename,
                'fit_data': fit_data,  # Include for charting
                'workout_data': workout_data  # Include full data
            })
        
        return workouts
        
    finally:
        conn.close()


def get_proposed_workouts_for_week(db_path: str, week_start: str) -> List[Dict[str, Any]]:
    """
    Get all proposed workouts for the week starting on given date
    
    Args:
        db_path: Path to SQLite database
        week_start: Monday date of week (YYYY-MM-DD)
    
    Returns:
        List of proposed workout dicts
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        # Calculate week end (Sunday)
        start_date = datetime.strptime(week_start, '%Y-%m-%d')
        end_date = start_date + timedelta(days=6)
        end_str = end_date.strftime('%Y-%m-%d')
        
        c.execute('''
            SELECT 
                pw.id,
                pw.name,
                pw.type,
                pw.plannedDuration,
                pw.plannedTSS_min,
                pw.plannedTSS_max,
                pw.notes,
                dp.date
            FROM proposed_workouts pw
            JOIN daily_plans dp ON pw.dailyPlanId = dp.id
            WHERE dp.date BETWEEN ? AND ?
            ORDER BY dp.date, pw.id
        ''', (week_start, end_str))
        
        workouts = []
        for row in c.fetchall():
            # Convert date to day of week
            workout_date = datetime.strptime(row[7], '%Y-%m-%d')
            day_of_week = workout_date.strftime('%A')  # e.g., "Monday", "Tuesday"
            
            # Calculate average TSS if min/max available
            tss = None
            if row[4] and row[5]:  # Both min and max TSS
                tss = (row[4] + row[5]) / 2
            elif row[4]:  # Only min TSS
                tss = row[4]
            elif row[5]:  # Only max TSS
                tss = row[5]
            
            workouts.append({
                'id': row[0],
                'name': row[1],
                'type': row[2],
                'planned_duration': row[3],
                'tss': tss,  # UI expects 'tss'
                'planned_tss_min': row[4],
                'planned_tss_max': row[5],
                'notes': row[6],
                'date': row[7],
                'workout_day': day_of_week  # UI expects 'workout_day' (day of week name)
            })
        
        return workouts
        
    finally:
        conn.close()


def match_workout_to_proposed(db_path: str, workout_id: int, proposed_workout_name: str,
                               match_source: str = "manual",
                               proposed_workout_id: Optional[int] = None) -> bool:
    """
    Record the athlete's match for a completed workout.

    Args:
        db_path: Path to SQLite database
        workout_id: ID of workout to match
        proposed_workout_name: Name of the planned workout, or a custom label for
            an unplanned session (warm-up, commute, hike...)
        match_source: Source of match ('manual' or 'ai')
        proposed_workout_id: proposed_workouts.id of the planned workout. This is
            the authoritative link; names repeat across weeks. None for custom labels.

    Returns:
        True if successful
    """
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.execute(
            """
            UPDATE workouts
            SET proposed_workout_name = ?,
                proposed_workout_id = ?,
                match_source = ?,
                matched_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (proposed_workout_name, proposed_workout_id, match_source, workout_id),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def get_matched_workouts(db_path: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    Get workouts that have already been matched (for re-matching)
    
    Args:
        db_path: Path to SQLite database
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
    
    Returns:
        List of matched workout dicts
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        c.execute('''
            SELECT 
                w.id,
                w.workout_day,
                w.workout_title,
                w.proposed_workout_name,
                w.match_source,
                w.matched_at,
                w.workout_data,
                w.athlete_comments,
                w.fit_file_id,
                CASE WHEN wa.id IS NOT NULL THEN 'YES' ELSE 'NO' END as analyzed
            FROM workouts w
            LEFT JOIN workout_analyses wa ON w.id = wa.workout_id
            WHERE w.workout_day BETWEEN ? AND ?
              AND w.proposed_workout_name IS NOT NULL
            ORDER BY w.workout_day, w.id
        ''', (start_date, end_date))
        
        workouts = []
        for row in c.fetchall():
            workout_data = json.loads(row[6]) if row[6] else {}
            metrics = workout_data.get('metrics', {})
            
            workouts.append({
                'id': row[0],
                'workout_date': row[1],  # UI expects 'workout_date'
                'title': row[2],  # UI expects 'title'
                'proposed_workout_name': row[3],
                'match_source': row[4],
                'matched_at': row[5],
                'tss': metrics.get('actual_tss') or 0,
                'duration_minutes': metrics.get('actual_duration') or 0,  # UI expects 'duration_minutes'
                'comments': row[7],  # UI expects 'comments'
                'fit_file_id': row[8],  # Add fit_file_id from query
                'analyzed': row[9]
            })
        
        return workouts
        
    finally:
        conn.close()


def delete_workout(db_path: str, workout_id: int) -> bool:
    """
    Delete a workout and its associated analysis (CASCADE)
    
    Args:
        db_path: Path to SQLite database
        workout_id: ID of workout to delete
    
    Returns:
        True if successful
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        # Delete analysis first (if exists)
        c.execute('DELETE FROM workout_analyses WHERE workout_id = ?', (workout_id,))
        
        # Delete workout
        c.execute('DELETE FROM workouts WHERE id = ?', (workout_id,))
        
        conn.commit()
        return c.rowcount > 0
        
    except Exception as e:
        print(f"Error deleting workout: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def get_week_start_date(date_str: str) -> str:
    """
    Get the Monday of the week containing the given date
    
    Args:
        date_str: Date string (YYYY-MM-DD)
    
    Returns:
        Monday date string (YYYY-MM-DD)
    """
    date = datetime.strptime(date_str, '%Y-%m-%d')
    days_since_monday = date.weekday()
    monday = date - timedelta(days=days_since_monday)
    return monday.strftime('%Y-%m-%d')


def get_workouts_with_fit_files(db_path: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    Get workouts with their current FIT file assignments for review/reassignment
    
    Args:
        db_path: Path to SQLite database
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
    
    Returns:
        List of workout dicts with FIT file details
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        c.execute('''
            SELECT 
                w.id,
                w.workout_day,
                w.workout_title,
                w.workout_data,
                w.fit_file_id,
                f.file_name,
                f.fit_data
            FROM workouts w
            LEFT JOIN fit_files f ON w.fit_file_id = f.id
            WHERE w.workout_day BETWEEN ? AND ?
            ORDER BY w.workout_day DESC, w.id
        ''', (start_date, end_date))
        
        workouts = []
        for row in c.fetchall():
            workout_id, day, title, workout_data_json, fit_file_id, fit_filename, fit_data_json = row
            
            # Parse workout data
            workout_data = json.loads(workout_data_json) if workout_data_json else {}
            metrics = workout_data.get('metrics', {})
            
            # Parse FIT data if available
            fit_tss = None
            fit_duration = None
            if fit_data_json:
                fit_data = json.loads(fit_data_json)
                fit_metrics = fit_data.get('metrics', {})
                fit_tss = fit_metrics.get('tss')
                fit_duration = fit_metrics.get('duration')
            
            workouts.append({
                'id': workout_id,
                'workout_date': day,
                'title': title,
                'workout_tss': metrics.get('actual_tss'),
                'workout_duration': metrics.get('actual_duration'),
                'fit_file_id': fit_file_id,
                'fit_filename': fit_filename,
                'fit_tss': fit_tss,
                'fit_duration': fit_duration
            })
        
        return workouts
        
    finally:
        conn.close()


def get_available_fit_files(db_path: str, workout_date: str) -> List[Dict[str, Any]]:
    """
    Get all FIT files available for a specific date (for reassignment dropdown)
    
    Args:
        db_path: Path to SQLite database
        workout_date: Date string (YYYY-MM-DD)
    
    Returns:
        List of FIT file dicts with details
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        c.execute('''
            SELECT 
                id,
                file_name,
                fit_data
            FROM fit_files
            WHERE workout_day = ?
            ORDER BY id
        ''', (workout_date,))
        
        fit_files = []
        for row in c.fetchall():
            fit_id, filename, fit_data_json = row
            
            # Parse FIT data
            fit_data = json.loads(fit_data_json) if fit_data_json else {}
            metrics = fit_data.get('metrics', {})
            
            fit_files.append({
                'id': fit_id,
                'filename': filename,
                'tss': metrics.get('tss'),
                'duration': metrics.get('duration')
            })
        
        return fit_files
        
    finally:
        conn.close()


def reassign_fit_file(db_path: str, workout_id: int, new_fit_file_id: Optional[int]) -> bool:
    """
    Update a workout's FIT file assignment
    
    Args:
        db_path: Path to SQLite database
        workout_id: ID of workout to update
        new_fit_file_id: New FIT file ID (or None to remove assignment)
    
    Returns:
        True if successful
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        c.execute('UPDATE workouts SET fit_file_id = ? WHERE id = ?', 
                 (new_fit_file_id, workout_id))
        conn.commit()
        return c.rowcount > 0
        
    except Exception as e:
        print(f"Error reassigning FIT file: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


def unassign_fit_file(db_path: str, workout_id: int) -> bool:
    """
    Remove FIT file assignment from a workout (convenience wrapper)
    
    Args:
        db_path: Path to SQLite database
        workout_id: ID of workout to update
    
    Returns:
        True if successful
    """
    return reassign_fit_file(db_path, workout_id, None)


def _is_zwift(name: str) -> bool:
    return "zwift" in (name or "").lower()


def _is_garmin(name: str) -> bool:
    lowered = (name or "").lower()
    return "tp-" in lowered or "garmin" in lowered


LOCAL_TZ = "America/Los_Angeles"


def local_date(start_time: Optional[str]):
    """Local (Pacific) calendar date of a FIT start time recorded in UTC."""
    if not start_time:
        return None
    try:
        import pytz
        t = datetime.fromisoformat(str(start_time))
        if t.tzinfo is None:
            t = pytz.UTC.localize(t)
        return t.astimezone(pytz.timezone(LOCAL_TZ)).date()
    except (ValueError, ImportError):
        return None


def link_fit_files(db_path: str, start_date: str, end_date: str) -> int:
    """Link completed workouts to their FIT files (the one FIT matcher).

    FIT start times are UTC; they're converted to Pacific and must fall on the
    workout's local date (+/-1 day only when a file has no start time). Zwift files only
    pair with Zwift workouts; strength sessions are skipped; a FIT file already
    linked to a workout is never reused. Garmin files are scored on duration only
    (their TSS is computed differently); Zwift on TSS + duration.
    """
    conn = sqlite3.connect(db_path)
    try:
        lo = (datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
        hi = (datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')
        workouts = conn.execute(
            "SELECT id, workout_day, workout_title, workout_data FROM workouts "
            "WHERE workout_day BETWEEN ? AND ? AND fit_file_id IS NULL ORDER BY workout_day, id",
            (start_date, end_date)).fetchall()
        fits = conn.execute(
            "SELECT f.id, f.workout_day, f.file_name, f.fit_data FROM fit_files f "
            "WHERE f.workout_day BETWEEN ? AND ? "
            "AND NOT EXISTS (SELECT 1 FROM workouts w WHERE w.fit_file_id = f.id)",
            (lo, hi)).fetchall()

        available = []
        for fid, day, file_name, fit_json in fits:
            try:
                data = json.loads(fit_json) if fit_json else {}
            except ValueError:
                data = {}
            data = data or {}
            local_day = local_date(data.get("start_time"))
            available.append({
                "id": fid, "day": day, "local_day": local_day, "file_name": file_name or "",
                "tss": float((data.get("metrics") or {}).get("tss") or 0),
                "duration_min": float((data.get("metrics") or {}).get("duration") or 0)
                                or float(data.get("duration_seconds") or 0) / 60,
            })

        linked = 0
        for wid, day, title, workout_json in workouts:
            title_l = (title or "").lower()
            if "strength" in title_l or "weight" in title_l:
                continue
            try:
                metrics = (json.loads(workout_json) or {}).get("metrics", {})
            except ValueError:
                metrics = {}
            tss = float(metrics.get("actual_tss") or 0)
            dur = float(metrics.get("actual_duration") or 0)
            wday = datetime.strptime(day[:10], '%Y-%m-%d').date()

            best, best_score = None, None
            for fit in available:
                if _is_zwift(fit["file_name"]) != _is_zwift(title):
                    continue
                if fit["local_day"]:
                    # Garmin/Zwift record UTC; TrainingPeaks dates are local (Pacific).
                    if fit["local_day"] != wday:
                        continue
                    fday = wday
                else:
                    fday = datetime.strptime(fit["day"][:10], '%Y-%m-%d').date()
                    if abs((fday - wday).days) > 1:
                        continue
                if _is_garmin(fit["file_name"]):
                    score = abs(dur - fit["duration_min"])
                else:
                    score = abs(tss - fit["tss"]) + abs(dur - fit["duration_min"])
                score += 15 if fday != wday else 0
                if best_score is None or score < best_score:
                    best, best_score = fit, score
            if best is None:
                continue
            threshold = 50 if _is_garmin(best["file_name"]) else 100
            if best_score < threshold:
                conn.execute("UPDATE workouts SET fit_file_id = ? WHERE id = ?", (best["id"], wid))
                available.remove(best)
                linked += 1
        conn.commit()
        return linked
    finally:
        conn.close()


_NON_RECORDED_TYPES = {"other", "strength", "yoga", "mobility", "breathing"}


def fix_double_linked_fit_files(db_path: str, apply: bool = False) -> List[Dict[str, Any]]:
    """Resolve FIT files linked to more than one workout (left by older matchers).

    Keeps the link on the workout whose sport and duration best fit the file
    (a ride's file belongs to the ride, not the yoga session that day) and
    unlinks the rest so link_fit_files can find them their own file.
    """
    conn = sqlite3.connect(db_path)
    try:
        dupes = [r[0] for r in conn.execute(
            "SELECT fit_file_id FROM workouts WHERE fit_file_id IS NOT NULL GROUP BY fit_file_id HAVING COUNT(*) > 1")]
        changes = []
        for fid in dupes:
            fit_min = conn.execute(
                "SELECT COALESCE(json_extract(fit_data, '$.duration_seconds') / 60.0,"
                " json_extract(fit_data, '$.metrics.duration')) FROM fit_files WHERE id = ?", (fid,)).fetchone()[0] or 0
            rows = conn.execute(
                "SELECT id, workout_title, json_extract(workout_data, '$.type'),"
                " json_extract(workout_data, '$.metrics.actual_duration') FROM workouts WHERE fit_file_id = ?",
                (fid,)).fetchall()

            def score(row):
                _, _, wtype, minutes = row
                sport_penalty = 1000 if (wtype or "").lower() in _NON_RECORDED_TYPES else 0
                return sport_penalty + abs((minutes or 0) - fit_min)

            keep = min(rows, key=score)
            for row in rows:
                if row[0] != keep[0]:
                    changes.append({"fit_file_id": fid, "unlink_workout": row[0], "unlink_title": row[1],
                                    "keep_workout": keep[0], "keep_title": keep[1]})
                    if apply:
                        conn.execute("UPDATE workouts SET fit_file_id = NULL WHERE id = ?", (row[0],))
        if apply:
            conn.commit()
        return changes
    finally:
        conn.close()


def fix_cross_day_links(db_path: str, apply: bool = False) -> List[Dict[str, Any]]:
    """Unlink FIT files whose Pacific start date isn't the workout's date.

    Older matchers compared UTC dates with local ones, so e.g. a Wednesday 8am
    commute (15:00 UTC) could end up on Tuesday's evening ride.
    """
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            "SELECT w.id, w.workout_day, w.workout_title, json_extract(f.fit_data, '$.start_time') "
            "FROM workouts w JOIN fit_files f ON f.id = w.fit_file_id").fetchall()
        changes = []
        for wid, day, title, start in rows:
            local = local_date(start)
            if local and local.isoformat() != day[:10]:
                changes.append({"workout_id": wid, "workout_day": day, "title": title, "file_local_day": local.isoformat()})
                if apply:
                    conn.execute("UPDATE workouts SET fit_file_id = NULL WHERE id = ?", (wid,))
        if apply:
            conn.commit()
        return changes
    finally:
        conn.close()


def heal_name_only_matches(db_path: str) -> int:
    """Give name-only manual matches (e.g. made in the legacy app) their plan id."""
    from src.storage.schema_migrations import _m2_proposed_workout_fk
    conn = sqlite3.connect(db_path)
    try:
        before = conn.execute("SELECT COUNT(*) FROM workouts WHERE proposed_workout_id IS NOT NULL").fetchone()[0]
        _m2_proposed_workout_fk(conn)
        conn.commit()
        return conn.execute("SELECT COUNT(*) FROM workouts WHERE proposed_workout_id IS NOT NULL").fetchone()[0] - before
    finally:
        conn.close()
