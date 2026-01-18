"""
SAF (SESAME ASCII Format) Loader
================================

Loads seismic data from SESAME ASCII format files.
Reference: http://sesame.geopsy.org/Delivrables/D09-03_Texte.pdf
"""

import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import logging

from hvsr_pro.loaders.base_loader import BaseDataLoader
from hvsr_pro.loaders.config import SAFConfig
from hvsr_pro.loaders.patterns import (
    SAF_VERSION, SAF_NPTS, SAF_FS, SAF_V_CH, SAF_N_CH, SAF_E_CH,
    SAF_NORTH_ROT, SAF_DATA_ROW, extract_saf_header
)
from hvsr_pro.core.data_structures import SeismicData, ComponentData

logger = logging.getLogger(__name__)


class SAFLoader(BaseDataLoader):
    """
    Loader for SESAME ASCII Format (SAF) files.
    
    SAF is a standard format defined by the SESAME project for storing
    three-component ambient vibration recordings. The format includes:
    - Header with metadata (sampling rate, number of points, channel IDs)
    - NORTH_ROT field for sensor orientation
    - Three columns of data (V, N, E or permutation based on CH*_ID)
    
    Example SAF header:
        SESAME ASCII data format (saf) v. 1
        SAMP_FREQ = 50
        NDAT = 45000
        CH0_ID = V
        CH1_ID = N
        CH2_ID = E
        NORTH_ROT = 0
    """
    
    def __init__(self):
        """Initialize SAF loader."""
        super().__init__()
        self.supported_extensions = ['.saf']
        self.loader_name = "SAFLoader"
    
    def can_load(self, filepath: str) -> bool:
        """
        Check if file is SAF format.
        
        Args:
            filepath: Path to file
            
        Returns:
            True if file appears to be SAF format
        """
        path = Path(filepath)
        
        # Check extension
        if path.suffix.lower() not in self.supported_extensions:
            return False
        
        # Try to read and verify SAF header
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                first_lines = f.read(500)
            
            # Check for SAF version line
            if SAF_VERSION.search(first_lines):
                return True
                
        except Exception:
            pass
        
        return False
    
    def load_file(self, filepath: str, config: SAFConfig = None, **kwargs) -> SeismicData:
        """
        Load SAF file.
        
        Args:
            filepath: Path to SAF file
            config: Optional SAFConfig with loading options
            **kwargs: Additional options (for compatibility)
            
        Returns:
            SeismicData object with loaded data
            
        Raises:
            ValueError: If file format is invalid
            FileNotFoundError: If file doesn't exist
        """
        # Use default config if not provided
        if config is None:
            config = SAFConfig(
                degrees_from_north=kwargs.get('degrees_from_north'),
                verbose=kwargs.get('verbose', False)
            )
        
        # Validate file
        self.validate_file(filepath)
        
        if config.verbose:
            logger.info(f"Loading SAF file: {filepath}")
        
        # Read file content
        with open(filepath, 'r', encoding='utf-8') as f:
            text = f.read()
        
        # Verify SAF format
        if not SAF_VERSION.search(text):
            raise ValueError(f"File does not appear to be SAF format: {filepath}")
        
        # Extract header
        header = extract_saf_header(text)
        
        if 'npts' not in header:
            raise ValueError("SAF file missing NDAT (number of points)")
        if 'sampling_rate' not in header:
            raise ValueError("SAF file missing SAMP_FREQ (sampling frequency)")
        
        npts = header['npts']
        sampling_rate = header['sampling_rate']
        
        # Get channel mapping (which column is V, N, E)
        v_ch = header.get('v_channel', 0)  # Default: column 0 = V
        n_ch = header.get('n_channel', 1)  # Default: column 1 = N
        e_ch = header.get('e_channel', 2)  # Default: column 2 = E
        
        # Get orientation
        if config.degrees_from_north is not None:
            degrees_from_north = config.degrees_from_north
        else:
            degrees_from_north = header.get('north_rot', 0.0)
            # Adjust based on which channel is in position 1
            if n_ch == 1:
                pass  # NORTH_ROT applies directly
            elif e_ch == 1:
                degrees_from_north += 90.0
        
        # Parse data
        data = np.empty((npts, 3), dtype=np.float64)
        
        idx = 0
        for match in SAF_DATA_ROW.finditer(text):
            if idx >= npts:
                break
            channels = match.groups()
            data[idx, 0] = float(channels[0])
            data[idx, 1] = float(channels[1])
            data[idx, 2] = float(channels[2])
            idx += 1
        
        if idx != npts:
            logger.warning(
                f"SAF header specifies {npts} points, but found {idx}. "
                f"Using {idx} points."
            )
            data = data[:idx]
        
        # Extract components based on channel mapping
        vt_data = data[:, v_ch]
        ns_data = data[:, n_ch]
        ew_data = data[:, e_ch]
        
        # Parse start time if available
        start_time = None
        if 'start_time_str' in header:
            try:
                start_time = datetime.strptime(
                    header['start_time_str'],
                    "%Y %m %d %H %M %S.%f"
                )
            except ValueError:
                pass
        
        # Create ComponentData objects
        east = ComponentData(
            name='E',
            data=ew_data,
            sampling_rate=sampling_rate,
            start_time=start_time,
            units='counts',
            metadata={'channel_index': e_ch}
        )
        
        north = ComponentData(
            name='N',
            data=ns_data,
            sampling_rate=sampling_rate,
            start_time=start_time,
            units='counts',
            metadata={'channel_index': n_ch}
        )
        
        vertical = ComponentData(
            name='Z',
            data=vt_data,
            sampling_rate=sampling_rate,
            start_time=start_time,
            units='counts',
            metadata={'channel_index': v_ch}
        )
        
        # Create SeismicData
        seismic_data = SeismicData(
            east=east,
            north=north,
            vertical=vertical,
            station_name=header.get('sta_code', 'UNKNOWN'),
            source_file=filepath,
            metadata={
                'format': 'SAF',
                'loader': self.loader_name,
                'degrees_from_north': degrees_from_north,
                'saf_version': header.get('version'),
                **header
            }
        )
        
        if config.verbose:
            logger.info(
                f"Loaded SAF: {idx} samples @ {sampling_rate} Hz, "
                f"rotation={degrees_from_north}°"
            )
        
        return seismic_data
    
    def get_file_preview(self, filepath: str, n_lines: int = 30) -> str:
        """
        Get preview of SAF file header.
        
        Args:
            filepath: Path to file
            n_lines: Number of header lines to preview
            
        Returns:
            String with file preview
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = [f.readline() for _ in range(n_lines)]
        
        return ''.join(lines)
