# Script Cleanup Log

**Date:** January 14, 2026

## Scripts Deleted (One-off/Completed Tasks)

These scripts were one-time use utilities for specific tasks that have been completed:

1. **`analyze_workout_554.py`** (3.6K, Jan 11)

   - Purpose: One-off analysis of specific workout #554
   - Status: Task completed, no longer needed

2. **`generate_week61_zwo.py`** (1.7K, Jan 13)

   - Purpose: Generate Week 61 Zwift workout files
   - Status: Duplicate of regenerate_week61_workouts.py, Week 61 completed

3. **`regenerate_week61_workouts.py`** (2.5K, Jan 13)

   - Purpose: Regenerate .zwo files for Week 61 from database
   - Status: Week 61 files successfully generated, task completed

4. **`reprocess_fit_files.py`** (1.9K, Jan 1)

   - Purpose: One-off reprocessing of FIT files from Jan 1
   - Status: Reprocessing completed

5. **`reprocess_jan1_fits.py`** (2.5K, Jan 1)

   - Purpose: One-off reprocessing of Jan 1 FIT files (duplicate functionality)
   - Status: Reprocessing completed

6. **`test_ai_matching.py`** (2.7K, Jan 7)

   - Purpose: Test script for AI workout matching on specific date (Jan 6)
   - Status: Testing completed

7. **`test_batch_models.py`** (2.3K, Dec 7)

   - Purpose: Old model testing script
   - Status: Model testing completed, superseded by current implementation

8. **`test_tss_fix.py`** (1.9K, Jan 5)
   - Purpose: One-off test for TSS calculation fix
   - Status: TSS fix validated and integrated

**Total Deleted:** 8 files (~19.5K)

## Scripts Moved to `scripts/utilities/`

These scripts have potential future utility and were moved for better organization:

1. **`analyze_cycling_workouts.py`** (7.7K, Jan 11)

   - Purpose: Bulk analyze cycling workouts with interval detection
   - Use Case: Re-analyze historical workouts if detection algorithm improves

2. **`backfill_workout_analyses.py`** (11K, Jan 5)

   - Purpose: Historical analysis backfill for workouts without AI analysis
   - Use Case: Backfill analyses if database is restored from backup

3. **`cleanup_bad_fit_analyses.py`** (2.0K, Jan 5)

   - Purpose: Cleanup corrupted or failed FIT file analyses
   - Use Case: Fix data quality issues if they arise

4. **`reanalyze_failed_workouts.py`** (7.1K, Jan 4)

   - Purpose: Retry failed workout analyses with updated logic
   - Use Case: Re-run analyses that failed due to API errors

5. **`refresh_gemini_models.py`** (1.0K, Dec 7)
   - Purpose: Refresh available Gemini model list
   - Use Case: Update model configurations when Google releases new models

**Total Moved:** 5 files (~28.8K)

## Scripts Remaining in Root

Essential operational scripts kept in root directory:

- **`sync_to_beelink.sh`** - Production deployment to Beelink server
- **`sync_zwift_from_beelink.sh`** - Sync Zwift workout files from Beelink to Mac
- **`docker-entrypoint.sh`** - Docker container startup script
- **`prepare_for_github.sh`** - Repository preparation for GitHub

## Recovery Information

If you need to recover any deleted script:

```bash
# View deleted file content from git history
git log --all --full-history -- "analyze_workout_554.py"
git show <commit-hash>:analyze_workout_554.py

# Restore deleted file
git checkout <commit-hash> -- analyze_workout_554.py
```

## Root Directory Status

**Before Cleanup:**

- 13 Python scripts in root (one-off utilities)
- 4 Shell scripts (operational)

**After Cleanup:**

- 0 Python scripts in root ✨
- 4 Shell scripts (operational - kept)
- 5 Python utilities organized in `scripts/utilities/`

The root directory is now clean and professional, with only essential operational scripts remaining.
