"""
Quality Control Settings Panel
==============================

Unified widget for HVSR quality control settings.
Uses QCSettings dataclass from processing/rejection/settings.py.
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

from hvsr_pro.processing.rejection.settings import (
    QCSettings,
    PRESET_DESCRIPTIONS,
    get_preset_names
)


if HAS_PYQT5:
    class QCSettingsPanel(QWidget):
        """
        Quality Control settings component.
        
        Provides controls for:
        - QC enable/disable
        - Preset vs Custom mode selection
        - Preset dropdown (conservative, balanced, aggressive, sesame, publication)
        - Custom algorithm checkboxes (quick toggles)
        - Cox FDWRA quick settings
        - Access to Advanced Settings dialog
        
        Signals:
            settings_changed: Emitted when any QC setting changes (QCSettings)
            advanced_settings_requested: Emitted when Advanced Settings button clicked
        """
        
        # Signals
        settings_changed = pyqtSignal(object)  # QCSettings
        advanced_settings_requested = pyqtSignal()
        
        def __init__(self, parent=None):
            super().__init__(parent)
            self._settings = QCSettings()
            self._block_signals = False
            self._init_ui()
            self._connect_internal_signals()
        
        def _init_ui(self):
            """Initialize the user interface."""
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            
            # === QC GROUP ===
            qc_group = QGroupBox("Quality Control Settings")
            qc_layout = QVBoxLayout(qc_group)
            
            self._create_enable_section(qc_layout)
            self._create_mode_selector(qc_layout)
            self._create_preset_section(qc_layout)
            self._create_custom_section(qc_layout)
            
            layout.addWidget(qc_group)
            
            # === COX FDWRA GROUP ===
            cox_group = self._create_cox_section()
            layout.addWidget(cox_group)
            
            # === ADVANCED BUTTON ===
            self.advanced_btn = QPushButton("Advanced Settings...")
            self.advanced_btn.setToolTip("Open full QC configuration dialog")
            layout.addWidget(self.advanced_btn)
        
        def _create_enable_section(self, layout: QVBoxLayout):
            """Create QC enable checkbox."""
            self.qc_enable_check = QCheckBox("Enable QC Rejection")
            self.qc_enable_check.setChecked(True)
            self.qc_enable_check.setToolTip("Apply quality control to reject noisy windows")
            self.qc_enable_check.toggled.connect(self._on_qc_enable_toggled)
            layout.addWidget(self.qc_enable_check)
        
        def _create_mode_selector(self, layout: QVBoxLayout):
            """Create Preset vs Custom mode selector."""
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
            
            layout.addWidget(mode_frame)
            
            self.preset_radio.toggled.connect(self._on_qc_mode_changed)
            self.custom_radio.toggled.connect(self._on_qc_mode_changed)
        
        def _create_preset_section(self, layout: QVBoxLayout):
            """Create preset mode widgets."""
            self.preset_widget = QWidget()
            preset_layout = QVBoxLayout(self.preset_widget)
            preset_layout.setContentsMargins(0, 5, 0, 0)
            
            # Preset combo
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
            
            layout.addWidget(self.preset_widget)
        
        def _create_custom_section(self, layout: QVBoxLayout):
            """Create custom mode widgets with algorithm toggles."""
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
            
            layout.addWidget(self.custom_widget)
            self.custom_widget.hide()  # Hidden by default (preset mode active)
        
        def _create_cox_section(self) -> QGroupBox:
            """Create Cox FDWRA settings group."""
            cox_group = QGroupBox("Cox FDWRA (Peak Consistency)")
            cox_layout = QVBoxLayout(cox_group)
            
            # Cox Enable checkbox
            self.cox_fdwra_check = QCheckBox("Enable Cox FDWRA")
            self.cox_fdwra_check.setChecked(False)
            self.cox_fdwra_check.setToolTip(
                "Apply Cox et al. (2020) Frequency-Domain Window Rejection\n"
                "after HVSR computation to ensure peak frequency consistency.\n"
                "Industry-standard for publication-quality HVSR analysis."
            )
            self.cox_fdwra_check.toggled.connect(self._on_cox_enable_toggled)
            cox_layout.addWidget(self.cox_fdwra_check)
            
            # Cox parameters (quick settings)
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
            self.cox_iterations_spin.setRange(1, 100)
            self.cox_iterations_spin.setValue(50)
            self.cox_iterations_spin.setEnabled(False)
            self.cox_iterations_spin.setToolTip("Maximum iterations for convergence")
            cox_params_layout.addWidget(self.cox_iterations_spin, 1, 1)
            
            cox_params_layout.addWidget(QLabel("Min Iter:"), 2, 0)
            self.cox_min_iterations_spin = QSpinBox()
            self.cox_min_iterations_spin.setRange(1, 50)
            self.cox_min_iterations_spin.setValue(1)
            self.cox_min_iterations_spin.setEnabled(False)
            self.cox_min_iterations_spin.setToolTip(
                "Minimum iterations before checking convergence.\n"
                "Set higher to force more rejection passes."
            )
            cox_params_layout.addWidget(self.cox_min_iterations_spin, 2, 1)
            
            cox_params_layout.addWidget(QLabel("Distribution:"), 3, 0)
            self.cox_dist_combo = QComboBox()
            self.cox_dist_combo.addItems(["lognormal", "normal"])
            self.cox_dist_combo.setEnabled(False)
            self.cox_dist_combo.setToolTip("Statistical distribution for peak modeling")
            cox_params_layout.addWidget(self.cox_dist_combo, 3, 1)
            
            cox_layout.addLayout(cox_params_layout)
            
            return cox_group
        
        def _connect_internal_signals(self):
            """Connect internal widget signals."""
            # Advanced settings button
            self.advanced_btn.clicked.connect(self.advanced_settings_requested.emit)
            
            # QC change signals
            self.qc_enable_check.toggled.connect(self._emit_settings_changed)
            self.qc_combo.currentIndexChanged.connect(self._on_preset_changed)
            self.cox_fdwra_check.toggled.connect(self._emit_settings_changed)
            self.cox_n_spin.valueChanged.connect(self._emit_settings_changed)
            self.cox_iterations_spin.valueChanged.connect(self._emit_settings_changed)
            self.cox_min_iterations_spin.valueChanged.connect(self._emit_settings_changed)
            self.cox_dist_combo.currentIndexChanged.connect(self._emit_settings_changed)
            
            # Custom algorithm checkboxes
            self.custom_amplitude_check.toggled.connect(self._emit_settings_changed)
            self.custom_quality_check.toggled.connect(self._emit_settings_changed)
            self.custom_stalta_check.toggled.connect(self._emit_settings_changed)
            self.custom_freq_check.toggled.connect(self._emit_settings_changed)
            self.custom_stats_check.toggled.connect(self._emit_settings_changed)
            self.custom_hvsr_amp_check.toggled.connect(self._emit_settings_changed)
            self.custom_flat_peak_check.toggled.connect(self._emit_settings_changed)
        
        def _emit_settings_changed(self):
            """Emit settings_changed signal with current settings."""
            if not self._block_signals:
                self._update_settings_from_ui()
                self.settings_changed.emit(self._settings)
        
        def _on_qc_enable_toggled(self, checked: bool):
            """Handle QC enable checkbox toggle."""
            self.preset_radio.setEnabled(checked)
            self.custom_radio.setEnabled(checked)
            self.preset_widget.setEnabled(checked)
            self.custom_widget.setEnabled(checked)
            self.qc_combo.setEnabled(checked)
        
        def _on_qc_mode_changed(self, checked: bool):
            """Handle Preset/Custom radio button toggle."""
            if self.preset_radio.isChecked():
                self.preset_widget.show()
                self.custom_widget.hide()
            else:
                self.preset_widget.hide()
                self.custom_widget.show()
            self._emit_settings_changed()
        
        def _on_preset_changed(self, index: int):
            """Handle preset selection change."""
            if not self._block_signals and self.preset_radio.isChecked():
                preset = self.qc_combo.currentData()
                self._settings.apply_preset(preset)
                # Update Cox checkbox based on preset
                self._block_signals = True
                self.cox_fdwra_check.setChecked(self._settings.cox_fdwra.enabled)
                self._on_cox_enable_toggled(self._settings.cox_fdwra.enabled)
                self._block_signals = False
                self._emit_settings_changed()
        
        def _update_preset_description(self):
            """Update the preset description based on selected preset."""
            current_mode = self.qc_combo.currentData()
            self.preset_desc_label.setText(
                PRESET_DESCRIPTIONS.get(current_mode, "")
            )
        
        def _on_cox_enable_toggled(self, checked: bool):
            """Handle Cox FDWRA enable checkbox toggle."""
            self.cox_n_spin.setEnabled(checked)
            self.cox_iterations_spin.setEnabled(checked)
            self.cox_min_iterations_spin.setEnabled(checked)
            self.cox_dist_combo.setEnabled(checked)
        
        def _update_settings_from_ui(self):
            """Update internal settings from UI state."""
            self._settings.enabled = self.qc_enable_check.isChecked()
            
            if self.preset_radio.isChecked():
                self._settings.mode = 'preset'
                self._settings.preset = self.qc_combo.currentData()
                # Apply preset to get correct algorithm settings
                self._settings.apply_preset(self._settings.preset)
            else:
                self._settings.mode = 'custom'
                # Update from custom checkboxes
                self._settings.amplitude.enabled = self.custom_amplitude_check.isChecked()
                self._settings.quality_threshold.enabled = self.custom_quality_check.isChecked()
                self._settings.sta_lta.enabled = self.custom_stalta_check.isChecked()
                self._settings.frequency_domain.enabled = self.custom_freq_check.isChecked()
                self._settings.statistical_outlier.enabled = self.custom_stats_check.isChecked()
                self._settings.hvsr_amplitude.enabled = self.custom_hvsr_amp_check.isChecked()
                self._settings.flat_peak.enabled = self.custom_flat_peak_check.isChecked()
            
            # Cox FDWRA settings (always available)
            self._settings.cox_fdwra.enabled = self.cox_fdwra_check.isChecked()
            self._settings.cox_fdwra.n = self.cox_n_spin.value()
            self._settings.cox_fdwra.max_iterations = self.cox_iterations_spin.value()
            self._settings.cox_fdwra.min_iterations = self.cox_min_iterations_spin.value()
            self._settings.cox_fdwra.distribution_fn = self.cox_dist_combo.currentText()
            self._settings.cox_fdwra.distribution_mc = self.cox_dist_combo.currentText()
        
        def _update_ui_from_settings(self):
            """Update UI state from internal settings."""
            self._block_signals = True
            
            self.qc_enable_check.setChecked(self._settings.enabled)
            
            if self._settings.mode == 'preset':
                self.preset_radio.setChecked(True)
                idx = self.qc_combo.findData(self._settings.preset)
                if idx >= 0:
                    self.qc_combo.setCurrentIndex(idx)
            else:
                self.custom_radio.setChecked(True)
                self.custom_amplitude_check.setChecked(self._settings.amplitude.enabled)
                self.custom_quality_check.setChecked(self._settings.quality_threshold.enabled)
                self.custom_stalta_check.setChecked(self._settings.sta_lta.enabled)
                self.custom_freq_check.setChecked(self._settings.frequency_domain.enabled)
                self.custom_stats_check.setChecked(self._settings.statistical_outlier.enabled)
                self.custom_hvsr_amp_check.setChecked(self._settings.hvsr_amplitude.enabled)
                self.custom_flat_peak_check.setChecked(self._settings.flat_peak.enabled)
            
            # Cox FDWRA
            self.cox_fdwra_check.setChecked(self._settings.cox_fdwra.enabled)
            self.cox_n_spin.setValue(self._settings.cox_fdwra.n)
            self.cox_iterations_spin.setValue(self._settings.cox_fdwra.max_iterations)
            self.cox_min_iterations_spin.setValue(self._settings.cox_fdwra.min_iterations)
            idx = self.cox_dist_combo.findText(self._settings.cox_fdwra.distribution_fn)
            if idx >= 0:
                self.cox_dist_combo.setCurrentIndex(idx)
            
            self._on_cox_enable_toggled(self._settings.cox_fdwra.enabled)
            self._on_qc_mode_changed(True)
            
            self._block_signals = False
        
        # === PUBLIC API ===
        
        def get_settings(self) -> QCSettings:
            """
            Get current QC settings.
            
            Returns:
                QCSettings object with all QC parameters
            """
            self._update_settings_from_ui()
            return self._settings
        
        def set_settings(self, settings: QCSettings):
            """
            Set QC settings.
            
            Args:
                settings: QCSettings object with values to apply
            """
            self._settings = QCSettings.from_dict(settings.to_dict())  # Deep copy
            self._update_ui_from_settings()
        
        def set_preset(self, preset: str):
            """
            Set QC to a specific preset.
            
            Args:
                preset: Preset name (conservative, balanced, aggressive, sesame, publication)
            """
            self._settings.apply_preset(preset)
            self._update_ui_from_settings()
        
        def is_qc_enabled(self) -> bool:
            """Check if QC is enabled."""
            return self.qc_enable_check.isChecked()
        
        def is_preset_mode(self) -> bool:
            """Check if preset mode is selected."""
            return self.preset_radio.isChecked()
        
        def get_preset(self) -> str:
            """Get selected preset name."""
            return self.qc_combo.currentData()
        
        def is_cox_fdwra_enabled(self) -> bool:
            """Check if Cox FDWRA is enabled."""
            return self.cox_fdwra_check.isChecked()
        
        def get_cox_params(self) -> Dict[str, Any]:
            """Get Cox FDWRA parameters."""
            return {
                'n': self.cox_n_spin.value(),
                'max_iterations': self.cox_iterations_spin.value(),
                'min_iterations': self.cox_min_iterations_spin.value(),
                'distribution_fn': self.cox_dist_combo.currentText(),
                'distribution_mc': self.cox_dist_combo.currentText(),
            }
        
        # Backward compatibility methods
        def get_qc_settings(self) -> Dict[str, Any]:
            """Get QC settings as dictionary (backward compatibility)."""
            return self.get_settings().to_dict()
        
        def get_custom_settings(self) -> Dict[str, Any]:
            """Get custom settings (backward compatibility)."""
            return self.get_settings().to_dict()


else:
    class QCSettingsPanel:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            raise ImportError("PyQt5 is required for GUI functionality")
