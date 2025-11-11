"""
TrainingPeaks Automated Sync
Standalone script that runs browser automation directly
"""

import os
import time
from pathlib import Path
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright, Page
import requests
from dotenv import load_dotenv
from trainingpeaks_file_processor import TrainingPeaksFileProcessor
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
        self.extract_dir = Path.home() / "Downloads" / "trainingpeaks_extracted"
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
        page.click("p.MuiTypography-root:has-text('Jake Robinson')")
        page.click("label.userSettingsOption:has-text('Settings')")
        
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
    
    def process_and_upload_files(self):
        """Process downloaded files and upload to database"""
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
            'errors': []
        }
        
        # Process FIT files
        if workout_files_path:
            print(f"📦 Processing FIT files from {workout_files_path.name}...")
            try:
                # Check if it's a directory or ZIP
                if workout_files_path.is_dir():
                    # Already extracted - find .fit.gz files directly
                    fit_gz_files = list(workout_files_path.rglob('*.fit.gz'))
                    fit_files = []
                    for fit_gz in fit_gz_files:
                        fit_file = processor.decompress_fit_gz(fit_gz)
                        fit_files.append(fit_file)
                else:
                    # It's a ZIP - use the processor method
                    fit_files = processor.process_workout_files_export(workout_files_path)
                
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
    
    def run_sync(self, start_date=None, end_date=None):
        """Run the complete sync process"""
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
            results = self.process_and_upload_files()
            
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
