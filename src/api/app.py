# src/api/app.py

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import List, Optional, Dict, Any
import pandas as pd
import numpy as np
import io
from pydantic import BaseModel
import json


from ..storage.database import WorkoutDatabase
from ..models.workout import DailyWorkout, WeeklySummary
from ..utils.helpers import format_value, clean_float
from ..utils.fit_parser import FitParser
from ..utils.metrics_processor import MetricsProcessor

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
            workout = {
                'title': str(row['Title']).strip(),
                'type': str(row['WorkoutType']).strip(),
                'workout_day': str(row['WorkoutDay']).strip(),
                'metrics': {
                    'actual_tss': float(row['TSS']) if pd.notna(row.get('TSS')) else None,
                    'actual_duration': float(row['TimeTotalInHours']) * 60 if pd.notna(row.get('TimeTotalInHours')) else None,
                    'rpe': float(row['Rpe']) if pd.notna(row.get('Rpe')) else None,
                },
                'power_data': {
                    'average': float(row['PowerAverage']) if pd.notna(row.get('PowerAverage')) else None,
                    'max': float(row['PowerMax']) if pd.notna(row.get('PowerMax')) else None,
                    'if': float(row['IF']) if pd.notna(row.get('IF')) else None,
                    'zones': {
                        'zone1': float(row['PWRZone1Minutes']) if pd.notna(row.get('PWRZone1Minutes')) else 0,
                        'zone2': float(row['PWRZone2Minutes']) if pd.notna(row.get('PWRZone2Minutes')) else 0,
                        'zone3': float(row['PWRZone3Minutes']) if pd.notna(row.get('PWRZone3Minutes')) else 0,
                        'zone4': float(row['PWRZone4Minutes']) if pd.notna(row.get('PWRZone4Minutes')) else 0,
                        'zone5': float(row['PWRZone5Minutes']) if pd.notna(row.get('PWRZone5Minutes')) else 0,
                    }
                } if pd.notna(row.get('PowerAverage')) else None,
                'heart_rate_data': {
                    'average': float(row['HeartRateAverage']) if pd.notna(row.get('HeartRateAverage')) else None,
                    'max': float(row['HeartRateMax']) if pd.notna(row.get('HeartRateMax')) else None,
                    'zones': {
                        'zone1': float(row['HRZone1Minutes']) if pd.notna(row.get('HRZone1Minutes')) else 0,
                        'zone2': float(row['HRZone2Minutes']) if pd.notna(row.get('HRZone2Minutes')) else 0,
                        'zone3': float(row['HRZone3Minutes']) if pd.notna(row.get('HRZone3Minutes')) else 0,
                        'zone4': float(row['HRZone4Minutes']) if pd.notna(row.get('HRZone4Minutes')) else 0,
                        'zone5': float(row['HRZone5Minutes']) if pd.notna(row.get('HRZone5Minutes')) else 0,
                    }
                } if pd.notna(row.get('HeartRateAverage')) else None,
            }
            
            # Save to database
            db = WorkoutDatabase()
            if db.save_workout(workout):
                workouts.append(workout)
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
                'modifications': data.modifications
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
        db = WorkoutDatabase()
        success = db.save_weekly_summary(summary)
        if success:
            return {"message": "Summary saved successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save summary")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

def format_value(value: Any) -> str:
    """Format values consistently"""
    if value is None or pd.isna(value):
        return "N/A"
    if isinstance(value, float):
        return f"{value:.1f}"
    return str(value)

@app.get("/summary/export")
async def export_summary(start_date: str, end_date: str):
    """Export summary in AI-ready format"""
    try:
        db = WorkoutDatabase()
        summary = db.generate_weekly_summary(start_date, end_date)
        if not summary:
            raise HTTPException(status_code=404, detail="No data found for the specified date range")

        # Start building content
        content = [
            "## Overall Weekly Summary",
            f"• Total TSS: {format_value(summary.get('total_tss'))}",
            f"• Total Training Hours: {format_value(summary.get('total_training_hours'))}",
            f"• Number of Sessions Completed: {summary.get('sessions_completed', 0)}",
            f"• Average Sleep Quality (1-5): {format_value(summary.get('avg_sleep_quality'))}",
            f"• Average Daily Energy (1-5): {format_value(summary.get('avg_daily_energy'))}",
            f"• Any schedule/weather challenges: {summary.get('schedule_challenges', 'None reported')}",
            "",
            "## Weekly Self-Assessment",
            "1. Overall Energy Trend:",
        ]

        # Add daily energy levels
        daily_energy = summary.get('daily_energy', {})
        for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
            content.append(f"   • {day}: {format_value(daily_energy.get(day))}")

        # Add recovery quality sections
        content.extend([
            "",
            "2. Recovery Quality:",
            f"   • Sleep quality trend: {format_value(summary.get('sleep_quality_trend'))}",
            f"   • Muscle soreness patterns: {format_value(summary.get('muscle_soreness_patterns'))}",
            f"   • General fatigue level: {format_value(summary.get('general_fatigue_level'))}",
            "",
            "3. Motivation/Engagement:",
            f"   • Enjoyment of workouts (1-5): {format_value(summary.get('workout_enjoyment'))}",
            f"   • Preferred workout types: {', '.join(summary.get('workout_types', []))}",
            f"   • Challenging aspects: {format_value(summary.get('challenging_aspects'))}",
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
                f"   - Planned TSS: {format_value(metrics.get('planned_tss'))} | Actual TSS: {format_value(metrics.get('actual_tss'))}",
                f"   - Duration: Planned {format_value(metrics.get('planned_duration'))} | Actual {format_value(metrics.get('actual_duration'))}",
                f"   - RPE (1-10): {format_value(metrics.get('rpe'))}",
            ])

            # Power Data section (for bike workouts)
            power_data = workout_data.get('power_data', {})
            if power_data and isinstance(power_data, dict):
                content.extend([
                    "",
                    "2. Power Data:",
                    f"   - Average Power: {format_value(power_data.get('average'))}",
                    f"   - Normalized Power: {format_value(power_data.get('normalized_power'))}",
                    f"   - Intensity Factor (IF): {format_value(power_data.get('intensity_factor'))}",
                    "   - Power Zone Distribution:",
                ])
                
                zones = power_data.get('zones', {})
                if isinstance(zones, dict):
                    for zone, value in zones.items():
                        if value and float(value) > 0:
                            content.append(f"     * {zone}: {format_value(value)}%")

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
                    for zone, value in zones.items():
                        if value and float(value) > 0:
                            content.append(f"     * {zone}: {format_value(value)}%")

            # Key Observations section
            feedback = workout.get('feedback', {})
            content.extend([
                "",
                "4. Key Observations:",
                f"   - How the workout felt: {format_value(feedback.get('how_it_felt'))}",
                f"   - Any unusual fatigue: {format_value(feedback.get('unusual_fatigue'))}",
                f"   - Technical issues: {format_value(feedback.get('technical_issues'))}",
                f"   - Modifications made: {format_value(feedback.get('modifications'))}",
            ])

            # Additional section for strength workouts
            if workout.get('type', '').lower() == 'strength':
                content.extend([
                    "",
                    "### For Strength Sessions:",
                    f"- Exercises completed: {format_value(workout.get('exercises_completed'))}",
                    f"- Weight/rep adjustments: {format_value(workout.get('weight_adjustments'))}",
                    f"- Areas of soreness: {format_value(workout.get('areas_of_soreness'))}",
                    f"- Recovery time needed: {format_value(workout.get('recovery_needed'))}",
                ])

        # Add final sections
        content.extend([
            "",
            "## Additional Notes",
            f"• Equipment issues: {format_value(summary.get('equipment_issues'))}",
            f"• Nutrition concerns: {format_value(summary.get('nutrition_concerns'))}",
            f"• Other relevant factors: {format_value(summary.get('other_factors'))}",
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
        
        if 'zwift-activity' in filename:
            # For Zwift files, we'll need the date from the FIT file itself
            date = "2025-01-16"  # This should be extracted from FIT data
        elif '.GarminPing.' in filename:
            # Extract date from Garmin filename format
            date_part = filename.split('.')[1]  # Gets the date part
            date = date_part[:10]  # Takes YYYY-MM-DD part
        
        if not date:
            print(f"Could not extract date from filename: {filename}")
            date = "2025-01-16"  # Fallback date
        
        print(f"Extracted date: {date}")
        
        # Parse the FIT file
        fit_parser = FitParser()
        parsed_data = fit_parser.parse_fit_file(contents)
        
        if parsed_data is None:
            raise ValueError(f"Failed to parse FIT file: {filename}")
        
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

# Make sure the app is available for import
__all__ = ['app']