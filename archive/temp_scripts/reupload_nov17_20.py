#!/usr/bin/env python3
"""
Re-upload FIT files for Nov 17-20 with updated timezone handling
"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.utils.trainingpeaks_sync import TrainingPeaksSync

def main():
    print("\n" + "="*80)
    print("Re-uploading FIT files for Nov 17-20")
    print("="*80 + "\n")
    
    sync = TrainingPeaksSync()
    
    # Run sync for Nov 17-20
    results = sync.run_sync(
        start_date='11/17/2025',
        end_date='11/20/2025'
    )
    
    print("\n" + "="*80)
    print("SYNC COMPLETE")
    print("="*80)
    print(f"FIT Files: {results.get('fit_files', 0)}")
    print(f"Workouts CSV: {'✅' if results.get('workouts_uploaded') else '❌'}")
    print(f"Metrics CSV: {'✅' if results.get('metrics_uploaded') else '❌'}")
    
    if results.get('errors'):
        print("\nErrors:")
        for error in results['errors']:
            print(f"  - {error}")
    
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
