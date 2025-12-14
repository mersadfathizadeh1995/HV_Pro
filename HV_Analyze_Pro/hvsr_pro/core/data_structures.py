"""
Data structures for HVSR Pro
=============================

Core data structures for seismic data representation.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime


@dataclass
class ComponentData:
    """
    Represents a single component (E, N, or Z) of seismic data.
    
    Attributes:
        name: Component name ('E', 'N', 'Z', 'HNE', 'HNN', 'HNZ', etc.)
        data: Time series data array
        sampling_rate: Sampling rate in Hz
        start_time: Start time of the recording
        units: Data units (e.g., 'm/s', 'm/s^2')
        metadata: Additional metadata dictionary
    """
    name: str
    data: np.ndarray
    sampling_rate: float
    start_time: Optional[datetime] = None
    units: str = 'm/s'
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate data after initialization."""
        if not isinstance(self.data, np.ndarray):
            self.data = np.array(self.data)
        
        if len(self.data) == 0:
            raise ValueError("Component data cannot be empty")
        
        if self.sampling_rate <= 0:
            raise ValueError(f"Sampling rate must be positive, got {self.sampling_rate}")
    
    @property
    def n_samples(self) -> int:
        """Return number of samples."""
        return len(self.data)
    
    @property
    def duration(self) -> float:
        """Return duration in seconds."""
        return self.n_samples / self.sampling_rate
    
    @property
    def time_vector(self) -> np.ndarray:
        """Generate time vector in seconds."""
        dt = 1.0 / self.sampling_rate
        return np.arange(self.n_samples) * dt
    
    @property
    def dt(self) -> float:
        """Return sampling interval in seconds."""
        return 1.0 / self.sampling_rate
    
    def get_slice(self, start_idx: int, end_idx: int) -> 'ComponentData':
        """
        Extract a slice of the data.
        
        Args:
            start_idx: Start index
            end_idx: End index
            
        Returns:
            New ComponentData with sliced data
        """
        sliced_data = self.data[start_idx:end_idx].copy()
        
        # Calculate new start time if available
        new_start_time = None
        if self.start_time:
            from datetime import timedelta
            offset_seconds = start_idx * self.dt
            new_start_time = self.start_time + timedelta(seconds=offset_seconds)
        
        return ComponentData(
            name=self.name,
            data=sliced_data,
            sampling_rate=self.sampling_rate,
            start_time=new_start_time,
            units=self.units,
            metadata=self.metadata.copy()
        )
    
    def __repr__(self) -> str:
        return (f"ComponentData(name='{self.name}', "
                f"samples={self.n_samples}, "
                f"rate={self.sampling_rate} Hz, "
                f"duration={self.duration:.2f}s)")


@dataclass
class SeismicData:
    """
    Container for three-component seismic data.
    
    Attributes:
        east: East component data
        north: North component data
        vertical: Vertical component data
        station_name: Station identifier
        location: Location code
        source_file: Original file path
        metadata: Global metadata dictionary
    """
    east: ComponentData
    north: ComponentData
    vertical: ComponentData
    station_name: str = "UNKNOWN"
    location: str = ""
    source_file: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate three-component data consistency."""
        # Check sampling rates match
        rates = [self.east.sampling_rate, self.north.sampling_rate, 
                 self.vertical.sampling_rate]
        if not all(r == rates[0] for r in rates):
            raise ValueError(
                f"Sampling rates must match: E={rates[0]}, N={rates[1]}, Z={rates[2]}"
            )
        
        # Check lengths match
        lengths = [self.east.n_samples, self.north.n_samples, 
                   self.vertical.n_samples]
        if not all(l == lengths[0] for l in lengths):
            raise ValueError(
                f"Component lengths must match: E={lengths[0]}, N={lengths[1]}, Z={lengths[2]}"
            )
    
    @property
    def sampling_rate(self) -> float:
        """Return common sampling rate."""
        return self.east.sampling_rate
    
    @property
    def n_samples(self) -> int:
        """Return common number of samples."""
        return self.east.n_samples
    
    @property
    def duration(self) -> float:
        """Return duration in seconds."""
        return self.east.duration
    
    @property
    def start_time(self) -> Optional[datetime]:
        """Return start time (from east component)."""
        return self.east.start_time
    
    @property
    def time_vector(self) -> np.ndarray:
        """Return time vector."""
        return self.east.time_vector
    
    def get_component(self, name: str) -> ComponentData:
        """
        Get component by name.
        
        Args:
            name: Component name ('E', 'N', 'Z', 'east', 'north', 'vertical')
            
        Returns:
            ComponentData object
        """
        name_lower = name.lower()
        if name_lower in ['e', 'east', 'e-w', 'ew']:
            return self.east
        elif name_lower in ['n', 'north', 'n-s', 'ns']:
            return self.north
        elif name_lower in ['z', 'vertical', 'up']:
            return self.vertical
        else:
            raise ValueError(f"Unknown component name: {name}")
    
    def get_horizontal_components(self) -> tuple[ComponentData, ComponentData]:
        """Return tuple of (east, north) components."""
        return self.east, self.north
    
    def get_slice(self, start_idx: int, end_idx: int) -> 'SeismicData':
        """
        Extract a time slice from all components.
        
        Args:
            start_idx: Start sample index
            end_idx: End sample index
            
        Returns:
            New SeismicData with sliced data
        """
        return SeismicData(
            east=self.east.get_slice(start_idx, end_idx),
            north=self.north.get_slice(start_idx, end_idx),
            vertical=self.vertical.get_slice(start_idx, end_idx),
            station_name=self.station_name,
            location=self.location,
            source_file=self.source_file,
            metadata=self.metadata.copy()
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary representation.
        
        Returns:
            Dictionary with all data and metadata
        """
        return {
            'station_name': self.station_name,
            'location': self.location,
            'source_file': self.source_file,
            'sampling_rate': self.sampling_rate,
            'n_samples': self.n_samples,
            'duration': self.duration,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'east': {
                'data': self.east.data.tolist(),
                'units': self.east.units,
                'metadata': self.east.metadata
            },
            'north': {
                'data': self.north.data.tolist(),
                'units': self.north.units,
                'metadata': self.north.metadata
            },
            'vertical': {
                'data': self.vertical.data.tolist(),
                'units': self.vertical.units,
                'metadata': self.vertical.metadata
            },
            'metadata': self.metadata
        }
    
    def __repr__(self) -> str:
        return (f"SeismicData(station='{self.station_name}', "
                f"samples={self.n_samples}, "
                f"rate={self.sampling_rate} Hz, "
                f"duration={self.duration:.2f}s)")
    
    def __str__(self) -> str:
        lines = [
            f"Seismic Data Record",
            f"  Station: {self.station_name}",
            f"  Location: {self.location or 'N/A'}",
            f"  Duration: {self.duration:.2f} seconds",
            f"  Sampling Rate: {self.sampling_rate} Hz",
            f"  Samples: {self.n_samples}",
            f"  Components: E, N, Z",
        ]
        if self.start_time:
            lines.append(f"  Start Time: {self.start_time.isoformat()}")
        if self.source_file:
            lines.append(f"  Source: {self.source_file}")
        return "\n".join(lines)
