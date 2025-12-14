from __future__ import annotations
"""NewTab4_WriteMiniseed.py

Tab for converting ArrayData.mat to individual MiniSEED files for Geopsy.
This is the second step after circular array reduction.
"""

from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
    QLabel, QLineEdit, QTextEdit, QMessageBox, QCheckBox, QGroupBox,
)

from array_write_miniseed import write_miniseed_files


class NewTab4_WriteMiniseed(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setLayout(QVBoxLayout())

        # Description
        desc = QLabel(
            "Convert ArrayData.mat to individual MiniSEED files for Geopsy.\n"
            "This creates one file per station per component (e.g., 30 files for 10 stations × 3 components).\n"
            "Output files can be imported into Geopsy for HFK, MSPAC, and HVSR analysis."
        )
        desc.setWordWrap(True)
        self.layout().addWidget(desc)

        # Input/Output section
        io_group = QGroupBox("Input / Output")
        io_layout = QVBoxLayout()
        io_group.setLayout(io_layout)
        self.layout().addWidget(io_group)

        def _row(label: str):
            hl = QHBoxLayout()
            hl.addWidget(QLabel(label))
            le = QLineEdit()
            hl.addWidget(le)
            btn = QPushButton("…")
            hl.addWidget(btn)
            io_layout.addLayout(hl)
            return le, btn

        self.le_mat, btn_mat = _row("ArrayData.mat:")
        self.le_out, btn_out = _row("Output folder:")

        btn_mat.clicked.connect(lambda: self._browse(self.le_mat, file=True, filter="MAT (*.mat)"))
        btn_out.clicked.connect(lambda: self._browse(self.le_out, dir=True))

        # Settings section
        settings_group = QGroupBox("Settings")
        settings_layout = QVBoxLayout()
        settings_group.setLayout(settings_layout)
        self.layout().addWidget(settings_group)

        # Array name
        hl_name = QHBoxLayout()
        hl_name.addWidget(QLabel("Array Name:"))
        self.le_array_name = QLineEdit("A1")
        self.le_array_name.setFixedWidth(100)
        self.le_array_name.setToolTip("Used in filename, e.g., AR.STN01.A1.HNZ")
        hl_name.addWidget(self.le_array_name)
        hl_name.addStretch(1)
        settings_layout.addLayout(hl_name)

        # Network code
        hl_net = QHBoxLayout()
        hl_net.addWidget(QLabel("Network Code:"))
        self.le_network = QLineEdit("AR")
        self.le_network.setFixedWidth(60)
        self.le_network.setToolTip("2-character network code")
        hl_net.addWidget(self.le_network)
        hl_net.addStretch(1)
        settings_layout.addLayout(hl_net)

        # Sampling rate override
        hl_sr = QHBoxLayout()
        hl_sr.addWidget(QLabel("Sampling Rate Override:"))
        self.le_sr = QLineEdit()
        self.le_sr.setPlaceholderText("leave blank to use from mat file")
        self.le_sr.setFixedWidth(200)
        hl_sr.addWidget(self.le_sr)
        hl_sr.addStretch(1)
        settings_layout.addLayout(hl_sr)

        # Relative time checkbox
        self.chk_relative = QCheckBox("Use relative time (recommended for Geopsy)")
        self.chk_relative.setChecked(True)
        self.chk_relative.setToolTip(
            "If checked, start time is rounded to integer day (like MATLAB relativetime=1).\n"
            "This is the standard for Geopsy processing."
        )
        settings_layout.addWidget(self.chk_relative)

        # Run button
        self.btn_run = QPushButton("Write MiniSEED Files")
        self.btn_run.setStyleSheet("font-weight: bold; padding: 10px;")
        self.layout().addWidget(self.btn_run)
        self.btn_run.clicked.connect(self._run)

        # Log pane
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.layout().addWidget(self.log, 1)

    def _browse(self, line: QLineEdit, *, file=False, dir=False, filter=""):
        if file:
            p, _ = QFileDialog.getOpenFileName(self, "Select file", "", filter)
        elif dir:
            p = QFileDialog.getExistingDirectory(self, "Select folder")
        else:
            p = ""
        if p:
            line.setText(p)

    def _run(self):
        """Run the MiniSEED writing process."""
        # Validate inputs
        mat_path = Path(self.le_mat.text()).expanduser()
        if not mat_path.is_file():
            QMessageBox.warning(self, "Input", "Please select a valid ArrayData.mat file.")
            return
        
        out_dir = Path(self.le_out.text()).expanduser()
        if not self.le_out.text().strip():
            QMessageBox.warning(self, "Output", "Please select an output folder.")
            return
        out_dir.mkdir(parents=True, exist_ok=True)
        
        array_name = self.le_array_name.text().strip() or "A1"
        network = self.le_network.text().strip() or "AR"
        
        # Sampling rate
        sr_text = self.le_sr.text().strip()
        sampling_rate = None
        if sr_text:
            try:
                sampling_rate = float(sr_text)
            except ValueError:
                QMessageBox.warning(self, "Sampling Rate", "Sampling rate must be numeric.")
                return
        
        use_relative_time = self.chk_relative.isChecked()
        
        self.log.clear()
        self.log.append("Array Write MiniSEED - Geopsy Export")
        self.log.append("=" * 50)
        self.log.append(f"Input: {mat_path}")
        self.log.append(f"Output: {out_dir}")
        self.log.append(f"Array name: {array_name}")
        self.log.append(f"Network: {network}")
        self.log.append(f"Relative time: {use_relative_time}")
        self.log.append("")
        
        try:
            files = write_miniseed_files(
                mat_path=mat_path,
                output_dir=out_dir,
                array_name=array_name,
                network=network,
                sampling_rate=sampling_rate,
                use_relative_time=use_relative_time,
                verbose=True,
            )
            
            self.log.append("")
            self.log.append("=" * 50)
            self.log.append(f"✓ SUCCESS! Created {len(files)} MiniSEED files")
            self.log.append("")
            self.log.append("Next steps for Geopsy:")
            self.log.append("1. Drag all files into Geopsy")
            self.log.append("2. Create table and sort by T0, Component, Name")
            self.log.append("3. Set receiver coordinates")
            self.log.append("4. Create groups for HFK (XYZ) and MSPAC (Z only)")
            self.log.append("=" * 50)
            
            QMessageBox.information(
                self,
                "Success",
                f"Created {len(files)} MiniSEED files!\n\n"
                f"Location: {out_dir}\n\n"
                f"Files can now be imported into Geopsy."
            )
            
        except Exception as exc:
            import traceback
            self.log.append("")
            self.log.append("=" * 50)
            self.log.append(f"❌ ERROR: {exc}")
            self.log.append("")
            self.log.append("Traceback:")
            self.log.append(traceback.format_exc())
            self.log.append("=" * 50)
            QMessageBox.critical(self, "Error", f"Failed:\n{exc}")
