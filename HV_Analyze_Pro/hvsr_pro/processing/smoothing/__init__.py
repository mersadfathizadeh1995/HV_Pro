"""
Smoothing Package
==================

Frequency-domain smoothing methods for HVSR spectral analysis.

This package provides:
- 7 smoothing methods with unified interface
- Configuration dataclasses
- Registry for dynamic method selection

Available Methods
-----------------
- konno_ohmachi: Log-frequency smoothing (standard for HVSR)
- parzen: Constant Hz bandwidth smoothing
- savitzky_golay: Polynomial fitting smoothing
- linear_rectangular: Simple boxcar average in Hz
- log_rectangular: Boxcar average in log-frequency
- linear_triangular: Weighted average in Hz
- log_triangular: Weighted average in log-frequency
- no_smoothing: Interpolation only

Example
-------
>>> from hvsr_pro.processing.smoothing import (
...     apply_smoothing, SmoothingConfig, SmoothingMethod
... )
>>> 
>>> # Simple usage
>>> smoothed = apply_smoothing(freqs, spectrum, center_freqs, 
...                            method='konno_ohmachi', bandwidth=40)
>>> 
>>> # Using config
>>> config = SmoothingConfig(
...     method=SmoothingMethod.PARZEN,
...     bandwidth=0.5
... )
>>> smooth_fn = get_smoothing_function(config.method.value)
>>> smoothed = smooth_fn(freqs, spectrum, center_freqs, config.bandwidth)
"""

from .methods import (
    konno_ohmachi,
    parzen,
    savitzky_golay,
    linear_rectangular,
    log_rectangular,
    linear_triangular,
    log_triangular,
    no_smoothing,
)

from .settings import (
    SmoothingMethod,
    SmoothingConfig,
    DEFAULT_BANDWIDTHS,
    BANDWIDTH_DESCRIPTIONS,
    BANDWIDTH_RANGES,
    get_method_info,
    list_available_methods,
)

from .registry import (
    SMOOTHING_OPERATORS,
    get_smoothing_function,
    get_smoothing_function_by_enum,
    get_default_bandwidth,
    apply_smoothing,
)


__all__ = [
    # Methods
    'konno_ohmachi',
    'parzen',
    'savitzky_golay',
    'linear_rectangular',
    'log_rectangular',
    'linear_triangular',
    'log_triangular',
    'no_smoothing',
    # Settings
    'SmoothingMethod',
    'SmoothingConfig',
    'DEFAULT_BANDWIDTHS',
    'BANDWIDTH_DESCRIPTIONS',
    'BANDWIDTH_RANGES',
    'get_method_info',
    'list_available_methods',
    # Registry
    'SMOOTHING_OPERATORS',
    'get_smoothing_function',
    'get_smoothing_function_by_enum',
    'get_default_bandwidth',
    'apply_smoothing',
]
