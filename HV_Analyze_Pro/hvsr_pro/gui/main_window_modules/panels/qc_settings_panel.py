"""
QC Settings Panel
=================

Panel containing quality control mode selection and algorithm configuration.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional

try:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
        QLabel, QComboBox, QCheckBox, QPushButton,
        QRadioButton, QButtonGroup, QFrame
    )
    from PyQt5.QtCore import pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


@dataclass
class QCSettings:
    """Data class for QC settings."""
    enabled: bool = True
    mode: str = 'preset'  # 'preset' or 'custom'
    preset: str = 'balanced'  # conservative, balanced, aggressive, sesame, publication
    custom_algorithms: Dict[str, Dict[str, Any]] = field(default_factory=dict)


if HAS_PYQT5:
    class QCSettingsPanel(QGroupBox):
        """
        Panel for configuring quality control settings.
        
        Features:
        - Enable/disable QC
        - Preset mode with predefined configurations
        - Custom mode with individual algorithm toggles
        - Advanced settings dialog access
        
        Signals:
            settings_changed: Emitted when any setting changes
            advanced_settings_requested: Emitted when advanced settings button clicked
        """
        
        settings_changed = pyqtSignal(object)  # QCSettings
        advanced_settings_requested = pyqtSignal()
        
        # Preset descriptions
        PRESET_DESCRIPTIONS = {
            "conservative": "Only rejects obvious problems (dead channels, clipping). Best for noisy data.",
            "balanced": "Amplitude checks only. Recommended for most datasets.",
            "aggressive": "Strict QC with STA/LTA, frequency, and statistical checks. For clean data.",
            "sesame": "SESAME-compliant processing with Cox FDWRA for publication-quality results.",
            "publication": "4-condition rejection: HVSR amplitude, peak consistency, flat peaks."
        }
        
        def __init__(self, parent=None):
            super().__init__("Quality Control Settings", parent)
            self._init_ui()
            self._connect_signals()
        
        def _init_ui(self):
            """Initialize the user interface."""
            layout = QVBoxLayout(self)
            
            # Enable checkbox
            self.enable_check = QCheckBox("Enable QC Rejection")
            self.enable_check.setChecked(True)
            self.enable_check.setToolTip("Apply quality control to reject noisy windows")
            layout.addWidget(self.enable_check)
            
            # Mode selector: Preset vs Custom
            mode_frame = QFrame()
            mode_layout = QHBoxLayout(mode_frame)
            mode_layout.setContentsMargins(0, 0, 0, 0)
            
            self.mode_group = QButtonGroup()
            self.preset_radio = QRadioButton("Preset")
            self.preset_radio.setChecked(True)
            self.custom_radio = QRadioButton("Custom")
            self.mode_group.addButton(self.preset_radio, 0)
            self.mode_group.addButton(self.custom_radio, 1)
            
            mode_layout.addWidget(QLabel("Mode:"))
            mode_layout.addWidget(self.preset_radio)
            mode_layout.addWidget(self.custom_radio)
            mode_layout.addStretch()
            layout.addWidget(mode_frame)
            
            # Preset mode widgets
            self.preset_widget = QWidget()
            preset_layout = QVBoxLayout(self.preset_widget)
            preset_layout.setContentsMargins(0, 5, 0, 0)
            
            preset_combo_layout = QHBoxLayout()
            preset_combo_layout.addWidget(QLabel("Preset:"))
            self.preset_combo = QComboBox()
            self.preset_combo.addItem("Conservative - Only obvious problems", "conservative")
            self.preset_combo.addItem("Balanced - Moderate QC (recommended)", "balanced")
            self.preset_combo.addItem("Aggressive - Strict quality control", "aggressive")
            self.preset_combo.addItem("SESAME - SESAME-compliant", "sesame")
            self.preset_combo.addItem("Publication - 4-condition rejection", "publication")
            self.preset_combo.setCurrentIndex(1)  # Default to balanced
            self.preset_combo.setToolTip(
                "Conservative: Amplitude + quality threshold (lenient)\n"
                "Balanced: Amplitude check only (recommended for most data)\n"
                "Aggressive: + STA/LTA + frequency + statistical checks\n"
                "SESAME: Pre-HVSR QC + Cox FDWRA for peak consistency\n"
                "Publication: HVSR amplitude, peak consistency, flat peak detection"
            )
            preset_combo_layout.addWidget(self.preset_combo)
            preset_layout.addLayout(preset_combo_layout)
            
            # Preset description label
            self.preset_desc_label = QLabel()
            self.preset_desc_label.setWordWrap(True)
            self.preset_desc_label.setStyleSheet(
                "color: #666; font-style: italic; padding: 3px;"
            )
            self._update_preset_description()
            preset_layout.addWidget(self.preset_desc_label)
            
            layout.addWidget(self.preset_widget)
            
            # Custom mode widgets
            self.custom_widget = QWidget()
            custom_layout = QVBoxLayout(self.custom_widget)
            custom_layout.setContentsMargins(0, 5, 0, 0)
            
            # Pre-HVSR algorithms section
            pre_hvsr_label = QLabel("<i>Time-Domain (Pre-HVSR):</i>")
            custom_layout.addWidget(pre_hvsr_label)
            
            self.amplitude_check = QCheckBox("Amplitude Rejection")
            self.amplitude_check.setChecked(True)
            self.amplitude_check.setToolTip(
                "Reject clipping, dead channels, extreme amplitudes"
            )
            custom_layout.addWidget(self.amplitude_check)
            
            self.quality_check = QCheckBox("Quality Threshold")
            self.quality_check.setToolTip(
                "Reject windows below SNR/stationarity threshold"
            )
            custom_layout.addWidget(self.quality_check)
            
            self.stalta_check = QCheckBox("STA/LTA Rejection")
            self.stalta_check.setToolTip(
                "Reject transients using short/long-term average ratio"
            )
            custom_layout.addWidget(self.stalta_check)
            
            self.freq_check = QCheckBox("Frequency Domain")
            self.freq_check.setToolTip("Reject windows with spectral spikes")
            custom_layout.addWidget(self.freq_check)
            
            self.stats_check = QCheckBox("Statistical Outliers")
            self.stats_check.setToolTip("Reject windows that are statistical outliers")
            custom_layout.addWidget(self.stats_check)
            
            # Post-HVSR algorithms section
            post_hvsr_label = QLabel("<i>Frequency-Domain (Post-HVSR):</i>")
            custom_layout.addWidget(post_hvsr_label)
            
            self.hvsr_amp_check = QCheckBox("HVSR Peak Amplitude < 1")
            self.hvsr_amp_check.setToolTip(
                "Reject windows where HVSR peak amplitude < 1.0"
            )
            custom_layout.addWidget(self.hvsr_amp_check)
            
            self.flat_peak_check = QCheckBox("Flat Peak Detection")
            self.flat_peak_check.setToolTip(
                "Reject windows with flat/wide peaks or multiple peaks"
            )
            custom_layout.addWidget(self.flat_peak_check)
            
            self.cox_fdwra_check = QCheckBox("Cox FDWRA (Peak Consistency)")
            self.cox_fdwra_check.setToolTip(
                "Cox et al. (2020) Frequency-Domain Window Rejection\n"
                "Ensures peak frequency consistency across windows"
            )
            custom_layout.addWidget(self.cox_fdwra_check)
            
            # Advanced settings button
            self.advanced_btn = QPushButton("Advanced Settings...")
            self.advanced_btn.setToolTip("Fine-tune individual algorithm thresholds")
            custom_layout.addWidget(self.advanced_btn)
            
            layout.addWidget(self.custom_widget)
            self.custom_widget.hide()  # Hidden by default (preset mode active)
        
        def _connect_signals(self):
            """Connect internal signals."""
            # Mode toggle
            self.preset_radio.toggled.connect(self._on_mode_changed)
            self.custom_radio.toggled.connect(self._on_mode_changed)
            
            # Enable toggle
            self.enable_check.toggled.connect(self._on_enable_toggled)
            
            # Preset change
            self.preset_combo.currentIndexChanged.connect(self._update_preset_description)
            self.preset_combo.currentIndexChanged.connect(self._emit_settings_changed)
            
            # Custom algorithm changes
            for checkbox in [self.amplitude_check, self.quality_check, 
                           self.stalta_check, self.freq_check, self.stats_check,
                           self.hvsr_amp_check, self.flat_peak_check, 
                           self.cox_fdwra_check]:
                checkbox.toggled.connect(self._emit_settings_changed)
            
            # Advanced settings button
            self.advanced_btn.clicked.connect(self.advanced_settings_requested.emit)
        
        def _on_mode_changed(self, checked: bool):
            """Handle preset/custom mode change."""
            if self.preset_radio.isChecked():
                self.preset_widget.show()
                self.custom_widget.hide()
            else:
                self.preset_widget.hide()
                self.custom_widget.show()
            self._emit_settings_changed()
        
        def _on_enable_toggled(self, enabled: bool):
            """Handle enable checkbox toggle."""
            self.preset_radio.setEnabled(enabled)
            self.custom_radio.setEnabled(enabled)
            self.preset_widget.setEnabled(enabled)
            self.custom_widget.setEnabled(enabled)
            self._emit_settings_changed()
        
        def _update_preset_description(self):
            """Update the preset description label."""
            preset = self.preset_combo.currentData()
            description = self.PRESET_DESCRIPTIONS.get(preset, "")
            self.preset_desc_label.setText(description)
        
        def _emit_settings_changed(self):
            """Emit settings_changed signal with current settings."""
            self.settings_changed.emit(self.get_settings())
        
        def get_settings(self) -> QCSettings:
            """
            Get current QC settings.
            
            Returns:
                QCSettings object with current values
            """
            custom_algorithms = {}
            if self.custom_radio.isChecked():
                custom_algorithms = {
                    'amplitude': {'enabled': self.amplitude_check.isChecked()},
                    'quality_threshold': {'enabled': self.quality_check.isChecked()},
                    'sta_lta': {'enabled': self.stalta_check.isChecked()},
                    'frequency_domain': {'enabled': self.freq_check.isChecked()},
                    'statistical_outlier': {'enabled': self.stats_check.isChecked()},
                    'hvsr_amplitude': {'enabled': self.hvsr_amp_check.isChecked()},
                    'flat_peak': {'enabled': self.flat_peak_check.isChecked()},
                    'cox_fdwra': {'enabled': self.cox_fdwra_check.isChecked()},
                }
            
            return QCSettings(
                enabled=self.enable_check.isChecked(),
                mode='custom' if self.custom_radio.isChecked() else 'preset',
                preset=self.preset_combo.currentData() if self.preset_radio.isChecked() else '',
                custom_algorithms=custom_algorithms
            )
        
        def set_settings(self, settings: QCSettings):
            """
            Set QC settings from a QCSettings object.
            
            Args:
                settings: QCSettings object with values to apply
            """
            self.blockSignals(True)
            
            self.enable_check.setChecked(settings.enabled)
            
            if settings.mode == 'preset':
                self.preset_radio.setChecked(True)
                idx = self.preset_combo.findData(settings.preset)
                if idx >= 0:
                    self.preset_combo.setCurrentIndex(idx)
            else:
                self.custom_radio.setChecked(True)
                algos = settings.custom_algorithms
                self.amplitude_check.setChecked(algos.get('amplitude', {}).get('enabled', False))
                self.quality_check.setChecked(algos.get('quality_threshold', {}).get('enabled', False))
                self.stalta_check.setChecked(algos.get('sta_lta', {}).get('enabled', False))
                self.freq_check.setChecked(algos.get('frequency_domain', {}).get('enabled', False))
                self.stats_check.setChecked(algos.get('statistical_outlier', {}).get('enabled', False))
                self.hvsr_amp_check.setChecked(algos.get('hvsr_amplitude', {}).get('enabled', False))
                self.flat_peak_check.setChecked(algos.get('flat_peak', {}).get('enabled', False))
                self.cox_fdwra_check.setChecked(algos.get('cox_fdwra', {}).get('enabled', False))
            
            self.blockSignals(False)
            self._emit_settings_changed()
        
        def get_preset_mode(self) -> str:
            """Get the current preset mode name."""
            return self.preset_combo.currentData()
        
        def is_custom_mode(self) -> bool:
            """Check if custom mode is active."""
            return self.custom_radio.isChecked()


else:
    class QCSettingsPanel:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            raise ImportError("PyQt5 is required for GUI functionality")
