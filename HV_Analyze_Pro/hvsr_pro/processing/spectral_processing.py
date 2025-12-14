"""
Spectral Processing for HVSR Pro
=================================

FFT computation, smoothing, and spectral analysis.
"""

import numpy as np
from typing import Optional, Tuple
from scipy import signal as scipy_signal
from scipy.fft import rfft, rfftfreq


def compute_fft(data: np.ndarray, sampling_rate: float, 
                taper: Optional[str] = 'hann') -> Tuple[np.ndarray, np.ndarray]:
    """
    Compute FFT with optional tapering.
    
    Args:
        data: Time series data
        sampling_rate: Sampling rate in Hz
        taper: Taper window ('hann', 'hamming', 'blackman', None)
        
    Returns:
        frequencies: Frequency array (Hz)
        spectrum: Amplitude spectrum
    """
    n = len(data)
    
    # Remove mean
    data = data - np.mean(data)
    
    # Apply taper
    if taper:
        if taper == 'hann':
            window = np.hanning(n)
        elif taper == 'hamming':
            window = np.hamming(n)
        elif taper == 'blackman':
            window = np.blackman(n)
        else:
            raise ValueError(f"Unknown taper: {taper}")
        data = data * window
    
    # Compute FFT (positive frequencies only)
    frequencies = rfftfreq(n, 1.0 / sampling_rate)
    fft_result = rfft(data)
    
    # Amplitude spectrum (absolute value, normalized)
    spectrum = np.abs(fft_result) * 2.0 / n
    
    return frequencies, spectrum


def konno_ohmachi_smoothing(frequencies: np.ndarray, 
                            spectrum: np.ndarray,
                            bandwidth: float = 40.0,
                            normalize: bool = True) -> np.ndarray:
    """
    Apply Konno-Ohmachi smoothing to spectrum.
    
    This is the standard smoothing method for HVSR analysis, providing
    log-frequency smoothing that preserves peak shapes.
    
    Reference:
        Konno & Ohmachi (1998): Ground-Motion Characteristics Estimated from 
        Spectral Ratio between Horizontal and Vertical Components of Microtremor.
    
    Args:
        frequencies: Frequency array (Hz)
        spectrum: Amplitude spectrum
        bandwidth: Bandwidth parameter (typically 20-40)
        normalize: Normalize smoothing window
        
    Returns:
        Smoothed spectrum
    """
    n_freq = len(frequencies)
    smoothed = np.zeros(n_freq)
    
    # Skip DC component
    if frequencies[0] == 0:
        smoothed[0] = spectrum[0]
        start_idx = 1
    else:
        start_idx = 0
    
    # Apply smoothing to each frequency
    for i in range(start_idx, n_freq):
        fc = frequencies[i]  # Center frequency
        
        # Calculate smoothing window for this center frequency
        # Avoid division by zero and log(0)
        ratio = frequencies / fc
        ratio = np.maximum(ratio, 1e-10)
        
        # Konno-Ohmachi window function
        # W(f, fc) = [sin(b * log10(f/fc)) / (b * log10(f/fc))]^4
        log_ratio = np.log10(ratio)
        
        # Handle the case where log_ratio = 0 (f = fc)
        window = np.ones_like(log_ratio)
        nonzero = log_ratio != 0
        
        arg = bandwidth * log_ratio[nonzero]
        window[nonzero] = (np.sin(arg) / arg) ** 4
        
        # Normalize window if requested
        if normalize:
            window_sum = np.sum(window)
            if window_sum > 0:
                window = window / window_sum
        
        # Apply smoothing
        smoothed[i] = np.sum(window * spectrum)
    
    return smoothed


def konno_ohmachi_smoothing_fast(frequencies: np.ndarray,
                                 spectrum: np.ndarray,
                                 bandwidth: float = 40.0,
                                 normalize: bool = True,
                                 fc_array: Optional[np.ndarray] = None) -> np.ndarray:
    """
    Optimized Konno-Ohmachi smoothing using vectorized operations.
    
    Args:
        frequencies: Frequency array (Hz)  
        spectrum: Amplitude spectrum
        bandwidth: Bandwidth parameter
        normalize: Normalize smoothing window
        fc_array: Optional custom center frequencies (defaults to frequencies)
        
    Returns:
        Smoothed spectrum
    """
    if fc_array is None:
        fc_array = frequencies.copy()
    
    # Remove DC component if present
    if frequencies[0] == 0:
        frequencies = frequencies[1:]
        spectrum = spectrum[1:]
        fc_array = fc_array[1:]
        has_dc = True
    else:
        has_dc = False
    
    # Reshape for broadcasting: (n_fc, 1) and (1, n_freq)
    fc = fc_array.reshape(-1, 1)
    f = frequencies.reshape(1, -1)
    
    # Calculate log ratio matrix
    ratio = f / fc
    ratio = np.maximum(ratio, 1e-10)
    log_ratio = np.log10(ratio)
    
    # Konno-Ohmachi window
    arg = bandwidth * log_ratio
    
    # Handle f = fc case
    window = np.ones_like(arg)
    nonzero = arg != 0
    window[nonzero] = (np.sin(arg[nonzero]) / arg[nonzero]) ** 4
    
    # Normalize
    if normalize:
        window_sum = np.sum(window, axis=1, keepdims=True)
        window = np.divide(window, window_sum, where=window_sum > 0, out=window)
    
    # Apply smoothing (matrix multiplication)
    smoothed = np.dot(window, spectrum.reshape(-1, 1)).flatten()
    
    # Add back DC if it was present
    if has_dc:
        smoothed = np.insert(smoothed, 0, 0.0)
    
    return smoothed


def calculate_horizontal_spectrum(east_spectrum: np.ndarray,
                                  north_spectrum: np.ndarray,
                                  method: str = 'geometric_mean') -> np.ndarray:
    """
    Calculate combined horizontal spectrum from E and N components.
    
    Args:
        east_spectrum: East component spectrum
        north_spectrum: North component spectrum  
        method: Combination method:
            - 'geometric_mean': sqrt(E * N) - SESAME 2004 recommendation
            - 'arithmetic_mean': (E + N) / 2
            - 'quadratic': sqrt(E^2 + N^2) - vector sum
            - 'maximum': max(E, N)
            
    Returns:
        Combined horizontal spectrum
    """
    if method == 'geometric_mean':
        # SESAME 2004 recommendation
        return np.sqrt(east_spectrum * north_spectrum)
    
    elif method == 'arithmetic_mean':
        return (east_spectrum + north_spectrum) / 2.0
    
    elif method == 'quadratic':
        # Vector magnitude
        return np.sqrt(east_spectrum**2 + north_spectrum**2)
    
    elif method == 'maximum':
        return np.maximum(east_spectrum, north_spectrum)
    
    else:
        raise ValueError(f"Unknown method: {method}")


def calculate_hvsr(horizontal_spectrum: np.ndarray,
                  vertical_spectrum: np.ndarray,
                  epsilon: float = 1e-10) -> np.ndarray:
    """
    Calculate H/V spectral ratio.
    
    Args:
        horizontal_spectrum: Horizontal component spectrum
        vertical_spectrum: Vertical component spectrum
        epsilon: Small value to avoid division by zero
        
    Returns:
        H/V ratio
    """
    # Avoid division by zero
    vertical_safe = np.maximum(vertical_spectrum, epsilon)
    return horizontal_spectrum / vertical_safe


def frequency_range_mask(frequencies: np.ndarray,
                        f_min: float = 0.2,
                        f_max: float = 20.0) -> np.ndarray:
    """
    Create boolean mask for frequency range.
    
    Args:
        frequencies: Frequency array
        f_min: Minimum frequency (Hz)
        f_max: Maximum frequency (Hz)
        
    Returns:
        Boolean mask
    """
    return (frequencies >= f_min) & (frequencies <= f_max)


def resample_spectrum(frequencies: np.ndarray,
                     spectrum: np.ndarray,
                     target_frequencies: np.ndarray,
                     method: str = 'log') -> np.ndarray:
    """
    Resample spectrum to target frequency array.
    
    Args:
        frequencies: Original frequency array
        spectrum: Original spectrum
        target_frequencies: Target frequency array
        method: Interpolation method ('linear' or 'log')
        
    Returns:
        Resampled spectrum
    """
    if method == 'log':
        # Log-log interpolation (better for spectral data)
        log_freq = np.log10(frequencies)
        log_spec = np.log10(spectrum)
        log_target = np.log10(target_frequencies)
        
        # Interpolate
        log_resampled = np.interp(log_target, log_freq, log_spec)
        return 10 ** log_resampled
    
    elif method == 'linear':
        return np.interp(target_frequencies, frequencies, spectrum)
    
    else:
        raise ValueError(f"Unknown method: {method}")


def logspace_frequencies(f_min: float = 0.1,
                        f_max: float = 25.0,
                        n_points: int = 100) -> np.ndarray:
    """
    Generate logarithmically-spaced frequency array.
    
    Useful for HVSR analysis which covers wide frequency range.
    
    Args:
        f_min: Minimum frequency (Hz)
        f_max: Maximum frequency (Hz)
        n_points: Number of points
        
    Returns:
        Frequency array
    """
    return np.logspace(np.log10(f_min), np.log10(f_max), n_points)
