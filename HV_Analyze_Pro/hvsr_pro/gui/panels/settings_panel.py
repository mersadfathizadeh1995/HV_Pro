"""
Processing Settings Panel
=========================

Standalone widget for HVSR processing settings.
Extracted from main_window.py for modularity.
"""

from typing import Dict, Any, Optional

try:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
        QLabel, QSpinBox, QDoubleSpinBox, QCheckBox,
        QPushButton, QComboBox, QRadioButton, QButtonGroup,
        QFrame, QGridLayout
    )
    from PyQt5.QtCore import Qt, pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


if HAS_PYQT5:
    class ProcessingSettingsPanel(QWidget):
        """
        Standalone processing settings panel.
        
        Provides controls for:
        - Window length and overlap
        - Smoothing bandwidth
        - Frequency range
        - Sampling rate override
        - Parallel processing
        
        Signals:
            settings_changed: Emitted when any setting changes
            process_requested: Emitted when Process button is clicked
        """
        
        # Signals
        settings_changed = pyqtSignal(dict)
        process_requested = pyqtSignal()
        
        def __init__(self, parent=None):
            super().__init__(parent)
            self._init_ui()
            self._connect_internal_signals()
        
        def _init_ui(self):
            """Initialize the user interface."""
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            
            # Main group box
            group = QGroupBox("Processing Settings")
            group_layout = QVBoxLayout(group)
            
            # === WINDOW SETTINGS ===
            self._create_window_settings(group_layout)
            
            # === FREQUENCY RANGE ===
            self._create_frequency_settings(group_layout)
            
            # === SAMPLING RATE OVERRIDE ===
            self._create_sampling_settings(group_layout)
            
            # === PARALLEL PROCESSING ===
            self._create_parallel_settings(group_layout)
            
            # === PROCESS BUTTON ===
            self._create_process_button(group_layout)
            
            layout.addWidget(group)
        
        def _create_window_settings(self, layout: QVBoxLayout):
            """Create window length and overlap controls."""
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
            self.smoothing_spin.setToolTip(
                "Konno-Ohmachi smoothing bandwidth parameter (b)\n"
                "Higher values = more smoothing\n"
                "Standard: b=40 (recommended)"
            )
            sb_layout.addWidget(self.smoothing_spin)
            layout.addLayout(sb_layout)
        
        def _create_frequency_settings(self, layout: QVBoxLayout):
            """Create frequency range controls."""
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
        
        def _create_sampling_settings(self, layout: QVBoxLayout):
            """Create sampling rate override controls."""
            sampling_label = QLabel("<b>Sampling Rate Override:</b>")
            layout.addWidget(sampling_label)
            
            # Override checkbox
            self.override_sampling_check = QCheckBox("Override Sampling Rate")
            self.override_sampling_check.setChecked(False)
            self.override_sampling_check.setToolTip(
                "Manually specify sampling rate instead of auto-detection"
            )
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
            self.sampling_rate_spin.setEnabled(False)
            self.sampling_rate_spin.setToolTip("Manual sampling rate (Hz)")
            sampling_layout.addWidget(self.sampling_rate_spin)
            layout.addLayout(sampling_layout)
        
        def _create_parallel_settings(self, layout: QVBoxLayout):
            """Create parallel processing controls."""
            cpu_count = self._get_cpu_count()
            
            # Parallel checkbox
            self.parallel_check = QCheckBox("Enable parallel processing (faster)")
            self.parallel_check.setChecked(True)
            self.parallel_check.setToolTip(
                "Use multiple CPU cores for faster HVSR computation.\n"
                "Recommended for datasets with >100 windows.\n"
                f"Your system has {cpu_count} CPU cores.\n"
                "Speed improvement: ~1.5-3x faster for large datasets."
            )
            self.parallel_check.stateChanged.connect(self._on_parallel_toggled)
            layout.addWidget(self.parallel_check)
            
            # CPU core count selector
            cores_layout = QHBoxLayout()
            cores_layout.addWidget(QLabel("   Number of cores to use:"))
            
            self.cores_spin = QSpinBox()
            self.cores_spin.setRange(1, max(1, cpu_count))
            self.cores_spin.setValue(max(1, cpu_count - 1))
            self.cores_spin.setToolTip(
                f"Select number of CPU cores to use (1-{cpu_count}).\n"
                "Using all cores may make your system unresponsive.\n"
                "Recommended: Leave at least 1 core free for system tasks."
            )
            cores_layout.addWidget(self.cores_spin)
            cores_layout.addStretch()
            layout.addLayout(cores_layout)
        
        def _create_process_button(self, layout: QVBoxLayout):
            """Create the Process HVSR button."""
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
        
        def _connect_internal_signals(self):
            """Connect internal widget signals."""
            # Process button
            self.process_btn.clicked.connect(self.process_requested.emit)
            
            # Settings change signals
            self.window_length_spin.valueChanged.connect(self._emit_settings_changed)
            self.overlap_spin.valueChanged.connect(self._emit_settings_changed)
            self.smoothing_spin.valueChanged.connect(self._emit_settings_changed)
            self.freq_min_spin.valueChanged.connect(self._emit_settings_changed)
            self.freq_max_spin.valueChanged.connect(self._emit_settings_changed)
            self.n_freq_spin.valueChanged.connect(self._emit_settings_changed)
            self.sampling_rate_spin.valueChanged.connect(self._emit_settings_changed)
            self.parallel_check.stateChanged.connect(self._emit_settings_changed)
            self.cores_spin.valueChanged.connect(self._emit_settings_changed)
        
        def _emit_settings_changed(self):
            """Emit settings_changed signal with current settings."""
            self.settings_changed.emit(self.get_settings())
        
        def _get_cpu_count(self) -> int:
            """Get number of CPU cores."""
            try:
                from multiprocessing import cpu_count
                return cpu_count()
            except:
                return 4
        
        def _on_override_sampling_toggled(self, checked: bool):
            """Handle sampling rate override checkbox toggle."""
            self.sampling_rate_spin.setEnabled(checked)
        
        def _on_parallel_toggled(self, state):
            """Handle parallel processing checkbox toggle."""
            enabled = (state == Qt.Checked)
            self.cores_spin.setEnabled(enabled)
        
        # === PUBLIC API ===
        
        def get_settings(self) -> Dict[str, Any]:
            """
            Get current processing settings.
            
            Returns:
                Dictionary with all processing parameters
            """
            return {
                'window_length': self.window_length_spin.value(),
                'overlap': self.overlap_spin.value() / 100.0,
                'smoothing_bandwidth': self.smoothing_spin.value(),
                'f_min': self.freq_min_spin.value(),
                'f_max': self.freq_max_spin.value(),
                'n_frequencies': self.n_freq_spin.value(),
                'override_sampling': self.override_sampling_check.isChecked(),
                'sampling_rate': self.sampling_rate_spin.value() if self.override_sampling_check.isChecked() else None,
                'parallel': self.parallel_check.isChecked(),
                'n_workers': self.cores_spin.value() if self.parallel_check.isChecked() else None,
            }
        
        def set_settings(self, settings: Dict[str, Any]):
            """
            Set processing settings from dictionary.
            
            Args:
                settings: Dictionary with processing parameters
            """
            if 'window_length' in settings:
                self.window_length_spin.setValue(settings['window_length'])
            if 'overlap' in settings:
                self.overlap_spin.setValue(int(settings['overlap'] * 100))
            if 'smoothing_bandwidth' in settings:
                self.smoothing_spin.setValue(settings['smoothing_bandwidth'])
            if 'f_min' in settings:
                self.freq_min_spin.setValue(settings['f_min'])
            if 'f_max' in settings:
                self.freq_max_spin.setValue(settings['f_max'])
            if 'n_frequencies' in settings:
                self.n_freq_spin.setValue(settings['n_frequencies'])
            if 'override_sampling' in settings:
                self.override_sampling_check.setChecked(settings['override_sampling'])
            if 'sampling_rate' in settings and settings['sampling_rate']:
                self.sampling_rate_spin.setValue(settings['sampling_rate'])
            if 'parallel' in settings:
                self.parallel_check.setChecked(settings['parallel'])
            if 'n_workers' in settings and settings['n_workers']:
                self.cores_spin.setValue(settings['n_workers'])
        
        def set_process_enabled(self, enabled: bool):
            """Enable or disable the process button."""
            self.process_btn.setEnabled(enabled)
        
        def get_window_length(self) -> float:
            """Get window length in seconds."""
            return self.window_length_spin.value()
        
        def get_overlap(self) -> float:
            """Get overlap as fraction (0-1)."""
            return self.overlap_spin.value() / 100.0
        
        def get_smoothing_bandwidth(self) -> float:
            """Get Konno-Ohmachi smoothing bandwidth."""
            return self.smoothing_spin.value()
        
        def get_frequency_range(self) -> tuple:
            """Get frequency range (f_min, f_max)."""
            return (self.freq_min_spin.value(), self.freq_max_spin.value())
        
        def get_n_frequencies(self) -> int:
            """Get number of frequency points."""
            return self.n_freq_spin.value()
        
        def is_parallel_enabled(self) -> bool:
            """Check if parallel processing is enabled."""
            return self.parallel_check.isChecked()
        
        def get_n_workers(self) -> Optional[int]:
            """Get number of workers for parallel processing."""
            if self.parallel_check.isChecked():
                return self.cores_spin.value()
            return None
        
        def get_sampling_rate_override(self) -> Optional[float]:
            """Get manual sampling rate if override is enabled."""
            if self.override_sampling_check.isChecked():
                return self.sampling_rate_spin.value()
            return None

else:
    class ProcessingSettingsPanel:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass

