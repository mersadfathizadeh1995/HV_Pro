from __future__ import annotations
"""NewTab3_Reduce.py
Tab 3 – Loop over the windows CSV (with Fs_Hz column) and generate
ArrayData_<Figure>.mat files using miniseed_array_reduction.process_station
(one window at a time).

Enhancements:
- Pick a MiniSEED directory and one sample file to infer the filename prefix.
- Display auto-detected Fs from the sample; allow manual override.
- Reduction uses manual Fs if provided; otherwise uses CSV Fs_Hz if present;
  otherwise falls back to auto Fs.
"""

import csv
import shutil
import re
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
    QLabel, QLineEdit, QTextEdit, QMessageBox,
)

from miniseed_array_reduction import process_station

class NewTab3_Reduce(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setLayout(QVBoxLayout())

        # file pickers --------------------------------------------------
        form = QVBoxLayout(); self.layout().addLayout(form)

        def _row(label:str):
            hl = QHBoxLayout(); hl.addWidget(QLabel(label));
            le = QLineEdit(); hl.addWidget(le); btn = QPushButton("…"); hl.addWidget(btn)
            form.addLayout(hl); return le,btn

        self.le_csv,   btn_csv   = _row("Windows CSV:")
        self.le_out,   btn_out   = _row("Output folder:")

        # MiniSEED directory and sample file to infer prefix and Fs
        self.le_dir, btn_dir = _row("MiniSEED directory:")
        btn_dir.clicked.connect(lambda: self._browse(self.le_dir, dir=True))
        self.le_sample, btn_sample = _row("Sample MiniSEED file:")
        btn_sample.clicked.connect(self._pick_sample)

        # Show inferred prefix and Fs with manual override
        hlf = QHBoxLayout(); form.addLayout(hlf)
        self.lbl_prefix = QLabel("Prefix: —"); hlf.addWidget(self.lbl_prefix)
        hlf.addStretch(1)
        hlf.addWidget(QLabel("Auto Fs:"))
        self.le_auto_fs = QLineEdit(); self.le_auto_fs.setReadOnly(True); self.le_auto_fs.setFixedWidth(80)
        hlf.addWidget(self.le_auto_fs)
        hlf.addWidget(QLabel("Manual Fs:"))
        self.le_manual_fs = QLineEdit(); self.le_manual_fs.setPlaceholderText("leave blank to use auto"); self.le_manual_fs.setFixedWidth(120)
        hlf.addWidget(self.le_manual_fs)

        self.le_id,    _         = _row("Station ID:")
        self.le_id.setText("1")
        self.data_dir: Optional[Path] = None
        self.sample_file: Optional[Path] = None
        self.inferred_prefix: Optional[str] = None
        self.auto_fs: Optional[float] = None

        btn_csv.clicked.connect(lambda: self._browse(self.le_csv, file=True))
        btn_out.clicked.connect(lambda: self._browse(self.le_out, dir=True))

        # run button ----------------------------------------------------
        self.btn_run = QPushButton("Run Reduction")
        self.layout().addWidget(self.btn_run)
        self.btn_run.clicked.connect(self._run)

        # log pane ------------------------------------------------------
        self.log = QTextEdit(); self.log.setReadOnly(True)
        self.layout().addWidget(self.log, 1)

    # ------------------------------------------------------------------ browse
    def _browse(self, line: QLineEdit, *, file=False, dir=False):
        if file:
            p,_ = QFileDialog.getOpenFileName(self,"Select file","", "CSV (*.csv)")
        elif dir:
            p = QFileDialog.getExistingDirectory(self,"Select folder")
        else:
            p=""
        if p:
            line.setText(p)

    def _pick_sample(self):
        start_dir = self.le_dir.text()
        path, _ = QFileDialog.getOpenFileName(self, "Select a sample MiniSEED file", start_dir,
                                              "MiniSEED (*.mseed *.miniseed *.msd);;All (*.*)")
        if not path:
            return
        self.sample_file = Path(path)
        self.le_sample.setText(str(self.sample_file))
        if not self.le_dir.text():
            self.le_dir.setText(str(self.sample_file.parent))
        self._infer_prefix()
        self._infer_fs()

    # ------------------------------------------------------------------ run
    def _run(self):
        csv_path = Path(self.le_csv.text()).expanduser()
        out_dir  = Path(self.le_out.text()).expanduser(); out_dir.mkdir(parents=True, exist_ok=True)

        seed_dir_txt = self.le_dir.text().strip()
        if not seed_dir_txt:
            QMessageBox.warning(self, "MiniSEED", "Select the MiniSEED directory and a sample file first."); return
        seed_dir = Path(seed_dir_txt)
        if not seed_dir.is_dir():
            QMessageBox.warning(self, "Data dir", f"MiniSEED folder invalid: {seed_dir}"); return
        if not self.sample_file:
            QMessageBox.warning(self, "Sample", "Pick a sample MiniSEED file to infer prefix and Fs."); return

        try:
            station_id = int(self.le_id.text())
        except ValueError:
            QMessageBox.warning(self,"Station ID","Enter integer station id.")
            return
        if not csv_path.is_file():
            QMessageBox.warning(self,"CSV","CSV path invalid.")
            return

        rows=[]
        with csv_path.open(newline="") as f:
            reader=csv.DictReader(f)
            rows=list(reader)
        if not rows:
            QMessageBox.warning(self,"CSV","CSV has no data rows.")
            return
        self.log.clear(); self.log.append(f"Processing {len(rows)} window(s)…")

        # Build filename pattern using inferred prefix (apply station if templated)
        prefix = self.inferred_prefix or ""
        if "{station" in prefix:
            try:
                prefix = prefix.format(station=station_id)
            except Exception:
                pass
        pattern = str(seed_dir / f"{prefix}{{date}}_{{hour:02d}}0000.miniseed")

        # Determine Fs to use: manual overrides, else CSV per-row, else auto
        manual_txt = self.le_manual_fs.text().strip()
        manual_fs: Optional[float] = None
        if manual_txt:
            try:
                manual_fs = float(manual_txt)
            except ValueError:
                QMessageBox.warning(self, "Manual Fs", "Manual Fs must be numeric (e.g. 500). Using auto/CSV values instead.")

        # Ensure auto Fs exists if needed
        if manual_fs is None and not self.auto_fs:
            self._infer_fs()

        # Show chosen Fs policy
        if manual_fs is not None:
            self.log.append(f"Manual Fs override: {manual_fs:g} Hz (applies to all rows)")
        elif self.auto_fs:
            self.log.append(f"Auto Fs from sample: {self.auto_fs:g} Hz (rows can override via CSV Fs_Hz)")
        else:
            self.log.append("Fs fallback: 500 Hz (no auto detected and no CSV Fs_Hz)")

        ok=0
        for r in rows:
            fig_name=r["Figure"].strip() or "HV"
            # Per-row Fs: manual > CSV Fs_Hz > auto > default 500
            sampling: float
            sampling = manual_fs if manual_fs is not None else (
                float(r.get("Fs_Hz","500")) if r.get("Fs_Hz","") not in (None, "") else (self.auto_fs or 500.0)
            )
            self.log.append(f"→ {fig_name}: using Fs = {sampling:g} Hz")
            # create temp CSV single-row
            tmp_csv = out_dir / f"_{fig_name}_tmp.csv"
            with tmp_csv.open("w", newline="") as fh:
                writer=csv.DictWriter(fh, fieldnames=list(r.keys()))
                writer.writeheader(); writer.writerow(r)
            try:
                process_station(
                    csv_path=tmp_csv,
                    pattern=pattern,
                    sampling_rate=sampling,
                    station_id=station_id,
                    output_dir=out_dir,
                    verbose=False,
                )
                # rename output file
                hv_file = out_dir / f"ArrayData_HV{station_id}.mat"
                if hv_file.exists():
                    hv_file.rename(out_dir / f"ArrayData_{fig_name}.mat")
                ok+=1; self.log.append(f"✓ {fig_name}")
            except Exception as exc:
                self.log.append(f"❌ {fig_name}: {exc}")
            finally:
                tmp_csv.unlink(missing_ok=True)

        self.log.append(f"Done. {ok}/{len(rows)} MAT files created.")

    # ------------------------------------------------------------------ inference helpers
    def _infer_prefix(self):
        if not self.sample_file:
            self.inferred_prefix = None
            self.lbl_prefix.setText("Prefix: —")
            return
        m = re.match(r"(.+?)_\d{8}_\d{6}$", self.sample_file.stem)
        self.inferred_prefix = (m.group(1) + "_") if m else None
        self.lbl_prefix.setText(f"Prefix: {self.inferred_prefix or '—'}")

    def _infer_fs(self):
        if not self.sample_file:
            self.auto_fs = None; self.le_auto_fs.setText(""); return
        try:
            from rdmseed_py import rdmseed
            XX, _ = rdmseed(str(self.sample_file))
            self.auto_fs = float(XX[0].SampleRate) if XX else None
        except Exception:
            self.auto_fs = None
        self.le_auto_fs.setText(f"{self.auto_fs:g}" if self.auto_fs else "")