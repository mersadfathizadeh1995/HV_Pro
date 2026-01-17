"""
Data Input Dialog Components
============================

Modular components for the data input dialog.

This package provides:
- DataInputTabBase: Base class for data input tabs
- TimeRangePanel: Reusable time range selection panel
- PreviewPanel: Visual preview with matplotlib
- File detection utilities
- Tab components for different loading modes
- DataInputDialog: The main dialog (imported from original location)
"""

from .base_tab import DataInputTabBase
from .time_range_panel import TimeRangePanel
from .preview_panel import PreviewPanel
from .file_detector import (
    can_auto_detect_channels,
    detect_type1_files,
    detect_type2_files,
    group_component_files,
    extract_base_and_component,
    get_file_info,
    get_miniseed_info,
    scan_directory_for_seismic_files,
)

# Tab components
from .tabs import (
    SingleFileTab,
    MultiType1Tab,
    MultiType2Tab,
    AdvancedOptionsTab,
)

# Main dialog
from .data_input_dialog import DataInputDialog

__all__ = [
    # Base classes
    'DataInputTabBase',
    'TimeRangePanel',
    'PreviewPanel',
    # File detection
    'can_auto_detect_channels',
    'detect_type1_files',
    'detect_type2_files',
    'group_component_files',
    'extract_base_and_component',
    'get_file_info',
    'get_miniseed_info',
    'scan_directory_for_seismic_files',
    # Tab components
    'SingleFileTab',
    'MultiType1Tab',
    'MultiType2Tab',
    'AdvancedOptionsTab',
    # Main dialog
    'DataInputDialog',
]
