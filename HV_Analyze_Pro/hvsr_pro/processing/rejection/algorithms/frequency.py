"""
Frequency-Domain Rejection Algorithm
=====================================

Spectral analysis for detecting anomalous frequency content.
"""

import numpy as np
from scipy import signal as scipy_signal

from hvsr_pro.processing.rejection.base import BaseRejectionAlgorithm, RejectionResult
from hvsr_pro.processing.windows import Window


class FrequencyDomainRejection(BaseRejectionAlgorithm):
    """
    Frequency-domain rejection based on spectral characteristics.
    
    Detects windows with unusual frequency content, spikes in spectrum,
    or poor signal-to-noise in the frequency band of interest.
    
    Reference: Based on Cox et al. (2020) HVSR processing guidelines.
    """
    
    def __init__(self,
                 freq_range: tuple = (0.2, 20.0),
                 spike_threshold: float = 5.0,
                 flatness_threshold: float = 1.0,
                 name: str = "FrequencyDomain"):
        """
        Initialize frequency-domain rejection.
        
        Args:
            freq_range: Frequency range of interest (f_min, f_max) in Hz
            spike_threshold: Threshold for spectral spike detection (std multiplier)
            flatness_threshold: Maximum acceptable spectral flatness (0-1)
                Note: Ambient noise typically has high flatness (0.95-1.0).
                Default 1.0 effectively disables this check.
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
        
        # Calculate FFT for vertical component
        vertical_data = window.data.vertical.data
        
        # Remove mean and apply taper
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
        
        # Very flat spectrum can indicate white noise
        too_flat = spectral_flatness > self.flatness_threshold
        
        # Determine rejection
        reasons = []
        if has_spike:
            reasons.append(f"Spectral spike ({spike_ratio:.1f}s)")
        if too_flat:
            reasons.append(f"Too flat (SF={spectral_flatness:.2f})")
        
        should_reject = bool(reasons)
        
        # Rejection score
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

