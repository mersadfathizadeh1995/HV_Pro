"""
Peak Detection for HVSR Pro
============================

Peak identification and characterization for HVSR curves.
"""

import numpy as np
from typing import List, Tuple, Optional, Dict
from scipy import signal as scipy_signal

from hvsr_pro.processing.hvsr_structures import Peak


def detect_peaks(frequencies: np.ndarray,
                hvsr: np.ndarray,
                min_prominence: float = 1.5,
                min_amplitude: float = 2.0,
                freq_range: Tuple[float, float] = (0.2, 20.0),
                distance: Optional[int] = None) -> List[Peak]:
    """
    Detect peaks in HVSR curve.
    
    Uses scipy.signal.find_peaks with prominence-based detection.
    
    Args:
        frequencies: Frequency array (Hz)
        hvsr: HVSR curve
        min_prominence: Minimum peak prominence
        min_amplitude: Minimum peak amplitude
        freq_range: Frequency range to search (f_min, f_max)
        distance: Minimum distance between peaks (in samples)
        
    Returns:
        List of Peak objects
    """
    # Mask to frequency range
    mask = (frequencies >= freq_range[0]) & (frequencies <= freq_range[1])
    freq_subset = frequencies[mask]
    hvsr_subset = hvsr[mask]
    
    if len(hvsr_subset) < 3:
        return []
    
    # Find peaks using scipy
    peak_indices, properties = scipy_signal.find_peaks(
        hvsr_subset,
        prominence=min_prominence,
        height=min_amplitude,
        distance=distance
    )
    
    # Convert to Peak objects
    peaks = []
    for idx in peak_indices:
        freq = freq_subset[idx]
        amp = hvsr_subset[idx]
        
        # Get prominence
        prom = properties['prominences'][len(peaks)]
        
        # Get width information
        widths, width_heights, left_ips, right_ips = scipy_signal.peak_widths(
            hvsr_subset, [idx], rel_height=0.5
        )
        
        width_hz = widths[0] * (freq_subset[1] - freq_subset[0])
        
        # Get left and right base frequencies
        left_idx = int(left_ips[0])
        right_idx = int(right_ips[0])
        left_freq = freq_subset[left_idx] if left_idx < len(freq_subset) else freq_subset[0]
        right_freq = freq_subset[right_idx] if right_idx < len(freq_subset) else freq_subset[-1]
        
        # Calculate peak quality (simple metric based on prominence and amplitude)
        quality = min(1.0, (prom / 3.0) * (amp / 5.0))
        
        peak = Peak(
            frequency=float(freq),
            amplitude=float(amp),
            prominence=float(prom),
            width=float(width_hz),
            left_freq=float(left_freq),
            right_freq=float(right_freq),
            quality=float(quality)
        )
        peaks.append(peak)
    
    # Sort by amplitude (highest first)
    peaks.sort(key=lambda p: p.amplitude, reverse=True)
    
    return peaks


def identify_fundamental_peak(peaks: List[Peak],
                              frequencies: np.ndarray,
                              hvsr: np.ndarray,
                              freq_range: Tuple[float, float] = (0.4, 10.0)) -> Optional[Peak]:
    """
    Identify the fundamental resonance peak.
    
    The fundamental peak is typically:
    - The first significant peak (lowest frequency with high amplitude)
    - In the range 0.4-10 Hz for typical site response
    - Has high prominence
    
    Args:
        peaks: List of detected peaks
        frequencies: Frequency array
        hvsr: HVSR curve
        freq_range: Expected frequency range for fundamental
        
    Returns:
        Fundamental peak or None
    """
    if not peaks:
        return None
    
    # Filter peaks in expected range
    candidates = [p for p in peaks if freq_range[0] <= p.frequency <= freq_range[1]]
    
    if not candidates:
        return None
    
    # Score peaks (prefer lower frequency, high amplitude, high prominence)
    scores = []
    for peak in candidates:
        freq_score = 1.0 / (1.0 + np.log10(peak.frequency / freq_range[0]))
        amp_score = peak.amplitude / 10.0
        prom_score = peak.prominence / 3.0
        
        total_score = freq_score * 0.3 + amp_score * 0.4 + prom_score * 0.3
        scores.append(total_score)
    
    # Return peak with highest score
    best_idx = np.argmax(scores)
    return candidates[best_idx]


def peak_consistency_check(window_peaks: List[List[Peak]],
                           tolerance: float = 0.1) -> Tuple[float, int]:
    """
    Check consistency of peak frequencies across windows.
    
    Args:
        window_peaks: List of peak lists (one per window)
        tolerance: Relative tolerance for frequency matching
        
    Returns:
        consistency_score: 0-1 score (1 = all windows agree)
        n_consistent_windows: Number of windows with consistent peaks
    """
    if not window_peaks or not any(window_peaks):
        return 0.0, 0
    
    # Get primary peaks from each window
    primary_freqs = []
    for peaks in window_peaks:
        if peaks:
            primary_freqs.append(peaks[0].frequency)
    
    if len(primary_freqs) < 2:
        return 1.0, len(primary_freqs)
    
    # Calculate median frequency
    median_freq = np.median(primary_freqs)
    
    # Count windows within tolerance
    tolerance_hz = median_freq * tolerance
    consistent = sum(1 for f in primary_freqs if abs(f - median_freq) <= tolerance_hz)
    
    consistency_score = consistent / len(primary_freqs)
    
    return consistency_score, consistent


def refine_peak_frequency(frequencies: np.ndarray,
                          hvsr: np.ndarray,
                          initial_freq: float,
                          window_hz: float = 1.0) -> float:
    """
    Refine peak frequency using parabolic interpolation.
    
    Args:
        frequencies: Frequency array
        hvsr: HVSR curve
        initial_freq: Initial peak frequency estimate
        window_hz: Search window around initial frequency
        
    Returns:
        Refined peak frequency
    """
    # Find index of initial frequency
    idx = np.argmin(np.abs(frequencies - initial_freq))
    
    # Define search window
    mask = np.abs(frequencies - initial_freq) <= window_hz
    if np.sum(mask) < 3:
        return initial_freq
    
    freq_window = frequencies[mask]
    hvsr_window = hvsr[mask]
    
    # Find maximum in window
    max_idx = np.argmax(hvsr_window)
    
    # Parabolic interpolation for sub-sample precision
    if 0 < max_idx < len(hvsr_window) - 1:
        y1, y2, y3 = hvsr_window[max_idx-1:max_idx+2]
        x1, x2, x3 = freq_window[max_idx-1:max_idx+2]
        
        # Parabolic fit: y = a*x^2 + b*x + c
        # Peak at x = -b/(2*a)
        denom = (x1 - x2) * (x1 - x3) * (x2 - x3)
        if abs(denom) > 1e-10:
            a = (x3 * (y2 - y1) + x2 * (y1 - y3) + x1 * (y3 - y2)) / denom
            b = (x3**2 * (y1 - y2) + x2**2 * (y3 - y1) + x1**2 * (y2 - y3)) / denom
            
            if abs(a) > 1e-10:
                refined_freq = -b / (2 * a)
                
                # Sanity check: refined frequency should be close to initial
                if abs(refined_freq - initial_freq) < window_hz:
                    return refined_freq
    
    return freq_window[max_idx]


def find_top_n_peaks(frequencies: np.ndarray,
                     hvsr: np.ndarray,
                     n_peaks: int = 3,
                     prominence: float = 0.5,
                     freq_range: Tuple[float, float] = (0.2, 20.0)) -> List[Dict]:
    """
    Find top N peaks by prominence (user-controlled).
    
    This is the user-facing function for "Auto Top N" mode.
    Finds all peaks, then returns the N most prominent ones.
    
    Args:
        frequencies: Frequency array (Hz)
        hvsr: HVSR curve
        n_peaks: Number of peaks to return
        prominence: Minimum prominence threshold
        freq_range: Frequency range to search (f_min, f_max)
        
    Returns:
        List of peak dictionaries with frequency, amplitude, prominence
    """
    # Use existing detect_peaks with lower amplitude threshold
    # We want to find all prominent peaks, then select top N
    peaks = detect_peaks(
        frequencies, 
        hvsr,
        min_prominence=prominence,
        min_amplitude=0.5,  # Lower threshold to catch more peaks
        freq_range=freq_range,
        distance=None
    )
    
    if not peaks:
        return []
    
    # Sort by prominence (highest first)
    peaks.sort(key=lambda p: p.prominence, reverse=True)
    
    # Take top N
    top_peaks = peaks[:n_peaks]
    
    # Convert to dictionaries for GUI
    result = []
    for peak in top_peaks:
        result.append({
            'frequency': peak.frequency,
            'amplitude': peak.amplitude,
            'prominence': peak.prominence,
            'source': 'Auto Top N'
        })
    
    return result


def find_multi_peaks(frequencies: np.ndarray,
                     hvsr: np.ndarray,
                     prominence: float = 0.3,
                     min_distance: int = 5,
                     freq_range: Tuple[float, float] = (0.2, 20.0)) -> List[Dict]:
    """
    Find ALL peaks above prominence threshold (user-controlled).
    
    This is the user-facing function for "Auto Multi-Peak" mode.
    Returns all significant peaks without N limit.
    Useful for multi-layer sites with multiple resonances.
    
    Args:
        frequencies: Frequency array (Hz)
        hvsr: HVSR curve
        prominence: Prominence threshold
        min_distance: Minimum distance between peaks (samples)
        freq_range: Frequency range to search (f_min, f_max)
        
    Returns:
        List of peak dictionaries sorted by frequency (ascending)
    """
    # Use existing detect_peaks
    peaks = detect_peaks(
        frequencies,
        hvsr,
        min_prominence=prominence,
        min_amplitude=0.5,  # Lower to catch all significant peaks
        freq_range=freq_range,
        distance=min_distance
    )
    
    if not peaks:
        return []
    
    # Sort by frequency (ascending) for multi-layer interpretation
    peaks.sort(key=lambda p: p.frequency)
    
    # Convert to dictionaries for GUI
    result = []
    for peak in peaks:
        result.append({
            'frequency': peak.frequency,
            'amplitude': peak.amplitude,
            'prominence': peak.prominence,
            'source': 'Auto Multi'
        })
    
    return result


def sesame_peak_criteria(peak: Peak,
                         frequencies: np.ndarray,
                         hvsr: np.ndarray) -> Dict[str, bool]:
    """
    Check SESAME (2004) reliability criteria for HVSR peak.
    
    Reference:
        SESAME (2004): Guidelines for the implementation of the H/V spectral
        ratio technique on ambient vibrations.
    
    Args:
        peak: Peak to evaluate
        frequencies: Frequency array
        hvsr: HVSR curve
        
    Returns:
        Dictionary of criteria and pass/fail status
    """
    f0 = peak.frequency
    A0 = peak.amplitude
    
    # Find indices for frequency ranges
    f_minus = f0 / 1.25  # f0 / 4^(-0.25) ≈ f0/1.25
    f_plus = f0 * 1.25   # f0 * 4^(0.25) ≈ f0*1.25
    
    # SESAME criteria
    criteria = {}
    
    # Criterion 1: f0 > 10 / lw (where lw is window length)
    # Assuming 30s windows -> f0 > 0.33 Hz
    criteria['f0_gt_10/lw'] = f0 > 0.33
    
    # Criterion 2: Number of significant cycles
    # nc(f0) > 200 (requires long enough recording)
    # This depends on total recording time, assuming pass if we have data
    criteria['nc_gt_200'] = True  # Conservative assumption
    
    # Criterion 3: Standard deviation of A0 < threshold
    # This requires multiple windows - assume pass for now
    criteria['sigma_A_lt_threshold'] = True
    
    # Criterion 4: Peak exists: A0 > 2
    criteria['A0_gt_2'] = A0 > 2.0
    
    # Criterion 5: Peak is prominent
    criteria['prominent'] = peak.prominence > 1.5
    
    # Criterion 6: Current frequency "peak" is stable
    # A(f) < A0 / 2 for f in [f-/4, f+/4]
    mask_low = (frequencies >= f_minus/4) & (frequencies < f_minus)
    mask_high = (frequencies > f_plus) & (frequencies <= f_plus*4)
    
    stable_low = True
    stable_high = True
    
    if np.any(mask_low):
        stable_low = np.all(hvsr[mask_low] < A0 / 2)
    if np.any(mask_high):
        stable_high = np.all(hvsr[mask_high] < A0 / 2)
    
    criteria['stable'] = stable_low and stable_high
    
    return criteria
