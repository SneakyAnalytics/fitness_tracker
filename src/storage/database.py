# src/storage/database.py

import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from ..models.workout import DailyWorkout, WeeklySummary

class WorkoutDatabase:
    def __init__(self, db_path: str = "data/fitness_data.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database with all required tables"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        # Create workouts table
        c.execute('''
            CREATE TABLE IF NOT EXISTS workouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workout_day TEXT NOT NULL,
                workout_title TEXT NOT NULL,
                workout_data TEXT NOT NULL,
                qualitative_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                athlete_comments TEXT,
                UNIQUE(workout_day, workout_title)
            )
        ''')

        # Create fit_files table
        c.execute('''
            CREATE TABLE IF NOT EXISTS fit_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workout_day TEXT NOT NULL,
                workout_title TEXT NOT NULL,
                fit_data TEXT NOT NULL,
                file_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(workout_day, workout_title)
            )
        ''')

        # Create daily_metrics table
        c.execute('''
            CREATE TABLE IF NOT EXISTS daily_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                metric_type TEXT NOT NULL,
                metric_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(date, metric_type)
            )
        ''')

        # Create weekly_summaries table (new)
        c.execute('''
            CREATE TABLE IF NOT EXISTS weekly_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                summary_data TEXT NOT NULL,
                qualitative_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(start_date, end_date)
            )
        ''')

        # Create weekly_plans table
        c.execute('''
            CREATE TABLE IF NOT EXISTS weekly_plans (
                weekNumber INTEGER PRIMARY KEY,
                startDate TEXT NOT NULL,
                plannedTSS_min INTEGER,
                plannedTSS_max INTEGER,
                notes TEXT NOT NULL
            )
        ''')

        # Create daily_plans table
        c.execute('''
            CREATE TABLE IF NOT EXISTS daily_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                weekNumber INTEGER NOT NULL,
                dayNumber INTEGER NOT NULL,
                date TEXT NOT NULL,
                FOREIGN KEY (weekNumber) REFERENCES weekly_plans(weekNumber)
            )
        ''')

        # Create proposed_workouts table
        c.execute('''
            CREATE TABLE IF NOT EXISTS proposed_workouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dailyPlanId INTEGER NOT NULL,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                plannedDuration INTEGER,
                plannedTSS_min INTEGER,
                plannedTSS_max INTEGER,
                targetRPE_min INTEGER,
                targetRPE_max INTEGER,
                intervals TEXT,
                sections TEXT,
                FOREIGN KEY (dailyPlanId) REFERENCES daily_plans(id),
                UNIQUE(dailyPlanId, name) ON CONFLICT IGNORE
            )
        ''')

        conn.commit()
        conn.close()
    
    def _get_numeric_value(self, value, default=0.0):
        """Safely convert value to float"""
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return default
        if isinstance(value, dict):
            return default
        return default
    
    def _calculate_sleep_quality_score(
        self, sleep_hours: float, deep_sleep: float, 
        light_sleep: float, rem_sleep: float
    ) -> float:
        """Calculate sleep quality score on 1-5 scale"""
        try:
            # Base score from total sleep duration
            if sleep_hours >= 7 and sleep_hours <= 9:
                duration_score = 5.0
            elif sleep_hours >= 6:
                duration_score = 4.0
            elif sleep_hours >= 5:
                duration_score = 3.0
            else:
                duration_score = 2.0
                
            # Calculate percentages of sleep stages
            total_sleep_minutes = sleep_hours * 60
            if total_sleep_minutes > 0:
                deep_pct = (deep_sleep / total_sleep_minutes) * 100
                rem_pct = (rem_sleep / total_sleep_minutes) * 100
            else:
                deep_pct = rem_pct = 0
                
            # Score sleep stages
            stages_score = 3.0  # Default score
            if deep_pct >= 20 and rem_pct >= 20:
                stages_score = 5.0
            elif deep_pct >= 15 and rem_pct >= 15:
                stages_score = 4.0
                
            # Final weighted score
            final_score = (duration_score * 0.6) + (stages_score * 0.4)
            return round(final_score, 2)
        except Exception as e:
            print(f"Error calculating sleep score: {str(e)}")
            return 1.0

    def save_fit_data(self, workout_day: str, workout_title: str, fit_data: Dict[str, Any], file_name: str) -> bool:
        """Save or update FIT file data"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        try:
            c.execute(
                '''
                INSERT OR REPLACE INTO fit_files
                (workout_day, workout_title, fit_data, file_name)
                VALUES (?, ?, ?, ?)
                ''',
                (
                    workout_day,
                    workout_title,
                    json.dumps(fit_data),
                    file_name
                )
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"Error saving FIT data: {e}")
            return False
        finally:
            conn.close()

    def save_daily_metric(self, date: str, metric_type: str, metric_data: Dict[str, Any]) -> bool:
        print(f"DEBUG: Saving metric {metric_type} for date {date}")
        print(f"DEBUG: Metric data: {json.dumps(metric_data, indent=2)}")
        
        """Save or update daily metric data"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            print(f"DEBUG: Saving daily metric for {date} - {metric_type}")
            c.execute(
                '''
                INSERT OR REPLACE INTO daily_metrics 
                (date, metric_type, metric_data)
                VALUES (?, ?, ?)
                ''',
                (
                    date,
                    metric_type,
                    json.dumps(metric_data)
                )
            )
            conn.commit()
            print(f"DEBUG: Successfully saved daily metric for {date} - {metric_type}")
            return True
        except Exception as e:
            print(f"Error saving daily metric: {e}")
            return False
        finally:
            conn.close()

    def save_workout(self, workout: Dict[str, Any]) -> bool:
        """Save or update a workout while preserving qualitative data"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            # Check if workout exists and get any existing qualitative data
            c.execute(
                "SELECT workout_data, qualitative_data FROM workouts WHERE workout_day = ? AND workout_title = ?",
                (workout['workout_day'], workout['title'])
            )
            existing = c.fetchone()
            
            if existing and existing[1]:  # If qualitative data exists
                existing_qual = json.loads(existing[1])
                # Create a new workout dict that includes the qualitative data
                workout_with_qual = workout.copy()
                workout_with_qual.update(existing_qual)
            else:
                workout_with_qual = workout.copy()

            athlete_comments = workout.get('athlete_comments')
            workout_with_qual['athlete_comments'] = athlete_comments
            workout_data = json.dumps(workout_with_qual)
            
            # Save workout with preserved qualitative data
            c.execute(
                '''
                INSERT OR REPLACE INTO workouts
                (workout_day, workout_title, workout_data, qualitative_data, athlete_comments, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''',
                (
                    workout['workout_day'],
                    workout['title'],
                    workout_data,
                    None,
                    athlete_comments  # Ensure this field is saved
                )
            )
            
            conn.commit()
            print(f"Successfully saved workout: {workout['title']} on {workout['workout_day']}")
            success = True
        except Exception as e:
            print(f"Error saving workout: {e}")
            success = False
        finally:
            conn.close()
        
        return success

    def update_workout_qualitative(
        self,
        workout_day: str,
        workout_title: str,
        qualitative_data: Dict[str, str]
    ) -> bool:
        """Update qualitative data for a workout"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            # Convert date format if needed
            try:
                #Parse the input date
                if ('/' in workout_day):
                    parsed_date = datetime.strptime(workout_day, '%m/%d/%y')
                else:
                    parsed_date = datetime.strptime(workout_day, '%Y-%m-%d')
                # Convert to standard format
                standard_date = parsed_date.strftime('%Y-%m-%d')        
            except Exception as e:
                print(f"Error parsing date {workout_day}: {e}")
                standard_date = workout_day
                    
            print(f"Looking for workout: {workout_title} on standardized date: {standard_date}")
            
            # Get existing workout data
            c.execute(
                "SELECT workout_data FROM workouts WHERE workout_day = ? AND workout_title = ?",
                (standard_date, workout_title)
            )
            result = c.fetchone()
            
            if result:
                print("Found workout, updating with qualitative data")
                workout_data = json.loads(result[0])
                
                # Create a new workout dict with qualitative data
                updated_workout = workout_data.copy()
                updated_workout.update(qualitative_data)
                athlete_comments = qualitative_data.get('athlete_comments')
                
                # Save both the complete workout data and separate qualitative data
                c.execute(
                    '''
                    UPDATE workouts
                    SET workout_data = ?,
                        qualitative_data = ?,
                        athlete_comments = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE workout_day = ? AND workout_title = ?
                    ''',
                    (
                        json.dumps(updated_workout),
                        json.dumps({k: v for k, v in qualitative_data.items() if k != 'athlete_comments'}),
                        athlete_comments,
                        standard_date,
                        workout_title
                    )
                )
                conn.commit()
                print("Successfully updated workout with qualitative data")
                success = True
            else:
                print(f"No workout found for {workout_title} on {standard_date}")
                print("Available workouts:")
                c.execute("SELECT workout_day, workout_title FROM workouts")
                available = c.fetchall()
                for day, title in available:
                    print(f"  - {title} on {day}")
                success = False
                
        except Exception as e:
            print(f"Error updating qualitative data: {e}")
            success = False
        finally:
            conn.close()
        
        return success
    
    def get_all_workouts(self) -> List[Dict[str, Any]]:
        """Retrieve all workouts"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            c.execute('SELECT workout_data, qualitative_data, athlete_comments FROM workouts ORDER BY workout_day DESC')
            rows = c.fetchall()
            
            workouts = []
            for row in rows:
                workout_data, qualitative_data, athlete_comments = row
                workout = json.loads(workout_data)
                if qualitative_data:
                    workout.update(json.loads(qualitative_data))
                workout['athlete_comments'] = athlete_comments
                workouts.append(workout)
            
            return workouts
        finally:
            conn.close()

    def get_workouts_by_week(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Retrieve workouts for a specific week"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            c.execute(
                'SELECT workout_data, qualitative_data FROM workouts WHERE workout_day BETWEEN ? AND ? ORDER BY workout_day',
                (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d'))
            )
            rows = c.fetchall()
            
            workouts = []
            for workout_data, qualitative_data in rows:
                workout = json.loads(workout_data)
                if qualitative_data:
                    workout.update(json.loads(qualitative_data))
                workouts.append(workout)
            
            return workouts
        finally:
            conn.close()
            
    def _find_matching_proposed_workout(self, date: str, workout_type: str, actual_duration: float, 
                                      proposed_workouts: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Find matching proposed workout based on date, type, and duration"""
        print(f"\nDEBUG: Looking for match - Date: {date}, Type: {workout_type}, Duration: {actual_duration}")
        print(f"DEBUG: Available proposed workouts: {json.dumps(proposed_workouts, indent=2)}")
        
        # Convert both dates to ISO format for consistent comparison
        iso_date = datetime.strptime(date, '%Y-%m-%d').date().isoformat()
        matching_workouts = [
            w for w in proposed_workouts
            if datetime.strptime(w['date'], '%Y-%m-%d').date().isoformat() == iso_date
            and w['type'].lower() == workout_type.lower()
        ]
        print(f"DEBUG: Matching workouts after date standardization: {len(matching_workouts)}")
        
        print(f"DEBUG: Found {len(matching_workouts)} potential matches by date and type")
        if matching_workouts:
            print(f"DEBUG: Matching workouts: {json.dumps(matching_workouts, indent=2)}")
        
        if not matching_workouts:
            print(f"DEBUG: No matches for Date: {iso_date}, Type: {workout_type.lower()}")
            for w in proposed_workouts:
                print(f"DEBUG: Available - Date: {w['date']}, Type: {w['type'].lower()}")
            return None
            
        # If multiple matches, use duration to find best match
        best_match = None
        min_duration_diff = float('inf')
        
        for workout in matching_workouts:
            planned_duration = workout.get('plannedDuration')
            if planned_duration is not None:
                duration_diff = abs(actual_duration - workout['plannedDuration'])

                duration_threshold = max(5, planned_duration * 0.15)

                print(f"DEBUG: Comparing durations - Planned: {planned_duration}, Actual: {actual_duration}, "
                      f"Diff: {duration_diff}, Threshold: {duration_threshold}")
                
                if duration_diff < min_duration_diff:
                    min_duration_diff = duration_diff
                    best_match = workout
        
        if best_match is None and matching_workouts:
            best_match = matching_workouts[0]
            print(f"DEBUG: No duration match found, selecting first match by date/type")

        if best_match:
            print(f"DEBUG: Best match found: {json.dumps(best_match, indent=2)}")
        else:
            print("DEBUG: No match found")
            
        return best_match

    def generate_weekly_summary(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Generate a comprehensive weekly summary integrating all data sources"""
        print(f"\nDEBUG: Generating weekly summary")
        print(f"Start date: {start_date}, End date: {end_date}")
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            # Get all workouts for the date range
            query = '''
                    SELECT w.workout_day, w.workout_title, w.workout_data, w.qualitative_data, w.athlete_comments, f.fit_data
                    FROM workouts w
                    LEFT JOIN fit_files f ON w.workout_day = f.workout_day
                    AND ABS(
                        CAST(json_extract(w.workout_data, '$.metrics.actual_duration') AS REAL) -
                        CAST(json_extract(f.fit_data, '$.metrics.duration') AS REAL)
                    ) < 1
                    WHERE w.workout_day >= ? AND w.workout_day <= ?
                    ORDER BY w.workout_day
                    '''

            print(f"\nExecuting query with dates: {start_date}, {end_date}")

            # Debug: Check available workout days and their formats
            c.execute("SELECT workout_day, typeof(workout_day) FROM workouts ORDER BY workout_day")
            available_dates = c.fetchall()
            print("\nAvailable workout days in database:")
            for date in available_dates:
                print(f"  - {date[0]}")
            
            try:
                formatted_start_date = datetime.strptime(start_date, '%Y-%m-%d').strftime('%Y-%m-%d')
                formatted_end_date = datetime.strptime(end_date, '%Y-%m-%d').strftime('%Y-%m-%d')
                print(f"\nFormatted dates for query: {formatted_start_date} to {formatted_end_date}")
                
                # Debug: Test the date comparison directly
                test_query = '''
                    SELECT COUNT(*)
                    FROM workouts
                    WHERE DATE(workout_day) BETWEEN ? AND ?
                '''
                c.execute(test_query, (formatted_start_date, formatted_end_date))
                count = c.fetchone()[0]
                print(f"\nFound {count} workouts in date range")
                
                # Execute the original query
                c.execute(query, (formatted_start_date, formatted_end_date))
            except ValueError as e:
                print(f"\nError parsing dates: {e}")
                raise
            workout_rows = c.fetchall()
            
            print(f"Found {len(workout_rows)} workouts")
            
            # Initialize summary data
            total_tss = 0.0
            total_duration = 0.0
            sessions_completed = len(workout_rows)
            workout_types = set()
            daily_workouts = []
            daily_energy = {}
            daily_sleep_quality = {}
            
            # Process workouts
            for row in workout_rows:
                try:
                    day, title, workout_data, qual_data, athlete_comments, fit_data = row
                    print(f"\nProcessing workout: {title} on {day}")
                    
                    workout = json.loads(workout_data)
                    print(f"Raw workout data: {json.dumps(workout, indent=2)}")
                    
                    qualitative = json.loads(qual_data) if qual_data else {}
                    
                    # Safely load fit_data
                    fit_metrics = {}
                    if fit_data:
                        try:
                            fit_metrics = json.loads(fit_data)
                        except json.JSONDecodeError as e:
                            print(f"Error decoding fit_data: {e}")
                            fit_metrics = {}
                    
                    # Get the workout type
                    workout_type = workout.get('type')
                    print(f"Workout type: {workout_type}")
                    if workout_type:
                        workout_types.add(workout_type)
                    
                    # Get metrics from all sources
                    csv_metrics = workout.get('metrics', {})
                    fit_metrics_metrics = fit_metrics.get('metrics', {}) if fit_metrics else {}
                    
                    # Process TSS
                    workout_tss = (
                        self._get_numeric_value(workout.get('TSS')) or
                        self._get_numeric_value(csv_metrics.get('actual_tss')) or
                        self._get_numeric_value(fit_metrics_metrics.get('tss'))
                    )
                    print(f"TSS: {workout_tss}")
                    total_tss += workout_tss
                    
                    # Process duration
                    duration = (
                        self._get_numeric_value(fit_metrics_metrics.get('duration')) or
                        self._get_numeric_value(csv_metrics.get('actual_duration')) or
                        self._get_numeric_value(workout.get('TimeTotalInHours', 0)) * 60
                    )
                    print(f"Duration: {duration}")
                    total_duration += duration
                    
                    # Combine power data from all sources with FIT priority
                    power_data = workout.get('power_data', {})
                    if fit_metrics.get('power_metrics'):
                        # Preserve normalized power from FIT files
                        fit_power = fit_metrics['power_metrics']
                        power_data.update({
                            'normalized_power': fit_power.get('normalized_power'),
                            # Explicitly map all power fields from FIT
                            'average_power': fit_power.get('average_power'),
                            'max_power': fit_power.get('max_power'),
                            'intensity_factor': fit_power.get('intensity_factor'),
                            'zones': fit_power.get('zones', {}),
                            # Merge with existing workout data
                            **power_data
                        })
                    print(f"Power data: {json.dumps(power_data, indent=2)}")
                    
                    # Combine heart rate data
                    hr_data = workout.get('heart_rate_data', {})
                    if fit_metrics.get('hr_metrics'):
                        hr_data.update(fit_metrics['hr_metrics'])
                    print(f"HR data: {json.dumps(hr_data, indent=2)}")

                    # Extract normalized power from fit_data
                    normalized_power = None
                    if fit_data:
                        try:
                            fit_data_json = json.loads(fit_data)
                            normalized_power = fit_data_json.get('power_metrics', {}).get('normalized_power')
                        except (json.JSONDecodeError, AttributeError):
                            print("Could not extract normalized_power from fit_data")

                    # Create workout entry
                    workout_entry = {
                        'day': day,
                        'type': workout_type,
                        'title': title,
                        'workout_data': {
                            'metrics': {
                                'actual_tss': workout_tss,
                                'actual_duration': duration,
                                'planned_tss': self._get_numeric_value(csv_metrics.get('planned_tss')),
                                'planned_duration': self._get_numeric_value(csv_metrics.get('planned_duration')),
                                'rpe': self._get_numeric_value(csv_metrics.get('rpe'))
                            },
                            'power_data': {
                                'average': power_data.get('average'),
                                'max': power_data.get('max'),
                                'intensity_factor': power_data.get('if'),
                                'zones': power_data.get('zones', {}),
                                'normalized_power': normalized_power
                            } if power_data else None,
                            'heart_rate_data': hr_data if hr_data else None
                        },
                        'feedback': {**qualitative, 'athlete_comments': athlete_comments}
                    }
                    # Remove None values from power_data if it exists
                    if workout_entry['workout_data']['power_data']:
                        workout_entry['workout_data']['power_data'] = {
                            k: v for k, v in workout_entry['workout_data']['power_data'].items()
                            if v is not None
                        }
                    daily_workouts.append(workout_entry)
                    print(f"Successfully added workout entry with power data: {json.dumps(workout_entry['workout_data'].get('power_data'), indent=2)}")
                except Exception as e:
                    print(f"Error processing workout: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    continue

            # Calculate average daily energy
            c.execute(
                '''
                SELECT date, metric_data FROM daily_metrics WHERE metric_type = 'Body Battery'
                AND date BETWEEN ? AND ?
                ''',
                (start_date, end_date)
            )
            body_battery_rows = c.fetchall()
            total_energy = 0
            count = 0
            for date, metric_data in body_battery_rows:
                metric_data = json.loads(metric_data)
                avg_body_battery = metric_data.get('summary', {}).get('avg', None)
                if avg_body_battery is not None:
                    scaled_energy = avg_body_battery * 5 / 100  # Scale to 1-5 range
                    daily_energy[date] = scaled_energy
                    total_energy += scaled_energy
                    count += 1
            
            avg_daily_energy = total_energy / count if count > 0 else None

            # Get all sleep-related metrics
            c.execute(
                '''
                SELECT date, metric_type, metric_data 
                FROM daily_metrics 
                WHERE (metric_type LIKE '%Sleep%' OR metric_type = 'Time In Deep Sleep' 
                    OR metric_type = 'Time In Light Sleep' OR metric_type = 'Time In REM Sleep')
                AND date BETWEEN ? AND ?
                ''',
                (start_date, end_date)
            )
            sleep_rows = c.fetchall()
            
            # Process sleep metrics by date
            daily_sleep_quality = {}
            total_sleep_quality = 0
            sleep_count = 0
            
            # First pass: gather all metrics by date
            for date, metric_type, metric_data in sleep_rows:
                if date not in daily_sleep_quality:
                    daily_sleep_quality[date] = {}
                    
                metric_data = json.loads(metric_data)
                # Store each sleep metric
                daily_sleep_quality[date][metric_type] = metric_data.get('summary', {}).get('avg')
            
            # Second pass: calculate sleep quality scores
            for date, metrics in daily_sleep_quality.items():
                sleep_hours = metrics.get('Sleep Hours', 0)
                deep_sleep = metrics.get('Time In Deep Sleep', 0)
                light_sleep = metrics.get('Time In Light Sleep', 0)
                rem_sleep = metrics.get('Time In REM Sleep', 0)
                
                # Calculate sleep quality score (1-5 scale)
                if sleep_hours > 0:  # Only calculate if we have sleep data
                    sleep_score = self._calculate_sleep_quality_score(
                        sleep_hours, deep_sleep, light_sleep, rem_sleep
                    )
                    daily_sleep_quality[date]['sleep_quality_score'] = sleep_score
                    total_sleep_quality += sleep_score
                    sleep_count += 1
                    print(f"DEBUG: Calculated sleep quality score for {date}: {sleep_score}")

            # Calculate average sleep quality
            avg_sleep_quality = total_sleep_quality / sleep_count if sleep_count > 0 else None
            print(f"DEBUG: Final average sleep quality: {avg_sleep_quality}")
                
            # Get weekly plan first
            c.execute(
                '''
                SELECT weekNumber, startDate, plannedTSS_min, plannedTSS_max, notes
                FROM weekly_plans
                WHERE startDate = ?
                ''',
                (start_date,)
            )
            week_plan = c.fetchone()
            weekly_plan_data = {
                'weekNumber': week_plan[0] if week_plan else None,
                'startDate': week_plan[1] if week_plan else None,
                'plannedTSS_min': week_plan[2] if week_plan else None,
                'plannedTSS_max': week_plan[3] if week_plan else None,
                'notes': week_plan[4] if week_plan else None
            } if week_plan else None

            # Get all proposed workouts for the week
            print("\nDEBUG: Fetching proposed workouts")
            c.execute(
                '''
                SELECT dp.date, p.type, p.plannedDuration, p.plannedTSS_min, p.plannedTSS_max, 
                    p.targetRPE_min, p.targetRPE_max
                FROM proposed_workouts p
                JOIN daily_plans dp ON p.dailyPlanId = dp.id
                WHERE dp.date BETWEEN ? AND ?
                ''',
                (start_date, end_date)
            )
            proposed_rows = c.fetchall()
            print(f"DEBUG: Found {len(proposed_rows)} proposed workouts")
            
            proposed_workouts = [
                {
                    'date': row[0],
                    'type': row[1],
                    'plannedDuration': row[2],
                    'plannedTSS_min': row[3],
                    'plannedTSS_max': row[4],
                    'targetRPE_min': row[5],
                    'targetRPE_max': row[6]
                }
                for row in proposed_rows
            ]
            print(f"DEBUG: Proposed workouts data: {json.dumps(proposed_workouts, indent=2)}")

            # When processing workouts, add debug logging
            for workout_entry in daily_workouts:
                print(f"\nDEBUG: Processing workout: {workout_entry['day']} - {workout_entry['type']}")
                matching_proposed = self._find_matching_proposed_workout(
                    workout_entry['day'],
                    workout_entry['type'],
                    workout_entry['workout_data']['metrics']['actual_duration'],
                    proposed_workouts
                )
                
                if matching_proposed:
                    print(f"DEBUG: Updating workout with planned data: {json.dumps(matching_proposed, indent=2)}")
                    workout_entry['workout_data']['metrics'].update({
                        'planned_tss': f"{matching_proposed['plannedTSS_min']}-{matching_proposed['plannedTSS_max']}",
                        'planned_duration': matching_proposed['plannedDuration'],
                        'planned_rpe': f"{matching_proposed['targetRPE_min']}-{matching_proposed['targetRPE_max']}"
                    })
                else:
                    print(f"DEBUG: No matching proposed workout found")

            summary = {
                'start_date': start_date,
                'end_date': end_date,
                'total_tss': round(total_tss, 2),
                'total_training_hours': round(total_duration / 60, 2),
                'sessions_completed': sessions_completed,
                'workout_types': list(workout_types),
                'qualitative_feedback': sorted(daily_workouts, key=lambda x: x.get('day', '')),
                'daily_energy': daily_energy,
                'avg_daily_energy': avg_daily_energy,
                'daily_sleep_quality': daily_sleep_quality,
                'avg_sleep_quality': avg_sleep_quality
            }
            
            print("\nFinal Summary Stats:")
            print(f"Total TSS: {summary['total_tss']}")
            print(f"Total Hours: {summary['total_training_hours']}")
            print(f"Sessions: {summary['sessions_completed']}")
            print(f"Workout Types: {summary['workout_types']}")
            print(f"Number of daily workouts: {len(summary['qualitative_feedback'])}")
            print(f"Average Daily Energy: {summary['avg_daily_energy']}")
            print(f"Average Sleep Quality: {summary['avg_sleep_quality']}")
            print(f"Daily Sleep Quality: {summary['daily_sleep_quality']}")

            # Add weekly plan and any unmatched proposed workouts to summary
            summary.update({
                'weekly_plan': weekly_plan_data,
                'proposed_workouts': proposed_workouts
            })

            return summary
                
        except Exception as e:
            print(f"Error generating weekly summary: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            conn.close()

    def get_all_summaries(self) -> List[Dict[str, Any]]:
        """Retrieve all weekly summaries"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            c.execute('''
                SELECT id, start_date, end_date, summary_data 
                FROM weekly_summaries 
                ORDER BY start_date DESC
            ''')
            rows = c.fetchall()
            
            summaries = []
            for row in rows:
                summary_id, start_date, end_date, summary_data = row
                data = json.loads(summary_data)
                data['id'] = summary_id
                summaries.append(data)
            
            return summaries
            
        except Exception as e:
            print(f"Error retrieving summaries: {str(e)}")
            return []
            
        finally:
            conn.close()

    def save_weekly_summary(self, summary: Dict[str, Any]) -> bool:
        """Save or update a weekly summary"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            # Separate qualitative data
            qualitative_data = {
                'muscle_soreness_patterns': summary.get('muscle_soreness_patterns'),
                'general_fatigue_level': summary.get('general_fatigue_level')
            }

            # Create a copy of summary without qualitative data
            summary_data = summary.copy()
            summary_data.pop('muscle_soreness_patterns', None)
            summary_data.pop('general_fatigue_level', None)

            # Debug: Print the data being saved
            print("DEBUG: Summary data to save:", json.dumps(summary_data, indent=2))
            print("DEBUG: Qualitative data to save:", json.dumps(qualitative_data, indent=2))

            c.execute(
                '''
                INSERT OR REPLACE INTO weekly_summaries 
                (start_date, end_date, summary_data, qualitative_data, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''',
                (
                    summary['start_date'],
                    summary['end_date'],
                    json.dumps(summary_data),
                    json.dumps(qualitative_data)
                )
            )
            conn.commit()

            # Verify what was actually saved
            c.execute(
                '''
                SELECT qualitative_data, summary_data 
                FROM weekly_summaries 
                WHERE start_date = ? AND end_date = ?
                ''',
                (summary['start_date'], summary['end_date'])
            )
            result = c.fetchone()

            if result:
                qual_verify = json.loads(result[0]) if result[0] else {}
                print("DEBUG: Verification - Saved Qualitative Data:", json.dumps(qual_verify, indent=2))
                summary_verify = json.loads(result[1]) if result[1] else {}
                print("DEBUG: Verification - Saved Summary Data:", json.dumps(summary_verify, indent=2))

            return True
        except Exception as e:
            conn.rollback()
            print(f"Error saving weekly summary: {e}")
            return False
        finally:
            conn.close()

    def create_weekly_plan(self, weekNumber: int, startDate: str, plannedTSS_min: int, plannedTSS_max: int, notes: str) -> bool:
        """Create a new weekly plan"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                c.execute(
                    '''
                    INSERT INTO weekly_plans (weekNumber, startDate, plannedTSS_min, plannedTSS_max, notes)
                    VALUES (?, ?, ?, ?, ?)
                    ''',
                    (weekNumber, startDate, plannedTSS_min, plannedTSS_max, notes)
                )
                conn.commit()
                print(f"DEBUG: Successfully inserted weekly plan: {weekNumber}, {startDate}, {plannedTSS_min}, {plannedTSS_max}, {notes}")
                return True
        except Exception as e:
            print(f"Error creating weekly plan: {e}")
            return False

    def create_daily_plan(self, weekNumber: int, dayNumber: int, date: str) -> bool:
        """Create a new daily plan"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                c.execute(
                    '''
                    INSERT INTO daily_plans (weekNumber, dayNumber, date)
                    VALUES (?, ?, ?)
                    ''',
                    (weekNumber, dayNumber, date)
                )
                conn.commit()
                return True
        except Exception as e:
            print(f"Error creating daily plan: {e}")
            return False

    def create_proposed_workout(self, dailyPlanId: int, type: str, name: str, plannedDuration: int, plannedTSS_min: int, plannedTSS_max: int, targetRPE_min: int, targetRPE_max: int, intervals: str, sections: str) -> bool:
        """Create a new proposed workout"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                c.execute(
                    '''
                    INSERT INTO proposed_workouts (dailyPlanId, type, name, plannedDuration, plannedTSS_min, plannedTSS_max, targetRPE_min, targetRPE_max, intervals, sections)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (dailyPlanId, type, name, plannedDuration, plannedTSS_min, plannedTSS_max, targetRPE_min, targetRPE_max, intervals, sections)
                )
                conn.commit()
                return True
        except Exception as e:
            print(f"Error creating proposed workout: {e}")
            return False

    def get_daily_plan_id(self, weekNumber: int, dayNumber: int, date: str) -> Optional[int]:
        """Retrieve a daily plan ID by weekNumber and dayNumber"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                c.execute(
                    '''
                    SELECT id
                    FROM daily_plans
                    WHERE weekNumber = ? AND dayNumber = ?
                    ''',
                    (weekNumber, dayNumber)
                )
                result = c.fetchone()

                if result:
                    return result[0]
                else:
                    return None
        except Exception as e:
            print(f"Error retrieving daily plan ID: {e}")
            return None

    def proposed_workout_exists(self, dailyPlanId: int, type: str, name: str) -> bool:
        """Check if a proposed workout already exists"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                c.execute(
                    '''
                    SELECT 1
                    FROM proposed_workouts
                    WHERE dailyPlanId = ? AND type = ? AND name = ?
                    ''',
                    (dailyPlanId, type, name)
                )
                result = c.fetchone()
                return result is not None
        except Exception as e:
            print(f"Error checking if proposed workout exists: {e}")
            return False

    def get_weekly_plan(self, weekNumber: int) -> Optional[Dict[str, Any]]:
        """Retrieve a weekly plan by weekNumber"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        try:
            c.execute(
                '''
                SELECT weekNumber, startDate, plannedTSS_min, plannedTSS_max
                FROM weekly_plans
                WHERE weekNumber = ?
                ''',
                (weekNumber,)
            )
            row = c.fetchone()

            if row:
                return {
                    'weekNumber': row[0],
                    'startDate': row[1],
                    'plannedTSS_min': row[2],
                    'plannedTSS_max': row[3]
                }
            else:
                return None
        except Exception as e:
            print(f"Error retrieving weekly plan: {e}")
            return None
        finally:
            conn.close()

    def get_proposed_workouts(self, weekNumber: int) -> List[Dict[str, Any]]:
        """Retrieve proposed workouts for a specific week"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        try:
            c.execute(
                '''
                SELECT id, weekNumber, dayNumber, date, workouts
                FROM proposed_workouts
                WHERE weekNumber = ?
                ''',
                (weekNumber,)
            )
            rows = c.fetchall()

            workouts = []
            for row in rows:
                workouts.append({
                    'id': row[0],
                    'weekNumber': row[1],
                    'dayNumber': row[2],
                    'date': row[3],
                    'workouts': row[4]
                })
            return workouts
        except Exception as e:
            print(f"Error retrieving proposed workouts: {e}")
            return []
        finally:
            conn.close()

    def get_weekly_summary_qualitative_data(self, start_date: str, end_date: str) -> Optional[Dict[str, Any]]:
        """Retrieve qualitative data for a specific week"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            # Get the most recent qualitative data for the given date range
            c.execute(
                '''
                SELECT qualitative_data
                FROM weekly_summaries
                WHERE start_date = ? AND end_date = ?
                ORDER BY updated_at DESC
                LIMIT 1
            ''',
                (start_date, end_date)
            )
            
            result = c.fetchone()
            if result and result[0]:
                print("\nDEBUG: Retrieved qualitative data:", result[0])
                qual_data = json.loads(result[0])
                if qual_data.get('muscle_soreness_patterns') or qual_data.get('general_fatigue_level'):
                    return qual_data
            
            print("DEBUG: No qualitative data found for date range")
            return None
            
        except Exception as e:
            print(f"Error retrieving qualitative data: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
            
        finally:
            conn.close()
    
    def get_proposed_workouts_for_week(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Get all proposed workouts for a specific week"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            # First get the weekly plan
            c.execute(
                """
                SELECT weekNumber, startDate, plannedTSS_min, plannedTSS_max, notes
                FROM weekly_plans
                WHERE startDate = ?
                LIMIT 1
                """,
                (start_date,)
            )
            weekly_plan_row = c.fetchone()
            weekly_plan = None
            
            if weekly_plan_row:
                weekly_plan = {
                    'weekNumber': weekly_plan_row[0],
                    'startDate': weekly_plan_row[1],
                    'plannedTSS_min': weekly_plan_row[2],
                    'plannedTSS_max': weekly_plan_row[3],
                    'notes': weekly_plan_row[4]
                }
            
            # Get all daily plans and workouts for the week
            c.execute(
                """
                SELECT dp.id, dp.weekNumber, dp.dayNumber, dp.date, 
                    pw.id, pw.type, pw.name, pw.plannedDuration, 
                    pw.plannedTSS_min, pw.plannedTSS_max, 
                    pw.targetRPE_min, pw.targetRPE_max,
                    pw.intervals, pw.sections
                FROM daily_plans dp
                LEFT JOIN proposed_workouts pw ON dp.id = pw.dailyPlanId
                WHERE dp.date BETWEEN ? AND ?
                ORDER BY dp.date, pw.id
                """,
                (start_date, end_date)
            )
            rows = c.fetchall()
            
            # Process rows into a structured format
            daily_workouts = []
            for row in rows:
                if row[4] is not None:  # Only include rows that have a workout
                    workout = {
                        'id': row[4],
                        'daily_plan_id': row[0],
                        'week_number': row[1],
                        'day_number': row[2],
                        'date': row[3],
                        'type': row[5],
                        'name': row[6],
                        'plannedDuration': row[7],
                        'plannedTSS_min': row[8],
                        'plannedTSS_max': row[9],
                        'targetRPE_min': row[10],
                        'targetRPE_max': row[11],
                        'intervals': row[12],
                        'sections': row[13]
                    }
                    daily_workouts.append(workout)
            
            return {
                'weekly_plan': weekly_plan,
                'daily_workouts': daily_workouts
            }
            
        except Exception as e:
            print(f"Error getting proposed workouts: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'weekly_plan': None, 'daily_workouts': []}
        finally:
            conn.close()

    def save_workout_performance(self, workout_id: int, workout_date: str, 
                            actual_duration: int, performance_data: Dict[str, Any]) -> bool:
        """Save performance data for a specific workout (especially for strength and yoga workouts)"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        try:
            # Create table if it doesn't exist
            c.execute(
                """
                CREATE TABLE IF NOT EXISTS workout_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workout_id INTEGER NOT NULL,
                    workout_date TEXT NOT NULL,
                    actual_duration INTEGER,
                    performance_data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(workout_id, workout_date)
                )
                """
            )
            
            # Check if performance data already exists
            c.execute(
                """
                SELECT id FROM workout_performance
                WHERE workout_id = ? AND workout_date = ?
                """,
                (workout_id, workout_date)
            )
            result = c.fetchone()
            
            performance_data_json = json.dumps(performance_data) if performance_data else None
            
            if result:
                # Update existing performance data
                c.execute(
                    """
                    UPDATE workout_performance
                    SET actual_duration = ?, performance_data = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE workout_id = ? AND workout_date = ?
                    """,
                    (actual_duration, performance_data_json, workout_id, workout_date)
                )
            else:
                # Insert new performance data
                c.execute(
                    """
                    INSERT INTO workout_performance 
                    (workout_id, workout_date, actual_duration, performance_data)
                    VALUES (?, ?, ?, ?)
                    """,
                    (workout_id, workout_date, actual_duration, performance_data_json)
                )
            
            conn.commit()
            return True
            
        except Exception as e:
            conn.rollback()
            print(f"Error saving workout performance: {str(e)}")
            return False
        finally:
            conn.close()

    def get_workout_performance(self, workout_id: int, workout_date: str) -> Optional[Dict[str, Any]]:
        """Retrieve performance data for a specific workout"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        try:
            c.execute(
                """
                SELECT actual_duration, performance_data 
                FROM workout_performance
                WHERE workout_id = ? AND workout_date = ?
                """,
                (workout_id, workout_date)
            )
            result = c.fetchone()
            
            if result:
                actual_duration, performance_data_json = result
                
                performance_data = None
                if performance_data_json:
                    try:
                        performance_data = json.loads(performance_data_json)
                    except json.JSONDecodeError:
                        performance_data = None
                
                return {
                    'actual_duration': actual_duration,
                    'performance_data': performance_data
                }
            
            return None
            
        except Exception as e:
            print(f"Error retrieving workout performance: {str(e)}")
            return None
        finally:
            conn.close()