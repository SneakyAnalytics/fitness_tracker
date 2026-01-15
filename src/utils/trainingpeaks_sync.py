"""
TrainingPeaks Automated Sync
Standalone script that runs browser automation directly
"""

import os
import time
import json
from pathlib import Path
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright, Page
import requests
from dotenv import load_dotenv
from .trainingpeaks_file_processor import TrainingPeaksFileProcessor
import nest_asyncio

# Allow nested event loops (needed when running from Streamlit)
nest_asyncio.apply()


class TrainingPeaksSync:
    """Automated sync from TrainingPeaks to local database"""
    
    def __init__(self):
        load_dotenv()
        self.username = os.getenv("TRAININGPEAKS_USERNAME")
        self.password = os.getenv("TRAININGPEAKS_PASSWORD")
        # Use dedicated project directory for downloads instead of ~/Downloads
        project_root = Path(__file__).parent.parent.parent
        self.downloads_dir = project_root / "data" / "trainingpeaks_downloads"
        self.extract_dir = project_root / "data" / "trainingpeaks_extracted"
        # Ensure directories exist
        self.downloads_dir.mkdir(parents=True, exist_ok=True)
        self.extract_dir.mkdir(parents=True, exist_ok=True)
        # Use API_URL from environment, fallback to localhost for local development
        self.api_base = os.getenv("API_URL", "http://localhost:8000")
    
    def get_current_week_dates(self):
        """Get Monday to Sunday of current week"""
        today = datetime.now().date()
        days_since_monday = today.weekday()
        monday = today - timedelta(days=days_since_monday)
        sunday = monday + timedelta(days=6)
        return monday, sunday
    
    def login_and_navigate(self, page: Page):
        """Handle login and navigation to export page"""
        print("🌐 Navigating to TrainingPeaks...")
        page.goto("https://www.trainingpeaks.com")
        
        # Accept cookies if present
        try:
            page.click("button#onetrust-accept-btn-handler", timeout=3000)
        except:
            pass
        
        # Click login
        print("🔐 Logging in...")
        page.click("a[href*='login']")
        page.wait_for_selector("input[name='Username']")
        
        # Fill credentials
        page.fill("input[name='Username']", self.username)
        page.fill("input[name='Password']", self.password)
        page.click("button[type='submit']")
        
        # Wait for potential captcha - give user 60 seconds in containerized environment
        print("⏸️  Waiting for login to complete (solve captcha if it appears)...")
        try:
            page.wait_for_selector("button:has-text('Calendar')", timeout=60000)
            print("✅ Login successful!")
        except:
            print("❌ Login timeout - captcha may need to be solved manually")
            print("   Waiting an additional 30 seconds...")
            time.sleep(30)
        
        # Add a small delay to ensure page is fully loaded
        time.sleep(2)
        
        # Navigate to Settings
        print("⚙️  Navigating to Settings...")
        
        # First, click Calendar to go to the main app
        try:
            page.click("button:has-text('Calendar')", timeout=10000)
            print("   ✓ Clicked Calendar button")
            time.sleep(1)  # Wait for navigation
        except Exception as e:
            print(f"   ⚠️  Could not find Calendar button: {e}")
            print("   Trying to continue anyway...")
            time.sleep(1)
        
        # Give the page a moment to load
        time.sleep(3)
        
        # Debug: Take a screenshot to see what's on the page
        try:
            screenshot_path = self.downloads_dir / "debug_after_login.png"
            page.screenshot(path=str(screenshot_path))
            print(f"   📸 Screenshot saved to: {screenshot_path}")
        except:
            pass
        
        # Click user menu - this is typically your name displayed in the top right
        print("   Opening user menu (looking for 'Jake Robinson')...")
        
        # Try to find and click the user menu by various methods
        user_menu_clicked = False
        
        # Method 1: Try clicking directly on "Jake Robinson"
        try:
            page.click("text=Jake Robinson", timeout=3000)
            user_menu_clicked = True
            print("   ✓ Clicked on 'Jake Robinson'")
        except Exception as e:
            print(f"   ⚠️  Could not click 'Jake Robinson' directly: {e}")
        
        # Method 2: Try common user menu patterns
        if not user_menu_clicked:
            print("   Trying alternative selectors...")
            selectors = [
                "button[class*='userMenu']",
                "div[class*='userMenu'] button",
                "button[aria-label*='menu']",
                "button[aria-label*='account']",
                "p.MuiTypography-root:has-text('Jake Robinson')",
            ]
            
            for selector in selectors:
                try:
                    page.click(selector, timeout=2000)
                    user_menu_clicked = True
                    print(f"   ✓ User menu opened with: {selector}")
                    break
                except:
                    continue
        
        # Method 3: JavaScript fallback
        if not user_menu_clicked:
            print("   Trying JavaScript to find clickable elements...")
            try:
                # Log all clickable text elements
                elements_info = page.evaluate("""
                    () => {
                        const elements = document.querySelectorAll('p, button, a, span');
                        const result = [];
                        elements.forEach((el) => {
                            const text = el.textContent.trim();
                            if (text && text.length > 0 && text.length < 50) {
                                result.push(text);
                            }
                        });
                        return result.slice(0, 30); // First 30 elements
                    }
                """)
                print(f"   Found {len(elements_info)} clickable elements:")
                for i, text in enumerate(elements_info[:10]):
                    print(f"     {i}: '{text}'")
                
                # Try to click "Jake Robinson" via JavaScript
                clicked = page.evaluate("""
                    () => {
                        const elements = document.querySelectorAll('p, button, span');
                        for (let el of elements) {
                            if (el.textContent.includes('Jake Robinson')) {
                                console.log('Found and clicking:', el.textContent);
                                el.click();
                                return true;
                            }
                        }
                        return false;
                    }
                """)
                if clicked:
                    user_menu_clicked = True
                    print("   ✓ Clicked 'Jake Robinson' via JavaScript")
                    time.sleep(2)
            except Exception as e:
                print(f"   ⚠️  JavaScript method failed: {e}")
        
        # Click Settings from the dropdown menu (should be visible now)
        print("   Clicking Settings option...")
        try:
            page.click("label.userSettingsOption:has-text('Settings')", timeout=10000)
            print("   ✓ Settings clicked")
        except Exception as e:
            print(f"   ❌ Could not click Settings: {e}")
            # Take another screenshot to see the menu
            try:
                screenshot_path = self.downloads_dir / "debug_after_usermenu.png"
                page.screenshot(path=str(screenshot_path))
                print(f"   📸 Screenshot saved to: {screenshot_path}")
            except:
                pass
            raise
        
        # Wait for export page
        page.wait_for_selector("input.datepicker.startDate", timeout=10000)
        print("✅ Export page loaded")
    
    def export_data(self, page: Page, start_date: str, end_date: str):
        """Fill dates and trigger exports"""
        print(f"📅 Setting date range: {start_date} to {end_date}")
        
        # Fill all date fields using JavaScript
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
        
        print("📥 Triggering exports...")
        
        # Click first export button (Workout Files)
        page.evaluate("document.querySelectorAll('button.download.tpSecondaryButton')[0].click()")
        time.sleep(2)
        
        # Click second export button (Workout Summary)
        page.evaluate("document.querySelectorAll('button.download.tpSecondaryButton')[1].click()")
        time.sleep(2)
        
        # Click third export button (Custom Metrics)
        page.evaluate("document.querySelectorAll('button.download.tpSecondaryButton')[2].click()")
        time.sleep(3)
        
        # Hide datepicker overlay
        print("💾 Starting downloads...")
        page.evaluate("""
            document.getElementById('ui-datepicker-div').style.display = 'none';
        """)
        
        # Click all download links (they appear in dialogs, so click first available each time)
        downloads = []
        max_attempts = 3  # Try to get 3 downloads
        
        for attempt in range(max_attempts):
            try:
                # Check if any links are available
                num_links = page.evaluate("document.querySelectorAll('a#userConfirm').length")
                if num_links == 0:
                    print(f"   No more download links available")
                    break
                
                # Always click the first link [0] since the array updates after each download
                with page.expect_download(timeout=60000) as download_info:
                    page.evaluate("document.querySelectorAll('a#userConfirm')[0].click()")
                download = download_info.value
                downloads.append(download)
                print(f"   📥 Download {attempt+1} started: {download.suggested_filename}")
                
                # Small delay to let dialog close before checking for next link
                time.sleep(0.5)
                
            except Exception as e:
                print(f"   ⚠️ Download {attempt+1} failed: {e}")
                # Continue trying in case there are more links
        
        print("⏳ Saving downloads...")
        
        # Save downloads with proper filenames
        saved_files = []
        for download in downloads:
            try:
                suggested_name = download.suggested_filename
                save_path = self.downloads_dir / suggested_name
                download.save_as(save_path)
                saved_files.append(save_path)
                print(f"   ✅ Saved: {suggested_name}")
            except Exception as e:
                print(f"   ❌ Failed to save: {e}")
        
        print(f"✅ Downloaded and saved {len(saved_files)} files!")
    
    def process_and_upload_files(self, cleanup_fit_files: bool = True):
        """Process downloaded files and upload to database
        
        Args:
            cleanup_fit_files: If False, FIT files are kept after upload for further processing
        """
        print("\n📦 Processing downloaded files...")
        
        processor = TrainingPeaksFileProcessor(self.downloads_dir, self.extract_dir)
        
        # Find the latest files - returns tuple of (workout_files, workout_summary, metrics)
        workout_files_path, workout_summary_path, metrics_path = processor.find_latest_exports()
        
        if not workout_files_path and not workout_summary_path and not metrics_path:
            print("❌ No export files found in Downloads folder")
            return {'fit_files': 0, 'workouts': False, 'metrics': False, 'errors': ['No files found']}
        
        results = {
            'fit_files': 0,
            'workouts': False,
            'metrics': False,
            'errors': [],
            'fit_file_paths': []  # Track extracted FIT file paths
        }
        
        extracted_fit_files = []  # Track extracted FIT file paths at function level
        
        # Process FIT files
        extracted_fit_files = []  # Track extracted FIT file paths
        if workout_files_path:
            print(f"📦 Processing FIT files from {workout_files_path.name}...")
            try:
                # Check if it's a directory or ZIP
                if workout_files_path.is_dir():
                    # Already extracted - find both .fit.gz and .FIT.gz files (case-insensitive)
                    fit_gz_files = list(workout_files_path.rglob('*.fit.gz'))
                    fit_gz_files.extend(list(workout_files_path.rglob('*.FIT.gz')))  # Add uppercase variant
                    fit_files = []
                    # Decompress .fit.gz/.FIT.gz files
                    for fit_gz in fit_gz_files:
                        fit_file = processor.decompress_fit_gz(fit_gz)
                        fit_files.append(fit_file)
                    # Also find plain .fit/.FIT files (case-insensitive)
                    plain_fit_files = list(workout_files_path.rglob('*.fit'))
                    plain_fit_files.extend(list(workout_files_path.rglob('*.FIT')))
                    # Filter out any files that were just decompressed
                    plain_fit_files = [f for f in plain_fit_files if not any(str(f).endswith(str(gz.with_suffix(''))) for gz in fit_gz_files)]
                    fit_files.extend(plain_fit_files)
                else:
                    # It's a ZIP - use the processor method
                    fit_files = processor.process_workout_files_export(workout_files_path)
                
                extracted_fit_files = fit_files  # Save for later analysis
                print(f"   Found {len(fit_files)} FIT files")
                
                # Upload each FIT file
                for fit_file in fit_files:
                    try:
                        with open(fit_file, 'rb') as f:
                            files_payload = {'file': (Path(fit_file).name, f, 'application/octet-stream')}
                            response = requests.post(f"{self.api_base}/upload/fit", files=files_payload)
                            if response.status_code == 200:
                                results['fit_files'] += 1
                                print(f"   ✅ Uploaded {Path(fit_file).name}")
                            else:
                                print(f"   ❌ Failed to upload {Path(fit_file).name}: {response.status_code}")
                                results['errors'].append(f"FIT upload failed: {Path(fit_file).name}")
                    except Exception as e:
                        print(f"   ❌ Error uploading {fit_file}: {str(e)}")
                        results['errors'].append(f"FIT error: {str(e)}")
                
                # Store FIT file paths in results
                results['fit_file_paths'] = extracted_fit_files
                
                # Clean up FIT files after upload (if enabled)
                if cleanup_fit_files:
                    print("🗑️  Cleaning up FIT files...")
                    for fit_file in fit_files:
                        try:
                            Path(fit_file).unlink()
                        except Exception as cleanup_err:
                            print(f"   ⚠️  Could not delete {Path(fit_file).name}: {cleanup_err}")
                
                # Clean up extraction directory if it's in /tmp (if cleanup enabled)
                if cleanup_fit_files and workout_files_path and str(workout_files_path).startswith('/tmp'):
                    try:
                        import shutil
                        # Find the top-level extraction directory
                        extract_base = workout_files_path
                        while extract_base.parent != Path('/tmp/trainingpeaks_extracted') and extract_base.parent.name != 'trainingpeaks_extracted':
                            extract_base = extract_base.parent
                            if extract_base == Path('/tmp'):
                                break
                        
                        if extract_base != Path('/tmp') and extract_base.exists():
                            shutil.rmtree(extract_base)
                            print(f"   🗑️  Removed extraction directory: {extract_base.name}")
                    except Exception as cleanup_err:
                        print(f"   ⚠️  Could not clean extraction directory: {cleanup_err}")
                
            except Exception as e:
                print(f"❌ Error processing FIT files: {str(e)}")
                results['errors'].append(f"FIT processing error: {str(e)}")
        
        # Upload workouts CSV
        if workout_summary_path:
            print(f"📤 Uploading {workout_summary_path.name}...")
            try:
                # Extract if it's a ZIP
                if workout_summary_path.suffix == '.zip':
                    extracted_dir = processor.extract_zip(workout_summary_path)
                    csv_files = list(Path(extracted_dir).glob('*.csv'))
                    if csv_files:
                        csv_path = csv_files[0]
                    else:
                        raise FileNotFoundError("No CSV found in WorkoutExport ZIP")
                else:
                    csv_path = workout_summary_path
                
                with open(csv_path, 'rb') as f:
                    files_payload = {'file': ('workouts.csv', f, 'text/csv')}
                    response = requests.post(f"{self.api_base}/upload/workouts", files=files_payload)
                    if response.status_code == 200:
                        print("   ✅ Workouts uploaded successfully")
                        results['workouts'] = True
                    else:
                        print(f"   ❌ Failed: {response.status_code}")
                        results['errors'].append(f"Workouts upload failed: {response.status_code}")
            except Exception as e:
                print(f"❌ Error uploading workouts: {str(e)}")
                results['errors'].append(f"Workouts error: {str(e)}")
        
        # Upload metrics CSV
        if metrics_path:
            print(f"📤 Uploading {metrics_path.name}...")
            try:
                # Extract if it's a ZIP
                if metrics_path.suffix == '.zip':
                    extracted_dir = processor.extract_zip(metrics_path)
                    csv_files = list(Path(extracted_dir).glob('*.csv'))
                    if csv_files:
                        csv_path = csv_files[0]
                    else:
                        raise FileNotFoundError("No CSV found in MetricsExport ZIP")
                else:
                    csv_path = metrics_path
                
                with open(csv_path, 'rb') as f:
                    files_payload = {'file': ('metrics.csv', f, 'text/csv')}
                    response = requests.post(f"{self.api_base}/upload/metrics", files=files_payload)
                    if response.status_code == 200:
                        print("   ✅ Metrics uploaded successfully")
                        results['metrics'] = True
                    else:
                        print(f"   ❌ Failed: {response.status_code}")
                        results['errors'].append(f"Metrics upload failed: {response.status_code}")
            except Exception as e:
                print(f"❌ Error uploading metrics: {str(e)}")
                results['errors'].append(f"Metrics error: {str(e)}")
        
        # Clean up downloaded ZIP files after successful processing
        print("\n🗑️  Cleaning up downloaded files...")
        try:
            zip_files = [
                self.downloads_dir / f"WorkoutFileExport-{datetime.now().strftime('%Y%m%d')}.zip",
                self.downloads_dir / f"WorkoutExport-{datetime.now().strftime('%Y%m%d')}.zip",
                self.downloads_dir / f"MetricsExport-{datetime.now().strftime('%Y%m%d')}.zip"
            ]
            
            # Also find any ZIP files from today in downloads directory
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
        
        # Link workouts to fit_files by matching TSS and duration
        if results['workouts'] and results['fit_files'] > 0:
            print("\n🔗 Linking workouts to FIT files...")
            try:
                self._match_workouts_to_fit_files(start_date, end_date)
            except Exception as e:
                print(f"   ⚠️  Matching warning: {e}")
        
        # Use AI to match workouts to proposed workouts for multi-workout days
        if results['workouts']:
            print("\n🤖 AI matching workouts to proposed workouts...")
            try:
                self._ai_match_to_proposed_workouts(start_date, end_date)
            except Exception as e:
                print(f"   ⚠️  AI matching warning: {e}")
        
        return results
    
    def _match_workouts_to_fit_files(self, start_date, end_date):
        """
        Match workouts to fit_files by comparing TSS and duration.
        This ensures workout records are linked to their FIT file data.
        """
        import sqlite3
        import json
        from pathlib import Path
        
        project_root = Path(__file__).parent.parent.parent
        db_path = project_root / "data" / "fitness_data.db"
        
        conn = sqlite3.connect(str(db_path))
        c = conn.cursor()
        
        try:
            # Get workouts without fit_file_id in date range
            c.execute('''
                SELECT id, workout_day, workout_title, workout_data
                FROM workouts
                WHERE workout_day BETWEEN ? AND ?
                  AND fit_file_id IS NULL
                ORDER BY workout_day, id
            ''', (start_date, end_date))
            
            workouts = []
            for row in c.fetchall():
                data = json.loads(row[3])
                metrics = data.get('metrics', {})
                workouts.append({
                    'id': row[0],
                    'day': row[1],
                    'title': row[2],
                    'tss': float(metrics.get('actual_tss', 0) or 0),
                    'duration_min': float(metrics.get('actual_duration', 0) or 0)
                })
            
            # Get fit_files in date range
            c.execute('''
                SELECT id, workout_day, file_name, fit_data
                FROM fit_files
                WHERE workout_day BETWEEN ? AND ?
                ORDER BY workout_day, id
            ''', (start_date, end_date))
            
            fit_files = []
            for row in c.fetchall():
                data = json.loads(row[3])
                metrics = data.get('metrics', {})
                fit_files.append({
                    'id': row[0],
                    'day': row[1],
                    'file_name': row[2],
                    'tss': float(metrics.get('tss', 0) or 0),
                    'duration_min': float(metrics.get('duration', 0) or 0)
                })
            
            # Match by day + closest TSS + duration
            matched_count = 0
            for workout in workouts:
                candidates = [f for f in fit_files if f['day'] == workout['day']]
                
                if not candidates:
                    continue
                
                best_match = None
                best_score = 999999
                
                for fit in candidates:
                    tss_diff = abs(workout['tss'] - fit['tss'])
                    dur_diff = abs(workout['duration_min'] - fit['duration_min'])
                    score = tss_diff + dur_diff
                    
                    if score < best_score:
                        best_score = score
                        best_match = fit
                
                # Match if score is reasonable (within 5 units total difference)
                if best_match and best_score < 5:
                    c.execute('UPDATE workouts SET fit_file_id = ? WHERE id = ?', 
                             (best_match['id'], workout['id']))
                    matched_count += 1
                    # Remove from candidates to avoid duplicate matching
                    fit_files.remove(best_match)
            
            conn.commit()
            if matched_count > 0:
                print(f"   ✅ Matched {matched_count} workouts to FIT files")
            else:
                print("   ℹ️  No new workout-FIT file matches needed")
                
        finally:
            conn.close()
    
    def _ai_match_to_proposed_workouts(self, start_date, end_date):
        """
        Use AI to match workouts to proposed workouts on days with multiple workouts.
        Stores the proposed_workout_name in the workouts table for use during analysis.
        """
        import sqlite3
        import json
        from pathlib import Path
        from .workout_matcher import WorkoutMatcher
        
        project_root = Path(__file__).parent.parent.parent
        db_path = project_root / "data" / "fitness_data.db"
        
        conn = sqlite3.connect(str(db_path))
        c = conn.cursor()
        
        try:
            matcher = WorkoutMatcher()
            
            # Find days with multiple workouts in the date range
            c.execute('''
                SELECT workout_day, COUNT(*) as workout_count
                FROM workouts
                WHERE workout_day BETWEEN ? AND ?
                  AND (workout_data IS NOT NULL OR fit_file_id IS NOT NULL)
                GROUP BY workout_day
                HAVING workout_count > 1
            ''', (start_date, end_date))
            
            multi_workout_days = [row[0] for row in c.fetchall()]
            
            if not multi_workout_days:
                print("   ℹ️  No multi-workout days found")
                return
            
            matched_count = 0
            
            for day in multi_workout_days:
                # Get actual workouts for this day
                c.execute('''
                    SELECT id, workout_title, workout_data, athlete_comments
                    FROM workouts
                    WHERE workout_day = ?
                    ORDER BY id
                ''', (day,))
                
                actual_workouts = []
                for row in c.fetchall():
                    workout_id, title, data_json, comments = row
                    data = json.loads(data_json) if data_json else {}
                    metrics = data.get('metrics', {})
                    
                    actual_workouts.append({
                        'id': workout_id,
                        'title': title,
                        'tss': float(metrics.get('actual_tss', 0) or 0),
                        'duration_min': float(metrics.get('actual_duration', 0) or 0),
                        'athlete_comments': comments or '',
                        'sport': data.get('sport', 'cycling')
                    })
                
                # Get proposed workouts for this day
                c.execute('''
                    SELECT pw.name, pw.type, pw.plannedDuration,
                           pw.plannedTSS_min, pw.plannedTSS_max, pw.notes
                    FROM proposed_workouts pw
                    JOIN daily_plans dp ON pw.dailyPlanId = dp.id
                    WHERE dp.date = ?
                ''', (day,))
                
                proposed_workouts = []
                for row in c.fetchall():
                    proposed_workouts.append({
                        'name': row[0],
                        'type': row[1],
                        'plannedDuration': row[2],
                        'plannedTSS_min': row[3],
                        'plannedTSS_max': row[4],
                        'notes': row[5]
                    })
                
                if not proposed_workouts:
                    continue
                
                # Use AI to match
                matches = matcher.match_workouts_for_day(
                    actual_workouts,
                    proposed_workouts,
                    day
                )
                
                # Store matches in database
                for workout_id, proposed_name in matches.items():
                    if proposed_name:
                        c.execute('''
                            UPDATE workouts
                            SET proposed_workout_name = ?
                            WHERE id = ?
                        ''', (proposed_name, workout_id))
                        matched_count += 1
                        print(f"   ✓ Matched workout {workout_id} to '{proposed_name}'")
            
            conn.commit()
            if matched_count > 0:
                print(f"   ✅ AI matched {matched_count} workouts to proposed workouts")
            
        except Exception as e:
            print(f"   ⚠️  AI matching error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            conn.close()
    
    def run_sync(self, start_date=None, end_date=None, cleanup_fit_files=True):
        """Run the complete sync process
        
        Args:
            start_date: Start date for sync
            end_date: End date for sync
            cleanup_fit_files: If False, FIT files are kept after upload for further processing
        """
        # Get dates
        if start_date is None or end_date is None:
            start_date, end_date = self.get_current_week_dates()
        
        start_str = start_date.strftime("%m/%d/%Y")
        end_str = end_date.strftime("%m/%d/%Y")
        
        print("=" * 60)
        print("🚀 TrainingPeaks Automated Sync")
        print("=" * 60)
        print(f"📅 Date Range: {start_str} to {end_str}")
        print(f"👤 User: {self.username}")
        print("=" * 60)
        
        try:
            with sync_playwright() as p:
                # Launch browser in headless mode with custom download path
                browser = p.chromium.launch(
                    headless=True, 
                    downloads_path=str(self.downloads_dir),
                    args=['--disable-blink-features=AutomationControlled']  # Avoid detection
                )
                context = browser.new_context(
                    accept_downloads=True,
                    viewport={'width': 1920, 'height': 1080},  # Set proper viewport size
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                )
                page = context.new_page()
                
                # Run automation
                self.login_and_navigate(page)
                self.export_data(page, start_str, end_str)
                
                # Close browser
                browser.close()
            
            # Process and upload files
            results = self.process_and_upload_files(cleanup_fit_files=cleanup_fit_files)
            
            print("\n" + "=" * 60)
            print("✅ SYNC COMPLETE!")
            print("=" * 60)
            print(f"FIT Files Uploaded: {results['fit_files']}")
            print(f"Workouts CSV: {'✅' if results['workouts'] else '❌'}")
            print(f"Metrics CSV: {'✅' if results['metrics'] else '❌'}")
            if results['errors']:
                print(f"Errors: {len(results['errors'])}")
                for error in results['errors']:
                    print(f"  - {error}")
            print("=" * 60)
            
            return results
            
        except Exception as e:
            print(f"\n❌ Sync failed: {str(e)}")
            import traceback
            traceback.print_exc()
            return None


if __name__ == "__main__":
    sync = TrainingPeaksSync()
    sync.run_sync()
