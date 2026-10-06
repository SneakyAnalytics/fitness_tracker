"""
Integration Test for Interval Detection

Tests the complete pipeline from FIT file parsing through interval detection.
Uses a synthetic workout to verify all components work together.

Run with: python tests/test_interval_integration.py

Author: Fitness Tracker
Created: January 1, 2026
"""

import numpy as np
from src.utils.interval_detector import IntervalDetector
from src.utils.interval_classifier import IntervalClassifier


def test_full_pipeline():
    """Test complete interval detection pipeline"""
    
    print("=" * 60)
    print("INTERVAL DETECTION INTEGRATION TEST")
    print("=" * 60)
    
    # Create synthetic 2x18min threshold workout
    print("\n1. Creating synthetic workout (2x18min @ threshold)...")
    
    ftp = 305
    power_series = []
    hr_series = []
    
    # 12min warmup (gradual increase from 120W to 200W)
    print("   - 12min warmup")
    for i in range(12 * 60):
        power = 120 + (i / (12 * 60)) * 80
        hr = 120 + (i / (12 * 60)) * 30
        power_series.append(power + np.random.randint(-5, 5))
        hr_series.append(int(hr + np.random.randint(-2, 2)))
    
    # First 18min interval @ 290W (95% FTP)
    print("   - 18min threshold #1 @ 290W")
    for i in range(18 * 60):
        power_series.append(290 + np.random.randint(-10, 10))
        hr_series.append(165 + np.random.randint(-3, 3))
    
    # 5min recovery @ 150W
    print("   - 5min recovery @ 150W")
    for i in range(5 * 60):
        power_series.append(150 + np.random.randint(-5, 5))
        hr_series.append(140 + np.random.randint(-2, 2))
    
    # Second 18min interval @ 285W (slight fatigue)
    print("   - 18min threshold #2 @ 285W")
    for i in range(18 * 60):
        power_series.append(285 + np.random.randint(-10, 10))
        hr_series.append(167 + np.random.randint(-3, 3))
    
    # 8min cooldown (gradual decrease from 160W to 120W)
    print("   - 8min cooldown")
    for i in range(8 * 60):
        power = 160 - (i / (8 * 60)) * 40
        hr = 150 - (i / (8 * 60)) * 30
        power_series.append(power + np.random.randint(-5, 5))
        hr_series.append(int(hr + np.random.randint(-2, 2)))
    
    total_duration = len(power_series) / 60
    print(f"\n   Total duration: {total_duration:.1f} minutes")
    print(f"   Data points: {len(power_series)}")
    
    # 2. Detect intervals
    print("\n2. Detecting intervals...")
    detector = IntervalDetector(ftp=ftp, weight_kg=75)
    intervals_data = detector.detect_intervals(
        power_stream=power_series,
        hr_stream=hr_series
    )
    
    print(f"   ✓ Detected {intervals_data['interval_count']} intervals")
    
    # 3. Classify intervals
    print("\n3. Classifying intervals...")
    classifier = IntervalClassifier(ftp=ftp)
    classified = classifier.classify_intervals(intervals_data)
    
    print(f"   ✓ Classification complete")
    
    # 4. Display results
    print("\n4. Results:")
    print("   " + "=" * 56)
    
    description = classified.get('description', 'Unknown structure')
    print(f"   Workout Structure: {description}")
    
    summary = classified.get('summary', {})
    print(f"\n   Summary:")
    print(f"     Total Intervals: {summary.get('total_intervals', 0)}")
    print(f"     Work Intervals:  {summary.get('work_intervals', 0)}")
    print(f"     Rest Periods:    {summary.get('rest_intervals', 0)}")
    print(f"     Warmup:          {summary.get('warmup_count', 0)}")
    print(f"     Cooldown:        {summary.get('cooldown_count', 0)}")
    
    # Show detailed breakdown
    print(f"\n   Interval Breakdown:")
    print("   " + "-" * 56)
    print("     #  Type             Duration    Avg Power  Zone  % FTP")
    print("   " + "-" * 56)
    
    for i, interval in enumerate(classified['intervals'], 1):
        mins = interval['duration_sec'] // 60
        secs = interval['duration_sec'] % 60
        duration_str = f"{mins:2d}:{secs:02d}"
        type_str = interval['type'].replace('_', ' ').title()
        
        print(f"     {i:2d} {type_str:16s} {duration_str:8s}  {int(interval['avg_power']):4d}W   "
              f"{interval['intensity_zone']:3s} {interval['percent_ftp']:5.1f}%")
    
    print("   " + "=" * 56)
    
    # 5. Validate detection
    print("\n5. Validation:")
    
    # Should have detected warmup
    warmup_intervals = [i for i in classified['intervals'] if i['type'] == 'warmup']
    assert len(warmup_intervals) >= 1, "Should detect warmup"
    print("   ✓ Warmup detected")
    
    # Should have detected threshold intervals
    threshold_intervals = [i for i in classified['intervals'] if 'threshold' in i['type']]
    assert len(threshold_intervals) >= 2, f"Should detect 2 threshold intervals (found {len(threshold_intervals)})"
    print(f"   ✓ {len(threshold_intervals)} threshold intervals detected")
    
    # Threshold intervals should be ~18 minutes
    for idx, interval in enumerate(threshold_intervals, 1):
        duration_min = interval['duration_sec'] / 60
        assert 16 <= duration_min <= 20, f"Threshold interval {idx} should be ~18 min (was {duration_min:.1f})"
        print(f"   ✓ Threshold {idx} duration: {duration_min:.1f} min")
    
    # Should have detected cooldown
    cooldown_intervals = [i for i in classified['intervals'] if i['type'] == 'cooldown']
    assert len(cooldown_intervals) >= 1, "Should detect cooldown"
    print("   ✓ Cooldown detected")
    
    # Should have detected recovery
    recovery_intervals = [i for i in classified['intervals'] if 'recovery' in i['type']]
    if len(recovery_intervals) > 0:
        print(f"   ✓ {len(recovery_intervals)} recovery period(s) detected")
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    
    return classified


if __name__ == '__main__':
    result = test_full_pipeline()
