from typing import Dict, List, Any, Optional
from datetime import datetime, date
import pandas as pd
from .fit_parser import FitParser

class MetricsProcessor:
    def __init__(self):
        self.fit_parser = FitParser()
        self.sleep_metrics = {}  # Will store metrics by date
        self.workouts = {}      # Will store workouts by date
        self.fit_data = {}      # Will store FIT data by date and workout title

    def process_metrics_csv(self, metrics_data: str):
        """Process sleep metrics CSV data"""
        df = pd.read_csv(pd.StringIO(metrics_data))
        
        for _, row in df.iterrows():
            date_str = row['Timestamp'].split()[0]  # Get just the date part
            self.sleep_metrics[date_str] = {
                'type': row['Type'],
                'value': row['Value']
            }

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
            'workouts': []
        }
        
        # Process each day in the range
        current_date = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        
        while current_date <= end:
            date_str = current_date.strftime('%Y-%m-%d')
            
            # Add sleep metrics
            if date_str in self.sleep_metrics:
                summary['sleep_quality'][date_str] = self.sleep_metrics[date_str]
            
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