"""
Azimuthal HVSR Result Structure
================================

Adapted from hvsrpy by Joseph P. Vantassel (joseph.p.vantassel@gmail.com).
"""

import logging
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
import numpy as np
from scipy.signal import find_peaks

logger = logging.getLogger(__name__)

__all__ = ["AzimuthalHVSRResult"]


@dataclass
class AzimuthalHVSRResult:
    """
    Container for HVSR results computed across various azimuths.
    
    Attributes:
        frequencies: Array of frequency values (Hz)
        azimuths: Array of rotation azimuths (degrees, 0-180)
        hvsr_per_azimuth: 2D array of HVSR curves, shape (n_azimuths, n_frequencies)
        mean_curves_per_azimuth: Mean HVSR curve for each azimuth
        std_curves_per_azimuth: Std deviation for each azimuth
        valid_windows_per_azimuth: Number of valid windows per azimuth
        peaks_per_azimuth: Peak info for each azimuth
        metadata: Additional processing information
    """
    
    frequencies: np.ndarray
    azimuths: np.ndarray
    hvsr_per_azimuth: np.ndarray  # Shape: (n_azimuths, n_windows, n_frequencies)
    mean_curves_per_azimuth: np.ndarray = None  # Shape: (n_azimuths, n_frequencies)
    std_curves_per_azimuth: np.ndarray = None  # Shape: (n_azimuths, n_frequencies)
    valid_windows_per_azimuth: np.ndarray = None  # Shape: (n_azimuths,)
    peaks_per_azimuth: List[Dict] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Compute statistics if not provided."""
        if self.mean_curves_per_azimuth is None and self.hvsr_per_azimuth is not None:
            # Compute mean for each azimuth
            self.mean_curves_per_azimuth = np.nanmean(self.hvsr_per_azimuth, axis=1)
        
        if self.std_curves_per_azimuth is None and self.hvsr_per_azimuth is not None:
            # Compute std for each azimuth
            self.std_curves_per_azimuth = np.nanstd(self.hvsr_per_azimuth, axis=1)
    
    @property
    def n_azimuths(self) -> int:
        """Number of azimuths."""
        return len(self.azimuths)
    
    @property
    def n_frequencies(self) -> int:
        """Number of frequency points."""
        return len(self.frequencies)
    
    def mean_curve(self, distribution: str = "lognormal") -> np.ndarray:
        """
        Compute overall mean HVSR curve across all azimuths.
        
        Args:
            distribution: 'lognormal' or 'normal'
            
        Returns:
            Mean HVSR curve
        """
        if distribution == "lognormal":
            # Geometric mean (exp of mean of log values)
            log_means = np.log(self.mean_curves_per_azimuth + 1e-10)
            return np.exp(np.mean(log_means, axis=0))
        else:
            return np.mean(self.mean_curves_per_azimuth, axis=0)
    
    def std_curve(self, distribution: str = "lognormal") -> np.ndarray:
        """
        Compute overall std HVSR curve across all azimuths.
        
        Args:
            distribution: 'lognormal' or 'normal'
            
        Returns:
            Std HVSR curve
        """
        if distribution == "lognormal":
            log_means = np.log(self.mean_curves_per_azimuth + 1e-10)
            return np.std(log_means, axis=0)
        else:
            return np.std(self.mean_curves_per_azimuth, axis=0)
    
    def mean_curve_peak(self, distribution: str = "lognormal", 
                        search_range_hz: Tuple[float, float] = None) -> Tuple[float, float]:
        """
        Find peak of overall mean curve.
        
        Returns:
            (peak_frequency, peak_amplitude)
        """
        mean = self.mean_curve(distribution)
        
        # Apply search range mask
        if search_range_hz:
            mask = (self.frequencies >= search_range_hz[0]) & (self.frequencies <= search_range_hz[1])
            freq_subset = self.frequencies[mask]
            mean_subset = mean[mask]
        else:
            freq_subset = self.frequencies
            mean_subset = mean
        
        # Find peak
        peak_idx = np.argmax(mean_subset)
        return (freq_subset[peak_idx], mean_subset[peak_idx])
    
    def mean_curve_peak_by_azimuth(self, distribution: str = "lognormal",
                                    search_range_hz: Tuple[float, float] = None) -> Tuple[np.ndarray, np.ndarray]:
        """
        Find peak of mean curve for each azimuth.
        
        Returns:
            (peak_frequencies, peak_amplitudes) arrays
        """
        peak_freqs = np.empty(self.n_azimuths)
        peak_amps = np.empty(self.n_azimuths)
        
        for i, az in enumerate(self.azimuths):
            curve = self.mean_curves_per_azimuth[i]
            
            if search_range_hz:
                mask = (self.frequencies >= search_range_hz[0]) & (self.frequencies <= search_range_hz[1])
                freq_subset = self.frequencies[mask]
                curve_subset = curve[mask]
            else:
                freq_subset = self.frequencies
                curve_subset = curve
            
            peak_idx = np.argmax(curve_subset)
            peak_freqs[i] = freq_subset[peak_idx]
            peak_amps[i] = curve_subset[peak_idx]
        
        return (peak_freqs, peak_amps)
    
    def mean_fn_frequency(self, distribution: str = "lognormal") -> float:
        """Mean fundamental frequency across all azimuths."""
        peak_freqs, _ = self.mean_curve_peak_by_azimuth(distribution)
        
        if distribution == "lognormal":
            return np.exp(np.mean(np.log(peak_freqs)))
        else:
            return np.mean(peak_freqs)
    
    def std_fn_frequency(self, distribution: str = "lognormal") -> float:
        """Std of fundamental frequency across all azimuths."""
        peak_freqs, _ = self.mean_curve_peak_by_azimuth(distribution)
        
        if distribution == "lognormal":
            return np.std(np.log(peak_freqs))
        else:
            return np.std(peak_freqs)
    
    def mean_fn_amplitude(self, distribution: str = "lognormal") -> float:
        """Mean fundamental amplitude across all azimuths."""
        _, peak_amps = self.mean_curve_peak_by_azimuth(distribution)
        
        if distribution == "lognormal":
            return np.exp(np.mean(np.log(peak_amps)))
        else:
            return np.mean(peak_amps)
    
    def std_fn_amplitude(self, distribution: str = "lognormal") -> float:
        """Std of fundamental amplitude across all azimuths."""
        _, peak_amps = self.mean_curve_peak_by_azimuth(distribution)
        
        if distribution == "lognormal":
            return np.std(np.log(peak_amps))
        else:
            return np.std(peak_amps)
    
    def to_mesh(self, distribution: str = "lognormal") -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Create mesh grid for 2D/3D plotting.
        
        Returns:
            (mesh_frequency, mesh_azimuth, mesh_amplitude)
        """
        # Extend azimuths to include 180 for smooth wrapping
        azimuths_extended = np.append(self.azimuths, 180.0)
        
        mesh_freq, mesh_azi = np.meshgrid(self.frequencies, azimuths_extended)
        
        # Amplitude data - wrap last azimuth to first
        mesh_amp = np.vstack([self.mean_curves_per_azimuth, self.mean_curves_per_azimuth[0:1]])
        
        return (mesh_freq, mesh_azi, mesh_amp)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'frequencies': self.frequencies.tolist(),
            'azimuths': self.azimuths.tolist(),
            'mean_curves_per_azimuth': self.mean_curves_per_azimuth.tolist(),
            'std_curves_per_azimuth': self.std_curves_per_azimuth.tolist(),
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AzimuthalHVSRResult':
        """Create from dictionary."""
        return cls(
            frequencies=np.array(data['frequencies']),
            azimuths=np.array(data['azimuths']),
            hvsr_per_azimuth=None,
            mean_curves_per_azimuth=np.array(data['mean_curves_per_azimuth']),
            std_curves_per_azimuth=np.array(data['std_curves_per_azimuth']),
            metadata=data.get('metadata', {})
        )

