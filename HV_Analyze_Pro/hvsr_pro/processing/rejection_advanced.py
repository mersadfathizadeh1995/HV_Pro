"""
Advanced Rejection Algorithms for HVSR Pro
===========================================

STA/LTA and frequency-domain rejection methods.
Includes Cox et al. (2020) FDWRA algorithm.
"""

import numpy as np
from typing import Dict, Any, Optional, List, Tuple
from scipy import signal as scipy_signal
from scipy import stats

from hvsr_pro.processing.rejection_algorithms import BaseRejectionAlgorithm, RejectionResult
from hvsr_pro.processing.window_structures import Window


class STALTARejection(BaseRejectionAlgorithm):
    """
    STA/LTA (Short-Term Average / Long-Term Average) rejection.
    
    Detects transients and spikes using the ratio of short-term
    to long-term energy averages.
    
    Reference: Classic earthquake detection algorithm adapted for HVSR.
    Uses industry-standard min/max bounds for robust detection.
    """
    
    def __init__(self,
                 sta_length: float = 1.0,
                 lta_length: float = 30.0,
                 min_ratio: float = 0.2,
                 max_ratio: float = 2.5,
                 threshold: Optional[float] = None,
                 name: str = "STA/LTA"):
        """
        Initialize STA/LTA rejection (industry-standard parameters).
        
        Args:
            sta_length: Short-term average window length in seconds (default: 1.0)
            lta_length: Long-term average window length in seconds (default: 30.0, ~window length)
            min_ratio: Minimum acceptable STA/LTA ratio (default: 0.2, industry-standard)
            max_ratio: Maximum acceptable STA/LTA ratio (default: 2.5, industry-standard)
            threshold: Legacy parameter (if provided, used as max_ratio for backward compatibility)
            name: Algorithm name
        """
        # Backward compatibility: if threshold provided, use it as max_ratio
        if threshold is not None:
            max_ratio = threshold
            super().__init__(name, threshold)
        else:
            super().__init__(name, max_ratio)
        
        self.sta_length = sta_length
        self.lta_length = lta_length
        self.min_ratio = min_ratio
        self.max_ratio = max_ratio
    
    def evaluate_window(self, window: Window) -> RejectionResult:
        """Evaluate window using STA/LTA ratio with min/max bounds (industry-standard)."""
        sampling_rate = window.data.sampling_rate
        
        # Convert lengths to samples
        sta_samples = int(self.sta_length * sampling_rate)
        lta_samples = int(self.lta_length * sampling_rate)
        
        # Calculate STA/LTA for each component
        ratios_max = []
        ratios_min = []
        
        for component_name in ['east', 'north', 'vertical']:
            component = window.data.get_component(component_name)
            data = np.abs(component.data)  # Envelope (absolute value)
            
            # Calculate STA and LTA
            sta = self._moving_average(data, sta_samples)
            lta = self._moving_average(data, lta_samples)
            
            # Calculate ratio (avoid division by zero)
            ratio = np.divide(sta, lta, out=np.zeros_like(sta), where=lta > 1e-10)
            
            # Get maximum and minimum ratios
            ratios_max.append(np.max(ratio))
            ratios_min.append(np.min(ratio))
        
        # Use maximum across all components for upper bound check
        max_sta_lta = max(ratios_max)
        # Use minimum across all components for lower bound check
        min_sta_lta = min(ratios_min)
        
        # Check both bounds (industry-standard approach)
        exceeds_max = max_sta_lta > self.max_ratio
        below_min = min_sta_lta < self.min_ratio
        should_reject = exceeds_max or below_min
        
        # Build reason string
        reasons = []
        if exceeds_max:
            reasons.append(f"Max STA/LTA = {max_sta_lta:.2f} > {self.max_ratio:.2f}")
        if below_min:
            reasons.append(f"Min STA/LTA = {min_sta_lta:.2f} < {self.min_ratio:.2f}")
        
        reason = " AND ".join(reasons) if reasons else f"STA/LTA within bounds ({min_sta_lta:.2f} - {max_sta_lta:.2f})"
        
        # Rejection score (normalize to 0-1)
        # Score based on how far outside bounds we are
        if exceeds_max:
            rejection_score = min(1.0, (max_sta_lta - self.max_ratio) / self.max_ratio)
        elif below_min:
            rejection_score = min(1.0, (self.min_ratio - min_sta_lta) / self.min_ratio)
        else:
            rejection_score = 0.0
        
        return RejectionResult(
            should_reject=should_reject,
            reason=reason,
            score=rejection_score,
            metadata={
                'max_sta_lta': float(max_sta_lta),
                'min_sta_lta': float(min_sta_lta),
                'east_max': float(ratios_max[0]),
                'north_max': float(ratios_max[1]),
                'vertical_max': float(ratios_max[2]),
                'east_min': float(ratios_min[0]),
                'north_min': float(ratios_min[1]),
                'vertical_min': float(ratios_min[2]),
                'sta_length': self.sta_length,
                'lta_length': self.lta_length,
                'min_ratio_threshold': self.min_ratio,
                'max_ratio_threshold': self.max_ratio
            }
        )
    
    @staticmethod
    def _moving_average(data: np.ndarray, window_size: int) -> np.ndarray:
        """Calculate moving average efficiently with padding."""
        if window_size <= 0 or window_size > len(data):
            window_size = len(data)
        
        # Use convolution for moving average (handles edges)
        kernel = np.ones(window_size) / window_size
        # 'same' mode returns output of same size as input
        return np.convolve(data, kernel, mode='same')


class FrequencyDomainRejection(BaseRejectionAlgorithm):
    """
    Frequency-domain rejection based on spectral characteristics.
    
    Detects windows with unusual frequency content, spikes in spectrum,
    or poor signal-to-noise in the frequency band of interest.
    
    Reference: Based on Cox et al. (2020) HVSR processing guidelines.
    """
    
    def __init__(self,
                 freq_range: tuple[float, float] = (0.2, 20.0),
                 spike_threshold: float = 5.0,
                 flatness_threshold: float = 1.0,
                 name: str = "FrequencyDomain"):
        """
        Initialize frequency-domain rejection.
        
        Args:
            freq_range: Frequency range of interest (f_min, f_max) in Hz
            spike_threshold: Threshold for spectral spike detection (std multiplier)
            flatness_threshold: Maximum acceptable spectral flatness (0-1)
                Note: Ambient seismic noise for HVSR typically has very high flatness (0.95-1.0).
                Default 1.0 effectively disables this check since spectral flatness ≤ 1.0 by definition.
                For non-HVSR applications, consider lowering to 0.95 to catch white noise artifacts.
            name: Algorithm name
        """
        super().__init__(name, threshold=0.5)
        self.freq_range = freq_range
        self.spike_threshold = spike_threshold
        self.flatness_threshold = flatness_threshold
    
    def evaluate_window(self, window: Window) -> RejectionResult:
        """Evaluate window in frequency domain."""
        sampling_rate = window.data.sampling_rate
        n_samples = window.n_samples
        
        # Calculate FFT for vertical component (most important for HVSR)
        vertical_data = window.data.vertical.data
        
        # Remove mean and apply taper if not already done
        vertical_data = vertical_data - np.mean(vertical_data)
        
        # Compute power spectrum
        freqs, psd = scipy_signal.welch(
            vertical_data,
            fs=sampling_rate,
            nperseg=min(n_samples, 1024),
            noverlap=None,
            scaling='density'
        )
        
        # Focus on frequency range of interest
        freq_mask = (freqs >= self.freq_range[0]) & (freqs <= self.freq_range[1])
        freqs_roi = freqs[freq_mask]
        psd_roi = psd[freq_mask]
        
        if len(psd_roi) == 0:
            return RejectionResult(
                should_reject=False,
                reason="Insufficient frequency resolution",
                score=0.0,
                metadata={'freq_range': self.freq_range}
            )
        
        # Check 1: Spectral spikes
        psd_mean = np.mean(psd_roi)
        psd_std = np.std(psd_roi)
        max_peak = np.max(psd_roi)
        
        spike_ratio = (max_peak - psd_mean) / (psd_std + 1e-10)
        has_spike = spike_ratio > self.spike_threshold
        
        # Check 2: Spectral flatness (Wiener entropy)
        geometric_mean = np.exp(np.mean(np.log(psd_roi + 1e-10)))
        arithmetic_mean = np.mean(psd_roi)
        spectral_flatness = geometric_mean / (arithmetic_mean + 1e-10)
        
        # Very flat spectrum can indicate white noise or digital artifacts
        # NOTE: Ambient seismic noise for HVSR typically has high flatness (0.95-1.0)
        # This check is conservative - only reject if spectral flatness is > threshold
        # Consider setting flatness_threshold=1.0 to disable this check for HVSR
        too_flat = spectral_flatness > self.flatness_threshold
        
        # Determine rejection
        reasons = []
        if has_spike:
            reasons.append(f"Spectral spike ({spike_ratio:.1f}σ)")
        if too_flat:
            reasons.append(f"Too flat (SF={spectral_flatness:.2f})")
        
        should_reject = bool(reasons)
        
        # Rejection score (combine factors)
        spike_score = min(1.0, spike_ratio / (2.0 * self.spike_threshold))
        flat_score = max(0.0, min(1.0, (spectral_flatness - 0.7) / 0.2))
        
        rejection_score = max(spike_score, flat_score)
        
        return RejectionResult(
            should_reject=should_reject,
            reason=" | ".join(reasons) if reasons else "Spectral quality OK",
            score=rejection_score,
            metadata={
                'spike_ratio': float(spike_ratio),
                'spectral_flatness': float(spectral_flatness),
                'peak_frequency': float(freqs_roi[np.argmax(psd_roi)]),
                'freq_range': self.freq_range,
                'has_spike': has_spike,
                'too_flat': too_flat
            }
        )


class AmplitudeRejection(BaseRejectionAlgorithm):
    """
    Amplitude-based rejection for extreme amplitudes.
    
    Rejects windows with clipping, dead channels, or unrealistic amplitudes.
    """
    
    def __init__(self,
                 max_amplitude: Optional[float] = None,
                 min_rms: float = 1e-10,
                 clipping_threshold: float = 0.95,
                 name: str = "Amplitude"):
        """
        Initialize amplitude rejection.
        
        Args:
            max_amplitude: Maximum acceptable amplitude (None = auto-detect)
            min_rms: Minimum RMS for non-dead channel
            clipping_threshold: Fraction of max amplitude considered clipping
            name: Algorithm name
        """
        super().__init__(name, threshold=0.5)
        self.max_amplitude = max_amplitude
        self.min_rms = min_rms
        self.clipping_threshold = clipping_threshold
    
    def evaluate_window(self, window: Window) -> RejectionResult:
        """Evaluate window based on amplitude characteristics."""
        issues = []
        scores = []
        
        for component_name in ['east', 'north', 'vertical']:
            component = window.data.get_component(component_name)
            data = component.data
            
            # Check RMS (dead channel detection)
            rms = np.sqrt(np.mean(data ** 2))
            if rms < self.min_rms:
                issues.append(f"{component_name} dead channel")
                scores.append(1.0)
                continue
            
            # Check for clipping
            abs_data = np.abs(data)
            max_val = np.max(abs_data)
            
            if self.max_amplitude is not None:
                if max_val > self.max_amplitude:
                    issues.append(f"{component_name} exceeds max amplitude")
                    scores.append(1.0)
            
            # Check for saturation (many samples at max value)
            if max_val > 0:
                near_max = np.sum(abs_data > self.clipping_threshold * max_val)
                clipping_fraction = near_max / len(data)
                
                if clipping_fraction > 0.01:  # >1% of samples clipping
                    issues.append(f"{component_name} clipping ({clipping_fraction:.1%})")
                    scores.append(min(1.0, clipping_fraction * 10))
        
        should_reject = len(issues) > 0
        rejection_score = max(scores) if scores else 0.0
        
        return RejectionResult(
            should_reject=should_reject,
            reason=" | ".join(issues) if issues else "Amplitude OK",
            score=rejection_score,
            metadata={
                'issues': issues,
                'max_amplitude': self.max_amplitude,
                'min_rms': self.min_rms
            }
        )
