"""
HVSR Processor
===============

Main class for computing HVSR from window collections.
"""

from __future__ import annotations

import logging
import warnings
from typing import Optional, Tuple, List, Dict, Any, TYPE_CHECKING
import numpy as np
from multiprocessing import Pool, cpu_count

if TYPE_CHECKING:
    from hvsr_pro.processing.windows.structures import WindowCollection, Window

from hvsr_pro.processing.hvsr.structures import HVSRResult, WindowSpectrum, Peak
from hvsr_pro.processing.hvsr.spectral import (
    compute_fft,
    konno_ohmachi_smoothing_fast,  # Keep for backward compatibility
    calculate_horizontal_spectrum,
    calculate_hvsr,
    logspace_frequencies
)
from hvsr_pro.processing.smoothing import get_smoothing_function, get_default_bandwidth

# Import window structures directly to avoid circular imports
# Peak detection is imported lazily in _detect_peaks method

logger = logging.getLogger(__name__)


def _get_window_classes():
    """Lazy import to avoid circular dependencies."""
    from hvsr_pro.processing.windows.structures import WindowCollection, Window
    return WindowCollection, Window


def _process_single_window_parallel(args):
    """
    Helper function for parallel window processing.
    Must be at module level for multiprocessing to pickle it.
    
    Args:
        args: Tuple of (window, target_frequencies, smoothing_bandwidth, 
              horizontal_method, taper, smoothing_method, detrend)
    
    Returns:
        Tuple of (WindowSpectrum, None) or (None, error_message)
    """
    window, target_frequencies, smoothing_bandwidth, horizontal_method, taper, smoothing_method, detrend = args
    
    try:
        # Import inside function for multiprocessing
        from hvsr_pro.processing.smoothing import get_smoothing_function
        from hvsr_pro.processing.hvsr.spectral import compute_fft, calculate_horizontal_spectrum, calculate_hvsr
        from hvsr_pro.processing.hvsr.structures import WindowSpectrum
        
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
        freq_e, spec_e = compute_fft(window.data.east.data, sampling_rate, taper, detrend=detrend)
        freq_n, spec_n = compute_fft(window.data.north.data, sampling_rate, taper, detrend=detrend)
        freq_z, spec_z = compute_fft(window.data.vertical.data, sampling_rate, taper, detrend=detrend)
        
        # Get smoothing function from registry
        smooth_fn = get_smoothing_function(smoothing_method)
        
        # Apply smoothing
        smooth_e = smooth_fn(freq_e, spec_e, target_frequencies, smoothing_bandwidth)
        smooth_n = smooth_fn(freq_n, spec_n, target_frequencies, smoothing_bandwidth)
        smooth_z = smooth_fn(freq_z, spec_z, target_frequencies, smoothing_bandwidth)
        
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
    - Configurable spectral smoothing (7 methods available)
    - Statistical analysis
    - Peak detection
    
    Available smoothing methods:
        - 'konno_ohmachi': Log-frequency smoothing (default, standard for HVSR)
        - 'parzen': Constant Hz bandwidth smoothing
        - 'savitzky_golay': Polynomial fitting smoothing
        - 'linear_rectangular': Simple boxcar average in Hz
        - 'log_rectangular': Boxcar average in log-frequency
        - 'linear_triangular': Weighted average in Hz
        - 'log_triangular': Weighted average in log-frequency
        - 'none': No smoothing (interpolation only)
    
    Example:
        >>> processor = HVSRProcessor(
        ...     smoothing_bandwidth=40,
        ...     smoothing_method='konno_ohmachi',
        ...     f_min=0.2,
        ...     f_max=30.0
        ... )
        >>> result = processor.process(windows)
        >>> print(f"Primary peak: {result.primary_peak.frequency:.2f} Hz")
    """
    
    def __init__(self,
                 smoothing_bandwidth: float = 40,
                 smoothing_method: str = 'konno_ohmachi',
                 f_min: float = 0.2,
                 f_max: float = 30.0,
                 n_frequencies: int = 300,
                 parallel: bool = True,
                 n_cores: Optional[int] = None,
                 horizontal_method: str = 'geometric_mean',
                 taper: Optional[str] = 'tukey',
                 detrend: str = 'linear',
                 statistics_method: str = 'lognormal',
                 std_ddof: int = 1,
                 min_prominence: float = 0.5,
                 min_amplitude: float = 2.0,
                 peak_basis: str = 'median'):
        """
        Initialize HVSR processor.
        
        Args:
            smoothing_bandwidth: Smoothing bandwidth parameter (default: 40)
                - Konno-Ohmachi: inverse width (20-80 typical, higher = less smoothing)
                - Parzen/rectangular/triangular: window width in Hz or log10
                - Savitzky-Golay: number of points (odd integer)
            smoothing_method: Smoothing method name (default: 'konno_ohmachi')
                Options: 'konno_ohmachi', 'parzen', 'savitzky_golay',
                        'linear_rectangular', 'log_rectangular',
                        'linear_triangular', 'log_triangular', 'none'
            f_min: Minimum frequency in Hz (default: 0.2)
            f_max: Maximum frequency in Hz (default: 30.0)
            n_frequencies: Number of frequency points (default: 300)
            parallel: Enable parallel processing for windows (default: True)
            n_cores: Number of worker processes (default: cpu_count - 1)
            horizontal_method: Method for combining horizontal components
            taper: Taper window type ('hann', 'hamming', 'blackman', 'tukey', None)
            detrend: Detrend method ('linear', 'mean', 'none'). Default 'linear'
                uses scipy.signal.detrend for proper linear trend removal.
            statistics_method: Method for computing HVSR statistics.
                'lognormal' — lognormal median & percentiles (recommended)
                'numpy'     — direct numpy median/percentile
            std_ddof: Delta degrees of freedom for std (default: 1)
            min_prominence: Minimum peak prominence for detection (default: 0.5)
            min_amplitude: Minimum HVSR amplitude for peak detection (default: 2.0)
            peak_basis: Curve used for peak detection.
                'median' — detect on median HVSR (recommended)
                'mean'   — detect on mean HVSR
        """
        self.smoothing_bandwidth = smoothing_bandwidth
        self.smoothing_method = smoothing_method.lower().replace(" ", "_").replace("-", "_")
        self.f_min = f_min
        self.f_max = f_max
        self.n_frequencies = n_frequencies
        self.parallel = parallel
        self.n_cores = n_cores
        self.horizontal_method = horizontal_method
        self.taper = taper if taper else None
        self.detrend = detrend
        self.statistics_method = statistics_method
        self.std_ddof = std_ddof
        self.min_prominence = min_prominence
        self.min_amplitude = min_amplitude
        self.peak_basis = peak_basis
        self.use_only_active = True
        
        # Validate smoothing method
        try:
            self._smooth_fn = get_smoothing_function(self.smoothing_method)
        except ValueError as e:
            raise ValueError(f"Invalid smoothing_method: {e}")
        
        # Generate target frequency array (log-spaced)
        self.target_frequencies = logspace_frequencies(f_min, f_max, n_frequencies)
        
        logger.info(f"HVSRProcessor initialized: method={self.smoothing_method}, "
                    f"b={smoothing_bandwidth}, f=[{f_min}, {f_max}] Hz")
    
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
        
        if self.parallel and len(window_list) > 4:
            n_workers = self.n_cores if self.n_cores else max(1, cpu_count() - 1)
            logger.info(f"Using parallel processing with {n_workers} workers")
            
            args_list = [
                (window, self.target_frequencies, self.smoothing_bandwidth, 
                 self.horizontal_method, self.taper, self.smoothing_method, self.detrend)
                for window in window_list
            ]
            
            with Pool(processes=n_workers) as pool:
                results = pool.map(_process_single_window_parallel, args_list)
            
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
                    if i < 3:
                        logger.error(f"Window {window.index} failure details:\n{error_detail}")
                    continue
        
        if not hvsr_curves:
            error_msg = f"No valid HVSR curves computed. All {len(window_list)} windows failed.\n"
            if failed_windows:
                error_msg += f"First error: Window {failed_windows[0][0]}: {failed_windows[0][1]}"
            raise ValueError(error_msg)
        
        # Stack into array for statistics
        hvsr_array = np.array(hvsr_curves)
        
        # Compute statistics
        mean_hvsr = np.mean(hvsr_array, axis=0)
        std_hvsr = np.std(hvsr_array, axis=0, ddof=self.std_ddof)
        
        if self.statistics_method == 'lognormal':
            # Lognormal statistics (matches old system)
            from scipy.stats import lognorm
            # Guard against zero/negative means
            safe_mean = np.maximum(mean_hvsr, 1e-10)
            safe_std = np.maximum(std_hvsr, 1e-10)
            zeta = np.sqrt(np.log1p((safe_std ** 2) / (safe_mean ** 2)))
            lam = np.log(safe_mean) - 0.5 * zeta ** 2
            median_hvsr = lognorm.median(s=zeta, scale=np.exp(lam))
            percentile_16, percentile_84 = (
                lognorm.ppf(p, s=zeta, scale=np.exp(lam)) for p in (0.16, 0.84))
        else:
            # Direct numpy statistics
            median_hvsr = np.median(hvsr_array, axis=0)
            percentile_16 = np.percentile(hvsr_array, 16, axis=0)
            percentile_84 = np.percentile(hvsr_array, 84, axis=0)
        
        logger.info(f"Computed HVSR statistics from {len(hvsr_curves)} valid windows")
        
        # Detect peaks
        peaks = []
        if detect_peaks_flag:
            # Choose curve for peak detection based on peak_basis setting
            if self.peak_basis == 'median':
                peak_curve = median_hvsr
            else:
                peak_curve = mean_hvsr
            peaks = self._detect_peaks(self.target_frequencies, peak_curve)
            logger.info(f"Detected {len(peaks)} peaks (basis={self.peak_basis})")
            
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
        sampling_rate = window.data.sampling_rate
        
        # Validate data
        if window.data.east is None or window.data.north is None or window.data.vertical is None:
            raise ValueError("Window missing component data")
        
        if len(window.data.east.data) == 0:
            raise ValueError("East component has no data")
        if len(window.data.north.data) == 0:
            raise ValueError("North component has no data")
        if len(window.data.vertical.data) == 0:
            raise ValueError("Vertical component has no data")
        
        # Compute FFT for each component
        freq_e, spec_e = compute_fft(window.data.east.data, sampling_rate, self.taper, detrend=self.detrend)
        freq_n, spec_n = compute_fft(window.data.north.data, sampling_rate, self.taper, detrend=self.detrend)
        freq_z, spec_z = compute_fft(window.data.vertical.data, sampling_rate, self.taper, detrend=self.detrend)
        
        # Apply smoothing using the configured method
        smooth_e = self._smooth_fn(freq_e, spec_e, self.target_frequencies, self.smoothing_bandwidth)
        smooth_n = self._smooth_fn(freq_n, spec_n, self.target_frequencies, self.smoothing_bandwidth)
        smooth_z = self._smooth_fn(freq_z, spec_z, self.target_frequencies, self.smoothing_bandwidth)
        
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
        """Detect and refine peaks using configurable parameters."""
        from hvsr_pro.processing.windows.peaks import detect_peaks, refine_peak_frequency
        
        peaks = detect_peaks(
            frequencies,
            hvsr,
            min_prominence=self.min_prominence,
            min_amplitude=self.min_amplitude,
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
            'smoothing_method': self.smoothing_method,
            'smoothing_bandwidth': self.smoothing_bandwidth,
            'f_min': self.f_min,
            'f_max': self.f_max,
            'n_frequencies': self.n_frequencies,
            'horizontal_method': self.horizontal_method,
            'taper': self.taper,
            'detrend': self.detrend,
            'statistics_method': self.statistics_method,
            'std_ddof': self.std_ddof,
            'min_prominence': self.min_prominence,
            'min_amplitude': self.min_amplitude,
            'peak_basis': self.peak_basis,
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
                f"smoothing={self.smoothing_method}(b={self.smoothing_bandwidth}), "
                f"horizontal={self.horizontal_method})")

