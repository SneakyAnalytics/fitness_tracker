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
        self.downloads_dir = Path.home() / "Downloads"
        self.extract_dir = Path("/tmp") / "trainingpeaks_extracted"
        self.api_base = "http://localhost:8000"
    
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
        
        # Wait for potential captcha - give user 30 seconds
        print("⏸️  Waiting for login to complete (solve captcha if it appears)...")
        try:
            page.wait_for_selector("button:has-text('Calendar')", timeout=30000)
            print("✅ Login successful!")
        except:
            print("❌ Login timeout - captcha may need to be solved manually")
            print("   Waiting an additional 30 seconds...")
            time.sleep(30)
        
        # Navigate to Settings
        print("⚙️  Navigating to Settings...")
        page.click("button:has-text('Calendar')")
        
        # Give the page a moment to load
        time.sleep(2)
        
        # Click user menu - this is typically your name displayed in the top right
        print("   Opening user menu (looking for your display name)...")
        
        # Try to find and click the user menu by various methods
        user_menu_clicked = False
        
        # Method 1: Try clicking on any visible name/user menu button
        try:
            # Look for common user menu patterns
            selectors = [
                "button[class*='userMenu']",
                "div[class*='userMenu'] button",
                "button[aria-label*='menu']",
                "button[aria-label*='account']",
                # Try finding by the Settings option being visible (reverse approach)
                "xpath=//label[contains(text(), 'Settings')]/ancestor::div[contains(@class, 'menu')]//button"
            ]
            
            for selector in selectors:
                try:
                    page.click(selector, timeout=2000)
                    user_menu_clicked = True
                    print(f"   ✓ User menu opened")
                    break
                except:
                    continue
                    
        except Exception as e:
            print(f"   ⚠️  Standard selectors failed: {e}")
        
        # Method 2: If standard selectors fail, try to find any clickable text that might be a username
        if not user_menu_clicked:
            print("   Trying to find username text...")
            try:
                # Get all p tags with MuiTypography class (common for user display)
                page.evaluate("""
                    () => {
                        const elements = document.querySelectorAll('p.MuiTypography-root');
                        console.log('Found typography elements:', elements.length);
                        elements.forEach((el, i) => {
                            console.log(`Element ${i}: "${el.textContent}"`);
                        });
                    }
                """)
                
                # Try clicking elements that might be usernames (not "Calendar", "Dashboard", etc.)
                excluded_texts = ['Calendar', 'Dashboard', 'Workouts', 'Reports', 'Training', 'Metrics']
                page.evaluate(f"""
                    () => {{
                        const excluded = {json.dumps(excluded_texts)};
                        const elements = document.querySelectorAll('p.MuiTypography-root');
                        for (let el of elements) {{
                            const text = el.textContent.trim();
                            if (text && text.length > 2 && !excluded.includes(text)) {{
                                console.log('Trying to click:', text);
                                el.click();
                                return true;
                            }}
                        }}
                        return false;
                    }}
                """)
                time.sleep(1)
                user_menu_clicked = True
                print("   ✓ Clicked potential user menu element")
            except Exception as e:
                print(f"   ⚠️  Could not find username: {e}")
        
        # Final attempt: Just wait for Settings to appear and click it directly
        if not user_menu_clicked:
            print("   ⚠️  Waiting for Settings option to appear...")
            time.sleep(3)
        
        # Click Settings from the dropdown menu (should be visible now)
        print("   Clicking Settings option...")
        page.click("label.userSettingsOption:has-text('Settings')", timeout=10000)
        
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
        
        return results
    
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
                # Launch browser
                browser = p.chromium.launch(headless=False, downloads_path=str(self.downloads_dir))
                context = browser.new_context(accept_downloads=True)
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
