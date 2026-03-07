"""
HVSR Settings Dialog
=====================

Configuration dialogs for HVSR processing parameters:
- HVSRSettingsDialog: main settings (frequency range, smoothing, peaks, QC, etc.)
- ProcessLengthDialog: per-array process length table
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QCheckBox, QMessageBox, QTableWidget, QTableWidgetItem,
    QHeaderView,
)
from PyQt5.QtCore import Qt
from datetime import datetime
import multiprocessing


class HVSRSettingsDialog(QDialog):
    """HVSR Settings Dialog for automatic workflow."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("HVSR Settings")
        self.setModal(True)
        self.setMinimumWidth(550)
        self._figure_export_config = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Frequency Range Group
        freq_group = QGroupBox("Frequency Range")
        freq_layout = QGridLayout(freq_group)

        freq_layout.addWidget(QLabel("Min Freq (Hz):"), 0, 0)
        self.freq_min = QDoubleSpinBox()
        self.freq_min.setRange(0.01, 10.0)
        self.freq_min.setValue(0.2)
        self.freq_min.setDecimals(2)
        freq_layout.addWidget(self.freq_min, 0, 1)

        freq_layout.addWidget(QLabel("Max Freq (Hz):"), 0, 2)
        self.freq_max = QDoubleSpinBox()
        self.freq_max.setRange(1.0, 100.0)
        self.freq_max.setValue(30.0)
        self.freq_max.setDecimals(1)
        freq_layout.addWidget(self.freq_max, 0, 3)

        freq_layout.addWidget(QLabel("Smoothing:"), 1, 0)
        self.smoothing_type = QComboBox()
        self.smoothing_type.addItems(["Konno-Ohmachi", "Parzen", "None"])
        freq_layout.addWidget(self.smoothing_type, 1, 1)

        freq_layout.addWidget(QLabel("Bandwidth:"), 1, 2)
        self.smoothing_bw = QSpinBox()
        self.smoothing_bw.setRange(1, 100)
        self.smoothing_bw.setValue(40)
        freq_layout.addWidget(self.smoothing_bw, 1, 3)

        freq_layout.addWidget(QLabel("Time Window (s):"), 2, 0)
        self.window_length = QSpinBox()
        self.window_length.setRange(10, 600)
        self.window_length.setValue(120)
        freq_layout.addWidget(self.window_length, 2, 1)

        freq_layout.addWidget(QLabel("Averaging:"), 2, 2)
        self.averaging = QComboBox()
        self.averaging.addItems(["geo", "quad", "energy", "N", "E"])
        freq_layout.addWidget(self.averaging, 2, 3)

        freq_layout.addWidget(QLabel("N Frequencies:"), 3, 0)
        self.n_frequencies = QSpinBox()
        self.n_frequencies.setRange(50, 2000)
        self.n_frequencies.setValue(300)
        self.n_frequencies.setToolTip("Number of log-spaced frequency points in median JSON output")
        freq_layout.addWidget(self.n_frequencies, 3, 1)

        freq_layout.addWidget(QLabel("Taper:"), 3, 2)
        self.taper = QComboBox()
        self.taper.addItems(["tukey", "hann", "hamming", "blackman", "none"])
        self.taper.setToolTip("Taper window applied to each time segment")
        freq_layout.addWidget(self.taper, 3, 3)

        freq_layout.addWidget(QLabel("Detrend:"), 4, 0)
        self.detrend = QComboBox()
        self.detrend.addItems(["linear", "mean", "none"])
        self.detrend.setToolTip(
            "Detrend method applied before FFT.\n"
            "'linear' removes linear trend (recommended),\n"
            "'mean' subtracts the mean, 'none' skips detrending.")
        freq_layout.addWidget(self.detrend, 4, 1)

        freq_layout.addWidget(QLabel("Statistics:"), 4, 2)
        self.statistics_method = QComboBox()
        self.statistics_method.addItems(["lognormal", "numpy"])
        self.statistics_method.setToolTip(
            "Method for computing median and percentiles.\n"
            "'lognormal' uses lognormal distribution (recommended),\n"
            "'numpy' uses direct numpy median/percentile.")
        freq_layout.addWidget(self.statistics_method, 4, 3)

        freq_layout.addWidget(QLabel("Std ddof:"), 5, 0)
        self.std_ddof = QSpinBox()
        self.std_ddof.setRange(0, 1)
        self.std_ddof.setValue(1)
        self.std_ddof.setToolTip("Delta degrees of freedom for std deviation (0 or 1)")
        freq_layout.addWidget(self.std_ddof, 5, 1)

        layout.addWidget(freq_group)

        # Peak Display Group
        peak_group = QGroupBox("Peak Display")
        peak_layout = QGridLayout(peak_group)

        peak_layout.addWidget(QLabel("Peak Label Font (pt):"), 0, 0)
        self.peak_font = QSpinBox()
        self.peak_font.setRange(6, 30)
        self.peak_font.setValue(10)
        self.peak_font.setToolTip("Font size for peak labels on the plot")
        peak_layout.addWidget(self.peak_font, 0, 1)

        layout.addWidget(peak_group)

        # Processing Options Group
        proc_group = QGroupBox("Processing Options")
        proc_layout = QGridLayout(proc_group)

        proc_layout.addWidget(QLabel("Start Skip (min):"), 0, 0)
        self.start_skip = QSpinBox()
        self.start_skip.setRange(0, 120)
        self.start_skip.setValue(0)
        proc_layout.addWidget(self.start_skip, 0, 1)

        self._process_len_label = QLabel("Process Length (min):")
        proc_layout.addWidget(self._process_len_label, 0, 2)
        self.process_len = QSpinBox()
        self.process_len.setRange(1, 240)
        self.process_len.setValue(20)
        self.process_len.setToolTip("Global process length applied to all arrays")
        proc_layout.addWidget(self.process_len, 0, 3)

        self.full_duration = QCheckBox("Use Full Duration")
        self.full_duration.setChecked(False)
        self.full_duration.setToolTip(
            "Use the entire recording duration instead of a fixed process length.\n"
            "When checked, Process Length is ignored.")
        self.full_duration.stateChanged.connect(self._on_full_duration_changed)
        proc_layout.addWidget(self.full_duration, 0, 4)

        self.per_array_check = QCheckBox("Per-Array")
        self.per_array_check.setChecked(False)
        self.per_array_check.setToolTip(
            "Check to set process length individually for each array.\n"
            "Uncheck to use the global value for all arrays.")
        self.per_array_check.stateChanged.connect(self._on_per_array_toggled)
        proc_layout.addWidget(self.per_array_check, 0, 5)

        self.per_array_btn = QPushButton("Configure...")
        self.per_array_btn.setEnabled(False)
        self.per_array_btn.setToolTip("Open per-array process length table")
        self.per_array_btn.clicked.connect(self._open_per_array_dialog)
        proc_layout.addWidget(self.per_array_btn, 0, 6)

        self._per_array_process_len = {}
        self._time_windows_ref = []

        self.save_png = QCheckBox("Save PNG")
        self.save_png.setChecked(True)
        proc_layout.addWidget(self.save_png, 1, 0)

        self.save_pdf = QCheckBox("Save PDF")
        self.save_pdf.setChecked(False)
        proc_layout.addWidget(self.save_pdf, 1, 1)

        # Parallel processing option
        proc_layout.addWidget(QLabel("Max Parallel:"), 1, 2)
        self.max_parallel = QSpinBox()
        self.max_parallel.setRange(1, multiprocessing.cpu_count())
        self.max_parallel.setValue(min(4, multiprocessing.cpu_count()))
        self.max_parallel.setToolTip("Maximum number of HVSR curves to process in parallel")
        proc_layout.addWidget(self.max_parallel, 1, 3)

        layout.addWidget(proc_group)

        # Automatic Mode Group (NEW)
        auto_group = QGroupBox("Automatic Peak Detection Mode")
        auto_layout = QGridLayout(auto_group)

        self.auto_mode = QCheckBox("Enable Automatic Peak Detection")
        self.auto_mode.setChecked(False)
        self.auto_mode.setToolTip("Automatically detect peaks and compute statistics across all stations")
        auto_layout.addWidget(self.auto_mode, 0, 0, 1, 2)

        auto_layout.addWidget(QLabel("Peak Basis:"), 0, 2)
        self.peak_basis = QComboBox()
        self.peak_basis.addItems(["median", "mean"])
        self.peak_basis.setCurrentText("median")
        self.peak_basis.setToolTip(
            "Curve used for peak detection and interactive peak picking.\n"
            "Median is more robust to outliers and recommended for most cases.")
        auto_layout.addWidget(self.peak_basis, 0, 3)

        auto_layout.addWidget(QLabel("Min Prominence:"), 1, 0)
        self.min_prominence = QDoubleSpinBox()
        self.min_prominence.setRange(0.1, 10.0)
        self.min_prominence.setValue(0.5)
        self.min_prominence.setDecimals(2)
        self.min_prominence.setToolTip("Minimum peak prominence for detection")
        auto_layout.addWidget(self.min_prominence, 1, 1)

        auto_layout.addWidget(QLabel("Min Amplitude:"), 1, 2)
        self.min_amplitude = QDoubleSpinBox()
        self.min_amplitude.setRange(1.0, 20.0)
        self.min_amplitude.setValue(2.0)
        self.min_amplitude.setDecimals(1)
        self.min_amplitude.setToolTip("Minimum HVSR amplitude for peak detection")
        auto_layout.addWidget(self.min_amplitude, 1, 3)

        auto_layout.addWidget(QLabel("Max Peaks:"), 2, 0)
        self.auto_npeaks = QSpinBox()
        self.auto_npeaks.setRange(1, 20)
        self.auto_npeaks.setValue(3)
        self.auto_npeaks.setToolTip(
            "Maximum number of peaks for auto-detection.\n"
            "Also used by the Auto-Detect button in interactive mode.")
        auto_layout.addWidget(self.auto_npeaks, 2, 1)

        auto_layout.addWidget(QLabel("Freq Tolerance (Hz):"), 2, 2)
        self.freq_tolerance = QDoubleSpinBox()
        self.freq_tolerance.setRange(0.05, 2.0)
        self.freq_tolerance.setValue(0.3)
        self.freq_tolerance.setDecimals(2)
        self.freq_tolerance.setToolTip("Frequency tolerance for grouping peaks across stations")
        auto_layout.addWidget(self.freq_tolerance, 2, 3)

        self.export_excel = QCheckBox("Export Excel")
        self.export_excel.setChecked(True)
        auto_layout.addWidget(self.export_excel, 3, 0)

        self.export_mat = QCheckBox("Export MAT")
        self.export_mat.setChecked(True)
        auto_layout.addWidget(self.export_mat, 3, 1)

        layout.addWidget(auto_group)

        # Output & Figure Settings Group (applies to both auto and interactive modes)
        auto_out_group = QGroupBox("Output & Figure Settings")
        auto_out_layout = QGridLayout(auto_out_group)

        auto_out_layout.addWidget(QLabel("Figure DPI:"), 0, 0)
        self.auto_fig_dpi = QSpinBox()
        self.auto_fig_dpi.setRange(72, 600)
        self.auto_fig_dpi.setValue(300)
        self.auto_fig_dpi.setToolTip("Resolution (dots per inch) for auto-mode figures")
        auto_out_layout.addWidget(self.auto_fig_dpi, 0, 1)

        self.auto_save_json = QCheckBox("Save JSON per station")
        self.auto_save_json.setChecked(True)
        self.auto_save_json.setToolTip("Save hvsr_pro-format JSON result for each station")
        auto_out_layout.addWidget(self.auto_save_json, 0, 2)

        self.auto_save_csv = QCheckBox("Save CSV per station")
        self.auto_save_csv.setChecked(True)
        self.auto_save_csv.setToolTip("Save median data CSV and metadata CSV for each station")
        auto_out_layout.addWidget(self.auto_save_csv, 0, 3)

        self.auto_fig_standard = QCheckBox("Window-curves figure")
        self.auto_fig_standard.setChecked(True)
        self.auto_fig_standard.setToolTip("Standard figure showing individual windows + mean ± std + peaks")
        auto_out_layout.addWidget(self.auto_fig_standard, 1, 0)

        self.auto_fig_hvsr_pro = QCheckBox("hvsr_pro HVSR curve")
        self.auto_fig_hvsr_pro.setChecked(True)
        self.auto_fig_hvsr_pro.setToolTip("Clean HVSR curve with uncertainty band (hvsr_pro style)")
        auto_out_layout.addWidget(self.auto_fig_hvsr_pro, 1, 1)

        self.auto_fig_statistics = QCheckBox("Statistics 4-panel")
        self.auto_fig_statistics.setChecked(True)
        self.auto_fig_statistics.setToolTip("4-panel statistics figure from hvsr_pro")
        auto_out_layout.addWidget(self.auto_fig_statistics, 1, 2)

        self.configure_figures_btn = QPushButton("Configure All Figures...")
        self.configure_figures_btn.setToolTip(
            "Open a detailed dialog to select from all available\n"
            "hvsr_pro figure types (waveform, comparison, etc.)")
        self.configure_figures_btn.clicked.connect(self._open_figure_export_dialog)
        auto_out_layout.addWidget(self.configure_figures_btn, 2, 0, 1, 4)

        layout.addWidget(auto_out_group)

        # QC/Rejection Algorithms Group (NEW)
        qc_group = QGroupBox("QC & Rejection Algorithms")
        qc_layout = QGridLayout(qc_group)

        # Algorithm enable checkboxes — layout: [checkbox] [...] [checkbox] [...]
        # Row 0: Amplitude Check + STA/LTA
        self.qc_amplitude = QCheckBox("Amplitude Check")
        self.qc_amplitude.setChecked(True)
        self.qc_amplitude.setToolTip("Detect clipping, dead channels, extreme amplitudes")
        qc_layout.addWidget(self.qc_amplitude, 0, 0)

        self.amplitude_settings_btn = QPushButton("...")
        self.amplitude_settings_btn.setMaximumWidth(30)
        self.amplitude_settings_btn.setToolTip("Configure amplitude check settings (presets & thresholds)")
        self.amplitude_settings_btn.clicked.connect(self._open_amplitude_settings)
        qc_layout.addWidget(self.amplitude_settings_btn, 0, 1)

        self.qc_stalta = QCheckBox("STA/LTA Transients")
        self.qc_stalta.setChecked(True)
        self.qc_stalta.setToolTip("Detect energy bursts from earthquakes, traffic, etc.")
        qc_layout.addWidget(self.qc_stalta, 0, 2)

        self.stalta_settings_btn = QPushButton("...")
        self.stalta_settings_btn.setMaximumWidth(30)
        self.stalta_settings_btn.setToolTip("Configure STA/LTA settings")
        self.stalta_settings_btn.clicked.connect(self._open_stalta_settings)
        qc_layout.addWidget(self.stalta_settings_btn, 0, 3)

        # Row 1: Cox FDWRA + HVSR Amplitude
        self.qc_fdwra = QCheckBox("Cox FDWRA")
        self.qc_fdwra.setChecked(True)
        self.qc_fdwra.setToolTip("Peak frequency consistency rejection (industry standard)")
        qc_layout.addWidget(self.qc_fdwra, 1, 0)

        self.fdwra_settings_btn = QPushButton("...")
        self.fdwra_settings_btn.setMaximumWidth(30)
        self.fdwra_settings_btn.setToolTip("Configure FDWRA settings")
        self.fdwra_settings_btn.clicked.connect(self._open_fdwra_settings)
        qc_layout.addWidget(self.fdwra_settings_btn, 1, 1)

        self.qc_hvsr_amp = QCheckBox("HVSR Amplitude Bounds")
        self.qc_hvsr_amp.setChecked(False)
        self.qc_hvsr_amp.setToolTip(
            "Reject windows where H/V peak is below min threshold\n"
            "OR any H/V value exceeds global max (catches low-freq spikes)")
        qc_layout.addWidget(self.qc_hvsr_amp, 1, 2)

        self.hvsr_amp_settings_btn = QPushButton("...")
        self.hvsr_amp_settings_btn.setMaximumWidth(30)
        self.hvsr_amp_settings_btn.setToolTip("Configure HVSR amplitude settings")
        self.hvsr_amp_settings_btn.clicked.connect(self._open_hvsr_amp_settings)
        qc_layout.addWidget(self.hvsr_amp_settings_btn, 1, 3)

        # Row 2: Flat Peak + Statistical Outliers
        self.qc_flat_peak = QCheckBox("Flat Peak Detection")
        self.qc_flat_peak.setChecked(False)
        self.qc_flat_peak.setToolTip("Reject windows with flat or unclear peaks")
        qc_layout.addWidget(self.qc_flat_peak, 2, 0)

        self.flat_peak_settings_btn = QPushButton("...")
        self.flat_peak_settings_btn.setMaximumWidth(30)
        self.flat_peak_settings_btn.setToolTip("Configure flat peak settings")
        self.flat_peak_settings_btn.clicked.connect(self._open_flat_peak_settings)
        qc_layout.addWidget(self.flat_peak_settings_btn, 2, 1)

        self.qc_statistical = QCheckBox("Statistical Outliers")
        self.qc_statistical.setChecked(True)
        self.qc_statistical.setToolTip("Reject windows whose H/V curve deviates from the group (MAD/IQR)")
        qc_layout.addWidget(self.qc_statistical, 2, 2)

        self.statistical_settings_btn = QPushButton("...")
        self.statistical_settings_btn.setMaximumWidth(30)
        self.statistical_settings_btn.setToolTip("Configure statistical outlier settings")
        self.statistical_settings_btn.clicked.connect(self._open_statistical_settings)
        qc_layout.addWidget(self.statistical_settings_btn, 2, 3)

        layout.addWidget(qc_group)

        # Initialize QC parameters storage
        self._init_qc_params()

        # Buttons
        btn_layout = QHBoxLayout()
        self.reset_btn = QPushButton("Reset to Defaults")
        self.reset_btn.clicked.connect(self._load_defaults)
        btn_layout.addWidget(self.reset_btn)
        btn_layout.addStretch()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setDefault(True)
        btn_layout.addWidget(self.ok_btn)
        layout.addLayout(btn_layout)

    def _on_full_duration_changed(self, state):
        is_full = (state == Qt.Checked)
        self.process_len.setEnabled(not is_full)
        self._process_len_label.setEnabled(not is_full)
        if is_full:
            self.per_array_check.setChecked(False)
            self.per_array_check.setEnabled(False)
            self.per_array_btn.setEnabled(False)
        else:
            self.per_array_check.setEnabled(True)

    def _on_auto_peaks_changed(self, state):
        # Legacy stub — num_peaks removed; interactive mode is now unlimited
        pass

    def _load_defaults(self):
        self.freq_min.setValue(0.2)
        self.freq_max.setValue(30.0)
        self.smoothing_type.setCurrentText("Konno-Ohmachi")
        self.smoothing_bw.setValue(40)
        self.window_length.setValue(120)
        self.averaging.setCurrentText("geo")
        self.n_frequencies.setValue(300)
        self.taper.setCurrentText("tukey")
        self.detrend.setCurrentText("linear")
        self.statistics_method.setCurrentText("lognormal")
        self.std_ddof.setValue(1)
        self.peak_font.setValue(10)
        self.start_skip.setValue(0)
        self.process_len.setValue(20)
        self.full_duration.setChecked(False)
        self.per_array_check.setChecked(False)
        self._per_array_process_len = {}
        self.save_png.setChecked(True)
        self.save_pdf.setChecked(False)
        self.max_parallel.setValue(min(4, multiprocessing.cpu_count()))
        # Automatic mode defaults
        self.auto_mode.setChecked(False)
        self.min_prominence.setValue(0.5)
        self.min_amplitude.setValue(2.0)
        self.auto_npeaks.setValue(3)
        self.freq_tolerance.setValue(0.3)
        self.export_excel.setChecked(True)
        self.export_mat.setChecked(True)
        # Auto-mode output defaults
        self.auto_fig_dpi.setValue(300)
        self.auto_save_json.setChecked(True)
        self.auto_save_csv.setChecked(True)
        self.auto_fig_standard.setChecked(True)
        self.auto_fig_hvsr_pro.setChecked(True)
        self.auto_fig_statistics.setChecked(True)
        self._figure_export_config = {}
        # QC algorithm defaults
        self.qc_amplitude.setChecked(True)
        self.qc_stalta.setChecked(True)
        self.qc_fdwra.setChecked(True)
        self.qc_hvsr_amp.setChecked(False)
        self.qc_flat_peak.setChecked(False)
        self.qc_statistical.setChecked(True)
        self._init_qc_params()

    def get_settings(self):
        return {
            'freq_min': self.freq_min.value(),
            'freq_max': self.freq_max.value(),
            'smoothing_type': self.smoothing_type.currentText(),
            'smoothing_bw': self.smoothing_bw.value(),
            'window_length': self.window_length.value(),
            'averaging': self.averaging.currentText(),
            'n_frequencies': self.n_frequencies.value(),
            'taper': self.taper.currentText(),
            'detrend': self.detrend.currentText(),
            'statistics_method': self.statistics_method.currentText(),
            'std_ddof': self.std_ddof.value(),
            'peak_font': self.peak_font.value(),
            'start_skip': self.start_skip.value(),
            'process_len': self.process_len.value(),
            'full_duration': self.full_duration.isChecked(),
            'save_png': self.save_png.isChecked(),
            'save_pdf': self.save_pdf.isChecked(),
            'max_parallel': self.max_parallel.value(),
            # Automatic mode settings
            'auto_mode': self.auto_mode.isChecked(),
            'peak_basis': self.peak_basis.currentText(),
            'min_prominence': self.min_prominence.value(),
            'min_amplitude': self.min_amplitude.value(),
            'auto_npeaks': self.auto_npeaks.value(),
            'freq_tolerance': self.freq_tolerance.value(),
            'export_excel': self.export_excel.isChecked(),
            'export_mat': self.export_mat.isChecked(),
            # Auto-mode output settings
            'auto_fig_dpi': self.auto_fig_dpi.value(),
            'auto_save_json': self.auto_save_json.isChecked(),
            'auto_save_csv': self.auto_save_csv.isChecked(),
            'auto_fig_standard': self.auto_fig_standard.isChecked(),
            'auto_fig_hvsr_pro': self.auto_fig_hvsr_pro.isChecked(),
            'auto_fig_statistics': self.auto_fig_statistics.isChecked(),
            'figure_export_config': dict(self._figure_export_config),
            # QC algorithm settings
            'qc_amplitude': self.qc_amplitude.isChecked(),
            'qc_stalta': self.qc_stalta.isChecked(),
            'qc_fdwra': self.qc_fdwra.isChecked(),
            'qc_hvsr_amp': self.qc_hvsr_amp.isChecked(),
            'qc_flat_peak': self.qc_flat_peak.isChecked(),
            'qc_statistical': self.qc_statistical.isChecked(),
            'qc_params': self._qc_params.copy(),
            'use_per_array': self.per_array_check.isChecked(),
            'per_array_process_len': dict(self._per_array_process_len),
        }

    def set_settings(self, settings):
        if 'freq_min' in settings:
            self.freq_min.setValue(settings['freq_min'])
        if 'freq_max' in settings:
            self.freq_max.setValue(settings['freq_max'])
        if 'smoothing_type' in settings:
            self.smoothing_type.setCurrentText(settings['smoothing_type'])
        if 'smoothing_bw' in settings:
            self.smoothing_bw.setValue(settings['smoothing_bw'])
        if 'window_length' in settings:
            self.window_length.setValue(settings['window_length'])
        if 'averaging' in settings:
            self.averaging.setCurrentText(settings['averaging'])
        if 'n_frequencies' in settings:
            self.n_frequencies.setValue(settings['n_frequencies'])
        if 'taper' in settings:
            self.taper.setCurrentText(settings['taper'])
        if 'detrend' in settings:
            self.detrend.setCurrentText(settings['detrend'])
        if 'statistics_method' in settings:
            self.statistics_method.setCurrentText(settings['statistics_method'])
        if 'std_ddof' in settings:
            self.std_ddof.setValue(settings['std_ddof'])
        if 'peak_font' in settings:
            self.peak_font.setValue(settings['peak_font'])
        if 'start_skip' in settings:
            self.start_skip.setValue(settings['start_skip'])
        if 'process_len' in settings:
            self.process_len.setValue(settings['process_len'])
        if 'full_duration' in settings:
            self.full_duration.setChecked(settings['full_duration'])
        if 'save_png' in settings:
            self.save_png.setChecked(settings['save_png'])
        if 'save_pdf' in settings:
            self.save_pdf.setChecked(settings['save_pdf'])
        if 'max_parallel' in settings:
            self.max_parallel.setValue(settings['max_parallel'])
        # Automatic mode settings
        if 'auto_mode' in settings:
            self.auto_mode.setChecked(settings['auto_mode'])
        if 'peak_basis' in settings:
            self.peak_basis.setCurrentText(settings['peak_basis'])
        if 'min_prominence' in settings:
            self.min_prominence.setValue(settings['min_prominence'])
        if 'min_amplitude' in settings:
            self.min_amplitude.setValue(settings['min_amplitude'])
        if 'auto_npeaks' in settings:
            self.auto_npeaks.setValue(settings['auto_npeaks'])
        elif 'num_peaks' in settings:
            self.auto_npeaks.setValue(settings['num_peaks'])
        if 'freq_tolerance' in settings:
            self.freq_tolerance.setValue(settings['freq_tolerance'])
        if 'export_excel' in settings:
            self.export_excel.setChecked(settings['export_excel'])
        if 'export_mat' in settings:
            self.export_mat.setChecked(settings['export_mat'])
        # Auto-mode output settings
        if 'auto_fig_dpi' in settings:
            self.auto_fig_dpi.setValue(settings['auto_fig_dpi'])
        if 'auto_save_json' in settings:
            self.auto_save_json.setChecked(settings['auto_save_json'])
        if 'auto_save_csv' in settings:
            self.auto_save_csv.setChecked(settings['auto_save_csv'])
        if 'auto_fig_standard' in settings:
            self.auto_fig_standard.setChecked(settings['auto_fig_standard'])
        if 'auto_fig_hvsr_pro' in settings:
            self.auto_fig_hvsr_pro.setChecked(settings['auto_fig_hvsr_pro'])
        if 'auto_fig_statistics' in settings:
            self.auto_fig_statistics.setChecked(settings['auto_fig_statistics'])
        if 'figure_export_config' in settings:
            self._figure_export_config = dict(settings['figure_export_config'])
        # QC settings
        if 'qc_amplitude' in settings:
            self.qc_amplitude.setChecked(settings['qc_amplitude'])
        if 'qc_stalta' in settings:
            self.qc_stalta.setChecked(settings['qc_stalta'])
        if 'qc_fdwra' in settings:
            self.qc_fdwra.setChecked(settings['qc_fdwra'])
        if 'qc_hvsr_amp' in settings:
            self.qc_hvsr_amp.setChecked(settings['qc_hvsr_amp'])
        if 'qc_flat_peak' in settings:
            self.qc_flat_peak.setChecked(settings['qc_flat_peak'])
        if 'qc_statistical' in settings:
            self.qc_statistical.setChecked(settings['qc_statistical'])
        if 'qc_params' in settings:
            self._qc_params = settings['qc_params'].copy()
        if 'use_per_array' in settings:
            self.per_array_check.setChecked(settings['use_per_array'])
        if 'per_array_process_len' in settings:
            self._per_array_process_len = dict(settings['per_array_process_len'])

    def _init_qc_params(self):
        """Initialize QC algorithm parameters with defaults."""
        from hvsr_pro.packages.batch_processing.dialogs.qc_settings import ALGORITHM_DEFAULTS
        self._qc_params = {
            'amplitude': ALGORITHM_DEFAULTS['amplitude'].copy(),
            'sta_lta': ALGORITHM_DEFAULTS['sta_lta'].copy(),
            'fdwra': ALGORITHM_DEFAULTS['fdwra'].copy(),
            'hvsr_amplitude': ALGORITHM_DEFAULTS['hvsr_amplitude'].copy(),
            'flat_peak': ALGORITHM_DEFAULTS['flat_peak'].copy(),
            'statistical_outlier': ALGORITHM_DEFAULTS['statistical_outlier'].copy(),
        }

    def _open_figure_export_dialog(self):
        """Open the detailed figure export configuration dialog."""
        from hvsr_pro.packages.batch_processing.dialogs.figure_export_dialog import FigureExportDialog
        dlg = FigureExportDialog(self, current_config=self._figure_export_config or None)
        if dlg.exec_() == QDialog.Accepted:
            self._figure_export_config = dlg.get_config()

    def _open_amplitude_settings(self):
        """Open amplitude check settings dialog."""
        from hvsr_pro.packages.batch_processing.dialogs.qc_settings import AmplitudeSettingsDialog
        dialog = AmplitudeSettingsDialog(self, self._qc_params.get('amplitude', {}))
        if dialog.exec_() == QDialog.Accepted:
            result = dialog.get_result()
            if result:
                self._qc_params['amplitude'] = result

    def _on_per_array_toggled(self, state):
        """Toggle between global process length and per-array mode."""
        per_array = (state == Qt.Checked)
        self.process_len.setEnabled(not per_array)
        self.per_array_btn.setEnabled(per_array)

    def set_time_windows(self, time_windows):
        """Provide time windows so the Per-Array dialog can show durations."""
        self._time_windows_ref = time_windows or []

    def _open_per_array_dialog(self):
        """Open the per-array process length configuration dialog."""
        if not self._time_windows_ref:
            QMessageBox.information(
                self, "No Time Windows",
                "No time windows configured yet.\n\n"
                "Please configure time windows first (in the Analysis tab),\n"
                "then re-open HVSR Settings to use Per-Array process lengths.")
            return

        dialog = ProcessLengthDialog(
            self,
            time_windows=self._time_windows_ref,
            default_process_len=self.process_len.value(),
            per_array_overrides=self._per_array_process_len,
        )
        if dialog.exec_() == QDialog.Accepted:
            self._per_array_process_len = dialog.get_result()

    def _open_stalta_settings(self):
        """Open STA/LTA settings dialog."""
        from hvsr_pro.packages.batch_processing.dialogs.qc_settings import STALTASettingsDialog
        dialog = STALTASettingsDialog(self, self._qc_params.get('sta_lta', {}))
        if dialog.exec_() == QDialog.Accepted:
            result = dialog.get_result()
            if result:
                self._qc_params['sta_lta'] = result

    def _open_fdwra_settings(self):
        """Open FDWRA (Cox) settings dialog."""
        from hvsr_pro.packages.batch_processing.dialogs.qc_settings import FDWRASettingsDialog
        dialog = FDWRASettingsDialog(self, self._qc_params.get('fdwra', {}))
        if dialog.exec_() == QDialog.Accepted:
            result = dialog.get_result()
            if result:
                self._qc_params['fdwra'] = result

    def _open_hvsr_amp_settings(self):
        """Open HVSR amplitude settings dialog."""
        from hvsr_pro.packages.batch_processing.dialogs.qc_settings import HVSRAmplitudeSettingsDialog
        dialog = HVSRAmplitudeSettingsDialog(self, self._qc_params.get('hvsr_amplitude', {}))
        if dialog.exec_() == QDialog.Accepted:
            result = dialog.get_result()
            if result:
                self._qc_params['hvsr_amplitude'] = result

    def _open_flat_peak_settings(self):
        """Open flat peak settings dialog."""
        from hvsr_pro.packages.batch_processing.dialogs.qc_settings import FlatPeakSettingsDialog
        dialog = FlatPeakSettingsDialog(self, self._qc_params.get('flat_peak', {}))
        if dialog.exec_() == QDialog.Accepted:
            result = dialog.get_result()
            if result:
                self._qc_params['flat_peak'] = result

    def _open_statistical_settings(self):
        """Open statistical outlier settings dialog."""
        from hvsr_pro.packages.batch_processing.dialogs.qc_settings import StatisticalOutlierSettingsDialog
        dialog = StatisticalOutlierSettingsDialog(self, self._qc_params.get('statistical_outlier', {}))
        if dialog.exec_() == QDialog.Accepted:
            result = dialog.get_result()
            if result:
                self._qc_params['statistical_outlier'] = result


class ProcessLengthDialog(QDialog):
    """Dialog for configuring per-array/per-station process length.

    Shows a table with each time window (array), its auto-detected recording
    duration, and an editable Process Length column.  Users can set values
    individually or apply the global default to all rows at once.
    """

    def __init__(self, parent=None, time_windows=None, default_process_len=20,
                 per_array_overrides=None):
        super().__init__(parent)
        self.setWindowTitle("Per-Array Process Length")
        self.setModal(True)
        self.setMinimumSize(620, 300)

        self._time_windows = time_windows or []
        self._default = default_process_len
        self._overrides = dict(per_array_overrides or {})
        self._build_ui()
        self._populate()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        layout = QVBoxLayout(self)

        info = QLabel(
            "Each row corresponds to a configured time window (array).\n"
            "Recording Duration is computed from the window start/end times.\n"
            "Edit Process Length to control how many minutes of data are used for HVSR."
        )
        info.setStyleSheet("color: #555; font-style: italic;")
        info.setWordWrap(True)
        layout.addWidget(info)

        # Table: Array Name | Duration (min) | Process Length (min)
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(
            ["Array / Window", "Recording Duration (min)", "Process Length (min)"])
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        layout.addWidget(self.table)

        # Buttons row
        btn_row = QHBoxLayout()

        self.btn_apply_default = QPushButton("Set All to Default")
        self.btn_apply_default.setToolTip(
            f"Set every row to the global default ({self._default} min)")
        self.btn_apply_default.clicked.connect(self._apply_default_to_all)
        btn_row.addWidget(self.btn_apply_default)

        self.btn_auto_full = QPushButton("Use Full Duration")
        self.btn_auto_full.setToolTip(
            "Set process length to each array's full recording duration")
        self.btn_auto_full.clicked.connect(self._apply_full_duration)
        btn_row.addWidget(self.btn_auto_full)

        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        ok_btn.setDefault(True)
        btn_row.addWidget(ok_btn)

        layout.addLayout(btn_row)

    # ----------------------------------------------------------- Populate
    def _populate(self):
        self.table.setRowCount(0)
        for win in self._time_windows:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # Column 0: Array / window name (read-only)
            name = win.get('name', f'Window_{row + 1}')
            name_item = QTableWidgetItem(name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 0, name_item)

            # Column 1: Duration in minutes (read-only, auto-computed)
            duration_min = self._compute_duration_min(win)
            dur_item = QTableWidgetItem(f"{duration_min:.1f}")
            dur_item.setFlags(dur_item.flags() & ~Qt.ItemIsEditable)
            dur_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 1, dur_item)

            # Column 2: Process Length spin box (editable)
            spin = QSpinBox()
            spin.setRange(1, max(240, int(duration_min) + 1))
            override = self._overrides.get(name, self._default)
            # Clamp to recording duration if shorter
            if duration_min > 0:
                spin.setValue(min(int(override), int(duration_min)))
            else:
                spin.setValue(int(override))
            self.table.setCellWidget(row, 2, spin)

    def _compute_duration_min(self, win):
        """Compute recording duration in minutes from window start/end."""
        try:
            start_str = win.get('start_utc', win.get('start_local', ''))
            end_str = win.get('end_utc', win.get('end_local', ''))
            if not start_str or not end_str:
                return 0.0
            start = datetime.strptime(str(start_str), "%Y-%m-%d %H:%M:%S")
            end = datetime.strptime(str(end_str), "%Y-%m-%d %H:%M:%S")
            delta = (end - start).total_seconds() / 60.0
            return max(0.0, delta)
        except (ValueError, TypeError):
            return 0.0

    # --------------------------------------------------------- Actions
    def _apply_default_to_all(self):
        for row in range(self.table.rowCount()):
            spin = self.table.cellWidget(row, 2)
            if spin:
                spin.setValue(self._default)

    def _apply_full_duration(self):
        for row in range(self.table.rowCount()):
            dur_item = self.table.item(row, 1)
            spin = self.table.cellWidget(row, 2)
            if dur_item and spin:
                dur = float(dur_item.text())
                if dur > 0:
                    spin.setValue(int(dur))

    # --------------------------------------------------------- Result
    def get_result(self):
        """Return dict mapping window name -> process length in minutes."""
        result = {}
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            spin = self.table.cellWidget(row, 2)
            if name_item and spin:
                result[name_item.text()] = spin.value()
        return result
