# src/utils/fit_parser.py

import gzip
from fitparse import FitFile
from typing import Dict, Any, List, Optional, cast
import numpy as np
import os

def convert_numpy(obj: Any) -> Any:
    """Convert numpy types to Python native types"""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj

def safe_divide(a: Any, b: Any, default: float = 0.0) -> float:
    """Safely divide two numbers with fallback to default. Coerces inputs to floats."""
    try:
        if a is None or b is None:
            return default
        a_f = float(a)
        b_f = float(b)
        if b_f == 0:
            return default
        return a_f / b_f
    except Exception:
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
        """Calculate time spent in each heart rate zone as a percentage of total workout duration"""
        if not hr_data:
            return {}

        # Allow override of HR zone boundaries via environment variable ATHLETE_HR_ZONES
        # Expected format: comma-separated upper bounds for zones 1..5, e.g. "138,156,165,173,200"
        env_zones = os.environ.get('ATHLETE_HR_ZONES')
        hr_array = np.array([x for x in hr_data if x is not None])
        if len(hr_array) == 0:
            return {}

        total_samples = len(hr_array)
        zones = {}

        if env_zones:
            try:
                bounds = [int(b.strip()) for b in env_zones.split(',') if b.strip()]
                # Expect 5 bounds (upper bound of each zone). If fewer provided, fall back to default behavior.
                if len(bounds) >= 5:
                    # Create zone ranges from bounds: zone1: <=bounds[0], zone2: (bounds[0], bounds[1]], ...
                    lower = None
                    # Use the same named keys as self.hr_zones for consistency
                    zone_names = list(self.hr_zones.keys())
                    for idx, upper in enumerate(bounds[:5]):
                        try:
                            if lower is None:
                                # zone 1
                                time_in_zone = np.sum(hr_array <= upper)
                            else:
                                time_in_zone = np.sum((hr_array > lower) & (hr_array <= upper))
                        except Exception:
                            time_in_zone = 0
                        name = zone_names[idx] if idx < len(zone_names) else f'Zone {idx+1}'
                        zones[name] = safe_divide(float(time_in_zone) * 100.0, float(total_samples))
                        lower = upper
                    return zones
            except Exception:
                # If parsing fails, fall back to percentage-of-max behavior below
                pass

        # Fallback: use percentage-of-max HR ranges defined in self.hr_zones
        if not max_hr:
            try:
                max_hr = int(max(x for x in hr_data if x is not None))
            except Exception:
                return {}

        for zone_name, (lower, upper) in self.hr_zones.items():
            lower_bound = max_hr * lower
            upper_bound = max_hr * upper
            time_in_zone = np.sum((hr_array >= lower_bound) & (hr_array < upper_bound))
            zones[zone_name] = safe_divide(float(time_in_zone) * 100.0, float(total_samples))

        return zones
    
    def parse_fit_file(self, file_content: bytes, athlete_ftp: Optional[float] = None) -> Optional[Dict[str, Any]]:
        """Parse a .fit.gz file and extract relevant metrics"""
        try:
            # Decompress if gzipped
            try:
                decompressed = gzip.decompress(file_content)
            except Exception:
                decompressed = file_content
            
            fitfile = FitFile(decompressed)
            
            # Data containers
            timestamps = []
            power_data = []
            hr_data = []
            cadence_data = []
            
            # Extract data
            for record in fitfile.get_messages('record'):
                # fitparse message objects sometimes expose get_values(); be defensive for typing
                try:
                    data_raw = cast(Any, record).get_values()
                except Exception:
                    try:
                        data_raw = dict(cast(Any, record))
                    except Exception:
                        data_raw = {}

                # Normalize keys to strings to satisfy static type checkers and unify access
                try:
                    if isinstance(data_raw, dict):
                        data = {str(k): v for k, v in data_raw.items()}
                    else:
                        data = {}
                except Exception:
                    data = {}

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
                # CRITICAL: Filter out None values BEFORE creating array
                power_data_filtered = [x for x in power_data if x is not None and x > 0]
                
                if not power_data_filtered:
                    print("DEBUG: No valid power data after filtering")
                else:
                    power_array = np.array(power_data_filtered)
                    print(f"DEBUG: Processing power data - {len(power_array)} data points")
                
                # Estimate FTP if not provided. Allow override via ATHLETE_FTP env var.
                env_ftp = None
                try:
                    env_val = os.environ.get('ATHLETE_FTP')
                    env_ftp = float(env_val) if env_val else None
                except Exception:
                    env_ftp = None

                ftp = athlete_ftp or env_ftp or float(np.percentile(power_array, 95))
                print(f"DEBUG: Using FTP of {ftp:.1f} watts")
                
                # Calculate normalized power with improved algorithm for outdoor rides
                # Use 30-second rolling average, but handle edge cases better
                if len(power_array) >= 30:
                    # Standard 30-second rolling average
                    rolling_avg = np.convolve(power_array, np.ones(30)/30, mode='valid')
                    print(f"DEBUG: Calculated {len(rolling_avg)} rolling averages")
                else:
                    # For very short workouts, use the entire array
                    rolling_avg = power_array
                    print(f"DEBUG: Using entire power array for short workout ({len(power_array)} points)")
                
                # Calculate 4th power average (standard normalized power formula)
                rolling_avg_4th = np.power(rolling_avg, 4)
                normalized_power = float(np.power(np.mean(rolling_avg_4th), 0.25))
                
                # Additional validation for outdoor rides
                # If normalized power seems unreasonable (too high/low), use average power as fallback
                avg_power = float(np.mean(power_array))
                if normalized_power > avg_power * 1.5 or normalized_power < avg_power * 0.5:
                    print(f"Warning: Normalized power ({normalized_power:.1f}) seems unreasonable compared to average power ({avg_power:.1f})")
                    print("Using average power as normalized power for outdoor ride")
                    normalized_power = avg_power
                
                print(f"DEBUG: Final normalized power: {normalized_power:.1f} watts")
                
                # Calculate TSS
                tss = self.calculate_tss(normalized_power, duration_hours, ftp)
                
                power_metrics = {
                    'average_power': float(np.mean(power_array)),
                    'normalized_power': normalized_power,
                    'max_power': float(np.max(power_array)),
                    'intensity_factor': float(normalized_power / ftp) if ftp > 0 else None,
                    'tss': float(tss),
                    'zones': self._calculate_power_zones(power_array, ftp),
                    # Include the raw power series and the FTP used so callers can recompute zones later
                    'power_series': convert_numpy(power_array),
                    'ftp': float(ftp)
                }
            
            # Process heart rate data
            hr_metrics = None
            if hr_data:
                # CRITICAL: Filter out None values BEFORE creating array
                hr_data_filtered = [x for x in hr_data if x is not None and x > 0]
                
                if not hr_data_filtered:
                    print("DEBUG: No valid heart rate data after filtering")
                else:
                    hr_array = np.array(hr_data_filtered)
                    hr_metrics = {
                        'average_hr': float(np.mean(hr_array)),
                        'max_hr': float(np.max(hr_array)),
                        'min_hr': float(np.min(hr_array)),
                        'zones': self.calculate_hr_zones(hr_data_filtered)  # Use filtered data
                    }
            # Detect sport type from session data
            sport = None
            try:
                for session in fitfile.get_messages('session'):
                    try:
                        session_raw = cast(Any, session).get_values()
                    except Exception:
                        try:
                            session_raw = dict(cast(Any, session))
                        except Exception:
                            session_raw = {}

                    try:
                        if isinstance(session_raw, dict):
                            session_data = {str(k): v for k, v in session_raw.items()}
                        else:
                            session_data = {}
                    except Exception:
                        session_data = {}

                    if 'sport' in session_data:
                        sport = str(session_data['sport']).lower()
                        print(f"DEBUG: Detected sport: {sport}")
                        break
            except Exception as e:
                print(f"DEBUG: Could not detect sport: {e}")
            return {
                'sport': sport,
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
        """Calculate time spent in each power zone as a percentage of total workout duration"""
        if len(power_array) == 0:
            return {}
            
        # Filter out None values
        power_array = np.array([x for x in power_array if x is not None])
        if len(power_array) == 0:
            return {}
            
        total_points = len(power_array)
        zones = {}
        
        # Allow explicit power zone upper bounds via ATHLETE_POWER_ZONES (comma-separated watt values)
        env_pzones = os.environ.get('ATHLETE_POWER_ZONES')
        if env_pzones:
            try:
                bounds = [float(b.strip()) for b in env_pzones.split(',') if b.strip()]
                if len(bounds) >= 5:
                    lower = None
                    zone_names = list(self.power_zones.keys())
                    for idx, upper in enumerate(bounds[:5]):
                        try:
                            if lower is None:
                                zone_points = np.sum(power_array <= upper)
                            else:
                                zone_points = np.sum((power_array > lower) & (power_array <= upper))
                        except Exception:
                            zone_points = 0
                        name = zone_names[idx] if idx < len(zone_names) else f'Zone {idx+1} (Custom)'
                        zones[name] = safe_divide(float(zone_points) * 100.0, float(total_points))
                        lower = upper
                    return zones
            except Exception:
                # If parsing fails, fall back to percentage-of-FTP behavior below
                pass

        for zone_name, (lower, upper) in self.power_zones.items():
            zone_points = np.sum((power_array >= ftp * lower) & (power_array < ftp * upper))
            zones[zone_name] = safe_divide(float(zone_points) * 100.0, float(total_points))
        
        return zones