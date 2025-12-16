"""
Azimuthal HVSR Processing Module
================================

This module provides azimuthal HVSR analysis capabilities, adapted from the hvsrpy package
by Joseph P. Vantassel (joseph.p.vantassel@gmail.com).

The module includes:
- Azimuthal HVSR computation at multiple rotation angles
- 3D visualization of HVSR vs frequency vs azimuth
- Statistical analysis across azimuths
"""

from .azimuthal_processor import AzimuthalHVSRProcessor
from .azimuthal_result import AzimuthalHVSRResult
from .azimuthal_plotting import (
    plot_azimuthal_contour_2d,
    plot_azimuthal_contour_3d,
    plot_azimuthal_summary
)

__all__ = [
    'AzimuthalHVSRProcessor',
    'AzimuthalHVSRResult',
    'plot_azimuthal_contour_2d',
    'plot_azimuthal_contour_3d',
    'plot_azimuthal_summary'
]

