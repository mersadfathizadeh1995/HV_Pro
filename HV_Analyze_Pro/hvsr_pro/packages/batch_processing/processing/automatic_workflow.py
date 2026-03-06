"""
Automatic HVSR Workflow
========================

Provides automatic peak detection and QC rejection workflow
for batch processing of HVSR data across multiple stations.
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import json

from hvsr_pro.packages.batch_processing.processing.structures import Peak, HVSRResult
from hvsr_pro.packages.batch_processing.processing.peaks import detect_peaks, find_top_n_peaks, sesame_peak_criteria


@dataclass
class StationResult:
    """
    HVSR result for a single station.
    
    Attributes:
        station_id: Station identifier
        station_name: Station display name
        topic: Topic/diameter group (e.g., "200", "300", "500")
        frequencies: Frequency array
        mean_hvsr: Mean HVSR curve
        median_hvsr: Median HVSR curve
        std_hvsr: Standard deviation
        percentile_16: 16th percentile HVSR curve
        percentile_84: 84th percentile HVSR curve
        peaks: Detected peaks
        valid_windows: Number of valid windows
        total_windows: Total windows
        mat_path: Path to ArrayData.mat file
        output_dir: Station output directory
        processing_params: Processing parameters used
    """
    station_id: int
    station_name: str
    topic: str
    frequencies: np.ndarray
    mean_hvsr: np.ndarray
    std_hvsr: np.ndarray
    median_hvsr: Optional[np.ndarray] = None
    percentile_16: Optional[np.ndarray] = None
    percentile_84: Optional[np.ndarray] = None
    peaks: List[Peak] = field(default_factory=list)
    valid_windows: int = 0
    total_windows: int = 0
    mat_path: str = ""
    output_dir: str = ""
    processing_params: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def primary_peak(self) -> Optional[Peak]:
        """Get the primary (highest amplitude) peak."""
        if not self.peaks:
            return None
        return max(self.peaks, key=lambda p: p.amplitude)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        d = {
            'station_id': self.station_id,
            'station_name': self.station_name,
            'topic': self.topic,
            'frequencies': self.frequencies.tolist(),
            'mean_hvsr': self.mean_hvsr.tolist(),
            'std_hvsr': self.std_hvsr.tolist(),
            'peaks': [p.to_dict() for p in self.peaks],
            'valid_windows': self.valid_windows,
            'total_windows': self.total_windows,
            'mat_path': self.mat_path,
            'output_dir': self.output_dir,
            'processing_params': self.processing_params,
            'metadata': self.metadata,
        }
        if self.median_hvsr is not None:
            d['median_hvsr'] = self.median_hvsr.tolist()
        if self.percentile_16 is not None:
            d['percentile_16'] = self.percentile_16.tolist()
        if self.percentile_84 is not None:
            d['percentile_84'] = self.percentile_84.tolist()
        return d


@dataclass
class PeakStatistics:
    """
    Statistics for a detected peak across multiple stations.
    
    Attributes:
        peak_id: Peak identifier (1, 2, 3, ...)
        mean_frequency: Mean peak frequency across stations
        std_frequency: Standard deviation of frequency
        min_frequency: Minimum frequency
        max_frequency: Maximum frequency
        mean_amplitude: Mean peak amplitude
        std_amplitude: Standard deviation of amplitude
        min_amplitude: Minimum amplitude
        max_amplitude: Maximum amplitude
        station_count: Number of stations with this peak
        total_stations: Total number of stations
        stations: List of station names with this peak
        sesame_pass_count: Number of stations passing SESAME criteria
    """
    peak_id: int
    mean_frequency: float
    std_frequency: float
    min_frequency: float
    max_frequency: float
    mean_amplitude: float
    std_amplitude: float
    min_amplitude: float
    max_amplitude: float
    station_count: int
    total_stations: int
    stations: List[str] = field(default_factory=list)
    sesame_pass_count: int = 0
    
    @property
    def detection_rate(self) -> float:
        """Fraction of stations with this peak."""
        return self.station_count / self.total_stations if self.total_stations > 0 else 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'peak_id': self.peak_id,
            'mean_frequency': self.mean_frequency,
            'std_frequency': self.std_frequency,
            'min_frequency': self.min_frequency,
            'max_frequency': self.max_frequency,
            'mean_amplitude': self.mean_amplitude,
            'std_amplitude': self.std_amplitude,
            'min_amplitude': self.min_amplitude,
            'max_amplitude': self.max_amplitude,
            'station_count': self.station_count,
            'total_stations': self.total_stations,
            'detection_rate': self.detection_rate,
            'stations': self.stations,
            'sesame_pass_count': self.sesame_pass_count
        }
    
    def summary_string(self) -> str:
        """Human-readable summary."""
        return (f"Peak {self.peak_id}: {self.mean_frequency:.2f} Hz "
                f"(±{self.std_frequency:.2f} Hz) | "
                f"Amp: {self.mean_amplitude:.1f} ({self.min_amplitude:.1f}-{self.max_amplitude:.1f}) | "
                f"Found in {self.station_count}/{self.total_stations} stations "
                f"({self.detection_rate:.0%})")


@dataclass
class AutomaticWorkflowResult:
    """
    Complete result from automatic workflow.
    
    Contains all station results, combined statistics, and median curves.
    """
    station_results: List[StationResult] = field(default_factory=list)
    peak_statistics: List[PeakStatistics] = field(default_factory=list)
    median_hvsr: Optional[np.ndarray] = None
    mean_hvsr: Optional[np.ndarray] = None
    std_hvsr: Optional[np.ndarray] = None
    percentile_16: Optional[np.ndarray] = None
    percentile_84: Optional[np.ndarray] = None
    frequencies: Optional[np.ndarray] = None
    combined_peaks: List[Peak] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)
    processing_params: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def n_stations(self) -> int:
        """Number of stations."""
        return len(self.station_results)
    
    def get_stations_by_topic(self, topic: str) -> List[StationResult]:
        """Get all stations for a specific topic."""
        return [s for s in self.station_results if s.topic == topic]
    
    def compute_median_hvsr(self) -> None:
        """Compute median-of-medians HVSR across all stations.

        Uses each station's median_hvsr when available (falls back to
        mean_hvsr).  All station curves are interpolated onto a common
        log-spaced frequency grid before stacking.
        """
        if not self.station_results:
            return

        # Determine common log-spaced frequency grid
        ref = self.station_results[0]
        pp = ref.processing_params or {}
        f_min = pp.get('f_min', float(ref.frequencies[0]))
        f_max = pp.get('f_max', float(ref.frequencies[-1]))
        n_freq = pp.get('n_frequencies', len(ref.frequencies))
        self.frequencies = np.logspace(np.log10(f_min), np.log10(f_max), n_freq)
        self.processing_params = dict(pp)

        # Interpolate each station's curves onto the common grid
        median_stack = []
        mean_stack = []
        std_stack = []
        for sr in self.station_results:
            curve = sr.median_hvsr if sr.median_hvsr is not None else sr.mean_hvsr
            median_stack.append(np.interp(self.frequencies, sr.frequencies, curve))
            mean_stack.append(np.interp(self.frequencies, sr.frequencies, sr.mean_hvsr))
            if sr.std_hvsr is not None:
                std_stack.append(np.interp(self.frequencies, sr.frequencies, sr.std_hvsr))

        median_arr = np.array(median_stack)
        mean_arr = np.array(mean_stack)

        self.median_hvsr = np.median(median_arr, axis=0)
        self.mean_hvsr = np.mean(mean_arr, axis=0)
        # Combined std: median of per-station intra-station stds when available,
        # otherwise fall back to inter-station std of medians
        if std_stack:
            self.std_hvsr = np.median(np.array(std_stack), axis=0)
        else:
            self.std_hvsr = np.std(median_arr, axis=0)
        self.percentile_16 = np.percentile(median_arr, 16, axis=0)
        self.percentile_84 = np.percentile(median_arr, 84, axis=0)
    
    def detect_combined_peaks(self, 
                              min_prominence: float = 1.5,
                              min_amplitude: float = 2.0,
                              n_peaks: int = 3) -> List[Peak]:
        """
        Detect peaks in the combined median HVSR curve.
        
        Args:
            min_prominence: Minimum peak prominence
            min_amplitude: Minimum peak amplitude
            n_peaks: Maximum number of peaks to return
            
        Returns:
            List of detected peaks
        """
        if self.median_hvsr is None or self.frequencies is None:
            self.compute_median_hvsr()
        
        if self.median_hvsr is None:
            return []
        
        self.combined_peaks = detect_peaks(
            self.frequencies,
            self.median_hvsr,
            min_prominence=min_prominence,
            min_amplitude=min_amplitude
        )[:n_peaks]

        # Label primary / secondary
        for i, pk in enumerate(self.combined_peaks):
            pk.peak_type = "primary" if i == 0 else "secondary"

        return self.combined_peaks

    def set_combined_peaks(self, peaks: List[Peak]) -> None:
        """Manually set combined peaks (e.g. from UI selection)."""
        self.combined_peaks = list(peaks)
        for i, pk in enumerate(self.combined_peaks):
            pk.peak_type = "primary" if i == 0 else "secondary"
    
    def compute_peak_statistics(self, 
                                frequency_tolerance: float = 0.2) -> List[PeakStatistics]:
        """
        Compute statistics for each detected peak across all stations.
        
        Groups peaks from different stations that are within tolerance
        of the combined peak frequencies.
        
        Args:
            frequency_tolerance: Relative frequency tolerance for matching
            
        Returns:
            List of PeakStatistics for each combined peak
        """
        if not self.combined_peaks:
            self.detect_combined_peaks()
        
        if not self.combined_peaks:
            return []
        
        self.peak_statistics = []
        
        for peak_id, target_peak in enumerate(self.combined_peaks, start=1):
            target_freq = target_peak.frequency
            tolerance_hz = target_freq * frequency_tolerance
            
            matching_freqs = []
            matching_amps = []
            matching_stations = []
            sesame_pass = 0
            
            for station in self.station_results:
                for peak in station.peaks:
                    if abs(peak.frequency - target_freq) <= tolerance_hz:
                        matching_freqs.append(peak.frequency)
                        matching_amps.append(peak.amplitude)
                        matching_stations.append(station.station_name)
                        
                        # Check SESAME criteria
                        criteria = sesame_peak_criteria(
                            peak, station.frequencies, station.mean_hvsr
                        )
                        if all(criteria.values()):
                            sesame_pass += 1
                        break
            
            if matching_freqs:
                stats = PeakStatistics(
                    peak_id=peak_id,
                    mean_frequency=float(np.mean(matching_freqs)),
                    std_frequency=float(np.std(matching_freqs)),
                    min_frequency=float(np.min(matching_freqs)),
                    max_frequency=float(np.max(matching_freqs)),
                    mean_amplitude=float(np.mean(matching_amps)),
                    std_amplitude=float(np.std(matching_amps)),
                    min_amplitude=float(np.min(matching_amps)),
                    max_amplitude=float(np.max(matching_amps)),
                    station_count=len(matching_stations),
                    total_stations=len(self.station_results),
                    stations=matching_stations,
                    sesame_pass_count=sesame_pass
                )
                self.peak_statistics.append(stats)
        
        return self.peak_statistics
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'n_stations': self.n_stations,
            'topics': self.topics,
            'station_results': [s.to_dict() for s in self.station_results],
            'peak_statistics': [p.to_dict() for p in self.peak_statistics],
            'frequencies': self.frequencies.tolist() if self.frequencies is not None else None,
            'median_hvsr': self.median_hvsr.tolist() if self.median_hvsr is not None else None,
            'mean_hvsr': self.mean_hvsr.tolist() if self.mean_hvsr is not None else None,
            'std_hvsr': self.std_hvsr.tolist() if self.std_hvsr is not None else None,
            'percentile_16': self.percentile_16.tolist() if self.percentile_16 is not None else None,
            'percentile_84': self.percentile_84.tolist() if self.percentile_84 is not None else None,
            'combined_peaks': [p.to_dict() for p in self.combined_peaks],
            'processing_params': self.processing_params,
            'metadata': self.metadata
        }

    def save(self, filepath: str) -> None:
        """Save to JSON file."""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    def save_as_station_format(self, filepath: str) -> None:
        """Save combined result in the same JSON format as per-station output.

        This produces a JSON file identical in structure to the per-station
        ``HVSR_*_result.json``, making downstream consumers format-agnostic.
        """
        from datetime import datetime as _dt
        if self.frequencies is None:
            self.compute_median_hvsr()
        if self.frequencies is None:
            return

        total_valid = sum(s.valid_windows for s in self.station_results)
        total_all = sum(s.total_windows for s in self.station_results)
        acc_rate = total_valid / total_all if total_all > 0 else 0.0

        data = {
            'frequencies': self.frequencies.tolist(),
            'mean_hvsr': self.mean_hvsr.tolist() if self.mean_hvsr is not None else [],
            'median_hvsr': self.median_hvsr.tolist() if self.median_hvsr is not None else [],
            'std_hvsr': self.std_hvsr.tolist() if self.std_hvsr is not None else [],
            'percentile_16': self.percentile_16.tolist() if self.percentile_16 is not None else [],
            'percentile_84': self.percentile_84.tolist() if self.percentile_84 is not None else [],
            'valid_windows': total_valid,
            'total_windows': total_all,
            'acceptance_rate': float(acc_rate),
            'peaks': [p.to_dict() for p in self.combined_peaks],
            'processing_params': dict(self.processing_params, n_stations=self.n_stations),
            'timestamp': _dt.now().isoformat(),
            'metadata': dict(
                self.metadata,
                stations=[s.station_name for s in self.station_results],
                type='combined',
            ),
        }
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)


def run_automatic_peak_detection(station_results: List[StationResult],
                                  min_prominence: float = 1.5,
                                  min_amplitude: float = 2.0,
                                  n_peaks: int = 3,
                                  frequency_tolerance: float = 0.2) -> AutomaticWorkflowResult:
    """
    Run automatic peak detection workflow on multiple stations.
    
    This is the main entry point for automatic mode.
    
    Args:
        station_results: List of StationResult objects
        min_prominence: Minimum peak prominence
        min_amplitude: Minimum peak amplitude
        n_peaks: Number of peaks to detect
        frequency_tolerance: Tolerance for matching peaks across stations
        
    Returns:
        AutomaticWorkflowResult with all statistics
    """
    # Create workflow result
    result = AutomaticWorkflowResult(
        station_results=station_results,
        topics=list(set(s.topic for s in station_results))
    )
    
    # Detect peaks for each station if not already done
    for station in result.station_results:
        if not station.peaks:
            station.peaks = detect_peaks(
                station.frequencies,
                station.mean_hvsr,
                min_prominence=min_prominence,
                min_amplitude=min_amplitude
            )[:n_peaks]
    
    # Compute combined statistics
    result.compute_median_hvsr()
    result.detect_combined_peaks(min_prominence, min_amplitude, n_peaks)
    result.compute_peak_statistics(frequency_tolerance)
    
    return result


def load_hvsr_from_mat(mat_path: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Load HVSR data from a .mat file produced by hvsr_making_peak.py.
    
    Args:
        mat_path: Path to the .mat file
        
    Returns:
        Tuple of (frequencies, mean_hvsr, std_hvsr)
    """
    from scipy.io import loadmat
    
    data = loadmat(mat_path)
    
    # Try common variable names
    freq_keys = ['f', 'freq', 'frequencies', 'Freq', 'F']
    hvsr_keys = ['HV', 'HVSR', 'hvsr', 'HV_mean', 'mean_hvsr']
    std_keys = ['HV_std', 'std_hvsr', 'std', 'STD']
    
    frequencies = None
    mean_hvsr = None
    std_hvsr = None
    
    for key in freq_keys:
        if key in data:
            frequencies = np.squeeze(data[key])
            break
    
    for key in hvsr_keys:
        if key in data:
            mean_hvsr = np.squeeze(data[key])
            break
    
    for key in std_keys:
        if key in data:
            std_hvsr = np.squeeze(data[key])
            break
    
    if frequencies is None or mean_hvsr is None:
        raise ValueError(f"Could not find frequency/HVSR data in {mat_path}")
    
    if std_hvsr is None:
        std_hvsr = np.zeros_like(mean_hvsr)
    
    return frequencies, mean_hvsr, std_hvsr
