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
        
        # Skip AI analysis for non-cycling workouts
        sport = parsed_data.get('sport', 'cycling').lower()
        if sport not in ['cycling', 'bike', 'biking']:
            print(f"⊘ Skipping AI analysis for non-cycling workout (sport: {sport})")
            return {
                'parsed_data': parsed_data,
                'peak_efforts': {},
                'ai_analysis': f"Non-cycling workout ({sport}) - AI analysis skipped",
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
        
        # Skip AI analysis if no matching proposed workout found
        if not proposed_workout:
            print(f"⊘ Skipping AI analysis - no matching proposed workout found")
            return {
                'parsed_data': parsed_data,
                'peak_efforts': {},
                'ai_analysis': f"No matching proposed workout found - AI analysis skipped",
                'analyzed_at': datetime.now().isoformat()
            }
        
        # Detect peak efforts (passing proposed workout for custom intervals)
        peak_efforts = self._detect_peak_efforts(parsed_data, proposed_workout)
        
        # Generate AI analysis
        ai_analysis = self._generate_ai_analysis(parsed_data, peak_efforts, athlete_notes)
        
        return {
            'parsed_data': parsed_data,
            'peak_efforts': peak_efforts,
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
    
    def _find_best_matching_workout(self, parsed_data: Dict[str, Any], workout_date: str, 
                                   date_window_days: int = 2) -> Optional[Dict[str, Any]]:
        """
        Find the best matching proposed workout based on TSS, duration, and workout characteristics.
        Searches within a date window (default ±2 days) to account for timezone issues.
        
        Args:
            parsed_data: Parsed FIT file data
            workout_date: Original workout date
            date_window_days: Number of days before/after to search
            
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
            
            for row in candidates:
                date, name, wtype, planned_dur, tss_min, tss_max, rpe_min, rpe_max, intervals, sections, notes = row
                
                # Calculate match score (0-100)
                # Priority: Date (50 pts) > Duration (30 pts) > TSS (20 pts)
                score = 0
                
                # Date proximity (50 points max) - HIGHEST PRIORITY
                days_diff = abs((datetime.strptime(date, '%Y-%m-%d') - base_date).days)
                if days_diff == 0:
                    score += 50  # Same day
                elif days_diff == 1:
                    score += 25  # 1 day off
                elif days_diff == 2:
                    score += 10  # 2 days off
                
                # Duration match (30 points max)
                if planned_dur:
                    dur_diff_pct = abs(actual_duration_min - planned_dur) / planned_dur * 100
                    if dur_diff_pct <= 10:
                        score += 30  # Within 10%
                    elif dur_diff_pct <= 20:
                        score += 20  # Within 20%
                    elif dur_diff_pct <= 40:
                        score += 10  # Within 40%
                
                # TSS match (20 points max)
                if tss_min and tss_max:
                    tss_avg = (tss_min + tss_max) / 2
                    tss_diff_pct = abs(actual_tss - tss_avg) / tss_avg * 100
                    if tss_diff_pct <= 10:
                        score += 20  # Within 10%
                    elif tss_diff_pct <= 20:
                        score += 15  # Within 20%
                    elif tss_diff_pct <= 40:
                        score += 10  # Within 40%
                    elif tss_diff_pct <= 60:
                        score += 5   # Within 60%
                
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
                             athlete_notes: Optional[str] = None) -> str:
        """
        Generate AI-powered workout analysis using Gemini
        
        Args:
            parsed_data: Parsed FIT file data
            peak_efforts: Detected peak efforts
            athlete_notes: Optional notes from athlete
            
        Returns:
            AI-generated workout analysis text
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
        
        # ENHANCED: Analyze trends throughout the workout
        trend_analysis = self._analyze_workout_trends(parsed_data)
        
        # Load proposed workout for context
        workout_date = parsed_data.get('start_time', '')[:10] if parsed_data.get('start_time') else None
        proposed_workout = None
        proposed_workout_text = ""
        
        if workout_date:
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
                    
                    # Categorize interval type
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
        
        # Generate interval-by-interval execution analysis
        interval_execution = ""
        if proposed_workout:
            interval_execution = self._analyze_prescribed_intervals(parsed_data, proposed_workout)
            if interval_execution:
                print(f"✓ Generated interval-by-interval analysis ({len(interval_execution)} chars)")
            else:
                print(f"⚠️ No interval execution data generated")
        
        if proposed_workout:
            # Build prompt WITH proposed workout context
            prompt = f"""You are an expert cycling coach analyzing workout EXECUTION compared to the PLANNED workout.

{proposed_workout_text}
{interval_execution}
📊 ACTUAL WORKOUT EXECUTION:

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
{trend_analysis}
ATHLETE NOTES:
{athlete_notes or "No notes provided"}

**ANALYSIS INSTRUCTIONS:**

As a professional cycling coach, analyze how well the athlete EXECUTED the prescribed workout plan. Be specific and concrete.

1. **ADHERENCE SCORE (Rate 1-10)**
   - Rate overall adherence to the prescribed plan
   - Did athlete complete all {total_work_intervals} work intervals as prescribed?
   - Were power targets hit during work intervals?
   - Were recovery intervals at appropriate low intensity?
   - Was total duration close to planned {proposed_workout.get('plannedDuration', 'N/A')} minutes?
   - Was TSS close to target {proposed_workout.get('plannedTSS', {}).get('min', 'N/A')}-{proposed_workout.get('plannedTSS', {}).get('max', 'N/A')}?

2. **INTERVAL-BY-INTERVAL EXECUTION ANALYSIS**
   - Go through each prescribed interval and assess execution
   - For WORK intervals: Did power hit the target range? Any struggles or early termination?
   - For RECOVERY intervals: Did athlete actually recover (low power, HR coming down)?
   - Note any intervals that were executed exceptionally well
   - Note any intervals where athlete struggled or deviated from plan
   - Comment on whether warmup and cooldown were adequate

3. **POWER DELIVERY QUALITY**
   - Analyze power progression throughout the workout (use the trend data)
   - Was power consistent during work intervals or erratic?
   - Did power fade in later intervals compared to early intervals?
   - Comment on normalized power vs average power (close = good pacing)
   - Look at power variability - smooth intervals or lots of surging?

4. **HEART RATE RESPONSE ASSESSMENT**
   - How did HR respond during work intervals? Appropriate for the power?
   - HR drift analysis: Did HR climb at steady power (sign of heat/fatigue)?
   - Recovery quality: Did HR drop appropriately during recovery intervals?
   - Compare HR zones to power zones - do they match the intended intensity?
   - Indoor workouts run 10-15 bpm higher - factor this in

5. **CADENCE EXECUTION**
   - Were cadence targets from the prescribed intervals met?
   - Was cadence consistent or variable?
   - Any signs of grinding (low cadence) indicating fatigue?

6. **WORKOUT TYPE ADHERENCE**
   - This was prescribed as a {workout_type} workout
   - Did the execution match this workout type's goals?
   - Were the appropriate energy systems targeted?

Be detailed and specific. Reference actual power numbers, HR values, and interval times. Use exact data from the trend analysis and peak efforts. Focus on execution quality and adherence to the plan. Response should be 400-600 words."""
        else:
            # Build the prompt WITHOUT proposed workout
            prompt = f"""Analyze this cycling workout and provide coaching insights:

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
{trend_analysis}
IMPORTANT ANALYSIS GUIDELINES:
1. Focus primarily on POWER ZONES distribution to assess workout intensity
2. If power zones show mostly Zone 1-2, this is a recovery/easy ride regardless of other metrics
3. Heart rate can be affected by many factors (heat, fatigue, hydration) - don't over-emphasize it
4. Look at the overall zone distribution patterns to understand the workout structure
5. Use the trend analysis data to identify fatigue patterns and execution quality

ATHLETE NOTES:
{athlete_notes or "No notes provided"}

Please provide:
1. **Workout Quality Assessment**: Overall quality (1-10 rating) and why
2. **Effort Distribution**: How the effort was distributed across zones and what this indicates
3. **Power & HR Trends**: Analyze the progression data - did athlete fade? maintain power? show HR drift?
4. **Cadence Patterns**: Comment on cadence consistency and whether it was in optimal range
5. **Notable Achievements**: Any impressive efforts, personal bests, or standout metrics
6. **Recovery Recommendations**: How much recovery needed and what type of workout should come next
7. **Performance Insights**: 2-3 actionable insights about pacing, effort, or execution

Keep your response concise but insightful (400-600 words). Be specific and reference the trend data. Use a motivating, coach-like tone."""

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
