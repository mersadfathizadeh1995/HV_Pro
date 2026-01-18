"""
GCF (Guralp Compressed Format) Loader
=====================================

Loads seismic data from Guralp Compressed Format files.
Single file contains all 3 components.
"""

import warnings
from pathlib import Path
from typing import Dict, Any, Optional, Union
from datetime import datetime
import logging

try:
    from obspy import read, Stream
    HAS_OBSPY = True
except ImportError:
    HAS_OBSPY = False

from hvsr_pro.loaders.base_loader import BaseDataLoader
from hvsr_pro.loaders.config import GCFConfig
from hvsr_pro.loaders.orientation import orient_traces, trim_traces
from hvsr_pro.core.data_structures import SeismicData, ComponentData

logger = logging.getLogger(__name__)


class GCFLoader(BaseDataLoader):
    """
    Loader for GCF (Guralp Compressed Format) files.
    
    GCF is a proprietary format used by Guralp seismometers.
    A single GCF file typically contains all three components.
    
    Usage:
        loader = GCFLoader()
        data = loader.load_file('recording.gcf')
    """
    
    def __init__(self):
        """Initialize GCF loader."""
        super().__init__()
        self.supported_extensions = ['.gcf']
        self.loader_name = "GCFLoader"
        
        if not HAS_OBSPY:
            raise ImportError(
                "ObsPy is required for GCF support. "
                "Install with: pip install obspy"
            )
    
    def can_load(self, filepath: str) -> bool:
        """
        Check if file is GCF format.
        
        Args:
            filepath: Path to file
            
        Returns:
            True if file appears to be GCF format
        """
        if not HAS_OBSPY:
            return False
        
        path = Path(filepath)
        
        # Check extension
        if path.suffix.lower() not in self.supported_extensions:
            return False
        
        # Try to read with ObsPy
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                st = read(filepath, headonly=True, format='GCF')
            return len(st) > 0
        except Exception:
            return False
    
    def load_file(
        self,
        filepath: Union[str, Path],
        config: GCFConfig = None,
        **kwargs
    ) -> SeismicData:
        """
        Load GCF file.
        
        Args:
            filepath: Path to GCF file
            config: Optional GCFConfig with loading options
            **kwargs: Additional options (for compatibility)
            
        Returns:
            SeismicData object with loaded data
            
        Raises:
            ValueError: If file doesn't contain exactly 3 traces
            FileNotFoundError: If file doesn't exist
        """
        # Handle list input (GCF should be single file)
        if isinstance(filepath, (list, tuple)):
            if len(filepath) != 1:
                raise ValueError(
                    f"GCF format uses a single file with 3 components, "
                    f"got {len(filepath)} files"
                )
            filepath = filepath[0]
        
        # Use default config if not provided
        if config is None:
            config = GCFConfig(
                degrees_from_north=kwargs.get('degrees_from_north'),
                verbose=kwargs.get('verbose', False)
            )
        
        # Validate file
        self.validate_file(filepath)
        
        if config.verbose:
            logger.info(f"Loading GCF file: {filepath}")
        
        # Read with ObsPy
        obspy_kwargs = {"format": "GCF"}
        stream = self._quiet_read(filepath, **obspy_kwargs)
        
        if len(stream) != 3:
            raise ValueError(
                f"Expected 3 traces in GCF file, got {len(stream)}. "
                f"Available channels: {[tr.stats.channel for tr in stream]}"
            )
        
        traces = list(stream)
        
        # Orient traces (determine N, E, Z)
        ns, ew, vt, degrees_from_north = orient_traces(
            traces,
            degrees_from_north=config.degrees_from_north
        )
        
        # Trim to common time window
        trim_traces([ns, ew, vt])
        
        # Get metadata
        sampling_rate = ns.stats.sampling_rate
        start_time = ns.stats.starttime.datetime
        station = ns.stats.station or 'UNKNOWN'
        
        # Create ComponentData objects
        east = ComponentData(
            name='E',
            data=ew.data.copy(),
            sampling_rate=sampling_rate,
            start_time=start_time,
            units='counts',
            metadata={'channel': ew.stats.channel}
        )
        
        north = ComponentData(
            name='N',
            data=ns.data.copy(),
            sampling_rate=sampling_rate,
            start_time=start_time,
            units='counts',
            metadata={'channel': ns.stats.channel}
        )
        
        vertical = ComponentData(
            name='Z',
            data=vt.data.copy(),
            sampling_rate=sampling_rate,
            start_time=start_time,
            units='counts',
            metadata={'channel': vt.stats.channel}
        )
        
        # Create SeismicData
        seismic_data = SeismicData(
            east=east,
            north=north,
            vertical=vertical,
            station_name=station,
            source_file=str(filepath),
            metadata={
                'format': 'GCF',
                'loader': self.loader_name,
                'degrees_from_north': degrees_from_north,
            }
        )
        
        if config.verbose:
            logger.info(
                f"Loaded GCF: {len(ns.data)} samples @ {sampling_rate} Hz, "
                f"rotation={degrees_from_north}°"
            )
        
        return seismic_data
    
    def _quiet_read(self, filepath: str, **kwargs) -> Stream:
        """Read file with ObsPy, suppressing warnings."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return read(filepath, **kwargs)
    
    def get_file_info(self, filepath: str) -> Dict[str, Any]:
        """
        Get GCF file information.
        
        Args:
            filepath: Path to GCF file
            
        Returns:
            Dictionary with file metadata
        """
        base_info = super().get_file_info(filepath)
        
        try:
            stream = self._quiet_read(filepath, format='GCF', headonly=True)
            if len(stream) > 0:
                base_info['n_traces'] = len(stream)
                base_info['channels'] = [tr.stats.channel for tr in stream]
                
                stats = stream[0].stats
                base_info.update({
                    'station': stats.station,
                    'sampling_rate': stats.sampling_rate,
                    'npts': stats.npts,
                    'starttime': str(stats.starttime),
                    'endtime': str(stats.endtime)
                })
        except Exception as e:
            base_info['read_error'] = str(e)
        
        return base_info
