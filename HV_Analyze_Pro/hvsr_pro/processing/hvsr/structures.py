"""
HVSR Data Structures
=====================

Data structures for HVSR spectral processing results.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import numpy as np
from datetime import datetime
import json
from pathlib import Path


@dataclass
class WindowSpectrum:
    """
    Spectral data for a single window.
    
    Attributes:
        window_index: Index of the window
        frequencies: Frequency array (Hz)
        east_spectrum: FFT of east component
        north_spectrum: FFT of north component
        vertical_spectrum: FFT of vertical component
        horizontal_spectrum: Combined horizontal spectrum
        hvsr: H/V spectral ratio
        is_valid: Whether this window passed quality control
        metadata: Additional information
    """
    window_index: int
    frequencies: np.ndarray
    east_spectrum: np.ndarray
    north_spectrum: np.ndarray
    vertical_spectrum: np.ndarray
    horizontal_spectrum: np.ndarray
    hvsr: np.ndarray
    is_valid: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'window_index': int(self.window_index),
            'frequencies': self.frequencies.tolist(),
            'east_spectrum': self.east_spectrum.tolist(),
            'north_spectrum': self.north_spectrum.tolist(),
            'vertical_spectrum': self.vertical_spectrum.tolist(),
            'horizontal_spectrum': self.horizontal_spectrum.tolist(),
            'hvsr': self.hvsr.tolist(),
            'is_valid': self.is_valid,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WindowSpectrum':
        """Create from dictionary."""
        return cls(
            window_index=data['window_index'],
            frequencies=np.array(data['frequencies']),
            east_spectrum=np.array(data['east_spectrum']),
            north_spectrum=np.array(data['north_spectrum']),
            vertical_spectrum=np.array(data['vertical_spectrum']),
            horizontal_spectrum=np.array(data['horizontal_spectrum']),
            hvsr=np.array(data['hvsr']),
            is_valid=data['is_valid'],
            metadata=data.get('metadata', {})
        )


@dataclass
class Peak:
    """
    HVSR peak information.
    
    Attributes:
        frequency: Peak frequency (Hz)
        amplitude: Peak amplitude
        prominence: Peak prominence (relative to neighbors)
        width: Peak width (Hz)
        left_freq: Left base frequency
        right_freq: Right base frequency
        quality: Peak quality score (0-1)
    """
    frequency: float
    amplitude: float
    prominence: float = 0.0
    width: float = 0.0
    left_freq: float = 0.0
    right_freq: float = 0.0
    quality: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'frequency': float(self.frequency),
            'amplitude': float(self.amplitude),
            'prominence': float(self.prominence),
            'width': float(self.width),
            'left_freq': float(self.left_freq),
            'right_freq': float(self.right_freq),
            'quality': float(self.quality)
        }


@dataclass
class HVSRResult:
    """
    Complete HVSR processing result.
    
    Contains all spectral data, statistics, and peaks.
    
    Attributes:
        frequencies: Frequency array (Hz)
        mean_hvsr: Mean HVSR curve
        median_hvsr: Median HVSR curve
        std_hvsr: Standard deviation
        percentile_16: 16th percentile
        percentile_84: 84th percentile
        valid_windows: Number of valid windows used
        total_windows: Total windows processed
        peaks: List of detected peaks
        window_spectra: Individual window spectra
        processing_params: Processing parameters used
        timestamp: Processing timestamp
        metadata: Additional information
    """
    frequencies: np.ndarray
    mean_hvsr: np.ndarray
    median_hvsr: np.ndarray
    std_hvsr: np.ndarray
    percentile_16: np.ndarray
    percentile_84: np.ndarray
    valid_windows: int
    total_windows: int
    peaks: List[Peak] = field(default_factory=list)
    window_spectra: List[WindowSpectrum] = field(default_factory=list)
    processing_params: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    @property
    def acceptance_rate(self) -> float:
        """Fraction of valid windows."""
        return self.valid_windows / self.total_windows if self.total_windows > 0 else 0.0
    
    @property
    def primary_peak(self) -> Optional[Peak]:
        """Return the primary (highest amplitude) peak."""
        if not self.peaks:
            return None
        return max(self.peaks, key=lambda p: p.amplitude)
    
    def get_hvsr_at_frequency(self, freq: float, curve: str = 'mean') -> float:
        """
        Get HVSR value at specific frequency (interpolated).
        
        Args:
            freq: Frequency in Hz
            curve: Which curve to use ('mean', 'median', 'std')
            
        Returns:
            Interpolated HVSR value
        """
        curve_map = {
            'mean': self.mean_hvsr,
            'median': self.median_hvsr,
            'std': self.std_hvsr,
            'p16': self.percentile_16,
            'p84': self.percentile_84
        }
        
        if curve not in curve_map:
            raise ValueError(f"Unknown curve: {curve}")
        
        return float(np.interp(freq, self.frequencies, curve_map[curve]))
    
    def to_dict(self, include_windows: bool = False) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.
        
        Args:
            include_windows: Include individual window spectra (large!)
        """
        result = {
            'frequencies': self.frequencies.tolist(),
            'mean_hvsr': self.mean_hvsr.tolist(),
            'median_hvsr': self.median_hvsr.tolist(),
            'std_hvsr': self.std_hvsr.tolist(),
            'percentile_16': self.percentile_16.tolist(),
            'percentile_84': self.percentile_84.tolist(),
            'valid_windows': int(self.valid_windows),
            'total_windows': int(self.total_windows),
            'acceptance_rate': float(self.acceptance_rate),
            'peaks': [p.to_dict() for p in self.peaks],
            'processing_params': self.processing_params,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'metadata': self.metadata
        }
        
        if include_windows:
            result['window_spectra'] = [w.to_dict() for w in self.window_spectra]
        
        return result
    
    def save(self, filepath: str, include_windows: bool = False) -> None:
        """
        Save to JSON file.
        
        Args:
            filepath: Output file path
            include_windows: Include individual window spectra
        """
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(include_windows), f, indent=2)
    
    @classmethod
    def load(cls, filepath: str) -> 'HVSRResult':
        """Load from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        # Reconstruct peaks
        peaks = [Peak(**p) for p in data.get('peaks', [])]
        
        # Reconstruct window spectra if present
        window_spectra = []
        if 'window_spectra' in data:
            window_spectra = [WindowSpectrum.from_dict(w) for w in data['window_spectra']]
        
        # Parse timestamp
        timestamp = None
        if data.get('timestamp'):
            timestamp = datetime.fromisoformat(data['timestamp'])
        
        return cls(
            frequencies=np.array(data['frequencies']),
            mean_hvsr=np.array(data['mean_hvsr']),
            median_hvsr=np.array(data['median_hvsr']),
            std_hvsr=np.array(data['std_hvsr']),
            percentile_16=np.array(data['percentile_16']),
            percentile_84=np.array(data['percentile_84']),
            valid_windows=data['valid_windows'],
            total_windows=data['total_windows'],
            peaks=peaks,
            window_spectra=window_spectra,
            processing_params=data.get('processing_params', {}),
            timestamp=timestamp,
            metadata=data.get('metadata', {})
        )
    
    def __repr__(self) -> str:
        peak_str = f", {len(self.peaks)} peaks" if self.peaks else ""
        return (f"HVSRResult({self.valid_windows}/{self.total_windows} windows, "
                f"{len(self.frequencies)} freqs{peak_str})")

