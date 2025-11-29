#!/usr/bin/env python3
"""
TrainingPeaks Data Sync Script

This script demonstrates how to use the TrainingPeaks automation to:
1. Log into TrainingPeaks
2. Download recent workout and metrics data
3. Save files for import into the fitness tracker

Usage:
    python scripts/sync_trainingpeaks.py [--days 7]
"""

import argparse
import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.trainingpeaks_sync import sync_trainingpeaks_data


async def main():
    """Main sync function."""
    parser = argparse.ArgumentParser(description="Sync data from TrainingPeaks")
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to sync (default: 7)"
    )
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    print(f"Starting TrainingPeaks sync for last {args.days} days...")
    print("-" * 60)
    
    try:
        result = await sync_trainingpeaks_data(days=args.days)
        
        if result["success"]:
            print("\n✅ Sync completed successfully!")
            print(f"Message: {result['message']}")
            if result.get("files"):
                print("\nDownloaded files:")
                for file in result["files"]:
                    print(f"  - {file}")
        else:
            print("\n❌ Sync failed!")
            print(f"Error: {result['message']}")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
