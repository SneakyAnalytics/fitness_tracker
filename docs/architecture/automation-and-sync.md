# Automation & Sync System

**Complete guide to automated TrainingPeaks sync and daily workout analysis**

## Table of Contents

1. [Overview](#overview)
2. [TrainingPeaks Sync](#trainingpeaks-sync)
3. [Daily Automation Workflow](#daily-automation-workflow)
4. [File Processing Pipeline](#file-processing-pipeline)
5. [Scheduled Automation](#scheduled-automation)
6. [Usage Examples](#usage-examples)
7. [Configuration](#configuration)
8. [Troubleshooting](#troubleshooting)

---

## Overview

The automation system provides **hands-free synchronization** from TrainingPeaks to your local database, followed by AI-powered workout analysis. This system eliminates manual data entry and ensures your training data is always up-to-date.

### What It Does

```
TrainingPeaks → Browser Automation → Downloads → Processing → Database → AI Analysis
     |              (Playwright)          |         (Extract)      |      (Gemini)
     |                                    |                       |
  Workout Data              ZIP files + FIT files        Parsed workouts
```

**Key Features:**

1. **Automated Login & Download** - Uses Playwright to navigate TrainingPeaks and download data
2. **Multi-File Handling** - Processes workout files (FIT), summaries (CSV), and metrics (CSV)
3. **Database Integration** - Stores all data via FastAPI endpoints
4. **AI Analysis** - Automatically generates insights for each workout
5. **Personal Best Tracking** - Identifies and records peak efforts
6. **Scheduled Execution** - Runs nightly via cron/scheduled task
7. **Error Recovery** - Handles captchas, timeouts, and partial failures
8. **Clean Isolation** - Uses dedicated directories, no pollution of user Downloads

### Why Browser Automation?

TrainingPeaks doesn't provide a public API for bulk data export. Browser automation solves this by:

- Logging in with your credentials (stored in `.env`)
- Navigating to the Settings → Data Export page
- Filling date ranges and clicking export buttons
- Downloading ZIP files containing FIT/CSV data
- Running in **headless mode** (no visible browser window)

---

## TrainingPeaks Sync

**File:** `src/utils/trainingpeaks_sync.py`

The `TrainingPeaksSync` class orchestrates the entire sync process using Playwright.

### Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                   TrainingPeaksSync                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  1. launch_browser()                                        │
│     ├─ Chromium in headless mode                          │
│     ├─ Custom download path: data/trainingpeaks_downloads  │
│     └─ Anti-detection headers                              │
│                                                              │
│  2. login_and_navigate()                                    │
│     ├─ Navigate to trainingpeaks.com                       │
│     ├─ Accept cookies                                       │
│     ├─ Fill username/password                              │
│     ├─ Submit login form                                    │
│     ├─ Wait for captcha (60s timeout)                     │
│     ├─ Click Calendar button                               │
│     ├─ Open user menu (your name)                          │
│     └─ Click Settings                                       │
│                                                              │
│  3. export_data()                                           │
│     ├─ Fill date ranges (start/end)                        │
│     ├─ Click 3 export buttons:                             │
│     │  ├─ Workout Files (FIT files)                        │
│     │  ├─ Workout Summary (CSV)                            │
│     │  └─ Custom Metrics (CSV)                             │
│     └─ Download all ZIP files                              │
│                                                              │
│  4. process_and_upload_files()                              │
│     ├─ Extract ZIP files                                    │
│     ├─ Decompress .fit.gz → .fit                          │
│     ├─ Parse CSVs                                           │
│     └─ Upload to database via API                          │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Usage

**Basic sync (current week):**

```python
from src.utils.trainingpeaks_sync import TrainingPeaksSync

# Sync current week (Monday to Sunday)
sync = TrainingPeaksSync()
results = sync.run_sync()

print(f"FIT files uploaded: {results['fit_files']}")
print(f"Workouts CSV: {'✅' if results['workouts'] else '❌'}")
print(f"Metrics CSV: {'✅' if results['metrics'] else '❌'}")
```

**Custom date range:**

```python
from datetime import date

# Sync specific dates
start = date(2025, 1, 1)
end = date(2025, 1, 7)

results = sync.run_sync(start_date=start, end_date=end)
```

**Keep FIT files for additional processing:**

```python
# Don't cleanup FIT files after upload (for AI analysis)
results = sync.run_sync(cleanup_fit_files=False)
```

### Login & Navigation Flow

The most complex part is navigating TrainingPeaks' UI, especially handling dynamic user menus:

```python
def login_and_navigate(self, page: Page):
    """Handle login and navigation to export page"""

    # 1. Navigate to homepage
    page.goto("https://www.trainingpeaks.com")

    # 2. Accept cookie consent
    try:
        page.click("button#onetrust-accept-btn-handler", timeout=3000)
    except:
        pass  # Might not appear

    # 3. Click login link
    page.click("a[href*='login']")

    # 4. Fill credentials
    page.wait_for_selector("input[name='Username']")
    page.fill("input[name='Username']", self.username)
    page.fill("input[name='Password']", self.password)
    page.click("button[type='submit']")

    # 5. Wait for captcha (user intervention if needed)
    print("⏸️  Waiting for login to complete (solve captcha if it appears)...")
    try:
        page.wait_for_selector("button:has-text('Calendar')", timeout=60000)
        print("✅ Login successful!")
    except:
        print("❌ Login timeout - captcha may need to be solved manually")
        time.sleep(30)  # Extra wait

    # 6. Navigate to calendar
    page.click("button:has-text('Calendar')", timeout=10000)
    time.sleep(1)

    # 7. Open user menu (this is tricky - try multiple methods)
    user_menu_clicked = False

    # Method 1: Direct text match
    try:
        page.click("text=Jake Robinson", timeout=3000)
        user_menu_clicked = True
    except:
        pass

    # Method 2: CSS selectors
    if not user_menu_clicked:
        selectors = [
            "button[class*='userMenu']",
            "div[class*='userMenu'] button",
            "p.MuiTypography-root:has-text('Jake Robinson')",
        ]
        for selector in selectors:
            try:
                page.click(selector, timeout=2000)
                user_menu_clicked = True
                break
            except:
                continue

    # Method 3: JavaScript fallback
    if not user_menu_clicked:
        clicked = page.evaluate("""
            () => {
                const elements = document.querySelectorAll('p, button, span');
                for (let el of elements) {
                    if (el.textContent.includes('Jake Robinson')) {
                        el.click();
                        return true;
                    }
                }
                return false;
            }
        """)
        if clicked:
            user_menu_clicked = True

    # 8. Click Settings from dropdown
    page.click("label.userSettingsOption:has-text('Settings')", timeout=10000)

    # 9. Wait for export page
    page.wait_for_selector("input.datepicker.startDate", timeout=10000)
    print("✅ Export page loaded")
```

**Key Challenges:**

- **Captcha Handling:** Cannot be automated - must wait 60s for user to solve manually
- **Dynamic User Menu:** Different accounts may have different names - tries multiple methods
- **JavaScript-Heavy UI:** Uses `.evaluate()` to execute JS when selectors fail
- **Timing Issues:** Careful use of `time.sleep()` and `wait_for_selector()` for stability

### Export Data Flow

Once on the settings page, exporting data is simpler:

```python
def export_data(self, page: Page, start_date: str, end_date: str):
    """Fill dates and trigger exports"""

    # 1. Fill all date fields using JavaScript
    page.evaluate(f"""
        const startInputs = document.querySelectorAll('input.datepicker.startDate');
        const endInputs = document.querySelectorAll('input.datepicker.endDate');

        startInputs.forEach(input => {{
            input.value = '{start_date}';
            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }});

        endInputs.forEach(input => {{
            input.value = '{end_date}';
            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
        }});
    """)

    # 2. Click export buttons (3 sections)
    page.evaluate("document.querySelectorAll('button.download.tpSecondaryButton')[0].click()")
    time.sleep(2)

    page.evaluate("document.querySelectorAll('button.download.tpSecondaryButton')[1].click()")
    time.sleep(2)

    page.evaluate("document.querySelectorAll('button.download.tpSecondaryButton')[2].click()")
    time.sleep(3)

    # 3. Download all available files
    downloads = []
    max_attempts = 3

    for attempt in range(max_attempts):
        try:
            # Check for download links
            num_links = page.evaluate("document.querySelectorAll('a#userConfirm').length")
            if num_links == 0:
                break

            # Click first link (array updates after each download)
            with page.expect_download(timeout=60000) as download_info:
                page.evaluate("document.querySelectorAll('a#userConfirm')[0].click()")

            download = download_info.value
            downloads.append(download)
            print(f"   📥 Download {attempt+1} started: {download.suggested_filename}")

            time.sleep(0.5)

        except Exception as e:
            print(f"   ⚠️ Download {attempt+1} failed: {e}")

    # 4. Save downloads with proper filenames
    saved_files = []
    for download in downloads:
        suggested_name = download.suggested_filename
        save_path = self.downloads_dir / suggested_name
        download.save_as(save_path)
        saved_files.append(save_path)
        print(f"   ✅ Saved: {suggested_name}")

    print(f"✅ Downloaded and saved {len(saved_files)} files!")
```

**Expected Downloads:**

1. **WorkoutFileExport-YYYYMMDD-YYYYMMDD.zip** - Contains `.fit.gz` files (raw workout data)
2. **WorkoutExport-YYYYMMDD-YYYYMMDD.zip** - Contains `Workouts.csv` (summary data)
3. **MetricsExport-YYYYMMDD-YYYYMMDD.zip** - Contains `CustomMetrics.csv` (metrics data)

### Browser Configuration

The sync uses **headless Chromium** with specific settings to avoid detection:

```python
browser = p.chromium.launch(
    headless=True,  # No visible window
    downloads_path=str(self.downloads_dir),  # Save to project dir
    args=['--disable-blink-features=AutomationControlled']  # Avoid detection
)

context = browser.new_context(
    accept_downloads=True,
    viewport={'width': 1920, 'height': 1080},  # Full HD viewport
    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
)
```

**Why These Settings?**

- `headless=True`: Runs in background without window (professional automation)
- `downloads_path`: Isolates downloads to project directory (no pollution of ~/Downloads)
- `--disable-blink-features=AutomationControlled`: Removes `navigator.webdriver` flag
- Custom `user_agent`: Mimics real Chrome browser

### File Processing & Upload

After downloads complete, files are processed and uploaded:

```python
def process_and_upload_files(self, cleanup_fit_files: bool = True):
    """Process downloaded files and upload to database"""

    processor = TrainingPeaksFileProcessor(self.downloads_dir, self.extract_dir)

    # 1. Find latest export files
    workout_files_path, workout_summary_path, metrics_path = processor.find_latest_exports()

    results = {
        'fit_files': 0,
        'workouts': False,
        'metrics': False,
        'errors': []
    }

    # 2. Process Workout Files (FIT files)
    if workout_files_path:
        fit_files = processor.process_workout_files_export(workout_files_path)

        # Upload each FIT file via API
        for fit_file in fit_files:
            success, message = self.upload_fit_file(fit_file)
            if success:
                results['fit_files'] += 1
            else:
                results['errors'].append(f"FIT upload failed: {message}")

    # 3. Process Workout Summary CSV
    if workout_summary_path:
        csv_file = processor.process_workout_summary_export(workout_summary_path)
        success, message = self.upload_workouts_csv(csv_file)
        results['workouts'] = success
        if not success:
            results['errors'].append(f"Workouts CSV failed: {message}")

    # 4. Process Metrics CSV
    if metrics_path:
        csv_file = processor.process_metrics_export(metrics_path)
        success, message = self.upload_metrics_csv(csv_file)
        results['metrics'] = success
        if not success:
            results['errors'].append(f"Metrics CSV failed: {message}")

    return results
```

**API Upload Methods:**

```python
def upload_fit_file(self, fit_file_path: Path) -> tuple[bool, str]:
    """Upload FIT file to API"""
    url = f"{self.api_base}/fit-files/upload"

    with open(fit_file_path, 'rb') as f:
        files = {'file': (fit_file_path.name, f, 'application/octet-stream')}
        response = requests.post(url, files=files, timeout=60)

    if response.status_code == 200:
        return True, "Success"
    else:
        return False, response.text

def upload_workouts_csv(self, csv_path: Path) -> tuple[bool, str]:
    """Upload workouts CSV to API"""
    url = f"{self.api_base}/trainingpeaks/import-workouts-csv"

    with open(csv_path, 'rb') as f:
        files = {'file': (csv_path.name, f, 'text/csv')}
        response = requests.post(url, files=files, timeout=60)

    if response.status_code == 200:
        return True, "Success"
    else:
        return False, response.text
```

---

## Daily Automation Workflow

**File:** `src/utils/daily_auto_sync_and_analyze.py`

The `DailyAutoSyncAndAnalyze` class orchestrates the complete end-to-end automation: sync → analyze → cleanup.

### Complete Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                  Daily Automation Workflow                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  STEP 1: TrainingPeaks Sync                                     │
│  ├─ Run TrainingPeaksSync for today's date                      │
│  ├─ Download: Workout files + Summary CSV + Metrics CSV         │
│  ├─ Upload to database via API                                  │
│  └─ Keep FIT files for analysis (cleanup_fit_files=False)       │
│                                                                  │
│  STEP 2: Find Today's FIT Files                                 │
│  ├─ Scan: data/trainingpeaks_extracted/                         │
│  ├─ Match by filename date (YYYY-MM-DD prefix)                  │
│  ├─ Fallback to modification date                               │
│  └─ Return list of Path objects                                 │
│                                                                  │
│  STEP 3: AI Analysis (with rate limiting)                       │
│  ├─ For each FIT file:                                          │
│  │  ├─ Load athlete FTP from database                           │
│  │  ├─ Read FIT file content (binary)                           │
│  │  ├─ Create FitFileAnalyzer(use_dynamic_models=True)          │
│  │  ├─ Run analysis (Gemini free models)                        │
│  │  ├─ Store analysis in database                               │
│  │  ├─ Store personal bests                                     │
│  │  └─ Sleep 6 seconds (rate limiting)                          │
│  └─ Track: workouts_analyzed, personal_bests count              │
│                                                                  │
│  STEP 4: Cleanup                                                │
│  ├─ Remove FIT files from extraction dir                        │
│  ├─ Remove ZIP files from downloads dir                         │
│  ├─ Remove empty directories                                    │
│  └─ Keep only permanent database records                        │
│                                                                  │
│  RESULT: Complete automation with full insights                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Usage

**Run daily automation for today:**

```python
from src.utils.daily_auto_sync_and_analyze import DailyAutoSyncAndAnalyze

automation = DailyAutoSyncAndAnalyze()
results = automation.run_daily_automation()

print(f"Workouts analyzed: {results['workouts_analyzed']}")
print(f"New PBs: {results['personal_bests']}")
```

**Run for specific date:**

```python
from datetime import date

# Process January 10, 2025
results = automation.run_daily_automation(target_date=date(2025, 1, 10))
```

**Custom FTP (override athlete settings):**

```python
# Force specific FTP for analysis
results = automation.run_daily_automation(ftp_watts=285)
```

**Skip cleanup (for debugging):**

```python
# Keep temporary files for inspection
results = automation.run_daily_automation(cleanup=False)
```

### Analyze from Database (Alternative Path)

If FIT files aren't available on disk, analysis can run directly from database:

```python
def analyze_workouts_from_database(
    self,
    target_date: date,
    ftp_watts: Optional[int] = None,
    results: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Analyze workouts directly from database without needing FIT files on disk.

    This is a fallback path when:
    - Sync results don't include FIT file paths
    - FIT files were already cleaned up
    - Re-analyzing previously uploaded workouts
    """

    # Query workouts without analysis
    conn = sqlite3.connect(self.db.db_path)
    c = conn.cursor()

    c.execute("""
        SELECT w.id, w.workout_day, w.workout_title, w.workout_data
        FROM workouts w
        LEFT JOIN workout_analyses wa ON w.id = wa.workout_id
        WHERE w.workout_day = ? AND wa.id IS NULL
        ORDER BY w.id
    """, (str(target_date),))

    workouts_to_analyze = c.fetchall()
    conn.close()

    # Analyze each workout using stored workout_data
    for workout_id, workout_day, workout_title, workout_data_json in workouts_to_analyze:
        workout_data = json.loads(workout_data_json)

        analyzer = FitFileAnalyzer(use_dynamic_models=True)

        # Use parsed data instead of raw file
        analysis = analyzer.analyze_workout_from_parsed_data(
            parsed_data=workout_data,
            athlete_ftp=float(ftp_watts)
        )

        if analysis:
            pb_count = self.db.store_workout_analysis(
                workout_id=workout_id,
                analysis_text=analysis.get('analysis_text', ''),
                analysis_data=json.dumps(analysis.get('analysis_data', {}))
            )

            results['workouts_analyzed'] += 1
            results['personal_bests'] += pb_count

        # Rate limiting
        time.sleep(self.api_delay)

    return results
```

**When This Is Used:**

- Sync results don't include `fit_file_paths` key
- FIT files were deleted after initial sync
- Re-running analysis on historical data
- Database already has parsed `workout_data` JSON

### Rate Limiting

To avoid hitting Gemini API rate limits, automation includes delays:

```python
# Rate limiting configuration
self.api_delay = 6  # seconds between analyses

# Applied between workouts
for i, fit_file in enumerate(fit_files):
    # Analyze workout
    analysis = self.analyze_workout(fit_file, ftp_watts)

    # Rate limit (except for last file)
    if i < len(fit_files) - 1:
        logger.info(f"   ⏸️  Rate limiting: {self.api_delay}s...")
        time.sleep(self.api_delay)
```

**Why 6 Seconds?**

- Gemini free tier: 15 RPM (requests per minute)
- 60 seconds ÷ 15 requests = 4 seconds minimum
- 6 seconds provides safety margin and reduces API stress

### Finding Today's FIT Files

After sync, FIT files must be located for analysis:

```python
def find_todays_fit_files(self, target_date: date = None) -> list[Path]:
    """
    Find FIT files from today's TrainingPeaks download.

    Uses two methods to match files:
    1. Filename parsing (YYYY-MM-DD prefix)
    2. File modification date
    """
    if target_date is None:
        target_date = date.today()

    fit_files = []

    # Scan extraction directory
    if self.tp_extract_dir.exists():
        for fit_file in self.tp_extract_dir.rglob('*.[Ff][Ii][Tt]'):

            # Method 1: Parse filename for date
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

            # Method 2: Check modification date
            mod_time = datetime.fromtimestamp(fit_file.stat().st_mtime).date()
            if mod_time == target_date:
                fit_files.append(fit_file)
                logger.info(f"   Found: {fit_file.name} (by mod date)")

    logger.info(f"Found {len(fit_files)} FIT file(s) for {target_date}")
    return fit_files
```

**Filename Format Examples:**

- `2025-01-14-Evening_Ride.fit` ✅ Matches by filename
- `Evening_Ride.fit` ✅ Matches by modification date
- `2025-01-14-123456.FIT` ✅ Case-insensitive

### Storing Analysis Results

After AI analysis, results are stored with personal bests:

```python
def store_analysis(
    self,
    analysis: Dict[str, Any],
    workout_id: Optional[int] = None,
    fit_file_id: Optional[int] = None
) -> int:
    """
    Store analysis results and personal bests in database.

    Returns count of personal bests stored.
    """

    # Lookup IDs if not provided
    if not fit_file_id and 'file_name' in analysis:
        # Strip date prefix (YYYY-MM-DD-filename.fit → filename.fit)
        file_name = analysis['file_name']
        if file_name.count('-') >= 2:
            parts = file_name.split('-', 3)
            if len(parts[0]) == 4 and parts[0].isdigit():
                file_name = parts[3]

        fit_file_id = self.db.get_fit_file_id_by_name(file_name)

    # Lookup workout_id from fit_file_id
    if not workout_id and fit_file_id:
        conn = sqlite3.connect(self.db.db_path)
        c = conn.cursor()
        c.execute('SELECT id FROM workouts WHERE fit_file_id = ?', (fit_file_id,))
        result = c.fetchone()
        if result:
            workout_id = result[0]
        conn.close()

    # Store analysis
    analysis_id = self.db.store_workout_analysis(
        workout_id=workout_id,
        fit_file_id=fit_file_id,
        analysis_text=analysis.get('ai_analysis', ''),
        analysis_data=analysis,  # Full object for visualization
        peak_efforts=analysis.get('peak_efforts'),
        model_used='gemini-2.0-flash-exp'
    )

    # Store personal bests
    peak_efforts = analysis.get('peak_efforts', {})
    workout_date = analysis.get('workout_date', datetime.now().date().isoformat())
    pb_count = 0

    for effort_type, effort_data in peak_efforts.items():
        if isinstance(effort_data, dict) and 'power' in effort_data:
            pb_id = self.db.store_personal_best(
                effort_type=effort_type,
                effort_value=effort_data['power'],
                achieved_date=workout_date,
                workout_id=workout_id
            )
            if pb_id:
                pb_count += 1
                logger.info(f"   🏅 Stored PB: {effort_type} = {effort_data['power']:.1f}W")

    return pb_count
```

**Database Storage:**

- `workout_analyses` table: Full analysis text + data JSON
- `personal_bests` table: Peak efforts (5s, 1min, 5min, 20min, etc.)
- Links: `workout_id` and `fit_file_id` for relational queries

### Cleanup Process

After analysis, temporary files are removed:

```python
def cleanup_temp_files(self, target_date: date = None):
    """Clean up temporary TrainingPeaks files after processing"""

    if target_date is None:
        target_date = date.today()

    logger.info("🧹 Cleaning up temporary files...")

    # 1. Clean extracted FIT files
    if self.tp_extract_dir.exists():
        for fit_file in self.tp_extract_dir.rglob('*.[Ff][Ii][Tt]'):
            mod_time = datetime.fromtimestamp(fit_file.stat().st_mtime).date()
            if mod_time == target_date:
                fit_file.unlink()
                logger.info(f"   🗑️  Removed: {fit_file.name}")

        # Remove empty directories
        for dir_path in self.tp_extract_dir.rglob('*'):
            if dir_path.is_dir() and not any(dir_path.iterdir()):
                dir_path.rmdir()

    # 2. Clean downloaded ZIP files
    for pattern in ['WorkoutFileExport-*.zip', 'WorkoutExport-*.zip', 'MetricsExport-*.zip']:
        for zip_file in self.downloads_dir.glob(pattern):
            mod_time = datetime.fromtimestamp(zip_file.stat().st_mtime).date()
            if mod_time == target_date:
                zip_file.unlink()
                logger.info(f"   🗑️  Removed: {zip_file.name}")

    logger.info("✅ Cleanup complete")
```

**What Gets Cleaned:**

- FIT files in `data/trainingpeaks_extracted/`
- ZIP files in `data/trainingpeaks_downloads/`
- Empty directories from extraction

**What Stays:**

- Database records in `fitness_data.db`
- Permanently stored workout data
- Analysis results and personal bests

### Command-Line Interface

The module can be run directly for automation:

```python
if __name__ == "__main__":
    import sys

    # Parse command-line date
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

    # Exit with error code if no workouts analyzed
    if results['workouts_analyzed'] == 0:
        sys.exit(1)
    else:
        sys.exit(0)
```

**Usage:**

```bash
# Run for today
python -m src.utils.daily_auto_sync_and_analyze

# Run for specific date
python -m src.utils.daily_auto_sync_and_analyze 2025-01-10

# Exit code 0 if successful, 1 if failed (for cron monitoring)
```

---

## File Processing Pipeline

**File:** `src/utils/trainingpeaks_file_processor.py`

The `TrainingPeaksFileProcessor` class handles extraction and organization of downloaded files.

### Architecture

```
┌────────────────────────────────────────────────────────────┐
│            TrainingPeaksFileProcessor                       │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  Input: 3 ZIP files from TrainingPeaks                     │
│  ├─ WorkoutFileExport-*.zip                                │
│  ├─ WorkoutExport-*.zip                                    │
│  └─ MetricsExport-*.zip                                    │
│                                                             │
│  Processing Steps:                                          │
│  1. extract_zip() - Unzip to temp directory                │
│  2. decompress_fit_gz() - Gunzip .fit.gz → .fit            │
│  3. Find CSV files in extracted folders                    │
│  4. Return organized paths                                  │
│                                                             │
│  Output:                                                    │
│  ├─ List of .fit file paths                                │
│  ├─ Path to Workouts.csv                                   │
│  └─ Path to CustomMetrics.csv                              │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

### Key Methods

**Extract ZIP files:**

```python
def extract_zip(self, zip_path: Path) -> Path:
    """
    Extract a ZIP file to extraction directory.

    Returns path to extracted folder.
    """
    extract_path = self.extract_dir / zip_path.stem
    extract_path.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)

    return extract_path
```

**Decompress FIT files:**

```python
def decompress_fit_gz(self, fit_gz_path: Path) -> Path:
    """
    Decompress a .fit.gz file to .fit format.

    Args:
        fit_gz_path: Path to compressed file

    Returns:
        Path to decompressed .fit file
    """
    fit_path = fit_gz_path.with_suffix('')  # Remove .gz extension

    with gzip.open(fit_gz_path, 'rb') as f_in:
        with open(fit_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)

    return fit_path
```

**Process Workout Files Export:**

```python
def process_workout_files_export(self, zip_path: Path) -> List[Path]:
    """
    Process WorkoutFileExport ZIP containing .fit.gz files.

    Steps:
    1. Extract ZIP
    2. Find all .fit.gz and .FIT.gz files (case-insensitive)
    3. Decompress each to .fit
    4. Return list of .fit file paths
    """
    extract_path = self.extract_zip(zip_path)

    # Find compressed files
    fit_gz_files = list(extract_path.rglob('*.fit.gz'))
    fit_gz_files.extend(list(extract_path.rglob('*.FIT.gz')))

    fit_files = []
    for fit_gz in fit_gz_files:
        fit_file = self.decompress_fit_gz(fit_gz)
        fit_files.append(fit_file)

    # Also find plain .fit files (if any)
    plain_fit_files = list(extract_path.rglob('*.fit'))
    plain_fit_files.extend(list(extract_path.rglob('*.FIT')))

    # Avoid duplicates
    plain_fit_files = [f for f in plain_fit_files
                       if not any(str(f).endswith(str(gz.with_suffix('')))
                       for gz in fit_gz_files)]

    fit_files.extend(plain_fit_files)

    return fit_files
```

**Process CSV Exports:**

```python
def process_workout_summary_export(self, zip_path: Path) -> Path:
    """
    Process WorkoutExport ZIP containing workout summary CSV.

    Returns path to extracted CSV file.
    """
    extract_path = self.extract_zip(zip_path)

    csv_files = list(extract_path.glob('*.csv'))
    if not csv_files:
        raise FileNotFoundError(f"No CSV found in {zip_path}")

    return csv_files[0]

def process_metrics_export(self, zip_path: Path) -> Path:
    """
    Process MetricsExport ZIP containing custom metrics CSV.

    Returns path to extracted CSV file.
    """
    extract_path = self.extract_zip(zip_path)

    csv_files = list(extract_path.glob('*.csv'))
    if not csv_files:
        raise FileNotFoundError(f"No CSV found in {zip_path}")

    return csv_files[0]
```

### Complete Processing Example

```python
from src.utils.trainingpeaks_file_processor import TrainingPeaksFileProcessor
from pathlib import Path

# Initialize processor
download_dir = Path("data/trainingpeaks_downloads")
extract_dir = Path("data/trainingpeaks_extracted")
processor = TrainingPeaksFileProcessor(download_dir, extract_dir)

# Find latest export files
workout_files_zip = download_dir / "WorkoutFileExport-20250101-20250107.zip"
workout_summary_zip = download_dir / "WorkoutExport-20250101-20250107.zip"
metrics_zip = download_dir / "MetricsExport-20250101-20250107.zip"

# Process workout files
fit_files = processor.process_workout_files_export(workout_files_zip)
print(f"Found {len(fit_files)} FIT files:")
for fit_file in fit_files:
    print(f"  - {fit_file.name}")

# Process CSVs
workouts_csv = processor.process_workout_summary_export(workout_summary_zip)
print(f"Workouts CSV: {workouts_csv}")

metrics_csv = processor.process_metrics_export(metrics_zip)
print(f"Metrics CSV: {metrics_csv}")
```

---

## Scheduled Automation

The automation system is designed to run automatically via **cron** (Linux/Mac) or **Task Scheduler** (Windows).

### Cron Setup (Linux/Mac)

**Create wrapper script:**

```bash
# File: bin/run_daily_automation.sh
#!/bin/bash

# Change to project directory
cd /Users/jacobrobinson/fitness_tracker

# Activate virtual environment
source venv/bin/activate

# Run automation with logging
python -m src.utils.daily_auto_sync_and_analyze >> logs/daily_automation.out 2>> logs/daily_automation.err

# Exit with command's exit code
exit $?
```

**Make executable:**

```bash
chmod +x bin/run_daily_automation.sh
```

**Add to crontab:**

```bash
# Edit crontab
crontab -e

# Add this line (runs every night at 10:00 PM)
0 22 * * * /Users/jacobrobinson/fitness_tracker/bin/run_daily_automation.sh
```

**Cron Schedule Examples:**

```bash
# Every night at 10:00 PM
0 22 * * * /path/to/run_daily_automation.sh

# Every day at 6:00 AM
0 6 * * * /path/to/run_daily_automation.sh

# Every 6 hours
0 */6 * * * /path/to/run_daily_automation.sh

# Monday through Friday at 11:00 PM
0 23 * * 1-5 /path/to/run_daily_automation.sh
```

### Task Scheduler (Windows)

**Create PowerShell script:**

```powershell
# File: bin\run_daily_automation.ps1

# Change to project directory
Set-Location "C:\Users\YourName\fitness_tracker"

# Activate virtual environment
.\venv\Scripts\Activate.ps1

# Run automation with logging
python -m src.utils.daily_auto_sync_and_analyze *>> logs\daily_automation.log
```

**Create Task Scheduler job:**

1. Open Task Scheduler
2. Create Basic Task
3. Name: "Fitness Tracker Daily Sync"
4. Trigger: Daily at 10:00 PM
5. Action: Start a program
   - Program: `powershell.exe`
   - Arguments: `-ExecutionPolicy Bypass -File "C:\Users\YourName\fitness_tracker\bin\run_daily_automation.ps1"`
6. Conditions:
   - ✅ Run only if network is available
   - ❌ Wake computer to run (optional)
7. Settings:
   - ✅ Run task as soon as possible after scheduled start is missed
   - ✅ Stop task if it runs longer than 1 hour

### Docker Automation

For containerized deployments, **Playwright and Chromium must be installed in the Docker image**.

#### Docker Setup for Playwright

**Dockerfile requirements:**

```dockerfile
# Install system dependencies including Playwright requirements
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libsqlite3-dev \
    curl \
    # Playwright/Chromium dependencies
    wget \
    gnupg \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (Chromium only for TrainingPeaks sync)
RUN playwright install chromium
RUN playwright install-deps chromium
```

**Important:** Without these steps, TrainingPeaks sync will fail with "Executable doesn't exist" errors.

#### Rebuild Containers After Adding Playwright

If you already have containers running without Playwright:

```bash
# Stop containers
docker-compose down

# Rebuild with new Dockerfile (no cache to ensure fresh install)
docker-compose build --no-cache

# Start containers
docker-compose up -d

# Verify Playwright is installed
docker exec fitness-tracker-ui python -c "from playwright.sync_api import sync_playwright; print('✅ Playwright installed')"
```

**Quick fix script** (deploy_playwright_fix.sh):

```bash
#!/bin/bash
# Automated fix for Playwright in Docker

docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Verify
docker exec fitness-tracker-ui playwright --version
```

#### Docker Compose with Scheduled Automation

**docker-compose.yml with cron:**

```yaml
version: "3.8"

services:
  app:
    build: .
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    environment:
      - TRAININGPEAKS_USERNAME=${TRAININGPEAKS_USERNAME}
      - TRAININGPEAKS_PASSWORD=${TRAININGPEAKS_PASSWORD}
    # Install cron and schedule daily automation
    command: |
      bash -c "
        apt-get update && apt-get install -y cron
        echo '0 22 * * * cd /app && python -m src.utils.daily_auto_sync_and_analyze >> logs/daily_automation.out 2>> logs/daily_automation.err' | crontab -
        cron -f
      "
```

**Note:** Most production deployments run cron on the host machine rather than in containers, pointing to `docker exec` commands.

### Monitoring Logs

**View recent automation runs:**

```bash
# Last 50 lines of output
tail -50 logs/daily_automation.out

# Last 50 lines of errors
tail -50 logs/daily_automation.err

# Follow in real-time
tail -f logs/daily_automation.out

# Search for failures
grep -i "error\|failed" logs/daily_automation.err
```

**Log Output Example:**

```
============================================================
🚀 DAILY AUTOMATION - 2025-01-14
============================================================

STEP 1: TrainingPeaks Sync
------------------------------------------------------------
🔄 TrainingPeaks Sync - 2025-01-14
============================================================
🌐 Navigating to TrainingPeaks...
🔐 Logging in...
⏸️  Waiting for login to complete (solve captcha if it appears)...
✅ Login successful!
⚙️  Navigating to Settings...
✅ Export page loaded
📅 Setting date range: 01/14/2025 to 01/14/2025
📥 Triggering exports...
   📥 Download 1 started: WorkoutFileExport-20250114-20250114.zip
   📥 Download 2 started: WorkoutExport-20250114-20250114.zip
   📥 Download 3 started: MetricsExport-20250114-20250114.zip
   ✅ Saved: WorkoutFileExport-20250114-20250114.zip
   ✅ Saved: WorkoutExport-20250114-20250114.zip
   ✅ Saved: MetricsExport-20250114-20250114.zip
✅ Downloaded and saved 3 files!

STEP 2: Get FIT Files from Sync
------------------------------------------------------------
Found 2 FIT file(s) to analyze

STEP 3: AI Analysis
------------------------------------------------------------
[1/2] 2025-01-14-Morning_Ride.fit
🤖 Analyzing: 2025-01-14-Morning_Ride.fit
   ✅ Analysis complete
   💾 Stored analysis ID: 1234
   🏅 Stored PB: 5s = 450.2W
   🏅 Stored PB: 1min = 380.5W
   💪 Total personal bests tracked: 2
   ⏸️  Rate limiting: 6s...

[2/2] 2025-01-14-Evening_Ride.fit
🤖 Analyzing: 2025-01-14-Evening_Ride.fit
   ✅ Analysis complete
   💾 Stored analysis ID: 1235
   🏅 Stored PB: 20min = 290.3W
   💪 Total personal bests tracked: 1

STEP 4: Cleanup
------------------------------------------------------------
🧹 Cleaning up temporary files...
   🗑️  Removed: 2025-01-14-Morning_Ride.fit
   🗑️  Removed: 2025-01-14-Evening_Ride.fit
   🗑️  Removed: WorkoutFileExport-20250114-20250114.zip
   🗑️  Removed: WorkoutExport-20250114-20250114.zip
   🗑️  Removed: MetricsExport-20250114-20250114.zip
✅ Cleanup complete

============================================================
✅ DAILY AUTOMATION COMPLETE
============================================================
Date: 2025-01-14
FIT Files Downloaded: 2
Workouts Analyzed: 2
New Personal Bests: 3
============================================================
```

---

## Usage Examples

### Example 1: Manual Sync for Current Week

```python
from src.utils.trainingpeaks_sync import TrainingPeaksSync

# Sync entire current week
sync = TrainingPeaksSync()
results = sync.run_sync()

if results:
    print(f"✅ Sync complete")
    print(f"   FIT files: {results['fit_files']}")
    print(f"   Workouts CSV: {'✅' if results['workouts'] else '❌'}")
    print(f"   Metrics CSV: {'✅' if results['metrics'] else '❌'}")

    if results['errors']:
        print(f"   Errors encountered: {len(results['errors'])}")
        for error in results['errors']:
            print(f"     - {error}")
else:
    print("❌ Sync failed")
```

### Example 2: Daily Automation with Custom FTP

```python
from src.utils.daily_auto_sync_and_analyze import DailyAutoSyncAndAnalyze
from datetime import date

# Run automation with specific FTP
automation = DailyAutoSyncAndAnalyze()
results = automation.run_daily_automation(
    target_date=date.today(),
    ftp_watts=290,  # Override athlete settings
    cleanup=True
)

# Check results
if results['workouts_analyzed'] > 0:
    print(f"✅ Analyzed {results['workouts_analyzed']} workout(s)")
    print(f"   New PBs: {results['personal_bests']}")
else:
    print(f"❌ No workouts analyzed")
    print(f"   Errors: {results['errors']}")
```

### Example 3: Backfill Historical Data

```python
from datetime import date, timedelta
from src.utils.trainingpeaks_sync import TrainingPeaksSync

# Sync last 30 days
sync = TrainingPeaksSync()
end_date = date.today()
start_date = end_date - timedelta(days=30)

print(f"Syncing {start_date} to {end_date}...")
results = sync.run_sync(start_date=start_date, end_date=end_date)

if results:
    print(f"✅ Historical sync complete")
    print(f"   Downloaded {results['fit_files']} FIT files")
```

### Example 4: Re-analyze Without Re-downloading

```python
from src.utils.daily_auto_sync_and_analyze import DailyAutoSyncAndAnalyze
from datetime import date

# Analyze workouts already in database (no sync)
automation = DailyAutoSyncAndAnalyze()

# This will analyze workouts without analysis from database
results = automation.analyze_workouts_from_database(
    target_date=date(2025, 1, 10),
    ftp_watts=285
)

print(f"Analyzed {results['workouts_analyzed']} workouts from database")
```

### Example 5: Sync Without Cleanup (for Debugging)

```python
from src.utils.trainingpeaks_sync import TrainingPeaksSync

# Keep all downloaded/extracted files
sync = TrainingPeaksSync()
results = sync.run_sync(cleanup_fit_files=False)

# Files remain in:
# - data/trainingpeaks_downloads/ (ZIP files)
# - data/trainingpeaks_extracted/ (FIT files)
print("Files kept for inspection")
```

### Example 6: Process Specific Downloaded Files

```python
from pathlib import Path
from src.utils.trainingpeaks_file_processor import TrainingPeaksFileProcessor

# Process specific ZIP files
download_dir = Path("data/trainingpeaks_downloads")
extract_dir = Path("data/trainingpeaks_extracted")

processor = TrainingPeaksFileProcessor(download_dir, extract_dir)

# Process workout files
workout_zip = download_dir / "WorkoutFileExport-20250110-20250110.zip"
fit_files = processor.process_workout_files_export(workout_zip)

print(f"Extracted {len(fit_files)} FIT files:")
for fit_file in fit_files:
    print(f"  - {fit_file}")
```

---

## Configuration

### Environment Variables

**Required in `.env` file:**

```bash
# TrainingPeaks Credentials
TRAININGPEAKS_USERNAME=your_email@example.com
TRAININGPEAKS_PASSWORD=your_password

# API URL (for uploads)
API_URL=http://localhost:8000  # Local development
# API_URL=http://100.117.194.8:8000  # Production (Beelink)

# Athlete Settings (optional overrides)
ATHLETE_FTP=285  # Override FTP for analysis
ATHLETE_HR_ZONES=0,60,70,80,90,100  # Custom HR zone percentages
```

### Directory Structure

**Automation uses these directories:**

```
data/
├── fitness_data.db              # Main database
├── trainingpeaks_downloads/     # Downloaded ZIP files (temp)
│   ├── WorkoutFileExport-*.zip
│   ├── WorkoutExport-*.zip
│   └── MetricsExport-*.zip
└── trainingpeaks_extracted/     # Extracted FIT files (temp)
    ├── WorkoutFileExport-*/
    │   └── *.fit
    └── (cleaned up after processing)

logs/
├── daily_automation.out         # Stdout from automation
└── daily_automation.err         # Stderr from automation
```

**Directory Creation:**

Directories are created automatically by the automation system:

```python
# In TrainingPeaksSync.__init__
self.downloads_dir.mkdir(parents=True, exist_ok=True)
self.extract_dir.mkdir(parents=True, exist_ok=True)
```

### Rate Limiting Settings

**Configured in `DailyAutoSyncAndAnalyze`:**

```python
# Rate limiting for Gemini API
self.api_delay = 6  # seconds between analyses
```

**Modify for different API tiers:**

```python
# Free tier: 15 RPM → 6 seconds
automation = DailyAutoSyncAndAnalyze()
automation.api_delay = 6

# Paid tier: 60 RPM → 1 second
automation.api_delay = 1

# Conservative: 30 RPM → 2 seconds
automation.api_delay = 2
```

### Browser Settings

**Headless mode (default):**

```python
browser = p.chromium.launch(
    headless=True,  # No visible window
    downloads_path=str(self.downloads_dir)
)
```

**Debug mode (visible browser):**

```python
browser = p.chromium.launch(
    headless=False,  # Show browser window
    downloads_path=str(self.downloads_dir)
)
```

**Slow-motion mode (for debugging):**

```python
browser = p.chromium.launch(
    headless=False,
    slow_mo=1000,  # 1 second between actions
    downloads_path=str(self.downloads_dir)
)
```

---

## Troubleshooting

### Issue 0: Playwright Not Installed in Docker (COMMON)

**Symptoms:**

- Error immediately when clicking TrainingPeaks sync button
- "Executable doesn't exist at /path/to/chromium"
- "playwright.\_impl.\_api_types.Error: Browser is not installed"

**This is the most common issue on new deployments (Beelink, Raspberry Pi, etc.)**

**Root Cause:**
The Dockerfile installs the `playwright` Python package but **not** the Chromium browser binaries. Playwright needs both.

**Solutions:**

1. **Update Dockerfile to install Playwright browsers:**

   ```dockerfile
   # Add after pip install
   RUN playwright install chromium
   RUN playwright install-deps chromium
   ```

2. **Rebuild Docker containers:**

   ```bash
   # Stop containers
   docker-compose down

   # Rebuild with no cache (important!)
   docker-compose build --no-cache

   # Start containers
   docker-compose up -d
   ```

3. **Use the automated fix script:**

   ```bash
   # Run from project root
   ./deploy_playwright_fix.sh
   ```

4. **Verify installation:**

   ```bash
   # Check Playwright is installed in container
   docker exec fitness-tracker-ui python -c "from playwright.sync_api import sync_playwright; print('✅ Playwright installed')"

   # Check Chromium browser exists
   docker exec fitness-tracker-ui sh -c "ls -la /root/.cache/ms-playwright/chromium-*/"
   ```

5. **If still failing, check system dependencies:**

   The Dockerfile must include Chromium's required system libraries:

   ```dockerfile
   RUN apt-get update && apt-get install -y \
       libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
       libcups2 libdrm2 libdbus-1-3 libxkbcommon0 \
       libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
       libgbm1 libpango-1.0-0 libcairo2 libasound2 \
       libatspi2.0-0 libxshmfence1
   ```

**Prevention:**
Always rebuild containers after updating the Dockerfile. Use `--no-cache` to ensure fresh installations.

### Issue 1: Login Fails / Captcha Required

**Symptoms:**

- Browser automation times out at login
- "Login timeout - captcha may need to be solved manually"

**Solutions:**

1. **Run in visible mode for manual captcha solving:**

   ```python
   # In trainingpeaks_sync.py, temporarily change:
   browser = p.chromium.launch(headless=False)  # Was: headless=True
   ```

2. **Increase captcha wait time:**

   ```python
   # In login_and_navigate method:
   page.wait_for_selector("button:has-text('Calendar')", timeout=120000)  # Was: 60000
   ```

3. **Check TrainingPeaks credentials:**

   ```bash
   # Verify .env file
   cat .env | grep TRAININGPEAKS

   # Test login manually in browser
   ```

4. **Use anti-captcha service (advanced):**
   - Integrate 2Captcha or similar service
   - Not recommended for personal use due to cost

### Issue 2: Download Files Not Found

**Symptoms:**

- "No export files found in Downloads folder"
- FIT files count is 0

**Solutions:**

1. **Check downloads directory:**

   ```bash
   ls -la data/trainingpeaks_downloads/
   ```

2. **Verify date range:**

   ```python
   # Make sure you have workouts in the date range
   sync.run_sync(start_date=date(2025, 1, 1), end_date=date(2025, 1, 14))
   ```

3. **Check file naming patterns:**

   ```python
   # In trainingpeaks_file_processor.py
   # Adjust find_latest_exports() patterns if TrainingPeaks changed format
   ```

4. **Manual download test:**
   - Log into TrainingPeaks manually
   - Navigate to Settings → Data Export
   - Verify exports work

### Issue 3: FIT File Parsing Errors

**Symptoms:**

- "No data found in [file].fit"
- "Failed to analyze [file]"

**Solutions:**

1. **Check FIT file integrity:**

   ```python
   from fitparse import FitFile

   fit = FitFile('data/trainingpeaks_extracted/workout.fit')
   messages = list(fit.get_messages('record'))
   print(f"Found {len(messages)} records")
   ```

2. **Verify FIT file is decompressed:**

   ```bash
   # Should be .fit, not .fit.gz
   file data/trainingpeaks_extracted/*.fit
   ```

3. **Re-download specific workout:**

   ```python
   # Sync just the problem date
   sync.run_sync(start_date=date(2025, 1, 10), end_date=date(2025, 1, 10))
   ```

4. **Check file size:**
   ```bash
   # FIT files should be > 0 bytes
   ls -lh data/trainingpeaks_extracted/*.fit
   ```

### Issue 4: API Upload Failures

**Symptoms:**

- "FIT upload failed: Connection refused"
- "Workouts CSV failed: 500 Internal Server Error"

**Solutions:**

1. **Verify API is running:**

   ```bash
   # Check FastAPI server
   curl http://localhost:8000/

   # Should return: {"status": "ok", "message": "Fitness Tracker API"}
   ```

2. **Check API_URL environment variable:**

   ```bash
   # In .env file
   API_URL=http://localhost:8000  # For local
   # or
   API_URL=http://100.117.194.8:8000  # For production
   ```

3. **Start API server:**

   ```bash
   # In project root
   ./bin/start_app.sh

   # Or manually
   uvicorn src.api.main:app --host 0.0.0.0 --port 8000
   ```

4. **Check API logs:**
   ```bash
   # View API errors
   docker logs fitness-tracker-api  # If using Docker
   # or
   journalctl -u fitness-tracker -n 50  # If using systemd
   ```

### Issue 5: AI Analysis Rate Limits

**Symptoms:**

- "429 Too Many Requests"
- "Quota exceeded"

**Solutions:**

1. **Increase rate limiting delay:**

   ```python
   automation = DailyAutoSyncAndAnalyze()
   automation.api_delay = 10  # Increase to 10 seconds
   ```

2. **Use dynamic free models:**

   ```python
   # Already configured in automation:
   analyzer = FitFileAnalyzer(use_dynamic_models=True)
   # This automatically uses free Gemini models
   ```

3. **Batch process over multiple days:**

   ```python
   # Spread analysis across multiple runs
   for day in range(7):
       target = date.today() - timedelta(days=day)
       automation.run_daily_automation(target_date=target)
       time.sleep(3600)  # 1 hour between batches
   ```

4. **Check Gemini API quota:**
   - Visit https://aistudio.google.com/
   - Check quota limits and usage

### Issue 6: Cron Job Not Running

**Symptoms:**

- No new logs in `logs/daily_automation.out`
- Automation never runs automatically

**Solutions:**

1. **Check crontab is configured:**

   ```bash
   crontab -l
   # Should show: 0 22 * * * /path/to/run_daily_automation.sh
   ```

2. **Verify script is executable:**

   ```bash
   ls -l bin/run_daily_automation.sh
   # Should show: -rwxr-xr-x (x = executable)

   chmod +x bin/run_daily_automation.sh
   ```

3. **Test script manually:**

   ```bash
   # Run script to check for errors
   ./bin/run_daily_automation.sh

   # Check exit code
   echo $?  # Should be 0 if successful
   ```

4. **Check cron logs:**

   ```bash
   # macOS
   tail -f /var/log/cron.log

   # Linux
   grep CRON /var/log/syslog
   ```

5. **Verify paths are absolute:**

   ```bash
   # In crontab, use full paths:
   0 22 * * * /Users/jacobrobinson/fitness_tracker/bin/run_daily_automation.sh

   # NOT relative paths:
   0 22 * * * ./bin/run_daily_automation.sh  # Won't work
   ```

### Issue 7: Playwright Browser Not Found

**Symptoms:**

- "Executable doesn't exist at /path/to/chromium"
- ImportError: Playwright not installed

**Solutions:**

1. **Install Playwright browsers:**

   ```bash
   # Activate virtual environment
   source venv/bin/activate

   # Install Playwright
   pip install playwright

   # Install browser binaries
   playwright install chromium
   ```

2. **Verify installation:**

   ```bash
   playwright --version
   playwright show-browsers
   ```

3. **Re-install if corrupted:**
   ```bash
   playwright uninstall chromium
   playwright install chromium
   ```

### Issue 8: Memory Leaks / High CPU Usage

**Symptoms:**

- Automation process uses excessive memory
- System becomes slow during sync

**Solutions:**

1. **Close browser properly:**

   ```python
   # Ensure browser.close() is called
   try:
       # ... automation code ...
   finally:
       browser.close()
   ```

2. **Limit parallel processing:**

   ```python
   # Process FIT files sequentially (already done)
   for fit_file in fit_files:
       analyze_workout(fit_file)
       time.sleep(6)  # Rate limiting also helps memory
   ```

3. **Monitor resource usage:**

   ```bash
   # Check memory during automation
   watch -n 1 'ps aux | grep chromium'

   # Check overall system
   htop
   ```

4. **Increase system resources:**
   - Close other applications
   - Increase Docker memory limits (if containerized)
   - Use swap space if low on RAM

---

## Related Documentation

- **[Data Processing Pipeline](data-processing-pipeline.md)** - FIT file parsing and interval detection
- **[AI Coaching System](ai-coaching-system.md)** - Workout analysis with Gemini AI
- **[Database Schema](database-schema.md)** - Data storage and relationships
- **[API Endpoints](api-endpoints.md)** - FastAPI upload endpoints
- **[Development Workflow](../agent-instructions/development-workflow.md)** - Testing and debugging

---

**Last Updated:** January 14, 2025
