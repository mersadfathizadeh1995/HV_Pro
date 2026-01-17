"""
Main Window Modules Package
===========================

Modular components for the main application window.

This package provides:
- Menu bar helpers
- Control panel components  
- Panel widgets (settings panels)
- Controller modules for specific functionality

The main HVSRMainWindow class remains in hvsr_pro.gui.main_window
for backward compatibility.
"""

# Import component modules
from . import menu_bar
from . import control_panel
from . import controllers
from . import panels
from . import view_state

# Re-export helpers for convenience
from .menu_bar import MenuBarHelper, show_about_dialog, show_shortcuts_dialog
from .control_panel import (
    SettingsGroup,
    ProcessingSettingsGroup,
    QCSettingsGroup,
    ParallelSettingsGroup,
)
from .controllers import (
    DataController,
    SessionController,
    WindowController,
    ProcessingController,
    PlottingController,
)
from .panels import (
    ProcessingSettingsPanel,
    QCSettingsPanel,
    CoxSettingsPanel,
)
from .view_state import ViewStateManager

__all__ = [
    # Modules
    'menu_bar',
    'control_panel',
    'controllers',
    'panels',
    'view_state',
    # Menu bar
    'MenuBarHelper',
    'show_about_dialog',
    'show_shortcuts_dialog',
    # Control panel
    'SettingsGroup',
    'ProcessingSettingsGroup',
    'QCSettingsGroup',
    'ParallelSettingsGroup',
    # Panels (new modular panels)
    'ProcessingSettingsPanel',
    'QCSettingsPanel',
    'CoxSettingsPanel',
    # View state
    'ViewStateManager',
    # Controllers
    'DataController',
    'SessionController',
    'WindowController',
    'ProcessingController',
    'PlottingController',
]
