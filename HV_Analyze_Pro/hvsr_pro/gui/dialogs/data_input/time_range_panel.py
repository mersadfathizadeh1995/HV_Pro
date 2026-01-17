"""
Time Range Panel
================

Reusable time range selection panel for data input dialogs.
"""

from datetime import datetime
from typing import Dict, Any, Optional

try:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
        QCheckBox, QLabel, QComboBox, QDateTimeEdit
    )
    from PyQt5.QtCore import Qt, pyqtSignal, QDateTime
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


# Common timezones - practical format with standard abbreviations
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
        Reusable time range selection panel.
        
        Features:
        - Enable/disable time filtering
        - Start and end datetime selectors
        - Timezone selection
        - Preview of selected range
        
        Signals:
            time_range_changed: Emitted when any time range setting changes
            enabled_changed: Emitted when enable state changes
        """
        
        # Signals
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
            
            # Main group box
            self.group_box = QGroupBox(self._title)
            group_layout = QVBoxLayout(self.group_box)
            
            # Enable checkbox
            self.enable_check = QCheckBox("Enable time range filter")
            self.enable_check.setToolTip(
                "Filter data to specific time range before processing"
            )
            group_layout.addWidget(self.enable_check)
            
            # Timezone selector
            tz_layout = QHBoxLayout()
            tz_layout.addWidget(QLabel("Timezone:"))
            self.tz_combo = QComboBox()
            for tz_name, _ in TIMEZONES:
                self.tz_combo.addItem(tz_name)
            # Default to CDT/EST which is common for US users
            default_idx = self.tz_combo.findText("UTC-5 (CDT/EST)")
            if default_idx >= 0:
                self.tz_combo.setCurrentIndex(default_idx)
            else:
                # Fallback to GMT
                gmt_idx = self.tz_combo.findText("UTC+0 (GMT)")
                if gmt_idx >= 0:
                    self.tz_combo.setCurrentIndex(gmt_idx)
            self.tz_combo.setEnabled(False)
            tz_layout.addWidget(self.tz_combo)
            group_layout.addLayout(tz_layout)
            
            # Start time
            start_layout = QHBoxLayout()
            start_layout.addWidget(QLabel("Start:"))
            self.start_datetime = QDateTimeEdit()
            self.start_datetime.setCalendarPopup(True)
            self.start_datetime.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
            self.start_datetime.setDateTime(QDateTime.currentDateTime())
            self.start_datetime.setEnabled(False)
            start_layout.addWidget(self.start_datetime)
            group_layout.addLayout(start_layout)
            
            # End time
            end_layout = QHBoxLayout()
            end_layout.addWidget(QLabel("End:"))
            self.end_datetime = QDateTimeEdit()
            self.end_datetime.setCalendarPopup(True)
            self.end_datetime.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
            self.end_datetime.setDateTime(
                QDateTime.currentDateTime().addSecs(3600)  # Default +1 hour
            )
            self.end_datetime.setEnabled(False)
            end_layout.addWidget(self.end_datetime)
            group_layout.addLayout(end_layout)
            
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
            self.start_datetime.dateTimeChanged.connect(self._on_settings_changed)
            self.end_datetime.dateTimeChanged.connect(self._on_settings_changed)
        
        def _on_enabled_changed(self, checked: bool):
            """Handle enable checkbox change."""
            self.tz_combo.setEnabled(checked)
            self.start_datetime.setEnabled(checked)
            self.end_datetime.setEnabled(checked)
            
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
            
            start_dt = self.start_datetime.dateTime().toPyDateTime()
            end_dt = self.end_datetime.dateTime().toPyDateTime()
            tz_name = self.tz_combo.currentText()
            
            duration = end_dt - start_dt
            hours = duration.total_seconds() / 3600
            
            if hours < 0:
                self.preview_label.setText(
                    "<span style='color: red;'>Invalid: End time before start time</span>"
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
                'start_dt': self.start_datetime.dateTime().toPyDateTime(),
                'end_dt': self.end_datetime.dateTime().toPyDateTime(),
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
                    self.start_datetime.setDateTime(
                        QDateTime(dt.year, dt.month, dt.day,
                                 dt.hour, dt.minute, dt.second)
                    )
            
            if 'end_dt' in time_range:
                dt = time_range['end_dt']
                if isinstance(dt, datetime):
                    self.end_datetime.setDateTime(
                        QDateTime(dt.year, dt.month, dt.day,
                                 dt.hour, dt.minute, dt.second)
                    )
            
            if 'timezone_name' in time_range:
                index = self.tz_combo.findText(time_range['timezone_name'])
                if index >= 0:
                    self.tz_combo.setCurrentIndex(index)
        
        def get_start_datetime(self) -> datetime:
            """Get start datetime."""
            return self.start_datetime.dateTime().toPyDateTime()
        
        def set_start_datetime(self, dt: datetime):
            """Set start datetime."""
            self.start_datetime.setDateTime(
                QDateTime(dt.year, dt.month, dt.day,
                         dt.hour, dt.minute, dt.second)
            )
        
        def get_end_datetime(self) -> datetime:
            """Get end datetime."""
            return self.end_datetime.dateTime().toPyDateTime()
        
        def set_end_datetime(self, dt: datetime):
            """Set end datetime."""
            self.end_datetime.setDateTime(
                QDateTime(dt.year, dt.month, dt.day,
                         dt.hour, dt.minute, dt.second)
            )
        
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
            
            start_dt = self.start_datetime.dateTime().toPyDateTime()
            end_dt = self.end_datetime.dateTime().toPyDateTime()
            return end_dt > start_dt
        
        def set_from_data_range(self, start_time: float, end_time: float,
                                sampling_rate: float = 100.0):
            """
            Set time range from data time values.
            
            Args:
                start_time: Start time in seconds
                end_time: End time in seconds  
                sampling_rate: Sampling rate (for time reference)
            """
            # Convert to datetime (assuming epoch reference)
            from datetime import timedelta
            
            base_dt = datetime.now().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            
            start_dt = base_dt + timedelta(seconds=start_time)
            end_dt = base_dt + timedelta(seconds=end_time)
            
            self.set_start_datetime(start_dt)
            self.set_end_datetime(end_dt)

else:
    class TimeRangePanel:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass

