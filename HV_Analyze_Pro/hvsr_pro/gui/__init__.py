"""
GUI module for HVSR Pro
========================

PyQt5-based graphical user interface with interactive window rejection.

Organized Structure:
-------------------
- main_window.py: Main application window (HVSRMainWindow)
- main_window_modules/: Modular helpers (menu_bar, control_panel, controllers)
- tabs/: Tab widgets (DataLoadTab, AzimuthalTab)
- canvas/: Matplotlib canvas widgets
- docks/: Dockable panels organized by function
- dialogs/: Dialog windows organized by function
- panels/: Embedded settings panels
- mixins/: Behavior mixins
- components/: Reusable UI components
- widgets/: Other widget components
- workers/: Background thread workers
- utils/: GUI utilities
"""

HAS_GUI = False

try:
    # === Main Window ===
    from hvsr_pro.gui.main_window import HVSRMainWindow
    
    # === Canvas ===
    from hvsr_pro.gui.canvas import (
        InteractiveHVSRCanvas,
        PreviewCanvas,
        PlotWindowManager,
    )
    
    # === Tabs ===
    from hvsr_pro.gui.tabs import (
        DataLoadTab,
        AzimuthalTab,
    )
    
    # === Docks ===
    from hvsr_pro.gui.docks import (
        ExportDock,
        WindowLayersDock,
        PeakPickerDock,
        AzimuthalPropertiesDock,
        PropertiesDock,
    )
    
    # === Dialogs ===
    from hvsr_pro.gui.dialogs import (
        DataInputDialog,
        ExportDialog,
        DataExportDialog,
        ChannelMapperDialog,
        SeismicColumnMapperDialog,
        AdvancedQCDialog,
    )
    
    # === Widgets ===
    from hvsr_pro.gui.widgets import (
        LoadedDataList,
        LoadedDataTree,
        ViewModeSelector,
    )
    
    # === Workers ===
    from hvsr_pro.gui.workers import (
        ProcessingThread,
        DataExportWorker,
        PlotExportWorker,
        AzimuthalProcessingThread,
    )
    
    # === Panels ===
    from hvsr_pro.gui.panels import ProcessingSettingsPanel, QCSettingsPanel
    
    # === Mixins === (deprecated - functionality moved to controllers)
    # ProcessingMixin, PlottingMixin, SessionMixin have been removed
    # See hvsr_pro.gui.main_window_modules.controllers instead
    
    # === Components ===
    from hvsr_pro.gui.components import (
        CollapsibleGroupBox, 
        CollapsibleSection, 
        ColorPickerButton,
        CollapsibleDataPanel,
    )
    
    # === Main Window Modules ===
    from hvsr_pro.gui import main_window_modules
    
    # Submodule access
    from hvsr_pro.gui import canvas
    from hvsr_pro.gui import tabs
    from hvsr_pro.gui import docks
    from hvsr_pro.gui import dialogs
    from hvsr_pro.gui import widgets
    from hvsr_pro.gui import components
    from hvsr_pro.gui import panels
    from hvsr_pro.gui import mixins
    from hvsr_pro.gui import workers
    from hvsr_pro.gui import utils
    
    HAS_GUI = True
    
except ImportError as e:
    import sys
    print(f"Warning: GUI module import error: {e}", file=sys.stderr)
    print("PyQt5 may not be available. GUI functionality disabled.", file=sys.stderr)
    print("Install with: pip install PyQt5", file=sys.stderr)

__all__ = [
    # Main window
    'HVSRMainWindow',
    
    # Canvas
    'InteractiveHVSRCanvas',
    'PreviewCanvas',
    'PlotWindowManager',
    
    # Tabs
    'DataLoadTab',
    'AzimuthalTab',
    
    # Docks
    'ExportDock',
    'WindowLayersDock',
    'PeakPickerDock',
    'AzimuthalPropertiesDock',
    'PropertiesDock',
    
    # Dialogs
    'DataInputDialog',
    'ExportDialog',
    'DataExportDialog',
    'ChannelMapperDialog',
    'SeismicColumnMapperDialog',
    'AdvancedQCDialog',
    
    # Widgets
    'LoadedDataList',
    'LoadedDataTree',
    'ViewModeSelector',
    
    # Workers
    'ProcessingThread',
    'DataExportWorker',
    'PlotExportWorker',
    'AzimuthalProcessingThread',
    
    # Panels
    'ProcessingSettingsPanel',
    'QCSettingsPanel',
    
    # Components
    'CollapsibleGroupBox',
    'CollapsibleSection',
    'ColorPickerButton',
    'CollapsibleDataPanel',
    
    # Submodules
    'canvas',
    'tabs',
    'docks',
    'dialogs',
    'widgets',
    'components',
    'panels',
    'mixins',
    'workers',
    'utils',
    'main_window_modules',
    
    # Flag
    'HAS_GUI',
]
