"""
Automatic Interval Detection

Detects intervals from workout power/HR data without manual tagging.
Uses rolling window analysis to identify state transitions (rest → work → rest).

Algorithm:
1. Calculate rolling averages over 30-second windows
2. Classify each window by intensity zone
3. Detect state transitions (rest/work changes)
4. Group consecutive work/rest periods into intervals
5. Apply minimum duration filters to avoid noise

Author: Fitness Tracker
Created: January 1, 2026
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class Interval:
    """Represents a detected interval"""
    id: int
    type: str  # 'warmup', 'work', 'rest', 'cooldown', 'steady_state'
    start_time: int  # seconds from workout start
    end_time: int  # seconds from workout start
    duration_sec: int
    avg_power: float
    normalized_power: float
    max_power: float
    avg_hr: Optional[float]
    max_hr: Optional[float]
    avg_cadence: Optional[float]
    intensity_zone: str  # 'Z1', 'Z2', 'Z3', 'Z4', 'Z5', 'Z6'
    percent_ftp: float


class IntervalDetector:
    """
    Detects intervals from workout power data
    """
    
    def __init__(self, ftp: int, weight_kg: Optional[float] = None):
        """
        Initialize interval detector
        
        Args:
            ftp: Functional Threshold Power in watts
            weight_kg: Athlete weight for power-to-weight calculations
        """
        self.ftp = ftp
        self.weight_kg = weight_kg
        
        # Training zones based on FTP (Coggan method)
        self.zones = {
            'Z1': (0, 0.55),      # Recovery
            'Z2': (0.55, 0.75),   # Endurance
            'Z3': (0.75, 0.90),   # Tempo
            'Z4': (0.90, 1.05),   # Threshold
            'Z5': (1.05, 1.20),   # VO2max
            'Z6': (1.20, 10.0)    # Anaerobic
        }
        
        # Detection parameters
        self.window_size = 30  # seconds for rolling average
        self.min_work_duration = 30  # minimum work interval duration
        self.min_rest_duration = 20  # minimum rest interval duration
        self.work_threshold_zone = 'Z3'  # minimum zone for "work"
        
    def classify_zone(self, power: float) -> str:
        """
        Classify power value into training zone
        
        Args:
            power: Power in watts
            
        Returns:
            Zone string ('Z1', 'Z2', etc.)
        """
        if power <= 0:
            return 'Z1'
        
        percent_ftp = power / self.ftp
        
        for zone, (lower, upper) in self.zones.items():
            if lower <= percent_ftp < upper:
                return zone
        
        return 'Z6'  # Above Z6 threshold
    
    def calculate_rolling_average(self, data: List[float], window: int) -> np.ndarray:
        """
        Calculate rolling average with specified window size
        
        Args:
            data: Time series data
            window: Window size in data points
            
        Returns:
            Array of rolling averages
        """
        if len(data) < window:
            return np.array(data)
        
        # Use numpy convolve for efficient rolling average
        weights = np.ones(window) / window
        return np.convolve(data, weights, mode='valid')
    
    def calculate_normalized_power(self, power_data: List[float]) -> float:
        """
        Calculate normalized power for a segment
        
        NP = fourth root of the average of the fourth power of power values
        
        Args:
            power_data: List of power values
            
        Returns:
            Normalized power in watts
        """
        if not power_data or len(power_data) == 0:
            return 0.0
        
        # Use 30-second rolling average first
        if len(power_data) >= 30:
            rolling_avg = self.calculate_rolling_average(power_data, 30)
        else:
            rolling_avg = power_data
        
        # Calculate NP: fourth root of average of fourth powers
        fourth_powers = np.power(rolling_avg, 4)
        avg_fourth_power = np.mean(fourth_powers)
        np_value = np.power(avg_fourth_power, 0.25)
        
        return float(np_value)
    
    def detect_state_transitions(self, power_stream: List[float]) -> List[Tuple[int, str]]:
        """
        Detect transitions between work and rest states
        
        Args:
            power_stream: List of power values (one per second)
            
        Returns:
            List of (time_index, state) tuples where state is 'work' or 'rest'
        """
        if len(power_stream) < self.window_size:
            logger.warning(f"Power stream too short ({len(power_stream)}s) for interval detection")
            return [(0, 'rest')]
        
        # Calculate rolling average
        rolling_power = self.calculate_rolling_average(power_stream, self.window_size)
        
        # Classify each window into zones
        states = []
        current_state = 'rest'
        
        for i, power in enumerate(rolling_power):
            zone = self.classify_zone(power)
            
            # Determine if this is "work" (Z3+) or "rest" (Z1-Z2)
            if zone in ['Z3', 'Z4', 'Z5', 'Z6']:
                new_state = 'work'
            else:
                new_state = 'rest'
            
            # Record state transitions
            if new_state != current_state:
                # Adjust index to account for rolling window offset
                actual_index = i + self.window_size // 2
                states.append((actual_index, new_state))
                current_state = new_state
        
        # Ensure we have a starting state
        if not states or states[0][0] > 0:
            states.insert(0, (0, 'rest'))
        
        return states
    
    def group_intervals(self, 
                       power_stream: List[float],
                       hr_stream: Optional[List[float]] = None,
                       cadence_stream: Optional[List[float]] = None) -> List[Interval]:
        """
        Group state transitions into intervals
        
        Args:
            power_stream: List of power values (one per second)
            hr_stream: Optional heart rate stream
            cadence_stream: Optional cadence stream
            
        Returns:
            List of detected Interval objects
        """
        # Detect state transitions
        transitions = self.detect_state_transitions(power_stream)
        
        if len(transitions) < 2:
            logger.warning("Not enough state transitions detected")
            return []
        
        intervals = []
        interval_id = 1
        
        # Create intervals from transitions
        for i in range(len(transitions) - 1):
            start_time = transitions[i][0]
            end_time = transitions[i + 1][0]
            state = transitions[i][1]
            duration = end_time - start_time
            
            # Apply minimum duration filters
            if state == 'work' and duration < self.min_work_duration:
                continue
            if state == 'rest' and duration < self.min_rest_duration:
                continue
            
            # Extract data for this interval
            power_segment = power_stream[start_time:end_time]
            
            if not power_segment:
                continue
            
            avg_power = float(np.mean(power_segment))
            max_power = float(np.max(power_segment))
            normalized_power = self.calculate_normalized_power(power_segment)
            percent_ftp = (avg_power / self.ftp) * 100
            zone = self.classify_zone(avg_power)
            
            # Calculate HR if available
            avg_hr = None
            max_hr = None
            if hr_stream and len(hr_stream) > end_time:
                hr_segment = hr_stream[start_time:end_time]
                if hr_segment:
                    avg_hr = float(np.mean([h for h in hr_segment if h > 0]))
                    max_hr = float(np.max(hr_segment))
            
            # Calculate cadence if available
            avg_cadence = None
            if cadence_stream and len(cadence_stream) > end_time:
                cadence_segment = cadence_stream[start_time:end_time]
                if cadence_segment:
                    avg_cadence = float(np.mean([c for c in cadence_segment if c > 0]))
            
            # Create interval
            interval = Interval(
                id=interval_id,
                type=state,  # Will be refined by classifier
                start_time=start_time,
                end_time=end_time,
                duration_sec=duration,
                avg_power=avg_power,
                normalized_power=normalized_power,
                max_power=max_power,
                avg_hr=avg_hr,
                max_hr=max_hr,
                avg_cadence=avg_cadence,
                intensity_zone=zone,
                percent_ftp=percent_ftp
            )
            
            intervals.append(interval)
            interval_id += 1
        
        # Handle final segment
        if transitions:
            last_transition = transitions[-1]
            start_time = last_transition[0]
            end_time = len(power_stream)
            state = last_transition[1]
            duration = end_time - start_time
            
            if (state == 'work' and duration >= self.min_work_duration) or \
               (state == 'rest' and duration >= self.min_rest_duration):
                
                power_segment = power_stream[start_time:end_time]
                
                if power_segment:
                    avg_power = float(np.mean(power_segment))
                    max_power = float(np.max(power_segment))
                    normalized_power = self.calculate_normalized_power(power_segment)
                    percent_ftp = (avg_power / self.ftp) * 100
                    zone = self.classify_zone(avg_power)
                    
                    avg_hr = None
                    max_hr = None
                    if hr_stream and len(hr_stream) >= end_time:
                        hr_segment = hr_stream[start_time:end_time]
                        if hr_segment:
                            avg_hr = float(np.mean([h for h in hr_segment if h > 0]))
                            max_hr = float(np.max(hr_segment))
                    
                    avg_cadence = None
                    if cadence_stream and len(cadence_stream) >= end_time:
                        cadence_segment = cadence_stream[start_time:end_time]
                        if cadence_segment:
                            avg_cadence = float(np.mean([c for c in cadence_segment if c > 0]))
                    
                    interval = Interval(
                        id=interval_id,
                        type=state,
                        start_time=start_time,
                        end_time=end_time,
                        duration_sec=duration,
                        avg_power=avg_power,
                        normalized_power=normalized_power,
                        max_power=max_power,
                        avg_hr=avg_hr,
                        max_hr=max_hr,
                        avg_cadence=avg_cadence,
                        intensity_zone=zone,
                        percent_ftp=percent_ftp
                    )
                    
                    intervals.append(interval)
        
        return intervals
    
    def detect_intervals(self,
                        power_stream: List[float],
                        hr_stream: Optional[List[float]] = None,
                        cadence_stream: Optional[List[float]] = None) -> Dict:
        """
        Main entry point: detect all intervals in a workout
        
        Args:
            power_stream: List of power values (one per second)
            hr_stream: Optional heart rate stream
            cadence_stream: Optional cadence stream
            
        Returns:
            Dictionary with detection metadata and list of intervals
        """
        from datetime import datetime
        
        logger.info(f"Detecting intervals from {len(power_stream)}s workout")
        
        # Detect and group intervals
        intervals = self.group_intervals(power_stream, hr_stream, cadence_stream)
        
        logger.info(f"Detected {len(intervals)} intervals")
        
        # Convert intervals to dictionaries for JSON storage
        intervals_dict = []
        for interval in intervals:
            intervals_dict.append({
                'id': interval.id,
                'type': interval.type,
                'start_time': interval.start_time,
                'end_time': interval.end_time,
                'duration_sec': interval.duration_sec,
                'avg_power': round(interval.avg_power, 1),
                'normalized_power': round(interval.normalized_power, 1),
                'max_power': round(interval.max_power, 1),
                'avg_hr': round(interval.avg_hr, 1) if interval.avg_hr else None,
                'max_hr': round(interval.max_hr, 1) if interval.max_hr else None,
                'avg_cadence': round(interval.avg_cadence, 1) if interval.avg_cadence else None,
                'intensity_zone': interval.intensity_zone,
                'percent_ftp': round(interval.percent_ftp, 1)
            })
        
        return {
            'detected_at': datetime.now().isoformat(),
            'algorithm_version': '1.0',
            'ftp_used': self.ftp,
            'detection_params': {
                'window_size': self.window_size,
                'min_work_duration': self.min_work_duration,
                'min_rest_duration': self.min_rest_duration
            },
            'interval_count': len(intervals),
            'intervals': intervals_dict
        }


def format_duration(seconds: int) -> str:
    """
    Format duration in seconds to human-readable string
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted string (e.g., "5:30", "1:23:45")
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes}:{secs:02d}"
