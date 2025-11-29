"""
Automated Daily Workout Analysis

Runs automatically to analyze completed workouts from FIT files.
Spreads Gemini API calls across the week to stay within rate limits.
"""

import os
import glob
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional
from pathlib import Path
import time

from src.storage.database import WorkoutDatabase
from src.utils.fit_file_analyzer import FitFileAnalyzer
from src.utils.fit_parser import FitParser


class DailyWorkoutAnalyzer:
    """Automatically analyze completed workouts on a daily basis"""
    
    def __init__(self, fit_files_directory: str = None, db_path: str = 'data/fitness_data.db'):
        """
        Initialize the daily analyzer
        
        Args:
            fit_files_directory: Directory to scan for FIT files (default: ~/Downloads)
            db_path: Path to the database
        """
        self.db = WorkoutDatabase(db_path)
        
        # Default to common locations for FIT files
        if fit_files_directory:
            self.fit_dir = os.path.expanduser(fit_files_directory)
        else:
            # Try multiple common locations
            possible_dirs = [
                '~/Downloads',
                '~/Documents/Zwift/Activities',
                '~/Documents/Garmin',
                '~/Library/Application Support/Zwift/Activities'
            ]
            for dir_path in possible_dirs:
                expanded = os.path.expanduser(dir_path)
                if os.path.exists(expanded):
                    self.fit_dir = expanded
                    break
            else:
                self.fit_dir = os.path.expanduser('~/Downloads')
        
        print(f"📁 Monitoring FIT files in: {self.fit_dir}")
    
    def find_todays_workouts(self, target_date: Optional[date] = None) -> List[str]:
        """
        Find FIT files from today (or specified date)
        
        Args:
            target_date: Date to search for (defaults to today)
            
        Returns:
            List of file paths for today's workouts
        """
        if target_date is None:
            target_date = datetime.now().date()
        
        todays_files = []
        
        # Search for .fit and .fit.gz files
        patterns = ['*.fit', '*.fit.gz', '*.FIT', '*.FIT.gz']
        
        for pattern in patterns:
            for filepath in glob.glob(os.path.join(self.fit_dir, pattern)):
                # Check file modification time
                file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath)).date()
                
                if file_mtime == target_date:
                    todays_files.append(filepath)
        
        return todays_files
    
    def check_if_already_analyzed(self, filepath: str) -> bool:
        """
        Check if a FIT file has already been analyzed
        
        Args:
            filepath: Path to the FIT file
            
        Returns:
            True if already analyzed, False otherwise
        """
        # For now, check by filename and date
        # TODO: Store FIT file hash in database for more robust checking
        filename = os.path.basename(filepath)
        
        # Simple check - in production, you'd want to store file hashes
        # For now, we'll just track by assuming one analysis per file per day
        return False  # Always analyze for now
    
    def analyze_workout_file(self, filepath: str, athlete_ftp: float = 258) -> Optional[Dict[str, Any]]:
        """
        Analyze a single workout file
        
        Args:
            filepath: Path to the FIT file
            athlete_ftp: Athlete's FTP
            
        Returns:
            Analysis result dictionary or None if failed
        """
        try:
            print(f"\n📊 Analyzing: {os.path.basename(filepath)}")
            
            # Read file content
            with open(filepath, 'rb') as f:
                file_content = f.read()
            
            # Initialize analyzer
            analyzer = FitFileAnalyzer()
            
            # Analyze the workout
            analysis_result = analyzer.analyze_workout(
                file_content,
                athlete_ftp=athlete_ftp,
                athlete_notes=None
            )
            
            if analysis_result:
                print(f"   ✅ Analysis complete")
                return analysis_result
            else:
                print(f"   ❌ Analysis failed")
                return None
        
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return None
    
    def store_analysis_results(self, analysis_result: Dict[str, Any], filepath: str) -> bool:
        """
        Store analysis results in the database
        
        Args:
            analysis_result: Result from FitFileAnalyzer
            filepath: Original file path
            
        Returns:
            True if stored successfully
        """
        try:
            parsed_data = analysis_result['parsed_data']
            peak_efforts = analysis_result['peak_efforts']
            ai_analysis = analysis_result['ai_analysis']
            
            # Store the AI analysis
            analysis_id = self.db.store_workout_analysis(
                workout_id=None,
                fit_file_id=None,
                analysis_text=ai_analysis,
                model_used="gemini-2.0-flash-exp"
            )
            
            print(f"   💾 Stored analysis (ID: {analysis_id})")
            
            # Store personal bests
            workout_date = parsed_data.get('start_time', '')[:10] if parsed_data.get('start_time') else str(datetime.now().date())
            
            new_pbs = []
            for effort_name, effort_data in peak_efforts.items():
                pb_id = self.db.store_personal_best(
                    effort_type=effort_name,
                    effort_value=effort_data['power'],
                    achieved_date=workout_date,
                    athlete_id='default'
                )
                if pb_id:
                    new_pbs.append(effort_name)
            
            if new_pbs:
                print(f"   🏆 New personal bests: {', '.join(new_pbs)}")
            
            return True
        
        except Exception as e:
            print(f"   ❌ Error storing results: {e}")
            return False
    
    def run_daily_analysis(self, athlete_ftp: float = 258, target_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Run the daily analysis workflow
        
        Args:
            athlete_ftp: Athlete's FTP
            target_date: Date to analyze (defaults to today)
            
        Returns:
            Summary of analysis results
        """
        if target_date is None:
            target_date = datetime.now().date()
        
        print(f"\n{'='*60}")
        print(f"🚴 Daily Workout Analysis - {target_date}")
        print(f"{'='*60}")
        
        # Find today's workouts
        workout_files = self.find_todays_workouts(target_date)
        
        if not workout_files:
            print(f"\n📭 No workout files found for {target_date}")
            return {
                'date': str(target_date),
                'files_found': 0,
                'files_analyzed': 0,
                'analyses_stored': 0,
                'new_pbs': 0
            }
        
        print(f"\n📂 Found {len(workout_files)} workout file(s):")
        for f in workout_files:
            print(f"   • {os.path.basename(f)}")
        
        # Analyze each workout
        results = {
            'date': str(target_date),
            'files_found': len(workout_files),
            'files_analyzed': 0,
            'analyses_stored': 0,
            'new_pbs': 0,
            'analyses': []
        }
        
        for filepath in workout_files:
            # Check if already analyzed
            if self.check_if_already_analyzed(filepath):
                print(f"\n⏭️  Skipping {os.path.basename(filepath)} (already analyzed)")
                continue
            
            # Analyze the workout
            analysis_result = self.analyze_workout_file(filepath, athlete_ftp)
            
            if analysis_result:
                results['files_analyzed'] += 1
                
                # Store results
                if self.store_analysis_results(analysis_result, filepath):
                    results['analyses_stored'] += 1
                    
                    # Count new PBs
                    peak_efforts = analysis_result.get('peak_efforts', {})
                    results['new_pbs'] += len(peak_efforts)
                
                results['analyses'].append({
                    'file': os.path.basename(filepath),
                    'summary': analysis_result['ai_analysis'][:200] + '...'
                })
            
            # Rate limiting: wait 6 seconds between analyses (10 per minute limit)
            if len(workout_files) > 1:
                print(f"   ⏳ Waiting 6s for rate limiting...")
                time.sleep(6)
        
        print(f"\n{'='*60}")
        print(f"✅ Analysis Complete!")
        print(f"   Files Found: {results['files_found']}")
        print(f"   Files Analyzed: {results['files_analyzed']}")
        print(f"   Analyses Stored: {results['analyses_stored']}")
        print(f"   Potential New PBs: {results['new_pbs']}")
        print(f"{'='*60}\n")
        
        return results


def run_daily_check():
    """
    Convenience function to run daily analysis
    Can be called from cron job or scheduled task
    """
    analyzer = DailyWorkoutAnalyzer()
    
    # Get athlete FTP from environment or use default
    ftp = float(os.environ.get('ATHLETE_FTP', 258))
    
    # Run analysis
    results = analyzer.run_daily_analysis(athlete_ftp=ftp)
    
    return results


if __name__ == "__main__":
    """Run daily analysis when script is executed directly"""
    import sys
    
    # Allow specifying a date via command line: python daily_workout_analyzer.py 2025-11-17
    if len(sys.argv) > 1:
        try:
            target_date = datetime.strptime(sys.argv[1], '%Y-%m-%d').date()
        except ValueError:
            print(f"Invalid date format. Use YYYY-MM-DD")
            sys.exit(1)
    else:
        target_date = None  # Use today
    
    analyzer = DailyWorkoutAnalyzer()
    ftp = float(os.environ.get('ATHLETE_FTP', 258))
    
    results = analyzer.run_daily_analysis(athlete_ftp=ftp, target_date=target_date)
