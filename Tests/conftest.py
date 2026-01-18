"""
Test Configuration for HVSR Pro
================================

Pytest configuration and shared fixtures for all tests.
"""

import sys
import os
import pytest
import numpy as np
from pathlib import Path

# Add the hvsr_pro package to the path
HVSR_PRO_PATH = Path(__file__).parent.parent / "HV_Analyze_Pro"
sys.path.insert(0, str(HVSR_PRO_PATH))

# Test data paths
TEST_DATA_ROOT = Path(__file__).parent.parent / "Files" / "hvsrpy-main" / "hvsrpy" / "test" / "data" / "input"
MSEED_COMBINED = TEST_DATA_ROOT / "mseed_combined"
MSEED_INDIVIDUAL = TEST_DATA_ROOT / "mseed_individual"
SAC_BIG_ENDIAN = TEST_DATA_ROOT / "sac_big_endian"
SAC_LITTLE_ENDIAN = TEST_DATA_ROOT / "sac_little_endian"


@pytest.fixture
def mseed_combined_file():
    """Path to a combined MiniSEED file with all 3 components."""
    return str(MSEED_COMBINED / "ut.stn11.a2_c50.mseed")


@pytest.fixture
def mseed_individual_files():
    """Paths to individual MiniSEED component files."""
    return {
        'E': str(MSEED_INDIVIDUAL / "ut.stn11.a2_c50_bhe.mseed"),
        'N': str(MSEED_INDIVIDUAL / "ut.stn11.a2_c50_bhn.mseed"),
        'Z': str(MSEED_INDIVIDUAL / "ut.stn11.a2_c50_bhz.mseed")
    }


@pytest.fixture
def sac_files_big_endian():
    """Paths to SAC files (big endian)."""
    return {
        'E': str(SAC_BIG_ENDIAN / "ut.stn11.a2_c50_e.sac"),
        'N': str(SAC_BIG_ENDIAN / "ut.stn11.a2_c50_n.sac"),
        'Z': str(SAC_BIG_ENDIAN / "ut.stn11.a2_c50_z.sac")
    }


@pytest.fixture
def sac_files_little_endian():
    """Paths to SAC files (little endian)."""
    return {
        'E': str(SAC_LITTLE_ENDIAN / "ut.stn11.a2_c50_e.sac"),
        'N': str(SAC_LITTLE_ENDIAN / "ut.stn11.a2_c50_n.sac"),
        'Z': str(SAC_LITTLE_ENDIAN / "ut.stn11.a2_c50_z.sac")
    }


@pytest.fixture
def synthetic_seismic_data():
    """Generate synthetic seismic data for testing edge cases."""
    from hvsr_pro.core.data_structures import SeismicData, ComponentData
    
    sampling_rate = 100.0
    duration = 60.0  # 60 seconds
    n_samples = int(duration * sampling_rate)
    t = np.arange(n_samples) / sampling_rate
    
    # Generate synthetic signal with a resonance peak at 2 Hz
    freq_resonance = 2.0
    signal_e = np.sin(2 * np.pi * freq_resonance * t) + 0.1 * np.random.randn(n_samples)
    signal_n = np.sin(2 * np.pi * freq_resonance * t + 0.1) + 0.1 * np.random.randn(n_samples)
    signal_z = 0.5 * np.sin(2 * np.pi * freq_resonance * t) + 0.05 * np.random.randn(n_samples)
    
    east = ComponentData(name='E', data=signal_e, sampling_rate=sampling_rate)
    north = ComponentData(name='N', data=signal_n, sampling_rate=sampling_rate)
    vertical = ComponentData(name='Z', data=signal_z, sampling_rate=sampling_rate)
    
    return SeismicData(east=east, north=north, vertical=vertical)


@pytest.fixture
def empty_data():
    """Generate empty seismic data for edge case testing."""
    # Note: ComponentData validates that data cannot be empty, so this fixture
    # tests whether the validation works properly
    return None  # Will test the validation directly in tests


@pytest.fixture
def very_short_data():
    """Generate very short seismic data (edge case)."""
    from hvsr_pro.core.data_structures import SeismicData, ComponentData
    
    sampling_rate = 100.0
    n_samples = 10  # Very short - less than typical window
    
    east = ComponentData(name='E', data=np.random.randn(n_samples), sampling_rate=sampling_rate)
    north = ComponentData(name='N', data=np.random.randn(n_samples), sampling_rate=sampling_rate)
    vertical = ComponentData(name='Z', data=np.random.randn(n_samples), sampling_rate=sampling_rate)
    
    return SeismicData(east=east, north=north, vertical=vertical)


@pytest.fixture
def zero_vertical_data():
    """Generate data with zero vertical component (division by zero test)."""
    from hvsr_pro.core.data_structures import SeismicData, ComponentData
    
    sampling_rate = 100.0
    n_samples = 6000
    
    # Use very small values instead of zeros to pass ComponentData validation
    east = ComponentData(name='E', data=np.random.randn(n_samples), sampling_rate=sampling_rate)
    north = ComponentData(name='N', data=np.random.randn(n_samples), sampling_rate=sampling_rate)
    vertical = ComponentData(name='Z', data=np.ones(n_samples) * 1e-15, sampling_rate=sampling_rate)
    
    return SeismicData(east=east, north=north, vertical=vertical)


@pytest.fixture
def flat_spectrum_data():
    """Generate data that produces flat HVSR (no peaks)."""
    from hvsr_pro.core.data_structures import SeismicData, ComponentData
    
    sampling_rate = 100.0
    n_samples = 6000
    
    # White noise - should produce flat H/V
    np.random.seed(42)
    east = ComponentData(name='E', data=np.random.randn(n_samples), sampling_rate=sampling_rate)
    north = ComponentData(name='N', data=np.random.randn(n_samples), sampling_rate=sampling_rate)
    vertical = ComponentData(name='Z', data=np.random.randn(n_samples), sampling_rate=sampling_rate)
    
    return SeismicData(east=east, north=north, vertical=vertical)
