"""
HVSR Pro Dock Widgets
=====================

Dockable panel widgets for the application.

Structure:
- export/: Export functionality dock
- layers/: Window layers dock
- peak_picker/: Peak picker dock
- azimuthal/: Azimuthal properties dock
- properties/: Plot properties dock with sections
"""

from .export.export_dock import ExportDock
from .layers.layers_dock import WindowLayersDock
from .peak_picker.peak_picker_dock import PeakPickerDock
from .azimuthal import AzimuthalPropertiesDock, AzimuthalDock
from .properties.properties_dock import PropertiesDock, PlotProperties

__all__ = [
    'ExportDock',
    'WindowLayersDock',
    'PeakPickerDock',
    'AzimuthalPropertiesDock',
    'AzimuthalDock',
    'PropertiesDock',
    'PlotProperties',
]
