"""
Smoothing Methods
==================

Frequency-domain smoothing functions for spectral analysis.
Pure NumPy implementations (no Numba dependency).

All methods share a unified interface:
    smoothing_function(frequencies, spectrum, center_frequencies, bandwidth)

Reference implementations adapted from hvsrpy (Vantassel, 2019-2025).
"""

import numpy as np
from scipy.signal import savgol_filter
from typing import Union


def _ensure_2d(spectrum: np.ndarray) -> tuple:
    """
    Ensure spectrum is 2D (nspectrum, nfrequency).
    
    Returns:
        (spectrum_2d, was_1d)
    """
    if spectrum.ndim == 1:
        return spectrum.reshape(1, -1), True
    return spectrum, False


def konno_ohmachi(frequencies: np.ndarray,
                  spectrum: np.ndarray,
                  center_frequencies: np.ndarray,
                  bandwidth: float = 40.0) -> np.ndarray:
    """
    Konno and Ohmachi (1998) smoothing.
    
    Log-frequency smoothing that preserves peak shapes while reducing
    high-frequency noise. This is the standard smoothing method for
    HVSR analysis.
    
    Parameters
    ----------
    frequencies : ndarray
        Frequencies of input spectrum, shape (nfrequency,).
    spectrum : ndarray
        Spectrum to smooth, shape (nspectrum, nfrequency) or (nfrequency,).
    center_frequencies : ndarray
        Center frequencies for output, shape (nfc,).
    bandwidth : float
        Smoothing bandwidth parameter (inversely related to window width).
        Default is 40. Higher values = narrower window = less smoothing.
        
    Returns
    -------
    ndarray
        Smoothed spectrum at center frequencies.
        
    Reference
    ---------
    Konno, K. and Ohmachi, T. (1998), "Ground-Motion Characteristics 
    Estimated from Spectral Ratio between Horizontal and Vertical 
    Components of Microtremor" Bull. Seism. Soc. Am. 88, 228-241.
    """
    spectrum_2d, was_1d = _ensure_2d(spectrum)
    n_spectra = spectrum_2d.shape[0]
    n_fc = len(center_frequencies)
    
    # Pre-compute limits
    upper_limit = 10 ** (3.0 / bandwidth)
    lower_limit = 10 ** (-3.0 / bandwidth)
    
    smoothed = np.zeros((n_spectra, n_fc))
    
    for fc_idx, fc in enumerate(center_frequencies):
        if fc < 1e-6:
            continue
            
        # Compute frequency ratio
        f_on_fc = frequencies / fc
        
        # Create mask for valid frequencies
        valid = (frequencies >= 1e-6) & (f_on_fc >= lower_limit) & (f_on_fc <= upper_limit)
        
        if not np.any(valid):
            continue
            
        # Compute window weights
        f_valid = frequencies[valid]
        f_on_fc_valid = f_valid / fc
        
        # Konno-Ohmachi window: (sin(b * log10(f/fc)) / (b * log10(f/fc)))^4
        log_ratio = np.log10(f_on_fc_valid)
        arg = bandwidth * log_ratio
        
        # Handle the case where f == fc (arg == 0)
        window = np.ones_like(arg)
        nonzero = np.abs(arg) > 1e-10
        window[nonzero] = (np.sin(arg[nonzero]) / arg[nonzero]) ** 4
        
        # Apply weighted average
        window_sum = np.sum(window)
        if window_sum > 0:
            smoothed[:, fc_idx] = np.sum(window * spectrum_2d[:, valid], axis=1) / window_sum
    
    return smoothed[0] if was_1d else smoothed


def parzen(frequencies: np.ndarray,
           spectrum: np.ndarray,
           center_frequencies: np.ndarray,
           bandwidth: float = 0.5) -> np.ndarray:
    """
    Parzen-style smoothing.
    
    Constant bandwidth smoothing in Hz. Good for linear frequency analysis.
    
    Parameters
    ----------
    frequencies : ndarray
        Frequencies of input spectrum, shape (nfrequency,).
    spectrum : ndarray
        Spectrum to smooth, shape (nspectrum, nfrequency) or (nfrequency,).
    center_frequencies : ndarray
        Center frequencies for output, shape (nfc,).
    bandwidth : float
        Width of smoothing window in Hz. Default is 0.5.
        
    Returns
    -------
    ndarray
        Smoothed spectrum at center frequencies.
        
    Reference
    ---------
    Konno, K. and Ohmachi, T. (1995), "A smoothing function suitable for 
    estimation of amplification factor of the surface ground from 
    microtremor and its application" Doboku Gakkai Ronbunshu. 525, 247-259.
    """
    spectrum_2d, was_1d = _ensure_2d(spectrum)
    n_spectra = spectrum_2d.shape[0]
    n_fc = len(center_frequencies)
    
    # Parzen window constant
    a = (np.pi * 280) / (2 * 151)
    limit = np.sqrt(6) * a / bandwidth
    
    smoothed = np.zeros((n_spectra, n_fc))
    
    for fc_idx, fc in enumerate(center_frequencies):
        if fc < 1e-6:
            continue
            
        # Compute frequency difference
        f_minus_fc = frequencies - fc
        
        # Create mask for valid frequencies
        valid = (frequencies >= 1e-6) & (np.abs(f_minus_fc) <= limit)
        
        if not np.any(valid):
            continue
            
        f_minus_fc_valid = f_minus_fc[valid]
        
        # Parzen window
        arg = a * f_minus_fc_valid / bandwidth
        
        window = np.ones_like(arg)
        nonzero = np.abs(arg) > 1e-10
        window[nonzero] = (np.sin(arg[nonzero]) / arg[nonzero]) ** 4
        
        window_sum = np.sum(window)
        if window_sum > 0:
            smoothed[:, fc_idx] = np.sum(window * spectrum_2d[:, valid], axis=1) / window_sum
    
    return smoothed[0] if was_1d else smoothed


def savitzky_golay(frequencies: np.ndarray,
                   spectrum: np.ndarray,
                   center_frequencies: np.ndarray,
                   bandwidth: Union[int, float] = 9) -> np.ndarray:
    """
    Savitzky-Golay (1964) smoothing.
    
    Polynomial fitting smoothing. Requires linearly-spaced frequencies.
    
    Parameters
    ----------
    frequencies : ndarray
        Frequencies of input spectrum, shape (nfrequency,).
        MUST be linearly spaced.
    spectrum : ndarray
        Spectrum to smooth, shape (nspectrum, nfrequency) or (nfrequency,).
    center_frequencies : ndarray
        Center frequencies for output, shape (nfc,).
    bandwidth : int
        Number of points in smoothing window (must be odd).
        Default is 9.
        
    Returns
    -------
    ndarray
        Smoothed spectrum at center frequencies.
        
    Reference
    ---------
    Savitzky, A. and Golay, M.J.E. (1964), "Smoothing and Differentiation 
    of Data by Simplified Least Squares Procedures" Anal. Chem. 36, 1627-1639.
    """
    spectrum_2d, was_1d = _ensure_2d(spectrum)
    
    m = int(bandwidth)
    if m % 2 != 1:
        raise ValueError("bandwidth for savitzky_golay must be an odd integer")
    if m < 3:
        raise ValueError("bandwidth must be at least 3")
    
    # Check linearly spaced frequencies
    diff = np.diff(frequencies)
    if np.abs(np.min(diff) - np.max(diff)) > 1e-6:
        raise ValueError("frequencies must be linearly spaced for savitzky_golay")
    
    df = diff[0]
    
    # Compute coefficients for simplified Savitzky-Golay
    nterms = ((m - 1) // 2) + 1
    coefficients = np.empty(nterms)
    for idx, i in enumerate(range(-(nterms - 1), 1)):
        coefficients[idx] = (3 * m * m - 7 - 20 * abs(i * i)) / 4
    norm_coef = m * (m * m - 4) / 3
    
    # Map center frequencies to indices
    f_min = np.min(frequencies)
    nfcs = np.round((center_frequencies - f_min) / df).astype(int)
    
    n_spectra = spectrum_2d.shape[0]
    n_freq = spectrum_2d.shape[1]
    n_fc = len(center_frequencies)
    n_coeff = len(coefficients)
    
    smoothed = np.zeros((n_spectra, n_fc))
    
    for nfc_idx, spec_idx in enumerate(nfcs):
        # Check bounds
        if spec_idx < n_coeff or spec_idx + n_coeff > n_freq:
            continue
            
        # Apply symmetric convolution
        summation = coefficients[-1] * spectrum_2d[:, spec_idx]
        for rel_idx, coef in enumerate(coefficients[:-1][::-1]):
            summation += coef * (spectrum_2d[:, spec_idx + (rel_idx + 1)] +
                                 spectrum_2d[:, spec_idx - (rel_idx + 1)])
        
        smoothed[:, nfc_idx] = summation / norm_coef
    
    return smoothed[0] if was_1d else smoothed


def linear_rectangular(frequencies: np.ndarray,
                       spectrum: np.ndarray,
                       center_frequencies: np.ndarray,
                       bandwidth: float = 0.5) -> np.ndarray:
    """
    Linear rectangular (boxcar) smoothing.
    
    Simple averaging within a fixed Hz bandwidth.
    
    Parameters
    ----------
    frequencies : ndarray
        Frequencies of input spectrum, shape (nfrequency,).
    spectrum : ndarray
        Spectrum to smooth, shape (nspectrum, nfrequency) or (nfrequency,).
    center_frequencies : ndarray
        Center frequencies for output, shape (nfc,).
    bandwidth : float
        Width of averaging window in Hz. Default is 0.5.
        
    Returns
    -------
    ndarray
        Smoothed spectrum at center frequencies.
    """
    spectrum_2d, was_1d = _ensure_2d(spectrum)
    n_spectra = spectrum_2d.shape[0]
    n_fc = len(center_frequencies)
    
    half_bw = bandwidth / 2.0
    smoothed = np.zeros((n_spectra, n_fc))
    
    for fc_idx, fc in enumerate(center_frequencies):
        if fc < 1e-6:
            continue
            
        # Find frequencies within window
        valid = (frequencies >= 1e-6) & (np.abs(frequencies - fc) <= half_bw)
        
        if not np.any(valid):
            continue
            
        # Simple average (all weights = 1)
        n_valid = np.sum(valid)
        smoothed[:, fc_idx] = np.sum(spectrum_2d[:, valid], axis=1) / n_valid
    
    return smoothed[0] if was_1d else smoothed


def log_rectangular(frequencies: np.ndarray,
                    spectrum: np.ndarray,
                    center_frequencies: np.ndarray,
                    bandwidth: float = 0.05) -> np.ndarray:
    """
    Log-scale rectangular (boxcar) smoothing.
    
    Averaging in log-frequency space with constant log10 bandwidth.
    
    Parameters
    ----------
    frequencies : ndarray
        Frequencies of input spectrum, shape (nfrequency,).
    spectrum : ndarray
        Spectrum to smooth, shape (nspectrum, nfrequency) or (nfrequency,).
    center_frequencies : ndarray
        Center frequencies for output, shape (nfc,).
    bandwidth : float
        Width of averaging window in log10 scale. Default is 0.05.
        
    Returns
    -------
    ndarray
        Smoothed spectrum at center frequencies.
    """
    spectrum_2d, was_1d = _ensure_2d(spectrum)
    n_spectra = spectrum_2d.shape[0]
    n_fc = len(center_frequencies)
    
    lower_limit = 10 ** (-bandwidth / 2)
    upper_limit = 10 ** (+bandwidth / 2)
    
    smoothed = np.zeros((n_spectra, n_fc))
    
    for fc_idx, fc in enumerate(center_frequencies):
        if fc < 1e-6:
            continue
            
        f_on_fc = frequencies / fc
        
        # Find frequencies within window
        valid = (frequencies >= 1e-6) & (f_on_fc >= lower_limit) & (f_on_fc <= upper_limit)
        
        if not np.any(valid):
            continue
            
        n_valid = np.sum(valid)
        smoothed[:, fc_idx] = np.sum(spectrum_2d[:, valid], axis=1) / n_valid
    
    return smoothed[0] if was_1d else smoothed


def linear_triangular(frequencies: np.ndarray,
                      spectrum: np.ndarray,
                      center_frequencies: np.ndarray,
                      bandwidth: float = 0.5) -> np.ndarray:
    """
    Linear triangular smoothing.
    
    Weighted average with linearly decreasing weights from center.
    
    Parameters
    ----------
    frequencies : ndarray
        Frequencies of input spectrum, shape (nfrequency,).
    spectrum : ndarray
        Spectrum to smooth, shape (nspectrum, nfrequency) or (nfrequency,).
    center_frequencies : ndarray
        Center frequencies for output, shape (nfc,).
    bandwidth : float
        Width of triangular window in Hz. Default is 0.5.
        
    Returns
    -------
    ndarray
        Smoothed spectrum at center frequencies.
    """
    spectrum_2d, was_1d = _ensure_2d(spectrum)
    n_spectra = spectrum_2d.shape[0]
    n_fc = len(center_frequencies)
    
    half_bw = bandwidth / 2.0
    smoothed = np.zeros((n_spectra, n_fc))
    
    for fc_idx, fc in enumerate(center_frequencies):
        if fc < 1e-6:
            continue
            
        f_minus_fc = frequencies - fc
        
        # Find frequencies within window
        valid = (frequencies >= 1e-6) & (np.abs(f_minus_fc) <= half_bw)
        
        if not np.any(valid):
            continue
            
        # Triangular weights: 1 at center, 0 at edges
        f_minus_fc_valid = f_minus_fc[valid]
        window = 1.0 - np.abs(f_minus_fc_valid) * (2.0 / bandwidth)
        
        window_sum = np.sum(window)
        if window_sum > 0:
            smoothed[:, fc_idx] = np.sum(window * spectrum_2d[:, valid], axis=1) / window_sum
    
    return smoothed[0] if was_1d else smoothed


def log_triangular(frequencies: np.ndarray,
                   spectrum: np.ndarray,
                   center_frequencies: np.ndarray,
                   bandwidth: float = 0.05) -> np.ndarray:
    """
    Log-scale triangular smoothing.
    
    Weighted average with linearly decreasing weights in log-frequency space.
    
    Parameters
    ----------
    frequencies : ndarray
        Frequencies of input spectrum, shape (nfrequency,).
    spectrum : ndarray
        Spectrum to smooth, shape (nspectrum, nfrequency) or (nfrequency,).
    center_frequencies : ndarray
        Center frequencies for output, shape (nfc,).
    bandwidth : float
        Width of triangular window in log10 scale. Default is 0.05.
        
    Returns
    -------
    ndarray
        Smoothed spectrum at center frequencies.
    """
    spectrum_2d, was_1d = _ensure_2d(spectrum)
    n_spectra = spectrum_2d.shape[0]
    n_fc = len(center_frequencies)
    
    lower_limit = 10 ** (-bandwidth / 2)
    upper_limit = 10 ** (+bandwidth / 2)
    
    smoothed = np.zeros((n_spectra, n_fc))
    
    for fc_idx, fc in enumerate(center_frequencies):
        if fc < 1e-6:
            continue
            
        f_on_fc = frequencies / fc
        
        # Find frequencies within window
        valid = (frequencies >= 1e-6) & (f_on_fc >= lower_limit) & (f_on_fc <= upper_limit)
        
        if not np.any(valid):
            continue
            
        # Triangular weights in log space
        f_on_fc_valid = f_on_fc[valid]
        window = 1.0 - np.abs(np.log10(f_on_fc_valid)) * (2.0 / bandwidth)
        
        window_sum = np.sum(window)
        if window_sum > 0:
            smoothed[:, fc_idx] = np.sum(window * spectrum_2d[:, valid], axis=1) / window_sum
    
    return smoothed[0] if was_1d else smoothed


def no_smoothing(frequencies: np.ndarray,
                 spectrum: np.ndarray,
                 center_frequencies: np.ndarray,
                 bandwidth: float = 0) -> np.ndarray:
    """
    No smoothing - interpolation only.
    
    Interpolates spectrum to center frequencies without any smoothing.
    
    Parameters
    ----------
    frequencies : ndarray
        Frequencies of input spectrum, shape (nfrequency,).
    spectrum : ndarray
        Spectrum to interpolate, shape (nspectrum, nfrequency) or (nfrequency,).
    center_frequencies : ndarray
        Center frequencies for output, shape (nfc,).
    bandwidth : float
        Ignored. Present for interface compatibility.
        
    Returns
    -------
    ndarray
        Interpolated spectrum at center frequencies.
    """
    spectrum_2d, was_1d = _ensure_2d(spectrum)
    n_spectra = spectrum_2d.shape[0]
    
    # Simple linear interpolation for each spectrum
    result = np.zeros((n_spectra, len(center_frequencies)))
    for i in range(n_spectra):
        result[i] = np.interp(center_frequencies, frequencies, spectrum_2d[i])
    
    return result[0] if was_1d else result
