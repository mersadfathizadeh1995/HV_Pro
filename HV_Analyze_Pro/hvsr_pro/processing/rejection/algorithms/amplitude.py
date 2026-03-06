"""
Amplitude-Based Rejection Algorithm
====================================

Detects clipping, dead channels, and extreme amplitudes.
Supports configurable presets (strict/moderate/lenient) and custom thresholds.
"""

import numpy as np
from typing import Optional, Dict, Any

from hvsr_pro.processing.rejection.base import BaseRejectionAlgorithm, RejectionResult
from hvsr_pro.processing.windows import Window


# Amplitude preset configurations
AMPLITUDE_PRESETS = {
    'strict': {
        'max_amplitude': 1e6,
        'min_rms': 1e-8,
        'clipping_threshold': 0.90,
        'clipping_max_percent': 0.005,
    },
    'moderate': {
        'max_amplitude': 1e7,
        'min_rms': 1e-10,
        'clipping_threshold': 0.95,
        'clipping_max_percent': 0.01,
    },
    'lenient': {
        'max_amplitude': 1e8,
        'min_rms': 1e-12,
        'clipping_threshold': 0.99,
        'clipping_max_percent': 0.05,
    },
}


class AmplitudeRejection(BaseRejectionAlgorithm):
    """
    Amplitude-based rejection for extreme amplitudes.
    
    Rejects windows with clipping, dead channels, or unrealistic amplitudes.
    Supports preset configurations (strict/moderate/lenient) or custom thresholds.
    
    Parameters:
        max_amplitude: Maximum acceptable absolute amplitude (None = no limit)
        min_rms: Minimum RMS for non-dead channel detection
        clipping_threshold: Fraction of max amplitude considered clipping
        clipping_max_percent: Maximum fraction of samples allowed at clipping level
        preset: Optional preset name ('strict', 'moderate', 'lenient')
    """
    
    def __init__(self,
                 max_amplitude: Optional[float] = None,
                 min_rms: float = 1e-10,
                 clipping_threshold: float = 0.95,
                 clipping_max_percent: float = 0.01,
                 preset: Optional[str] = None,
                 name: str = "Amplitude"):
        super().__init__(name, threshold=0.5)
        
        # Apply preset if specified
        if preset and preset in AMPLITUDE_PRESETS:
            p = AMPLITUDE_PRESETS[preset]
            self.max_amplitude = p['max_amplitude']
            self.min_rms = p['min_rms']
            self.clipping_threshold = p['clipping_threshold']
            self.clipping_max_percent = p['clipping_max_percent']
        else:
            self.max_amplitude = max_amplitude
            self.min_rms = min_rms
            self.clipping_threshold = clipping_threshold
            self.clipping_max_percent = clipping_max_percent
    
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
                issues.append(f"{component_name} dead channel (RMS={rms:.2e})")
                scores.append(1.0)
                continue
            
            # Check for extreme amplitude
            abs_data = np.abs(data)
            max_val = np.max(abs_data)
            
            if self.max_amplitude is not None:
                if max_val > self.max_amplitude:
                    issues.append(f"{component_name} exceeds max amplitude ({max_val:.2e})")
                    scores.append(1.0)
            
            # Check for saturation/clipping
            if max_val > 0:
                near_max = np.sum(abs_data > self.clipping_threshold * max_val)
                clipping_fraction = near_max / len(data)
                
                if clipping_fraction > self.clipping_max_percent:
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
                'min_rms': self.min_rms,
                'clipping_threshold': self.clipping_threshold,
                'clipping_max_percent': self.clipping_max_percent
            }
        )
    
    @staticmethod
    def get_preset_names():
        """Get list of available preset names."""
        return list(AMPLITUDE_PRESETS.keys())
    
    @staticmethod
    def get_preset_params(preset: str) -> Dict[str, Any]:
        """Get parameters for a preset."""
        return AMPLITUDE_PRESETS.get(preset, AMPLITUDE_PRESETS['moderate']).copy()
