"""
Main Window Panels Package
==========================

Contains modular panel components for the main window.
"""

from hvsr_pro.gui.main_window_modules.panels.processing_settings_panel import (
    ProcessingSettingsPanel,
    ProcessingSettings,
)
from hvsr_pro.gui.main_window_modules.panels.qc_settings_panel import (
    QCSettingsPanel,
    QCSettings,
)
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
