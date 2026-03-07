"""
Window Layers Panel
====================

Professional layer management panel for HVSR window visibility.
Ported from hvsr_pro's WindowLayersDock (gui/docks/layers/layers_dock.py)
as a standalone QWidget suitable for embedding in any layout.

Features:
- Scrollable list of all windows with checkboxes
- Color icons matching plot line colors
- Quality scores displayed
- [REJ] suffix for rejected windows (grayed out)
- Batch operations: All On, All Off, Invert
- Real-time mean recalculation on toggle
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QListView, QPushButton, QLabel,
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import (
    QStandardItemModel, QStandardItem, QIcon,
    QPixmap, QPainter, QColor,
)

from matplotlib import colors as mcolors


class WindowLayersPanel(QWidget):
    """
    Panel widget for managing HVSR window layer visibility.

    Signals
    -------
    visibility_changed(int, bool)
        Emitted when a window's visibility changes.
        Args: (window_index, is_visible)
    """

    visibility_changed = pyqtSignal(int, bool)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Data references (set via set_data)
        self._window_lines = {}   # {window_index: matplotlib Line2D}
        self._stat_lines = {}     # {'mean': Line2D, 'std_plus': Line2D, ...}
        self._rejected_mask = []  # bool list aligned with window indices
        self._fig = None          # matplotlib Figure for redraw

        self._build_ui()

    # ------------------------------------------------------------------
    #  UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # Header label
        header = QLabel("Window Layers")
        header.setStyleSheet("font-weight: bold; font-size: 11px;")
        layout.addWidget(header)

        # Batch buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)

        self.btn_all_on = QPushButton("All On")
        self.btn_all_on.setToolTip("Show all windows")
        self.btn_all_on.clicked.connect(lambda: self._set_all(True))

        self.btn_all_off = QPushButton("All Off")
        self.btn_all_off.setToolTip("Hide all windows")
        self.btn_all_off.clicked.connect(lambda: self._set_all(False))

        self.btn_invert = QPushButton("Invert")
        self.btn_invert.setToolTip("Invert visibility selection")
        self.btn_invert.clicked.connect(self._invert_selection)

        for btn in (self.btn_all_on, self.btn_all_off, self.btn_invert):
            btn.setFixedHeight(24)
            btn_layout.addWidget(btn)

        layout.addLayout(btn_layout)

        # Scrollable list view with item model
        self.view = QListView()
        self.model = QStandardItemModel()
        self.view.setModel(self.model)
        self.view.setEditTriggers(QListView.NoEditTriggers)
        self.model.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self.view)

    # ------------------------------------------------------------------
    #  Public API
    # ------------------------------------------------------------------

    def set_data(self, window_lines, rejected_mask, stat_lines=None,
                 fig=None, quality_scores=None):
        """
        Populate the panel with window data.

        Parameters
        ----------
        window_lines : dict
            {window_index: matplotlib Line2D} for each window curve.
        rejected_mask : list[bool]
            True if window at that index was rejected by QC.
        stat_lines : dict, optional
            {'mean': Line2D, 'std_plus': Line2D, 'std_minus': Line2D}.
        fig : matplotlib.figure.Figure, optional
            Figure reference for canvas redraw.
        quality_scores : list[float], optional
            Overall quality score per window.
        """
        self._window_lines = window_lines or {}
        self._rejected_mask = rejected_mask or []
        self._stat_lines = stat_lines or {}
        self._fig = fig

        self._rebuild(quality_scores)

    def get_visible_indices(self):
        """Return list of window indices currently checked (visible)."""
        visible = []
        for row in range(self.model.rowCount()):
            item = self.model.item(row)
            if item is None:
                continue
            data = item.data(Qt.UserRole)
            if isinstance(data, int) and item.checkState() == Qt.Checked:
                visible.append(data)
        return visible

    # ------------------------------------------------------------------
    #  Internal — rebuild list
    # ------------------------------------------------------------------

    def _rebuild(self, quality_scores=None):
        self.model.blockSignals(True)
        self.model.clear()

        sorted_indices = sorted(self._window_lines.keys())

        for idx in sorted_indices:
            line = self._window_lines[idx]
            is_rejected = (idx < len(self._rejected_mask)
                           and self._rejected_mask[idx])

            # Build label
            q_str = ""
            if quality_scores and idx < len(quality_scores):
                q_str = f" (Q={quality_scores[idx]:.2f})"
            label = f"Window {idx + 1}{q_str}"
            if is_rejected:
                label += " [REJ]"

            # Icon from line color
            icon = self._make_icon(line)

            item = QStandardItem(icon, label)
            item.setCheckable(True)

            # Rejected windows start hidden; active start visible
            initial_visible = not is_rejected
            item.setCheckState(
                Qt.Checked if initial_visible else Qt.Unchecked
            )
            item.setData(idx, Qt.UserRole)

            if is_rejected:
                item.setForeground(QColor(150, 150, 150))

            self.model.appendRow(item)

        # Separator + stat lines
        if self._stat_lines:
            sep = QStandardItem("\u2500" * 20)
            sep.setEnabled(False)
            self.model.appendRow(sep)

            entries = [
                ("Median H/V", "median", "#CC0000", True),
                ("Mean H/V",   "mean",   "#000080", False),
                ("+1\u03c3",   "std_plus",  "black", True),
                ("-1\u03c3",   "std_minus", "black", True),
            ]
            for label, key, color, default_on in entries:
                if key in self._stat_lines:
                    icon = self._make_icon(color, icon_type="line")
                    item = QStandardItem(icon, label)
                    item.setCheckable(True)
                    item.setCheckState(
                        Qt.Checked if default_on else Qt.Unchecked
                    )
                    item.setData(key, Qt.UserRole)
                    self.model.appendRow(item)

        self.model.blockSignals(False)

    # ------------------------------------------------------------------
    #  Internal — icon helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _make_icon(color_or_line, icon_type="circle"):
        if hasattr(color_or_line, "get_color"):
            color = color_or_line.get_color() or "black"
        else:
            color = color_or_line

        r, g, b, _ = mcolors.to_rgba(color)
        qc = QColor(int(r * 255), int(g * 255), int(b * 255))

        pixmap = QPixmap(16, 16)
        pixmap.fill(QColor(0, 0, 0, 0))

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        if icon_type == "circle":
            painter.setBrush(qc)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(2, 2, 12, 12)
        else:
            painter.setPen(qc)
            painter.drawLine(2, 8, 14, 8)

        painter.end()
        return QIcon(pixmap)

    # ------------------------------------------------------------------
    #  Internal — signal handlers
    # ------------------------------------------------------------------

    def _on_item_changed(self, item):
        role_data = item.data(Qt.UserRole)
        is_checked = (item.checkState() == Qt.Checked)

        # Stat line toggle
        if isinstance(role_data, str):
            self._toggle_stat_line(role_data, is_checked)
            return

        # Window toggle
        if not isinstance(role_data, int):
            return

        window_idx = role_data
        if window_idx in self._window_lines:
            self._window_lines[window_idx].set_visible(is_checked)

        self.visibility_changed.emit(window_idx, is_checked)
        self._redraw()

    def _toggle_stat_line(self, stat_id, visible):
        if stat_id in self._stat_lines:
            self._stat_lines[stat_id].set_visible(visible)
            self._redraw()

    # ------------------------------------------------------------------
    #  Internal — batch operations
    # ------------------------------------------------------------------

    def _set_all(self, visible):
        self.model.blockSignals(True)
        state = Qt.Checked if visible else Qt.Unchecked

        for row in range(self.model.rowCount()):
            item = self.model.item(row)
            if item and item.isCheckable():
                item.setCheckState(state)

        self.model.blockSignals(False)

        # Apply to matplotlib lines
        for idx, line in self._window_lines.items():
            line.set_visible(visible)
            self.visibility_changed.emit(idx, visible)

        for line in self._stat_lines.values():
            line.set_visible(visible)

        self._redraw()

    def _invert_selection(self):
        self.model.blockSignals(True)

        for row in range(self.model.rowCount()):
            item = self.model.item(row)
            if item and item.isCheckable():
                new_state = (Qt.Unchecked if item.checkState() == Qt.Checked
                             else Qt.Checked)
                item.setCheckState(new_state)

        self.model.blockSignals(False)

        # Apply to matplotlib lines
        for row in range(self.model.rowCount()):
            item = self.model.item(row)
            if item is None:
                continue
            data = item.data(Qt.UserRole)
            is_checked = (item.checkState() == Qt.Checked)

            if isinstance(data, int) and data in self._window_lines:
                self._window_lines[data].set_visible(is_checked)
                self.visibility_changed.emit(data, is_checked)
            elif isinstance(data, str) and data in self._stat_lines:
                self._stat_lines[data].set_visible(is_checked)

        self._redraw()

    # ------------------------------------------------------------------
    #  Internal — canvas redraw
    # ------------------------------------------------------------------

    def _redraw(self):
        if self._fig is not None:
            self._fig.canvas.draw_idle()
