"""
Results Table Widget
=====================

Interactive table showing all station results across arrays with
checkboxes for inclusion/exclusion from output and statistics.
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QCheckBox, QLabel, QMenu, QAction,
    QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QBrush, QFont

import numpy as np
from typing import List, Dict, Any, Optional


# Column indices
COL_CHECK = 0
COL_ARRAY = 1
COL_STATION = 2
COL_VALID = 3
COL_F0 = 4
COL_A0 = 5
COL_F1 = 6
COL_A1 = 7
COL_F2 = 8
COL_A2 = 9
COL_NOTES = 10

HEADERS = [
    "", "Array", "Station", "Valid/Total",
    "F0 (Hz)", "A0", "F1 (Hz)", "A1", "F2 (Hz)", "A2", "Notes"
]

# Row colors
COLOR_NO_PEAKS = QColor(255, 230, 230)      # light red
COLOR_LOW_QC = QColor(255, 255, 210)        # light yellow
COLOR_NORMAL = QColor(255, 255, 255)        # white


class ResultsTableWidget(QWidget):
    """Interactive results table with checkboxes for station inclusion."""

    station_toggled = pyqtSignal(str, str, bool)   # array, station, checked
    selection_changed = pyqtSignal()                # any checkbox changed

    def __init__(self, parent=None):
        super().__init__(parent)
        self._station_results = []
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)

        # Toolbar
        toolbar = QHBoxLayout()

        self.btn_select_all = QPushButton("Select All")
        self.btn_select_all.clicked.connect(lambda: self._set_all_checked(True))
        toolbar.addWidget(self.btn_select_all)

        self.btn_deselect_all = QPushButton("Deselect All")
        self.btn_deselect_all.clicked.connect(lambda: self._set_all_checked(False))
        toolbar.addWidget(self.btn_deselect_all)

        self.chk_only_f0 = QCheckBox("Only stations with F0")
        self.chk_only_f0.stateChanged.connect(self._filter_by_f0)
        toolbar.addWidget(self.chk_only_f0)

        toolbar.addStretch()

        self.btn_export_csv = QPushButton("Export CSV")
        self.btn_export_csv.clicked.connect(self._export_csv)
        toolbar.addWidget(self.btn_export_csv)

        layout.addLayout(toolbar)

        # Table
        self.table = QTableWidget(0, len(HEADERS))
        self.table.setHorizontalHeaderLabels(HEADERS)
        self.table.horizontalHeader().setSectionResizeMode(COL_ARRAY, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(COL_STATION, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(COL_VALID, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(COL_NOTES, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(COL_CHECK, QHeaderView.Fixed)
        self.table.setColumnWidth(COL_CHECK, 30)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSortingEnabled(True)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)

        layout.addWidget(self.table)

        # Status bar
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.status_label)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def populate(self, station_results: list):
        """
        Populate the table from a list of StationResult objects.

        Parameters
        ----------
        station_results : list
            List of StationResult dataclass instances.
        """
        self._station_results = station_results
        self.table.blockSignals(True)
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)

        for sr in station_results:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # Checkbox
            chk_item = QTableWidgetItem()
            chk_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk_item.setCheckState(Qt.Checked)
            self.table.setItem(row, COL_CHECK, chk_item)

            # Array (topic)
            self.table.setItem(row, COL_ARRAY, QTableWidgetItem(str(sr.topic)))

            # Station
            self.table.setItem(row, COL_STATION, QTableWidgetItem(sr.station_name))

            # Valid / Total
            valid_str = f"{sr.valid_windows}/{sr.total_windows}" if sr.total_windows > 0 else "—"
            self.table.setItem(row, COL_VALID, QTableWidgetItem(valid_str))

            # Peaks (up to 3)
            peaks_sorted = sorted(sr.peaks, key=lambda p: p.frequency) if sr.peaks else []
            for i, (fc, ac) in enumerate([(COL_F0, COL_A0), (COL_F1, COL_A1), (COL_F2, COL_A2)]):
                if i < len(peaks_sorted):
                    self.table.setItem(row, fc, QTableWidgetItem(f"{peaks_sorted[i].frequency:.2f}"))
                    self.table.setItem(row, ac, QTableWidgetItem(f"{peaks_sorted[i].amplitude:.2f}"))
                else:
                    self.table.setItem(row, fc, QTableWidgetItem(""))
                    self.table.setItem(row, ac, QTableWidgetItem(""))

            # Notes
            notes = []
            if sr.total_windows > 0 and sr.valid_windows / sr.total_windows < 0.5:
                notes.append("Low QC")
            if not sr.peaks:
                notes.append("No peaks")
            self.table.setItem(row, COL_NOTES, QTableWidgetItem("; ".join(notes)))

            # Row coloring
            self._color_row(row, sr)

        self.table.setSortingEnabled(True)
        self.table.blockSignals(False)

        # Connect cell-changed AFTER population
        try:
            self.table.cellChanged.disconnect(self._on_cell_changed)
        except TypeError:
            pass
        self.table.cellChanged.connect(self._on_cell_changed)

        self._update_status()

    def get_checked_results(self) -> list:
        """Return list of StationResult objects for checked rows."""
        checked = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, COL_CHECK)
            if item and item.checkState() == Qt.Checked:
                array_name = self.table.item(row, COL_ARRAY).text()
                stn_name = self.table.item(row, COL_STATION).text()
                for sr in self._station_results:
                    if sr.topic == array_name and sr.station_name == stn_name:
                        checked.append(sr)
                        break
        return checked

    def get_checked_keys(self) -> list:
        """Return list of (array, station) tuples for checked rows."""
        keys = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, COL_CHECK)
            if item and item.checkState() == Qt.Checked:
                array_name = self.table.item(row, COL_ARRAY).text()
                stn_name = self.table.item(row, COL_STATION).text()
                keys.append((array_name, stn_name))
        return keys

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _color_row(self, row: int, sr):
        """Apply background color to row based on data quality."""
        if not sr.peaks:
            color = COLOR_NO_PEAKS
        elif sr.total_windows > 0 and sr.valid_windows / sr.total_windows < 0.5:
            color = COLOR_LOW_QC
        else:
            color = COLOR_NORMAL

        brush = QBrush(color)
        for col in range(self.table.columnCount()):
            item = self.table.item(row, col)
            if item:
                item.setBackground(brush)

    def _on_cell_changed(self, row, col):
        if col != COL_CHECK:
            return
        item = self.table.item(row, COL_CHECK)
        if item is None:
            return
        checked = item.checkState() == Qt.Checked
        array_name = self.table.item(row, COL_ARRAY).text()
        stn_name = self.table.item(row, COL_STATION).text()
        self.station_toggled.emit(array_name, stn_name, checked)
        self.selection_changed.emit()
        self._update_status()

    def _set_all_checked(self, checked: bool):
        self.table.blockSignals(True)
        state = Qt.Checked if checked else Qt.Unchecked
        for row in range(self.table.rowCount()):
            item = self.table.item(row, COL_CHECK)
            if item:
                item.setCheckState(state)
        self.table.blockSignals(False)
        self.selection_changed.emit()
        self._update_status()

    def _filter_by_f0(self, state):
        """If checked, deselect stations without F0."""
        if state != Qt.Checked:
            return
        self.table.blockSignals(True)
        for row in range(self.table.rowCount()):
            f0_item = self.table.item(row, COL_F0)
            has_f0 = f0_item is not None and f0_item.text().strip() != ""
            chk = self.table.item(row, COL_CHECK)
            if chk and not has_f0:
                chk.setCheckState(Qt.Unchecked)
        self.table.blockSignals(False)
        self.selection_changed.emit()
        self._update_status()

    def _update_status(self):
        total = self.table.rowCount()
        checked = sum(
            1 for r in range(total)
            if self.table.item(r, COL_CHECK) and self.table.item(r, COL_CHECK).checkState() == Qt.Checked
        )
        self.status_label.setText(f"{checked}/{total} stations selected")

    def _show_context_menu(self, pos):
        menu = QMenu(self)
        rows = set(idx.row() for idx in self.table.selectedIndexes())
        if not rows:
            return

        # Get array name(s) of selected rows
        arrays = set()
        for r in rows:
            arr_item = self.table.item(r, COL_ARRAY)
            if arr_item:
                arrays.add(arr_item.text())

        act_check = QAction("Check Selected", self)
        act_check.triggered.connect(lambda: self._set_rows_checked(rows, True))
        menu.addAction(act_check)

        act_uncheck = QAction("Uncheck Selected", self)
        act_uncheck.triggered.connect(lambda: self._set_rows_checked(rows, False))
        menu.addAction(act_uncheck)

        if len(arrays) == 1:
            arr_name = list(arrays)[0]
            menu.addSeparator()
            act_sel_arr = QAction(f"Select All in '{arr_name}'", self)
            act_sel_arr.triggered.connect(lambda: self._set_array_checked(arr_name, True))
            menu.addAction(act_sel_arr)

            act_desel_arr = QAction(f"Deselect All in '{arr_name}'", self)
            act_desel_arr.triggered.connect(lambda: self._set_array_checked(arr_name, False))
            menu.addAction(act_desel_arr)

        menu.exec_(self.table.viewport().mapToGlobal(pos))

    def _set_rows_checked(self, rows, checked):
        self.table.blockSignals(True)
        state = Qt.Checked if checked else Qt.Unchecked
        for r in rows:
            item = self.table.item(r, COL_CHECK)
            if item:
                item.setCheckState(state)
        self.table.blockSignals(False)
        self.selection_changed.emit()
        self._update_status()

    def _set_array_checked(self, array_name, checked):
        self.table.blockSignals(True)
        state = Qt.Checked if checked else Qt.Unchecked
        for row in range(self.table.rowCount()):
            arr_item = self.table.item(row, COL_ARRAY)
            if arr_item and arr_item.text() == array_name:
                chk = self.table.item(row, COL_CHECK)
                if chk:
                    chk.setCheckState(state)
        self.table.blockSignals(False)
        self.selection_changed.emit()
        self._update_status()

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Results Table", "results_table.csv", "CSV (*.csv)"
        )
        if not path:
            return
        try:
            import csv
            with open(path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Included"] + HEADERS[1:])
                for row in range(self.table.rowCount()):
                    chk = self.table.item(row, COL_CHECK)
                    included = "Yes" if chk and chk.checkState() == Qt.Checked else "No"
                    cols = [included]
                    for c in range(1, self.table.columnCount()):
                        item = self.table.item(row, c)
                        cols.append(item.text() if item else "")
                    writer.writerow(cols)
            QMessageBox.information(self, "Export", f"Table exported to:\n{path}")
        except Exception as e:
            QMessageBox.warning(self, "Export Error", str(e))
