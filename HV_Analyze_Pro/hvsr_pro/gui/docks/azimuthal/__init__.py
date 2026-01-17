"""
Azimuthal Properties Dock
=========================

Azimuthal analysis properties and export dock widget.

Package Structure:
- azimuthal_dock.py: Main dock widget
- sections/: Collapsible section components (theme, figure, legend, font, export)
- dialogs/: Dialog components (export report selection)
- exporters/: Export functions (CSV, JSON, figures, reports)
"""

from .azimuthal_dock import AzimuthalDock, AzimuthalPropertiesDock

# Re-export sections for extensibility
from .sections import (
    ThemeSection,
    FigureSection,
    LegendSection,
    FontSection,
    ExportSection,
)

# Re-export dialogs
from .dialogs import ExportReportDialog

# Re-export exporters
from .exporters import (
    write_csv,
    write_json,
    write_individual_csv,
    write_peaks_csv,
    export_plot_to_file,
    get_format_info,
    ReportGenerator,
)

__all__ = [
    # Main dock widget
    'AzimuthalDock',
    'AzimuthalPropertiesDock',  # Backward compatibility alias
    
    # Sections
    'ThemeSection',
    'FigureSection',
    'LegendSection',
    'FontSection',
    'ExportSection',
    
    # Dialogs
    'ExportReportDialog',
    
    # Exporters
    'write_csv',
    'write_json',
    'write_individual_csv',
    'write_peaks_csv',
    'export_plot_to_file',
    'get_format_info',
    'ReportGenerator',
]
