"""
SeismicRecording3C JSON Loader
==============================

Loader for hvsrpy's SeismicRecording3C JSON serialization format.
"""

import json
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any
import logging

from hvsr_pro.loaders.base_loader import BaseDataLoader
from hvsr_pro.core.data_structures import SeismicData, ComponentData

logger = logging.getLogger(__name__)


class SeismicRecording3CLoader(BaseDataLoader):
    """
    Loader for hvsrpy's SeismicRecording3C JSON format.
    
    This format is hvsrpy's native serialization for 3-component
    seismic recordings. Files are JSON with the following structure:
    
    {
        "dt_in_seconds": <float>,      # Time step (1/sampling_rate)
        "ns_amplitude": [<floats>],    # North-South amplitudes
        "ew_amplitude": [<floats>],    # East-West amplitudes
        "vt_amplitude": [<floats>],    # Vertical amplitudes
        "degrees_from_north": <float>, # Sensor orientation
        "meta": {<metadata>}           # Additional metadata
    }
    
    Example:
        >>> loader = SeismicRecording3CLoader()
        >>> data = loader.load_file('ut.stn11.a2_c50.json')
        >>> print(data.duration)
        7200.0
    """
    
    def __init__(self):
        """Initialize SeismicRecording3C loader."""
        super().__init__()
        self.loader_name = "SeismicRecording3CLoader"
        self.supported_extensions = ['.json']
    
    def can_load(self, filepath: str) -> bool:
        """
        Check if this loader can handle the file.
        
        Args:
            filepath: Path to file
            
        Returns:
            True if file is SeismicRecording3C JSON format
        """
        path = Path(filepath)
        
        # Check extension
        if path.suffix.lower() != '.json':
            return False
        
        # Verify JSON structure
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check for required keys
            required_keys = ['dt_in_seconds', 'ns_amplitude', 'ew_amplitude', 'vt_amplitude']
            if all(key in data for key in required_keys):
                return True
                
        except (json.JSONDecodeError, Exception):
            pass
        
        return False
    
    def load_file(self, filepath: str, **kwargs) -> SeismicData:
        """
        Load seismic data from SeismicRecording3C JSON file.
        
        Args:
            filepath: Path to .json file
            **kwargs: Additional options (currently unused)
            
        Returns:
            SeismicData object with E, N, Z components
            
        Raises:
            ValueError: If file format is invalid
            FileNotFoundError: If file doesn't exist
        """
        self.validate_file(filepath)
        
        # Read JSON content
        with open(filepath, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        # Validate required fields
        required_keys = ['dt_in_seconds', 'ns_amplitude', 'ew_amplitude', 'vt_amplitude']
        missing = [k for k in required_keys if k not in json_data]
        if missing:
            raise ValueError(f"Invalid SeismicRecording3C JSON: missing keys {missing}")
        
        # Extract data
        dt = json_data['dt_in_seconds']
        sampling_rate = 1.0 / dt
        
        ns_amplitude = np.array(json_data['ns_amplitude'], dtype=np.float64)
        ew_amplitude = np.array(json_data['ew_amplitude'], dtype=np.float64)
        vt_amplitude = np.array(json_data['vt_amplitude'], dtype=np.float64)
        
        degrees_from_north = json_data.get('degrees_from_north', 0.0)
        meta = json_data.get('meta', {})
        
        logger.info(f"SeismicRecording3C: {len(ns_amplitude)} samples, {sampling_rate:.1f} Hz, orientation={degrees_from_north}")
        
        # Create component data objects
        # Map: NS -> North, EW -> East, VT -> Vertical/Z
        east = ComponentData(
            name='E',
            data=ew_amplitude,
            sampling_rate=sampling_rate
        )
        
        north = ComponentData(
            name='N',
            data=ns_amplitude,
            sampling_rate=sampling_rate
        )
        
        vertical = ComponentData(
            name='Z',
            data=vt_amplitude,
            sampling_rate=sampling_rate
        )
        
        # Extract station name from metadata or filename
        station = meta.get('station') or Path(filepath).stem
        
        # If meta has 'file name(s)', use that for source info
        source_files = meta.get('file name(s)')
        if isinstance(source_files, list):
            source_file = ', '.join(str(f) for f in source_files)
        elif source_files:
            source_file = str(source_files)
        else:
            source_file = str(filepath)
        
        # Create SeismicData
        data = SeismicData(
            east=east,
            north=north,
            vertical=vertical,
            station_name=station,
            source_file=source_file
        )
        
        # Store additional metadata
        data.metadata = {
            'degrees_from_north': degrees_from_north,
            'original_meta': meta,
            'format': 'seismic_recording_3c'
        }
        
        logger.info(f"Loaded SeismicRecording3C: {data.duration:.1f}s duration")
        
        return data
