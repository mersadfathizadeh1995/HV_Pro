"""
Advanced QC Settings Dialog
============================

Dialog for customizing all QC algorithms and their thresholds.
Includes pre-HVSR, post-HVSR, Cox FDWRA, and ML algorithms.
"""

try:
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
        QCheckBox, QLabel, QDoubleSpinBox, QPushButton,
        QScrollArea, QWidget, QSpinBox, QComboBox,
        QTabWidget, QGridLayout, QFrame
    )
    from PyQt5.QtCore import Qt
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False

from hvsr_pro.processing.rejection.settings import (
    QCSettings,
    PRESET_DESCRIPTIONS,
    get_preset_names
)


class AdvancedQCDialog(QDialog):
    """
    Comprehensive dialog for advanced QC settings configuration.
    
    Includes all rejection algorithms:
    - Pre-HVSR (time-domain): Amplitude, Quality, STA/LTA, Frequency, Statistical
    - Post-HVSR (frequency-domain): HVSR Amplitude, Flat Peak
    - Cox FDWRA: Iterative peak consistency
    - ML (optional): Isolation Forest
    """

    def __init__(self, parent=None, settings: QCSettings = None):
        super().__init__(parent)
        self.setWindowTitle("Advanced QC Settings")
        self.setMinimumWidth(700)
        self.setMinimumHeight(800)

        # Initialize settings
        if settings is not None:
            self.settings = QCSettings.from_dict(settings.to_dict())  # Deep copy
        else:
            self.settings = QCSettings()

        self._init_ui()
        self._load_settings_to_ui()

    def _init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout()

        # Master enable/disable
        self.master_enable = QCheckBox("Enable Quality Control")
        self.master_enable.setStyleSheet("font-weight: bold; font-size: 12pt;")
        self.master_enable.toggled.connect(self._on_master_toggle)
        layout.addWidget(self.master_enable)

        # Tab widget for organized sections
        self.tabs = QTabWidget()
        
        # Pre-HVSR Tab
        pre_hvsr_tab = self._create_pre_hvsr_tab()
        self.tabs.addTab(pre_hvsr_tab, "Pre-HVSR (Time-Domain)")
        
        # Post-HVSR Tab
        post_hvsr_tab = self._create_post_hvsr_tab()
        self.tabs.addTab(post_hvsr_tab, "Post-HVSR (Frequency-Domain)")
        
        # Cox FDWRA Tab
        cox_tab = self._create_cox_tab()
        self.tabs.addTab(cox_tab, "Cox FDWRA")
        
        # ML Tab
        ml_tab = self._create_ml_tab()
        self.tabs.addTab(ml_tab, "ML Algorithms")
        
        layout.addWidget(self.tabs)

        # Buttons
        button_layout = QHBoxLayout()

        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self._reset_to_defaults)
        button_layout.addWidget(reset_btn)
        
        preset_btn = QPushButton("Apply Preset...")
        preset_btn.clicked.connect(self._show_preset_menu)
        button_layout.addWidget(preset_btn)

        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setDefault(True)
        button_layout.addWidget(ok_btn)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def _create_pre_hvsr_tab(self) -> QWidget:
        """Create Pre-HVSR algorithms tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # Info label
        info = QLabel(
            "<i>Pre-HVSR algorithms analyze time-domain waveforms before HVSR computation. "
            "They reject windows with obvious problems like transients, clipping, or anomalies.</i>"
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #666; padding: 5px;")
        scroll_layout.addWidget(info)

        # Amplitude Rejection
        self.amplitude_group = self._create_algorithm_group(
            "Amplitude Rejection",
            "Rejects windows with extremely high or low amplitudes (transients, dead periods, clipping)",
            []
        )
        scroll_layout.addWidget(self.amplitude_group)

        # Quality Threshold Rejection
        self.quality_group = self._create_algorithm_group(
            "Quality Threshold Rejection",
            "Rejects windows below overall quality threshold (combines SNR, stationarity, energy)",
            [
                ("Threshold:", "quality_threshold", 0.0, 1.0, 0.5, 2, 0.05,
                 "Overall quality score threshold (0-1, lower is more strict)")
            ]
        )
        scroll_layout.addWidget(self.quality_group)

        # STA/LTA Rejection
        self.stalta_group = self._create_algorithm_group(
            "STA/LTA Rejection",
            "Rejects windows with unusual energy levels using Short-Term/Long-Term Average ratio",
            [
                ("STA Length (s):", "sta_length", 0.1, 10.0, 1.0, 2, 0.1,
                 "Short-term average window length"),
                ("LTA Length (s):", "lta_length", 5.0, 60.0, 30.0, 1, 1.0,
                 "Long-term average window length"),
                ("Min Ratio:", "min_ratio", 0.01, 1.0, 0.15, 2, 0.01,
                 "Minimum STA/LTA ratio (rejects if below)"),
                ("Max Ratio:", "max_ratio", 1.0, 10.0, 2.5, 2, 0.1,
                 "Maximum STA/LTA ratio (rejects if above)")
            ]
        )
        scroll_layout.addWidget(self.stalta_group)

        # Frequency Domain Rejection
        self.freq_group = self._create_algorithm_group(
            "Frequency Domain Rejection",
            "Rejects windows with spectral anomalies (narrow-band noise, spikes)",
            [
                ("Spike Threshold:", "spike_threshold", 1.0, 10.0, 3.0, 1, 0.5,
                 "Threshold for detecting spectral spikes (in standard deviations)")
            ]
        )
        scroll_layout.addWidget(self.freq_group)

        # Statistical Outlier Rejection
        self.stats_group = self._create_algorithm_group(
            "Statistical Outlier Rejection",
            "Rejects windows that are statistical outliers using IQR or Z-score method",
            [
                ("Method:", "method_combo", None, None, None, None, None,
                 "Detection method"),
                ("Threshold:", "stats_threshold", 1.0, 5.0, 2.0, 1, 0.5,
                 "IQR multiplier or Z-score threshold (higher = more lenient)")
            ]
        )
        scroll_layout.addWidget(self.stats_group)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        return widget

    def _create_post_hvsr_tab(self) -> QWidget:
        """Create Post-HVSR algorithms tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Info label
        info = QLabel(
            "<i>Post-HVSR algorithms analyze computed HVSR curves. "
            "They reject windows with problematic spectral characteristics.</i>"
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #666; padding: 5px;")
        layout.addWidget(info)

        # HVSR Amplitude Rejection
        self.hvsr_amp_group = self._create_algorithm_group(
            "HVSR Peak Amplitude Rejection",
            "Rejects windows where HVSR peak amplitude is below threshold (indicates poor H/V contrast)",
            [
                ("Min Amplitude:", "min_amplitude", 0.5, 10.0, 1.0, 2, 0.1,
                 "Minimum HVSR peak amplitude (typical threshold: 1.0)")
            ]
        )
        layout.addWidget(self.hvsr_amp_group)

        # Flat Peak Detection
        self.flat_peak_group = self._create_algorithm_group(
            "Flat Peak Detection",
            "Rejects windows with flat, wide, or multiple peaks (indicates unclear resonance)",
            [
                ("Flatness Threshold:", "flatness_threshold", 0.01, 0.5, 0.15, 2, 0.01,
                 "Peak flatness threshold (lower = stricter)")
            ]
        )
        layout.addWidget(self.flat_peak_group)

        # Curve Outlier Rejection
        self.curve_outlier_group = self._create_algorithm_group(
            "Curve Outlier Rejection (Median-MAD)",
            "Iterative sigma clipping on H/V curves. Rejects windows whose curve deviates strongly from the population median.",
            [
                ("Threshold (sigma):", "threshold", 1.0, 10.0, 3.0, 1, 0.5,
                 "Number of scaled-MAD units to flag as outlier (lower = stricter)"),
                ("Max Iterations:", "max_iterations", 1.0, 20.0, 5.0, 0, 1.0,
                 "Maximum sigma-clipping iterations"),
            ]
        )
        layout.addWidget(self.curve_outlier_group)

        layout.addStretch()
        return widget

    def _create_cox_tab(self) -> QWidget:
        """Create Cox FDWRA settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Info label
        info = QLabel(
            "<i>Cox et al. (2020) Frequency-Domain Window Rejection Algorithm (FDWRA) "
            "iteratively removes windows whose peak frequencies deviate from the group consensus. "
            "This is the industry-standard algorithm for publication-quality HVSR analysis.</i>"
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #666; padding: 5px;")
        layout.addWidget(info)
        
        # Enable checkbox
        self.cox_enable = QCheckBox("Enable Cox FDWRA")
        self.cox_enable.setStyleSheet("font-weight: bold;")
        self.cox_enable.toggled.connect(self._on_cox_toggle)
        layout.addWidget(self.cox_enable)
        
        # Settings group
        self.cox_settings_widget = QWidget()
        cox_layout = QGridLayout(self.cox_settings_widget)
        cox_layout.setColumnStretch(1, 1)
        
        row = 0
        
        # N-value
        cox_layout.addWidget(QLabel("n-value (sigma):"), row, 0)
        self.cox_n_spin = QDoubleSpinBox()
        self.cox_n_spin.setRange(0.5, 10.0)
        self.cox_n_spin.setValue(2.0)
        self.cox_n_spin.setDecimals(1)
        self.cox_n_spin.setSingleStep(0.5)
        self.cox_n_spin.setToolTip(
            "Number of standard deviations for rejection bounds.\n"
            "Lower = stricter rejection (more windows removed).\n"
            "Typical values: 1.5-3.0"
        )
        cox_layout.addWidget(self.cox_n_spin, row, 1)
        row += 1
        
        # Max iterations
        cox_layout.addWidget(QLabel("Max Iterations:"), row, 0)
        self.cox_max_iter_spin = QSpinBox()
        self.cox_max_iter_spin.setRange(1, 100)
        self.cox_max_iter_spin.setValue(50)
        self.cox_max_iter_spin.setToolTip("Maximum iterations before stopping")
        cox_layout.addWidget(self.cox_max_iter_spin, row, 1)
        row += 1
        
        # Min iterations
        cox_layout.addWidget(QLabel("Min Iterations:"), row, 0)
        self.cox_min_iter_spin = QSpinBox()
        self.cox_min_iter_spin.setRange(1, 50)
        self.cox_min_iter_spin.setValue(1)
        self.cox_min_iter_spin.setToolTip(
            "Minimum iterations before checking convergence.\n"
            "Set higher to force more rejection passes."
        )
        cox_layout.addWidget(self.cox_min_iter_spin, row, 1)
        row += 1
        
        # Distribution for fn
        cox_layout.addWidget(QLabel("fn Distribution:"), row, 0)
        self.cox_dist_fn_combo = QComboBox()
        self.cox_dist_fn_combo.addItems(["lognormal", "normal"])
        self.cox_dist_fn_combo.setToolTip(
            "Statistical distribution for peak frequency (fn) modeling.\n"
            "Lognormal is recommended for most cases."
        )
        cox_layout.addWidget(self.cox_dist_fn_combo, row, 1)
        row += 1
        
        # Distribution for mc
        cox_layout.addWidget(QLabel("Mean Curve Distribution:"), row, 0)
        self.cox_dist_mc_combo = QComboBox()
        self.cox_dist_mc_combo.addItems(["lognormal", "normal"])
        self.cox_dist_mc_combo.setToolTip("Statistical distribution for mean curve modeling")
        cox_layout.addWidget(self.cox_dist_mc_combo, row, 1)
        row += 1
        
        # Convergence thresholds
        cox_layout.addWidget(QLabel("Convergence (diff):"), row, 0)
        self.cox_conv_diff_spin = QDoubleSpinBox()
        self.cox_conv_diff_spin.setRange(0.001, 0.1)
        self.cox_conv_diff_spin.setValue(0.01)
        self.cox_conv_diff_spin.setDecimals(3)
        self.cox_conv_diff_spin.setSingleStep(0.005)
        self.cox_conv_diff_spin.setToolTip("Convergence threshold for difference metric")
        cox_layout.addWidget(self.cox_conv_diff_spin, row, 1)
        row += 1
        
        cox_layout.addWidget(QLabel("Convergence (std):"), row, 0)
        self.cox_conv_std_spin = QDoubleSpinBox()
        self.cox_conv_std_spin.setRange(0.001, 0.1)
        self.cox_conv_std_spin.setValue(0.01)
        self.cox_conv_std_spin.setDecimals(3)
        self.cox_conv_std_spin.setSingleStep(0.005)
        self.cox_conv_std_spin.setToolTip("Convergence threshold for standard deviation")
        cox_layout.addWidget(self.cox_conv_std_spin, row, 1)
        row += 1
        
        # Search range
        search_frame = QFrame()
        search_layout = QHBoxLayout(search_frame)
        search_layout.setContentsMargins(0, 0, 0, 0)
        
        self.cox_search_check = QCheckBox("Limit search range:")
        self.cox_search_check.toggled.connect(self._on_cox_search_toggle)
        search_layout.addWidget(self.cox_search_check)
        
        self.cox_search_min = QDoubleSpinBox()
        self.cox_search_min.setRange(0.1, 50.0)
        self.cox_search_min.setValue(0.5)
        self.cox_search_min.setSuffix(" Hz")
        self.cox_search_min.setEnabled(False)
        search_layout.addWidget(self.cox_search_min)
        
        search_layout.addWidget(QLabel("to"))
        
        self.cox_search_max = QDoubleSpinBox()
        self.cox_search_max.setRange(0.5, 100.0)
        self.cox_search_max.setValue(20.0)
        self.cox_search_max.setSuffix(" Hz")
        self.cox_search_max.setEnabled(False)
        search_layout.addWidget(self.cox_search_max)
        
        search_layout.addStretch()
        
        cox_layout.addWidget(search_frame, row, 0, 1, 2)
        
        layout.addWidget(self.cox_settings_widget)
        layout.addStretch()
        
        return widget

    def _create_ml_tab(self) -> QWidget:
        """Create ML algorithms tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Info label
        info = QLabel(
            "<i>Machine Learning algorithms use anomaly detection to identify problematic windows. "
            "These are experimental and require scikit-learn to be installed.</i>"
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #666; padding: 5px;")
        layout.addWidget(info)
        
        # Check sklearn availability
        try:
            import sklearn
            sklearn_available = True
        except ImportError:
            sklearn_available = False
        
        if not sklearn_available:
            warning = QLabel(
                "<b style='color: orange;'>scikit-learn not installed.</b><br>"
                "Install with: <code>pip install scikit-learn</code>"
            )
            warning.setWordWrap(True)
            layout.addWidget(warning)
        
        # Isolation Forest
        self.isolation_group = self._create_algorithm_group(
            "Isolation Forest Anomaly Detection",
            "Uses ensemble of isolation trees to detect anomalous windows",
            [
                ("Contamination:", "contamination", 0.01, 0.5, 0.1, 2, 0.01,
                 "Expected proportion of outliers (0.1 = 10%)"),
                ("N Estimators:", "n_estimators", 10, 500, 100, 0, 10,
                 "Number of isolation trees")
            ]
        )
        self.isolation_group.setEnabled(sklearn_available)
        layout.addWidget(self.isolation_group)
        
        layout.addStretch()
        return widget

    def _create_algorithm_group(self, title: str, description: str, params: list) -> QGroupBox:
        """
        Create a group box for an algorithm.
        
        Args:
            title: Group title
            description: Algorithm description
            params: List of parameter specs
                   [(label, key, min, max, default, decimals, step, tooltip), ...]
        """
        group = QGroupBox(title)
        layout = QVBoxLayout()

        # Enable checkbox
        enable_check = QCheckBox("Enable this algorithm")
        enable_check.setStyleSheet("font-weight: bold;")
        layout.addWidget(enable_check)

        # Description
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(desc_label)

        # Parameters
        param_widgets = {}
        for param_spec in params:
            label, key, min_val, max_val, default, decimals, step, tooltip = param_spec

            param_layout = QHBoxLayout()
            param_layout.addWidget(QLabel(label))

            if key == 'method_combo':
                # Special case for combo box
                combo = QComboBox()
                combo.addItems(['iqr', 'zscore'])
                combo.setToolTip(tooltip)
                param_layout.addWidget(combo)
                param_widgets[key] = combo
            elif decimals == 0:
                # Integer spinner
                spinbox = QSpinBox()
                spinbox.setRange(int(min_val), int(max_val))
                spinbox.setSingleStep(int(step))
                spinbox.setValue(int(default))
                spinbox.setToolTip(tooltip)
                param_layout.addWidget(spinbox)
                param_widgets[key] = spinbox
            else:
                # Float spinner
                spinbox = QDoubleSpinBox()
                spinbox.setRange(min_val, max_val)
                spinbox.setDecimals(decimals)
                spinbox.setSingleStep(step)
                spinbox.setValue(default)
                spinbox.setToolTip(tooltip)
                param_layout.addWidget(spinbox)
                param_widgets[key] = spinbox

            layout.addLayout(param_layout)

        # Store references
        group._enable_check = enable_check
        group._param_widgets = param_widgets

        # Connect enable checkbox to param widgets
        def toggle_params(enabled):
            for widget in param_widgets.values():
                widget.setEnabled(enabled)

        enable_check.toggled.connect(toggle_params)
        toggle_params(enable_check.isChecked())

        group.setLayout(layout)
        return group

    def _on_master_toggle(self, enabled: bool):
        """Handle master enable/disable toggle."""
        self.tabs.setEnabled(enabled)

    def _on_cox_toggle(self, enabled: bool):
        """Handle Cox FDWRA enable toggle."""
        self.cox_settings_widget.setEnabled(enabled)

    def _on_cox_search_toggle(self, enabled: bool):
        """Handle Cox search range checkbox toggle."""
        self.cox_search_min.setEnabled(enabled)
        self.cox_search_max.setEnabled(enabled)

    def _load_settings_to_ui(self):
        """Load settings from QCSettings to UI widgets."""
        s = self.settings
        
        # Master enable
        self.master_enable.setChecked(s.enabled)
        
        # Amplitude
        self.amplitude_group._enable_check.setChecked(s.amplitude.enabled)
        
        # Quality threshold
        self.quality_group._enable_check.setChecked(s.quality_threshold.enabled)
        if 'quality_threshold' in self.quality_group._param_widgets:
            self.quality_group._param_widgets['quality_threshold'].setValue(
                s.quality_threshold.params.get('threshold', 0.5)
            )
        
        # STA/LTA
        self.stalta_group._enable_check.setChecked(s.sta_lta.enabled)
        params = s.sta_lta.params
        if 'sta_length' in self.stalta_group._param_widgets:
            self.stalta_group._param_widgets['sta_length'].setValue(params.get('sta_length', 1.0))
        if 'lta_length' in self.stalta_group._param_widgets:
            self.stalta_group._param_widgets['lta_length'].setValue(params.get('lta_length', 30.0))
        if 'min_ratio' in self.stalta_group._param_widgets:
            self.stalta_group._param_widgets['min_ratio'].setValue(params.get('min_ratio', 0.15))
        if 'max_ratio' in self.stalta_group._param_widgets:
            self.stalta_group._param_widgets['max_ratio'].setValue(params.get('max_ratio', 2.5))
        
        # Frequency domain
        self.freq_group._enable_check.setChecked(s.frequency_domain.enabled)
        if 'spike_threshold' in self.freq_group._param_widgets:
            self.freq_group._param_widgets['spike_threshold'].setValue(
                s.frequency_domain.params.get('spike_threshold', 3.0)
            )
        
        # Statistical outlier
        self.stats_group._enable_check.setChecked(s.statistical_outlier.enabled)
        params = s.statistical_outlier.params
        if 'method_combo' in self.stats_group._param_widgets:
            method = params.get('method', 'iqr')
            idx = self.stats_group._param_widgets['method_combo'].findText(method)
            if idx >= 0:
                self.stats_group._param_widgets['method_combo'].setCurrentIndex(idx)
        if 'stats_threshold' in self.stats_group._param_widgets:
            self.stats_group._param_widgets['stats_threshold'].setValue(params.get('threshold', 2.0))
        
        # HVSR Amplitude
        self.hvsr_amp_group._enable_check.setChecked(s.hvsr_amplitude.enabled)
        if 'min_amplitude' in self.hvsr_amp_group._param_widgets:
            self.hvsr_amp_group._param_widgets['min_amplitude'].setValue(
                s.hvsr_amplitude.params.get('min_amplitude', 1.0)
            )
        
        # Flat peak
        self.flat_peak_group._enable_check.setChecked(s.flat_peak.enabled)
        if 'flatness_threshold' in self.flat_peak_group._param_widgets:
            self.flat_peak_group._param_widgets['flatness_threshold'].setValue(
                s.flat_peak.params.get('flatness_threshold', 0.15)
            )
        
        # Cox FDWRA
        self.cox_enable.setChecked(s.cox_fdwra.enabled)
        self.cox_n_spin.setValue(s.cox_fdwra.n)
        self.cox_max_iter_spin.setValue(s.cox_fdwra.max_iterations)
        self.cox_min_iter_spin.setValue(s.cox_fdwra.min_iterations)
        
        idx = self.cox_dist_fn_combo.findText(s.cox_fdwra.distribution_fn)
        if idx >= 0:
            self.cox_dist_fn_combo.setCurrentIndex(idx)
        
        idx = self.cox_dist_mc_combo.findText(s.cox_fdwra.distribution_mc)
        if idx >= 0:
            self.cox_dist_mc_combo.setCurrentIndex(idx)
        
        self.cox_conv_diff_spin.setValue(s.cox_fdwra.convergence_threshold_diff)
        self.cox_conv_std_spin.setValue(s.cox_fdwra.convergence_threshold_std)
        
        if s.cox_fdwra.search_range_hz:
            self.cox_search_check.setChecked(True)
            self.cox_search_min.setValue(s.cox_fdwra.search_range_hz[0])
            self.cox_search_max.setValue(s.cox_fdwra.search_range_hz[1])
        else:
            self.cox_search_check.setChecked(False)
        
        self._on_cox_toggle(s.cox_fdwra.enabled)
        
        # Isolation Forest
        self.isolation_group._enable_check.setChecked(s.isolation_forest.enabled)
        params = s.isolation_forest.params
        if 'contamination' in self.isolation_group._param_widgets:
            self.isolation_group._param_widgets['contamination'].setValue(params.get('contamination', 0.1))
        if 'n_estimators' in self.isolation_group._param_widgets:
            self.isolation_group._param_widgets['n_estimators'].setValue(params.get('n_estimators', 100))

    def _save_ui_to_settings(self):
        """Save UI widget values to QCSettings."""
        s = self.settings
        
        # Master enable
        s.enabled = self.master_enable.isChecked()
        s.mode = 'custom'  # Always custom when using advanced dialog
        
        # Amplitude
        s.amplitude.enabled = self.amplitude_group._enable_check.isChecked()
        
        # Quality threshold
        s.quality_threshold.enabled = self.quality_group._enable_check.isChecked()
        if 'quality_threshold' in self.quality_group._param_widgets:
            s.quality_threshold.params['threshold'] = self.quality_group._param_widgets['quality_threshold'].value()
        
        # STA/LTA
        s.sta_lta.enabled = self.stalta_group._enable_check.isChecked()
        if 'sta_length' in self.stalta_group._param_widgets:
            s.sta_lta.params['sta_length'] = self.stalta_group._param_widgets['sta_length'].value()
        if 'lta_length' in self.stalta_group._param_widgets:
            s.sta_lta.params['lta_length'] = self.stalta_group._param_widgets['lta_length'].value()
        if 'min_ratio' in self.stalta_group._param_widgets:
            s.sta_lta.params['min_ratio'] = self.stalta_group._param_widgets['min_ratio'].value()
        if 'max_ratio' in self.stalta_group._param_widgets:
            s.sta_lta.params['max_ratio'] = self.stalta_group._param_widgets['max_ratio'].value()
        
        # Frequency domain
        s.frequency_domain.enabled = self.freq_group._enable_check.isChecked()
        if 'spike_threshold' in self.freq_group._param_widgets:
            s.frequency_domain.params['spike_threshold'] = self.freq_group._param_widgets['spike_threshold'].value()
        
        # Statistical outlier
        s.statistical_outlier.enabled = self.stats_group._enable_check.isChecked()
        if 'method_combo' in self.stats_group._param_widgets:
            s.statistical_outlier.params['method'] = self.stats_group._param_widgets['method_combo'].currentText()
        if 'stats_threshold' in self.stats_group._param_widgets:
            s.statistical_outlier.params['threshold'] = self.stats_group._param_widgets['stats_threshold'].value()
        
        # HVSR Amplitude
        s.hvsr_amplitude.enabled = self.hvsr_amp_group._enable_check.isChecked()
        if 'min_amplitude' in self.hvsr_amp_group._param_widgets:
            s.hvsr_amplitude.params['min_amplitude'] = self.hvsr_amp_group._param_widgets['min_amplitude'].value()
        
        # Flat peak
        s.flat_peak.enabled = self.flat_peak_group._enable_check.isChecked()
        if 'flatness_threshold' in self.flat_peak_group._param_widgets:
            s.flat_peak.params['flatness_threshold'] = self.flat_peak_group._param_widgets['flatness_threshold'].value()
        
        # Cox FDWRA
        s.cox_fdwra.enabled = self.cox_enable.isChecked()
        s.cox_fdwra.n = self.cox_n_spin.value()
        s.cox_fdwra.max_iterations = self.cox_max_iter_spin.value()
        s.cox_fdwra.min_iterations = self.cox_min_iter_spin.value()
        s.cox_fdwra.distribution_fn = self.cox_dist_fn_combo.currentText()
        s.cox_fdwra.distribution_mc = self.cox_dist_mc_combo.currentText()
        s.cox_fdwra.convergence_threshold_diff = self.cox_conv_diff_spin.value()
        s.cox_fdwra.convergence_threshold_std = self.cox_conv_std_spin.value()
        
        if self.cox_search_check.isChecked():
            s.cox_fdwra.search_range_hz = (
                self.cox_search_min.value(),
                self.cox_search_max.value()
            )
        else:
            s.cox_fdwra.search_range_hz = None
        
        # Isolation Forest
        s.isolation_forest.enabled = self.isolation_group._enable_check.isChecked()
        if 'contamination' in self.isolation_group._param_widgets:
            s.isolation_forest.params['contamination'] = self.isolation_group._param_widgets['contamination'].value()
        if 'n_estimators' in self.isolation_group._param_widgets:
            s.isolation_forest.params['n_estimators'] = int(self.isolation_group._param_widgets['n_estimators'].value())

    def _reset_to_defaults(self):
        """Reset all settings to defaults."""
        self.settings = QCSettings()
        self._load_settings_to_ui()

    def _show_preset_menu(self):
        """Show preset selection menu."""
        from PyQt5.QtWidgets import QMenu, QAction
        
        menu = QMenu(self)
        
        for preset in get_preset_names():
            action = QAction(f"{preset.title()}: {PRESET_DESCRIPTIONS[preset][:50]}...", self)
            action.setData(preset)
            action.triggered.connect(lambda checked, p=preset: self._apply_preset(p))
            menu.addAction(action)
        
        # Show menu at button position
        btn = self.sender()
        if btn:
            menu.exec_(btn.mapToGlobal(btn.rect().bottomLeft()))

    def _apply_preset(self, preset: str):
        """Apply a preset configuration."""
        self.settings.apply_preset(preset)
        self._load_settings_to_ui()

    def get_settings(self) -> QCSettings:
        """Get current settings from UI."""
        self._save_ui_to_settings()
        return self.settings

    def accept(self):
        """Handle dialog acceptance."""
        self._save_ui_to_settings()
        super().accept()
