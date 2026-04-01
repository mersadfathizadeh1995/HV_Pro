"""
HVSR Pro - Main GUI Window
===========================

Main application window with interactive HVSR analysis workflow.
"""

import sys
from pathlib import Path
from typing import Optional, List
import numpy as np

try:
    from PyQt5.QtWidgets import (
        QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QSpinBox, QDoubleSpinBox,
        QComboBox, QCheckBox, QGroupBox, QTextEdit,
        QProgressBar, QFileDialog, QMessageBox,
        QSplitter, QTabWidget, QScrollArea, QDockWidget,
        QApplication, QInputDialog, QStatusBar, QAction, QMenu
    )
    from PyQt5.QtCore import Qt, QThread, pyqtSignal
    from PyQt5.QtGui import QFont
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False
    print("Warning: PyQt5 not available. GUI will not work.")

from hvsr_pro.core import HVSRDataHandler
from hvsr_pro.processing import (
    WindowManager, RejectionEngine, HVSRProcessor
)
from hvsr_pro.processing.hvsr import HVSRResult
from hvsr_pro.visualization import HVSRPlotter

if HAS_PYQT5:
    from hvsr_pro.gui.canvas import InteractiveHVSRCanvas, PlotWindowManager
    from hvsr_pro.gui.docks import (
        WindowLayersDock, PeakPickerDock, ExportDock, AzimuthalPropertiesDock
    )
    from hvsr_pro.gui.dialogs import DataInputDialog
    from hvsr_pro.gui.tabs import DataLoadTab, AzimuthalTab, ProcessingTab
    from hvsr_pro.gui.workers import ProcessingThread
    
    # Import modular controllers and panels
    from hvsr_pro.gui.main_window_modules.controllers import (
        ProcessingController, PlottingController, 
        SessionController, WindowController, DataController,
        PeakController, ExportController
    )
    from hvsr_pro.gui.main_window_modules.panels import (
        ProcessingSettings, UnifiedQCPanel
    )
    from hvsr_pro.gui.main_window_modules.ui_coordinator import UIUpdateCoordinator



class HVSRMainWindow(QMainWindow):
    """
    Main application window for HVSR analysis.
    
    Features:
    - Interactive window rejection (click to toggle)
    - Color-coded windows (green=active, gray=rejected)
    - Real-time HVSR updates
    - Complete processing pipeline
    - Export capabilities
    """
    
    def __init__(self):
        super().__init__()
        
        # Data storage
        self.data = None
        self.windows = None
        self.hvsr_result = None
        self.current_file = None
        self.load_mode = 'single'  # Track how files should be loaded
        self.current_time_range = None  # Store time range from dialog

        # Custom QC settings storage
        self.custom_qc_settings = None  # Will be set if user opens Advanced QC dialog
        
        # Work directory for file dialogs and temp files
        self._work_directory = ''
        self._pending_window_states = []  # For session loading

        # Plot window manager (separate window by default)
        self.plot_manager = PlotWindowManager(self)
        
        # Initialize modular controllers
        self.processing_ctrl = ProcessingController(self)
        self.plotting_ctrl = PlottingController(self.plot_manager, self)
        self.session_ctrl = SessionController(self)
        self.window_ctrl = WindowController(self)
        self.data_ctrl = DataController(self)
        self.peak_ctrl = PeakController(self)
        self.export_ctrl = ExportController(self)
        
        # Import ViewStateManager locally to avoid circular imports
        from hvsr_pro.gui.main_window_modules.view_state import ViewStateManager
        self.view_state = ViewStateManager(self)
        
        # UI Update Coordinator for shared processing/restore logic
        self.ui_coordinator = UIUpdateCoordinator(self)
        self.ui_coordinator.info_message.connect(self.add_info)
        
        # Connect controller signals
        self._connect_controller_signals()
        
        # Window lines storage for layer dock
        self.window_lines = {}  # {window_index: matplotlib_line}
        self.stat_lines = {}  # {'mean': line, 'std_plus': line, ...}
        
        # Setup UI
        self.setWindowTitle("HVSR Pro - Control Panel")
        self.setGeometry(100, 100, 900, 700)  # Smaller control window
        
        # Make window resizable with minimum size
        self.setMinimumSize(800, 600)
        
        # Set window icon (if available)
        try:
            from PyQt5.QtGui import QIcon
            import os
            icon_path = os.path.join(os.path.dirname(__file__), 'icons', 'hvsr_icon.png')
            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
        except:
            pass
        
        self.init_ui()
        self.connect_signals()
    
        # Install event filter on menu bar to fix Windows click issues
        self.menuBar().installEventFilter(self)
    
    def _connect_controller_signals(self):
        """Connect modular controller signals to main window handlers."""
        # Processing controller signals
        self.processing_ctrl.progress_updated.connect(self.on_progress)
        self.processing_ctrl.processing_error.connect(self.on_processing_error)
        
        # Plotting controller signals  
        self.plotting_ctrl.plot_updated.connect(self._on_plot_updated)
        self.plotting_ctrl.mean_recalculated.connect(self._on_mean_recalculated)
        
        # Window controller signals
        self.window_ctrl.statistics_updated.connect(self._on_window_stats_updated)
        
        # Data controller signals
        self.data_ctrl.info_message.connect(self.add_info)
        self.data_ctrl.loading_error.connect(self._on_data_load_error)
        
        # Peak controller signals
        self.peak_ctrl.info_message.connect(self.add_info)
        self.peak_ctrl.error_occurred.connect(self._on_peak_detection_error)
        
        # Export controller signals
        self.export_ctrl.info_message.connect(self.add_info)
        self.export_ctrl.error_occurred.connect(self._on_export_error)
    
    def _on_plot_updated(self):
        """Handle plot update from plotting controller."""
        self.status_bar.showMessage("Plot updated")
    
    def _on_mean_recalculated(self, n_visible: int):
        """Handle mean recalculation from plotting controller."""
        if n_visible > 0:
            self.add_info(f"Mean recalculated from {n_visible} visible windows")
        else:
            self.add_info("WARNING: No visible windows - mean hidden")
    
    def _on_window_stats_updated(self, stats: dict):
        """Handle window statistics update from window controller."""
        self.update_window_info()
    
    def eventFilter(self, obj, event):
        """Event filter to ensure menu bar receives clicks on Windows."""
        from PyQt5.QtCore import QEvent
        
        # If mouse enters menu bar area, activate the window
        if obj == self.menuBar():
            if event.type() == QEvent.Enter:
                self.activateWindow()
            elif event.type() == QEvent.MouseButtonPress:
                # Ensure window is active on click
                self.activateWindow()
                self.raise_()
        
        return super().eventFilter(obj, event)
    
    def create_menu_bar(self):
        """Create menu bar using MenuBarHelper."""
        from hvsr_pro.gui.main_window_modules.menu_bar import MenuBarHelper
        
        self.menu_helper = MenuBarHelper(self)
        self.menu_helper.build_complete_menu_bar()
    
    def copy_info(self):
        """Copy info text to clipboard."""
        info_text = None
        if hasattr(self, 'processing_tab') and hasattr(self.processing_tab, 'info_text'):
            info_text = self.processing_tab.info_text
        elif hasattr(self, 'info_text'):
            info_text = self.info_text
        
        if info_text and info_text.toPlainText():
            clipboard = QApplication.clipboard()
            clipboard.setText(info_text.toPlainText())
            self.statusBar().showMessage("Info copied to clipboard", 2000)
    
    def show_about(self):
        """Show about dialog. Delegates to menu_bar module."""
        from hvsr_pro.gui.main_window_modules.menu_bar import show_about_dialog
        show_about_dialog(self)
    
    def show_shortcuts(self):
        """Show keyboard shortcuts dialog. Delegates to menu_bar module."""
        from hvsr_pro.gui.main_window_modules.menu_bar import show_shortcuts_dialog
        show_shortcuts_dialog(self)
    
    def _get_cpu_count(self) -> int:
        """Get number of CPU cores."""
        try:
            from multiprocessing import cpu_count
            return cpu_count()
        except:
            return 4  # Default fallback

    # === REMOVED: Toggle handlers ===
    # _on_parallel_toggled, _on_qc_enable_toggled, _on_qc_mode_changed, _update_preset_description
    # These are now handled internally by ProcessingTab and its panels
    # See gui/tabs/processing_tab.py and gui/main_window_modules/panels/
    
    def _get_custom_qc_settings_from_ui(self):
        """Get custom QC settings from the UI (via ProcessingTab's UnifiedQCPanel)."""
        if hasattr(self, 'processing_tab') and hasattr(self.processing_tab, 'unified_qc_panel'):
            return self.processing_tab.unified_qc_panel.get_settings()
        # Fallback
        return {
            'enabled': True,
            'mode': 'sesame',
            'algorithms': {}
        }

    # === REMOVED: _on_cox_enable_toggled ===
    # Now handled internally by CoxSettingsPanel

    def init_ui(self):
        """
        Initialize user interface.
        
        Delegates to focused sub-methods for better maintainability.
        """
        # Central widget with main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Create components in order
        self._create_tabs()
        main_layout.addWidget(self.mode_tabs)
        
        self._create_docks()
        self._connect_dock_signals()
        self._setup_canvas_and_status()
        
    def _create_tabs(self):
        """Create mode tabs (Data Load, Processing, Azimuthal)."""
        self.mode_tabs = QTabWidget()

        # === Tab 1: Data Load ===
        self.data_load_tab = DataLoadTab(self)
        self.data_load_tab.load_file_requested.connect(self.load_data_file)
        self.data_load_tab.file_selected.connect(self.on_data_file_selected_for_preview)
        self.data_load_tab.data_cleared.connect(self._on_data_cleared)
        # Sync preview canvas time range edits to processing time range
        if hasattr(self.data_load_tab, 'preview_canvas'):
            self.data_load_tab.preview_canvas.time_range_applied.connect(
                self._on_preview_time_range_applied
            )
        self.mode_tabs.addTab(self.data_load_tab, "Data Load")

        # === Tab 2: Processing ===
        self.processing_tab = ProcessingTab(self)
        self.processing_tab.process_requested.connect(self._on_process_requested)
        self.processing_tab.recompute_requested.connect(self.recompute_hvsr)
        self.processing_tab.reject_all_btn.clicked.connect(self.reject_all_windows)
        self.processing_tab.accept_all_btn.clicked.connect(self.accept_all_windows)
        self.mode_tabs.addTab(self.processing_tab, "Processing")
        
        # Alias for backward compatibility
        self.processing_data_panel = self.processing_tab.data_panel

        # === Tab 3: Azimuthal Processing ===
        self.azimuthal_tab = AzimuthalTab(self)
        self.mode_tabs.addTab(self.azimuthal_tab, "Azimuthal")
        # Start hidden - can be shown via View menu
        self.azimuthal_tab_visible = False

        # Connect tab change signal
        self.mode_tabs.currentChanged.connect(self.on_tab_changed)
        
    def _create_docks(self):
        """Create and configure all dock widgets."""
        # Create layers dock
        self.layers_dock = WindowLayersDock(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.layers_dock)
        
        # Create peak picker dock
        self.peak_picker_dock = PeakPickerDock(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.peak_picker_dock)
        
        # Create properties dock
        from hvsr_pro.gui.docks import PropertiesDock
        self.properties_dock = PropertiesDock(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.properties_dock)

        # Create export dock
        self.export_dock = ExportDock(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.export_dock)
        
        # Create azimuthal properties dock (for azimuthal tab)
        self.azimuthal_properties_dock = AzimuthalPropertiesDock(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.azimuthal_properties_dock)

        # Stack docks (layers, peak picker, properties, export as tabs)
        self.tabifyDockWidget(self.layers_dock, self.peak_picker_dock)
        self.tabifyDockWidget(self.peak_picker_dock, self.properties_dock)
        self.tabifyDockWidget(self.properties_dock, self.export_dock)
        self.layers_dock.raise_()  # Layers dock visible by default

        # Initially hide docks since we start on Data Load tab
        self.layers_dock.setVisible(False)
        self.peak_picker_dock.setVisible(False)
        self.properties_dock.setVisible(False)
        self.export_dock.setVisible(False)
        self.azimuthal_properties_dock.setVisible(False)
        
        # Connect layer dock references
        self.layers_dock.set_references(self.plot_manager, None)  # Windows set later
        
    def _connect_dock_signals(self):
        """Connect signals from all dock widgets."""
        # Azimuthal properties dock signals
        self.azimuthal_properties_dock.plot_options_changed.connect(self._on_azimuthal_options_changed)
        
        # Layer dock signals
        self.layers_dock.visibility_changed.connect(self.on_layer_visibility_changed)
        
        # Peak picker dock signals
        self.peak_picker_dock.peaks_changed.connect(self.on_peaks_changed)
        self.peak_picker_dock.detect_peaks_requested.connect(self.on_detect_peaks_requested)
        self.peak_picker_dock.manual_mode_requested.connect(self.on_manual_mode_requested)
        
        # Properties dock signals
        self.properties_dock.properties_changed.connect(self.on_properties_changed)
        self.properties_dock.visualization_mode_changed.connect(self.on_view_mode_changed)

    def _setup_canvas_and_status(self):
        """Setup canvas, status bar, and menu bar."""
        # Interactive canvas (old - keep for compatibility)
        self.canvas = InteractiveHVSRCanvas(self)
        # Don't add to layout - will use plot_manager instead
        
        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Add menu bar LAST to ensure it receives mouse events properly on Windows
        self.create_menu_bar()
        
        # Force window to raise and activate to ensure menu bar is interactive
        self.raise_()
        self.activateWindow()

    def on_tab_changed(self, index):
        """
        Handle tab change - manage dock visibility.
        
        Delegates to ViewStateManager.handle_tab_changed().

        Args:
            index: Tab index (0 = Data Load, 1 = Processing, 2 = Azimuthal)
        """
        self.view_state.handle_tab_changed(index)

    def on_data_file_selected_for_preview(self, file_path: str):
        """
        Handle file selection from Data Load tab for preview.

        Args:
            file_path: Path to selected file
        """
        # Get data from cache
        data = self.data_load_tab.get_loaded_data(file_path)

        if data:
            # Already cached, just show info
            self.add_info(f"Previewing: {Path(file_path).name}")
        else:
            # Need to load - this shouldn't happen normally
            self.add_info(f"Loading for preview: {Path(file_path).name}")
    
    def _on_data_cleared(self):
        """
        Handle data cleared from Data Load tab.
        
        Syncs the clearing across all tabs and resets processing state.
        """
        # Clear main window data state
        self.data = None
        self.current_file = None
        self.windows = None
        self.hvsr_result = None
        self.load_mode = 'single'
        self.current_time_range = None
        
        # Disable process button
        self.processing_tab.process_btn.setEnabled(False)
        
        # Clear processing tab's collapsible data panel
        if hasattr(self, 'processing_data_panel') and self.processing_data_panel:
            self.processing_data_panel.clear_files()
        
        # Clear azimuthal tab's data panel
        if hasattr(self, 'azimuthal_tab') and hasattr(self.azimuthal_tab, 'data_panel'):
            self.azimuthal_tab.data_panel.clear_files()
        
        # Clear plot window if showing
        if hasattr(self, 'plot_manager') and self.plot_manager:
            try:
                self.plot_manager.clear()
            except Exception:
                pass  # Plot manager may not have clear method
        
        # Clear layers dock
        if hasattr(self, 'layers_dock'):
            self.layers_dock.rebuild({}, {})
        
        # Clear controller state
        if hasattr(self, 'data_ctrl'):
            self.data_ctrl.clear()
        
        self.add_info("Data cleared from all tabs")
        self.status_bar.showMessage("Data cleared")
    
    # === REMOVED: create_control_panel, create_file_group ===
    # These methods are now replaced by ProcessingTab
    # See gui/tabs/processing_tab.py
    
    # === REMOVED: create_file_group ===
    # File loading is now handled by DataLoadTab
    
    # === REMOVED: create_settings_group, create_window_group, create_actions_group ===
    # These methods are now replaced by ProcessingTab and its modular panels
    # See gui/tabs/processing_tab.py
    
    def connect_signals(self):
        """Connect signals and slots."""
        # Canvas signals (old compatibility)
        self.canvas.window_toggled.connect(self.on_window_toggled)
        self.canvas.status_message.connect(self.status_bar.showMessage)
    
    def toggle_plot_window(self):
        """Toggle between separate and embedded plot modes. Delegates to ViewStateManager."""
        self.view_state.toggle_plot_window()

    def toggle_preview_canvas(self, checked):
        """Toggle preview canvas visibility. Delegates to ViewStateManager."""
        self.view_state.toggle_preview_canvas(checked)

    def toggle_loaded_data_column(self, checked):
        """Toggle loaded data column visibility. Delegates to ViewStateManager."""
        self.view_state.toggle_loaded_data_column(checked)

    def toggle_azimuthal_tab(self, checked):
        """Toggle azimuthal tab visibility. Delegates to ViewStateManager."""
        self.view_state.toggle_azimuthal_tab(checked)
    
    def on_view_mode_changed(self, mode: str):
        """
        Handle view mode change.
        
        Delegates to ViewStateManager.handle_view_mode_changed().
        
        Args:
            mode: View mode ('statistical', 'windows', 'both')
        """
        self.add_info(f"View mode changed to: {mode}")
        
        if self.view_state.handle_view_mode_changed(mode):
            self.add_info(f"Switched to {mode} view")

    # === REMOVED: _on_override_sampling_toggled ===
    # Now handled internally by ProcessingSettingsPanel

    def open_batch_processing(self, project_context=None):
        """Open the Batch Processing window.
        
        Parameters
        ----------
        project_context : dict, optional
            {'project': Project, 'batch_id': str} from Project Manager.
        """
        try:
            from hvsr_pro.packages.batch_processing import BatchProcessingWindow
            
            # If project context changed, recreate window
            if project_context and (
                not hasattr(self, '_batch_window') or self._batch_window is None
                or getattr(self._batch_window, '_project_context', None) != project_context
            ):
                if hasattr(self, '_batch_window') and self._batch_window is not None:
                    self._batch_window.close()
                self._batch_window = BatchProcessingWindow(
                    self, project_context=project_context)

            if not hasattr(self, '_batch_window') or self._batch_window is None:
                self._batch_window = BatchProcessingWindow(self)
            
            self._batch_window.show()
            self._batch_window.raise_()
            self._batch_window.activateWindow()
        except ImportError as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Not Available",
                f"Batch Processing package not available:\n{str(e)}")
    
    def open_bedrock_mapping(self, project_context=None):
        """Open the 3D Bedrock Mapping window.
        
        Parameters
        ----------
        project_context : dict, optional
            {'project': Project, 'map_id': str} from Project Manager.
        """
        try:
            from hvsr_pro.packages.bedrock_mapping import BedrockMappingWindow
            
            # If project context changed, recreate window
            if project_context and (
                not hasattr(self, '_bedrock_window') or self._bedrock_window is None
                or getattr(self._bedrock_window, '_project_context', None) != project_context
            ):
                if hasattr(self, '_bedrock_window') and self._bedrock_window is not None:
                    self._bedrock_window.close()
                self._bedrock_window = BedrockMappingWindow(
                    self, project_context=project_context)

            if not hasattr(self, '_bedrock_window') or self._bedrock_window is None:
                self._bedrock_window = BedrockMappingWindow(self)
            
            self._bedrock_window.show()
            self._bedrock_window.raise_()
            self._bedrock_window.activateWindow()
        except ImportError as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Not Available",
                f"3D Bedrock Mapping package not available:\n{str(e)}")

    def open_hvstrip_progressive(self, project_context=None):
        """Open the HV Strip Progressive window.

        Parameters
        ----------
        project_context : dict, optional
            {'project': Project, 'profile_id': str} from Project Manager.
        """
        try:
            from hvsr_pro.packages import hvstrip_progressive_pkg
            HVStripWindow = hvstrip_progressive_pkg.HVStripWindow

            if HVStripWindow is None:
                err = hvstrip_progressive_pkg.get_import_error()
                raise ImportError(
                    f"HV_Strip_Progressive failed to import: {err}")

            # Recreate if project context changed
            if project_context and (
                not hasattr(self, '_hvstrip_window') or self._hvstrip_window is None
                or getattr(self._hvstrip_window, '_project_context', None) != project_context
            ):
                if hasattr(self, '_hvstrip_window') and self._hvstrip_window is not None:
                    self._hvstrip_window.close()
                self._hvstrip_window = HVStripWindow(self, project_context=project_context)

            if not hasattr(self, '_hvstrip_window') or self._hvstrip_window is None:
                self._hvstrip_window = HVStripWindow(self)

            self._hvstrip_window.show()
            self._hvstrip_window.raise_()
            self._hvstrip_window.activateWindow()
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Not Available",
                f"HV Strip Progressive package not available:\n{str(e)}")

    def open_invert_hvsr(self, project_context=None):
        """Open the HVSR Inversion Wizard window.

        Parameters
        ----------
        project_context : dict, optional
            {'project': Project, 'inv_id': str} from Project Manager.
        """
        try:
            from hvsr_pro.packages import invert_hvsr_pkg
            InvertMainWindow = invert_hvsr_pkg.MainWindow

            if InvertMainWindow is None:
                err = invert_hvsr_pkg.get_import_error()
                raise ImportError(
                    f"Invert_HVSR failed to import: {err}")

            # Recreate if project context changed
            if project_context and (
                not hasattr(self, '_invert_window') or self._invert_window is None
                or getattr(self._invert_window, '_project_context', None) != project_context
            ):
                if hasattr(self, '_invert_window') and self._invert_window is not None:
                    self._invert_window.close()
                self._invert_window = InvertMainWindow(
                    project_context=project_context)

            if not hasattr(self, '_invert_window') or self._invert_window is None:
                self._invert_window = InvertMainWindow()

            self._invert_window.show()
            self._invert_window.raise_()
            self._invert_window.activateWindow()
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Not Available",
                f"HVSR Inversion Wizard not available:\n{str(e)}")

    # ------------------------------------------------------------------
    # Project Manager
    # ------------------------------------------------------------------

    def new_project(self):
        """Create a new HV Pro project via the New Project dialog."""
        try:
            from hvsr_pro.packages.project_manager.gui.new_project_dialog import NewProjectDialog
            from hvsr_pro.packages.project_manager.project import Project
            from hvsr_pro.packages.project_manager.station_registry import StationRegistry
            from hvsr_pro.packages.project_manager.project_io import add_recent_project

            dlg = NewProjectDialog(self)
            if dlg.exec_() and dlg.project_name:
                proj = Project.create(
                    name=dlg.project_name,
                    path=dlg.project_location,
                    author=dlg.author,
                    description=dlg.description,
                )

                if dlg.csv_path:
                    reg = StationRegistry.from_file(dlg.csv_path)
                    proj.registry = reg
                    proj.save()

                add_recent_project(str(proj.hvpro_file))
                self._open_hub_for_project(proj)
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error",
                f"Failed to create project:\n{str(e)}")

    def open_project(self):
        """Open an existing project via file dialog."""
        try:
            from PyQt5.QtWidgets import QFileDialog
            from hvsr_pro.packages.project_manager.project import Project
            from hvsr_pro.packages.project_manager.project_io import add_recent_project

            path, _ = QFileDialog.getOpenFileName(
                self, "Open HV Pro Project", "",
                "HV Pro Project (*.hvpro);;All Files (*)",
            )
            if path:
                proj = Project.load(path)
                add_recent_project(path)
                self._open_hub_for_project(proj)
        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Error",
                f"Failed to open project:\n{str(e)}")

    def open_project_hub(self):
        """Show the Project Hub for the current project (or prompt to create one)."""
        if hasattr(self, '_hub_window') and self._hub_window is not None:
            self._hub_window.show()
            self._hub_window.raise_()
            self._hub_window.activateWindow()
        else:
            self.new_project()

    def _open_hub_for_project(self, project):
        """Open the Project Hub window for a given Project."""
        from hvsr_pro.packages.project_manager.gui.project_hub import ProjectHubWindow

        if hasattr(self, '_hub_window') and self._hub_window is not None:
            self._hub_window.close()

        self._hub_window = ProjectHubWindow(project, parent=None)
        self._current_project = project

        # Connect hub signals to module openers with project context
        self._hub_window.open_batch_requested.connect(
            lambda bid: self.open_batch_processing(
                project_context={'project': project, 'batch_id': bid})
        )
        self._hub_window.open_bedrock_requested.connect(
            lambda mid: self.open_bedrock_mapping(
                project_context={'project': project, 'map_id': mid})
        )
        self._hub_window.open_hvstrip_requested.connect(
            lambda pid: self.open_hvstrip_progressive(
                project_context={'project': project, 'profile_id': pid})
        )
        self._hub_window.open_inversion_requested.connect(
            lambda iid: self.open_invert_hvsr(
                project_context={'project': project, 'inv_id': iid})
        )
        self._hub_window.open_hvsr_requested.connect(
            lambda aid: self._open_hvsr_with_project(project, aid)
        )

        # When hub saves, also save ALL open module windows
        self._hub_window.save_all_requested.connect(self._save_all_module_states)

        self._hub_window.show()

    # ------------------------------------------------------------------
    #  Centralised project save (triggered by hub's Save / Close)
    # ------------------------------------------------------------------

    def _save_all_module_states(self):
        """Save state for every open module window + main HVSR."""
        # HVSR main window
        ctx = getattr(self, '_hvsr_project_context', None)
        if ctx:
            try:
                self._save_hvsr_to_project(ctx)
            except Exception as e:
                print(f"[SaveAll] HVSR save failed: {e}")
        # Sub-module windows — each has _save_project_state()
        for attr in ('_batch_window', '_bedrock_window',
                     '_hvstrip_window', '_invert_window'):
            win = getattr(self, attr, None)
            if win is not None and hasattr(win, '_save_project_state'):
                try:
                    win._save_project_state()
                except Exception as e:
                    print(f"[SaveAll] {attr} save failed: {e}")

    def _open_hvsr_with_project(self, project, analysis_id):
        """Open the main HVSR window in project context.

        Sets the project context so that Save Session writes to the
        project's ``hvsr_analysis/analysis_NNN/`` directory.  If the
        analysis folder already contains saved state, it is restored
        automatically.
        """
        from hvsr_pro.packages.project_manager.project import MODULE_HVSR_ANALYSIS

        # ── Save & clear previous analysis before switching ──
        old_ctx = getattr(self, '_hvsr_project_context', None)
        if old_ctx:
            try:
                self._save_hvsr_to_project(old_ctx)
            except Exception:
                pass
        self._on_data_cleared()  # reset data, plots, file list

        self._hvsr_project_context = {
            'project': project,
            'analysis_id': analysis_id,
        }

        # Set work directory into the project analysis folder
        analysis_dir = project.ensure_module_dir(
            MODULE_HVSR_ANALYSIS, analysis_id)
        self._work_directory = str(analysis_dir)
        self.session_ctrl.set_work_directory(str(analysis_dir))

        # Update the Work Directory field in the Data Load tab
        if hasattr(self, 'data_load_tab') and hasattr(self.data_load_tab, 'work_dir_edit'):
            self.data_load_tab.work_dir_edit.setText(str(analysis_dir))

        # Update window title
        self.setWindowTitle(
            f"HVSR Pro — {project.name} — {analysis_id}")

        # Attempt to restore from existing state
        from hvsr_pro.packages.project_manager.module_state.hvsr_state_io import (
            has_hvsr_state, load_hvsr_state,
        )
        if has_hvsr_state(analysis_dir):
            try:
                loaded = load_hvsr_state(analysis_dir)
                if loaded.get("hvsr_result") is not None and loaded.get("windows") is not None:
                    self.add_info(f"Restoring analysis {analysis_id} ...")

                    # Apply settings from state_dict
                    sd = loaded.get("state_dict", {})
                    if "processing" in sd:
                        proc = sd["processing"]
                        pp = getattr(
                            getattr(self, 'processing_tab', None),
                            'processing_panel', None)
                        if pp:
                            for attr, spin_name in [
                                ("window_length", "window_length_spin"),
                                ("smoothing_bandwidth", "smoothing_spin"),
                                ("f_min", "freq_min_spin"),
                                ("f_max", "freq_max_spin"),
                                ("n_frequencies", "n_freq_spin"),
                            ]:
                                spin = getattr(pp, spin_name, None)
                                if spin and attr in proc:
                                    spin.setValue(proc[attr])
                            if "overlap" in proc:
                                ov_spin = getattr(pp, "overlap_spin", None)
                                if ov_spin:
                                    ov_spin.setValue(int(proc["overlap"] * 100))

                    # Restore QC settings
                    if "qc_settings" in sd:
                        self.custom_qc_settings = sd["qc_settings"]
                        if hasattr(self, 'processing_tab') and hasattr(self.processing_tab, 'unified_qc_panel'):
                            panel = self.processing_tab.unified_qc_panel
                            if hasattr(panel, 'apply_advanced_settings'):
                                try:
                                    panel.apply_advanced_settings(sd["qc_settings"])
                                except Exception:
                                    pass

                    # Restore load_mode
                    if "load_mode" in sd:
                        self.load_mode = sd["load_mode"]

                    # Restore current_file from saved path
                    fp = sd.get("file_path", "")
                    if fp:
                        lm = sd.get("load_mode", "single")
                        if lm == "single":
                            self.current_file = fp
                        else:
                            self.current_file = fp.split(";") if ";" in fp else fp

                    # Restore overall time range
                    if "current_time_range" in sd:
                        self.current_time_range = sd["current_time_range"]

                    # Restore data objects (plots the HVSR curve)
                    seismic_data = loaded.get("seismic_data")
                    self.restore_session_gui(
                        loaded["hvsr_result"],
                        loaded["windows"],
                        seismic_data,
                    )

                    # ── Restore loaded-file list in Data Load & Processing tabs ──
                    lf = sd.get("loaded_files")
                    if lf and hasattr(self, 'data_load_tab'):
                        tr_map = lf.get("time_ranges", {})
                        for grp in lf.get("groups", []):
                            gname = grp.get("name", "Restored")
                            for fpath, meta in grp.get("files", {}).items():
                                tr = tr_map.get(fpath)
                                self.data_load_tab.add_loaded_file(
                                    fpath,
                                    seismic_data,
                                    meta,
                                    tr,
                                    group_name=gname,
                                )
                        # Sync processing & azimuthal data panels
                        if hasattr(self, 'processing_data_panel'):
                            self.processing_data_panel.update_from_data_load_tab(
                                self.data_load_tab)
                        if (hasattr(self, 'azimuthal_tab')
                                and hasattr(self.azimuthal_tab, 'data_panel')):
                            self.azimuthal_tab.data_panel.update_from_data_load_tab(
                                self.data_load_tab)
                        self.processing_tab.process_btn.setEnabled(True)

                    # Azimuthal
                    if loaded.get("azimuthal_result") is not None:
                        if hasattr(self, 'azimuthal_tab'):
                            self.azimuthal_tab.result = loaded["azimuthal_result"]
                            try:
                                self.azimuthal_tab.update_plot()
                            except Exception:
                                pass

                    self.add_info(f"Analysis {analysis_id} restored successfully.")
                else:
                    self.add_info(f"Opening new analysis: {analysis_id}")
            except Exception as e:
                self.add_info(
                    f"Could not restore {analysis_id}: {e}")
        else:
            self.add_info(f"New analysis: {analysis_id}")

        # Bring main window to front (re-show if it was hidden)
        self.show()
        self.raise_()
        self.activateWindow()

    def open_advanced_qc_settings(self):
        """Open Advanced QC Settings dialog."""
        from hvsr_pro.gui.dialogs import AdvancedQCDialog
        
        # Get current settings from unified panel
        current_settings = None
        if hasattr(self, 'processing_tab') and hasattr(self.processing_tab, 'unified_qc_panel'):
            current_settings = self.processing_tab.unified_qc_panel.get_settings()
        
        dialog = AdvancedQCDialog(self, current_settings)
        if dialog.exec_():
            new_settings = dialog.get_settings()
            self.custom_qc_settings = new_settings
            self.add_info("Advanced QC settings updated")
            
            # Switch unified panel to custom mode with the new settings
            if hasattr(self, 'processing_tab') and hasattr(self.processing_tab, 'unified_qc_panel'):
                panel = self.processing_tab.unified_qc_panel
                if hasattr(panel, 'apply_advanced_settings'):
                    panel.apply_advanced_settings(new_settings)

    def on_layer_visibility_changed(self, window_idx: int, is_visible: bool):
        """Handle layer visibility toggle from dock."""
        action = "shown" if is_visible else "hidden"
        self.add_info(f"Window {window_idx + 1} {action}")
        
        # Real-time mean recalculation
        self.recalculate_mean_from_visible_windows()
    
    def load_data_file(self):
        """Load seismic data file using enhanced dialog."""
        dialog = DataInputDialog(self)
        dialog.files_selected.connect(self.on_files_selected)
        dialog.exec_()
    
    def on_files_selected(self, result: dict):
        """
        Handle files selected from DataInputDialog.
        
        Delegates loading to DataController and updates UI after load.
        """
        # Delegate loading to DataController
        load_result = self.data_ctrl.load_from_dialog_result(result)
        
        if load_result.success:
            self._update_ui_after_load(load_result)
        else:
            QMessageBox.critical(self, "Load Error", load_result.error_message)
            self.add_info(f"ERROR: {load_result.error_message.split(chr(10))[0]}")
    
    def _update_ui_after_load(self, load_result):
        """
        Update UI components after successful data load.
        
        Args:
            load_result: LoadResult from DataController
        """
        # Store load mode and time range
        self.load_mode = load_result.mode
        self.current_time_range = load_result.time_range
        
        # Get time range in seconds format
        tr_seconds = load_result.time_range_seconds
        
        # Add files to data load tab
        for metadata in load_result.metadata_list:
            display_name = metadata.get('display_name', metadata.get('file_path', 'Unknown'))
            self.data_load_tab.add_loaded_file(
                display_name, 
                load_result.data, 
                metadata, 
                tr_seconds
            )
        
        # Update preview canvas time filter if time range was specified
        if load_result.time_range and load_result.time_range.get('enabled'):
            self._apply_time_range_to_preview(load_result.time_range, load_result.data)
        
        # Store the loaded data
        self.data = load_result.data

                # Store for processing
        if load_result.mode == 'single':
            self.current_file = load_result.files[0] if load_result.files else None
        elif load_result.mode == 'multi_type1':
            self.current_file = load_result.files
        elif load_result.mode == 'multi_type2':
            self.current_file = load_result.groups
        elif load_result.mode == 'multi_component':
            # For multi-component (SAC, PEER), store the list of files
            self.current_file = load_result.files
        
        self.processing_tab.process_btn.setEnabled(True)
        
        # Update collapsible data panels in Processing and Azimuthal tabs
        if hasattr(self, 'processing_data_panel'):
            self.processing_data_panel.update_from_data_load_tab(self.data_load_tab)
        if hasattr(self, 'azimuthal_tab') and hasattr(self.azimuthal_tab, 'data_panel'):
            self.azimuthal_tab.data_panel.update_from_data_load_tab(self.data_load_tab)
    
    def _on_data_load_error(self, error_msg: str):
        """Handle data loading error from controller."""
        QMessageBox.critical(self, "Load Error", error_msg)
        self.add_info(f"ERROR: {error_msg}")
    
    def _apply_time_range_to_preview(self, time_range: dict, data):
        """
        Apply time range settings from DataInputDialog to the preview canvas.
        
        Args:
            time_range: Dict with 'enabled', 'start', 'end', 'timezone_offset', 'timezone_name'
            data: SeismicData object with timing info
        """
        try:
            preview_canvas = self.data_load_tab.preview_canvas
            
            # Enable time filter checkbox
            preview_canvas.time_filter_checkbox.setChecked(True)
            
            # Set datetime pickers — do NOT use Qt.UTC timeSpec.
            # All timezone math is manual via _current_tz_offset.
            from PyQt5.QtCore import QDateTime, QDate, QTime
            
            start_dt = time_range['start']
            end_dt = time_range['end']
            tz_name = time_range.get('timezone_name', 'UTC+0 (GMT)')
            tz_offset = time_range.get('timezone_offset', 0.0)
            
            # Block ALL signals to prevent cascade effects during setup
            preview_canvas.datetime_start.blockSignals(True)
            preview_canvas.datetime_end.blockSignals(True)
            preview_canvas.timezone_combo.blockSignals(True)
            
            # Set timezone combo and update internal offset tracker
            tz_index = preview_canvas.timezone_combo.findText(tz_name, Qt.MatchContains)
            if tz_index >= 0:
                preview_canvas.timezone_combo.setCurrentIndex(tz_index)
            preview_canvas.selected_timezone = tz_name
            preview_canvas._current_tz_offset = tz_offset
            
            # Create plain QDateTime (no timeSpec) — values are in user's local timezone
            start_qdt = QDateTime(
                QDate(start_dt.year, start_dt.month, start_dt.day),
                QTime(start_dt.hour, start_dt.minute, start_dt.second)
            )
            end_qdt = QDateTime(
                QDate(end_dt.year, end_dt.month, end_dt.day),
                QTime(end_dt.hour, end_dt.minute, end_dt.second)
            )
            preview_canvas.datetime_start.setDateTime(start_qdt)
            preview_canvas.datetime_end.setDateTime(end_qdt)
            
            # Unblock all signals
            preview_canvas.datetime_start.blockSignals(False)
            preview_canvas.datetime_end.blockSignals(False)
            preview_canvas.timezone_combo.blockSignals(False)
            
            # Apply the time filter
            preview_canvas.apply_time_filter()
            
            self.add_info(f"Time range applied to preview: {start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')} ({tz_name})")
            
        except Exception as e:
            print(f"Warning: Could not apply time range to preview: {e}")
    
    def _on_preview_time_range_applied(self, time_range: dict):
        """Update current_time_range when user edits time range in preview canvas."""
        self.current_time_range = time_range
    
    def _on_process_requested(self, settings):
        """
        Handle process request from ProcessingTab.
        
        Args:
            settings: FullProcessingSettings from ProcessingTab
        """
        # Add file info to settings
        settings.current_file = self.current_file
        settings.load_mode = self.load_mode
        settings.time_range = self.current_time_range
        
        # Call process_hvsr with settings
        self._process_with_settings(settings)
    
    def _process_with_settings(self, settings):
        """Process HVSR with given settings object."""
        if not settings.current_file:
            QMessageBox.warning(self, "No File", "Please load a data file first.")
            return
        
        # Disable controls
        self.processing_tab.set_processing_enabled(False)
        self.processing_tab.set_progress(0, visible=True)
        
        # Log settings
        self.add_info(f"Frequency range: {settings.freq_min:.2f} - {settings.freq_max:.1f} Hz ({settings.n_frequencies} points)")
        if settings.manual_sampling_rate:
            self.add_info(f"Sampling rate: {settings.manual_sampling_rate:.4f} Hz (manual override)")
        if settings.qc_mode == 'preset':
            self.add_info(f"QC Mode: {settings.qc_preset}")
        else:
            self.add_info(f"QC Mode: Custom (manual settings)")
        if settings.cox_enabled:
            self.add_info(f"Cox FDWRA: Enabled (peak frequency consistency)")
        if settings.use_parallel:
            self.add_info(f"Parallel processing: Enabled (using {settings.n_cores} cores)")
        
        # Build custom QC settings dict if needed
        custom_qc_settings = None
        if settings.qc_mode == 'custom' and settings.custom_qc_settings:
            custom_qc_settings = self._build_custom_qc_dict(settings.custom_qc_settings)
        
        # Build Cox FDWRA settings dict
        cox_fdwra_settings = {
            'n': settings.cox_n,
            'max_iterations': settings.cox_max_iterations,
            'min_iterations': settings.cox_min_iterations,
            'distribution': settings.cox_distribution
        }
        
        # Start processing thread
        self.thread = ProcessingThread(
            settings.current_file,
            settings.window_length,
            settings.overlap,
            settings.smoothing_bandwidth,
            settings.load_mode,
            settings.time_range,
            settings.freq_min,
            settings.freq_max,
            settings.n_frequencies,
            settings.qc_mode,  # 'sesame' or 'custom'
            settings.cox_enabled,
            settings.use_parallel,
            settings.n_cores,
            settings.manual_sampling_rate,
            custom_qc_settings,
            cox_fdwra_settings,
            getattr(settings, 'smoothing_method', 'konno_ohmachi'),
            qc_enabled=settings.qc_enabled,
            phase1_enabled=getattr(settings, 'phase1_enabled', True),
            phase2_enabled=getattr(settings, 'phase2_enabled', True),
            horizontal_method=getattr(settings, 'horizontal_method', 'geometric_mean')
        )
        self.thread.progress.connect(self.on_progress)
        self.thread.finished.connect(self.on_processing_finished)
        self.thread.error.connect(self.on_processing_error)
        self.thread.start()
    
    def _build_custom_qc_dict(self, custom_settings):
        """Build custom QC settings dictionary from panel settings.
        
        Handles both old format (algorithms at top level) and new format
        (algorithms inside 'algorithms' sub-dict). Also maps spectral_spike
        to frequency_domain for worker compatibility.
        """
        # Extract algorithms from either nested or flat structure
        if isinstance(custom_settings, dict) and 'algorithms' in custom_settings:
            algos = custom_settings['algorithms']
        else:
            algos = custom_settings if isinstance(custom_settings, dict) else {}
        
        # Map spectral_spike -> frequency_domain for worker compatibility
        if 'spectral_spike' in algos and 'frequency_domain' not in algos:
            algos['frequency_domain'] = algos['spectral_spike']
        
        def _get_algo(key, default_params=None):
            """Extract algorithm settings with fallback."""
            algo = algos.get(key, {})
            enabled = algo.get('enabled', False)
            params = algo.get('params', default_params or {})
            return {'enabled': enabled, 'params': params}
        
        return {
            'enabled': custom_settings.get('enabled', True) if isinstance(custom_settings, dict) else True,
            'mode': 'custom',
            'algorithms': {
                'amplitude': _get_algo('amplitude', {}),
                'quality_threshold': _get_algo('quality_threshold', {'threshold': 0.5}),
                'sta_lta': _get_algo('sta_lta', {
                    'sta_length': 1.0, 'lta_length': 30.0, 'min_ratio': 0.2, 'max_ratio': 2.5
                }),
                'frequency_domain': _get_algo('frequency_domain', {'spike_threshold': 3.0}),
                'statistical_outlier': _get_algo('statistical_outlier', {'method': 'iqr', 'threshold': 2.0}),
                'hvsr_amplitude': _get_algo('hvsr_amplitude', {'min_amplitude': 1.0}),
                'flat_peak': _get_algo('flat_peak', {'flatness_threshold': 0.15}),
                'curve_outlier': _get_algo('curve_outlier', {
                    'threshold': 3.0, 'max_iterations': 5, 'metric': 'mean'
                }),
                'cox_fdwra': _get_algo('cox_fdwra', {'n': 2.0, 'max_iterations': 50}),
                'fdwra': _get_algo('fdwra', {'n': 2.0, 'max_iterations': 50}),
            }
        }
    
    def process_hvsr(self):
        """
        Start HVSR processing in background thread.
        
        .. deprecated::
            This method is deprecated. Use ProcessingTab.process_requested signal
            and the _process_with_settings() method instead.
            This method is kept for backward compatibility with external code.
        """
        import warnings
        warnings.warn(
            "process_hvsr() is deprecated. Use ProcessingTab's Process HVSR button instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        # Delegate to the processing tab's process method
        if hasattr(self, 'processing_tab'):
            self.processing_tab._on_process_clicked()
        else:
            QMessageBox.warning(self, "Error", "Processing tab not available.")
    
    def on_progress(self, value: int, message: str):
        """Update progress bar."""
        # Update processing tab's progress bar
        if hasattr(self, 'processing_tab'):
            self.processing_tab.set_progress(value)
        # Legacy progress bar (if exists)
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setValue(value)
        self.status_bar.showMessage(message)
        self.add_info(message)
    
    def on_processing_finished(self, result, windows, data):
        """
        Handle processing completion.
        
        Validates results and delegates UI updates to UIUpdateCoordinator.
        """
        # CRITICAL: Validate results via ProcessingController
        is_valid, error_msg = self.processing_ctrl.validate_results(result, windows)

        if not is_valid:
            # Show QC failure dialog via controller
            self.processing_ctrl._show_qc_failure_dialog(windows, error_msg)

            # Re-enable controls via processing tab
            if hasattr(self, 'processing_tab'):
                self.processing_tab.set_progress(0, visible=False)
                self.processing_tab.set_processing_enabled(True)
            return  # Don't proceed with plotting

        # Delegate all UI updates to the coordinator
        self.ui_coordinator.update_after_processing(result, windows, data)
    
    def plot_results_separate_window(self, result, windows, data):
        """
        Plot results in separate plot window.
        
        Delegates to PlottingController for actual implementation.
        
        Args:
            result: HVSRResult object
            windows: WindowCollection object
            data: SeismicData object
        """
        # Check if this is a QC failure result
        if hasattr(result, 'metadata') and result.metadata.get('qc_failure', False):
            return
        
        # Delegate to PlottingController
        self.plotting_ctrl.set_data(result, windows, data)
        self.plotting_ctrl.set_plot_manager(self.plot_manager)
        
        lines = self.plotting_ctrl.plot_hvsr_results(result, windows, data)
        self.window_lines = lines.get('window_lines', {})
        self.stat_lines = lines.get('stat_lines', {})
        
        # Rebuild layer dock with lines
        self.layers_dock.rebuild(self.window_lines, self.stat_lines)
        
        # Show plot window
        self.plot_manager.show_separate()
        self.add_info("Plot window opened")
    
    def refresh_plot(self):
        """Refresh plot with current panel visibility settings."""
        if not self.hvsr_result or not self.windows or not self.data:
            return
        
        # Replot with current settings via controller
        self.plotting_ctrl.refresh_plot()
        
        self.add_info(f"Plot refreshed")
    
    def _get_color_palette(self):
        """Get color palette for window curves."""
        return [
            '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
            '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
            '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
            '#c49c94', '#f7b6d2', '#c7c7c7', '#dbdb8d', '#9edae5'
        ]
    
    def recalculate_mean_from_visible_windows(self):
        """
        Recalculate mean HVSR from currently visible windows in real-time.
        
        This provides instant visual feedback when user toggles window visibility.
        Delegates to PlottingController.
        """
        # Delegate to plotting controller
        self.plotting_ctrl.recalculate_mean_from_visible()

    def on_processing_error(self, error_msg: str):
        """Handle processing error."""
        self.processing_tab.progress_bar.setVisible(False)
        self.processing_tab.process_btn.setEnabled(True)
        QMessageBox.critical(self, "Processing Error", error_msg)
        self.add_info(f"ERROR: {error_msg}")
    
    def on_window_toggled(self, window_index: int):
        """Handle window toggle event from canvas. Delegates to WindowController."""
        new_state = self.window_ctrl.toggle_window(window_index)
        action = "Activated" if new_state else "Rejected"
        self.add_info(f"{action} window {window_index}")
        
        # Update info and refresh canvas
        self.update_window_info()
        self.canvas.update_window_states()
    
    def reject_all_windows(self):
        """Reject all windows. Delegates to WindowController."""
        self.window_ctrl.reject_all()
        self.update_window_info()
        self.canvas.update_window_states()
        self.add_info("Rejected all windows")
    
    def accept_all_windows(self):
        """Accept all windows. Delegates to WindowController."""
        self.window_ctrl.accept_all()
        self.update_window_info()
        self.canvas.update_window_states()
        self.add_info("Accepted all windows")
    
    def recompute_hvsr(self):
        """Recompute HVSR with current window selection."""
        if self.windows is None:
            return
        
        self.add_info("Recomputing HVSR...")
        self.status_bar.showMessage("Recomputing HVSR...")
        
        try:
            # Read settings from processing tab panels
            proc_panel = self.processing_tab.processing_panel
            smoothing = proc_panel.smoothing_spin.value()
            smoothing_method = getattr(proc_panel, 'smoothing_method_combo', None)
            method_name = smoothing_method.currentData() if smoothing_method else 'konno_ohmachi'
            freq_min = proc_panel.freq_min_spin.value()
            freq_max = proc_panel.freq_max_spin.value()
            n_frequencies = proc_panel.n_freq_spin.value()
            
            processor = HVSRProcessor(
                smoothing_method=method_name,
                smoothing_bandwidth=smoothing,
                f_min=freq_min,
                f_max=freq_max,
                n_frequencies=n_frequencies
            )
            self.hvsr_result = processor.process(self.windows, detect_peaks_flag=True, save_window_spectra=True)
            
            # Update canvas
            self.canvas.set_data(self.hvsr_result, self.windows, self.data)
            
            self.add_info(f"HVSR recomputed!")
            if self.hvsr_result.primary_peak:
                self.add_info(f"   Primary peak: f0 = {self.hvsr_result.primary_peak.frequency:.2f} Hz")
            
            self.status_bar.showMessage("HVSR recomputed successfully")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to recompute HVSR: {str(e)}")
            self.add_info(f"ERROR - Recompute: {str(e)}")
    
    def update_window_info(self):
        """Update window information display."""
        if self.windows is None:
            self.processing_tab.window_info_label.setText("No windows")
            return
        
        info = (f"Total: {self.windows.n_windows}\n"
                f"Active: {self.windows.n_active} "
                f"({self.windows.acceptance_rate*100:.1f}%)\n"
                f"Rejected: {self.windows.n_rejected}")
        self.processing_tab.window_info_label.setText(info)
    
    def generate_report_plots(self):
        """Open advanced export dialog. Delegates to ExportController."""
        self.export_ctrl.set_references(self.hvsr_result, self.windows, self.data, self.plot_manager)
        self.export_ctrl.open_report_dialog()
    
    def export_results(self):
        """Export HVSR results. Delegates to ExportController."""
        if self.hvsr_result is None:
            QMessageBox.warning(self, "No Results", "No results to export.")
            return
        
        self.export_ctrl.set_references(self.hvsr_result, self.windows, self.data, self.plot_manager)
        result = self.export_ctrl.export_results()
        
        if result.success:
                QMessageBox.information(
                    self, "Export Complete",
                f"Results exported to:\n{result.file_path}\n\n"
                    f"Files created:\n" +
                "\n".join([f"• {Path(f).name}" for f in result.created_files.values()])
            )
        elif result.error_message:
            QMessageBox.critical(self, "Export Error", result.error_message)
    
    def save_session(self):
        """
        Save current session state including all settings and computed data.
        If a project context is active, also writes to the project folder
        and updates the project activity log.
        """
        # Sync work directory with controller
        self.session_ctrl.set_work_directory(getattr(self, '_work_directory', ''))
        
        # Delegate to session controller
        result = self.session_ctrl.save_full_session(self)
        
        if result.success:
            # Also persist into project if context is active
            ctx = getattr(self, '_hvsr_project_context', None)
            if ctx:
                try:
                    self._save_hvsr_to_project(ctx)
                except Exception as e:
                    self.add_info(f"Warning: project save failed: {e}")
            QMessageBox.information(self, "Session Saved", result.info_message)
        else:
            QMessageBox.critical(self, "Save Failed", result.error_message)

    def _save_hvsr_to_project(self, ctx):
        """Persist current HVSR state into the project folder."""
        if not ctx:
            return
        from hvsr_pro.packages.project_manager.project import MODULE_HVSR_ANALYSIS
        from hvsr_pro.packages.project_manager.module_state.hvsr_state_io import (
            save_hvsr_state,
        )

        project = ctx['project']
        analysis_id = ctx['analysis_id']
        analysis_dir = project.ensure_module_dir(
            MODULE_HVSR_ANALYSIS, analysis_id)

        # Build state dict from current GUI
        state_dict = {}
        proc_panel = getattr(
            getattr(self, 'processing_tab', None), 'processing_panel', None)
        if proc_panel:
            state_dict["processing"] = {
                "window_length": proc_panel.window_length_spin.value(),
                "overlap": proc_panel.overlap_spin.value() / 100.0,
                "smoothing_bandwidth": proc_panel.smoothing_spin.value(),
                "f_min": proc_panel.freq_min_spin.value(),
                "f_max": proc_panel.freq_max_spin.value(),
                "n_frequencies": proc_panel.n_freq_spin.value(),
            }

        # QC settings
        qc_settings = self._get_custom_qc_settings_from_ui()
        if qc_settings:
            state_dict["qc_settings"] = qc_settings

        # File info
        current_file = getattr(self, 'current_file', '')
        if isinstance(current_file, list):
            current_file = ';'.join(str(f) for f in current_file)
        state_dict["file_path"] = str(current_file) if current_file else ''
        state_dict["load_mode"] = getattr(self, 'load_mode', 'single')

        # ── Loaded files list (groups + per-file metadata + time ranges) ──
        if hasattr(self, 'data_load_tab'):
            dlt = self.data_load_tab
            groups_out = []
            time_ranges_out = {}
            for gid, ginfo in getattr(dlt, 'data_groups', {}).items():
                files_meta = {}
                for fp, meta in ginfo.get('files', {}).items():
                    # Keep only JSON-safe scalars
                    files_meta[str(fp)] = {
                        k: v for k, v in meta.items()
                        if isinstance(v, (str, int, float, bool, type(None)))
                    }
                groups_out.append({
                    "group_id": gid,
                    "name": ginfo.get('name', ''),
                    "files": files_meta,
                })
            for fp, cached in getattr(dlt, 'data_cache', {}).items():
                tr = cached.get('time_range')
                if tr is not None:
                    time_ranges_out[str(fp)] = {
                        k: v for k, v in tr.items()
                        if isinstance(v, (str, int, float, bool, type(None)))
                    }
            state_dict["loaded_files"] = {
                "groups": groups_out,
                "time_ranges": time_ranges_out,
            }

        # Overall time range used for processing
        ctr = getattr(self, 'current_time_range', None)
        if ctr:
            try:
                state_dict["current_time_range"] = {
                    k: (str(v) if not isinstance(v, (str, int, float, bool, type(None))) else v)
                    for k, v in ctr.items()
                }
            except Exception:
                pass

        # Window states (active/rejection per window)
        windows = getattr(self, 'windows', None)
        if windows and hasattr(windows, '__iter__'):
            try:
                win_states = []
                for i, w in enumerate(windows):
                    ws = {"index": i}
                    if hasattr(w, 'is_active'):
                        ws["is_active"] = bool(w.is_active)
                    if hasattr(w, 'rejection_reason'):
                        ws["rejection_reason"] = str(w.rejection_reason) if w.rejection_reason else None
                    win_states.append(ws)
                state_dict["window_states"] = win_states
            except Exception:
                pass

        # Peak summary
        hvsr_result = getattr(self, 'hvsr_result', None)
        if hvsr_result and hasattr(hvsr_result, 'primary_peak') and hvsr_result.primary_peak:
            state_dict["peak_frequency"] = hvsr_result.primary_peak.frequency
            state_dict["peak_amplitude"] = hvsr_result.primary_peak.amplitude

        # Metadata
        if windows:
            try:
                n_total = len(windows)
                n_active = sum(1 for w in windows if getattr(w, 'is_active', True))
                state_dict["n_total_windows"] = n_total
                state_dict["n_active_windows"] = n_active
            except Exception:
                pass

        seismic_data = getattr(self, 'seismic_data', None) or getattr(self, 'data', None)
        azimuthal_result = None
        if hasattr(self, 'azimuthal_tab') and hasattr(self.azimuthal_tab, 'result'):
            azimuthal_result = self.azimuthal_tab.result

        save_hvsr_state(
            analysis_dir,
            state_dict=state_dict,
            windows=windows,
            hvsr_result=hvsr_result,
            seismic_data=seismic_data,
            azimuthal_result=azimuthal_result,
        )

        project.log_activity(
            MODULE_HVSR_ANALYSIS,
            f"Analysis saved: {analysis_id}",
        )
        project.save()
        self.add_info(f"Saved to project: {analysis_id}")
    
    def load_session(self):
        """
        Load saved session state including computed data.
        Delegates to SessionController for loading and applies state to GUI.
        """
        # Sync work directory with controller
        self.session_ctrl.set_work_directory(getattr(self, '_work_directory', ''))
        
        # Delegate loading to session controller
        result = self.session_ctrl.load_full_session()
        
        if not result.success:
            if result.error_message:
                QMessageBox.critical(self, "Load Failed", result.error_message)
                return
            
        # Apply settings to GUI via controller
        self.session_ctrl.apply_session_state(self, result)
        
        # Build info message
        state = result.state
        restored_data = []
        if result.windows is not None:
            n_total = getattr(state, 'n_total_windows', 0)
            n_active = getattr(state, 'n_active_windows', 0)
            restored_data.append(f"Window collection ({n_total} windows, {n_active} active)")
        if result.hvsr_result is not None:
            peak_freq = getattr(state, 'peak_frequency', None)
            if peak_freq is not None:
                restored_data.append(f"HVSR results (f0 = {peak_freq:.3f} Hz)")
            else:
                restored_data.append("HVSR results")
        if result.seismic_data is not None:
            restored_data.append("Original seismic data")
        if result.azimuthal_result is not None:
            restored_data.append("Azimuthal processing results")
        
        session_name = Path(getattr(state, 'session_folder', '')).name if state else 'Unknown'
        self.add_info(f"Session loaded: {session_name}")
        
        # Restore full GUI state if we have complete data
        if result.hvsr_result is not None and result.windows is not None:
            self.add_info("Restoring GUI with HVSR results and windows...")
            try:
                self.restore_session_gui(result.hvsr_result, result.windows, result.seismic_data)
                self.add_info("GUI fully restored - plot, layers, and docks updated")
            except Exception as e:
                self.add_info(f"Warning: Partial restore - {str(e)}")
        
        # Restore azimuthal results if available
        if result.azimuthal_result is not None and hasattr(self, 'azimuthal_tab'):
            try:
                self.azimuthal_tab.result = result.azimuthal_result
                self.azimuthal_tab.update_plot()
                self.add_info("Azimuthal results restored")
            except Exception as e:
                self.add_info(f"Warning: Could not restore azimuthal results - {str(e)}")
        
        # Build info message
        info_msg = f"Session loaded successfully!\n\nSession: {session_name}\n\n"
        if restored_data:
            info_msg += "Restored data:\n"
            for item in restored_data:
                info_msg += f"  - {item}\n"
            info_msg += "\nAll data restored - no re-processing needed!"
        else:
            info_msg += "Settings restored. Data will need to be re-processed.\n"
            file_path = getattr(state.file_info, 'path', '') if hasattr(state, 'file_info') else ''
            if file_path:
                info_msg += f"\nOriginal file: {file_path}"
        
        QMessageBox.information(self, "Session Loaded", info_msg)
    
    def restore_session_gui(self, hvsr_result, windows, seismic_data):
        """
        Restore GUI state after loading a session.
        
        Delegates to UIUpdateCoordinator for the actual UI updates.
        
        Args:
            hvsr_result: HVSRResult object (can be None)
            windows: WindowCollection object (can be None)
            seismic_data: SeismicData object (can be None)
        """
        # Delegate to the UI coordinator
        self.ui_coordinator.update_after_session_restore(hvsr_result, windows, seismic_data)
    
    def on_peaks_changed(self, peaks: list):
        """Handle peak list changes from dock. Delegates to PeakController."""
        self.peak_ctrl.set_references(self.hvsr_result, self.peak_picker_dock, self.plot_manager)
        self.peak_ctrl.on_peaks_changed(peaks)
    
    def on_detect_peaks_requested(self, mode: str, settings: dict):
        """Handle peak detection request from dock. Delegates to PeakController."""
        if self.hvsr_result is None:
            QMessageBox.warning(self, "No Data", "Please process HVSR data first.")
            return
        
        # Set up controller with current references
        self.peak_ctrl.set_references(self.hvsr_result, self.peak_picker_dock, self.plot_manager)
        
        # Detect peaks
        peaks = self.peak_ctrl.detect_peaks(mode, settings)
        
        # Add to dock if found
        if peaks:
            self.peak_picker_dock.add_peaks(peaks)
        else:
            QMessageBox.information(
                self, "No Peaks", 
                "No peaks found with current settings.\nTry lowering prominence threshold."
            )
    
    def on_manual_mode_requested(self, activate: bool):
        """Handle manual peak picking mode toggle. Delegates to PeakController."""
        self.peak_ctrl.set_references(self.hvsr_result, self.peak_picker_dock, self.plot_manager)
        
        if activate:
            self.peak_ctrl.enable_manual_mode(self.on_manual_peak_selected)
            self.status_bar.showMessage("MANUAL MODE: Click on HVSR curve to add peak")
        else:
            self.peak_ctrl.disable_manual_mode()
            self.status_bar.showMessage("Ready")
    
    def on_manual_peak_selected(self, frequency: float, amplitude: float):
        """Handle manual peak selection from plot click. Delegates to PeakController."""
        self.peak_ctrl.add_manual_peak(frequency, amplitude)
    
    def _on_peak_detection_error(self, error_msg: str):
        """Handle peak detection error from controller."""
        QMessageBox.critical(self, "Detection Error", error_msg)
    
    def on_properties_changed(self, properties):
        """
        Handle plot properties changes from properties dock.
        
        Args:
            properties: PlotProperties object with new settings
        """
        if not self.hvsr_result or not self.windows or not self.data:
            self.add_info("No data to apply properties to")
            return
        
        self.add_info(f"Properties applied: {properties.style_preset} style")
        
        # Apply properties via plotting controller
        self.plotting_ctrl.apply_properties(properties)
        
        # Update layers dock
        self.window_lines = self.plotting_ctrl.get_window_lines()
        self.stat_lines = self.plotting_ctrl.get_stat_lines()
        self.layers_dock.rebuild(self.window_lines, self.stat_lines)
    
    def _on_azimuthal_options_changed(self, options: dict):
        """
        Handle azimuthal plot options changes from properties dock.
        
        Args:
            options: Dictionary with plot options from AzimuthalPropertiesDock
        """
        if not hasattr(self, 'azimuthal_tab') or not self.azimuthal_tab.result:
            return
        
        # Update the azimuthal tab plot with new options
        try:
            self.azimuthal_tab.update_plot_with_options(options)
            self.add_info(f"Azimuthal plot updated: {options.get('cmap', 'default')} colormap")
        except Exception as e:
            self.add_info(f"Error updating azimuthal plot: {str(e)}")
    
    def replot_with_properties(self, properties):
        """
        Replot with given properties.
        
        Delegates to PlottingController for actual implementation.
        This method is called by plot_window_manager and properties_dock.
        
        Args:
            properties: PlotProperties object
        """
        if not self.hvsr_result or not self.windows:
            return
        
        # Delegate to PlottingController
        self.plotting_ctrl.set_data(self.hvsr_result, self.windows, self.data)
        self.plotting_ctrl.set_plot_manager(self.plot_manager)
        self.plotting_ctrl.apply_properties(properties)
        
        # Update local line references from controller
        self.window_lines = self.plotting_ctrl.get_window_lines()
        self.stat_lines = self.plotting_ctrl.get_stat_lines()
        
        # Rebuild layer dock
        self.layers_dock.rebuild(self.window_lines, self.stat_lines)
    
    def export_figure(self):
        """Export current plot as image (alias for export_plot_image)."""
        self.export_plot_image()
    
    def export_plot_image(self):
        """Export current plot view as high-DPI image. Delegates to ExportController."""
        if self.hvsr_result is None or self.plot_manager.fig is None:
            QMessageBox.warning(self, "No Plot", "No plot to export. Please process data first.")
            return
        
        self.export_ctrl.set_references(self.hvsr_result, self.windows, self.data, self.plot_manager)
        result = self.export_ctrl.export_plot_image()
        
        if result.success:
            file_size = Path(result.file_path).stat().st_size / 1024  # KB
            QMessageBox.information(
                self,
                "Export Success",
                f"Plot saved successfully!\n\n"
                f"File: {Path(result.file_path).name}\n"
                f"Size: {file_size:.1f} KB"
            )
        elif result.error_message:
            QMessageBox.critical(self, "Export Error", result.error_message)
    
    def _on_export_error(self, error_msg: str):
        """Handle export error from controller."""
        QMessageBox.critical(self, "Export Error", error_msg)
    
    def add_info(self, message: str):
        """Add information message to log."""
        # Use processing tab's info text if available
        if hasattr(self, 'processing_tab') and hasattr(self.processing_tab, 'info_text'):
            self.processing_tab.add_info(message)
        elif hasattr(self, 'info_text'):
            self.info_text.append(message)
            scrollbar = self.info_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())

    # ------------------------------------------------------------------
    #  Close / auto-save
    # ------------------------------------------------------------------

    def closeEvent(self, event):
        """Auto-save ALL module states on close.

        Saves HVSR + batch + bedrock + hvstrip + inversion state while
        the child widgets are still alive (before super() destroys them).
        If the Project Hub is still open, hide instead of closing so the
        hub can re-open a different analysis later.
        """
        # Save ALL modules (HVSR + sub-windows) while widgets are alive
        self._save_all_module_states()

        # If the hub is alive, just hide — don't destroy the main window
        hub = getattr(self, '_hub_window', None)
        if hub is not None and hub.isVisible():
            event.ignore()
            self.hide()
            return

        super().closeEvent(event)
    


if not HAS_PYQT5:
    class HVSRMainWindow:
        """Dummy class when PyQt5 not available."""
        def __init__(self):
            raise ImportError("PyQt5 is required for GUI functionality")
