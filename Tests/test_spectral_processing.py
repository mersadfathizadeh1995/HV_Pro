"""
Test Spectral Processing - High Severity Issues
=================================================

Tests for division by zero, NaN handling, and edge cases in spectral calculations.

ISSUE CATEGORY: VERY HIGH SEVERITY
- Division by zero in HVSR calculation
- NaN propagation through pipeline
- Empty array handling
"""

import pytest
import numpy as np
import sys
from pathlib import Path

# Add hvsr_pro to path
sys.path.insert(0, str(Path(__file__).parent.parent / "HV_Analyze_Pro"))


class TestCalculateHVSR:
    """Test HVSR calculation for division by zero and edge cases."""
    
    def test_hvsr_with_zero_vertical_spectrum(self):
        """
        ISSUE: Division by zero when vertical spectrum is zero.
        SEVERITY: VERY HIGH
        EXPECTED: Should handle gracefully with epsilon protection.
        """
        from hvsr_pro.processing.hvsr.spectral import calculate_hvsr
        
        horizontal = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        vertical = np.array([0.0, 0.0, 0.0, 0.0, 0.0])  # All zeros
        
        # Should NOT raise ZeroDivisionError
        result = calculate_hvsr(horizontal, vertical)
        
        # Should return finite values (protected by epsilon)
        assert np.all(np.isfinite(result)), "HVSR should be finite even with zero vertical"
        assert not np.any(np.isnan(result)), "HVSR should not contain NaN"
        assert not np.any(np.isinf(result)), "HVSR should not contain Inf"
    
    def test_hvsr_with_very_small_vertical_spectrum(self):
        """
        ISSUE: Numerical instability with very small vertical values.
        SEVERITY: HIGH
        """
        from hvsr_pro.processing.hvsr.spectral import calculate_hvsr
        
        horizontal = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        vertical = np.array([1e-15, 1e-15, 1e-15, 1e-15, 1e-15])  # Very small
        
        result = calculate_hvsr(horizontal, vertical)
        
        assert np.all(np.isfinite(result)), "HVSR should handle very small vertical values"
        # Values should be large but finite due to epsilon
    
    def test_hvsr_with_nan_input(self):
        """
        ISSUE: NaN propagation through HVSR calculation.
        SEVERITY: HIGH
        """
        from hvsr_pro.processing.hvsr.spectral import calculate_hvsr
        
        horizontal = np.array([1.0, np.nan, 3.0, 4.0, 5.0])
        vertical = np.array([1.0, 1.0, 1.0, 1.0, 1.0])
        
        result = calculate_hvsr(horizontal, vertical)
        
        # NaN should propagate (expected behavior) - test that it doesn't crash
        assert len(result) == len(horizontal), "Output length should match input"
    
    def test_hvsr_with_empty_arrays(self):
        """
        ISSUE: Empty array handling in HVSR calculation.
        SEVERITY: VERY HIGH
        """
        from hvsr_pro.processing.hvsr.spectral import calculate_hvsr
        
        horizontal = np.array([])
        vertical = np.array([])
        
        # Should not crash
        result = calculate_hvsr(horizontal, vertical)
        assert len(result) == 0, "Empty input should produce empty output"
    
    def test_hvsr_with_negative_values(self):
        """
        ISSUE: Negative spectrum values (should not happen but test robustness).
        SEVERITY: MEDIUM
        """
        from hvsr_pro.processing.hvsr.spectral import calculate_hvsr
        
        horizontal = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        vertical = np.array([-1.0, 1.0, 1.0, 1.0, 1.0])  # First is negative
        
        # Should handle without crashing
        result = calculate_hvsr(horizontal, vertical)
        assert len(result) == len(horizontal)


class TestFFTComputation:
    """Test FFT computation edge cases."""
    
    def test_fft_with_single_sample(self):
        """
        ISSUE: FFT with single sample data.
        SEVERITY: HIGH
        """
        from hvsr_pro.processing.hvsr.spectral import compute_fft
        
        data = np.array([1.0])
        sampling_rate = 100.0
        
        try:
            frequencies, spectrum = compute_fft(data, sampling_rate, taper=None)
            # Should complete without error
            assert len(frequencies) >= 1
        except Exception as e:
            pytest.fail(f"FFT with single sample should not crash: {e}")
    
    def test_fft_with_constant_data(self):
        """
        ISSUE: FFT with constant (DC only) data.
        SEVERITY: MEDIUM
        """
        from hvsr_pro.processing.hvsr.spectral import compute_fft
        
        data = np.ones(1000)  # Constant value
        sampling_rate = 100.0
        
        frequencies, spectrum = compute_fft(data, sampling_rate, taper='hann')
        
        # After mean removal, should be all zeros -> spectrum should be zero
        assert not np.any(np.isnan(spectrum)), "Constant data FFT should not produce NaN"
    
    def test_fft_with_empty_data(self):
        """
        ISSUE: FFT with empty array.
        SEVERITY: VERY HIGH
        """
        from hvsr_pro.processing.hvsr.spectral import compute_fft
        
        data = np.array([])
        sampling_rate = 100.0
        
        # Should handle gracefully
        try:
            frequencies, spectrum = compute_fft(data, sampling_rate, taper=None)
        except (ValueError, IndexError) as e:
            # Expected to fail - document the behavior
            print(f"FINDING: FFT with empty data raises {type(e).__name__}: {e}")
    
    def test_fft_taper_with_short_data(self):
        """
        ISSUE: Taper window applied to very short data.
        SEVERITY: MEDIUM
        """
        from hvsr_pro.processing.hvsr.spectral import compute_fft
        
        data = np.array([1.0, 2.0, 3.0])  # Very short
        sampling_rate = 100.0
        
        for taper in ['hann', 'hamming', 'blackman', None]:
            try:
                frequencies, spectrum = compute_fft(data, sampling_rate, taper=taper)
                assert len(spectrum) >= 1
            except Exception as e:
                print(f"FINDING: Taper '{taper}' with short data: {type(e).__name__}: {e}")


class TestKonnoOhmachiSmoothing:
    """Test Konno-Ohmachi smoothing edge cases."""
    
    def test_smoothing_with_dc_component(self):
        """
        ISSUE: Handling DC (0 Hz) component in smoothing.
        SEVERITY: HIGH
        """
        from hvsr_pro.processing.hvsr.spectral import konno_ohmachi_smoothing
        
        # Include DC component (0 Hz)
        frequencies = np.array([0.0, 0.5, 1.0, 2.0, 5.0, 10.0])
        spectrum = np.array([1.0, 2.0, 3.0, 4.0, 3.0, 2.0])
        
        result = konno_ohmachi_smoothing(frequencies, spectrum, bandwidth=40.0)
        
        assert not np.any(np.isnan(result)), "Smoothing should handle DC component"
        assert not np.any(np.isinf(result)), "Smoothing should not produce Inf"
    
    def test_smoothing_with_zero_bandwidth(self):
        """
        ISSUE: Zero bandwidth parameter.
        SEVERITY: HIGH
        """
        from hvsr_pro.processing.hvsr.spectral import konno_ohmachi_smoothing
        
        frequencies = np.logspace(-1, 1, 50)
        spectrum = np.random.rand(50)
        
        try:
            result = konno_ohmachi_smoothing(frequencies, spectrum, bandwidth=0.0)
            print(f"FINDING: Zero bandwidth produces result with max={np.max(result)}")
        except Exception as e:
            print(f"FINDING: Zero bandwidth raises {type(e).__name__}: {e}")
    
    def test_smoothing_with_negative_frequencies(self):
        """
        ISSUE: Negative frequencies in smoothing (shouldn't happen but test).
        SEVERITY: MEDIUM
        """
        from hvsr_pro.processing.hvsr.spectral import konno_ohmachi_smoothing
        
        frequencies = np.array([-1.0, 0.0, 1.0, 2.0, 5.0])  # Negative included
        spectrum = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        
        try:
            result = konno_ohmachi_smoothing(frequencies, spectrum, bandwidth=40.0)
            has_nan = np.any(np.isnan(result))
            print(f"FINDING: Negative frequencies - NaN present: {has_nan}")
        except Exception as e:
            print(f"FINDING: Negative frequencies raise {type(e).__name__}: {e}")
    
    def test_fast_smoothing_consistency(self):
        """
        ISSUE: Fast and standard smoothing should produce similar results.
        SEVERITY: MEDIUM
        """
        from hvsr_pro.processing.hvsr.spectral import (
            konno_ohmachi_smoothing, 
            konno_ohmachi_smoothing_fast
        )
        
        frequencies = np.logspace(-1, 1, 50)
        spectrum = np.random.rand(50)
        
        result_std = konno_ohmachi_smoothing(frequencies, spectrum, bandwidth=40.0)
        result_fast = konno_ohmachi_smoothing_fast(frequencies, spectrum, bandwidth=40.0)
        
        # They should be very close
        max_diff = np.max(np.abs(result_std - result_fast))
        print(f"FINDING: Max difference between standard and fast smoothing: {max_diff}")
        
        assert max_diff < 0.01, f"Smoothing methods differ significantly: {max_diff}"


class TestHorizontalSpectrumCombination:
    """Test horizontal spectrum combination methods."""
    
    def test_geometric_mean_with_zeros(self):
        """
        ISSUE: Geometric mean with zero values.
        SEVERITY: HIGH
        """
        from hvsr_pro.processing.hvsr.spectral import calculate_horizontal_spectrum
        
        east = np.array([0.0, 1.0, 2.0, 3.0])
        north = np.array([1.0, 2.0, 3.0, 4.0])
        
        result = calculate_horizontal_spectrum(east, north, method='geometric_mean')
        
        # sqrt(0 * x) = 0, should be handled
        assert result[0] == 0.0, "Geometric mean of zero should be zero"
        assert not np.any(np.isnan(result)), "Should not produce NaN"
    
    def test_geometric_mean_with_negative(self):
        """
        ISSUE: Geometric mean with negative values (invalid for sqrt).
        SEVERITY: HIGH
        """
        from hvsr_pro.processing.hvsr.spectral import calculate_horizontal_spectrum
        
        east = np.array([-1.0, 1.0, 2.0, 3.0])  # Negative value
        north = np.array([1.0, 2.0, 3.0, 4.0])
        
        try:
            result = calculate_horizontal_spectrum(east, north, method='geometric_mean')
            # sqrt of negative produces NaN or warning
            has_nan = np.any(np.isnan(result))
            print(f"FINDING: Geometric mean with negative - NaN present: {has_nan}")
        except Exception as e:
            print(f"FINDING: Geometric mean with negative raises {type(e).__name__}: {e}")
    
    def test_all_combination_methods(self):
        """Test all horizontal combination methods work."""
        from hvsr_pro.processing.hvsr.spectral import calculate_horizontal_spectrum
        
        east = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        north = np.array([1.5, 2.5, 3.5, 4.5, 5.5])
        
        methods = ['geometric_mean', 'arithmetic_mean', 'quadratic', 'maximum']
        
        for method in methods:
            result = calculate_horizontal_spectrum(east, north, method=method)
            assert len(result) == len(east), f"{method} should preserve length"
            assert not np.any(np.isnan(result)), f"{method} should not produce NaN"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
