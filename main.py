# main.py

from datetime import datetime
from src.models.workout import DailyWorkout, PowerData, HeartRateData, WeeklySummary
from src.storage.database import WorkoutDatabase


def get_user_input(prompt: str, required: bool = True) -> str:
    """Get input from user with validation for required fields"""
    while True:
        value = input(prompt).strip()
        if value or not required:
            return value
        print("This field is required. Please enter a value.")

def get_number_input(prompt: str, min_val: float, max_val: float) -> float:
    """Get numeric input from user with validation"""
    while True:
        try:
            value = float(input(prompt))
            if min_val <= value <= max_val:
                return value
            print(f"Please enter a value between {min_val} and {max_val}")
        except ValueError:
            print("Please enter a valid number")

def add_workout():
    """Add a new workout entry"""
    print("\n=== Adding New Workout ===")
    
    # Get basic workout information
    workout_type = get_user_input("Workout type (Bike/Run/Strength/etc.): ")
    planned_tss = get_number_input("Planned TSS: ", 0, 500)
    actual_tss = get_number_input("Actual TSS: ", 0, 500)
    planned_duration = int(get_number_input("Planned duration (minutes): ", 0, 600))
    actual_duration = int(get_number_input("Actual duration (minutes): ", 0, 600))
    rpe = int(get_number_input("RPE (1-10): ", 1, 10))

    # Get qualitative feedback
    how_it_felt = get_user_input("How did the workout feel? ", required=False)
    unusual_fatigue = get_user_input("Any unusual fatigue? ", required=False)
    technical_issues = get_user_input("Any technical issues? ", required=False)
    modifications = get_user_input("Any modifications made? ", required=False)

    # Initialize power and heart rate data
    power_data = None
    heart_rate_data = None

    # If it's a bike workout, get power data
    if workout_type.lower() == "bike":
        print("\n=== Power Data ===")
        avg_power = get_number_input("Average power (watts): ", 0, 2000)
        norm_power = get_number_input("Normalized power (watts): ", 0, 2000)
        intensity = get_number_input("Intensity factor (0.0-1.5): ", 0, 1.5)
        
        power_data = PowerData(
            average_power=avg_power,
            normalized_power=norm_power,
            intensity_factor=intensity
        )

    # Get heart rate data for cardio workouts
    if workout_type.lower() in ["bike", "run"]:
        print("\n=== Heart Rate Data ===")
        avg_hr = int(get_number_input("Average heart rate: ", 0, 250))
        max_hr = int(get_number_input("Maximum heart rate: ", 0, 250))
        
        heart_rate_data = HeartRateData(
            average_hr=avg_hr,
            max_hr=max_hr
        )

    # Create and save the workout
    workout = DailyWorkout(
        date=datetime.now(),
        workout_type=workout_type,
        planned_tss=planned_tss,
        actual_tss=actual_tss,
        planned_duration=planned_duration,
        actual_duration=actual_duration,
        rpe=rpe,
        power_data=power_data,
        heart_rate_data=heart_rate_data,
        how_it_felt=how_it_felt,
        unusual_fatigue=unusual_fatigue,
        technical_issues=technical_issues,
        modifications=modifications
    )

    # Save to database
    db = WorkoutDatabase()
    db.save_workout(workout)
    print("\nWorkout saved successfully!")

def add_weekly_summary():
    """Add a weekly summary"""
    print("\n=== Adding Weekly Summary ===")
    
    # Get basic weekly information
    total_tss = get_number_input("Total TSS for the week: ", 0, 2000)
    total_hours = get_number_input("Total training hours: ", 0, 50)
    sessions_completed = int(get_number_input("Number of sessions completed: ", 0, 30))
    sessions_planned = int(get_number_input("Number of sessions planned: ", 0, 30))
    avg_sleep = get_number_input("Average sleep quality (1-5): ", 1, 5)
    avg_energy = get_number_input("Average daily energy (1-5): ", 1, 5)
    workout_enjoyment = int(get_number_input("Overall workout enjoyment (1-5): ", 1, 5))  # Added this line

    # Get daily energy levels
    print("\n=== Daily Energy Levels (1-5) ===")
    daily_energy = {}
    for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
        daily_energy[day] = int(get_number_input(f"{day}: ", 1, 5))

    # Get recovery metrics
    print("\n=== Recovery Metrics ===")
    sleep_trend = get_user_input("Sleep quality trend: ", required=False)
    soreness = get_user_input("Muscle soreness patterns: ", required=False)
    fatigue = get_user_input("General fatigue level: ", required=False)

    # Create and save the weekly summary
    summary = WeeklySummary(
        start_date=datetime.now(),  # You might want to adjust this
        end_date=datetime.now(),    # You might want to adjust this
        total_tss=total_tss,
        total_training_hours=total_hours,
        sessions_completed=sessions_completed,
        sessions_planned=sessions_planned,
        avg_sleep_quality=avg_sleep,
        avg_daily_energy=avg_energy,
        workout_enjoyment=workout_enjoyment,  # Added this line
        daily_energy=daily_energy,
        sleep_quality_trend=sleep_trend,
        muscle_soreness_patterns=soreness,
        general_fatigue_level=fatigue
    )

    # Save to database
    db = WorkoutDatabase()
    db.save_weekly_summary(summary)
    print("\nWeekly summary saved successfully!")

def view_workouts():
    """View all recorded workouts"""
    db = WorkoutDatabase()
    workouts = db.get_all_workouts()
    
    if not workouts:
        print("\nNo workouts found.")
        return
    
    print("\n=== Recorded Workouts ===")
    for workout in workouts:
        print(f"\nID: {workout['id']}")
        print(f"Date: {workout['date']}")
        print(f"Type: {workout['workout_type']}")
        print(f"Duration: {workout['actual_duration']} minutes")
        print(f"TSS: {workout['actual_tss']}")
        print("------------------------")

def view_summaries():
    """View all weekly summaries"""
    db = WorkoutDatabase()
    summaries = db.get_all_summaries()
    
    if not summaries:
        print("\nNo weekly summaries found.")
        return
    
    print("\n=== Weekly Summaries ===")
    for summary in summaries:
        print(f"\nID: {summary['id']}")
        print(f"Week: {summary['start_date']} to {summary['end_date']}")
        print(f"Total TSS: {summary['total_tss']}")
        print(f"Training Hours: {summary['total_training_hours']}")
        print(f"Sessions: {summary['sessions_completed']}/{summary['sessions_planned']}")
        print("------------------------")

def delete_workout():
    """Delete a workout by ID"""
    workout_id = get_number_input("Enter workout ID to delete: ", 0, 99999)
    db = WorkoutDatabase()
    if db.delete_workout(int(workout_id)):
        print("Workout deleted successfully!")
    else:
        print("Workout not found or could not be deleted.")

def delete_summary():
    """Delete a weekly summary by ID"""
    summary_id = get_number_input("Enter summary ID to delete: ", 0, 99999)
    db = WorkoutDatabase()
    if db.delete_summary(int(summary_id)):
        print("Weekly summary deleted successfully!")
    else:
        print("Summary not found or could not be deleted.")

# Update the main menu function to include new options
def main():
    """Main program loop"""
    while True:
        print("\n=== Fitness Tracker ===")
        print("1. Add Workout")
        print("2. Add Weekly Summary")
        print("3. View Workouts")
        print("4. View Weekly Summaries")
        print("5. Delete Workout")
        print("6. Delete Weekly Summary")
        print("7. Exit")
        
        choice = input("\nEnter your choice (1-7): ")
        
        if choice == "1":
            add_workout()
        elif choice == "2":
            add_weekly_summary()
        elif choice == "3":
            view_workouts()
        elif choice == "4":
            view_summaries()
        elif choice == "5":
            delete_workout()
        elif choice == "6":
            delete_summary()
        elif choice == "7":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()