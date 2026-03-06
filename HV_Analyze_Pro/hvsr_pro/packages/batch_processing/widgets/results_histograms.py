"""
Results Histogram Widget
=========================

Matplotlib canvas showing peak frequency distributions (F0, F1, F2)
with statistics annotations.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
    QLabel, QFileDialog, QMessageBox
)
from PyQt5.QtCore import pyqtSignal

import numpy as np
from typing import List, Dict, Optional

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# Colors matching results_canvas peak colors
PEAK_COLORS = {0: '#d62728', 1: '#1f77b4', 2: '#2ca02c'}
PEAK_LABELS = {0: 'F0 (Primary)', 1: 'F1 (Secondary)', 2: 'F2 (Tertiary)'}

# Array bar colors
ARRAY_COLORS = [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
]


class ResultsHistogramWidget(QWidget):
    """Histogram canvas for peak frequency distributions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._station_results = []
        self._array_names = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)

        # Controls
        ctrl = QHBoxLayout()
        ctrl.addWidget(QLabel("Peak:"))
        self.peak_combo = QComboBox()
        self.peak_combo.addItems(["F0 (Primary)", "F1 (Secondary)", "F2 (Tertiary)", "All Peaks"])
        self.peak_combo.currentIndexChanged.connect(self._on_combo_changed)
        ctrl.addWidget(self.peak_combo)

        ctrl.addWidget(QLabel("  Style:"))
        self.style_combo = QComboBox()
        self.style_combo.addItems(["Simple Count", "By Array"])
        self.style_combo.currentIndexChanged.connect(self._on_combo_changed)
        ctrl.addWidget(self.style_combo)

        ctrl.addStretch()

        self.btn_export = QPushButton("Export")
        self.btn_export.clicked.connect(self._export)
        ctrl.addWidget(self.btn_export)

        layout.addLayout(ctrl)

        # Figure
        self.fig = Figure(figsize=(5, 3), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvas(self.fig)
        layout.addWidget(self.canvas, stretch=1)

        # Stats label
        self.stats_label = QLabel("")
        self.stats_label.setWordWrap(True)
        self.stats_label.setStyleSheet("color: #444; font-size: 11px; padding: 4px;")
        layout.addWidget(self.stats_label)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_data(self, station_results: list, array_names: list):
        """Store references and plot the default (F0) histogram."""
        self._station_results = station_results
        self._array_names = array_names
        self._plot_histogram(0)

    def refresh(self, station_results: list):
        """Refresh with updated (checked-only) station results."""
        self._station_results = station_results
        idx = self.peak_combo.currentIndex()
        peak_idx = idx if idx < 3 else -1
        self._plot_histogram(peak_idx)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_combo_changed(self, _idx=None):
        combo_idx = self.peak_combo.currentIndex()
        peak_idx = combo_idx if combo_idx < 3 else -1  # -1 = all
        simple = self.style_combo.currentIndex() == 0
        self._plot_histogram(peak_idx, simple=simple)

    def _collect_freqs(self, peak_idx: int):
        """Collect peak frequencies grouped by array."""
        freq_by_array = {}
        for sr in self._station_results:
            peaks_sorted = sorted(sr.peaks, key=lambda p: p.frequency) if sr.peaks else []
            if peak_idx == -1:
                freqs = [p.frequency for p in peaks_sorted[:3]]
            else:
                freqs = [peaks_sorted[peak_idx].frequency] if peak_idx < len(peaks_sorted) else []
            if freqs:
                freq_by_array.setdefault(sr.topic, []).extend(freqs)
        all_freqs = []
        for arr_freqs in freq_by_array.values():
            all_freqs.extend(arr_freqs)
        return freq_by_array, all_freqs

    def _plot_histogram(self, peak_idx: int, simple: bool = True):
        """
        Plot histogram for a given peak rank.

        Parameters
        ----------
        peak_idx : int
            0=F0, 1=F1, 2=F2, -1=all peaks.
        simple : bool
            True = single-color count histogram.
            False = stacked bars colored by array.
        """
        self.ax.clear()

        if not self._station_results:
            self.ax.set_title("No data")
            self.canvas.draw_idle()
            self.stats_label.setText("")
            return

        freq_by_array, all_freqs = self._collect_freqs(peak_idx)

        if not all_freqs:
            title = PEAK_LABELS.get(peak_idx, "All Peaks") if peak_idx >= 0 else "All Peaks"
            self.ax.set_title(f"{title} — No peaks found")
            self.canvas.draw_idle()
            self.stats_label.setText("")
            return

        # Determine bins
        f_min = min(all_freqs) * 0.8
        f_max = max(all_freqs) * 1.2
        n_bins = min(20, max(5, len(all_freqs) // 2))
        bins = np.linspace(f_min, f_max, n_bins + 1)

        if simple:
            # Simple count histogram — one color, no array breakdown
            pk_color = PEAK_COLORS.get(peak_idx, '#555555') if peak_idx >= 0 else '#555555'
            self.ax.hist(
                all_freqs, bins=bins,
                color=pk_color, edgecolor='white', linewidth=0.5,
                alpha=0.85,
            )
        else:
            # Stacked histogram colored by array
            arrays_ordered = [a for a in self._array_names if a in freq_by_array]
            data_list = [np.array(freq_by_array[a]) for a in arrays_ordered]
            colors = [ARRAY_COLORS[self._array_names.index(a) % len(ARRAY_COLORS)]
                      for a in arrays_ordered]
            if data_list:
                self.ax.hist(
                    data_list, bins=bins, stacked=True,
                    color=colors, edgecolor='white', linewidth=0.5,
                    label=arrays_ordered,
                )
                self.ax.legend(fontsize=7, loc='upper right')

        # Mean line
        mean_f = float(np.mean(all_freqs))
        std_f = float(np.std(all_freqs))
        self.ax.axvline(mean_f, color='black', ls='--', lw=1.5,
                        label=f'Mean={mean_f:.2f} Hz')

        # Title and labels
        if peak_idx >= 0:
            title = PEAK_LABELS.get(peak_idx, f"F{peak_idx}")
        else:
            title = "All Peaks"
        mode_str = "Count" if simple else "By Array"
        self.ax.set_title(f"{title} Frequency Distribution ({mode_str})")
        self.ax.set_xlabel("Frequency (Hz)")
        self.ax.set_ylabel("Number of Stations")
        self.ax.grid(True, axis='y', ls=':', alpha=0.5)
        # Force integer y-ticks
        from matplotlib.ticker import MaxNLocator
        self.ax.yaxis.set_major_locator(MaxNLocator(integer=True))

        self.fig.tight_layout()
        self.canvas.draw_idle()

        # Stats text
        median_f = float(np.median(all_freqs))
        min_f = float(np.min(all_freqs))
        max_f = float(np.max(all_freqs))
        n = len(all_freqs)
        self.stats_label.setText(
            f"Mean: {mean_f:.3f} ± {std_f:.3f} Hz  |  "
            f"Median: {median_f:.3f} Hz  |  "
            f"Range: {min_f:.3f} – {max_f:.3f} Hz  |  "
            f"N = {n}"
        )

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Histogram", "histogram.png",
            "PNG (*.png);;PDF (*.pdf);;SVG (*.svg)"
        )
        if not path:
            return
        try:
            self.fig.savefig(path, dpi=300, bbox_inches='tight')
            QMessageBox.information(self, "Export", f"Histogram saved to:\n{path}")
        except Exception as e:
            QMessageBox.warning(self, "Export Error", str(e))
