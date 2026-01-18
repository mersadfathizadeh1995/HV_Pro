"""
HVSR Pro GUI Panels
===================

Reusable panel components for the main window.
"""

from .settings_panel import ProcessingSettingsPanel
from .qc_panel import QCSettingsPanel  # Deprecated - use UnifiedQCPanel
from .unified_qc_panel import UnifiedQCPanel, SESAME_DEFAULTS, load_custom_settings, save_custom_settings

# Re-export QCSettings for convenience
from hvsr_pro.processing.rejection.settings import QCSettings

__all__ = [
    'ProcessingSettingsPanel',
    'QCSettingsPanel',  # Deprecated
    'UnifiedQCPanel',
    'QCSettings',
    'SESAME_DEFAULTS',
    'load_custom_settings',
    'save_custom_settings',
]

