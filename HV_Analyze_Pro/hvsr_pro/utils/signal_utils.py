"""
Signal processing utilities for HVSR Pro
=========================================
"""

import numpy as np
from scipy import signal


def detrend(data: np.ndarray, method: str = 'linear') -> np.ndarray:
    """
    Remove trend from data.
    
    Args:
        data: Input data array
        method: 'linear' or 'constant'
        
    Returns:
        Detrended data
    """
    if method == 'linear':
        return signal.detrend(data, type='linear')
    elif method == 'constant':
        return signal.detrend(data, type='constant')
    else:
        raise ValueError(f"Unknown detrend method: {method}")


def taper(data: np.ndarray, taper_type: str = 'tukey', alpha: float = 0.1) -> np.ndarray:
    """
    Apply taper to data.
    
    Args:
        data: Input data array
        taper_type: Type of taper ('tukey', 'hann', 'hamming')
        alpha: Taper parameter (for tukey)
        
    Returns:
        Tapered data
    """
    n = len(data)
    
    if taper_type == 'tukey':
        window = signal.windows.tukey(n, alpha=alpha)
    elif taper_type == 'hann':
        window = signal.windows.hann(n)
    elif taper_type == 'hamming':
        window = signal.windows.hamming(n)
    else:
        raise ValueError(f"Unknown taper type: {taper_type}")
    
    return data * window


def check_gaps(data: np.ndarray, threshold: float = 1e10) -> bool:
    """
    Check for gaps or invalid values in data.
    
    Args:
        data: Input data array
        threshold: Maximum allowed value
        
    Returns:
        True if gaps/invalid values found
    """
    # Check for NaN or Inf
    if np.any(~np.isfinite(data)):
        return True
    
    # Check for unreasonably large values
    if np.any(np.abs(data) > threshold):
        return True
    
    return False
