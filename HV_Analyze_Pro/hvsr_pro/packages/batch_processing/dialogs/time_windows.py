"""
Time Windows Dialog
====================

Dialog for managing multiple time windows with timezone conversion.
Supports CSV import/export and CST/CDT/UTC timezone handling.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QMessageBox,
)
from PyQt5.QtCore import Qt
from datetime import datetime, timedelta
import csv


class TimeWindowsDialog(QDialog):
    """Dialog for managing multiple time windows with timezone conversion."""

    # Timezone offsets (hours to ADD to local time to get UTC)
    TZ_OFFSETS = {
        'UTC': 0,
        'CST': 6,   # Central Standard Time -> UTC+6
        'CDT': 5,   # Central Daylight Time -> UTC+5
    }

    def __init__(self, parent=None, time_windows=None, timezone='CST'):
        super().__init__(parent)
        self.setWindowTitle("Time Windows Configuration")
        self.setModal(True)
        self.setMinimumSize(700, 400)

        self._time_windows = time_windows or []
        self._timezone = timezone
        self._build_ui()
        self._load_windows()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Timezone selection
        tz_layout = QHBoxLayout()
        tz_layout.addWidget(QLabel("Input times are in:"))
        self.tz_combo = QComboBox()
        self.tz_combo.addItems(['CST (Central Standard, +6h to UTC)',
                                'CDT (Central Daylight, +5h to UTC)',
                                'UTC (no conversion)'])
        if self._timezone == 'CDT':
            self.tz_combo.setCurrentIndex(1)
        elif self._timezone == 'UTC':
            self.tz_combo.setCurrentIndex(2)
        else:
            self.tz_combo.setCurrentIndex(0)
        self.tz_combo.setToolTip("Select timezone of your input times.\nTimes will be converted to UTC for processing.")
        tz_layout.addWidget(self.tz_combo)
        tz_layout.addStretch()
        layout.addLayout(tz_layout)

        # Info label
        info_label = QLabel("Each row defines a time window. All windows will be processed for each station.")
        info_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(info_label)

        # Table for time windows
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(['Config Name', 'Start Time', 'End Time'])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setToolTip("Format: YYYY-MM-DD HH:MM:SS")
        layout.addWidget(self.table)

        # Buttons for row management
        btn_layout = QHBoxLayout()

        self.add_btn = QPushButton("+ Add Row")
        self.add_btn.clicked.connect(self._add_row)
        btn_layout.addWidget(self.add_btn)

        self.remove_btn = QPushButton("- Remove Selected")
        self.remove_btn.clicked.connect(self._remove_selected)
        btn_layout.addWidget(self.remove_btn)

        btn_layout.addStretch()

        self.import_btn = QPushButton("Import CSV...")
        self.import_btn.clicked.connect(self._import_csv)
        btn_layout.addWidget(self.import_btn)

        self.export_btn = QPushButton("Export CSV...")
        self.export_btn.clicked.connect(self._export_csv)
        btn_layout.addWidget(self.export_btn)

        layout.addLayout(btn_layout)

        # OK/Cancel buttons
        dialog_btns = QHBoxLayout()
        dialog_btns.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        dialog_btns.addWidget(self.cancel_btn)

        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setDefault(True)
        dialog_btns.addWidget(self.ok_btn)

        layout.addLayout(dialog_btns)

    def _add_row(self, config_name="", start_time="", end_time=""):
        """Add a new row to the table."""
        row = self.table.rowCount()
        self.table.insertRow(row)

        # Config name
        name_item = QTableWidgetItem(config_name or f"Config_{row+1}")
        self.table.setItem(row, 0, name_item)

        # Start time
        start_item = QTableWidgetItem(start_time)
        start_item.setToolTip("YYYY-MM-DD HH:MM:SS")
        self.table.setItem(row, 1, start_item)

        # End time
        end_item = QTableWidgetItem(end_time)
        end_item.setToolTip("YYYY-MM-DD HH:MM:SS")
        self.table.setItem(row, 2, end_item)

    def _remove_selected(self):
        """Remove selected rows."""
        rows = set(item.row() for item in self.table.selectedItems())
        for row in sorted(rows, reverse=True):
            self.table.removeRow(row)

    def _load_windows(self):
        """Load existing time windows into the table."""
        for win in self._time_windows:
            self._add_row(
                config_name=win.get('name', ''),
                start_time=win.get('start_local', ''),
                end_time=win.get('end_local', '')
            )

        # Add an empty row if no windows
        if self.table.rowCount() == 0:
            self._add_row()

    def _get_timezone(self):
        """Get selected timezone key."""
        idx = self.tz_combo.currentIndex()
        return ['CST', 'CDT', 'UTC'][idx]

    def _get_tz_offset_hours(self):
        """Get timezone offset in hours to convert to UTC."""
        tz = self._get_timezone()
        return self.TZ_OFFSETS.get(tz, 0)

    def _import_csv(self):
        """Import time windows from CSV file."""
        path, _ = QFileDialog.getOpenFileName(self, "Import Time Windows CSV", "", "CSV files (*.csv)")
        if not path:
            return

        try:
            with open(path, 'r', newline='') as f:
                reader = csv.reader(f)
                header = next(reader, None)

                # Clear existing rows
                self.table.setRowCount(0)

                for row in reader:
                    if len(row) < 13:
                        continue

                    # Parse CSV format: Config, S_Year, S_Month, S_Day, S_Hour, S_Min, S_Sec, E_Year, ...
                    config_name = row[0].strip()
                    try:
                        s_year, s_month, s_day = int(row[1]), int(row[2]), int(row[3])
                        s_hour, s_min, s_sec = int(row[4]), int(row[5]), int(row[6])
                        e_year, e_month, e_day = int(row[7]), int(row[8]), int(row[9])
                        e_hour, e_min, e_sec = int(row[10]), int(row[11]), int(row[12])

                        start_str = f"{s_year:04d}-{s_month:02d}-{s_day:02d} {s_hour:02d}:{s_min:02d}:{s_sec:02d}"
                        end_str = f"{e_year:04d}-{e_month:02d}-{e_day:02d} {e_hour:02d}:{e_min:02d}:{e_sec:02d}"

                        self._add_row(config_name, start_str, end_str)
                    except (ValueError, IndexError):
                        continue

                QMessageBox.information(self, "Import Complete",
                    f"Imported {self.table.rowCount()} time window(s) from:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Could not read CSV:\n{e}")

    def _export_csv(self):
        """Export time windows to CSV file."""
        windows = self.get_time_windows_local()
        if not windows:
            QMessageBox.warning(self, "No Windows", "No valid time windows to export.")
            return

        path, _ = QFileDialog.getSaveFileName(self, "Export Time Windows CSV",
                                               "time_windows.csv", "CSV files (*.csv)")
        if not path:
            return

        try:
            with open(path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Config', 'S_Year', 'S_Month', 'S_Day', 'S_Hour', 'S_Min', 'S_Sec',
                                'E_Year', 'E_Month', 'E_Day', 'E_Hour', 'E_Min', 'E_Sec'])

                for win in windows:
                    start = win['start_dt']
                    end = win['end_dt']
                    writer.writerow([
                        win['name'],
                        start.year, start.month, start.day, start.hour, start.minute, start.second,
                        end.year, end.month, end.day, end.hour, end.minute, end.second
                    ])

            QMessageBox.information(self, "Export Complete", f"Exported to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Could not write CSV:\n{e}")

    def get_time_windows_local(self):
        """Get time windows as entered (local time, no conversion)."""
        windows = []
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            start_item = self.table.item(row, 1)
            end_item = self.table.item(row, 2)

            if not all([name_item, start_item, end_item]):
                continue

            name = name_item.text().strip()
            start_str = start_item.text().strip()
            end_str = end_item.text().strip()

            if not start_str or not end_str:
                continue

            try:
                start_dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S")
                end_dt = datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S")

                windows.append({
                    'name': name or f"Window_{row+1}",
                    'start_local': start_str,
                    'end_local': end_str,
                    'start_dt': start_dt,
                    'end_dt': end_dt,
                })
            except ValueError:
                continue

        return windows

    def get_time_windows_utc(self):
        """Get time windows converted to UTC."""
        windows_local = self.get_time_windows_local()
        offset_hours = self._get_tz_offset_hours()
        offset = timedelta(hours=offset_hours)

        windows_utc = []
        for win in windows_local:
            start_utc = win['start_dt'] + offset
            end_utc = win['end_dt'] + offset

            windows_utc.append({
                'name': win['name'],
                'start_local': win['start_local'],
                'end_local': win['end_local'],
                'start_utc': start_utc.strftime("%Y-%m-%d %H:%M:%S"),
                'end_utc': end_utc.strftime("%Y-%m-%d %H:%M:%S"),
                'start_dt_utc': start_utc,
                'end_dt_utc': end_utc,
            })

        return windows_utc

    def get_timezone(self):
        """Return selected timezone."""
        return self._get_timezone()

    def get_result(self):
        """Get dialog result: list of time windows with UTC conversion."""
        return {
            'timezone': self._get_timezone(),
            'windows': self.get_time_windows_utc(),
        }
