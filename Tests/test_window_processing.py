"""
Test Window Processing - High Severity Issues
===============================================

Tests for window creation, quality calculation, and edge cases.

ISSUE CATEGORY: VERY HIGH SEVERITY
- Empty window handling
- Very short data that can't form windows
- Window overlap edge cases
"""

import pytest
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "HV_Analyze_Pro"))


class TestWindowManager:
    """Test WindowManager for edge cases and potential crashes."""
    
    def test_create_windows_normal(self, synthetic_seismic_data):
        """Normal case - should work without issues."""
        from hvsr_pro.processing.windows import WindowManager
        
        manager = WindowManager(window_length=10.0, overlap=0.5)
        windows = manager.create_windows(synthetic_seismic_data, calculate_quality=True)
        
        assert windows.n_windows > 0, "Should create windows from valid data"
        assert windows.n_active > 0, "Some windows should be active"
    
    def test_create_windows_with_very_short_data(self, very_short_data):
        """
        ISSUE: Data shorter than window length.
        SEVERITY: VERY HIGH
        EXPECTED: Should handle gracefully, not crash.
        """
        from hvsr_pro.processing.windows import WindowManager
        
        manager = WindowManager(window_length=10.0, overlap=0.5)
        
        try:
            windows = manager.create_windows(very_short_data, calculate_quality=True)
            print(f"FINDING: Very short data created {windows.n_windows} windows")
            # If it creates 0 windows, that's acceptable behavior
        except ValueError as e:
            print(f"FINDING: Very short data raises ValueError: {e}")
            # This is expected behavior
        except Exception as e:
            pytest.fail(f"Unexpected exception with very short data: {type(e).__name__}: {e}")
    
    def test_create_windows_with_zero_overlap(self, synthetic_seismic_data):
        """
        ISSUE: Zero overlap parameter.
        SEVERITY: MEDIUM
        """
        from hvsr_pro.processing.windows import WindowManager
        
        manager = WindowManager(window_length=10.0, overlap=0.0)
        windows = manager.create_windows(synthetic_seismic_data, calculate_quality=True)
        
        assert windows.n_windows > 0, "Should create windows with zero overlap"
    
    def test_create_windows_with_full_overlap(self, synthetic_seismic_data):
        """
        ISSUE: 100% overlap (overlap=1.0) - edge case.
        SEVERITY: HIGH
        """
        from hvsr_pro.processing.windows import WindowManager
        
        try:
            manager = WindowManager(window_length=10.0, overlap=1.0)
            windows = manager.create_windows(synthetic_seismic_data, calculate_quality=True)
            print(f"FINDING: 100% overlap created {windows.n_windows} windows")
        except ValueError as e:
            print(f"FINDING: 100% overlap raises ValueError: {e}")
        except ZeroDivisionError as e:
            pytest.fail(f"CRITICAL: 100% overlap causes ZeroDivisionError: {e}")
    
    def test_create_windows_with_negative_overlap(self, synthetic_seismic_data):
        """
        ISSUE: Negative overlap parameter.
        SEVERITY: HIGH
        """
        from hvsr_pro.processing.windows import WindowManager
        
        try:
            manager = WindowManager(window_length=10.0, overlap=-0.5)
            windows = manager.create_windows(synthetic_seismic_data, calculate_quality=True)
            print(f"FINDING: Negative overlap created {windows.n_windows} windows")
        except ValueError as e:
            print(f"FINDING: Negative overlap correctly raises ValueError: {e}")
    
    def test_create_windows_with_zero_window_length(self, synthetic_seismic_data):
        """
        ISSUE: Zero window length.
        SEVERITY: VERY HIGH
        """
        from hvsr_pro.processing.windows import WindowManager
        
        try:
            manager = WindowManager(window_length=0.0, overlap=0.5)
            windows = manager.create_windows(synthetic_seismic_data, calculate_quality=True)
            pytest.fail("Zero window length should raise an error")
        except (ValueError, ZeroDivisionError) as e:
            print(f"FINDING: Zero window length correctly raises {type(e).__name__}: {e}")
    
    def test_create_windows_with_negative_window_length(self, synthetic_seismic_data):
        """
        ISSUE: Negative window length.
        SEVERITY: VERY HIGH
        """
        from hvsr_pro.processing.windows import WindowManager
        
        try:
            manager = WindowManager(window_length=-10.0, overlap=0.5)
            windows = manager.create_windows(synthetic_seismic_data, calculate_quality=True)
            pytest.fail("Negative window length should raise an error")
        except ValueError as e:
            print(f"FINDING: Negative window length correctly raises ValueError: {e}")
    
    def test_window_length_equals_data_length(self, synthetic_seismic_data):
        """
        ISSUE: Window length exactly equals data duration.
        SEVERITY: MEDIUM
        """
        from hvsr_pro.processing.windows import WindowManager
        
        data_duration = synthetic_seismic_data.duration
        manager = WindowManager(window_length=data_duration, overlap=0.5)
        
        windows = manager.create_windows(synthetic_seismic_data, calculate_quality=True)
        print(f"FINDING: Window = data length created {windows.n_windows} windows")
    
    def test_window_length_exceeds_data_length(self, synthetic_seismic_data):
        """
        ISSUE: Window length exceeds data duration.
        SEVERITY: VERY HIGH
        """
        from hvsr_pro.processing.windows import WindowManager
        
        data_duration = synthetic_seismic_data.duration
        manager = WindowManager(window_length=data_duration * 2, overlap=0.5)
        
        try:
            windows = manager.create_windows(synthetic_seismic_data, calculate_quality=True)
            print(f"FINDING: Window > data created {windows.n_windows} windows")
        except ValueError as e:
            print(f"FINDING: Window > data raises ValueError: {e}")


class TestWindowQualityCalculator:
    """Test quality metric calculations for edge cases."""
    
    def test_quality_with_zero_data(self):
        """
        ISSUE: Quality calculation with all-zero data.
        SEVERITY: HIGH
        """
        from hvsr_pro.core.data_structures import SeismicData, ComponentData
        from hvsr_pro.processing.windows.structures import Window
        from hvsr_pro.processing.windows.quality import WindowQualityCalculator
        
        sampling_rate = 100.0
        n_samples = 1000
        zero_data = np.zeros(n_samples)
        
        east = ComponentData(name='E', data=zero_data + 1e-10, sampling_rate=sampling_rate)
        north = ComponentData(name='N', data=zero_data + 1e-10, sampling_rate=sampling_rate)
        vertical = ComponentData(name='Z', data=zero_data + 1e-10, sampling_rate=sampling_rate)
        
        data = SeismicData(east=east, north=north, vertical=vertical)
        
        window = Window(
            index=0,
            start_sample=0,
            end_sample=n_samples,
            data=data
        )
        
        calculator = WindowQualityCalculator()
        
        try:
            metrics = calculator.calculate_all(window)
            print(f"FINDING: Zero data quality metrics: {metrics}")
            
            # Check for NaN or Inf
            for metric, value in metrics.items():
                assert np.isfinite(value), f"Metric '{metric}' is not finite: {value}"
        except ZeroDivisionError as e:
            pytest.fail(f"CRITICAL: Zero data causes ZeroDivisionError: {e}")
        except Exception as e:
            print(f"FINDING: Zero data quality raises {type(e).__name__}: {e}")
    
    def test_quality_with_constant_data(self):
        """
        ISSUE: Quality calculation with constant (non-varying) data.
        SEVERITY: MEDIUM
        """
        from hvsr_pro.core.data_structures import SeismicData, ComponentData
        from hvsr_pro.processing.windows.structures import Window
        from hvsr_pro.processing.windows.quality import WindowQualityCalculator
        
        sampling_rate = 100.0
        n_samples = 1000
        constant_data = np.ones(n_samples) * 5.0
        
        east = ComponentData(name='E', data=constant_data, sampling_rate=sampling_rate)
        north = ComponentData(name='N', data=constant_data, sampling_rate=sampling_rate)
        vertical = ComponentData(name='Z', data=constant_data, sampling_rate=sampling_rate)
        
        data = SeismicData(east=east, north=north, vertical=vertical)
        
        window = Window(
            index=0,
            start_sample=0,
            end_sample=n_samples,
            data=data
        )
        
        calculator = WindowQualityCalculator()
        metrics = calculator.calculate_all(window)
        
        print(f"FINDING: Constant data quality metrics: {metrics}")
        
        # All metrics should be finite
        for metric, value in metrics.items():
            assert np.isfinite(value), f"Metric '{metric}' is not finite: {value}"


class TestWindowCollection:
    """Test WindowCollection methods for edge cases."""
    
    def test_get_active_windows_when_all_rejected(self, synthetic_seismic_data):
        """
        ISSUE: get_active_windows when all windows are rejected.
        SEVERITY: VERY HIGH
        """
        from hvsr_pro.processing.windows import WindowManager
        
        manager = WindowManager(window_length=10.0, overlap=0.5)
        windows = manager.create_windows(synthetic_seismic_data, calculate_quality=True)
        
        # Reject all windows
        for window in windows.windows:
            window.reject("Test rejection", manual=True)
        
        active = windows.get_active_windows()
        
        assert len(active) == 0, "Should return empty list when all rejected"
        assert windows.n_active == 0, "n_active should be 0"
        assert windows.acceptance_rate == 0.0, "Acceptance rate should be 0"
    
    def test_window_statistics_with_no_windows(self):
        """
        ISSUE: Statistics on empty WindowCollection.
        SEVERITY: HIGH
        """
        from hvsr_pro.processing.windows.structures import WindowCollection
        from hvsr_pro.core.data_structures import SeismicData, ComponentData
        
        # WindowCollection requires source_data, window_length, overlap
        # Create minimal valid SeismicData
        n_samples = 100
        sampling_rate = 100.0
        east = ComponentData(name='E', data=np.random.randn(n_samples), sampling_rate=sampling_rate)
        north = ComponentData(name='N', data=np.random.randn(n_samples), sampling_rate=sampling_rate)
        vertical = ComponentData(name='Z', data=np.random.randn(n_samples), sampling_rate=sampling_rate)
        source_data = SeismicData(east=east, north=north, vertical=vertical)
        
        collection = WindowCollection(windows=[], source_data=source_data, window_length=10.0, overlap=0.5)
        
        assert collection.n_windows == 0
        assert collection.n_active == 0
        
        # These should not crash
        active = collection.get_active_windows()
        assert len(active) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
