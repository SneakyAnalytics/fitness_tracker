"""
🔍 Workout Type Analyzer
========================
Analyzes and classifies bike workouts by training zone/intensity.
Helps AI coach understand training progression and periodization patterns.

🎯 Features:
- Automatic workout classification from titles
- Zone-based analysis (Recovery, Endurance, Tempo, Threshold, VO2max)
- Power/IF trend analysis by workout type
- Progression tracking over time
"""

import sqlite3
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import json


class WorkoutTypeAnalyzer:
    """
    Analyzes bike workout patterns and classifications for AI coaching insights.
    """
    
    # Workout type classification patterns
    WORKOUT_PATTERNS = {
        'Recovery': [
            r'recovery',
            r'spin',
            r'easy spin',
            r'active recovery',
            r'rest day ride'
        ],
        'Endurance': [
            r'endurance',
            r'long',
            r'steady',
            r'z2',
            r'zone 2',
            r'base'
        ],
        'Tempo': [
            r'tempo',
            r'sweet spot',
            r'z3',
            r'zone 3'
        ],
        'Threshold': [
            r'threshold',
            r'ftp',
            r'z4',
            r'zone 4',
            r'lactate threshold',
            r'lt'
        ],
        'VO2max': [
            r'vo2',
            r'vo2max',
            r'z5',
            r'zone 5',
            r'anaerobic'
        ],
        'Race/Event': [
            r'race(?! simulation)',  # Match "race" but not "race simulation"
            r'event',
            r'group ride',
            r'ttt',
            r'criterium',
            r'gran fondo'
        ],
        'Test': [
            r'ftp test',
            r'ramp test',
            r'test protocol',
            r'assessment'
        ]
    }
    
    # Intensity Factor ranges for validation/classification
    IF_RANGES = {
        'Recovery': (0.0, 0.65),
        'Endurance': (0.65, 0.80),
        'Tempo': (0.80, 0.90),
        'Threshold': (0.90, 1.05),
        'VO2max': (1.05, 1.20),
        'Race/Event': (0.85, 1.20),  # Wide range
        'Test': (0.75, 1.20)  # Wide range
    }
    
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            project_root = Path(__file__).parent.parent.parent
            db_path = project_root / "data" / "fitness_data.db"
        
        self.db_path = Path(db_path)
        
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found at {self.db_path}")
    
    def _execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
        """Execute a read-only query and return results as list of dicts."""
        conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            results = [dict(row) for row in cursor.fetchall()]
            return results
        finally:
            conn.close()
    
    def classify_workout(self, title: str, intensity_factor: Optional[float] = None,
                        workout_type: str = 'Bike', duration_min: Optional[float] = None,
                        avg_hr: Optional[float] = None, hr_zones: Optional[Dict] = None) -> str:
        """
        Classify a workout based on type, title, and metrics.
        
        Args:
            title: Workout title
            intensity_factor: Power intensity factor (for bike workouts)
            workout_type: 'Bike', 'Run', 'Strength', 'Other', etc.
            duration_min: Workout duration in minutes
            avg_hr: Average heart rate
            hr_zones: Heart rate zone distribution dict
        
        Returns workout classification string
        """
        title_lower = title.lower()
        
        # Handle non-Bike workouts
        if workout_type == 'Run':
            return self._classify_run(title_lower, duration_min, avg_hr, hr_zones)
        elif workout_type in ('Strength', 'Other'):
            # Try to classify as Strength or Mobility
            strength_class = self._classify_strength(title_lower)
            if strength_class != 'Unclassified':
                return strength_class
            mobility_class = self._classify_mobility(title_lower, avg_hr)
            if mobility_class != 'Unclassified':
                return mobility_class
            return 'Other'
        
        # Bike workout classification (original logic)
        # Check each pattern category
        for bike_type, patterns in self.WORKOUT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, title_lower):
                    # If we have IF, validate it's in expected range
                    if intensity_factor is not None:
                        if_range = self.IF_RANGES.get(bike_type)
                        if if_range and if_range[0] <= intensity_factor <= if_range[1]:
                            return bike_type
                        # IF doesn't match expected range - title might be mislabeled
                        # Fall through to IF-based classification
                    else:
                        return bike_type
        
        # If no pattern match, try to classify by IF alone
        if intensity_factor is not None:
            for bike_type, (min_if, max_if) in self.IF_RANGES.items():
                if min_if <= intensity_factor <= max_if:
                    # Skip Race/Event and Test for IF-only classification
                    if bike_type not in ['Race/Event', 'Test']:
                        return bike_type
        
        return 'Unclassified'
    
    def _classify_run(self, title_lower: str, duration_min: Optional[float],
                     avg_hr: Optional[float], hr_zones: Optional[Dict]) -> str:
        """Classify running workouts."""
        # Pattern matching first
        if re.search(r'interval|speed|track|repeat', title_lower):
            return 'Run - Intervals'
        if re.search(r'tempo|threshold|marathon pace', title_lower):
            return 'Run - Tempo'
        if re.search(r'long run|distance', title_lower):
            return 'Run - Long'
        if re.search(r'easy|recovery|shake', title_lower):
            return 'Run - Easy'
        
        # HR-based classification (if available)
        if hr_zones:
            # Convert zone names to standardized format if needed
            z4_pct = hr_zones.get('Zone 4 (Threshold)', 0) + hr_zones.get('Zone 4', 0)
            z5_pct = hr_zones.get('Zone 5 (Maximum)', 0) + hr_zones.get('Zone 5', 0)
            z3_pct = hr_zones.get('Zone 3 (Tempo)', 0) + hr_zones.get('Zone 3', 0)
            z2_pct = hr_zones.get('Zone 2 (Endurance)', 0) + hr_zones.get('Zone 2', 0)
            
            # High intensity (Z4-Z5 > 50%)
            if (z4_pct + z5_pct) > 50:
                return 'Run - Intervals'
            # Tempo effort (Z3-Z4 > 50%)
            elif (z3_pct + z4_pct) > 50:
                return 'Run - Tempo'
            # Easy/recovery (Z2 dominant)
            elif z2_pct > 60:
                # Long run if duration > 60 min
                if duration_min and duration_min > 60:
                    return 'Run - Long'
                else:
                    return 'Run - Easy'
        
        # Duration-based fallback
        if duration_min:
            if duration_min > 75:
                return 'Run - Long'
            elif duration_min < 30:
                return 'Run - Easy'
        
        # Default
        return 'Run - Easy'
    
    def _classify_strength(self, title_lower: str) -> str:
        """Classify strength training workouts."""
        if re.search(r'upper body|chest|back|shoulder|arm|pull.*up|push.*up|bench', title_lower):
            return 'Strength - Upper Body'
        if re.search(r'lower body|leg|squat|deadlift|lunge|calf', title_lower):
            return 'Strength - Lower Body'
        if re.search(r'full body|total body|whole body', title_lower):
            return 'Strength - Full Body'
        if re.search(r'core|abs|plank|crunch', title_lower):
            return 'Strength - Core'
        if re.search(r'strength|lift|weight|gym', title_lower):
            return 'Strength - General'
        return 'Unclassified'
    
    def _classify_mobility(self, title_lower: str, avg_hr: Optional[float]) -> str:
        """Classify mobility/flexibility workouts."""
        if re.search(r'yoga', title_lower):
            return 'Mobility - Yoga'
        if re.search(r'stretch|flexibility|mobility', title_lower):
            return 'Mobility - Stretching'
        if re.search(r'foam roll|recovery|massage', title_lower):
            return 'Mobility - Recovery'
        
        # HR-based: very low HR suggests mobility work
        if avg_hr and avg_hr < 90:
            return 'Mobility - Recovery'
        
        return 'Unclassified'
    
    def get_workout_history_by_type(self, workout_type: str, 
                                     num_workouts: int = 10) -> List[Dict]:
        """
        Get most recent workouts of a specific type.
        
        Returns workout details including date, title, metrics, and progression.
        """
        query = """
        SELECT 
            workout_day,
            workout_title,
            json_extract(workout_data, '$.TSS') as tss,
            json_extract(workout_data, '$.TimeTotalInHours') as hours,
            json_extract(workout_data, '$.power_data.average') as avg_power,
            json_extract(workout_data, '$.power_data.normalized_power') as normalized_power,
            json_extract(workout_data, '$.power_data.intensity_factor') as intensity_factor,
            json_extract(workout_data, '$.heart_rate_data.average_hr') as avg_hr,
            workout_data
        FROM workouts
        WHERE json_extract(workout_data, '$.type') = 'Bike'
        ORDER BY workout_day DESC
        """
        
        all_workouts = self._execute_query(query)
        
        # Filter by workout type
        typed_workouts = []
        for workout in all_workouts:
            title = workout['workout_title']
            if_val = workout['intensity_factor']
            try:
                if_val = float(if_val) if if_val else None
            except (ValueError, TypeError):
                if_val = None
            
            classified_type = self.classify_workout(title, if_val)
            
            if classified_type == workout_type:
                typed_workouts.append({
                    'date': workout['workout_day'],
                    'title': workout['workout_title'],
                    'tss': float(workout['tss']) if workout['tss'] else None,
                    'duration_hours': float(workout['hours']) if workout['hours'] else None,
                    'avg_power': float(workout['avg_power']) if workout['avg_power'] else None,
                    'normalized_power': float(workout['normalized_power']) if workout['normalized_power'] else None,
                    'intensity_factor': if_val,
                    'avg_hr': float(workout['avg_hr']) if workout['avg_hr'] else None
                })
                
                if len(typed_workouts) >= num_workouts:
                    break
        
        return typed_workouts
    
    def analyze_workout_type_trends(self, workout_type: str, 
                                     weeks_back: int = 12) -> Dict:
        """
        Analyze trends for a specific workout type over time.
        
        Returns:
        - Count of workouts
        - Average metrics (power, IF, TSS, duration)
        - Progression indicators (improving, stable, declining)
        - Week-by-week breakdown
        """
        workouts = self.get_workout_history_by_type(workout_type, num_workouts=100)
        
        # Filter by date range
        cutoff_date = (datetime.now() - timedelta(weeks=weeks_back)).strftime('%Y-%m-%d')
        recent_workouts = [w for w in workouts if w['date'] >= cutoff_date]
        
        if not recent_workouts:
            return {
                'workout_type': workout_type,
                'count': 0,
                'message': f'No {workout_type} workouts found in last {weeks_back} weeks'
            }
        
        # Calculate averages
        metrics_with_values = {
            'avg_power': [w['avg_power'] for w in recent_workouts if w['avg_power']],
            'normalized_power': [w['normalized_power'] for w in recent_workouts if w['normalized_power']],
            'intensity_factor': [w['intensity_factor'] for w in recent_workouts if w['intensity_factor']],
            'tss': [w['tss'] for w in recent_workouts if w['tss']],
            'duration_hours': [w['duration_hours'] for w in recent_workouts if w['duration_hours']],
            'avg_hr': [w['avg_hr'] for w in recent_workouts if w['avg_hr']]
        }
        
        averages = {}
        trends = {}
        
        for metric, values in metrics_with_values.items():
            if values:
                averages[metric] = sum(values) / len(values)
                
                # Calculate trend (compare first half vs second half)
                if len(values) >= 4:
                    mid = len(values) // 2
                    recent_avg = sum(values[:mid]) / mid
                    earlier_avg = sum(values[mid:]) / (len(values) - mid)
                    
                    change_pct = ((recent_avg - earlier_avg) / earlier_avg * 100) if earlier_avg > 0 else 0
                    
                    if change_pct > 2:
                        trends[metric] = 'improving'
                    elif change_pct < -2:
                        trends[metric] = 'declining'
                    else:
                        trends[metric] = 'stable'
                else:
                    trends[metric] = 'insufficient_data'
        
        # Group by week
        weekly_breakdown = defaultdict(list)
        for workout in recent_workouts:
            workout_date = datetime.strptime(workout['date'], '%Y-%m-%d')
            week_start = (workout_date - timedelta(days=workout_date.weekday())).strftime('%Y-%m-%d')
            weekly_breakdown[week_start].append(workout)
        
        return {
            'workout_type': workout_type,
            'count': len(recent_workouts),
            'weeks_analyzed': weeks_back,
            'averages': averages,
            'trends': trends,
            'weekly_breakdown': dict(weekly_breakdown),
            'most_recent': recent_workouts[0] if recent_workouts else None
        }
    
    def get_all_workout_types_summary(self, weeks_back: int = 4) -> Dict:
        """
        Get summary of all workout types for periodization analysis.
        
        Returns distribution and trends for all workout types (Bike, Run, Strength, Mobility).
        """
        # Get all workouts (not just bike)
        query = """
        SELECT 
            workout_day,
            workout_title,
            json_extract(workout_data, '$.type') as workout_type,
            json_extract(workout_data, '$.power_data.intensity_factor') as intensity_factor,
            json_extract(workout_data, '$.metrics.actual_duration') as duration_min,
            json_extract(workout_data, '$.heart_rate_data.average_hr') as avg_hr,
            json_extract(workout_data, '$.heart_rate_data.zones') as hr_zones_json
        FROM workouts
        WHERE workout_day >= date('now', '-' || ? || ' days')
        ORDER BY workout_day DESC
        """
        
        workouts = self._execute_query(query, (weeks_back * 7,))
        
        # Classify all workouts
        type_counts = defaultdict(int)
        for workout in workouts:
            wtype = workout['workout_type'] or 'Bike'
            if_val = workout['intensity_factor']
            duration = workout['duration_min']
            avg_hr_val = workout['avg_hr']
            
            try:
                if_val = float(if_val) if if_val else None
            except (ValueError, TypeError):
                if_val = None
            
            try:
                duration = float(duration) if duration else None
            except (ValueError, TypeError):
                duration = None
            
            try:
                avg_hr_val = float(avg_hr_val) if avg_hr_val else None
            except (ValueError, TypeError):
                avg_hr_val = None
            
            # Parse HR zones
            hr_zones = None
            if workout['hr_zones_json']:
                try:
                    hr_zones = json.loads(workout['hr_zones_json'])
                except:
                    pass
            
            classified_type = self.classify_workout(
                workout['workout_title'], 
                if_val, 
                wtype,
                duration,
                avg_hr_val,
                hr_zones
            )
            type_counts[classified_type] += 1
        
        total_workouts = sum(type_counts.values())
        
        return {
            'weeks_analyzed': weeks_back,
            'total_workouts': total_workouts,
            'distribution': dict(type_counts),
            'distribution_pct': {
                wtype: round((count / total_workouts * 100), 1) 
                for wtype, count in type_counts.items()
            } if total_workouts > 0 else {}
        }
    
    def compare_workout_types(self, type1: str, type2: str, 
                              weeks_back: int = 12) -> Dict:
        """
        Compare two workout types side-by-side.
        
        Useful for analyzing periodization shifts (e.g., Endurance vs Threshold).
        """
        analysis1 = self.analyze_workout_type_trends(type1, weeks_back)
        analysis2 = self.analyze_workout_type_trends(type2, weeks_back)
        
        return {
            'weeks_analyzed': weeks_back,
            type1: analysis1,
            type2: analysis2,
            'ratio': {
                'count': f"{analysis1['count']}:{analysis2['count']}",
                'interpretation': self._interpret_ratio(type1, type2, 
                                                        analysis1['count'], 
                                                        analysis2['count'])
            }
        }
    
    def _interpret_ratio(self, type1: str, type2: str, count1: int, count2: int) -> str:
        """Provide coaching interpretation of workout type ratios."""
        if count1 == 0 and count2 == 0:
            return "No workouts of either type found"
        
        ratio = count1 / count2 if count2 > 0 else float('inf')
        
        # Context-specific interpretations
        if type1 == 'Endurance' and type2 == 'Threshold':
            if ratio > 3:
                return "Heavy base-building phase - appropriate for off-season"
            elif ratio > 1.5:
                return "Balanced endurance/threshold mix - typical build phase"
            elif ratio < 0.5:
                return "High threshold load - peak/race phase or potential overtraining risk"
            else:
                return "Moderate threshold emphasis - transition or maintenance phase"
        
        elif type1 == 'Recovery' and type2 in ['Threshold', 'VO2max']:
            if ratio < 0.3:
                return "Low recovery volume - monitor fatigue closely"
            elif ratio > 1:
                return "Good recovery balance - sustainable training load"
        
        return f"{type1}: {count1}, {type2}: {count2}"


# Test functionality
if __name__ == "__main__":
    print("🔍 Testing Workout Type Analyzer\n")
    
    try:
        analyzer = WorkoutTypeAnalyzer()
        
        # Test 1: Overall distribution
        print("=" * 80)
        print("📊 Workout Type Distribution (Last 4 Weeks)\n")
        summary = analyzer.get_all_workout_types_summary(weeks_back=4)
        
        print(f"Total bike workouts: {summary['total_bike_workouts']}")
        print(f"\nDistribution:")
        for wtype, count in sorted(summary['distribution'].items(), 
                                   key=lambda x: x[1], reverse=True):
            pct = summary['distribution_pct'].get(wtype, 0)
            print(f"  {wtype:15s}: {count:2d} workouts ({pct:4.1f}%)")
        
        # Test 2: Threshold workout analysis
        print("\n" + "=" * 80)
        print("📈 Threshold Workout Progression (Last 12 Weeks)\n")
        threshold_analysis = analyzer.analyze_workout_type_trends('Threshold', weeks_back=12)
        
        if threshold_analysis['count'] > 0:
            print(f"Workouts found: {threshold_analysis['count']}")
            print(f"\nAverages:")
            for metric, value in threshold_analysis['averages'].items():
                trend = threshold_analysis['trends'].get(metric, 'unknown')
                print(f"  {metric:20s}: {value:6.1f}  [{trend}]")
            
            if threshold_analysis.get('most_recent'):
                recent = threshold_analysis['most_recent']
                print(f"\nMost recent:")
                print(f"  Date: {recent['date']}")
                print(f"  {recent['title']}")
                np_str = f"{recent['normalized_power']:.0f}W" if recent['normalized_power'] else "N/A"
                if_str = f"{recent['intensity_factor']:.2f}" if recent['intensity_factor'] else "N/A"
                print(f"  NP: {np_str}, IF: {if_str}")
        else:
            print(threshold_analysis['message'])
        
        # Test 3: Endurance vs Threshold comparison
        print("\n" + "=" * 80)
        print("⚖️  Endurance vs Threshold Balance (Last 12 Weeks)\n")
        comparison = analyzer.compare_workout_types('Endurance', 'Threshold', weeks_back=12)
        
        print(f"Ratio: {comparison['ratio']['count']}")
        print(f"Interpretation: {comparison['ratio']['interpretation']}")
        
        # Test 4: Recent VO2max workouts
        print("\n" + "=" * 80)
        print("💨 Recent VO2max Workouts\n")
        vo2_workouts = analyzer.get_workout_history_by_type('VO2max', num_workouts=5)
        
        if vo2_workouts:
            for i, workout in enumerate(vo2_workouts, 1):
                if_str = f"{workout['intensity_factor']:.2f}" if workout['intensity_factor'] else "N/A"
                tss_str = f"{workout['tss']:.0f}" if workout['tss'] else "N/A"
                print(f"{i}. {workout['date']} - IF: {if_str}, TSS: {tss_str}")
                print(f"   {workout['title'][:70]}")
        else:
            print("No VO2max workouts found")
        
    except FileNotFoundError as e:
        print(f"❌ Database not found: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
