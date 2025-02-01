# src/utils/fit_parser.py

import gzip
from fitparse import FitFile
from typing import Dict, Any, List, Optional
import numpy as np
from datetime import datetime

def convert_numpy(obj: Any) -> Any:
    """Convert numpy types to Python native types"""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj

def safe_divide(a: float, b: float, default: float = 0.0) -> float:
    """Safely divide two numbers with fallback to default"""
    try:
        if b == 0 or a is None or b is None:
            return default
        return a / b
    except:
        return default

class FitParser:
    def __init__(self):
        # Define heart rate zones (can be customized)
        self.hr_zones = {
            'Zone 1 (Recovery)': (0, 0.60),    # Up to 60% of max HR
            'Zone 2 (Endurance)': (0.60, 0.70), # 60-70% of max HR
            'Zone 3 (Tempo)': (0.70, 0.80),     # 70-80% of max HR
            'Zone 4 (Threshold)': (0.80, 0.90),  # 80-90% of max HR
            'Zone 5 (Maximum)': (0.90, 1.0)     # 90-100% of max HR
        }
        
        # Define power zones (based on FTP)
        self.power_zones = {
            'Zone 1 (Recovery)': (0, 0.55),     # Up to 55% of FTP
            'Zone 2 (Endurance)': (0.56, 0.75), # 56-75% of FTP
            'Zone 3 (Tempo)': (0.76, 0.90),     # 76-90% of FTP
            'Zone 4 (Threshold)': (0.91, 1.05),  # 91-105% of FTP
            'Zone 5 (VO2 Max)': (1.06, 1.5)     # Above 105% of FTP
        }
    
    def calculate_tss(self, normalized_power: float, duration_hours: float, ftp: float) -> float:
        """Calculate Training Stress Score (TSS)"""
        intensity_factor = safe_divide(normalized_power, ftp)
        return (duration_hours * normalized_power * intensity_factor * 100) / (ftp * 3600)

    
    def calculate_hr_zones(self, hr_data: List[int], max_hr: Optional[int] = None) -> Dict[str, float]:
        """Calculate time spent in each heart rate zone"""
        if not hr_data:
            return {}
        
        if not max_hr:
            try:
                max_hr = max(x for x in hr_data if x is not None)
            except ValueError:
                return {}
    
        hr_array = np.array([x for x in hr_data if x is not None])
        if len(hr_array) == 0:
            return {}
            
        total_samples = len(hr_array)
        zones = {}
        
        for zone_name, (lower, upper) in self.hr_zones.items():
            lower_bound = max_hr * lower
            upper_bound = max_hr * upper
            time_in_zone = np.sum((hr_array >= lower_bound) & (hr_array < upper_bound))
            zones[zone_name] = safe_divide(time_in_zone * 100, total_samples)
        
        return zones
    
    def parse_fit_file(self, file_content: bytes, athlete_ftp: Optional[float] = None) -> Dict[str, Any]:
        """Parse a .fit.gz file and extract relevant metrics"""
        try:
            # Decompress if gzipped
            try:
                decompressed = gzip.decompress(file_content)
            except:
                decompressed = file_content
            
            fitfile = FitFile(decompressed)
            
            # Data containers
            timestamps = []
            power_data = []
            hr_data = []
            cadence_data = []
            
            # Extract data
            for record in fitfile.get_messages('record'):
                data = record.get_values()
                if 'timestamp' in data:
                    timestamps.append(data['timestamp'])
                if 'power' in data:
                    power_data.append(convert_numpy(data['power']))
                if 'heart_rate' in data:
                    hr_data.append(convert_numpy(data['heart_rate']))
                if 'cadence' in data:
                    cadence_data.append(convert_numpy(data['cadence']))
            
            # Calculate duration
            if timestamps:
                duration_seconds = (timestamps[-1] - timestamps[0]).total_seconds()
                duration_hours = duration_seconds / 3600
            else:
                duration_hours = 0
            
            # Process power data
            power_metrics = None
            if power_data:
                power_array = np.array(power_data)
                
                # Estimate FTP if not provided
                ftp = athlete_ftp if athlete_ftp else float(np.percentile(power_array, 95))
                
                # Calculate normalized power
                rolling_avg = np.convolve(power_array, np.ones(30)/30, mode='valid')
                rolling_avg_4th = np.power(rolling_avg, 4)
                normalized_power = float(np.power(np.mean(rolling_avg_4th), 0.25))
                
                # Calculate TSS
                tss = self.calculate_tss(normalized_power, duration_hours, ftp)
                
                power_metrics = {
                    'average_power': float(np.mean(power_array)),
                    'normalized_power': normalized_power,
                    'max_power': float(np.max(power_array)),
                    'intensity_factor': float(normalized_power / ftp) if ftp > 0 else None,
                    'tss': float(tss),
                    'zones': self._calculate_power_zones(power_array, ftp)
                }
            
            # Process heart rate data
            hr_metrics = None
            if hr_data:
                hr_array = np.array(hr_data)
                hr_metrics = {
                    'average_hr': float(np.mean(hr_array)),
                    'max_hr': float(np.max(hr_array)),
                    'min_hr': float(np.min(hr_array)),
                    'zones': self.calculate_hr_zones(hr_data)
                }
            
            return {
                'start_time': timestamps[0].isoformat() if timestamps else None,
                'duration_hours': duration_hours,
                'power_metrics': power_metrics,
                'hr_metrics': hr_metrics,
                'metrics': {
                    'tss': power_metrics['tss'] if power_metrics else None,
                    'duration': duration_hours * 60,  # Convert to minutes
                    'intensity': power_metrics['intensity_factor'] if power_metrics else None,
                }
            }
            
        except Exception as e:
            print(f"Error parsing FIT file: {str(e)}")
            return None
    
    def _calculate_power_zones(self, power_array: np.ndarray, ftp: float) -> Dict[str, float]:
        """Calculate time spent in each power zone"""
        if len(power_array) == 0:
            return {}
            
        # Filter out None values
        power_array = np.array([x for x in power_array if x is not None])
        if len(power_array) == 0:
            return {}
            
        total_points = len(power_array)
        zones = {}
        
        for zone_name, (lower, upper) in self.power_zones.items():
            zone_points = np.sum((power_array >= ftp * lower) & (power_array < ftp * upper))
            zones[zone_name] = safe_divide(zone_points * 100, total_points)
        
        return zones