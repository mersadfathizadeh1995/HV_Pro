"""
HVSR Pro Canvas Widgets
=======================

Matplotlib-based canvas widgets for plotting.
"""

from .interactive_canvas import InteractiveHVSRCanvas
from .preview_canvas import PreviewCanvas
from .plot_window_manager import PlotWindowManager

__all__ = [
    'InteractiveHVSRCanvas',
    'PreviewCanvas',
    'PlotWindowManager',
]
