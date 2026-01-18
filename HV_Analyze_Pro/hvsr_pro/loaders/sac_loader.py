"""
SAC (Seismic Analysis Code) Loader
==================================

Loads seismic data from SAC format files.
Requires 3 separate files (one per component).
Reference: https://ds.iris.edu/files/sac-manual/sac_manual.pdf
"""

import warnings
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import logging

try:
    from obspy import read, Stream
    HAS_OBSPY = True
except ImportError:
    HAS_OBSPY = False

from hvsr_pro.loaders.base_loader import BaseDataLoader
from hvsr_pro.loaders.config import SACConfig
from hvsr_pro.loaders.orientation import orient_traces, trim_traces
from hvsr_pro.core.data_structures import SeismicData, ComponentData

logger = logging.getLogger(__name__)


class SACLoader(BaseDataLoader):
    """
    Loader for SAC (Seismic Analysis Code) format files.
    
    SAC is a standard format that stores one trace per file, so
    three-component recordings require three separate files.
    The loader handles both little-endian and big-endian byte orders.
    
    Usage:
        loader = SACLoader()
        data = loader.load_file([
            'recording_e.sac',
            'recording_n.sac',
            'recording_z.sac'
        ])
    """
    
    def __init__(self):
        """Initialize SAC loader."""
        super().__init__()
        self.supported_extensions = ['.sac']
        self.loader_name = "SACLoader"
        
        if not HAS_OBSPY:
            raise ImportError(
                "ObsPy is required for SAC support. "
                "Install with: pip install obspy"
            )
    
    def can_load(self, filepath: str) -> bool:
        """
        Check if file is SAC format.
        
        Args:
            filepath: Path to file
            
        Returns:
            True if file appears to be SAC format
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
                st = read(filepath, headonly=True, format='SAC')
            return len(st) > 0
        except Exception:
            return False
    
    def load_file(
        self,
        filepaths: Union[str, List[str]],
        config: SACConfig = None,
        **kwargs
    ) -> SeismicData:
        """
        Load SAC files.
        
        Args:
            filepaths: List of 3 SAC file paths (one per component)
            config: Optional SACConfig with loading options
            **kwargs: Additional options (for compatibility)
            
        Returns:
            SeismicData object with loaded data
            
        Raises:
            ValueError: If not exactly 3 files provided or format is invalid
            FileNotFoundError: If any file doesn't exist
        """
        # Handle single file path (convert to list)
        if isinstance(filepaths, (str, Path)):
            raise ValueError(
                "SAC format requires 3 separate files (one per component). "
                "Please provide a list of 3 file paths."
            )
        
        if len(filepaths) != 3:
            raise ValueError(
                f"SAC format requires exactly 3 files, got {len(filepaths)}"
            )
        
        # Use default config if not provided
        if config is None:
            config = SACConfig(
                degrees_from_north=kwargs.get('degrees_from_north'),
                byteorder=kwargs.get('byteorder', 'auto'),
                verbose=kwargs.get('verbose', False)
            )
        
        if config.verbose:
            logger.info(f"Loading {len(filepaths)} SAC files...")
        
        # Load each file
        traces = []
        obspy_kwargs = {"format": "SAC"}
        
        for filepath in filepaths:
            self.validate_file(filepath)
            
            # Try loading with auto byte order detection
            if config.byteorder == 'auto':
                try:
                    obspy_kwargs["byteorder"] = "little"
                    stream = self._quiet_read(filepath, **obspy_kwargs)
                except Exception:
                    # Reset file if it's a BytesIO
                    obspy_kwargs["byteorder"] = "big"
                    stream = self._quiet_read(filepath, **obspy_kwargs)
            else:
                obspy_kwargs["byteorder"] = config.byteorder
                stream = self._quiet_read(filepath, **obspy_kwargs)
            
            if len(stream) != 1:
                raise ValueError(
                    f"Expected 1 trace per SAC file, got {len(stream)} in {filepath}"
                )
            
            traces.append(stream[0])
        
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
        
        # Create ComponentData objects
        east = ComponentData(
            name='E',
            data=ew.data.copy(),
            sampling_rate=sampling_rate,
            start_time=start_time,
            units='m/s',
            metadata={'channel': ew.stats.channel}
        )
        
        north = ComponentData(
            name='N',
            data=ns.data.copy(),
            sampling_rate=sampling_rate,
            start_time=start_time,
            units='m/s',
            metadata={'channel': ns.stats.channel}
        )
        
        vertical = ComponentData(
            name='Z',
            data=vt.data.copy(),
            sampling_rate=sampling_rate,
            start_time=start_time,
            units='m/s',
            metadata={'channel': vt.stats.channel}
        )
        
        # Create SeismicData
        seismic_data = SeismicData(
            east=east,
            north=north,
            vertical=vertical,
            station_name=ns.stats.station or 'UNKNOWN',
            source_file=f"SAC: {len(filepaths)} files",
            metadata={
                'format': 'SAC',
                'loader': self.loader_name,
                'degrees_from_north': degrees_from_north,
                'source_files': [str(f) for f in filepaths],
                'byteorder': config.byteorder
            }
        )
        
        if config.verbose:
            logger.info(
                f"Loaded SAC: {len(ns.data)} samples @ {sampling_rate} Hz, "
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
        Get SAC file information.
        
        Args:
            filepath: Path to SAC file
            
        Returns:
            Dictionary with file metadata
        """
        base_info = super().get_file_info(filepath)
        
        try:
            stream = self._quiet_read(filepath, format='SAC', headonly=True)
            if len(stream) > 0:
                stats = stream[0].stats
                base_info.update({
                    'station': stats.station,
                    'channel': stats.channel,
                    'sampling_rate': stats.sampling_rate,
                    'npts': stats.npts,
                    'starttime': str(stats.starttime),
                    'endtime': str(stats.endtime)
                })
        except Exception as e:
            base_info['read_error'] = str(e)
        
        return base_info
