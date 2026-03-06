"""
Station Manager
================

Manages the station file table: adding/removing rows, browsing files,
batch import, auto-detect from folder, station number extraction,
and file grouping by station.
"""

from PyQt5.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QSpinBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QMessageBox,
)
from PyQt5.QtCore import Qt
import os
import re


class StationManager:
    """Encapsulates station table operations for the automatic workflow.

    The caller creates a QTableWidget and passes it in. This class provides
    all the methods that were previously inline in NewTab0_Automatic.
    """

    def __init__(self, station_table: QTableWidget, log_fn=None):
        self._table = station_table
        self._log = log_fn or (lambda msg: None)

    # ----------------------------------------------------------------
    # Public API
    # ----------------------------------------------------------------

    _COL_STATION = 0
    _COL_FILENAME = 1
    _COL_FILES = 2
    _COL_ACTIONS = 3

    def add_station_row(self, station_num=None, files=None):
        """Add a new station row to the table."""
        row = self._table.rowCount()
        self._table.insertRow(row)

        stn_spin = QSpinBox()
        stn_spin.setRange(1, 99)
        if station_num:
            stn_spin.setValue(station_num)
        else:
            existing = self.get_existing_station_nums()
            next_num = 1
            while next_num in existing:
                next_num += 1
            stn_spin.setValue(next_num)
        self._table.setCellWidget(row, self._COL_STATION, stn_spin)

        fname_item = QTableWidgetItem()
        fname_item.setFlags(fname_item.flags() & ~Qt.ItemIsEditable)
        fname_item.setText(self._format_filename(files or []))
        self._table.setItem(row, self._COL_FILENAME, fname_item)

        files_item = QTableWidgetItem()
        files_item.setData(Qt.UserRole, files or [])
        files_item.setText(self._format_files_text(files or []))
        files_item.setFlags(files_item.flags() & ~Qt.ItemIsEditable)
        self._table.setItem(row, self._COL_FILES, files_item)

        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(2, 2, 2, 2)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(lambda checked, r=row: self.browse_station_files(r))
        action_layout.addWidget(browse_btn)

        self._table.setCellWidget(row, self._COL_ACTIONS, action_widget)
        self._log(f"Added station row #{stn_spin.value()}")

    def remove_selected_rows(self):
        """Remove selected rows from the table."""
        rows = set(idx.row() for idx in self._table.selectedIndexes())
        for r in sorted(rows, reverse=True):
            self._table.removeRow(r)
        if rows:
            self._log(f"Removed {len(rows)} station row(s)")

    def clear_all(self):
        """Remove all station rows."""
        self._table.setRowCount(0)
        self._log("Cleared all stations")

    def browse_station_files(self, row):
        """Open file dialog for a specific station row."""
        from hvsr_pro.packages.batch_processing.data_adapter import get_file_dialog_filter
        file_filter = get_file_dialog_filter()
        files, _ = QFileDialog.getOpenFileNames(
            self._table, "Select Seismic Data Files for Station", "",
            file_filter
        )
        if files:
            item = self._table.item(row, self._COL_FILES)
            if item:
                existing = item.data(Qt.UserRole) or []
                all_files = existing + [f for f in files if f not in existing]
                item.setData(Qt.UserRole, all_files)
                item.setText(self._format_files_text(all_files))

                fname_item = self._table.item(row, self._COL_FILENAME)
                if fname_item:
                    fname_item.setText(self._format_filename(all_files))

                stn_spin = self._table.cellWidget(row, self._COL_STATION)
                stn_num = stn_spin.value() if stn_spin else row + 1
                self._log(f"Added {len(files)} file(s) to Station #{stn_num}")

    def batch_import_files(self):
        """Select multiple files at once and auto-group by station.

        If station numbers cannot be detected from any filename, each
        file is assigned to its own station sequentially.
        """
        from hvsr_pro.packages.batch_processing.data_adapter import get_file_dialog_filter
        file_filter = get_file_dialog_filter()
        files, _ = QFileDialog.getOpenFileNames(
            self._table, "Select ALL Seismic Data Files (will auto-group by station)", "",
            file_filter
        )
        if not files:
            return

        station_files, unmatched = self.group_files_by_station(files)

        if not station_files and not unmatched:
            return

        if not station_files and unmatched:
            station_files = self._assign_sequential_stations(files)
            unmatched = []
            self._log("No station pattern detected — assigning each file to its own station")

        elif unmatched:
            next_num = max(station_files.keys()) + 1 if station_files else 1
            for fpath in unmatched:
                full = self._resolve_unmatched_path(fpath, files)
                station_files[next_num] = [full]
                next_num += 1
            self._log(f"{len(unmatched)} file(s) without station pattern assigned sequentially")
            unmatched = []

        self._table.setRowCount(0)
        for stn_num in sorted(station_files.keys()):
            self.add_station_row(station_num=stn_num, files=station_files[stn_num])

        total_files = sum(len(f) for f in station_files.values())
        msg = f"Imported {total_files} file(s) into {len(station_files)} station(s)"
        self._log(msg)

    def auto_detect_stations(self):
        """Auto-detect stations from a folder."""
        folder = QFileDialog.getExistingDirectory(self._table, "Select Folder with Seismic Data Files")
        if not folder:
            return

        from hvsr_pro.packages.batch_processing.data_adapter import get_supported_extensions
        supported = tuple(get_supported_extensions())
        file_paths = [
            os.path.join(folder, f) for f in os.listdir(folder)
            if f.lower().endswith(supported)
        ]

        station_files, unmatched = self.group_files_by_station(file_paths)

        if not station_files:
            QMessageBox.warning(self._table, "No Files Found",
                "No seismic files with station numbers found.\n\n"
                "Expected patterns:\n"
                "  - AR.STN01.centaur-3_0655_*.miniseed\n"
                "  - STN01_*.mseed\n"
                "  - centaur-3_0655_*.miniseed (0655=STN01)\n"
                "  - station01.saf, station01.sac, etc.")
            return

        self._table.setRowCount(0)
        for stn_num in sorted(station_files.keys()):
            self.add_station_row(station_num=stn_num, files=station_files[stn_num])

        fmt_info = ""
        try:
            from hvsr_pro.packages.batch_processing.data_adapter import get_format_name
            first_file = next(iter(next(iter(station_files.values()))))
            fmt_info = f" [{get_format_name(first_file)}]"
        except Exception:
            pass
        msg = f"Auto-detected {len(station_files)} stations from folder{fmt_info}"
        if unmatched:
            msg += f" ({len(unmatched)} files skipped)"
        self._log(msg)

    def get_station_files(self) -> dict:
        """Return dict mapping station_id -> list of file paths."""
        result = {}
        for r in range(self._table.rowCount()):
            spin = self._table.cellWidget(r, self._COL_STATION)
            item = self._table.item(r, self._COL_FILES)
            if spin and item:
                stn_id = spin.value()
                files = item.data(Qt.UserRole) or []
                if files:
                    if stn_id in result:
                        result[stn_id].extend(files)
                    else:
                        result[stn_id] = list(files)
        return result

    def get_existing_station_nums(self) -> list:
        """Return list of station numbers currently in the table."""
        nums = []
        for r in range(self._table.rowCount()):
            spin = self._table.cellWidget(r, self._COL_STATION)
            if spin:
                nums.append(spin.value())
        return nums

    # ----------------------------------------------------------------
    # Station number extraction & file grouping (pure logic)
    # ----------------------------------------------------------------

    @staticmethod
    def extract_station_number(filename: str):
        """Extract station number from filename using multiple patterns.

        Supports:
        - AR.STN01.centaur-3_0655_* (STN pattern + centaur ID)
        - STN01_*, STN02_* (direct STN pattern)
        - centaur-3_0655_* (centaur ID: 0655=STN01, 0656=STN02, etc.)
        - station01.saf, station_02.sac (generic station## pattern)
        - XX01_pt1.txt, AR02_data.saf (letter prefix + digits at start)
        - _01.saf, _02.sac (trailing number before extension)

        Returns
        -------
        int or None
        """
        match = re.search(r'STN(\d{1,2})', filename, re.IGNORECASE)
        if match:
            return int(match.group(1))

        match = re.search(r'centaur-3_(\d{4})_', filename, re.IGNORECASE)
        if match:
            centaur_id = int(match.group(1))
            if 655 <= centaur_id <= 664:
                return centaur_id - 654

        match = re.search(r'station[_-]?(\d{1,2})', filename, re.IGNORECASE)
        if match:
            return int(match.group(1))

        match = re.match(r'^[A-Za-z]{1,4}(\d{1,2})(?:[_.\-]|$)', filename)
        if match:
            return int(match.group(1))

        match = re.search(r'[_-](\d{1,2})\.[a-zA-Z]+$', filename)
        if match:
            return int(match.group(1))

        return None

    @classmethod
    def group_files_by_station(cls, file_paths: list) -> tuple:
        """Group file paths by station number.

        Returns
        -------
        (station_files, unmatched) where station_files is
        dict[int, list[str]] and unmatched is list[str].
        """
        from hvsr_pro.packages.batch_processing.data_adapter import get_supported_extensions
        supported = tuple(get_supported_extensions())

        station_files = {}
        unmatched = []

        for fpath in file_paths:
            fname = os.path.basename(fpath)
            if not fname.lower().endswith(supported):
                continue

            stn_num = cls.extract_station_number(fname)
            if stn_num is not None:
                if stn_num not in station_files:
                    station_files[stn_num] = []
                station_files[stn_num].append(fpath)
            else:
                unmatched.append(fname)

        return station_files, unmatched

    # ----------------------------------------------------------------
    # Private helpers
    # ----------------------------------------------------------------

    @staticmethod
    def _assign_sequential_stations(file_paths: list) -> dict:
        """Assign each file to its own station sequentially (1, 2, 3, ...)."""
        result = {}
        for i, fpath in enumerate(file_paths, start=1):
            result[i] = [fpath]
        return result

    @staticmethod
    def _resolve_unmatched_path(basename: str, original_paths: list) -> str:
        """Find the full path for an unmatched basename from the original list."""
        for p in original_paths:
            if os.path.basename(p) == basename:
                return p
        return basename

    @staticmethod
    def _format_filename(files: list) -> str:
        """Format filename(s) for the Filename column."""
        if not files:
            return ""
        elif len(files) == 1:
            return os.path.basename(files[0])
        else:
            return f"{os.path.basename(files[0])} (+{len(files)-1})"

    @staticmethod
    def _format_files_text(files: list) -> str:
        """Format file list for display in the Files column (full paths)."""
        if not files:
            return "(No files selected)"
        elif len(files) == 1:
            return files[0]
        else:
            return f"{len(files)} files: {files[0]}, ..."
