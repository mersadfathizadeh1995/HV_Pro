"""
Metadata management for HVSR Pro
=================================

Handles extraction, storage, and management of seismic data metadata.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import json


class MetadataManager:
    """
    Manages metadata for seismic recordings.
    
    Handles:
    - Header information extraction
    - Sensor specifications
    - Location data
    - Processing history
    - Quality metrics
    """
    
    def __init__(self):
        """Initialize metadata manager."""
        self._metadata_cache = {}
        self._required_fields = {
            'station_name', 'sampling_rate', 'n_samples'
        }
        self._optional_fields = {
            'sensor_type', 'depth', 'units', 'location', 
            'start_time', 'end_time', 'duration'
        }
    
    def create_metadata(self, 
                       station_name: str,
                       sampling_rate: float,
                       n_samples: int,
                       **kwargs) -> Dict[str, Any]:
        """
        Create metadata dictionary with validation.
        
        Args:
            station_name: Station identifier
            sampling_rate: Sampling rate in Hz
            n_samples: Number of samples
            **kwargs: Additional metadata fields
            
        Returns:
            Validated metadata dictionary
        """
        metadata = {
            'station_name': station_name,
            'sampling_rate': float(sampling_rate),
            'n_samples': int(n_samples),
            'creation_time': datetime.now().isoformat()
        }
        
        # Add optional fields
        metadata.update(kwargs)
        
        # Validate
        self._validate_metadata(metadata)
        
        return metadata
    
    def _validate_metadata(self, metadata: Dict[str, Any]) -> None:
        """
        Validate metadata dictionary.
        
        Args:
            metadata: Metadata to validate
            
        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Check required fields
        missing = self._required_fields - set(metadata.keys())
        if missing:
            raise ValueError(f"Missing required metadata fields: {missing}")
        
        # Validate types and ranges
        if metadata['sampling_rate'] <= 0:
            raise ValueError("Sampling rate must be positive")
        
        if metadata['n_samples'] <= 0:
            raise ValueError("Number of samples must be positive")
    
    def parse_oscar_header(self, header_lines: list) -> Dict[str, Any]:
        """
        Parse OSCAR ASCII file header format.
        
        Args:
            header_lines: List of header lines from file
            
        Returns:
            Dictionary of parsed metadata
            
        Example header format:
            Site: XX01
            Duration[s]: 18000.00
            Sensor_Type: CMG6TD
            Depth[m]: 0.4
            Units: m\\s
        """
        metadata = {}
        
        for line in header_lines:
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip()
                value = value.strip()
                
                # Parse specific fields
                if key.lower() == 'site':
                    metadata['station_name'] = value
                elif 'duration' in key.lower():
                    metadata['duration'] = float(value)
                elif 'sensor' in key.lower() or 'type' in key.lower():
                    metadata['sensor_type'] = value
                elif 'depth' in key.lower():
                    metadata['depth'] = float(value)
                elif 'units' in key.lower():
                    # Handle backslash notation
                    metadata['units'] = value.replace('\\', '/')
                elif 'sampling' in key.lower() or 'frequency' in key.lower():
                    # Extract numeric value
                    try:
                        metadata['sampling_rate'] = float(value.split()[0])
                    except (ValueError, IndexError):
                        pass
        
        return metadata
    
    def parse_miniseed_metadata(self, stats: Any) -> Dict[str, Any]:
        """
        Parse metadata from ObsPy Stream stats object.
        
        Args:
            stats: ObsPy Stats object from Trace
            
        Returns:
            Dictionary of parsed metadata
        """
        metadata = {
            'station_name': stats.station,
            'network': stats.network,
            'location': stats.location,
            'channel': stats.channel,
            'sampling_rate': stats.sampling_rate,
            'n_samples': stats.npts,
            'start_time': stats.starttime.datetime,
            'end_time': stats.endtime.datetime,
            'duration': (stats.endtime - stats.starttime),
        }
        
        # Add calibration info if available
        if hasattr(stats, 'calib'):
            metadata['calibration'] = stats.calib
        
        # Add response info if available
        if hasattr(stats, 'response'):
            metadata['has_response'] = True
        
        return metadata
    
    def extract_from_filename(self, filepath: str) -> Dict[str, Any]:
        """
        Extract metadata from filename patterns.
        
        Args:
            filepath: Path to data file
            
        Returns:
            Dictionary of extracted metadata
        """
        metadata = {}
        path = Path(filepath)
        filename = path.stem  # Without extension
        
        # OSCAR text file pattern: XX##_pt#_raw/corrected
        if 'XX' in filename and 'pt' in filename:
            parts = filename.split('_')
            for part in parts:
                if part.startswith('XX'):
                    metadata['station_name'] = part
                    metadata['site_id'] = part
                elif part.startswith('pt'):
                    metadata['position'] = part
                elif part in ['raw', 'corrected']:
                    metadata['processing_level'] = part
        
        # MiniSEED pattern: Network.Station.Location_Instrument_Date_Time
        elif '.' in filename:
            parts = filename.split('.')
            if len(parts) >= 2:
                metadata['network'] = parts[0]
                metadata['station_name'] = parts[1]
        
        metadata['filename'] = path.name
        metadata['source_path'] = str(path.absolute())
        
        return metadata
    
    def merge_metadata(self, *metadata_dicts: Dict[str, Any]) -> Dict[str, Any]:
        """Merge multiple metadata dictionaries."""
        merged = {}
        for md in metadata_dicts:
            if md:
                merged.update(md)
        return merged
    
    def save_metadata(self, metadata: Dict[str, Any], filepath: str) -> None:
        """Save metadata to JSON file."""
        serializable = self._make_serializable(metadata)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(serializable, f, indent=2)
    
    def load_metadata(self, filepath: str) -> Dict[str, Any]:
        """Load metadata from JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        return metadata
    
    def _make_serializable(self, obj):
        """Convert objects to JSON-serializable format."""
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, '__dict__'):
            return self._make_serializable(obj.__dict__)
        else:
            return obj
