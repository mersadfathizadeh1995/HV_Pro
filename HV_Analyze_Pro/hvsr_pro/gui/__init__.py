"""
GUI module for HVSR Pro
========================

PyQt5-based graphical user interface with interactive window rejection.

Organized Structure:
-------------------
- main_window: Main application window
- panels/: Embedded settings panels (ProcessingSettingsPanel, QCSettingsPanel)
- mixins/: Behavior mixins (ProcessingMixin, PlottingMixin, SessionMixin)
- dialogs/: Dialog windows (DataInputDialog, ExportDialog, etc.)
- components/: Reusable UI components (CollapsibleBox, ColorPicker, CollapsibleDataPanel)
- workers/: Background thread workers
"""

HAS_GUI = False

try:
    # === Main Window ===
    from hvsr_pro.gui.main_window import HVSRMainWindow
    
    # === Flat imports (direct file access) ===
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
    from hvsr_pro.gui.properties_dock import PropertiesDock
    from hvsr_pro.gui.peak_picker_dock import PeakPickerDock
    from hvsr_pro.gui.export_dock import ExportDock
    from hvsr_pro.gui.azimuthal_tab import AzimuthalTab
    
    # === Workers ===
    from hvsr_pro.gui.workers import (
        ProcessingThread,
        DataExportWorker,
        PlotExportWorker,
        AzimuthalProcessingThread,
    )
    
    # === Panels ===
    from hvsr_pro.gui.panels import ProcessingSettingsPanel, QCSettingsPanel
    
    # === Mixins ===
    from hvsr_pro.gui.mixins import ProcessingMixin, PlottingMixin, SessionMixin
    
    # === Components ===
    from hvsr_pro.gui.components import (
        CollapsibleGroupBox, 
        CollapsibleSection, 
        ColorPickerButton,
        CollapsibleDataPanel,
    )
    
    # Submodule access
    from hvsr_pro.gui import components
    from hvsr_pro.gui import panels
    from hvsr_pro.gui import mixins
    from hvsr_pro.gui import workers
    from hvsr_pro.gui import dialogs
    
    HAS_GUI = True
    
except ImportError as e:
    import sys
    print(f"Warning: GUI module import error: {e}", file=sys.stderr)
    print("PyQt5 may not be available. GUI functionality disabled.", file=sys.stderr)
    print("Install with: pip install PyQt5", file=sys.stderr)

__all__ = [
    # Main window
    'HVSRMainWindow',
    
    # Direct file imports
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
    'PropertiesDock',
    'PeakPickerDock',
    'ExportDock',
    'AzimuthalTab',
    
    # Workers
    'ProcessingThread',
    'DataExportWorker',
    'PlotExportWorker',
    'AzimuthalProcessingThread',
    
    # Panels
    'ProcessingSettingsPanel',
    'QCSettingsPanel',
    
    # Mixins
    'ProcessingMixin',
    'PlottingMixin',
    'SessionMixin',
    
    # Components
    'CollapsibleGroupBox',
    'CollapsibleSection',
    'ColorPickerButton',
    'CollapsibleDataPanel',
    
    # Submodules
    'components',
    'panels',
    'mixins',
    'workers',
    'dialogs',
    
    # Flag
    'HAS_GUI',
]
