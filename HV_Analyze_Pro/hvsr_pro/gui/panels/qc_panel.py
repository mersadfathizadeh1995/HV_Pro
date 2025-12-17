"""
Quality Control Settings Panel
==============================

Standalone widget for HVSR quality control settings.
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
    class QCSettingsPanel(QWidget):
        """
        Quality Control settings component.
        
        Provides controls for:
        - QC enable/disable
        - Preset vs Custom mode selection
        - Preset dropdown (conservative, balanced, aggressive, sesame, publication)
        - Custom algorithm checkboxes
        - Cox FDWRA settings
        
        Signals:
            qc_settings_changed: Emitted when any QC setting changes
            advanced_settings_requested: Emitted when Advanced Settings button clicked
        """
        
        # Signals
        qc_settings_changed = pyqtSignal(dict)
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
            super().__init__(parent)
            self._custom_qc_settings = None
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
            """Create custom mode widgets."""
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
            self.custom_cox_fdwra_check.setToolTip(
                "Cox et al. (2020) Frequency-Domain Window Rejection\n"
                "Ensures peak frequency consistency across windows"
            )
            custom_layout.addWidget(self.custom_cox_fdwra_check)
            
            # Advanced settings button for custom mode
            self.advanced_qc_btn = QPushButton("Advanced Settings...")
            self.advanced_qc_btn.setToolTip("Fine-tune individual algorithm thresholds")
            custom_layout.addWidget(self.advanced_qc_btn)
            
            layout.addWidget(self.custom_widget)
            self.custom_widget.hide()  # Hidden by default (preset mode active)
        
        def _create_cox_section(self) -> QGroupBox:
            """Create Cox FDWRA settings group."""
            cox_group = QGroupBox("Cox FDWRA (Frequency-Domain)")
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
            
            # Cox parameters
            cox_params_layout = QGridLayout()
            cox_params_layout.setColumnStretch(1, 1)
            
            cox_params_layout.addWidget(QLabel("n-value:"), 0, 0)
            self.cox_n_spin = QDoubleSpinBox()
            self.cox_n_spin.setRange(1.0, 5.0)
            self.cox_n_spin.setValue(2.0)
            self.cox_n_spin.setDecimals(1)
            self.cox_n_spin.setEnabled(False)
            self.cox_n_spin.setToolTip("Standard deviation multiplier (1-5)")
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
            self.advanced_qc_btn.clicked.connect(self.advanced_settings_requested.emit)
            
            # QC change signals
            self.qc_enable_check.toggled.connect(self._emit_settings_changed)
            self.qc_combo.currentIndexChanged.connect(self._emit_settings_changed)
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
            self.custom_cox_fdwra_check.toggled.connect(self._emit_settings_changed)
        
        def _emit_settings_changed(self):
            """Emit qc_settings_changed signal with current settings."""
            self.qc_settings_changed.emit(self.get_qc_settings())
        
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
            current_mode = self.qc_combo.currentData()
            self.preset_desc_label.setText(
                self.PRESET_DESCRIPTIONS.get(current_mode, "")
            )
        
        def _on_cox_enable_toggled(self, checked: bool):
            """Handle Cox FDWRA enable checkbox toggle."""
            self.cox_n_spin.setEnabled(checked)
            self.cox_iterations_spin.setEnabled(checked)
            self.cox_min_iterations_spin.setEnabled(checked)
            self.cox_dist_combo.setEnabled(checked)
        
        # === PUBLIC API ===
        
        def get_qc_settings(self) -> Dict[str, Any]:
            """
            Get current QC settings.
            
            Returns:
                Dictionary with all QC parameters
            """
            if self.preset_radio.isChecked():
                # Preset mode
                return {
                    'enabled': self.qc_enable_check.isChecked(),
                    'mode': 'preset',
                    'preset': self.qc_combo.currentData(),
                    'cox_fdwra': {
                        'enabled': self.cox_fdwra_check.isChecked(),
                        'n': self.cox_n_spin.value(),
                        'max_iterations': self.cox_iterations_spin.value(),
                        'distribution': self.cox_dist_combo.currentText(),
                    }
                }
            else:
                # Custom mode
                return self.get_custom_settings()
        
        def get_custom_settings(self) -> Dict[str, Any]:
            """
            Get custom QC settings from UI checkboxes.
            
            Returns:
                Dictionary with custom algorithm settings
            """
            return {
                'enabled': self.qc_enable_check.isChecked(),
                'mode': 'custom',
                'algorithms': {
                    'amplitude': {
                        'enabled': self.custom_amplitude_check.isChecked(),
                        'params': {}
                    },
                    'quality_threshold': {
                        'enabled': self.custom_quality_check.isChecked(),
                        'params': {'threshold': 0.5}
                    },
                    'sta_lta': {
                        'enabled': self.custom_stalta_check.isChecked(),
                        'params': {
                            'sta_length': 1.0,
                            'lta_length': 30.0,
                            'min_ratio': 0.15,
                            'max_ratio': 2.5
                        }
                    },
                    'frequency_domain': {
                        'enabled': self.custom_freq_check.isChecked(),
                        'params': {'spike_threshold': 3.0}
                    },
                    'statistical_outlier': {
                        'enabled': self.custom_stats_check.isChecked(),
                        'params': {'method': 'iqr', 'threshold': 2.0}
                    },
                    'hvsr_amplitude': {
                        'enabled': self.custom_hvsr_amp_check.isChecked(),
                        'params': {'min_amplitude': 1.0}
                    },
                    'flat_peak': {
                        'enabled': self.custom_flat_peak_check.isChecked(),
                        'params': {'flatness_threshold': 0.15}
                    },
                    'cox_fdwra': {
                        'enabled': self.custom_cox_fdwra_check.isChecked(),
                        'params': {
                            'n': self.cox_n_spin.value(),
                            'max_iterations': self.cox_iterations_spin.value(),
                            'min_iterations': self.cox_min_iterations_spin.value()
                        }
                    }
                },
                'cox_fdwra': {
                    'enabled': self.cox_fdwra_check.isChecked(),
                    'n': self.cox_n_spin.value(),
                    'max_iterations': self.cox_iterations_spin.value(),
                    'min_iterations': self.cox_min_iterations_spin.value(),
                    'distribution': self.cox_dist_combo.currentText(),
                }
            }
        
        def set_preset(self, preset: str):
            """
            Set QC to a specific preset.
            
            Args:
                preset: Preset name (conservative, balanced, aggressive, sesame, publication)
            """
            index = self.qc_combo.findData(preset)
            if index >= 0:
                self.preset_radio.setChecked(True)
                self.qc_combo.setCurrentIndex(index)
        
        def set_custom_qc_settings(self, settings: Optional[Dict]):
            """
            Store custom QC settings from Advanced dialog.
            
            Args:
                settings: Custom settings dictionary or None
            """
            self._custom_qc_settings = settings
        
        def get_stored_custom_settings(self) -> Optional[Dict]:
            """Get stored custom QC settings from Advanced dialog."""
            return self._custom_qc_settings
        
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
                'distribution': self.cox_dist_combo.currentText(),
            }

else:
    class QCSettingsPanel:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass

