"""
Amplitude-Based Rejection Algorithm
====================================

Detects clipping, dead channels, and extreme amplitudes.
"""

import numpy as np
from typing import Optional

from hvsr_pro.processing.rejection.base import BaseRejectionAlgorithm, RejectionResult
from hvsr_pro.processing.windows import Window


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

