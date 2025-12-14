"""
HVSR Processor for HVSR Pro
============================

Main class for computing HVSR from window collections.
"""

import logging
from typing import Optional, Tuple, List, Dict, Any
import numpy as np
from multiprocessing import Pool, cpu_count
from functools import partial

from hvsr_pro.processing.window_structures import WindowCollection, Window
from hvsr_pro.processing.hvsr_structures import HVSRResult, WindowSpectrum, Peak
from hvsr_pro.processing.spectral_processing import (
    compute_fft,
    konno_ohmachi_smoothing_fast,
    calculate_horizontal_spectrum,
    calculate_hvsr,
    frequency_range_mask,
    logspace_frequencies
)
from hvsr_pro.processing.peak_detection import (
    detect_peaks,
    identify_fundamental_peak,
    refine_peak_frequency
)

logger = logging.getLogger(__name__)


def _process_single_window_parallel(args):
    """
    Helper function for parallel window processing.
    Must be at module level for multiprocessing to pickle it.
    
    Args:
        args: Tuple of (window, target_frequencies, smoothing_bandwidth, 
              horizontal_method, taper)
    
    Returns:
        Tuple of (WindowSpectrum, None) or (None, error_message)
    """
    window, target_frequencies, smoothing_bandwidth, horizontal_method, taper = args
    
    try:
        # Get sampling rate
        sampling_rate = window.data.sampling_rate
        
        # Validate data
        if window.data.east is None or window.data.north is None or window.data.vertical is None:
            return None, f"Window {window.index}: missing component data"
        
        if len(window.data.east.data) == 0:
            return None, f"Window {window.index}: East component has no data"
        if len(window.data.north.data) == 0:
            return None, f"Window {window.index}: North component has no data"
        if len(window.data.vertical.data) == 0:
            return None, f"Window {window.index}: Vertical component has no data"
        
        # Compute FFT for each component
        freq_e, spec_e = compute_fft(window.data.east.data, sampling_rate, taper)
        freq_n, spec_n = compute_fft(window.data.north.data, sampling_rate, taper)
        freq_z, spec_z = compute_fft(window.data.vertical.data, sampling_rate, taper)
        
        # Apply Konno-Ohmachi smoothing
        smooth_e = konno_ohmachi_smoothing_fast(
            freq_e, spec_e, smoothing_bandwidth, normalize=True, fc_array=target_frequencies
        )
        smooth_n = konno_ohmachi_smoothing_fast(
            freq_n, spec_n, smoothing_bandwidth, normalize=True, fc_array=target_frequencies
        )
        smooth_z = konno_ohmachi_smoothing_fast(
            freq_z, spec_z, smoothing_bandwidth, normalize=True, fc_array=target_frequencies
        )
        
        # Calculate horizontal spectrum
        horizontal = calculate_horizontal_spectrum(smooth_e, smooth_n, horizontal_method)
        
        # Calculate H/V ratio
        hvsr = calculate_hvsr(horizontal, smooth_z)
        
        # Create WindowSpectrum
        spectrum = WindowSpectrum(
            window_index=window.index,
            frequencies=target_frequencies,
            east_spectrum=smooth_e,
            north_spectrum=smooth_n,
            vertical_spectrum=smooth_z,
            horizontal_spectrum=horizontal,
            hvsr=hvsr,
            is_valid=window.is_active(),
            metadata={
                'sampling_rate': sampling_rate,
                'window_duration': window.duration,
                'start_time': window.start_time
            }
        )
        
        return spectrum, None
        
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        return None, f"Window {window.index}: {error_detail}"


class HVSRProcessor:
    """
    HVSR spectral processing engine.
    
    Computes H/V spectral ratios from window collections with:
    - FFT computation
    - Konno-Ohmachi smoothing
    - Statistical analysis
    - Peak detection
    
    Example:
        >>> processor = HVSRProcessor(
        ...     smoothing_bandwidth=40,
        ...     f_min=0.2,
        ...     f_max=20.0
        ... )
        >>> result = processor.process(windows)
        >>> print(f"Primary peak: {result.primary_peak.frequency:.2f} Hz")
    """
    
    def __init__(self,
                 smoothing_bandwidth: float = 40,
                 f_min: float = 0.2,
                 f_max: float = 20.0,
                 n_frequencies: int = 100,
                 parallel: bool = False,
                 horizontal_method: str = 'geometric_mean',
                 taper: Optional[str] = 'hann'):
        """
        Initialize HVSR processor.
        
        Args:
            smoothing_bandwidth: Konno-Ohmachi smoothing parameter (default: 40)
            f_min: Minimum frequency in Hz (default: 0.2)
            f_max: Maximum frequency in Hz (default: 20.0)
            n_frequencies: Number of frequency points (default: 100)
            parallel: Enable parallel processing for windows (default: False, experimental)
            horizontal_method: Method for combining horizontal components (default: 'geometric_mean')
            taper: Taper window type ('hann', 'hamming', 'blackman', None) (default: 'hann')
        """
        self.smoothing_bandwidth = smoothing_bandwidth
        self.f_min = f_min
        self.f_max = f_max
        self.n_frequencies = n_frequencies
        self.parallel = parallel
        self.horizontal_method = horizontal_method
        self.taper = taper if taper else None  # Convert empty string to None
        self.use_only_active = True  # Always use only active windows
        
        # Generate target frequency array (log-spaced)
        self.target_frequencies = logspace_frequencies(f_min, f_max, n_frequencies)
        
        logger.info(f"HVSRProcessor initialized: b={smoothing_bandwidth}, f=[{f_min}, {f_max}] Hz, parallel={parallel}")
    
    def process(self,
                windows: WindowCollection,
                detect_peaks_flag: bool = True,
                save_window_spectra: bool = False) -> HVSRResult:
        """
        Process window collection to compute HVSR.
        
        Args:
            windows: Window collection from WindowManager
            detect_peaks_flag: Run peak detection
            save_window_spectra: Save individual window spectra in result
            
        Returns:
            HVSRResult with mean, median, std, peaks, etc.
        """
        logger.info(f"Processing {windows.n_windows} windows...")
        
        # Filter to active windows if requested
        if self.use_only_active:
            window_list = windows.get_active_windows()
        else:
            window_list = windows.windows
        
        if not window_list:
            raise ValueError("No windows available for processing")
        
        logger.info(f"Using {len(window_list)} windows for HVSR computation")
        
        # Process each window
        window_spectra = []
        hvsr_curves = []
        failed_windows = []
        
        if self.parallel and len(window_list) > 20:
            # Parallel processing for large datasets
            n_workers = max(1, cpu_count() - 1)  # Leave one core free
            logger.info(f"Using parallel processing with {n_workers} workers")
            
            # Prepare arguments for parallel processing
            args_list = [
                (window, self.target_frequencies, self.smoothing_bandwidth, 
                 self.horizontal_method, self.taper)
                for window in window_list
            ]
            
            # Process in parallel
            with Pool(processes=n_workers) as pool:
                results = pool.map(_process_single_window_parallel, args_list)
            
            # Collect results
            for i, (spectrum, error) in enumerate(results):
                if spectrum is not None:
                    window_spectra.append(spectrum)
                    hvsr_curves.append(spectrum.hvsr)
                else:
                    failed_windows.append((window_list[i].index, error))
                    if i < 3:
                        logger.error(f"Window processing failed: {error}")
        
        else:
            # Sequential processing (default)
            if self.parallel and len(window_list) <= 20:
                logger.info("Parallel processing disabled for small datasets (<20 windows)")
            
            for i, window in enumerate(window_list):
                try:
                    spectrum = self._process_window(window)
                    window_spectra.append(spectrum)
                    hvsr_curves.append(spectrum.hvsr)
                except Exception as e:
                    import traceback
                    error_detail = f"{str(e)}\n{traceback.format_exc()}"
                    logger.error(f"Failed to process window {window.index}: {error_detail}")
                    failed_windows.append((window.index, str(e)))
                    # Log first 3 failures in detail, then just count
                    if i < 3:
                        logger.error(f"Window {window.index} failure details:\n{error_detail}")
                    continue
        
        if not hvsr_curves:
            error_msg = f"No valid HVSR curves computed. All {len(window_list)} windows failed.\n"
            if failed_windows:
                error_msg += f"First error: Window {failed_windows[0][0]}: {failed_windows[0][1]}"
            raise ValueError(error_msg)
        
        # Stack into array for statistics
        hvsr_array = np.array(hvsr_curves)  # Shape: (n_windows, n_frequencies)
        
        # Compute statistics
        mean_hvsr = np.mean(hvsr_array, axis=0)
        median_hvsr = np.median(hvsr_array, axis=0)
        std_hvsr = np.std(hvsr_array, axis=0)
        percentile_16 = np.percentile(hvsr_array, 16, axis=0)
        percentile_84 = np.percentile(hvsr_array, 84, axis=0)
        
        logger.info(f"Computed HVSR statistics from {len(hvsr_curves)} valid windows")
        
        # Detect peaks
        peaks = []
        if detect_peaks_flag:
            peaks = self._detect_peaks(self.target_frequencies, mean_hvsr)
            logger.info(f"Detected {len(peaks)} peaks")
            
            if peaks:
                primary = peaks[0]
                logger.info(f"Primary peak: {primary.frequency:.2f} Hz (A={primary.amplitude:.2f})")
        
        # Create result
        result = HVSRResult(
            frequencies=self.target_frequencies,
            mean_hvsr=mean_hvsr,
            median_hvsr=median_hvsr,
            std_hvsr=std_hvsr,
            percentile_16=percentile_16,
            percentile_84=percentile_84,
            valid_windows=len(hvsr_curves),
            total_windows=windows.n_windows,
            peaks=peaks,
            window_spectra=window_spectra if save_window_spectra else [],
            processing_params=self._get_processing_params()
        )
        
        return result
    
    def _process_window(self, window: Window) -> WindowSpectrum:
        """Process a single window."""
        # Get sampling rate
        sampling_rate = window.data.sampling_rate
        
        # Validate data
        if window.data.east is None or window.data.north is None or window.data.vertical is None:
            raise ValueError("Window missing component data")
        
        # Check for valid data
        if len(window.data.east.data) == 0:
            raise ValueError("East component has no data")
        if len(window.data.north.data) == 0:
            raise ValueError("North component has no data")
        if len(window.data.vertical.data) == 0:
            raise ValueError("Vertical component has no data")
        
        # Compute FFT for each component
        freq_e, spec_e = compute_fft(window.data.east.data, sampling_rate, self.taper)
        freq_n, spec_n = compute_fft(window.data.north.data, sampling_rate, self.taper)
        freq_z, spec_z = compute_fft(window.data.vertical.data, sampling_rate, self.taper)
        
        # Apply Konno-Ohmachi smoothing
        smooth_e = konno_ohmachi_smoothing_fast(
            freq_e, spec_e, self.smoothing_bandwidth, normalize=True, fc_array=self.target_frequencies
        )
        smooth_n = konno_ohmachi_smoothing_fast(
            freq_n, spec_n, self.smoothing_bandwidth, normalize=True, fc_array=self.target_frequencies
        )
        smooth_z = konno_ohmachi_smoothing_fast(
            freq_z, spec_z, self.smoothing_bandwidth, normalize=True, fc_array=self.target_frequencies
        )
        
        # Calculate horizontal spectrum
        horizontal = calculate_horizontal_spectrum(smooth_e, smooth_n, self.horizontal_method)
        
        # Calculate H/V ratio
        hvsr = calculate_hvsr(horizontal, smooth_z)
        
        # Create WindowSpectrum
        return WindowSpectrum(
            window_index=window.index,
            frequencies=self.target_frequencies,
            east_spectrum=smooth_e,
            north_spectrum=smooth_n,
            vertical_spectrum=smooth_z,
            horizontal_spectrum=horizontal,
            hvsr=hvsr,
            is_valid=window.is_active(),
            metadata={
                'sampling_rate': sampling_rate,
                'window_duration': window.duration,
                'start_time': window.start_time
            }
        )
    
    def _detect_peaks(self, frequencies: np.ndarray, hvsr: np.ndarray) -> List[Peak]:
        """Detect and refine peaks."""
        # Initial peak detection
        peaks = detect_peaks(
            frequencies,
            hvsr,
            min_prominence=1.5,
            min_amplitude=2.0,
            freq_range=(self.f_min, self.f_max)
        )
        
        # Refine peak frequencies
        for peak in peaks:
            refined_freq = refine_peak_frequency(
                frequencies, hvsr, peak.frequency, window_hz=0.5
            )
            peak.frequency = refined_freq
        
        return peaks
    
    def _get_processing_params(self) -> Dict[str, Any]:
        """Get processing parameters."""
        return {
            'smoothing_bandwidth': self.smoothing_bandwidth,
            'f_min': self.f_min,
            'f_max': self.f_max,
            'n_frequencies': self.n_frequencies,
            'horizontal_method': self.horizontal_method,
            'taper': self.taper,
            'use_only_active': self.use_only_active
        }
    
    def process_quick(self, windows: WindowCollection) -> Tuple[np.ndarray, np.ndarray]:
        """
        Quick processing - return only mean HVSR.
        
        Args:
            windows: Window collection
            
        Returns:
            frequencies, mean_hvsr
        """
        result = self.process(windows, detect_peaks_flag=False, save_window_spectra=False)
        return result.frequencies, result.mean_hvsr
    
    def __repr__(self) -> str:
        return (f"HVSRProcessor(f=[{self.f_min}-{self.f_max}]Hz, "
                f"smoothing=KO{self.smoothing_bandwidth}, "
                f"method={self.horizontal_method})")
