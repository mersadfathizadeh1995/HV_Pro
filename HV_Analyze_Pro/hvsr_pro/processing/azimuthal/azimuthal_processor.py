"""
Azimuthal HVSR Processor
========================

Computes HVSR at multiple rotation angles for directional site characterization.
Adapted from hvsrpy by Joseph P. Vantassel (joseph.p.vantassel@gmail.com).
"""

import logging
import sys
import os
from typing import List, Optional, Tuple, Callable
import numpy as np

# Conditional multiprocessing import with safer defaults on Windows
try:
    from multiprocessing import Pool, cpu_count
    HAS_MULTIPROCESSING = True
except ImportError:
    HAS_MULTIPROCESSING = False
    def cpu_count():
        return 4  # Fallback

from hvsr_pro.processing.windows import WindowCollection, Window
from hvsr_pro.processing.hvsr import (
    compute_fft,
    konno_ohmachi_smoothing_fast,
    calculate_hvsr,
    logspace_frequencies
)
from .azimuthal_result import AzimuthalHVSRResult

logger = logging.getLogger(__name__)

__all__ = ["AzimuthalHVSRProcessor"]

# Windows-specific: limit default cores to prevent memory exhaustion
IS_WINDOWS = sys.platform == 'win32'
MAX_SAFE_WORKERS_WINDOWS = 4  # Windows multiprocessing is memory-heavy


def _rotate_horizontals(east_data: np.ndarray, north_data: np.ndarray, 
                        azimuth_deg: float) -> np.ndarray:
    """
    Rotate horizontal components to a specific azimuth.
    
    Args:
        east_data: East component amplitude array
        north_data: North component amplitude array
        azimuth_deg: Azimuth in degrees (clockwise from North)
        
    Returns:
        Rotated horizontal component
    """
    azimuth_rad = np.radians(azimuth_deg)
    return north_data * np.cos(azimuth_rad) + east_data * np.sin(azimuth_rad)


def _process_window_at_azimuth(args):
    """
    Process a single window at a single azimuth.
    Helper for parallel processing.
    """
    (window_data, azimuth, target_frequencies, smoothing_bandwidth, 
     taper, sampling_rate) = args
    
    try:
        east_data = window_data['east']
        north_data = window_data['north']
        vertical_data = window_data['vertical']
        
        # Rotate horizontal to azimuth
        horizontal_rotated = _rotate_horizontals(east_data, north_data, azimuth)
        
        # Compute FFT
        freq_h, spec_h = compute_fft(horizontal_rotated, sampling_rate, taper)
        freq_v, spec_v = compute_fft(vertical_data, sampling_rate, taper)
        
        # Apply smoothing
        smooth_h = konno_ohmachi_smoothing_fast(
            freq_h, spec_h, smoothing_bandwidth, 
            normalize=True, fc_array=target_frequencies
        )
        smooth_v = konno_ohmachi_smoothing_fast(
            freq_v, spec_v, smoothing_bandwidth,
            normalize=True, fc_array=target_frequencies
        )
        
        # Calculate H/V ratio
        hvsr = calculate_hvsr(smooth_h, smooth_v)
        
        return hvsr, None
        
    except Exception as e:
        return None, str(e)


class AzimuthalHVSRProcessor:
    """
    Processor for computing HVSR at multiple rotation angles.
    
    This enables directional analysis of site response, useful for
    identifying azimuth-dependent resonance patterns.
    
    Example:
        >>> processor = AzimuthalHVSRProcessor(
        ...     azimuths=range(0, 180, 10),  # 0, 10, 20, ..., 170 degrees
        ...     smoothing_bandwidth=40
        ... )
        >>> result = processor.process(windows)
        >>> plot_azimuthal_contour_3d(result)
    """
    
    def __init__(self,
                 azimuths: List[float] = None,
                 smoothing_bandwidth: float = 40,
                 f_min: float = 0.2,
                 f_max: float = 20.0,
                 n_frequencies: int = 100,
                 parallel: bool = True,
                 n_workers: int = None,
                 taper: str = 'hann'):
        """
        Initialize azimuthal processor.
        
        Args:
            azimuths: List of azimuths in degrees (0-180). Default: 0, 5, 10, ..., 175
            smoothing_bandwidth: Konno-Ohmachi bandwidth parameter
            f_min: Minimum frequency (Hz)
            f_max: Maximum frequency (Hz)
            n_frequencies: Number of frequency points
            parallel: Enable parallel processing
            n_workers: Number of workers (default: cpu_count - 1, max 4 on Windows)
            taper: Taper window type
        """
        self.azimuths = np.array(azimuths) if azimuths is not None else np.arange(0, 180, 5)
        self.smoothing_bandwidth = smoothing_bandwidth
        self.f_min = f_min
        self.f_max = f_max
        self.n_frequencies = n_frequencies
        self.taper = taper
        
        # Determine safe number of workers
        available_cores = cpu_count()
        default_workers = max(1, available_cores - 1)
        
        # On Windows, limit workers to prevent memory exhaustion
        # Windows multiprocessing uses 'spawn' which is very memory-heavy
        if IS_WINDOWS:
            default_workers = min(default_workers, MAX_SAFE_WORKERS_WINDOWS)
            if n_workers and n_workers > MAX_SAFE_WORKERS_WINDOWS:
                logger.warning(
                    f"Reducing workers from {n_workers} to {MAX_SAFE_WORKERS_WINDOWS} on Windows "
                    f"to prevent memory exhaustion. Each worker requires significant memory."
                )
                n_workers = MAX_SAFE_WORKERS_WINDOWS
        
        self.n_workers = n_workers if n_workers else default_workers
        self.parallel = parallel and HAS_MULTIPROCESSING
        
        # Generate target frequencies
        self.target_frequencies = logspace_frequencies(f_min, f_max, n_frequencies)
        
        logger.info(f"AzimuthalHVSRProcessor initialized: {len(self.azimuths)} azimuths, "
                   f"f=[{f_min}, {f_max}] Hz, workers={self.n_workers}")
    
    def process(self, 
                windows: WindowCollection,
                progress_callback=None) -> AzimuthalHVSRResult:
        """
        Process windows at all azimuths.
        
        Args:
            windows: Window collection from WindowManager
            progress_callback: Optional callback(progress, message) for progress updates
            
        Returns:
            AzimuthalHVSRResult with HVSR curves per azimuth
        """
        # Get active windows
        window_list = windows.get_active_windows()
        n_windows = len(window_list)
        n_azimuths = len(self.azimuths)
        
        if not window_list:
            raise ValueError("No active windows for azimuthal processing")
        
        logger.info(f"Processing {n_windows} windows at {n_azimuths} azimuths...")
        
        if progress_callback:
            progress_callback(5, f"Processing {n_windows} windows at {n_azimuths} azimuths...")
        
        # Prepare window data for processing
        sampling_rate = window_list[0].data.sampling_rate
        window_data_list = []
        for window in window_list:
            window_data_list.append({
                'east': window.data.east.data,
                'north': window.data.north.data,
                'vertical': window.data.vertical.data
            })
        
        # Process all combinations of windows and azimuths
        hvsr_results = np.zeros((n_azimuths, n_windows, self.n_frequencies))
        
        use_parallel = self.parallel and n_windows * n_azimuths > 50 and HAS_MULTIPROCESSING
        
        if use_parallel:
            # Parallel processing with error handling for memory issues
            logger.info(f"Using parallel processing with {self.n_workers} workers")
            
            if progress_callback:
                progress_callback(8, f"Starting parallel processing ({self.n_workers} workers)...")
            
            try:
                # Prepare all argument combinations
                all_args = []
                for az_idx, azimuth in enumerate(self.azimuths):
                    for win_idx, win_data in enumerate(window_data_list):
                        all_args.append((
                            win_data, azimuth, self.target_frequencies,
                            self.smoothing_bandwidth, self.taper, sampling_rate
                        ))
                
                # Process in parallel with chunking for better memory management
                chunk_size = max(1, len(all_args) // (self.n_workers * 4))
                
                with Pool(processes=self.n_workers) as pool:
                    results = pool.map(_process_window_at_azimuth, all_args, chunksize=chunk_size)
                
                # Collect results
                idx = 0
                for az_idx in range(n_azimuths):
                    for win_idx in range(n_windows):
                        hvsr, error = results[idx]
                        if hvsr is not None:
                            hvsr_results[az_idx, win_idx, :] = hvsr
                        else:
                            hvsr_results[az_idx, win_idx, :] = np.nan
                            logger.warning(f"Failed at azimuth {self.azimuths[az_idx]}, window {win_idx}: {error}")
                        idx += 1
                    
                    if progress_callback:
                        progress = 10 + int(80 * (az_idx + 1) / n_azimuths)
                        progress_callback(progress, f"Azimuth {self.azimuths[az_idx]:.0f} deg complete")
                        
            except (MemoryError, OSError) as e:
                # Memory or resource error - fall back to sequential processing
                logger.warning(f"Parallel processing failed ({type(e).__name__}), falling back to sequential...")
                if progress_callback:
                    progress_callback(10, "Memory issue detected, switching to sequential processing...")
                use_parallel = False  # Fall through to sequential processing
        
        if not use_parallel:
            # Sequential processing
            for az_idx, azimuth in enumerate(self.azimuths):
                for win_idx, win_data in enumerate(window_data_list):
                    args = (win_data, azimuth, self.target_frequencies,
                           self.smoothing_bandwidth, self.taper, sampling_rate)
                    hvsr, error = _process_window_at_azimuth(args)
                    
                    if hvsr is not None:
                        hvsr_results[az_idx, win_idx, :] = hvsr
                    else:
                        hvsr_results[az_idx, win_idx, :] = np.nan
                
                if progress_callback:
                    progress = 10 + int(80 * (az_idx + 1) / n_azimuths)
                    progress_callback(progress, f"Azimuth {azimuth:.0f} deg complete")
        
        # Compute statistics
        mean_curves = np.nanmean(hvsr_results, axis=1)
        std_curves = np.nanstd(hvsr_results, axis=1)
        valid_windows = np.sum(~np.isnan(hvsr_results[:, :, 0]), axis=1)
        
        if progress_callback:
            progress_callback(95, "Computing statistics...")
        
        # Create result
        result = AzimuthalHVSRResult(
            frequencies=self.target_frequencies,
            azimuths=self.azimuths,
            hvsr_per_azimuth=hvsr_results,
            mean_curves_per_azimuth=mean_curves,
            std_curves_per_azimuth=std_curves,
            valid_windows_per_azimuth=valid_windows,
            metadata={
                'smoothing_bandwidth': self.smoothing_bandwidth,
                'f_min': self.f_min,
                'f_max': self.f_max,
                'n_windows': n_windows,
                'n_azimuths': n_azimuths
            }
        )
        
        if progress_callback:
            progress_callback(100, "Azimuthal processing complete")
        
        logger.info(f"Azimuthal processing complete: {n_azimuths} azimuths, {n_windows} windows")
        
        return result
    
    def __repr__(self) -> str:
        return (f"AzimuthalHVSRProcessor(azimuths={len(self.azimuths)}, "
                f"f=[{self.f_min}-{self.f_max}]Hz)")

