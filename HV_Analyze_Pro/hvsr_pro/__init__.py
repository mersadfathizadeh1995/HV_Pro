"""
HVSR Pro - Professional HVSR Analysis Package
==============================================

A modern, integrated HVSR analysis workflow for seismic site characterization.

Main Components:
    - HVSRDataHandler: Unified data import and management
    - HVSRProcessor: Core HVSR processing engine
    - WindowManager: Advanced window management
    - RejectionEngine: Multi-algorithm window rejection
    - HVSRPlotter: Visualization tools

Subpackages:
    - core: Data handling and structures
    - processing: HVSR, windows, and rejection algorithms
    - visualization: Plotting and figure generation
    - config: Settings and validation
    - gui: Graphical user interface
    - cli: Command-line interface
    - api: Programmatic API

Example:
    >>> from hvsr_pro import HVSRDataHandler, HVSRProcessor
    >>> handler = HVSRDataHandler()
    >>> data = handler.load_data('data.txt')
    >>> processor = HVSRProcessor()
    >>> results = processor.process(data)
"""

__version__ = '0.2.0'
__author__ = 'OSCAR HVSR Development Team'
__all__ = [
    # Core
    'HVSRDataHandler',
    # Processing
    'WindowManager',
    'Window',
    'WindowState',
    'WindowCollection',
    'RejectionEngine',
    'HVSRProcessor',
    'HVSRResult',
    # Visualization
    'HVSRPlotter',
    # Config
    'DEFAULT_SETTINGS',
    # API
    'HVSRAnalysis',
    'batch_process',
]

# Core imports
from hvsr_pro.core.data_handler import HVSRDataHandler
from hvsr_pro.core.metadata import MetadataManager

# Processing imports (using new modular structure)
from hvsr_pro.processing.windows import (
    WindowManager,
    Window,
    WindowState,
    WindowCollection,
)
from hvsr_pro.processing.rejection import RejectionEngine
from hvsr_pro.processing.hvsr import HVSRProcessor, HVSRResult

# Visualization imports
from hvsr_pro.visualization.plotter import HVSRPlotter

# Config imports
from hvsr_pro.config import DEFAULT_SETTINGS

# API imports
from hvsr_pro.api import HVSRAnalysis, batch_process


def get_version():
    """Return the current version of HVSR Pro."""
    return __version__


def get_info():
    """Return package information."""
    return {
        'name': 'HVSR Pro',
        'version': __version__,
        'author': __author__,
        'description': 'Professional HVSR Analysis Package'
    }
