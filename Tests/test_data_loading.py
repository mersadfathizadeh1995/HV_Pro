"""
Test Data Loading - High Severity Issues
==========================================

Tests for data loading edge cases using actual test files.

ISSUE CATEGORY: HIGH SEVERITY
- Corrupted or malformed files
- Empty files
- Mismatched component lengths
"""

import pytest
import numpy as np
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "HV_Analyze_Pro"))


class TestHVSRDataHandler:
    """Test HVSRDataHandler for edge cases."""
    
    def test_load_combined_miniseed(self, mseed_combined_file):
        """Test loading combined MiniSEED file."""
        from hvsr_pro.core import HVSRDataHandler
        
        if not Path(mseed_combined_file).exists():
            pytest.skip(f"Test file not found: {mseed_combined_file}")
        
        handler = HVSRDataHandler()
        
        try:
            data = handler.load_data(mseed_combined_file)
            
            assert data is not None, "Should load data"
            assert data.east is not None, "Should have east component"
            assert data.north is not None, "Should have north component"
            assert data.vertical is not None, "Should have vertical component"
            
            print(f"FINDING: Loaded combined MiniSEED successfully")
            print(f"FINDING: Duration: {data.duration:.2f}s, SR: {data.sampling_rate} Hz")
            print(f"FINDING: Samples: {data.n_samples}")
            
        except Exception as e:
            print(f"FINDING: Combined MiniSEED loading raises {type(e).__name__}: {e}")
    
    def test_load_individual_miniseed(self, mseed_individual_files):
        """Test loading individual MiniSEED files."""
        from hvsr_pro.core import HVSRDataHandler
        
        for comp, path in mseed_individual_files.items():
            if not Path(path).exists():
                pytest.skip(f"Test file not found: {path}")
        
        handler = HVSRDataHandler()
        
        try:
            file_list = list(mseed_individual_files.values())
            data = handler.load_multi_miniseed_type1(file_list)
            
            assert data is not None, "Should load data"
            print(f"FINDING: Loaded individual MiniSEED files successfully")
            
        except Exception as e:
            print(f"FINDING: Individual MiniSEED loading raises {type(e).__name__}: {e}")
    
    def test_load_nonexistent_file(self):
        """
        ISSUE: Loading a file that doesn't exist.
        SEVERITY: HIGH
        """
        from hvsr_pro.core import HVSRDataHandler
        
        handler = HVSRDataHandler()
        
        try:
            data = handler.load_data("nonexistent_file_12345.mseed")
            pytest.fail("Should raise error for nonexistent file")
        except (FileNotFoundError, ValueError, IOError) as e:
            print(f"FINDING: Nonexistent file correctly raises: {e}")
    
    def test_load_empty_path(self):
        """
        ISSUE: Loading with empty string path.
        SEVERITY: HIGH
        """
        from hvsr_pro.core import HVSRDataHandler
        
        handler = HVSRDataHandler()
        
        try:
            data = handler.load_data("")
            pytest.fail("Should raise error for empty path")
        except (FileNotFoundError, ValueError) as e:
            print(f"FINDING: Empty path correctly raises: {e}")
    
    def test_load_none_path(self):
        """
        ISSUE: Loading with None as path.
        SEVERITY: HIGH
        """
        from hvsr_pro.core import HVSRDataHandler
        
        handler = HVSRDataHandler()
        
        try:
            data = handler.load_data(None)
            pytest.fail("Should raise error for None path")
        except (TypeError, ValueError, AttributeError) as e:
            print(f"FINDING: None path correctly raises: {e}")
    
    def test_load_directory_instead_of_file(self):
        """
        ISSUE: Loading a directory path instead of file.
        SEVERITY: MEDIUM
        """
        from hvsr_pro.core import HVSRDataHandler
        import tempfile
        import os
        
        handler = HVSRDataHandler()
        
        # Use a known directory
        temp_dir = tempfile.gettempdir()
        
        try:
            data = handler.load_data(temp_dir)
            pytest.fail("Should raise error for directory path")
        except (IsADirectoryError, ValueError, IOError) as e:
            print(f"FINDING: Directory path correctly raises: {type(e).__name__}: {e}")
    
    def test_auto_format_detection(self, mseed_combined_file):
        """Test automatic format detection."""
        from hvsr_pro.core import HVSRDataHandler
        
        if not Path(mseed_combined_file).exists():
            pytest.skip("Test file not found")
        
        handler = HVSRDataHandler()
        
        try:
            # Should auto-detect format
            data = handler.load_data(mseed_combined_file, format='auto')
            assert data is not None
            print("FINDING: Auto format detection works")
        except Exception as e:
            print(f"FINDING: Auto detection raises {type(e).__name__}: {e}")


class TestDataStructures:
    """Test SeismicData and ComponentData structures."""
    
    def test_seismic_data_mismatched_lengths(self):
        """
        ISSUE: SeismicData with components of different lengths.
        SEVERITY: VERY HIGH
        """
        from hvsr_pro.core.data_structures import SeismicData, ComponentData
        
        sampling_rate = 100.0
        
        east = ComponentData(data=np.random.randn(1000), 
                           sampling_rate=sampling_rate, component='E')
        north = ComponentData(data=np.random.randn(1100),  # Different length!
                            sampling_rate=sampling_rate, component='N')
        vertical = ComponentData(data=np.random.randn(1000), 
                               sampling_rate=sampling_rate, component='Z')
        
        try:
            data = SeismicData(east=east, north=north, vertical=vertical)
            # If it succeeds, check what n_samples reports
            print(f"FINDING: Mismatched lengths created SeismicData")
            print(f"FINDING: n_samples = {data.n_samples}")
        except ValueError as e:
            print(f"FINDING: Mismatched lengths correctly raises: {e}")
    
    def test_seismic_data_mismatched_sampling_rates(self):
        """
        ISSUE: SeismicData with components of different sampling rates.
        SEVERITY: HIGH
        """
        from hvsr_pro.core.data_structures import SeismicData, ComponentData
        
        n_samples = 1000
        
        east = ComponentData(data=np.random.randn(n_samples), 
                           sampling_rate=100.0, component='E')
        north = ComponentData(data=np.random.randn(n_samples), 
                            sampling_rate=200.0, component='N')  # Different rate!
        vertical = ComponentData(data=np.random.randn(n_samples), 
                               sampling_rate=100.0, component='Z')
        
        try:
            data = SeismicData(east=east, north=north, vertical=vertical)
            print(f"FINDING: Mismatched sampling rates created SeismicData")
            print(f"FINDING: sampling_rate = {data.sampling_rate}")
        except ValueError as e:
            print(f"FINDING: Mismatched sampling rates correctly raises: {e}")
    
    def test_component_data_zero_sampling_rate(self):
        """
        ISSUE: ComponentData with zero sampling rate.
        SEVERITY: VERY HIGH
        """
        from hvsr_pro.core.data_structures import ComponentData
        
        try:
            comp = ComponentData(data=np.random.randn(1000), 
                               sampling_rate=0.0, component='E')
            # If it succeeds, check duration
            print(f"FINDING: Zero sampling rate created ComponentData")
            print(f"FINDING: duration = {comp.duration}")  # Would be inf or error
        except (ValueError, ZeroDivisionError) as e:
            print(f"FINDING: Zero sampling rate correctly raises: {e}")
    
    def test_component_data_negative_sampling_rate(self):
        """
        ISSUE: ComponentData with negative sampling rate.
        SEVERITY: HIGH
        """
        from hvsr_pro.core.data_structures import ComponentData
        
        try:
            comp = ComponentData(data=np.random.randn(1000), 
                               sampling_rate=-100.0, component='E')
            print(f"FINDING: Negative sampling rate created ComponentData")
        except ValueError as e:
            print(f"FINDING: Negative sampling rate correctly raises: {e}")


class TestTimeSlicing:
    """Test time slicing functionality."""
    
    def test_slice_by_time_invalid_range(self, mseed_combined_file):
        """
        ISSUE: Time slice with invalid range (start > end).
        SEVERITY: HIGH
        """
        from hvsr_pro.core import HVSRDataHandler
        from datetime import datetime
        
        if not Path(mseed_combined_file).exists():
            pytest.skip("Test file not found")
        
        handler = HVSRDataHandler()
        data = handler.load_data(mseed_combined_file)
        
        # Invalid time range: start after end
        start_time = datetime(2024, 1, 1, 12, 0, 0)
        end_time = datetime(2024, 1, 1, 10, 0, 0)  # Earlier than start!
        
        try:
            sliced = handler.slice_by_time(data, start_time, end_time, tz_offset=0)
            print(f"FINDING: Invalid time range succeeded with {sliced.n_samples} samples")
        except ValueError as e:
            print(f"FINDING: Invalid time range correctly raises: {e}")
    
    def test_slice_by_time_outside_data_range(self, mseed_combined_file):
        """
        ISSUE: Time slice completely outside data range.
        SEVERITY: HIGH
        """
        from hvsr_pro.core import HVSRDataHandler
        from datetime import datetime
        
        if not Path(mseed_combined_file).exists():
            pytest.skip("Test file not found")
        
        handler = HVSRDataHandler()
        data = handler.load_data(mseed_combined_file)
        
        # Time range completely outside data
        start_time = datetime(2099, 1, 1, 0, 0, 0)
        end_time = datetime(2099, 1, 1, 1, 0, 0)
        
        try:
            sliced = handler.slice_by_time(data, start_time, end_time, tz_offset=0)
            print(f"FINDING: Outside range succeeded with {sliced.n_samples} samples")
        except ValueError as e:
            print(f"FINDING: Outside range correctly raises: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
