"""
Time Windows Dialog
====================

Dialog for managing multiple time windows with timezone conversion.
Supports CSV import/export and CST/CDT/UTC timezone handling.

Uses QDateTimeEdit widgets for intuitive date/time entry with calendar popup.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QMessageBox, QDateTimeEdit,
)
from PyQt5.QtCore import Qt, QDateTime
from datetime import datetime, timedelta
from typing import Optional
import csv


_DT_FORMAT = "yyyy-MM-dd  HH:mm:ss"
_DT_PARSE = "%Y-%m-%d %H:%M:%S"


class TimeWindowsDialog(QDialog):
    """Dialog for managing multiple time windows with timezone conversion.

    Optionally supports per-station assignment when *station_ids* is provided.
    """

    TZ_OFFSETS = {
        'UTC': 0,
        'CST': 6,
        'CDT': 5,
    }

    def __init__(self, parent=None, time_windows=None, timezone='CST',
                 station_ids=None, station_assignments=None):
        """
        Parameters
        ----------
        station_ids : list[int], optional
            Station numbers available for assignment. If provided,
            an "Assigned Stations" column is added to the table.
        station_assignments : dict, optional
            Maps config_name -> list of station_ids pre-assigned.
        """
        super().__init__(parent)
        self.setWindowTitle("Time Windows Configuration")
        self.setModal(True)
        self.setMinimumSize(800, 480)

        self._time_windows = time_windows or []
        self._timezone = timezone
        self._station_ids = station_ids or []
        self._station_assignments = station_assignments or {}
        self._has_stations = bool(self._station_ids)
        self._build_ui()
        self._load_windows()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # Timezone selection
        tz_layout = QHBoxLayout()
        tz_layout.addWidget(QLabel("Input times are in:"))
        self.tz_combo = QComboBox()
        self.tz_combo.addItems([
            'CST (Central Standard, +6h to UTC)',
            'CDT (Central Daylight, +5h to UTC)',
            'UTC (no conversion)',
        ])
        if self._timezone == 'CDT':
            self.tz_combo.setCurrentIndex(1)
        elif self._timezone == 'UTC':
            self.tz_combo.setCurrentIndex(2)
        else:
            self.tz_combo.setCurrentIndex(0)
        self.tz_combo.setToolTip(
            "Select timezone of your input times.\n"
            "Times will be converted to UTC for processing."
        )
        tz_layout.addWidget(self.tz_combo)
        tz_layout.addStretch()
        layout.addLayout(tz_layout)

        # Info label
        if self._has_stations:
            info_label = QLabel(
                "Define time windows and assign stations to each. "
                "Use Auto-Distribute to assign automatically."
            )
        else:
            info_label = QLabel(
                "Each row defines a time window. "
                "All windows will be processed for each station."
            )
        info_label.setStyleSheet("color: #666; font-style: italic;")
        layout.addWidget(info_label)

        # Table for time windows
        n_cols = 4 if self._has_stations else 3
        self.table = QTableWidget(0, n_cols)
        headers = ['Config Name', 'Start  (Date  &  Time)', 'End  (Date  &  Time)']
        if self._has_stations:
            headers.append('Assigned Stations')
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        if self._has_stations:
            self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.verticalHeader().setDefaultSectionSize(36)
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

        # Auto-distribute buttons (only when stations are available)
        if self._has_stations:
            dist_layout = QHBoxLayout()
            dist_layout.addWidget(QLabel("Auto-Assign:"))

            btn_seq = QPushButton("Sequential Split")
            btn_seq.setToolTip(
                "Divide stations equally among time windows.\n"
                "E.g. 24 stations / 4 windows -> 1-6, 7-12, 13-18, 19-24"
            )
            btn_seq.clicked.connect(self._auto_distribute_sequential)
            dist_layout.addWidget(btn_seq)

            btn_clear = QPushButton("Clear All Assignments")
            btn_clear.clicked.connect(self._clear_assignments)
            dist_layout.addWidget(btn_clear)

            dist_layout.addStretch()
            layout.addLayout(dist_layout)

        # OK / Cancel buttons
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

    # ------------------------------------------------------------------
    # Helpers for creating QDateTimeEdit widgets inside the table
    # ------------------------------------------------------------------

    def _make_dt_widget(self, dt: datetime = None) -> QDateTimeEdit:
        """Create a QDateTimeEdit configured for use inside the table."""
        w = QDateTimeEdit()
        w.setCalendarPopup(True)
        w.setDisplayFormat(_DT_FORMAT)
        if dt:
            w.setDateTime(QDateTime(
                dt.year, dt.month, dt.day,
                dt.hour, dt.minute, dt.second
            ))
        else:
            w.setDateTime(QDateTime.currentDateTime())
        return w

    def _get_row_start_dt(self, row: int) -> Optional[datetime]:
        """Read start datetime from the widget in *row*."""
        w = self.table.cellWidget(row, 1)
        if isinstance(w, QDateTimeEdit):
            return w.dateTime().toPyDateTime()
        return None

    def _get_row_end_dt(self, row: int) -> Optional[datetime]:
        """Read end datetime from the widget in *row*."""
        w = self.table.cellWidget(row, 2)
        if isinstance(w, QDateTimeEdit):
            return w.dateTime().toPyDateTime()
        return None

    # ------------------------------------------------------------------
    # Row management
    # ------------------------------------------------------------------

    def _add_row(self, config_name="", start_dt: datetime = None,
                 end_dt: datetime = None, assigned_stations=None):
        """Add a new row to the table."""
        row = self.table.rowCount()
        self.table.insertRow(row)

        # Config name
        name_item = QTableWidgetItem(config_name or f"Config_{row + 1}")
        self.table.setItem(row, 0, name_item)

        # Start time widget
        self.table.setCellWidget(row, 1, self._make_dt_widget(start_dt))

        # End time widget
        self.table.setCellWidget(row, 2, self._make_dt_widget(end_dt))

        # Assigned stations (editable text, comma-separated station IDs)
        if self._has_stations:
            stn_text = ""
            if assigned_stations:
                stn_text = ", ".join(str(s) for s in assigned_stations)
            stn_item = QTableWidgetItem(stn_text)
            stn_item.setToolTip(
                "Comma-separated station numbers.\n"
                f"Available: {', '.join(str(s) for s in self._station_ids)}"
            )
            self.table.setItem(row, 3, stn_item)

    def _remove_selected(self):
        """Remove selected rows."""
        rows = set()
        for item in self.table.selectedItems():
            rows.add(item.row())
        for idx in self.table.selectionModel().selectedRows():
            rows.add(idx.row())
        # Also count rows where a cell widget is focused
        current = self.table.currentRow()
        if current >= 0:
            rows.add(current)
        for row in sorted(rows, reverse=True):
            self.table.removeRow(row)

    def _load_windows(self):
        """Load existing time windows into the table."""
        for win in self._time_windows:
            name = win.get('name', '')
            assigned = self._station_assignments.get(name, [])

            start_dt = None
            end_dt = None
            if 'start_dt' in win:
                start_dt = win['start_dt']
            elif 'start_local' in win and win['start_local']:
                try:
                    start_dt = datetime.strptime(win['start_local'], _DT_PARSE)
                except ValueError:
                    pass
            if 'end_dt' in win:
                end_dt = win['end_dt']
            elif 'end_local' in win and win['end_local']:
                try:
                    end_dt = datetime.strptime(win['end_local'], _DT_PARSE)
                except ValueError:
                    pass

            self._add_row(
                config_name=name,
                start_dt=start_dt,
                end_dt=end_dt,
                assigned_stations=assigned,
            )

        if self.table.rowCount() == 0:
            self._add_row()

    # ------------------------------------------------------------------
    # Timezone helpers
    # ------------------------------------------------------------------

    def _get_timezone(self):
        """Get selected timezone key."""
        idx = self.tz_combo.currentIndex()
        return ['CST', 'CDT', 'UTC'][idx]

    def _get_tz_offset_hours(self):
        """Get timezone offset in hours to convert to UTC."""
        tz = self._get_timezone()
        return self.TZ_OFFSETS.get(tz, 0)

    # ------------------------------------------------------------------
    # CSV import / export
    # ------------------------------------------------------------------

    def _import_csv(self):
        """Import time windows from CSV file."""
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Time Windows CSV", "", "CSV files (*.csv)"
        )
        if not path:
            return

        try:
            with open(path, 'r', newline='') as f:
                reader = csv.reader(f)
                next(reader, None)  # skip header

                self.table.setRowCount(0)

                for row_data in reader:
                    if len(row_data) < 13:
                        continue

                    config_name = row_data[0].strip()
                    try:
                        s = datetime(
                            int(row_data[1]), int(row_data[2]), int(row_data[3]),
                            int(row_data[4]), int(row_data[5]), int(row_data[6]),
                        )
                        e = datetime(
                            int(row_data[7]), int(row_data[8]), int(row_data[9]),
                            int(row_data[10]), int(row_data[11]), int(row_data[12]),
                        )
                        self._add_row(config_name, start_dt=s, end_dt=e)
                    except (ValueError, IndexError):
                        continue

                QMessageBox.information(
                    self, "Import Complete",
                    f"Imported {self.table.rowCount()} time window(s) from:\n{path}"
                )
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Could not read CSV:\n{e}")

    def _export_csv(self):
        """Export time windows to CSV file."""
        windows = self.get_time_windows_local()
        if not windows:
            QMessageBox.warning(self, "No Windows", "No valid time windows to export.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "Export Time Windows CSV", "time_windows.csv", "CSV files (*.csv)"
        )
        if not path:
            return

        try:
            with open(path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'Config', 'S_Year', 'S_Month', 'S_Day', 'S_Hour', 'S_Min', 'S_Sec',
                    'E_Year', 'E_Month', 'E_Day', 'E_Hour', 'E_Min', 'E_Sec',
                ])

                for win in windows:
                    s = win['start_dt']
                    e = win['end_dt']
                    writer.writerow([
                        win['name'],
                        s.year, s.month, s.day, s.hour, s.minute, s.second,
                        e.year, e.month, e.day, e.hour, e.minute, e.second,
                    ])

            QMessageBox.information(self, "Export Complete", f"Exported to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Could not write CSV:\n{e}")

    # ------------------------------------------------------------------
    # Station distribution helpers
    # ------------------------------------------------------------------

    def _auto_distribute_sequential(self):
        """Distribute stations evenly across time windows."""
        n_windows = self.table.rowCount()
        if n_windows == 0 or not self._station_ids:
            return

        sorted_ids = sorted(self._station_ids)
        chunk_size = len(sorted_ids) // n_windows
        remainder = len(sorted_ids) % n_windows

        idx = 0
        for row in range(n_windows):
            n = chunk_size + (1 if row < remainder else 0)
            chunk = sorted_ids[idx:idx + n]
            idx += n

            if self._has_stations:
                stn_item = self.table.item(row, 3)
                if stn_item:
                    stn_item.setText(", ".join(str(s) for s in chunk))

    def _clear_assignments(self):
        """Clear all station assignments."""
        if not self._has_stations:
            return
        for row in range(self.table.rowCount()):
            stn_item = self.table.item(row, 3)
            if stn_item:
                stn_item.setText("")

    def _parse_assigned_stations(self, row: int) -> list:
        """Parse the assigned stations text for a row."""
        if not self._has_stations:
            return []
        stn_item = self.table.item(row, 3)
        if not stn_item:
            return []
        text = stn_item.text().strip()
        if not text:
            return []
        result = []
        for part in text.replace(";", ",").split(","):
            part = part.strip()
            if part:
                try:
                    result.append(int(part))
                except ValueError:
                    pass
        return result

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_station_assignments(self) -> dict:
        """Return dict mapping config_name -> [station_ids]."""
        assignments = {}
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            if not name_item:
                continue
            name = name_item.text().strip() or f"Window_{row + 1}"
            stations = self._parse_assigned_stations(row)
            if stations:
                assignments[name] = stations
        return assignments

    def get_time_windows_local(self):
        """Get time windows as entered (local time, no conversion)."""
        windows = []
        for row in range(self.table.rowCount()):
            name_item = self.table.item(row, 0)
            if not name_item:
                continue

            name = name_item.text().strip()
            start_dt = self._get_row_start_dt(row)
            end_dt = self._get_row_end_dt(row)

            if start_dt is None or end_dt is None:
                continue

            start_str = start_dt.strftime(_DT_PARSE)
            end_str = end_dt.strftime(_DT_PARSE)

            windows.append({
                'name': name or f"Window_{row + 1}",
                'start_local': start_str,
                'end_local': end_str,
                'start_dt': start_dt,
                'end_dt': end_dt,
            })

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
                'start_utc': start_utc.strftime(_DT_PARSE),
                'end_utc': end_utc.strftime(_DT_PARSE),
                'start_dt_utc': start_utc,
                'end_dt_utc': end_utc,
            })

        return windows_utc

    def get_timezone(self):
        """Return selected timezone."""
        return self._get_timezone()

    def get_result(self):
        """Get dialog result: list of time windows with UTC conversion + assignments."""
        result = {
            'timezone': self._get_timezone(),
            'windows': self.get_time_windows_utc(),
        }
        if self._has_stations:
            result['station_assignments'] = self.get_station_assignments()
        return result
