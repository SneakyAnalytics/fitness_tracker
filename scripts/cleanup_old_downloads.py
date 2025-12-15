#!/usr/bin/env python3
"""
Clean up old TrainingPeaks and workout files from ~/Downloads folder.
These files are now stored in the project's data directory and database.
"""

from pathlib import Path
from datetime import datetime
import re
import zipfile

def is_uuid_filename(filename):
    """Check if filename matches UUID pattern."""
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return re.match(uuid_pattern, filename) is not None

def check_uuid_zip_contents(filepath):
    """Check if UUID zip contains workout/fitness files (FIT, metrics.csv, etc)."""
    try:
        with zipfile.ZipFile(filepath, 'r') as zf:
            files = zf.namelist()
            # Check if contains FIT files or metrics
            fitness_files = [
                '.fit', '.fit.gz',  # FIT workout files
                'metrics.csv',      # Daily metrics
                'workouts.csv',     # Workout summaries
                'tp-', 'zwift-',    # TrainingPeaks or Zwift prefixes
                'garminping'        # Garmin sync files
            ]
            for zip_file in files:
                file_lower = zip_file.lower()
                if any(pattern in file_lower for pattern in fitness_files):
                    return True
            return False
    except:
        return False

def cleanup_old_tp_downloads():
    """Remove old TrainingPeaks and workout files from Downloads folder."""
    downloads = Path.home() / "Downloads"
    
    print("=" * 70)
    print("DOWNLOADS CLEANUP - FITNESS TRACKER FILES")
    print("=" * 70)
    
    # Find TrainingPeaks export files
    tp_patterns = [
        "*Export-*Robinson-Jake*.zip",
        "*Export-*Robinson-Jake*.csv",
        "WorkoutFileExport-*.zip",
        "WorkoutExport-*.zip",
        "MetricsExport-*.zip",
        "WorkoutFileExport-*"  # Directories
    ]
    
    tp_files = []
    for pattern in tp_patterns:
        tp_files.extend(downloads.glob(pattern))
    
    # Remove duplicates
    tp_files = list(set(tp_files))
    
    # Find UUID-named files (likely workout ZIP files)
    all_files = list(downloads.iterdir())
    uuid_files = []
    
    print("\n🔍 Scanning for UUID workout files...")
    for f in all_files:
        if f.is_file() and is_uuid_filename(f.name):
            # Check if it's a workout-related ZIP
            if check_uuid_zip_contents(f):
                uuid_files.append(f)
    
    print(f"   Found {len(uuid_files)} UUID workout ZIP files")
    
    # Combine all files to delete
    all_to_delete = tp_files + uuid_files
    
    if not all_to_delete:
        print("\n✅ No fitness tracker files found in Downloads folder")
        return
    
    print(f"\n📊 Summary:")
    print(f"   TrainingPeaks exports: {len(tp_files)}")
    print(f"   UUID workout ZIPs: {len(uuid_files)}")
    print(f"   Total files: {len(all_to_delete)}")
    
    # Calculate total size
    total_size = 0
    for f in all_to_delete:
        try:
            if f.is_file():
                total_size += f.stat().st_size
            elif f.is_dir():
                total_size += sum(file.stat().st_size for file in f.rglob('*') if file.is_file())
        except:
            pass
    
    total_size_mb = total_size / (1024 * 1024)
    print(f"   Total size: {total_size_mb:.1f} MB")
    
    # Show date range for UUID files
    if uuid_files:
        oldest = min(uuid_files, key=lambda x: x.stat().st_mtime)
        newest = max(uuid_files, key=lambda x: x.stat().st_mtime)
        print(f"\n📅 UUID files date range:")
        print(f"   Oldest: {datetime.fromtimestamp(oldest.stat().st_mtime).strftime('%Y-%m-%d %H:%M')}")
        print(f"   Newest: {datetime.fromtimestamp(newest.stat().st_mtime).strftime('%Y-%m-%d %H:%M')}")
    
    # Show sample files
    print(f"\n📝 Sample files to delete:")
    samples = (tp_files[:3] if tp_files else []) + (uuid_files[:5] if uuid_files else [])
    for f in samples[:8]:
        size_mb = f.stat().st_size / (1024 * 1024) if f.is_file() else 0
        mod_time = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d")
        file_type = "📁 DIR" if f.is_dir() else "📄 ZIP"
        print(f"   {file_type} {f.name[:50]:<50} {size_mb:>6.1f} MB  {mod_time}")
    
    if len(all_to_delete) > 8:
        print(f"   ... and {len(all_to_delete) - 8} more files")
    
    print("\n" + "=" * 70)
    print("⚠️  These files contain FIT workout data that should already be")
    print("   in your database. They are safe to delete.")
    print("=" * 70)
    
    response = input("\n🗑️  Delete all these files? (y/n): ")
    if response.lower() != 'y':
        print("\n❌ Cancelled.")
        return
    
    # Delete files and directories
    print("\n🗑️  Deleting files...")
    deleted = 0
    errors = []
    
    for f in all_to_delete:
        try:
            if f.is_file():
                f.unlink()
                deleted += 1
            elif f.is_dir():
                import shutil
                shutil.rmtree(f)
                deleted += 1
        except Exception as e:
            errors.append(f"{f.name}: {e}")
    
    print(f"\n✅ Deleted {deleted} files/folders ({total_size_mb:.1f} MB freed)")
    
    if errors:
        print(f"\n⚠️  Errors ({len(errors)}):")
        for error in errors[:5]:
            print(f"  • {error}")
        if len(errors) > 5:
            print(f"  ... and {len(errors) - 5} more errors")


if __name__ == "__main__":
    cleanup_old_tp_downloads()
