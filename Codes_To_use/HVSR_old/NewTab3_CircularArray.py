from __future__ import annotations
"""NewTab3_CircularArray.py

Tab for processing circular array data with multiple stations.
Users provide sample files for each station to auto-detect prefixes,
then process all stations together to create ArrayData_CircularArray.mat
"""

import csv
import re
from pathlib import Path
from typing import Optional, Dict

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
    QLabel, QLineEdit, QTextEdit, QMessageBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QGroupBox,
)

from circular_array_reduction import process_circular_array, extract_station_prefix, extract_station_number


class NewTab3_CircularArray(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setLayout(QVBoxLayout())

        # Station configuration section -------------------------------
        station_group = QGroupBox("Station Configuration")
        station_layout = QVBoxLayout()
        station_group.setLayout(station_layout)
        self.layout().addWidget(station_group)

        # Station numbers - flexible input (allows skipping stations)
        num_station_layout = QHBoxLayout()
        num_station_layout.addWidget(QLabel("Station Numbers:"))
        self.le_station_nums = QLineEdit()
        self.le_station_nums.setPlaceholderText("e.g., 1,2,4-10 or 1-2,4-10 (skip dead stations)")
        self.le_station_nums.setText("1-10")  # Default to all 10 stations
        self.le_station_nums.setMinimumWidth(250)
        self.le_station_nums.editingFinished.connect(self._update_station_table)
        num_station_layout.addWidget(self.le_station_nums)
        num_station_layout.addStretch(1)
        station_layout.addLayout(num_station_layout)

        # Table for station sample files
        station_layout.addWidget(QLabel("Select one sample file per station to detect naming pattern:"))
        self.station_table = QTableWidget(0, 3)
        self.station_table.setHorizontalHeaderLabels(["Station #", "Sample File", "Detected Prefix"])
        self.station_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.station_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.station_table.setMaximumHeight(300)
        station_layout.addWidget(self.station_table)

        # Button to browse all sample files
        btn_browse_stations = QPushButton("Browse Station Files...")
        btn_browse_stations.clicked.connect(self._browse_station_files)
        station_layout.addWidget(btn_browse_stations)

        # File pickers ------------------------------------------------
        form = QVBoxLayout()
        self.layout().addLayout(form)

        def _row(label: str):
            hl = QHBoxLayout()
            hl.addWidget(QLabel(label))
            le = QLineEdit()
            hl.addWidget(le)
            btn = QPushButton("…")
            hl.addWidget(btn)
            form.addLayout(hl)
            return le, btn

        self.le_csv, btn_csv = _row("Windows CSV:")
        self.le_out, btn_out = _row("Output folder:")

        btn_csv.clicked.connect(lambda: self._browse(self.le_csv, file=True))
        btn_out.clicked.connect(lambda: self._browse(self.le_out, dir=True))

        # Sampling rate settings --------------------------------------
        hlf = QHBoxLayout()
        form.addLayout(hlf)
        hlf.addWidget(QLabel("Auto Fs:"))
        self.le_auto_fs = QLineEdit()
        self.le_auto_fs.setReadOnly(True)
        self.le_auto_fs.setFixedWidth(80)
        hlf.addWidget(self.le_auto_fs)
        hlf.addWidget(QLabel("Manual Fs:"))
        self.le_manual_fs = QLineEdit()
        self.le_manual_fs.setPlaceholderText("leave blank to use auto")
        self.le_manual_fs.setFixedWidth(120)
        hlf.addWidget(self.le_manual_fs)
        hlf.addStretch(1)

        # Internal state
        self.station_patterns: Dict[int, str] = {}  # station_num -> prefix
        self.auto_fs: Optional[float] = None

        # Initialize table
        self._update_station_table()

        # Run button --------------------------------------------------
        self.btn_run = QPushButton("Run Circular Array Reduction")
        self.layout().addWidget(self.btn_run)
        self.btn_run.clicked.connect(self._run)

        # Log pane ----------------------------------------------------
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.layout().addWidget(self.log, 1)

    # ------------------------------------------------------------------ helpers
    def _browse(self, line: QLineEdit, *, file=False, dir=False):
        if file:
            p, _ = QFileDialog.getOpenFileName(self, "Select file", "", "CSV (*.csv)")
        elif dir:
            p = QFileDialog.getExistingDirectory(self, "Select folder")
        else:
            p = ""
        if p:
            line.setText(p)

    def _parse_station_numbers(self) -> list:
        """Parse station numbers string like '1,2,4-10' into a list of integers."""
        text = self.le_station_nums.text().strip()
        if not text:
            return list(range(1, 11))  # Default to 1-10
        
        station_nums = []
        parts = text.replace(" ", "").split(",")
        for part in parts:
            if "-" in part:
                try:
                    start, end = part.split("-")
                    station_nums.extend(range(int(start), int(end) + 1))
                except ValueError:
                    continue
            else:
                try:
                    station_nums.append(int(part))
                except ValueError:
                    continue
        
        # Remove duplicates and sort, filter to valid range 1-99
        station_nums = sorted(set(n for n in station_nums if 1 <= n <= 99))
        return station_nums

    def _update_station_table(self):
        """Update the station table based on the station numbers specified."""
        station_nums = self._parse_station_numbers()
        
        # Save current file entries before clearing
        current_files = {}
        for i in range(self.station_table.rowCount()):
            stn_item = self.station_table.item(i, 0)
            file_item = self.station_table.item(i, 1)
            if stn_item and file_item and file_item.text().strip():
                try:
                    stn_num = int(stn_item.text())
                    current_files[stn_num] = file_item.text()
                except ValueError:
                    pass
        
        self.station_table.setRowCount(len(station_nums))
        
        for i, station_num in enumerate(station_nums):
            # Station number (read-only)
            item_num = QTableWidgetItem(f"{station_num:02d}")
            item_num.setFlags(item_num.flags() & ~Qt.ItemIsEditable)
            self.station_table.setItem(i, 0, item_num)
            
            # Sample file path - restore if previously entered
            if station_num in current_files:
                self.station_table.setItem(i, 1, QTableWidgetItem(current_files[station_num]))
                # Re-extract prefix
                prefix = extract_station_prefix(Path(current_files[station_num]))
                display_prefix = Path(prefix).name if "/" in prefix or "\\" in prefix else prefix
                item_prefix = QTableWidgetItem(display_prefix)
                item_prefix.setFlags(item_prefix.flags() & ~Qt.ItemIsEditable)
                self.station_table.setItem(i, 2, item_prefix)
            else:
                self.station_table.setItem(i, 1, QTableWidgetItem(""))
                item_prefix = QTableWidgetItem("")
                item_prefix.setFlags(item_prefix.flags() & ~Qt.ItemIsEditable)
                self.station_table.setItem(i, 2, item_prefix)

    def _browse_station_files(self):
        """Allow user to select multiple sample files for stations."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select sample MiniSEED files (one per station)",
            "",
            "MiniSEED (*.mseed *.miniseed *.msd);;All (*.*)"
        )
        
        if not files:
            return
        
        # Get currently configured station numbers
        station_nums = self._parse_station_numbers()
        
        # Create a mapping of station number to table row
        station_to_row = {stn: i for i, stn in enumerate(station_nums)}
        
        # Try to auto-detect station numbers from filenames
        for file_path in files:
            path = Path(file_path)
            # Try to extract station number
            match = re.search(r"STN(\d+)", path.name)
            if match:
                station_num = int(match.group(1))
                if station_num in station_to_row:
                    row = station_to_row[station_num]
                    self.station_table.setItem(row, 1, QTableWidgetItem(str(path)))
                    # Auto-detect prefix (full path)
                    prefix = extract_station_prefix(path)
                    self.station_patterns[station_num] = prefix
                    # Display only filename part in table
                    display_prefix = Path(prefix).name if "/" in prefix or "\\" in prefix else prefix
                    item_prefix = QTableWidgetItem(display_prefix)
                    item_prefix.setFlags(item_prefix.flags() & ~Qt.ItemIsEditable)
                    self.station_table.setItem(row, 2, item_prefix)
        
        # Infer Fs from first file if we haven't already
        if not self.auto_fs and files:
            self._infer_fs(Path(files[0]))

    def _infer_fs(self, sample_file: Path):
        """Infer sampling rate from a sample file."""
        try:
            from rdmseed_py import rdmseed
            XX, _ = rdmseed(str(sample_file), plot=False, verbose=False)
            self.auto_fs = float(XX[0].SampleRate) if XX else None
        except Exception as e:
            self.auto_fs = None
            self.log.append(f"Warning: Could not infer Fs from {sample_file.name}: {e}")
        
        self.le_auto_fs.setText(f"{self.auto_fs:g}" if self.auto_fs else "")

    def _collect_station_patterns(self) -> bool:
        """Collect all station patterns from the table. Returns False if any are missing."""
        self.station_patterns.clear()
        station_nums = self._parse_station_numbers()
        
        if not station_nums:
            QMessageBox.warning(
                self,
                "No Stations",
                "Please specify at least one station number (e.g., '1-10' or '1,2,4-10')"
            )
            return False
        
        for i, station_num in enumerate(station_nums):
            file_item = self.station_table.item(i, 1)
            
            if not file_item or not file_item.text().strip():
                QMessageBox.warning(
                    self,
                    "Missing Station File",
                    f"Please provide a sample file for Station {station_num:02d}"
                )
                return False
            
            sample_path = Path(file_item.text().strip())
            if not sample_path.is_file():
                QMessageBox.warning(
                    self,
                    "Invalid File",
                    f"Station {station_num:02d} file does not exist:\n{sample_path}"
                )
                return False
            
            # Extract prefix
            prefix = extract_station_prefix(sample_path)
            self.station_patterns[station_num] = prefix
            
            # Update table display - show only filename part, not full path
            display_prefix = Path(prefix).name if "/" in prefix or "\\" in prefix else prefix
            item_prefix = QTableWidgetItem(display_prefix)
            item_prefix.setFlags(item_prefix.flags() & ~Qt.ItemIsEditable)
            self.station_table.setItem(i, 2, item_prefix)
        
        return True

    # ------------------------------------------------------------------ run
    def _run(self):
        """Run the circular array reduction process."""
        # Validate inputs
        csv_path = Path(self.le_csv.text()).expanduser()
        if not csv_path.is_file():
            QMessageBox.warning(self, "CSV", "Please select a valid windows CSV file.")
            return
        
        out_dir = Path(self.le_out.text()).expanduser()
        out_dir.mkdir(parents=True, exist_ok=True)
        
        # Collect station patterns
        if not self._collect_station_patterns():
            return
        
        # Determine sampling rate
        manual_txt = self.le_manual_fs.text().strip()
        if manual_txt:
            try:
                sampling_rate = float(manual_txt)
            except ValueError:
                QMessageBox.warning(self, "Manual Fs", "Manual Fs must be numeric.")
                return
        elif self.auto_fs:
            sampling_rate = self.auto_fs
        else:
            # Try to infer from first station file
            first_file = Path(self.station_table.item(0, 1).text())
            self._infer_fs(first_file)
            if self.auto_fs:
                sampling_rate = self.auto_fs
            else:
                # Default fallback to 100 Hz (MATLAB default)
                sampling_rate = 100.0
                self.log.append(f"Warning: Using default Fs = {sampling_rate} Hz (MATLAB default)")
        
        self.log.clear()
        self.log.append(f"Circular Array Reduction - MATLAB Compatible")
        self.log.append(f"Processing {len(self.station_patterns)} stations")
        self.log.append(f"Sampling rate: {sampling_rate} Hz")
        self.log.append(f"\nStation patterns:")
        for stn, prefix in sorted(self.station_patterns.items()):
            self.log.append(f"  Station {stn:02d}: {prefix}")
        self.log.append("")
        
        # Run the processing
        try:
            mat_path = process_circular_array(
                csv_path=csv_path,
                station_patterns=self.station_patterns,
                sampling_rate=sampling_rate,
                output_dir=out_dir,
                verbose=True,
            )
            
            self.log.append("")
            self.log.append("=" * 60)
            self.log.append("✓ SUCCESS!")
            self.log.append(f"Created: {mat_path}")
            self.log.append("")
            self.log.append("Output file: ArrayData.mat")
            self.log.append("  - Array1Z, Array1N, Array1E: num_samples × num_stations")
            self.log.append("  - TArray1Z, TArray1N, TArray1E: cell arrays")
            self.log.append("  - time1: time vector")
            self.log.append("  - Fs_Hz: sampling rate")
            self.log.append("=" * 60)
            
            QMessageBox.information(
                self,
                "Success",
                f"Circular array data processed successfully!\n\n"
                f"Output: {mat_path}\n\n"
                f"This ArrayData.mat file can now be used with\n"
                f"ArrayWriteMiniseed.m or Geopsy processing."
            )
            
        except Exception as exc:
            import traceback
            self.log.append("")
            self.log.append("=" * 60)
            self.log.append(f"❌ ERROR: {exc}")
            self.log.append("")
            self.log.append("Traceback:")
            self.log.append(traceback.format_exc())
            self.log.append("=" * 60)
            QMessageBox.critical(self, "Processing Error", f"Failed to process:\n{exc}")
