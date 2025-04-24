# src/api/app.py

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
import pandas as pd
import pytz
import numpy as np
import io
from pydantic import BaseModel
import json


from ..storage.database import WorkoutDatabase
from ..models.workout import DailyWorkout, WeeklySummary
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

def clean_float(value: Any) -> Optional[float]:
    """Clean float values, handling NaN and infinite values"""
    if pd.isna(value) or pd.isnull(value):
        return None
    if isinstance(value, (int, float)):
        if np.isinf(value) or np.isneginf(value):
            return None
        return float(value)
    return None

def generate_workout_analysis(workout_data: Dict[str, Any]) -> Dict[str, str]:
    """Generate AI analysis of workout data"""
    
    # Create structured prompt for power analysis
    power_prompt = """Analyze this workout's power data:
    - Average Power: {avg_power}W
    - Normalized Power: {norm_power}W
    - Intensity Factor: {intensity}
    - Zone Distribution: {zones}
    
    Provide a brief analysis of:
    1. Overall intensity and distribution
    2. Workout type (based on zone distribution)
    3. Training impact and recovery needs
    """
    
    # Create structured prompt for heart rate analysis
    hr_prompt = """Analyze this workout's heart rate response:
    - Average HR: {avg_hr}bpm
    - Max HR: {max_hr}bpm
    - HR Zone Distribution: {zones}
    
    Consider:
    1. Cardiovascular strain
    2. Time spent in different zones
    3. Recovery implications
    """
    
    # Format prompts with actual data
    if workout_data.get('power_metrics'):
        power_analysis = power_prompt.format(
            avg_power=workout_data['power_metrics']['average_power'],
            norm_power=workout_data['power_metrics']['normalized_power'],
            intensity=workout_data['power_metrics']['intensity_factor'],
            zones=workout_data['power_metrics']['zones']
        )
    else:
        power_analysis = None
    
    if workout_data.get('hr_metrics'):
        hr_analysis = hr_prompt.format(
            avg_hr=workout_data['hr_metrics']['average_hr'],
            max_hr=workout_data['hr_metrics']['max_hr'],
            zones=workout_data.get('hr_metrics', {}).get('zones', 'N/A')
        )
    else:
        hr_analysis = None
    
    # TODO: Integrate with actual AI analysis
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
    def calculate_zone_percentages(zone_minutes: Dict[str, float]) -> Dict[str, float]:
        total_minutes = sum(v for v in zone_minutes.values() if pd.notna(v))
        if total_minutes > 0:
            return {
                k: (v / total_minutes) * 100 if pd.notna(v) else 0 
                for k, v in zone_minutes.items()
            }
        return zone_minutes

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

@app.get("/")
async def root():
    return {"message": "Fitness Tracker API is running"}

@app.get("/workouts")
async def get_workouts():
    db = WorkoutDatabase()
    return db.get_all_workouts()

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
        
        # Basic validation of CSV structure
        df = pd.read_csv(io.StringIO(decoded_contents))
        required_columns = ['Title', 'WorkoutType', 'WorkoutDay']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Convert date format for consistency
        df['WorkoutDay'] = pd.to_datetime(df['WorkoutDay']).dt.strftime('%Y-%m-%d')
        
        workouts = []
        for _, row in df.iterrows():
            print(f"Processing workout: {row['Title']} on {row['WorkoutDay']}")
            
            # Calculate zone percentages based on minutes
            def calculate_zone_percentages(zone_minutes: Dict[str, float], total_minutes: float) -> Dict[str, float]:
                if total_minutes > 0:
                    return {
                        k: (v / total_minutes) * 100 if pd.notna(v) else 0 
                        for k, v in zone_minutes.items()
                    }
                return zone_minutes
            
            actual_duration = clean_float(row.get('TimeTotalInHours', 0) * 60) if pd.notna(row.get('TimeTotalInHours')) else None
            
            workout = {
                'title': str(row['Title']).strip(),
                'type': str(row['WorkoutType']).strip(),
                'workout_day': str(row['WorkoutDay']).strip(),
                'metrics': {
                    'actual_tss': float(row['TSS']) if pd.notna(row.get('TSS')) else None,
                    'actual_duration': actual_duration,
                    'rpe': float(row['Rpe']) if pd.notna(row.get('Rpe')) else None,  # Include RPE value
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
                    }, actual_duration)
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
                    }, actual_duration)
                } if pd.notna(row.get('HeartRateAverage')) else None,
                'athlete_comments': str(row.get('AthleteComments')) if pd.notna(row.get('AthleteComments')) else None  # Ensure this field is included
            }
            
            # Clean workout data
            cleaned_workout = clean_workout_data(workout)

            # Save to database
            db = WorkoutDatabase()
            if db.save_workout(cleaned_workout):
                workouts.append(cleaned_workout)
                print(f"Saved workout: {workout['title']} on {workout['workout_day']}")
            else:
                print(f"Failed to save workout: {workout['title']} on {workout['workout_day']}")
        
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
        
        # Parse CSV
        df = pd.read_csv(
            io.StringIO(decoded_contents),
            on_bad_lines='skip',
            skipinitialspace=True
        )
        
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
                'how_it_felt': data.how_it_felt,
                'technical_issues': data.technical_issues,
                'modifications': data.modifications,
                'athlete_comments': data.athlete_comments
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

        # Start building content with weekly plan details
        content = [
            "## Overall Weekly Summary"
        ]
        
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
            feedback = workout.get('feedback', {})
            athlete_comments = feedback.get('athlete_comments')
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
async def upload_fit_file(file: UploadFile = File(...)):
    """Handle FIT file upload"""
    try:
        print(f"Processing FIT file: {file.filename}")
        contents = await file.read()
        
        # Parse date from filename and standardize format
        date = None
        filename = file.filename

        # First parse the FIT file
        fit_parser = FitParser()
        try:
            parsed_data = fit_parser.parse_fit_file(contents)
            # Ensure we always have a dictionary, even if parsing fails
            if parsed_data is None:
                print(f"Warning: FIT file parsing returned None for {file.filename}")
                parsed_data = {}
        except Exception as e:
            print(f"Error parsing FIT file {file.filename}: {str(e)}")
            parsed_data = {}
        
        # Then handle date extraction
        if 'zwift-activity' in filename:
            start_time_str = parsed_data.get('start_time')
            if start_time_str:
                try:
                    # Convert to datetime object
                    start_time = datetime.fromisoformat(start_time_str)
    
                    # Convert to Los Angeles timezone
                    la_timezone = pytz.timezone('America/Los_Angeles')
                    la_start_time = start_time.astimezone(la_timezone)
    
                    # Log times for debugging
                    print(f"Original start_time: {start_time}")
                    print(f"LA start_time: {la_start_time}")
    
                    # Extract date in YYYY-MM-DD format
                    date = la_start_time.strftime('%Y-%m-%d')
                except Exception as e:
                    print(f"Error processing start time {start_time_str}: {str(e)}")
                    date = None
            else:
                date = '2025-01-16'
        elif '.GarminPing.' in filename:
            date_part = filename.split('.')[1]
            date = date_part[:10]
        
        if not date:
            print(f"Could not extract date from filename: {filename}")
            date = "2025-01-16"  # Fallback date
        
        
        print(f"Extracted date: {date}")
        
        # Parse the FIT file
        fit_parser = FitParser()
        parsed_data = None  # Initialize parsed_data
        parsed_data = fit_parser.parse_fit_file(contents)
        
        if parsed_data is None:
            print(f"Failed to parse FIT file: {filename}")
            # Handle the case where parsing fails
            # You might want to log the error or take other actions
        # Save to database
        db = WorkoutDatabase()
        # Extract title from filename or use a default
        title = filename.split('.')[0].replace('zwift-activity-', 'Zwift Workout ')
        saved = db.save_fit_data(date, title, parsed_data, filename)
        
        if not saved:
            raise ValueError("Failed to save FIT data to database")
        
        return {
            "message": "Successfully processed FIT file",
            "workout_data": parsed_data
        }
        
    except Exception as e:
        print(f"Error processing FIT file {file.filename}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/debug/workout_upload")
async def debug_workout_upload(file: UploadFile = File(...)):
    """Debug endpoint to examine CSV data"""
    try:
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))
        
        # Get full data analysis
        debug_info = {
            "columns": list(df.columns),
            "row_count": len(df),
            "sample_rows": [],
            "column_stats": {}
        }
        
        # Analyze each column
        for column in df.columns:
            non_null_count = df[column].count()
            unique_values = df[column].nunique()
            sample_values = df[column].dropna().head(3).tolist()
            
            debug_info["column_stats"][column] = {
                "non_null_count": int(non_null_count),
                "unique_values": int(unique_values),
                "has_nulls": bool(df[column].isnull().any()),
                "sample_values": sample_values,
                "dtype": str(df[column].dtype)
            }
        
        # Get sample rows
        for _, row in df.head(3).iterrows():
            row_dict = row.to_dict()
            # Convert any special types to strings for JSON serialization
            row_dict = {k: str(v) if pd.isna(v) else v for k, v in row_dict.items()}
            debug_info["sample_rows"].append(row_dict)
        
        return debug_info
    
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error analyzing CSV: {str(e)}")

__all__ = ['app']

@app.post("/upload/proposed_workouts")
async def upload_proposed_workouts(file: UploadFile = File(...)):
    try:
        print(f"Processing proposed workouts file: {file.filename}")
        json_contents = await file.read()
        with open("temp_proposed_workouts.json", "wb") as f:
            f.write(json_contents)

        weekly_plan, daily_plans, proposed_workouts = process_proposed_workouts("temp_proposed_workouts.json")
        db = WorkoutDatabase()

        existing_weekly_plan = db.get_weekly_plan(weekly_plan.weekNumber)
        if existing_weekly_plan:
            print(f"Weekly plan already exists for weekNumber: {weekly_plan.weekNumber}. Deleting existing data...")
            # Delete existing weekly plan and all associated data
            db.delete_weekly_plan_cascade(weekly_plan.weekNumber)
            print(f"Successfully deleted existing data for week {weekly_plan.weekNumber}")
            
        # Create new weekly plan
        print(f"Creating weekly plan: {weekly_plan.weekNumber}, {weekly_plan.startDate}, {weekly_plan.plannedTSS_min}, {weekly_plan.plannedTSS_max}, {weekly_plan.notes}")
        db.create_weekly_plan(
            weekNumber=weekly_plan.weekNumber, 
            startDate=weekly_plan.startDate, 
            plannedTSS_min=weekly_plan.plannedTSS_min, 
            plannedTSS_max=weekly_plan.plannedTSS_max, 
            notes=weekly_plan.notes
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
        print(f"DEBUG: Proposed workouts before matching: {[(w.name, getattr(w, '_dayNumber', None)) for w in proposed_workouts]}")

        for workout in proposed_workouts:
            daily_plan_id = next(
                (dp.id for dp in daily_plans if dp.dayNumber == getattr(workout, '_dayNumber', None)),
                0
            )
            if daily_plan_id == 0:
                print(f"DEBUG: Failed to match workout {workout.name} with _dayNumber {getattr(workout, '_dayNumber', None)}")
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
                sections=workout.sections
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
                zwift_output_dir = "/Users/jacobrobinson/Documents/Zwift/Workouts/6870291"
                
                # Use the module to generate files
                from ..utils.zwift_workout_generator import generate_zwift_workouts_from_db
                generated_files = generate_zwift_workouts_from_db(
                    db_connection=db,
                    start_date=start_date,
                    end_date=end_date,
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

@app.get("/zwift/generate_workouts")
async def generate_zwift_workouts(start_date: str, end_date: str, output_dir: Optional[str] = None, ftp: int = 258, week_number: Optional[int] = None):
    """Generate Zwift workout files for all cycling workouts in the date range"""
    try:
        import os
        from ..utils.zwift_workout_generator import generate_zwift_workouts_from_db
        
        db = WorkoutDatabase()
        
        # Set default output directory to the Zwift workouts directory if not specified
        if not output_dir:
            output_dir = "/Users/jacobrobinson/Documents/Zwift/Workouts/6870291"
        
        # If week number wasn't provided, try to get it from the database
        if week_number is None:
            # Try to get the weekly plan from the database
            proposed_workouts_data = db.get_proposed_workouts_for_week(start_date, end_date)
            weekly_plan = proposed_workouts_data.get('weekly_plan', {})
            if weekly_plan and 'weekNumber' in weekly_plan:
                week_number = weekly_plan.get('weekNumber')
                print(f"Using week number from database: {week_number}")
        
        # Create weekly folders within the output directory
        generated_files = generate_zwift_workouts_from_db(
            db_connection=db,
            start_date=start_date,
            end_date=end_date,
            ftp=ftp,
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
async def save_workout_performance(
    workout_id: int = Form(...),
    workout_date: str = Form(...),
    actual_duration: int = Form(...),
    performance_data: str = Form(...)
):
    """Save performance data for a specific workout"""
    try:
        # Parse performance_data JSON
        perf_data_dict = None
        if performance_data:
            try:
                perf_data_dict = json.loads(performance_data)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid JSON in performance_data"
                )
        
        db = WorkoutDatabase()
        success = db.save_workout_performance(
            workout_id=workout_id,
            workout_date=workout_date,
            actual_duration=actual_duration,
            performance_data=perf_data_dict
        )
        
        if success:
            return {"message": "Performance data saved successfully"}
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to save performance data"
            )
    except Exception as e:
        print(f"Error saving workout performance: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error saving workout performance data: {str(e)}"
        )

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