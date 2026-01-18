"""
HVSR Pro GUI Panels
===================

Reusable panel components for the main window.
"""

from .settings_panel import ProcessingSettingsPanel
from .qc_panel import QCSettingsPanel

# Re-export QCSettings for convenience
from hvsr_pro.processing.rejection.settings import QCSettings

__all__ = [
    'ProcessingSettingsPanel',
    'QCSettingsPanel',
    'QCSettings',
]

