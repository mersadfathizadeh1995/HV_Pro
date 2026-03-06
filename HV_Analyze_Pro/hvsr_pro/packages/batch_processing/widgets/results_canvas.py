"""
Results Canvas Widget
======================

Matplotlib canvas displaying all station median HVSR curves with
peak markers, grand median, and ±1σ band.
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QComboBox, QSpinBox, QLabel, QDoubleSpinBox,
                             QColorDialog, QGroupBox, QGridLayout)
from PyQt5.QtCore import pyqtSignal

import numpy as np
from typing import List, Dict, Any, Optional, Tuple

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.colors as mcolors

# Distinct color palette for arrays
ARRAY_COLORS = [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
]

# Peak marker colors by rank
PEAK_COLORS = {0: '#d62728', 1: '#1f77b4', 2: '#2ca02c'}  # F0=red, F1=blue, F2=green
PEAK_LABELS = {0: 'F0', 1: 'F1', 2: 'F2'}


def _compute_smart_ylim(all_hvsr_arrays, n_sigma=4):
    """Compute Y-axis limits that clip outliers using robust statistics.

    Uses median and MAD (median absolute deviation) which are resistant
    to single extreme curves (e.g. a window with H/V > 200).

    Parameters
    ----------
    all_hvsr_arrays : list of array-like
        Each element is a 1-D H/V curve.
    n_sigma : int
        Number of MAD-based deviations above the median for the upper limit.

    Returns
    -------
    (y_min, y_max) : tuple of float
        Sensible Y-axis bounds.  Returns None if input is empty.
    """
    if not all_hvsr_arrays:
        return None
    stacked = np.column_stack(all_hvsr_arrays)      # (n_freq, n_curves)
    med = np.median(stacked, axis=1)                 # per-frequency median
    # MAD scaled to match std for normal distributions (factor 1.4826)
    mad = np.median(np.abs(stacked - med[:, None]), axis=1) * 1.4826
    upper_env = med + n_sigma * mad
    y_max = float(np.max(upper_env))
    y_min = float(min(0.0, np.min(med - n_sigma * mad)))
    # Guarantee a minimum visible range
    if y_max - y_min < 1.0:
        y_max = y_min + 1.0
    # Small padding
    y_max *= 1.05
    return (y_min, y_max)


def _station_color(array_idx: int, station_idx: int, n_stations: int) -> str:
    """Generate a unique color for a station within an array."""
    base = mcolors.to_rgb(ARRAY_COLORS[array_idx % len(ARRAY_COLORS)])
    # Lighten/darken based on station index
    factor = 0.6 + 0.4 * (station_idx / max(1, n_stations - 1)) if n_stations > 1 else 1.0
    r = min(1.0, base[0] * factor)
    g = min(1.0, base[1] * factor)
    b = min(1.0, base[2] * factor)
    return mcolors.to_hex((r, g, b))


class ResultsCanvasWidget(QWidget):
    """Matplotlib canvas for HVSR median curves and peaks."""

    manual_peaks_changed = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._station_lines = {}       # (array, station) -> Line2D
        self._peak_markers = {}        # (array, station, peak_idx) -> Line2D
        self._peak_annotations = {}    # (array, station, peak_idx) -> Annotation
        self._array_median_lines = {}  # array_name -> Line2D
        self._array_std_fills = {}     # array_name -> PolyCollection (±1σ band)
        self._grand_median_line = None
        self._grand_std_fill = None
        self._combined_std_plus = None   # grand_median + combined_std line
        self._combined_std_minus = None  # grand_median - combined_std line

        # Manual peak picking state
        self._pick_mode = False
        self._manual_peak_markers = []   # list of Line2D
        self._manual_peak_annotations = []  # list of Annotation
        self._manual_peaks = []          # list of {'frequency': f, 'amplitude': a}
        self._click_cid = None           # mpl_connect id
        self._release_cid = None         # mpl_connect id for button release
        self._drag_start = None          # (freq, amp) while mouse held
        self._drag_temp_marker = None    # temporary marker during drag

        # Marker style defaults (primary = peak 0, secondary = peaks 1+)
        self._marker_styles = {
            'primary_shape': '*',
            'primary_color': '#e74c3c',
            'primary_size': 14,
            'secondary_shape': '*',
            'secondary_color': '#3498db',
            'secondary_size': 10,
        }

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)

        # Matplotlib figure
        self.fig = Figure(figsize=(8, 5), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.canvas = FigureCanvas(self.fig)

        # Navigation toolbar
        self.toolbar = NavigationToolbar(self.canvas, self)

        # Peak picking toolbar
        pick_layout = QHBoxLayout()
        self.btn_pick_peaks = QPushButton("Pick Peaks")
        self.btn_pick_peaks.setCheckable(True)
        self.btn_pick_peaks.setStyleSheet(
            "QPushButton:checked { background-color: #e74c3c; color: white; }")
        self.btn_pick_peaks.toggled.connect(self._toggle_pick_mode)
        pick_layout.addWidget(self.btn_pick_peaks)

        pick_layout.addWidget(QLabel("Max:"))
        self.pick_max_spin = QSpinBox()
        self.pick_max_spin.setRange(1, 10)
        self.pick_max_spin.setValue(3)
        self.pick_max_spin.setToolTip("Maximum number of manual peaks")
        pick_layout.addWidget(self.pick_max_spin)

        self.btn_clear_picks = QPushButton("Clear Picks")
        self.btn_clear_picks.clicked.connect(self.clear_manual_peaks)
        pick_layout.addWidget(self.btn_clear_picks)

        self.pick_status_label = QLabel("")
        pick_layout.addWidget(self.pick_status_label)

        pick_layout.addStretch()

        # Marker style toolbar
        marker_layout = QHBoxLayout()
        marker_layout.addWidget(QLabel("Primary:"))

        self.primary_shape_combo = QComboBox()
        self.primary_shape_combo.addItems(['*', 'o', 's', 'D', '^', 'v', 'P', 'X'])
        self.primary_shape_combo.setCurrentText('*')
        self.primary_shape_combo.setToolTip("Primary peak marker shape")
        self.primary_shape_combo.setMaximumWidth(50)
        marker_layout.addWidget(self.primary_shape_combo)

        self.primary_size_spin = QDoubleSpinBox()
        self.primary_size_spin.setRange(4, 30)
        self.primary_size_spin.setValue(14)
        self.primary_size_spin.setDecimals(0)
        self.primary_size_spin.setToolTip("Primary peak marker size")
        self.primary_size_spin.setMaximumWidth(50)
        marker_layout.addWidget(self.primary_size_spin)

        self.btn_primary_color = QPushButton()
        self.btn_primary_color.setFixedSize(24, 24)
        self.btn_primary_color.setStyleSheet("background-color: #e74c3c; border: 1px solid #333;")
        self.btn_primary_color.setToolTip("Primary peak color")
        self.btn_primary_color.clicked.connect(lambda: self._pick_marker_color('primary'))
        marker_layout.addWidget(self.btn_primary_color)

        marker_layout.addWidget(QLabel("  Secondary:"))

        self.secondary_shape_combo = QComboBox()
        self.secondary_shape_combo.addItems(['*', 'o', 's', 'D', '^', 'v', 'P', 'X'])
        self.secondary_shape_combo.setCurrentText('*')
        self.secondary_shape_combo.setToolTip("Secondary peak marker shape")
        self.secondary_shape_combo.setMaximumWidth(50)
        marker_layout.addWidget(self.secondary_shape_combo)

        self.secondary_size_spin = QDoubleSpinBox()
        self.secondary_size_spin.setRange(4, 30)
        self.secondary_size_spin.setValue(10)
        self.secondary_size_spin.setDecimals(0)
        self.secondary_size_spin.setToolTip("Secondary peak marker size")
        self.secondary_size_spin.setMaximumWidth(50)
        marker_layout.addWidget(self.secondary_size_spin)

        self.btn_secondary_color = QPushButton()
        self.btn_secondary_color.setFixedSize(24, 24)
        self.btn_secondary_color.setStyleSheet("background-color: #3498db; border: 1px solid #333;")
        self.btn_secondary_color.setToolTip("Secondary peak color")
        self.btn_secondary_color.clicked.connect(lambda: self._pick_marker_color('secondary'))
        marker_layout.addWidget(self.btn_secondary_color)

        marker_layout.addStretch()

        # Export buttons
        btn_layout = QHBoxLayout()
        self.btn_export_png = QPushButton("Export PNG")
        self.btn_export_png.clicked.connect(lambda: self._export_figure("png"))
        btn_layout.addWidget(self.btn_export_png)

        self.btn_export_pdf = QPushButton("Export PDF")
        self.btn_export_pdf.clicked.connect(lambda: self._export_figure("pdf"))
        btn_layout.addWidget(self.btn_export_pdf)

        btn_layout.addStretch()

        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas, stretch=1)
        layout.addLayout(pick_layout)
        layout.addLayout(marker_layout)
        layout.addLayout(btn_layout)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def plot_all(self, station_results: list, array_names: list):
        """
        Plot all station median curves grouped by array.

        Parameters
        ----------
        station_results : list
            List of StationResult objects.
        array_names : list
            Ordered list of unique array/topic names.
        """
        self.ax.clear()
        self._station_lines.clear()
        self._peak_markers.clear()
        self._peak_annotations.clear()
        self._array_median_lines.clear()
        self._array_std_fills.clear()
        self._grand_median_line = None
        self._grand_std_fill = None
        self._combined_std_plus = None
        self._combined_std_minus = None

        if not station_results:
            self.canvas.draw_idle()
            return

        # Group by array
        arrays = {}
        for sr in station_results:
            arrays.setdefault(sr.topic, []).append(sr)

        # Plot each station curve
        for arr_idx, arr_name in enumerate(array_names):
            stations = arrays.get(arr_name, [])
            n_stn = len(stations)
            for stn_idx, sr in enumerate(stations):
                color = _station_color(arr_idx, stn_idx, n_stn)
                label = f"{arr_name}_{sr.station_name}"
                line, = self.ax.plot(
                    sr.frequencies, sr.mean_hvsr,
                    color=color, lw=1.0, alpha=0.8, label=label
                )
                self._station_lines[(arr_name, sr.station_name)] = line

                # Plot peak markers
                peaks_sorted = sorted(sr.peaks, key=lambda p: p.frequency) if sr.peaks else []
                for pk_idx, pk in enumerate(peaks_sorted[:3]):
                    pk_color = PEAK_COLORS.get(pk_idx, '#333333')
                    marker, = self.ax.plot(
                        pk.frequency, pk.amplitude,
                        'o', color=pk_color, markersize=6, zorder=5
                    )
                    ann = self.ax.annotate(
                        f"{pk.frequency:.2f}",
                        xy=(pk.frequency, pk.amplitude),
                        xytext=(5, 5), textcoords='offset points',
                        fontsize=7, color=pk_color,
                        bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.7, lw=0)
                    )
                    self._peak_markers[(arr_name, sr.station_name, pk_idx)] = marker
                    self._peak_annotations[(arr_name, sr.station_name, pk_idx)] = ann

        # Per-array median curves with ±1σ bands
        for arr_idx, arr_name in enumerate(array_names):
            stations = arrays.get(arr_name, [])
            if not stations:
                continue
            freq = stations[0].frequencies
            hvsr_stack = [s.mean_hvsr for s in stations if len(s.mean_hvsr) == len(freq)]
            if len(hvsr_stack) < 1:
                continue
            arr_data = np.array(hvsr_stack)
            arr_median = np.median(arr_data, axis=0)
            arr_std = np.std(arr_data, axis=0)
            base_color = ARRAY_COLORS[arr_idx % len(ARRAY_COLORS)]
            line, = self.ax.plot(
                freq, arr_median,
                color=base_color, lw=2.5, ls='--', alpha=0.9,
                label=f"{arr_name} Median"
            )
            self._array_median_lines[arr_name] = line
            # ±1σ band for this array
            fill = self.ax.fill_between(
                freq, arr_median - arr_std, arr_median + arr_std,
                color=base_color, alpha=0.08, zorder=1
            )
            self._array_std_fills[arr_name] = fill

        # Grand median (all stations)
        all_freq = station_results[0].frequencies
        all_stack = [s.mean_hvsr for s in station_results if len(s.mean_hvsr) == len(all_freq)]
        if all_stack:
            grand_median = np.median(np.array(all_stack), axis=0)
            grand_std = np.std(np.array(all_stack), axis=0)
            self._grand_median_line, = self.ax.plot(
                all_freq, grand_median,
                color='black', lw=2.5, ls='-', label='Grand Median', zorder=10
            )
            # Inter-station ±1σ band (OFF by default)
            self._grand_std_fill = self.ax.fill_between(
                all_freq,
                grand_median - grand_std,
                grand_median + grand_std,
                color='gray', alpha=0.15, label='±1σ Band', zorder=1
            )
            self._grand_std_fill.set_visible(False)

            # Combined std: median of per-station std_hvsr (intra-station uncertainty)
            std_stack = [s.std_hvsr for s in station_results
                         if s.std_hvsr is not None and len(s.std_hvsr) == len(all_freq)]
            if std_stack:
                combined_std = np.median(np.array(std_stack), axis=0)
                self._combined_std_plus, = self.ax.plot(
                    all_freq, grand_median + combined_std,
                    color='#2ca02c', lw=1.2, ls='--', alpha=0.7,
                    label='+Std (combined)', zorder=9
                )
                self._combined_std_minus, = self.ax.plot(
                    all_freq, grand_median - combined_std,
                    color='#2ca02c', lw=1.2, ls='--', alpha=0.7,
                    label='-Std (combined)', zorder=9
                )

        # Smart Y-axis limits (median + 4*std) to suppress outlier blow-up
        all_curves = [s.mean_hvsr for s in station_results]
        ylims = _compute_smart_ylim(all_curves, n_sigma=4)
        if ylims is not None:
            self.ax.set_ylim(*ylims)

        # Axes formatting
        self.ax.set_xscale('log')
        self.ax.set_xlabel('Frequency (Hz)')
        self.ax.set_ylabel('H/V Spectral Ratio')
        self.ax.set_title('HVSR — All Stations')
        self.ax.grid(True, which='both', ls=':', alpha=0.5)
        self.ax.legend(fontsize=7, ncol=3, loc='upper right', frameon=True, framealpha=0.8)

        self.fig.tight_layout()
        self.canvas.draw_idle()

    def replot_grand_median(self, checked_results: list):
        """
        Recompute and redraw grand median from checked stations only.

        Parameters
        ----------
        checked_results : list
            StationResult objects for checked stations.
        """
        # Remove old grand median artists
        if self._grand_median_line is not None:
            self._grand_median_line.remove()
            self._grand_median_line = None
        if self._grand_std_fill is not None:
            self._grand_std_fill.remove()
            self._grand_std_fill = None
        if self._combined_std_plus is not None:
            self._combined_std_plus.remove()
            self._combined_std_plus = None
        if self._combined_std_minus is not None:
            self._combined_std_minus.remove()
            self._combined_std_minus = None

        if not checked_results:
            self.canvas.draw_idle()
            return

        freq = checked_results[0].frequencies
        stack = [s.mean_hvsr for s in checked_results if len(s.mean_hvsr) == len(freq)]
        if not stack:
            self.canvas.draw_idle()
            return

        grand_median = np.median(np.array(stack), axis=0)
        grand_std = np.std(np.array(stack), axis=0)

        self._grand_median_line, = self.ax.plot(
            freq, grand_median,
            color='black', lw=2.5, ls='-', label='Grand Median', zorder=10
        )
        # Inter-station ±1σ band (OFF by default)
        self._grand_std_fill = self.ax.fill_between(
            freq,
            grand_median - grand_std,
            grand_median + grand_std,
            color='gray', alpha=0.15, label='±1σ Band', zorder=1
        )
        self._grand_std_fill.set_visible(False)

        # Combined std: median of per-station std_hvsr (intra-station uncertainty)
        std_stack = [s.std_hvsr for s in checked_results
                     if s.std_hvsr is not None and len(s.std_hvsr) == len(freq)]
        if std_stack:
            combined_std = np.median(np.array(std_stack), axis=0)
            self._combined_std_plus, = self.ax.plot(
                freq, grand_median + combined_std,
                color='#2ca02c', lw=1.2, ls='--', alpha=0.7,
                label='+Std (combined)', zorder=9
            )
            self._combined_std_minus, = self.ax.plot(
                freq, grand_median - combined_std,
                color='#2ca02c', lw=1.2, ls='--', alpha=0.7,
                label='-Std (combined)', zorder=9
            )

        # Recompute smart Y-limits from checked data
        ylims = _compute_smart_ylim([s.mean_hvsr for s in checked_results], n_sigma=4)
        if ylims is not None:
            self.ax.set_ylim(*ylims)

        # Rebuild legend
        self.ax.legend(fontsize=7, ncol=3, loc='upper right', frameon=True, framealpha=0.8)
        self.canvas.draw_idle()

    def replot_array_median(self, array_name: str, checked_results: list):
        """Recompute per-array median from checked stations for one array."""
        # Remove old line
        old = self._array_median_lines.pop(array_name, None)
        if old is not None:
            old.remove()

        stations = [s for s in checked_results if s.topic == array_name]
        if not stations:
            self.canvas.draw_idle()
            return

        freq = stations[0].frequencies
        stack = [s.mean_hvsr for s in stations if len(s.mean_hvsr) == len(freq)]
        if not stack:
            self.canvas.draw_idle()
            return

        arr_median = np.median(np.array(stack), axis=0)
        # Find array index for color
        arr_idx = 0
        line, = self.ax.plot(
            freq, arr_median,
            color=ARRAY_COLORS[arr_idx % len(ARRAY_COLORS)],
            lw=2.5, ls='--', alpha=0.9, label=f"{array_name} Median"
        )
        self._array_median_lines[array_name] = line
        self.ax.legend(fontsize=7, ncol=3, loc='upper right', frameon=True, framealpha=0.8)
        self.canvas.draw_idle()

    # ------------------------------------------------------------------
    # Visibility control (called by layer tree)
    # ------------------------------------------------------------------

    def set_station_visible(self, array_name: str, station_name: str, visible: bool):
        """Toggle visibility of a single station curve and its peaks."""
        key = (array_name, station_name)
        line = self._station_lines.get(key)
        if line:
            line.set_visible(visible)

        # Toggle associated peak markers and annotations
        for pk_idx in range(3):
            mk = self._peak_markers.get((array_name, station_name, pk_idx))
            if mk:
                mk.set_visible(visible)
            ann = self._peak_annotations.get((array_name, station_name, pk_idx))
            if ann:
                ann.set_visible(visible)

        self.canvas.draw_idle()

    def set_array_median_visible(self, array_name: str, visible: bool):
        """Toggle visibility of an array median curve and its ±1σ band."""
        line = self._array_median_lines.get(array_name)
        if line:
            line.set_visible(visible)
        fill = self._array_std_fills.get(array_name)
        if fill:
            fill.set_visible(visible)
        self.canvas.draw_idle()

    def set_grand_median_visible(self, visible: bool):
        """Toggle visibility of grand median and ±1σ band."""
        if self._grand_median_line:
            self._grand_median_line.set_visible(visible)
        if self._grand_std_fill:
            self._grand_std_fill.set_visible(visible)
        self.canvas.draw_idle()

    def set_std_band_visible(self, visible: bool):
        """Toggle visibility of ±1σ band only."""
        if self._grand_std_fill:
            self._grand_std_fill.set_visible(visible)
            self.canvas.draw_idle()

    def set_combined_std_visible(self, visible: bool):
        """Toggle visibility of combined std (±) lines."""
        if self._combined_std_plus:
            self._combined_std_plus.set_visible(visible)
        if self._combined_std_minus:
            self._combined_std_minus.set_visible(visible)
        self.canvas.draw_idle()

    def set_peak_group_visible(self, peak_idx: int, visible: bool):
        """Toggle visibility of ALL markers/annotations for a peak rank (0=F0, 1=F1, 2=F2)."""
        for key, mk in self._peak_markers.items():
            if key[2] == peak_idx:
                mk.set_visible(visible)
        for key, ann in self._peak_annotations.items():
            if key[2] == peak_idx:
                ann.set_visible(visible)
        self.canvas.draw_idle()

    # ------------------------------------------------------------------
    # Artist accessors (for layer tree)
    # ------------------------------------------------------------------

    def get_station_line(self, array_name, station_name):
        return self._station_lines.get((array_name, station_name))

    def get_array_median_line(self, array_name):
        return self._array_median_lines.get(array_name)

    def get_grand_median_line(self):
        return self._grand_median_line

    def get_grand_std_fill(self):
        return self._grand_std_fill

    # ------------------------------------------------------------------
    # Manual peak picking
    # ------------------------------------------------------------------

    def _pick_marker_color(self, which: str):
        """Open color picker for primary or secondary peak markers."""
        from PyQt5.QtGui import QColor
        current = self._marker_styles[f'{which}_color']
        color = QColorDialog.getColor(QColor(current), self, f"Pick {which} peak color")
        if color.isValid():
            hex_color = color.name()
            self._marker_styles[f'{which}_color'] = hex_color
            btn = self.btn_primary_color if which == 'primary' else self.btn_secondary_color
            btn.setStyleSheet(f"background-color: {hex_color}; border: 1px solid #333;")
            self._refresh_manual_peak_styles()

    def _get_marker_style(self, peak_index: int):
        """Return (shape, color, size) for the given peak index."""
        self._marker_styles['primary_shape'] = self.primary_shape_combo.currentText()
        self._marker_styles['primary_size'] = self.primary_size_spin.value()
        self._marker_styles['secondary_shape'] = self.secondary_shape_combo.currentText()
        self._marker_styles['secondary_size'] = self.secondary_size_spin.value()

        if peak_index == 0:
            return (self._marker_styles['primary_shape'],
                    self._marker_styles['primary_color'],
                    self._marker_styles['primary_size'])
        return (self._marker_styles['secondary_shape'],
                self._marker_styles['secondary_color'],
                self._marker_styles['secondary_size'])

    def _refresh_manual_peak_styles(self):
        """Re-apply marker styles to all existing manual peaks."""
        for i, mk in enumerate(self._manual_peak_markers):
            shape, color, size = self._get_marker_style(i)
            mk.set_marker(shape)
            mk.set_color(color)
            mk.set_markersize(size)
        for i, ann in enumerate(self._manual_peak_annotations):
            _, color, _ = self._get_marker_style(i)
            ann.get_bbox_patch().set_edgecolor(color)
            ann.set_color(color)
        self.canvas.draw_idle()

    def _toggle_pick_mode(self, active: bool):
        """Enable or disable click-drag-release peak picking."""
        self._pick_mode = active
        if active:
            self._click_cid = self.canvas.mpl_connect(
                'button_press_event', self._on_canvas_press)
            self._release_cid = self.canvas.mpl_connect(
                'button_release_event', self._on_canvas_release)
            self.btn_pick_peaks.setText("Picking... (click & drag)")
        else:
            if self._click_cid is not None:
                self.canvas.mpl_disconnect(self._click_cid)
                self._click_cid = None
            if self._release_cid is not None:
                self.canvas.mpl_disconnect(self._release_cid)
                self._release_cid = None
            self._drag_start = None
            if self._drag_temp_marker is not None:
                self._drag_temp_marker.remove()
                self._drag_temp_marker = None
            self.btn_pick_peaks.setText("Pick Peaks")

    def _snap_to_median(self, xdata_click):
        """Return (freq, amp) snapped to nearest grand median point."""
        if self._grand_median_line is None:
            return None
        xdata = np.array(self._grand_median_line.get_xdata())
        ydata = np.array(self._grand_median_line.get_ydata())
        if len(xdata) == 0:
            return None
        log_dist = np.abs(np.log10(xdata) - np.log10(xdata_click))
        idx = int(np.argmin(log_dist))
        return float(xdata[idx]), float(ydata[idx])

    def _on_canvas_press(self, event):
        """Mouse press: snap to peak, show temporary marker."""
        if not self._pick_mode or event.inaxes != self.ax:
            return

        # Right-click removes nearest peak
        if event.button == 3:
            self._remove_nearest_manual_peak(event.xdata)
            return

        if event.button != 1:
            return

        max_peaks = self.pick_max_spin.value()
        if len(self._manual_peaks) >= max_peaks:
            return

        result = self._snap_to_median(event.xdata)
        if result is None:
            return
        freq, amp = result

        # Avoid duplicates
        for pk in self._manual_peaks:
            if abs(pk['frequency'] - freq) / freq < 0.01:
                return

        self._drag_start = (freq, amp)
        peak_idx = len(self._manual_peaks)
        shape, color, size = self._get_marker_style(peak_idx)
        self._drag_temp_marker, = self.ax.plot(
            freq, amp, shape, color=color, markersize=size,
            markeredgecolor='black', markeredgewidth=0.8, zorder=20)
        self.canvas.draw_idle()

    def _on_canvas_release(self, event):
        """Mouse release: place annotation at release point with arrow to peak."""
        if self._drag_start is None or event.button != 1:
            return

        freq, amp = self._drag_start
        self._drag_start = None

        # Remove temp marker and create final marker
        if self._drag_temp_marker is not None:
            self._drag_temp_marker.remove()
            self._drag_temp_marker = None

        peak_idx = len(self._manual_peaks)
        shape, color, size = self._get_marker_style(peak_idx)

        marker, = self.ax.plot(
            freq, amp, shape, color=color, markersize=size,
            markeredgecolor='black', markeredgewidth=0.8, zorder=20)

        # Annotation at release position (or offset if no drag)
        if event.inaxes == self.ax and event.xdata is not None:
            ann = self.ax.annotate(
                f"{freq:.2f} Hz",
                xy=(freq, amp), xycoords='data',
                xytext=(event.xdata, event.ydata), textcoords='data',
                fontsize=8, fontweight='bold', color=color,
                arrowprops=dict(arrowstyle='->', color=color),
                bbox=dict(boxstyle='round,pad=0.3', fc='white',
                          ec=color, alpha=0.9, lw=1))
        else:
            ann = self.ax.annotate(
                f"{freq:.2f} Hz",
                xy=(freq, amp), xytext=(12, 12),
                textcoords='offset points',
                fontsize=8, fontweight='bold', color=color,
                arrowprops=dict(arrowstyle='->', color=color),
                bbox=dict(boxstyle='round,pad=0.3', fc='white',
                          ec=color, alpha=0.9, lw=1))
        ann.set_annotation_clip(False)

        self._manual_peak_markers.append(marker)
        self._manual_peak_annotations.append(ann)
        self._manual_peaks.append({'frequency': freq, 'amplitude': amp})

        # Sort by frequency
        combined = sorted(
            zip(self._manual_peaks, self._manual_peak_markers,
                self._manual_peak_annotations),
            key=lambda t: t[0]['frequency'])
        if combined:
            self._manual_peaks = [c[0] for c in combined]
            self._manual_peak_markers = [c[1] for c in combined]
            self._manual_peak_annotations = [c[2] for c in combined]

        # Re-apply styles after sort (primary/secondary may have changed)
        self._refresh_manual_peak_styles()
        self._update_pick_status()
        self.canvas.draw_idle()
        self.manual_peaks_changed.emit(list(self._manual_peaks))

    def _remove_nearest_manual_peak(self, click_freq):
        """Remove the manual peak nearest to click_freq."""
        if not self._manual_peaks:
            return

        dists = [abs(np.log10(pk['frequency']) - np.log10(click_freq))
                 for pk in self._manual_peaks]
        idx = int(np.argmin(dists))

        self._manual_peak_markers[idx].remove()
        self._manual_peak_annotations[idx].remove()
        del self._manual_peak_markers[idx]
        del self._manual_peak_annotations[idx]
        del self._manual_peaks[idx]

        self._update_pick_status()
        self.canvas.draw_idle()
        self.manual_peaks_changed.emit(list(self._manual_peaks))

    def clear_manual_peaks(self):
        """Remove all manual peak markers."""
        for mk in self._manual_peak_markers:
            mk.remove()
        for ann in self._manual_peak_annotations:
            ann.remove()
        self._manual_peak_markers.clear()
        self._manual_peak_annotations.clear()
        self._manual_peaks.clear()
        self._update_pick_status()
        self.canvas.draw_idle()
        self.manual_peaks_changed.emit([])

    def get_manual_peaks(self):
        """Return current manual peaks as list of dicts."""
        return list(self._manual_peaks)

    def _update_pick_status(self):
        n = len(self._manual_peaks)
        mx = self.pick_max_spin.value()
        if n == 0:
            self.pick_status_label.setText("")
        else:
            labels = [f"{pk['frequency']:.2f} Hz" for pk in self._manual_peaks]
            self.pick_status_label.setText(
                f"{n}/{mx} peaks: " + ", ".join(labels))

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def _export_figure(self, fmt: str):
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        ext = f"*.{fmt}"
        path, _ = QFileDialog.getSaveFileName(
            self, f"Export Figure as {fmt.upper()}",
            f"HVSR_AllMedians.{fmt}", f"{fmt.upper()} ({ext})"
        )
        if not path:
            return
        try:
            self.fig.savefig(path, dpi=300, bbox_inches='tight')
            QMessageBox.information(self, "Export", f"Figure saved to:\n{path}")
        except Exception as e:
            QMessageBox.warning(self, "Export Error", str(e))
