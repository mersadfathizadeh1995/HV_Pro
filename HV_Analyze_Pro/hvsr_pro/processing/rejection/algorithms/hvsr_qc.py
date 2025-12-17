"""
HVSR-Specific QC Algorithms
============================

Post-HVSR rejection methods based on computed HVSR curves.

These algorithms require HVSR curves to be computed first and should
be applied as POST-HVSR rejection steps.
"""

import numpy as np
from typing import Optional, Tuple

from hvsr_pro.processing.rejection.base import BaseRejectionAlgorithm, RejectionResult
from hvsr_pro.processing.windows import Window


class HVSRAmplitudeRejection(BaseRejectionAlgorithm):
    """
    Reject windows where HVSR peak amplitude < threshold.
    
    Based on publication-quality QC Condition 1: PeakAmp > 1
    
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
        
        # Rejection score
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
    
    Based on publication-quality QC Condition 3:
        abs(HVInterestMean - HVInterestPeak) / HVInterestPeak > threshold
    
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
        mean_fn = getattr(window, 'collection_mean_fn', None)
        std_fn = getattr(window, 'collection_std_fn', None)
        
        if mean_fn is None or std_fn is None:
            # Fall back to using full frequency range
            freq_mask = np.ones(len(frequencies), dtype=bool)
        else:
            # Define frequency range of interest
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
        
        # SMALL flatness = FLAT peak = BAD
        should_reject = flatness <= self.flatness_threshold
        
        if should_reject:
            reason = f"Flat peak detected (flatness={flatness:.3f} <= {self.flatness_threshold})"
        else:
            reason = f"Peak shape OK (flatness={flatness:.3f})"
        
        # Rejection score
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

