"""
Advanced QC Settings Dialog
============================

Dialog for customizing individual QC algorithms and their thresholds.
"""

try:
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
        QCheckBox, QLabel, QDoubleSpinBox, QPushButton,
        QScrollArea, QWidget, QSpinBox
    )
    from PyQt5.QtCore import Qt
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


class AdvancedQCDialog(QDialog):
    """Dialog for advanced QC settings configuration."""

    def __init__(self, parent=None, current_settings=None):
        super().__init__(parent)
        self.setWindowTitle("Advanced QC Settings")
        self.setMinimumWidth(600)
        self.setMinimumHeight(700)

        # Initialize settings with defaults
        if current_settings:
            self.settings = current_settings.copy()
        else:
            self.settings = self._get_default_settings()

        self.init_ui()

    def _get_default_settings(self):
        """Get default QC settings."""
        return {
            'enabled': True,
            'algorithms': {
                'amplitude': {
                    'enabled': True,
                    'params': {}
                },
                'quality_threshold': {
                    'enabled': False,
                    'params': {'threshold': 0.5}
                },
                'sta_lta': {
                    'enabled': False,
                    'params': {
                        'sta_length': 1.0,
                        'lta_length': 30.0,
                        'min_ratio': 0.15,
                        'max_ratio': 2.5
                    }
                },
                'frequency_domain': {
                    'enabled': False,
                    'params': {'spike_threshold': 3.0}
                },
                'statistical_outlier': {
                    'enabled': False,
                    'params': {
                        'method': 'iqr',
                        'threshold': 2.0
                    }
                }
            }
        }

    def init_ui(self):
        """Initialize the UI."""
        layout = QVBoxLayout()

        # Master enable/disable
        self.master_enable = QCheckBox("Enable Quality Control")
        self.master_enable.setChecked(self.settings['enabled'])
        self.master_enable.setStyleSheet("font-weight: bold; font-size: 12pt;")
        self.master_enable.toggled.connect(self._on_master_toggle)
        layout.addWidget(self.master_enable)

        # Scroll area for algorithm settings
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # Store UI elements
        self.ui_elements = {}

        # Amplitude Rejection
        amp_group = self._create_algorithm_group(
            "Amplitude Rejection",
            "amplitude",
            "Rejects windows with extremely high or low amplitudes (transients, dead periods)",
            []
        )
        scroll_layout.addWidget(amp_group)

        # Quality Threshold Rejection
        quality_params = [
            ("Threshold:", "threshold", 0.0, 1.0, 0.5, 2, 0.05,
             "Overall quality score threshold (0-1, lower is more strict)")
        ]
        quality_group = self._create_algorithm_group(
            "Quality Threshold Rejection",
            "quality_threshold",
            "Rejects windows below overall quality threshold (SNR, stationarity, energy)",
            quality_params
        )
        scroll_layout.addWidget(quality_group)

        # STA/LTA Rejection
        stalta_params = [
            ("STA Length (s):", "sta_length", 0.1, 10.0, 1.0, 2, 0.1,
             "Short-term average window length"),
            ("LTA Length (s):", "lta_length", 5.0, 60.0, 30.0, 1, 1.0,
             "Long-term average window length"),
            ("Min Ratio:", "min_ratio", 0.01, 1.0, 0.15, 2, 0.01,
             "Minimum STA/LTA ratio (rejects if below)"),
            ("Max Ratio:", "max_ratio", 1.0, 10.0, 2.5, 2, 0.1,
             "Maximum STA/LTA ratio (rejects if above)")
        ]
        stalta_group = self._create_algorithm_group(
            "STA/LTA Rejection",
            "sta_lta",
            "Rejects windows with unusual energy levels (earthquakes, transients)",
            stalta_params
        )
        scroll_layout.addWidget(stalta_group)

        # Frequency Domain Rejection
        freq_params = [
            ("Spike Threshold:", "spike_threshold", 1.0, 10.0, 3.0, 1, 0.5,
             "Threshold for detecting spectral spikes (σ)")
        ]
        freq_group = self._create_algorithm_group(
            "Frequency Domain Rejection",
            "frequency_domain",
            "Rejects windows with spectral anomalies (narrow-band noise)",
            freq_params
        )
        scroll_layout.addWidget(freq_group)

        # Statistical Outlier Rejection
        stats_params = [
            ("Threshold:", "threshold", 1.0, 5.0, 2.0, 1, 0.5,
             "IQR multiplier for outlier detection (higher = more lenient)")
        ]
        stats_group = self._create_algorithm_group(
            "Statistical Outlier Rejection",
            "statistical_outlier",
            "Rejects windows that are statistical outliers (IQR method)",
            stats_params
        )
        scroll_layout.addWidget(stats_group)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Buttons
        button_layout = QHBoxLayout()

        reset_btn = QPushButton("Reset to Defaults")
        reset_btn.clicked.connect(self._reset_to_defaults)
        button_layout.addWidget(reset_btn)

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

        # Apply initial enabled state
        self._on_master_toggle(self.master_enable.isChecked())

    def _create_algorithm_group(self, title, algo_key, description, params):
        """Create a group box for an algorithm."""
        group = QGroupBox(title)
        layout = QVBoxLayout()

        # Enable checkbox
        enable_check = QCheckBox("Enable this algorithm")
        enable_check.setChecked(self.settings['algorithms'][algo_key]['enabled'])
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

            spinbox = QDoubleSpinBox()
            spinbox.setRange(min_val, max_val)
            spinbox.setDecimals(decimals)
            spinbox.setSingleStep(step)
            spinbox.setValue(self.settings['algorithms'][algo_key]['params'].get(key, default))
            spinbox.setToolTip(tooltip)
            param_layout.addWidget(spinbox)

            param_widgets[key] = spinbox
            layout.addLayout(param_layout)

        # Store references
        self.ui_elements[algo_key] = {
            'group': group,
            'enable': enable_check,
            'params': param_widgets
        }

        # Connect enable checkbox to param widgets
        def toggle_params(enabled):
            for widget in param_widgets.values():
                widget.setEnabled(enabled)

        enable_check.toggled.connect(toggle_params)
        toggle_params(enable_check.isChecked())

        group.setLayout(layout)
        return group

    def _on_master_toggle(self, enabled):
        """Handle master enable/disable toggle."""
        for algo_data in self.ui_elements.values():
            algo_data['group'].setEnabled(enabled)

    def _reset_to_defaults(self):
        """Reset all settings to defaults."""
        defaults = self._get_default_settings()

        self.master_enable.setChecked(defaults['enabled'])

        for algo_key, algo_data in defaults['algorithms'].items():
            ui = self.ui_elements[algo_key]
            ui['enable'].setChecked(algo_data['enabled'])
            for param_key, param_value in algo_data['params'].items():
                if param_key in ui['params']:
                    ui['params'][param_key].setValue(param_value)

    def get_settings(self):
        """Get current settings from UI."""
        settings = {
            'enabled': self.master_enable.isChecked(),
            'algorithms': {}
        }

        for algo_key, ui in self.ui_elements.items():
            params = {}
            for param_key, spinbox in ui['params'].items():
                params[param_key] = spinbox.value()

            settings['algorithms'][algo_key] = {
                'enabled': ui['enable'].isChecked(),
                'params': params
            }

        return settings
