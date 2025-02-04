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
                workout_data = json.dumps(workout_with_qual)
                qual_data = existing[1]  # Keep existing qualitative data
            else:
                workout_data = json.dumps(workout)
                qual_data = None
            
            # Save workout with preserved qualitative data
            c.execute(
                '''
                INSERT OR REPLACE INTO workouts 
                (workout_day, workout_title, workout_data, qualitative_data, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''',
                (
                    workout['workout_day'],
                    workout['title'],
                    workout_data,
                    qual_data
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
                
                # Save both the complete workout data and separate qualitative data
                c.execute(
                    '''
                    UPDATE workouts 
                    SET workout_data = ?,
                        qualitative_data = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE workout_day = ? AND workout_title = ?
                    ''',
                    (
                        json.dumps(updated_workout),
                        json.dumps(qualitative_data),
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
            c.execute('SELECT workout_data, qualitative_data FROM workouts ORDER BY workout_day DESC')
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
            
    def generate_weekly_summary(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Generate a comprehensive weekly summary integrating all data sources"""
        print(f"\nDEBUG: Generating weekly summary")
        print(f"Start date: {start_date}, End date: {end_date}")
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            # Get all workouts for the date range
            query = '''
                SELECT w.workout_day, w.workout_title, w.workout_data, w.qualitative_data, f.fit_data
                FROM workouts w
                LEFT JOIN fit_files f 
                    ON w.workout_day = f.workout_day 
                    AND w.workout_title = f.workout_title
                WHERE w.workout_day BETWEEN ? AND ?
                ORDER BY w.workout_day
            '''
            
            print(f"\nExecuting query with dates: {start_date}, {end_date}")
            c.execute(query, (start_date, end_date))
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
            for day, title, workout_data, qual_data, fit_data in workout_rows:
                try:
                    print(f"\nProcessing workout: {title} on {day}")
                    
                    workout = json.loads(workout_data)
                    print(f"Raw workout data: {json.dumps(workout, indent=2)}")
                    
                    qualitative = json.loads(qual_data) if qual_data else {}
                    fit_metrics = json.loads(fit_data) if fit_data else {}
                    
                    # Get the workout type
                    workout_type = workout.get('type')
                    print(f"Workout type: {workout_type}")
                    if workout_type:
                        workout_types.add(workout_type)
                    
                    # Get metrics from all sources
                    csv_metrics = workout.get('metrics', {})
                    fit_metrics = fit_metrics.get('metrics', {}) if fit_metrics else {}
                    
                    # Process TSS
                    workout_tss = (
                        self._get_numeric_value(workout.get('TSS')) or
                        self._get_numeric_value(csv_metrics.get('actual_tss')) or
                        self._get_numeric_value(fit_metrics.get('tss'))
                    )
                    print(f"TSS: {workout_tss}")
                    total_tss += workout_tss
                    
                    # Process duration
                    duration = (
                        self._get_numeric_value(fit_metrics.get('duration')) or
                        self._get_numeric_value(csv_metrics.get('actual_duration')) or
                        self._get_numeric_value(workout.get('TimeTotalInHours', 0)) * 60
                    )
                    print(f"Duration: {duration}")
                    total_duration += duration
                    
                    # Combine power data from all sources
                    power_data = workout.get('power_data', {})
                    if fit_metrics.get('power_metrics'):
                        power_data.update(fit_metrics['power_metrics'])
                    print(f"Power data: {json.dumps(power_data, indent=2)}")
                    
                    # Combine heart rate data
                    hr_data = workout.get('heart_rate_data', {})
                    if fit_metrics.get('hr_metrics'):
                        hr_data.update(fit_metrics['hr_metrics'])
                    print(f"HR data: {json.dumps(hr_data, indent=2)}")
                    
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
                                'rpe': workout.get('Rpe')
                            },
                            'power_data': power_data if power_data else None,
                            'heart_rate_data': hr_data if hr_data else None
                        },
                        'feedback': qualitative
                    }
                    
                    daily_workouts.append(workout_entry)
                    print(f"Successfully added workout entry")
                    
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