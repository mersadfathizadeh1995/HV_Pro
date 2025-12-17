"""
Window Management Package
==========================

Window creation, management, and state tracking for HVSR analysis.

Components:
    - structures: Window, WindowState, WindowCollection
    - manager: WindowManager for window creation
    - peaks: Peak detection and analysis
    - quality: Window quality metrics calculator
"""

from hvsr_pro.processing.windows.structures import (
    Window,
    WindowState,
    WindowCollection,
)
from hvsr_pro.processing.windows.manager import WindowManager
from hvsr_pro.processing.windows.peaks import (
    detect_peaks,
    identify_fundamental_peak,
    peak_consistency_check,
    refine_peak_frequency,
    find_top_n_peaks,
    find_multi_peaks,
    sesame_peak_criteria,
)
from hvsr_pro.processing.windows.quality import WindowQualityCalculator

__all__ = [
    # Structures
    'Window',
    'WindowState',
    'WindowCollection',
    # Manager
    'WindowManager',
    # Peak detection
    'detect_peaks',
    'identify_fundamental_peak',
    'peak_consistency_check',
    'refine_peak_frequency',
    'find_top_n_peaks',
    'find_multi_peaks',
    'sesame_peak_criteria',
    # Quality
    'WindowQualityCalculator',
]

