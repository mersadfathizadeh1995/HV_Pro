"""
STA/LTA Rejection Algorithm
============================

Short-Term Average / Long-Term Average for transient detection.
"""

import numpy as np
from typing import Optional

from hvsr_pro.processing.rejection.base import BaseRejectionAlgorithm, RejectionResult
from hvsr_pro.processing.windows import Window


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
            lta_length: Long-term average window length in seconds (default: 30.0)
            min_ratio: Minimum acceptable STA/LTA ratio (default: 0.2)
            max_ratio: Maximum acceptable STA/LTA ratio (default: 2.5)
            threshold: Legacy parameter (if provided, used as max_ratio)
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
        """Evaluate window using STA/LTA ratio with min/max bounds."""
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
        
        # Check both bounds
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
        
        # Rejection score
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
        
        # Use convolution for moving average
        kernel = np.ones(window_size) / window_size
        return np.convolve(data, kernel, mode='same')

