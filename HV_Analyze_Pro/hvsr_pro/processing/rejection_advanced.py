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


class HVSRAmplitudeRejection(BaseRejectionAlgorithm):
    """
    Reject windows where HVSR peak amplitude < threshold.
    
    Based on MATLAB code Condition 1: PeakAmp > 1
    Reference: HVSRMakingPeak_Final.m (Salman Rahimi, University of Arkansas)
    
    Rationale: HVSR values < 1 indicate vertical motion dominates,
    which is physically unrealistic for site response and suggests
    either noise contamination or non-resonant conditions.
    
    NOTE: This algorithm requires HVSR curves to be computed first.
    It should be applied as a POST-HVSR rejection step.
    """
    
    def __init__(self,
                 min_amplitude: float = 1.0,
                 freq_range: Optional[Tuple[float, float]] = None,
                 name: str = "HVSR Amplitude"):
        """
        Initialize HVSR amplitude rejection.
        
        Args:
            min_amplitude: Minimum acceptable HVSR peak amplitude (default: 1.0)
            freq_range: Frequency range (f_min, f_max) in Hz for peak search
                       None = use full frequency range
            name: Algorithm name
        """
        super().__init__(name, threshold=min_amplitude)
        self.min_amplitude = min_amplitude
        self.freq_range = freq_range
    
    def evaluate_window(self, window: Window) -> RejectionResult:
        """
        Evaluate window based on HVSR peak amplitude.
        
        Requires window to have 'hvsr_curve' and 'hvsr_frequencies' attributes
        set during HVSR computation.
        """
        # Check if HVSR data is available
        if not hasattr(window, 'hvsr_curve') or window.hvsr_curve is None:
            return RejectionResult(
                should_reject=False,
                reason="No HVSR curve available (run HVSR first)",
                score=0.0,
                metadata={'error': 'missing_hvsr'}
            )
        
        hvsr_curve = window.hvsr_curve
        frequencies = getattr(window, 'hvsr_frequencies', None)
        
        # Apply frequency range filter if specified
        if self.freq_range is not None and frequencies is not None:
            f_min, f_max = self.freq_range
            mask = (frequencies >= f_min) & (frequencies <= f_max)
            if np.any(mask):
                hvsr_curve = hvsr_curve[mask]
                frequencies = frequencies[mask]
        
        # Find peak amplitude
        peak_amplitude = np.max(hvsr_curve)
        peak_idx = np.argmax(hvsr_curve)
        peak_frequency = frequencies[peak_idx] if frequencies is not None else None
        
        # Check if peak amplitude meets threshold
        should_reject = peak_amplitude < self.min_amplitude
        
        if should_reject:
            reason = f"HVSR peak amplitude ({peak_amplitude:.2f}) < {self.min_amplitude:.1f}"
        else:
            reason = f"HVSR peak amplitude OK ({peak_amplitude:.2f})"
        
        # Rejection score: how far below threshold
        if peak_amplitude < self.min_amplitude:
            rejection_score = 1.0 - (peak_amplitude / self.min_amplitude)
        else:
            rejection_score = 0.0
        
        return RejectionResult(
            should_reject=should_reject,
            reason=reason,
            score=rejection_score,
            metadata={
                'peak_amplitude': float(peak_amplitude),
                'peak_frequency': float(peak_frequency) if peak_frequency else None,
                'min_amplitude_threshold': self.min_amplitude,
                'freq_range': self.freq_range
            }
        )


class FlatPeakRejection(BaseRejectionAlgorithm):
    """
    Reject windows with flat/wide peaks or multiple peaks.
    
    Based on MATLAB code Condition 3:
        abs(HVInterestMean - HVInterestPeak) / HVInterestPeak > 0.15
    
    Reference: HVSRMakingPeak_Final.m (Salman Rahimi, University of Arkansas)
    
    A flat peak suggests:
    - Multiple modes interfering
    - Noise contamination
    - Non-resonant response
    - Wide impedance contrast zone
    
    NOTE: This algorithm requires HVSR curves to be computed first.
    It should be applied as a POST-HVSR rejection step.
    """
    
    def __init__(self,
                 flatness_threshold: float = 0.15,
                 freq_std_range: float = 3.0,
                 name: str = "Flat Peak"):
        """
        Initialize flat peak rejection.
        
        Args:
            flatness_threshold: Maximum acceptable flatness ratio (default: 0.15)
                Calculated as: abs(mean_hvsr - peak_hvsr) / peak_hvsr
                Lower values = more strict (rejects flatter peaks)
            freq_std_range: Number of standard deviations around mean peak frequency
                to define the frequency range of interest (default: 3.0)
            name: Algorithm name
        """
        super().__init__(name, threshold=flatness_threshold)
        self.flatness_threshold = flatness_threshold
        self.freq_std_range = freq_std_range
    
    def evaluate_window(self, window: Window) -> RejectionResult:
        """
        Evaluate window for flat/wide peaks.
        
        Requires window to have 'hvsr_curve' and 'hvsr_frequencies' attributes,
        plus collection-level 'mean_peak_frequency' and 'std_peak_frequency'.
        """
        # Check if HVSR data is available
        if not hasattr(window, 'hvsr_curve') or window.hvsr_curve is None:
            return RejectionResult(
                should_reject=False,
                reason="No HVSR curve available (run HVSR first)",
                score=0.0,
                metadata={'error': 'missing_hvsr'}
            )
        
        hvsr_curve = window.hvsr_curve
        frequencies = getattr(window, 'hvsr_frequencies', None)
        
        if frequencies is None:
            return RejectionResult(
                should_reject=False,
                reason="No frequency array available",
                score=0.0,
                metadata={'error': 'missing_frequencies'}
            )
        
        # Get mean and std of peak frequencies from collection
        # These should be set by the engine before evaluation
        mean_fn = getattr(window, 'collection_mean_fn', None)
        std_fn = getattr(window, 'collection_std_fn', None)
        
        if mean_fn is None or std_fn is None:
            # Fall back to using full frequency range
            freq_mask = np.ones(len(frequencies), dtype=bool)
        else:
            # Define frequency range of interest: mean +/- freq_std_range * std
            f_min = mean_fn - self.freq_std_range * std_fn
            f_max = mean_fn + self.freq_std_range * std_fn
            freq_mask = (frequencies >= f_min) & (frequencies <= f_max)
        
        if not np.any(freq_mask):
            return RejectionResult(
                should_reject=False,
                reason="No frequencies in range of interest",
                score=0.0,
                metadata={'error': 'no_frequencies_in_range'}
            )
        
        # Extract HVSR values in frequency range of interest
        hvsr_interest = hvsr_curve[freq_mask]
        
        # Calculate flatness: abs(mean - peak) / peak
        hvsr_mean = np.mean(hvsr_interest)
        hvsr_peak = np.max(hvsr_interest)
        
        if hvsr_peak > 0:
            flatness = abs(hvsr_mean - hvsr_peak) / hvsr_peak
        else:
            flatness = 1.0  # Treat zero peak as maximum flatness
        
        # MATLAB condition: flatness <= 0.15 indicates flat peak (reject)
        # Note: MATLAB rejects if abs(mean-peak)/peak <= 0.15
        # This means SMALL flatness = FLAT peak = BAD
        should_reject = flatness <= self.flatness_threshold
        
        if should_reject:
            reason = f"Flat peak detected (flatness={flatness:.3f} <= {self.flatness_threshold})"
        else:
            reason = f"Peak shape OK (flatness={flatness:.3f})"
        
        # Rejection score: inverse of flatness (lower flatness = higher score)
        if should_reject:
            rejection_score = 1.0 - (flatness / self.flatness_threshold)
        else:
            rejection_score = 0.0
        
        return RejectionResult(
            should_reject=should_reject,
            reason=reason,
            score=rejection_score,
            metadata={
                'flatness': float(flatness),
                'hvsr_mean': float(hvsr_mean),
                'hvsr_peak': float(hvsr_peak),
                'flatness_threshold': self.flatness_threshold,
                'freq_std_range': self.freq_std_range
            }
        )
