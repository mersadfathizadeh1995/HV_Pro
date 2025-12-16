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
    from hvsr_pro.gui.preview_canvas import PreviewCanvas
    from hvsr_pro.gui.loaded_data_list import LoadedDataList
    from hvsr_pro.gui.loaded_data_tree import LoadedDataTree
    from hvsr_pro.gui.data_load_tab import DataLoadTab
    from hvsr_pro.gui.channel_mapper_dialog import ChannelMapperDialog
    from hvsr_pro.gui.column_mapper_dialog import SeismicColumnMapperDialog
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
    'PreviewCanvas',
    'LoadedDataList',
    'LoadedDataTree',
    'DataLoadTab',
    'ChannelMapperDialog',
    'SeismicColumnMapperDialog',
    'HAS_GUI'
]
