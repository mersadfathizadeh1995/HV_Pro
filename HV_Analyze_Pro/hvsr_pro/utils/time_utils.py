"""
Time utility functions for HVSR Pro
====================================
"""

from datetime import datetime
from typing import Union


def parse_time(time_str: str) -> datetime:
    """
    Parse time string to datetime.
    
    Args:
        time_str: Time string in various formats
        
    Returns:
        datetime object
    """
    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y%m%d_%H%M%S',
        '%Y-%m-%dT%H:%M:%S',
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(time_str, fmt)
        except ValueError:
            continue
    
    raise ValueError(f"Cannot parse time string: {time_str}")


def time_to_samples(time_seconds: float, sampling_rate: float) -> int:
    """
    Convert time in seconds to sample index.
    
    Args:
        time_seconds: Time in seconds
        sampling_rate: Sampling rate in Hz
        
    Returns:
        Sample index
    """
    return int(time_seconds * sampling_rate)
