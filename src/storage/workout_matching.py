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
                               match_source: str = "manual") -> bool:
    """
    Match a workout to a proposed workout name and update database
    
    Args:
        db_path: Path to SQLite database
        workout_id: ID of workout to match
        proposed_workout_name: Name of proposed workout (or custom name)
        match_source: Source of match ('manual' or 'ai')
    
    Returns:
        True if successful
    """
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    try:
        c.execute('''
            UPDATE workouts
            SET proposed_workout_name = ?,
                match_source = ?,
                matched_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (proposed_workout_name, match_source, workout_id))
        
        conn.commit()
        return c.rowcount > 0
        
    except Exception as e:
        print(f"Error matching workout: {e}")
        conn.rollback()
        return False
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
