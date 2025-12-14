from __future__ import annotations

"""NewTab1_Windows.py

Tab 1 of the new workflow: create / edit a time-window table.
The user can:
  • add empty rows or delete selected rows
  • import an existing CSV (with or without header)
  • save the table to CSV – figure name is the first column
Columns:
  Figure, S_Year, S_Month, S_Day, S_Hour, S_Min, S_Sec,
          E_Year, E_Month, E_Day, E_Hour, E_Min, E_Sec
"""

import csv
from pathlib import Path
from typing import List
from datetime import datetime, timedelta

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
    QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView, QComboBox,
)

_COLS: List[str] = [
    "Figure",  # HV1 …
    "S_Year", "S_Month", "S_Day", "S_Hour", "S_Min", "S_Sec",
    "E_Year", "E_Month", "E_Day", "E_Hour", "E_Min", "E_Sec",
]

class NewTab1_Windows(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setLayout(QVBoxLayout())

        # Table --------------------------------------------------------
        self.table = QTableWidget(0, len(_COLS))
        self.table.setHorizontalHeaderLabels(_COLS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.layout().addWidget(self.table)

        # Button / options bar ----------------------------------------
        btn_bar = QHBoxLayout()
        self.layout().addLayout(btn_bar)

        btn_add    = QPushButton("Add Row")
        btn_del    = QPushButton("Delete Row")
        btn_import = QPushButton("Import CSV")
        btn_save   = QPushButton("Save CSV")

        btn_bar.addWidget(btn_add)
        btn_bar.addWidget(btn_del)

        # timezone selection
        btn_bar.addStretch(1)
        # label-like spacer for TZ
        tz_label = QPushButton("TZ:")
        tz_label.setEnabled(False)
        tz_label.setFlat(True)
        tz_label.setStyleSheet("QPushButton{border:none; color:gray;}")
        btn_bar.addWidget(tz_label)
        self.tz_combo = QComboBox()
        self.tz_combo.addItems(["CST (UTC-6)", "CDT (UTC-5)", "GMT+0 (No correction)"])
        btn_bar.addWidget(self.tz_combo)

        btn_bar.addWidget(btn_import)
        btn_bar.addWidget(btn_save)

        btn_add.clicked.connect(self._add_row)
        btn_del.clicked.connect(self._del_row)
        btn_import.clicked.connect(self._import_csv)
        btn_save.clicked.connect(self._save_csv)

    # ------------------------------------------------------------------
    # Button callbacks
    # ------------------------------------------------------------------
    def _add_row(self):
        self.table.insertRow(self.table.rowCount())

    def _del_row(self):
        rows = {idx.row() for idx in self.table.selectedIndexes()}
        for r in sorted(rows, reverse=True):
            self.table.removeRow(r)

    def _import_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open CSV", "", "CSV files (*.csv)")
        if not path:
            return
        try:
            with open(path, newline="") as f:
                reader = csv.reader(f)
                rows = list(reader)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not read CSV:\n{e}")
            return

        # clear table
        self.table.setRowCount(0)
        header = rows[0]
        start_row = 1 if header[0].strip().lower() == "figure" else 0
        for row in rows[start_row:]:
            self._add_row()
            for c, val in enumerate(row[:len(_COLS)]):
                self.table.setItem(self.table.rowCount()-1, c, QTableWidgetItem(val))

    def _save_csv(self):
        if self.table.rowCount() == 0:
            QMessageBox.warning(self, "Nothing to save", "The table is empty.")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save CSV", "windows.csv", "CSV files (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(_COLS)
                for r in range(self.table.rowCount()):
                    local_vals = [self._cell(r, c) for c in range(len(_COLS))]
                    try:
                        gmt_vals = self._to_gmt(local_vals)
                    except Exception as exc:
                        QMessageBox.warning(
                            self, "Skip row",
                            f"Row {r+1} has invalid date/time: {exc} – skipped")
                        continue
                    writer.writerow(gmt_vals)
            QMessageBox.information(self, "Saved", f"CSV written to\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not write CSV:\n{e}")

    # ------------------------------------------------------------------
    def _cell(self, row: int, col: int) -> str:
        item = self.table.item(row, col)
        return item.text().strip() if item else ""

    def _to_gmt(self, row: List[str]) -> List[str]:
        """Convert start/end components in *row* (list of str) to GMT using tz offset."""
        if len(row) != len(_COLS):
            raise ValueError("wrong column count")
        # CST = UTC-6 (add 6h), CDT = UTC-5 (add 5h), GMT+0 = no offset
        tz_idx = self.tz_combo.currentIndex()
        if tz_idx == 0:
            offset = 6  # CST
        elif tz_idx == 1:
            offset = 5  # CDT
        else:
            offset = 0  # GMT+0 (no correction needed)

        def conv(prefix: str) -> List[str]:
            idx = _COLS.index(f"{prefix}_Year")
            y, m, d, h, mi, s = map(int, row[idx:idx+6])
            dt = datetime(y, m, d, h, mi, s) + timedelta(hours=offset)
            return [str(dt.year), str(dt.month), str(dt.day), str(dt.hour), str(dt.minute), str(dt.second)]

        out = [row[0]]  # Figure stays
        out += conv("S")
        out += conv("E")
        return out 