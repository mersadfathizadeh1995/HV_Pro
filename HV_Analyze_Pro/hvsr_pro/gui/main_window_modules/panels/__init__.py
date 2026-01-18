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
from hvsr_pro.gui.panels.qc_panel import QCSettingsPanel
from hvsr_pro.processing.rejection.settings import QCSettings

from hvsr_pro.gui.main_window_modules.panels.cox_settings_panel import (
    CoxSettingsPanel,
    CoxFDWRASettings,
)

__all__ = [
    'ProcessingSettingsPanel',
    'ProcessingSettings',
    'QCSettingsPanel',
    'QCSettings',
    'CoxSettingsPanel',
    'CoxFDWRASettings',
]
