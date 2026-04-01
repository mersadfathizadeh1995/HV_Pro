"""
Algorithm Settings Dialogs
==========================

Individual settings dialogs for each QC algorithm.
Adapted from hvsr_pro for standalone use in HVSR_old.
"""

from typing import Dict, Any, Optional

try:
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
        QLabel, QSpinBox, QDoubleSpinBox, QComboBox, QCheckBox,
        QPushButton, QGroupBox, QMessageBox
    )
    from PyQt5.QtCore import Qt
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


# Default parameters for each algorithm
ALGORITHM_DEFAULTS = {
    'amplitude': {
        'preset': 'moderate',
        'max_amplitude': None,
        'min_rms': 1e-10,
        'clipping_threshold': 0.95,
        'clipping_max_percent': 1.0,
    },
    'sta_lta': {
        'sta_length': 1.0,
        'lta_length': 30.0,
        'min_ratio': 0.2,
        'max_ratio': 2.5
    },
    'statistical_outlier': {
        'method': 'mad',
        'threshold': 3.0,
        'metric': 'max_deviation',
    },
    'fdwra': {
        'n': 2.0,
        'max_iterations': 50,
        'min_iterations': 1,
        'distribution_fn': 'lognormal',
        'distribution_mc': 'lognormal'
    },
    'hvsr_amplitude': {
        'min_amplitude': 1.0,
        'max_amplitude': 15.0,
    },
    'flat_peak': {
        'flatness_threshold': 0.15
    },
    'curve_outlier': {
        'threshold': 3.0,
        'max_iterations': 5,
        'metric': 'mean'
    }
}


if HAS_PYQT5:
    class BaseAlgorithmDialog(QDialog):
        """Base class for algorithm settings dialogs."""
        
        def __init__(self, parent, title: str, description: str, current_params: Dict[str, Any]):
            super().__init__(parent)
            self.setWindowTitle(f"{title} Settings")
            self.setModal(True)
            self.setMinimumWidth(350)
            
            self._current_params = current_params.copy()
            self._result_params = None
            
            layout = QVBoxLayout(self)
            
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: #666; padding: 5px; background-color: #f5f5f5; border-radius: 3px;")
            layout.addWidget(desc_label)
            
            self.params_group = QGroupBox("Parameters")
            self.params_layout = QGridLayout(self.params_group)
            self._setup_parameters()
            layout.addWidget(self.params_group)
            
            btn_layout = QHBoxLayout()
            
            self.reset_btn = QPushButton("Reset to Defaults")
            self.reset_btn.clicked.connect(self._on_reset)
            btn_layout.addWidget(self.reset_btn)
            
            btn_layout.addStretch()
            
            self.cancel_btn = QPushButton("Cancel")
            self.cancel_btn.clicked.connect(self.reject)
            btn_layout.addWidget(self.cancel_btn)
            
            self.ok_btn = QPushButton("OK")
            self.ok_btn.setDefault(True)
            self.ok_btn.clicked.connect(self._on_ok)
            btn_layout.addWidget(self.ok_btn)
            
            layout.addLayout(btn_layout)
        
        def _setup_parameters(self):
            """Override in subclasses to add parameter widgets."""
            pass
        
        def _get_defaults(self) -> Dict[str, Any]:
            """Override in subclasses to return default values."""
            return {}
        
        def _collect_params(self) -> Dict[str, Any]:
            """Override in subclasses to collect current widget values."""
            return {}
        
        def _apply_params(self, params: Dict[str, Any]):
            """Override in subclasses to apply params to widgets."""
            pass
        
        def _on_reset(self):
            """Reset to default values."""
            self._apply_params(self._get_defaults())
        
        def _on_ok(self):
            """Accept dialog and store results."""
            self._result_params = self._collect_params()
            self.accept()
        
        def get_result(self) -> Optional[Dict[str, Any]]:
            """Get result params (None if cancelled)."""
            return self._result_params


    # Presets for the Amplitude Check algorithm
    AMPLITUDE_PRESETS = {
        'strict': {
            'max_amplitude': 1e6,
            'min_rms': 1e-8,
            'clipping_threshold': 0.90,
            'clipping_max_percent': 0.5,
        },
        'moderate': {
            'max_amplitude': None,
            'min_rms': 1e-10,
            'clipping_threshold': 0.95,
            'clipping_max_percent': 1.0,
        },
        'lenient': {
            'max_amplitude': None,
            'min_rms': 1e-12,
            'clipping_threshold': 0.99,
            'clipping_max_percent': 5.0,
        },
    }

    class AmplitudeSettingsDialog(BaseAlgorithmDialog):
        """Settings dialog for Amplitude Check algorithm with presets."""

        def __init__(self, parent, current_params: Dict[str, Any]):
            super().__init__(
                parent,
                "Amplitude Check",
                "Rejects windows with clipping, dead channels, or extreme amplitudes.\n"
                "Select a preset or choose Custom to set thresholds manually.",
                current_params
            )
            self.setMinimumWidth(420)

        def _setup_parameters(self):
            row = 0

            # Preset selector
            self.params_layout.addWidget(QLabel("Preset:"), row, 0)
            self.preset_combo = QComboBox()
            self.preset_combo.addItems(['Strict', 'Moderate', 'Lenient', 'Custom'])
            self.preset_combo.setToolTip(
                "Strict  - tight thresholds, rejects more windows\n"
                "Moderate - balanced defaults (recommended)\n"
                "Lenient - loose thresholds, keeps more windows\n"
                "Custom  - set every parameter yourself")
            self.preset_combo.currentTextChanged.connect(self._on_preset_changed)
            self.params_layout.addWidget(self.preset_combo, row, 1)
            row += 1

            # Separator line
            sep = QLabel("")
            sep.setFixedHeight(6)
            self.params_layout.addWidget(sep, row, 0, 1, 2)
            row += 1

            # Max amplitude
            self.params_layout.addWidget(QLabel("Max Amplitude:"), row, 0)
            amp_layout = QHBoxLayout()
            self.max_amp_check = QCheckBox("Limit")
            self.max_amp_check.setToolTip("Enable to set a hard upper limit on signal amplitude")
            self.max_amp_check.stateChanged.connect(self._on_max_amp_toggled)
            amp_layout.addWidget(self.max_amp_check)
            self.max_amp_spin = QDoubleSpinBox()
            self.max_amp_spin.setRange(1.0, 1e12)
            self.max_amp_spin.setDecimals(0)
            self.max_amp_spin.setSingleStep(1000)
            self.max_amp_spin.setValue(1e6)
            self.max_amp_spin.setToolTip("Maximum acceptable raw amplitude (counts)")
            amp_layout.addWidget(self.max_amp_spin)
            self.params_layout.addLayout(amp_layout, row, 1)
            row += 1

            # Min RMS (dead channel)
            self.params_layout.addWidget(QLabel("Min RMS (dead channel):"), row, 0)
            self.min_rms_combo = QComboBox()
            self.min_rms_combo.addItems([
                '1e-8  (strict)',
                '1e-10 (moderate)',
                '1e-12 (lenient)',
            ])
            self.min_rms_combo.setToolTip(
                "Minimum RMS energy for a channel to be considered alive.\n"
                "Channels below this are flagged as dead.")
            self.params_layout.addWidget(self.min_rms_combo, row, 1)
            row += 1

            # Clipping threshold
            self.params_layout.addWidget(QLabel("Clipping Threshold:"), row, 0)
            self.clip_thresh_spin = QDoubleSpinBox()
            self.clip_thresh_spin.setRange(0.50, 1.00)
            self.clip_thresh_spin.setDecimals(2)
            self.clip_thresh_spin.setSingleStep(0.01)
            self.clip_thresh_spin.setToolTip(
                "Fraction of peak amplitude above which samples are\n"
                "considered near-clipping (0.90 = strict, 0.99 = lenient)")
            self.params_layout.addWidget(self.clip_thresh_spin, row, 1)
            row += 1

            # Clipping max percent
            self.params_layout.addWidget(QLabel("Max Clipping (%):"), row, 0)
            self.clip_pct_spin = QDoubleSpinBox()
            self.clip_pct_spin.setRange(0.1, 50.0)
            self.clip_pct_spin.setDecimals(1)
            self.clip_pct_spin.setSingleStep(0.5)
            self.clip_pct_spin.setToolTip(
                "Maximum allowed percentage of samples near the clipping\n"
                "threshold before the window is rejected")
            self.params_layout.addWidget(self.clip_pct_spin, row, 1)
            row += 1

            # Apply current params to widgets
            self._apply_params(self._current_params)

        # ---- helpers ----
        _RMS_MAP = {'1e-8  (strict)': 1e-8, '1e-10 (moderate)': 1e-10, '1e-12 (lenient)': 1e-12}
        _RMS_REVERSE = {v: k for k, v in _RMS_MAP.items()}

        def _on_max_amp_toggled(self, state):
            self.max_amp_spin.setEnabled(state == Qt.Checked)

        def _on_preset_changed(self, text):
            key = text.lower()
            if key in AMPLITUDE_PRESETS:
                self._apply_params({**AMPLITUDE_PRESETS[key], 'preset': key})
                self._set_fields_enabled(False)
            else:
                self._set_fields_enabled(True)

        def _set_fields_enabled(self, enabled):
            self.max_amp_check.setEnabled(enabled)
            self.max_amp_spin.setEnabled(enabled and self.max_amp_check.isChecked())
            self.min_rms_combo.setEnabled(enabled)
            self.clip_thresh_spin.setEnabled(enabled)
            self.clip_pct_spin.setEnabled(enabled)

        # ---- overrides ----
        def _get_defaults(self) -> Dict[str, Any]:
            return ALGORITHM_DEFAULTS['amplitude'].copy()

        def _collect_params(self) -> Dict[str, Any]:
            preset = self.preset_combo.currentText().lower()
            max_amp = self.max_amp_spin.value() if self.max_amp_check.isChecked() else None
            rms_text = self.min_rms_combo.currentText()
            min_rms = self._RMS_MAP.get(rms_text, 1e-10)
            return {
                'preset': preset,
                'max_amplitude': max_amp,
                'min_rms': min_rms,
                'clipping_threshold': self.clip_thresh_spin.value(),
                'clipping_max_percent': self.clip_pct_spin.value(),
            }

        def _apply_params(self, params: Dict[str, Any]):
            # Preset combo
            preset = params.get('preset', 'moderate')
            combo_text = preset.capitalize()
            idx = self.preset_combo.findText(combo_text)
            if idx >= 0:
                self.preset_combo.blockSignals(True)
                self.preset_combo.setCurrentIndex(idx)
                self.preset_combo.blockSignals(False)

            # Max amplitude
            max_amp = params.get('max_amplitude', None)
            self.max_amp_check.setChecked(max_amp is not None)
            if max_amp is not None:
                self.max_amp_spin.setValue(max_amp)
            self.max_amp_spin.setEnabled(max_amp is not None)

            # Min RMS
            min_rms = params.get('min_rms', 1e-10)
            rms_label = self._RMS_REVERSE.get(min_rms, '1e-10 (moderate)')
            rms_idx = self.min_rms_combo.findText(rms_label)
            if rms_idx >= 0:
                self.min_rms_combo.setCurrentIndex(rms_idx)

            # Clipping
            self.clip_thresh_spin.setValue(params.get('clipping_threshold', 0.95))
            self.clip_pct_spin.setValue(params.get('clipping_max_percent', 1.0))

            # Enable/disable fields based on preset
            is_custom = (preset == 'custom')
            self._set_fields_enabled(is_custom)


    class STALTASettingsDialog(BaseAlgorithmDialog):
        """Settings dialog for STA/LTA Transient Detection algorithm."""
        
        def __init__(self, parent, current_params: Dict[str, Any]):
            super().__init__(
                parent,
                "STA/LTA Transient Detection",
                "Rejects windows with unusual energy bursts using Short-Term/Long-Term Average ratio.\n"
                "Effective for detecting earthquakes, traffic, or other transients.",
                current_params
            )
        
        def _setup_parameters(self):
            row = 0
            
            self.params_layout.addWidget(QLabel("Short-Term Average (s):"), row, 0)
            self.sta_spin = QDoubleSpinBox()
            self.sta_spin.setRange(0.1, 10.0)
            self.sta_spin.setDecimals(1)
            self.sta_spin.setSingleStep(0.5)
            self.sta_spin.setValue(self._current_params.get('sta_length', 1.0))
            self.params_layout.addWidget(self.sta_spin, row, 1)
            row += 1
            
            self.params_layout.addWidget(QLabel("Long-Term Average (s):"), row, 0)
            self.lta_spin = QDoubleSpinBox()
            self.lta_spin.setRange(1.0, 120.0)
            self.lta_spin.setDecimals(1)
            self.lta_spin.setSingleStep(5.0)
            self.lta_spin.setValue(self._current_params.get('lta_length', 30.0))
            self.params_layout.addWidget(self.lta_spin, row, 1)
            row += 1
            
            self.params_layout.addWidget(QLabel("Minimum STA/LTA Ratio:"), row, 0)
            self.min_ratio_spin = QDoubleSpinBox()
            self.min_ratio_spin.setRange(0.01, 1.0)
            self.min_ratio_spin.setDecimals(2)
            self.min_ratio_spin.setSingleStep(0.05)
            self.min_ratio_spin.setValue(self._current_params.get('min_ratio', 0.2))
            self.params_layout.addWidget(self.min_ratio_spin, row, 1)
            row += 1
            
            self.params_layout.addWidget(QLabel("Maximum STA/LTA Ratio:"), row, 0)
            self.max_ratio_spin = QDoubleSpinBox()
            self.max_ratio_spin.setRange(1.0, 20.0)
            self.max_ratio_spin.setDecimals(1)
            self.max_ratio_spin.setSingleStep(0.5)
            self.max_ratio_spin.setValue(self._current_params.get('max_ratio', 2.5))
            self.params_layout.addWidget(self.max_ratio_spin, row, 1)
        
        def _get_defaults(self) -> Dict[str, Any]:
            return ALGORITHM_DEFAULTS['sta_lta'].copy()
        
        def _collect_params(self) -> Dict[str, Any]:
            return {
                'sta_length': self.sta_spin.value(),
                'lta_length': self.lta_spin.value(),
                'min_ratio': self.min_ratio_spin.value(),
                'max_ratio': self.max_ratio_spin.value()
            }
        
        def _apply_params(self, params: Dict[str, Any]):
            self.sta_spin.setValue(params.get('sta_length', 1.0))
            self.lta_spin.setValue(params.get('lta_length', 30.0))
            self.min_ratio_spin.setValue(params.get('min_ratio', 0.2))
            self.max_ratio_spin.setValue(params.get('max_ratio', 2.5))


    class FDWRASettingsDialog(BaseAlgorithmDialog):
        """Settings dialog for Peak Frequency Consistency (FDWRA) algorithm."""
        
        def __init__(self, parent, current_params: Dict[str, Any]):
            super().__init__(
                parent,
                "Peak Frequency Consistency (FDWRA)",
                "Industry-standard algorithm for ensuring peak frequency consistency.\n"
                "Iteratively removes windows whose peak frequencies deviate from the group consensus.",
                current_params
            )
        
        def _setup_parameters(self):
            row = 0
            
            self.params_layout.addWidget(QLabel("n-value:"), row, 0)
            self.n_spin = QDoubleSpinBox()
            self.n_spin.setRange(0.5, 10.0)
            self.n_spin.setDecimals(1)
            self.n_spin.setSingleStep(0.5)
            self.n_spin.setValue(self._current_params.get('n', 2.0))
            self.params_layout.addWidget(self.n_spin, row, 1)
            row += 1
            
            self.params_layout.addWidget(QLabel("Max Iterations:"), row, 0)
            self.max_iter_spin = QSpinBox()
            self.max_iter_spin.setRange(1, 100)
            self.max_iter_spin.setValue(self._current_params.get('max_iterations', 50))
            self.params_layout.addWidget(self.max_iter_spin, row, 1)
            row += 1
            
            self.params_layout.addWidget(QLabel("Min Iterations:"), row, 0)
            self.min_iter_spin = QSpinBox()
            self.min_iter_spin.setRange(1, 50)
            self.min_iter_spin.setValue(self._current_params.get('min_iterations', 1))
            self.params_layout.addWidget(self.min_iter_spin, row, 1)
            row += 1
            
            self.params_layout.addWidget(QLabel("Distribution:"), row, 0)
            self.dist_combo = QComboBox()
            self.dist_combo.addItems(['lognormal', 'normal'])
            dist = self._current_params.get('distribution_fn', 'lognormal')
            idx = self.dist_combo.findText(dist)
            if idx >= 0:
                self.dist_combo.setCurrentIndex(idx)
            self.params_layout.addWidget(self.dist_combo, row, 1)
        
        def _get_defaults(self) -> Dict[str, Any]:
            return ALGORITHM_DEFAULTS['fdwra'].copy()
        
        def _collect_params(self) -> Dict[str, Any]:
            dist = self.dist_combo.currentText()
            return {
                'n': self.n_spin.value(),
                'max_iterations': self.max_iter_spin.value(),
                'min_iterations': self.min_iter_spin.value(),
                'distribution_fn': dist,
                'distribution_mc': dist
            }
        
        def _apply_params(self, params: Dict[str, Any]):
            self.n_spin.setValue(params.get('n', 2.0))
            self.max_iter_spin.setValue(params.get('max_iterations', 50))
            self.min_iter_spin.setValue(params.get('min_iterations', 1))
            dist = params.get('distribution_fn', 'lognormal')
            idx = self.dist_combo.findText(dist)
            if idx >= 0:
                self.dist_combo.setCurrentIndex(idx)


    class HVSRAmplitudeSettingsDialog(BaseAlgorithmDialog):
        """Settings dialog for HVSR Amplitude Bounds algorithm."""
        
        def __init__(self, parent, current_params: Dict[str, Any]):
            super().__init__(
                parent,
                "HVSR Amplitude Bounds",
                "Rejects windows where:\n"
                "  • The H/V peak in the analysis range is below 'Min Amplitude'\n"
                "  • Any H/V value across ALL frequencies exceeds 'Max Amplitude (global)'\n\n"
                "The global max catches extreme low-frequency spikes that stretch the Y-axis.",
                current_params
            )
        
        def _setup_parameters(self):
            self.params_layout.addWidget(QLabel("Min Peak Amplitude:"), 0, 0)
            self.threshold_spin = QDoubleSpinBox()
            self.threshold_spin.setRange(0.1, 5.0)
            self.threshold_spin.setDecimals(1)
            self.threshold_spin.setSingleStep(0.1)
            self.threshold_spin.setValue(self._current_params.get('min_amplitude', 1.0))
            self.threshold_spin.setToolTip("Minimum HVSR peak amplitude in the analysis frequency range")
            self.params_layout.addWidget(self.threshold_spin, 0, 1)

            self.params_layout.addWidget(QLabel("Max Amplitude (global):"), 1, 0)
            self.max_amp_spin = QDoubleSpinBox()
            self.max_amp_spin.setRange(5.0, 100.0)
            self.max_amp_spin.setDecimals(1)
            self.max_amp_spin.setSingleStep(1.0)
            self.max_amp_spin.setValue(self._current_params.get('max_amplitude', 15.0))
            self.max_amp_spin.setToolTip(
                "Maximum acceptable HVSR value at ANY frequency.\n"
                "Windows with extreme low-frequency spikes above this\n"
                "value will be rejected.  Set to 100 to effectively disable.")
            self.params_layout.addWidget(self.max_amp_spin, 1, 1)
        
        def _get_defaults(self) -> Dict[str, Any]:
            return ALGORITHM_DEFAULTS['hvsr_amplitude'].copy()
        
        def _collect_params(self) -> Dict[str, Any]:
            return {
                'min_amplitude': self.threshold_spin.value(),
                'max_amplitude': self.max_amp_spin.value(),
            }
        
        def _apply_params(self, params: Dict[str, Any]):
            self.threshold_spin.setValue(params.get('min_amplitude', 1.0))
            self.max_amp_spin.setValue(params.get('max_amplitude', 15.0))


    class FlatPeakSettingsDialog(BaseAlgorithmDialog):
        """Settings dialog for Flat Peak Detection algorithm."""
        
        def __init__(self, parent, current_params: Dict[str, Any]):
            super().__init__(
                parent,
                "Flat Peak Detection",
                "Rejects windows with flat, wide, or multiple peaks.\n"
                "Such peaks indicate unclear resonance or data quality issues.",
                current_params
            )
        
        def _setup_parameters(self):
            self.params_layout.addWidget(QLabel("Flatness Threshold:"), 0, 0)
            self.threshold_spin = QDoubleSpinBox()
            self.threshold_spin.setRange(0.01, 1.0)
            self.threshold_spin.setDecimals(2)
            self.threshold_spin.setSingleStep(0.05)
            self.threshold_spin.setValue(self._current_params.get('flatness_threshold', 0.15))
            self.params_layout.addWidget(self.threshold_spin, 0, 1)
        
        def _get_defaults(self) -> Dict[str, Any]:
            return ALGORITHM_DEFAULTS['flat_peak'].copy()
        
        def _collect_params(self) -> Dict[str, Any]:
            return {'flatness_threshold': self.threshold_spin.value()}
        
        def _apply_params(self, params: Dict[str, Any]):
            self.threshold_spin.setValue(params.get('flatness_threshold', 0.15))


    class CurveOutlierSettingsDialog(BaseAlgorithmDialog):
        """Settings dialog for Curve Outlier Rejection (iterative median-MAD)."""
        
        def __init__(self, parent, current_params: Dict[str, Any]):
            super().__init__(
                parent,
                "Curve Outlier Rejection",
                "Iterative median-MAD sigma clipping on per-window H/V curves.\n"
                "Rejects windows whose H/V deviates strongly from the population median.",
                current_params
            )
        
        def _setup_parameters(self):
            row = 0
            
            self.params_layout.addWidget(QLabel("Threshold (sigma):"), row, 0)
            self.threshold_spin = QDoubleSpinBox()
            self.threshold_spin.setRange(1.0, 10.0)
            self.threshold_spin.setDecimals(1)
            self.threshold_spin.setSingleStep(0.5)
            self.threshold_spin.setValue(self._current_params.get('threshold', 3.0))
            self.params_layout.addWidget(self.threshold_spin, row, 1)
            row += 1
            
            self.params_layout.addWidget(QLabel("Max Iterations:"), row, 0)
            self.iter_spin = QSpinBox()
            self.iter_spin.setRange(1, 20)
            self.iter_spin.setValue(self._current_params.get('max_iterations', 5))
            self.params_layout.addWidget(self.iter_spin, row, 1)
            row += 1
            
            self.params_layout.addWidget(QLabel("Deviation Metric:"), row, 0)
            self.metric_combo = QComboBox()
            self.metric_combo.addItems(['mean', 'max'])
            idx = self.metric_combo.findText(self._current_params.get('metric', 'mean'))
            if idx >= 0:
                self.metric_combo.setCurrentIndex(idx)
            self.params_layout.addWidget(self.metric_combo, row, 1)
        
        def _get_defaults(self) -> Dict[str, Any]:
            return ALGORITHM_DEFAULTS['curve_outlier'].copy()
        
        def _collect_params(self) -> Dict[str, Any]:
            return {
                'threshold': self.threshold_spin.value(),
                'max_iterations': self.iter_spin.value(),
                'metric': self.metric_combo.currentText()
            }
        
        def _apply_params(self, params: Dict[str, Any]):
            self.threshold_spin.setValue(params.get('threshold', 3.0))
            self.iter_spin.setValue(params.get('max_iterations', 5))
            idx = self.metric_combo.findText(params.get('metric', 'mean'))
            if idx >= 0:
                self.metric_combo.setCurrentIndex(idx)


    class StatisticalOutlierSettingsDialog(BaseAlgorithmDialog):
        """Settings dialog for Statistical Outlier H/V curve rejection."""

        def __init__(self, parent, current_params: Dict[str, Any]):
            super().__init__(
                parent,
                "Statistical Outlier (H/V Curve)",
                "Rejects time windows whose H/V curve deviates too far from the\n"
                "group median.  Uses robust statistics (MAD or IQR) so a single\n"
                "extreme window does not inflate the threshold.\n\n"
                "This is the recommended QC for removing pink/brown/gray outlier\n"
                "windows that distort the mean HVSR curve.",
                current_params
            )
            self.setMinimumWidth(420)

        def _setup_parameters(self):
            row = 0

            self.params_layout.addWidget(QLabel("Method:"), row, 0)
            self.method_combo = QComboBox()
            self.method_combo.addItems(['mad', 'iqr'])
            self.method_combo.setToolTip(
                "mad - Median Absolute Deviation (recommended, robust)\n"
                "iqr - Inter-Quartile Range")
            method = self._current_params.get('method', 'mad')
            idx = self.method_combo.findText(method)
            if idx >= 0:
                self.method_combo.setCurrentIndex(idx)
            self.params_layout.addWidget(self.method_combo, row, 1)
            row += 1

            self.params_layout.addWidget(QLabel("Threshold (n):"), row, 0)
            self.threshold_spin = QDoubleSpinBox()
            self.threshold_spin.setRange(1.0, 10.0)
            self.threshold_spin.setDecimals(1)
            self.threshold_spin.setSingleStep(0.5)
            self.threshold_spin.setValue(self._current_params.get('threshold', 3.0))
            self.threshold_spin.setToolTip(
                "Number of MAD/IQR deviations above median before a window\n"
                "is rejected.  Lower = stricter (rejects more windows).\n"
                "  2.0 = strict\n"
                "  3.0 = moderate (recommended)\n"
                "  5.0 = lenient")
            self.params_layout.addWidget(self.threshold_spin, row, 1)
            row += 1

            self.params_layout.addWidget(QLabel("Metric:"), row, 0)
            self.metric_combo = QComboBox()
            self.metric_combo.addItems(['max_deviation', 'mean_deviation', 'area'])
            self.metric_combo.setToolTip(
                "How to measure each window's deviation from the group:\n"
                "  max_deviation  - peak deviation at any frequency (catches spikes)\n"
                "  mean_deviation - average deviation across all frequencies\n"
                "  area           - total area between curve and median")
            metric = self._current_params.get('metric', 'max_deviation')
            idx = self.metric_combo.findText(metric)
            if idx >= 0:
                self.metric_combo.setCurrentIndex(idx)
            self.params_layout.addWidget(self.metric_combo, row, 1)

        def _get_defaults(self) -> Dict[str, Any]:
            return ALGORITHM_DEFAULTS['statistical_outlier'].copy()

        def _collect_params(self) -> Dict[str, Any]:
            return {
                'method': self.method_combo.currentText(),
                'threshold': self.threshold_spin.value(),
                'metric': self.metric_combo.currentText(),
            }

        def _apply_params(self, params: Dict[str, Any]):
            method = params.get('method', 'mad')
            idx = self.method_combo.findText(method)
            if idx >= 0:
                self.method_combo.setCurrentIndex(idx)
            self.threshold_spin.setValue(params.get('threshold', 3.0))
            metric = params.get('metric', 'max_deviation')
            idx = self.metric_combo.findText(metric)
            if idx >= 0:
                self.metric_combo.setCurrentIndex(idx)


    # Dialog mapping
    DIALOG_CLASSES = {
        'amplitude': AmplitudeSettingsDialog,
        'sta_lta': STALTASettingsDialog,
        'fdwra': FDWRASettingsDialog,
        'hvsr_amplitude': HVSRAmplitudeSettingsDialog,
        'flat_peak': FlatPeakSettingsDialog,
        'statistical_outlier': StatisticalOutlierSettingsDialog,
    }


    def open_algorithm_settings_dialog(
        parent, 
        algo_key: str, 
        algo_name: str, 
        current_params: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Open the appropriate settings dialog for an algorithm.
        
        Args:
            parent: Parent widget
            algo_key: Algorithm key (e.g., 'sta_lta', 'fdwra')
            algo_name: Display name for the algorithm
            current_params: Current parameter values
        
        Returns:
            New parameter values if OK clicked, None if cancelled
        """
        dialog_class = DIALOG_CLASSES.get(algo_key)
        if dialog_class is None:
            QMessageBox.warning(
                parent, "Unknown Algorithm",
                f"No settings dialog available for '{algo_name}'"
            )
            return None
        
        dialog = dialog_class(parent, current_params)
        result = dialog.exec_()
        
        if result == QDialog.Accepted:
            return dialog.get_result()
        return None


else:
    DIALOG_CLASSES = {}
    
    def open_algorithm_settings_dialog(*args, **kwargs):
        raise ImportError("PyQt5 is required for GUI functionality")
