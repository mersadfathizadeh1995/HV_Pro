"""
Main Window Modules Package
===========================

Modular components for the main application window.

This package provides:
- Menu bar helpers
- Control panel components  
- Controller modules for specific functionality

The main HVSRMainWindow class remains in hvsr_pro.gui.main_window
for backward compatibility.
"""

# Import component modules
from . import menu_bar
from . import control_panel
from . import controllers

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
)

__all__ = [
    # Modules
    'menu_bar',
    'control_panel',
    'controllers',
    # Menu bar
    'MenuBarHelper',
    'show_about_dialog',
    'show_shortcuts_dialog',
    # Control panel
    'SettingsGroup',
    'ProcessingSettingsGroup',
    'QCSettingsGroup',
    'ParallelSettingsGroup',
    # Controllers
    'DataController',
    'SessionController',
    'WindowController',
]
