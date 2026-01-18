"""
Test Peak Detection - High Severity Issues
============================================

Tests for peak detection edge cases and potential failures.

ISSUE CATEGORY: HIGH SEVERITY
- Flat HVSR curves (no peaks)
- Very noisy data
- Edge cases in frequency ranges
"""

import pytest
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "HV_Analyze_Pro"))


class TestPeakDetection:
    """Test peak detection functions for edge cases."""
    
    def test_detect_peaks_flat_curve(self):
        """
        ISSUE: Flat HVSR curve with no peaks.
        SEVERITY: HIGH
        EXPECTED: Should return empty list, not crash.
        """
        from hvsr_pro.processing.windows.peaks import detect_peaks
        
        frequencies = np.logspace(-1, 1, 100)
        hvsr = np.ones(100)  # Perfectly flat
        
        peaks = detect_peaks(frequencies, hvsr, min_prominence=1.5, min_amplitude=2.0)
        
        assert isinstance(peaks, list), "Should return a list"
        assert len(peaks) == 0, "Flat curve should have no peaks"
    
    def test_detect_peaks_all_below_threshold(self):
        """
        ISSUE: All values below amplitude threshold.
        SEVERITY: MEDIUM
        """
        from hvsr_pro.processing.windows.peaks import detect_peaks
        
        frequencies = np.logspace(-1, 1, 100)
        hvsr = np.ones(100) * 0.5  # All below typical threshold of 2.0
        
        peaks = detect_peaks(frequencies, hvsr, min_prominence=1.5, min_amplitude=2.0)
        
        assert len(peaks) == 0, "Should find no peaks below threshold"
    
    def test_detect_peaks_single_point(self):
        """
        ISSUE: Single frequency point (can't detect peaks).
        SEVERITY: HIGH
        """
        from hvsr_pro.processing.windows.peaks import detect_peaks
        
        frequencies = np.array([1.0])
        hvsr = np.array([5.0])
        
        peaks = detect_peaks(frequencies, hvsr, min_prominence=0.1, min_amplitude=0.1)
        
        assert len(peaks) == 0, "Single point cannot have a peak"
    
    def test_detect_peaks_two_points(self):
        """
        ISSUE: Two frequency points.
        SEVERITY: HIGH
        """
        from hvsr_pro.processing.windows.peaks import detect_peaks
        
        frequencies = np.array([1.0, 2.0])
        hvsr = np.array([3.0, 5.0])
        
        peaks = detect_peaks(frequencies, hvsr, min_prominence=0.1, min_amplitude=0.1)
        # At minimum 3 points needed for peak detection
        print(f"FINDING: 2-point detection found {len(peaks)} peaks")
    
    def test_detect_peaks_empty_arrays(self):
        """
        ISSUE: Empty frequency/HVSR arrays.
        SEVERITY: VERY HIGH
        """
        from hvsr_pro.processing.windows.peaks import detect_peaks
        
        frequencies = np.array([])
        hvsr = np.array([])
        
        peaks = detect_peaks(frequencies, hvsr, min_prominence=1.5, min_amplitude=2.0)
        
        assert len(peaks) == 0, "Empty arrays should return empty list"
    
    def test_detect_peaks_with_nan(self):
        """
        ISSUE: HVSR curve containing NaN values.
        SEVERITY: HIGH
        """
        from hvsr_pro.processing.windows.peaks import detect_peaks
        
        frequencies = np.logspace(-1, 1, 100)
        hvsr = np.ones(100) * 3.0
        hvsr[50] = np.nan  # NaN in the middle
        
        try:
            peaks = detect_peaks(frequencies, hvsr, min_prominence=0.5, min_amplitude=1.0)
            print(f"FINDING: NaN in HVSR found {len(peaks)} peaks")
        except Exception as e:
            print(f"FINDING: NaN in HVSR raises {type(e).__name__}: {e}")
    
    def test_detect_peaks_with_inf(self):
        """
        ISSUE: HVSR curve containing Inf values.
        SEVERITY: HIGH
        """
        from hvsr_pro.processing.windows.peaks import detect_peaks
        
        frequencies = np.logspace(-1, 1, 100)
        hvsr = np.ones(100) * 3.0
        hvsr[50] = np.inf  # Inf in the middle
        
        try:
            peaks = detect_peaks(frequencies, hvsr, min_prominence=0.5, min_amplitude=1.0)
            print(f"FINDING: Inf in HVSR found {len(peaks)} peaks")
        except Exception as e:
            print(f"FINDING: Inf in HVSR raises {type(e).__name__}: {e}")
    
    def test_detect_peaks_frequency_range_outside_data(self):
        """
        ISSUE: Frequency range outside actual data range.
        SEVERITY: MEDIUM
        """
        from hvsr_pro.processing.windows.peaks import detect_peaks
        
        frequencies = np.logspace(-1, 1, 100)  # 0.1 to 10 Hz
        hvsr = np.ones(100) * 3.0
        hvsr[50] = 10.0  # Peak in middle
        
        # Search range completely outside data
        peaks = detect_peaks(
            frequencies, hvsr, 
            min_prominence=0.5, 
            min_amplitude=1.0,
            freq_range=(50.0, 100.0)  # Way outside data range
        )
        
        assert len(peaks) == 0, "Should find no peaks outside data range"
    
    def test_detect_peaks_negative_hvsr(self):
        """
        ISSUE: Negative HVSR values (shouldn't happen but test).
        SEVERITY: MEDIUM
        """
        from hvsr_pro.processing.windows.peaks import detect_peaks
        
        frequencies = np.logspace(-1, 1, 100)
        hvsr = np.ones(100) * -3.0  # All negative
        hvsr[50] = -1.0  # "Peak" (less negative)
        
        peaks = detect_peaks(frequencies, hvsr, min_prominence=0.5, min_amplitude=-5.0)
        print(f"FINDING: Negative HVSR found {len(peaks)} peaks")
    
    def test_detect_peaks_very_narrow_peak(self):
        """
        ISSUE: Very narrow (single-point) peak.
        SEVERITY: MEDIUM
        """
        from hvsr_pro.processing.windows.peaks import detect_peaks
        
        frequencies = np.logspace(-1, 1, 100)
        hvsr = np.ones(100) * 1.0
        hvsr[50] = 10.0  # Single point peak
        
        peaks = detect_peaks(frequencies, hvsr, min_prominence=0.5, min_amplitude=2.0)
        
        print(f"FINDING: Single-point peak detected: {len(peaks)} peaks")
        if peaks:
            print(f"FINDING: Peak width: {peaks[0].width}")


class TestPeakRefinement:
    """Test peak frequency refinement functions."""
    
    def test_refine_peak_at_edge(self):
        """
        ISSUE: Refine peak at array edge.
        SEVERITY: MEDIUM
        """
        from hvsr_pro.processing.windows.peaks import refine_peak_frequency
        
        frequencies = np.logspace(-1, 1, 100)
        hvsr = np.ones(100) * 2.0
        hvsr[0] = 5.0  # Peak at first element
        
        refined = refine_peak_frequency(frequencies, hvsr, frequencies[0], window_hz=0.5)
        
        assert np.isfinite(refined), "Refined frequency should be finite"
        print(f"FINDING: Edge peak refinement: {frequencies[0]} -> {refined}")
    
    def test_refine_peak_at_last_element(self):
        """
        ISSUE: Refine peak at last array element.
        SEVERITY: MEDIUM
        """
        from hvsr_pro.processing.windows.peaks import refine_peak_frequency
        
        frequencies = np.logspace(-1, 1, 100)
        hvsr = np.ones(100) * 2.0
        hvsr[-1] = 5.0  # Peak at last element
        
        refined = refine_peak_frequency(frequencies, hvsr, frequencies[-1], window_hz=0.5)
        
        assert np.isfinite(refined), "Refined frequency should be finite"
        print(f"FINDING: Last element peak refinement: {frequencies[-1]} -> {refined}")
    
    def test_refine_peak_very_narrow_window(self):
        """
        ISSUE: Refinement with very narrow search window.
        SEVERITY: LOW
        """
        from hvsr_pro.processing.windows.peaks import refine_peak_frequency
        
        frequencies = np.logspace(-1, 1, 100)
        hvsr = np.ones(100) * 2.0
        hvsr[50] = 5.0
        
        refined = refine_peak_frequency(frequencies, hvsr, frequencies[50], window_hz=0.001)
        
        assert np.isfinite(refined), "Narrow window refinement should work"


class TestIdentifyFundamentalPeak:
    """Test fundamental peak identification."""
    
    def test_identify_fundamental_no_peaks(self):
        """
        ISSUE: No peaks to identify fundamental from.
        SEVERITY: MEDIUM
        """
        from hvsr_pro.processing.windows.peaks import identify_fundamental_peak
        
        frequencies = np.logspace(-1, 1, 100)
        hvsr = np.ones(100)
        
        fundamental = identify_fundamental_peak([], frequencies, hvsr)
        
        assert fundamental is None, "Should return None when no peaks"
    
    def test_identify_fundamental_all_outside_range(self):
        """
        ISSUE: All peaks outside expected fundamental range.
        SEVERITY: MEDIUM
        """
        from hvsr_pro.processing.windows.peaks import detect_peaks, identify_fundamental_peak
        from hvsr_pro.processing.hvsr.structures import Peak
        
        frequencies = np.logspace(-1, 1, 100)
        hvsr = np.ones(100)
        
        # Create peaks outside typical fundamental range
        peaks = [
            Peak(frequency=15.0, amplitude=5.0, prominence=2.0, width=0.5,
                 left_freq=14.5, right_freq=15.5, quality=0.8)
        ]
        
        fundamental = identify_fundamental_peak(peaks, frequencies, hvsr, freq_range=(0.4, 10.0))
        
        assert fundamental is None, "Should return None when no peaks in range"


class TestSESAMECriteria:
    """Test SESAME reliability criteria."""
    
    def test_sesame_with_low_amplitude_peak(self):
        """
        ISSUE: Peak with amplitude below SESAME threshold.
        SEVERITY: LOW
        """
        from hvsr_pro.processing.windows.peaks import sesame_peak_criteria
        from hvsr_pro.processing.hvsr.structures import Peak
        
        frequencies = np.logspace(-1, 1, 100)
        hvsr = np.ones(100) * 1.5  # Low baseline
        hvsr[50] = 1.8  # Low peak
        
        peak = Peak(
            frequency=frequencies[50],
            amplitude=1.8,
            prominence=0.3,
            width=0.5,
            left_freq=frequencies[45],
            right_freq=frequencies[55],
            quality=0.3
        )
        
        criteria = sesame_peak_criteria(peak, frequencies, hvsr)
        
        assert not criteria['A0_gt_2'], "Low amplitude should fail A0 > 2 criterion"
        print(f"FINDING: SESAME criteria for low peak: {criteria}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
