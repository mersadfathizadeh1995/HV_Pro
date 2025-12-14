"""
Main data handler for HVSR Pro
===============================

Unified interface for loading all supported seismic data formats.
"""

from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime, timedelta
import logging

from hvsr_pro.core.data_structures import SeismicData, ComponentData
from hvsr_pro.core.metadata import MetadataManager
from hvsr_pro.core.data_cache import DataCache
from hvsr_pro.loaders.base_loader import BaseDataLoader
from hvsr_pro.loaders.txt_loader import TxtDataLoader
from hvsr_pro.loaders.miniseed_loader import MiniSeedLoader

# Setup logging
logger = logging.getLogger(__name__)


class HVSRDataHandler:
    """
    Universal data handler for HVSR analysis.
    
    Features:
    - Auto-detection of file formats
    - Multiple format support (ASCII txt, MiniSEED, etc.)
    - Data caching for performance
    - Metadata preservation
    - Batch loading capabilities
    
    Example:
        >>> handler = HVSRDataHandler()
        >>> data = handler.load_data('XX01_pt1_raw.txt')
        >>> print(data)
        SeismicData(station='XX01', samples=3600000, rate=200.0 Hz)
    """
    
    def __init__(self, 
                 use_cache: bool = True,
                 cache_size_mb: float = 1000):
        """
        Initialize data handler.
        
        Args:
            use_cache: Enable data caching (default: True)
            cache_size_mb: Maximum cache size in megabytes
        """
        self.metadata_manager = MetadataManager()
        self.cache = DataCache(max_memory_mb=cache_size_mb) if use_cache else None
        
        # Initialize loaders
        self.loaders: Dict[str, BaseDataLoader] = {
            'txt': TxtDataLoader(),
            'miniseed': MiniSeedLoader(),
        }
        
        logger.info(f"HVSR Data Handler initialized with loaders: {list(self.loaders.keys())}")
    
    def load_data(self, filepath: str, 
                  format: str = 'auto',
                  use_cache: bool = True,
                  **kwargs) -> SeismicData:
        """
        Load seismic data from file.
        
        Args:
            filepath: Path to data file
            format: Format hint ('auto', 'txt', 'miniseed')
            use_cache: Use cached data if available
            **kwargs: Loader-specific options
            
        Returns:
            SeismicData object
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If format is unsupported
        """
        # Check cache first
        if use_cache and self.cache:
            cached_data = self.cache.get(filepath)
            if cached_data is not None:
                logger.info(f"Loaded from cache: {filepath}")
                return cached_data
        
        # Detect format if auto
        if format == 'auto':
            format = self._detect_format(filepath)
            logger.info(f"Auto-detected format: {format}")
        
        # Get appropriate loader
        loader = self._get_loader(format)
        
        # Load data
        logger.info(f"Loading {filepath} with {loader.loader_name}")
        data = loader.load_file(filepath, **kwargs)
        
        # Cache result
        if use_cache and self.cache:
            self.cache.put(filepath, data)
        
        return data
    
    def load_multiple(self, 
                     filepaths: List[str],
                     format: str = 'auto',
                     **kwargs) -> List[SeismicData]:
        """
        Load multiple files.
        
        Args:
            filepaths: List of file paths
            format: Format hint for all files
            **kwargs: Loader options
            
        Returns:
            List of SeismicData objects
        """
        results = []
        
        for filepath in filepaths:
            try:
                data = self.load_data(filepath, format=format, **kwargs)
                results.append(data)
            except Exception as e:
                logger.error(f"Failed to load {filepath}: {e}")
                continue
        
        return results
    
    def load_oscar_station(self, 
                          station_dir: str,
                          time_period: str = 'day',
                          version: str = 'raw',
                          positions: Optional[List[str]] = None) -> List[SeismicData]:
        """
        Load all data for an OSCAR station.
        
        Args:
            station_dir: Path to station directory (e.g., D:/Oscar/Data/XX01)
            time_period: 'day' or 'night'
            version: 'raw' or 'corrected'
            positions: List of positions to load (e.g., ['pt1', 'pt2']).
                      If None, loads all available.
            
        Returns:
            List of SeismicData objects
        """
        station_path = Path(station_dir)
        
        # Determine subdirectory
        subdir_name = f"Few_Hours_Few_Positions_{time_period}"
        data_dir = station_path / subdir_name
        
        if not data_dir.exists():
            raise FileNotFoundError(f"Data directory not found: {data_dir}")
        
        # Find all matching files
        pattern = f"*{version}.txt"
        files = list(data_dir.glob(pattern))
        
        # Filter by positions if specified
        if positions:
            files = [f for f in files if any(pos in f.name for pos in positions)]
        
        logger.info(f"Loading {len(files)} files from {data_dir}")
        
        return self.load_multiple([str(f) for f in files], format='txt')
    
    def load_oscar_miniseed_station(self,
                                   station_dir: str,
                                   time_period: str = 'day',
                                   version: str = 'raw',
                                   positions: Optional[List[str]] = None) -> List[SeismicData]:
        """
        Load MiniSEED data for an OSCAR station.
        
        Args:
            station_dir: Path to miniseed station directory
            time_period: 'day' or 'night'
            version: 'raw' or 'corrected'
            positions: List of positions to load
            
        Returns:
            List of SeismicData objects
        """
        station_path = Path(station_dir)
        
        # Build path
        subdir = f"Few_Hours_Few_Positions_{time_period}/mseed"
        data_dir = station_path / subdir
        
        if not data_dir.exists():
            raise FileNotFoundError(f"MiniSEED directory not found: {data_dir}")
        
        # Find unique position/version combinations
        all_files = list(data_dir.glob("*.miniseed"))
        
        # Extract station and positions
        combinations = set()
        for f in all_files:
            parts = f.stem.split('_')
            if len(parts) >= 3:
                station = parts[0]
                position = parts[1]
                file_version = parts[2]
                
                if file_version == version:
                    combinations.add((station, position))
        
        # Filter by positions if specified
        if positions:
            combinations = {c for c in combinations if c[1] in positions}
        
        # Load each combination
        results = []
        for station, position in combinations:
            try:
                # Build component file map
                component_files = {}
                for comp in ['E', 'N', 'Z']:
                    filename = f"{station}_{position}_{version}_{comp}.miniseed"
                    filepath = data_dir / filename
                    if filepath.exists():
                        component_files[comp] = str(filepath)
                
                if len(component_files) == 3:
                    data = self.loaders['miniseed'].load_file(
                        str(component_files['E']),
                        component_files=component_files
                    )
                    results.append(data)
                else:
                    logger.warning(f"Incomplete component set for {station}_{position}")
                    
            except Exception as e:
                logger.error(f"Failed to load {station}_{position}: {e}")
                continue
        
        return results
    
    def _detect_format(self, filepath: str) -> str:
        """
        Auto-detect file format.
        
        Args:
            filepath: Path to file
            
        Returns:
            Format string ('txt', 'miniseed', etc.)
        """
        # Try each loader's can_load method
        for format_name, loader in self.loaders.items():
            if loader.can_load(filepath):
                return format_name
        
        # Fallback: use extension
        ext = Path(filepath).suffix.lower()
        if ext in ['.txt', '.dat', '.asc']:
            return 'txt'
        elif ext in ['.miniseed', '.mseed', '.ms']:
            return 'miniseed'
        
        raise ValueError(f"Unknown file format: {filepath}")
    
    def _get_loader(self, format: str) -> BaseDataLoader:
        """
        Get loader for specified format.
        
        Args:
            format: Format name
            
        Returns:
            Appropriate loader instance
        """
        if format not in self.loaders:
            raise ValueError(
                f"Unsupported format: {format}. "
                f"Available: {list(self.loaders.keys())}"
            )
        
        return self.loaders[format]
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported formats."""
        return list(self.loaders.keys())
    
    def clear_cache(self) -> None:
        """Clear data cache."""
        if self.cache:
            self.cache.clear()
            logger.info("Cache cleared")
    
    def load_multi_miniseed_type1(self, file_list: List[str], **kwargs) -> SeismicData:
        """
        Load and merge multiple MiniSEED files where each contains E, N, Z channels.
        
        This method is for files like:
        - AR.STN06.centaur-3_0660_20251002_180000.miniseed
        - AR.STN06.centaur-3_0660_20251002_190000.miniseed
        
        Each file contains all 3 components (E, N, Z), and they need to be merged
        chronologically to form a continuous time series.
        
        Args:
            file_list: List of MiniSEED file paths (sorted chronologically)
            **kwargs: Additional loader options
            
        Returns:
            Single SeismicData object with merged time series
            
        Raises:
            ValueError: If files have inconsistent sampling rates or components
        """
        try:
            from obspy import read, Stream
        except ImportError:
            raise ImportError("ObsPy is required for MiniSEED multi-file loading. "
                            "Install with: pip install obspy")
        
        if not file_list:
            raise ValueError("File list is empty")
        
        logger.info(f"Loading {len(file_list)} MiniSEED files (Type 1)...")
        
        # Sort files chronologically (in case they aren't already)
        file_list = sorted(file_list)
        
        # Load all files into ObsPy streams
        streams = []
        for i, filepath in enumerate(file_list):
            logger.debug(f"Loading file {i+1}/{len(file_list)}: {Path(filepath).name}")
            stream = read(filepath)
            streams.append(stream)
        
        # Merge all streams
        logger.info("Merging streams chronologically...")
        merged_stream = streams[0]
        for stream in streams[1:]:
            merged_stream += stream
        
        # Merge method 1: interpolate small gaps
        # method=-1 would error on gaps, method=1 interpolates
        merged_stream.merge(method=1, fill_value='interpolate')
        
        # Convert to SeismicData using the MiniSeed loader
        loader = self.loaders['miniseed']
        
        # Get sampling rate from first trace
        sampling_rate = merged_stream[0].stats.sampling_rate
        station = merged_stream[0].stats.station
        start_time = merged_stream[0].stats.starttime.datetime
        
        # Extract components - handle various channel naming conventions
        # Check specific patterns first (HNE, HNN, HNZ) to avoid confusion
        data_dict = {}
        for tr in merged_stream:
            channel = tr.stats.channel.upper()
            
            # Check specific 3-letter codes first
            if 'HNE' in channel:
                data_dict['east'] = tr.data
            elif 'HNN' in channel:
                data_dict['north'] = tr.data
            elif 'HNZ' in channel:
                data_dict['vertical'] = tr.data
            # Generic patterns (single letter at end)
            elif channel.endswith('E') or channel.endswith('1'):
                if 'east' not in data_dict:  # Don't overwrite HNE
                    data_dict['east'] = tr.data
            elif channel.endswith('N') or channel.endswith('2'):
                if 'north' not in data_dict:  # Don't overwrite HNN
                    data_dict['north'] = tr.data
            elif channel.endswith('Z') or channel.endswith('3'):
                if 'vertical' not in data_dict:  # Don't overwrite HNZ
                    data_dict['vertical'] = tr.data
        
        if len(data_dict) != 3:
            available = list(data_dict.keys())
            channels_str = ', '.join([tr.stats.channel for tr in merged_stream])
            raise ValueError(
                f"Expected 3 components (E, N, Z), found {len(data_dict)}: {available}\n"
                f"Available channels in file: {channels_str}"
            )
        
        # Ensure all components have the same length (trim to shortest)
        lengths = [len(data_dict['east']), len(data_dict['north']), len(data_dict['vertical'])]
        min_length = min(lengths)
        
        if not all(l == min_length for l in lengths):
            logger.warning(
                f"Component lengths differ: E={lengths[0]}, N={lengths[1]}, Z={lengths[2]}. "
                f"Trimming to shortest: {min_length} samples"
            )
            data_dict['east'] = data_dict['east'][:min_length]
            data_dict['north'] = data_dict['north'][:min_length]
            data_dict['vertical'] = data_dict['vertical'][:min_length]
        
        # Create ComponentData objects
        east_comp = ComponentData(
            name='E',
            data=data_dict['east'],
            sampling_rate=float(sampling_rate),
            start_time=start_time
        )
        
        north_comp = ComponentData(
            name='N',
            data=data_dict['north'],
            sampling_rate=float(sampling_rate),
            start_time=start_time
        )
        
        vertical_comp = ComponentData(
            name='Z',
            data=data_dict['vertical'],
            sampling_rate=float(sampling_rate),
            start_time=start_time
        )
        
        # Create SeismicData object
        seismic_data = SeismicData(
            east=east_comp,
            north=north_comp,
            vertical=vertical_comp,
            station_name=station,
            source_file=f"{len(file_list)} files merged"
        )
        
        logger.info(f"Successfully merged {len(file_list)} files → "
                   f"{seismic_data.duration:.1f}s @ {sampling_rate}Hz")
        
        return seismic_data
    
    def load_multi_miniseed_type2(self, file_groups: Dict[str, Dict[str, Path]], 
                                   **kwargs) -> SeismicData:
        """
        Load and merge MiniSEED files where E, N, Z are in separate files.
        
        This method is for files like:
        - XX01_pt1_corrected_E.miniseed
        - XX01_pt1_corrected_N.miniseed
        - XX01_pt1_corrected_Z.miniseed
        
        Multiple groups can be loaded and merged chronologically.
        
        Args:
            file_groups: Dict mapping base_name → {'E': Path, 'N': Path, 'Z': Path}
            **kwargs: Additional loader options
            
        Returns:
            Single SeismicData object with merged data from all groups
            
        Raises:
            ValueError: If any group is incomplete (missing E, N, or Z)
        """
        try:
            from obspy import read, Stream
        except ImportError:
            raise ImportError("ObsPy is required for MiniSEED multi-file loading. "
                            "Install with: pip install obspy")
        
        if not file_groups:
            raise ValueError("No file groups provided")
        
        # Filter to complete groups only
        complete_groups = {name: files for name, files in file_groups.items()
                          if 'E' in files and 'N' in files and 'Z' in files}
        
        if not complete_groups:
            raise ValueError("No complete file groups (E+N+Z) found")
        
        logger.info(f"Loading {len(complete_groups)} file groups (Type 2)...")
        
        # Sort groups by name (often includes timestamps)
        sorted_groups = sorted(complete_groups.items())
        
        all_streams = []
        
        # Load each group
        for i, (group_name, files) in enumerate(sorted_groups):
            logger.debug(f"Loading group {i+1}/{len(sorted_groups)}: {group_name}")
            
            # Load the three component files
            e_stream = read(str(files['E']))
            n_stream = read(str(files['N']))
            z_stream = read(str(files['Z']))
            
            # Combine into single stream
            group_stream = e_stream + n_stream + z_stream
            all_streams.append(group_stream)
        
        # Merge all groups
        logger.info("Merging all groups chronologically...")
        merged_stream = all_streams[0]
        for stream in all_streams[1:]:
            merged_stream += stream
        
        # Merge traces with same channel
        merged_stream.merge(method=1, fill_value='interpolate')
        
        # Get sampling rate
        sampling_rate = merged_stream[0].stats.sampling_rate
        station = merged_stream[0].stats.station
        start_time = merged_stream[0].stats.starttime.datetime
        
        # Extract components - handle various channel naming conventions
        # Check specific patterns first (HNE, HNN, HNZ) to avoid confusion
        data_dict = {}
        for tr in merged_stream:
            channel = tr.stats.channel.upper()
            
            # Check specific 3-letter codes first
            if 'HNE' in channel:
                data_dict['east'] = tr.data
            elif 'HNN' in channel:
                data_dict['north'] = tr.data
            elif 'HNZ' in channel:
                data_dict['vertical'] = tr.data
            # Generic patterns (single letter at end)
            elif channel.endswith('E') or channel.endswith('1'):
                if 'east' not in data_dict:  # Don't overwrite HNE
                    data_dict['east'] = tr.data
            elif channel.endswith('N') or channel.endswith('2'):
                if 'north' not in data_dict:  # Don't overwrite HNN
                    data_dict['north'] = tr.data
            elif channel.endswith('Z') or channel.endswith('3'):
                if 'vertical' not in data_dict:  # Don't overwrite HNZ
                    data_dict['vertical'] = tr.data
        
        if len(data_dict) != 3:
            available = list(data_dict.keys())
            channels_str = ', '.join([tr.stats.channel for tr in merged_stream])
            raise ValueError(
                f"Expected 3 components (E, N, Z), found {len(data_dict)}: {available}\n"
                f"Available channels in file: {channels_str}"
            )
        
        # Ensure all components have the same length (trim to shortest)
        lengths = [len(data_dict['east']), len(data_dict['north']), len(data_dict['vertical'])]
        min_length = min(lengths)
        
        if not all(l == min_length for l in lengths):
            logger.warning(
                f"Component lengths differ: E={lengths[0]}, N={lengths[1]}, Z={lengths[2]}. "
                f"Trimming to shortest: {min_length} samples"
            )
            data_dict['east'] = data_dict['east'][:min_length]
            data_dict['north'] = data_dict['north'][:min_length]
            data_dict['vertical'] = data_dict['vertical'][:min_length]
        
        # Create ComponentData objects
        east_comp = ComponentData(
            name='E',
            data=data_dict['east'],
            sampling_rate=float(sampling_rate),
            start_time=start_time
        )
        
        north_comp = ComponentData(
            name='N',
            data=data_dict['north'],
            sampling_rate=float(sampling_rate),
            start_time=start_time
        )
        
        vertical_comp = ComponentData(
            name='Z',
            data=data_dict['vertical'],
            sampling_rate=float(sampling_rate),
            start_time=start_time
        )
        
        # Create SeismicData object
        seismic_data = SeismicData(
            east=east_comp,
            north=north_comp,
            vertical=vertical_comp,
            station_name=station,
            source_file=f"{len(complete_groups)} groups merged"
        )
        
        logger.info(f"Successfully merged {len(complete_groups)} groups → "
                   f"{seismic_data.duration:.1f}s @ {sampling_rate}Hz")
        
        return seismic_data
    
    def slice_by_time(self, 
                      data: SeismicData,
                      start_time: datetime,
                      end_time: datetime,
                      timezone_offset_hours: int = 0) -> SeismicData:
        """
        Extract time slice from SeismicData.
        
        This method allows you to extract a specific time range from your data,
        which is especially useful when data is recorded in GMT but you want
        to analyze a specific local time period.
        
        Args:
            data: Full SeismicData object
            start_time: Start time (in LOCAL time)
            end_time: End time (in LOCAL time)
            timezone_offset_hours: Timezone offset from GMT
                Negative for Western hemisphere (e.g., -5 for EST/CDT)
                Positive for Eastern hemisphere (e.g., +9 for JST)
        
        Returns:
            Sliced SeismicData containing only the requested time range
        
        Raises:
            ValueError: If time range is invalid or outside data bounds
        
        Example:
            >>> from datetime import datetime
            >>> # Data recorded in GMT, want 18:00-21:00 local time (UTC-5)
            >>> handler = HVSRDataHandler()
            >>> full_data = handler.load_data('recording.mseed')
            >>> 
            >>> start = datetime(2025, 10, 2, 18, 0, 0)  # 6 PM local
            >>> end = datetime(2025, 10, 2, 21, 0, 0)    # 9 PM local
            >>> sliced = handler.slice_by_time(full_data, start, end, timezone_offset_hours=-5)
            >>> print(f"Sliced to {sliced.duration/3600:.1f} hours")
        """
        logger.info(f"Slicing data by time range...")
        logger.info(f"  Local time: {start_time} to {end_time}")
        logger.info(f"  Timezone: UTC{timezone_offset_hours:+d}")
        
        # Step 1: Convert local time to GMT
        offset_delta = timedelta(hours=abs(timezone_offset_hours))
        
        if timezone_offset_hours < 0:
            # Western hemisphere: local time is behind GMT
            # To convert local → GMT, ADD the offset
            start_gmt = start_time + offset_delta
            end_gmt = end_time + offset_delta
        else:
            # Eastern hemisphere: local time is ahead of GMT
            # To convert local → GMT, SUBTRACT the offset
            start_gmt = start_time - offset_delta
            end_gmt = end_time - offset_delta
        
        logger.info(f"  GMT time: {start_gmt} to {end_gmt}")
        
        # Step 2: Validate input times
        if start_time >= end_time:
            raise ValueError(
                f"Start time ({start_time}) must be before end time ({end_time})"
            )
        
        # Step 3: Calculate elapsed time from data start
        elapsed_start = (start_gmt - data.start_time).total_seconds()
        elapsed_end = (end_gmt - data.start_time).total_seconds()
        
        logger.info(f"  Elapsed from data start: {elapsed_start:.1f}s to {elapsed_end:.1f}s")
        
        # Step 4: Validate range is within data bounds
        if elapsed_start < 0:
            raise ValueError(
                f"Start time {start_gmt} (GMT) is before data start {data.start_time} (GMT). "
                f"Requested time is {abs(elapsed_start):.1f} seconds too early."
            )
        
        if elapsed_end > data.duration:
            raise ValueError(
                f"End time {end_gmt} (GMT) exceeds data duration. "
                f"Data ends at {data.start_time + timedelta(seconds=data.duration)}, "
                f"requested time is {elapsed_end - data.duration:.1f} seconds too late."
            )
        
        # Step 5: Calculate sample indices
        sr = data.sampling_rate
        start_idx = int(elapsed_start * sr)
        end_idx = int(elapsed_end * sr)
        
        # Ensure we don't go out of bounds
        start_idx = max(0, start_idx)
        end_idx = min(len(data.east.data), end_idx)
        
        n_samples = end_idx - start_idx
        duration = n_samples / sr
        
        logger.info(f"  Sample indices: {start_idx} to {end_idx} ({n_samples} samples)")
        logger.info(f"  Sliced duration: {duration:.2f} seconds ({duration/3600:.2f} hours)")
        
        # Step 6: Slice all components
        east_sliced = ComponentData(
            name='E',
            data=data.east.data[start_idx:end_idx].copy(),
            sampling_rate=sr,
            start_time=start_gmt,
            units=data.east.units,
            metadata=data.east.metadata.copy()
        )
        
        north_sliced = ComponentData(
            name='N',
            data=data.north.data[start_idx:end_idx].copy(),
            sampling_rate=sr,
            start_time=start_gmt,
            units=data.north.units,
            metadata=data.north.metadata.copy()
        )
        
        vertical_sliced = ComponentData(
            name='Z',
            data=data.vertical.data[start_idx:end_idx].copy(),
            sampling_rate=sr,
            start_time=start_gmt,
            units=data.vertical.units,
            metadata=data.vertical.metadata.copy()
        )
        
        # Step 7: Create new SeismicData with sliced components
        sliced_data = SeismicData(
            east=east_sliced,
            north=north_sliced,
            vertical=vertical_sliced,
            station_name=data.station_name,
            source_file=f"{data.source_file} [sliced: {start_time} to {end_time} local]"
        )
        
        logger.info(f"✓ Successfully sliced data to {duration/3600:.2f} hours")
        logger.info(f"  Original: {data.duration/3600:.2f} hours → Sliced: {sliced_data.duration/3600:.2f} hours")
        
        return sliced_data
    
    def get_cache_stats(self) -> Optional[Dict[str, Any]]:
        """Get cache statistics."""
        if self.cache:
            return self.cache.get_stats()
        return None
    
    def __repr__(self) -> str:
        return f"HVSRDataHandler(loaders={list(self.loaders.keys())})"
