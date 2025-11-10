# src/storage/database.py

import sqlite3
import json
from datetime import datetime
from typing import List, Optional, Dict, Any

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
                sequence_number INTEGER DEFAULT 1,
                fit_file_id INTEGER,
                UNIQUE(workout_day, workout_title, sequence_number)
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
                sequence_number INTEGER DEFAULT 1,
                UNIQUE(workout_day, workout_title, sequence_number)
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

        # Create athlete_settings table for persisted athlete defaults (FTP, HR zones, power zones)
        c.execute('''
            CREATE TABLE IF NOT EXISTS athlete_settings (
                athlete_id TEXT PRIMARY KEY,
                settings_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
                notes TEXT,
                FOREIGN KEY (dailyPlanId) REFERENCES daily_plans(id),
                UNIQUE(dailyPlanId, name) ON CONFLICT IGNORE
            )
        ''')
        
        # Migration: Add notes column if it doesn't exist
        try:
            c.execute("ALTER TABLE proposed_workouts ADD COLUMN notes TEXT")
            print("Added notes column to proposed_workouts table")
        except sqlite3.OperationalError:
            # Column already exists
            pass

        conn.commit()
        conn.close()
        
        # Handle database migration for existing databases
        self._migrate_database()
    
    def _migrate_database(self):
        """Migrate existing database to support sequence numbers for duplicate workouts"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            # Check if sequence_number column exists in workouts table
            c.execute("PRAGMA table_info(workouts)")
            columns = [column[1] for column in c.fetchall()]
            
            if 'sequence_number' not in columns:
                print("Migrating workouts table to add sequence_number column...")
                # Add sequence_number column
                c.execute("ALTER TABLE workouts ADD COLUMN sequence_number INTEGER DEFAULT 1")
                
                # Update existing records to have proper sequence numbers
                # Find duplicates and assign sequence numbers
                c.execute('''
                    SELECT workout_day, workout_title, COUNT(*) as count
                    FROM workouts
                    GROUP BY workout_day, workout_title
                    HAVING count > 1
                ''')
                duplicates = c.fetchall()
                
                for day, title, count in duplicates:
                    # Get all records for this day/title combination
                    c.execute('''
                        SELECT id FROM workouts 
                        WHERE workout_day = ? AND workout_title = ?
                        ORDER BY created_at
                    ''', (day, title))
                    records = c.fetchall()
                    
                    # Update each record with a sequence number
                    for i, (record_id,) in enumerate(records):
                        c.execute('''
                            UPDATE workouts 
                            SET sequence_number = ?
                            WHERE id = ?
                        ''', (i + 1, record_id))
                
                print(f"Updated {len(duplicates)} duplicate workout groups with sequence numbers")
            # Ensure fit_file_id column exists for workouts
            if 'fit_file_id' not in columns:
                try:
                    print("Migrating workouts table to add fit_file_id column...")
                    c.execute("ALTER TABLE workouts ADD COLUMN fit_file_id INTEGER")
                    print("Added fit_file_id column to workouts table")
                except Exception as e:
                    print(f"Error adding fit_file_id column to workouts: {e}")
            
            # Check if sequence_number column exists in fit_files table
            c.execute("PRAGMA table_info(fit_files)")
            columns = [column[1] for column in c.fetchall()]
            
            if 'sequence_number' not in columns:
                print("Migrating fit_files table to add sequence_number column...")
                # Add sequence_number column
                c.execute("ALTER TABLE fit_files ADD COLUMN sequence_number INTEGER DEFAULT 1")
                
                # Update existing records to have proper sequence numbers
                c.execute('''
                    SELECT workout_day, workout_title, COUNT(*) as count
                    FROM fit_files
                    GROUP BY workout_day, workout_title
                    HAVING count > 1
                ''')
                duplicates = c.fetchall()
                
                for day, title, count in duplicates:
                    # Get all records for this day/title combination
                    c.execute('''
                        SELECT id FROM fit_files 
                        WHERE workout_day = ? AND workout_title = ?
                        ORDER BY created_at
                    ''', (day, title))
                    records = c.fetchall()
                    
                    # Update each record with a sequence number
                    for i, (record_id,) in enumerate(records):
                        c.execute('''
                            UPDATE fit_files 
                            SET sequence_number = ?
                            WHERE id = ?
                        ''', (i + 1, record_id))
                
                print(f"Updated {len(duplicates)} duplicate fit file groups with sequence numbers")
            
            # Add FTP column to weekly_plans table if it doesn't exist
            c.execute("PRAGMA table_info(weekly_plans)")
            columns = [column[1] for column in c.fetchall()]
            if 'ftp' not in columns:
                c.execute("ALTER TABLE weekly_plans ADD COLUMN ftp INTEGER")
                print("Added FTP column to weekly_plans table")
            
            conn.commit()
            print("Database migration completed successfully")
            
        except Exception as e:
            print(f"Error during database migration: {e}")
            conn.rollback()
        finally:
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
        """Save or update FIT file data with sequence number support for duplicates"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()

        try:
            # Find the next available sequence number for this day/title combination
            c.execute('''
                SELECT COALESCE(MAX(sequence_number), 0) + 1
                FROM fit_files
                WHERE workout_day = ? AND workout_title = ?
            ''', (workout_day, workout_title))
            next_sequence = c.fetchone()[0]
            
            c.execute(
                '''
                INSERT OR REPLACE INTO fit_files
                (workout_day, workout_title, fit_data, file_name, sequence_number)
                VALUES (?, ?, ?, ?, ?)
                ''',
                (
                    workout_day,
                    workout_title,
                    json.dumps(fit_data),
                    file_name,
                    next_sequence
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
        """Save or update a workout while preserving qualitative data with sequence number support for duplicates"""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            # Find the next available sequence number for this day/title combination
            c.execute('''
                SELECT COALESCE(MAX(sequence_number), 0) + 1
                FROM workouts
                WHERE workout_day = ? AND workout_title = ?
            ''', (workout['workout_day'], workout['title']))
            next_sequence = c.fetchone()[0]
            
            # Check if workout exists and get any existing qualitative data
            c.execute(
                "SELECT workout_data, qualitative_data FROM workouts WHERE workout_day = ? AND workout_title = ? AND sequence_number = ?",
                (workout['workout_day'], workout['title'], next_sequence)
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
            
            # Save workout with preserved qualitative data and sequence number
            fit_file_id_val = workout.get('fit_file_id')
            c.execute(
                '''
                INSERT OR REPLACE INTO workouts
                (workout_day, workout_title, workout_data, qualitative_data, athlete_comments, sequence_number, fit_file_id, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''',
                (
                    workout['workout_day'],
                    workout['title'],
                    workout_data,
                    None,
                    athlete_comments,  # Ensure this field is saved
                    next_sequence,
                    fit_file_id_val
                )
            )
            
            conn.commit()
            print(f"Successfully saved workout: {workout['title']} on {workout['workout_day']} (sequence {next_sequence})")
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
            print("DEBUG: No duration match found, selecting first match by date/type")

        if best_match:
            print(f"DEBUG: Best match found: {json.dumps(best_match, indent=2)}")
        else:
            print("DEBUG: No match found")
            
        return best_match

    def generate_weekly_summary(self, start_date: str, end_date: str) -> Optional[Dict[str, Any]]:
        """Generate a comprehensive weekly summary integrating all data sources"""
        print("\nDEBUG: Generating weekly summary")
        print(f"Start date: {start_date}, End date: {end_date}")
        
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            # Get all workouts for the date range - updated to handle sequence numbers
            query = '''
                    SELECT w.workout_day, w.workout_title, w.workout_data, w.qualitative_data, w.athlete_comments, w.sequence_number, f.fit_data
                    FROM workouts w
                    LEFT JOIN fit_files f ON w.workout_day = f.workout_day 
                    AND w.workout_title = f.workout_title 
                    AND w.sequence_number = f.sequence_number
                    WHERE w.workout_day >= ? AND w.workout_day <= ?
                    ORDER BY w.workout_day, w.sequence_number
                    '''

            print(f"\nExecuting query with dates: {start_date}, {end_date}")

            # Debug: Check available workout days and their formats
            c.execute("SELECT workout_day, typeof(workout_day) FROM workouts ORDER BY workout_day")
            available_dates = c.fetchall()
            print("\nAvailable workout days in database:")
            for date in available_dates:
                print(f"  - {date[0]}")

            # Execute the main query
            c.execute(query, (start_date, end_date))
            workout_rows = c.fetchall()

            # Try to load persisted athlete settings (FTP / power zones) to guide zone computations
            try:
                athlete_settings = self.load_athlete_settings('default') or {}
                athlete_ftp_setting = None
                athlete_power_zone_bounds = None
                if athlete_settings and isinstance(athlete_settings, dict):
                    athlete_ftp_setting = athlete_settings.get('ftp') or athlete_settings.get('FTP')
                    athlete_power_zone_bounds = athlete_settings.get('power_zones') or athlete_settings.get('power_zones')
                    try:
                        if athlete_ftp_setting is not None:
                            athlete_ftp_setting = float(athlete_ftp_setting)
                    except Exception:
                        athlete_ftp_setting = None
            except Exception:
                athlete_ftp_setting = None
                athlete_power_zone_bounds = None

            # Initialize summary data
            total_tss = 0.0
            total_duration = 0.0
            sessions_completed = len(workout_rows)
            workout_types = set()
            daily_workouts = []
            daily_energy: Dict[str, float] = {}
            daily_sleep_quality: Dict[str, Dict[str, Optional[float]]] = {}
            
            # Process workouts
            for row in workout_rows:
                try:
                    day, title, workout_data, qual_data, athlete_comments, sequence_number, fit_data = row
                    print(f"\nProcessing workout: {title} on {day} (sequence {sequence_number})")
                    
                    workout = json.loads(workout_data)
                    print(f"Raw workout data: {json.dumps(workout, indent=2)}")
                    
                    qualitative = json.loads(qual_data) if qual_data else {}
                    
                    # Safely load fit_data. If the LEFT JOIN didn't find a matching fit row (sequence mismatch),
                    # try a fallback lookup for any fit_files entry matching day/title (use latest sequence).
                    fit_metrics = {}
                    matched_fit_id = None
                    if not fit_data:
                        try:
                            # First try fallback by exact title (most recent sequence) and capture id
                            c.execute(
                                '''
                                SELECT id, fit_data FROM fit_files
                                WHERE workout_day = ? AND workout_title = ?
                                ORDER BY sequence_number DESC
                                LIMIT 1
                                ''',
                                (day, title)
                            )
                            fallback = c.fetchone()
                            if fallback and fallback[1]:
                                matched_fit_id = fallback[0]
                                fit_data = fallback[1]
                                print(f"DEBUG: Fallback fit_data found for {title} on {day} (by exact title) - fit_id: {matched_fit_id}")
                            else:
                                    # As a more robust fallback, try to find the best FIT file for the same day.
                                    # If multiple FIT files exist for the day, choose the one whose average power
                                    # (from the FIT file) is closest to the workout's CSV average power when available.
                                    try:
                                        c.execute(
                                            '''
                                            SELECT id, fit_data, workout_title, file_name, sequence_number FROM fit_files
                                            WHERE workout_day = ?
                                            ''',
                                            (day,)
                                        )
                                        candidates = c.fetchall()
                                        if candidates:
                                            # Determine CSV average power if available for matching heuristic
                                            csv_avg = None
                                            try:
                                                csv_power = workout.get('metrics') or {}
                                                # Try common CSV keys for average power
                                                csv_avg = workout.get('power_data', {}).get('average') or csv_power.get('actual_average_power') or csv_power.get('average_power')
                                                if csv_avg is not None:
                                                    csv_avg = float(csv_avg)
                                            except Exception:
                                                csv_avg = None

                                            best_candidate = None
                                            best_diff = None
                                            for cand in candidates:
                                                fid, fdata, ftitle, fname, fseq = cand
                                                try:
                                                    parsed = json.loads(fdata) if fdata else {}
                                                except Exception:
                                                    parsed = {}

                                                pm = parsed.get('power_metrics') if isinstance(parsed, dict) else {}
                                                cand_avg = None
                                                if isinstance(pm, dict):
                                                    cand_avg = pm.get('average_power') or pm.get('average')
                                                try:
                                                    cand_avg = float(cand_avg) if cand_avg is not None else None
                                                except Exception:
                                                    cand_avg = None

                                                # If we have a csv_avg, choose candidate minimizing abs diff
                                                if csv_avg is not None and cand_avg is not None:
                                                    diff = abs(csv_avg - cand_avg)
                                                else:
                                                    # If we don't have numeric comparison data, prefer highest sequence (most recent)
                                                    diff = None

                                                if csv_avg is not None and diff is not None:
                                                    if best_diff is None or diff < best_diff:
                                                        best_diff = diff
                                                        best_candidate = (fid, fdata)
                                                else:
                                                    # fallback to preferring the highest sequence number if no numeric match possible
                                                    if best_candidate is None:
                                                        best_candidate = (fid, fdata)
                                                    else:
                                                        # prefer candidate with higher sequence_number
                                                        if fseq is not None and best_candidate:
                                                            if fseq > (best_candidate[0] or 0):
                                                                best_candidate = (fid, fdata)

                                            if best_candidate:
                                                matched_fit_id = best_candidate[0]
                                                fit_data = best_candidate[1]
                                                print(f"DEBUG: Selected best-fit fit_data for {title} on {day} - fit_id: {matched_fit_id}")
                                    except Exception as e:
                                        print(f"DEBUG: Error during fallback fit_files lookup: {e}")
                        except Exception as e:
                            print(f"DEBUG: Error during fallback fit_files lookup: {e}")

                    if fit_data:
                        try:
                            fit_metrics = json.loads(fit_data)
                            # Ensure all expected fields exist as at least empty dictionaries
                            if not isinstance(fit_metrics.get('metrics'), dict):
                                fit_metrics['metrics'] = {}
                            if not isinstance(fit_metrics.get('power_metrics'), dict):
                                fit_metrics['power_metrics'] = {}
                            if not isinstance(fit_metrics.get('hr_metrics'), dict):
                                fit_metrics['hr_metrics'] = {}
                        except json.JSONDecodeError as e:
                            print(f"Error decoding fit_data: {e}")
                            fit_metrics = {
                                'metrics': {},
                                'power_metrics': {},
                                'hr_metrics': {}
                            }
                    
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
                    power_data = workout.get('power_data', {}) or {}
                    if fit_metrics.get('power_metrics'):
                        # Preserve normalized power from FIT files
                        fit_power = fit_metrics['power_metrics']
                        # Merge FIT power metrics into the existing power_data but do not overwrite
                        # the canonical keys we use for export. We'll canonicalize names below.
                        power_data = {**power_data}  # shallow copy
                        if fit_power.get('normalized_power') is not None:
                            power_data['normalized_power'] = fit_power.get('normalized_power')
                        if fit_power.get('average_power') is not None:
                            power_data['average_power'] = fit_power.get('average_power')
                        if fit_power.get('max_power') is not None:
                            power_data['max_power'] = fit_power.get('max_power')
                        if fit_power.get('intensity_factor') is not None:
                            power_data['intensity_factor'] = fit_power.get('intensity_factor')
                        if fit_power.get('zones') is not None:
                            power_data['zones'] = fit_power.get('zones')

                    # Canonicalize power field names so downstream code can reliably read them.
                    canonical_power = {
                        'average': power_data.get('average') if power_data.get('average') is not None else power_data.get('average_power'),
                        'max': power_data.get('max') if power_data.get('max') is not None else power_data.get('max_power'),
                        # intensity_factor may appear as 'if' in CSV-derived data; accept both
                        'intensity_factor': power_data.get('intensity_factor') if power_data.get('intensity_factor') is not None else power_data.get('if'),
                        'zones': power_data.get('zones', {}),
                        'normalized_power': power_data.get('normalized_power')
                    }

                    print(f"Power data (canonical): {json.dumps(canonical_power, indent=2)}")

                    # Normalize/override power zone distribution if we have a persisted FTP or explicit numeric power zone bounds.
                    # Some FIT files include pre-computed zones that were calculated with a different FTP; prefer a simple
                    # heuristic: if normalized_power is present and athlete FTP or explicit zone bounds are available,
                    # place the bulk of time in the zone where normalized_power falls (more intuitive for exports).
                    try:
                        npower = canonical_power.get('normalized_power')
                        # Prefer to recompute percent-time-in-zone using raw power samples if available
                        power_series = None
                        fit_power = (fit_metrics.get('power_metrics') or {}) if fit_metrics else {}
                        if isinstance(fit_power, dict):
                            power_series = fit_power.get('power_series') or fit_metrics.get('power_series')

                        # Determine FTP to use for zone cutoffs: persisted athlete setting preferred,
                        # otherwise fall back to FTP recorded by the FIT parser if present
                        ftp_for_zones = None
                        if athlete_ftp_setting:
                            ftp_for_zones = athlete_ftp_setting
                        else:
                            # Defensive: fit_power may not always be a dict (could be a list, string, etc.)
                            # Normalize to dict when possible and safely extract ftp
                            if not isinstance(fit_power, dict):
                                try:
                                    if isinstance(fit_power, str):
                                        parsed = json.loads(fit_power)
                                        fit_power = parsed if isinstance(parsed, dict) else {}
                                    else:
                                        fit_power = {}
                                except Exception:
                                    fit_power = {}

                            ftp_for_zones = None
                            # Try common places for FTP: fit_power dict, then top-level fit_metrics
                            ftp_candidate = None
                            if isinstance(fit_power, dict):
                                ftp_candidate = fit_power.get('ftp')
                            if ftp_candidate is None and isinstance(fit_metrics, dict):
                                ftp_candidate = fit_metrics.get('ftp') or (fit_metrics.get('metrics') or {}).get('ftp')

                            # Use helper to defensively convert ftp_candidate to a numeric value.
                            # _get_numeric_value returns the provided default (None) when conversion
                            # isn't possible (e.g. dicts or malformed strings).
                            # Defensive numeric conversion for FTP candidate: only attempt to
                            # cast if it's a numeric or numeric string. Otherwise leave as None.
                            ftp_for_zones = None
                            if isinstance(ftp_candidate, (int, float)):
                                ftp_for_zones = float(ftp_candidate)
                            elif isinstance(ftp_candidate, str):
                                try:
                                    ftp_for_zones = float(ftp_candidate)
                                except Exception:
                                    ftp_for_zones = None

                        zones_override = None

                        # If we have raw power samples and either explicit numeric power bounds or an FTP, compute percent-time-in-zone
                        if power_series and (athlete_power_zone_bounds or ftp_for_zones):
                            try:
                                # Normalize samples to floats and filter invalid entries
                                samples = [float(x) for x in power_series if x is not None]
                                total = len(samples)
                                if total > 0:
                                    zone_names = [
                                        'Zone 1 (Recovery)',
                                        'Zone 2 (Endurance)',
                                        'Zone 3 (Tempo)',
                                        'Zone 4 (Threshold)',
                                        'Zone 5 (VO2 Max)'
                                    ]
                                    zones_override = {name: 0.0 for name in zone_names}

                                    if athlete_power_zone_bounds and isinstance(athlete_power_zone_bounds, list) and len(athlete_power_zone_bounds) >= 5:
                                        bounds = [float(b) for b in athlete_power_zone_bounds[:5]]
                                        lower = None
                                        for i, upper in enumerate(bounds):
                                            if lower is None:
                                                cnt = sum(1 for s in samples if s <= upper)
                                            else:
                                                cnt = sum(1 for s in samples if s > lower and s <= upper)
                                            zones_override[zone_names[i]] = (cnt / total) * 100.0
                                            lower = upper
                                        # Anything above highest bound goes to last zone
                                        if lower is not None:
                                            cnt = sum(1 for s in samples if s > lower)
                                            zones_override[zone_names[-1]] += (cnt / total) * 100.0
                                    elif ftp_for_zones:
                                        # Create numeric cutoffs from FTP using FitParser conventions
                                        cutoffs = [0.55, 0.75, 0.90, 1.05, 1.5]
                                        thresholds = [ftp_for_zones * c for c in cutoffs]
                                        lower = None
                                        for i, upper in enumerate(thresholds):
                                            if lower is None:
                                                cnt = sum(1 for s in samples if s <= upper)
                                            else:
                                                cnt = sum(1 for s in samples if s > lower and s <= upper)
                                            zones_override[zone_names[i]] = (cnt / total) * 100.0
                                            lower = upper
                                        if lower is not None:
                                            cnt = sum(1 for s in samples if s > lower)
                                            zones_override[zone_names[-1]] += (cnt / total) * 100.0
                            except Exception as e:
                                print(f"DEBUG: Error computing zones from power_series: {e}")

                        # If we couldn't compute percent-time zones from samples, fall back to simple single-zone override based on NP (legacy heuristic)
                        if zones_override is None:
                            if npower is not None:
                                # If explicit numeric bounds are persisted, use them
                                if athlete_power_zone_bounds and isinstance(athlete_power_zone_bounds, list) and len(athlete_power_zone_bounds) >= 5:
                                    bounds = athlete_power_zone_bounds
                                    zone_names = [
                                        'Zone 1 (Recovery)',
                                        'Zone 2 (Endurance)',
                                        'Zone 3 (Tempo)',
                                        'Zone 4 (Threshold)',
                                        'Zone 5 (VO2 Max)'
                                    ]
                                    zones_override = {name: 0.0 for name in zone_names}
                                    for i, b in enumerate(bounds[:5]):
                                        try:
                                            if npower <= float(b):
                                                zones_override[zone_names[i]] = 100.0
                                                break
                                        except Exception:
                                            continue
                                    if sum(zones_override.values()) == 0:
                                        zones_override[zone_names[-1]] = 100.0
                                elif athlete_ftp_setting:
                                    pct = npower / athlete_ftp_setting
                                    zone_names = [
                                        'Zone 1 (Recovery)',
                                        'Zone 2 (Endurance)',
                                        'Zone 3 (Tempo)',
                                        'Zone 4 (Threshold)',
                                        'Zone 5 (VO2 Max)'
                                    ]
                                    cutoffs = [0.55, 0.75, 0.90, 1.05, 1.5]
                                    zones_override = {name: 0.0 for name in zone_names}
                                    for i, cutoff in enumerate(cutoffs):
                                        if pct <= cutoff:
                                            zones_override[zone_names[i]] = 100.0
                                            break
                                    if sum(zones_override.values()) == 0:
                                        zones_override[zone_names[-1]] = 100.0

                        if zones_override is not None:
                            canonical_power['zones'] = zones_override
                    except Exception as e:
                        print(f"DEBUG: Could not override power zones: {e}")
                    
                    # Helper function to standardize heart rate zone format
                    def standardize_hr_zones(zones_data):
                        """Standardize heart rate zone format to use 'Zone X (Name)' format"""
                        if zones_data is None:
                            return {}
                            
                        if not isinstance(zones_data, dict):
                            print(f"Warning: zones_data is not a dictionary, got {type(zones_data)}: {zones_data}")
                            return {}

                        if not zones_data:  # Empty dict
                            return {}

                        # Mapping from different formats to standardized format
                        zone_name_mapping = {
                            'zone1': 'Zone 1 (Recovery)',
                            'zone2': 'Zone 2 (Endurance)',
                            'zone3': 'Zone 3 (Tempo)',
                            'zone4': 'Zone 4 (Threshold)',
                            'zone5': 'Zone 5 (Maximum)',
                            'Zone 1': 'Zone 1 (Recovery)',
                            'Zone 2': 'Zone 2 (Endurance)',
                            'Zone 3': 'Zone 3 (Tempo)',
                            'Zone 4': 'Zone 4 (Threshold)',
                            'Zone 5': 'Zone 5 (Maximum)',
                            'Zone 1 (Easy)': 'Zone 1 (Recovery)',
                            'Zone 2 (Moderate)': 'Zone 2 (Endurance)',
                            'Zone 3 (Hard)': 'Zone 3 (Tempo)',
                            'Zone 4 (Very Hard)': 'Zone 4 (Threshold)'
                        }

                        # Create a new standardized dictionary
                        standardized_zones = {}
                        
                        # Process each zone
                        try:
                            for zone_key, value in zones_data.items():
                                if zone_key is None or value is None:
                                    continue
                                    
                                # Convert numeric values safely
                                try:
                                    if isinstance(value, str):
                                        value = float(value)
                                except (ValueError, TypeError):
                                    # Skip invalid values
                                    print(f"Warning: Skipping invalid zone value: {value} for zone {zone_key}")
                                    continue
                                    
                                # Convert zone name to standard format if a mapping exists
                                standard_zone_name = zone_name_mapping.get(str(zone_key), zone_key)
                                standardized_zones[standard_zone_name] = value
                        except Exception as e:
                            print(f"Error standardizing zones: {str(e)}, zones_data: {zones_data}")
                            return {}
                                
                        return standardized_zones

                    # Combine heart rate data - prioritize workout CSV data over FIT file data
                    hr_data = workout.get('heart_rate_data', {})
                    
                    # Handle case where hr_data is None (outdoor rides without HR data)
                    if hr_data is None:
                        hr_data = {}
                    
                    # Extract and standardize zones from workout CSV data
                    csv_hr_zones = standardize_hr_zones(hr_data.get('zones', {}))
                    
                    # Only update with FIT metrics if workout CSV data doesn't have these fields
                    fit_hr = fit_metrics.get('hr_metrics', {})
                    if fit_hr:   # Check if fit_hr is a non-empty dictionary
                        # Keep original CSV data values if present
                        if 'average_hr' not in hr_data and fit_hr.get('average_hr'):
                            hr_data['average_hr'] = fit_hr.get('average_hr')
                        if 'max_hr' not in hr_data and fit_hr.get('max_hr'):
                            hr_data['max_hr'] = fit_hr.get('max_hr')
                        if 'min_hr' not in hr_data and fit_hr.get('min_hr'):
                            hr_data['min_hr'] = fit_hr.get('min_hr')
                        
                        # For zones, only use FIT data if we don't have CSV zone data
                        fit_hr_zones = fit_hr.get('zones', {})
                        if not csv_hr_zones and fit_hr_zones and isinstance(fit_hr_zones, dict):
                            hr_data['zones'] = standardize_hr_zones(fit_hr_zones)
                        else:
                            hr_data['zones'] = csv_hr_zones
                    else:
                        # No FIT data, just use CSV data
                        hr_data['zones'] = csv_hr_zones
                        
                    print(f"HR data after standardization: {json.dumps(hr_data, indent=2)}")

                    # Extract normalized power from fit_data
                    normalized_power = None
                    if fit_data:
                        try:
                            # We already loaded fit_data into fit_metrics earlier
                            power_metrics = fit_metrics.get('power_metrics')
                            if isinstance(power_metrics, dict):
                                normalized_power = power_metrics.get('normalized_power')
                                if normalized_power is not None:
                                    print(f"Successfully extracted normalized_power: {normalized_power}")
                        except Exception as e:
                            print(f"Could not extract normalized_power from fit_data: {str(e)}")

                    # Check for workout performance data (for strength and yoga workouts)
                    performance_data = None
                    if workout_type and workout_type.lower() in ('strength', 'yoga', 'other'):
                        # Find the workout ID first
                        c.execute(
                            '''
                            SELECT id FROM workouts 
                            WHERE workout_day = ? AND workout_title = ?
                            ''',
                            (day, title)
                        )
                        workout_id_row = c.fetchone()
                        if workout_id_row:
                            workout_id = workout_id_row[0]
                            
                            # Get performance data for this workout
                            c.execute(
                                '''
                                SELECT actual_duration, performance_data 
                                FROM workout_performance
                                WHERE workout_id = ? AND workout_date = ?
                                ''',
                                (workout_id, day)
                            )
                            performance_row = c.fetchone()
                            
                            if performance_row and performance_row[1]:
                                actual_duration, performance_data_json = performance_row
                                try:
                                    performance_data = json.loads(performance_data_json)
                                    print(f"Found performance data for workout {title} on {day}")
                                except json.JSONDecodeError:
                                    print(f"Error decoding performance data for workout {title} on {day}")
                                    performance_data = None

                    # Create workout entry with sequence number in title for multiple workouts same day
                    display_title = title
                    if sequence_number > 1:
                        display_title = f"{title} (#{sequence_number})"
                    
                    workout_entry = {
                        'day': day,
                        'type': workout_type,
                        'title': display_title,
                        'original_title': title,
                        'sequence_number': sequence_number,
                        'workout_data': {
                            'metrics': {
                                'actual_tss': workout_tss,
                                'actual_duration': duration,
                                'planned_tss': self._get_numeric_value(csv_metrics.get('planned_tss')),
                                'planned_duration': self._get_numeric_value(csv_metrics.get('planned_duration')),
                                'rpe': self._get_numeric_value(csv_metrics.get('rpe'))
                            },
                            'power_data': {
                                'average': canonical_power.get('average'),
                                'max': canonical_power.get('max'),
                                'intensity_factor': canonical_power.get('intensity_factor'),
                                'zones': canonical_power.get('zones', {}),
                                'normalized_power': canonical_power.get('normalized_power') if canonical_power.get('normalized_power') is not None else normalized_power
                            } if (power_data or normalized_power is not None) else None,
                            'heart_rate_data': hr_data if hr_data else None,
                            'performance_data': performance_data
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
                    # If we found a fallback fit_file, persist the association so future queries join directly
                    if matched_fit_id:
                        try:
                            c.execute(
                                '''
                                UPDATE workouts SET fit_file_id = ? WHERE workout_day = ? AND workout_title = ? AND sequence_number = ?
                                ''',
                                (matched_fit_id, day, title, sequence_number)
                            )
                            conn.commit()
                            print(f"DEBUG: Updated workout row to reference fit_file_id {matched_fit_id} for {title} on {day} (seq {sequence_number})")
                        except Exception as e:
                            print(f"DEBUG: Could not update workout with fit_file_id: {e}")
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
            total_energy = 0.0
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
                # Normalize numeric values (some may be None or strings)
                sleep_hours = self._get_numeric_value(metrics.get('Sleep Hours'), default=0)
                deep_sleep = self._get_numeric_value(metrics.get('Time In Deep Sleep'), default=0)
                light_sleep = self._get_numeric_value(metrics.get('Time In Light Sleep'), default=0)
                rem_sleep = self._get_numeric_value(metrics.get('Time In REM Sleep'), default=0)
                
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
                    print("DEBUG: No matching proposed workout found")

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

    def save_athlete_settings(self, athlete_id: str, settings: Dict[str, Any]) -> bool:
        """Persist athlete-specific settings (FTP, HR zones, power zones) as JSON."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                # Use SQLite upsert to insert or update by athlete_id
                c.execute(
                    '''
                    INSERT INTO athlete_settings (athlete_id, settings_json, created_at, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT(athlete_id) DO UPDATE SET
                        settings_json = excluded.settings_json,
                        updated_at = CURRENT_TIMESTAMP
                    ''',
                    (athlete_id, json.dumps(settings))
                )
                conn.commit()
                print(f"DEBUG: Saved athlete settings for {athlete_id}")
                return True
        except Exception as e:
            print(f"Error saving athlete settings: {e}")
            return False

    def load_athlete_settings(self, athlete_id: str) -> Optional[Dict[str, Any]]:
        """Load persisted athlete settings by athlete_id. Returns dict or None."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                c.execute(
                    '''
                    SELECT settings_json FROM athlete_settings WHERE athlete_id = ? LIMIT 1
                    ''',
                    (athlete_id,)
                )
                row = c.fetchone()
                if row and row[0]:
                    try:
                        return json.loads(row[0])
                    except json.JSONDecodeError:
                        return None
                return None
        except Exception as e:
            print(f"Error loading athlete settings: {e}")
            return None

    def delete_weekly_plan_cascade(self, weekNumber: int) -> bool:
        """Delete a weekly plan and all associated daily plans and proposed workouts"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                
                # First get all daily plan IDs for this week
                c.execute(
                    '''
                    SELECT id FROM daily_plans WHERE weekNumber = ?
                    ''',
                    (weekNumber,)
                )
                daily_plan_ids = [row[0] for row in c.fetchall()]
                
                # Delete associated proposed workouts
                if daily_plan_ids:
                    placeholders = ', '.join(['?'] * len(daily_plan_ids))
                    c.execute(
                        f'''
                        DELETE FROM proposed_workouts
                        WHERE dailyPlanId IN ({placeholders})
                        ''',
                        daily_plan_ids
                    )
                    print(f"DEBUG: Deleted proposed workouts for week {weekNumber}")
                
                # Delete daily plans
                c.execute(
                    '''
                    DELETE FROM daily_plans WHERE weekNumber = ?
                    ''',
                    (weekNumber,)
                )
                print(f"DEBUG: Deleted daily plans for week {weekNumber}")
                
                # Delete weekly plan
                c.execute(
                    '''
                    DELETE FROM weekly_plans WHERE weekNumber = ?
                    ''',
                    (weekNumber,)
                )
                print(f"DEBUG: Deleted weekly plan {weekNumber}")
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Error deleting weekly plan cascade: {e}")
            return False
    
    def create_weekly_plan(self, weekNumber: int, startDate: str, plannedTSS_min: int, plannedTSS_max: int, notes: str, ftp: Optional[int] = None) -> bool:
        """Create a new weekly plan"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                c.execute(
                    '''
                    INSERT INTO weekly_plans (weekNumber, startDate, plannedTSS_min, plannedTSS_max, notes, ftp)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ''',
                    (weekNumber, startDate, plannedTSS_min, plannedTSS_max, notes, ftp)
                )
                conn.commit()
                print(f"DEBUG: Successfully inserted weekly plan: {weekNumber}, {startDate}, {plannedTSS_min}, {plannedTSS_max}, {notes}, FTP: {ftp}")
                return True
        except Exception as e:
            print(f"Error creating weekly plan: {e}")
            return False

    def create_daily_plan(self, weekNumber: int, dayNumber: int, date: str) -> bool:
        """Create a new daily plan or update an existing one, preventing duplicates"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                
                # First check if a plan with exact same weekNumber, dayNumber, date exists
                c.execute(
                    '''
                    SELECT id FROM daily_plans 
                    WHERE weekNumber = ? AND dayNumber = ? AND date = ?
                    ''', 
                    (weekNumber, dayNumber, date)
                )
                exact_match = c.fetchone()
                
                if exact_match:
                    print(f"Exact daily plan already exists: {weekNumber}, {dayNumber}, {date}")
                    return True
                
                # Check if a daily plan with this weekNumber and dayNumber exists but date is different
                c.execute(
                    '''
                    SELECT id, date FROM daily_plans 
                    WHERE weekNumber = ? AND dayNumber = ? 
                    LIMIT 1
                    ''', 
                    (weekNumber, dayNumber)
                )
                existing_plan = c.fetchone()
                
                if existing_plan:
                    # Update the date
                    plan_id, current_date = existing_plan
                    if current_date != date:
                        c.execute(
                            '''
                            UPDATE daily_plans 
                            SET date = ? 
                            WHERE id = ?
                            ''', 
                            (date, plan_id)
                        )
                        print(f"Updated daily plan date from {current_date} to {date} for plan with ID {plan_id}")
                    return True
                
                # No existing plan found, insert a new one
                c.execute(
                    '''
                    INSERT INTO daily_plans (weekNumber, dayNumber, date)
                    VALUES (?, ?, ?)
                    ''',
                    (weekNumber, dayNumber, date)
                )
                print(f"Created new daily plan: {weekNumber}, {dayNumber}, {date}")
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Error creating/updating daily plan: {e}")
            return False

    def create_proposed_workout(self, dailyPlanId: int, type: str, name: str, plannedDuration: int, plannedTSS_min: int, plannedTSS_max: int, targetRPE_min: int, targetRPE_max: int, intervals: str, sections: str, notes: Optional[str] = None) -> bool:
        """Create a new proposed workout or update existing one"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                
                # Check if a proposed workout with this dailyPlanId and name already exists
                c.execute(
                    '''
                    SELECT id FROM proposed_workouts 
                    WHERE dailyPlanId = ? AND name = ?
                    ''',
                    (dailyPlanId, name)
                )
                existing_workout = c.fetchone()
                
                if existing_workout:
                    # Update the existing workout with new values
                    workout_id = existing_workout[0]
                    c.execute(
                        '''
                        UPDATE proposed_workouts 
                        SET type = ?, plannedDuration = ?, 
                            plannedTSS_min = ?, plannedTSS_max = ?,
                            targetRPE_min = ?, targetRPE_max = ?,
                            intervals = ?, sections = ?, notes = ?
                        WHERE id = ?
                        ''',
                        (type, plannedDuration, plannedTSS_min, plannedTSS_max, 
                         targetRPE_min, targetRPE_max, intervals, sections, notes or "", workout_id)
                    )
                    print(f"Updated existing proposed workout '{name}' for dailyPlanId {dailyPlanId}")
                else:
                    # Insert a new workout
                    c.execute(
                        '''
                        INSERT INTO proposed_workouts 
                        (dailyPlanId, type, name, plannedDuration, plannedTSS_min, plannedTSS_max, 
                         targetRPE_min, targetRPE_max, intervals, sections, notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''',
                        (dailyPlanId, type, name, plannedDuration, plannedTSS_min, plannedTSS_max, 
                         targetRPE_min, targetRPE_max, intervals, sections, notes or "")
                    )
                    print(f"Created new proposed workout '{name}' for dailyPlanId {dailyPlanId}")
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Error creating/updating proposed workout: {e}")
            return False

    def get_daily_plan_id(self, weekNumber: int, dayNumber: int, date: str) -> Optional[int]:
        """Retrieve a daily plan ID by weekNumber, dayNumber, and date"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                c = conn.cursor()
                # First try to get an exact match on all three fields
                c.execute(
                    '''
                    SELECT id
                    FROM daily_plans
                    WHERE weekNumber = ? AND dayNumber = ? AND date = ?
                    ''',
                    (weekNumber, dayNumber, date)
                )
                result = c.fetchone()

                if result:
                    return result[0]
                
                # If no exact match, try with weekNumber and dayNumber
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
                    # Update the date to match the correct one from the JSON
                    c.execute(
                        '''
                        UPDATE daily_plans
                        SET date = ?
                        WHERE id = ?
                        ''',
                        (date, result[0])
                    )
                    conn.commit()
                    print(f"Updated daily plan date to {date} for plan ID {result[0]}")
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
                SELECT weekNumber, startDate, plannedTSS_min, plannedTSS_max, notes, ftp
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
                    'notes': weekly_plan_row[4],
                    'ftp': weekly_plan_row[5]
                }
            
            # Get all daily plans and workouts for the week
            c.execute(
                """
                SELECT dp.id, dp.weekNumber, dp.dayNumber, dp.date, 
                    pw.id, pw.type, pw.name, pw.plannedDuration, 
                    pw.plannedTSS_min, pw.plannedTSS_max, 
                    pw.targetRPE_min, pw.targetRPE_max,
                    pw.intervals, pw.sections, pw.notes
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
                        'sections': row[13],
                        'notes': row[14]
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
                print(f"Updated workout performance data for workout ID {workout_id} on {workout_date}")
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
                print(f"Created new workout performance data for workout ID {workout_id} on {workout_date}")
            
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

    def get_all_workouts_for_week(self, start_date: str, end_date: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get both completed and proposed workouts for a specific week.
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            Dictionary containing two lists:
            - completed_workouts: List of completed workouts from the workouts table
            - proposed_workouts: List of proposed workouts from the proposed_workouts table
        """
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        
        try:
            # Get completed workouts
            c.execute(
                '''
                SELECT workout_day, workout_title, workout_data, qualitative_data, athlete_comments
                FROM workouts 
                WHERE workout_day BETWEEN ? AND ?
                ORDER BY workout_day
                ''',
                (start_date, end_date)
            )
            completed_rows = c.fetchall()
            
            completed_workouts = []
            for row in completed_rows:
                workout_day, title, workout_data, qual_data, comments = row
                workout = json.loads(workout_data)
                if qual_data:
                    workout.update(json.loads(qual_data))
                workout['athlete_comments'] = comments
                workout['date'] = workout_day
                workout['title'] = title
                completed_workouts.append(workout)
            
            # Get proposed workouts
            c.execute(
                '''
                SELECT dp.date, pw.type, pw.name, pw.plannedDuration, 
                    pw.plannedTSS_min, pw.plannedTSS_max, 
                    pw.targetRPE_min, pw.targetRPE_max,
                    pw.intervals, pw.sections
                FROM daily_plans dp
                JOIN proposed_workouts pw ON dp.id = pw.dailyPlanId
                WHERE dp.date BETWEEN ? AND ?
                ORDER BY dp.date
                ''',
                (start_date, end_date)
            )
            proposed_rows = c.fetchall()
            
            proposed_workouts = []
            for row in proposed_rows:
                workout = {
                    'date': row[0],
                    'type': row[1],
                    'name': row[2],
                    'plannedDuration': row[3],
                    'plannedTSS_min': row[4],
                    'plannedTSS_max': row[5],
                    'targetRPE_min': row[6],
                    'targetRPE_max': row[7],
                    'intervals': row[8],
                    'sections': row[9]
                }
                proposed_workouts.append(workout)
            
            return {
                'completed_workouts': completed_workouts,
                'proposed_workouts': proposed_workouts
            }
            
        except Exception as e:
            print(f"Error retrieving workouts: {str(e)}")
            import traceback
            traceback.print_exc()
            return {'completed_workouts': [], 'proposed_workouts': []}
        finally:
            conn.close()