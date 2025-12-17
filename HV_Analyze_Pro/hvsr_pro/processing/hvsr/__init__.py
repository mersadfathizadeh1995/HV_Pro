"""
HVSR Processing Package
========================

Core HVSR spectral processing engine.

Components:
    - processor: HVSRProcessor for computing HVSR
    - structures: HVSRResult, WindowSpectrum, Peak
    - spectral: FFT, smoothing, spectral computations
"""

from hvsr_pro.processing.hvsr.processor import HVSRProcessor
from hvsr_pro.processing.hvsr.structures import HVSRResult, WindowSpectrum, Peak
from hvsr_pro.processing.hvsr.spectral import (
    compute_fft,
    konno_ohmachi_smoothing,
    konno_ohmachi_smoothing_fast,
    calculate_horizontal_spectrum,
    calculate_hvsr,
    frequency_range_mask,
    resample_spectrum,
    logspace_frequencies,
)

__all__ = [
    # Main processor
    'HVSRProcessor',
    # Data structures
    'HVSRResult',
    'WindowSpectrum',
    'Peak',
    # Spectral functions
    'compute_fft',
    'konno_ohmachi_smoothing',
    'konno_ohmachi_smoothing_fast',
    'calculate_horizontal_spectrum',
    'calculate_hvsr',
    'frequency_range_mask',
    'resample_spectrum',
    'logspace_frequencies',
]

