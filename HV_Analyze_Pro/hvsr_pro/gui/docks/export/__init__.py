"""
Export Dock Package
===================

Comprehensive export functionality for HVSR results.
Includes modular sections and pure exporter functions.
"""

from .export_dock import ExportDock

# Re-export sections for extensibility
from .sections import (
    PlotExportSection,
    DataExportSection,
    StatsExportSection,
    ComparisonFiguresSection,
    ReportSection,
    SessionSection,
)

# Re-export pure functions for programmatic use
from .exporters import (
    export_csv,
    export_json,
    interpolate_curve,
    export_statistics_csv,
    export_comparison_figure,
    export_waveform_figure,
    export_prepost_figure,
)

__all__ = [
    # Main dock
    'ExportDock',
    # Sections
    'PlotExportSection',
    'DataExportSection',
    'StatsExportSection',
    'ComparisonFiguresSection',
    'ReportSection',
    'SessionSection',
    # Exporters
    'export_csv',
    'export_json',
    'interpolate_curve',
    'export_statistics_csv',
    'export_comparison_figure',
    'export_waveform_figure',
    'export_prepost_figure',
]
