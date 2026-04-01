"""
Time Range Panel
================

Reusable time range selection panel for data input dialogs.

Uses separate Date and Time widgets for clarity.
"""

from datetime import datetime, date, time as dtime
from typing import Dict, Any, Optional

try:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QGridLayout,
        QCheckBox, QLabel, QComboBox, QDateEdit, QTimeEdit
    )
    from PyQt5.QtCore import Qt, pyqtSignal, QDateTime, QDate, QTime
    from PyQt5.QtGui import QFont
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


TIMEZONES = [
    ("UTC-12", -12),
    ("UTC-11", -11),
    ("UTC-10 (HST)", -10),
    ("UTC-9 (AKST)", -9),
    ("UTC-8 (PST)", -8),
    ("UTC-7 (MST)", -7),
    ("UTC-6 (CST)", -6),
    ("UTC-5 (CDT/EST)", -5),
    ("UTC-4 (EDT)", -4),
    ("UTC-3", -3),
    ("UTC-2", -2),
    ("UTC-1", -1),
    ("UTC+0 (GMT)", 0),
    ("UTC+1 (CET)", 1),
    ("UTC+2 (EET)", 2),
    ("UTC+3 (MSK)", 3),
    ("UTC+4", 4),
    ("UTC+5", 5),
    ("UTC+5:30 (IST)", 5.5),
    ("UTC+6", 6),
    ("UTC+7", 7),
    ("UTC+8 (CST/SGT)", 8),
    ("UTC+9 (JST/KST)", 9),
    ("UTC+10 (AEST)", 10),
    ("UTC+11", 11),
    ("UTC+12 (NZST)", 12),
]


if HAS_PYQT5:
    class TimeRangePanel(QWidget):
        """
        Reusable time range selection panel with separate Date and Time inputs.

        Signals:
            time_range_changed: Emitted when any time range setting changes
            enabled_changed: Emitted when enable state changes
        """

        time_range_changed = pyqtSignal(dict)
        enabled_changed = pyqtSignal(bool)

        def __init__(self, parent=None, title: str = "Time Range Filter"):
            super().__init__(parent)
            self._title = title
            self._init_ui()
            self._connect_signals()

        def _init_ui(self):
            """Initialize the user interface."""
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)

            self.group_box = QGroupBox(self._title)
            group_layout = QVBoxLayout(self.group_box)

            self.enable_check = QCheckBox("Enable time range filter")
            self.enable_check.setToolTip(
                "Filter data to a specific time range before processing"
            )
            group_layout.addWidget(self.enable_check)

            # Timezone selector
            tz_layout = QHBoxLayout()
            tz_layout.addWidget(QLabel("Timezone:"))
            self.tz_combo = QComboBox()
            for tz_name, _ in TIMEZONES:
                self.tz_combo.addItem(tz_name)
            default_idx = self.tz_combo.findText("UTC-5 (CDT/EST)")
            if default_idx >= 0:
                self.tz_combo.setCurrentIndex(default_idx)
            else:
                gmt_idx = self.tz_combo.findText("UTC+0 (GMT)")
                if gmt_idx >= 0:
                    self.tz_combo.setCurrentIndex(gmt_idx)
            self.tz_combo.setEnabled(False)
            tz_layout.addWidget(self.tz_combo)
            group_layout.addLayout(tz_layout)

            # Grid for start / end date-time
            grid = QGridLayout()
            grid.setHorizontalSpacing(8)
            grid.setVerticalSpacing(4)

            # Column headers
            header_font = QFont()
            header_font.setBold(True)

            date_header = QLabel("Date (YYYY-MM-DD)")
            date_header.setFont(header_font)
            date_header.setAlignment(Qt.AlignCenter)
            time_header = QLabel("Time (HH:MM:SS)")
            time_header.setFont(header_font)
            time_header.setAlignment(Qt.AlignCenter)

            grid.addWidget(QLabel(""), 0, 0)
            grid.addWidget(date_header, 0, 1)
            grid.addWidget(time_header, 0, 2)

            # --- Start row ---
            start_label = QLabel("Start:")
            start_label.setFont(header_font)
            grid.addWidget(start_label, 1, 0)

            # Force C locale to prevent system-locale date input issues (MM/DD vs DD/MM)
            from PyQt5.QtCore import QLocale as _QLocale
            c_locale = _QLocale(_QLocale.C)

            self.start_date = QDateEdit()
            self.start_date.setCalendarPopup(True)
            self.start_date.setDisplayFormat("yyyy-MM-dd")
            self.start_date.setLocale(c_locale)
            self.start_date.setDate(QDate.currentDate())
            self.start_date.setEnabled(False)
            grid.addWidget(self.start_date, 1, 1)

            self.start_time = QTimeEdit()
            self.start_time.setDisplayFormat("HH:mm:ss")
            self.start_time.setTime(QTime(0, 0, 0))
            self.start_time.setEnabled(False)
            grid.addWidget(self.start_time, 1, 2)

            # --- End row ---
            end_label = QLabel("End:")
            end_label.setFont(header_font)
            grid.addWidget(end_label, 2, 0)

            self.end_date = QDateEdit()
            self.end_date.setCalendarPopup(True)
            self.end_date.setDisplayFormat("yyyy-MM-dd")
            self.end_date.setLocale(c_locale)
            self.end_date.setDate(QDate.currentDate())
            self.end_date.setEnabled(False)
            grid.addWidget(self.end_date, 2, 1)

            self.end_time = QTimeEdit()
            self.end_time.setDisplayFormat("HH:mm:ss")
            self.end_time.setTime(QTime(23, 59, 59))
            self.end_time.setEnabled(False)
            grid.addWidget(self.end_time, 2, 2)

            group_layout.addLayout(grid)

            # Data range hint label
            self.data_range_label = QLabel()
            self.data_range_label.setStyleSheet(
                "color: #007ACC; font-size: 11px; padding: 2px 5px;"
            )
            self.data_range_label.setWordWrap(True)
            self.data_range_label.hide()
            group_layout.addWidget(self.data_range_label)

            # Preview label
            self.preview_label = QLabel()
            self.preview_label.setStyleSheet(
                "color: #666; font-style: italic; padding: 5px;"
            )
            self.preview_label.setWordWrap(True)
            group_layout.addWidget(self.preview_label)

            layout.addWidget(self.group_box)

        def _connect_signals(self):
            """Connect internal signals."""
            self.enable_check.toggled.connect(self._on_enabled_changed)
            self.tz_combo.currentIndexChanged.connect(self._on_settings_changed)
            self.start_date.dateChanged.connect(self._on_settings_changed)
            self.start_time.timeChanged.connect(self._on_settings_changed)
            self.end_date.dateChanged.connect(self._on_settings_changed)
            self.end_time.timeChanged.connect(self._on_settings_changed)

        def _on_enabled_changed(self, checked: bool):
            """Handle enable checkbox change."""
            self.tz_combo.setEnabled(checked)
            self.start_date.setEnabled(checked)
            self.start_time.setEnabled(checked)
            self.end_date.setEnabled(checked)
            self.end_time.setEnabled(checked)

            self.enabled_changed.emit(checked)
            self._update_preview()
            self._emit_time_range()

        def _on_settings_changed(self):
            """Handle any setting change."""
            self._update_preview()
            self._emit_time_range()

        def _update_preview(self):
            """Update the preview label."""
            if not self.enable_check.isChecked():
                self.preview_label.setText("")
                return

            start_dt = self._combine_start()
            end_dt = self._combine_end()
            tz_name = self.tz_combo.currentText()

            duration = end_dt - start_dt
            hours = duration.total_seconds() / 3600

            if hours < 0:
                self.preview_label.setText(
                    "<span style='color: red;'>Invalid: End time is before start time</span>"
                )
            else:
                self.preview_label.setText(
                    f"Duration: {hours:.2f} hours ({tz_name})"
                )

        def _emit_time_range(self):
            """Emit time_range_changed signal."""
            self.time_range_changed.emit(self.get_time_range())

        def _get_timezone_offset(self) -> float:
            """Get timezone offset in hours."""
            tz_text = self.tz_combo.currentText()
            for name, offset in TIMEZONES:
                if name == tz_text:
                    return offset
            return 0.0

        def _combine_start(self) -> datetime:
            """Combine start date and time widgets into a single datetime."""
            qd = self.start_date.date()
            qt = self.start_time.time()
            return datetime(qd.year(), qd.month(), qd.day(),
                            qt.hour(), qt.minute(), qt.second())

        def _combine_end(self) -> datetime:
            """Combine end date and time widgets into a single datetime."""
            qd = self.end_date.date()
            qt = self.end_time.time()
            return datetime(qd.year(), qd.month(), qd.day(),
                            qt.hour(), qt.minute(), qt.second())

        # === PUBLIC API ===

        def is_enabled(self) -> bool:
            """Check if time range filtering is enabled."""
            return self.enable_check.isChecked()

        def set_enabled(self, enabled: bool):
            """Set enable state."""
            self.enable_check.setChecked(enabled)

        def get_time_range(self) -> Dict[str, Any]:
            """
            Get current time range settings.

            Returns:
                Dictionary with time range settings:
                - enabled: bool
                - start_dt: datetime
                - end_dt: datetime
                - timezone_offset: float (hours)
                - timezone_name: str
            """
            if not self.enable_check.isChecked():
                return {'enabled': False}

            return {
                'enabled': True,
                'start_dt': self._combine_start(),
                'end_dt': self._combine_end(),
                'timezone_offset': self._get_timezone_offset(),
                'timezone_name': self.tz_combo.currentText(),
            }

        def set_time_range(self, time_range: Dict[str, Any]):
            """
            Set time range from dictionary.

            Args:
                time_range: Dictionary with time range settings
            """
            if 'enabled' in time_range:
                self.enable_check.setChecked(time_range['enabled'])

            if 'start_dt' in time_range:
                dt = time_range['start_dt']
                if isinstance(dt, datetime):
                    self.set_start_datetime(dt)

            if 'end_dt' in time_range:
                dt = time_range['end_dt']
                if isinstance(dt, datetime):
                    self.set_end_datetime(dt)

            if 'timezone_name' in time_range:
                index = self.tz_combo.findText(time_range['timezone_name'])
                if index >= 0:
                    self.tz_combo.setCurrentIndex(index)

        def get_start_datetime(self) -> datetime:
            """Get start datetime."""
            return self._combine_start()

        def set_start_datetime(self, dt: datetime):
            """Set start datetime."""
            self.start_date.setDate(QDate(dt.year, dt.month, dt.day))
            self.start_time.setTime(QTime(dt.hour, dt.minute, dt.second))

        def get_end_datetime(self) -> datetime:
            """Get end datetime."""
            return self._combine_end()

        def set_end_datetime(self, dt: datetime):
            """Set end datetime."""
            self.end_date.setDate(QDate(dt.year, dt.month, dt.day))
            self.end_time.setTime(QTime(dt.hour, dt.minute, dt.second))

        def get_timezone_offset(self) -> float:
            """Get timezone offset in hours."""
            return self._get_timezone_offset()

        def set_timezone(self, tz_name: str):
            """Set timezone by name."""
            index = self.tz_combo.findText(tz_name)
            if index >= 0:
                self.tz_combo.setCurrentIndex(index)

        def is_valid(self) -> bool:
            """Check if time range is valid (end > start)."""
            if not self.enable_check.isChecked():
                return True
            return self._combine_end() > self._combine_start()

        def set_from_data_range(self, start_time: float, end_time: float,
                                sampling_rate: float = 100.0):
            """
            Set time range from data time values.

            Args:
                start_time: Start time in seconds
                end_time: End time in seconds
                sampling_rate: Sampling rate (for time reference)
            """
            from datetime import timedelta

            base_dt = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )

            start_dt = base_dt + timedelta(seconds=start_time)
            end_dt = base_dt + timedelta(seconds=end_time)

            self.set_start_datetime(start_dt)
            self.set_end_datetime(end_dt)

            self.data_range_label.setText(
                f"Data range: {start_dt.strftime('%Y-%m-%d %H:%M:%S')} \u2013 "
                f"{end_dt.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            self.data_range_label.show()

        def show_data_range_hint(self, start_dt: datetime, end_dt: datetime):
            """Display detected data time range as an informational hint."""
            self.data_range_label.setText(
                f"Detected data range: {start_dt.strftime('%Y-%m-%d %H:%M:%S')} \u2013 "
                f"{end_dt.strftime('%Y-%m-%d %H:%M:%S')}"
            )
            self.data_range_label.show()

else:
    class TimeRangePanel:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass
