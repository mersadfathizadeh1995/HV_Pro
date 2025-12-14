"""
HVSR Pro - Professional HVSR Analysis Package
==============================================

A modern, integrated HVSR analysis workflow for the OSCAR project.

Main Components:
    - HVSRDataHandler: Unified data import and management
    - HVSRProcessor: Core HVSR processing engine
    - WindowManager: Advanced window management
    - WindowRejectionEngine: Multi-algorithm rejection
    - HVSRVisualizer: Interactive visualization

Example:
    >>> from hvsr_pro import HVSRDataHandler, HVSRProcessor
    >>> handler = HVSRDataHandler()
    >>> data = handler.load_data('data.txt')
    >>> processor = HVSRProcessor()
    >>> results = processor.process(data)
"""

__version__ = '0.1.0'
__author__ = 'OSCAR HVSR Development Team'
__all__ = [
    'HVSRDataHandler',
    'WindowManager',
    'Window',
    'WindowState',
    'WindowCollection',
    'RejectionEngine',
    'HVSRProcessor',
    'HVSRResult',
    'HVSRPlotter',
]

# Core imports
from hvsr_pro.core.data_handler import HVSRDataHandler
from hvsr_pro.core.metadata import MetadataManager

# Processing imports
from hvsr_pro.processing.window_manager import WindowManager
from hvsr_pro.processing.window_structures import Window, WindowState, WindowCollection
from hvsr_pro.processing.rejection_engine import RejectionEngine
from hvsr_pro.processing.hvsr_processor import HVSRProcessor
from hvsr_pro.processing.hvsr_structures import HVSRResult

# Visualization imports
from hvsr_pro.visualization.plotter import HVSRPlotter

# Version info
def get_version():
    """Return the current version of HVSR Pro."""
    return __version__


def get_info():
    """Return package information."""
    return {
        'name': 'HVSR Pro',
        'version': __version__,
        'author': __author__,
        'description': 'Professional HVSR Analysis Package for OSCAR'
    }
