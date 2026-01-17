"""
AI-Powered FIT File Analysis Module

Uses Gemini AI to generate workout insights and track personal bests.
Dynamically discovers available free models for resilience.
"""

import os
from typing import Dict, Any, Optional, List
from datetime import datetime
import numpy as np
from pathlib import Path
from .fit_parser import FitParser
import google.generativeai as genai
from google.api_core import exceptions
from dotenv import load_dotenv

# Load environment variables from project root
load_dotenv(Path(__file__).parent.parent.parent / '.env')


class FitFileAnalyzer:
    """Analyzes cycling workout data from FIT files using AI"""
    
    # Static fallback models (used if dynamic discovery fails)
    FALLBACK_MODELS = [
        'gemini-1.5-flash-002',
        'gemini-1.5-flash',
        'gemini-1.5-flash-8b',
        'gemini-2.0-flash-exp',
        'gemini-1.5-pro',
        'gemini-pro',
    ]
    
    def __init__(self, gemini_api_key: Optional[str] = None, use_dynamic_models: bool = True):
        """
        Initialize the analyzer with Gemini API
        
        Args:
            gemini_api_key: Optional Gemini API key. If not provided, uses GEMINI_API_KEY env var
            use_dynamic_models: If True, dynamically discover free models. If False, use static list.
        """
        self.parser = FitParser()
        
        # Initialize Gemini
        api_key = gemini_api_key or os.environ.get('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("Gemini API key required. Set GEMINI_API_KEY environment variable.")
        
        genai.configure(api_key=api_key)
        
        # Get model list (dynamic or static)
        self.use_dynamic_models = use_dynamic_models
        self._models_cache: Optional[List[str]] = None
        
    @property
    def MODELS(self) -> List[str]:
        """
        Get list of models to try.
        
        Uses dynamic discovery if enabled, otherwise returns static fallback.
        Caches the result to avoid repeated API calls.
        """
        if self._models_cache is not None:
            return self._models_cache
        
        if self.use_dynamic_models:
            try:
                from .gemini_model_discovery import get_best_free_models
                print("🔍 Using dynamic model discovery...")
                models = get_best_free_models(max_models=7, force_refresh=False)
                self._models_cache = models
                return models
            except Exception as e:
                print(f"⚠️  Dynamic model discovery failed: {e}")
                print("📋 Falling back to static model list")
        
        # Use static fallback
        self._models_cache = self.FALLBACK_MODELS
        return self.FALLBACK_MODELS
        
    def analyze_workout(self, fit_file_content: bytes, athlete_ftp: Optional[float] = None,
                       athlete_notes: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Analyze a workout from FIT file data
        
        Args:
            fit_file_content: Raw bytes of the FIT file
            athlete_ftp: Optional FTP value for power calculations
            athlete_notes: Optional notes from the athlete about the workout
            
        Returns:
            Dictionary containing parsed metrics, AI analysis, and detected personal bests
        """
        # Parse the FIT file
        parsed_data = self.parser.parse_fit_file(fit_file_content, athlete_ftp)
        
        if not parsed_data:
            return None
        
        return self.analyze_workout_from_parsed_data(parsed_data, athlete_ftp, athlete_notes)
    
    def _get_csv_tss_for_workout(self, parsed_data: Dict[str, Any]) -> Optional[float]:
        """
        Get TSS from workouts CSV table - more reliable than FIT file TSS.
        Matches by workout_day and looks for actual_tss in metrics.
        
        Returns:
            TSS value from CSV or None if not found
        """
        from pathlib import Path
        import sqlite3
        import json
        import ast
        
        try:
            # Get workout date
            workout_date = parsed_data.get('workout_date')
            if not workout_date and 'start_time' in parsed_data:
                from datetime import datetime
                start_time = parsed_data['start_time']
                if isinstance(start_time, str):
                    workout_date = start_time[:10]
            
            if not workout_date:
                return None
            
            # Connect to database
            db_path = Path(__file__).parent.parent.parent / 'data' / 'fitness_data.db'
            conn = sqlite3.connect(str(db_path))
            c = conn.cursor()
            
            # Query workouts table for this date
            c.execute('''
                SELECT workout_data
                FROM workouts
                WHERE workout_day = ?
                  AND json_extract(workout_data, '$.type') = 'Bike'
                LIMIT 1
            ''', (workout_date,))
            
            row = c.fetchone()
            conn.close()
            
            if not row:
                return None
            
            # Parse workout_data JSON
            workout_data = json.loads(row[0])
            
            # Extract metrics (stored as string representation of dict)
            metrics_str = workout_data.get('metrics', '{}')
            if isinstance(metrics_str, str):
                metrics = ast.literal_eval(metrics_str)
            else:
                metrics = metrics_str
            
            # Get actual_tss
            tss = metrics.get('actual_tss')
            return float(tss) if tss else None
            
        except Exception as e:
            print(f"⚠️  Could not retrieve CSV TSS: {e}")
            return None
    
    def analyze_workout_from_parsed_data(self, parsed_data: Dict[str, Any], 
                                        athlete_ftp: Optional[float] = None,
                                        athlete_notes: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Analyze a workout from already-parsed FIT data (useful when database stores JSON)
        
        Args:
            parsed_data: Already-parsed workout data (dict from JSON)
            athlete_ftp: Optional FTP value for power calculations  
            athlete_notes: Optional notes from the athlete about the workout
            
        Returns:
            Dictionary containing parsed metrics, AI analysis, and detected personal bests
        """
        if not parsed_data:
            return None
        
        # Normalize data structure - stored JSON may have different field names
        # Convert duration_hours to duration_seconds if needed
        if 'duration_hours' in parsed_data and 'duration_seconds' not in parsed_data:
            parsed_data['duration_seconds'] = parsed_data['duration_hours'] * 3600
        
        # Ensure metrics.duration is in minutes if present
        if 'metrics' not in parsed_data:
            parsed_data['metrics'] = {}
        if 'duration' not in parsed_data['metrics'] and 'duration_hours' in parsed_data:
            parsed_data['metrics']['duration'] = parsed_data['duration_hours'] * 60
        
        # Get TSS from CSV data (workouts table) if available - this is most accurate
        # FIT file TSS from compressed .fit.gz files is unreliable
        csv_tss = self._get_csv_tss_for_workout(parsed_data)
        
        if csv_tss and csv_tss > 0:
            # Use CSV TSS - most reliable
            print(f"✓ Using CSV TSS: {csv_tss:.1f}")
            if 'power_metrics' not in parsed_data:
                parsed_data['power_metrics'] = {}
            parsed_data['power_metrics']['tss'] = csv_tss
            parsed_data['metrics']['tss'] = csv_tss
        else:
            # Fall back to FIT TSS only if reasonable (> 10)
            power_metrics = parsed_data.get('power_metrics', {})
            fit_tss = power_metrics.get('tss', 0)
            
            if fit_tss > 10:
                # FIT TSS looks reasonable, use it
                print(f"✓ Using FIT TSS: {fit_tss:.1f}")
                parsed_data['metrics']['tss'] = fit_tss
            else:
                # Bad or missing TSS - will affect workout matching
                print(f"⚠️  No reliable TSS available (FIT: {fit_tss:.4f}, CSV: {csv_tss})")
                parsed_data['metrics']['tss'] = None
        
        # Detect sport type
        sport = parsed_data.get('sport', 'cycling').lower()
        is_cycling = sport in ['cycling', 'bike', 'biking']
        
        # Non-cycling workouts get simpler analysis (no power metrics, just basic summary)
        if not is_cycling:
            print(f"ℹ️  Analyzing non-cycling workout (sport: {sport})")
            # Create basic analysis for non-cycling
            duration_hours = parsed_data.get('duration_hours', 0)
            distance = parsed_data.get('distance_km', 0)
            avg_hr = parsed_data.get('heart_rate_data', {}).get('average_hr', 0)
            max_hr = parsed_data.get('heart_rate_data', {}).get('max_hr', 0)
            
            ai_analysis = f"""### {sport.title()} Workout Summary

**Duration:** {duration_hours:.2f} hours ({duration_hours * 60:.0f} minutes)
**Distance:** {distance:.2f} km
**Heart Rate:** Avg {avg_hr:.0f} bpm, Max {max_hr:.0f} bpm

This {sport} workout has been logged. Detailed AI analysis is currently only available for cycling workouts.
"""
            
            return {
                'parsed_data': parsed_data,
                'peak_efforts': {},
                'ai_analysis': ai_analysis,
                'analyzed_at': datetime.now().isoformat()
            }
        
        # Get workout date for finding proposed workout
        # Extract date from start_time if workout_date not present
        workout_date = parsed_data.get('workout_date')
        if not workout_date:
            start_time_str = parsed_data.get('start_time')
            if start_time_str:
                try:
                    from pathlib import Path
                    import pytz
                    # Parse start time (UTC) and convert to PST
                    start_time = datetime.fromisoformat(start_time_str)
                    if start_time.tzinfo is None:
                        start_time = pytz.UTC.localize(start_time)
                    pst = pytz.timezone('America/Los_Angeles')
                    pst_time = start_time.astimezone(pst)
                    workout_date = pst_time.strftime('%Y-%m-%d')
                    print(f"Extracted workout date from start_time: {workout_date}")
                except Exception as e:
                    print(f"Error extracting date from start_time: {e}")
                    workout_date = datetime.now().strftime('%Y-%m-%d')
            else:
                workout_date = datetime.now().strftime('%Y-%m-%d')
        
        # Try to find best matching proposed workout (allows for timezone issues)
        proposed_workout = self._find_best_matching_workout(parsed_data, workout_date)
        
        # Continue with analysis even if no proposed workout found
        # (historical workouts may not have proposed workouts)
        if not proposed_workout:
            print(f"ℹ️ No proposed workout found - analyzing as standalone workout")
        
        # Detect peak efforts (passing proposed workout for custom intervals if available)
        peak_efforts = self._detect_peak_efforts(parsed_data, proposed_workout)
        
        # Detect intervals automatically
        intervals_data = self._detect_intervals(parsed_data, athlete_ftp)
        
        # Generate AI analysis (pass intervals and matched proposed workout for context)
        ai_analysis = self._generate_ai_analysis(
            parsed_data,
            peak_efforts,
            athlete_notes,
            intervals_data,
            proposed_workout=proposed_workout
        )
        
        return {
            'parsed_data': parsed_data,
            'peak_efforts': peak_efforts,
            'intervals': intervals_data,
            'ai_analysis': ai_analysis,
            'analyzed_at': datetime.now().isoformat()
        }
    
    def _detect_peak_efforts(self, parsed_data: Dict[str, Any], proposed_workout: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, float]]:
        """
        Detect peak power efforts across multiple time windows
        
        Args:
            parsed_data: Output from FitParser.parse_fit_file()
            proposed_workout: Optional proposed workout to extract custom interval durations
            
        Returns:
            Dictionary mapping effort duration to {power, heart_rate, timestamp}
        """
        power_metrics = parsed_data.get('power_metrics')
        hr_metrics = parsed_data.get('hr_metrics')
        
        if not power_metrics or 'power_series' not in power_metrics:
            return {}
        
        power_series = np.array(power_metrics['power_series'])
        hr_series = None
        if hr_metrics and 'hr_series' in hr_metrics:
            hr_series = np.array(hr_metrics.get('hr_series', []))
        
        # Standard time windows to analyze (in seconds)
        windows = {
            '30s': 30,
            '1min': 60,
            '3min': 180,
            '5min': 300,
            '10min': 600,
            '20min': 1200,
            '45min': 2700,
            '60min': 3600
        }
        
        # Add custom intervals from proposed workout
        if proposed_workout and 'intervals' in proposed_workout:
            for interval in proposed_workout['intervals']:
                interval_name = interval.get('name', '').upper()
                # Check if this is a work interval (not warmup, cooldown, or recovery)
                is_work_interval = any(keyword in interval_name for keyword in [
                    'THRESHOLD', 'VO2MAX', 'TEMPO', 'SWEETSPOT', 'BLOCK', 
                    'INTERVAL', 'WORK', 'EFFORT', 'REP'
                ]) and not any(keyword in interval_name for keyword in [
                    'WARMUP', 'WARM-UP', 'WARM UP', 'COOLDOWN', 'COOL-DOWN', 
                    'COOL DOWN', 'RECOVERY'
                ])
                
                if is_work_interval:
                    duration_seconds = interval.get('duration', 0)
                    duration_minutes = duration_seconds // 60
                    
                    # Add this duration if it's substantial and not already covered
                    if duration_minutes >= 2 and duration_seconds not in windows.values():
                        label = f"{duration_minutes}min"
                        if label not in windows:
                            windows[label] = duration_seconds
                            print(f"DEBUG: Added custom interval duration: {label} ({duration_seconds}s) from '{interval.get('name')}'")
        
        peak_efforts = {}
        
        for label, window_size in windows.items():
            if len(power_series) < window_size:
                continue
            
            # Calculate rolling average for this window
            rolling_avg = np.convolve(power_series, np.ones(window_size)/window_size, mode='valid')
            
            if len(rolling_avg) > 0:
                max_avg_power = float(np.max(rolling_avg))
                max_index = int(np.argmax(rolling_avg))
                
                effort_data = {
                    'power': max_avg_power,
                    'index': max_index,
                    'duration_seconds': window_size
                }
                
                # Add average HR for this effort window if available
                if hr_series is not None and len(hr_series) > max_index + window_size:
                    hr_window = hr_series[max_index:max_index + window_size]
                    # Filter out zeros/invalid readings
                    valid_hr = hr_window[hr_window > 0]
                    if len(valid_hr) > 0:
                        effort_data['heart_rate'] = float(np.mean(valid_hr))
                
                peak_efforts[label] = effort_data
        
        return peak_efforts
    
    def _load_proposed_workout(self, workout_date: str) -> Optional[Dict[str, Any]]:
        """
        Load the proposed workout for a given date from the database
        
        Args:
            workout_date: Date string in YYYY-MM-DD format
            
        Returns:
            Proposed workout dict or None if not found
        """
        from pathlib import Path
        import json
        import sqlite3
        
        try:
            # Connect to database
            db_path = Path(__file__).parent.parent.parent / 'data' / 'fitness_data.db'
            conn = sqlite3.connect(str(db_path))
            c = conn.cursor()
            
            # Query for the proposed workout on this date
            c.execute('''
                SELECT pw.name, pw.type, pw.plannedDuration,
                       pw.plannedTSS_min, pw.plannedTSS_max,
                       pw.targetRPE_min, pw.targetRPE_max,
                       pw.intervals, pw.sections, pw.notes
                FROM proposed_workouts pw
                JOIN daily_plans dp ON pw.dailyPlanId = dp.id
                WHERE dp.date = ? AND pw.type = 'bike'
                LIMIT 1
            ''', (workout_date,))
            
            row = c.fetchone()
            conn.close()
            
            if not row:
                print(f"No proposed bike workout found for {workout_date}")
                return None
            
            # Parse the workout data
            workout = {
                'name': row[0],
                'type': row[1],
                'plannedDuration': row[2],
                'plannedTSS': {
                    'min': row[3],
                    'max': row[4]
                },
                'targetRPE': {
                    'min': row[5],
                    'max': row[6]
                },
                'intervals': json.loads(row[7]) if row[7] else [],
                'sections': json.loads(row[8]) if row[8] else [],
                'notes': row[9]
            }
            
            print(f"✓ Found proposed workout from database: {workout['name']}")
            return workout
            
        except Exception as e:
            print(f"Error loading proposed workout from database: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _detect_intervals(self, parsed_data: Dict[str, Any], athlete_ftp: Optional[float] = None) -> Dict[str, Any]:
        """
        Automatically detect intervals from workout power data
        
        Args:
            parsed_data: Output from FitParser.parse_fit_file()
            athlete_ftp: Athlete's FTP in watts
            
        Returns:
            Dictionary with detected intervals or empty dict if detection fails
        """
        try:
            from .interval_detector import IntervalDetector
            from .interval_classifier import IntervalClassifier
            
            # Get power data
            power_metrics = parsed_data.get('power_metrics')
            if not power_metrics or 'power_series' not in power_metrics:
                print("⊘ No power data available for interval detection")
                return {}
            
            power_series = power_metrics['power_series']
            
            # Get FTP
            if not athlete_ftp:
                athlete_ftp = power_metrics.get('ftp', 300)  # Default to 300 if not available
            
            # Get optional HR and cadence data
            hr_series = None
            hr_metrics = parsed_data.get('hr_metrics')
            if hr_metrics and 'hr_series' in hr_metrics:
                hr_series = hr_metrics['hr_series']
            
            cadence_series = None
            if 'cadence_series' in parsed_data:
                cadence_series = parsed_data['cadence_series']
            
            # Detect intervals
            print(f"🔍 Detecting intervals with FTP={int(athlete_ftp)}W...")
            detector = IntervalDetector(ftp=int(athlete_ftp))
            intervals_data = detector.detect_intervals(
                power_stream=power_series,
                hr_stream=hr_series,
                cadence_stream=cadence_series
            )
            
            # Classify intervals
            classifier = IntervalClassifier(ftp=int(athlete_ftp))
            classified_data = classifier.classify_intervals(intervals_data)
            
            # Generate description
            description = classifier.describe_workout_structure(classified_data)
            classified_data['description'] = description
            
            print(f"✓ Detected {classified_data['interval_count']} intervals: {description}")
            
            return classified_data
            
        except Exception as e:
            print(f"⚠️  Interval detection failed: {e}")
            import traceback
            traceback.print_exc()
            return {}
    
    def _find_best_matching_workout(self, parsed_data: Dict[str, Any], workout_date: str, 
                                   date_window_days: int = 7, 
                                   used_workout_ids: Optional[set] = None) -> Optional[Dict[str, Any]]:
        """
        Find the best matching proposed workout based on TSS, duration, and workout characteristics.
        Searches within a date window (default ±2 days) to account for timezone issues.
        Handles multiple workouts per day by tracking which proposed workouts are already matched.
        
        Args:
            parsed_data: Parsed FIT file data
            workout_date: Original workout date
            date_window_days: Number of days before/after to search
            used_workout_ids: Set of (date, name) tuples already matched to avoid duplicates
            
        Returns:
            Best matching proposed workout dict or None
        """
        from pathlib import Path
        import json
        import sqlite3
        from datetime import datetime, timedelta
        
        try:
            # Extract actual workout characteristics
            actual_tss = parsed_data.get('power_metrics', {}).get('tss', 0)
            actual_duration_min = parsed_data.get('duration_seconds', 0) / 60
            actual_np = parsed_data.get('power_metrics', {}).get('normalized_power', 0)
            
            if not actual_tss or not actual_duration_min:
                print("⚠️  Missing TSS or duration - cannot match workout")
                return None
            
            # Calculate date range for search
            base_date = datetime.strptime(workout_date, '%Y-%m-%d')
            start_date = (base_date - timedelta(days=date_window_days)).strftime('%Y-%m-%d')
            end_date = (base_date + timedelta(days=date_window_days)).strftime('%Y-%m-%d')
            
            # Connect to database
            db_path = Path(__file__).parent.parent.parent / 'data' / 'fitness_data.db'
            conn = sqlite3.connect(str(db_path))
            c = conn.cursor()
            
            # Query for proposed bike workouts in date range
            c.execute('''
                SELECT dp.date, pw.name, pw.type, pw.plannedDuration,
                       pw.plannedTSS_min, pw.plannedTSS_max,
                       pw.targetRPE_min, pw.targetRPE_max,
                       pw.intervals, pw.sections, pw.notes
                FROM proposed_workouts pw
                JOIN daily_plans dp ON pw.dailyPlanId = dp.id
                WHERE dp.date >= ? AND dp.date <= ? AND pw.type = 'bike'
            ''', (start_date, end_date))
            
            candidates = c.fetchall()
            conn.close()
            
            if not candidates:
                print(f"No proposed bike workouts found in date range {start_date} to {end_date}")
                return None
            
            print(f"Found {len(candidates)} candidate workouts in date range")
            
            # Score each candidate
            best_score = 0
            best_match = None
            
            # Track used workouts to prevent duplicates
            if used_workout_ids is None:
                used_workout_ids = set()
            
            actual_title = (parsed_data.get('title') or '').lower()
            title_keywords = ['race', 'warmup', 'pre', 'recovery', 'zone 2', 'endurance', 'tempo', 'threshold', 'vo2']

            for row in candidates:
                date, name, wtype, planned_dur, tss_min, tss_max, rpe_min, rpe_max, intervals, sections, notes = row
                name_lower = (name or '').lower()
                
                # Skip if this workout already matched to another file on same day
                workout_id = (date, name)
                if workout_id in used_workout_ids:
                    continue
                
                # Calculate match score (0-100)
                # For multi-workout days: TSS+Duration matter more than exact date
                # Priority: TSS (40 pts) > Duration (40 pts) > Date (20 pts)
                score = 0
                
                cand_date = datetime.strptime(date, '%Y-%m-%d')

                # Date proximity (20 points max) - keep, but don't force same-day
                days_diff = abs((cand_date - base_date).days)
                if days_diff == 0:
                    score += 20  # Same day
                elif days_diff == 1:
                    score += 10  # 1 day off
                elif days_diff == 2:
                    score += 5   # 2 days off

                # Same-week bonus (10 points) - prefer workouts from the same training week
                if cand_date.isocalendar()[:2] == base_date.isocalendar()[:2]:
                    score += 10

                # Title keyword match (15 points max) - strong signal when available
                if actual_title:
                    for kw in title_keywords:
                        if kw in actual_title and kw in name_lower:
                            score += 15
                            break
                
                # Duration match (40 points max) - CRITICAL for distinguishing workouts
                if planned_dur:
                    dur_diff_pct = abs(actual_duration_min - planned_dur) / planned_dur * 100
                    if dur_diff_pct <= 5:
                        score += 40  # Within 5% - excellent match
                    elif dur_diff_pct <= 10:
                        score += 35  # Within 10%
                    elif dur_diff_pct <= 20:
                        score += 25  # Within 20%
                    elif dur_diff_pct <= 30:
                        score += 15  # Within 30%
                    elif dur_diff_pct <= 50:
                        score += 5   # Within 50%
                
                # TSS match (40 points max) - CRITICAL for workout intensity
                if tss_min and tss_max:
                    # Use TSS range instead of average for better matching
                    if actual_tss >= tss_min and actual_tss <= tss_max:
                        score += 40  # Within range - perfect
                    else:
                        # Calculate distance from range
                        if actual_tss < tss_min:
                            tss_diff_pct = (tss_min - actual_tss) / tss_min * 100
                        else:
                            tss_diff_pct = (actual_tss - tss_max) / tss_max * 100
                        
                        if tss_diff_pct <= 10:
                            score += 35  # Just outside range
                        elif tss_diff_pct <= 20:
                            score += 25  # Within 20%
                        elif tss_diff_pct <= 40:
                            score += 15  # Within 40%
                        elif tss_diff_pct <= 60:
                            score += 8   # Within 60%
                
                print(f"  {date} - {name}: score={score} (TSS {tss_min}-{tss_max}, {planned_dur}min)")
                
                if score > best_score:
                    best_score = score
                    best_match = {
                        'date': date,
                        'name': name,
                        'type': wtype,
                        'plannedDuration': planned_dur,
                        'plannedTSS': {
                            'min': tss_min,
                            'max': tss_max
                        },
                        'targetRPE': {
                            'min': rpe_min,
                            'max': rpe_max
                        },
                        'intervals': json.loads(intervals) if intervals else [],
                        'sections': json.loads(sections) if sections else [],
                        'notes': notes
                    }
            
            # Only return if score is reasonable (>= 45 points - requires same-day with some duration/TSS match)
            if best_match and best_score >= 45:
                # Mark this workout as used to prevent duplicate matching on same day
                workout_id = (best_match['date'], best_match['name'])
                if used_workout_ids is not None:
                    used_workout_ids.add(workout_id)
                
                print(f"✓ Best match (score={best_score}): {best_match['name']} on {best_match['date']}")
                return best_match
            elif best_match:
                print(f"⚠️  Best match score too low ({best_score}), skipping analysis")
                return None
            else:
                print("No matching proposed workout found")
                return None
            
        except Exception as e:
            print(f"Error finding matching workout: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _analyze_prescribed_intervals(self, parsed_data: Dict[str, Any], proposed_workout: Optional[Dict[str, Any]]) -> str:
        """
        Analyze actual execution for each prescribed interval in the workout.
        Returns formatted text showing interval-by-interval performance.
        """
        if not proposed_workout or 'intervals' not in proposed_workout:
            return ""
        
        power_metrics = parsed_data.get('power_metrics', {})
        hr_metrics = parsed_data.get('hr_metrics', {})
        time_series = parsed_data.get('time_series', {})
        
        power_series = power_metrics.get('power_series', [])
        hr_series = hr_metrics.get('hr_series', [])
        cadence_series = time_series.get('cadence', [])
        
        if not power_series:
            return ""
        
        intervals = proposed_workout.get('intervals', [])
        analysis_lines = []
        current_time = 0
        
        for idx, interval in enumerate(intervals, 1):
            interval_name = interval.get('name', f'Interval {idx}')
            duration = interval.get('duration', 0)
            
            if duration == 0:
                continue
            
            # Extract data for this time window
            start_idx = current_time
            end_idx = min(current_time + duration, len(power_series))
            
            if start_idx >= len(power_series):
                break
            
            # Calculate averages for this interval
            interval_power = power_series[start_idx:end_idx]
            interval_hr = hr_series[start_idx:end_idx] if start_idx < len(hr_series) else []
            interval_cadence = cadence_series[start_idx:end_idx] if start_idx < len(cadence_series) else []
            
            # Filter out zeros and calculate stats
            valid_power = [p for p in interval_power if p > 0]
            valid_hr = [h for h in interval_hr if h is not None and h > 0]
            valid_cadence = [c for c in interval_cadence if c is not None and c > 0]
            
            avg_power = np.mean(valid_power) if valid_power else 0
            avg_hr = np.mean(valid_hr) if valid_hr else 0
            avg_cadence = np.mean(valid_cadence) if valid_cadence else 0
            
            # Get prescribed targets
            power_target = interval.get('powerTarget', {})
            cadence_target = interval.get('cadenceTarget', {})
            
            # Format power target
            power_target_str = "N/A"
            if isinstance(power_target, dict):
                if power_target.get('type') == 'range':
                    power_target_str = f"{power_target.get('min', 0)}-{power_target.get('max', 0)}W"
                elif power_target.get('type') == 'watts':
                    power_target_str = f"{power_target.get('value', 0)}W"
                elif power_target.get('type') == 'percent_ftp':
                    power_target_str = f"{power_target.get('value', 0)}% FTP"
                elif 'start' in power_target and 'end' in power_target:
                    start_val = power_target['start'].get('value', 0)
                    end_val = power_target['end'].get('value', 0)
                    power_target_str = f"{start_val}-{end_val}% FTP ramp"
            
            # Format cadence target
            cadence_target_str = "N/A"
            if isinstance(cadence_target, dict):
                cad_min = cadence_target.get('min', 0)
                cad_max = cadence_target.get('max', 0)
                if cad_min and cad_max:
                    cadence_target_str = f"{cad_min}-{cad_max} rpm"
            
            # Format time window
            start_min = current_time // 60
            end_min = (current_time + duration) // 60
            time_str = f"Minutes {start_min}-{end_min}"
            
            # Build the interval analysis line
            analysis_lines.append(
                f"\n{interval_name} ({duration//60}min {duration%60}s) - {time_str}:\n"
                f"  Prescribed: {power_target_str}, Cadence: {cadence_target_str}\n"
                f"  Actual: {avg_power:.0f}W avg, {avg_hr:.0f} bpm avg, {avg_cadence:.0f} rpm avg"
            )
            
            current_time += duration
        
        if analysis_lines:
            return "\n📊 INTERVAL-BY-INTERVAL EXECUTION:\n" + "".join(analysis_lines) + "\n"
        return ""
    
    def _generate_ai_analysis(self, parsed_data: Dict[str, Any], 
                             peak_efforts: Dict[str, Dict[str, float]],
                             athlete_notes: Optional[str] = None,
                             intervals_data: Optional[Dict] = None,
                             proposed_workout: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate AI-powered workout analysis using Gemini
        
        Args:
            parsed_data: Parsed FIT file data
            peak_efforts: Detected peak efforts
            athlete_notes: Optional notes from athlete
            intervals_data: Optional detected intervals data
            proposed_workout: Optional matched proposed workout to use in prompt
        """
        power_metrics = parsed_data.get('power_metrics', {})
        hr_metrics = parsed_data.get('hr_metrics', {})
        duration_hours = parsed_data.get('duration_hours', 0)
        
        # Format peak efforts for prompt
        peak_efforts_text = "\n".join([
            f"  - {label}: {data['power']:.0f}W"
            for label, data in peak_efforts.items()
        ])
        
        # Format power zones
        power_zones_text = ""
        if power_metrics and 'zones' in power_metrics:
            power_zones_text = "\n".join([
                f"  - {zone}: {pct:.1f}%"
                for zone, pct in power_metrics['zones'].items()
            ])
        
        # Format HR zones
        hr_zones_text = ""
        if hr_metrics and 'zones' in hr_metrics:
            hr_zones_text = "\n".join([
                f"  - {zone}: {pct:.1f}%"
                for zone, pct in hr_metrics['zones'].items()
            ])
        
        # Calculate HR statistics from actual time series if available
        hr_series_stats = ""
        if hr_metrics and 'hr_series' in hr_metrics:
            hr_series = hr_metrics.get('hr_series', [])
            if hr_series and len(hr_series) > 0:
                import numpy as np
                hr_array = np.array([h for h in hr_series if h and h > 0])  # Filter valid HR
                if len(hr_array) > 0:
                    hr_series_stats = f"""\nHR TIME SERIES ANALYSIS:
- Median HR: {np.median(hr_array):.0f} bpm
- 90th Percentile HR: {np.percentile(hr_array, 90):.0f} bpm
- 10th Percentile HR: {np.percentile(hr_array, 10):.0f} bpm
- HR Variability (std dev): {np.std(hr_array):.1f} bpm"""
        
        # Format detected intervals
        detected_intervals_text = ""
        if intervals_data and intervals_data.get('intervals'):
            detected_intervals_text = "\n\n🤖 AUTO-DETECTED INTERVAL STRUCTURE:\n"
            detected_intervals_text += f"Workout Structure: {intervals_data.get('description', 'Unknown')}\n\n"
            
            for interval in intervals_data['intervals']:
                mins = interval['duration_sec'] // 60
                secs = interval['duration_sec'] % 60
                interval_type = interval['type'].replace('_', ' ').title()
                
                detected_intervals_text += (
                    f"  • {interval_type}: {mins}:{secs:02d} @ "
                    f"{int(interval['avg_power'])}W ({interval['intensity_zone']}, "
                    f"{interval['percent_ftp']:.0f}% FTP)"
                )
                
                if interval.get('avg_hr'):
                    detected_intervals_text += f", HR: {int(interval['avg_hr'])}bpm"
                
                detected_intervals_text += "\n"
            
            # Add summary
            summary = intervals_data.get('summary', {})
            detected_intervals_text += f"\nSummary: {summary.get('work_intervals', 0)} work intervals, "
            detected_intervals_text += f"{summary.get('rest_intervals', 0)} recovery periods\n"
        
        # ENHANCED: Analyze trends throughout the workout
        trend_analysis = self._analyze_workout_trends(parsed_data)
        
        # Load proposed workout for context (use matched workout if provided)
        workout_date = parsed_data.get('start_time', '')[:10] if parsed_data.get('start_time') else None
        proposed_workout_text = ""
        
        if proposed_workout is None and workout_date:
            proposed_workout = self._load_proposed_workout(workout_date)
        if proposed_workout:
            # Format the intervals from the proposed workout with detailed targets
            intervals_text = ""
            workout_type = "UNKNOWN"
            total_work_intervals = 0
            total_recovery_intervals = 0
            
            if 'intervals' in proposed_workout and proposed_workout['intervals']:
                intervals_text = "\n📊 PRESCRIBED INTERVAL STRUCTURE:\n"
                
                for i, interval in enumerate(proposed_workout['intervals'], 1):
                    interval_name = interval.get('name', 'Interval')
                    duration_sec = interval.get('duration', 0)
                    duration_min = duration_sec / 60
                    
                    # Parse power target
                    power_target = interval.get('powerTarget', {})
                    power_str = ""
                    
                    if power_target:
                        if power_target.get('type') == 'range':
                            # Absolute watts range
                            power_str = f"{power_target.get('min', 0)}-{power_target.get('max', 0)}W"
                        elif 'start' in power_target and 'end' in power_target:
                            # Ramp (start to end)
                            start = power_target['start']
                            end = power_target['end']
                            if start.get('type') == 'percent_ftp':
                                power_str = f"{start.get('value', 0)}-{end.get('value', 0)}% FTP"
                            else:
                                power_str = f"{start.get('value', 0)}-{end.get('value', 0)}W"
                        elif power_target.get('type') == 'percent_ftp':
                            power_str = f"{power_target.get('value', 0)}% FTP"
                        else:
                            power_str = f"{power_target.get('value', 0)}W"
                    
                    # Parse cadence target
                    cadence_target = interval.get('cadenceTarget', {})
                    cadence_str = ""
                    if cadence_target:
                        cad_min = cadence_target.get('min', 0)
                        cad_max = cadence_target.get('max', 0)
                        if cad_min and cad_max:
                            cadence_str = f", Cadence: {cad_min}-{cad_max} rpm"

                    interval_lower = interval_name.lower()
                    if any(x in interval_lower for x in ['warmup', 'warm up', 'warm-up']):
                        interval_type = "WARMUP"
                    elif any(x in interval_lower for x in ['cooldown', 'cool down', 'cool-down']):
                        interval_type = "COOLDOWN"
                    elif any(x in interval_lower for x in ['recovery', 'rest', 'easy']):
                        interval_type = "RECOVERY"
                        total_recovery_intervals += 1
                    else:
                        interval_type = "WORK"
                        total_work_intervals += 1
                        # Determine workout type from work intervals
                        if 'threshold' in interval_lower or 'sweetspot' in interval_lower:
                            workout_type = "THRESHOLD/SWEETSPOT"
                        elif 'vo2' in interval_lower or 'vo2max' in interval_lower:
                            workout_type = "VO2MAX"
                        elif 'tempo' in interval_lower:
                            workout_type = "TEMPO"
                        elif 'endurance' in interval_lower or 'aerobic' in interval_lower:
                            workout_type = "ENDURANCE"
                    
                    intervals_text += f"  {i}. [{interval_type}] {interval_name}: "
                    intervals_text += f"{duration_min:.1f}min ({duration_sec}s) @ {power_str}{cadence_str}\n"
                
                # Add workout summary
                intervals_text += f"\n  WORKOUT TYPE: {workout_type}\n"
                intervals_text += f"  Total Work Intervals: {total_work_intervals}\n"
                intervals_text += f"  Total Recovery Intervals: {total_recovery_intervals}\n"
            else:
                # No specific intervals - probably endurance/free ride
                intervals_text = "\n📊 WORKOUT TYPE: STEADY STATE / ENDURANCE (No specific intervals prescribed)\n"
            
            # Format coaching notes
            notes_text = ""
            notes = proposed_workout.get('notes')
            if notes:
                if isinstance(notes, list):
                    notes_text = "\n🎯 COACHING POINTS:\n" + "\n".join([f"  • {note}" for note in notes])
                else:
                    notes_text = f"\n🎯 COACHING POINTS:\n  {notes}\n"
            
            proposed_workout_text = f"""
📋 PLANNED WORKOUT PRESCRIPTION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Workout: {proposed_workout.get('name', 'N/A')}
Planned Duration: {proposed_workout.get('plannedDuration', 'N/A')} minutes
Target TSS: {proposed_workout.get('plannedTSS', {}).get('min', 'N/A')}-{proposed_workout.get('plannedTSS', {}).get('max', 'N/A')}
Target RPE: {proposed_workout.get('targetRPE', {}).get('min', 'N/A')}-{proposed_workout.get('targetRPE', {}).get('max', 'N/A')}/10
{intervals_text}{notes_text}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        if proposed_workout:
            # Build prompt WITH proposed workout context (as reference only)
            prompt = f"""You are an expert cycling coach analyzing workout execution with a supportive, constructive approach.

{proposed_workout_text}
ACTUAL WORKOUT EXECUTION:

WORKOUT METRICS:
Duration: {duration_hours:.2f} hours ({duration_hours * 60:.0f} minutes)
Sport: {parsed_data.get('sport', 'cycling')}

POWER DATA:
- Average Power: {power_metrics.get('average_power', 0):.0f}W
- Normalized Power: {power_metrics.get('normalized_power', 0):.0f}W
- Max Power: {power_metrics.get('max_power', 0):.0f}W
- Intensity Factor: {power_metrics.get('intensity_factor', 0):.2f}
- TSS (actual): {power_metrics.get('tss', 0):.1f}
- FTP (used for calculations): {power_metrics.get('ftp', 0):.0f}W

POWER ZONES (% of workout time):
{power_zones_text or "No power zone data"}

PEAK EFFORTS:
{peak_efforts_text or "No peak efforts detected"}

HEART RATE DATA:
- Average HR: {hr_metrics.get('average_hr', 0):.0f} bpm
- Max HR: {hr_metrics.get('max_hr', 0):.0f} bpm
- Min HR: {hr_metrics.get('min_hr', 0):.0f} bpm{hr_series_stats}

HEART RATE ZONES (% of workout time):
{hr_zones_text or "No heart rate zone data"}
{detected_intervals_text}
{trend_analysis}
ATHLETE NOTES:
{athlete_notes or "No notes provided"}

**CRITICAL ANALYSIS INSTRUCTIONS:**

You must use the AUTO-DETECTED INTERVAL STRUCTURE above as the PRIMARY SOURCE OF TRUTH for what actually happened in the workout. The planned workout is provided only for REFERENCE to understand the athlete's intent.

**IMPORTANT GUIDELINES:**
1. The detected intervals show ACTUAL execution - trust these classifications (work, recovery, vo2max, threshold, etc.)
2. Intervals labeled "vo2max" or "threshold" in detected intervals ARE work intervals that were executed
3. Intervals labeled "recovery" or "rest" ARE actual recovery periods at low power
4. DO NOT assume the athlete failed to execute work intervals - check the detected intervals first
5. Power execution within ±5-10% of targets is NORMAL and GOOD (not a failure)
6. Athletes often modify workouts slightly (shorter warmup, different interval count) - this is acceptable
7. Focus on the QUALITY of execution for the intervals that were actually performed

**SCORING RUBRIC (Rate 1-10):**
- 9-10: Exceptional execution, hit all targets, perfect pacing
- 7-8: Very good execution, minor deviations (±5-10% power, HR appropriate)
- 5-6: Acceptable execution, some struggles but completed core work
- 3-4: Significant struggles, major deviations from targets
- 1-2: Did not execute the workout as intended, abandoned early

**ANALYSIS STRUCTURE:**

1. **EXECUTION SCORE (Rate 1-10 using rubric above)**
   - Based on the AUTO-DETECTED INTERVALS, did athlete complete appropriate work?
   - Were work intervals (vo2max, threshold, tempo, etc.) executed at proper intensity?
   - Were recovery intervals truly easy to allow adaptation?
   - Was overall TSS close to planned {proposed_workout.get('plannedTSS', {}).get('min', 'N/A')}-{proposed_workout.get('plannedTSS', {}).get('max', 'N/A')}?

2. **WHAT WENT WELL**
   - Identify 2-3 positive aspects of the execution
   - Reference specific intervals from the detected intervals that were executed well
   - Mention good pacing, appropriate power delivery, or smart execution decisions

3. **INTERVAL EXECUTION QUALITY**
   - Review the detected intervals and assess quality
   - For work intervals: Was power appropriate for the interval type? (e.g., vo2max = Z5/Z6, threshold = Z4)
   - For recovery intervals: Was power actually low (~50-60% FTP) to allow recovery?
   - Comment on progression through the workout (did athlete fade or maintain quality?)

4. **POWER & HEART RATE RELATIONSHIP**
   - Did HR respond appropriately to power output?
   - Any signs of HR drift (HR climbing at steady power = fatigue/heat)?
   - Recovery quality: Did HR drop during rest intervals?
   - Indoor workouts typically run 10-15 bpm higher - factor this in

5. **CONSTRUCTIVE FEEDBACK (1-2 items maximum)**
   - If there are areas for improvement, mention them constructively
   - Focus on actionable insights (pacing, recovery discipline, warmup adequacy)
   - Frame as opportunities for optimization, not failures

6. **TRAINING IMPACT & NEXT STEPS**
   - What physiological adaptations will this workout drive?
   - Recommended recovery time before next hard session
   - Type of workout that would complement this one well

Be specific and reference actual numbers from the detected intervals. Use an encouraging, professional coaching tone. Response should be 400-600 words."""
        else:
            # Build the prompt WITHOUT proposed workout - analyze as standalone session
            prompt = f"""You are an expert cycling coach analyzing this workout. Since there was no planned workout for this session, provide an objective analysis of what the athlete accomplished and how their body responded.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
WORKOUT EXECUTION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

WORKOUT METRICS:
Duration: {duration_hours:.2f} hours ({duration_hours * 60:.0f} minutes)
Sport: {parsed_data.get('sport', 'cycling')}

POWER DATA:
- Average Power: {power_metrics.get('average_power', 0):.0f}W
- Normalized Power: {power_metrics.get('normalized_power', 0):.0f}W
- Max Power: {power_metrics.get('max_power', 0):.0f}W
- Intensity Factor: {power_metrics.get('intensity_factor', 0):.2f}
- TSS: {power_metrics.get('tss', 0):.1f}
- FTP: {power_metrics.get('ftp', 0):.0f}W

POWER ZONES (% of workout time):
{power_zones_text or "No power zone data"}

PEAK EFFORTS:
{peak_efforts_text or "No peak efforts detected"}

HEART RATE DATA:
- Average HR: {hr_metrics.get('average_hr', 0):.0f} bpm
- Max HR: {hr_metrics.get('max_hr', 0):.0f} bpm
- Min HR: {hr_metrics.get('min_hr', 0):.0f} bpm{hr_series_stats}

HEART RATE ZONES (% of workout time):
{hr_zones_text or "No heart rate zone data"}
{detected_intervals_text}
{trend_analysis}
ATHLETE NOTES:
{athlete_notes or "No notes provided"}

**ANALYSIS INSTRUCTIONS FOR STANDALONE WORKOUT:**

This was an UNPLANNED session (warmup, cooldown, spontaneous ride, or training outside the structured plan). Focus on characterizing WHAT the workout was and HOW the athlete performed.

**IMPORTANT GUIDELINES:**
1. Use AUTO-DETECTED INTERVALS to identify what type of session this was
2. Characterize the workout based on intensity distribution (endurance, tempo, threshold, VO2max mix)
3. Assess execution quality - did athlete pace well, maintain intensity, recover appropriately?
4. Look for physiological responses - HR appropriate for power, no excessive drift, good recovery
5. Consider context from athlete notes (warmup before race, recovery spin, group ride, etc.)

**SCORING RUBRIC (Rate 1-10):**
- 9-10: Excellent quality for the workout type, smart execution, appropriate intensity
- 7-8: Good execution, reasonable pacing, appropriate for purpose
- 5-6: Acceptable session, some good elements but room for improvement
- 3-4: Sub-optimal quality, poor pacing, or mismatched intensity for type
- 1-2: Poor execution or incomplete session

**ANALYSIS STRUCTURE:**

1. **WORKOUT CHARACTERIZATION**
   - What type of session was this? (Recovery ride, group ride, warmup, tempo session, mixed efforts, etc.)
   - Based on intensity distribution and detected intervals, what was the primary training stimulus?
   - Duration and TSS appropriate for the apparent workout type?

2. **EXECUTION QUALITY SCORE (Rate 1-10 using rubric above)**
   - How well did the athlete execute for this type of workout?
   - Was pacing appropriate? (steady for endurance, proper rest in intervals, etc.)
   - Did athlete maintain quality throughout or fade?

3. **INTERVAL STRUCTURE ANALYSIS (if applicable)**
   - Review detected intervals - were they executed consistently?
   - For recovery periods: Was power actually low enough to recover?
   - For work efforts: Appropriate intensity for the interval type?
   - Any standout efforts or particularly well-executed segments?

4. **PHYSIOLOGICAL RESPONSE**
   - How did heart rate track with power output?
   - Any signs of excessive fatigue (HR drift, inability to hit power targets)?
   - Recovery quality between efforts (if applicable)
   - Appropriate cardiovascular stress for the power output?

5. **TRAINING VALUE**
   - What physiological adaptations will this session provide?
   - How does this fit into a broader training context?
   - Was this likely the intended purpose based on execution?

6. **RECOMMENDATIONS**
   - If this was a warmup: Was duration/intensity appropriate for the main event?
   - If recovery ride: Was intensity truly easy enough for recovery?
   - If group ride/mixed efforts: Comments on pacing strategy
   - General suggestions for similar sessions in future

Be specific with numbers from the detected intervals and power data. Use an objective, analytical coaching tone that recognizes this was unplanned but still provides valuable insights. Response should be 350-500 words."""

        # Try each model in the list until one works
        last_error = None
        for model_name in self.MODELS:
            try:
                print(f"🤖 Attempting analysis with model: {model_name}")
                model = genai.GenerativeModel(model_name)
                response = model.generate_content(prompt)
                print(f"✅ Successfully generated analysis with {model_name}")
                return response.text
            except exceptions.ResourceExhausted as e:
                print(f"⚠️  Quota exceeded for {model_name}, trying next model...")
                last_error = f"Quota exceeded: {str(e)}"
                continue
            except exceptions.InvalidArgument as e:
                print(f"⚠️  Model {model_name} not available or invalid: {str(e)}")
                last_error = f"Invalid model: {str(e)}"
                continue
            except Exception as e:
                print(f"⚠️  Error with {model_name}: {type(e).__name__}: {str(e)}")
                last_error = f"{type(e).__name__}: {str(e)}"
                # Try next model for any error
                continue
        
        # If we get here, all models failed
        error_msg = f"❌ Could not generate analysis - all {len(self.MODELS)} models failed.\nLast error: {last_error}\n\nTried models: {', '.join(self.MODELS)}"
        print(error_msg)
        return error_msg
    
    def _analyze_workout_trends(self, parsed_data: Dict[str, Any]) -> str:
        """
        Analyze trends in power, heart rate, and cadence throughout the workout.
        
        Args:
            parsed_data: Parsed FIT file data with time series
            
        Returns:
            Formatted string with trend analysis
        """
        import numpy as np
        from typing import List
        
        trend_text = "\n🔍 WORKOUT TRENDS ANALYSIS:\n"
        
        # Get time series data
        power_series = parsed_data.get('power_metrics', {}).get('power_series', [])
        hr_series = parsed_data.get('hr_metrics', {}).get('hr_series', [])
        time_series = parsed_data.get('time_series', {})
        cadence_series = time_series.get('cadence', []) if time_series else []
        
        # Analyze power trends
        if power_series and len(power_series) > 30:
            power_array = np.array([p for p in power_series if p and p > 0])
            if len(power_array) > 30:
                # Split into thirds to analyze progression
                third = len(power_array) // 3
                first_third_avg = np.mean(power_array[:third])
                second_third_avg = np.mean(power_array[third:2*third])
                final_third_avg = np.mean(power_array[2*third:])
                
                power_fade = ((final_third_avg - first_third_avg) / first_third_avg) * 100
                
                trend_text += f"\nPOWER PROGRESSION:\n"
                trend_text += f"  - First third average: {first_third_avg:.0f}W\n"
                trend_text += f"  - Middle third average: {second_third_avg:.0f}W\n"
                trend_text += f"  - Final third average: {final_third_avg:.0f}W\n"
                trend_text += f"  - Power fade/gain: {power_fade:+.1f}%"
                
                if abs(power_fade) < 3:
                    trend_text += " (excellent consistency)"
                elif power_fade < -5:
                    trend_text += " (significant fade - possible fatigue)"
                elif power_fade > 5:
                    trend_text += " (negative split - strong finish)"
                trend_text += "\n"
                
                # Analyze power variability
                power_cv = (np.std(power_array) / np.mean(power_array)) * 100
                trend_text += f"  - Power variability (CV): {power_cv:.1f}%"
                if power_cv < 10:
                    trend_text += " (very steady)"
                elif power_cv < 20:
                    trend_text += " (moderately variable)"
                else:
                    trend_text += " (highly variable - intervals or surges)"
                trend_text += "\n"
        
        # Analyze heart rate trends and HR drift
        if hr_series and len(hr_series) > 30:
            hr_array = np.array([h for h in hr_series if h and h > 0])
            if len(hr_array) > 30:
                # Split into thirds
                third = len(hr_array) // 3
                first_third_avg_hr = np.mean(hr_array[:third])
                final_third_avg_hr = np.mean(hr_array[2*third:])
                
                hr_drift = final_third_avg_hr - first_third_avg_hr
                hr_drift_pct = (hr_drift / first_third_avg_hr) * 100
                
                trend_text += f"\nHEART RATE RESPONSE:\n"
                trend_text += f"  - First third average: {first_third_avg_hr:.0f} bpm\n"
                trend_text += f"  - Final third average: {final_third_avg_hr:.0f} bpm\n"
                trend_text += f"  - HR drift: {hr_drift:+.1f} bpm ({hr_drift_pct:+.1f}%)"
                
                if abs(hr_drift) < 3:
                    trend_text += " (minimal drift - excellent)"
                elif hr_drift > 5:
                    trend_text += " (moderate drift - watch hydration/cooling)"
                elif hr_drift > 10:
                    trend_text += " (significant drift - heat/fatigue stress)"
                trend_text += "\n"
                
                # Calculate time to recover between potential intervals
                # Look for drops in HR > 10 bpm as signs of rest periods
                hr_drops = []
                for i in range(1, len(hr_array)):
                    if hr_array[i-1] - hr_array[i] > 10:
                        # Found a drop, track recovery
                        recovery_time = 0
                        baseline = hr_array[i]
                        for j in range(i, min(i + 120, len(hr_array))):  # Look ahead 2 min max
                            if hr_array[j] < baseline + 5:
                                recovery_time += 1
                            else:
                                break
                        if recovery_time > 0:
                            hr_drops.append(recovery_time)
                
                if hr_drops:
                    avg_recovery = np.mean(hr_drops)
                    trend_text += f"  - Average HR recovery time: {avg_recovery:.0f} seconds\n"
        
        # Analyze cadence trends
        if cadence_series:
            valid_cadence = [c for c in cadence_series if c and c > 0]
            if len(valid_cadence) > 30:
                cadence_array = np.array(valid_cadence)
                avg_cadence = np.mean(cadence_array)
                cadence_std = np.std(cadence_array)
                
                trend_text += f"\nCADENCE ANALYSIS:\n"
                trend_text += f"  - Average cadence: {avg_cadence:.0f} rpm\n"
                trend_text += f"  - Cadence variability: ±{cadence_std:.0f} rpm"
                
                if avg_cadence < 75:
                    trend_text += " (low cadence - grinding)"
                elif avg_cadence < 85:
                    trend_text += " (moderate cadence)"
                elif avg_cadence < 95:
                    trend_text += " (optimal cadence)"
                else:
                    trend_text += " (high cadence - spinning)"
                trend_text += "\n"
                
                # Check cadence consistency
                if cadence_std < 5:
                    trend_text += "  - Cadence consistency: Excellent (very steady)\n"
                elif cadence_std < 10:
                    trend_text += "  - Cadence consistency: Good\n"
                else:
                    trend_text += "  - Cadence consistency: Variable (intervals or terrain changes)\n"
        
        return trend_text if len(trend_text) > 50 else ""
    
    def compare_peak_efforts_to_history(self, current_efforts: Dict[str, Dict[str, float]],
                                       historical_bests: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Compare current peak efforts to historical personal bests
        
        Args:
            current_efforts: Peak efforts from current workout
            historical_bests: Dictionary mapping effort type to list of top 3 historical efforts
            
        Returns:
            Dictionary indicating which efforts are new personal bests and their ranking
        """
        new_bests = {}
        
        for effort_type, current_data in current_efforts.items():
            current_power = current_data['power']
            
            # Get historical top 3 for this effort type
            historical = historical_bests.get(effort_type, [])
            
            # Determine if this is a new PB and what rank
            rank = None
            is_new_pb = False
            
            if len(historical) < 3:
                # Not enough history, this is automatically a PB
                rank = len(historical) + 1
                is_new_pb = True
            else:
                # Compare to existing top 3
                for i, hist_effort in enumerate(historical):
                    hist_power = hist_effort.get('power', 0)
                    if current_power > hist_power:
                        rank = i + 1
                        is_new_pb = True
                        break
            
            if is_new_pb:
                new_bests[effort_type] = {
                    'power': current_power,
                    'rank': rank,
                    'medal': {1: '🥇 Gold', 2: '🥈 Silver', 3: '🥉 Bronze'}.get(rank, 'Off-podium'),
                    'improvement': self._calculate_improvement(current_power, historical, rank)
                }
        
        return new_bests
    
    def _calculate_improvement(self, current_power: float, 
                               historical: List[Dict[str, Any]], 
                               rank: int) -> Optional[float]:
        """Calculate percentage improvement over previous best"""
        if not historical or rank is None:
            return None
        
        if rank > len(historical):
            return None
        
        previous_best = historical[rank - 1] if rank <= len(historical) else historical[-1]
        previous_power = previous_best.get('power', 0)
        
        if previous_power == 0:
            return None
        
        improvement_pct = ((current_power - previous_power) / previous_power) * 100
        return improvement_pct
