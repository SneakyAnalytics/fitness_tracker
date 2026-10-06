# src/api/app.py

from src.config import get_db_path
from fastapi import Request, FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware

from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
import pandas as pd
import pytz
import io
from pydantic import BaseModel
import json
import sqlite3
import re
import os

# On Windows Docker Desktop bind mounts, the data/ directory itself is not writable
# for new file creation, so SQLite cannot create journal/WAL sidecar files.
# Patch sqlite3.connect to set journal_mode=MEMORY on every connection so that
# journaling is done in-memory and no sidecar files are ever written to disk.
_sqlite3_connect_orig = sqlite3.connect
def _sqlite3_connect_patched(*args, **kwargs):
    conn = _sqlite3_connect_orig(*args, **kwargs)
    try:
        conn.execute("PRAGMA journal_mode=MEMORY")
    except Exception:
        pass
    return conn
sqlite3.connect = _sqlite3_connect_patched


from ..storage.database import WorkoutDatabase
from ..utils.helpers import format_value, clean_float, clean_workout_data
from ..utils.fit_parser import FitParser
from ..utils.metrics_processor import MetricsProcessor
from ..utils.proposed_workouts_processor import process_proposed_workouts

# Initialize metrics processor
metrics_processor = MetricsProcessor()

app = FastAPI(title="Fitness Tracker API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)



def generate_workout_analysis(workout_data: Dict[str, Any]) -> Dict[str, str]:
    """Generate AI analysis of workout data"""
    
    # Placeholder prompts for future AI integration (kept as comments)
    # Create structured prompt for power analysis (example):
    # """Analyze this workout's power data:
    # - Average Power: {avg_power}W
    # - Normalized Power: {norm_power}W
    # - Intensity Factor: {intensity}
    # - Zone Distribution: {zones}
    #
    # Provide a brief analysis of:
    # 1. Overall intensity and distribution
    # 2. Workout type (based on zone distribution)
    # 3. Training impact and recovery needs
    # """
    #
    # Create structured prompt for heart rate analysis (example):
    # """Analyze this workout's heart rate response:
    # - Average HR: {avg_hr}bpm
    # - Max HR: {max_hr}bpm
    # - HR Zone Distribution: {zones}
    #
    # Consider:
    # 1. Cardiovascular strain
    # 2. Time spent in different zones
    # 3. Recovery implications
    # """
    
    # TODO: Integrate with actual AI analysis in the future
    # For now, return placeholder analysis
    return {
        "power_analysis": "Power analysis would appear here",
        "heart_rate_analysis": "Heart rate analysis would appear here",
        "overall_summary": "Overall workout analysis would appear here"
    }

def process_workout_data(row: pd.Series) -> Dict[str, Any]:
    """Process a single workout row into template format"""
    
    # Always use Title instead of "Other" for workout type
    workout_type = str(row['Title']) if row['WorkoutType'].lower() == 'other' else str(row['WorkoutType'])
    
    # Calculate zone percentages based on minutes
    def calculate_zone_percentages(zone_minutes: Dict[str, Optional[float]]) -> Dict[str, float]:
        # Coerce None/NaN to 0.0 for calculation
        sanitized = {k: (float(v) if v is not None and pd.notna(v) else 0.0) for k, v in zone_minutes.items()}
        total_minutes = sum(sanitized.values())
        if total_minutes > 0:
            return {k: (v / total_minutes) * 100.0 for k, v in sanitized.items()}
        # If total is zero, return zeros for each zone
        return {k: 0.0 for k in sanitized.keys()}

    workout = {
        'title': str(row['Title']),
        'type': workout_type,
        'workout_day': str(row['WorkoutDay']),
        
        # Basic Metrics
        'metrics': {
            'actual_tss': clean_float(row.get('TSS')),
            'actual_duration': clean_float(row.get('TimeTotalInHours', 0) * 60) if pd.notna(row.get('TimeTotalInHours')) else None,
            'rpe': clean_float(row.get('Rpe')),
            'feeling': clean_float(row.get('Feeling'))
        },
        
        # Power Data
        'power_data': {
            'average': clean_float(row.get('PowerAverage')),
            'max': clean_float(row.get('PowerMax')),
            'intensity_factor': clean_float(row.get('IF')),
            'zones': calculate_zone_percentages({
                'Zone 1 (Recovery)': clean_float(row.get('PWRZone1Minutes')),
                'Zone 2 (Endurance)': clean_float(row.get('PWRZone2Minutes')),
                'Zone 3 (Tempo)': clean_float(row.get('PWRZone3Minutes')),
                'Zone 4 (Threshold)': clean_float(row.get('PWRZone4Minutes')),
                'Zone 5 (VO2 Max)': clean_float(row.get('PWRZone5Minutes'))
            })
        } if pd.notna(row.get('PowerAverage')) else None,
        
        # Heart Rate Data
        'heart_rate_data': {
            'average': clean_float(row.get('HeartRateAverage')),
            'max': clean_float(row.get('HeartRateMax')),
            'zones': calculate_zone_percentages({
                'Zone 1 (Easy)': clean_float(row.get('HRZone1Minutes')),
                'Zone 2 (Moderate)': clean_float(row.get('HRZone2Minutes')),
                'Zone 3 (Hard)': clean_float(row.get('HRZone3Minutes')),
                'Zone 4 (Very Hard)': clean_float(row.get('HRZone4Minutes')),
                'Zone 5 (Maximum)': clean_float(row.get('HRZone5Minutes'))
            })
        } if pd.notna(row.get('HeartRateAverage')) else None,
        
        # Additional Metrics
        'distance': clean_float(row.get('DistanceInMeters')),
        'energy': clean_float(row.get('Energy')),
        'cadence_avg': clean_float(row.get('CadenceAverage')),
        'cadence_max': clean_float(row.get('CadenceMax')),
        'velocity_avg': clean_float(row.get('VelocityAverage')),
        'velocity_max': clean_float(row.get('VelocityMax')),
        
        # Comments/Description
        'description': str(row.get('WorkoutDescription', '')),
        'athlete_comments': str(row.get('AthleteComments', '')) if pd.notna(row.get('AthleteComments')) else None,
        'coach_comments': str(row.get('CoachComments', '')) if pd.notna(row.get('CoachComments')) else None
    }
    
    # Remove None values and empty strings from nested dictionaries
    for key in ['metrics', 'power_data', 'heart_rate_data']:
        if workout.get(key):
            workout[key] = {k: v for k, v in workout[key].items() if v is not None and v != ''}
            # Also clean nested zones dictionaries
            if 'zones' in workout[key]:
                workout[key]['zones'] = {k: v for k, v in workout[key]['zones'].items() if v is not None and v != ''}
    
    # Remove top-level None values and empty strings
    workout = {k: v for k, v in workout.items() if v is not None and v != ''}
    
    return workout

def parse_metric_value(value_str: str) -> Dict[str, float]:
    """Parse metric value string into components"""
    try:
        # Handle format like "Min : 32 / Max : 71 / Avg : 55"
        if '/' in value_str:
            parts = value_str.split('/')
            result = {}
            for part in parts:
                key, val = part.split(':')
                result[key.strip().lower()] = float(val.strip())
            return result
        # Handle simple numeric values
        return {"value": float(value_str)}
    except (ValueError, AttributeError):
        return {"value": 0.0}

class QualitativeData(BaseModel):
    workout_day: str
    workout_title: str
    how_it_felt: str
    technical_issues: Optional[str] = None
    modifications: Optional[str] = None
    athlete_comments: Optional[str] = None

from src.api.coach_routes import router as coach_router
app.include_router(coach_router)


@app.get("/")
async def root():
    return {"message": "Fitness Tracker API is running"}

@app.get("/health")
async def health_check():
    """Health check for monitoring and post-deploy verification."""
    import os
    from src.storage.events import unacknowledged_events

    db_path = Path(get_db_path())
    db_accessible, schema_version, db_error = False, None, None
    try:
        WorkoutDatabase()  # applies pending migrations
        conn = sqlite3.connect(str(db_path))
        try:
            schema_version = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()[0]
        finally:
            conn.close()
        db_accessible = True
    except Exception as e:
        db_error = str(e)

    return {
        "status": "healthy" if db_accessible else "degraded",
        "database": {"exists": db_path.exists(), "accessible": db_accessible, "path": str(db_path),
                     "schema_version": schema_version, "error": db_error},
        "environment": {
            "has_claude_key": bool(os.getenv("CLAUDE_API_KEY") or os.getenv("ANTHROPIC_API_KEY")),
            "has_gemini_key": bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")),
            "has_tp_username": bool(os.getenv("TRAININGPEAKS_USERNAME")),
        },
        "open_problems": len(unacknowledged_events(limit=100, levels=("warning", "error"))) if db_accessible else None,
        "message": "Fitness Tracker API is running",
    }


@app.get("/workouts")
async def get_workouts():
    db = WorkoutDatabase()
    return db.get_all_workouts()

@app.get("/workouts/with-analyses")
async def get_workouts_with_analyses():
    """Get all workouts with their analyses and interval data"""
    import sqlite3
    import json
    
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    
    # Use proposed_workout_name if available (from AI matching), otherwise fall back to workout_title
    query = """
    SELECT 
        w.id,
        w.workout_day,
        w.workout_title,
        COALESCE(w.proposed_workout_name, w.workout_title) as workout_name,
        w.workout_data,
        wa.analysis_text,
        wa.analysis_data
    FROM workouts w
    LEFT JOIN workout_analyses wa ON w.id = wa.workout_id
    WHERE wa.id IS NOT NULL
    ORDER BY w.workout_day DESC
    """
    
    cursor = conn.execute(query)
    columns = [desc[0] for desc in cursor.description]
    results = []
    
    for row in cursor.fetchall():
        workout = dict(zip(columns, row))
        results.append(workout)
    
    conn.close()
    return results

@app.get("/summaries")
async def get_summaries():
    """Get all weekly summaries"""
    try:
        db = WorkoutDatabase()
        summaries = db.get_all_summaries()
        return summaries if summaries else []
    except Exception as e:
        print(f"Error getting summaries: {str(e)}")
        return []

@app.post("/upload/workouts")
async def upload_workouts(file: UploadFile = File(...)):
    """Handle workouts CSV upload"""
    try:
        print(f"Processing workouts file: {file.filename}")
        contents = await file.read()
        decoded_contents = contents.decode('utf-8')
        
        # Parse CSV
        df = pd.read_csv(io.StringIO(decoded_contents))

        # Normalize WorkoutDay to local date (America/Los_Angeles) when a time
        # component is present. If the CSV contains only dates, preserve as-is.
        def _normalize_workout_day(series: pd.Series) -> pd.Series:
            import re

            # If any value looks like it contains a time component or timezone
            # (e.g., contains ':' or 'T' or 'Z' or a +/- offset), parse as UTC
            # then convert to America/Los_Angeles. Otherwise treat as date-only.
            pattern = re.compile(r"T|\d:\d|Z|[\+\-]\d{2}:?\d{2}")
            sample_values = series.dropna().astype(str).head(20).tolist()
            has_time = any(pattern.search(s) for s in sample_values)

            if has_time:
                # Parse as UTC (this will make naive timestamps assumed to be UTC)
                parsed = pd.to_datetime(series, utc=True, errors='coerce')
                # Convert to LA timezone and take the date part
                la = pytz.timezone('America/Los_Angeles')
                return parsed.dt.tz_convert(la).dt.strftime('%Y-%m-%d')
            else:
                # Date-only values - parse normally
                return pd.to_datetime(series, errors='coerce').dt.strftime('%Y-%m-%d')

        df['WorkoutDay'] = _normalize_workout_day(df['WorkoutDay'])
        
        # Get date range from CSV
        min_date = df['WorkoutDay'].min()
        max_date = df['WorkoutDay'].max()
        print(f"CSV contains workouts from {min_date} to {max_date}")
        
        # Initialize database connection
        db = WorkoutDatabase()
        
        # Delete existing workouts in date range (will be re-inserted with merged FIT data).
        # Their ids, matches and notes are put back afterwards (restore_workouts).
        from src.storage.workout_matching import (reattach_orphan_analyses, restore_workouts,
                                                  snapshot_workouts)
        kept = snapshot_workouts(db.db_path, min_date, max_date)
        conn = sqlite3.connect(db.db_path)
        c = conn.cursor()
        
        # Delete existing workouts in date range to avoid duplicates
        try:
            c.execute('DELETE FROM workouts WHERE workout_day >= ? AND workout_day <= ?', (min_date, max_date))
            deleted_workouts = c.rowcount
            conn.commit()
            print(f"Deleted {deleted_workouts} existing workouts in date range")
        except Exception as e:
            print(f"Error deleting existing workouts: {e}")
        
        # Note: We do NOT delete FIT files here - they are managed by save_fit_data() 
        # which updates existing entries based on filename to avoid duplicates
        
        # Build a map of existing FIT files to merge with CSV workouts
        # Match by date - store as LIST to handle multiple workouts per day
        existing_fit_data_by_date = {}  # date -> [parsed_fit_data, ...]
        try:
            # Query FIT files using DATE() to match date-only values from CSV
            c.execute('''
                SELECT id, workout_day, fit_data, file_name
                FROM fit_files 
                WHERE DATE(workout_day) >= DATE(?) AND DATE(workout_day) <= DATE(?)
                ORDER BY workout_day, id
            ''', (min_date, max_date))
            
            for fit_id, day, fit_data_str, filename in c.fetchall():
                try:
                    fit_data = json.loads(fit_data_str)
                    
                    # Calculate duration_minutes for matching
                    if 'duration_minutes' not in fit_data:
                        if 'duration_seconds' in fit_data:
                            fit_data['duration_minutes'] = fit_data['duration_seconds'] / 60
                        elif 'duration_hours' in fit_data:
                            fit_data['duration_minutes'] = fit_data['duration_hours'] * 60
                        elif 'metrics' in fit_data and 'duration' in fit_data['metrics']:
                            fit_data['duration_minutes'] = fit_data['metrics']['duration']
                    
                    # Normalize day to date-only format (YYYY-MM-DD) to match CSV workout_day
                    day_only = day.split(' ')[0] if ' ' in day else day
                    
                    # Store as list to handle multiple workouts per day (include ALL FIT files, not just cycling)
                    if day_only not in existing_fit_data_by_date:
                        existing_fit_data_by_date[day_only] = []
                    fit_data['_fit_id'] = fit_id  # Track ID for matching
                    fit_data['_filename'] = filename  # Track filename for matching
                    existing_fit_data_by_date[day_only].append(fit_data)
                    
                    # Log with appropriate detail based on FIT file type
                    has_power = fit_data.get('power_metrics', {}).get('power_series')
                    if has_power:
                        ps_len = len(fit_data['power_metrics']['power_series'])
                        dur_str = f", {fit_data.get('duration_minutes', 0):.0f}min" if fit_data.get('duration_minutes') else ""
                        print(f"Found FIT data for {day_only} (ID:{fit_id}, {filename}{dur_str}) with {ps_len} power points")
                    else:
                        dur_str = f", {fit_data.get('duration_minutes', 0):.0f}min" if fit_data.get('duration_minutes') else ""
                        print(f"Found FIT data for {day_only} (ID:{fit_id}, {filename}{dur_str}) [no power data]")
                except Exception as e:
                    print(f"Error parsing FIT data: {e}")
        except Exception as e:
            print(f"Error querying FIT files: {e}")
        finally:
            conn.close()
        
        # Track which FIT files have been used to avoid reusing them
        used_fit_ids = set()
        
        # Now insert all workouts from CSV, merging with FIT data where available
        workouts = []
        for _, row in df.iterrows():
            print(f"Processing workout: {row['Title']} on {row['WorkoutDay']}")
            
            # Calculate zone percentages based on minutes
            def calculate_zone_percentages(zone_minutes: Dict[str, Optional[float]], total_minutes: float) -> Dict[str, float]:
                # Coerce None/NaN to 0.0 for calculation
                sanitized = {k: (float(v) if v is not None and pd.notna(v) else 0.0) for k, v in zone_minutes.items()}
                if total_minutes > 0:
                    return {k: (v / total_minutes) * 100.0 for k, v in sanitized.items()}
                return {k: 0.0 for k in sanitized.keys()}
            
            actual_duration = clean_float(row.get('TimeTotalInHours', 0) * 60) if pd.notna(row.get('TimeTotalInHours')) else None
            
            workout = {
                'title': str(row['Title']).strip(),
                'type': str(row['WorkoutType']).strip(),
                'workout_day': str(row['WorkoutDay']).strip(),
                'metrics': {
                    'actual_tss': float(row['TSS']) if pd.notna(row.get('TSS')) else None,
                    'actual_duration': actual_duration,
                    'rpe': float(row['Rpe']) if pd.notna(row.get('Rpe')) else None,
                },

                'power_data': {
                    'average': float(row['PowerAverage']) if pd.notna(row.get('PowerAverage')) else None,
                    'max': float(row['PowerMax']) if pd.notna(row.get('PowerMax')) else None,
                    'if': float(row['IF']) if pd.notna(row.get('IF')) else None,
                    'zones': calculate_zone_percentages({
                        'zone1': float(row['PWRZone1Minutes']) if pd.notna(row.get('PWRZone1Minutes')) else 0,
                        'zone2': float(row['PWRZone2Minutes']) if pd.notna(row.get('PWRZone2Minutes')) else 0,
                        'zone3': float(row['PWRZone3Minutes']) if pd.notna(row.get('PWRZone3Minutes')) else 0,
                        'zone4': float(row['PWRZone4Minutes']) if pd.notna(row.get('PWRZone4Minutes')) else 0,
                        'zone5': float(row['PWRZone5Minutes']) if pd.notna(row.get('PWRZone5Minutes')) else 0,
                    }, (actual_duration or 0.0))
                } if pd.notna(row.get('PowerAverage')) else None,
                'heart_rate_data': {
                    'average': float(row['HeartRateAverage']) if pd.notna(row.get('HeartRateAverage')) else None,
                    'max': float(row['HeartRateMax']) if pd.notna(row.get('HeartRateMax')) else None,
                    'zones': calculate_zone_percentages({
                        'zone1': float(row['HRZone1Minutes']) if pd.notna(row.get('HRZone1Minutes')) else 0,
                        'zone2': float(row['HRZone2Minutes']) if pd.notna(row.get('HRZone2Minutes')) else 0,
                        'zone3': float(row['HRZone3Minutes']) if pd.notna(row.get('HRZone3Minutes')) else 0,
                        'zone4': float(row['HRZone4Minutes']) if pd.notna(row.get('HRZone4Minutes')) else 0,
                        'zone5': float(row['HRZone5Minutes']) if pd.notna(row.get('HRZone5Minutes')) else 0,
                    }, (actual_duration or 0.0))
                } if pd.notna(row.get('HeartRateAverage')) else None,
                'athlete_comments': str(row.get('AthleteComments')) if pd.notna(row.get('AthleteComments')) else None
            }
            
            # Check if there's FIT data for this date (match intelligently with multiple workouts per day)
            if workout['workout_day'] in existing_fit_data_by_date and workout['type'] in ['Bike', 'Cycling', 'Biking']:
                available_fits = existing_fit_data_by_date[workout['workout_day']]
                fit_data = None
                
                # Try to find the best match:
                # 1. Match by sport type (Zwift vs Garmin)
                # 2. Match by duration (within 5 minutes)
                # 3. Use first unused FIT file
                
                workout_duration = workout['metrics'].get('actual_duration')
                workout_title_lower = workout['title'].lower()
                
                # First pass: Look for intelligent matches
                for candidate in available_fits:
                    if candidate['_fit_id'] in used_fit_ids:
                        continue  # Already used
                    
                    # Check if title hints at type (e.g., "Strength" should not match Zwift FIT)
                    candidate_filename = candidate.get('_filename', '').lower()
                    
                    # If CSV workout is clearly Zwift, prefer FIT file with "zwift" in filename
                    if 'zwift' in workout_title_lower and 'zwift' in candidate_filename:
                        fit_data = candidate
                        print(f"  Matched by Zwift title: {candidate_filename}")
                        break
                    
                    # If CSV workout has "strength" in title, skip FIT files from Zwift
                    if 'strength' in workout_title_lower and 'zwift' in candidate_filename:
                        print(f"  Skipping Zwift FIT {candidate_filename} for Strength workout")
                        continue
                    
                    # Match by duration (within 10% or 5 minutes)
                    if workout_duration:
                        fit_duration = candidate.get('duration_minutes')
                        if fit_duration:
                            duration_diff = abs(workout_duration - fit_duration)
                            if duration_diff < 5 or duration_diff / workout_duration < 0.1:
                                fit_data = candidate
                                print(f"  Matched by duration: CSV {workout_duration}min ≈ FIT {fit_duration}min")
                                break
                
                # Second pass: If no intelligent match, use first unused FIT file
                if not fit_data:
                    for candidate in available_fits:
                        if candidate['_fit_id'] not in used_fit_ids:
                            fit_data = candidate
                            print(f"  Using first unused FIT file: {candidate.get('_filename')}")
                            break
                
                # If we found a match, merge the data and mark as used
                if fit_data:
                    used_fit_ids.add(fit_data['_fit_id'])
                    workout['fit_file_id'] = fit_data['_fit_id']  # Link workout row to fit_files row
                    print(f"  Merging FIT data (ID:{fit_data['_fit_id']}) for {workout['workout_day']} {workout['title']}")
                
                    # Transform power_metrics (FIT format) to power_data (workout format)
                    power_metrics = fit_data.get('power_metrics') or {}
                    if power_metrics and 'power_series' in power_metrics:
                        if workout['power_data'] is None:
                            workout['power_data'] = {}
                        
                        # Add power_series and time_series from FIT
                        workout['power_data']['power_series'] = power_metrics['power_series']
                        if 'time_series' in fit_data:
                            workout['power_data']['time_series'] = fit_data['time_series']
                        
                        print(f"    Added power_series: {len(workout['power_data']['power_series'])} points")
                    
                    # Transform hr_metrics to heart_rate_data format
                    hr_metrics = fit_data.get('hr_metrics') or {}
                    if hr_metrics and 'hr_series' in hr_metrics:
                        if workout['heart_rate_data'] is None:
                            workout['heart_rate_data'] = {}
                        workout['heart_rate_data']['hr_series'] = hr_metrics['hr_series']
                        print(f"    Added hr_series: {len(workout['heart_rate_data']['hr_series'])} points")
                    
                    # Preserve sport classification from FIT file
                    if 'sport' in fit_data:
                        workout['sport'] = fit_data['sport']
                        print(f"    Set sport: {workout['sport']}")
                else:
                    print(f"  No unused FIT file available for {workout['title']}")
            
            # Clean workout data
            cleaned_workout = clean_workout_data(workout)

            # Save to database (using the same db instance)
            if db.save_workout(cleaned_workout):
                workouts.append(cleaned_workout)
                print(f"Saved workout: {workout['title']} on {workout['workout_day']}")
            else:
                print(f"Failed to save workout: {workout['title']} on {workout['workout_day']}")
        
        restored = restore_workouts(db.db_path, kept, min_date, max_date)
        reattached = reattach_orphan_analyses(db.db_path)
        print(f"\n✓ Successfully processed {len(workouts)} workouts "
              f"(kept identity of {restored}, reattached {reattached} analyses)")
        return {
            "message": f"Successfully processed {len(workouts)} workouts",
            "workouts": workouts
        }
        
    except Exception as e:
        print(f"Error processing workouts file: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/upload/metrics")
async def upload_metrics(file: UploadFile = File(...)):
    """Handle metrics CSV upload"""
    try:
        print(f"Processing metrics file: {file.filename}")
        contents = await file.read()
        decoded_contents = contents.decode('utf-8')
        
        # Print first few lines for debugging
        print(f"First few lines of file:\n{decoded_contents[:200]}")
        
        # Guard against empty uploads
        if not decoded_contents or decoded_contents.strip() == "":
            print("Error processing metrics file: uploaded file is empty")
            raise HTTPException(status_code=400, detail="Uploaded metrics file is empty or malformed")

        # Parse CSV (guard pandas EmptyDataError for clearer feedback)
        try:
            df = pd.read_csv(
                io.StringIO(decoded_contents),
                on_bad_lines='skip',
                skipinitialspace=True
            )
        except pd.errors.EmptyDataError as ede:
            print(f"Error processing metrics file: {str(ede)}")
            raise HTTPException(status_code=400, detail="Uploaded metrics file contains no parseable data")
        
        print(f"Columns found: {df.columns.tolist()}")
        
        # Group metrics by date and type
        df['Date'] = pd.to_datetime(df['Timestamp']).dt.date.astype(str)
        grouped = df.groupby(['Date', 'Type'])
        
        db = WorkoutDatabase()
        processed_metrics = []
        
        for (date, metric_type), group in grouped:
            # Process each value in the group
            metric_values = []
            for _, row in group.iterrows():
                parsed_value = parse_metric_value(row['Value'])
                metric_values.append({
                    'timestamp': row['Timestamp'],
                    **parsed_value
                })
            
            metric_data = {
                'values': metric_values,
                'summary': {
                    'min': min(v.get('min', v.get('value', 0)) for v in metric_values),
                    'max': max(v.get('max', v.get('value', 0)) for v in metric_values),
                    'avg': sum(v.get('avg', v.get('value', 0)) for v in metric_values) / len(metric_values)
                }
            }
            
            # Save to database
            saved = db.save_daily_metric(date, metric_type, metric_data)
            if saved:
                processed_metrics.append({
                    'date': date,
                    'type': metric_type,
                    'data': metric_data
                })
            
            print(f"Processed metrics for {date} - {metric_type}")
        
        return {
            "message": f"Successfully processed {len(processed_metrics)} metrics",
            "metrics": processed_metrics
        }
    except Exception as e:
        print(f"Error processing metrics file: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/workouts/qualitative")
async def save_qualitative_data(data: QualitativeData):
    """Save qualitative data for a workout"""
    try:
        db = WorkoutDatabase()
        success = db.update_workout_qualitative(
            workout_day=data.workout_day,
            workout_title=data.workout_title,
            qualitative_data={
                'how_it_felt': data.how_it_felt or '',
                'technical_issues': data.technical_issues or '',
                'modifications': data.modifications or '',
                'athlete_comments': data.athlete_comments or ''
            }
        )
        if success:
            return {"message": "Qualitative data saved successfully"}
        else:
            raise HTTPException(status_code=404, detail="Workout not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/summary/generate")
async def generate_summary(start_date: str, end_date: str):
    """Generate a weekly summary"""
    try:
        print(f"\nGenerating weekly summary for {start_date} to {end_date}")
        db = WorkoutDatabase()
        summary = db.generate_weekly_summary(start_date, end_date)
        
        if not summary:
            print("No summary data returned from database")
            raise ValueError("No data found for the specified date range")
        
        print(f"Generated summary with {len(summary.get('qualitative_feedback', []))} workouts")
        print(f"Total TSS: {summary.get('total_tss')}")
        print(f"Total Hours: {summary.get('total_training_hours')}")
        
        return summary
        
    except Exception as e:
        print(f"Error generating summary: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/summary/save")
async def save_summary(summary: Dict[str, Any]):
    """Save a weekly summary"""
    try:
        # Validate required fields
        required_fields = [
            'start_date', 'end_date', 'total_tss', 'total_training_hours',
            'sessions_completed', 'avg_sleep_quality', 'avg_daily_energy'
        ]

        missing_fields = [field for field in required_fields if field not in summary]
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")

        # Clean the summary data to ensure it matches our model
        cleaned_summary = {
            'start_date': summary['start_date'],
            'end_date': summary['end_date'],
            'total_tss': float(summary['total_tss']),
            'total_training_hours': float(summary['total_training_hours']),
            'sessions_completed': int(summary['sessions_completed']),
            'avg_sleep_quality': float(summary['avg_sleep_quality']),
            'avg_daily_energy': float(summary['avg_daily_energy']),
            'daily_energy': summary.get('daily_energy', {}),
            'daily_sleep_quality': summary.get('daily_sleep_quality', {}),
            'muscle_soreness_patterns': summary.get('muscle_soreness_patterns'),
            'general_fatigue_level': summary.get('general_fatigue_level'),
            'qualitative_feedback': summary.get('qualitative_feedback', []),
            'workout_types': summary.get('workout_types', [])
        }

        # Debug: Print the cleaned summary data
        print("DEBUG: Cleaned summary data:", json.dumps(cleaned_summary, indent=2))

        db = WorkoutDatabase()
        success = db.save_weekly_summary(cleaned_summary)
        if success:
            return {"message": "Summary saved successfully"}
        else:
            raise HTTPException(
                status_code=500,
                detail="Database save operation failed"
            )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )

@app.get("/summary/export")
async def export_summary(start_date: str, end_date: str):
    """Export summary in AI-ready format"""
    try:
        db = WorkoutDatabase()
        summary = db.generate_weekly_summary(start_date, end_date)
        if not summary:
            raise HTTPException(status_code=404, detail="No data found for the specified date range")

        print("DEBUG: Raw summary data:", json.dumps(summary, indent=2))        

        # Get the qualitative data from the database
        qualitative_data = db.get_weekly_summary_qualitative_data(start_date, end_date)
        if qualitative_data:
            summary.update(qualitative_data)
            
        print("DEBUG: Summary with qualitative data:", json.dumps(summary, indent=2))

        # Load persisted athlete settings (if any) and include in export header
        try:
            athlete_settings = db.load_athlete_settings('default')
        except Exception:
            athlete_settings = None

        if athlete_settings:
            print("DEBUG: Loaded athlete settings:", json.dumps(athlete_settings, indent=2))

        # Start building content with athlete settings and weekly plan details
        content = []
        if athlete_settings:
            content.append("## Athlete Settings (effective)")
            # Show FTP if available
            ftp_val = athlete_settings.get('ftp') or athlete_settings.get('ATHLETE_FTP')
            if ftp_val:
                content.append(f"• FTP: {ftp_val}")

            # HR zones may be stored as list or comma string
            hr_zones = athlete_settings.get('hr_zones') or athlete_settings.get('ATHLETE_HR_ZONES')
            if hr_zones:
                if isinstance(hr_zones, str):
                    hr_display = hr_zones
                elif isinstance(hr_zones, (list, tuple)):
                    hr_display = ','.join(str(x) for x in hr_zones)
                else:
                    hr_display = str(hr_zones)
                content.append(f"• HR zone upper bounds: {hr_display}")

            power_zones = athlete_settings.get('power_zones') or athlete_settings.get('ATHLETE_POWER_ZONES')
            if power_zones:
                if isinstance(power_zones, str):
                    p_display = power_zones
                elif isinstance(power_zones, (list, tuple)):
                    p_display = ','.join(str(x) for x in power_zones)
                else:
                    p_display = str(power_zones)
                content.append(f"• Power zone cutoffs (watts): {p_display}")
            content.append("")

        content.append("## Overall Weekly Summary")
        
        if summary.get('weekly_plan'):
            wp = summary['weekly_plan']
            content.extend([
                f"• Planned Weekly TSS Range: {wp['plannedTSS_min']} - {wp['plannedTSS_max']}",
                f"• Actual Total TSS: {format_value(summary.get('total_tss'))}",
                f"• Weekly Plan Notes: {wp['notes']}"
            ])
        else:
            content.append(f"• Total TSS: {format_value(summary.get('total_tss'))}")
            
        content.extend([
            f"• Total Training Hours: {format_value(summary.get('total_training_hours'))}",
            f"• Number of Sessions Completed: {summary.get('sessions_completed', 0)}",
            f"• Average Sleep Quality (1-5): {format_value(summary.get('avg_sleep_quality'))}",
            f"• Average Daily Energy (1-5): {format_value(summary.get('avg_daily_energy'))}",
        ])
        # Add daily energy levels
        daily_energy = summary.get('daily_energy', {})
        days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        for day in days_of_week:
            date_str = (pd.to_datetime(start_date) + pd.Timedelta(days=days_of_week.index(day))).strftime('%Y-%m-%d')
            energy_value = daily_energy.get(date_str, "N/A")
            content.append(f"   • {day}: {format_value(energy_value)}")

        # Add daily sleep quality levels
        content.append("")
        content.append("2. Sleep Quality Trend:")
        daily_sleep_quality = summary.get('daily_sleep_quality', {})
        for day in days_of_week:
            date_str = (pd.to_datetime(start_date) + pd.Timedelta(days=days_of_week.index(day))).strftime('%Y-%m-%d')
            sleep_quality_value = daily_sleep_quality.get(date_str, "N/A")
            content.append(f"   • {day}: {format_value(sleep_quality_value)}")

        # Add recovery quality sections
        content.extend([
            "",
            "3. Recovery Quality:",
            f"   • Muscle soreness patterns: {format_value(summary.get('muscle_soreness_patterns'))}",
            f"   • General fatigue level: {format_value(summary.get('general_fatigue_level'))}",

            "",
            "## Daily Workout Details"
        ])

        # Process each workout
        for workout in sorted(summary.get('qualitative_feedback', []), key=lambda x: x.get('day', '')):
            content.extend([
                "",
                f"### {workout.get('day')} - {workout.get('type')}",
            ])

            # Basic Metrics section
            workout_data = workout.get('workout_data', {})
            metrics = workout_data.get('metrics', {})
            content.extend([
                "1. Basic Metrics:",
                f"   - TSS: {format_value(metrics.get('planned_tss'))} (planned) | {format_value(metrics.get('actual_tss'))} (actual)",
                f"   - Duration: {format_value(metrics.get('planned_duration'))} mins (planned) | {format_value(metrics.get('actual_duration'))} mins (actual)",
                f"   - RPE: {metrics.get('planned_rpe', 'N/A')} (target) | {format_value(metrics.get('rpe'))} (actual)",
            ])

            # Power Data section (for bike workouts)
            power_data = workout_data.get('power_data', {})
            if power_data and isinstance(power_data, dict):
                content.extend([
                    "",
                    "2. Power Data:",
                    f"   - Average Power: {format_value(power_data.get('average'))}",
                    f"   - Max Power: {format_value(power_data.get('max'))}",
                    f"   - Normalized Power: {format_value(power_data.get('normalized_power'))}",
                    f"   - Intensity Factor (IF): {format_value(power_data.get('intensity_factor'))}",
                    "   - Power Zone Distribution:",
                ])
                
                zones = power_data.get('zones', {})
                if isinstance(zones, dict):
                    for zone, value in zones.items():
                        if value and float(value) > 0:
                            content.append(f"     * {zone}: {format_value(value, is_percentage=True)}")

            # Heart Rate Analysis section
            hr_data = workout_data.get('heart_rate_data', {})
            if hr_data and isinstance(hr_data, dict):
                content.extend([
                    "",
                    "3. Heart Rate Analysis:",
                    f"   - Average HR: {format_value(hr_data.get('average'))}",
                    f"   - Max HR: {format_value(hr_data.get('max'))}",
                    "   - Time in HR Zones:",
                ])
                
                zones = hr_data.get('zones', {})
                if isinstance(zones, dict):
                    # Standardize zone names for display
                    def standardize_hr_zone_key(key):
                        """Convert any zone format to a consistent display format"""
                        if isinstance(key, str):
                            # Handle 'zone1' format
                            if key.lower().startswith('zone'):
                                if len(key) > 4 and key[4:5].isdigit() and key.lower() == f"zone{key[4:5]}":
                                    zone_num = key[4:5]
                                    # Map to standard format
                                    zone_names = {
                                        '1': 'Zone 1 (Recovery)',
                                        '2': 'Zone 2 (Endurance)',
                                        '3': 'Zone 3 (Tempo)',
                                        '4': 'Zone 4 (Threshold)',
                                        '5': 'Zone 5 (Maximum)'
                                    }
                                    return zone_names.get(zone_num, f"Zone {zone_num}")
                                # Already in a fully defined format
                                return key
                        return key
                    
                    # Create a standardized dictionary
                    standardized_zones = {standardize_hr_zone_key(k): v for k, v in zones.items()}
                    
                    # Add zones in order for better readability (if they exist)
                    ordered_zone_names = [
                        'Zone 1 (Recovery)', 
                        'Zone 2 (Endurance)', 
                        'Zone 3 (Tempo)', 
                        'Zone 4 (Threshold)', 
                        'Zone 5 (Maximum)'
                    ]
                    
                    # First try to show zones in the standard order
                    for zone_name in ordered_zone_names:
                        if zone_name in standardized_zones and standardized_zones[zone_name] and float(standardized_zones[zone_name]) > 0:
                            content.append(f"     * {zone_name}: {format_value(standardized_zones[zone_name], is_percentage=True)}")
                    
                    # Then show any remaining zones not in the standard format
                    for zone, value in standardized_zones.items():
                        if zone not in ordered_zone_names and value and float(value) > 0:
                            content.append(f"     * {zone}: {format_value(value, is_percentage=True)}")

            # Athlete Comments section
            # Comments may be stored directly on the workout entry (athlete_comments)
            # or inside the qualitative/feedback object depending on code path.
            athlete_comments = (
                workout.get('athlete_comments') or
                (workout.get('feedback') or {}).get('athlete_comments') or
                (workout.get('qualitative') or {}).get('athlete_comments')
            )
            content.extend([
                "",
                "4. Athlete Comments:",
                f"   - {format_value(athlete_comments) if athlete_comments else 'No comments provided'}",
            ])

            # Additional section for strength or yoga workouts with performance data
            if workout.get('type', '').lower() in ('strength', 'yoga', 'other'):
                # Look for performance data
                performance_data = workout.get('workout_data', {}).get('performance_data')
                
                if performance_data:
                    content.extend([
                        "",
                        f"### Performance Data for {workout.get('type', '').capitalize()} Session:",
                    ])
                    
                    # Add general notes if available
                    if performance_data.get('general_notes'):
                        content.append(f"**Overall Notes:** {performance_data.get('general_notes')}")
                        content.append("")
                    
                    # Process sections with exercises
                    for section_idx, section in enumerate(performance_data.get('sections', [])):
                        section_name = section.get('name', f"Section {section_idx+1}")
                        content.append(f"**{section_name}**")
                        
                        # Process exercises in this section
                        for exercise in section.get('exercises', []):
                            exercise_name = exercise.get('name', 'Exercise')
                            content.append(f"- {exercise_name}:")
                            
                            # Process each set
                            for set_idx, set_data in enumerate(exercise.get('sets', [])):
                                set_notes = f" ({set_data.get('notes')})" if set_data.get('notes') else ""
                                # Include round information if available
                                round_info = f" (Round {set_data.get('round')})" if set_data.get('round') else ""
                                if set_data.get('actual_reps') > 0 or set_data.get('actual_weight') > 0:
                                    set_text = f"  * Set {set_idx+1}{round_info}: {set_data.get('actual_reps', 0)} reps @ {set_data.get('actual_weight', 0)} lbs{set_notes}"
                                    content.append(set_text)
                        
                        content.append("")
                else:
                    # Legacy format for strength workouts without detailed performance data
                    if workout.get('type', '').lower() == 'strength':
                        content.extend([
                            "",
                            "### For Strength Sessions:",
                            f"- Exercises completed: {format_value(workout.get('exercises_completed'))}",
                            f"- Weight/rep adjustments: {format_value(workout.get('weight_adjustments'))}",
                            f"- Areas of soreness: {format_value(workout.get('areas_of_soreness'))}",
                            f"- Recovery time needed: {format_value(workout.get('recovery_needed'))}",
                        ])

        return {
            "content": "\n".join(content),
            "filename": f"weekly_summary_{start_date}_to_{end_date}.txt"
        }

    except Exception as e:
        print(f"Error in export_summary: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Error generating export: {str(e)}")

@app.post("/upload/fit")
async def upload_fit(file: UploadFile = File(...)):
    """Handle FIT file upload with improved unique title generation"""
    try:
        print(f"\n{'='*80}")
        print(f"Processing FIT file: {file.filename}")
        print(f"{'='*80}")
        contents = await file.read()
        
        # Parse date from filename and standardize format
        date = None
        filename: str = file.filename or ""

        # Parse the FIT file once. Prefer a persisted athlete FTP if available to avoid per-file FTP estimation
        fit_parser = FitParser()
        try:
            # Try to load athlete FTP from persisted settings
            try:
                db_for_parse = WorkoutDatabase()
                athlete_settings = db_for_parse.load_athlete_settings('default') or {}
                athlete_ftp = None
                if athlete_settings and isinstance(athlete_settings, dict):
                    athlete_ftp = athlete_settings.get('ftp') or athlete_settings.get('FTP')
                    if athlete_ftp is not None:
                        try:
                            athlete_ftp = float(athlete_ftp)
                        except Exception:
                            athlete_ftp = None
            except Exception as e:
                print(f"DEBUG: Could not load athlete settings for FTP: {e}")
                athlete_ftp = None

            parsed_data = fit_parser.parse_fit_file(contents, athlete_ftp=athlete_ftp)
            # Ensure we always have a dictionary, even if parsing fails
            if parsed_data is None:
                print(f"⚠️  Warning: FIT file parsing returned None for {file.filename}")
                parsed_data = {}
        except Exception as e:
            print(f"⚠️  Error parsing FIT file {file.filename}: {str(e)}")
            print("Continuing with empty parsed_data...")
            parsed_data = {}
        
        # Handle date extraction based on filename patterns
        if 'zwift-activity' in filename:
            start_time_str = parsed_data.get('start_time')
            if start_time_str:
                try:
                    import pytz
                    # Convert to datetime object (assume UTC if no timezone)
                    start_time = datetime.fromisoformat(start_time_str)
                    
                    # If timezone-naive, assume it's UTC
                    if start_time.tzinfo is None:
                        utc = pytz.UTC
                        start_time = utc.localize(start_time)
    
                    # Convert to Los Angeles timezone
                    la_timezone = pytz.timezone('America/Los_Angeles')
                    la_start_time = start_time.astimezone(la_timezone)
    
                    # Log times for debugging
                    print(f"Original start_time (UTC): {start_time}")
                    print(f"LA start_time (PST/PDT): {la_start_time}")
    
                    # Extract date in YYYY-MM-DD format
                    date = la_start_time.strftime('%Y-%m-%d')
                    print(f"Extracted date from Zwift file: {date}")
                except Exception as e:
                    print(f"Error processing start time {start_time_str}: {str(e)}")
                    date = None
            else:
                date = '2025-01-16'
        elif '.GarminPing.' in filename or '_GarminPing_' in filename:
            # Handle both formats: dots and underscores
            if '.GarminPing.' in filename:
                date_part = filename.split('.')[1]
                print("Using period-separated format for date extraction")
            else:  # '_GarminPing_' format
                # Extract date from underscore format: tp-5350487_2025-10-23-15-06-02-533Z_GarminPing_...
                parts = filename.split('_')
                if len(parts) >= 2:
                    date_part = parts[1]  # Get the second part which contains the date
                    print("Using underscore-separated format for date extraction")
                else:
                    date_part = None
            
            if date_part:
                # GarminPing timestamps are UTC (Z suffix), e.g. "2026-05-03-00-54-17-559Z"
                # A UTC timestamp like 00:54 on May 3 is actually May 2 in Pacific time (UTC-7/PDT)
                # so we must convert to local time before extracting the date.
                try:
                    import re as _re
                    ts_match = _re.match(r'(\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})-(\d{2})', date_part)
                    if ts_match:
                        utc_dt = datetime(
                            int(ts_match.group(1)), int(ts_match.group(2)), int(ts_match.group(3)),
                            int(ts_match.group(4)), int(ts_match.group(5)), int(ts_match.group(6)),
                            tzinfo=pytz.UTC
                        )
                        la_tz = pytz.timezone('America/Los_Angeles')
                        local_dt = utc_dt.astimezone(la_tz)
                        date = local_dt.strftime('%Y-%m-%d')
                        print(f"Extracted date from GarminPing filename (UTC→local): utc={utc_dt.date()} → local={date}")
                    else:
                        date = date_part[:10]
                        print(f"Extracted date from GarminPing filename: {date}")
                except Exception as _tz_err:
                    date = date_part[:10]
                    print(f"Extracted date from GarminPing filename (fallback): {date} ({_tz_err})")
        elif filename.endswith('.fit') or filename.endswith('.FIT'):
            # Handle standard Garmin FIT files - try to extract date from filename
            # Common patterns: YYYY-MM-DD_HH-MM-SS.fit, Activity_YYYY-MM-DD.fit, etc.
            import re
            date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
            if date_match:
                date = date_match.group(1)
                print(f"Extracted date using regex: {date}")
            else:
                # Try to get date from FIT file start_time
                start_time_str = parsed_data.get('start_time')
                if start_time_str:
                    try:
                        start_time = datetime.fromisoformat(start_time_str)
                        # Convert to Los Angeles timezone
                        la_timezone = pytz.timezone('America/Los_Angeles')
                        la_start_time = start_time.astimezone(la_timezone)
                        date = la_start_time.strftime('%Y-%m-%d')
                        print(f"Extracted date from FIT file start_time: {date}")
                    except Exception as e:
                        print(f"Error extracting date from start_time {start_time_str}: {str(e)}")
                        date = None
        
        if not date:
            print(f"⚠️  Could not extract date from filename: {filename}")
            date = "2025-01-16"  # Fallback date
        
        print(f"Final date: {date}")
        
        # Extract title from filename - make it UNIQUE to avoid collisions
        if 'zwift-activity' in filename:
            # Keep the activity ID for uniqueness
            title = filename.split('.')[0].replace('zwift-activity-', 'Zwift Workout ')
            print(f"Generated Zwift title: {title}")
        elif '.GarminPing.' in filename or '_GarminPing_' in filename:
            # Extract the unique identifier from the filename
            # Format: tp-5350487.2025-10-23-15-06-02-533Z.GarminPing.AAAAAGj6RFpWW8L5.FIT.gz
            # We want the unique ID: AAAAAGj6RFpWW8L5 (after GarminPing)
            
            # Split by periods and find the unique ID (after GarminPing)
            parts = filename.split('.')
            unique_id = None
            
            for i, part in enumerate(parts):
                if 'GarminPing' in part and i + 1 < len(parts):
                    unique_id = parts[i + 1]
                    break
            
            if unique_id and unique_id not in ['FIT', 'fit', 'gz']:
                title = f"Garmin-{unique_id}"
            else:
                # Fallback: use the full filename without extensions
                title = filename.replace('.fit.gz', '').replace('.FIT.gz', '')
            
            print(f"Generated Garmin title: {title}")
        else:
            # For other FIT files, use a more specific title
            # Remove extension and use full filename
            title = filename.rsplit('.', 2)[0] if '.gz' in filename else filename.rsplit('.', 1)[0]
            print(f"Generated generic title: {title}")
        
        # Save to database
        db = WorkoutDatabase()
        saved = db.save_fit_data(date, title, parsed_data, filename)
        
        if not saved:
            raise ValueError(f"Failed to save FIT data to database for {filename}")
        
        # Also save FIT file to disk so AI analysis can find it later
        try:
            extract_dir = Path("data/trainingpeaks_extracted")
            extract_dir.mkdir(parents=True, exist_ok=True)
            
            # Prefix filename with date so find_todays_fit_files can find it
            safe_filename = filename if filename else f"{title.replace(' ', '_')}.fit"
            date_prefixed_filename = f"{date}-{safe_filename}"
            fit_file_path = extract_dir / date_prefixed_filename
            
            with open(fit_file_path, 'wb') as f:
                f.write(contents)
            
            print(f"✓ Saved FIT file to disk: {fit_file_path}")
        except Exception as save_err:
            print(f"⚠️  Warning: Could not save FIT file to disk: {save_err}")
            # Don't fail the upload if disk save fails - database save is sufficient
        
        print(f"✓ Successfully saved to database: {title} on {date}")
        print(f"{'='*80}\n")
        
        return {
            "message": "Successfully processed FIT file",
            "workout_data": parsed_data
        }
        
    except Exception as e:
        print(f"❌ Error processing FIT file {file.filename}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/upload/proposed_workouts")
async def upload_proposed_workouts(file: UploadFile = File(...)):
    try:
        print(f"Processing proposed workouts file: {file.filename}")
        json_contents = await file.read()
        with open("data/temp/temp_proposed_workouts.json", "wb") as f:
            f.write(json_contents)

        weekly_plan, daily_plans, proposed_workouts = process_proposed_workouts("data/temp/temp_proposed_workouts.json")
        db = WorkoutDatabase()

        existing_weekly_plan = db.get_weekly_plan(weekly_plan.weekNumber)
        if existing_weekly_plan:
            print(f"Weekly plan already exists for weekNumber: {weekly_plan.weekNumber}. Deleting existing data...")
            # Delete existing weekly plan and all associated data
            db.delete_weekly_plan_cascade(weekly_plan.weekNumber)
            print(f"Successfully deleted existing data for week {weekly_plan.weekNumber}")
            
        # Create new weekly plan
        print(f"Creating weekly plan: {weekly_plan.weekNumber}, {weekly_plan.startDate}, {weekly_plan.plannedTSS_min}, {weekly_plan.plannedTSS_max}, {weekly_plan.notes}, FTP: {weekly_plan.ftp}")
        db.create_weekly_plan(
            weekNumber=weekly_plan.weekNumber, 
            startDate=weekly_plan.startDate, 
            plannedTSS_min=weekly_plan.plannedTSS_min, 
            plannedTSS_max=weekly_plan.plannedTSS_max, 
            notes=weekly_plan.notes,
            ftp=weekly_plan.ftp
        )

        for daily_plan in daily_plans:
            print(f"DEBUG: Before creating daily plan - weekNumber: {daily_plan.weekNumber}, dayNumber: {daily_plan.dayNumber}, date: {daily_plan.date}")
            success = db.create_daily_plan(
                weekNumber=daily_plan.weekNumber,
                dayNumber=daily_plan.dayNumber,
                date=daily_plan.date
            )
            if success:
                daily_plan_id = db.get_daily_plan_id(
                    weekNumber=daily_plan.weekNumber,
                    dayNumber=daily_plan.dayNumber,
                    date=daily_plan.date
                )
                daily_plan.id = daily_plan_id or 0
            else:
                raise Exception(f"Failed to save daily plan for {daily_plan.date}")

        print(f"DEBUG: Daily plans after DB: {[dp.__dict__ for dp in daily_plans]}")
        print(f"DEBUG: Proposed workouts before matching: {[(w.name, getattr(w, 'dayNumber', None)) for w in proposed_workouts]}")

        for workout in proposed_workouts:
            # Match using the dataclass field `dayNumber` set during parsing
            daily_plan_id = next(
                (dp.id for dp in daily_plans if dp.dayNumber == getattr(workout, 'dayNumber', None)),
                0
            )
            if daily_plan_id == 0:
                print(f"DEBUG: Failed to match workout {workout.name} with dayNumber {getattr(workout, 'dayNumber', None)}")
                raise Exception(f"No daily plan found for workout {workout.name}")
            workout.dailyPlanId = daily_plan_id

            success = db.create_proposed_workout(
                dailyPlanId=workout.dailyPlanId,
                type=workout.type,
                name=workout.name,
                plannedDuration=workout.plannedDuration,
                plannedTSS_min=workout.plannedTSS_min,
                plannedTSS_max=workout.plannedTSS_max,
                targetRPE_min=workout.targetRPE_min,
                targetRPE_max=workout.targetRPE_max,
                intervals=workout.intervals,
                sections=workout.sections,
                notes=workout.notes
            )
            if not success:
                raise Exception(f"Failed to save proposed workout {workout.name}")
        
        # Generate Zwift workout files for cycling workouts
        zwift_files = []
        try:
            # Find daily plans that have a date
            date_filtered_plans = [dp for dp in daily_plans if dp.date]
            
            if date_filtered_plans:
                # Find earliest and latest dates in the uploaded plans
                start_date = min(dp.date for dp in date_filtered_plans)
                end_date = max(dp.date for dp in date_filtered_plans)
                
                # Generate Zwift workouts for these dates
                # Guard against .env overriding ZWIFT_WORKOUTS_DIR to a Windows path
                _zwd = os.getenv('ZWIFT_WORKOUTS_DIR', '')
                zwift_output_dir = _zwd if _zwd and not _zwd.startswith('C:') else '/app/shareable/zwift_workouts'
                
                # Extract FTP from weekly plan - try explicit FTP field first, then notes as fallback
                ftp = 258  # Default FTP
                try:
                    # First, check for explicit FTP field in weekly plan
                    if weekly_plan.ftp:
                        ftp = weekly_plan.ftp
                        print(f"Using explicit FTP: {ftp}W from weekly plan")
                    elif weekly_plan.notes:
                        # Fallback to parsing FTP from notes
                        notes_data = json.loads(weekly_plan.notes) if isinstance(weekly_plan.notes, str) else weekly_plan.notes
                        if isinstance(notes_data, dict):
                            special_considerations = notes_data.get('specialConsiderations', '')
                            # Look for FTP pattern like "FTP 300W confirmed" or "FTP: 300W"
                            ftp_match = re.search(r'FTP[:\s]*(\d+)W?', special_considerations, re.IGNORECASE)
                            if ftp_match:
                                ftp = int(ftp_match.group(1))
                                print(f"Extracted FTP: {ftp}W from weekly plan notes (fallback)")
                except Exception as e:
                    print(f"Could not extract FTP from weekly plan: {e}, using default {ftp}W")
                
                # Use the module to generate files
                from ..utils.zwift_workout_generator import generate_zwift_workouts_from_db
                generated_files = generate_zwift_workouts_from_db(
                    db_connection=db,
                    start_date=start_date,
                    end_date=end_date,
                    ftp=ftp,
                    output_dir=zwift_output_dir,
                    week_number=weekly_plan.weekNumber
                )
                
                if generated_files:
                    zwift_files = generated_files
                    print(f"Generated {len(generated_files)} Zwift workout files")
        except Exception as e:
            print(f"Error generating Zwift workouts: {str(e)}")
            # Continue even if Zwift generation fails - we don't want to fail the whole upload

        response_message = "Successfully processed proposed workouts"
        if zwift_files:
            response_message += f" and generated {len(zwift_files)} Zwift workout files"
            
        return {
            "message": response_message,
            "zwift_files": zwift_files
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error: {str(e)}")
    
@app.get("/proposed_workouts/week")
async def get_proposed_workouts_week(start_date: str, end_date: str):
    """Get all proposed workouts for a specific week"""
    try:
        db = WorkoutDatabase()
        result = db.get_proposed_workouts_for_week(start_date, end_date)
        return result
    except Exception as e:
        print(f"Error retrieving proposed workouts: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving proposed workouts: {str(e)}"
        )


@app.get("/athlete/settings")
async def get_athlete_settings(athlete_id: Optional[str] = 'default'):
    """Get persisted athlete settings (ftp, hr_zones, power_zones)."""
    try:
        db = WorkoutDatabase()
        aid = athlete_id or 'default'
        settings = db.load_athlete_settings(aid)
        if settings is None:
            return {"athlete_id": aid, "settings": {}}
        return {"athlete_id": aid, "settings": settings}
    except Exception as e:
        print(f"Error getting athlete settings: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


async def _read_body(request: Request) -> Dict[str, Any]:
    """JSON (React) or form fields (Streamlit) — both are accepted."""
    if "application/json" in (request.headers.get("content-type") or ""):
        body = await request.json()
        return body if isinstance(body, dict) else {}
    return dict(await request.form())


def _maybe_json(value: Any) -> Any:
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON")
    return value


@app.post("/athlete/settings")
async def save_athlete_settings(request: Request):
    """Save athlete settings. JSON `{"athlete_id"?, "settings": {...}}` or the
    legacy form fields `athlete_id` + `settings` (JSON string)."""
    body = await _read_body(request)
    settings_obj = _maybe_json(body.get("settings"))
    if not isinstance(settings_obj, dict):
        raise HTTPException(status_code=400, detail="`settings` object is required")
    aid = body.get("athlete_id") or "default"
    if not WorkoutDatabase().save_athlete_settings(aid, settings_obj):
        raise HTTPException(status_code=500, detail="Failed to persist athlete settings")
    return {"message": "Athlete settings saved", "athlete_id": aid}


@app.get("/zwift/generate_workouts")
async def generate_zwift_workouts(start_date: str, end_date: str, output_dir: Optional[str] = None, ftp: int = 258, week_number: Optional[int] = None):
    """Generate Zwift workout files for all cycling workouts in the date range"""
    try:
        from ..utils.zwift_workout_generator import generate_zwift_workouts_from_db
        
        db = WorkoutDatabase()
        
        # Set default output directory to the Zwift workouts directory if not specified
        if not output_dir:
            # Guard against .env overriding ZWIFT_WORKOUTS_DIR to a Windows path
            _zwd = os.getenv('ZWIFT_WORKOUTS_DIR', '')
            output_dir = _zwd if _zwd and not _zwd.startswith('C:') else '/app/shareable/zwift_workouts'
        
        # Extract FTP from weekly plan - try explicit FTP field first, then notes as fallback
        extracted_ftp = ftp  # Use provided FTP as ultimate fallback
        try:
            proposed_workouts_data = db.get_proposed_workouts_for_week(start_date, end_date)
            weekly_plan = proposed_workouts_data.get('weekly_plan', {})
            
            # First, check for explicit FTP field in weekly plan
            if weekly_plan and weekly_plan.get('ftp'):
                extracted_ftp = weekly_plan.get('ftp')
                print(f"Using explicit FTP: {extracted_ftp}W from weekly plan")
            elif weekly_plan and weekly_plan.get('notes'):
                # Fallback to parsing FTP from notes
                notes = weekly_plan['notes']
                notes_data = json.loads(notes) if isinstance(notes, str) else notes
                if isinstance(notes_data, dict):
                    special_considerations = notes_data.get('specialConsiderations', '')
                    # Look for FTP pattern like "FTP 300W confirmed" or "FTP: 300W"
                    ftp_match = re.search(r'FTP[:\s]*(\d+)W?', special_considerations, re.IGNORECASE)
                    if ftp_match:
                        extracted_ftp = int(ftp_match.group(1))
                        print(f"Extracted FTP: {extracted_ftp}W from weekly plan notes (fallback)")
        except Exception as e:
            print(f"Could not extract FTP from weekly plan: {e}, using provided FTP {extracted_ftp}W")
        
        # If week number wasn't provided, try to get it from the database
        if week_number is None:
            # Try to get the weekly plan from the database
            if weekly_plan and 'weekNumber' in weekly_plan:
                week_number = weekly_plan.get('weekNumber')
                print(f"Using week number from database: {week_number}")
        
        # Create weekly folders within the output directory
        generated_files = generate_zwift_workouts_from_db(
            db_connection=db,
            start_date=start_date,
            end_date=end_date,
            ftp=extracted_ftp,
            output_dir=output_dir,
            week_number=week_number
        )
        
        if generated_files:
            return {
                "message": f"Generated {len(generated_files)} Zwift workout files",
                "files": generated_files
            }
        else:
            return {
                "message": "No Zwift workout files were generated. No cycling workouts found for the specified date range."
            }
    except Exception as e:
        print(f"Error generating Zwift workouts: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error generating Zwift workouts: {str(e)}"
        )

@app.post("/workout/performance")
async def save_workout_performance(request: Request):
    """Save logged performance (sets/reps/weights) for a workout.
    JSON or form: workout_id, workout_date, actual_duration, performance_data."""
    body = await _read_body(request)
    try:
        workout_id = int(body["workout_id"])
        workout_date = str(body["workout_date"])
        actual_duration = int(float(body.get("actual_duration") or 0))
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=400, detail="workout_id and workout_date are required")
    perf = _maybe_json(body.get("performance_data")) or {}
    if not WorkoutDatabase().save_workout_performance(
            workout_id=workout_id, workout_date=workout_date,
            actual_duration=actual_duration, performance_data=perf):
        raise HTTPException(status_code=500, detail="Failed to save performance data")
    return {"message": "Performance data saved successfully"}

@app.get("/workout/performance")
async def get_workout_performance(workout_id: int, workout_date: str):
    """Get performance data for a specific workout"""
    try:
        db = WorkoutDatabase()
        performance_data = db.get_workout_performance(workout_id, workout_date)
        
        if performance_data:
            return performance_data
        else:
            return {"message": "No performance data found for this workout"}
    except Exception as e:
        print(f"Error retrieving workout performance: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving workout performance data: {str(e)}"
        )

@app.get("/workouts/week")
async def get_workouts_week(start_date: str, end_date: str):
    """Get all completed and proposed workouts for a specific week"""
    try:
        db = WorkoutDatabase()
        result = db.get_all_workouts_for_week(start_date, end_date)
        # Unconfirmed workouts carry the review step's suggestion, so the calendar
        # shows them against the plan before the Sunday review.
        from src.utils.week_review import review_week
        suggested = {}
        for row in review_week(start_date)["workouts"]:
            if row["status"] == "suggested" and row.get("match"):
                suggested[row["id"]] = row["match"]
        for w in result["completed_workouts"]:
            m = suggested.get(w.get("id"))
            if m and not w.get("proposed_workout_id"):
                w["suggested_proposed_workout_id"] = m.get("proposed_workout_id")
                w["suggested_label"] = None if m.get("proposed_workout_id") else m.get("name")
        return result
    except Exception as e:
        print(f"Error retrieving workouts: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving workouts: {str(e)}"
        )