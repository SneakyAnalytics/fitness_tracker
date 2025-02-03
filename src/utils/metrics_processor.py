from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, date
import pandas as pd
from .fit_parser import FitParser

class MetricsProcessor:
    def __init__(self):
        self.fit_parser = FitParser()
        self.sleep_metrics = {}  # Will store metrics by date
        self.workouts = {}      # Will store workouts by date
        self.fit_data = {}      # Will store FIT data by date and workout title
        self.body_battery = {}  # Will store body battery metrics by date

    def process_metrics_csv(self, metrics_data: str):
        """Process sleep and body battery metrics CSV data"""
        df = pd.read_csv(pd.StringIO(metrics_data))
        print("DEBUG: Initial metrics dataframe:")
        print(df.head())

        for _, row in df.iterrows():
            date_str = row['Timestamp'].split()[0]  # Get just the date part
            print(f"DEBUG: Processing metrics for date {date_str}")
            metric_type = row['Type']
            value = row['Value']
            
            if metric_type == 'Body Battery':
                # Parse the body battery value string
                parsed_value = self.parse_metric_value(value)
                self.body_battery[date_str] = parsed_value.get('avg', None)
            else:
                if date_str not in self.sleep_metrics:
                    self.sleep_metrics[date_str] = {}
                self.sleep_metrics[date_str][metric_type] = value

        # Calculate sleep quality score for each date
        for date_str, metrics in self.sleep_metrics.items():
            self.sleep_metrics[date_str]['sleep_quality_score'] = self.calculate_sleep_quality_score(metrics)
            print(f"DEBUG: Calculated sleep quality score for {date_str}: {self.sleep_metrics[date_str]['sleep_quality_score']}")

    def calculate_sleep_quality_score(self, metrics: Dict[str, Any]) -> float:
        """Calculate a composite sleep quality score based on various metrics"""
        # Extract base metrics with error handling
        try:
            total_sleep = float(metrics.get('Sleep Hours', 0))
            deep_sleep = float(metrics.get('Time In Deep Sleep', 0))
            light_sleep = float(metrics.get('Time In Light Sleep', 0))
            rem_sleep = float(metrics.get('Time In REM Sleep', 0))
            time_awake = float(metrics.get('Time Awake', 0))
            hrv = float(metrics.get('HRV', 0))
            pulse = float(metrics.get('Pulse', 0))
            stress_level = self.parse_metric_value(metrics.get('Stress Level', '0')).get('avg', 0)
            stress_qualifier = metrics.get('Stress Qualifier', '').lower()
        except (ValueError, TypeError) as e:
            print(f"DEBUG: Error extracting metrics: {e}")
            return 1.0  # Return minimum score if data is invalid

        # Calculate sleep stage percentages
        total_sleep_minutes = total_sleep * 60
        if total_sleep_minutes == 0:
            print("DEBUG: Total sleep minutes is 0, returning minimum score")
            return 1.0

        deep_sleep_pct = (deep_sleep / total_sleep_minutes) * 100
        rem_sleep_pct = (rem_sleep / total_sleep_minutes) * 100
        light_sleep_pct = (light_sleep / total_sleep_minutes) * 100
        awake_pct = (time_awake / total_sleep_minutes) * 100

        print(f"DEBUG: Sleep stages - Deep: {deep_sleep_pct}%, REM: {rem_sleep_pct}%, Light: {light_sleep_pct}%, Awake: {awake_pct}%")

        # Define ideal ranges based on research
        weights = {
            'duration': 0.30,  # 30% - Most important factor
            'deep_sleep': 0.25,  # 25% - Critical for physical recovery
            'rem_sleep': 0.20,  # 20% - Important for mental recovery
            'efficiency': 0.15,  # 15% - Time awake impacts overall quality
            'recovery': 0.10,  # 10% - HRV and RHR indicate recovery state
        }

        # Score each component (1-5 scale)
        duration_score = self._score_duration(total_sleep)
        deep_sleep_score = self._score_sleep_stage(deep_sleep_pct, ideal_range=(20, 25))
        rem_sleep_score = self._score_sleep_stage(rem_sleep_pct, ideal_range=(20, 25))
        
        # Efficiency score (penalize time awake)
        efficiency_score = 5 - min(5, (awake_pct / 10))
        
        # Recovery score based on HRV and RHR
        recovery_score = self._calculate_recovery_score(hrv, pulse, stress_level, stress_qualifier)

        # Calculate weighted final score
        final_score = (
            weights['duration'] * duration_score +
            weights['deep_sleep'] * deep_sleep_score +
            weights['rem_sleep'] * rem_sleep_score +
            weights['efficiency'] * efficiency_score +
            weights['recovery'] * recovery_score
        )

        # Ensure score is between 1-5
        final_score = max(1.0, min(5.0, final_score))
        print(f"DEBUG: Final sleep quality score: {final_score}")
        return final_score

    def _score_duration(self, hours: float) -> float:
        """Score sleep duration on a 1-5 scale"""
        if hours >= 7 and hours <= 9:
            return 5.0
        elif hours >= 6 and hours < 7:
            return 4.0
        elif hours >= 5 and hours < 6:
            return 3.0
        elif hours >= 4 and hours < 5:
            return 2.0
        else:
            return 1.0

    def _score_sleep_stage(self, percentage: float, ideal_range: Tuple[float, float]) -> float:
        """Score sleep stage percentage on a 1-5 scale"""
        min_ideal, max_ideal = ideal_range
        if percentage >= min_ideal and percentage <= max_ideal:
            return 5.0
        elif percentage >= min_ideal * 0.8 and percentage <= max_ideal * 1.2:
            return 4.0
        elif percentage >= min_ideal * 0.6 and percentage <= max_ideal * 1.4:
            return 3.0
        elif percentage >= min_ideal * 0.4 and percentage <= max_ideal * 1.6:
            return 2.0
        else:
            return 1.0

    def _calculate_recovery_score(self, hrv: float, rhr: float, stress_level: float, 
                                stress_qualifier: str) -> float:
        """Calculate recovery score based on HRV, RHR, and stress metrics"""
        # Base score on HRV and RHR trends
        recovery_score = 3.0  # Start at neutral
        
        # Adjust for HRV (higher is better)
        if hrv > 0:
            recovery_score += min(1.0, hrv / 100)
        
        # Adjust for RHR (lower is better)
        if rhr > 0:
            recovery_score -= min(1.0, (rhr - 40) / 100)
        
        # Adjust for stress
        stress_adjustments = {
            'calm': 0.5,
            'balanced': 0.0,
            'stressful': -0.5
        }
        recovery_score += stress_adjustments.get(stress_qualifier, 0.0)
        
        # Ensure score is between 1-5
        return max(1.0, min(5.0, recovery_score))

    def parse_metric_value(self, value_str: str) -> Dict[str, float]:
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

    def process_workouts_csv(self, workouts_data: str):
        """Process workouts CSV data"""
        df = pd.read_csv(pd.StringIO(workouts_data))
        
        for _, row in df.iterrows():
            workout_date = row['WorkoutDay']
            workout_title = row['Title']
            
            if workout_date not in self.workouts:
                self.workouts[workout_date] = []
            
            self.workouts[workout_date].append({
                'title': workout_title,
                'type': row['WorkoutType'],
                'planned_duration': row.get('PlannedDuration'),
                'actual_duration': row.get('TimeTotalInHours', 0) * 60 if pd.notna(row.get('TimeTotalInHours')) else None,
                'tss': row.get('TSS'),
                'if': row.get('IF'),
                'rpe': row.get('Rpe'),
                'feeling': row.get('Feeling'),
                'power_avg': row.get('PowerAverage'),
                'power_max': row.get('PowerMax'),
                'hr_avg': row.get('HeartRateAverage'),
                'hr_max': row.get('HeartRateMax')
            })

    def add_fit_data(self, date: str, workout_title: str, fit_content: bytes):
        """Add FIT file data for a specific workout"""
        if date not in self.fit_data:
            self.fit_data[date] = {}
            
        print(f"Adding FIT data for {workout_title} on {date}")
        parsed_data = self.fit_parser.parse_fit_file(fit_content)
        if parsed_data:
            self.fit_data[date][workout_title] = parsed_data

    def get_combined_workout_data(self, date: str, workout_title: str) -> Dict[str, Any]:
        """Combine all data sources for a specific workout"""
        workout_data = {}
        
        # Get base workout data from CSV
        if date in self.workouts:
            for workout in self.workouts[date]:
                if workout['title'] == workout_title:
                    workout_data.update(workout)
                    break
        
        # Add FIT file data if available
        if date in self.fit_data and workout_title in self.fit_data[date]:
            fit_data = self.fit_data[date][workout_title]
            print(f"FIT data for {workout_title} on {date}: {fit_data}")
            # Update or add detailed metrics
            if 'power_metrics' in fit_data:
                workout_data['power_data'] = fit_data['power_metrics']
            if 'hr_metrics' in fit_data:
                workout_data['heart_rate_data'] = fit_data['hr_metrics']
            
            # Update basic metrics if not already present
            if not workout_data.get('tss') and fit_data.get('metrics', {}).get('tss'):
                workout_data['tss'] = fit_data['metrics']['tss']
            if not workout_data.get('actual_duration') and fit_data.get('metrics', {}).get('duration'):
                workout_data['actual_duration'] = fit_data['metrics']['duration']

        # Add sleep metrics if available
        if date in self.sleep_metrics:
            workout_data['sleep_metrics'] = self.sleep_metrics[date]

        return workout_data

    def get_weekly_summary(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Generate a weekly summary combining all data sources"""
        summary = {
            'start_date': start_date,
            'end_date': end_date,
            'total_tss': 0,
            'total_training_hours': 0,
            'sessions_completed': 0,
            'workout_types': set(),
            'daily_metrics': {},
            'sleep_quality': {},
            'workouts': [],
            'daily_energy': {}
        }
        
        # Process each day in the range
        current_date = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        
        while current_date <= end:
            date_str = current_date.strftime('%Y-%m-%d')
            
            # Add sleep metrics
            if date_str in self.sleep_metrics:
                summary['sleep_quality'][date_str] = self.sleep_metrics[date_str]
            
            # Add body battery metrics
            if date_str in self.body_battery:
                summary['daily_energy'][date_str] = self.body_battery[date_str]
            
            # Process workouts for the day
            if date_str in self.workouts:
                for workout in self.workouts[date_str]:
                    # Get combined data for this workout
                    full_workout_data = self.get_combined_workout_data(
                        date_str,
                        workout['title']
                    )
                    
                    # Update summary metrics
                    if 'tss' in full_workout_data:
                        summary['total_tss'] += full_workout_data['tss']
                    if 'actual_duration' in full_workout_data:
                        summary['total_training_hours'] += full_workout_data['actual_duration'] / 60
                    
                    summary['sessions_completed'] += 1
                    summary['workout_types'].add(full_workout_data['type'])
                    summary['workouts'].append(full_workout_data)
            
            current_date += pd.Timedelta(days=1)
        
        # Convert workout_types to list for JSON serialization
        summary['workout_types'] = list(summary['workout_types'])
        
        return summary