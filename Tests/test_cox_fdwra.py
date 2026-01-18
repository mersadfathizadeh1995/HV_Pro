"""
Test Cox FDWRA Algorithm - High Severity Issues
=================================================

Tests for Cox et al. (2020) FDWRA algorithm edge cases.

ISSUE CATEGORY: VERY HIGH SEVERITY
- Less than 3 windows available
- All windows have same peak frequency
- Convergence issues
- Lognormal with zero/negative values
"""

import pytest
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "HV_Analyze_Pro"))


class TestCoxFDWRAEdgeCases:
    """Test Cox FDWRA algorithm for edge cases and potential crashes."""
    
    def test_fdwra_with_less_than_3_windows(self):
        """
        ISSUE: FDWRA with less than 3 windows (minimum required).
        SEVERITY: VERY HIGH
        EXPECTED: Should handle gracefully, not crash.
        """
        from hvsr_pro.processing.rejection.algorithms.cox_fdwra import CoxFDWRARejection
        from hvsr_pro.processing.windows.structures import WindowCollection, Window
        from hvsr_pro.core.data_structures import SeismicData, ComponentData
        
        # Create only 2 windows (below minimum)
        windows = []
        for i in range(2):
            n_samples = 1000
            sampling_rate = 100.0
            
            east = ComponentData(name='E', data=np.random.randn(n_samples), 
                               sampling_rate=sampling_rate)
            north = ComponentData(name='N', data=np.random.randn(n_samples), 
                                sampling_rate=sampling_rate)
            vertical = ComponentData(name='Z', data=np.random.randn(n_samples), 
                                   sampling_rate=sampling_rate)
            
            data = SeismicData(east=east, north=north, vertical=vertical)
            window = Window(index=i, start_sample=i*1000, end_sample=(i+1)*1000, data=data)
            windows.append(window)
        
        # Need source_data for WindowCollection
        source_data = data  # Use last window's data as source
        collection = WindowCollection(windows=windows, source_data=source_data, 
                                      window_length=10.0, overlap=0.5)
        
        # Attach mock HVSR result
        class MockHVSRResult:
            def __init__(self):
                self.frequencies = np.logspace(-1, 1, 50)
                self.window_spectra = []
                for i in range(2):
                    class MockSpectrum:
                        hvsr = np.random.rand(50) + 1
                    self.window_spectra.append(MockSpectrum())
        
        collection._hvsr_result = MockHVSRResult()
        
        cox = CoxFDWRARejection(n=2.0, max_iterations=50)
        
        try:
            results = cox.evaluate_collection(collection)
            print(f"FINDING: FDWRA with 2 windows returned {len(results)} results")
            # Should complete without crashing
        except Exception as e:
            pytest.fail(f"FDWRA with 2 windows should not crash: {type(e).__name__}: {e}")
    
    def test_fdwra_with_single_window(self):
        """
        ISSUE: FDWRA with only 1 window.
        SEVERITY: VERY HIGH
        """
        from hvsr_pro.processing.rejection.algorithms.cox_fdwra import CoxFDWRARejection
        from hvsr_pro.processing.windows.structures import WindowCollection, Window
        from hvsr_pro.core.data_structures import SeismicData, ComponentData
        
        n_samples = 1000
        sampling_rate = 100.0
        
        east = ComponentData(name='E', data=np.random.randn(n_samples), 
                           sampling_rate=sampling_rate)
        north = ComponentData(name='N', data=np.random.randn(n_samples), 
                            sampling_rate=sampling_rate)
        vertical = ComponentData(name='Z', data=np.random.randn(n_samples), 
                               sampling_rate=sampling_rate)
        
        data = SeismicData(east=east, north=north, vertical=vertical)
        window = Window(index=0, start_sample=0, end_sample=n_samples, data=data)
        
        collection = WindowCollection(windows=[window], source_data=data, 
                                      window_length=10.0, overlap=0.5)
        
        class MockHVSRResult:
            def __init__(self):
                self.frequencies = np.logspace(-1, 1, 50)
                class MockSpectrum:
                    hvsr = np.random.rand(50) + 1
                self.window_spectra = [MockSpectrum()]
        
        collection._hvsr_result = MockHVSRResult()
        
        cox = CoxFDWRARejection(n=2.0)
        
        try:
            results = cox.evaluate_collection(collection)
            print(f"FINDING: FDWRA with 1 window returned {len(results)} results")
        except Exception as e:
            print(f"FINDING: FDWRA with 1 window raises {type(e).__name__}: {e}")
    
    def test_fdwra_with_no_hvsr_result(self):
        """
        ISSUE: FDWRA called without HVSR result attached.
        SEVERITY: VERY HIGH
        """
        from hvsr_pro.processing.rejection.algorithms.cox_fdwra import CoxFDWRARejection
        from hvsr_pro.processing.windows.structures import WindowCollection, Window
        from hvsr_pro.core.data_structures import SeismicData, ComponentData
        
        # Create windows without HVSR result
        windows = []
        for i in range(5):
            n_samples = 1000
            sampling_rate = 100.0
            
            east = ComponentData(name='E', data=np.random.randn(n_samples), 
                               sampling_rate=sampling_rate)
            north = ComponentData(name='N', data=np.random.randn(n_samples), 
                                sampling_rate=sampling_rate)
            vertical = ComponentData(name='Z', data=np.random.randn(n_samples), 
                                   sampling_rate=sampling_rate)
            
            data = SeismicData(east=east, north=north, vertical=vertical)
            window = Window(index=i, start_sample=i*1000, end_sample=(i+1)*1000, data=data)
            windows.append(window)
        
        source_data = data
        collection = WindowCollection(windows=windows, source_data=source_data, 
                                      window_length=10.0, overlap=0.5)
        # Note: NOT attaching _hvsr_result
        
        cox = CoxFDWRARejection(n=2.0)
        
        results = cox.evaluate_collection(collection)
        
        # Should return results indicating HVSR required
        assert len(results) == len(windows)
        print(f"FINDING: FDWRA without HVSR - first result: {results[0].reason}")
    
    def test_fdwra_with_identical_peak_frequencies(self):
        """
        ISSUE: All windows have identical peak frequencies (zero std).
        SEVERITY: HIGH
        """
        from hvsr_pro.processing.rejection.algorithms.cox_fdwra import CoxFDWRARejection
        from hvsr_pro.processing.windows.structures import WindowCollection, Window
        from hvsr_pro.core.data_structures import SeismicData, ComponentData
        
        windows = []
        for i in range(10):
            n_samples = 1000
            sampling_rate = 100.0
            
            east = ComponentData(name='E', data=np.random.randn(n_samples), 
                               sampling_rate=sampling_rate)
            north = ComponentData(name='N', data=np.random.randn(n_samples), 
                                sampling_rate=sampling_rate)
            vertical = ComponentData(name='Z', data=np.random.randn(n_samples), 
                                   sampling_rate=sampling_rate)
            
            data = SeismicData(east=east, north=north, vertical=vertical)
            window = Window(index=i, start_sample=i*1000, end_sample=(i+1)*1000, data=data)
            windows.append(window)
        
        source_data = data
        collection = WindowCollection(windows=windows, source_data=source_data,
                                      window_length=10.0, overlap=0.5)
        
        # Create identical HVSR curves (same peak at 2 Hz)
        class MockHVSRResult:
            def __init__(self):
                self.frequencies = np.logspace(-1, 1, 50)
                self.window_spectra = []
                
                # Identical curve for all windows
                base_hvsr = np.ones(50)
                peak_idx = 25  # Same peak for all
                base_hvsr[peak_idx] = 5.0  # Strong peak
                
                for i in range(10):
                    class MockSpectrum:
                        hvsr = base_hvsr.copy()
                    self.window_spectra.append(MockSpectrum())
        
        collection._hvsr_result = MockHVSRResult()
        
        cox = CoxFDWRARejection(n=2.0)
        
        try:
            results = cox.evaluate_collection(collection)
            n_rejected = sum(1 for r in results if r.should_reject)
            print(f"FINDING: Identical peaks - {n_rejected}/{len(results)} rejected")
        except ZeroDivisionError as e:
            pytest.fail(f"CRITICAL: Identical peaks causes ZeroDivisionError: {e}")
    
    def test_fdwra_lognormal_with_zero_frequencies(self):
        """
        ISSUE: Lognormal distribution with zero peak frequencies.
        SEVERITY: VERY HIGH (log(0) = -inf)
        """
        from hvsr_pro.processing.rejection.algorithms.cox_fdwra import CoxFDWRARejection
        
        cox = CoxFDWRARejection(n=2.0, distribution_fn='lognormal')
        
        # Test internal methods with zeros
        values = np.array([0.0, 1.0, 2.0, 3.0])
        
        try:
            mean = cox._calculate_mean(values, 'lognormal')
            std = cox._calculate_std(values, 'lognormal')
            print(f"FINDING: Lognormal with zero - mean={mean}, std={std}")
        except Exception as e:
            print(f"FINDING: Lognormal with zero raises {type(e).__name__}: {e}")
    
    def test_fdwra_convergence_max_iterations(self):
        """
        ISSUE: FDWRA reaching max iterations without convergence.
        SEVERITY: MEDIUM
        """
        from hvsr_pro.processing.rejection.algorithms.cox_fdwra import CoxFDWRARejection
        from hvsr_pro.processing.windows.structures import WindowCollection, Window
        from hvsr_pro.core.data_structures import SeismicData, ComponentData
        
        windows = []
        for i in range(20):
            n_samples = 1000
            sampling_rate = 100.0
            
            east = ComponentData(name='E', data=np.random.randn(n_samples), 
                               sampling_rate=sampling_rate)
            north = ComponentData(name='N', data=np.random.randn(n_samples), 
                                sampling_rate=sampling_rate)
            vertical = ComponentData(name='Z', data=np.random.randn(n_samples), 
                                   sampling_rate=sampling_rate)
            
            data = SeismicData(east=east, north=north, vertical=vertical)
            window = Window(index=i, start_sample=i*1000, end_sample=(i+1)*1000, data=data)
            windows.append(window)
        
        source_data = data
        collection = WindowCollection(windows=windows, source_data=source_data,
                                      window_length=10.0, overlap=0.5)
        
        # Create widely varying HVSR curves (hard to converge)
        class MockHVSRResult:
            def __init__(self):
                self.frequencies = np.logspace(-1, 1, 50)
                self.window_spectra = []
                
                for i in range(20):
                    class MockSpectrum:
                        hvsr = np.ones(50)
                    spec = MockSpectrum()
                    # Different peak position for each
                    spec.hvsr[10 + i] = 5.0
                    self.window_spectra.append(spec)
        
        collection._hvsr_result = MockHVSRResult()
        
        # Very low max iterations
        cox = CoxFDWRARejection(n=2.0, max_iterations=3)
        
        results = cox.evaluate_collection(collection)
        
        print(f"FINDING: Max 3 iterations - converged: {cox.converged_iteration is not None}")
        print(f"FINDING: Iterations run: {len(cox.iteration_history)}")


class TestCoxFDWRAStatistics:
    """Test statistical calculations in Cox FDWRA."""
    
    def test_calculate_mean_normal(self):
        """Test normal distribution mean calculation."""
        from hvsr_pro.processing.rejection.algorithms.cox_fdwra import CoxFDWRARejection
        
        cox = CoxFDWRARejection()
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        
        mean = cox._calculate_mean(values, 'normal')
        assert np.isclose(mean, 3.0), f"Normal mean should be 3.0, got {mean}"
    
    def test_calculate_mean_lognormal(self):
        """Test lognormal distribution mean calculation."""
        from hvsr_pro.processing.rejection.algorithms.cox_fdwra import CoxFDWRARejection
        
        cox = CoxFDWRARejection()
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        
        mean = cox._calculate_mean(values, 'lognormal')
        # Lognormal mean: exp(mean(log(x)))
        expected = np.exp(np.mean(np.log(values)))
        assert np.isclose(mean, expected), f"Lognormal mean incorrect: {mean} vs {expected}"
    
    def test_calculate_std_with_single_value(self):
        """
        ISSUE: Standard deviation with single value (ddof=1).
        SEVERITY: HIGH
        """
        from hvsr_pro.processing.rejection.algorithms.cox_fdwra import CoxFDWRARejection
        
        cox = CoxFDWRARejection()
        values = np.array([5.0])  # Single value
        
        try:
            std = cox._calculate_std(values, 'normal')
            print(f"FINDING: Single value std = {std}")
            # With ddof=1, this produces NaN
        except Exception as e:
            print(f"FINDING: Single value std raises {type(e).__name__}: {e}")
    
    def test_nth_std_bounds_normal(self):
        """Test n-sigma bounds for normal distribution."""
        from hvsr_pro.processing.rejection.algorithms.cox_fdwra import CoxFDWRARejection
        
        cox = CoxFDWRARejection()
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        
        lower = cox._calculate_nth_std(values, -2.0, 'normal')
        upper = cox._calculate_nth_std(values, +2.0, 'normal')
        
        assert lower < np.mean(values) < upper, "Mean should be between bounds"
        print(f"FINDING: Normal 2-sigma bounds: [{lower}, {upper}]")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
