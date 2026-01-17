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
    
    # Import modular controllers and panels for future use
    from hvsr_pro.gui.main_window_modules.controllers import (
        ProcessingController, PlottingController, 
        SessionController, WindowController, DataController,
        PeakController, ExportController
    )
    from hvsr_pro.gui.main_window_modules.panels import (
        ProcessingSettings, QCSettings, CoxFDWRASettings
    )




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
        if self.info_text.toPlainText():
            clipboard = QApplication.clipboard()
            clipboard.setText(self.info_text.toPlainText())
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
        """Get custom QC settings from the UI (via ProcessingTab's QCSettingsPanel)."""
        if hasattr(self, 'processing_tab') and hasattr(self.processing_tab, 'qc_panel'):
            qc_settings = self.processing_tab.qc_panel.get_settings()
            return {
                'enabled': qc_settings.enabled,
                'mode': qc_settings.mode,
                'algorithms': qc_settings.custom_algorithms
            }
        # Fallback for direct access (shouldn't happen after refactor)
        return {
            'enabled': True,
            'mode': 'preset',
            'algorithms': {}
        }

    # === REMOVED: _on_cox_enable_toggled ===
    # Now handled internally by CoxSettingsPanel

    def init_ui(self):
        """Initialize user interface."""
        # Central widget - just control panel (no embedded canvas by default)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout(central_widget)
        
        # Create tab widget for Data Load / Processing modes
        self.mode_tabs = QTabWidget()

        # === Tab 1: Data Load ===
        self.data_load_tab = DataLoadTab(self)
        self.data_load_tab.load_file_requested.connect(self.load_data_file)
        self.data_load_tab.file_selected.connect(self.on_data_file_selected_for_preview)
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
        
        main_layout.addWidget(self.mode_tabs)
        
        # Right side - docks
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
        
        # Connect azimuthal properties dock signals
        self.azimuthal_properties_dock.plot_options_changed.connect(self._on_azimuthal_options_changed)

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
        
        # Connect layer dock signals
        self.layers_dock.visibility_changed.connect(self.on_layer_visibility_changed)
        
        # Connect peak picker dock signals
        self.peak_picker_dock.peaks_changed.connect(self.on_peaks_changed)
        self.peak_picker_dock.detect_peaks_requested.connect(self.on_detect_peaks_requested)
        self.peak_picker_dock.manual_mode_requested.connect(self.on_manual_mode_requested)
        
        # Connect properties dock signals
        self.properties_dock.properties_changed.connect(self.on_properties_changed)
        self.properties_dock.visualization_mode_changed.connect(self.on_view_mode_changed)

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

        Args:
            index: Tab index (0 = Data Load, 1 = Processing, 2 = Azimuthal)
        """
        if index == 0:  # Data Load tab
            # Hide all docks
            self.layers_dock.setVisible(False)
            self.peak_picker_dock.setVisible(False)
            self.properties_dock.setVisible(False)
            self.export_dock.setVisible(False)
            self.azimuthal_properties_dock.setVisible(False)
            self.status_bar.showMessage("Data Load mode - Load and preview seismic data")

        elif index == 1:  # Processing tab
            # Show processing docks, hide azimuthal dock
            self.layers_dock.setVisible(True)
            self.peak_picker_dock.setVisible(True)
            self.properties_dock.setVisible(True)
            self.export_dock.setVisible(True)
            self.azimuthal_properties_dock.setVisible(False)
            self.status_bar.showMessage("Processing mode - Configure and run HVSR analysis")

        elif index == 2:  # Azimuthal tab
            # Hide processing docks, show azimuthal properties dock
            self.layers_dock.setVisible(False)
            self.peak_picker_dock.setVisible(False)
            self.properties_dock.setVisible(False)
            self.export_dock.setVisible(False)
            self.azimuthal_properties_dock.setVisible(True)
            self.azimuthal_properties_dock.raise_()  # Bring to front
            self.status_bar.showMessage("Azimuthal mode - Analyze directional site response")
            
            # Pass windows to azimuthal tab if available
            if self.windows and hasattr(self, 'azimuthal_tab'):
                self.azimuthal_tab.set_windows(self.windows)

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
        """Handle view mode change."""
        self.add_info(f"View mode changed to: {mode}")
        
        if not self.window_lines or not self.stat_lines:
            return
        
        # Update line visibility based on mode
        if mode == 'statistical':
            # Hide individual windows, show statistics
            for line in self.window_lines.values():
                line.set_visible(False)
            for line in self.stat_lines.values():
                line.set_visible(True)
        
        elif mode == 'windows':
            # Show individual windows + stats, respect visibility flags
            if self.windows:
                for idx, line in self.window_lines.items():
                    window = self.windows.get_window(idx)
                    if window:
                        line.set_visible(window.is_active() and window.visible)
            for line in self.stat_lines.values():
                line.set_visible(True)
        
        elif mode == 'both':
            # Show everything
            if self.windows:
                for idx, line in self.window_lines.items():
                    window = self.windows.get_window(idx)
                    if window:
                        line.set_visible(window.is_active() and window.visible)
            for line in self.stat_lines.values():
                line.set_visible(True)
        
        # Redraw
        if self.plot_manager:
            self.plot_manager.fig.canvas.draw_idle()

        self.add_info(f"Switched to {mode} view")

    # === REMOVED: _on_override_sampling_toggled ===
    # Now handled internally by ProcessingSettingsPanel

    def open_advanced_qc_settings(self):
        """Open Advanced QC Settings dialog."""
        from hvsr_pro.gui.dialogs import AdvancedQCDialog
        dialog = AdvancedQCDialog(self, self.custom_qc_settings)
        if dialog.exec_():
            self.custom_qc_settings = dialog.get_settings()
            self.add_info("Advanced QC settings updated")
            # Update QC mode combo to show "Custom"
            if self.custom_qc_settings and self.custom_qc_settings.get('enabled'):
                custom_idx = self.qc_combo.findData("custom")
                if custom_idx == -1:
                    self.qc_combo.addItem("Custom (Advanced)", "custom")
                    custom_idx = self.qc_combo.count() - 1
                self.qc_combo.setCurrentIndex(custom_idx)

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
        
        # Store for processing
        if load_result.mode == 'single':
            self.current_file = load_result.files[0] if load_result.files else None
        elif load_result.mode == 'multi_type1':
            self.current_file = load_result.files
        elif load_result.mode == 'multi_type2':
            self.current_file = load_result.groups
        
        self.process_btn.setEnabled(True)
        
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
            
            # Set timezone in combo box
            tz_name = time_range.get('timezone_name', 'UTC+0 (GMT)')
            tz_index = preview_canvas.timezone_combo.findText(tz_name, Qt.MatchContains)
            if tz_index >= 0:
                preview_canvas.timezone_combo.setCurrentIndex(tz_index)
            
            # Set datetime pickers
            from PyQt5.QtCore import QDateTime
            
            start_dt = time_range['start']
            end_dt = time_range['end']
            
            # Block signals to prevent auto-updates during setting
            preview_canvas.datetime_start.blockSignals(True)
            preview_canvas.datetime_end.blockSignals(True)
            
            preview_canvas.datetime_start.setDateTime(QDateTime(start_dt))
            preview_canvas.datetime_end.setDateTime(QDateTime(end_dt))
            
            preview_canvas.datetime_start.blockSignals(False)
            preview_canvas.datetime_end.blockSignals(False)
            
            # Apply the time filter
            preview_canvas.apply_time_filter()
            
            self.add_info(f"Time range applied to preview: {start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')} ({tz_name})")
            
        except Exception as e:
            print(f"Warning: Could not apply time range to preview: {e}")
    
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
            settings.qc_preset if settings.qc_mode == 'preset' else 'custom',
            settings.cox_enabled,
            settings.use_parallel,
            settings.n_cores,
            settings.manual_sampling_rate,
            custom_qc_settings,
            cox_fdwra_settings
        )
        self.thread.progress.connect(self.on_progress)
        self.thread.finished.connect(self.on_processing_finished)
        self.thread.error.connect(self.on_processing_error)
        self.thread.start()
    
    def _build_custom_qc_dict(self, custom_algorithms):
        """Build custom QC settings dictionary from panel settings."""
        return {
            'enabled': True,
            'mode': 'custom',
            'algorithms': {
                'amplitude': {'enabled': custom_algorithms.get('amplitude', {}).get('enabled', False), 'params': {}},
                'quality_threshold': {'enabled': custom_algorithms.get('quality_threshold', {}).get('enabled', False), 'params': {'threshold': 0.5}},
                'sta_lta': {'enabled': custom_algorithms.get('sta_lta', {}).get('enabled', False), 'params': {
                    'sta_length': 1.0, 'lta_length': 30.0, 'min_ratio': 0.15, 'max_ratio': 2.5
                }},
                'frequency_domain': {'enabled': custom_algorithms.get('frequency_domain', {}).get('enabled', False), 'params': {'spike_threshold': 3.0}},
                'statistical_outlier': {'enabled': custom_algorithms.get('statistical_outlier', {}).get('enabled', False), 'params': {'method': 'iqr', 'threshold': 2.0}},
                'hvsr_amplitude': {'enabled': custom_algorithms.get('hvsr_amplitude', {}).get('enabled', False), 'params': {'min_amplitude': 1.0}},
                'flat_peak': {'enabled': custom_algorithms.get('flat_peak', {}).get('enabled', False), 'params': {'flatness_threshold': 0.15}},
                'cox_fdwra': {'enabled': custom_algorithms.get('cox_fdwra', {}).get('enabled', False), 'params': {'n': 2.0, 'max_iterations': 20}}
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
            "process_hvsr() is deprecated. Use ProcessingTab.process_requested signal instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        if not self.current_file:
            QMessageBox.warning(self, "No File", "Please load a data file first.")
            return
        
        # Disable controls
        self.process_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # Get settings
        window_length = self.window_length_spin.value()
        overlap = self.overlap_spin.value() / 100.0
        smoothing = self.smoothing_spin.value()
        freq_min = self.freq_min_spin.value()
        freq_max = self.freq_max_spin.value()
        n_frequencies = self.n_freq_spin.value()
        # Get QC mode (preset or custom)
        if self.preset_radio.isChecked():
            qc_mode = self.qc_combo.currentData()  # Preset mode
            custom_qc_from_ui = None
        else:
            qc_mode = 'custom'  # Custom mode
            custom_qc_from_ui = self._get_custom_qc_settings_from_ui()
        
        apply_cox_fdwra = self.cox_fdwra_check.isChecked()  # Get Cox FDWRA setting
        use_parallel = self.parallel_check.isChecked()  # Get parallel processing setting
        n_cores = self.cores_spin.value() if use_parallel else 1  # Get number of cores to use

        # Get sampling rate override
        override_sampling = self.override_sampling_check.isChecked()
        manual_sampling_rate = self.sampling_rate_spin.value() if override_sampling else None
        
        # Validate frequency range
        if freq_min >= freq_max:
            QMessageBox.warning(self, "Invalid Range", "Minimum frequency must be less than maximum frequency.")
            self.process_btn.setEnabled(True)
            self.progress_bar.setVisible(False)
            return
        
        # Log settings
        self.add_info(f"Frequency range: {freq_min:.2f} - {freq_max:.1f} Hz ({n_frequencies} points)")
        if manual_sampling_rate:
            self.add_info(f"Sampling rate: {manual_sampling_rate:.4f} Hz (manual override)")
        if self.preset_radio.isChecked():
            self.add_info(f"QC Mode: {self.qc_combo.currentText()}")
        else:
            self.add_info(f"QC Mode: Custom (manual settings)")
        if apply_cox_fdwra or qc_mode in ('sesame', 'publication'):
            self.add_info(f"Cox FDWRA: Enabled (peak frequency consistency)")
        if use_parallel:
            self.add_info(f"Parallel processing: Enabled (using {n_cores} of {self._get_cpu_count()} cores)")

        # Determine which custom settings to use
        final_custom_settings = custom_qc_from_ui if custom_qc_from_ui else self.custom_qc_settings
        
        # Get Cox FDWRA specific settings
        cox_fdwra_settings = {
            'n': self.cox_n_spin.value(),
            'max_iterations': self.cox_iterations_spin.value(),
            'min_iterations': self.cox_min_iterations_spin.value(),
            'distribution': self.cox_dist_combo.currentText()
        }
        
        # Start processing thread with load mode and time range
        self.thread = ProcessingThread(
            self.current_file, window_length, overlap, smoothing,
            self.load_mode, self.current_time_range,
            freq_min, freq_max, n_frequencies, qc_mode, apply_cox_fdwra, use_parallel,
            n_cores, manual_sampling_rate, final_custom_settings,
            cox_fdwra_settings
        )
        self.thread.progress.connect(self.on_progress)
        self.thread.finished.connect(self.on_processing_finished)
        self.thread.error.connect(self.on_processing_error)
        self.thread.start()
    
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
        """Handle processing completion."""
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

        self.hvsr_result = result
        self.windows = windows
        self.data = data
        
        # Update WindowController with windows reference
        self.window_ctrl.set_windows(windows)
        
        # Update UI via processing tab
        if hasattr(self, 'processing_tab'):
            self.processing_tab.set_progress(0, visible=False)
            self.processing_tab.set_processing_enabled(True)
            self.processing_tab.set_window_buttons_enabled(True)
        
        # Enable action buttons if they exist (may be in Export dock instead)
        if hasattr(self, 'export_plot_btn'):
            self.export_plot_btn.setEnabled(True)
        if hasattr(self, 'report_btn'):
            self.report_btn.setEnabled(True)
        if hasattr(self, 'export_btn'):
            self.export_btn.setEnabled(True)
        if hasattr(self, 'save_btn'):
            self.save_btn.setEnabled(True)
        
        # Update window info
        self.update_window_info()
        
        # Update canvas (old method - keep for compatibility)
        self.canvas.set_data(result, windows, data)
        
        # Update layers dock with windows reference BEFORE plotting
        self.layers_dock.set_references(self.plot_manager, windows)

        # Update peak picker dock with HVSR data
        self.peak_picker_dock.set_hvsr_data(result, result.frequencies, result.mean_hvsr)

        # Update export dock with results and seismic data
        self.export_dock.set_references(result, windows, self.plot_manager, data)

        # Update collapsible data panel in Processing tab with data from Data Load tab
        if hasattr(self, 'processing_data_panel') and hasattr(self, 'data_load_tab'):
            self.processing_data_panel.update_from_data_load_tab(self.data_load_tab)

        # Update azimuthal tab with windows and data for potential azimuthal processing
        if hasattr(self, 'azimuthal_tab'):
            self.azimuthal_tab.set_windows(windows, data)
            # Also update its data panel
            if hasattr(self.azimuthal_tab, 'data_panel') and hasattr(self, 'data_load_tab'):
                self.azimuthal_tab.data_panel.update_from_data_load_tab(self.data_load_tab)

        # === Plot in separate window via controller ===
        # Set data in plotting controller
        self.plotting_ctrl.set_data(result, windows, data)
        self.plotting_ctrl.set_plot_manager(self.plot_manager)
        
        # Plot using controller
        lines = self.plotting_ctrl.plot_hvsr_results(result, windows, data)
        self.window_lines = lines.get('window_lines', {})
        self.stat_lines = lines.get('stat_lines', {})
        
        # Rebuild layer dock with lines
        self.layers_dock.rebuild(self.window_lines, self.stat_lines)
        
        # Show plot window
        self.plot_manager.show_separate()
        
        # Add info
        self.add_info(f"Processing complete!")
        self.add_info(f"   Windows: {windows.n_active}/{windows.n_windows}")
        if result.primary_peak:
            self.add_info(f"   Primary peak: f0 = {result.primary_peak.frequency:.2f} Hz")
        
        self.status_bar.showMessage("Ready - Use layer dock to toggle visibility")
    
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
            print("[Main] Cannot refresh: no data available")
            return
        
        print(f"[Main] Refreshing plot (timeline={self.plot_manager.show_timeline}, stats={self.plot_manager.show_quality_stats})")
        
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

    def _validate_processing_results(self, result, windows):
        """
        Validate HVSR processing results before plotting.
        
        .. deprecated::
            Use self.processing_ctrl.validate_results() instead.

        Returns:
            tuple: (is_valid: bool, error_message: str)
        """
        # Delegate to ProcessingController
        return self.processing_ctrl.validate_results(result, windows)

    def _show_qc_failure_dialog(self, windows, error_msg):
        """
        Show detailed QC failure dialog with diagnostic information.
        
        .. deprecated::
            Use self.processing_ctrl._show_qc_failure_dialog() instead.

        Args:
            windows: WindowCollection object
            error_msg: Primary error message
        """
        # Delegate to ProcessingController
        self.processing_ctrl._show_qc_failure_dialog(windows, error_msg)
        
        # Also log to info panel (controller doesn't have access to this)
        report = self.processing_ctrl._generate_qc_report(windows)
        self.add_info("=" * 60)
        self.add_info("QC FAILURE - No windows passed quality control")
        self.add_info("=" * 60)
        self.add_info(report)
        self.add_info("=" * 60)

    def _generate_qc_diagnostic_report(self, windows):
        """
        Generate diagnostic report showing why windows failed QC.
        
        .. deprecated::
            Use self.processing_ctrl._generate_qc_report() instead.

        Args:
            windows: WindowCollection object

        Returns:
            str: Formatted diagnostic report
        """
        # Delegate to ProcessingController
        return self.processing_ctrl._generate_qc_report(windows)

    def on_processing_error(self, error_msg: str):
        """Handle processing error."""
        self.progress_bar.setVisible(False)
        self.process_btn.setEnabled(True)
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
            # Recompute with current windows
            smoothing = self.smoothing_spin.value()
            processor = HVSRProcessor(smoothing_bandwidth=smoothing)
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
            self.window_info_label.setText("No windows")
            return
        
        info = (f"Total: {self.windows.n_windows}\n"
                f"Active: {self.windows.n_active} "
                f"({self.windows.acceptance_rate*100:.1f}%)\n"
                f"Rejected: {self.windows.n_rejected}")
        self.window_info_label.setText(info)
    
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
        Delegates to SessionController for the heavy lifting.
        """
        # Sync work directory with controller
        self.session_ctrl.set_work_directory(getattr(self, '_work_directory', ''))
        
        # Delegate to session controller
        result = self.session_ctrl.save_full_session(self)
        
        if result.success:
            QMessageBox.information(self, "Session Saved", result.info_message)
        else:
            QMessageBox.critical(self, "Save Failed", result.error_message)
    
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
        Mirrors on_processing_finished() behavior to fully restore the UI.
        
        Args:
            hvsr_result: HVSRResult object (can be None)
            windows: WindowCollection object (can be None)
            seismic_data: SeismicData object (can be None)
        """
        # 1. Store data in instance variables FIRST (before any dock updates)
        self.hvsr_result = hvsr_result
        self.windows = windows
        self.data = seismic_data
        
        # Update WindowController with windows reference
        if windows is not None:
            self.window_ctrl.set_windows(windows)
        
        # Log data availability for debugging
        self.add_info(f"Session data: HVSR={'Yes' if hvsr_result else 'No'}, "
                     f"Windows={'Yes' if windows else 'No'}, "
                     f"SeismicData={'Yes' if seismic_data else 'No'}")
        
        # 2. Update interactive canvas
        if hasattr(self, 'canvas') and hvsr_result is not None:
            try:
                self.canvas.set_data(hvsr_result, windows, seismic_data)
            except Exception as e:
                self.add_info(f"Warning: Could not update canvas: {str(e)}")
        
        # 3. Update layers dock (CRITICAL for window layers to work)
        if hasattr(self, 'layers_dock') and windows is not None:
            try:
                self.layers_dock.set_references(self.plot_manager, windows)
            except Exception as e:
                self.add_info(f"Warning: Could not update layers dock: {str(e)}")
        
        # 4. Update peak picker dock
        if hasattr(self, 'peak_picker_dock') and hvsr_result is not None:
            try:
                self.peak_picker_dock.set_hvsr_data(
                    hvsr_result,
                    hvsr_result.frequencies,
                    hvsr_result.mean_hvsr
                )
            except Exception as e:
                self.add_info(f"Warning: Could not update peak picker: {str(e)}")
        
        # 5. Update export dock with all references including seismic data
        if hasattr(self, 'export_dock'):
            try:
                self.export_dock.set_references(
                    hvsr_result, windows, self.plot_manager, seismic_data
                )
                # Log whether waveform export will be available
                if seismic_data is not None:
                    self.add_info("Export dock: All figure types available (including waveform plots)")
                else:
                    self.add_info("Export dock: Waveform plots unavailable (no seismic data)")
            except Exception as e:
                self.add_info(f"Warning: Could not update export dock: {str(e)}")
        
        # 6. Update collapsible data panel in Processing tab
        if hasattr(self, 'processing_data_panel') and hasattr(self, 'data_load_tab'):
            try:
                self.processing_data_panel.update_from_data_load_tab(self.data_load_tab)
            except Exception as e:
                self.add_info(f"Warning: Could not update data panel: {str(e)}")
        
        # 7. Update azimuthal tab with windows and data
        if hasattr(self, 'azimuthal_tab') and windows is not None:
            try:
                self.azimuthal_tab.set_windows(windows, seismic_data)
                if hasattr(self.azimuthal_tab, 'data_panel') and hasattr(self, 'data_load_tab'):
                    self.azimuthal_tab.data_panel.update_from_data_load_tab(self.data_load_tab)
            except Exception as e:
                self.add_info(f"Warning: Could not update azimuthal tab: {str(e)}")
        
        # 8. Enable action buttons
        self._enable_buttons_after_restore()
        
        # 9. Update window info display
        self.update_window_info()
        
        # 10. Plot in separate window (the main HVSR plot) via PlottingController
        if hvsr_result is not None and windows is not None:
            try:
                # Use the thin wrapper which delegates to PlottingController
                self.plot_results_separate_window(hvsr_result, windows, seismic_data)
            except Exception as e:
                self.add_info(f"Warning: Could not open plot window: {str(e)}")
        
        # 11. Switch to Processing tab
        self.mode_tabs.setCurrentIndex(1)
        
        # 12. Update status
        self.status_bar.showMessage("Session restored - Use layer dock to toggle visibility")
    
    def _enable_buttons_after_restore(self):
        """Enable action buttons after session restore."""
        # Enable export/action buttons
        button_names = ['export_plot_btn', 'report_btn', 'export_btn', 'save_btn']
        for btn_name in button_names:
            if hasattr(self, btn_name):
                getattr(self, btn_name).setEnabled(True)
        
        # Enable window manipulation buttons
        if hasattr(self, 'reject_all_btn'):
            self.reject_all_btn.setEnabled(True)
        if hasattr(self, 'accept_all_btn'):
            self.accept_all_btn.setEnabled(True)
        if hasattr(self, 'recompute_btn'):
            self.recompute_btn.setEnabled(True)
    
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
    
    # === Backward compatibility properties ===
    # 
    # These proxy to processing_tab widgets for code that references them directly.
    # 
    # .. deprecated::
    #     These properties are maintained for backward compatibility only.
    #     New code should access widgets directly via self.processing_tab:
    #         main_window.processing_tab.window_length_spin
    #     Or use the ProcessingTab's settings methods:
    #         main_window.processing_tab.get_settings()
    #
    # These properties will be removed in a future version.
    # 
    
    @property
    def window_length_spin(self):
        """Backward compatibility: access window length spin via processing_tab."""
        return self.processing_tab.window_length_spin
    
    @property
    def overlap_spin(self):
        """Backward compatibility: access overlap spin via processing_tab."""
        return self.processing_tab.overlap_spin
    
    @property
    def smoothing_spin(self):
        """Backward compatibility: access smoothing spin via processing_tab."""
        return self.processing_tab.smoothing_spin
    
    @property
    def freq_min_spin(self):
        """Backward compatibility: access freq min spin via processing_tab."""
        return self.processing_tab.freq_min_spin
    
    @property
    def freq_max_spin(self):
        """Backward compatibility: access freq max spin via processing_tab."""
        return self.processing_tab.freq_max_spin
    
    @property
    def n_freq_spin(self):
        """Backward compatibility: access n freq spin via processing_tab."""
        return self.processing_tab.n_freq_spin
    
    @property
    def override_sampling_check(self):
        """Backward compatibility: access override sampling check via processing_tab."""
        return self.processing_tab.override_sampling_check
    
    @property
    def sampling_rate_spin(self):
        """Backward compatibility: access sampling rate spin via processing_tab."""
        return self.processing_tab.sampling_rate_spin
    
    @property
    def qc_enable_check(self):
        """Backward compatibility: access QC enable check via processing_tab."""
        return self.processing_tab.qc_enable_check
    
    @property
    def preset_radio(self):
        """Backward compatibility: access preset radio via processing_tab."""
        return self.processing_tab.preset_radio
    
    @property
    def custom_radio(self):
        """Backward compatibility: access custom radio via processing_tab."""
        return self.processing_tab.custom_radio
    
    @property
    def qc_combo(self):
        """Backward compatibility: access QC preset combo via processing_tab."""
        return self.processing_tab.qc_combo
    
    @property
    def cox_fdwra_check(self):
        """Backward compatibility: access Cox enable check via processing_tab."""
        return self.processing_tab.cox_fdwra_check
    
    @property
    def cox_n_spin(self):
        """Backward compatibility: access Cox n spin via processing_tab."""
        return self.processing_tab.cox_n_spin
    
    @property
    def cox_iterations_spin(self):
        """Backward compatibility: access Cox max iterations spin via processing_tab."""
        return self.processing_tab.cox_iterations_spin
    
    @property
    def cox_min_iterations_spin(self):
        """Backward compatibility: access Cox min iterations spin via processing_tab."""
        return self.processing_tab.cox_min_iterations_spin
    
    @property
    def cox_dist_combo(self):
        """Backward compatibility: access Cox distribution combo via processing_tab."""
        return self.processing_tab.cox_dist_combo
    
    @property
    def parallel_check(self):
        """Backward compatibility: access parallel check via processing_tab."""
        return self.processing_tab.parallel_check
    
    @property
    def cores_spin(self):
        """Backward compatibility: access cores spin via processing_tab."""
        return self.processing_tab.cores_spin
    
    @property
    def process_btn(self):
        """Backward compatibility: access process button via processing_tab."""
        return self.processing_tab.process_btn
    
    @property
    def progress_bar(self):
        """Backward compatibility: access progress bar via processing_tab."""
        return self.processing_tab.progress_bar
    
    @property
    def info_text(self):
        """Backward compatibility: access info text via processing_tab."""
        return self.processing_tab.info_text
    
    @property
    def window_info_label(self):
        """Backward compatibility: access window info label via processing_tab."""
        return self.processing_tab.window_info_label
    
    @property
    def reject_all_btn(self):
        """Backward compatibility: access reject all button via processing_tab."""
        return self.processing_tab.reject_all_btn
    
    @property
    def accept_all_btn(self):
        """Backward compatibility: access accept all button via processing_tab."""
        return self.processing_tab.accept_all_btn
    
    @property
    def recompute_btn(self):
        """Backward compatibility: access recompute button via processing_tab."""
        return self.processing_tab.recompute_btn


if not HAS_PYQT5:
    class HVSRMainWindow:
        """Dummy class when PyQt5 not available."""
        def __init__(self):
            raise ImportError("PyQt5 is required for GUI functionality")
