"""
MiniSEED file loader for HVSR Pro
==================================

Loads MiniSEED format files using ObsPy, handles component merging.
"""

import numpy as np
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

try:
    from obspy import read, Stream, Trace
    HAS_OBSPY = True
except ImportError:
    HAS_OBSPY = False

from hvsr_pro.loaders.base_loader import BaseDataLoader
from hvsr_pro.core.data_structures import SeismicData, ComponentData
from hvsr_pro.core.metadata import MetadataManager


class MiniSeedLoader(BaseDataLoader):
    """
    Loader for MiniSEED format files.
    
    Handles:
    - Single file with three components
    - Separate files for E, N, Z components
    - Component identification and merging
    - Timing synchronization
    """
    
    def __init__(self):
        """Initialize MiniSEED loader."""
        super().__init__()
        self.supported_extensions = ['.miniseed', '.mseed', '.ms']
        self.loader_name = "MiniSeedLoader"
        self.metadata_manager = MetadataManager()
        
        if not HAS_OBSPY:
            raise ImportError(
                "ObsPy is required for MiniSEED support. "
                "Install it with: pip install obspy"
            )
    
    def can_load(self, filepath: str) -> bool:
        """
        Check if file is MiniSEED format.
        
        Args:
            filepath: Path to check
            
        Returns:
            True if file can be loaded
        """
        if not HAS_OBSPY:
            return False
        
        path = Path(filepath)
        
        # Check extension
        if path.suffix.lower() not in self.supported_extensions:
            return False
        
        # Try to read with ObsPy
        try:
            st = read(filepath, headonly=True)
            return len(st) > 0
        except Exception:
            return False
    
    def load_file(self, filepath: str, **kwargs) -> SeismicData:
        """
        Load MiniSEED file(s).
        
        Args:
            filepath: Path to MiniSEED file (or base path for multiple files)
            **kwargs: Optional parameters
                - component_files: Dict mapping component to filepath
                  e.g., {'E': 'file_E.mseed', 'N': 'file_N.mseed', 'Z': 'file_Z.mseed'}
                - merge_components: Auto-merge components from stream (default: True)
                
        Returns:
            SeismicData object with loaded data
        """
        # Check for separate component files
        component_files = kwargs.get('component_files', None)
        
        if component_files:
            return self._load_separate_components(component_files, **kwargs)
        else:
            return self._load_single_file(filepath, **kwargs)
    
    def _load_single_file(self, filepath: str, **kwargs) -> SeismicData:
        """Load data from single MiniSEED file containing all components."""
        # Read stream
        stream = read(filepath)

        # Extract channel mapping if provided
        channel_mapping = kwargs.get('channel_mapping', None)

        # Extract components
        components = self._extract_components_from_stream(stream, channel_mapping=channel_mapping)

        # Get metadata
        metadata = self._extract_metadata(stream, filepath)

        # Create SeismicData
        return self._create_seismic_data(components, metadata, filepath)
    
    def _load_separate_components(self, component_files: Dict[str, str], **kwargs) -> SeismicData:
        """Load data from separate component files."""
        components = {}
        all_metadata = []
        
        for comp_name, comp_file in component_files.items():
            # Read component stream
            stream = read(comp_file)
            
            if len(stream) == 0:
                raise ValueError(f"No data in file: {comp_file}")
            
            # Use first trace
            trace = stream[0]
            
            # Store component
            components[comp_name.upper()] = trace
            
            # Extract metadata
            metadata = self.metadata_manager.parse_miniseed_metadata(trace.stats)
            all_metadata.append(metadata)
        
        # Merge metadata
        merged_metadata = self.metadata_manager.merge_metadata(*all_metadata)
        merged_metadata['component_files'] = component_files
        
        # Get source file (use first one)
        source_file = list(component_files.values())[0]
        
        # Create SeismicData
        return self._create_seismic_data(components, merged_metadata, source_file)
    
    def _extract_components_from_stream(self, stream: Stream, channel_mapping: Optional[Dict[str, str]] = None) -> Dict[str, Trace]:
        """
        Extract E, N, Z components from ObsPy Stream.

        Args:
            stream: ObsPy Stream object
            channel_mapping: Optional dict mapping component to channel code
                           e.g., {'E': 'HHE', 'N': 'HHN', 'Z': 'HHZ'}

        Returns:
            Dictionary mapping component name to Trace
        """
        components = {}

        if channel_mapping:
            # Use explicit channel mapping
            for trace in stream:
                channel = trace.stats.channel.upper()

                # Check if this channel matches any mapped component
                for component, mapped_channel in channel_mapping.items():
                    if channel == mapped_channel.upper():
                        components[component] = trace
                        break
        else:
            # Auto-detect based on standard naming conventions
            for trace in stream:
                channel = trace.stats.channel.upper()

                # For standard SEED channel codes (3 chars), the last
                # character is the component indicator (E/N/Z/1/2).
                last = channel[-1] if channel else ''
                if last in ('E', '1'):
                    components.setdefault('E', trace)
                elif last in ('N', '2'):
                    components.setdefault('N', trace)
                elif last in ('Z', '3'):
                    components.setdefault('Z', trace)
                elif 'EAST' in channel:
                    components.setdefault('E', trace)
                elif 'NORTH' in channel:
                    components.setdefault('N', trace)
                elif 'VERT' in channel:
                    components.setdefault('Z', trace)

        # Validate we have all three
        required = {'E', 'N', 'Z'}
        missing = required - set(components.keys())
        if missing:
            if channel_mapping:
                raise ValueError(
                    f"Missing required components: {missing}. "
                    f"Channel mapping: {channel_mapping}. "
                    f"Available channels: {[t.stats.channel for t in stream]}"
                )
            else:
                raise ValueError(
                    f"Missing required components: {missing}. "
                    f"Available channels: {[t.stats.channel for t in stream]}. "
                    f"Consider using channel mapping for non-standard channel names."
                )

        return components
    
    def _extract_metadata(self, stream: Stream, filepath: str) -> Dict[str, Any]:
        """Extract metadata from ObsPy Stream."""
        # Use first trace for general metadata
        first_trace = stream[0]
        stats = first_trace.stats
        
        # Parse with metadata manager
        metadata = self.metadata_manager.parse_miniseed_metadata(stats)
        
        # Extract from filename
        file_metadata = self.metadata_manager.extract_from_filename(filepath)
        
        # Merge
        metadata = self.metadata_manager.merge_metadata(file_metadata, metadata)
        
        # Add loader info
        metadata['loader'] = self.loader_name
        metadata['format'] = 'MINISEED'
        metadata['n_traces'] = len(stream)
        
        return metadata
    
    def _create_seismic_data(self, 
                            components: Dict[str, Trace], 
                            metadata: Dict[str, Any],
                            source_file: str) -> SeismicData:
        """Create SeismicData from components and metadata."""
        # Get sampling rate and check consistency
        sampling_rates = [comp.stats.sampling_rate for comp in components.values()]
        if not all(abs(sr - sampling_rates[0]) < 0.01 for sr in sampling_rates):
            raise ValueError(
                f"Inconsistent sampling rates: {sampling_rates}. "
                "All components must have the same rate."
            )
        sampling_rate = sampling_rates[0]
        
        # Check lengths and trim to shortest
        lengths = [comp.stats.npts for comp in components.values()]
        min_length = min(lengths)
        if not all(l == lengths[0] for l in lengths):
            print(f"Warning: Component lengths differ {lengths}, trimming to {min_length}")
        
        # Get units (assume consistent)
        units = metadata.get('units', 'm/s')
        
        # Get start time
        start_time = components['E'].stats.starttime.datetime
        
        # Create ComponentData objects
        east = ComponentData(
            name='E',
            data=components['E'].data[:min_length].copy(),
            sampling_rate=sampling_rate,
            start_time=start_time,
            units=units,
            metadata={'channel': components['E'].stats.channel}
        )
        
        north = ComponentData(
            name='N',
            data=components['N'].data[:min_length].copy(),
            sampling_rate=sampling_rate,
            start_time=start_time,
            units=units,
            metadata={'channel': components['N'].stats.channel}
        )
        
        vertical = ComponentData(
            name='Z',
            data=components['Z'].data[:min_length].copy(),
            sampling_rate=sampling_rate,
            start_time=start_time,
            units=units,
            metadata={'channel': components['Z'].stats.channel}
        )
        
        # Create SeismicData
        seismic_data = SeismicData(
            east=east,
            north=north,
            vertical=vertical,
            station_name=metadata.get('station_name', 'UNKNOWN'),
            location=metadata.get('location', ''),
            source_file=source_file,
            metadata=metadata
        )
        
        return seismic_data
    
    def load_component_set(self, base_path: str, station: str, point: str, 
                          version: str = 'raw') -> SeismicData:
        """
        Load a set of three component files following OSCAR naming convention.
        
        Args:
            base_path: Directory containing files
            station: Station ID (e.g., 'XX01')
            point: Point ID (e.g., 'pt1')
            version: 'raw' or 'corrected'
            
        Returns:
            SeismicData object
        """
        base_dir = Path(base_path)
        
        # Build filenames
        component_files = {}
        for comp in ['E', 'N', 'Z']:
            pattern = f"{station}_{point}_{version}_{comp}.miniseed"
            filepath = base_dir / pattern
            
            if not filepath.exists():
                raise FileNotFoundError(f"Component file not found: {filepath}")
            
            component_files[comp] = str(filepath)
        
        return self.load_file(str(component_files['E']), component_files=component_files)
