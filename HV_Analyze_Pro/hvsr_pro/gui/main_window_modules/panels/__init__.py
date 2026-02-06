"""
Main Window Panels Package
==========================

Contains modular panel components for the main window.
"""

from hvsr_pro.gui.main_window_modules.panels.processing_settings_panel import (
    ProcessingSettingsPanel,
    ProcessingSettings,
)
from hvsr_pro.gui.panels.unified_qc_panel import UnifiedQCPanel, SESAME_DEFAULTS
from hvsr_pro.processing.rejection.settings import QCSettings

__all__ = [
    'ProcessingSettingsPanel',
    'ProcessingSettings',
    'UnifiedQCPanel',
    'SESAME_DEFAULTS',
    'QCSettings',
]
