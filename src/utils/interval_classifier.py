"""
Interval Classifier

Refines detected intervals into specific workout types:
- Warmup: Initial low-intensity period
- Cooldown: Final low-intensity period  
- Work: High-intensity efforts (threshold, VO2max, sprint)
- Rest/Recovery: Low-intensity between work intervals
- Steady State: Continuous moderate intensity

Classification logic based on:
- Position in workout (start/end)
- Duration
- Intensity zone
- Power profile (steady vs. variable)

Author: Fitness Tracker
Created: January 1, 2026
"""

import numpy as np
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class IntervalClassifier:
    """
    Classifies detected intervals into specific workout types
    """
    
    def __init__(self, ftp: int):
        """
        Initialize interval classifier
        
        Args:
            ftp: Functional Threshold Power in watts
        """
        self.ftp = ftp
        
        # Classification thresholds
        self.warmup_max_duration = 25 * 60  # 25 minutes max warmup
        self.cooldown_min_start = 0.80  # Must be in last 20% of workout
        self.cooldown_max_duration = 20 * 60  # 20 minutes max cooldown
        
        self.sprint_max_duration = 30  # seconds
        self.vo2max_duration_range = (3 * 60, 8 * 60)  # 3-8 minutes
        self.threshold_duration_range = (8 * 60, 25 * 60)  # 8-25 minutes
        self.steady_state_min_duration = 20 * 60  # 20+ minutes
    
    def classify_work_interval(self, interval: Dict, workout_duration: int) -> str:
        """
        Classify a work interval into specific type
        
        Args:
            interval: Interval dictionary
            workout_duration: Total workout duration in seconds
            
        Returns:
            Refined interval type string
        """
        duration = interval['duration_sec']
        avg_power = interval['avg_power']
        zone = interval['intensity_zone']
        percent_ftp = interval['percent_ftp']
        
        # Sprint: Very short, very high power
        if duration <= self.sprint_max_duration and zone in ['Z5', 'Z6']:
            return 'sprint'
        
        # VO2max: 3-8 minutes at Z5-Z6
        if (self.vo2max_duration_range[0] <= duration <= self.vo2max_duration_range[1] and
            zone in ['Z5', 'Z6']):
            return 'vo2max'
        
        # Threshold: 8-25 minutes at Z4
        if (self.threshold_duration_range[0] <= duration <= self.threshold_duration_range[1] and
            zone == 'Z4'):
            return 'threshold'
        
        # Long threshold: 25+ minutes at Z4
        if duration > self.threshold_duration_range[1] and zone == 'Z4':
            return 'threshold_long'
        
        # Steady state: 20+ minutes at Z2-Z3
        if duration >= self.steady_state_min_duration and zone in ['Z2', 'Z3']:
            return 'steady_state'
        
        # Default: generic work interval
        return 'work'
    
    def is_warmup(self, interval: Dict, workout_duration: int, interval_index: int) -> bool:
        """
        Check if interval is a warmup
        
        Args:
            interval: Interval dictionary
            workout_duration: Total workout duration
            interval_index: Position in interval list
            
        Returns:
            True if this is a warmup interval
        """
        # Must be first or second interval
        if interval_index > 1:
            return False
        
        # Must be rest/low intensity
        if interval['type'] != 'rest':
            return False
        
        # Must be in Z1 or Z2
        if interval['intensity_zone'] not in ['Z1', 'Z2']:
            return False
        
        # Must not be too long
        if interval['duration_sec'] > self.warmup_max_duration:
            return False
        
        # Must start near beginning of workout
        if interval['start_time'] > 5 * 60:  # Allow 5 min delay
            return False
        
        return True
    
    def is_cooldown(self, interval: Dict, workout_duration: int, interval_index: int, total_intervals: int) -> bool:
        """
        Check if interval is a cooldown
        
        Args:
            interval: Interval dictionary
            workout_duration: Total workout duration
            interval_index: Position in interval list
            total_intervals: Total number of intervals
            
        Returns:
            True if this is a cooldown interval
        """
        # Must be last or second-to-last interval
        if interval_index < total_intervals - 2:
            return False
        
        # Must be rest/low intensity
        if interval['type'] != 'rest':
            return False
        
        # Must be in Z1 or Z2
        if interval['intensity_zone'] not in ['Z1', 'Z2']:
            return False
        
        # Must not be too long
        if interval['duration_sec'] > self.cooldown_max_duration:
            return False
        
        # Must be in last portion of workout
        relative_position = interval['start_time'] / workout_duration
        if relative_position < self.cooldown_min_start:
            return False
        
        return True
    
    def classify_intervals(self, intervals_data: Dict) -> Dict:
        """
        Classify all intervals in a workout
        
        Args:
            intervals_data: Dictionary from IntervalDetector.detect_intervals()
            
        Returns:
            Updated intervals_data with refined interval types
        """
        intervals = intervals_data['intervals']
        
        if not intervals:
            return intervals_data
        
        # Calculate workout duration
        workout_duration = max(interval['end_time'] for interval in intervals)
        total_intervals = len(intervals)
        
        logger.info(f"Classifying {total_intervals} intervals from {workout_duration}s workout")
        
        # Classify each interval
        for i, interval in enumerate(intervals):
            original_type = interval['type']
            
            # Check for warmup
            if self.is_warmup(interval, workout_duration, i):
                interval['type'] = 'warmup'
                logger.debug(f"Interval {i+1}: warmup ({interval['duration_sec']}s)")
            
            # Check for cooldown
            elif self.is_cooldown(interval, workout_duration, i, total_intervals):
                interval['type'] = 'cooldown'
                logger.debug(f"Interval {i+1}: cooldown ({interval['duration_sec']}s)")
            
            # Refine work intervals
            elif original_type == 'work':
                refined_type = self.classify_work_interval(interval, workout_duration)
                interval['type'] = refined_type
                logger.debug(f"Interval {i+1}: {refined_type} ({interval['duration_sec']}s, {interval['intensity_zone']})")
            
            # Rest intervals stay as 'rest' (or could be 'recovery')
            elif original_type == 'rest':
                # If between work intervals, call it recovery
                if i > 0 and i < total_intervals - 1:
                    prev_interval = intervals[i-1]
                    next_interval = intervals[i+1]
                    if prev_interval['type'] != 'warmup' and next_interval['type'] != 'cooldown':
                        interval['type'] = 'recovery'
                        logger.debug(f"Interval {i+1}: recovery ({interval['duration_sec']}s)")
        
        # Add summary statistics
        interval_summary = self._generate_summary(intervals)
        intervals_data['summary'] = interval_summary
        
        logger.info(f"Classification complete: {interval_summary}")
        
        return intervals_data
    
    def _generate_summary(self, intervals: List[Dict]) -> Dict:
        """
        Generate summary statistics for classified intervals
        
        Args:
            intervals: List of classified interval dictionaries
            
        Returns:
            Summary dictionary
        """
        summary = {
            'total_intervals': len(intervals),
            'warmup_count': 0,
            'work_intervals': 0,
            'rest_intervals': 0,
            'cooldown_count': 0,
            'by_type': {}
        }
        
        for interval in intervals:
            interval_type = interval['type']
            
            # Update type-specific counts
            if interval_type not in summary['by_type']:
                summary['by_type'][interval_type] = {
                    'count': 0,
                    'total_duration': 0,
                    'avg_power': []
                }
            
            summary['by_type'][interval_type]['count'] += 1
            summary['by_type'][interval_type]['total_duration'] += interval['duration_sec']
            summary['by_type'][interval_type]['avg_power'].append(interval['avg_power'])
            
            # Update category counts
            if interval_type == 'warmup':
                summary['warmup_count'] += 1
            elif interval_type == 'cooldown':
                summary['cooldown_count'] += 1
            elif interval_type in ['rest', 'recovery']:
                summary['rest_intervals'] += 1
            else:
                summary['work_intervals'] += 1
        
        # Calculate averages
        for interval_type, data in summary['by_type'].items():
            if data['avg_power']:
                data['avg_power'] = round(np.mean(data['avg_power']), 1)
            else:
                data['avg_power'] = 0
        
        return summary
    
    def describe_workout_structure(self, intervals_data: Dict) -> str:
        """
        Generate human-readable description of workout structure
        
        Args:
            intervals_data: Classified intervals data
            
        Returns:
            Descriptive string
        """
        summary = intervals_data.get('summary', {})
        intervals = intervals_data.get('intervals', [])
        
        if not intervals:
            return "No intervals detected"
        
        parts = []
        
        # Warmup
        if summary.get('warmup_count', 0) > 0:
            warmup = [i for i in intervals if i['type'] == 'warmup'][0]
            parts.append(f"{warmup['duration_sec']//60}min warmup")
        
        # Work intervals
        work_count = summary.get('work_intervals', 0)
        if work_count > 0:
            # Group by type
            work_types = summary.get('by_type', {})
            
            for work_type in ['sprint', 'vo2max', 'threshold', 'threshold_long', 'steady_state', 'work']:
                if work_type in work_types:
                    type_data = work_types[work_type]
                    count = type_data['count']
                    avg_duration = type_data['total_duration'] / count
                    avg_power = type_data['avg_power']
                    
                    # Format description
                    if work_type == 'sprint':
                        parts.append(f"{count}x {int(avg_duration)}sec sprints @ {int(avg_power)}W")
                    elif work_type == 'vo2max':
                        parts.append(f"{count}x {int(avg_duration/60)}min VO2max @ {int(avg_power)}W")
                    elif work_type in ['threshold', 'threshold_long']:
                        parts.append(f"{count}x {int(avg_duration/60)}min threshold @ {int(avg_power)}W")
                    elif work_type == 'steady_state':
                        parts.append(f"{int(avg_duration/60)}min steady state @ {int(avg_power)}W")
                    else:
                        parts.append(f"{count}x work intervals @ {int(avg_power)}W")
        
        # Cooldown
        if summary.get('cooldown_count', 0) > 0:
            cooldown = [i for i in intervals if i['type'] == 'cooldown'][-1]
            parts.append(f"{cooldown['duration_sec']//60}min cooldown")
        
        return " + ".join(parts) if parts else "Unstructured workout"
