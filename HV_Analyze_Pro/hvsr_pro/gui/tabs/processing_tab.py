"""
Processing Tab for HVSR Pro
============================

Tab widget for HVSR processing with modular settings panels.
Replaces the inline Processing tab that was in main_window.py.
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass

try:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
        QPushButton, QLabel, QTextEdit, QProgressBar,
        QScrollArea, QSpinBox, QCheckBox, QMessageBox
    )
    from PyQt5.QtCore import Qt, pyqtSignal
    from PyQt5.QtGui import QFont
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


@dataclass
class FullProcessingSettings:
    """Combined settings for a complete processing run."""
    # Processing settings
    window_length: float = 60.0
    overlap: float = 0.5
    smoothing_method: str = 'konno_ohmachi'
    smoothing_bandwidth: float = 40.0
    freq_min: float = 0.2
    freq_max: float = 20.0
    n_frequencies: int = 100
    override_sampling: bool = False
    manual_sampling_rate: Optional[float] = None
    
    # QC settings
    qc_enabled: bool = True
    qc_mode: str = 'sesame'  # 'sesame' or 'custom'
    qc_preset: str = 'sesame'
    custom_qc_settings: Optional[Dict] = None
    phase1_enabled: bool = True  # Phase 1 (Pre-HVSR) enable
    phase2_enabled: bool = True  # Phase 2 (Post-HVSR) enable
    
    # Cox FDWRA settings (now part of Phase 2)
    cox_enabled: bool = True  # FDWRA enabled in SESAME by default
    cox_n: float = 2.0
    cox_max_iterations: int = 50  # hvsrpy default
    cox_min_iterations: int = 1
    cox_distribution: str = 'lognormal'
    
    # Parallel processing
    use_parallel: bool = True
    n_cores: int = 4
    
    # File info (set by main window before processing)
    current_file: Any = None
    load_mode: str = 'single'
    time_range: Optional[Dict] = None


if HAS_PYQT5:
    from hvsr_pro.gui.components import CollapsibleDataPanel
    from hvsr_pro.gui.main_window_modules.panels import (
        ProcessingSettingsPanel, UnifiedQCPanel
    )
    # Keep old imports for backward compatibility but mark as deprecated
    from hvsr_pro.gui.main_window_modules.panels import QCSettingsPanel, CoxSettingsPanel

    class ProcessingTab(QWidget):
        """
        Processing Tab - HVSR computation and visualization settings.
        
        Uses modular panels from main_window_modules/panels/ for settings.
        
        Layout:
        - Top: Collapsible loaded data panel
        - Left: Settings panels in scroll area
        - Contains: Processing settings, QC settings, Cox FDWRA, Process button
        
        Signals:
            process_requested: Emitted with FullProcessingSettings when Process clicked
            recompute_requested: Emitted when Recompute clicked
            settings_changed: Emitted when any setting changes
        """
        
        # Signals
        process_requested = pyqtSignal(object)  # FullProcessingSettings
        recompute_requested = pyqtSignal()
        settings_changed = pyqtSignal()
        
        def __init__(self, parent=None):
            super().__init__(parent)
            
            # Store main window reference
            self._main_window = parent
            
            # Initialize UI
            self._init_ui()
            self._connect_signals()
        
        def _init_ui(self):
            """Initialize the user interface."""
            outer_layout = QVBoxLayout(self)
            outer_layout.setContentsMargins(5, 5, 5, 5)
            outer_layout.setSpacing(5)
            
            # Collapsible data panel at top
            self.data_panel = CollapsibleDataPanel(title="Loaded Data")
            outer_layout.addWidget(self.data_panel)
            
            # Main content area
            main_layout = QHBoxLayout()
            main_layout.setContentsMargins(0, 0, 0, 0)
            
            # Left panel - processing controls with scroll area
            left_panel = self._create_control_panel()
            
            # Wrap control panel in scroll area
            scroll_area = QScrollArea()
            scroll_area.setWidget(left_panel)
            scroll_area.setWidgetResizable(True)
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            scroll_area.setMinimumWidth(300)
            
            main_layout.addWidget(scroll_area, stretch=1)
            outer_layout.addLayout(main_layout, 1)  # stretch
        
        def _create_control_panel(self) -> QWidget:
            """Create left control panel with settings."""
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
            
            # Processing settings panel (from modular panels)
            self.processing_panel = ProcessingSettingsPanel()
            layout.addWidget(self.processing_panel)
            
            # Unified QC settings panel (replaces old qc_panel + cox_panel)
            self.unified_qc_panel = UnifiedQCPanel()
            layout.addWidget(self.unified_qc_panel)
            
            # Backward compatibility aliases
            self.qc_panel = self.unified_qc_panel
            self.cox_panel = None  # Deprecated - use unified_qc_panel
            
            # Parallel processing group
            parallel_group = self._create_parallel_group()
            layout.addWidget(parallel_group)
            
            # Process button - prominent and bold
            self.process_btn = QPushButton("Process HVSR")
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
            
            # Window management group
            window_group = self._create_window_group()
            layout.addWidget(window_group)
            
            # Info display
            self.info_text = QTextEdit()
            self.info_text.setReadOnly(True)
            self.info_text.setMaximumHeight(200)
            self.info_text.setPlaceholderText("Processing information will appear here...")
            layout.addWidget(self.info_text)
            
            # Progress bar
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
        
        def _create_parallel_group(self) -> QGroupBox:
            """Create parallel processing settings group."""
            group = QGroupBox("Parallel Processing")
            layout = QVBoxLayout(group)
            
            # Get CPU count
            try:
                from multiprocessing import cpu_count
                max_cores = cpu_count()
            except:
                max_cores = 4
            
            # Enable checkbox
            self.parallel_check = QCheckBox("Enable parallel processing (faster)")
            self.parallel_check.setChecked(True)
            self.parallel_check.setToolTip(
                f"Use multiple CPU cores for faster HVSR computation.\n"
                f"Your system has {max_cores} CPU cores."
            )
            layout.addWidget(self.parallel_check)
            
            # Core count
            cores_layout = QHBoxLayout()
            cores_layout.addWidget(QLabel("   Number of cores to use:"))
            
            self.cores_spin = QSpinBox()
            self.cores_spin.setRange(1, max(1, max_cores))
            self.cores_spin.setValue(max(1, max_cores - 1))
            self.cores_spin.setToolTip(
                f"Select number of CPU cores to use (1-{max_cores}).\n"
                "Recommended: Leave at least 1 core free for system tasks."
            )
            cores_layout.addWidget(self.cores_spin)
            cores_layout.addStretch()
            
            layout.addLayout(cores_layout)
            
            return group
        
        def _create_window_group(self) -> QGroupBox:
            """Create window management group."""
            group = QGroupBox("Window Management")
            layout = QVBoxLayout(group)
            
            # Window info
            self.window_info_label = QLabel("No windows")
            layout.addWidget(self.window_info_label)
            
            # Toggle buttons
            btn_layout = QHBoxLayout()
            
            self.reject_all_btn = QPushButton("Reject All")
            self.reject_all_btn.setEnabled(False)
            btn_layout.addWidget(self.reject_all_btn)
            
            self.accept_all_btn = QPushButton("Accept All")
            self.accept_all_btn.setEnabled(False)
            btn_layout.addWidget(self.accept_all_btn)
            
            layout.addLayout(btn_layout)
            
            # Recompute button
            self.recompute_btn = QPushButton("Recompute HVSR")
            self.recompute_btn.setEnabled(False)
            layout.addWidget(self.recompute_btn)
            
            return group
        
        def _connect_signals(self):
            """Connect internal signals."""
            # Process button
            self.process_btn.clicked.connect(self._on_process_clicked)
            
            # Recompute button
            self.recompute_btn.clicked.connect(self.recompute_requested.emit)
            
            # Parallel checkbox enables/disables cores spin
            self.parallel_check.stateChanged.connect(
                lambda state: self.cores_spin.setEnabled(state == Qt.Checked)
            )
            
            # Panel changes emit settings_changed
            self.processing_panel.settings_changed.connect(self.settings_changed.emit)
            self.unified_qc_panel.settings_changed.connect(self.settings_changed.emit)
        
        def _on_process_clicked(self):
            """Handle Process HVSR button click."""
            # Validate settings
            is_valid, error_msg = self.validate_settings()
            if not is_valid:
                QMessageBox.warning(self, "Invalid Settings", error_msg)
                return
            
            # Emit signal with settings
            settings = self.get_settings()
            self.process_requested.emit(settings)
        
        def validate_settings(self) -> tuple:
            """
            Validate current settings.
            
            Returns:
                Tuple of (is_valid: bool, error_message: str)
            """
            # Validate processing panel
            is_valid, error_msg = self.processing_panel.validate()
            if not is_valid:
                return False, error_msg
            
            return True, ""
        
        def get_settings(self) -> FullProcessingSettings:
            """
            Get all settings as FullProcessingSettings object.
            
            Returns:
                FullProcessingSettings with current values
            """
            proc = self.processing_panel.get_settings()
            qc_settings = self.unified_qc_panel.get_settings()
            
            # Extract FDWRA settings from unified panel
            fdwra = qc_settings.get('cox_fdwra', {})
            
            return FullProcessingSettings(
                # Processing
                window_length=proc.window_length,
                overlap=proc.overlap,
                smoothing_method=getattr(proc, 'smoothing_method', 'konno_ohmachi'),
                smoothing_bandwidth=proc.smoothing_bandwidth,
                freq_min=proc.freq_min,
                freq_max=proc.freq_max,
                n_frequencies=proc.n_frequencies,
                override_sampling=proc.override_sampling,
                manual_sampling_rate=proc.manual_sampling_rate,
                # QC
                qc_enabled=qc_settings.get('enabled', True),
                qc_mode=qc_settings.get('mode', 'sesame'),
                qc_preset='sesame' if qc_settings.get('mode') == 'sesame' else 'custom',
                custom_qc_settings=qc_settings,
                phase1_enabled=qc_settings.get('phase1_enabled', True),
                phase2_enabled=qc_settings.get('phase2_enabled', True),
                # Cox FDWRA (from unified panel)
                cox_enabled=fdwra.get('enabled', False),
                cox_n=fdwra.get('n', 2.0),
                cox_max_iterations=fdwra.get('max_iterations', 50),
                cox_min_iterations=fdwra.get('min_iterations', 1),
                cox_distribution=fdwra.get('distribution_fn', 'lognormal'),
                # Parallel
                use_parallel=self.parallel_check.isChecked(),
                n_cores=self.cores_spin.value(),
            )
        
        def set_processing_enabled(self, enabled: bool):
            """Enable or disable processing button."""
            self.process_btn.setEnabled(enabled)
        
        def set_window_buttons_enabled(self, enabled: bool):
            """Enable or disable window management buttons."""
            self.reject_all_btn.setEnabled(enabled)
            self.accept_all_btn.setEnabled(enabled)
            self.recompute_btn.setEnabled(enabled)
        
        def update_window_info(self, total: int, active: int, rejected: int, rate: float):
            """Update window info label."""
            info = (f"Total: {total}\n"
                    f"Active: {active} ({rate:.1f}%)\n"
                    f"Rejected: {rejected}")
            self.window_info_label.setText(info)
        
        def set_progress(self, value: int, visible: bool = True):
            """Set progress bar value and visibility."""
            self.progress_bar.setVisible(visible)
            self.progress_bar.setValue(value)
        
        def add_info(self, message: str):
            """Add message to info text."""
            self.info_text.append(message)
            # Auto-scroll to bottom
            scrollbar = self.info_text.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
        
        def clear_info(self):
            """Clear info text."""
            self.info_text.clear()
        
        # === Backward compatibility properties ===
        # These allow main_window.py to access widgets via the old paths
        
        @property
        def window_length_spin(self):
            """Backward compatibility: access window length spin."""
            return self.processing_panel.window_length_spin
        
        @property
        def overlap_spin(self):
            """Backward compatibility: access overlap spin."""
            return self.processing_panel.overlap_spin
        
        @property
        def smoothing_spin(self):
            """Backward compatibility: access smoothing spin."""
            return self.processing_panel.smoothing_spin
        
        @property
        def freq_min_spin(self):
            """Backward compatibility: access freq min spin."""
            return self.processing_panel.freq_min_spin
        
        @property
        def freq_max_spin(self):
            """Backward compatibility: access freq max spin."""
            return self.processing_panel.freq_max_spin
        
        @property
        def n_freq_spin(self):
            """Backward compatibility: access n freq spin."""
            return self.processing_panel.n_freq_spin
        
        @property
        def override_sampling_check(self):
            """Backward compatibility: access override sampling check."""
            return self.processing_panel.override_sampling_check
        
        @property
        def sampling_rate_spin(self):
            """Backward compatibility: access sampling rate spin."""
            return self.processing_panel.sampling_rate_spin
        
        @property
        def qc_enable_check(self):
            """Backward compatibility: access QC enable check."""
            return self.unified_qc_panel.master_enable
        
        @property
        def preset_radio(self):
            """Backward compatibility: access preset radio (SESAME)."""
            return self.unified_qc_panel.sesame_radio
        
        @property
        def custom_radio(self):
            """Backward compatibility: access custom radio."""
            return self.unified_qc_panel.custom_radio
        
        @property
        def qc_combo(self):
            """Backward compatibility: QC combo is deprecated - returns None."""
            # No longer a combo box - SESAME/Custom only
            return None
        
        @property
        def cox_fdwra_check(self):
            """Backward compatibility: access FDWRA enable check."""
            return self.unified_qc_panel.fdwra_row['checkbox']
        
        @property
        def cox_n_spin(self):
            """Backward compatibility: Cox n spin is in dialog - returns None."""
            # Parameters now in settings dialog
            return None
        
        @property
        def cox_iterations_spin(self):
            """Backward compatibility: Cox iterations spin is in dialog - returns None."""
            return None
        
        @property
        def cox_min_iterations_spin(self):
            """Backward compatibility: Cox min iterations spin is in dialog - returns None."""
            return None
        
        @property
        def cox_dist_combo(self):
            """Backward compatibility: Cox distribution combo is in dialog - returns None."""
            return None


else:
    class ProcessingTab:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            raise ImportError("PyQt5 is required for GUI functionality")
