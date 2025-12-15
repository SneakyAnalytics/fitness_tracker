#!/usr/bin/env python3
"""
Clean up old TrainingPeaks files from ~/Downloads folder.
These files are now stored in the project's data/trainingpeaks_downloads directory.
"""

from pathlib import Path
from datetime import datetime

def cleanup_old_tp_downloads():
    """Remove old TrainingPeaks export files from Downloads folder."""
    downloads = Path.home() / "Downloads"
    
    # Find TrainingPeaks export files
    patterns = [
        "*Export-*Robinson-Jake*.zip",
        "*Export-*Robinson-Jake*.csv",
        "WorkoutFileExport-*.zip",
        "WorkoutExport-*.zip",
        "MetricsExport-*.zip"
    ]
    
    tp_files = []
    for pattern in patterns:
        tp_files.extend(downloads.glob(pattern))
    
    # Remove duplicates
    tp_files = list(set(tp_files))
    
    if not tp_files:
        print("✅ No TrainingPeaks files found in Downloads folder")
        return
    
    print(f"Found {len(tp_files)} TrainingPeaks files in {downloads}")
    print("\nFiles to delete:")
    
    total_size = 0
    for f in sorted(tp_files, key=lambda x: x.stat().st_mtime, reverse=True):
        size_mb = f.stat().st_size / (1024 * 1024)
        total_size += size_mb
        mod_time = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        print(f"  • {f.name} ({size_mb:.1f} MB) - {mod_time}")
    
    print(f"\nTotal size: {total_size:.1f} MB")
    
    response = input("\nDelete these files? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled.")
        return
    
    # Delete files
    deleted = 0
    errors = []
    for f in tp_files:
        try:
            f.unlink()
            deleted += 1
        except Exception as e:
            errors.append(f"{f.name}: {e}")
    
    print(f"\n✅ Deleted {deleted} files ({total_size:.1f} MB)")
    
    if errors:
        print(f"\n⚠️  Errors:")
        for error in errors:
            print(f"  • {error}")


if __name__ == "__main__":
    cleanup_old_tp_downloads()
