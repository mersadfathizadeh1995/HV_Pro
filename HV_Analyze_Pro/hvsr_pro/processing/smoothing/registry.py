"""
Smoothing Registry
==================

Registry of available smoothing operators for dynamic lookup.
"""

from typing import Callable, Dict, Optional
import numpy as np

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
from .settings import SmoothingMethod, DEFAULT_BANDWIDTHS


# Type alias for smoothing functions
SmoothingFunction = Callable[[np.ndarray, np.ndarray, np.ndarray, float], np.ndarray]


# Registry mapping method names to functions
SMOOTHING_OPERATORS: Dict[str, SmoothingFunction] = {
    "konno_ohmachi": konno_ohmachi,
    "parzen": parzen,
    "savitzky_golay": savitzky_golay,
    "linear_rectangular": linear_rectangular,
    "log_rectangular": log_rectangular,
    "linear_triangular": linear_triangular,
    "log_triangular": log_triangular,
    "none": no_smoothing,
}


def get_smoothing_function(method_name: str) -> SmoothingFunction:
    """
    Get smoothing function by name.
    
    Parameters
    ----------
    method_name : str
        Name of the smoothing method (e.g., 'konno_ohmachi', 'parzen').
        
    Returns
    -------
    callable
        The smoothing function.
        
    Raises
    ------
    ValueError
        If method_name is not recognized.
    """
    # Normalize name
    name_lower = method_name.lower().replace(" ", "_").replace("-", "_")
    
    if name_lower not in SMOOTHING_OPERATORS:
        available = ", ".join(SMOOTHING_OPERATORS.keys())
        raise ValueError(
            f"Unknown smoothing method: '{method_name}'. "
            f"Available methods: {available}"
        )
    
    return SMOOTHING_OPERATORS[name_lower]


def get_smoothing_function_by_enum(method: SmoothingMethod) -> SmoothingFunction:
    """
    Get smoothing function by enum.
    
    Parameters
    ----------
    method : SmoothingMethod
        The smoothing method enum.
        
    Returns
    -------
    callable
        The smoothing function.
    """
    return SMOOTHING_OPERATORS[method.value]


def get_default_bandwidth(method_name: str) -> float:
    """
    Get default bandwidth for a smoothing method.
    
    Parameters
    ----------
    method_name : str
        Name of the smoothing method.
        
    Returns
    -------
    float
        Default bandwidth value.
    """
    try:
        method = SmoothingMethod.from_string(method_name)
        return DEFAULT_BANDWIDTHS.get(method, 40.0)
    except ValueError:
        return 40.0


def list_available_methods() -> list:
    """
    List all available smoothing method names.
    
    Returns
    -------
    list
        List of method name strings.
    """
    return list(SMOOTHING_OPERATORS.keys())


def apply_smoothing(frequencies: np.ndarray,
                    spectrum: np.ndarray,
                    center_frequencies: np.ndarray,
                    method: str = 'konno_ohmachi',
                    bandwidth: Optional[float] = None) -> np.ndarray:
    """
    Apply smoothing to spectrum using specified method.
    
    Convenience function that handles method lookup and default bandwidth.
    
    Parameters
    ----------
    frequencies : ndarray
        Frequencies of input spectrum, shape (nfrequency,).
    spectrum : ndarray
        Spectrum to smooth, shape (nspectrum, nfrequency) or (nfrequency,).
    center_frequencies : ndarray
        Center frequencies for output, shape (nfc,).
    method : str
        Smoothing method name. Default is 'konno_ohmachi'.
    bandwidth : float, optional
        Bandwidth parameter. If None, uses method's default.
        
    Returns
    -------
    ndarray
        Smoothed spectrum at center frequencies.
    """
    smooth_fn = get_smoothing_function(method)
    
    if bandwidth is None:
        bandwidth = get_default_bandwidth(method)
    
    return smooth_fn(frequencies, spectrum, center_frequencies, bandwidth)
