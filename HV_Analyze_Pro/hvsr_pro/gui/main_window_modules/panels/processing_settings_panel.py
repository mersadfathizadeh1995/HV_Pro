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
        QLabel, QSpinBox, QDoubleSpinBox, QCheckBox
    )
    from PyQt5.QtCore import pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


@dataclass
class ProcessingSettings:
    """Data class for processing settings."""
    window_length: float = 60.0
    overlap: float = 0.5
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
            
            # Connect all value changes to emit settings_changed
            self.window_length_spin.valueChanged.connect(self._emit_settings_changed)
            self.overlap_spin.valueChanged.connect(self._emit_settings_changed)
            self.smoothing_spin.valueChanged.connect(self._emit_settings_changed)
            self.freq_min_spin.valueChanged.connect(self._emit_settings_changed)
            self.freq_max_spin.valueChanged.connect(self._emit_settings_changed)
            self.n_freq_spin.valueChanged.connect(self._emit_settings_changed)
            self.override_sampling_check.toggled.connect(self._emit_settings_changed)
            self.sampling_rate_spin.valueChanged.connect(self._emit_settings_changed)
        
        def _emit_settings_changed(self):
            """Emit settings_changed signal with current settings."""
            self.settings_changed.emit(self.get_settings())
        
        def get_settings(self) -> ProcessingSettings:
            """
            Get current processing settings.
            
            Returns:
                ProcessingSettings object with current values
            """
            override = self.override_sampling_check.isChecked()
            return ProcessingSettings(
                window_length=self.window_length_spin.value(),
                overlap=self.overlap_spin.value() / 100.0,
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
