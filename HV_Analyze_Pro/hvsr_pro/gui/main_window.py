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
    from hvsr_pro.gui.tabs import DataLoadTab, AzimuthalTab
    from hvsr_pro.gui.workers import ProcessingThread
    
    # Import modular controllers and panels for future use
    from hvsr_pro.gui.main_window_modules.controllers import (
        ProcessingController, PlottingController, 
        SessionController, WindowController
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
        """Create menu bar with common actions."""
        menubar = self.menuBar()
        menubar.setNativeMenuBar(False)  # Fix for Windows menu bar click issues
        
        # Ensure menu bar is visible and can receive events
        menubar.setVisible(True)

        # File menu
        file_menu = menubar.addMenu('&File')
        
        # Open action
        open_action = file_menu.addAction('&Open...')
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.load_data_file)
        
        # Save results action
        save_action = file_menu.addAction('&Save Results...')
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.export_results)
        
        file_menu.addSeparator()
        
        # Session menu items
        save_session_action = file_menu.addAction('Save &Session...')
        save_session_action.setShortcut('Ctrl+Shift+S')
        save_session_action.triggered.connect(self.save_session)
        save_session_action.setToolTip("Save current settings and state to resume later")
        
        load_session_action = file_menu.addAction('&Load Session...')
        load_session_action.setShortcut('Ctrl+Shift+O')
        load_session_action.triggered.connect(self.load_session)
        load_session_action.setToolTip("Load a saved session file")
        
        file_menu.addSeparator()
        
        # Export figure action
        export_fig_action = file_menu.addAction('&Export Figure...')
        export_fig_action.setShortcut('Ctrl+E')
        export_fig_action.triggered.connect(self.export_figure)
        
        file_menu.addSeparator()
        
        # Exit action
        exit_action = file_menu.addAction('E&xit')
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        
        # Edit menu
        edit_menu = menubar.addMenu('&Edit')
        
        # Copy info action
        copy_action = edit_menu.addAction('&Copy Info')
        copy_action.setShortcut('Ctrl+C')
        copy_action.triggered.connect(self.copy_info)
        
        # Clear info action
        clear_action = edit_menu.addAction('C&lear Info')
        clear_action.triggered.connect(lambda: self.info_text.clear())
        
        # View menu
        view_menu = menubar.addMenu('&View')

        # Processing Tab section
        processing_submenu = QMenu('Processing Tab', self)

        self.layers_action = processing_submenu.addAction('&Layers Dock')
        self.layers_action.setShortcut('Ctrl+Shift+L')
        self.layers_action.setCheckable(True)
        self.layers_action.setChecked(True)
        self.layers_action.triggered.connect(lambda checked: self.layers_dock.setVisible(checked))

        self.peaks_action = processing_submenu.addAction('&Peak Picker Dock')
        self.peaks_action.setShortcut('Ctrl+Shift+P')
        self.peaks_action.setCheckable(True)
        self.peaks_action.setChecked(True)
        self.peaks_action.triggered.connect(lambda checked: self.peak_picker_dock.setVisible(checked))

        self.props_action = processing_submenu.addAction('P&roperties Dock')
        self.props_action.setShortcut('Ctrl+Shift+R')
        self.props_action.setCheckable(True)
        self.props_action.setChecked(True)
        self.props_action.triggered.connect(lambda checked: self.properties_dock.setVisible(checked))

        view_menu.addMenu(processing_submenu)
        view_menu.addSeparator()

        # Data Load Tab section
        dataload_submenu = QMenu('Data Load Tab', self)

        self.preview_action = dataload_submenu.addAction('&Preview Canvas')
        self.preview_action.setShortcut('Ctrl+Shift+V')
        self.preview_action.setCheckable(True)
        self.preview_action.setChecked(True)
        self.preview_action.triggered.connect(self.toggle_preview_canvas)

        view_menu.addMenu(dataload_submenu)
        view_menu.addSeparator()

        # Tab visibility section
        tabs_submenu = QMenu('Tabs', self)

        self.azimuthal_tab_action = tabs_submenu.addAction('&Azimuthal Tab')
        self.azimuthal_tab_action.setShortcut('Ctrl+3')
        self.azimuthal_tab_action.setCheckable(True)
        self.azimuthal_tab_action.setChecked(True)
        self.azimuthal_tab_action.triggered.connect(self.toggle_azimuthal_tab)

        view_menu.addMenu(tabs_submenu)
        view_menu.addSeparator()

        # Loaded Data Column (global)
        self.loaded_data_action = view_menu.addAction('&Loaded Data Column')
        self.loaded_data_action.setShortcut('Ctrl+Shift+D')
        self.loaded_data_action.setCheckable(True)
        self.loaded_data_action.setChecked(True)
        self.loaded_data_action.triggered.connect(self.toggle_loaded_data_column)

        view_menu.addSeparator()

        # Plot Window (global)
        plot_action = view_menu.addAction('&Plot Window')
        plot_action.setShortcut('Ctrl+P')
        plot_action.triggered.connect(self.toggle_plot_window)
        
        # Mode menu
        mode_menu = menubar.addMenu('&Mode')

        dataload_action = mode_menu.addAction('&Data Load')
        dataload_action.setShortcut('Ctrl+1')
        dataload_action.triggered.connect(lambda: self.mode_tabs.setCurrentIndex(0))
        dataload_action.setToolTip("Switch to Data Load tab (Ctrl+1)")

        processing_action = mode_menu.addAction('&Processing')
        processing_action.setShortcut('Ctrl+2')
        processing_action.triggered.connect(lambda: self.mode_tabs.setCurrentIndex(1))
        processing_action.setToolTip("Switch to Processing tab (Ctrl+2)")
        
        # Help menu
        help_menu = menubar.addMenu('&Help')
        
        about_action = help_menu.addAction('&About')
        about_action.triggered.connect(self.show_about)
        
        shortcuts_action = help_menu.addAction('&Keyboard Shortcuts')
        shortcuts_action.setShortcut('F1')
        shortcuts_action.triggered.connect(self.show_shortcuts)
    
    def copy_info(self):
        """Copy info text to clipboard."""
        if self.info_text.toPlainText():
            clipboard = QApplication.clipboard()
            clipboard.setText(self.info_text.toPlainText())
            self.statusBar().showMessage("Info copied to clipboard", 2000)
    
    def show_about(self):
        """Show about dialog."""
        QMessageBox.about(self, "About HVSR Pro",
            "<h2>HVSR Pro v2.0</h2>"
            "<p>Professional Horizontal-to-Vertical Spectral Ratio Analysis</p>"
            "<p>A comprehensive tool for seismic data processing and HVSR computation.</p>"
            "<br>"
            "<p><b>Features:</b></p>"
            "<ul>"
            "<li>Single file processing</li>"
            "<li>Advanced quality control algorithms</li>"
            "<li>Cox FDWRA peak consistency analysis</li>"
            "<li>Interactive visualization</li>"
            "<li>Customizable processing parameters</li>"
            "</ul>"
            "<br>"
            "<p>© 2024 HVSR Pro Development Team</p>")
    
    def show_shortcuts(self):
        """Show keyboard shortcuts dialog."""
        shortcuts_text = """
        <h3>Keyboard Shortcuts</h3>
        <table cellpadding="5">
        <tr><th colspan="2" align="left">File Operations</th></tr>
        <tr><td><b>Ctrl+O</b></td><td>Open file</td></tr>
        <tr><td><b>Ctrl+S</b></td><td>Save results</td></tr>
        <tr><td><b>Ctrl+E</b></td><td>Export figure</td></tr>
        <tr><td><b>Ctrl+Q</b></td><td>Exit</td></tr>

        <tr><th colspan="2" align="left"><br>Tab Navigation</th></tr>
        <tr><td><b>Ctrl+1</b></td><td>Switch to Data Load tab</td></tr>
        <tr><td><b>Ctrl+2</b></td><td>Switch to Processing tab</td></tr>

        <tr><th colspan="2" align="left"><br>View Controls</th></tr>
        <tr><td><b>Ctrl+P</b></td><td>Toggle plot window</td></tr>
        <tr><td><b>Ctrl+Shift+L</b></td><td>Toggle Layers Dock</td></tr>
        <tr><td><b>Ctrl+Shift+P</b></td><td>Toggle Peak Picker Dock</td></tr>
        <tr><td><b>Ctrl+Shift+R</b></td><td>Toggle Properties Dock</td></tr>
        <tr><td><b>Ctrl+Shift+V</b></td><td>Toggle Preview Canvas</td></tr>
        <tr><td><b>Ctrl+Shift+D</b></td><td>Toggle Loaded Data Column</td></tr>

        <tr><th colspan="2" align="left"><br>Other</th></tr>
        <tr><td><b>F1</b></td><td>Show this help</td></tr>
        </table>
        """
        QMessageBox.information(self, "Keyboard Shortcuts", shortcuts_text)
    
    def _get_cpu_count(self) -> int:
        """Get number of CPU cores."""
        try:
            from multiprocessing import cpu_count
            return cpu_count()
        except:
            return 4  # Default fallback

    def _on_parallel_toggled(self, state):
        """Handle parallel processing checkbox toggle."""
        enabled = (state == Qt.Checked)
        self.cores_spin.setEnabled(enabled)

    def _on_qc_enable_toggled(self, checked: bool):
        """Handle QC enable checkbox toggle."""
        self.preset_radio.setEnabled(checked)
        self.custom_radio.setEnabled(checked)
        self.preset_widget.setEnabled(checked)
        self.custom_widget.setEnabled(checked)
        self.qc_combo.setEnabled(checked)
        self.advanced_qc_btn.setEnabled(checked)
    
    def _on_qc_mode_changed(self, checked: bool):
        """Handle Preset/Custom radio button toggle."""
        if self.preset_radio.isChecked():
            self.preset_widget.show()
            self.custom_widget.hide()
        else:
            self.preset_widget.hide()
            self.custom_widget.show()
    
    def _update_preset_description(self):
        """Update the preset description based on selected preset."""
        descriptions = {
            "conservative": "Only rejects obvious problems (dead channels, clipping). Best for noisy data.",
            "balanced": "Amplitude checks only. Recommended for most datasets.",
            "aggressive": "Strict QC with STA/LTA, frequency, and statistical checks. For clean data.",
            "sesame": "SESAME-compliant processing with Cox FDWRA for publication-quality results.",
            "publication": "4-condition rejection: HVSR amplitude, peak consistency, flat peaks."
        }
        current_mode = self.qc_combo.currentData()
        self.preset_desc_label.setText(descriptions.get(current_mode, ""))
    
    def _get_custom_qc_settings_from_ui(self):
        """Get custom QC settings from the UI checkboxes."""
        return {
            'enabled': self.qc_enable_check.isChecked(),
            'mode': 'custom',
            'algorithms': {
                'amplitude': {'enabled': self.custom_amplitude_check.isChecked(), 'params': {}},
                'quality_threshold': {'enabled': self.custom_quality_check.isChecked(), 'params': {'threshold': 0.5}},
                'sta_lta': {'enabled': self.custom_stalta_check.isChecked(), 'params': {
                    'sta_length': 1.0, 'lta_length': 30.0, 'min_ratio': 0.15, 'max_ratio': 2.5
                }},
                'frequency_domain': {'enabled': self.custom_freq_check.isChecked(), 'params': {'spike_threshold': 3.0}},
                'statistical_outlier': {'enabled': self.custom_stats_check.isChecked(), 'params': {'method': 'iqr', 'threshold': 2.0}},
                'hvsr_amplitude': {'enabled': self.custom_hvsr_amp_check.isChecked(), 'params': {'min_amplitude': 1.0}},
                'flat_peak': {'enabled': self.custom_flat_peak_check.isChecked(), 'params': {'flatness_threshold': 0.15}},
                'cox_fdwra': {'enabled': self.custom_cox_fdwra_check.isChecked(), 'params': {'n': 2.0, 'max_iterations': 20}}
            }
        }

    def _on_cox_enable_toggled(self, checked: bool):
        """Handle Cox FDWRA enable checkbox toggle."""
        self.cox_n_spin.setEnabled(checked)
        self.cox_iterations_spin.setEnabled(checked)
        self.cox_min_iterations_spin.setEnabled(checked)
        self.cox_dist_combo.setEnabled(checked)

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

        # === Tab 2: Processing (renamed from Single File) ===
        processing_tab = QWidget()
        processing_outer_layout = QVBoxLayout(processing_tab)
        processing_outer_layout.setContentsMargins(5, 5, 5, 5)
        processing_outer_layout.setSpacing(5)

        # Collapsible data panel at top
        from hvsr_pro.gui.components import CollapsibleDataPanel
        self.processing_data_panel = CollapsibleDataPanel(title="Loaded Data")
        # Starts collapsed by default
        processing_outer_layout.addWidget(self.processing_data_panel)

        # Main processing content
        processing_layout = QHBoxLayout()
        processing_layout.setContentsMargins(0, 0, 0, 0)

        # Left panel - processing controls with scroll area
        left_panel = self.create_control_panel()

        # Wrap control panel in scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidget(left_panel)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setMinimumWidth(300)

        processing_layout.addWidget(scroll_area, stretch=1)
        processing_outer_layout.addLayout(processing_layout, 1)  # stretch

        # Add processing tab
        self.mode_tabs.addTab(processing_tab, "Processing")

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
    
    def create_control_panel(self) -> QWidget:
        """Create left control panel."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Title with version
        title = QLabel("HVSR Pro v2.0")
        title.setFont(QFont("Arial", 16, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                color: #2C3E50;
                padding: 10px;
                background-color: #ECF0F1;
                border-radius: 5px;
            }
        """)
        layout.addWidget(title)

        # Info label
        info_label = QLabel("Configure processing parameters below.\nLoad data in the 'Data Load' tab first.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("QLabel { color: #666; padding: 5px; }")
        layout.addWidget(info_label)

        # Processing settings group
        settings_group = self.create_settings_group()
        layout.addWidget(settings_group)

        # Note: View mode selector has been moved to Properties panel
        # (see properties_dock.py - Visualization Mode section)

        # Plot window toggle button
        self.plot_mode_button = QPushButton("Show Plot Window")
        self.plot_mode_button.clicked.connect(self.toggle_plot_window)
        self.plot_mode_button.setToolTip("Open plot in separate window")
        layout.addWidget(self.plot_mode_button)
        
        # Window management group (for quick accept/reject all)
        window_group = self.create_window_group()
        layout.addWidget(window_group)
        
        # Note: Actions (Export, Save, etc.) have been moved to the Export dock
        # to reduce clutter in the main control panel.
        # Uncomment below if you want to restore inline actions:
        # actions_group = self.create_actions_group()
        # layout.addWidget(actions_group)
        
        # Info display
        self.info_text = QTextEdit()
        self.info_text.setReadOnly(True)
        self.info_text.setMaximumHeight(200)
        self.info_text.setPlaceholderText("Processing information will appear here...")
        layout.addWidget(self.info_text)
        
        # Progress bar with text
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        layout.addStretch()
        return panel
    
    def create_file_group(self) -> QGroupBox:
        """Create file import group."""
        group = QGroupBox("Data Import")
        layout = QVBoxLayout()
        
        # File path display
        self.file_label = QLabel("No file loaded")
        self.file_label.setWordWrap(True)
        layout.addWidget(self.file_label)
        
        # Load button with shortcut and tooltip
        load_btn = QPushButton("Load Data File")
        load_btn.clicked.connect(self.load_data_file)
        load_btn.setShortcut("Ctrl+O")
        load_btn.setToolTip("Load seismic data file (Ctrl+O)\nSupported formats: .txt, .csv, .mseed")
        load_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 4px;
                padding: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        layout.addWidget(load_btn)
        
        # Recent files combo (placeholder)
        self.recent_combo = QComboBox()
        self.recent_combo.addItem("Recent files...")
        self.recent_combo.setEnabled(False)
        layout.addWidget(self.recent_combo)
        
        group.setLayout(layout)
        return group
    
    def create_settings_group(self) -> QGroupBox:
        """Create processing settings group."""
        group = QGroupBox("Processing Settings")
        layout = QVBoxLayout()
        
        # Window length
        wl_layout = QHBoxLayout()
        wl_layout.addWidget(QLabel("Window Length (s):"))
        self.window_length_spin = QDoubleSpinBox()
        self.window_length_spin.setRange(10, 300)
        self.window_length_spin.setValue(30)
        self.window_length_spin.setSingleStep(5)
        wl_layout.addWidget(self.window_length_spin)
        layout.addLayout(wl_layout)
        
        # Overlap
        ov_layout = QHBoxLayout()
        ov_layout.addWidget(QLabel("Overlap (%):"))
        self.overlap_spin = QSpinBox()
        self.overlap_spin.setRange(0, 90)
        self.overlap_spin.setValue(50)
        self.overlap_spin.setSingleStep(10)
        ov_layout.addWidget(self.overlap_spin)
        layout.addLayout(ov_layout)
        
        # Smoothing bandwidth
        sb_layout = QHBoxLayout()
        sb_layout.addWidget(QLabel("Konno-Ohmachi (b):"))
        self.smoothing_spin = QDoubleSpinBox()
        self.smoothing_spin.setRange(10, 100)
        self.smoothing_spin.setValue(40)
        self.smoothing_spin.setSingleStep(5)
        self.smoothing_spin.setToolTip("Konno-Ohmachi smoothing bandwidth parameter (b)\n"
                                       "Higher values = more smoothing\n"
                                       "Standard: b=40 (recommended)")
        sb_layout.addWidget(self.smoothing_spin)
        layout.addLayout(sb_layout)
        
        # === FREQUENCY RANGE SECTION ===
        freq_label = QLabel("<b>Frequency Range (HVSR Computation):</b>")
        layout.addWidget(freq_label)
        
        # Min frequency
        fmin_layout = QHBoxLayout()
        fmin_layout.addWidget(QLabel("Min Freq (Hz):"))
        self.freq_min_spin = QDoubleSpinBox()
        self.freq_min_spin.setRange(0.1, 100.0)
        self.freq_min_spin.setValue(0.2)
        self.freq_min_spin.setDecimals(2)
        self.freq_min_spin.setSingleStep(0.1)
        self.freq_min_spin.setToolTip("Minimum frequency for HVSR computation")
        fmin_layout.addWidget(self.freq_min_spin)
        layout.addLayout(fmin_layout)
        
        # Max frequency
        fmax_layout = QHBoxLayout()
        fmax_layout.addWidget(QLabel("Max Freq (Hz):"))
        self.freq_max_spin = QDoubleSpinBox()
        self.freq_max_spin.setRange(0.1, 100.0)
        self.freq_max_spin.setValue(20.0)
        self.freq_max_spin.setDecimals(1)
        self.freq_max_spin.setSingleStep(1.0)
        self.freq_max_spin.setToolTip("Maximum frequency for HVSR computation")
        fmax_layout.addWidget(self.freq_max_spin)
        layout.addLayout(fmax_layout)
        
        # Number of frequency points
        nfreq_layout = QHBoxLayout()
        nfreq_layout.addWidget(QLabel("Freq Points:"))
        self.n_freq_spin = QSpinBox()
        self.n_freq_spin.setRange(50, 500)
        self.n_freq_spin.setValue(100)
        self.n_freq_spin.setSingleStep(10)
        self.n_freq_spin.setToolTip("Number of frequency points (log-spaced)")
        nfreq_layout.addWidget(self.n_freq_spin)
        layout.addLayout(nfreq_layout)

        # === SAMPLING RATE OVERRIDE SECTION ===
        sampling_label = QLabel("<b>Sampling Rate Override:</b>")
        layout.addWidget(sampling_label)

        # Override checkbox
        self.override_sampling_check = QCheckBox("Override Sampling Rate")
        self.override_sampling_check.setChecked(False)
        self.override_sampling_check.setToolTip("Manually specify sampling rate instead of auto-detection")
        self.override_sampling_check.toggled.connect(self._on_override_sampling_toggled)
        layout.addWidget(self.override_sampling_check)

        # Manual sampling rate input
        sampling_layout = QHBoxLayout()
        sampling_layout.addWidget(QLabel("Sampling Rate (Hz):"))
        self.sampling_rate_spin = QDoubleSpinBox()
        self.sampling_rate_spin.setRange(0.1, 10000.0)
        self.sampling_rate_spin.setValue(100.0)
        self.sampling_rate_spin.setDecimals(4)
        self.sampling_rate_spin.setSingleStep(0.1)
        self.sampling_rate_spin.setEnabled(False)  # Disabled by default
        self.sampling_rate_spin.setToolTip("Manual sampling rate (Hz)")
        sampling_layout.addWidget(self.sampling_rate_spin)
        layout.addLayout(sampling_layout)

        # === WINDOW REJECTION SECTION ===
        rejection_label = QLabel("<b>Window Rejection:</b>")
        layout.addWidget(rejection_label)

        # Quality Control (QC) group with Preset/Custom modes
        qc_group = QGroupBox("Quality Control Settings")
        qc_group_layout = QVBoxLayout(qc_group)

        # Top row: Enable checkbox
        self.qc_enable_check = QCheckBox("Enable QC Rejection")
        self.qc_enable_check.setChecked(True)
        self.qc_enable_check.setToolTip("Apply quality control to reject noisy windows")
        self.qc_enable_check.toggled.connect(self._on_qc_enable_toggled)
        qc_group_layout.addWidget(self.qc_enable_check)

        # Mode selector: Preset vs Custom
        from PyQt5.QtWidgets import QRadioButton, QButtonGroup, QFrame
        mode_frame = QFrame()
        mode_layout = QHBoxLayout(mode_frame)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        
        self.qc_mode_group = QButtonGroup()
        self.preset_radio = QRadioButton("Preset")
        self.preset_radio.setChecked(True)
        self.custom_radio = QRadioButton("Custom")
        self.qc_mode_group.addButton(self.preset_radio, 0)
        self.qc_mode_group.addButton(self.custom_radio, 1)
        
        mode_layout.addWidget(QLabel("Mode:"))
        mode_layout.addWidget(self.preset_radio)
        mode_layout.addWidget(self.custom_radio)
        mode_layout.addStretch()
        qc_group_layout.addWidget(mode_frame)
        
        self.preset_radio.toggled.connect(self._on_qc_mode_changed)
        self.custom_radio.toggled.connect(self._on_qc_mode_changed)

        # === PRESET MODE WIDGETS ===
        self.preset_widget = QWidget()
        preset_layout = QVBoxLayout(self.preset_widget)
        preset_layout.setContentsMargins(0, 5, 0, 0)
        
        preset_combo_layout = QHBoxLayout()
        preset_combo_layout.addWidget(QLabel("Preset:"))
        self.qc_combo = QComboBox()
        self.qc_combo.addItem("Conservative - Only obvious problems", "conservative")
        self.qc_combo.addItem("Balanced - Moderate QC (recommended)", "balanced")
        self.qc_combo.addItem("Aggressive - Strict quality control", "aggressive")
        self.qc_combo.addItem("SESAME - SESAME-compliant", "sesame")
        self.qc_combo.addItem("Publication - 4-condition rejection", "publication")
        self.qc_combo.setCurrentIndex(1)  # Default to balanced
        self.qc_combo.setToolTip(
            "Conservative: Amplitude + quality threshold (lenient)\n"
            "Balanced: Amplitude check only (recommended for most data)\n"
            "Aggressive: + STA/LTA + frequency + statistical checks\n"
            "SESAME: Pre-HVSR QC + Cox FDWRA for peak consistency\n"
            "Publication: HVSR amplitude, peak consistency, flat peak detection"
        )
        preset_combo_layout.addWidget(self.qc_combo)
        preset_layout.addLayout(preset_combo_layout)
        
        # Preset description label
        self.preset_desc_label = QLabel()
        self.preset_desc_label.setWordWrap(True)
        self.preset_desc_label.setStyleSheet("color: #666; font-style: italic; padding: 3px;")
        self._update_preset_description()
        self.qc_combo.currentIndexChanged.connect(self._update_preset_description)
        preset_layout.addWidget(self.preset_desc_label)
        
        qc_group_layout.addWidget(self.preset_widget)

        # === CUSTOM MODE WIDGETS ===
        self.custom_widget = QWidget()
        custom_layout = QVBoxLayout(self.custom_widget)
        custom_layout.setContentsMargins(0, 5, 0, 0)
        
        # Pre-HVSR algorithms section
        pre_hvsr_label = QLabel("<i>Time-Domain (Pre-HVSR):</i>")
        custom_layout.addWidget(pre_hvsr_label)
        
        # Checkboxes for each algorithm
        self.custom_amplitude_check = QCheckBox("Amplitude Rejection")
        self.custom_amplitude_check.setChecked(True)
        self.custom_amplitude_check.setToolTip("Reject clipping, dead channels, extreme amplitudes")
        custom_layout.addWidget(self.custom_amplitude_check)
        
        self.custom_quality_check = QCheckBox("Quality Threshold")
        self.custom_quality_check.setToolTip("Reject windows below SNR/stationarity threshold")
        custom_layout.addWidget(self.custom_quality_check)
        
        self.custom_stalta_check = QCheckBox("STA/LTA Rejection")
        self.custom_stalta_check.setToolTip("Reject transients using short/long-term average ratio")
        custom_layout.addWidget(self.custom_stalta_check)
        
        self.custom_freq_check = QCheckBox("Frequency Domain")
        self.custom_freq_check.setToolTip("Reject windows with spectral spikes")
        custom_layout.addWidget(self.custom_freq_check)
        
        self.custom_stats_check = QCheckBox("Statistical Outliers")
        self.custom_stats_check.setToolTip("Reject windows that are statistical outliers")
        custom_layout.addWidget(self.custom_stats_check)
        
        # Post-HVSR algorithms section
        post_hvsr_label = QLabel("<i>Frequency-Domain (Post-HVSR):</i>")
        custom_layout.addWidget(post_hvsr_label)
        
        self.custom_hvsr_amp_check = QCheckBox("HVSR Peak Amplitude < 1")
        self.custom_hvsr_amp_check.setToolTip("Reject windows where HVSR peak amplitude < 1.0")
        custom_layout.addWidget(self.custom_hvsr_amp_check)
        
        self.custom_flat_peak_check = QCheckBox("Flat Peak Detection")
        self.custom_flat_peak_check.setToolTip("Reject windows with flat/wide peaks or multiple peaks")
        custom_layout.addWidget(self.custom_flat_peak_check)
        
        self.custom_cox_fdwra_check = QCheckBox("Cox FDWRA (Peak Consistency)")
        self.custom_cox_fdwra_check.setToolTip("Cox et al. (2020) Frequency-Domain Window Rejection\nEnsures peak frequency consistency across windows")
        custom_layout.addWidget(self.custom_cox_fdwra_check)
        
        # Advanced settings button for custom mode
        self.advanced_qc_btn = QPushButton("Advanced Settings...")
        self.advanced_qc_btn.clicked.connect(self.open_advanced_qc_settings)
        self.advanced_qc_btn.setToolTip("Fine-tune individual algorithm thresholds")
        custom_layout.addWidget(self.advanced_qc_btn)
        
        qc_group_layout.addWidget(self.custom_widget)
        self.custom_widget.hide()  # Hidden by default (preset mode active)

        layout.addWidget(qc_group)

        # Cox FDWRA group (Frequency-Domain)
        cox_group = QGroupBox("Cox FDWRA (Frequency-Domain)")
        cox_group_layout = QVBoxLayout(cox_group)

        # Cox Enable checkbox
        self.cox_fdwra_check = QCheckBox("Enable Cox FDWRA")
        self.cox_fdwra_check.setChecked(False)
        self.cox_fdwra_check.setToolTip(
            "Apply Cox et al. (2020) Frequency-Domain Window Rejection\n"
            "after HVSR computation to ensure peak frequency consistency.\n"
            "Industry-standard for publication-quality HVSR analysis."
        )
        self.cox_fdwra_check.toggled.connect(self._on_cox_enable_toggled)
        cox_group_layout.addWidget(self.cox_fdwra_check)

        # Cox parameters
        from PyQt5.QtWidgets import QGridLayout
        cox_params_layout = QGridLayout()
        cox_params_layout.setColumnStretch(1, 1)

        cox_params_layout.addWidget(QLabel("n-value:"), 0, 0)
        self.cox_n_spin = QDoubleSpinBox()
        self.cox_n_spin.setRange(0.5, 10.0)
        self.cox_n_spin.setValue(2.0)
        self.cox_n_spin.setDecimals(1)
        self.cox_n_spin.setSingleStep(0.5)
        self.cox_n_spin.setEnabled(False)
        self.cox_n_spin.setToolTip("Standard deviation multiplier (lower = stricter rejection)")
        cox_params_layout.addWidget(self.cox_n_spin, 0, 1)

        cox_params_layout.addWidget(QLabel("Max Iter:"), 1, 0)
        self.cox_iterations_spin = QSpinBox()
        self.cox_iterations_spin.setRange(1, 50)
        self.cox_iterations_spin.setValue(20)
        self.cox_iterations_spin.setEnabled(False)
        self.cox_iterations_spin.setToolTip("Maximum iterations for convergence")
        cox_params_layout.addWidget(self.cox_iterations_spin, 1, 1)

        cox_params_layout.addWidget(QLabel("Min Iter:"), 2, 0)
        self.cox_min_iterations_spin = QSpinBox()
        self.cox_min_iterations_spin.setRange(1, 20)
        self.cox_min_iterations_spin.setValue(1)
        self.cox_min_iterations_spin.setEnabled(False)
        self.cox_min_iterations_spin.setToolTip(
            "Minimum iterations before checking convergence.\n"
            "Set higher to force more rejection passes even if convergence is reached early."
        )
        cox_params_layout.addWidget(self.cox_min_iterations_spin, 2, 1)

        cox_params_layout.addWidget(QLabel("Distribution:"), 3, 0)
        self.cox_dist_combo = QComboBox()
        self.cox_dist_combo.addItems(["lognormal", "normal"])
        self.cox_dist_combo.setEnabled(False)
        self.cox_dist_combo.setToolTip("Statistical distribution for peak modeling")
        cox_params_layout.addWidget(self.cox_dist_combo, 3, 1)

        cox_group_layout.addLayout(cox_params_layout)
        layout.addWidget(cox_group)
        
        # Parallel processing checkbox
        self.parallel_check = QCheckBox("Enable parallel processing (faster)")
        self.parallel_check.setChecked(True)  # Enabled by default
        cpu_count = self._get_cpu_count()
        self.parallel_check.setToolTip("Use multiple CPU cores for faster HVSR computation.\n"
                                      "Recommended for datasets with >100 windows.\n"
                                      f"Your system has {cpu_count} CPU cores.\n"
                                      "Speed improvement: ~1.5-3x faster for large datasets.")
        self.parallel_check.stateChanged.connect(self._on_parallel_toggled)
        layout.addWidget(self.parallel_check)

        # CPU core count selector
        cores_layout = QHBoxLayout()
        cores_layout.addWidget(QLabel("   Number of cores to use:"))

        self.cores_spin = QSpinBox()
        self.cores_spin.setRange(1, max(1, cpu_count))
        self.cores_spin.setValue(max(1, cpu_count - 1))  # Default: leave one core free
        self.cores_spin.setToolTip(f"Select number of CPU cores to use (1-{cpu_count}).\n"
                                   "Using all cores may make your system unresponsive.\n"
                                   "Recommended: Leave at least 1 core free for system tasks.")
        cores_layout.addWidget(self.cores_spin)
        cores_layout.addStretch()

        layout.addLayout(cores_layout)

        # Process button - prominent and bold
        self.process_btn = QPushButton("Process HVSR")
        self.process_btn.clicked.connect(self.process_hvsr)
        self.process_btn.setEnabled(False)
        self.process_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                font-size: 14px;
                padding: 12px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
                color: #757575;
            }
        """)
        layout.addWidget(self.process_btn)
        
        group.setLayout(layout)
        return group
    
    def create_window_group(self) -> QGroupBox:
        """Create window management group."""
        group = QGroupBox("Window Management")
        layout = QVBoxLayout()
        
        # Window info
        self.window_info_label = QLabel("No windows")
        layout.addWidget(self.window_info_label)
        
        # Toggle buttons
        btn_layout = QHBoxLayout()
        
        self.reject_all_btn = QPushButton("Reject All")
        self.reject_all_btn.clicked.connect(self.reject_all_windows)
        self.reject_all_btn.setEnabled(False)
        btn_layout.addWidget(self.reject_all_btn)
        
        self.accept_all_btn = QPushButton("Accept All")
        self.accept_all_btn.clicked.connect(self.accept_all_windows)
        self.accept_all_btn.setEnabled(False)
        btn_layout.addWidget(self.accept_all_btn)
        
        layout.addLayout(btn_layout)
        
        # Recompute button
        self.recompute_btn = QPushButton("Recompute HVSR")
        self.recompute_btn.clicked.connect(self.recompute_hvsr)
        self.recompute_btn.setEnabled(False)
        layout.addWidget(self.recompute_btn)
        
        group.setLayout(layout)
        return group
    
    def create_actions_group(self) -> QGroupBox:
        """Create actions group."""
        group = QGroupBox("Actions")
        layout = QVBoxLayout()
        
        # Export Plot as Image button (NEW - HIGH PRIORITY)
        export_plot_btn = QPushButton("Export Plot as Image")
        export_plot_btn.clicked.connect(self.export_plot_image)
        export_plot_btn.setEnabled(False)
        export_plot_btn.setStyleSheet("font-weight: bold; background-color: #2196F3; color: white; padding: 6px;")
        export_plot_btn.setToolTip("Save current plot view as PNG/PDF (high DPI)")
        self.export_plot_btn = export_plot_btn
        layout.addWidget(export_plot_btn)
        
        # Generate Report Plots button
        report_btn = QPushButton("Generate Report Plots")
        report_btn.clicked.connect(self.generate_report_plots)
        report_btn.setEnabled(False)
        report_btn.setStyleSheet("font-weight: bold; background-color: #4CAF50; color: white; padding: 6px;")
        self.report_btn = report_btn
        layout.addWidget(report_btn)
        
        # Export button
        export_btn = QPushButton("Export Results (CSV/JSON)")
        export_btn.clicked.connect(self.export_results)
        export_btn.setEnabled(False)
        self.export_btn = export_btn
        layout.addWidget(export_btn)
        
        # Save session
        save_btn = QPushButton("Save Session")
        save_btn.clicked.connect(self.save_session)
        save_btn.setEnabled(False)
        self.save_btn = save_btn
        layout.addWidget(save_btn)
        
        # Load session
        load_session_btn = QPushButton("Load Session")
        load_session_btn.clicked.connect(self.load_session)
        layout.addWidget(load_session_btn)
        
        group.setLayout(layout)
        return group
    
    def connect_signals(self):
        """Connect signals and slots."""
        # Canvas signals (old compatibility)
        self.canvas.window_toggled.connect(self.on_window_toggled)
        self.canvas.status_message.connect(self.status_bar.showMessage)
    
    def toggle_plot_window(self):
        """Toggle between separate and embedded plot modes."""
        if self.plot_manager.mode == 'separate':
            self.plot_manager.show_separate()
            self.plot_mode_button.setText("Dock Plot")
        else:
            self.plot_manager.show_embedded()
            self.plot_mode_button.setText("Show Plot")

    def toggle_preview_canvas(self, checked):
        """
        Toggle preview canvas visibility.

        Args:
            checked: True to show, False to hide
        """
        if hasattr(self, 'data_load_tab'):
            self.data_load_tab.preview_canvas.setVisible(checked)

    def toggle_loaded_data_column(self, checked):
        """
        Toggle loaded data column visibility.

        Args:
            checked: True to show, False to hide
        """
        if hasattr(self, 'data_load_tab'):
            self.data_load_tab.set_loaded_list_visible(checked)

    def toggle_azimuthal_tab(self, checked):
        """
        Toggle azimuthal tab visibility.

        Args:
            checked: True to show, False to hide
        """
        if hasattr(self, 'azimuthal_tab'):
            # Find the tab index
            for i in range(self.mode_tabs.count()):
                if self.mode_tabs.widget(i) == self.azimuthal_tab:
                    if checked:
                        self.mode_tabs.setTabVisible(i, True)
                    else:
                        self.mode_tabs.setTabVisible(i, False)
                        # If currently on azimuthal tab, switch to processing
                        if self.mode_tabs.currentIndex() == i:
                            self.mode_tabs.setCurrentIndex(1)
                    break
    
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

    def _on_override_sampling_toggled(self, checked: bool):
        """Handle sampling rate override checkbox toggle."""
        self.sampling_rate_spin.setEnabled(checked)
        if checked:
            self.add_info("Sampling rate override enabled")
        else:
            self.add_info("Using auto-detected sampling rate")

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
        """Handle files selected from DataInputDialog."""
        mode = result['mode']
        files = result['files']
        groups = result['groups']
        options = result['options']
        time_range = result.get('time_range')  # May be None

        # Store load mode and time range
        self.load_mode = mode
        self.current_time_range = time_range

        # Log time range if enabled
        if time_range and time_range.get('enabled'):
            start = time_range['start']
            end = time_range['end']
            tz_name = time_range.get('timezone_name', 'UTC')
            self.add_info(f"Time range selected: {start.strftime('%Y-%m-%d %H:%M')} to {end.strftime('%H:%M')} ({tz_name})")

        # Load data and add to Data Load tab
        try:
            handler = HVSRDataHandler()

            if mode == 'single':
                # Single file mode
                file_path = files[0]
                self.add_info(f"Loading: {Path(file_path).name}...")

                data = handler.load_data(file_path)

                # Get file metadata
                file_size = Path(file_path).stat().st_size / (1024 * 1024)  # MB
                metadata = {
                    'duration': data.duration,
                    'sampling_rate': data.east.sampling_rate,
                    'size_mb': file_size,
                    'status': 'loaded'
                }

                # Convert time_range to seconds if provided
                tr_seconds = None
                if time_range and time_range.get('enabled'):
                    start_dt = time_range['start']
                    end_dt = time_range['end']
                    # Calculate duration in seconds
                    duration_seconds = (end_dt - start_dt).total_seconds()
                    tr_seconds = {'start': 0.0, 'end': duration_seconds}

                # Add to data load tab
                self.data_load_tab.add_loaded_file(file_path, data, metadata, tr_seconds)
                
                # Update preview canvas time filter if time range was specified
                if time_range and time_range.get('enabled'):
                    self._apply_time_range_to_preview(time_range, data)

                # Store for processing
                self.current_file = file_path
                self.process_btn.setEnabled(True)
                self.add_info(f"Loaded: {Path(file_path).name}")

            elif mode == 'multi_type1':
                # Multiple files with E,N,Z in each
                self.add_info(f"Loading {len(files)} MiniSEED files...")

                # Extract channel mapping from options if provided
                channel_mapping = options.get('channel_mapping', None)
                if channel_mapping:
                    self.add_info(f"Using channel mapping: {channel_mapping}")
                    data = handler.load_multi_miniseed_type1(files, channel_mapping=channel_mapping)
                else:
                    data = handler.load_multi_miniseed_type1(files)

                # Convert time_range to seconds if provided
                tr_seconds = None
                if time_range and time_range.get('enabled'):
                    start_dt = time_range['start']
                    end_dt = time_range['end']
                    duration_seconds = (end_dt - start_dt).total_seconds()
                    tr_seconds = {'start': 0.0, 'end': duration_seconds}

                # Add each file individually to the list
                for file_path in files:
                    file_size = Path(file_path).stat().st_size / (1024 * 1024)
                    # Estimate duration per file (approximate)
                    file_duration = data.duration / len(files)
                    metadata = {
                        'duration': file_duration,
                        'sampling_rate': data.east.sampling_rate,
                        'size_mb': file_size,
                        'status': 'loaded'
                    }
                    self.data_load_tab.add_loaded_file(file_path, data, metadata, tr_seconds)
                
                # Update preview canvas time filter if time range was specified
                if time_range and time_range.get('enabled'):
                    self._apply_time_range_to_preview(time_range, data)

                # Store for processing
                self.current_file = files
                self.process_btn.setEnabled(True)
                self.add_info(f"Loaded {len(files)} files (merged chronologically)")

            elif mode == 'multi_type2':
                # Separate E, N, Z files
                complete = sum(1 for g in groups.values() if 'E' in g and 'N' in g and 'Z' in g)
                self.add_info(f"Loading {complete} file groups...")
                data = handler.load_multi_miniseed_type2(groups)

                # Convert time_range to seconds if provided
                tr_seconds = None
                if time_range and time_range.get('enabled'):
                    start_dt = time_range['start']
                    end_dt = time_range['end']
                    duration_seconds = (end_dt - start_dt).total_seconds()
                    tr_seconds = {'start': 0.0, 'end': duration_seconds}

                # Add each file group to the list
                file_duration_per_group = data.duration / complete if complete > 0 else data.duration
                for group_name, group_files in groups.items():
                    if all(c in group_files for c in ['E', 'N', 'Z']):
                        # Calculate size for this group
                        group_size = sum(Path(str(f)).stat().st_size for f in group_files.values()) / (1024 * 1024)

                        # Use group name as display name
                        display_name = f"{group_name} (E/N/Z)"
                        metadata = {
                            'duration': file_duration_per_group,
                            'sampling_rate': data.east.sampling_rate,
                            'size_mb': group_size,
                            'status': 'loaded'
                        }
                        self.data_load_tab.add_loaded_file(display_name, data, metadata, tr_seconds)
                
                # Update preview canvas time filter if time range was specified
                if time_range and time_range.get('enabled'):
                    self._apply_time_range_to_preview(time_range, data)

                # Store for processing
                self.current_file = groups
                self.process_btn.setEnabled(True)
                self.add_info(f"Loaded {complete} groups (3-component streams)")

            # Update collapsible data panels in Processing and Azimuthal tabs
            if hasattr(self, 'processing_data_panel'):
                self.processing_data_panel.update_from_data_load_tab(self.data_load_tab)
            if hasattr(self, 'azimuthal_tab') and hasattr(self.azimuthal_tab, 'data_panel'):
                self.azimuthal_tab.data_panel.update_from_data_load_tab(self.data_load_tab)

        except Exception as e:
            import traceback
            error_msg = f"Failed to load data: {str(e)}\n{traceback.format_exc()}"
            QMessageBox.critical(self, "Load Error", error_msg)
            self.add_info(f"ERROR: {str(e)}")
    
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
    
    def process_hvsr(self):
        """Start HVSR processing in background thread."""
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
        self.progress_bar.setValue(value)
        self.status_bar.showMessage(message)
        self.add_info(message)
    
    def on_processing_finished(self, result, windows, data):
        """Handle processing completion."""
        # CRITICAL: Validate results before attempting to use them
        is_valid, error_msg = self._validate_processing_results(result, windows)

        if not is_valid:
            # Show QC failure dialog with diagnostic information
            self._show_qc_failure_dialog(windows, error_msg)

            # Re-enable controls
            self.progress_bar.setVisible(False)
            self.process_btn.setEnabled(True)
            return  # Don't proceed with plotting

        self.hvsr_result = result
        self.windows = windows
        self.data = data
        
        # Update UI
        self.progress_bar.setVisible(False)
        self.process_btn.setEnabled(True)
        
        # Enable action buttons if they exist (may be in Export dock instead)
        if hasattr(self, 'export_plot_btn'):
            self.export_plot_btn.setEnabled(True)
        if hasattr(self, 'report_btn'):
            self.report_btn.setEnabled(True)
        if hasattr(self, 'export_btn'):
            self.export_btn.setEnabled(True)
        if hasattr(self, 'save_btn'):
            self.save_btn.setEnabled(True)
        
        self.reject_all_btn.setEnabled(True)
        self.accept_all_btn.setEnabled(True)
        self.recompute_btn.setEnabled(True)
        
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

        # === NEW: Plot in separate window ===
        self.plot_results_separate_window(result, windows, data)
        
        # Add info
        self.add_info(f"Processing complete!")
        self.add_info(f"   Windows: {windows.n_active}/{windows.n_windows}")
        if result.primary_peak:
            self.add_info(f"   Primary peak: f0 = {result.primary_peak.frequency:.2f} Hz")
        
        self.status_bar.showMessage("Ready - Use layer dock to toggle visibility")
    
    def plot_results_separate_window(self, result, windows, data):
        """Plot results in separate plot window."""
        # Check if this is a QC failure result
        if hasattr(result, 'metadata') and result.metadata.get('qc_failure', False):
            # Don't try to plot QC failure results in separate window
            # The interactive canvas will show the error message
            return
        
        # Recreate axes with current visibility settings
        self.plot_manager._create_axes()
        
        # Get axes from plot manager (some may be None if hidden)
        ax_timeline, ax_hvsr, ax_stats = self.plot_manager.get_axes()
        
        # Plot timeline (if visible)
        if ax_timeline is not None:
            ax_timeline.clear()
            ax_timeline.set_title('Window Timeline (Click to Toggle State)')
            ax_timeline.set_xlabel('Time (s)')
            ax_timeline.set_ylabel('Window')
            
            # Simple timeline visualization
            for i, window in enumerate(windows.windows):
                color = 'green' if window.is_active() else 'gray'
                ax_timeline.barh(i, window.duration, left=window.start_time, 
                               height=0.8, color=color, alpha=0.7)
            
            ax_timeline.set_ylim(-1, len(windows.windows))
            ax_timeline.invert_yaxis()
        
        # Plot HVSR curves - Individual Windows Mode
        self.window_lines = {}
        color_palette = self._get_color_palette()
        
        print(f"\n=== DEBUG: Plotting Window Lines ===")
        print(f"Total windows: {len(windows.windows)}")
        print(f"Window spectra available: {len(result.window_spectra)}")
        
        # Extract individual window HVSR from result
        # IMPORTANT: Plot ALL windows (active AND rejected) so layers panel can manage them
        for i, window in enumerate(windows.windows):
            if i < len(result.window_spectra):
                # Use gray color for rejected windows, normal color for active
                if window.is_active():
                    color = color_palette[i % len(color_palette)]
                    alpha = 0.5
                else:
                    color = 'gray'
                    alpha = 0.3  # More transparent for rejected
                
                # Get this window's HVSR curve
                window_spectrum = result.window_spectra[i]
                window_hvsr = window_spectrum.hvsr
                
                # Plot individual window curve
                # visibility controlled by window.visible (layer panel manages this)
                line, = ax_hvsr.plot(result.frequencies, window_hvsr,
                                    color=color, linewidth=0.8, alpha=alpha,
                                    visible=window.is_active() and window.visible,
                                    label=f'W{i+1}' if i < 5 else '')
                self.window_lines[i] = line
                
                if i < 3:  # Log first 3 windows
                    print(f"  Window {i}: active={window.is_active()}, visible={window.visible}, plotted={line is not None}")
        
        print(f"Total window_lines created: {len(self.window_lines)}")
        print(f"=================================\n")
        
        # Plot mean and std
        mean_line, = ax_hvsr.plot(result.frequencies, result.mean_hvsr,
                                 'k-', linewidth=2.5, label='Mean', zorder=100)
        
        std_plus, = ax_hvsr.plot(result.frequencies, 
                                result.mean_hvsr + result.std_hvsr,
                                'k--', linewidth=1.5, label='+1σ', zorder=99)
        
        std_minus, = ax_hvsr.plot(result.frequencies,
                                 result.mean_hvsr - result.std_hvsr,
                                 'k--', linewidth=1.5, label='-1σ', zorder=99)
        
        self.stat_lines = {
            'mean': mean_line,
            'std_plus': std_plus,
            'std_minus': std_minus
        }
        
        ax_hvsr.set_xscale('log')
        ax_hvsr.set_xlabel('Frequency (Hz)')
        ax_hvsr.set_ylabel('H/V Ratio')
        ax_hvsr.set_title('HVSR Curve - Individual Windows Mode')
        ax_hvsr.grid(True, which='both', alpha=0.3)
        ax_hvsr.legend(loc='upper right', fontsize=8)
        
        # Plot quality statistics (if visible)
        if ax_stats is not None:
            ax_stats.clear()
            ax_stats.set_title('Window Quality Statistics')
            ax_stats.set_xlabel('Window Index')
            ax_stats.set_ylabel('Quality Score')
            
            qualities = [w.quality_metrics.get('overall', 0.0) for w in windows.windows]
            colors = ['green' if w.is_active() else 'gray' for w in windows.windows]
            ax_stats.scatter(range(len(windows.windows)), qualities, 
                            c=colors, alpha=0.7, s=50)
            ax_stats.axhline(0.5, color='red', linestyle='--', alpha=0.5, label='Threshold')
            ax_stats.legend()
            ax_stats.grid(True, alpha=0.3)
        
        # Adjust layout
        self.plot_manager.fig.tight_layout()
        self.plot_manager.canvas.draw()
        
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
        
        # Replot with current settings
        self.plot_results_separate_window(self.hvsr_result, self.windows, self.data)
        
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
        """
        if not self.hvsr_result or not self.windows or not self.stat_lines:
            return
        
        # Collect visible window HVSR curves
        visible_hvsr_curves = []
        
        for i, window in enumerate(self.windows.windows):
            # Include if: state==ACTIVE AND visible==True
            if window.should_include_in_hvsr() and i < len(self.hvsr_result.window_spectra):
                window_spectrum = self.hvsr_result.window_spectra[i]
                visible_hvsr_curves.append(window_spectrum.hvsr)
        
        if not visible_hvsr_curves:
            # No visible windows - hide mean lines
            for line in self.stat_lines.values():
                line.set_visible(False)
            self.plot_manager.fig.canvas.draw_idle()
            self.add_info("WARNING: No visible windows - mean hidden")
            return
        
        # Compute new mean and std from visible curves
        visible_hvsr_array = np.array(visible_hvsr_curves)
        new_mean = np.mean(visible_hvsr_array, axis=0)
        new_std = np.std(visible_hvsr_array, axis=0)
        
        # Update mean line
        if 'mean' in self.stat_lines:
            self.stat_lines['mean'].set_ydata(new_mean)
        
        # Update +1σ line
        if 'std_plus' in self.stat_lines:
            self.stat_lines['std_plus'].set_ydata(new_mean + new_std)
        
        # Update -1σ line
        if 'std_minus' in self.stat_lines:
            self.stat_lines['std_minus'].set_ydata(new_mean - new_std)
        
        # Redraw canvas
        self.plot_manager.fig.canvas.draw_idle()
        
        # Log update
        n_visible = len(visible_hvsr_curves)
        self.add_info(f"Mean recalculated from {n_visible} visible windows")

    def _validate_processing_results(self, result, windows):
        """
        Validate HVSR processing results before plotting.

        Returns:
            tuple: (is_valid: bool, error_message: str)
        """
        # Check 1: Any windows passed QC?
        if windows.n_active == 0:
            return False, f"No windows passed QC (0/{windows.n_windows} rejected)"

        # Check 2: Valid frequency data?
        if result is None or len(result.frequencies) == 0:
            return False, "No frequency data generated"

        # Check 3: Valid HVSR values?
        if result.mean_hvsr is None:
            return False, "HVSR computation failed - no mean values"

        if np.all(np.isnan(result.mean_hvsr)):
            return False, "All HVSR values are NaN"

        # All checks passed
        return True, "OK"

    def _show_qc_failure_dialog(self, windows, error_msg):
        """
        Show detailed QC failure dialog with diagnostic information.

        Args:
            windows: WindowCollection object
            error_msg: Primary error message
        """
        # Generate QC diagnostic report
        report = self._generate_qc_diagnostic_report(windows)

        # Create detailed message
        message = f"<h3>QC Failure: Cannot Process Data</h3>"
        message += f"<p><b>Error:</b> {error_msg}</p>"
        message += f"<hr>"
        message += f"<h4>QC Diagnostic Report:</h4>"
        message += f"<pre>{report}</pre>"
        message += f"<hr>"
        message += f"<h4>Suggested Solutions:</h4>"
        message += f"<ul>"
        message += f"<li>Click <b>⚙️ Advanced QC Settings</b> and:"
        message += f"<ul>"
        message += f"<li>UNCHECK 'Enable Quality Control' to bypass QC entirely</li>"
        message += f"<li>OR adjust individual algorithm thresholds</li>"
        message += f"</ul>"
        message += f"</li>"
        message += f"<li>Check your input data quality</li>"
        message += f"<li>Try different QC modes (Conservative, Balanced, Aggressive)</li>"
        message += f"<li>Verify sampling rate is correct</li>"
        message += f"</ul>"

        # Show message box
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("QC Failure")
        msg_box.setTextFormat(Qt.RichText)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()

        # Log to info panel
        self.add_info("=" * 60)
        self.add_info("QC FAILURE - No windows passed quality control")
        self.add_info("=" * 60)
        self.add_info(report)
        self.add_info("=" * 60)

    def _generate_qc_diagnostic_report(self, windows):
        """
        Generate diagnostic report showing why windows failed QC.

        Args:
            windows: WindowCollection object

        Returns:
            str: Formatted diagnostic report
        """
        total = windows.n_windows
        active = windows.n_active
        rejected = windows.n_rejected

        report = f"Total Windows: {total}\n"
        report += f"Passed: {active} ({active/total*100:.1f}%)\n"
        report += f"Failed: {rejected} ({rejected/total*100:.1f}%)\n"
        report += f"\n"

        # Analyze rejection reasons
        rejection_reasons = {}
        for window in windows.windows:
            if not window.is_active():
                reason = window.rejection_reason if window.rejection_reason else "Unknown"
                rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1

        if rejection_reasons:
            report += f"Failure Breakdown:\n"
            report += f"{'-' * 40}\n"
            for reason, count in sorted(rejection_reasons.items(), key=lambda x: -x[1]):
                pct = count / total * 100
                report += f"{reason}: {count} ({pct:.1f}%)\n"
        else:
            report += f"No rejection reason data available\n"

        report += f"\n"
        report += f"Recommendations:\n"
        if rejected == total:
            report += f"  • ALL windows failed - QC may be too strict\n"
            report += f"  • Consider disabling QC entirely for diagnosis\n"
            report += f"  • Check if data has unusual characteristics\n"
        elif rejected > total * 0.9:
            report += f"  • >90% rejection rate - QC very strict\n"
            report += f"  • Try relaxing QC thresholds\n"
            report += f"  • Review individual algorithm settings\n"

        report += f"  • Use Advanced QC Settings to customize\n"
        report += f"  • Verify data quality and sensor response\n"

        return report

    def on_processing_error(self, error_msg: str):
        """Handle processing error."""
        self.progress_bar.setVisible(False)
        self.process_btn.setEnabled(True)
        QMessageBox.critical(self, "Processing Error", error_msg)
        self.add_info(f"ERROR: {error_msg}")
    
    def on_window_toggled(self, window_index: int):
        """Handle window toggle event from canvas."""
        if self.windows is None:
            return
        
        window = self.windows.get_window(window_index)
        if window is None:
            return
        
        # Toggle state
        if window.is_active():
            window.reject("Manual rejection", manual=True)
            self.add_info(f"Rejected window {window_index}")
        else:
            window.activate()
            self.add_info(f"Activated window {window_index}")
        
        # Update info
        self.update_window_info()
        
        # Refresh canvas
        self.canvas.update_window_states()
    
    def reject_all_windows(self):
        """Reject all windows."""
        if self.windows is None:
            return
        
        for window in self.windows.windows:
            if window.is_active():
                window.reject("Batch rejection", manual=True)
        
        self.update_window_info()
        self.canvas.update_window_states()
        self.add_info("Rejected all windows")
    
    def accept_all_windows(self):
        """Accept all windows."""
        if self.windows is None:
            return
        
        for window in self.windows.windows:
            if window.is_rejected():
                window.activate()
        
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
        """Open advanced export dialog for comprehensive visualizations."""
        if self.hvsr_result is None:
            QMessageBox.warning(self, "No Results", "No results to export.")
            return
        
        from hvsr_pro.gui.dialogs import ExportDialog
        
        dialog = ExportDialog(self, self.hvsr_result, self.windows, self.data)
        dialog.exec_()
    
    def export_results(self):
        """Export HVSR results (curve data, peaks, metadata)."""
        if self.hvsr_result is None:
            QMessageBox.warning(self, "No Results", "No results to export.")
            return
        
        # Select output directory
        output_dir = QFileDialog.getExistingDirectory(
            self, "Select Output Directory"
        )
        
        if output_dir:
            try:
                from hvsr_pro.utils.export_utils import export_complete_dataset
                
                # Export complete dataset
                created_files = export_complete_dataset(
                    self.hvsr_result,
                    output_dir,
                    base_filename="hvsr"
                )
                
                self.add_info(f"Exported to: {output_dir}")
                for file_type, filepath in created_files.items():
                    filename = Path(filepath).name
                    self.add_info(f"   - {filename} ({file_type})")
                
                QMessageBox.information(
                    self, "Export Complete",
                    f"Results exported to:\n{output_dir}\n\n"
                    f"Files created:\n" +
                    "\n".join([f"• {Path(f).name}" for f in created_files.values()])
                )
                
            except Exception as e:
                import traceback
                error_msg = f"{str(e)}\n\n{traceback.format_exc()}"
                QMessageBox.critical(self, "Export Error", error_msg)
                self.add_info(f"ERROR - Export: {str(e)}")
    
    def save_session(self):
        """Save current session state including all settings and computed data."""
        from hvsr_pro.config.session import (
            SessionManager, SessionState, 
            ProcessingSettings as SessionProcessingSettings,
            QCSettings as SessionQCSettings,
            FileInfo, WindowState
        )
        
        # Get work directory for default save location
        work_dir = getattr(self, '_work_directory', '')
        
        if not work_dir:
            # Ask user to set work directory first
            reply = QMessageBox.question(
                self, "Work Directory Required",
                "Please set a work directory first to save sessions.\n\n"
                "Would you like to select a work directory now?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                work_dir = QFileDialog.getExistingDirectory(
                    self, "Select Work Directory"
                )
                if work_dir:
                    self._work_directory = work_dir
                    if hasattr(self, 'data_load_tab') and hasattr(self.data_load_tab, 'work_dir_edit'):
                        self.data_load_tab.work_dir_edit.setText(work_dir)
                else:
                    return
            else:
                return
        
        manager = SessionManager(work_directory=work_dir)
        
        # Build session state
        state = SessionState()
        state.work_directory = work_dir
        
        # File info
        current_file = getattr(self, 'current_file', '')
        if isinstance(current_file, list):
            current_file = ';'.join(str(f) for f in current_file)
        state.file_info = FileInfo(
            path=str(current_file) if current_file else '',
            load_mode=getattr(self, 'load_mode', 'single')
        )
        
        # Processing settings
        state.processing = SessionProcessingSettings(
            window_length=self.window_length_spin.value() if hasattr(self, 'window_length_spin') else 60.0,
            overlap=self.overlap_spin.value() / 100.0 if hasattr(self, 'overlap_spin') else 0.5,
            smoothing_bandwidth=self.smoothing_spin.value() if hasattr(self, 'smoothing_spin') else 40.0,
            f_min=self.freq_min_spin.value() if hasattr(self, 'freq_min_spin') else 0.2,
            f_max=self.freq_max_spin.value() if hasattr(self, 'freq_max_spin') else 20.0,
            n_frequencies=self.freq_points_spin.value() if hasattr(self, 'freq_points_spin') else 100
        )
        
        # QC settings
        state.qc = SessionQCSettings(
            enabled=self.qc_enable_check.isChecked() if hasattr(self, 'qc_enable_check') else True,
            mode=self.qc_combo.currentData() if hasattr(self, 'qc_combo') else 'balanced',
            cox_fdwra_enabled=self.cox_fdwra_check.isChecked() if hasattr(self, 'cox_fdwra_check') else False,
            cox_n=self.cox_n_spin.value() if hasattr(self, 'cox_n_spin') else 2.0,
            cox_max_iterations=self.cox_iterations_spin.value() if hasattr(self, 'cox_iterations_spin') else 50,
            cox_min_iterations=self.cox_min_iterations_spin.value() if hasattr(self, 'cox_min_iterations_spin') else 1,
            cox_distribution=self.cox_dist_combo.currentText() if hasattr(self, 'cox_dist_combo') else 'lognormal'
        )
        
        # Window states
        if self.windows and hasattr(self.windows, 'windows'):
            state.window_states = [
                WindowState(
                    index=i,
                    active=w.is_active(),
                    rejection_reason=getattr(w, 'rejection_reason', None)
                )
                for i, w in enumerate(self.windows.windows)
            ]
            state.n_total_windows = len(self.windows.windows)
            state.n_active_windows = self.windows.n_active
        
        # Results summary
        if self.hvsr_result:
            state.has_results = True
            # Try to get peak_frequency from various possible attributes
            peak_freq = None
            if hasattr(self.hvsr_result, 'peak_frequency') and self.hvsr_result.peak_frequency is not None:
                peak_freq = float(self.hvsr_result.peak_frequency)
            elif hasattr(self.hvsr_result, 'f0') and self.hvsr_result.f0 is not None:
                peak_freq = float(self.hvsr_result.f0)
            elif hasattr(self.hvsr_result, 'peaks') and self.hvsr_result.peaks:
                # Try to get from peaks list
                if isinstance(self.hvsr_result.peaks, list) and len(self.hvsr_result.peaks) > 0:
                    first_peak = self.hvsr_result.peaks[0]
                    if isinstance(first_peak, dict) and 'frequency' in first_peak:
                        peak_freq = float(first_peak['frequency'])
                    elif hasattr(first_peak, 'frequency'):
                        peak_freq = float(first_peak.frequency)
            state.peak_frequency = peak_freq
            
            # Try to get peak_amplitude
            peak_amp = None
            if hasattr(self.hvsr_result, 'peak_amplitude') and self.hvsr_result.peak_amplitude is not None:
                peak_amp = float(self.hvsr_result.peak_amplitude)
            elif hasattr(self.hvsr_result, 'a0') and self.hvsr_result.a0 is not None:
                peak_amp = float(self.hvsr_result.a0)
            state.peak_amplitude = peak_amp
        
        # Get seismic data if available
        seismic_data = getattr(self, 'seismic_data', None)
        
        # Get azimuthal result if available (from azimuthal tab)
        azimuthal_result = None
        if hasattr(self, 'azimuthal_tab') and hasattr(self.azimuthal_tab, 'result'):
            azimuthal_result = self.azimuthal_tab.result
        
        # Save full session with pickled data
        session_folder = manager.save_full_session(
            state=state,
            windows=self.windows,
            hvsr_result=self.hvsr_result,
            seismic_data=seismic_data,
            azimuthal_result=azimuthal_result
        )
        
        if session_folder:
            self.add_info(f"Session saved: {Path(session_folder).name}")
            
            # Build info message
            info_msg = f"Session saved successfully to:\n{session_folder}\n\n"
            info_msg += "Saved data:\n"
            info_msg += f"  - Settings and metadata\n"
            if self.windows:
                info_msg += f"  - Window collection ({state.n_total_windows} windows)\n"
            if self.hvsr_result:
                if state.peak_frequency is not None:
                    info_msg += f"  - HVSR results (f0 = {state.peak_frequency:.3f} Hz)\n"
                else:
                    info_msg += f"  - HVSR results\n"
            if seismic_data:
                info_msg += f"  - Original seismic data\n"
            if azimuthal_result:
                info_msg += f"  - Azimuthal processing results\n"
            
            QMessageBox.information(self, "Session Saved", info_msg)
        else:
            QMessageBox.critical(
                self, "Save Failed",
                "Failed to save session. Check the log for details."
            )
    
    def load_session(self):
        """Load saved session state including computed data."""
        from hvsr_pro.config.session import SessionManager
        
        # Get work directory for default location
        work_dir = getattr(self, '_work_directory', '')
        default_dir = work_dir if work_dir else str(Path.home())
        
        # Check for sessions folder
        sessions_dir = Path(default_dir) / 'sessions' if default_dir else None
        if sessions_dir and sessions_dir.exists():
            default_dir = str(sessions_dir)
        
        manager = SessionManager(work_directory=work_dir)
        
        # Allow user to select session.json or session folder
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Session",
            default_dir,
            "Session Files (session.json);;All Files (*)"
        )
        
        if not file_path:
            return
        
        # Load full session with pickled data
        state, windows, hvsr_result, seismic_data, azimuthal_result = manager.load_full_session(file_path)
        
        if not state:
            QMessageBox.critical(
                self, "Load Failed",
                "Failed to load session. The file may be corrupted or invalid."
            )
            return
        
        # Apply settings to GUI
        # Work directory
        self._work_directory = state.work_directory
        if hasattr(self, 'data_load_tab') and hasattr(self.data_load_tab, 'work_dir_edit'):
            self.data_load_tab.work_dir_edit.setText(state.work_directory)
        
        # Processing settings
        if hasattr(self, 'window_length_spin'):
            self.window_length_spin.setValue(state.processing.window_length)
        if hasattr(self, 'overlap_spin'):
            self.overlap_spin.setValue(int(state.processing.overlap * 100))
        if hasattr(self, 'smoothing_spin'):
            self.smoothing_spin.setValue(state.processing.smoothing_bandwidth)
        if hasattr(self, 'freq_min_spin'):
            self.freq_min_spin.setValue(state.processing.f_min)
        if hasattr(self, 'freq_max_spin'):
            self.freq_max_spin.setValue(state.processing.f_max)
        if hasattr(self, 'freq_points_spin'):
            self.freq_points_spin.setValue(state.processing.n_frequencies)
        
        # QC settings
        if hasattr(self, 'qc_enable_check'):
            self.qc_enable_check.setChecked(state.qc.enabled)
        if hasattr(self, 'qc_combo'):
            idx = self.qc_combo.findData(state.qc.mode)
            if idx >= 0:
                self.qc_combo.setCurrentIndex(idx)
        if hasattr(self, 'cox_fdwra_check'):
            self.cox_fdwra_check.setChecked(state.qc.cox_fdwra_enabled)
        if hasattr(self, 'cox_n_spin'):
            self.cox_n_spin.setValue(state.qc.cox_n)
        if hasattr(self, 'cox_iterations_spin'):
            self.cox_iterations_spin.setValue(state.qc.cox_max_iterations)
        if hasattr(self, 'cox_min_iterations_spin'):
            self.cox_min_iterations_spin.setValue(state.qc.cox_min_iterations)
        if hasattr(self, 'cox_dist_combo'):
            self.cox_dist_combo.setCurrentText(state.qc.cox_distribution)
        
        # Store file info and restore to data load tab
        if state.file_info.path:
            self.current_file = state.file_info.path
            self.load_mode = state.file_info.load_mode
            
            # Restore file path to data load tab UI
            if hasattr(self, 'data_load_tab'):
                # Try to find the file path display widget
                if hasattr(self.data_load_tab, 'file_path_edit'):
                    self.data_load_tab.file_path_edit.setText(state.file_info.path)
                elif hasattr(self.data_load_tab, 'file_label'):
                    self.data_load_tab.file_label.setText(f"File: {state.file_info.path}")
                
                # Check if file exists and show warning if not
                from pathlib import Path as PathLib
                if not PathLib(state.file_info.path).exists():
                    self.add_info(f"Warning: Original file not found: {state.file_info.path}")
                else:
                    self.add_info(f"Original file path restored: {state.file_info.path}")
        
        # Also store seismic_data attribute
        if seismic_data is not None:
            self.seismic_data = seismic_data
        
        # Build info message for user
        restored_data = []
        if windows is not None:
            restored_data.append(f"Window collection ({state.n_total_windows} windows, {state.n_active_windows} active)")
        if hvsr_result is not None:
            if state.peak_frequency is not None:
                restored_data.append(f"HVSR results (f0 = {state.peak_frequency:.3f} Hz)")
            else:
                restored_data.append("HVSR results")
        if seismic_data is not None:
            restored_data.append("Original seismic data")
        if azimuthal_result is not None:
            restored_data.append("Azimuthal processing results")
        
        self.add_info(f"Session loaded: {Path(state.session_folder).name}")
        
        # Restore full GUI state if we have complete data
        if hvsr_result is not None and windows is not None:
            self.add_info("Restoring GUI with HVSR results and windows...")
            try:
                # Use the proper restore method that mirrors on_processing_finished()
                self.restore_session_gui(hvsr_result, windows, seismic_data)
                self.add_info("GUI fully restored - plot, layers, and docks updated")
            except Exception as e:
                self.add_info(f"Warning: Partial restore - {str(e)}")
        
        # Restore azimuthal results if available
        if azimuthal_result is not None and hasattr(self, 'azimuthal_tab'):
            try:
                self.azimuthal_tab.result = azimuthal_result
                self.azimuthal_tab.update_plot()
                self.add_info("Azimuthal results restored")
            except Exception as e:
                self.add_info(f"Warning: Could not restore azimuthal results - {str(e)}")
        
        # Build info message
        info_msg = f"Session loaded successfully!\n\n"
        info_msg += f"Session: {Path(state.session_folder).name}\n\n"
        
        if restored_data:
            info_msg += "Restored data:\n"
            for item in restored_data:
                info_msg += f"  - {item}\n"
            info_msg += "\nAll data restored - no re-processing needed!"
        else:
            info_msg += "Settings restored. Data will need to be re-processed.\n"
            if state.file_info.path:
                info_msg += f"\nOriginal file: {state.file_info.path}"
        
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
        
        # 10. Plot in separate window (the main HVSR plot)
        if hvsr_result is not None and windows is not None:
            try:
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
        """Handle peak list changes from dock."""
        # Update plot markers
        self.plot_manager.add_peak_markers(peaks)
        self.add_info(f"Peaks updated: {len(peaks)} peak(s) - markers updated on plot")
    
    def on_detect_peaks_requested(self, mode: str, settings: dict):
        """Handle peak detection request from dock."""
        if self.hvsr_result is None:
            QMessageBox.warning(self, "No Data", "Please process HVSR data first.")
            return
        
        self.add_info(f"Peak detection: mode={mode}, settings={settings}")
        
        try:
            from hvsr_pro.processing.windows import find_top_n_peaks, find_multi_peaks
            
            frequencies = self.hvsr_result.frequencies
            mean_hvsr = self.hvsr_result.mean_hvsr
            
            # Run appropriate detection algorithm
            if mode == "auto_top_n":
                peaks = find_top_n_peaks(
                    frequencies,
                    mean_hvsr,
                    n_peaks=settings['n_peaks'],
                    prominence=settings['prominence'],
                    freq_range=(settings['freq_min'], settings['freq_max'])
                )
                self.add_info(f"Auto Top N: Found {len(peaks)} peak(s)")
                
            elif mode == "auto_multi":
                peaks = find_multi_peaks(
                    frequencies,
                    mean_hvsr,
                    prominence=settings['prominence'],
                    min_distance=settings['min_distance'],
                    freq_range=(settings['freq_min'], settings['freq_max'])
                )
                self.add_info(f"Auto Multi: Found {len(peaks)} peak(s)")
            
            else:
                self.add_info(f"Unknown mode: {mode}")
                return
            
            # Add peaks to dock
            if peaks:
                self.peak_picker_dock.add_peaks(peaks)
                
                # Log peak details
                for i, peak in enumerate(peaks, 1):
                    self.add_info(f"  Peak {i}: f={peak['frequency']:.2f} Hz, A={peak['amplitude']:.2f}")
            else:
                QMessageBox.information(self, "No Peaks", "No peaks found with current settings.\nTry lowering prominence threshold.")
                self.add_info("No peaks detected - try different settings")
        
        except Exception as e:
            QMessageBox.critical(self, "Detection Error", f"Peak detection failed:\n{str(e)}")
            self.add_info(f"ERROR - Peak detection: {str(e)}")
    
    def on_manual_mode_requested(self, activate: bool):
        """Handle manual peak picking mode toggle."""
        if activate:
            # Enable manual picking on plot
            self.plot_manager.enable_manual_picking(self.on_manual_peak_selected)
            self.add_info("Manual peak picking ACTIVE - Click on HVSR curve to add peak")
            self.status_bar.showMessage("MANUAL MODE: Click on HVSR curve to add peak")
        else:
            # Disable manual picking
            self.plot_manager.disable_manual_picking()
            self.add_info("Manual peak picking deactivated")
            self.status_bar.showMessage("Ready")
    
    def on_manual_peak_selected(self, frequency: float, amplitude: float):
        """
        Handle manual peak selection from plot click.
        
        Args:
            frequency: Clicked frequency (Hz)
            amplitude: Clicked amplitude (H/V ratio)
        """
        # Add peak to dock with 'Manual' source
        self.peak_picker_dock.add_peak(frequency, amplitude, source='Manual')
        self.add_info(f"Manual peak added: f={frequency:.2f} Hz, A={amplitude:.2f}")
    
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
        
        # Store data in plot manager
        self.plot_manager.set_plot_data(self.hvsr_result, self.windows, self.data)
        
        # Replot with properties
        self.replot_with_properties(properties)
    
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
        
        Args:
            properties: PlotProperties object
        """
        import numpy as np
        
        # Recreate axes
        self.plot_manager._create_axes()
        
        # Get axes
        ax_timeline, ax_hvsr, ax_stats = self.plot_manager.get_axes()
        
        result = self.hvsr_result
        windows = self.windows
        
        # Plot timeline (if visible)
        if ax_timeline is not None:
            ax_timeline.clear()
            ax_timeline.set_title('Window Timeline')
            ax_timeline.set_xlabel('Time (s)')
            ax_timeline.set_ylabel('Window')
            
            for i, window in enumerate(windows.windows):
                color = 'green' if window.is_active() else 'gray'
                ax_timeline.barh(i, window.duration, left=window.start_time, 
                               height=0.8, color=color, alpha=0.7)
            
            ax_timeline.set_ylim(-1, len(windows.windows))
            ax_timeline.invert_yaxis()
        
        # === PLOT HVSR WITH PROPERTIES ===
        self.window_lines = {}
        color_palette = self._get_color_palette()
        
        # Set background color
        bg_color = self.plot_manager.get_background_color(properties)
        ax_hvsr.set_facecolor(bg_color)
        
        # Plot individual windows (if enabled)
        if properties.show_windows:
            for i, window in enumerate(windows.windows):
                if i < len(result.window_spectra):
                    if window.is_active():
                        color = color_palette[i % len(color_palette)]
                        alpha = properties.window_alpha
                    else:
                        color = 'gray'
                        alpha = properties.window_alpha * 0.6
                    
                    window_spectrum = result.window_spectra[i]
                    window_hvsr = window_spectrum.hvsr
                    
                    line, = ax_hvsr.plot(result.frequencies, window_hvsr,
                                        color=color, linewidth=0.8, alpha=alpha,
                                        visible=window.is_active() and window.visible)
                    self.window_lines[i] = line
        
        # Plot percentile shading (if enabled)
        if properties.show_percentile_shading and result.percentile_16 is not None:
            perc_color = getattr(properties, 'percentile_color', '#9C27B0')
            ax_hvsr.fill_between(result.frequencies,
                                result.percentile_16,
                                result.percentile_84,
                                color=perc_color, alpha=0.2, zorder=50,
                                label='16th-84th percentile')
        
        # Plot mean curve (if enabled)
        if properties.show_mean:
            mean_color = getattr(properties, 'mean_color', '#1976D2')
            mean_line, = ax_hvsr.plot(result.frequencies, result.mean_hvsr,
                                     color=mean_color, linewidth=properties.mean_linewidth,
                                     label='Mean H/V', zorder=100)
            self.stat_lines = {'mean': mean_line}
        else:
            self.stat_lines = {}
        
        # Plot std bands (if enabled)
        if properties.show_std_bands and result.std_hvsr is not None:
            std_color = getattr(properties, 'std_color', '#FF5722')
            std_lw = getattr(properties, 'std_linewidth', 1.5)
            std_plus, = ax_hvsr.plot(result.frequencies, 
                                    result.mean_hvsr + result.std_hvsr,
                                    color=std_color, linestyle='--', linewidth=std_lw, 
                                    label='+1σ', zorder=99)
            
            std_minus, = ax_hvsr.plot(result.frequencies,
                                     result.mean_hvsr - result.std_hvsr,
                                     color=std_color, linestyle='--', linewidth=std_lw, 
                                     label='-1σ', zorder=99)
            
            self.stat_lines['std_plus'] = std_plus
            self.stat_lines['std_minus'] = std_minus
        
        # Plot median (if enabled)
        if properties.show_median and result.median_hvsr is not None:
            median_color = getattr(properties, 'median_color', '#D32F2F')
            median_lw = getattr(properties, 'median_linewidth', 1.5)
            median_line, = ax_hvsr.plot(result.frequencies, result.median_hvsr,
                                        color=median_color, linewidth=median_lw, 
                                        label='Median', zorder=98)
            self.stat_lines['median'] = median_line
        
        # Set Y-axis limits based on properties
        y_min, y_max = self.plot_manager.calculate_y_limits(properties, result)
        ax_hvsr.set_ylim(y_min, y_max)
        
        # Axis properties
        ax_hvsr.set_xscale('log')
        ax_hvsr.set_xlabel('Frequency (Hz)')
        ax_hvsr.set_ylabel('H/V Spectral Ratio')
        ax_hvsr.set_title('HVSR Curve')
        ax_hvsr.set_xlim(result.frequencies[0], result.frequencies[-1])
        
        # Grid (if enabled)
        if properties.show_grid:
            ax_hvsr.grid(True, which='both', alpha=0.3)
        
        # Legend (if enabled)
        if properties.show_legend:
            ax_hvsr.legend(loc='upper right', fontsize=9)
        
        # Acceptance badge (if enabled)
        if properties.show_acceptance_badge:
            acceptance_rate = windows.acceptance_rate * 100
            badge_text = f'Acceptance: {acceptance_rate:.1f}%'
            ax_hvsr.text(0.02, 0.98, badge_text,
                        transform=ax_hvsr.transAxes,
                        fontsize=10, verticalalignment='top',
                        bbox=dict(boxstyle='round,pad=0.5', facecolor='white',
                                edgecolor='black', alpha=0.8))
        
        # Add peak markers (with property-controlled style)
        if properties.show_peak_labels and hasattr(self, 'peak_picker_dock'):
            peaks = self.peak_picker_dock.peaks
            if peaks:
                # Modify peak label style based on properties
                self.plot_manager.add_peak_markers(peaks, label_style=properties.peak_label_style)
        
        # Plot stats panel (if visible)
        if ax_stats is not None:
            ax_stats.clear()
            ax_stats.set_title('Window Quality Statistics')
            ax_stats.set_xlabel('Window Index')
            ax_stats.set_ylabel('Quality Score')
            
            qualities = [w.quality_metrics.get('overall', 0.0) for w in windows.windows]
            colors = ['green' if w.is_active() else 'gray' for w in windows.windows]
            ax_stats.scatter(range(len(windows.windows)), qualities, 
                            c=colors, alpha=0.7, s=50)
            ax_stats.axhline(0.5, color='red', linestyle='--', alpha=0.5, label='Threshold')
            ax_stats.legend()
            if properties.show_grid:
                ax_stats.grid(True, alpha=0.3)
        
        # Adjust layout and redraw
        self.plot_manager.fig.tight_layout()
        self.plot_manager.canvas.draw()
        
        # Rebuild layer dock
        self.layers_dock.rebuild(self.window_lines, self.stat_lines)
        
        # Show plot window
        self.plot_manager.show_separate()
    
    def export_figure(self):
        """Export current plot as image (alias for export_plot_image)."""
        self.export_plot_image()
    
    def export_plot_image(self):
        """Export current plot view as high-DPI image."""
        if self.hvsr_result is None or self.plot_manager.fig is None:
            QMessageBox.warning(self, "No Plot", "No plot to export. Please process data first.")
            return
        
        # Ask user for file path and format
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Plot as Image",
            "hvsr_plot.png",
            "PNG Image (*.png);;PDF Document (*.pdf);;SVG Vector (*.svg);;JPEG Image (*.jpg)"
        )
        
        if not file_path:
            return  # User cancelled
        
        try:
            # Determine DPI based on format
            if file_path.endswith('.pdf') or file_path.endswith('.svg'):
                dpi = 300  # Vector formats
            else:
                # Ask for DPI for raster formats
                dpi, ok = QInputDialog.getItem(
                    self,
                    "Select Resolution",
                    "Choose image resolution (DPI):",
                    ["150 (Screen)", "300 (Print)", "600 (High Quality)"],
                    1,  # Default to 300
                    False
                )
                
                if not ok:
                    return  # User cancelled
                
                # Extract DPI number
                dpi = int(dpi.split()[0])
            
            # Save the figure
            self.plot_manager.fig.savefig(
                file_path,
                dpi=dpi,
                bbox_inches='tight',
                facecolor='white',
                edgecolor='none'
            )
            
            # Log success
            file_size = Path(file_path).stat().st_size / 1024  # KB
            self.add_info(f"Plot exported to: {Path(file_path).name}")
            self.add_info(f"  Resolution: {dpi} DPI, Size: {file_size:.1f} KB")
            
            QMessageBox.information(
                self,
                "Export Success",
                f"Plot saved successfully!\n\n"
                f"File: {Path(file_path).name}\n"
                f"Resolution: {dpi} DPI\n"
                f"Size: {file_size:.1f} KB"
            )
            
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export plot:\n{str(e)}")
            self.add_info(f"ERROR - Plot export: {str(e)}")
    
    def add_info(self, message: str):
        """Add information message to log."""
        self.info_text.append(message)
        # Auto-scroll to bottom
        scrollbar = self.info_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())


if not HAS_PYQT5:
    class HVSRMainWindow:
        """Dummy class when PyQt5 not available."""
        def __init__(self):
            raise ImportError("PyQt5 is required for GUI functionality")
