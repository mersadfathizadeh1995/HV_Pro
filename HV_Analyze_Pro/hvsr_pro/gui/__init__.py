"""
GUI module for HVSR Pro
========================

PyQt5-based graphical user interface with interactive window rejection.
"""

try:
    from hvsr_pro.gui.main_window import HVSRMainWindow
    from hvsr_pro.gui.interactive_canvas import InteractiveHVSRCanvas
    from hvsr_pro.gui.plot_window_manager import PlotWindowManager
    from hvsr_pro.gui.layers_dock import WindowLayersDock
    from hvsr_pro.gui.view_mode_selector import ViewModeSelector
    from hvsr_pro.gui.data_input_dialog import DataInputDialog
    HAS_GUI = True
except ImportError:
    HAS_GUI = False
    print("Warning: PyQt5 not available. GUI functionality disabled.")
    print("Install with: pip install PyQt5")

__all__ = [
    'HVSRMainWindow',
    'InteractiveHVSRCanvas',
    'PlotWindowManager',
    'WindowLayersDock',
    'ViewModeSelector',
    'DataInputDialog',
    'HAS_GUI'
]
