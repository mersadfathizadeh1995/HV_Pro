from __future__ import annotations

"""NewTab2_FsCheck.py

Tab 2 – Load the windows CSV, select a MiniSEED directory and one sample
file to infer the filename prefix and the nominal sampling rate (Fs).
Auto-fill the `Fs_Hz` column, but keep cells editable so the user can
manually override values for the next tab.
"""

import csv
import re
from pathlib import Path
from typing import List, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
    QTableWidget, QTableWidgetItem, QMessageBox, QHeaderView, QLabel, QLineEdit,
)

from rdmseed_py import rdmseed

_COLS = [
    "Figure",  # first column from Tab1
    "S_Year", "S_Month", "S_Day", "S_Hour", "S_Min", "S_Sec",
    "E_Year", "E_Month", "E_Day", "E_Hour", "E_Min", "E_Sec",
    "Fs_Hz",  # added by this tab
]

class NewTab2_FsCheck(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setLayout(QVBoxLayout())

        # ---------------- Table --------------------------------------
        self.table = QTableWidget(0, len(_COLS))
        self.table.setHorizontalHeaderLabels(_COLS)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.layout().addWidget(self.table)

        # ---------------- Top controls row ---------------------------
        row = QHBoxLayout(); self.layout().addLayout(row)
        btn_load_csv  = QPushButton("Open Windows CSV")
        btn_save_csv  = QPushButton("Save CSV")
        row.addWidget(btn_load_csv); row.addWidget(btn_save_csv)
        row.addStretch(1)

        # Data directory + sample file to infer prefix and Fs
        self.le_dir = QLineEdit(); self.le_dir.setPlaceholderText("MiniSEED directory…")
        btn_dir = QPushButton("Dir…", clicked=self._pick_dir)
        self.le_sample = QLineEdit(); self.le_sample.setPlaceholderText("Sample MiniSEED file…")
        btn_sample = QPushButton("Sample…", clicked=self._pick_sample)
        self.lbl_prefix = QLabel("Prefix: —")
        self.lbl_auto_fs = QLabel("Auto Fs: —")
        row.addWidget(self.le_dir); row.addWidget(btn_dir)
        row.addWidget(self.le_sample); row.addWidget(btn_sample)
        row.addWidget(self.lbl_prefix); row.addWidget(self.lbl_auto_fs)
        row.addStretch(1)

        btn_compute = QPushButton("Auto‑fill Fs")
        row.addWidget(btn_compute)

        # Store paths / state
        self.data_dir: Optional[Path] = None
        self.sample_file: Optional[Path] = None
        self.prefix: Optional[str] = None
        self.sample_fs: Optional[float] = None
        self.current_csv: Optional[Path] = None

        # callbacks
        btn_load_csv.clicked.connect(self._open_csv)
        btn_save_csv.clicked.connect(self._save_csv)
        btn_compute.clicked.connect(self._compute_fs)

    # ------------------------------------------------------------------
    def _pick_dir(self):
        p = QFileDialog.getExistingDirectory(self, "Select MiniSEED directory")
        if not p:
            return
        self.data_dir = Path(p)
        self.le_dir.setText(str(self.data_dir))
        # If sample not set, propose from this dir
        if not self.sample_file:
            self.le_sample.setText("")
        self._update_prefix_and_fs_labels()

    def _pick_sample(self):
        start_dir = str(self.data_dir) if self.data_dir else ""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select a sample MiniSEED file",
            start_dir,
            "MiniSEED (*.mseed *.miniseed *.msd);;All (*.*)",
        )
        if not path:
            return
        self.sample_file = Path(path)
        self.le_sample.setText(str(self.sample_file))
        if not self.data_dir:
            self.data_dir = self.sample_file.parent
            self.le_dir.setText(str(self.data_dir))
        self._infer_prefix_from_sample()
        self._infer_fs_from_sample()
        self._update_prefix_and_fs_labels()

    # ------------------------------------------------------------------ CSV IO
    def _open_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open CSV", "", "CSV (*.csv)")
        if not path:
            return
        try:
            with open(path, newline="") as f:
                rows = list(csv.reader(f))
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Cannot read CSV:\n{exc}")
            return
        header = rows[0]
        start = 1 if header[0].strip().lower() == "figure" else 0
        self.table.setRowCount(0)
        for r in rows[start:]:
            self.table.insertRow(self.table.rowCount())
            r = r + [""]*(len(_COLS)-len(r))  # pad
            for c,val in enumerate(r):
                self.table.setItem(self.table.rowCount()-1,c,QTableWidgetItem(val))
        self.current_csv = Path(path)

    def _save_csv(self):
        if self.table.rowCount()==0:
            QMessageBox.warning(self,"Empty","No data to save.")
            return
        path, _ = QFileDialog.getSaveFileName(self,"Save CSV", str(self.current_csv or "windows_withFs.csv"),"CSV (*.csv)")
        if not path:
            return
        try:
            with open(path,"w",newline="") as f:
                writer=csv.writer(f); writer.writerow(_COLS)
                for r in range(self.table.rowCount()):
                    writer.writerow([self._cell(r,c) for c in range(len(_COLS))])
            QMessageBox.information(self,"Saved", path)
        except Exception as exc:
            QMessageBox.critical(self,"Error", str(exc))

    # ------------------------------------------------------------------ Fs check
    def _compute_fs(self):
        if not self.sample_file:
            QMessageBox.warning(self, "Sample file", "Select a sample MiniSEED file first.")
            return
        # Ensure we have an auto Fs from the sample
        try:
            self._infer_fs_from_sample()
        except Exception as exc:
            QMessageBox.critical(self, "Read error", str(exc)); return

        if self.sample_fs is None:
            QMessageBox.warning(self, "Fs", "Could not infer Fs from sample file.")
            return

        # Fill the Fs_Hz column for all rows; keep cells editable
        for row in range(self.table.rowCount()):
            self.table.setItem(row, _COLS.index("Fs_Hz"), QTableWidgetItem(str(self.sample_fs)))

        QMessageBox.information(self, "Done", f"Fs column set to {self.sample_fs:g} Hz for all rows. You can edit cells manually if needed.")

    # ------------------------------------------------------------------ helpers
    def _cell(self,row:int,col:int)->str:
        it = self.table.item(row,col)
        return it.text().strip() if it else ""

    # ------------------------------------------------------------------ helpers (new)
    def _infer_prefix_from_sample(self):
        if not self.sample_file:
            return
        m = re.match(r"(.+?)_\d{8}_\d{6}$", self.sample_file.stem)
        if m:
            self.prefix = m.group(1) + "_"
        else:
            self.prefix = None

    def _infer_fs_from_sample(self):
        if not self.sample_file:
            return
        try:
            XX, _ = rdmseed(str(self.sample_file))
            if not XX:
                raise RuntimeError("No data blocks in sample file")
            # Take the first blockʼs SampleRate as nominal Fs
            self.sample_fs = float(XX[0].SampleRate)
        except Exception as exc:
            self.sample_fs = None
            raise

    def _update_prefix_and_fs_labels(self):
        self.lbl_prefix.setText(f"Prefix: {self.prefix or '—'}")
        self.lbl_auto_fs.setText(f"Auto Fs: {self.sample_fs:g} Hz" if self.sample_fs else "Auto Fs: —")