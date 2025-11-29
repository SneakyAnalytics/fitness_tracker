#!/usr/bin/env python3
"""
Re-upload Nov 17-20 FIT files with corrected timezone conversion
"""
import sys
import requests
from pathlib import Path

def upload_fit_file(file_path: Path, api_url: str = "http://localhost:8000"):
    """Upload a single FIT file to the API"""
    try:
        with open(file_path, 'rb') as f:
            files = {'file': (file_path.name, f, 'application/octet-stream')}
            response = requests.post(f"{api_url}/upload/fit", files=files)
            
        if response.status_code == 200:
            print(f"✅ {file_path.name}")
            return True
        else:
            print(f"❌ {file_path.name}: {response.status_code} - {response.text[:100]}")
            return False
    except Exception as e:
        print(f"❌ {file_path.name}: {e}")
        return False

def main():
    # FIT files to upload (in chronological order)
    fit_files = [
        Path("~/Downloads/trainingpeaks_extracted/WorkoutFileExport-Robinson-Jake-2025-11-17-2025-11-17/zwift-activity-2009248879257600000.fit"),  # Nov 17 evening - light workout
        Path("~/Downloads/trainingpeaks_extracted/WorkoutFileExport-Robinson-Jake-2025-11-18-2025-11-18/zwift-activity-2009997700933648416.fit"),  # Nov 18 evening - race warmup  
        Path("~/Downloads/trainingpeaks_extracted/WorkoutFileExport-Robinson-Jake-2025-11-18-2025-11-18/zwift-activity-2010005754467090448.fit"),  # Nov 18 evening - actual race
        Path("~/Downloads/trainingpeaks_extracted/WorkoutFileExport-Robinson-Jake-2025-11-19-2025-11-19/zwift-activity-2010366798410579968.fit"),  # Nov 19 morning - recovery
    ]
    
    print("\n" + "="*80)
    print("Re-uploading FIT files with corrected timezone conversion")
    print("="*80 + "\n")
    
    # Check if API is running
    try:
        response = requests.get("http://localhost:8000/docs")
        if response.status_code != 200:
            print("⚠️  API may not be running. Start it with: uvicorn src.api.app:app --reload")
            return
    except:
        print("❌ API is not running. Start it with: uvicorn src.api.app:app --reload")
        return
    
    uploaded = 0
    for fit_path in fit_files:
        expanded_path = fit_path.expanduser()
        if not expanded_path.exists():
            print(f"⚠️  Not found: {fit_path}")
            continue
        
        if upload_fit_file(expanded_path):
            uploaded += 1
    
    print(f"\n✅ Uploaded {uploaded}/{len(fit_files)} files")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
