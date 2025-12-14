"""
NewTab4_HVSRPicker – rev‑4 (thread‑safe)
========================================
* Complete rewrite (~230 LOC) that **keeps the main GUI responsive** by running
  `hvsr_making_peak.py` inside a `QThread` (no more "Not Responding").
* All earlier features retained:
  * dynamic figure title via `HV_TITLE`
  * editable peak‑label font size via `HV_PFONT`
  * every knob of `hvsr_making_peak.py` exposed in the form.
* Log streaming is done with Qt signals instead of direct loop → thread‑safe.
* Code volume similar to the original (~210 lines).
"""
from __future__ import annotations

import os, sys, shlex, subprocess
from pathlib import Path
from typing import Optional, Dict, Any

import pandas as pd
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget, QSplitter, QListWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFileDialog, QLineEdit, QGroupBox, QFormLayout, QSpinBox,
    QComboBox, QTextEdit, QMessageBox, QCheckBox, QSizePolicy
)
from PyQt5.QtWidgets import QDoubleSpinBox

__all__ = ["NewTab4_HVSRPicker"]

# ──────────────────────────────────────────────────────────── worker thread ─
class PeakWorker(QThread):
    log_line  = pyqtSignal(str)
    finished  = pyqtSignal(int)

    def __init__(self, env: Dict[str, str], parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._env = env

    def run(self):
        cmd = [sys.executable, "hvsr_making_peak.py"]
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, env=self._env)
        except FileNotFoundError as exc:
            self.log_line.emit(f"Error: {exc}\n"); self.finished.emit(-1); return

        assert proc.stdout is not None
        for line in proc.stdout:
            self.log_line.emit(line.rstrip())
        proc.wait()
        self.finished.emit(proc.returncode)

# ────────────────────────────────────────────────────────────────────────────
class NewTab4_HVSRPicker(QWidget):
    """HVSR peak‑picking tab (Thread‑safe version)."""

    # ..................................................................... UI
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._df: Optional[pd.DataFrame] = None
        self._worker: Optional[PeakWorker] = None

        splitter = QSplitter(Qt.Horizontal, self)
        splitter.setChildrenCollapsible(False)

        # ── left: figure list ────────────────────────────────────────────
        self.list_fig = QListWidget(maximumWidth=210)
        self.list_fig.itemSelectionChanged.connect(self._on_fig_pick)
        splitter.addWidget(self.list_fig)

        # ── right: controls + log ────────────────────────────────────────
        right = QWidget(); splitter.addWidget(right)
        rlay  = QVBoxLayout(right)

        rlay.addWidget(self._build_paths_group())
        rlay.addWidget(self._build_settings_group())

        # run button
        btn_run = QPushButton("Compute Peaks", clicked=self._on_run)
        btn_run.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        rlay.addWidget(btn_run, alignment=Qt.AlignRight)

        # log pane
        self.log = QTextEdit(readOnly=True)
        rlay.addWidget(self.log, 1)

        # ── top‑level layout ─────────────────────────────────────────────
        top = QVBoxLayout(self); top.addWidget(splitter)

    # ................................................ build sub‑widgets ...
    def _build_paths_group(self) -> QGroupBox:
        gb = QGroupBox("Project Paths")
        form = QFormLayout(gb)
        self.le_csv, self.le_mat, self.le_out = (QLineEdit() for _ in range(3))
        for le in (self.le_csv, self.le_mat, self.le_out): le.setMinimumWidth(420)
        form.addRow("Windows CSV:", self._row(self.le_csv, QPushButton("…", clicked=self._pick_csv)))
        form.addRow("MAT folder:",   self._row(self.le_mat, QPushButton("…", clicked=lambda: self._pick_dir(self.le_mat))))
        form.addRow("Output base:",  self._row(self.le_out, QPushButton("…", clicked=lambda: self._pick_dir(self.le_out))))
        return gb

    def _build_settings_group(self) -> QGroupBox:
        gb = QGroupBox("Processing Settings")
        form = QFormLayout(gb)
        self.sb_tw   = self._spin(form, "Time‑window [s]",       120, 10, 600)
        self.sb_ko   = self._spin(form, "KO bandwidth",          40,  10, 120)
        self.sb_fmin = QDoubleSpinBox()
        self.sb_fmin.setRange(0.01, 5.00)  # 10 mHz → 5 Hz
        self.sb_fmin.setDecimals(2)
        self.sb_fmin.setSingleStep(0.05)
        self.sb_fmin.setValue(0.20)  # default 0.20 Hz
        form.addRow("Freq min [Hz]", self.sb_fmin)
        self.sb_lgf  = self._spin(form, "Legend font pt",         8,   5,  20)
        self.sb_pfs  = self._spin(form, "Peak‑label font pt",    10,   6,  30)
        self.sb_np   = self._spin(form, "# Peaks",                2,   1,   5)
        self.cmb_avg = QComboBox(); self.cmb_avg.addItems(["geo","quad","energy","N","E"])
        form.addRow("Averaging", self.cmb_avg)
        self.sb_skip = self._spin(form, "Start‑skip [min]",      0,  0, 120)
        self.sb_proc = self._spin(form, "Process\u202flen [min]",     20,  1, 240)
        self.cb_save = QCheckBox("Save\u00a0PNG", checked=True); form.addRow(self.cb_save)
        # New checkbox – allow saving PDF alongside PNG
        self.cb_save_pdf = QCheckBox("Save\u00a0PDF", checked=False)
        form.addRow(self.cb_save_pdf)

        return gb

    # ................................................ utility builders ...
    @staticmethod
    def _row(*wids):
        w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(0,0,0,0)
        for wid in wids: h.addWidget(wid)
        return w

    @staticmethod
    def _spin(f, label, val, lo, hi):
        sb = QSpinBox(); sb.setRange(lo, hi); sb.setValue(val); f.addRow(label, sb); return sb

    # ................................................ directory pickers ...
    def _pick_dir(self, line: QLineEdit):
        p = QFileDialog.getExistingDirectory(self, "Select folder");
        if p: line.setText(p)

    # ................................................ CSV handling ........
    def _pick_csv(self):
        p, _ = QFileDialog.getOpenFileName(self, "Windows CSV", filter="CSV (*.csv)")
        if not p: return
        self.le_csv.setText(p)
        try:
            self._df = pd.read_csv(p)
        except Exception as e:
            QMessageBox.critical(self, "CSV error", str(e)); return
        if self._df.empty:
            QMessageBox.warning(self, "CSV", "CSV appears empty"); return
        self.list_fig.clear(); col0 = self._df.columns[0]
        for fig in self._df[col0].astype(str):
            self.list_fig.addItem(fig)
        base = Path(p).parent
        if not self.le_mat.text(): self.le_mat.setText(str(base))
        if not self.le_out.text(): self.le_out.setText(str(base/"peaks"))
        self.log.append(f"Loaded {len(self._df)} rows from CSV.")

    def _on_fig_pick(self):
        if self._df is None or not self.list_fig.currentItem(): return
        fig = self.list_fig.currentItem().text(); row = self._df[self._df.iloc[:,0].astype(str)==fig]
        if row.empty: return
        fs = row.iloc[0].get("Fs_Hz", "?")
        self.log.append(f"→ {fig}: Fs = {fs} Hz")

    # ................................................ run button ..........
    def _on_run(self):
        if self._df is None:
            QMessageBox.warning(self, "CSV", "Load the Windows CSV first"); return
        if not self.list_fig.currentItem():
            QMessageBox.warning(self, "Figure", "Select a Figure"); return

        fig = self.list_fig.currentItem().text(); row = self._df[self._df.iloc[:,0].astype(str)==fig]
        if row.empty: QMessageBox.critical(self, "CSV", "Row not found"); return
        fs = row.iloc[0].get("Fs_Hz");
        if pd.isna(fs): QMessageBox.critical(self, "CSV", "Run Fs‑check first"); return

        mat_dir = Path(self.le_mat.text()); mat = mat_dir/f"ArrayData_{fig}.mat"
        if not mat.is_file(): QMessageBox.critical(self, "MAT", f"{mat} missing"); return
        out_dir = Path(self.le_out.text() or mat_dir)/fig; out_dir.mkdir(parents=True, exist_ok=True)

        # env: Dict[str,str] = os.environ.copy(); env.update({
        #     "HV_ARRAY":str(mat), "HV_OUTDIR":str(out_dir), "HV_FIG":fig, "HV_TITLE":fig,
        #     "HV_FS":str(fs), "HV_TW":str(self.sb_tw.value()), "HV_KO":str(self.sb_ko.value()),
        #     "HV_FMIN" : str(self.sb_fmin.value()),
        #     "HV_LGFONT":str(self.sb_lgf.value()), "HV_PFONT":str(self.sb_pfs.value()),
        #     "HV_NUMPK":str(self.sb_np.value()), "HV_AVG":self.cmb_avg.currentText(),
        #     "HV_SKIP":str(self.sb_skip.value()), "HV_PROC":str(self.sb_proc.value()),
        #     "HV_SAVE":"1" if self.cb_save.isChecked() else "0",
        # })
        env: Dict[str, str] = os.environ.copy();
        env.update({
            "HV_ARRAY": str(mat),
            "HV_OUTDIR": str(out_dir),
            "HV_FIG": fig,
            "HV_TITLE": fig,

            "HV_FS": str(fs),
            "HV_TW": str(self.sb_tw.value()),
            "HV_KO": str(self.sb_ko.value()),
            "HV_FMIN": str(self.sb_fmin.value()),  # if you added F-min
            "HV_PROC": str(self.sb_proc.value()),  # ← **NEW / ensure present**
            "HV_SKIP": str(self.sb_skip.value()),

            "HV_LGFONT": str(self.sb_lgf.value()),
            "HV_PFONT": str(self.sb_pfs.value()),
            "HV_NUMPK": str(self.sb_np.value()),
            "HV_AVG": self.cmb_avg.currentText(),
            "HV_SAVE": "1" if self.cb_save.isChecked() else "0",
            "HV_PDF": "1" if self.cb_save_pdf.isChecked() else "0",
        })

        # detach previous worker if still running
        if self._worker and self._worker.isRunning():
            QMessageBox.warning(self, "Busy", "Wait for the current run to finish"); return

        self._worker = PeakWorker(env, self)
        self._worker.log_line.connect(self._append_log)
        self._worker.finished.connect(self._run_finished)
        self.log.append(f"$ python hvsr_making_peak.py  (Figure {fig})\n")
        self._worker.start()

    # ................................................ slots ...............
    def _append_log(self, txt: str):
        self.log.append(txt); self.log.ensureCursorVisible()

    def _run_finished(self, code: int):
        self.log.append(f"— finished (exit {code})\n")
