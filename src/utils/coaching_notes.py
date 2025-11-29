"""
📝 Coaching Notes Manager
=========================
Manages persistent coaching notes that provide continuity between
weekly coaching sessions. This is the AI coach's "memory" system.

🏆 Features:
- Athlete profile and goals
- Week-over-week observations
- Training focus areas
- Coaching personality/style
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class AthleteProfile:
    """Core athlete information and goals"""
    name: str = "Athlete"  # Configure in data/coaching_notes.json
    current_ftp: int = 300
    starting_ftp: int = 200  # Impressive 100W improvement!
    
    primary_goals: Optional[List[str]] = None
    weekly_availability: str = "1-2 hours weekdays, flexible weekends"
    seasonal_preferences: Optional[Dict[str, List[str]]] = None
    
    def __post_init__(self):
        if self.primary_goals is None:
            self.primary_goals = [
                "50-100 mile gravel rides in Oregon with significant climbing",
                "Continue FTP improvement (target: 320W+)",
                "Build sustainable endurance for ultra-distance events",
                "Maintain well-rounded fitness (cycling, running, XC skiing, strength)"
            ]
        
        if self.seasonal_preferences is None:
            self.seasonal_preferences = {
                "winter": ["XC skiing", "indoor cycling", "strength training"],
                "spring": ["gravel riding", "running", "outdoor cycling"],
                "summer": ["gravel events", "long rides", "hiking"],
                "fall": ["gravel riding", "running", "race prep"]
            }


@dataclass
class CoachingObservation:
    """A single coaching observation or note"""
    date: str  # YYYY-MM-DD format
    week_number: int
    observation: str
    focus_areas: List[str]
    athlete_response: Optional[str] = None  # How athlete is responding to training
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class CoachingContinuity:
    """
    Week-to-week coaching continuity - AI's memory of recent training.
    This enables the AI to reference past weeks and maintain context.
    """
    week_start_date: str  # YYYY-MM-DD
    week_end_date: str
    week_number: int
    
    # Key takeaways from this week
    key_observations: List[str]  # e.g., "Strong threshold power improvement", "Recovery improving"
    progression_notes: List[str]  # e.g., "FTP increased 5W", "Endurance workouts getting easier"
    areas_to_monitor: List[str]  # e.g., "Watch for overtraining", "Monitor sleep quality"
    
    # What to remember for next week
    next_week_priorities: List[str]  # e.g., "Include recovery week", "Focus on tempo work"
    
    # Recurring schedule items (to avoid re-asking)
    recurring_schedule: Optional[Dict[str, str]] = None  # e.g., {"Tuesday": "Zwift racing league"}
    
    # Metadata
    created_date: Optional[str] = None
    
    def __post_init__(self):
        if self.created_date is None:
            self.created_date = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class CoachingPersonality:
    """Defines the AI coach's personality and approach"""
    style: str = "data-driven, encouraging, scientific"
    voice: str = "professional yet personable"
    approach: str = "progressive overload with proper recovery, evidence-based training"
    communication_preferences: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.communication_preferences is None:
            self.communication_preferences = [
                "Use data to support recommendations",
                "Explain the 'why' behind workouts",
                "Balance hard work with recovery",
                "Acknowledge progress and improvements",
                "Provide context for training decisions"
            ]
    
    def to_dict(self) -> Dict:
        return asdict(self)


class CoachingNotesManager:
    """
    Manages persistent coaching notes stored in JSON format.
    
    🏃‍♂️ This is how the AI coach maintains continuity week-over-week,
    remembering past observations and building a relationship with the athlete.
    """
    
    def __init__(self, notes_path: Optional[Path] = None):
        if notes_path is None:
            # Default to data/coaching_notes.json (gitignored for privacy)
            project_root = Path(__file__).parent.parent.parent
            notes_path = project_root / "data" / "coaching_notes.json"
        
        self.notes_path = Path(notes_path)
        self.notes_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load existing notes or create new
        if self.notes_path.exists():
            self.load()
        else:
            self.initialize_new()
    
    def initialize_new(self):
        """Create new coaching notes with default athlete profile"""
        self.athlete_profile = AthleteProfile()
        self.observations: List[CoachingObservation] = []
        self.personality = CoachingPersonality()
        self.coaching_continuity: List[CoachingContinuity] = []  # NEW: Week-to-week memory
        self.next_week_focus = "Build aerobic base with progressive endurance development"
        self.current_training_phase = "Base Building"
        
        # Save initial notes
        self.save()
    
    def load(self):
        """Load coaching notes from JSON file"""
        with open(self.notes_path, 'r') as f:
            data = json.load(f)
        
        # Load athlete profile
        profile_data = data.get('athlete_profile', {})
        self.athlete_profile = AthleteProfile(**profile_data)
        
        # Load observations
        obs_data = data.get('observations', [])
        self.observations = [
            CoachingObservation(**obs) for obs in obs_data
        ]
        
        # Load personality
        personality_data = data.get('personality', {})
        self.personality = CoachingPersonality(**personality_data)
        
        # Load coaching continuity (NEW)
        continuity_data = data.get('coaching_continuity', [])
        self.coaching_continuity = [
            CoachingContinuity(**cont) for cont in continuity_data
        ]
        
        # Load other fields
        self.next_week_focus = data.get('next_week_focus', '')
        self.current_training_phase = data.get('current_training_phase', 'Base Building')
    
    def save(self):
        """Save coaching notes to JSON file"""
        data = {
            'athlete_profile': asdict(self.athlete_profile),
            'observations': [obs.to_dict() for obs in self.observations],
            'personality': self.personality.to_dict(),
            'coaching_continuity': [cont.to_dict() for cont in self.coaching_continuity],  # NEW
            'next_week_focus': self.next_week_focus,
            'current_training_phase': self.current_training_phase,
            'last_updated': datetime.now().isoformat()
        }
        
        with open(self.notes_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def add_observation(self, 
                       observation: str, 
                       focus_areas: List[str],
                       week_number: int,
                       athlete_response: Optional[str] = None):
        """Add a new coaching observation"""
        obs = CoachingObservation(
            date=datetime.now().strftime('%Y-%m-%d'),
            week_number=week_number,
            observation=observation,
            focus_areas=focus_areas,
            athlete_response=athlete_response
        )
        self.observations.append(obs)
        self.save()
    
    def get_recent_observations(self, n: int = 4) -> List[CoachingObservation]:
        """Get the N most recent observations"""
        return self.observations[-n:] if self.observations else []
    
    def update_ftp(self, new_ftp: int):
        """Update athlete's FTP"""
        self.athlete_profile.current_ftp = new_ftp
        self.save()
    
    def update_next_week_focus(self, focus: str):
        """Update what to focus on next week"""
        self.next_week_focus = focus
        self.save()
    
    def update_training_phase(self, phase: str):
        """Update current training phase (Base, Build, Peak, Recovery)"""
        self.current_training_phase = phase
        self.save()
    
    def add_coaching_continuity(self,
                               week_start_date: str,
                               week_end_date: str,
                               week_number: int,
                               key_observations: List[str],
                               progression_notes: List[str],
                               areas_to_monitor: List[str],
                               next_week_priorities: List[str],
                               recurring_schedule: Optional[Dict[str, str]] = None):
        """
        Add coaching continuity for a completed week.
        This is the AI's memory of what happened and what to focus on next.
        """
        continuity = CoachingContinuity(
            week_start_date=week_start_date,
            week_end_date=week_end_date,
            week_number=week_number,
            key_observations=key_observations,
            progression_notes=progression_notes,
            areas_to_monitor=areas_to_monitor,
            next_week_priorities=next_week_priorities,
            recurring_schedule=recurring_schedule
        )
        self.coaching_continuity.append(continuity)
        self.save()
    
    def get_recent_continuity(self, n: int = 2) -> List[CoachingContinuity]:
        """Get the N most recent coaching continuity entries"""
        return self.coaching_continuity[-n:] if self.coaching_continuity else []
    
    def get_last_week_continuity(self) -> Optional[CoachingContinuity]:
        """Get the most recent coaching continuity entry"""
        return self.coaching_continuity[-1] if self.coaching_continuity else None
    
    def get_context_for_ai(self) -> Dict:
        """
        Get coaching notes formatted for AI context.
        This is what gets passed to the AI coach each week.
        """
        recent_obs = self.get_recent_observations(n=4)
        recent_continuity = self.get_recent_continuity(n=2)
        
        return {
            'athlete_profile': {
                'name': self.athlete_profile.name,
                'current_ftp': self.athlete_profile.current_ftp,
                'ftp_improvement': self.athlete_profile.current_ftp - self.athlete_profile.starting_ftp,
                'goals': self.athlete_profile.primary_goals,
                'availability': self.athlete_profile.weekly_availability,
                'seasonal_preferences': self.athlete_profile.seasonal_preferences
            },
            'recent_observations': [
                {
                    'week': obs.week_number,
                    'observation': obs.observation,
                    'focus_areas': obs.focus_areas,
                    'athlete_response': obs.athlete_response
                }
                for obs in recent_obs
            ],
            'coaching_continuity': [
                {
                    'week_dates': f"{cont.week_start_date} to {cont.week_end_date}",
                    'week_number': cont.week_number,
                    'key_observations': cont.key_observations,
                    'progression': cont.progression_notes,
                    'monitor': cont.areas_to_monitor,
                    'next_priorities': cont.next_week_priorities,
                    'recurring_schedule': cont.recurring_schedule
                }
                for cont in recent_continuity
            ],
            'coaching_approach': {
                'style': self.personality.style,
                'voice': self.personality.voice,
                'preferences': self.personality.communication_preferences
            },
            'next_week_focus': self.next_week_focus,
            'current_phase': self.current_training_phase
        }
    
    def get_summary(self) -> str:
        """Get a human-readable summary of coaching notes"""
        recent = self.get_recent_observations(n=3)
        
        goals = self.athlete_profile.primary_goals or []
        goals_str = ', '.join(goals[:2]) if goals else "No goals set"
        
        summary = f"""
🏃‍♂️ ATHLETE PROFILE
==================
Name: {self.athlete_profile.name}
Current FTP: {self.athlete_profile.current_ftp}W (↑ {self.athlete_profile.current_ftp - self.athlete_profile.starting_ftp}W from start!)
Goals: {goals_str}

📊 CURRENT TRAINING
===================
Phase: {self.current_training_phase}
Next Week Focus: {self.next_week_focus}

🎯 RECENT OBSERVATIONS ({len(recent)} most recent)
==================
"""
        for obs in recent:
            summary += f"\nWeek {obs.week_number} ({obs.date}):\n"
            summary += f"  • {obs.observation}\n"
            summary += f"  • Focus: {', '.join(obs.focus_areas)}\n"
        
        return summary


# Test/demo functionality
if __name__ == "__main__":
    print("🏋️ Testing Coaching Notes Manager\n")
    
    # Create manager (will initialize with defaults if no file exists)
    manager = CoachingNotesManager()
    
    # Add a sample observation (simulating what AI coach would do)
    if len(manager.observations) == 0:
        print("📝 Adding initial observation...")
        manager.add_observation(
            observation="Athlete showing strong consistency in training adherence. "
                       "Power improvements evident from recent threshold work.",
            focus_areas=["power consistency", "endurance building", "recovery optimization"],
            week_number=1,
            athlete_response="Responding well to structured training, good recovery habits"
        )
    
    # Print summary
    print(manager.get_summary())
    
    # Show what gets passed to AI
    print("\n🤖 Context for AI Coach:")
    print("=" * 60)
    ai_context = manager.get_context_for_ai()
    print(json.dumps(ai_context, indent=2))
    
    print(f"\n✅ Coaching notes saved to: {manager.notes_path}")
