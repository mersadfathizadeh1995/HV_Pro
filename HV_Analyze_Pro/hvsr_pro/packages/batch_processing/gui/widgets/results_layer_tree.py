"""
Results Layer Tree Widget
==========================

Hierarchical QTreeWidget with checkboxes to toggle visibility of
HVSR median curves, per-array medians, and peak markers on the canvas.

Tree structure:
  ☑ All Medians
  │  ☑ Array_200m
  │  │  ☑ STN01 (F0=1.25 Hz)
  │  │  ☑ STN02 (F0=1.30 Hz)
  │  ☑ Array_300m
  │     ☑ STN01 ...
  ☑ Grand Median
  │  ☑ Grand Median Curve
  │  ☑ ±1σ Band
  ☑ Peaks
     ☑ F0 (Primary)
     ☑ F1 (Secondary)
     ☑ F2 (Tertiary)
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPixmap, QPainter, QIcon, QBrush

from typing import List, Dict, Optional
import matplotlib.colors as mcolors


def _make_color_icon(hex_color: str, size: int = 14) -> QIcon:
    """Create a small colored circle icon."""
    r, g, b, _ = mcolors.to_rgba(hex_color)
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor(int(r * 255), int(g * 255), int(b * 255)))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(1, 1, size - 2, size - 2)
    painter.end()
    return QIcon(pixmap)


def _make_line_icon(hex_color: str, size: int = 14, dashed: bool = False) -> QIcon:
    """Create a small horizontal-line icon."""
    from PyQt5.QtGui import QPen
    from PyQt5.QtCore import QLine
    r, g, b, _ = mcolors.to_rgba(hex_color)
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor(int(r * 255), int(g * 255), int(b * 255)), 2)
    if dashed:
        pen.setStyle(Qt.DashLine)
    painter.setPen(pen)
    painter.drawLine(1, size // 2, size - 1, size // 2)
    painter.end()
    return QIcon(pixmap)


# Array colors matching results_canvas
ARRAY_COLORS = [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
]

PEAK_COLORS = {0: '#d62728', 1: '#1f77b4', 2: '#2ca02c'}
PEAK_LABELS = {0: 'F0 (Primary)', 1: 'F1 (Secondary)', 2: 'F2 (Tertiary)'}


class ResultsLayerTree(QWidget):
    """Hierarchical layer tree for toggling HVSR curve visibility."""

    # Signals emitted when user toggles items
    station_visibility_changed = pyqtSignal(str, str, bool)      # array, station, visible
    array_median_visibility_changed = pyqtSignal(str, bool)      # array, visible
    grand_median_visibility_changed = pyqtSignal(bool)
    std_band_visibility_changed = pyqtSignal(bool)
    combined_std_visibility_changed = pyqtSignal(bool)           # combined std (±) lines
    peak_group_visibility_changed = pyqtSignal(int, bool)        # peak_idx, visible

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_all_on = QPushButton("All On")
        self.btn_all_on.clicked.connect(lambda: self._set_all(True))
        btn_layout.addWidget(self.btn_all_on)

        self.btn_all_off = QPushButton("All Off")
        self.btn_all_off.clicked.connect(lambda: self._set_all(False))
        btn_layout.addWidget(self.btn_all_off)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Tree
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Layer", "Info"])
        self.tree.setColumnCount(2)
        self.tree.setColumnWidth(0, 200)
        self.tree.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.tree)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(self, station_results: list, array_names: list, station_colors: dict):
        """
        Build the tree from station results.

        Parameters
        ----------
        station_results : list
            List of StationResult objects.
        array_names : list
            Ordered list of unique array/topic names.
        station_colors : dict
            Mapping (array_name, station_name) -> hex color string.
        """
        self.tree.blockSignals(True)
        self.tree.clear()

        # Group by array
        arrays = {}
        for sr in station_results:
            arrays.setdefault(sr.topic, []).append(sr)

        # ── All Medians group ──
        medians_root = QTreeWidgetItem(self.tree, ["All Medians", ""])
        medians_root.setFlags(medians_root.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsAutoTristate)
        medians_root.setCheckState(0, Qt.Checked)
        font = medians_root.font(0)
        font.setBold(True)
        medians_root.setFont(0, font)

        for arr_idx, arr_name in enumerate(array_names):
            stations = arrays.get(arr_name, [])
            arr_color = ARRAY_COLORS[arr_idx % len(ARRAY_COLORS)]

            # Array branch (includes per-array median)
            arr_item = QTreeWidgetItem(medians_root, [arr_name, f"{len(stations)} stations"])
            arr_item.setFlags(arr_item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsAutoTristate)
            arr_item.setCheckState(0, Qt.Checked)
            arr_item.setIcon(0, _make_line_icon(arr_color, dashed=True))
            arr_item.setData(0, Qt.UserRole, ('array_median', arr_name))
            arr_font = arr_item.font(0)
            arr_font.setBold(True)
            arr_item.setFont(0, arr_font)

            # Station children
            for sr in stations:
                color = station_colors.get((arr_name, sr.station_name), arr_color)
                f0_str = ""
                if sr.peaks:
                    peaks_sorted = sorted(sr.peaks, key=lambda p: p.frequency)
                    f0_str = f"F0={peaks_sorted[0].frequency:.2f} Hz"

                stn_item = QTreeWidgetItem(arr_item, [sr.station_name, f0_str])
                stn_item.setFlags(stn_item.flags() | Qt.ItemIsUserCheckable)
                stn_item.setCheckState(0, Qt.Checked)
                stn_item.setIcon(0, _make_color_icon(color))
                stn_item.setData(0, Qt.UserRole, ('station', arr_name, sr.station_name))

        medians_root.setExpanded(True)

        # ── Grand Median group ──
        grand_root = QTreeWidgetItem(self.tree, ["Grand Median", ""])
        grand_root.setFlags(grand_root.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsAutoTristate)
        grand_root.setCheckState(0, Qt.Checked)
        font_g = grand_root.font(0)
        font_g.setBold(True)
        grand_root.setFont(0, font_g)

        grand_curve = QTreeWidgetItem(grand_root, ["Grand Median Curve", ""])
        grand_curve.setFlags(grand_curve.flags() | Qt.ItemIsUserCheckable)
        grand_curve.setCheckState(0, Qt.Checked)
        grand_curve.setIcon(0, _make_line_icon('#000000'))
        grand_curve.setData(0, Qt.UserRole, ('grand_median',))

        std_band = QTreeWidgetItem(grand_root, ["±1σ Band", "inter-station"])
        std_band.setFlags(std_band.flags() | Qt.ItemIsUserCheckable)
        std_band.setCheckState(0, Qt.Unchecked)
        std_band.setIcon(0, _make_color_icon('#AAAAAA'))
        std_band.setData(0, Qt.UserRole, ('std_band',))

        combined_std = QTreeWidgetItem(grand_root, ["Combined Std (±)", "intra-station"])
        combined_std.setFlags(combined_std.flags() | Qt.ItemIsUserCheckable)
        combined_std.setCheckState(0, Qt.Checked)
        combined_std.setIcon(0, _make_line_icon('#2ca02c', dashed=True))
        combined_std.setData(0, Qt.UserRole, ('combined_std',))

        grand_root.setExpanded(True)

        # ── Peaks group ──
        peaks_root = QTreeWidgetItem(self.tree, ["Peaks", ""])
        peaks_root.setFlags(peaks_root.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsAutoTristate)
        peaks_root.setCheckState(0, Qt.Checked)
        font_p = peaks_root.font(0)
        font_p.setBold(True)
        peaks_root.setFont(0, font_p)

        for pk_idx in range(3):
            pk_color = PEAK_COLORS.get(pk_idx, '#333333')
            pk_label = PEAK_LABELS.get(pk_idx, f'F{pk_idx}')
            pk_item = QTreeWidgetItem(peaks_root, [pk_label, ""])
            pk_item.setFlags(pk_item.flags() | Qt.ItemIsUserCheckable)
            pk_item.setCheckState(0, Qt.Checked)
            pk_item.setIcon(0, _make_color_icon(pk_color))
            pk_item.setData(0, Qt.UserRole, ('peak_group', pk_idx))

        peaks_root.setExpanded(True)

        self.tree.blockSignals(False)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _on_item_changed(self, item, column):
        """Handle checkbox toggle — emit appropriate signals."""
        if column != 0:
            return

        data = item.data(0, Qt.UserRole)
        if data is None:
            return

        checked = item.checkState(0) != Qt.Unchecked

        kind = data[0]
        if kind == 'station':
            _, arr_name, stn_name = data
            self.station_visibility_changed.emit(arr_name, stn_name, checked)
        elif kind == 'array_median':
            _, arr_name = data
            self.array_median_visibility_changed.emit(arr_name, checked)
            # Also toggle all station children
            for i in range(item.childCount()):
                child = item.child(i)
                child_data = child.data(0, Qt.UserRole)
                if child_data and child_data[0] == 'station':
                    child_checked = child.checkState(0) != Qt.Unchecked
                    self.station_visibility_changed.emit(child_data[1], child_data[2], child_checked)
        elif kind == 'grand_median':
            self.grand_median_visibility_changed.emit(checked)
        elif kind == 'std_band':
            self.std_band_visibility_changed.emit(checked)
        elif kind == 'combined_std':
            self.combined_std_visibility_changed.emit(checked)
        elif kind == 'peak_group':
            _, pk_idx = data
            self.peak_group_visibility_changed.emit(pk_idx, checked)

    def _set_all(self, visible: bool):
        self.tree.blockSignals(True)
        state = Qt.Checked if visible else Qt.Unchecked
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            self._recursive_set(top, state)
        self.tree.blockSignals(False)

        # Emit bulk signals
        self.grand_median_visibility_changed.emit(visible)
        self.std_band_visibility_changed.emit(visible)
        for pk_idx in range(3):
            self.peak_group_visibility_changed.emit(pk_idx, visible)

        # Emit station signals
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            self._emit_all_stations(top, visible)

    def _recursive_set(self, item, state):
        item.setCheckState(0, state)
        for i in range(item.childCount()):
            self._recursive_set(item.child(i), state)

    def _emit_all_stations(self, item, visible):
        data = item.data(0, Qt.UserRole)
        if data and data[0] == 'station':
            self.station_visibility_changed.emit(data[1], data[2], visible)
        elif data and data[0] == 'array_median':
            self.array_median_visibility_changed.emit(data[1], visible)
        for i in range(item.childCount()):
            self._emit_all_stations(item.child(i), visible)
