"""
Test HVSR Processor - High Severity Issues
============================================

Tests for HVSRProcessor edge cases and pipeline failures.

ISSUE CATEGORY: VERY HIGH SEVERITY
- No windows pass processing
- All windows fail
- Empty results handling
"""

import pytest
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "HV_Analyze_Pro"))


class TestHVSRProcessor:
    """Test HVSRProcessor for edge cases and potential crashes."""
    
    def test_process_normal_data(self, synthetic_seismic_data):
        """Normal case - should work without issues."""
        from hvsr_pro.processing.windows import WindowManager
        from hvsr_pro.processing.hvsr import HVSRProcessor
        
        manager = WindowManager(window_length=10.0, overlap=0.5)
        windows = manager.create_windows(synthetic_seismic_data, calculate_quality=True)
        
        processor = HVSRProcessor(
            smoothing_bandwidth=40,
            smoothing_method='konno_ohmachi',
            f_min=0.2,
            f_max=20.0,
            n_frequencies=100
        )
        
        result = processor.process(windows, detect_peaks_flag=True)
        
        assert result is not None, "Should return a result"
        assert len(result.frequencies) == 100, "Should have 100 frequency points"
        assert len(result.mean_hvsr) == 100, "Mean HVSR should have 100 points"
    
    def test_process_with_zero_vertical(self, zero_vertical_data):
        """
        ISSUE: Processing data with zero vertical component.
        SEVERITY: VERY HIGH (division by zero)
        """
        from hvsr_pro.processing.windows import WindowManager
        from hvsr_pro.processing.hvsr import HVSRProcessor
        
        manager = WindowManager(window_length=10.0, overlap=0.5)
        
        try:
            windows = manager.create_windows(zero_vertical_data, calculate_quality=True)
            
            processor = HVSRProcessor(
                smoothing_bandwidth=40,
                f_min=0.2,
                f_max=20.0
            )
            
            result = processor.process(windows, detect_peaks_flag=True)
            
            # Check for infinite or NaN values
            has_nan = np.any(np.isnan(result.mean_hvsr))
            has_inf = np.any(np.isinf(result.mean_hvsr))
            
            print(f"FINDING: Zero vertical - NaN: {has_nan}, Inf: {has_inf}")
            print(f"FINDING: Max HVSR value: {np.max(result.mean_hvsr)}")
            
        except Exception as e:
            print(f"FINDING: Zero vertical raises {type(e).__name__}: {e}")
    
    def test_process_with_all_windows_rejected(self, synthetic_seismic_data):
        """
        ISSUE: All windows rejected before processing.
        SEVERITY: VERY HIGH
        """
        from hvsr_pro.processing.windows import WindowManager
        from hvsr_pro.processing.hvsr import HVSRProcessor
        
        manager = WindowManager(window_length=10.0, overlap=0.5)
        windows = manager.create_windows(synthetic_seismic_data, calculate_quality=True)
        
        # Reject all windows
        for window in windows.windows:
            window.reject("Test rejection", manual=True)
        
        processor = HVSRProcessor()
        
        try:
            result = processor.process(windows, detect_peaks_flag=True)
            pytest.fail("Should raise error when all windows rejected")
        except ValueError as e:
            print(f"FINDING: All windows rejected correctly raises: {e}")
    
    def test_process_with_single_window(self, synthetic_seismic_data):
        """
        ISSUE: Processing with only one window.
        SEVERITY: HIGH
        """
        from hvsr_pro.processing.windows import WindowManager
        from hvsr_pro.processing.hvsr import HVSRProcessor
        
        # Create windows, then keep only one active
        manager = WindowManager(window_length=10.0, overlap=0.5)
        windows = manager.create_windows(synthetic_seismic_data, calculate_quality=True)
        
        # Reject all but first window
        for i, window in enumerate(windows.windows):
            if i > 0:
                window.reject("Keep only first", manual=True)
        
        processor = HVSRProcessor()
        
        try:
            result = processor.process(windows, detect_peaks_flag=True)
            print(f"FINDING: Single window processing succeeded")
            print(f"FINDING: Std HVSR: {np.mean(result.std_hvsr)}")  # Should be 0 with single window
        except Exception as e:
            print(f"FINDING: Single window raises {type(e).__name__}: {e}")
    
    def test_process_invalid_smoothing_method(self, synthetic_seismic_data):
        """
        ISSUE: Invalid smoothing method name.
        SEVERITY: MEDIUM
        """
        from hvsr_pro.processing.windows import WindowManager
        from hvsr_pro.processing.hvsr import HVSRProcessor
        
        manager = WindowManager(window_length=10.0, overlap=0.5)
        windows = manager.create_windows(synthetic_seismic_data, calculate_quality=True)
        
        try:
            processor = HVSRProcessor(smoothing_method='invalid_method')
            pytest.fail("Should raise error for invalid smoothing method")
        except ValueError as e:
            print(f"FINDING: Invalid smoothing method correctly raises: {e}")
    
    def test_process_extreme_frequency_range(self, synthetic_seismic_data):
        """
        ISSUE: Extreme frequency range (very wide or very narrow).
        SEVERITY: MEDIUM
        """
        from hvsr_pro.processing.windows import WindowManager
        from hvsr_pro.processing.hvsr import HVSRProcessor
        
        manager = WindowManager(window_length=10.0, overlap=0.5)
        windows = manager.create_windows(synthetic_seismic_data, calculate_quality=True)
        
        # Very narrow range
        try:
            processor = HVSRProcessor(f_min=1.0, f_max=1.1, n_frequencies=10)
            result = processor.process(windows, detect_peaks_flag=True)
            print(f"FINDING: Very narrow range (1.0-1.1 Hz) succeeded")
        except Exception as e:
            print(f"FINDING: Very narrow range raises {type(e).__name__}: {e}")
        
        # Very wide range
        try:
            processor = HVSRProcessor(f_min=0.001, f_max=100.0, n_frequencies=100)
            result = processor.process(windows, detect_peaks_flag=True)
            print(f"FINDING: Very wide range (0.001-100 Hz) succeeded")
        except Exception as e:
            print(f"FINDING: Very wide range raises {type(e).__name__}: {e}")
    
    def test_process_inverted_frequency_range(self, synthetic_seismic_data):
        """
        ISSUE: f_min > f_max (inverted range).
        SEVERITY: HIGH
        """
        from hvsr_pro.processing.windows import WindowManager
        from hvsr_pro.processing.hvsr import HVSRProcessor
        
        manager = WindowManager(window_length=10.0, overlap=0.5)
        windows = manager.create_windows(synthetic_seismic_data, calculate_quality=True)
        
        try:
            processor = HVSRProcessor(f_min=20.0, f_max=0.2)  # Inverted
            result = processor.process(windows, detect_peaks_flag=True)
            print(f"FINDING: Inverted range succeeded with {len(result.frequencies)} points")
        except Exception as e:
            print(f"FINDING: Inverted range raises {type(e).__name__}: {e}")
    
    def test_process_zero_bandwidth(self, synthetic_seismic_data):
        """
        ISSUE: Zero smoothing bandwidth.
        SEVERITY: HIGH
        """
        from hvsr_pro.processing.windows import WindowManager
        from hvsr_pro.processing.hvsr import HVSRProcessor
        
        manager = WindowManager(window_length=10.0, overlap=0.5)
        windows = manager.create_windows(synthetic_seismic_data, calculate_quality=True)
        
        try:
            processor = HVSRProcessor(smoothing_bandwidth=0)
            result = processor.process(windows, detect_peaks_flag=True)
            print(f"FINDING: Zero bandwidth succeeded")
        except Exception as e:
            print(f"FINDING: Zero bandwidth raises {type(e).__name__}: {e}")
    
    def test_process_negative_bandwidth(self, synthetic_seismic_data):
        """
        ISSUE: Negative smoothing bandwidth.
        SEVERITY: MEDIUM
        """
        from hvsr_pro.processing.windows import WindowManager
        from hvsr_pro.processing.hvsr import HVSRProcessor
        
        manager = WindowManager(window_length=10.0, overlap=0.5)
        windows = manager.create_windows(synthetic_seismic_data, calculate_quality=True)
        
        try:
            processor = HVSRProcessor(smoothing_bandwidth=-40)
            result = processor.process(windows, detect_peaks_flag=True)
            print(f"FINDING: Negative bandwidth succeeded")
        except Exception as e:
            print(f"FINDING: Negative bandwidth raises {type(e).__name__}: {e}")


class TestHVSRResult:
    """Test HVSRResult structure and methods."""
    
    def test_result_with_no_peaks(self, flat_spectrum_data):
        """
        ISSUE: HVSR result with no detected peaks.
        SEVERITY: HIGH
        """
        from hvsr_pro.processing.windows import WindowManager
        from hvsr_pro.processing.hvsr import HVSRProcessor
        
        manager = WindowManager(window_length=10.0, overlap=0.5)
        windows = manager.create_windows(flat_spectrum_data, calculate_quality=True)
        
        processor = HVSRProcessor()
        result = processor.process(windows, detect_peaks_flag=True)
        
        # Flat data should produce no significant peaks
        print(f"FINDING: Flat spectrum detected {len(result.peaks)} peaks")
        
        # Check primary_peak access doesn't crash
        try:
            if hasattr(result, 'primary_peak'):
                primary = result.primary_peak
                print(f"FINDING: Primary peak: {primary}")
        except Exception as e:
            print(f"FINDING: Accessing primary_peak raises {type(e).__name__}: {e}")
    
    def test_result_statistics_consistency(self, synthetic_seismic_data):
        """Test that statistical measures are consistent."""
        from hvsr_pro.processing.windows import WindowManager
        from hvsr_pro.processing.hvsr import HVSRProcessor
        
        manager = WindowManager(window_length=10.0, overlap=0.5)
        windows = manager.create_windows(synthetic_seismic_data, calculate_quality=True)
        
        processor = HVSRProcessor()
        result = processor.process(windows, detect_peaks_flag=True)
        
        # Percentile 16 should be <= median <= percentile 84
        assert np.all(result.percentile_16 <= result.median_hvsr + 1e-10), \
            "P16 should be <= median"
        assert np.all(result.median_hvsr <= result.percentile_84 + 1e-10), \
            "Median should be <= P84"
        
        # Standard deviation should be non-negative
        assert np.all(result.std_hvsr >= 0), "Std should be non-negative"


class TestHorizontalMethods:
    """Test different horizontal combination methods."""
    
    def test_all_horizontal_methods(self, synthetic_seismic_data):
        """Test all supported horizontal combination methods."""
        from hvsr_pro.processing.windows import WindowManager
        from hvsr_pro.processing.hvsr import HVSRProcessor
        
        manager = WindowManager(window_length=10.0, overlap=0.5)
        windows = manager.create_windows(synthetic_seismic_data, calculate_quality=True)
        
        methods = ['geometric_mean', 'arithmetic_mean', 'quadratic', 'maximum']
        
        for method in methods:
            try:
                processor = HVSRProcessor(horizontal_method=method)
                result = processor.process(windows, detect_peaks_flag=True)
                print(f"FINDING: {method} - max HVSR: {np.max(result.mean_hvsr):.2f}")
            except Exception as e:
                print(f"FINDING: {method} raises {type(e).__name__}: {e}")
    
    def test_invalid_horizontal_method(self, synthetic_seismic_data):
        """
        ISSUE: Invalid horizontal combination method.
        SEVERITY: MEDIUM
        """
        from hvsr_pro.processing.windows import WindowManager
        from hvsr_pro.processing.hvsr import HVSRProcessor
        
        manager = WindowManager(window_length=10.0, overlap=0.5)
        windows = manager.create_windows(synthetic_seismic_data, calculate_quality=True)
        
        try:
            processor = HVSRProcessor(horizontal_method='invalid_method')
            result = processor.process(windows, detect_peaks_flag=True)
            pytest.fail("Should raise error for invalid horizontal method")
        except ValueError as e:
            print(f"FINDING: Invalid horizontal method correctly raises: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
