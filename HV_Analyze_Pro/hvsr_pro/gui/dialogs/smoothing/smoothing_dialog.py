"""
Smoothing Settings Dialog
==========================

Dialog for advanced smoothing method configuration.
"""

try:
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
        QLabel, QComboBox, QDoubleSpinBox, QSpinBox,
        QPushButton, QTextEdit, QDialogButtonBox
    )
    from PyQt5.QtCore import Qt, pyqtSignal
    from PyQt5.QtGui import QFont
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False

from hvsr_pro.processing.smoothing import (
    SmoothingMethod,
    SmoothingConfig,
    DEFAULT_BANDWIDTHS,
    BANDWIDTH_DESCRIPTIONS,
    BANDWIDTH_RANGES
)


if HAS_PYQT5:
    class SmoothingSettingsDialog(QDialog):
        """
        Dialog for advanced smoothing settings.
        
        Shows method-specific parameter explanations and validation.
        
        Signals:
            settings_accepted: Emitted with SmoothingConfig when OK is clicked
        """
        
        settings_accepted = pyqtSignal(object)  # SmoothingConfig
        
        def __init__(self, current_config: SmoothingConfig = None, parent=None):
            super().__init__(parent)
            self.setWindowTitle("Smoothing Settings")
            self.setMinimumWidth(450)
            self.setMinimumHeight(400)
            
            # Current config
            self._config = current_config or SmoothingConfig()
            
            self._init_ui()
            self._connect_signals()
            self._load_current_config()
        
        def _init_ui(self):
            """Initialize the user interface."""
            layout = QVBoxLayout(self)
            
            # Method selection group
            method_group = QGroupBox("Smoothing Method")
            method_layout = QVBoxLayout(method_group)
            
            # Method dropdown
            method_row = QHBoxLayout()
            method_row.addWidget(QLabel("Method:"))
            self.method_combo = QComboBox()
            
            # Add all methods with display names
            for method in SmoothingMethod:
                self.method_combo.addItem(method.display_name(), method.value)
            
            method_row.addWidget(self.method_combo)
            method_layout.addLayout(method_row)
            
            layout.addWidget(method_group)
            
            # Bandwidth parameter group
            bandwidth_group = QGroupBox("Bandwidth Parameter")
            bandwidth_layout = QVBoxLayout(bandwidth_group)
            
            # Bandwidth input row
            bw_row = QHBoxLayout()
            self.bw_label = QLabel("Bandwidth:")
            bw_row.addWidget(self.bw_label)
            
            # Double spin for most methods
            self.bw_spin_double = QDoubleSpinBox()
            self.bw_spin_double.setDecimals(3)
            self.bw_spin_double.setSingleStep(0.1)
            bw_row.addWidget(self.bw_spin_double)
            
            # Integer spin for Savitzky-Golay
            self.bw_spin_int = QSpinBox()
            self.bw_spin_int.setMinimum(3)
            self.bw_spin_int.setMaximum(51)
            self.bw_spin_int.setSingleStep(2)  # Always odd
            self.bw_spin_int.setVisible(False)
            bw_row.addWidget(self.bw_spin_int)
            
            # Default button
            self.default_btn = QPushButton("Reset to Default")
            self.default_btn.setMaximumWidth(120)
            bw_row.addWidget(self.default_btn)
            
            bandwidth_layout.addLayout(bw_row)
            
            # Description text
            self.bw_description = QLabel()
            self.bw_description.setWordWrap(True)
            self.bw_description.setStyleSheet("color: gray; font-style: italic;")
            bandwidth_layout.addWidget(self.bw_description)
            
            layout.addWidget(bandwidth_group)
            
            # Help text group
            help_group = QGroupBox("Method Description")
            help_layout = QVBoxLayout(help_group)
            
            self.help_text = QTextEdit()
            self.help_text.setReadOnly(True)
            self.help_text.setMaximumHeight(150)
            help_layout.addWidget(self.help_text)
            
            layout.addWidget(help_group)
            
            # Buttons
            button_box = QDialogButtonBox(
                QDialogButtonBox.Ok | QDialogButtonBox.Cancel
            )
            button_box.accepted.connect(self._on_accept)
            button_box.rejected.connect(self.reject)
            layout.addWidget(button_box)
        
        def _connect_signals(self):
            """Connect internal signals."""
            self.method_combo.currentIndexChanged.connect(self._on_method_changed)
            self.default_btn.clicked.connect(self._reset_to_default)
            self.bw_spin_int.valueChanged.connect(self._ensure_odd)
        
        def _load_current_config(self):
            """Load current config into UI."""
            # Set method
            index = self.method_combo.findData(self._config.method.value)
            if index >= 0:
                self.method_combo.setCurrentIndex(index)
            
            # Set bandwidth (triggers _on_method_changed)
            self._update_bandwidth_ui()
        
        def _on_method_changed(self, index: int):
            """Handle method selection change."""
            method_value = self.method_combo.currentData()
            method = SmoothingMethod.from_string(method_value)
            
            # Update bandwidth UI for the selected method
            self._update_bandwidth_for_method(method)
            
            # Update help text
            self._update_help_text(method)
        
        def _update_bandwidth_for_method(self, method: SmoothingMethod):
            """Update bandwidth controls for the selected method."""
            # Get bandwidth range
            bw_range = BANDWIDTH_RANGES.get(method, (0, 100))
            default_bw = DEFAULT_BANDWIDTHS.get(method, 40.0)
            
            # Show appropriate spin box
            is_savitzky = method == SmoothingMethod.SAVITZKY_GOLAY
            self.bw_spin_double.setVisible(not is_savitzky)
            self.bw_spin_int.setVisible(is_savitzky)
            
            if is_savitzky:
                self.bw_spin_int.setRange(int(bw_range[0]), int(bw_range[1]))
                self.bw_spin_int.setValue(int(default_bw))
                self.bw_label.setText("Window Points (odd):")
            else:
                self.bw_spin_double.setRange(bw_range[0], bw_range[1])
                self.bw_spin_double.setValue(default_bw)
                
                # Adjust decimals and step based on range
                if bw_range[1] <= 1:
                    self.bw_spin_double.setDecimals(3)
                    self.bw_spin_double.setSingleStep(0.01)
                elif bw_range[1] <= 10:
                    self.bw_spin_double.setDecimals(2)
                    self.bw_spin_double.setSingleStep(0.1)
                else:
                    self.bw_spin_double.setDecimals(1)
                    self.bw_spin_double.setSingleStep(1.0)
                
                self.bw_label.setText("Bandwidth:")
            
            # Update description
            desc = BANDWIDTH_DESCRIPTIONS.get(method, "")
            self.bw_description.setText(desc)
            
            # Disable for 'none' method
            is_none = method == SmoothingMethod.NONE
            self.bw_spin_double.setEnabled(not is_none)
            self.bw_spin_int.setEnabled(not is_none)
            self.default_btn.setEnabled(not is_none)
        
        def _update_bandwidth_ui(self):
            """Update bandwidth UI with current config."""
            method = self._config.method
            self._update_bandwidth_for_method(method)
            
            # Set the actual value from config
            if method == SmoothingMethod.SAVITZKY_GOLAY:
                self.bw_spin_int.setValue(int(self._config.bandwidth))
            else:
                self.bw_spin_double.setValue(self._config.bandwidth)
        
        def _update_help_text(self, method: SmoothingMethod):
            """Update help text for the method."""
            help_texts = {
                SmoothingMethod.KONNO_OHMACHI: (
                    "<b>Konno-Ohmachi Smoothing</b><br><br>"
                    "The standard smoothing method for HVSR analysis. Uses a "
                    "logarithmic frequency scale with a sinc^4 window function.<br><br>"
                    "<b>Bandwidth (b):</b> Higher values = narrower window = less smoothing. "
                    "Standard value is 40.<br><br>"
                    "<i>Reference: Konno & Ohmachi (1998)</i>"
                ),
                SmoothingMethod.PARZEN: (
                    "<b>Parzen Smoothing</b><br><br>"
                    "Constant-bandwidth smoothing in Hz. Uses a sinc^4 window "
                    "with fixed width in linear frequency space.<br><br>"
                    "<b>Bandwidth:</b> Window width in Hz. Smaller = less smoothing.<br><br>"
                    "<i>Reference: Konno & Ohmachi (1995)</i>"
                ),
                SmoothingMethod.SAVITZKY_GOLAY: (
                    "<b>Savitzky-Golay Smoothing</b><br><br>"
                    "Polynomial least-squares fitting. Preserves peak shapes "
                    "while reducing noise. Requires linearly-spaced frequencies.<br><br>"
                    "<b>Window Points:</b> Number of points (must be odd). "
                    "More points = more smoothing.<br><br>"
                    "<i>Reference: Savitzky & Golay (1964)</i>"
                ),
                SmoothingMethod.LINEAR_RECTANGULAR: (
                    "<b>Linear Rectangular (Boxcar) Smoothing</b><br><br>"
                    "Simple moving average with equal weights in linear frequency space.<br><br>"
                    "<b>Bandwidth:</b> Window width in Hz."
                ),
                SmoothingMethod.LOG_RECTANGULAR: (
                    "<b>Logarithmic Rectangular (Boxcar) Smoothing</b><br><br>"
                    "Simple moving average with equal weights in log-frequency space.<br><br>"
                    "<b>Bandwidth:</b> Window width in log10 scale."
                ),
                SmoothingMethod.LINEAR_TRIANGULAR: (
                    "<b>Linear Triangular Smoothing</b><br><br>"
                    "Weighted average with triangular weights (linear decrease "
                    "from center) in linear frequency space.<br><br>"
                    "<b>Bandwidth:</b> Triangle base width in Hz."
                ),
                SmoothingMethod.LOG_TRIANGULAR: (
                    "<b>Logarithmic Triangular Smoothing</b><br><br>"
                    "Weighted average with triangular weights in log-frequency space.<br><br>"
                    "<b>Bandwidth:</b> Triangle base width in log10 scale."
                ),
                SmoothingMethod.NONE: (
                    "<b>No Smoothing</b><br><br>"
                    "Interpolation only. The spectrum is resampled to the output "
                    "frequencies without any smoothing applied.<br><br>"
                    "Useful for comparing raw spectra or when smoothing is "
                    "applied elsewhere in the pipeline."
                ),
            }
            
            self.help_text.setHtml(help_texts.get(method, ""))
        
        def _reset_to_default(self):
            """Reset bandwidth to default for current method."""
            method_value = self.method_combo.currentData()
            method = SmoothingMethod.from_string(method_value)
            default_bw = DEFAULT_BANDWIDTHS.get(method, 40.0)
            
            if method == SmoothingMethod.SAVITZKY_GOLAY:
                self.bw_spin_int.setValue(int(default_bw))
            else:
                self.bw_spin_double.setValue(default_bw)
        
        def _ensure_odd(self, value: int):
            """Ensure Savitzky-Golay window is odd."""
            if value % 2 == 0:
                self.bw_spin_int.setValue(value + 1)
        
        def _on_accept(self):
            """Handle OK button click."""
            method_value = self.method_combo.currentData()
            method = SmoothingMethod.from_string(method_value)
            
            if method == SmoothingMethod.SAVITZKY_GOLAY:
                bandwidth = self.bw_spin_int.value()
            else:
                bandwidth = self.bw_spin_double.value()
            
            config = SmoothingConfig(
                method=method,
                bandwidth=bandwidth
            )
            
            # Validate
            errors = config.validate()
            if errors:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self, "Validation Error",
                    "\n".join(errors)
                )
                return
            
            self._config = config
            self.settings_accepted.emit(config)
            self.accept()
        
        def get_config(self) -> SmoothingConfig:
            """Get the current configuration."""
            return self._config


else:
    class SmoothingSettingsDialog:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            raise ImportError("PyQt5 is required for GUI functionality")
