"""
File utility functions for HVSR Pro
====================================
"""

from pathlib import Path
from typing import Optional


def detect_file_format(filepath: str) -> str:
    """
    Detect file format from extension.
    
    Args:
        filepath: Path to file
        
    Returns:
        Format string
    """
    ext = Path(filepath).suffix.lower()
    
    format_map = {
        '.txt': 'txt',
        '.dat': 'txt',
        '.asc': 'txt',
        '.miniseed': 'miniseed',
        '.mseed': 'miniseed',
        '.ms': 'miniseed',
        '.sac': 'sac',
    }
    
    return format_map.get(ext, 'unknown')


def validate_path(filepath: str) -> Path:
    """
    Validate and return Path object.
    
    Args:
        filepath: Path string
        
    Returns:
        Path object
        
    Raises:
        FileNotFoundError: If path doesn't exist
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Path does not exist: {filepath}")
    return path
