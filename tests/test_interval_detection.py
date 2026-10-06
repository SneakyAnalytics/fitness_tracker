"""
Unit Tests for Interval Detection

Tests the automatic interval detection and classification logic
with synthetic workout data.

Run with: pytest tests/test_interval_detection.py -v

Author: Fitness Tracker
Created: January 1, 2026
"""

import pytest
import numpy as np
from src.utils.interval_detector import IntervalDetector
from src.utils.interval_classifier import IntervalClassifier


class TestIntervalDetector:
    """Test suite for IntervalDetector"""
    
    @pytest.fixture
    def detector(self):
        """Create detector with FTP of 300W"""
        return IntervalDetector(ftp=300, weight_kg=75)
    
    def test_zone_classification(self, detector):
        """Test power zone classification"""
        assert detector.classify_zone(100) == 'Z1'  # 33% FTP
        assert detector.classify_zone(180) == 'Z2'  # 60% FTP
        assert detector.classify_zone(240) == 'Z3'  # 80% FTP
        assert detector.classify_zone(285) == 'Z4'  # 95% FTP
        assert detector.classify_zone(315) == 'Z5'  # 105% FTP
        assert detector.classify_zone(400) == 'Z6'  # 133% FTP
    
    def test_rolling_average(self, detector):
        """Test rolling average calculation"""
        data = [100, 200, 300, 200, 100]
        result = detector.calculate_rolling_average(data, 3)
        
        # First window: (100+200+300)/3 = 200
        # Second window: (200+300+200)/3 = 233.33
        # Third window: (300+200+100)/3 = 200
        assert len(result) == 3
        assert result[0] == pytest.approx(200, abs=1)
        assert result[1] == pytest.approx(233, abs=1)
        assert result[2] == pytest.approx(200, abs=1)
    
    def test_normalized_power(self, detector):
        """Test normalized power calculation"""
        # Steady power should equal NP
        steady_power = [250] * 300  # 5 minutes at 250W
        np_steady = detector.calculate_normalized_power(steady_power)
        assert np_steady == pytest.approx(250, abs=5)
        
        # Variable power should have higher NP
        variable_power = ([200] * 30 + [350] * 30) * 5  # Alternating 200W and 350W
        np_variable = detector.calculate_normalized_power(variable_power)
        avg_variable = np.mean(variable_power)
        assert np_variable > avg_variable  # NP should be higher than average
    
    def test_simple_interval_detection(self, detector):
        """Test detection of simple warmup-work-cooldown structure"""
        # Create synthetic workout:
        # 10min warmup @ 150W (Z2)
        # 20min work @ 285W (Z4)
        # 5min cooldown @ 120W (Z1)
        
        power_stream = (
            [150] * (10 * 60) +  # Warmup
            [285] * (20 * 60) +  # Work
            [120] * (5 * 60)     # Cooldown
        )
        
        result = detector.detect_intervals(power_stream)
        
        assert result['interval_count'] >= 2  # At least warmup/rest and work
        assert result['ftp_used'] == 300
        
        intervals = result['intervals']
        
        # Check that work interval was detected
        work_intervals = [i for i in intervals if i['type'] == 'work']
        assert len(work_intervals) >= 1
        
        # Check work interval properties
        main_work = work_intervals[0]
        assert main_work['intensity_zone'] == 'Z4'
        assert main_work['avg_power'] == pytest.approx(285, abs=5)
        assert main_work['duration_sec'] >= 20 * 60 - 60  # Allow 1min tolerance
    
    def test_interval_workout_detection(self, detector):
        """Test detection of structured interval workout"""
        # Create 4x5min @ 320W with 3min recoveries
        power_stream = []
        power_stream += [150] * (10 * 60)  # Warmup
        
        for i in range(4):
            power_stream += [320] * (5 * 60)   # Work
            if i < 3:  # No recovery after last interval
                power_stream += [140] * (3 * 60)  # Recovery
        
        power_stream += [120] * (5 * 60)  # Cooldown
        
        result = detector.detect_intervals(power_stream)
        intervals = result['intervals']
        
        # Should detect 4 work intervals
        work_intervals = [i for i in intervals if i['type'] == 'work']
        assert len(work_intervals) >= 3  # At least 3 of 4 (allow for detection variance)
        
        # Check work interval properties
        for work in work_intervals:
            assert work['intensity_zone'] in ['Z5', 'Z6']  # 320W is Z5 for 300W FTP
            assert 4 * 60 <= work['duration_sec'] <= 6 * 60  # ~5 minutes
    
    def test_empty_power_stream(self, detector):
        """Test handling of empty power data"""
        result = detector.detect_intervals([])
        assert result['interval_count'] == 0
        assert result['intervals'] == []
    
    def test_short_workout(self, detector):
        """Test handling of very short workout"""
        # 20 seconds of data (too short for interval detection)
        power_stream = [200] * 20
        result = detector.detect_intervals(power_stream)
        
        # Should handle gracefully without crashing
        assert 'interval_count' in result


class TestIntervalClassifier:
    """Test suite for IntervalClassifier"""
    
    @pytest.fixture
    def classifier(self):
        """Create classifier with FTP of 300W"""
        return IntervalClassifier(ftp=300)
    
    @pytest.fixture
    def detector(self):
        """Create detector for generating test intervals"""
        return IntervalDetector(ftp=300, weight_kg=75)
    
    def test_warmup_detection(self, classifier):
        """Test warmup interval detection"""
        interval = {
            'id': 1,
            'type': 'rest',
            'start_time': 0,
            'end_time': 600,
            'duration_sec': 600,
            'avg_power': 150,
            'intensity_zone': 'Z2'
        }
        
        # First interval at low intensity should be warmup
        assert classifier.is_warmup(interval, 3000, 0) == True
        
        # Same interval later in workout should not be warmup
        assert classifier.is_warmup(interval, 3000, 5) == False
    
    def test_cooldown_detection(self, classifier):
        """Test cooldown interval detection"""
        interval = {
            'id': 10,
            'type': 'rest',
            'start_time': 2700,  # 45min into workout
            'end_time': 3000,    # 50min total
            'duration_sec': 300,
            'avg_power': 120,
            'intensity_zone': 'Z1'
        }
        
        # Last interval at low intensity should be cooldown
        assert classifier.is_cooldown(interval, 3000, 9, 10) == True
        
        # Same interval early in workout should not be cooldown
        assert classifier.is_cooldown(interval, 3000, 2, 10) == False
    
    def test_sprint_classification(self, classifier):
        """Test sprint interval classification"""
        interval = {
            'duration_sec': 15,
            'avg_power': 500,
            'intensity_zone': 'Z6',
            'percent_ftp': 167
        }
        
        result = classifier.classify_work_interval(interval, 3000)
        assert result == 'sprint'
    
    def test_vo2max_classification(self, classifier):
        """Test VO2max interval classification"""
        interval = {
            'duration_sec': 5 * 60,  # 5 minutes
            'avg_power': 330,
            'intensity_zone': 'Z5',
            'percent_ftp': 110
        }
        
        result = classifier.classify_work_interval(interval, 3000)
        assert result == 'vo2max'
    
    def test_threshold_classification(self, classifier):
        """Test threshold interval classification"""
        interval = {
            'duration_sec': 15 * 60,  # 15 minutes
            'avg_power': 290,
            'intensity_zone': 'Z4',
            'percent_ftp': 97
        }
        
        result = classifier.classify_work_interval(interval, 3000)
        assert result == 'threshold'
    
    def test_steady_state_classification(self, classifier):
        """Test steady state classification"""
        interval = {
            'duration_sec': 25 * 60,  # 25 minutes
            'avg_power': 220,
            'intensity_zone': 'Z2',
            'percent_ftp': 73
        }
        
        result = classifier.classify_work_interval(interval, 3000)
        assert result == 'steady_state'
    
    def test_full_workout_classification(self, classifier, detector):
        """Test classification of complete workout"""
        # Create structured workout
        power_stream = (
            [150] * (10 * 60) +   # Warmup
            [320] * (5 * 60) +    # VO2max work
            [140] * (3 * 60) +    # Recovery
            [320] * (5 * 60) +    # VO2max work
            [140] * (3 * 60) +    # Recovery
            [320] * (5 * 60) +    # VO2max work
            [120] * (5 * 60)      # Cooldown
        )
        
        # Detect intervals
        intervals_data = detector.detect_intervals(power_stream)
        
        # Classify intervals
        classified = classifier.classify_intervals(intervals_data)
        
        # Check summary
        assert 'summary' in classified
        summary = classified['summary']
        
        # Should have warmup
        assert summary['warmup_count'] >= 1
        
        # Should have work intervals
        assert summary['work_intervals'] >= 3
        
        # Should have cooldown
        assert summary['cooldown_count'] >= 1
    
    def test_workout_description(self, classifier, detector):
        """Test human-readable workout description"""
        # Simple threshold workout
        power_stream = (
            [150] * (10 * 60) +   # Warmup
            [290] * (20 * 60) +   # Threshold work
            [120] * (5 * 60)      # Cooldown
        )
        
        intervals_data = detector.detect_intervals(power_stream)
        classified = classifier.classify_intervals(intervals_data)
        
        description = classifier.describe_workout_structure(classified)
        
        # Should mention key components
        assert isinstance(description, str)
        assert len(description) > 0


class TestIntegration:
    """Integration tests for complete detection pipeline"""
    
    def test_real_world_threshold_workout(self):
        """Test detection on realistic 2x18min threshold workout"""
        detector = IntervalDetector(ftp=305, weight_kg=75)
        classifier = IntervalClassifier(ftp=305)
        
        # Create realistic 2x18min threshold workout
        power_stream = []
        
        # 12min warmup with gradual increase
        for i in range(12 * 60):
            power = 120 + (i / (12 * 60)) * 80  # 120W → 200W
            power_stream.append(power)
        
        # First 18min interval @ 290W with some variability
        for i in range(18 * 60):
            power = 290 + np.random.randint(-10, 10)
            power_stream.append(power)
        
        # 5min recovery @ 150W
        power_stream += [150 + np.random.randint(-5, 5) for _ in range(5 * 60)]
        
        # Second 18min interval @ 285W (slight fatigue)
        for i in range(18 * 60):
            power = 285 + np.random.randint(-10, 10)
            power_stream.append(power)
        
        # 8min cooldown with gradual decrease
        for i in range(8 * 60):
            power = 160 - (i / (8 * 60)) * 40  # 160W → 120W
            power_stream.append(power)
        
        # Detect and classify
        intervals_data = detector.detect_intervals(power_stream)
        classified = classifier.classify_intervals(intervals_data)
        
        # Validate structure
        assert classified['interval_count'] >= 4  # warmup, work, recovery, work, cooldown
        
        # Check for threshold intervals
        intervals = classified['intervals']
        threshold_intervals = [i for i in intervals if 'threshold' in i['type']]
        
        assert len(threshold_intervals) >= 2  # Should detect both work intervals
        
        # Check first threshold interval
        first_threshold = threshold_intervals[0]
        assert 16 * 60 <= first_threshold['duration_sec'] <= 20 * 60  # ~18 minutes
        assert first_threshold['avg_power'] >= 280  # Should average around 290W
        assert first_threshold['intensity_zone'] == 'Z4'
        
        # Check description
        description = classifier.describe_workout_structure(classified)
        assert 'threshold' in description.lower()
        assert 'warmup' in description.lower() or 'cooldown' in description.lower()
    
    def test_unstructured_group_ride(self):
        """Test detection on unstructured group ride (highly variable power)"""
        detector = IntervalDetector(ftp=300)
        classifier = IntervalClassifier(ftp=300)
        
        # Create variable power profile simulating group ride
        power_stream = []
        
        for minute in range(90):  # 90 minute ride
            # Random surges and lulls
            if np.random.random() < 0.1:  # 10% chance of surge
                power_stream += [350 + np.random.randint(-20, 20) for _ in range(60)]
            elif np.random.random() < 0.2:  # 20% chance of recovery
                power_stream += [120 + np.random.randint(-10, 10) for _ in range(60)]
            else:  # Steady endurance pace
                power_stream += [220 + np.random.randint(-15, 15) for _ in range(60)]
        
        # Detect intervals
        intervals_data = detector.detect_intervals(power_stream)
        classified = classifier.classify_intervals(intervals_data)
        
        # Should detect multiple intervals due to variability
        assert classified['interval_count'] > 0
        
        # Description should indicate unstructured or multiple intervals
        description = classifier.describe_workout_structure(classified)
        assert len(description) > 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
