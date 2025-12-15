"""
🔍 AI Database Query Utilities
===============================
Provides read-only database query functions for the AI coach to analyze
historical training data and make informed coaching decisions.

🎯 Features:
- Safe, read-only queries
- Pre-built analysis functions (TSS trends, workout distribution, etc.)
- Raw SQL query capability for flexible analysis
- Data aggregation and statistical analysis
"""

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import json

# Import workout type analyzer
try:
    from .workout_type_analyzer import WorkoutTypeAnalyzer
except ImportError:
    from workout_type_analyzer import WorkoutTypeAnalyzer


class AICoachDatabaseQueries:
    """
    Database query interface for AI coaching system.
    
    🔒 Security: All queries are read-only to prevent accidental data modification.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            # Default to standard database location
            project_root = Path(__file__).parent.parent.parent
            db_path = project_root / "data" / "fitness_data.db"
        
        self.db_path = Path(db_path)
        
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found at {self.db_path}")
        
        # Initialize workout type analyzer
        self.workout_analyzer = WorkoutTypeAnalyzer(db_path)
    
    def _execute_query(self, query: str, params: tuple = ()) -> List[Dict]:
        """
        Execute a read-only query and return results as list of dicts.
        
        🔒 Safety: Opens connection in read-only mode
        """
        # Connect in read-only mode
        conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            results = [dict(row) for row in cursor.fetchall()]
            return results
        finally:
            conn.close()
    
    def get_recent_weeks_summary(self, num_weeks: int = 4) -> List[Dict]:
        """
        Get summary statistics for the last N weeks.
        
        Returns weekly totals of:
        - Total TSS
        - Total hours
        - Workout count by type
        - Average workout duration
        """
        query = """
        WITH weekly_data AS (
            SELECT 
                date(workout_day, 'weekday 0', '-6 days') as week_start,
                json_extract(workout_data, '$.type') as workout_type,
                COUNT(*) as workout_count,
                SUM(CAST(json_extract(workout_data, '$.TSS') AS REAL)) as total_tss,
                SUM(CAST(json_extract(workout_data, '$.TimeTotalInHours') AS REAL) * 60) as total_minutes
            FROM workouts
            WHERE workout_day >= date('now', '-' || ? || ' days')
            GROUP BY week_start, workout_type
        )
        SELECT 
            week_start,
            workout_type,
            workout_count,
            ROUND(total_tss, 1) as total_tss,
            ROUND(total_minutes / 60.0, 1) as total_hours,
            ROUND(total_minutes / workout_count, 0) as avg_duration_minutes
        FROM weekly_data
        ORDER BY week_start DESC, workout_type
        """
        
        results = self._execute_query(query, (num_weeks * 7,))
        
        # Aggregate by week
        weeks = {}
        for row in results:
            week_start = row['week_start']
            if week_start not in weeks:
                weeks[week_start] = {
                    'week_start': week_start,
                    'total_tss': 0,
                    'total_hours': 0,
                    'total_workouts': 0,
                    'by_type': {}
                }
            
            workout_type = row['workout_type']
            weeks[week_start]['by_type'][workout_type] = {
                'count': row['workout_count'],
                'tss': row['total_tss'],
                'hours': row['total_hours'],
                'avg_duration': row['avg_duration_minutes']
            }
            weeks[week_start]['total_tss'] += row['total_tss'] or 0
            weeks[week_start]['total_hours'] += row['total_hours'] or 0
            weeks[week_start]['total_workouts'] += row['workout_count']
        
        return list(weeks.values())
    
    def get_ftp_progression(self) -> List[Dict]:
        """
        Get FTP progression over time from weekly plans.
        
        Returns list of {week_start, ftp} showing FTP changes.
        """
        query = """
        SELECT 
            startDate as week_start,
            ftp
        FROM weekly_plans
        WHERE ftp IS NOT NULL
        ORDER BY startDate
        """
        
        return self._execute_query(query)
    
    def get_workout_compliance(self, num_weeks: int = 4) -> Dict:
        """
        Compare planned vs completed workouts.
        
        Returns:
        - Planned workout count
        - Completed workout count
        - Compliance percentage
        - Breakdown by workout type
        """
        # Get planned workouts
        planned_query = """
        SELECT 
            pw.type as workout_type,
            COUNT(*) as planned_count
        FROM proposed_workouts pw
        JOIN daily_plans dp ON pw.dailyPlanId = dp.id
        WHERE dp.date >= date('now', '-' || ? || ' days')
        GROUP BY pw.type
        """
        
        planned = self._execute_query(planned_query, (num_weeks * 7,))
        
        # Get completed workouts
        completed_query = """
        SELECT 
            json_extract(workout_data, '$.type') as workout_type,
            COUNT(*) as completed_count
        FROM workouts
        WHERE workout_day >= date('now', '-' || ? || ' days')
        GROUP BY workout_type
        """
        
        completed = self._execute_query(completed_query, (num_weeks * 7,))
        
        # Combine results
        planned_dict = {row['workout_type']: row['planned_count'] for row in planned}
        completed_dict = {row['workout_type']: row['completed_count'] for row in completed}
        
        all_types = set(planned_dict.keys()) | set(completed_dict.keys())
        
        compliance_by_type = {}
        total_planned = 0
        total_completed = 0
        
        for workout_type in all_types:
            planned_count = planned_dict.get(workout_type, 0)
            completed_count = completed_dict.get(workout_type, 0)
            
            compliance_by_type[workout_type] = {
                'planned': planned_count,
                'completed': completed_count,
                'compliance_pct': round((completed_count / planned_count * 100) if planned_count > 0 else 0, 1)
            }
            
            total_planned += planned_count
            total_completed += completed_count
        
        return {
            'total_planned': total_planned,
            'total_completed': total_completed,
            'overall_compliance_pct': round((total_completed / total_planned * 100) if total_planned > 0 else 0, 1),
            'by_type': compliance_by_type
        }
    
    def get_power_trends(self, num_weeks: int = 4) -> Dict:
        """
        Analyze power-related metrics for cycling workouts.
        
        Returns trends in:
        - Average power
        - Normalized power
        - Intensity factor
        - Variability index
        """
        query = """
        SELECT 
            date(workout_day, 'weekday 0', '-6 days') as week_start,
            AVG(CAST(json_extract(workout_data, '$.power_data.average') AS REAL)) as avg_power,
            AVG(CAST(json_extract(workout_data, '$.power_data.normalized_power') AS REAL)) as normalized_power,
            AVG(CAST(json_extract(workout_data, '$.power_data.intensity_factor') AS REAL)) as intensity_factor,
            COUNT(*) as workout_count
        FROM workouts
        WHERE json_extract(workout_data, '$.type') = 'Bike'
        AND workout_day >= date('now', '-' || ? || ' days')
        AND json_extract(workout_data, '$.power_data.average') IS NOT NULL
        GROUP BY week_start
        ORDER BY week_start DESC
        """
        
        results = self._execute_query(query, (num_weeks * 7,))
        
        return {
            'weekly_trends': results,
            'latest_avg_power': results[0]['avg_power'] if results else None,
            'trend': self._calculate_trend([r['avg_power'] for r in results if r['avg_power']])
        }
    
    def get_heart_rate_trends(self, num_weeks: int = 4) -> Dict:
        """
        Analyze heart rate metrics for all workouts.
        
        Returns trends in:
        - Average HR
        - Max HR
        - HR efficiency (power/HR ratio for cycling)
        """
        query = """
        SELECT 
            date(workout_day, 'weekday 0', '-6 days') as week_start,
            json_extract(workout_data, '$.type') as workout_type,
            AVG(CAST(json_extract(workout_data, '$.heart_rate_data.average_hr') AS REAL)) as avg_hr,
            AVG(CAST(json_extract(workout_data, '$.heart_rate_data.max_hr') AS REAL)) as max_hr,
            COUNT(*) as workout_count
        FROM workouts
        WHERE workout_day >= date('now', '-' || ? || ' days')
        AND json_extract(workout_data, '$.heart_rate_data.average_hr') IS NOT NULL
        GROUP BY week_start, workout_type
        ORDER BY week_start DESC, workout_type
        """
        
        results = self._execute_query(query, (num_weeks * 7,))
        
        return {
            'weekly_trends': results
        }
    
    def get_recent_workouts(self, num_workouts: int = 10, workout_type: Optional[str] = None) -> List[Dict]:
        """
        Get the N most recent workouts, optionally filtered by type.
        
        Returns full workout details including:
        - Date, title, type
        - Duration, TSS
        - Key metrics (power, HR, etc.)
        """
        type_filter = f"AND json_extract(workout_data, '$.type') = '{workout_type}'" if workout_type else ""
        
        query = f"""
        SELECT 
            workout_day,
            workout_title,
            json_extract(workout_data, '$.type') as workout_type,
            workout_data
        FROM workouts
        WHERE 1=1 {type_filter}
        ORDER BY workout_day DESC
        LIMIT ?
        """
        
        results = self._execute_query(query, (num_workouts,))
        
        # Parse workout_data JSON
        for row in results:
            if row['workout_data']:
                row['workout_data'] = json.loads(row['workout_data'])
        
        return results
    
    def _calculate_trend(self, values: List[float]) -> str:
        """
        Calculate simple trend (improving, declining, stable).
        
        Compares recent half to earlier half of data.
        """
        if not values or len(values) < 2:
            return "insufficient_data"
        
        mid = len(values) // 2
        recent_avg = sum(values[:mid]) / mid
        earlier_avg = sum(values[mid:]) / (len(values) - mid)
        
        change_pct = ((recent_avg - earlier_avg) / earlier_avg * 100) if earlier_avg > 0 else 0
        
        if change_pct > 2:
            return "improving"
        elif change_pct < -2:
            return "declining"
        else:
            return "stable"
    
    def custom_query(self, query: str, params: tuple = ()) -> List[Dict]:
        """
        Execute a custom read-only SQL query.
        
        ⚠️ Use with caution - ensure query is read-only!
        
        This allows the AI to perform custom analysis queries
        for specific questions.
        """
        # Basic safety check - prevent write operations
        query_lower = query.lower().strip()
        write_keywords = ['insert', 'update', 'delete', 'drop', 'create', 'alter', 'truncate']
        
        for keyword in write_keywords:
            if keyword in query_lower:
                raise ValueError(f"Write operation '{keyword}' not allowed in read-only queries")
        
        return self._execute_query(query, params)
    
    def get_recent_ai_analyses(self, num_analyses: int = 3) -> List[Dict]:
        """
        Get the most recent AI weekly analysis texts for coaching continuity.
        
        This allows the AI to reference its own prior insights when generating
        next week's plan, creating coaching continuity and narrative thread.
        
        **ENHANCED:** Now extracts week numbers using multiple patterns.
        
        Args:
            num_analyses: Number of recent analyses to retrieve (default 3)
            
        Returns:
            List of dicts with 'timestamp', 'week_number', 'week_info', 'analysis_text'
        """
        import re
        
        output_dir = Path(__file__).parent.parent.parent / "data" / "ai_coach_output"
        if not output_dir.exists():
            return []
        
        # Find all analysis files
        analysis_files = sorted(output_dir.glob("analysis_*.txt"), reverse=True)
        
        analyses = []
        for analysis_file in analysis_files[:num_analyses]:
            # Extract timestamp from filename (e.g., analysis_20251113_202851.txt)
            timestamp_str = analysis_file.stem.replace('analysis_', '')
            try:
                timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
            except ValueError:
                timestamp = None
            
            # Read analysis text
            analysis_text = analysis_file.read_text()
            
            # Extract week number using multiple patterns
            week_number = None
            week_info_line = None
            
            # Check first 10 lines for week references
            for line in analysis_text.split('\n')[:10]:
                # Pattern 1: "Week 52 Analysis" or "Week 52:" or "## Week 52"
                match = re.search(r'Week\s*(\d+)', line, re.IGNORECASE)
                if match:
                    week_number = int(match.group(1))
                    week_info_line = line.strip()
                    break
                
                # Pattern 2: "Training Week 52" or "52nd Week"
                match = re.search(r'(\d+)(?:st|nd|rd|th)?\s*Week', line, re.IGNORECASE)
                if match:
                    week_number = int(match.group(1))
                    week_info_line = line.strip()
                    break
                
                # Pattern 3: Date range (e.g., "December 9-15, 2025")
                if 'December' in line or 'November' in line or any(month in line for month in 
                   ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October']):
                    week_info_line = line.strip()
            
            # If no week number found, try to extract from accompanying JSON files
            if week_number is None:
                json_file = analysis_file.parent / f"coaching_result_{timestamp_str}.json"
                if json_file.exists():
                    try:
                        with open(json_file, 'r') as f:
                            result_data = json.load(f)
                            # Check for week_number in various locations
                            week_number = (
                                result_data.get('week_number') or
                                result_data.get('weekly_summary', {}).get('week_number') or
                                result_data.get('workout_plan', {}).get('weekNumber')
                            )
                    except:
                        pass
            
            analyses.append({
                'timestamp': timestamp.isoformat() if timestamp else timestamp_str,
                'week_number': week_number,
                'week_info': week_info_line or f'Week {week_number}' if week_number else 'Week info not found',
                'analysis_text': analysis_text[:2000],  # First 2000 chars for context
                'full_length': len(analysis_text),
                'date_analyzed': timestamp.strftime('%B %d, %Y') if timestamp else 'Unknown date'
            })
        
        return analyses
    
    def get_comprehensive_context(self, weeks_back: int = 4) -> Dict:
        """
        Get comprehensive training context for AI coach.
        
        This is the main method the AI will use to get all relevant
        historical data in one call.
        
        **NEW: Now includes prior AI analysis texts for coaching continuity!**
        """
        return {
            'weeks_analyzed': weeks_back,
            'weekly_summary': self.get_recent_weeks_summary(weeks_back),
            'ftp_progression': self.get_ftp_progression(),
            'workout_compliance': self.get_workout_compliance(weeks_back),
            'power_trends': self.get_power_trends(weeks_back),
            'heart_rate_trends': self.get_heart_rate_trends(weeks_back),
            'recent_workouts': self.get_recent_workouts(15),
            'workout_type_distribution': self.workout_analyzer.get_all_workout_types_summary(weeks_back),
            'workout_type_progressions': {
                'Threshold': self.workout_analyzer.analyze_workout_type_trends('Threshold', weeks_back * 3),
                'VO2max': self.workout_analyzer.analyze_workout_type_trends('VO2max', weeks_back * 3),
                'Endurance': self.workout_analyzer.analyze_workout_type_trends('Endurance', weeks_back * 3),
                'Tempo': self.workout_analyzer.analyze_workout_type_trends('Tempo', weeks_back * 3)
            },
            'previous_ai_analyses': self.get_recent_ai_analyses(num_analyses=3),
            'timestamp': datetime.now().isoformat()
        }


# Test functionality
if __name__ == "__main__":
    print("🔍 Testing AI Database Query Utilities\n")
    
    try:
        db = AICoachDatabaseQueries()
        
        print("📊 Getting 4-week training context...\n")
        context = db.get_comprehensive_context(weeks_back=4)
        
        print(f"✅ Successfully queried database")
        print(f"   Weeks analyzed: {context['weeks_analyzed']}")
        print(f"   Weekly summaries: {len(context['weekly_summary'])} weeks")
        print(f"   FTP history: {len(context['ftp_progression'])} entries")
        print(f"   Recent workouts: {len(context['recent_workouts'])} workouts")
        
        # Show latest week summary
        if context['weekly_summary']:
            latest_week = context['weekly_summary'][0]
            print(f"\n📅 Most Recent Week ({latest_week['week_start']}):")
            print(f"   Total TSS: {latest_week['total_tss']:.1f}")
            print(f"   Total Hours: {latest_week['total_hours']:.1f}")
            print(f"   Workouts: {latest_week['total_workouts']}")
            print(f"   By Type:")
            for workout_type, stats in latest_week['by_type'].items():
                tss_value = stats['tss'] if stats['tss'] is not None else 0
                print(f"     • {workout_type}: {stats['count']} workouts, {tss_value:.1f} TSS")
        
        # Show compliance
        compliance = context['workout_compliance']
        print(f"\n✅ Workout Compliance (last 4 weeks):")
        print(f"   Overall: {compliance['overall_compliance_pct']}% ({compliance['total_completed']}/{compliance['total_planned']} workouts)")
        
        # Show power trend
        power_trends = context['power_trends']
        print(f"\n⚡ Power Trends:")
        print(f"   Latest avg power: {power_trends['latest_avg_power']:.0f}W" if power_trends['latest_avg_power'] else "   No power data available")
        print(f"   Trend: {power_trends['trend']}")
        
    except FileNotFoundError as e:
        print(f"❌ Database not found: {e}")
        print("   This is normal if you haven't uploaded any workout data yet")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
