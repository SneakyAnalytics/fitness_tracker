# src/models/workout.py

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional

@dataclass
class PowerData:
    """Store power-related metrics for bike workouts"""
    average_power: float
    normalized_power: float
    intensity_factor: float
    zone_distribution: Dict[str, float] = None
    
    def __post_init__(self):
        if self.zone_distribution is None:
            self.zone_distribution = {
                "Zone 1 (Recovery)": 0,
                "Zone 2 (Endurance)": 0,
                "Zone 3 (Tempo)": 0,
                "Zone 4 (Threshold)": 0,
                "Zone 5+": 0
            }

@dataclass
class HeartRateData:
    """Store heart rate-related metrics"""
    average_hr: int
    max_hr: int
    zone_distribution: Dict[str, float] = None
    
    def __post_init__(self):
        if self.zone_distribution is None:
            self.zone_distribution = {
                "Zone 1": 0,
                "Zone 2": 0,
                "Zone 3": 0,
                "Zone 4": 0,
                "Zone 5": 0
            }

@dataclass
class DailyWorkout:
    """Represents a single workout session"""
    date: datetime
    workout_type: str
    planned_tss: float
    actual_tss: float
    planned_duration: int  # in minutes
    actual_duration: int
    rpe: int  # 1-10
    power_data: Optional[PowerData] = None
    heart_rate_data: Optional[HeartRateData] = None
    how_it_felt: Optional[str] = None
    unusual_fatigue: Optional[str] = None
    technical_issues: Optional[str] = None
    modifications: Optional[str] = None
    athlete_comments:  Optional[str] = None
    exercises_completed: Optional[List[str]] = None
    weight_adjustments: Optional[str] = None
    areas_of_soreness: Optional[str] = None
    recovery_needed: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Convert workout to dictionary format"""
        data = asdict(self)
        data['date'] = self.date.isoformat()
        return data

@dataclass
class WeeklySummary:
    """Store weekly summary data"""
    # Required fields (no default values)
    start_date: datetime
    end_date: datetime
    total_tss: float
    total_training_hours: float
    sessions_completed: int
    sessions_planned: int
    avg_sleep_quality: float
    avg_daily_energy: float
    
    # Optional fields (with default values)
    daily_energy: Dict[str, int] = None
    sleep_quality_trend: Optional[str] = None
    muscle_soreness_patterns: Optional[str] = None
    general_fatigue_level: Optional[str] = None
    
    def __post_init__(self):
        if self.daily_energy is None:
            self.daily_energy = {
                'Monday': None,
                'Tuesday': None,
                'Wednesday': None,
                'Thursday': None,
                'Friday': None,
                'Saturday': None,
            }
        if self.preferred_workout_types is None:
            self.preferred_workout_types = []
    
    def to_dict(self) -> Dict:
        """Convert weekly summary to dictionary format"""
        data = asdict(self)
        data['start_date'] = self.start_date.isoformat()
        data['end_date'] = self.end_date.isoformat()
        return data