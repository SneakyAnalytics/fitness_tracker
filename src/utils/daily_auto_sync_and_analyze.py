"""
Automated Daily TrainingPeaks Sync & Analysis

Complete end-to-end automation:
1. Navigate to TrainingPeaks (headless browser)
2. Download today's workout files
3. Store in database via API
4. Run AI analysis with Gemini
5. Clean up temporary files

Designed to run at 10pm PST via cron job.
"""

import os
from pathlib import Path
from datetime import datetime, date, timedelta
import time
import shutil
import logging
from typing import Dict, Any, Optional

from .trainingpeaks_sync import TrainingPeaksSync
from .fit_file_analyzer import FitFileAnalyzer
from ..storage.database import WorkoutDatabase

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DailyAutoSyncAndAnalyze:
    """
    Complete daily automation workflow:
    - TrainingPeaks login & download
    - Database storage
    - AI analysis
    - Cleanup
    """
    
    def __init__(self, db_path: str = 'data/fitness_data.db'):
        """Initialize the daily automation system"""
        self.db = WorkoutDatabase(db_path)
        self.project_root = Path(__file__).parent.parent.parent
        self.downloads_dir = self.project_root / "data" / "trainingpeaks_downloads"
        self.tp_extract_dir = self.project_root / "data" / "trainingpeaks_extracted"
        
        # Rate limiting for Gemini API
        self.api_delay = 6  # seconds between analyses
        
        logger.info(f"Initialized daily automation with database: {db_path}")
    
    def get_today_date_range(self) -> tuple[str, str]:
        """
        Get today's date as start and end for TrainingPeaks export.
        
        Returns:
            Tuple of (start_date, end_date) in MM/DD/YYYY format
        """
        today = date.today()
        date_str = today.strftime("%m/%d/%Y")
        return date_str, date_str
    
    def sync_trainingpeaks(self, target_date: date = None) -> Dict[str, Any]:
        """
        Run TrainingPeaks sync to download and store workout data.
        
        Args:
            target_date: Date to sync (default: today)
            
        Returns:
            Sync results dict
        """
        if target_date is None:
            target_date = date.today()
        
        logger.info(f"=" * 60)
        logger.info(f"🔄 TrainingPeaks Sync - {target_date}")
        logger.info(f"=" * 60)
        
        try:
            # Use existing TrainingPeaks sync
            tp_sync = TrainingPeaksSync()
            
            # Run sync for target date (start_date = end_date = target_date)
            # Don't cleanup FIT files - we need them for AI analysis
            results = tp_sync.run_sync(start_date=target_date, end_date=target_date, cleanup_fit_files=False)
            
            if results:
                logger.info(f"✅ TrainingPeaks sync completed")
                logger.info(f"   FIT files uploaded: {results['fit_files']}")
                logger.info(f"   Workouts CSV: {'✅' if results['workouts'] else '❌'}")
                logger.info(f"   Metrics CSV: {'✅' if results['metrics'] else '❌'}")
                return results
            else:
                logger.error("❌ TrainingPeaks sync failed")
                return {
                    'fit_files': 0,
                    'workouts': False,
                    'metrics': False,
                    'errors': ['Sync failed']
                }
                
        except Exception as e:
            logger.error(f"❌ Error during TrainingPeaks sync: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'fit_files': 0,
                'workouts': False,
                'metrics': False,
                'errors': [str(e)]
            }
    
    def find_todays_fit_files(self, target_date: date = None) -> list[Path]:
        """
        Find FIT files from today's TrainingPeaks download.
        
        Args:
            target_date: Date to find files for (default: today)
            
        Returns:
            List of FIT file paths
        """
        if target_date is None:
            target_date = date.today()
        
        fit_files = []
        
        # Check TrainingPeaks extracted directory
        if self.tp_extract_dir.exists():
            logger.info(f"Scanning {self.tp_extract_dir} for FIT files...")
            
            # Find all .fit files
            for fit_file in self.tp_extract_dir.rglob('*.[Ff][Ii][Tt]'):
                # Check modification date
                mod_time = datetime.fromtimestamp(fit_file.stat().st_mtime).date()
                
                # Also try filename parsing (YYYY-MM-DD format)
                try:
                    filename = fit_file.stem
                    if filename.count('-') >= 2:
                        parts = filename.split('-')
                        file_date = date(int(parts[0]), int(parts[1]), int(parts[2]))
                        if file_date == target_date:
                            fit_files.append(fit_file)
                            logger.info(f"   Found: {fit_file.name} (by filename)")
                            continue
                except (ValueError, IndexError):
                    pass
                
                # Fall back to modification date
                if mod_time == target_date:
                    fit_files.append(fit_file)
                    logger.info(f"   Found: {fit_file.name} (by mod date)")
        
        logger.info(f"Found {len(fit_files)} FIT file(s) for {target_date}")
        return fit_files
    
    def analyze_workouts_from_database(
        self,
        target_date: date,
        ftp_watts: Optional[int] = None,
        results: Dict[str, Any] = None,
        reanalyze_existing: bool = False
    ) -> Dict[str, Any]:
        """
        Analyze workouts directly from database without needing FIT files on disk.
        
        Args:
            target_date: Date to analyze workouts for
            ftp_watts: Athlete's FTP in watts
            results: Results dict to update (creates new if None)
            
        Returns:
            Updated results dict
        """
        if results is None:
            results = {
                'date': str(target_date),
                'sync_successful': True,
                'fit_files_downloaded': 0,
                'workouts_analyzed': 0,
                'personal_bests': 0,
                'errors': []
            }
        
        # Load FTP if not provided
        if ftp_watts is None:
            settings = self.db.get_athlete_settings()
            ftp_watts = settings.get('ftp', 300)
        
        # Get workouts for this date (optionally reanalyze existing)
        import sqlite3
        import json
        conn = sqlite3.connect(self.db.db_path)
        c = conn.cursor()

        if reanalyze_existing:
            c.execute("""
                SELECT w.id, w.workout_day, w.workout_title, w.workout_data, w.fit_file_id
                FROM workouts w
                WHERE w.workout_day = ?
                ORDER BY w.id
            """, (str(target_date),))
        else:
            c.execute("""
                SELECT w.id, w.workout_day, w.workout_title, w.workout_data, w.fit_file_id
                FROM workouts w
                LEFT JOIN workout_analyses wa ON w.id = wa.workout_id
                WHERE w.workout_day = ? AND wa.id IS NULL
                ORDER BY w.id
            """, (str(target_date),))
        
        workouts_to_analyze = c.fetchall()
        conn.close()
        
        logger.info(f"Found {len(workouts_to_analyze)} workouts without analysis for {target_date}")
        
        # Step 3: Analyze each workout
        logger.info("")
        logger.info("STEP 3: AI Analysis (from database)")
        logger.info("-" * 60)
        
        for i, (workout_id, workout_day, workout_title, workout_data_json, fit_file_id) in enumerate(workouts_to_analyze):
            logger.info(f"[{i+1}/{len(workouts_to_analyze)}] {workout_title}")
            
            try:
                # Parse workout data
                workout_data = json.loads(workout_data_json) if isinstance(workout_data_json, str) else workout_data_json
                
                # Create analyzer
                analyzer = FitFileAnalyzer(use_dynamic_models=True)
                
                # Run analysis using the workout data
                analysis = analyzer.analyze_workout_from_parsed_data(
                    parsed_data=workout_data,
                    athlete_ftp=float(ftp_watts)
                )
                
                if analysis:
                    # Store analysis (full analysis object for UI + visualization)
                    self.db.store_workout_analysis(
                        workout_id=workout_id,
                        fit_file_id=fit_file_id,
                        analysis_text=analysis.get('ai_analysis', ''),
                        analysis_data=analysis,
                        peak_efforts=analysis.get('peak_efforts')
                    )
                    
                    results['workouts_analyzed'] += 1
                    # Personal bests are tracked when analyzing FIT files; keep count unchanged here
                    logger.info("   ✅ Analysis complete")
                else:
                    results['errors'].append(f"Failed to analyze {workout_title}")
                    logger.warning(f"   ⚠️  Analysis failed")
                
                # Rate limiting
                if i < len(workouts_to_analyze) - 1:
                    logger.info(f"   ⏸️  Rate limiting: {self.api_delay}s...")
                    time.sleep(self.api_delay)
                    
            except Exception as e:
                error_msg = f"Error analyzing {workout_title}: {str(e)}"
                logger.error(f"   ❌ {error_msg}")
                results['errors'].append(error_msg)
                import traceback
                traceback.print_exc()
        
        # Step 4: Cleanup (no files to clean if analyzing from DB)
        logger.info("")
        logger.info("STEP 4: Cleanup")
        logger.info("-" * 60)
        logger.info("   ℹ️  Analyzed from database, no files to clean up")
        
        # Final summary
        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ DAILY AUTOMATION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Date: {results['date']}")
        logger.info(f"Workouts Analyzed: {results['workouts_analyzed']}")
        logger.info(f"New Personal Bests: {results['personal_bests']}")
        if results['errors']:
            logger.info(f"Errors: {len(results['errors'])}")
            for error in results['errors']:
                logger.error(f"  - {error}")
        logger.info("=" * 60)
        
        return results
    
    def analyze_workout(
        self,
        fit_file_path: Path,
        ftp_watts: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze a single workout FIT file with AI.
        
        Args:
            fit_file_path: Path to FIT file
            ftp_watts: Athlete's FTP in watts (if None, loads from athlete_settings)
            
        Returns:
            Analysis results or None if failed
        """
        try:
            # Load FTP from database if not provided
            if ftp_watts is None:
                settings = self.db.get_athlete_settings()
                ftp_watts = settings.get('ftp', 300)  # Default to 300 if not found
                logger.info(f"Loaded FTP from athlete_settings: {ftp_watts}W")
            
            logger.info(f"🤖 Analyzing: {fit_file_path.name}")
            
            # Read FIT file content
            with open(fit_file_path, 'rb') as f:
                file_content = f.read()
            
            # Create analyzer with dynamic free model discovery
            # This ensures batch operations use free Gemini models instead of premium ones
            analyzer = FitFileAnalyzer(use_dynamic_models=True)
            analysis = analyzer.analyze_workout(
                fit_file_content=file_content,
                athlete_ftp=float(ftp_watts)
            )
            
            if not analysis:
                logger.warning(f"No data found in {fit_file_path.name}")
                return None
            
            # Get peak efforts for tracking
            peak_efforts = analysis.get('peak_efforts', {})
            
            # Add metadata
            analysis['file_path'] = str(fit_file_path)
            analysis['file_name'] = fit_file_path.name
            analysis['workout_date'] = datetime.now().date().isoformat()
            
            logger.info(f"   ✅ Analysis complete")
            return analysis
            
        except Exception as e:
            logger.error(f"   ❌ Failed to analyze {fit_file_path}: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def store_analysis(
        self,
        analysis: Dict[str, Any],
        workout_id: Optional[int] = None,
        fit_file_id: Optional[int] = None
    ) -> int:
        """
        Store analysis results and personal bests in database.
        
        Args:
            analysis: Analysis results
            workout_id: Optional database workout ID
            fit_file_id: Optional FIT file database ID
            
        Returns:
            Count of personal bests stored (0 if failed)
        """
        try:
            # Lookup FIT file ID by filename if not provided
            if not fit_file_id and 'file_name' in analysis:
                # Strip date prefix if present (format: YYYY-MM-DD-filename.fit)
                file_name = analysis['file_name']
                if file_name.count('-') >= 2:
                    parts = file_name.split('-', 3)  # Split max 3 times
                    if len(parts[0]) == 4 and parts[0].isdigit():  # Year
                        file_name = parts[3]  # Get everything after YYYY-MM-DD-
                
                fit_file_id = self.db.get_fit_file_id_by_name(file_name)
            
            # Lookup workout_id from fit_file if not provided
            # This links the analysis to the workout record for better UI display
            if not workout_id and fit_file_id:
                import sqlite3
                conn = sqlite3.connect(self.db.db_path)
                c = conn.cursor()
                c.execute('SELECT id FROM workouts WHERE fit_file_id = ?', (fit_file_id,))
                result = c.fetchone()
                if result:
                    workout_id = result[0]
                conn.close()
            
            # Store the analysis with full data for visualization
            analysis_id = self.db.store_workout_analysis(
                workout_id=workout_id,
                fit_file_id=fit_file_id,
                analysis_text=analysis.get('ai_analysis', ''),  # Text for display
                analysis_data=analysis,  # Full analysis object with parsed_data for viz
                peak_efforts=analysis.get('peak_efforts'),
                model_used='gemini-2.0-flash-exp'
            )
            
            logger.info(f"   💾 Stored analysis ID: {analysis_id}")
            
            # Store personal bests from peak efforts
            peak_efforts = analysis.get('peak_efforts', {})
            workout_date = analysis.get('workout_date', datetime.now().date().isoformat())
            pb_count = 0
            
            for effort_type, effort_data in peak_efforts.items():
                if isinstance(effort_data, dict) and 'power' in effort_data:
                    # Store each peak effort - database will handle ranking
                    pb_id = self.db.store_personal_best(
                        effort_type=effort_type,
                        effort_value=effort_data['power'],
                        achieved_date=workout_date,
                        workout_id=workout_id
                    )
                    if pb_id:
                        pb_count += 1
                        logger.info(f"   🏅 Stored PB: {effort_type} = {effort_data['power']:.1f}W")
            
            if pb_count > 0:
                logger.info(f"   💪 Total personal bests tracked: {pb_count}")
            
            return pb_count
            
        except Exception as e:
            logger.error(f"   ❌ Failed to store analysis: {str(e)}")
            return 0
    
    def cleanup_temp_files(self, target_date: date = None):
        """
        Clean up temporary TrainingPeaks files after processing.
        
        Args:
            target_date: Date to clean up files for (default: today)
        """
        if target_date is None:
            target_date = date.today()
        
        logger.info("🧹 Cleaning up temporary files...")
        
        # Clean extracted files
        if self.tp_extract_dir.exists():
            try:
                # Only remove files from target date
                for fit_file in self.tp_extract_dir.rglob('*.[Ff][Ii][Tt]'):
                    mod_time = datetime.fromtimestamp(fit_file.stat().st_mtime).date()
                    if mod_time == target_date:
                        fit_file.unlink()
                        logger.info(f"   🗑️  Removed: {fit_file.name}")
                
                # Remove empty directories
                for dir_path in self.tp_extract_dir.rglob('*'):
                    if dir_path.is_dir() and not any(dir_path.iterdir()):
                        dir_path.rmdir()
                        logger.info(f"   🗑️  Removed empty dir: {dir_path.name}")
                        
            except Exception as e:
                logger.error(f"   ⚠️  Cleanup error: {str(e)}")
        
        # Clean downloaded ZIP files from Downloads folder
        try:
            for pattern in ['WorkoutFileExport-*.zip', 'WorkoutExport-*.zip', 'MetricsExport-*.zip']:
                for zip_file in self.downloads_dir.glob(pattern):
                    mod_time = datetime.fromtimestamp(zip_file.stat().st_mtime).date()
                    if mod_time == target_date:
                        zip_file.unlink()
                        logger.info(f"   🗑️  Removed: {zip_file.name}")
        except Exception as e:
            logger.error(f"   ⚠️  ZIP cleanup error: {str(e)}")
        
        # Clean any remaining extraction directories in /tmp
        try:
            if self.tp_extract_dir.exists():
                import shutil
                for item in self.tp_extract_dir.iterdir():
                    if item.is_dir():
                        try:
                            shutil.rmtree(item)
                            logger.info(f"   🗑️  Removed temp dir: {item.name}")
                        except Exception as e:
                            logger.warning(f"   ⚠️  Could not remove {item.name}: {e}")
        except Exception as e:
            logger.error(f"   ⚠️  Temp dir cleanup error: {str(e)}")
        
        logger.info("✅ Cleanup complete")
    
    def run_daily_automation(
        self,
        target_date: date = None,
        ftp_watts: Optional[int] = None,
        cleanup: bool = True
    ) -> Dict[str, Any]:
        """
        Run the complete daily automation workflow.
        
        Args:
            target_date: Date to process (default: today)
            ftp_watts: Athlete's FTP in watts (if None, loads from athlete_settings)
            cleanup: Whether to clean up temp files after processing
            
        Returns:
            Results summary dict
        """
        if target_date is None:
            target_date = date.today()
        
        logger.info("")
        logger.info("=" * 60)
        logger.info(f"🚀 DAILY AUTOMATION - {target_date}")
        logger.info("=" * 60)
        logger.info("")
        
        results = {
            'date': str(target_date),
            'sync_successful': False,
            'fit_files_downloaded': 0,
            'workouts_analyzed': 0,
            'personal_bests': 0,
            'errors': []
        }
        
        # Step 1: Sync TrainingPeaks
        logger.info("STEP 1: TrainingPeaks Sync")
        logger.info("-" * 60)
        sync_results = self.sync_trainingpeaks(target_date)
        
        if sync_results and sync_results['fit_files'] > 0:
            results['sync_successful'] = True
            results['fit_files_downloaded'] = sync_results['fit_files']
        else:
            results['errors'].append("TrainingPeaks sync failed or no files found")
            logger.warning("⚠️  No FIT files downloaded, skipping analysis")
            return results
        
        # Step 2: Get FIT files from sync results
        logger.info("")
        logger.info("STEP 2: Get FIT Files from Sync")
        logger.info("-" * 60)
        fit_files = sync_results.get('fit_file_paths', [])
        
        if not fit_files:
            # Fallback: Analyze workouts directly from database
            logger.info("No FIT file paths in sync results, analyzing from database...")
            return self.analyze_workouts_from_database(target_date, ftp_watts, results)
        
        if not fit_files:
            results['errors'].append("No FIT files found after sync")
            logger.warning("⚠️  No FIT files found")
            return results
        
        logger.info(f"Found {len(fit_files)} FIT file(s) to analyze")
        
        # Step 3: Analyze each workout
        logger.info("")
        logger.info("STEP 3: AI Analysis")
        logger.info("-" * 60)
        
        for i, fit_file in enumerate(fit_files):
            logger.info(f"[{i+1}/{len(fit_files)}] {fit_file.name}")
            
            try:
                # Analyze
                analysis = self.analyze_workout(fit_file, ftp_watts)
                
                if analysis:
                    # Store results and get PB count
                    pb_count = self.store_analysis(analysis)
                    
                    results['workouts_analyzed'] += 1
                    results['personal_bests'] += pb_count
                else:
                    results['errors'].append(f"Failed to analyze {fit_file.name}")
                
                # Rate limiting (except for last file)
                if i < len(fit_files) - 1:
                    logger.info(f"   ⏸️  Rate limiting: {self.api_delay}s...")
                    time.sleep(self.api_delay)
                    
            except Exception as e:
                error_msg = f"Error processing {fit_file.name}: {str(e)}"
                logger.error(f"   ❌ {error_msg}")
                results['errors'].append(error_msg)
        
        # Step 4: Cleanup
        if cleanup:
            logger.info("")
            logger.info("STEP 4: Cleanup")
            logger.info("-" * 60)
            self.cleanup_temp_files(target_date)
        
        # Final summary
        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ DAILY AUTOMATION COMPLETE")
        logger.info("=" * 60)
        logger.info(f"Date: {results['date']}")
        logger.info(f"FIT Files Downloaded: {results['fit_files_downloaded']}")
        logger.info(f"Workouts Analyzed: {results['workouts_analyzed']}")
        logger.info(f"New Personal Bests: {results['personal_bests']}")
        if results['errors']:
            logger.info(f"Errors: {len(results['errors'])}")
            for error in results['errors']:
                logger.error(f"  - {error}")
        logger.info("=" * 60)
        logger.info("")
        
        return results


def run_daily_check(target_date: date = None, ftp_watts: Optional[int] = None) -> Dict[str, Any]:
    """
    Convenience function for cron job.
    
    Args:
        target_date: Date to process (default: today)
        ftp_watts: Athlete's FTP in watts (if None, loads from athlete_settings)
        
    Returns:
        Results summary
    """
    automation = DailyAutoSyncAndAnalyze()
    return automation.run_daily_automation(target_date=target_date, ftp_watts=ftp_watts)


if __name__ == "__main__":
    import sys
    
    # Allow specifying date via command line
    target_date = None
    if len(sys.argv) > 1:
        try:
            target_date = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
            print(f"Running automation for: {target_date}")
        except ValueError:
            print(f"Invalid date format: {sys.argv[1]}")
            print("Usage: python -m src.utils.daily_auto_sync_and_analyze [YYYY-MM-DD]")
            sys.exit(1)
    
    # Run automation
    results = run_daily_check(target_date=target_date)
    
    # Exit with error code if failed
    if results['workouts_analyzed'] == 0:
        sys.exit(1)
    else:
        sys.exit(0)
