"""
Processing Settings Panel
=========================

Panel containing window length, overlap, smoothing, and frequency range controls.
"""

from dataclasses import dataclass
from typing import Optional

try:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
        QLabel, QSpinBox, QDoubleSpinBox, QCheckBox,
        QComboBox, QPushButton
    )
    from PyQt5.QtCore import pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False

from hvsr_pro.processing.smoothing import (
    SmoothingMethod, SmoothingConfig, DEFAULT_BANDWIDTHS, BANDWIDTH_RANGES
)


@dataclass
class ProcessingSettings:
    """Data class for processing settings."""
    window_length: float = 60.0
    overlap: float = 0.5
    smoothing_method: str = 'konno_ohmachi'
    smoothing_bandwidth: float = 40.0
    freq_min: float = 0.2
    freq_max: float = 20.0
    n_frequencies: int = 100
    override_sampling: bool = False
    manual_sampling_rate: Optional[float] = None


if HAS_PYQT5:
    class ProcessingSettingsPanel(QGroupBox):
        """
        Panel for configuring HVSR processing parameters.
        
        Contains controls for:
        - Window length (seconds)
        - Overlap percentage
        - Konno-Ohmachi smoothing bandwidth
        - Frequency range (min, max, n_points)
        - Sampling rate override
        
        Signals:
            settings_changed: Emitted when any setting changes
        """
        
        settings_changed = pyqtSignal(object)  # ProcessingSettings
        
        def __init__(self, parent=None):
            super().__init__("Processing Settings", parent)
            self._init_ui()
            self._connect_signals()
        
        def _init_ui(self):
            """Initialize the user interface."""
            layout = QVBoxLayout(self)
            
            # Window length
            wl_layout = QHBoxLayout()
            wl_layout.addWidget(QLabel("Window Length (s):"))
            self.window_length_spin = QDoubleSpinBox()
            self.window_length_spin.setRange(10, 300)
            self.window_length_spin.setValue(60)
            self.window_length_spin.setSingleStep(5)
            self.window_length_spin.setToolTip("Length of each analysis window in seconds")
            wl_layout.addWidget(self.window_length_spin)
            layout.addLayout(wl_layout)
            
            # Overlap
            ov_layout = QHBoxLayout()
            ov_layout.addWidget(QLabel("Overlap (%):"))
            self.overlap_spin = QSpinBox()
            self.overlap_spin.setRange(0, 90)
            self.overlap_spin.setValue(50)
            self.overlap_spin.setSingleStep(10)
            self.overlap_spin.setToolTip("Overlap between consecutive windows")
            ov_layout.addWidget(self.overlap_spin)
            layout.addLayout(ov_layout)
            
            # Smoothing section
            smoothing_label = QLabel("<b>Spectral Smoothing:</b>")
            layout.addWidget(smoothing_label)
            
            # Method selector
            method_layout = QHBoxLayout()
            method_layout.addWidget(QLabel("Method:"))
            self.smoothing_method_combo = QComboBox()
            
            # Add all smoothing methods
            for method in SmoothingMethod:
                self.smoothing_method_combo.addItem(method.display_name(), method.value)
            
            self.smoothing_method_combo.setToolTip(
                "Select spectral smoothing method\n"
                "Konno-Ohmachi is the standard for HVSR analysis"
            )
            method_layout.addWidget(self.smoothing_method_combo)
            
            # Advanced settings button
            self.smoothing_advanced_btn = QPushButton("...")
            self.smoothing_advanced_btn.setMaximumWidth(30)
            self.smoothing_advanced_btn.setToolTip("Open advanced smoothing settings")
            method_layout.addWidget(self.smoothing_advanced_btn)
            layout.addLayout(method_layout)
            
            # Bandwidth
            sb_layout = QHBoxLayout()
            self.smoothing_bw_label = QLabel("Bandwidth (b):")
            sb_layout.addWidget(self.smoothing_bw_label)
            self.smoothing_spin = QDoubleSpinBox()
            self.smoothing_spin.setRange(1, 200)
            self.smoothing_spin.setValue(40)
            self.smoothing_spin.setSingleStep(5)
            self.smoothing_spin.setToolTip(
                "Smoothing bandwidth parameter\n"
                "Meaning depends on selected method"
            )
            sb_layout.addWidget(self.smoothing_spin)
            layout.addLayout(sb_layout)
            
            # Store smoothing config
            self._smoothing_config = SmoothingConfig()
            
            # Frequency range section
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
            
            # Sampling rate override section
            sampling_label = QLabel("<b>Sampling Rate Override:</b>")
            layout.addWidget(sampling_label)
            
            self.override_sampling_check = QCheckBox("Override Sampling Rate")
            self.override_sampling_check.setChecked(False)
            self.override_sampling_check.setToolTip(
                "Manually specify sampling rate instead of auto-detection"
            )
            layout.addWidget(self.override_sampling_check)
            
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
        
        def _connect_signals(self):
            """Connect internal signals."""
            # Connect override checkbox to enable/disable sampling rate spin
            self.override_sampling_check.toggled.connect(
                self.sampling_rate_spin.setEnabled
            )
            
            # Connect smoothing method change to update bandwidth range
            self.smoothing_method_combo.currentIndexChanged.connect(
                self._on_smoothing_method_changed
            )
            
            # Connect advanced button
            self.smoothing_advanced_btn.clicked.connect(self._open_smoothing_dialog)
            
            # Connect all value changes to emit settings_changed
            self.window_length_spin.valueChanged.connect(self._emit_settings_changed)
            self.overlap_spin.valueChanged.connect(self._emit_settings_changed)
            self.smoothing_method_combo.currentIndexChanged.connect(self._emit_settings_changed)
            self.smoothing_spin.valueChanged.connect(self._emit_settings_changed)
            self.freq_min_spin.valueChanged.connect(self._emit_settings_changed)
            self.freq_max_spin.valueChanged.connect(self._emit_settings_changed)
            self.n_freq_spin.valueChanged.connect(self._emit_settings_changed)
            self.override_sampling_check.toggled.connect(self._emit_settings_changed)
            self.sampling_rate_spin.valueChanged.connect(self._emit_settings_changed)
        
        def _emit_settings_changed(self):
            """Emit settings_changed signal with current settings."""
            self.settings_changed.emit(self.get_settings())
        
        def _on_smoothing_method_changed(self, index: int):
            """Handle smoothing method change."""
            method_value = self.smoothing_method_combo.currentData()
            try:
                method = SmoothingMethod.from_string(method_value)
            except ValueError:
                return
            
            # Update bandwidth range and label based on method
            bw_range = BANDWIDTH_RANGES.get(method, (1, 200))
            default_bw = DEFAULT_BANDWIDTHS.get(method, 40.0)
            
            # Update label
            if method == SmoothingMethod.SAVITZKY_GOLAY:
                self.smoothing_bw_label.setText("Window Points:")
                self.smoothing_spin.setDecimals(0)
                self.smoothing_spin.setSingleStep(2)
            elif method in (SmoothingMethod.LOG_RECTANGULAR, SmoothingMethod.LOG_TRIANGULAR):
                self.smoothing_bw_label.setText("Bandwidth (log):")
                self.smoothing_spin.setDecimals(3)
                self.smoothing_spin.setSingleStep(0.01)
            elif method == SmoothingMethod.KONNO_OHMACHI:
                self.smoothing_bw_label.setText("Bandwidth (b):")
                self.smoothing_spin.setDecimals(1)
                self.smoothing_spin.setSingleStep(5)
            else:
                self.smoothing_bw_label.setText("Bandwidth (Hz):")
                self.smoothing_spin.setDecimals(2)
                self.smoothing_spin.setSingleStep(0.1)
            
            # Update range
            self.smoothing_spin.setRange(bw_range[0], bw_range[1])
            
            # Set default value if current is out of range
            current = self.smoothing_spin.value()
            if current < bw_range[0] or current > bw_range[1]:
                self.smoothing_spin.setValue(default_bw)
            
            # Disable for 'none' method
            self.smoothing_spin.setEnabled(method != SmoothingMethod.NONE)
            
            # Update internal config
            self._smoothing_config = SmoothingConfig(
                method=method,
                bandwidth=self.smoothing_spin.value()
            )
        
        def _open_smoothing_dialog(self):
            """Open advanced smoothing settings dialog."""
            from hvsr_pro.gui.dialogs.smoothing import SmoothingSettingsDialog
            
            # Get current config
            method_value = self.smoothing_method_combo.currentData()
            try:
                method = SmoothingMethod.from_string(method_value)
            except ValueError:
                method = SmoothingMethod.KONNO_OHMACHI
            
            config = SmoothingConfig(
                method=method,
                bandwidth=self.smoothing_spin.value()
            )
            
            # Open dialog
            dialog = SmoothingSettingsDialog(config, self)
            if dialog.exec_():
                new_config = dialog.get_config()
                
                # Update UI with new config
                index = self.smoothing_method_combo.findData(new_config.method.value)
                if index >= 0:
                    self.smoothing_method_combo.setCurrentIndex(index)
                
                self.smoothing_spin.setValue(new_config.bandwidth)
                self._smoothing_config = new_config
        
        def get_settings(self) -> ProcessingSettings:
            """
            Get current processing settings.
            
            Returns:
                ProcessingSettings object with current values
            """
            override = self.override_sampling_check.isChecked()
            method_value = self.smoothing_method_combo.currentData() or 'konno_ohmachi'
            
            return ProcessingSettings(
                window_length=self.window_length_spin.value(),
                overlap=self.overlap_spin.value() / 100.0,
                smoothing_method=method_value,
                smoothing_bandwidth=self.smoothing_spin.value(),
                freq_min=self.freq_min_spin.value(),
                freq_max=self.freq_max_spin.value(),
                n_frequencies=self.n_freq_spin.value(),
                override_sampling=override,
                manual_sampling_rate=self.sampling_rate_spin.value() if override else None
            )
        
        def set_settings(self, settings: ProcessingSettings):
            """
            Set processing settings from a ProcessingSettings object.
            
            Args:
                settings: ProcessingSettings object with values to apply
            """
            # Block signals to prevent multiple emissions
            self.blockSignals(True)
            
            self.window_length_spin.setValue(settings.window_length)
            self.overlap_spin.setValue(int(settings.overlap * 100))
            
            # Set smoothing method
            method = getattr(settings, 'smoothing_method', 'konno_ohmachi')
            index = self.smoothing_method_combo.findData(method)
            if index >= 0:
                self.smoothing_method_combo.setCurrentIndex(index)
            
            self.smoothing_spin.setValue(settings.smoothing_bandwidth)
            self.freq_min_spin.setValue(settings.freq_min)
            self.freq_max_spin.setValue(settings.freq_max)
            self.n_freq_spin.setValue(settings.n_frequencies)
            self.override_sampling_check.setChecked(settings.override_sampling)
            if settings.manual_sampling_rate is not None:
                self.sampling_rate_spin.setValue(settings.manual_sampling_rate)
            
            self.blockSignals(False)
            self._emit_settings_changed()
        
        def validate(self) -> tuple:
            """
            Validate current settings.
            
            Returns:
                Tuple of (is_valid: bool, error_message: str)
            """
            freq_min = self.freq_min_spin.value()
            freq_max = self.freq_max_spin.value()
            
            if freq_min >= freq_max:
                return False, "Minimum frequency must be less than maximum frequency"
            
            return True, ""


else:
    class ProcessingSettingsPanel:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            raise ImportError("PyQt5 is required for GUI functionality")
