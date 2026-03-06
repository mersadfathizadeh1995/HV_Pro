"""
Figure Export Dialog
=====================

Popup dialog for selecting which hvsr_pro figures to generate in auto-mode,
with DPI, format, and figure size options.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QGridLayout,
    QCheckBox, QSpinBox, QComboBox, QLabel, QPushButton,
    QDialogButtonBox,
)
from PyQt5.QtCore import Qt


# All available figure types mapped to human-readable labels
FIGURE_TYPES = {
    # HVSR Curves
    'fig_standard': 'Standard HVSR (accepted windows + mean)',
    'fig_hvsr_curve': 'HVSR Curve (with uncertainty band)',
    'fig_mean_vs_median': 'Mean vs Median comparison',
    'fig_components': 'Component Spectra (E/N/V + H/V)',
    'fig_with_windows': 'HVSR with Individual Windows overlay',
    # Statistics
    'fig_statistics': '4-Panel Statistics (mean, median, std, summary)',
    'fig_peak_analysis': 'Peak Analysis (width & prominence detail)',
    'fig_peak_details': 'Peak Details (primary peak analysis)',
    # Windows
    'fig_window_overview': 'Window Collection Overview (status + quality)',
    'fig_quality_grid': 'Quality Metrics Grid',
    'fig_quality_histogram': 'Quality Score Distribution',
    'fig_rejection_timeline': 'Rejection Timeline',
    # Comparison
    'fig_raw_vs_adjusted': 'Raw vs Adjusted HVSR (dual-panel)',
    'fig_pre_post_rejection': 'Pre & Post Rejection (5-panel waveform+HVSR)',
    # Waveform
    'fig_waveform_3c': '3-Component Waveform with rejection markers',
    'fig_window_timeseries': 'Window Timeseries (3-component)',
    'fig_window_spectrogram': 'Window Spectrogram',
    # Report
    'fig_dashboard': 'Interactive Dashboard (composite)',
}

# Group structure for UI
FIGURE_GROUPS = {
    'HVSR Curves': [
        'fig_standard', 'fig_hvsr_curve', 'fig_mean_vs_median',
        'fig_components', 'fig_with_windows',
    ],
    'Statistics': [
        'fig_statistics', 'fig_peak_analysis', 'fig_peak_details',
    ],
    'Windows': [
        'fig_window_overview', 'fig_quality_grid',
        'fig_quality_histogram', 'fig_rejection_timeline',
    ],
    'Comparison': [
        'fig_raw_vs_adjusted', 'fig_pre_post_rejection',
    ],
    'Waveform': [
        'fig_waveform_3c', 'fig_window_timeseries', 'fig_window_spectrogram',
    ],
    'Report': [
        'fig_dashboard',
    ],
}

# Defaults: which figures are checked initially
DEFAULT_ENABLED = {
    'fig_standard', 'fig_hvsr_curve', 'fig_statistics',
}


class FigureExportDialog(QDialog):
    """
    Dialog for configuring which figures to generate and their settings.

    Usage::

        dlg = FigureExportDialog(parent)
        if dlg.exec_() == QDialog.Accepted:
            config = dlg.get_config()
    """

    def __init__(self, parent=None, current_config=None):
        super().__init__(parent)
        self.setWindowTitle("Figure Export Settings")
        self.setMinimumWidth(520)
        self._checkboxes = {}
        self._build_ui()
        if current_config:
            self.set_config(current_config)

    # ------------------------------------------------------------------
    #  UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # ── Global settings ──
        global_grp = QGroupBox("Global Settings")
        g_layout = QGridLayout(global_grp)

        g_layout.addWidget(QLabel("DPI:"), 0, 0)
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 600)
        self.dpi_spin.setValue(300)
        self.dpi_spin.setToolTip("Resolution in dots per inch")
        g_layout.addWidget(self.dpi_spin, 0, 1)

        g_layout.addWidget(QLabel("Format:"), 0, 2)
        self.format_combo = QComboBox()
        self.format_combo.addItems(["PNG", "PDF", "SVG", "TIFF"])
        self.format_combo.setToolTip("Image format for saved figures")
        g_layout.addWidget(self.format_combo, 0, 3)

        g_layout.addWidget(QLabel("Figure Size:"), 1, 0)
        self.size_combo = QComboBox()
        self.size_combo.addItems([
            "Standard (10x7)",
            "Large (14x10)",
            "Publication (12x8)",
            "Wide (16x6)",
        ])
        self.size_combo.setToolTip("Default figure dimensions in inches")
        g_layout.addWidget(self.size_combo, 1, 1, 1, 3)

        # ── Smart Y-Limit options ──
        self.auto_ylim = QCheckBox("Smart Y-Limit (clip outlier display)")
        self.auto_ylim.setChecked(True)
        self.auto_ylim.setToolTip(
            "Compute a robust Y-axis upper limit so that outlier\n"
            "window spikes don't stretch the plot.  Does NOT change\n"
            "data or rejection — purely cosmetic.")
        g_layout.addWidget(self.auto_ylim, 2, 0, 1, 2)

        self.ylim_method = QComboBox()
        self.ylim_method.addItems([
            "95th Percentile",
            "Mean + 3×Std",
            "Mean + 2×IQR",
        ])
        self.ylim_method.setToolTip(
            "Method to compute the Y-axis upper bound:\n"
            "  95th Percentile — robust, uses 95th pctl of all accepted H/V values\n"
            "  Mean + 3×Std — 3 standard deviations above the mean curve peak\n"
            "  Mean + 2×IQR — 2 inter-quartile ranges above the 84th percentile")
        g_layout.addWidget(self.ylim_method, 2, 2, 1, 2)

        layout.addWidget(global_grp)

        # ── Figure type checkboxes grouped by category ──
        for group_name, keys in FIGURE_GROUPS.items():
            grp = QGroupBox(group_name)
            grp_layout = QVBoxLayout(grp)

            for key in keys:
                label = FIGURE_TYPES.get(key, key)
                cb = QCheckBox(label)
                cb.setChecked(key in DEFAULT_ENABLED)
                cb.setToolTip(f"Toggle: {label}")
                self._checkboxes[key] = cb
                grp_layout.addWidget(cb)

            layout.addWidget(grp)

        # ── Select All / Deselect All ──
        sel_bar = QHBoxLayout()
        btn_all = QPushButton("Select All")
        btn_all.clicked.connect(lambda: self._set_all(True))
        btn_none = QPushButton("Deselect All")
        btn_none.clicked.connect(lambda: self._set_all(False))
        sel_bar.addWidget(btn_all)
        sel_bar.addWidget(btn_none)
        sel_bar.addStretch()
        layout.addLayout(sel_bar)

        # ── OK / Cancel ──
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------
    #  Public API
    # ------------------------------------------------------------------

    def get_config(self):
        """
        Return current configuration as a dict.

        Returns
        -------
        dict
            Keys: 'dpi', 'format', 'figsize', plus one bool per figure type key.
        """
        config = {
            'dpi': self.dpi_spin.value(),
            'format': self.format_combo.currentText().lower(),
            'figsize': self.size_combo.currentText(),
            'auto_ylim': self.auto_ylim.isChecked(),
            'ylim_method': self.ylim_method.currentText(),
        }
        for key, cb in self._checkboxes.items():
            config[key] = cb.isChecked()
        return config

    def set_config(self, config):
        """
        Restore configuration from a dict.

        Parameters
        ----------
        config : dict
            As returned by :meth:`get_config`.
        """
        if 'dpi' in config:
            self.dpi_spin.setValue(int(config['dpi']))
        if 'format' in config:
            idx = self.format_combo.findText(
                config['format'].upper(), Qt.MatchFixedString
            )
            if idx >= 0:
                self.format_combo.setCurrentIndex(idx)
        if 'figsize' in config:
            idx = self.size_combo.findText(config['figsize'], Qt.MatchStartsWith)
            if idx >= 0:
                self.size_combo.setCurrentIndex(idx)
        if 'auto_ylim' in config:
            self.auto_ylim.setChecked(bool(config['auto_ylim']))
        if 'ylim_method' in config:
            idx = self.ylim_method.findText(config['ylim_method'], Qt.MatchStartsWith)
            if idx >= 0:
                self.ylim_method.setCurrentIndex(idx)
        for key, cb in self._checkboxes.items():
            if key in config:
                cb.setChecked(bool(config[key]))

    # ------------------------------------------------------------------
    #  Internal
    # ------------------------------------------------------------------

    def _set_all(self, checked):
        for cb in self._checkboxes.values():
            cb.setChecked(checked)
