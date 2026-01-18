"""
Main Window Panels Package
==========================

Contains modular panel components for the main window.
"""

from hvsr_pro.gui.main_window_modules.panels.processing_settings_panel import (
    ProcessingSettingsPanel,
    ProcessingSettings,
)
# QCSettingsPanel now uses unified QCSettings from processing/rejection/settings.py
from hvsr_pro.gui.panels.qc_panel import QCSettingsPanel  # Deprecated
from hvsr_pro.gui.panels.unified_qc_panel import UnifiedQCPanel, SESAME_DEFAULTS
from hvsr_pro.processing.rejection.settings import QCSettings

# CoxSettingsPanel is deprecated - use UnifiedQCPanel instead
from hvsr_pro.gui.main_window_modules.panels.cox_settings_panel import (
    CoxSettingsPanel,
    CoxFDWRASettings,
)

__all__ = [
    'ProcessingSettingsPanel',
    'ProcessingSettings',
    'QCSettingsPanel',  # Deprecated - use UnifiedQCPanel
    'UnifiedQCPanel',
    'SESAME_DEFAULTS',
    'QCSettings',
    'CoxSettingsPanel',  # Deprecated - use UnifiedQCPanel
    'CoxFDWRASettings',
]
