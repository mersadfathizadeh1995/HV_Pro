"""
Data Input Dialog Components
============================

Modular components for the data input dialog.

This package provides:
- DataInputTabBase: Base class for data input tabs
- TimeRangePanel: Reusable time range selection panel
- DataInputDialog: The main dialog (imported from original location)
"""

from .base_tab import DataInputTabBase
from .time_range_panel import TimeRangePanel

# Import the original dialog for backward compatibility
from hvsr_pro.gui.data_input_dialog import DataInputDialog

__all__ = [
    'DataInputTabBase',
    'TimeRangePanel',
    'DataInputDialog',
]

