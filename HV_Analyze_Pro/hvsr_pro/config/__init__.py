"""
Configuration Management Package
=================================

Default settings, presets, and validation schemas.

Components:
    - settings: Default settings and presets
    - schemas: Validation schemas for configuration
    - session: Session save/load management
"""

from hvsr_pro.config.settings import (
    DEFAULT_SETTINGS,
    ProcessingSettings,
    WindowSettings,
    QCSettings,
    ExportSettings,
    get_default_settings,
    load_settings,
    save_settings,
)
from hvsr_pro.config.schemas import (
    validate_settings,
    validate_processing_params,
    validate_qc_params,
)
from hvsr_pro.config.session import (
    SessionManager,
    SessionState,
    save_session,
    load_session,
)
from hvsr_pro.config.plot_properties import (
    PlotProperties,
    DEFAULT_PLOT_PROPERTIES,
    PUBLICATION_PRESET,
    ANALYSIS_PRESET,
    MINIMAL_PRESET,
)

__all__ = [
    # Settings
    'DEFAULT_SETTINGS',
    'ProcessingSettings',
    'WindowSettings',
    'QCSettings',
    'ExportSettings',
    'get_default_settings',
    'load_settings',
    'save_settings',
    # Schemas
    'validate_settings',
    'validate_processing_params',
    'validate_qc_params',
    # Session
    'SessionManager',
    'SessionState',
    'save_session',
    'load_session',
    # Plot Properties
    'PlotProperties',
    'DEFAULT_PLOT_PROPERTIES',
    'PUBLICATION_PRESET',
    'ANALYSIS_PRESET',
    'MINIMAL_PRESET',
]

