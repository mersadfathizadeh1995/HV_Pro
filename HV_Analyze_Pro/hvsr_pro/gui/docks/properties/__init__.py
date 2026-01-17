"""
Properties Dock Components
==========================

Plot properties dock widget and its modular sections.

This package provides:
- PropertiesDock: The main dock widget
- PlotProperties: Data class for plot settings
- Section components for different property groups
"""

from .properties_dock import PropertiesDock, PlotProperties
from .sections import (
    PresetSection,
    AxisSection,
    CurvesSection,
    AnnotationsSection,
    AppearanceSection,
)

__all__ = [
    'PropertiesDock',
    'PlotProperties',
    'PresetSection',
    'AxisSection',
    'CurvesSection',
    'AnnotationsSection',
    'AppearanceSection',
]
