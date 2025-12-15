# TrainingPeaks Automation Download Configuration

## Changes Made (December 15, 2025)

### Problem

- Browser automation was downloading TrainingPeaks export files to `~/Downloads` folder
- Files were accumulating (7 files, 1 MB) without cleanup
- Browser window was visible during automation (headless=False)

### Solution

#### 1. **Relocated Download Directory**

Changed from:

```python
self.downloads_dir = Path.home() / "Downloads"
```

To:

```python
project_root = Path(__file__).parent.parent.parent
self.downloads_dir = project_root / "data" / "trainingpeaks_downloads"
```

**Benefits:**

- All TrainingPeaks data stays within project structure
- No pollution of user's Downloads folder
- Easier to manage and gitignore
- Consistent with `trainingpeaks_automation_integration.py` approach

#### 2. **Enabled Headless Mode**

Changed from:

```python
browser = p.chromium.launch(headless=False, downloads_path=str(self.downloads_dir))
```

To:

```python
browser = p.chromium.launch(headless=True, downloads_path=str(self.downloads_dir))
```

**Benefits:**

- No visible browser window during automation
- Automation runs in background
- More professional automation experience
- Slightly faster execution

#### 3. **Added Auto-Cleanup**

After successful file processing and database upload, the script now:

1. Identifies all downloaded ZIP files from today
2. Deletes them automatically
3. Logs cleanup results

**Code added to `process_and_upload_files()`:**

```python
# Clean up downloaded ZIP files after successful processing
print("\n🗑️  Cleaning up downloaded files...")
try:
    today_zips = list(self.downloads_dir.glob(f"*Export-{datetime.now().strftime('%Y%m%d')}*.zip"))

    for zip_file in today_zips:
        try:
            if zip_file.exists():
                zip_file.unlink()
                print(f"   ✅ Removed: {zip_file.name}")
        except Exception as e:
            print(f"   ⚠️  Could not remove {zip_file.name}: {e}")

    print("   ✅ Cleanup complete")
except Exception as e:
    print(f"   ⚠️  Cleanup warning: {e}")
```

**Benefits:**

- No manual file cleanup needed
- Prevents directory bloat
- Only removes files after successful database upload
- Errors are logged but don't stop the process

#### 4. **Created Cleanup Script**

Added `scripts/cleanup_old_downloads.py` to remove legacy files from `~/Downloads`:

- Finds all old TrainingPeaks export files
- Shows file list with sizes and dates
- Prompts for confirmation before deletion
- Cleaned up 7 files (1 MB) from initial run

## Directory Structure

```
fitness_tracker/
├── data/
│   ├── trainingpeaks_downloads/    # New: Automated downloads go here
│   │   ├── WorkoutFileExport-*.zip # Deleted after processing
│   │   ├── WorkoutExport-*.zip     # Deleted after processing
│   │   └── MetricsExport-*.zip     # Deleted after processing
│   │
│   └── trainingpeaks_extracted/    # Temporary extraction directory
│       └── [extracted CSVs]        # Cleaned up after upload
│
└── scripts/
    └── cleanup_old_downloads.py    # One-time cleanup of ~/Downloads
```

## Workflow After Changes

1. **Automation runs** (weekly cron or manual)
2. **Browser launches** (headless, no window)
3. **Files download** to `data/trainingpeaks_downloads/`
4. **Files extracted** to `data/trainingpeaks_extracted/`
5. **Data uploaded** to database via FastAPI
6. **ZIP files deleted** from downloads folder
7. **Extracted files cleaned** from temp directory

**Result:** Zero file accumulation, clean automation, no user Downloads pollution

## Testing the Changes

To verify the new behavior:

```bash
# Run the sync manually
python3 -c "from src.utils.trainingpeaks_sync import TrainingPeaksSync; TrainingPeaksSync().run_sync()"

# Check that files were created and cleaned up
ls -lh data/trainingpeaks_downloads/
# Should show 0 ZIP files after successful run

# Verify ~/Downloads is clean
ls ~/Downloads/*Export*.zip 2>/dev/null || echo "✅ No TrainingPeaks files in Downloads"
```

## Configuration

The automation respects these environment variables (from `.env`):

- `TRAININGPEAKS_USERNAME` - Your TrainingPeaks login email
- `TRAININGPEAKS_PASSWORD` - Your TrainingPeaks password

## Rollback (If Needed)

If you need to see the browser window for debugging:

```python
# In src/utils/trainingpeaks_sync.py, line ~460
browser = p.chromium.launch(headless=False, downloads_path=str(self.downloads_dir))
```

To disable auto-cleanup:

```python
# Comment out the cleanup section in process_and_upload_files()
# Lines ~420-440
```

## Future Enhancements

Consider adding:

1. Configurable retention (keep last N days of ZIPs)
2. Backup of ZIPs before deletion (optional)
3. Logging to file for audit trail
4. Cleanup of extraction directory based on age
