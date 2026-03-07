"""
Interactive Peak-Picking Dialog
================================

A QDialog that provides interactive HVSR peak picking for batch processing.
Replaces the old subprocess-based approach with an in-process modal dialog.

Usage:
    dialog = InteractivePeakDialog(
        freq_ref, combined_hv, rejected_mask, hv_median, hv_mean, hv_std,
        fig_label="StationXX", settings={...}, parent=parent_widget)
    if dialog.exec_() == QDialog.Accepted:
        peaks = dialog.get_peaks()  # list of (frequency, amplitude) tuples
"""

import logging
import numpy as np
from typing import List, Tuple, Optional, Dict, Any

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QSplitter, QLabel, QListWidget, QListWidgetItem,
    QTabWidget,
)
from PyQt5.QtCore import Qt
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigCanvas,
    NavigationToolbar2QT as NavToolbar,
)
from matplotlib.figure import Figure as MplFig
import matplotlib.lines as mlines
from scipy.stats import lognorm

from hvsr_pro.packages.batch_processing.widgets.window_layers_panel import (
    WindowLayersPanel,
)

logger = logging.getLogger(__name__)


def _default_palette(n):
    import matplotlib.cm as cm
    return [cm.tab20(i / max(n, 1)) for i in range(n)]


class InteractivePeakDialog(QDialog):
    """Modal dialog for interactive HVSR peak picking."""

    def __init__(
        self,
        freq_ref: np.ndarray,
        combined_hv: np.ndarray,
        rejected_mask: np.ndarray,
        hv_median: np.ndarray,
        hv_mean: np.ndarray,
        hv_std: np.ndarray,
        fig_label: str = "",
        settings: Optional[Dict[str, Any]] = None,
        parent=None,
    ):
        """
        Parameters
        ----------
        freq_ref : 1-D array of frequencies
        combined_hv : 2-D array (n_freq, n_windows)
        rejected_mask : bool array (n_windows,)
        hv_median, hv_mean, hv_std : 1-D arrays (n_freq,)
        fig_label : station label for window title
        settings : dict with peak detection settings
        """
        super().__init__(parent)
        self.setWindowTitle(f"HVSR Peak Picking — {fig_label}")
        self.setMinimumSize(1100, 650)
        self.resize(1200, 700)

        self._freq = freq_ref
        self._combined = combined_hv
        self._rejected = rejected_mask
        self._median = hv_median
        self._mean = hv_mean
        self._std = hv_std
        self._label = fig_label
        self._settings = settings or {}

        self._peak_coords: List[Tuple[float, float]] = []
        self._peak_scatter = []
        self._peak_annots = []
        self._primary_idx = 0

        peak_basis = self._settings.get('peak_basis', 'median')
        self._basis_data = hv_median if peak_basis == 'median' else hv_mean

        self._build_ui()
        self._connect_events()

    def _build_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        splitter = QSplitter(Qt.Horizontal)

        # ── Left: canvas + toolbar + buttons ──
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self._fig = MplFig(figsize=(10, 7))
        self._ax = self._fig.add_subplot(111)
        self._canvas = FigCanvas(self._fig)
        self._toolbar = NavToolbar(self._canvas, left)
        left_layout.addWidget(self._toolbar)
        left_layout.addWidget(self._canvas)

        # Plot data
        self._plot_curves()

        # Button bar
        btn_bar = QHBoxLayout()
        self._btn_auto = QPushButton("Auto-Detect Peaks")
        self._btn_auto.setStyleSheet("background-color: #cce0ff;")
        self._btn_auto.setMinimumHeight(30)

        self._btn_clear = QPushButton("Clear All")
        self._btn_clear.setStyleSheet("background-color: #ffe0cc;")
        self._btn_clear.setMinimumHeight(30)

        self._btn_undo = QPushButton("Undo")
        self._btn_undo.setStyleSheet("background-color: #ffcccc;")
        self._btn_undo.setMinimumHeight(30)

        self._btn_accept = QPushButton("Accept && Save")
        self._btn_accept.setStyleSheet("background-color: #ccffcc; font-weight: bold;")
        self._btn_accept.setMinimumHeight(30)

        self._btn_skip = QPushButton("Skip Station")
        self._btn_skip.setStyleSheet("background-color: #f0f0f0;")
        self._btn_skip.setMinimumHeight(30)

        btn_bar.addWidget(self._btn_auto)
        btn_bar.addWidget(self._btn_clear)
        btn_bar.addWidget(self._btn_undo)
        btn_bar.addStretch()
        btn_bar.addWidget(self._btn_skip)
        btn_bar.addWidget(self._btn_accept)
        left_layout.addLayout(btn_bar)

        # ── Right: tabbed panel (Peaks + Layers) ──
        right_tabs = QTabWidget()

        # Tab 0 — Detected Peaks
        peaks_tab = QWidget()
        peaks_layout = QVBoxLayout(peaks_tab)
        peaks_layout.addWidget(QLabel("Detected Peaks:"))

        self._peak_list = QListWidget()
        peaks_layout.addWidget(self._peak_list)

        n_acc = int(np.sum(~self._rejected))
        n_tot = len(self._rejected)
        self._info_label = QLabel(
            f"Station: {self._label}\n"
            f"Windows: {n_acc}/{n_tot} accepted\n"
            f"Click on canvas to add peaks\n"
            f"Right-click to remove nearest peak")
        self._info_label.setWordWrap(True)
        peaks_layout.addWidget(self._info_label)

        right_tabs.addTab(peaks_tab, "Detected Peaks")

        # Tab 1 — Layers (window visibility)
        self._layers_panel = WindowLayersPanel()
        self._layers_panel.set_data(
            window_lines=self._window_line_dict,
            rejected_mask=list(self._rejected),
            stat_lines=self._stat_lines_dict,
            fig=self._fig,
        )
        self._layers_panel.visibility_changed.connect(
            self._on_window_toggled)
        right_tabs.addTab(self._layers_panel, "Layers")

        splitter.addWidget(left)
        splitter.addWidget(right_tabs)
        splitter.setStretchFactor(0, 80)
        splitter.setStretchFactor(1, 20)
        layout.addWidget(splitter)

    def _plot_curves(self):
        ax = self._ax
        n_windows = self._combined.shape[1]
        palette = _default_palette(n_windows)

        # Individual window curves — store Line2D refs for layers panel
        self._window_line_dict = {}
        for i in range(n_windows):
            curve = self._combined[:, i]
            if self._rejected[i]:
                ln, = ax.plot(self._freq, curve, color='#AAAAAA', lw=0.6,
                              alpha=0.3, linestyle='--')
                ln.set_visible(False)
            else:
                ln, = ax.plot(self._freq, curve,
                              color=palette[i % len(palette)],
                              lw=0.8, alpha=0.6)
            self._window_line_dict[i] = ln

        # Statistics lines — store refs for layers panel
        self._median_line, = ax.plot(
            self._freq, self._median, color='#CC0000', lw=2, label='Median')
        self._mean_line, = ax.plot(
            self._freq, self._mean, color='#000080', lw=2, label='Mean')
        self._mean_line.set_visible(False)

        std_plus = self._mean + self._std
        std_minus = np.maximum(self._mean - self._std, 0)
        self._std_plus_line, = ax.plot(
            self._freq, std_plus, '--k', lw=1, label='+Std')
        self._std_minus_line, = ax.plot(
            self._freq, std_minus, '--k', lw=1, label='-Std')

        self._stat_lines_dict = {
            "median": self._median_line,
            "mean": self._mean_line,
            "std_plus": self._std_plus_line,
            "std_minus": self._std_minus_line,
        }

        ax.set_xscale('log')
        ax.set_xlabel('Frequency [Hz]')
        ax.set_ylabel('HVSR')
        ax.set_title(f'HVSR Peak Picking — {self._label}')
        ax.grid(True, which='both', ls=':')
        ax.legend(fontsize=8, ncol=3, loc='upper right', frameon=True)
        self._fig.tight_layout()

    def _connect_events(self):
        self._canvas.mpl_connect('button_press_event', self._on_click)
        self._btn_auto.clicked.connect(self._auto_detect)
        self._btn_clear.clicked.connect(self._clear_all)
        self._btn_undo.clicked.connect(self._undo_peak)
        self._btn_accept.clicked.connect(self.accept)
        self._btn_skip.clicked.connect(self.reject)

    def _on_window_toggled(self, window_idx, is_visible):
        """Recompute statistics from visible windows and update plot."""
        visible_cols = []
        for idx, ln in self._window_line_dict.items():
            if ln.get_visible():
                visible_cols.append(self._combined[:, idx])

        if not visible_cols:
            return

        mat = np.column_stack(visible_cols)
        m = mat.mean(axis=1)
        s = mat.std(axis=1, ddof=1)

        # Update mean / std lines
        self._mean_line.set_ydata(m)
        self._std_plus_line.set_ydata(m + s)
        self._std_minus_line.set_ydata(np.maximum(m - s, 0))

        # Recompute lognormal median
        with np.errstate(divide='ignore', invalid='ignore'):
            zeta = np.sqrt(np.log1p((s ** 2) / (m ** 2)))
            lam = np.log(m) - 0.5 * zeta ** 2
            median = lognorm.median(s=zeta, scale=np.exp(lam))
            median = np.nan_to_num(median, nan=0.0, posinf=0.0)

        self._median_line.set_ydata(median)

        # Update the basis data used for peak snapping
        peak_basis = self._settings.get('peak_basis', 'median')
        if peak_basis == 'median':
            self._basis_data = median
        else:
            self._basis_data = m

        # Update stored arrays for consistency
        self._mean = m
        self._std = s
        self._median = median

        # Update info label with visible window count
        n_visible = len(visible_cols)
        n_tot = len(self._rejected)
        self._info_label.setText(
            f"Station: {self._label}\n"
            f"Windows: {n_visible}/{n_tot} visible\n"
            f"Click on canvas to add peaks\n"
            f"Right-click to remove nearest peak")

        self._canvas.draw_idle()

    def _on_click(self, event):
        if event.inaxes != self._ax:
            return
        if self._toolbar.mode != '':
            return  # zoom/pan active

        if event.button == 1:  # left click — add peak
            idx = np.abs(self._freq - event.xdata).argmin()
            freq = float(self._freq[idx])
            amp = float(self._basis_data[idx])
            self._add_peak(freq, amp)
        elif event.button == 3:  # right click — remove nearest peak
            if self._peak_coords:
                dists = [abs(np.log10(f) - np.log10(event.xdata))
                         for f, _ in self._peak_coords]
                nearest = int(np.argmin(dists))
                self._remove_peak(nearest)

    def _add_peak(self, freq: float, amp: float):
        self._peak_coords.append((freq, amp))
        is_primary = (len(self._peak_coords) == 1)
        marker = '*' if is_primary else 'o'
        ms = 14 if is_primary else 8
        color = '#FFD700' if is_primary else 'r'
        scat, = self._ax.plot(freq, amp, marker=marker, color=color,
                              markersize=ms, markeredgecolor='black',
                              markeredgewidth=1, zorder=5)
        lbl = f"★ {freq:.2f} Hz" if is_primary else f"{freq:.2f} Hz"
        ann = self._ax.annotate(
            lbl, xy=(freq, amp), xycoords='data',
            xytext=(15, 15), textcoords='offset points',
            fontsize=10, arrowprops=dict(arrowstyle='->'),
            bbox=dict(boxstyle='round,pad=0.3',
                      fc='gold' if is_primary else 'yellow', alpha=0.85, lw=0))
        self._peak_scatter.append(scat)
        self._peak_annots.append(ann)
        self._canvas.draw_idle()
        self._update_peak_list()

    def _remove_peak(self, index: int):
        if 0 <= index < len(self._peak_coords):
            self._peak_coords.pop(index)
            self._peak_scatter.pop(index).remove()
            self._peak_annots.pop(index).remove()
            if self._primary_idx >= len(self._peak_coords):
                self._primary_idx = 0
            self._canvas.draw_idle()
            self._update_peak_list()

    def _undo_peak(self):
        if self._peak_coords:
            self._remove_peak(len(self._peak_coords) - 1)

    def _clear_all(self):
        while self._peak_coords:
            self._peak_coords.pop()
            self._peak_scatter.pop().remove()
            self._peak_annots.pop().remove()
        self._primary_idx = 0
        self._canvas.draw_idle()
        self._update_peak_list()

    def _auto_detect(self):
        """Run automatic peak detection."""
        self._clear_all()
        freq_min = self._settings.get('freq_min', 0.2)
        freq_max = self._settings.get('freq_max', 30.0)
        min_prom = self._settings.get('min_prominence', 0.5)
        min_amp = self._settings.get('min_amplitude', 2.0)
        max_peaks = self._settings.get('auto_npeaks', 3)

        try:
            from hvsr_pro.processing.windows.peaks import detect_peaks
            detected = detect_peaks(
                self._freq, self._basis_data,
                min_prominence=min_prom,
                min_amplitude=min_amp,
                freq_range=(freq_min, freq_max),
            )[:max_peaks]
            for pk in detected:
                self._add_peak(pk.frequency, pk.amplitude)
            logger.info("Auto-detected %d peaks", len(detected))
        except ImportError:
            from scipy.signal import find_peaks as sp_find
            mask = (self._freq >= freq_min) & (self._freq <= freq_max)
            hv_sub = self._basis_data[mask]
            fr_sub = self._freq[mask]
            pidx, _ = sp_find(hv_sub, prominence=min_prom, height=min_amp)
            sorted_idx = sorted(range(len(pidx)),
                                key=lambda k: hv_sub[pidx[k]], reverse=True)
            for si in sorted_idx[:max_peaks]:
                self._add_peak(float(fr_sub[pidx[si]]),
                               float(hv_sub[pidx[si]]))
            logger.info("Auto-detected %d peaks via scipy", min(max_peaks, len(pidx)))

    def _update_peak_list(self):
        self._peak_list.clear()
        for i, (f, a) in enumerate(self._peak_coords):
            prefix = "★ " if i == self._primary_idx else ""
            self._peak_list.addItem(f"{prefix}{f:.3f} Hz  (A={a:.2f})")

    def get_peaks(self) -> List[Tuple[float, float]]:
        """Return list of (frequency, amplitude) for accepted peaks."""
        return list(self._peak_coords)

    def get_primary_peak(self) -> Optional[Tuple[float, float]]:
        """Return the primary peak (freq, amp) or None."""
        if self._peak_coords:
            return self._peak_coords[self._primary_idx]
        return None
