"""
Algorithm Settings Dialogs
==========================

Individual settings dialogs for each QC algorithm.
Each dialog provides parameters configuration with descriptions and validation.
"""

from typing import Dict, Any, Optional

try:
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
        QLabel, QSpinBox, QDoubleSpinBox, QComboBox,
        QPushButton, QGroupBox, QFrame
    )
    from PyQt5.QtCore import Qt
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


# Default parameters for each algorithm (SESAME/hvsrpy compatible)
ALGORITHM_DEFAULTS = {
    'amplitude': {
        'preset': 'Moderate',
        'max_amplitude': None,
        'min_rms': 1e-10,
        'clipping_threshold': 0.95,
        'clipping_max_percent': 0.01,
    },
    'sta_lta': {
        'sta_length': 1.0,
        'lta_length': 30.0,
        'min_ratio': 0.2,
        'max_ratio': 2.5
    },
    'spectral_spike': {
        'spike_threshold': 3.0
    },
    'statistical_outlier': {
        'method': 'iqr',
        'threshold': 2.0
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
        'max_amplitude': 15.0
    },
    'flat_peak': {
        'flatness_threshold': 0.15
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
            
            # Description
            desc_label = QLabel(description)
            desc_label.setWordWrap(True)
            desc_label.setStyleSheet("color: #666; padding: 5px; background-color: #f5f5f5; border-radius: 3px;")
            layout.addWidget(desc_label)
            
            # Parameters group
            self.params_group = QGroupBox("Parameters")
            self.params_layout = QGridLayout(self.params_group)
            self._setup_parameters()
            layout.addWidget(self.params_group)
            
            # Buttons
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


    class AmplitudeSettingsDialog(BaseAlgorithmDialog):
        """Settings dialog for Amplitude Check algorithm with presets."""
        
        # Preset values matching processing/rejection/algorithms/amplitude.py
        PRESETS = {
            'Strict': {
                'max_amplitude': 1e6, 'min_rms': 1e-8,
                'clipping_threshold': 0.90, 'clipping_max_percent': 0.005
            },
            'Moderate': {
                'max_amplitude': None, 'min_rms': 1e-10,
                'clipping_threshold': 0.95, 'clipping_max_percent': 0.01
            },
            'Lenient': {
                'max_amplitude': None, 'min_rms': 1e-12,
                'clipping_threshold': 0.99, 'clipping_max_percent': 0.05
            },
        }
        
        def __init__(self, parent, current_params: Dict[str, Any]):
            super().__init__(
                parent,
                "Amplitude Check",
                "Rejects windows with clipping, dead channels, or extreme amplitudes.\n"
                "Choose a preset or configure custom thresholds.",
                current_params
            )
            self.setMinimumWidth(420)
        
        def _setup_parameters(self):
            from PyQt5.QtWidgets import QCheckBox
            
            row = 0
            
            # Preset selector
            self.params_layout.addWidget(QLabel("Preset:"), row, 0)
            self.preset_combo = QComboBox()
            self.preset_combo.addItems(['Strict', 'Moderate', 'Lenient', 'Custom'])
            preset = self._current_params.get('preset', 'Moderate')
            idx = self.preset_combo.findText(preset)
            self.preset_combo.setCurrentIndex(idx if idx >= 0 else 1)
            self.preset_combo.currentTextChanged.connect(self._on_preset_changed)
            self.preset_combo.setToolTip(
                "Strict: Tight thresholds, rejects aggressively\n"
                "Moderate: Balanced (recommended)\n"
                "Lenient: Relaxed thresholds\n"
                "Custom: Set your own values"
            )
            self.params_layout.addWidget(self.preset_combo, row, 1)
            row += 1
            
            # Separator
            sep = QFrame()
            sep.setFrameShape(QFrame.HLine)
            self.params_layout.addWidget(sep, row, 0, 1, 2)
            row += 1
            
            # Max amplitude (optional, with checkbox)
            self.max_amp_check = QCheckBox("Limit Max Amplitude:")
            max_amp = self._current_params.get('max_amplitude')
            self.max_amp_check.setChecked(max_amp is not None)
            self.max_amp_check.toggled.connect(lambda c: self.max_amp_spin.setEnabled(c))
            self.params_layout.addWidget(self.max_amp_check, row, 0)
            
            self.max_amp_spin = QDoubleSpinBox()
            self.max_amp_spin.setRange(1.0, 1e12)
            self.max_amp_spin.setDecimals(0)
            self.max_amp_spin.setSingleStep(1e5)
            self.max_amp_spin.setValue(max_amp if max_amp is not None else 1e7)
            self.max_amp_spin.setEnabled(max_amp is not None)
            self.max_amp_spin.setToolTip("Maximum acceptable absolute amplitude (counts or m/s)")
            self.params_layout.addWidget(self.max_amp_spin, row, 1)
            row += 1
            
            # Min RMS
            self.params_layout.addWidget(QLabel("Min RMS (dead channel):"), row, 0)
            self.min_rms_spin = QDoubleSpinBox()
            self.min_rms_spin.setRange(1e-14, 1e-4)
            self.min_rms_spin.setDecimals(14)
            self.min_rms_spin.setValue(self._current_params.get('min_rms', 1e-10))
            self.min_rms_spin.setToolTip(
                "Minimum RMS amplitude for a channel to be considered alive.\n"
                "Channels below this are flagged as dead."
            )
            self.params_layout.addWidget(self.min_rms_spin, row, 1)
            row += 1
            
            # Clipping threshold
            self.params_layout.addWidget(QLabel("Clipping Threshold:"), row, 0)
            self.clip_thresh_spin = QDoubleSpinBox()
            self.clip_thresh_spin.setRange(0.50, 1.00)
            self.clip_thresh_spin.setDecimals(2)
            self.clip_thresh_spin.setSingleStep(0.05)
            self.clip_thresh_spin.setValue(self._current_params.get('clipping_threshold', 0.95))
            self.clip_thresh_spin.setToolTip(
                "Fraction of peak amplitude above which samples are considered near-clipping.\n"
                "0.95 = samples above 95% of max are clipping"
            )
            self.params_layout.addWidget(self.clip_thresh_spin, row, 1)
            row += 1
            
            # Clipping max percent
            self.params_layout.addWidget(QLabel("Clipping Max % :"), row, 0)
            self.clip_pct_spin = QDoubleSpinBox()
            self.clip_pct_spin.setRange(0.1, 50.0)
            self.clip_pct_spin.setDecimals(1)
            self.clip_pct_spin.setSingleStep(0.5)
            self.clip_pct_spin.setSuffix(" %")
            self.clip_pct_spin.setValue(self._current_params.get('clipping_max_percent', 1.0) * 100)
            self.clip_pct_spin.setToolTip(
                "Maximum percentage of samples allowed near clipping level.\n"
                "Windows exceeding this are rejected."
            )
            self.params_layout.addWidget(self.clip_pct_spin, row, 1)
            
            # Apply initial preset state
            self._on_preset_changed(self.preset_combo.currentText())
        
        def _on_preset_changed(self, preset_name: str):
            """Update fields when preset changes."""
            is_custom = (preset_name == 'Custom')
            self.max_amp_check.setEnabled(is_custom)
            self.max_amp_spin.setEnabled(is_custom and self.max_amp_check.isChecked())
            self.min_rms_spin.setEnabled(is_custom)
            self.clip_thresh_spin.setEnabled(is_custom)
            self.clip_pct_spin.setEnabled(is_custom)
            
            if not is_custom and preset_name in self.PRESETS:
                p = self.PRESETS[preset_name]
                has_max = p['max_amplitude'] is not None
                self.max_amp_check.setChecked(has_max)
                if has_max:
                    self.max_amp_spin.setValue(p['max_amplitude'])
                self.min_rms_spin.setValue(p['min_rms'])
                self.clip_thresh_spin.setValue(p['clipping_threshold'])
                self.clip_pct_spin.setValue(p['clipping_max_percent'] * 100)
        
        def _get_defaults(self) -> Dict[str, Any]:
            return {'preset': 'Moderate', 'max_amplitude': None, 'min_rms': 1e-10,
                    'clipping_threshold': 0.95, 'clipping_max_percent': 0.01}
        
        def _collect_params(self) -> Dict[str, Any]:
            return {
                'preset': self.preset_combo.currentText(),
                'max_amplitude': self.max_amp_spin.value() if self.max_amp_check.isChecked() else None,
                'min_rms': self.min_rms_spin.value(),
                'clipping_threshold': self.clip_thresh_spin.value(),
                'clipping_max_percent': self.clip_pct_spin.value() / 100.0,
            }
        
        def _apply_params(self, params: Dict[str, Any]):
            preset = params.get('preset', 'Moderate')
            idx = self.preset_combo.findText(preset)
            if idx >= 0:
                self.preset_combo.setCurrentIndex(idx)
            max_amp = params.get('max_amplitude')
            self.max_amp_check.setChecked(max_amp is not None)
            if max_amp is not None:
                self.max_amp_spin.setValue(max_amp)
            self.min_rms_spin.setValue(params.get('min_rms', 1e-10))
            self.clip_thresh_spin.setValue(params.get('clipping_threshold', 0.95))
            self.clip_pct_spin.setValue(params.get('clipping_max_percent', 0.01) * 100)


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
            
            # STA length
            self.params_layout.addWidget(QLabel("Short-Term Average (s):"), row, 0)
            self.sta_spin = QDoubleSpinBox()
            self.sta_spin.setRange(0.1, 10.0)
            self.sta_spin.setDecimals(1)
            self.sta_spin.setSingleStep(0.5)
            self.sta_spin.setValue(self._current_params.get('sta_length', 1.0))
            self.sta_spin.setToolTip("Length of short-term averaging window in seconds")
            self.params_layout.addWidget(self.sta_spin, row, 1)
            row += 1
            
            # LTA length
            self.params_layout.addWidget(QLabel("Long-Term Average (s):"), row, 0)
            self.lta_spin = QDoubleSpinBox()
            self.lta_spin.setRange(1.0, 120.0)
            self.lta_spin.setDecimals(1)
            self.lta_spin.setSingleStep(5.0)
            self.lta_spin.setValue(self._current_params.get('lta_length', 30.0))
            self.lta_spin.setToolTip("Length of long-term averaging window in seconds")
            self.params_layout.addWidget(self.lta_spin, row, 1)
            row += 1
            
            # Min ratio
            self.params_layout.addWidget(QLabel("Minimum STA/LTA Ratio:"), row, 0)
            self.min_ratio_spin = QDoubleSpinBox()
            self.min_ratio_spin.setRange(0.01, 1.0)
            self.min_ratio_spin.setDecimals(2)
            self.min_ratio_spin.setSingleStep(0.05)
            self.min_ratio_spin.setValue(self._current_params.get('min_ratio', 0.2))
            self.min_ratio_spin.setToolTip("Windows with STA/LTA below this are rejected (too quiet)")
            self.params_layout.addWidget(self.min_ratio_spin, row, 1)
            row += 1
            
            # Max ratio
            self.params_layout.addWidget(QLabel("Maximum STA/LTA Ratio:"), row, 0)
            self.max_ratio_spin = QDoubleSpinBox()
            self.max_ratio_spin.setRange(1.0, 20.0)
            self.max_ratio_spin.setDecimals(1)
            self.max_ratio_spin.setSingleStep(0.5)
            self.max_ratio_spin.setValue(self._current_params.get('max_ratio', 2.5))
            self.max_ratio_spin.setToolTip("Windows with STA/LTA above this are rejected (transients)")
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


    class SpectralSpikeSettingsDialog(BaseAlgorithmDialog):
        """Settings dialog for Spectral Spike Detection algorithm."""
        
        def __init__(self, parent, current_params: Dict[str, Any]):
            super().__init__(
                parent,
                "Spectral Spike Detection",
                "Rejects windows with narrow-band noise (e.g., machine vibration).\n"
                "Analyzes frequency content for anomalous spectral peaks.",
                current_params
            )
        
        def _setup_parameters(self):
            self.params_layout.addWidget(QLabel("Spike Threshold (sigma):"), 0, 0)
            self.threshold_spin = QDoubleSpinBox()
            self.threshold_spin.setRange(1.0, 10.0)
            self.threshold_spin.setDecimals(1)
            self.threshold_spin.setSingleStep(0.5)
            self.threshold_spin.setValue(self._current_params.get('spike_threshold', 3.0))
            self.threshold_spin.setToolTip(
                "Standard deviations above mean for spike detection.\n"
                "Lower = more sensitive (rejects more), Higher = less sensitive"
            )
            self.params_layout.addWidget(self.threshold_spin, 0, 1)
        
        def _get_defaults(self) -> Dict[str, Any]:
            return ALGORITHM_DEFAULTS['spectral_spike'].copy()
        
        def _collect_params(self) -> Dict[str, Any]:
            return {'spike_threshold': self.threshold_spin.value()}
        
        def _apply_params(self, params: Dict[str, Any]):
            self.threshold_spin.setValue(params.get('spike_threshold', 3.0))


    class StatisticalOutlierSettingsDialog(BaseAlgorithmDialog):
        """Settings dialog for Statistical Outlier Detection algorithm."""
        
        def __init__(self, parent, current_params: Dict[str, Any]):
            super().__init__(
                parent,
                "Statistical Outlier Detection",
                "Rejects windows that are statistical outliers compared to other windows.\n"
                "Uses either IQR (Interquartile Range) or Z-score method.",
                current_params
            )
        
        def _setup_parameters(self):
            row = 0
            
            # Method
            self.params_layout.addWidget(QLabel("Detection Method:"), row, 0)
            self.method_combo = QComboBox()
            self.method_combo.addItems(['iqr', 'zscore'])
            method = self._current_params.get('method', 'iqr')
            idx = self.method_combo.findText(method)
            if idx >= 0:
                self.method_combo.setCurrentIndex(idx)
            self.method_combo.setToolTip(
                "IQR: Uses interquartile range (robust to outliers)\n"
                "Z-score: Uses standard deviation (assumes normal distribution)"
            )
            self.params_layout.addWidget(self.method_combo, row, 1)
            row += 1
            
            # Threshold
            self.params_layout.addWidget(QLabel("Threshold:"), row, 0)
            self.threshold_spin = QDoubleSpinBox()
            self.threshold_spin.setRange(0.5, 10.0)
            self.threshold_spin.setDecimals(1)
            self.threshold_spin.setSingleStep(0.5)
            self.threshold_spin.setValue(self._current_params.get('threshold', 2.0))
            self.threshold_spin.setToolTip(
                "For IQR: multiplier for IQR (1.5 = standard, 3.0 = lenient)\n"
                "For Z-score: number of standard deviations"
            )
            self.params_layout.addWidget(self.threshold_spin, row, 1)
        
        def _get_defaults(self) -> Dict[str, Any]:
            return ALGORITHM_DEFAULTS['statistical_outlier'].copy()
        
        def _collect_params(self) -> Dict[str, Any]:
            return {
                'method': self.method_combo.currentText(),
                'threshold': self.threshold_spin.value()
            }
        
        def _apply_params(self, params: Dict[str, Any]):
            method = params.get('method', 'iqr')
            idx = self.method_combo.findText(method)
            if idx >= 0:
                self.method_combo.setCurrentIndex(idx)
            self.threshold_spin.setValue(params.get('threshold', 2.0))


    class FDWRASettingsDialog(BaseAlgorithmDialog):
        """Settings dialog for Peak Frequency Consistency (FDWRA) algorithm."""
        
        def __init__(self, parent, current_params: Dict[str, Any]):
            super().__init__(
                parent,
                "Peak Frequency Consistency (FDWRA)",
                "Industry-standard algorithm for ensuring peak frequency consistency.\n"
                "Iteratively removes windows whose peak frequencies deviate from the group consensus.\n"
                "Essential for publication-quality results.",
                current_params
            )
        
        def _setup_parameters(self):
            row = 0
            
            # N value
            self.params_layout.addWidget(QLabel("n-value:"), row, 0)
            self.n_spin = QDoubleSpinBox()
            self.n_spin.setRange(0.5, 10.0)
            self.n_spin.setDecimals(1)
            self.n_spin.setSingleStep(0.5)
            self.n_spin.setValue(self._current_params.get('n', 2.0))
            self.n_spin.setToolTip(
                "Standard deviation multiplier for rejection threshold.\n"
                "Lower = stricter rejection (more windows rejected)\n"
                "Typical values: 1.5-3.0, Default: 2.0"
            )
            self.params_layout.addWidget(self.n_spin, row, 1)
            row += 1
            
            # Max iterations
            self.params_layout.addWidget(QLabel("Max Iterations:"), row, 0)
            self.max_iter_spin = QSpinBox()
            self.max_iter_spin.setRange(1, 100)
            self.max_iter_spin.setValue(self._current_params.get('max_iterations', 50))
            self.max_iter_spin.setToolTip("Maximum number of rejection iterations before stopping")
            self.params_layout.addWidget(self.max_iter_spin, row, 1)
            row += 1
            
            # Min iterations
            self.params_layout.addWidget(QLabel("Min Iterations:"), row, 0)
            self.min_iter_spin = QSpinBox()
            self.min_iter_spin.setRange(1, 50)
            self.min_iter_spin.setValue(self._current_params.get('min_iterations', 1))
            self.min_iter_spin.setToolTip(
                "Minimum iterations before checking convergence.\n"
                "Set higher to force more rejection passes."
            )
            self.params_layout.addWidget(self.min_iter_spin, row, 1)
            row += 1
            
            # Distribution
            self.params_layout.addWidget(QLabel("Distribution:"), row, 0)
            self.dist_combo = QComboBox()
            self.dist_combo.addItems(['lognormal', 'normal'])
            dist = self._current_params.get('distribution_fn', 'lognormal')
            idx = self.dist_combo.findText(dist)
            if idx >= 0:
                self.dist_combo.setCurrentIndex(idx)
            self.dist_combo.setToolTip(
                "Statistical distribution for peak frequency modeling.\n"
                "Lognormal: Better for natural frequency distributions (recommended)\n"
                "Normal: Standard Gaussian distribution"
            )
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
        """Settings dialog for HVSR Peak Amplitude Bounds algorithm."""
        
        def __init__(self, parent, current_params: Dict[str, Any]):
            super().__init__(
                parent,
                "HVSR Peak Amplitude Bounds",
                "Rejects windows where the H/V ratio peak is outside acceptable bounds.\n"
                "Peak < min indicates poor response. Peak > max indicates sensor issues.",
                current_params
            )
        
        def _setup_parameters(self):
            row = 0
            
            # Min amplitude
            self.params_layout.addWidget(QLabel("Minimum Peak Amplitude:"), row, 0)
            self.min_spin = QDoubleSpinBox()
            self.min_spin.setRange(0.1, 10.0)
            self.min_spin.setDecimals(1)
            self.min_spin.setSingleStep(0.1)
            self.min_spin.setValue(self._current_params.get('min_amplitude', 1.0))
            self.min_spin.setToolTip(
                "Minimum acceptable HVSR peak amplitude.\n"
                "Windows with peak < this value are rejected.\n"
                "Default: 1.0 (H/V should be > 1 at resonance)"
            )
            self.params_layout.addWidget(self.min_spin, row, 1)
            row += 1
            
            # Max amplitude
            self.params_layout.addWidget(QLabel("Maximum Peak Amplitude:"), row, 0)
            self.max_spin = QDoubleSpinBox()
            self.max_spin.setRange(1.0, 100.0)
            self.max_spin.setDecimals(1)
            self.max_spin.setSingleStep(1.0)
            self.max_spin.setValue(self._current_params.get('max_amplitude', 15.0))
            self.max_spin.setToolTip(
                "Maximum acceptable HVSR peak amplitude.\n"
                "Windows with peak > this value are rejected.\n"
                "Default: 15.0 (very high H/V suggests sensor issues)"
            )
            self.params_layout.addWidget(self.max_spin, row, 1)
        
        def _get_defaults(self) -> Dict[str, Any]:
            return ALGORITHM_DEFAULTS['hvsr_amplitude'].copy()
        
        def _collect_params(self) -> Dict[str, Any]:
            return {
                'min_amplitude': self.min_spin.value(),
                'max_amplitude': self.max_spin.value()
            }
        
        def _apply_params(self, params: Dict[str, Any]):
            self.min_spin.setValue(params.get('min_amplitude', 1.0))
            self.max_spin.setValue(params.get('max_amplitude', 15.0))


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
            self.threshold_spin.setToolTip(
                "Peak flatness threshold.\n"
                "Lower = stricter (rejects flatter peaks)\n"
                "Higher = more lenient"
            )
            self.params_layout.addWidget(self.threshold_spin, 0, 1)
        
        def _get_defaults(self) -> Dict[str, Any]:
            return ALGORITHM_DEFAULTS['flat_peak'].copy()
        
        def _collect_params(self) -> Dict[str, Any]:
            return {'flatness_threshold': self.threshold_spin.value()}
        
        def _apply_params(self, params: Dict[str, Any]):
            self.threshold_spin.setValue(params.get('flatness_threshold', 0.15))


    # Dialog mapping
    DIALOG_CLASSES = {
        'amplitude': AmplitudeSettingsDialog,
        'sta_lta': STALTASettingsDialog,
        'spectral_spike': SpectralSpikeSettingsDialog,
        'statistical_outlier': StatisticalOutlierSettingsDialog,
        'fdwra': FDWRASettingsDialog,
        'hvsr_amplitude': HVSRAmplitudeSettingsDialog,
        'flat_peak': FlatPeakSettingsDialog
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
            from PyQt5.QtWidgets import QMessageBox
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
    def open_algorithm_settings_dialog(*args, **kwargs):
        raise ImportError("PyQt5 is required for GUI functionality")
