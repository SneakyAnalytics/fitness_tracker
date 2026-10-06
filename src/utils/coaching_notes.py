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
    sentiment: Optional[str] = None  # NEW: positive, negative, neutral, struggling, confident
    
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
class Achievement:
    """
    Categorized achievement/milestone for tracking progress.
    
    **NEW: Achievement Categories**
    - distance: Long rides, centuries, gran fondos
    - power: FTP improvements, peak power PRs, threshold milestones
    - endurance: Multi-hour efforts, back-to-back training blocks
    - technical: Skills (climbing, descending, cornering), equipment mastery
    - event: Race completions, podium finishes, participation milestones
    - consistency: Training streaks, attendance records
    """
    date: str  # YYYY-MM-DD
    description: str
    category: str  # One of: distance, power, endurance, technical, event, consistency
    value: Optional[str] = None  # e.g., "100 miles", "310W", "5 hours"
    week_number: Optional[int] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class Goal:
    """
    Prioritized training goal with metadata.
    
    **NEW: Goal Prioritization**
    - priority: 1 (highest) to 5 (lowest)
    - status: active, completed, paused, abandoned
    - added_date: When goal was added
    - target_date: Optional deadline
    - progress_notes: Updates on progress toward goal
    """
    description: str
    category: str  # One of: distance, power, endurance, technical, event, consistency
    priority: int = 3  # 1-5, default to medium priority
    status: str = "active"  # active, completed, paused, abandoned
    added_date: Optional[str] = None
    target_date: Optional[str] = None  # YYYY-MM-DD
    progress_notes: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.added_date is None:
            self.added_date = datetime.now().strftime('%Y-%m-%d')
        if self.progress_notes is None:
            self.progress_notes = []
    
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
        self.coaching_continuity: List[CoachingContinuity] = []
        self.achievements: List[Achievement] = []  # NEW: Categorized achievements
        self.goals: List[Goal] = []  # NEW: Prioritized goals
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
        
        # Load coaching continuity
        continuity_data = data.get('coaching_continuity', [])
        self.coaching_continuity = [
            CoachingContinuity(**cont) for cont in continuity_data
        ]
        
        # Load achievements (NEW)
        achievements_data = data.get('achievements', [])
        self.achievements = [
            Achievement(**ach) for ach in achievements_data
        ]
        
        # Load goals (NEW)
        goals_data = data.get('goals', [])
        self.goals = [
            Goal(**goal) for goal in goals_data
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
            'coaching_continuity': [cont.to_dict() for cont in self.coaching_continuity],
            'achievements': [ach.to_dict() for ach in self.achievements],  # NEW
            'goals': [goal.to_dict() for goal in self.goals],  # NEW
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
                       athlete_response: Optional[str] = None,
                       sentiment: Optional[str] = None):
        """Add a new coaching observation with optional sentiment"""
        # Auto-detect sentiment if not provided
        if sentiment is None and athlete_response:
            sentiment = self._detect_sentiment(athlete_response)
        
        obs = CoachingObservation(
            date=datetime.now().strftime('%Y-%m-%d'),
            week_number=week_number,
            observation=observation,
            focus_areas=focus_areas,
            athlete_response=athlete_response,
            sentiment=sentiment
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
    
    def add_goal(self,
                 description: str,
                 category: str = 'event',
                 priority: int = 1,
                 target_date: Optional[str] = None,
                 progress_notes: Optional[List[str]] = None) -> 'Goal':
        """Add a new goal and persist immediately."""
        goal = Goal(
            description=description,
            category=category,
            priority=priority,
            status='active',
            added_date=datetime.now().strftime('%Y-%m-%d'),
            target_date=target_date,
            progress_notes=progress_notes or [],
        )
        self.goals.append(goal)
        self.save()
        return goal

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
                    'athlete_response': obs.athlete_response,
                    'sentiment': obs.sentiment  # NEW: Include sentiment for AI context
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
    
    def _extract_value_from_text(self, text: str) -> Optional[str]:
        """
        Extract numeric value from achievement/goal text.
        Examples: "100 miles", "310W", "5 hours"
        """
        import re
        
        # Pattern: number + optional decimal + unit
        patterns = [
            r'(\d+\.?\d*)\s*(mile|km|kilometer|watts?|w|hours?|h|minutes?|min)',
            r'(\d+)\s*%',
            r'(\d+)\s*(st|nd|rd|th)\s*place'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        
        return None
    
    def _detect_sentiment(self, text: str) -> str:
        """
        Detect sentiment/mood from athlete feedback text.
        
        **NEW: Sentiment Analysis**
        Returns one of: positive, negative, neutral, struggling, confident
        
        This helps the AI coach:
        - Adjust encouragement level
        - Detect potential overtraining/burnout
        - Celebrate successes appropriately
        - Provide extra support when struggling
        """
        text_lower = text.lower()
        
        # Struggling indicators (highest priority - needs support)
        # Check these FIRST before positive words
        struggling_keywords = [
            'exhausted', 'burned out', 'burnout', 'struggling', 'hard time',
            'too much', 'overwhelmed', 'dreading', 'considering quitting', 'unmotivated',
            'terrible', 'awful', 'miserable', 'suffering', 'couldn\'t finish',
            'gave up', 'failed', 'hurting', 'injured', 'sick', 'not recovering',
            'can\'t even', 'unable to', 'impossible'
        ]
        if any(kw in text_lower for kw in struggling_keywords):
            return 'struggling'
        
        # Confident/strong indicators
        confident_keywords = [
            'crushed', 'smashed', 'nailed', 'felt amazing', 'felt strong', 'felt great',
            'easy', 'effortless', 'confident', 'ready', 'excited', 'can\'t wait',
            'breakthrough', 'best ever', 'personal best', 'pb', 'pr', 'killed it',
            'dominating', 'strongest', 'fittest', 'incredible', 'awesome'
        ]
        if any(kw in text_lower for kw in confident_keywords):
            return 'confident'
        
        # Positive indicators
        positive_keywords = [
            'good', 'great', 'excellent', 'well', 'better', 'improved', 'progress',
            'proud', 'happy', 'satisfied', 'accomplished', 'achieved', 'completed',
            'enjoyed', 'fun', 'loved', 'nice', 'solid', 'pleased', 'successful'
        ]
        if any(kw in text_lower for kw in positive_keywords):
            return 'positive'
        
        # Negative indicators
        negative_keywords = [
            'bad', 'poor', 'worse', 'decline', 'difficult', 'tough', 'hard', 'tired',
            'fatigued', 'sore', 'disappointed', 'frustrated', 'discouraged', 'setback',
            'problem', 'issue', 'concern', 'worried', 'anxious', 'stressed'
        ]
        if any(kw in text_lower for kw in negative_keywords):
            return 'negative'
        
        # Default to neutral
        return 'neutral'
    
    def get_achievements_by_category(self, category: Optional[str] = None, limit: Optional[int] = None) -> List[Achievement]:
        """
        Get achievements, optionally filtered by category and limited.
        
        Args:
            category: One of: distance, power, endurance, technical, event, consistency (or None for all)
            limit: Max number to return (most recent first)
        
        Returns:
            List of Achievement objects
        """
        filtered = [ach for ach in self.achievements if category is None or ach.category == category]
        # Sort by date, most recent first
        filtered.sort(key=lambda x: x.date, reverse=True)
        return filtered[:limit] if limit else filtered
    
    def get_goals_by_priority(self, status: str = 'active', limit: Optional[int] = None) -> List[Goal]:
        """
        Get goals sorted by priority (1=highest to 5=lowest).
        
        Args:
            status: Filter by status ('active', 'completed', 'paused', 'abandoned')
            limit: Max number to return
        
        Returns:
            List of Goal objects sorted by priority
        """
        filtered = [goal for goal in self.goals if goal.status == status]
        # Sort by priority (1 first), then by added date (newer first)
        filtered.sort(key=lambda x: (x.priority, x.added_date), reverse=False)
        return filtered[:limit] if limit else filtered
    
    def get_goals_by_category(self, category: str, status: str = 'active') -> List[Goal]:
        """Get goals filtered by category and status."""
        return [goal for goal in self.goals if goal.category == category and goal.status == status]
    
    def update_goal_status(self, goal_description: str, new_status: str, progress_note: Optional[str] = None):
        """
        Update the status of a goal.
        
        Args:
            goal_description: Description or partial match of goal
            new_status: One of: active, completed, paused, abandoned
            progress_note: Optional note about the update
        """
        today = datetime.now().strftime('%Y-%m-%d')
        
        for goal in self.goals:
            if goal_description.lower() in goal.description.lower():
                goal.status = new_status
                if progress_note:
                    goal.progress_notes.append(f"{today}: {progress_note}")
                else:
                    goal.progress_notes.append(f"{today}: Status changed to {new_status}")
                self.save()
                return True
        return False
    
    def update_goal_priority(self, goal_description: str, new_priority: int, reason: Optional[str] = None):
        """
        Update the priority of a goal.
        
        Args:
            goal_description: Description or partial match of goal
            new_priority: New priority (1-5)
            reason: Optional reason for priority change
        """
        today = datetime.now().strftime('%Y-%m-%d')
        
        for goal in self.goals:
            if goal_description.lower() in goal.description.lower():
                old_priority = goal.priority
                goal.priority = new_priority
                note = f"{today}: Priority changed from {old_priority} to {new_priority}"
                if reason:
                    note += f" - {reason}"
                goal.progress_notes.append(note)
                self.save()
                return True
        return False
    
    def get_achievement_stats(self) -> Dict:
        """
        Get statistics about achievements by category.
        
        Returns:
            Dict with counts and recent achievements per category
        """
        stats = {
            'total': len(self.achievements),
            'by_category': {},
            'recent': self.get_achievements_by_category(limit=5)
        }
        
        categories = ['distance', 'power', 'endurance', 'technical', 'event', 'consistency']
        for category in categories:
            achievements_in_category = self.get_achievements_by_category(category)
            stats['by_category'][category] = {
                'count': len(achievements_in_category),
                'most_recent': achievements_in_category[0].to_dict() if achievements_in_category else None
            }
        
        return stats
    
    def get_goal_stats(self) -> Dict:
        """
        Get statistics about goals by priority and status.
        
        Returns:
            Dict with counts by priority/status and top priorities
        """
        stats = {
            'total': len(self.goals),
            'by_status': {},
            'by_priority': {},
            'top_priorities': [g.to_dict() for g in self.get_goals_by_priority(limit=3)]
        }
        
        # Count by status
        for status in ['active', 'completed', 'paused', 'abandoned']:
            stats['by_status'][status] = len([g for g in self.goals if g.status == status])
        
        # Count by priority
        for priority in range(1, 6):
            goals_at_priority = [g for g in self.goals if g.priority == priority and g.status == 'active']
            stats['by_priority'][priority] = len(goals_at_priority)
        
        return stats
    
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
    
    def analyze_multi_week_patterns(self, weeks_back: int = 4) -> Dict:
        """
        **NEW: Multi-Week Pattern Recognition**
        
        Analyze trends across multiple weeks of coaching continuity.
        Identifies patterns in:
        - Power progression (improving, stable, declining)
        - Training compliance (consistent, inconsistent)
        - Recovery trends (improving, stable, declining)
        - Recurring issues/strengths
        
        Args:
            weeks_back: Number of weeks to analyze (default 4)
        
        Returns:
            Dict with detected patterns and trends
        """
        recent_continuity = self.coaching_continuity[-weeks_back:] if weeks_back <= len(self.coaching_continuity) else self.coaching_continuity
        
        if not recent_continuity:
            return {'patterns_detected': False, 'message': 'Insufficient data for pattern analysis'}
        
        patterns = {
            'patterns_detected': True,
            'weeks_analyzed': len(recent_continuity),
            'power_trend': None,
            'compliance_trend': None,
            'recovery_trend': None,
            'recurring_strengths': [],
            'recurring_concerns': [],
            'insights': []
        }
        
        # Analyze power-related keywords across weeks
        power_keywords_positive = ['power improvement', 'ftp increase', 'stronger', 'power up', 'threshold improved']
        power_keywords_negative = ['power decline', 'ftp drop', 'weaker', 'struggling with power']
        
        power_mentions = []
        for cont in recent_continuity:
            all_text = ' '.join(cont.key_observations + cont.progression_notes).lower()
            if any(kw in all_text for kw in power_keywords_positive):
                power_mentions.append('positive')
            elif any(kw in all_text for kw in power_keywords_negative):
                power_mentions.append('negative')
            else:
                power_mentions.append('neutral')
        
        # Determine power trend
        if power_mentions.count('positive') >= len(power_mentions) * 0.6:
            patterns['power_trend'] = 'improving'
            patterns['insights'].append("Power metrics showing consistent improvement over multiple weeks")
        elif power_mentions.count('negative') >= len(power_mentions) * 0.4:
            patterns['power_trend'] = 'declining'
            patterns['insights'].append("Power metrics showing decline - may need recovery week or training adjustment")
        else:
            patterns['power_trend'] = 'stable'
        
        # Analyze compliance trends
        compliance_keywords = ['compliance', 'consistency', 'adherence', 'completed', 'missed']
        compliance_mentions = []
        for cont in recent_continuity:
            all_text = ' '.join(cont.key_observations + cont.progression_notes).lower()
            if 'high compliance' in all_text or 'strong consistency' in all_text or 'excellent adherence' in all_text:
                compliance_mentions.append('high')
            elif 'low compliance' in all_text or 'missed' in all_text or 'inconsistent' in all_text:
                compliance_mentions.append('low')
            else:
                compliance_mentions.append('moderate')
        
        if compliance_mentions.count('high') >= len(compliance_mentions) * 0.6:
            patterns['compliance_trend'] = 'consistently_high'
            patterns['recurring_strengths'].append("Excellent training consistency and adherence")
        elif compliance_mentions.count('low') >= len(compliance_mentions) * 0.4:
            patterns['compliance_trend'] = 'inconsistent'
            patterns['recurring_concerns'].append("Inconsistent training adherence - life balance may need attention")
        else:
            patterns['compliance_trend'] = 'moderate'
        
        # Analyze recovery patterns
        # Positive indicators: explicit recovery weeks, positive recovery mentions in observations
        recovery_keywords_positive = ['recovering well', 'good recovery', 'fresh', 'rested', 
                                     'recovery week', 'deload', 'recovery execution', 
                                     'recovery capacity', 'strong recovery']
        # Negative indicators: fatigue/tiredness in KEY OBSERVATIONS (current state, not future monitoring)
        recovery_keywords_negative = ['not recovering', 'burnout', 'exhausted', 
                                     'fatigue accumulation', 'chronic fatigue', 'overreaching']
        
        recovery_mentions = []
        for cont in recent_continuity:
            # Check key observations and progression notes for CURRENT recovery state
            observations_text = ' '.join(cont.key_observations + cont.progression_notes).lower()
            
            # Positive: Recovery week execution or explicit positive recovery mentions
            if any(kw in observations_text for kw in recovery_keywords_positive):
                recovery_mentions.append('positive')
            # Negative: Fatigue mentioned as CURRENT problem in observations (not just future monitoring)
            elif any(kw in observations_text for kw in recovery_keywords_negative):
                recovery_mentions.append('negative')
            # Also check if "fatigue" appears as CURRENT issue, not future monitoring
            elif 'fatigue' in observations_text and 'despite' not in observations_text:
                # "despite fatigue" means they're performing well despite it = not a problem
                # Plain "fatigue" as observation = current issue
                recovery_mentions.append('negative')
            else:
                recovery_mentions.append('neutral')
        
        # Determine recovery trend - be more conservative about flagging decline
        if recovery_mentions.count('negative') >= len(recovery_mentions) * 0.6:  # Changed from 0.5
            patterns['recovery_trend'] = 'declining'
            patterns['recurring_concerns'].append("Recovery showing signs of decline - may need deload week")
            patterns['insights'].append("Multiple weeks showing recovery concerns - prioritize rest")
        elif recovery_mentions.count('positive') >= len(recovery_mentions) * 0.4:  # Changed from 0.6
            patterns['recovery_trend'] = 'strong'
            patterns['recurring_strengths'].append("Consistent positive recovery signals")
        else:
            patterns['recovery_trend'] = 'adequate'
        
        # Find recurring priorities across weeks
        all_priorities = []
        for cont in recent_continuity:
            all_priorities.extend(cont.next_week_priorities)
        
        # Count frequency of similar priorities
        from collections import Counter
        priority_keywords = ['recovery', 'vo2max', 'threshold', 'endurance', 'intensity', 'volume']
        priority_counts = Counter()
        for priority in all_priorities:
            priority_lower = priority.lower()
            for keyword in priority_keywords:
                if keyword in priority_lower:
                    priority_counts[keyword] += 1
        
        # If something appears in >50% of weeks, it's recurring
        threshold = len(recent_continuity) * 0.5
        for keyword, count in priority_counts.items():
            if count >= threshold:
                patterns['insights'].append(f"Recurring focus area: {keyword} (mentioned in {count}/{len(recent_continuity)} weeks)")
        
        return patterns
    
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
