"""
Enhanced Daily Workout Analyzer (v2)

Automatically analyzes completed workouts on a daily basis.
Integrates with TrainingPeaks sync to automatically find today's workouts.

Features:
- Finds FIT files from TrainingPeaks downloads (~/Downloads/WorkoutFileExport-*)
- Also scans common FIT file locations as fallback
- Can run manually via Streamlit UI
- Can run automatically via cron (10pm PST)
- Spreads Gemini API calls across the week
"""

import os
import glob
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import time
import logging

from src.storage.database import WorkoutDatabase
from src.utils.fit_file_analyzer import FitFileAnalyzer
from src.utils.fit_parser import FitParser

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DailyWorkoutAnalyzerV2:
    """
    Enhanced daily workout analyzer with TrainingPeaks integration.
    
    Automatically finds and analyzes today's workouts from:
    1. TrainingPeaks extracted files (~/Downloads/WorkoutFileExport-*)
    2. Downloads folder (~/Downloads/*.fit)
    3. Zwift activities (~/Documents/Zwift/Activities/)
    4. Garmin activities (~/Documents/Garmin/)
    """
    
    def __init__(self, db_path: str = 'data/fitness_data.db'):
        """
        Initialize the daily analyzer
        
        Args:
            db_path: Path to the database
        """
        self.db = WorkoutDatabase(db_path)
        
        # Define search locations (in priority order)
        self.search_locations = [
            # TrainingPeaks extracted workouts (highest priority)
            os.path.expanduser('~/Downloads/trainingpeaks_extracted'),
            os.path.expanduser('~/Downloads/WorkoutFileExport-*'),  # Pattern for directories
            
            # Direct downloads
            os.path.expanduser('~/Downloads'),
            
            # Zwift
            os.path.expanduser('~/Documents/Zwift/Activities'),
            os.path.expanduser('~/Library/Application Support/Zwift/Activities'),
            
            # Garmin
            os.path.expanduser('~/Documents/Garmin'),
            os.path.expanduser('~/Library/Application Support/Garmin/Activities'),
        ]
        
        # Rate limiting (Gemini free tier: 10 requests/min, 1500/day)
        self.api_delay = 6  # seconds between API calls
        
        logger.info(f"Initialized DailyWorkoutAnalyzerV2 with database: {db_path}")
    
    def find_trainingpeaks_workouts(self, target_date: date = None) -> List[Path]:
        """
        Find FIT files from TrainingPeaks extracted directories.
        
        Args:
            target_date: Date to find workouts for (default: today)
            
        Returns:
            List of FIT file paths from TrainingPeaks
        """
        if target_date is None:
            target_date = date.today()
        
        fit_files = []
        downloads_dir = Path.home() / "Downloads"
        
        # Find TrainingPeaks extracted directories
        tp_patterns = [
            'trainingpeaks_extracted/WorkoutFileExport-*',
            'WorkoutFileExport-*'
        ]
        
        for pattern in tp_patterns:
            for tp_dir in downloads_dir.glob(pattern):
                if not tp_dir.is_dir():
                    continue
                
                logger.info(f"Scanning TrainingPeaks directory: {tp_dir}")
                
                # Find all .fit files (case-insensitive)
                for fit_file in tp_dir.rglob('*.[Ff][Ii][Tt]'):
                    # Check file modification date
                    mod_time = datetime.fromtimestamp(fit_file.stat().st_mtime).date()
                    
                    # Also try to parse the filename for date
                    # Format: YYYY-MM-DD-HH-MM-SS.fit or similar
                    try:
                        filename = fit_file.stem
                        if filename.count('-') >= 2:
                            parts = filename.split('-')
                            file_date = date(int(parts[0]), int(parts[1]), int(parts[2]))
                            if file_date == target_date:
                                fit_files.append(fit_file)
                                logger.info(f"Found TrainingPeaks workout (by filename): {fit_file.name}")
                                continue
                    except (ValueError, IndexError):
                        pass
                    
                    # Fall back to modification date
                    if mod_time == target_date:
                        fit_files.append(fit_file)
                        logger.info(f"Found TrainingPeaks workout (by date): {fit_file.name}")
        
        return fit_files
    
    def find_workouts_by_date(self, target_date: date = None) -> List[Path]:
        """
        Find all FIT files from target date across all locations.
        
        Args:
            target_date: Date to find workouts for (default: today)
            
        Returns:
            List of FIT file paths
        """
        if target_date is None:
            target_date = date.today()
        
        logger.info(f"Searching for workouts from {target_date}")
        
        # First, try TrainingPeaks (highest priority)
        fit_files = self.find_trainingpeaks_workouts(target_date)
        
        if fit_files:
            logger.info(f"Found {len(fit_files)} workouts from TrainingPeaks")
            return fit_files
        
        # Fall back to scanning other locations
        logger.info("No TrainingPeaks workouts found, scanning other locations...")
        
        for location in self.search_locations:
            # Skip TrainingPeaks patterns (already checked)
            if 'trainingpeaks' in location.lower() or 'WorkoutFileExport' in location:
                continue
            
            # Handle glob patterns (with *)
            if '*' in location:
                for dir_path in Path(location).parent.glob(Path(location).name):
                    if dir_path.is_dir():
                        fit_files.extend(self._scan_directory(dir_path, target_date))
            else:
                if os.path.exists(location):
                    fit_files.extend(self._scan_directory(location, target_date))
        
        # Remove duplicates (same file found in multiple locations)
        unique_files = list(set(fit_files))
        
        logger.info(f"Found {len(unique_files)} total workouts for {target_date}")
        return unique_files
    
    def _scan_directory(self, directory: str, target_date: date) -> List[Path]:
        """
        Scan a directory for FIT files from target date.
        
        Args:
            directory: Directory to scan
            target_date: Date to filter by
            
        Returns:
            List of matching FIT file paths
        """
        dir_path = Path(directory)
        fit_files = []
        
        if not dir_path.exists():
            return fit_files
        
        # Find all .fit files (case-insensitive)
        for fit_file in dir_path.glob('*.[Ff][Ii][Tt]'):
            # Check modification date
            mod_time = datetime.fromtimestamp(fit_file.stat().st_mtime).date()
            if mod_time == target_date:
                fit_files.append(fit_file)
                logger.info(f"Found workout in {directory}: {fit_file.name}")
        
        return fit_files
    
    def analyze_workout_file(
        self,
        fit_file_path: Path,
        ftp_watts: int = 330
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze a single workout FIT file.
        
        Args:
            fit_file_path: Path to FIT file
            ftp_watts: Athlete's FTP in watts
            
        Returns:
            Analysis results dict or None if failed
        """
        try:
            logger.info(f"Analyzing: {fit_file_path.name}")
            
            # Parse FIT file
            fit_parser = FitParser(str(fit_file_path))
            workout_data = fit_parser.parse()
            
            if not workout_data or 'records' not in workout_data or len(workout_data['records']) == 0:
                logger.warning(f"No data found in {fit_file_path.name}")
                return None
            
            # Create analyzer
            analyzer = FitFileAnalyzer(ftp_watts=ftp_watts)
            
            # Run analysis
            analysis = analyzer.analyze_workout(
                workout_data=workout_data,
                workout_name=fit_file_path.stem
            )
            
            # Compare to personal bests
            pb_results = analyzer.compare_peak_efforts_to_history(self.db)
            
            # Add metadata
            analysis['file_path'] = str(fit_file_path)
            analysis['file_name'] = fit_file_path.name
            analysis['analyzed_at'] = datetime.now().isoformat()
            analysis['personal_bests'] = pb_results
            
            logger.info(f"✅ Analysis complete for {fit_file_path.name}")
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze {fit_file_path}: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def store_analysis_results(
        self,
        analysis: Dict[str, Any],
        workout_id: Optional[int] = None
    ) -> bool:
        """
        Store analysis results and personal bests in database.
        
        Args:
            analysis: Analysis results from analyze_workout_file()
            workout_id: Optional database workout ID to link to
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Store the analysis
            analysis_id = self.db.store_workout_analysis(
                workout_id=workout_id,
                analysis_data=analysis['ai_analysis'],
                peak_efforts=analysis['peak_efforts'],
                model_used=analysis.get('model_used', 'gemini-2.0-flash-exp')
            )
            
            logger.info(f"Stored analysis with ID: {analysis_id}")
            
            # Store personal bests
            if 'personal_bests' in analysis:
                for pb in analysis['personal_bests']:
                    self.db.store_personal_best(
                        effort_type=pb['effort_type'],
                        effort_value=pb['value'],
                        achieved_date=pb['achieved_date'],
                        workout_id=workout_id,
                        analysis_id=analysis_id
                    )
                    logger.info(f"New personal best: {pb['effort_type']} = {pb['value']:.1f}W")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to store analysis: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def run_daily_analysis(
        self,
        target_date: date = None,
        ftp_watts: int = 330
    ) -> Dict[str, Any]:
        """
        Run daily analysis for all workouts from target date.
        
        Args:
            target_date: Date to analyze (default: today)
            ftp_watts: Athlete's FTP in watts
            
        Returns:
            Summary dict with results
        """
        if target_date is None:
            target_date = date.today()
        
        logger.info("=" * 60)
        logger.info(f"🔍 Daily Workout Analysis - {target_date}")
        logger.info("=" * 60)
        
        # Find workouts
        fit_files = self.find_workouts_by_date(target_date)
        
        if not fit_files:
            logger.info(f"No workouts found for {target_date}")
            return {
                'date': str(target_date),
                'workouts_found': 0,
                'workouts_analyzed': 0,
                'personal_bests': 0,
                'errors': []
            }
        
        logger.info(f"Found {len(fit_files)} workout(s) to analyze")
        
        results = {
            'date': str(target_date),
            'workouts_found': len(fit_files),
            'workouts_analyzed': 0,
            'personal_bests': 0,
            'errors': [],
            'analyses': []
        }
        
        # Analyze each workout
        for i, fit_file in enumerate(fit_files):
            logger.info(f"\n[{i+1}/{len(fit_files)}] Processing: {fit_file.name}")
            
            try:
                # Analyze
                analysis = self.analyze_workout_file(fit_file, ftp_watts)
                
                if analysis:
                    # Store results
                    success = self.store_analysis_results(analysis)
                    
                    if success:
                        results['workouts_analyzed'] += 1
                        results['analyses'].append({
                            'file': fit_file.name,
                            'duration_minutes': analysis['duration_minutes'],
                            'avg_power': analysis['avg_power'],
                            'summary': analysis['ai_analysis'].get('workout_quality', 'N/A')
                        })
                        
                        # Count personal bests
                        if 'personal_bests' in analysis:
                            results['personal_bests'] += len(analysis['personal_bests'])
                    else:
                        results['errors'].append(f"Failed to store analysis for {fit_file.name}")
                else:
                    results['errors'].append(f"Failed to analyze {fit_file.name}")
                
                # Rate limiting (except for last file)
                if i < len(fit_files) - 1:
                    logger.info(f"⏸️  Rate limiting: waiting {self.api_delay}s...")
                    time.sleep(self.api_delay)
                    
            except Exception as e:
                error_msg = f"Error processing {fit_file.name}: {str(e)}"
                logger.error(error_msg)
                results['errors'].append(error_msg)
        
        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("✅ Daily Analysis Complete")
        logger.info("=" * 60)
        logger.info(f"Workouts Found: {results['workouts_found']}")
        logger.info(f"Workouts Analyzed: {results['workouts_analyzed']}")
        logger.info(f"New Personal Bests: {results['personal_bests']}")
        if results['errors']:
            logger.info(f"Errors: {len(results['errors'])}")
            for error in results['errors']:
                logger.error(f"  - {error}")
        logger.info("=" * 60)
        
        return results
    
    def get_latest_analysis_summary(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get summary of recent analyses.
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of analysis summaries
        """
        # This would query the database for recent analyses
        # Implementation depends on your database schema
        pass


def run_daily_check(target_date: date = None, ftp_watts: int = 330) -> Dict[str, Any]:
    """
    Convenience function for cron job - runs daily analysis.
    
    Args:
        target_date: Date to analyze (default: today)
        ftp_watts: Athlete's FTP in watts
        
    Returns:
        Analysis results summary
    """
    analyzer = DailyWorkoutAnalyzerV2()
    return analyzer.run_daily_analysis(target_date=target_date, ftp_watts=ftp_watts)


if __name__ == "__main__":
    import sys
    
    # Allow specifying date via command line: python -m src.utils.daily_workout_analyzer_v2 2025-11-18
    target_date = None
    if len(sys.argv) > 1:
        try:
            target_date = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
            print(f"Analyzing workouts from: {target_date}")
        except ValueError:
            print(f"Invalid date format: {sys.argv[1]}")
            print("Usage: python -m src.utils.daily_workout_analyzer_v2 [YYYY-MM-DD]")
            sys.exit(1)
    
    # Run analysis
    results = run_daily_check(target_date=target_date)
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 ANALYSIS SUMMARY")
    print("=" * 60)
    print(f"Date: {results['date']}")
    print(f"Workouts Found: {results['workouts_found']}")
    print(f"Workouts Analyzed: {results['workouts_analyzed']}")
    print(f"New Personal Bests: {results['personal_bests']}")
    if results.get('analyses'):
        print("\nWorkout Details:")
        for analysis in results['analyses']:
            print(f"  • {analysis['file']}")
            print(f"    Duration: {analysis['duration_minutes']} min")
            print(f"    Avg Power: {analysis['avg_power']} W")
            print(f"    Quality: {analysis['summary']}")
    if results['errors']:
        print(f"\n⚠️  Errors: {len(results['errors'])}")
        for error in results['errors']:
            print(f"  - {error}")
    print("=" * 60)
