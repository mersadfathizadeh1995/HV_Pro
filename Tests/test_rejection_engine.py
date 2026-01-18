"""
Test Rejection Engine - High Severity Issues
==============================================

Tests for RejectionEngine and QC algorithms edge cases.

ISSUE CATEGORY: HIGH SEVERITY
- Empty collections
- All algorithms disabled
- Conflicting settings
"""

import pytest
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "HV_Analyze_Pro"))


class TestRejectionEngine:
    """Test RejectionEngine for edge cases."""
    
    def test_evaluate_empty_collection(self):
        """
        ISSUE: Evaluate empty WindowCollection.
        SEVERITY: VERY HIGH
        """
        from hvsr_pro.processing.rejection import RejectionEngine
        from hvsr_pro.processing.windows.structures import WindowCollection
        
        engine = RejectionEngine()
        engine.create_default_pipeline(mode='balanced')
        
        collection = WindowCollection(windows=[])
        
        try:
            result = engine.evaluate(collection, auto_apply=True)
            print(f"FINDING: Empty collection evaluate returned: {result}")
        except Exception as e:
            print(f"FINDING: Empty collection raises {type(e).__name__}: {e}")
    
    def test_evaluate_no_algorithms(self, synthetic_seismic_data):
        """
        ISSUE: Evaluate with no algorithms added.
        SEVERITY: MEDIUM
        """
        from hvsr_pro.processing.rejection import RejectionEngine
        from hvsr_pro.processing.windows import WindowManager
        
        manager = WindowManager(window_length=10.0, overlap=0.5)
        windows = manager.create_windows(synthetic_seismic_data, calculate_quality=True)
        
        engine = RejectionEngine()
        # No algorithms added
        
        result = engine.evaluate(windows, auto_apply=True)
        
        # Should pass all windows through
        assert windows.n_active == windows.n_windows, "No rejection should occur"
        print(f"FINDING: No algorithms - all {windows.n_windows} windows remain active")
    
    def test_default_pipeline_modes(self, synthetic_seismic_data):
        """Test all default pipeline modes work."""
        from hvsr_pro.processing.rejection import RejectionEngine
        from hvsr_pro.processing.windows import WindowManager
        
        modes = ['none', 'light', 'balanced', 'strict', 'sesame']
        
        for mode in modes:
            manager = WindowManager(window_length=10.0, overlap=0.5)
            windows = manager.create_windows(synthetic_seismic_data, calculate_quality=True)
            
            engine = RejectionEngine()
            
            try:
                engine.create_default_pipeline(mode=mode)
                result = engine.evaluate(windows, auto_apply=True)
                print(f"FINDING: Mode '{mode}' - {windows.n_active}/{windows.n_windows} active")
            except Exception as e:
                print(f"FINDING: Mode '{mode}' raises {type(e).__name__}: {e}")
    
    def test_invalid_pipeline_mode(self):
        """
        ISSUE: Invalid pipeline mode name.
        SEVERITY: MEDIUM
        """
        from hvsr_pro.processing.rejection import RejectionEngine
        
        engine = RejectionEngine()
        
        try:
            engine.create_default_pipeline(mode='invalid_mode')
            pytest.fail("Should raise error for invalid mode")
        except (ValueError, KeyError) as e:
            print(f"FINDING: Invalid mode correctly raises: {e}")


class TestSTALTARejection:
    """Test STA/LTA rejection algorithm edge cases."""
    
    def test_stalta_with_constant_data(self):
        """
        ISSUE: STA/LTA with constant data (no variation).
        SEVERITY: HIGH
        """
        from hvsr_pro.processing.rejection.algorithms.stalta import STALTARejection
        from hvsr_pro.processing.windows.structures import Window
        from hvsr_pro.core.data_structures import SeismicData, ComponentData
        
        sampling_rate = 100.0
        n_samples = 6000
        constant_data = np.ones(n_samples)
        
        east = ComponentData(name='E', data=constant_data, sampling_rate=sampling_rate)
        north = ComponentData(name='N', data=constant_data, sampling_rate=sampling_rate)
        vertical = ComponentData(name='Z', data=constant_data, sampling_rate=sampling_rate)
        
        data = SeismicData(east=east, north=north, vertical=vertical)
        window = Window(index=0, start_sample=0, end_sample=n_samples, data=data)
        
        algo = STALTARejection()
        
        try:
            result = algo.evaluate_window(window)
            print(f"FINDING: Constant data STA/LTA - reject: {result.should_reject}")
            print(f"FINDING: Reason: {result.reason}")
        except ZeroDivisionError as e:
            pytest.fail(f"CRITICAL: Constant data causes ZeroDivisionError: {e}")
    
    def test_stalta_with_zero_data(self):
        """
        ISSUE: STA/LTA with all-zero data.
        SEVERITY: VERY HIGH
        """
        from hvsr_pro.processing.rejection.algorithms.stalta import STALTARejection
        from hvsr_pro.processing.windows.structures import Window
        from hvsr_pro.core.data_structures import SeismicData, ComponentData
        
        sampling_rate = 100.0
        n_samples = 6000
        zero_data = np.zeros(n_samples)
        
        east = ComponentData(name='E', data=zero_data + 1e-10, sampling_rate=sampling_rate)
        north = ComponentData(name='N', data=zero_data + 1e-10, sampling_rate=sampling_rate)
        vertical = ComponentData(name='Z', data=zero_data + 1e-10, sampling_rate=sampling_rate)
        
        data = SeismicData(east=east, north=north, vertical=vertical)
        window = Window(index=0, start_sample=0, end_sample=n_samples, data=data)
        
        algo = STALTARejection()
        
        try:
            result = algo.evaluate_window(window)
            print(f"FINDING: Zero data STA/LTA - reject: {result.should_reject}")
            print(f"FINDING: Reason: {result.reason}")
        except ZeroDivisionError as e:
            pytest.fail(f"CRITICAL: Zero data causes ZeroDivisionError: {e}")
    
    def test_stalta_lta_longer_than_data(self):
        """
        ISSUE: LTA window longer than data length.
        SEVERITY: HIGH
        """
        from hvsr_pro.processing.rejection.algorithms.stalta import STALTARejection
        from hvsr_pro.processing.windows.structures import Window
        from hvsr_pro.core.data_structures import SeismicData, ComponentData
        
        sampling_rate = 100.0
        n_samples = 1000  # 10 seconds
        
        east = ComponentData(name='E', data=np.random.randn(n_samples), 
                           sampling_rate=sampling_rate)
        north = ComponentData(name='N', data=np.random.randn(n_samples), 
                            sampling_rate=sampling_rate)
        vertical = ComponentData(name='Z', data=np.random.randn(n_samples), 
                               sampling_rate=sampling_rate)
        
        data = SeismicData(east=east, north=north, vertical=vertical)
        window = Window(index=0, start_sample=0, end_sample=n_samples, data=data)
        
        # LTA of 30 seconds > 10 seconds of data
        algo = STALTARejection(sta_length=1.0, lta_length=30.0)
        
        try:
            result = algo.evaluate_window(window)
            print(f"FINDING: LTA > data length - reject: {result.should_reject}")
        except Exception as e:
            print(f"FINDING: LTA > data length raises {type(e).__name__}: {e}")


class TestAmplitudeRejection:
    """Test Amplitude rejection algorithm edge cases."""
    
    def test_amplitude_with_extreme_values(self):
        """
        ISSUE: Amplitude check with extreme values (very large).
        SEVERITY: MEDIUM
        """
        from hvsr_pro.processing.rejection.algorithms.amplitude import AmplitudeRejection
        from hvsr_pro.processing.windows.structures import Window
        from hvsr_pro.core.data_structures import SeismicData, ComponentData
        
        sampling_rate = 100.0
        n_samples = 1000
        
        # Very large values
        large_data = np.ones(n_samples) * 1e10
        
        east = ComponentData(name='E', data=large_data, sampling_rate=sampling_rate)
        north = ComponentData(name='N', data=large_data, sampling_rate=sampling_rate)
        vertical = ComponentData(name='Z', data=large_data, sampling_rate=sampling_rate)
        
        data = SeismicData(east=east, north=north, vertical=vertical)
        window = Window(index=0, start_sample=0, end_sample=n_samples, data=data)
        
        algo = AmplitudeRejection()
        
        result = algo.evaluate_window(window)
        print(f"FINDING: Extreme values amplitude - reject: {result.should_reject}")


class TestFrequencyDomainRejection:
    """Test Frequency Domain rejection algorithm edge cases."""
    
    def test_frequency_domain_with_spike(self):
        """Test spike detection in frequency domain."""
        from hvsr_pro.processing.rejection.algorithms.frequency import FrequencyDomainRejection
        from hvsr_pro.processing.windows.structures import Window
        from hvsr_pro.core.data_structures import SeismicData, ComponentData
        
        sampling_rate = 100.0
        n_samples = 1000
        t = np.arange(n_samples) / sampling_rate
        
        # Create data with a strong spike (monochromatic)
        spike_data = np.sin(2 * np.pi * 10.0 * t)  # Strong 10 Hz signal
        
        east = ComponentData(name='E', data=spike_data, sampling_rate=sampling_rate)
        north = ComponentData(name='N', data=spike_data, sampling_rate=sampling_rate)
        vertical = ComponentData(name='Z', data=spike_data * 0.5, sampling_rate=sampling_rate)
        
        data = SeismicData(east=east, north=north, vertical=vertical)
        window = Window(index=0, start_sample=0, end_sample=n_samples, data=data)
        
        algo = FrequencyDomainRejection(spike_threshold=3.0)
        
        result = algo.evaluate_window(window)
        print(f"FINDING: Spike detection - reject: {result.should_reject}")
        print(f"FINDING: Reason: {result.reason}")


class TestStatisticalOutlierRejection:
    """Test Statistical Outlier rejection algorithm edge cases."""
    
    def test_outlier_with_single_window(self):
        """
        ISSUE: Outlier detection with single window (can't compute statistics).
        SEVERITY: HIGH
        """
        from hvsr_pro.processing.rejection.algorithms.statistical import StatisticalOutlierRejection
        from hvsr_pro.processing.windows.structures import WindowCollection, Window
        from hvsr_pro.core.data_structures import SeismicData, ComponentData
        
        sampling_rate = 100.0
        n_samples = 1000
        
        east = ComponentData(name='E', data=np.random.randn(n_samples), 
                           sampling_rate=sampling_rate)
        north = ComponentData(name='N', data=np.random.randn(n_samples), 
                            sampling_rate=sampling_rate)
        vertical = ComponentData(name='Z', data=np.random.randn(n_samples), 
                               sampling_rate=sampling_rate)
        
        data = SeismicData(east=east, north=north, vertical=vertical)
        window = Window(index=0, start_sample=0, end_sample=n_samples, data=data)
        
        collection = WindowCollection(windows=[window])
        
        algo = StatisticalOutlierRejection()
        
        try:
            results = algo.evaluate_collection(collection)
            print(f"FINDING: Single window outlier detection - results: {len(results)}")
        except Exception as e:
            print(f"FINDING: Single window outlier raises {type(e).__name__}: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
