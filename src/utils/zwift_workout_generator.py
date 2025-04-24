import json
import os
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional

# Default user FTP in watts - adjust this as your fitness changes
DEFAULT_FTP = 258

def generate_zwift_workout(workout_date: str, workout_name: str, intervals: List[Dict[str, Any]], 
                          description: str = "", ftp: int = DEFAULT_FTP, output_dir: Optional[str] = None, 
                          week_number: Optional[int] = None) -> str:
    """
    Generate a Zwift .zwo file from intervals data.
    
    Args:
        workout_date: Date of the workout in YYYY-MM-DD format
        workout_name: Name of the workout
        intervals: List of interval dictionaries with power and duration data
        description: Optional workout description
        ftp: FTP value in watts to use for calculations (default: 258)
        output_dir: Directory to save the .zwo file (defaults to current working directory)
        week_number: Optional week number for folder naming (defaults to ISO week of year)
        
    Returns:
        Path to the generated .zwo file
    """
    # Parse the date for filename and folder organization
    workout_date_obj = datetime.strptime(workout_date, "%Y-%m-%d")
    date_prefix = workout_date_obj.strftime("%Y_%m_%d")
    
    # Make sure the date is correct and properly formatted in the workout name
    formatted_date = workout_date_obj.strftime('%m/%d')
    display_name = f"{formatted_date} {workout_name}"
    
    # Clean workout name for filename
    clean_name = ''.join(c if c.isalnum() or c in ' -_' else '_' for c in workout_name)
    clean_name = clean_name.replace(' ', '_')
    
    # Create filename
    filename = f"{date_prefix}_{clean_name}.zwo"
    
    # Determine output directory and create weekly folders
    if not output_dir:
        output_dir = os.getcwd()
    
    # Create weekly folder based on provided week number or fallback to ISO week
    if week_number is not None:
        week_folder = f"Week_{week_number}"
    else:
        week_of_year = workout_date_obj.isocalendar()[1]
        week_folder = f"Week_{week_of_year}"
    weekly_output_dir = os.path.join(output_dir, week_folder)
    
    # Create the weekly directory if it doesn't exist
    os.makedirs(weekly_output_dir, exist_ok=True)
    
    # Full path for the output file
    output_path = os.path.join(weekly_output_dir, filename)
    
    # Generate a more detailed description if none provided
    if not description:
        description = f"{workout_name} - {formatted_date}\n"
        for interval in intervals:
            interval_name = interval.get('name', '')
            duration = interval.get('duration', 0)
            power_target = interval.get('powerTarget', {})
            cadence_target = interval.get('cadenceTarget', {})
            
            # Add interval details to description
            description += f"\n{interval_name}: {duration//60}min"
            if power_target:
                power_str = format_power_target(power_target, ftp)
                description += f" @ {power_str}"
            if cadence_target:
                cadence_min = cadence_target.get('min')
                cadence_max = cadence_target.get('max')
                if cadence_min and cadence_max:
                    description += f" ({cadence_min}-{cadence_max} RPM)"
    
    # Start building the XML content with the correct name tag
    xml_content = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<workout_file>',
        '  <author/>',
        f'  <name>{display_name}</name>',
        f'  <description>{description}</description>',
        '  <sportType>bike</sportType>',
        '  <durationType>time</durationType>',
        '  <tags/>',
        '  <workout>'
    ]
    
    # Process intervals
    for interval in intervals:
        interval_type, xml_element = convert_interval_to_zwift(interval, ftp)
        if xml_element:
            xml_content.append(f'    {xml_element}')
    
    # Close the XML
    xml_content.extend([
        '  </workout>',
        '</workout_file>'
    ])
    
    # Write the file
    with open(output_path, 'w') as f:
        f.write('\n'.join(xml_content))
    
    print(f"Generated Zwift workout file at: {output_path}")
    return output_path

def fix_xml_tag_in_file(file_path: str) -> None:
    """
    Fix the XML tag issue in the generated file by replacing <n> with <name>.
    
    Args:
        file_path: Path to the ZWO file to fix
    """
    try:
        # Read the file content
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Replace <n> tags with <name> tags
        content = content.replace('<n>', '<name>').replace('</n>', '</name>')
        
        # Write the fixed content back
        with open(file_path, 'w') as f:
            f.write(content)
    except Exception as e:
        print(f"Warning: Could not fix XML tag in {file_path}: {str(e)}")

def convert_interval_to_zwift(interval: Dict[str, Any], ftp: int) -> Tuple[str, str]:
    """
    Convert an interval dictionary to Zwift XML format.
    
    Args:
        interval: Dictionary containing interval data
        ftp: FTP value in watts for power calculations
        
    Returns:
        Tuple of (interval_type, xml_element)
    """
    interval_type = interval.get('name', '')
    duration = interval.get('duration', 0)
    power_target = interval.get('powerTarget', {})
    cadence_target = interval.get('cadenceTarget', {})
    
    # Handle different power target formats
    if isinstance(power_target, dict):
        if 'start' in power_target and 'end' in power_target:
            # Ramp interval
            start_power = calculate_power(power_target['start'], ftp)
            end_power = calculate_power(power_target['end'], ftp)
            xml_element = f'<Ramp Duration="{duration}" PowerLow="{start_power}" PowerHigh="{end_power}" pace="0"'
        else:
            # Steady state interval
            power = calculate_power(power_target, ftp)
            xml_element = f'<SteadyState Duration="{duration}" Power="{power}" pace="0"'
    else:
        # Default to steady state if power format is unknown
        power = calculate_power(power_target, ftp)
        xml_element = f'<SteadyState Duration="{duration}" Power="{power}" pace="0"'
    
    # Add cadence target if specified
    if cadence_target:
        cadence_min = cadence_target.get('min')
        cadence_max = cadence_target.get('max')
        if cadence_min and cadence_max:
            xml_element += f' Cadence="{cadence_min}-{cadence_max}"'
    
    # Add interval description as text event
    if interval_type:
        xml_element += '>'
        # Add text event at 10% of the interval duration
        time_offset = max(10, int(duration * 0.1))
        xml_element += f'\n      <textevent timeoffset="{time_offset}" message="{interval_type}"/>'
        xml_element += '\n    </SteadyState>' if 'SteadyState' in xml_element else '\n    </Ramp>'
    else:
        xml_element += '/>'
    
    return interval_type, xml_element

def generate_zwift_workouts_from_db(db_connection, start_date: str, end_date: str, 
                                   ftp: int = DEFAULT_FTP, output_dir: Optional[str] = None,
                                   week_number: Optional[int] = None) -> List[str]:
    """
    Generate Zwift workouts for all cycling workouts in the specified date range from the database.
    
    Args:
        db_connection: Database connection object with get_proposed_workouts_for_week method
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        ftp: FTP value in watts to use for calculations
        output_dir: Directory to save .zwo files
        week_number: Optional week number for folder naming
        
    Returns:
        List of paths to generated .zwo files
    """
    generated_files = []
    
    try:
        # Get all proposed workouts for the date range
        proposed_workouts_data = db_connection.get_proposed_workouts_for_week(start_date, end_date)
        daily_workouts = proposed_workouts_data.get('daily_workouts', [])
        
        # If week_number wasn't provided as an argument, try to get it from the data
        if week_number is None:
            weekly_plan = proposed_workouts_data.get('weekly_plan', {})
            if weekly_plan and 'weekNumber' in weekly_plan:
                week_number = weekly_plan.get('weekNumber')
                
        # Print debug info
        print(f"Processing workouts for Week {week_number}")
        
        for workout in daily_workouts:
            # Only process cycling workouts
            if workout.get('type', '').lower() == 'bike':
                workout_date = workout.get('date')
                workout_name = workout.get('name')
                
                # Parse intervals from JSON string
                intervals_str = workout.get('intervals')
                intervals = []
                if intervals_str:
                    try:
                        intervals = json.loads(intervals_str)
                    except json.JSONDecodeError:
                        print(f"Error parsing intervals for {workout_name} on {workout_date}")
                        continue
                
                if intervals:
                    try:
                        # Generate the Zwift workout file
                        output_file = generate_zwift_workout(
                            workout_date=workout_date,
                            workout_name=workout_name,
                            intervals=intervals,
                            ftp=ftp,
                            output_dir=output_dir,
                            week_number=week_number
                        )
                        generated_files.append(output_file)
                        print(f"Generated Zwift workout for '{workout_name}' on {workout_date}")
                    except Exception as e:
                        print(f"Error generating Zwift workout for '{workout_name}': {str(e)}")
    
    except Exception as e:
        print(f"Error processing workouts from database: {str(e)}")
    
    return generated_files

def format_power_target(power_target: Dict[str, Any], ftp: int) -> str:
    """Format power target for description"""
    if isinstance(power_target, dict):
        if 'start' in power_target and 'end' in power_target:
            start_power = calculate_power(power_target['start'], ftp)
            end_power = calculate_power(power_target['end'], ftp)
            return f"{start_power*100:.0f}-{end_power*100:.0f}% FTP"
        elif 'type' in power_target:
            power = calculate_power(power_target, ftp)
            return f"{power*100:.0f}% FTP"
        elif 'min' in power_target and 'max' in power_target:
            return f"{power_target['min']}-{power_target['max']} watts"
        elif 'value' in power_target:
            return f"{power_target['value']} watts"
    return "Unknown power target"
