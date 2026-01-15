"""
Workout Comparison and Similarity Analysis

Compares cycling workouts to find similar sessions and track progress over time.
Inspired by Vekta's session comparison feature.
"""

from typing import Dict, List, Tuple, Optional, Any
import numpy as np
from datetime import datetime
import json


class WorkoutComparator:
    """Compare workouts and find similar sessions"""
    
    def __init__(self):
        """Initialize the comparator"""
        pass
    
    def calculate_similarity_score(self, workout1: Dict[str, Any], workout2: Dict[str, Any]) -> float:
        """
        Calculate similarity score between two workouts (0-100)
        
        Higher score = more similar workouts
        
        Factors:
        - TSS similarity (30% weight)
        - Duration similarity (25% weight)
        - Interval structure similarity (25% weight)
        - Power zone distribution similarity (20% weight)
        
        Args:
            workout1: First workout dict with workout_data and analysis_data
            workout2: Second workout dict with workout_data and analysis_data
            
        Returns:
            Similarity score (0-100)
        """
        scores = []
        weights = []
        
        # Extract data
        data1 = json.loads(workout1.get('workout_data', '{}'))
        data2 = json.loads(workout2.get('workout_data', '{}'))
        
        analysis1 = json.loads(workout1.get('analysis_data', '{}'))
        analysis2 = json.loads(workout2.get('analysis_data', '{}'))
        
        # 1. TSS Similarity (30% weight)
        tss1 = data1.get('tss')
        tss2 = data2.get('tss')
        if tss1 and tss2:
            tss_diff = abs(tss1 - tss2)
            tss_avg = (tss1 + tss2) / 2
            tss_similarity = max(0, 100 - (tss_diff / tss_avg * 100))
            scores.append(tss_similarity)
            weights.append(0.30)
        
        # 2. Duration Similarity (25% weight)
        duration1 = data1.get('duration')  # in minutes
        duration2 = data2.get('duration')
        if duration1 and duration2:
            duration_diff = abs(duration1 - duration2)
            duration_avg = (duration1 + duration2) / 2
            duration_similarity = max(0, 100 - (duration_diff / duration_avg * 100))
            scores.append(duration_similarity)
            weights.append(0.25)
        
        # 3. Interval Structure Similarity (25% weight)
        intervals1 = analysis1.get('intervals', {})
        intervals2 = analysis2.get('intervals', {})
        
        if intervals1 and intervals2:
            interval_similarity = self._compare_interval_structures(intervals1, intervals2)
            scores.append(interval_similarity)
            weights.append(0.25)
        
        # 4. Power Zone Distribution Similarity (20% weight)
        # This would compare how time was spent across zones
        # For now, use a simple check if both have power data
        has_power1 = 'tss' in data1 and data1.get('tss') is not None
        has_power2 = 'tss' in data2 and data2.get('tss') is not None
        if has_power1 and has_power2:
            # Placeholder - would calculate zone distribution similarity
            scores.append(80)  # Assume moderate similarity if both have power
            weights.append(0.20)
        
        # Calculate weighted average
        if not scores:
            return 0.0
        
        total_weight = sum(weights)
        if total_weight == 0:
            return 0.0
        
        weighted_score = sum(s * w for s, w in zip(scores, weights)) / total_weight
        return round(weighted_score, 1)
    
    def _compare_interval_structures(self, intervals1: Dict, intervals2: Dict) -> float:
        """
        Compare the structure of intervals between two workouts
        
        Returns similarity score (0-100)
        """
        list1 = intervals1.get('intervals', [])
        list2 = intervals2.get('intervals', [])
        
        if not list1 or not list2:
            return 0.0
        
        # Compare work interval counts
        work_types = ['work', 'vo2max', 'threshold', 'tempo']
        work1 = [i for i in list1 if i['type'] in work_types]
        work2 = [i for i in list2 if i['type'] in work_types]
        
        count_diff = abs(len(work1) - len(work2))
        count_score = max(0, 100 - (count_diff * 20))  # -20 points per interval difference
        
        # Compare interval durations
        if work1 and work2:
            durations1 = [i['duration_sec'] for i in work1]
            durations2 = [i['duration_sec'] for i in work2]
            
            avg_dur1 = np.mean(durations1)
            avg_dur2 = np.mean(durations2)
            
            dur_diff_pct = abs(avg_dur1 - avg_dur2) / ((avg_dur1 + avg_dur2) / 2) * 100
            duration_score = max(0, 100 - dur_diff_pct)
        else:
            duration_score = 0
        
        # Average the scores
        structure_score = (count_score + duration_score) / 2
        return round(structure_score, 1)
    
    def find_similar_workouts(self, target_workout: Dict[str, Any], 
                            candidate_workouts: List[Dict[str, Any]],
                            min_similarity: float = 50.0,
                            max_results: int = 5) -> List[Tuple[Dict[str, Any], float]]:
        """
        Find workouts similar to the target workout
        
        Args:
            target_workout: The workout to find matches for
            candidate_workouts: List of workouts to compare against
            min_similarity: Minimum similarity score to include (0-100)
            max_results: Maximum number of results to return
            
        Returns:
            List of (workout, similarity_score) tuples, sorted by similarity (highest first)
        """
        matches = []
        
        for candidate in candidate_workouts:
            # Don't compare workout to itself
            if candidate.get('id') == target_workout.get('id'):
                continue
            
            similarity = self.calculate_similarity_score(target_workout, candidate)
            
            if similarity >= min_similarity:
                matches.append((candidate, similarity))
        
        # Sort by similarity (highest first)
        matches.sort(key=lambda x: x[1], reverse=True)
        
        # Return top N matches
        return matches[:max_results]
    
    def compare_workouts_detailed(self, workout1: Dict[str, Any], 
                                 workout2: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform detailed comparison between two workouts
        
        Returns comprehensive comparison metrics for display
        
        Args:
            workout1: First workout (usually the more recent one)
            workout2: Second workout (usually the comparison/historical one)
            
        Returns:
            Dict with comparison metrics
        """
        data1 = json.loads(workout1.get('workout_data', '{}'))
        data2 = json.loads(workout2.get('workout_data', '{}'))
        
        analysis1 = json.loads(workout1.get('analysis_data', '{}'))
        analysis2 = json.loads(workout2.get('analysis_data', '{}'))
        
        comparison = {
            'workout1': {
                'id': workout1.get('id'),
                'date': workout1.get('workout_day'),
                'title': workout1.get('workout_title'),
            },
            'workout2': {
                'id': workout2.get('id'),
                'date': workout2.get('workout_day'),
                'title': workout2.get('workout_title'),
            },
            'metrics': {},
            'intervals': {},
            'improvements': []
        }
        
        # Compare basic metrics
        metrics = ['tss', 'duration', 'distance']
        for metric in metrics:
            val1 = data1.get(metric)
            val2 = data2.get(metric)
            
            if val1 is not None and val2 is not None:
                change = val1 - val2
                change_pct = (change / val2 * 100) if val2 != 0 else 0
                
                comparison['metrics'][metric] = {
                    'workout1': val1,
                    'workout2': val2,
                    'change': change,
                    'change_pct': round(change_pct, 1)
                }
        
        # Compare intervals
        intervals1 = analysis1.get('intervals', {})
        intervals2 = analysis2.get('intervals', {})
        
        if intervals1 and intervals2:
            comparison['intervals'] = self._compare_intervals_detailed(intervals1, intervals2)
        
        # Identify improvements
        comparison['improvements'] = self._identify_improvements(comparison)
        
        return comparison
    
    def _compare_intervals_detailed(self, intervals1: Dict, intervals2: Dict) -> Dict:
        """Compare interval execution between two workouts"""
        list1 = intervals1.get('intervals', [])
        list2 = intervals2.get('intervals', [])
        
        work_types = ['work', 'vo2max', 'threshold', 'tempo']
        work1 = [i for i in list1 if i['type'] in work_types]
        work2 = [i for i in list2 if i['type'] in work_types]
        
        comparison = {
            'work_interval_count': {
                'workout1': len(work1),
                'workout2': len(work2)
            }
        }
        
        if work1 and work2:
            # Compare average power across work intervals
            avg_power1 = np.mean([i['avg_power'] for i in work1])
            avg_power2 = np.mean([i['avg_power'] for i in work2])
            power_change = avg_power1 - avg_power2
            power_change_pct = (power_change / avg_power2 * 100) if avg_power2 != 0 else 0
            
            comparison['avg_work_power'] = {
                'workout1': round(avg_power1, 1),
                'workout2': round(avg_power2, 1),
                'change': round(power_change, 1),
                'change_pct': round(power_change_pct, 1)
            }
            
            # Compare average HR if available
            hrs1 = [i.get('avg_hr') for i in work1 if i.get('avg_hr')]
            hrs2 = [i.get('avg_hr') for i in work2 if i.get('avg_hr')]
            
            if hrs1 and hrs2:
                avg_hr1 = np.mean(hrs1)
                avg_hr2 = np.mean(hrs2)
                hr_change = avg_hr1 - avg_hr2
                hr_change_pct = (hr_change / avg_hr2 * 100) if avg_hr2 != 0 else 0
                
                comparison['avg_work_hr'] = {
                    'workout1': round(avg_hr1, 1),
                    'workout2': round(avg_hr2, 1),
                    'change': round(hr_change, 1),
                    'change_pct': round(hr_change_pct, 1)
                }
        
        return comparison
    
    def _identify_improvements(self, comparison: Dict) -> List[str]:
        """Identify key improvements between workouts"""
        improvements = []
        
        # Check TSS improvement
        if 'tss' in comparison['metrics']:
            tss_data = comparison['metrics']['tss']
            if tss_data['change'] > 5:
                improvements.append(f"Higher training load (+{tss_data['change']:.0f} TSS)")
        
        # Check power improvement
        if 'avg_work_power' in comparison.get('intervals', {}):
            power_data = comparison['intervals']['avg_work_power']
            if power_data['change'] > 5:
                improvements.append(f"Stronger intervals (+{power_data['change']:.0f}W avg)")
            elif power_data['change'] < -5:
                improvements.append(f"Lower power (-{abs(power_data['change']):.0f}W avg)")
        
        # Check HR efficiency
        if 'avg_work_hr' in comparison.get('intervals', {}):
            hr_data = comparison['intervals']['avg_work_hr']
            power_data = comparison['intervals'].get('avg_work_power', {})
            
            # Better efficiency = higher power at same/lower HR, or same power at lower HR
            if power_data.get('change', 0) > 0 and hr_data['change'] <= 0:
                improvements.append(f"Improved efficiency (more power at lower HR)")
            elif power_data.get('change', 0) >= 0 and hr_data['change'] < -3:
                improvements.append(f"Better cardiovascular efficiency (-{abs(hr_data['change']):.0f} bpm)")
        
        return improvements
