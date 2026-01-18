"""
MiniShark Data Loader
=====================

Loader for MiniShark seismometer format files.
"""

import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any
import logging

from hvsr_pro.loaders.base_loader import BaseDataLoader
from hvsr_pro.loaders.patterns import (
    MSHARK_NPTS, MSHARK_FS, MSHARK_GAIN, MSHARK_CONVERSION, MSHARK_DATA_ROW
)
from hvsr_pro.core.data_structures import SeismicData, ComponentData

logger = logging.getLogger(__name__)


class MiniSharkLoader(BaseDataLoader):
    """
    Loader for MiniShark format files.
    
    MiniShark is a compact seismometer that records data in a 
    tab-separated text format with metadata headers.
    
    File format:
        #Sample number: <npts>
        #Sample rate (sps): <fs>
        #Gain: <gain>
        #Conversion factor: <conversion>
        ... (other headers)
        <vt>	<ns>	<ew>   (tab-separated data rows)
        ...
    
    The data columns are: Vertical, North-South, East-West.
    Raw values are converted by dividing by gain and conversion factor.
    
    Example:
        >>> loader = MiniSharkLoader()
        >>> data = loader.load_file('0003_181115_0441.minishark')
        >>> print(data.duration)
        3600.0
    """
    
    def __init__(self, degrees_from_north: Optional[float] = None):
        """
        Initialize MiniShark loader.
        
        Args:
            degrees_from_north: Sensor orientation (default 0.0 - aligned with north)
        """
        super().__init__()
        self.loader_name = "MiniSharkLoader"
        self.supported_extensions = ['.minishark']
        self.degrees_from_north = degrees_from_north if degrees_from_north is not None else 0.0
    
    def can_load(self, filepath: str) -> bool:
        """
        Check if this loader can handle the file.
        
        Args:
            filepath: Path to file
            
        Returns:
            True if file is MiniShark format
        """
        path = Path(filepath)
        
        # Check extension
        if path.suffix.lower() != '.minishark':
            return False
        
        # Verify header structure
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                text = f.read(2000)  # Read first 2KB for header check
            
            # Check for required headers
            if MSHARK_NPTS.search(text) and MSHARK_FS.search(text):
                return True
                
        except Exception:
            pass
        
        return False
    
    def load_file(self, filepath: str, **kwargs) -> SeismicData:
        """
        Load seismic data from MiniShark file.
        
        Args:
            filepath: Path to .minishark file
            **kwargs: Additional options
                - degrees_from_north: Override sensor orientation
            
        Returns:
            SeismicData object with E, N, Z components
            
        Raises:
            ValueError: If file format is invalid
            FileNotFoundError: If file doesn't exist
        """
        self.validate_file(filepath)
        
        # Get orientation
        degrees_from_north = kwargs.get('degrees_from_north', self.degrees_from_north)
        if degrees_from_north is None:
            degrees_from_north = 0.0
        
        # Read file content
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()
        
        # Extract header values
        npts_match = MSHARK_NPTS.search(text)
        fs_match = MSHARK_FS.search(text)
        gain_match = MSHARK_GAIN.search(text)
        conversion_match = MSHARK_CONVERSION.search(text)
        
        if not npts_match or not fs_match:
            raise ValueError("Invalid MiniShark file: missing required headers")
        
        npts_header = int(npts_match.group(1))
        sampling_rate = float(fs_match.group(1))
        gain = int(gain_match.group(1)) if gain_match else 1
        conversion = int(conversion_match.group(1)) if conversion_match else 1
        
        logger.info(f"MiniShark header: npts={npts_header}, fs={sampling_rate}, gain={gain}, conversion={conversion}")
        
        # Parse data rows
        data_array = np.empty((npts_header, 3), dtype=np.float32)
        
        idx = 0
        for match in MSHARK_DATA_ROW.finditer(text):
            if idx >= npts_header:
                break
            vt, ns, ew = match.groups()
            data_array[idx, 0] = float(vt)
            data_array[idx, 1] = float(ns)
            data_array[idx, 2] = float(ew)
            idx += 1
        
        # Verify sample count
        if idx != npts_header:
            logger.warning(f"Sample count mismatch: header={npts_header}, found={idx}")
        
        # Apply gain and conversion corrections
        data_array = data_array / gain / conversion
        
        # Extract components: columns are VT, NS, EW
        vt_data = data_array[:idx, 0]
        ns_data = data_array[:idx, 1]
        ew_data = data_array[:idx, 2]
        
        # Create component data objects
        # Note: E=East-West, N=North-South, Z=Vertical
        east = ComponentData(
            name='E',
            data=ew_data.astype(np.float64),
            sampling_rate=sampling_rate
        )
        
        north = ComponentData(
            name='N',
            data=ns_data.astype(np.float64),
            sampling_rate=sampling_rate
        )
        
        vertical = ComponentData(
            name='Z',
            data=vt_data.astype(np.float64),
            sampling_rate=sampling_rate
        )
        
        # Create SeismicData
        data = SeismicData(
            east=east,
            north=north,
            vertical=vertical,
            station_name=Path(filepath).stem,
            source_file=str(filepath)
        )
        
        logger.info(f"Loaded MiniShark file: {idx} samples, {sampling_rate} Hz, {data.duration:.1f}s duration")
        
        return data
