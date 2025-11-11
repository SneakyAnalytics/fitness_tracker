"""
TrainingPeaks File Processor

Handles extraction and processing of TrainingPeaks export files:
- Extracts ZIP files containing CSVs and FIT files
- Decompresses .fit.gz files to .fit format
- Organizes files for import
"""

import zipfile
import gzip
import shutil
from pathlib import Path
from typing import List, Dict, Tuple, Any, Optional
from datetime import datetime, timedelta


class TrainingPeaksFileProcessor:
    """Process TrainingPeaks export files."""
    
    def __init__(self, download_dir: Path, extract_dir: Path):
        """
        Initialize the file processor.
        
        Args:
            download_dir: Directory containing downloaded ZIP files
            extract_dir: Directory to extract files to
        """
        self.download_dir = Path(download_dir)
        self.extract_dir = Path(extract_dir)
        self.extract_dir.mkdir(parents=True, exist_ok=True)
    
    def extract_zip(self, zip_path: Path) -> Path:
        """
        Extract a ZIP file.
        
        Args:
            zip_path: Path to ZIP file
            
        Returns:
            Path to extraction directory
        """
        extract_path = self.extract_dir / zip_path.stem
        extract_path.mkdir(parents=True, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        
        return extract_path
    
    def decompress_fit_gz(self, fit_gz_path: Path) -> Path:
        """
        Decompress a .fit.gz file to .fit format.
        
        Args:
            fit_gz_path: Path to .fit.gz file
            
        Returns:
            Path to decompressed .fit file
        """
        fit_path = fit_gz_path.with_suffix('')  # Remove .gz extension
        
        with gzip.open(fit_gz_path, 'rb') as f_in:
            with open(fit_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        return fit_path
    
    def process_workout_files_export(self, zip_path: Path) -> List[Path]:
        """
        Process WorkoutFileExport ZIP containing .fit.gz files.
        
        Args:
            zip_path: Path to WorkoutFileExport ZIP
            
        Returns:
            List of paths to decompressed .fit files
        """
        # Extract ZIP
        extract_path = self.extract_zip(zip_path)
        
        # Find all .fit.gz files
        fit_gz_files = list(extract_path.rglob('*.fit.gz'))
        
        # Decompress each file
        fit_files = []
        for fit_gz in fit_gz_files:
            fit_file = self.decompress_fit_gz(fit_gz)
            fit_files.append(fit_file)
        
        return fit_files
    
    def process_workout_summary_export(self, zip_path: Path) -> Path:
        """
        Process WorkoutExport ZIP containing workout summary CSV.
        
        Args:
            zip_path: Path to WorkoutExport ZIP
            
        Returns:
            Path to extracted CSV file
        """
        extract_path = self.extract_zip(zip_path)
        
        # Find the CSV file
        csv_files = list(extract_path.glob('*.csv'))
        if not csv_files:
            raise FileNotFoundError(f"No CSV found in {zip_path}")
        
        return csv_files[0]
    
    def process_metrics_export(self, zip_path: Path) -> Path:
        """
        Process MetricsExport ZIP containing custom metrics CSV.
        
        Args:
            zip_path: Path to MetricsExport ZIP
            
        Returns:
            Path to extracted CSV file
        """
        extract_path = self.extract_zip(zip_path)
        
        # Find the CSV file
        csv_files = list(extract_path.glob('*.csv'))
        if not csv_files:
            raise FileNotFoundError(f"No CSV found in {zip_path}")
        
        return csv_files[0]
    
    def process_all_exports(self, 
                           workout_files_zip: Path,
                           workout_summary_zip: Path,
                           metrics_zip: Path) -> Dict[str, Any]:
        """
        Process all three TrainingPeaks export files.
        
        Args:
            workout_files_zip: WorkoutFileExport ZIP
            workout_summary_zip: WorkoutExport ZIP
            metrics_zip: MetricsExport ZIP
            
        Returns:
            Dict with paths to processed files
        """
        result = {
            'fit_files': [],
            'workout_summary_csv': None,
            'metrics_csv': None,
            'errors': []
        }
        
        # Process workout files (.fit.gz -> .fit)
        try:
            result['fit_files'] = self.process_workout_files_export(workout_files_zip)
        except Exception as e:
            result['errors'].append(f"Error processing workout files: {e}")
        
        # Process workout summary CSV
        try:
            result['workout_summary_csv'] = self.process_workout_summary_export(workout_summary_zip)
        except Exception as e:
            result['errors'].append(f"Error processing workout summary: {e}")
        
        # Process metrics CSV
        try:
            result['metrics_csv'] = self.process_metrics_export(metrics_zip)
        except Exception as e:
            result['errors'].append(f"Error processing metrics: {e}")
        
        return result
    
    def find_latest_exports(self, date_str: Optional[str] = None) -> Tuple[Optional[Path], Optional[Path], Optional[Path]]:
        """
        Find the latest export files in the download directory.
        
        Args:
            date_str: Optional date string to filter files (format: YYYY-MM-DD)
            
        Returns:
            Tuple of (workout_files_zip, workout_summary_zip, metrics_zip)
        """
        # Pattern for exported files: *Export-Robinson-Jake-*.zip
        workout_files = list(self.download_dir.glob('WorkoutFileExport-*.zip'))
        workout_summaries = list(self.download_dir.glob('WorkoutExport-*.zip'))
        metrics = list(self.download_dir.glob('MetricsExport-*.zip'))
        
        # Also check for directories (already extracted)
        workout_dirs = list(self.download_dir.glob('WorkoutFileExport-*'))
        workout_dirs = [d for d in workout_dirs if d.is_dir()]
        
        # Get most recent of each type (or None if not found)
        workout_file = None
        if workout_files:
            workout_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            workout_file = workout_files[0]
        elif workout_dirs:
            workout_dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            workout_file = workout_dirs[0]
        
        workout_summary = None
        if workout_summaries:
            workout_summaries.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            workout_summary = workout_summaries[0]
        
        metric = None
        if metrics:
            metrics.sort(key=lambda p: p.stat().st_mtime, reverse=True)
            metric = metrics[0]
        
        return workout_file, workout_summary, metric


def get_current_week_range() -> Tuple[str, str]:
    """
    Get Monday-Sunday date range for the current week.
    
    Returns:
        Tuple of (start_date, end_date) in MM/DD/YYYY format
    """
    today = datetime.now()
    
    # Find Monday of current week (0 = Monday, 6 = Sunday)
    days_since_monday = today.weekday()  # 0-6 where 0 is Monday
    monday = today - timedelta(days=days_since_monday)
    
    # Sunday is 6 days after Monday
    sunday = monday + timedelta(days=6)
    
    return monday.strftime("%m/%d/%Y"), sunday.strftime("%m/%d/%Y")
