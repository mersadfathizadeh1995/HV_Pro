"""
Main Window Modules Package
===========================

Modular components for the main application window.

This package provides:
- Menu bar helpers
- Control panel components  
- Panel widgets (settings panels)
- Controller modules for specific functionality

The main HVSRMainWindow class remains in hvsr_pro.gui.main_window.
"""

# Import component modules
from . import menu_bar
from . import control_panel
from . import controllers
from . import panels
from . import view_state
from . import ui_coordinator

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
    UnifiedQCPanel,
)
from .view_state import ViewStateManager
from .ui_coordinator import UIUpdateCoordinator

__all__ = [
    # Modules
    'menu_bar',
    'control_panel',
    'controllers',
    'panels',
    'view_state',
    'ui_coordinator',
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
    'UnifiedQCPanel',
    # View state
    'ViewStateManager',
    # UI update coordination
    'UIUpdateCoordinator',
    # Controllers
    'DataController',
    'SessionController',
    'WindowController',
    'ProcessingController',
    'PlottingController',
]
