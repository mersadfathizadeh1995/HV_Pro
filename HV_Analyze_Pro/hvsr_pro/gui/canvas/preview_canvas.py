"""
Preview Canvas for HVSR Pro
============================

Dockable/detachable canvas for previewing seismic data before processing.

Features:
- Component signal display (E, N, Z)
- Spectrograms
- Time series plots
- Can be detached into separate window
"""

import numpy as np
from typing import Optional

try:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
        QRadioButton, QPushButton, QButtonGroup, QMainWindow,
        QCheckBox, QLabel, QDoubleSpinBox, QDateTimeEdit, QComboBox
    )
    from PyQt5.QtCore import Qt, pyqtSignal, QDateTime, QDate, QTime
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_qt5agg import (
        FigureCanvasQTAgg as FigureCanvas,
        NavigationToolbar2QT
    )
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


if HAS_PYQT5:

    class PreviewCanvas(QWidget):
        """
        Preview canvas widget for displaying seismic data.

        Supports multiple view modes:
        - E, N, Z component signals
        - Spectrograms
        - Time series

        Can be detached into separate window.
        """

        # Signals
        detached = pyqtSignal()
        attached = pyqtSignal()
        time_range_applied = pyqtSignal(dict)  # Emitted when user applies time filter

        def __init__(self, parent=None):
            super().__init__(parent)

            # Data storage
            self.seismic_data = None
            self.current_view = 'E'  # Default view

            # Time filtering
            self.time_filter_enabled = False
            self.time_start = 0.0
            self.time_end = None  # None means end of data
            self.data_start_datetime = None  # Store actual datetime from data
            self.selected_timezone = 'UTC+0 (GMT)'  # Default timezone for input interpretation
            self._current_tz_offset = 0.0  # Current timezone offset of displayed times (hours)

            # Detached window reference
            self.detached_window = None
            self.is_detached = False

            # Store icons for later use
            from PyQt5.QtWidgets import QApplication, QStyle
            style = QApplication.style()
            self.detach_icon = style.standardIcon(QStyle.SP_TitleBarMaxButton)
            self.attach_icon = style.standardIcon(QStyle.SP_TitleBarNormalButton)

            # Create UI
            self.init_ui()

        def init_ui(self):
            """Initialize user interface."""
            layout = QVBoxLayout(self)

            # Matplotlib figure and canvas
            self.fig = Figure(figsize=(10, 6), dpi=100)
            self.canvas = FigureCanvas(self.fig)
            self.ax = self.fig.add_subplot(111)

            # Navigation toolbar
            self.toolbar = NavigationToolbar2QT(self.canvas, self)

            # Add detach/attach button to toolbar with proper icon
            self.detach_action = self.toolbar.addAction(self.detach_icon, "Detach")
            self.detach_action.setToolTip("Detach preview to separate window")
            self.detach_action.triggered.connect(self.toggle_detach)

            layout.addWidget(self.toolbar)

            # Canvas
            layout.addWidget(self.canvas)

            # Enable context menu for canvas
            self.canvas.setContextMenuPolicy(Qt.CustomContextMenu)
            self.canvas.customContextMenuRequested.connect(self.show_context_menu)

            # Preview options group
            options_group = QGroupBox("Preview Options")
            options_layout = QHBoxLayout()

            # Radio buttons for view modes
            self.button_group = QButtonGroup(self)

            self.radio_e = QRadioButton("E Component")
            self.radio_e.setChecked(True)
            self.radio_e.toggled.connect(lambda checked: checked and self.show_component_signal('E'))
            self.button_group.addButton(self.radio_e)
            options_layout.addWidget(self.radio_e)

            self.radio_n = QRadioButton("N Component")
            self.radio_n.toggled.connect(lambda checked: checked and self.show_component_signal('N'))
            self.button_group.addButton(self.radio_n)
            options_layout.addWidget(self.radio_n)

            self.radio_z = QRadioButton("Z Component")
            self.radio_z.toggled.connect(lambda checked: checked and self.show_component_signal('Z'))
            self.button_group.addButton(self.radio_z)
            options_layout.addWidget(self.radio_z)

            self.radio_spec = QRadioButton("Spectrogram")
            self.radio_spec.toggled.connect(lambda checked: checked and self.show_spectrogram())
            self.button_group.addButton(self.radio_spec)
            options_layout.addWidget(self.radio_spec)

            self.radio_time = QRadioButton("Time Series (All)")
            self.radio_time.toggled.connect(lambda checked: checked and self.show_timeseries())
            self.button_group.addButton(self.radio_time)
            options_layout.addWidget(self.radio_time)

            options_layout.addStretch()

            options_group.setLayout(options_layout)
            layout.addWidget(options_group)

            # Time filtering controls
            time_filter_group = QGroupBox("Time Range Filter")
            time_filter_layout = QVBoxLayout()

            # Enable checkbox - default to checked
            self.time_filter_checkbox = QCheckBox("Use Custom Time Range (default: use full data range)")
            self.time_filter_checkbox.setChecked(False)
            self.time_filter_checkbox.stateChanged.connect(self.on_time_filter_toggled)
            time_filter_layout.addWidget(self.time_filter_checkbox)

            # Timezone selector (matching data_input_dialog.py format)
            tz_layout = QHBoxLayout()
            tz_layout.addWidget(QLabel("Timezone:"))
            self.timezone_combo = QComboBox()
            self.timezone_combo.addItems([
                "UTC-12", "UTC-11", "UTC-10", "UTC-9", "UTC-8",
                "UTC-7 (MST)", "UTC-6 (CST)", "UTC-5 (CDT/EST)", "UTC-4 (EDT)",
                "UTC-3", "UTC-2", "UTC-1", "UTC+0 (GMT)",
                "UTC+1", "UTC+2", "UTC+3", "UTC+4", "UTC+5", "UTC+6",
                "UTC+7", "UTC+8", "UTC+9", "UTC+10", "UTC+11", "UTC+12"
            ])
            self.timezone_combo.setCurrentText("UTC+0 (GMT)")
            self.timezone_combo.currentTextChanged.connect(self.on_timezone_changed)
            self.timezone_combo.setToolTip("Select the timezone for the date/time inputs below.\nTimes will be converted to UTC for processing.")
            tz_layout.addWidget(self.timezone_combo)
            tz_layout.addStretch()
            time_filter_layout.addLayout(tz_layout)

            # Info about timezone
            tz_info = QLabel("Note: Enter times in the selected timezone. They will be converted to UTC for data processing.")
            tz_info.setStyleSheet("color: #FF9800; font-size: 9px; font-style: italic;")
            tz_info.setWordWrap(True)
            time_filter_layout.addWidget(tz_info)

            # DateTime inputs
            datetime_layout = QVBoxLayout()

            # Start datetime
            start_layout = QHBoxLayout()
            start_layout.addWidget(QLabel("Start Time:"))
            self.datetime_start = QDateTimeEdit()
            self.datetime_start.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
            self.datetime_start.setCalendarPopup(True)
            self.datetime_start.setEnabled(False)
            # Force C locale to prevent system-locale date input issues (MM/DD vs DD/MM)
            from PyQt5.QtCore import QLocale
            c_locale = QLocale(QLocale.C)
            self.datetime_start.setLocale(c_locale)
            self.datetime_start.dateTimeChanged.connect(self.on_time_range_changed)
            start_layout.addWidget(self.datetime_start)
            datetime_layout.addLayout(start_layout)

            # End datetime
            end_layout = QHBoxLayout()
            end_layout.addWidget(QLabel("End Time:"))
            self.datetime_end = QDateTimeEdit()
            self.datetime_end.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
            self.datetime_end.setCalendarPopup(True)
            self.datetime_end.setEnabled(False)
            self.datetime_end.setLocale(c_locale)
            self.datetime_end.dateTimeChanged.connect(self.on_time_range_changed)
            end_layout.addWidget(self.datetime_end)
            datetime_layout.addLayout(end_layout)

            time_filter_layout.addLayout(datetime_layout)

            # Apply button
            button_layout = QHBoxLayout()
            self.apply_time_btn = QPushButton("Apply Time Range")
            self.apply_time_btn.setEnabled(False)
            self.apply_time_btn.clicked.connect(self.apply_time_filter)
            button_layout.addWidget(self.apply_time_btn)
            button_layout.addStretch()
            time_filter_layout.addLayout(button_layout)

            # Info label
            self.time_filter_info = QLabel("Using full data range")
            self.time_filter_info.setStyleSheet("color: gray; font-size: 9px;")
            time_filter_layout.addWidget(self.time_filter_info)

            time_filter_group.setLayout(time_filter_layout)
            layout.addWidget(time_filter_group)
            
            # Show initial empty state
            self.clear_preview()

        def set_data(self, seismic_data, time_range=None):
            """
            Set seismic data for preview.

            Args:
                seismic_data: SeismicData object with E, N, Z components
                time_range: Optional dict with 'start' and 'end' datetime objects or times in seconds
            """
            from datetime import datetime, timedelta

            self.seismic_data = seismic_data

            if seismic_data:
                # Get start datetime from data (if available)
                # IMPORTANT: We assume data timestamps are in UTC
                # Try to get from metadata, otherwise use current time as placeholder
                if hasattr(seismic_data, 'start_time') and seismic_data.start_time:
                    data_start_raw = seismic_data.start_time
                elif hasattr(seismic_data, 'metadata') and 'start_time' in seismic_data.metadata:
                    data_start_raw = seismic_data.metadata['start_time']
                else:
                    # Use current date/time as placeholder
                    data_start_raw = datetime.now()

                # Strip timezone info to avoid QDateTime local timezone conversion
                # We'll handle timezone explicitly through the combo box
                if hasattr(data_start_raw, 'tzinfo') and data_start_raw.tzinfo is not None:
                    # Convert to naive datetime (assume UTC)
                    self.data_start_datetime = data_start_raw.replace(tzinfo=None)
                else:
                    self.data_start_datetime = data_start_raw

                # Default to full data range
                self.time_start = 0.0
                self.time_end = seismic_data.duration

                # Reset timezone tracking — data loads as UTC
                self._current_tz_offset = 0.0
                self.timezone_combo.blockSignals(True)
                self.timezone_combo.setCurrentText("UTC+0 (GMT)")
                self.timezone_combo.blockSignals(False)
                self.selected_timezone = 'UTC+0 (GMT)'

                # Convert to QDateTime for the pickers
                # NOTE: Do NOT use setTimeSpec(Qt.UTC) — it causes date corruption on
                # some Windows locales. All timezone math is done manually via _current_tz_offset.
                dt = self.data_start_datetime
                start_qdatetime = QDateTime(
                    QDate(dt.year, dt.month, dt.day),
                    QTime(dt.hour, dt.minute, dt.second)
                )

                end_dt = dt + timedelta(seconds=seismic_data.duration)
                end_qdatetime = QDateTime(
                    QDate(end_dt.year, end_dt.month, end_dt.day),
                    QTime(end_dt.hour, end_dt.minute, end_dt.second)
                )

                # Set datetime range - block signals to prevent cascade
                self.datetime_start.blockSignals(True)
                self.datetime_end.blockSignals(True)

                self.datetime_start.setDateTime(start_qdatetime)
                self.datetime_end.setDateTime(end_qdatetime)

                self.datetime_start.blockSignals(False)
                self.datetime_end.blockSignals(False)

                # Set time range from provided range if available
                if time_range:
                    if 'start' in time_range and 'end' in time_range:
                        if isinstance(time_range['start'], (datetime,)):
                            s = time_range['start']
                            e = time_range['end']
                            self.datetime_start.setDateTime(QDateTime(
                                QDate(s.year, s.month, s.day),
                                QTime(s.hour, s.minute, s.second)
                            ))
                            self.datetime_end.setDateTime(QDateTime(
                                QDate(e.year, e.month, e.day),
                                QTime(e.hour, e.minute, e.second)
                            ))
                            # Calculate seconds from start
                            self.time_start = (time_range['start'] - self.data_start_datetime).total_seconds()
                            self.time_end = (time_range['end'] - self.data_start_datetime).total_seconds()
                        else:
                            # If seconds provided
                            self.time_start = time_range['start']
                            self.time_end = time_range['end']
                            # Update datetime pickers from seconds
                            s = dt + timedelta(seconds=self.time_start)
                            e = dt + timedelta(seconds=self.time_end)
                            self.datetime_start.setDateTime(QDateTime(
                                QDate(s.year, s.month, s.day),
                                QTime(s.hour, s.minute, s.second)
                            ))
                            self.datetime_end.setDateTime(QDateTime(
                                QDate(e.year, e.month, e.day),
                                QTime(e.hour, e.minute, e.second)
                            ))

                        self.time_filter_enabled = True
                        self.time_filter_checkbox.setChecked(True)

            # Update preview with current view mode
            if self.radio_e.isChecked():
                self.show_component_signal('E')
            elif self.radio_n.isChecked():
                self.show_component_signal('N')
            elif self.radio_z.isChecked():
                self.show_component_signal('Z')
            elif self.radio_spec.isChecked():
                self.show_spectrogram()
            elif self.radio_time.isChecked():
                self.show_timeseries()

        def set_data_from_files(self, data_list, time_range=None):
            """
            Set data from multiple files (concatenated).

            This method concatenates data from multiple SeismicData objects
            and previews them as a single combined dataset.

            Args:
                data_list: List of SeismicData objects to concatenate
                time_range: Optional time range to apply to combined data
            """
            if not data_list:
                return

            # If only one file, use regular set_data
            if len(data_list) == 1:
                self.set_data(data_list[0], time_range)
                return

            # Concatenate multiple files
            combined_data = self.concatenate_seismic_data(data_list)

            # Use existing set_data method
            if combined_data:
                self.set_data(combined_data, time_range)

        def concatenate_seismic_data(self, data_list):
            """
            Concatenate multiple SeismicData objects into one.

            Args:
                data_list: List of SeismicData objects

            Returns:
                Combined SeismicData object or None if concatenation fails
            """
            if not data_list:
                return None

            try:
                # Import SeismicData and ComponentData classes
                from hvsr_pro.core.data_structures import SeismicData, ComponentData

                # Collect components from all files
                e_arrays = []
                n_arrays = []
                z_arrays = []

                # Track metadata
                first_data = data_list[0]
                sampling_rate = first_data.sampling_rate if hasattr(first_data, 'sampling_rate') else None
                start_time = first_data.start_time if hasattr(first_data, 'start_time') else None

                # Concatenate each component
                for data in data_list:
                    # Validate sampling rate consistency
                    if sampling_rate and hasattr(data, 'sampling_rate'):
                        if abs(data.sampling_rate - sampling_rate) > 0.01:
                            # Sampling rates don't match - warn but continue
                            print(f"Warning: Inconsistent sampling rates detected ({sampling_rate} vs {data.sampling_rate})")

                    # Get component data (access as east/north/vertical)
                    e_data = data.east.data if hasattr(data.east, 'data') else data.east
                    n_data = data.north.data if hasattr(data.north, 'data') else data.north
                    z_data = data.vertical.data if hasattr(data.vertical, 'data') else data.vertical

                    e_arrays.append(e_data)
                    n_arrays.append(n_data)
                    z_arrays.append(z_data)

                # Concatenate arrays
                combined_e = np.concatenate(e_arrays)
                combined_n = np.concatenate(n_arrays)
                combined_z = np.concatenate(z_arrays)

                # Create combined SeismicData object
                # Try to create with proper structure
                try:
                    # Create ComponentData objects first
                    east_comp = ComponentData(
                        name='E',
                        data=combined_e,
                        sampling_rate=sampling_rate,
                        start_time=start_time
                    )
                    north_comp = ComponentData(
                        name='N',
                        data=combined_n,
                        sampling_rate=sampling_rate,
                        start_time=start_time
                    )
                    vertical_comp = ComponentData(
                        name='Z',
                        data=combined_z,
                        sampling_rate=sampling_rate,
                        start_time=start_time
                    )

                    # Create SeismicData with ComponentData objects
                    combined = SeismicData(
                        east=east_comp,
                        north=north_comp,
                        vertical=vertical_comp,
                        station_name='COMBINED',
                        metadata={'combined': True, 'n_files': len(data_list)}
                    )
                except Exception as e:
                    # Fallback: create simple object with basic attributes
                    class CombinedSeismicData:
                        def __init__(self, e, n, z, fs, start_time):
                            self.east = type('Component', (), {'data': e, 'sampling_rate': fs})()
                            self.north = type('Component', (), {'data': n, 'sampling_rate': fs})()
                            self.vertical = type('Component', (), {'data': z, 'sampling_rate': fs})()
                            self.sampling_rate = fs
                            self.start_time = start_time
                            self.duration = len(e) / fs if fs else len(e)
                            self.metadata = {'combined': True, 'n_files': len(data_list)}

                    combined = CombinedSeismicData(combined_e, combined_n, combined_z, sampling_rate, start_time)

                return combined

            except Exception as e:
                print(f"Error concatenating seismic data: {str(e)}")
                import traceback
                traceback.print_exc()
                return None

        def on_time_filter_toggled(self, state):
            """Handle time filter checkbox toggle."""
            from PyQt5.QtCore import Qt
            enabled = (state == Qt.Checked)

            self.time_filter_enabled = enabled
            self.datetime_start.setEnabled(enabled)
            self.datetime_end.setEnabled(enabled)
            self.apply_time_btn.setEnabled(enabled)

            if enabled:
                start_str = self.datetime_start.dateTime().toString("yyyy-MM-dd HH:mm:ss")
                end_str = self.datetime_end.dateTime().toString("yyyy-MM-dd HH:mm:ss")
                self.time_filter_info.setText(f"Custom range: {start_str} to {end_str}")
                self.time_filter_info.setStyleSheet("color: green; font-size: 9px;")
            else:
                self.time_filter_info.setText("Using full data range")
                self.time_filter_info.setStyleSheet("color: gray; font-size: 9px;")
                # Reset to full range when disabled
                if self.seismic_data and self.data_start_datetime:
                    self.time_start = 0.0
                    self.time_end = self.seismic_data.duration

            # Refresh plot
            self.apply_time_filter()

        def on_timezone_changed(self, tz_text):
            """Handle timezone selection change — convert displayed times to new timezone."""
            old_offset = self._current_tz_offset
            new_offset = self._parse_timezone_offset(tz_text)
            self.selected_timezone = tz_text

            if self.data_start_datetime is not None:
                # Convert displayed times: old_local → UTC → new_local
                # UTC = displayed - old_offset;  new_local = UTC + new_offset
                from datetime import timedelta
                delta = timedelta(hours=(new_offset - old_offset))

                self.datetime_start.blockSignals(True)
                self.datetime_end.blockSignals(True)

                old_start = self.datetime_start.dateTime()
                old_end = self.datetime_end.dateTime()

                self.datetime_start.setDateTime(old_start.addSecs(int(delta.total_seconds())))
                self.datetime_end.setDateTime(old_end.addSecs(int(delta.total_seconds())))

                self.datetime_start.blockSignals(False)
                self.datetime_end.blockSignals(False)

            self._current_tz_offset = new_offset

            # Update info label
            if self.time_filter_enabled:
                start_str = self.datetime_start.dateTime().toString("yyyy-MM-dd HH:mm:ss")
                end_str = self.datetime_end.dateTime().toString("yyyy-MM-dd HH:mm:ss")
                self.time_filter_info.setText(f"Range in {tz_text}: {start_str} to {end_str}")

        def _parse_timezone_offset(self, tz_text):
            """
            Parse timezone offset from combo box text.

            Args:
                tz_text: Text like 'UTC+0 (GMT)', 'UTC-5 (CDT/EST)', 'UTC+3', etc.

            Returns:
                offset in hours as float (e.g., -5.0 for UTC-5)
            """
            import re

            # Handle UTC+0 or GMT special case
            if 'UTC+0' in tz_text or '(GMT)' in tz_text:
                return 0.0

            # Match UTC+/-N pattern (e.g., "UTC-5 (CDT/EST)", "UTC+3", "UTC-12")
            match = re.search(r'UTC([+-])(\d+)', tz_text)
            if match:
                sign = 1 if match.group(1) == '+' else -1
                hours = int(match.group(2))
                return sign * hours

            return 0.0  # Default to UTC if parsing fails

        def on_time_range_changed(self):
            """Handle time range value changes."""
            # Update info label with new range
            if self.time_filter_enabled:
                start_str = self.datetime_start.dateTime().toString("yyyy-MM-dd HH:mm:ss")
                end_str = self.datetime_end.dateTime().toString("yyyy-MM-dd HH:mm:ss")
                tz_name = self.selected_timezone.split('(')[0].strip()
                self.time_filter_info.setText(f"Range in {tz_name}: {start_str} to {end_str}")

        def apply_time_filter(self):
            """Apply time filter and refresh plot."""
            if self.time_filter_enabled and self.data_start_datetime:
                from datetime import timedelta

                # Get user input times from datetime pickers
                # These are in the currently selected timezone (may be UTC or local)
                qdt_start = self.datetime_start.dateTime()
                qdt_end = self.datetime_end.dateTime()
                
                # Extract via QDateTime methods to avoid any toPyDateTime() locale issues
                start_dt_from_picker = datetime(
                    qdt_start.date().year(), qdt_start.date().month(), qdt_start.date().day(),
                    qdt_start.time().hour(), qdt_start.time().minute(), qdt_start.time().second()
                )
                end_dt_from_picker = datetime(
                    qdt_end.date().year(), qdt_end.date().month(), qdt_end.date().day(),
                    qdt_end.time().hour(), qdt_end.time().minute(), qdt_end.time().second()
                )

                # Debug: show exactly what we read from the pickers
                print(f"[TimeFilter] QDateTime start: {qdt_start.toString('yyyy-MM-dd HH:mm:ss')} "
                      f"(y={qdt_start.date().year()}, m={qdt_start.date().month()}, d={qdt_start.date().day()})")
                print(f"[TimeFilter] Python start:    {start_dt_from_picker}")

                # Validate time range BEFORE any conversion
                if end_dt_from_picker <= start_dt_from_picker:
                    self.time_filter_info.setText("ERROR: End time must be after start time!")
                    self.time_filter_info.setStyleSheet("color: red; font-size: 9px; font-weight: bold;")
                    if self.seismic_data:
                        self.time_start = 0.0
                        self.time_end = self.seismic_data.duration
                    return

                # Get timezone offset in hours
                tz_offset_hours = self._parse_timezone_offset(self.selected_timezone)

                # If user selected a non-UTC timezone, they want to ENTER times in that timezone
                # So we need to convert FROM that timezone TO UTC
                if tz_offset_hours != 0:
                    # User entered time in selected timezone (e.g., CDT = UTC-5)
                    # To convert to UTC, we subtract the offset
                    # For UTC-5: UTC = Local - (-5) = Local + 5
                    # For UTC+3: UTC = Local - (+3) = Local - 3
                    tz_offset_delta = timedelta(hours=tz_offset_hours)
                    start_dt_utc = start_dt_from_picker - tz_offset_delta
                    end_dt_utc = end_dt_from_picker - tz_offset_delta
                else:
                    # Already in UTC
                    start_dt_utc = start_dt_from_picker
                    end_dt_utc = end_dt_from_picker

                # Assume data_start_datetime is in UTC (or naive)
                # If data_start_datetime is timezone-aware, handle accordingly
                data_start = self.data_start_datetime
                if hasattr(data_start, 'tzinfo') and data_start.tzinfo is not None:
                    # Data start is timezone-aware
                    # Make sure our UTC times are also timezone-aware for comparison
                    import pytz
                    utc = pytz.UTC
                    if start_dt_utc.tzinfo is None:
                        start_dt_utc = utc.localize(start_dt_utc)
                    if end_dt_utc.tzinfo is None:
                        end_dt_utc = utc.localize(end_dt_utc)
                else:
                    # Data start is naive - treat both as naive
                    if start_dt_utc.tzinfo is not None:
                        start_dt_utc = start_dt_utc.replace(tzinfo=None)
                    if end_dt_utc.tzinfo is not None:
                        end_dt_utc = end_dt_utc.replace(tzinfo=None)

                # Convert to seconds from data start
                self.time_start = (start_dt_utc - data_start).total_seconds()
                self.time_end = (end_dt_utc - data_start).total_seconds()

                # Debug: print conversion for diagnosis
                print(f"[TimeFilter] TZ offset: {tz_offset_hours}h, UTC: {start_dt_utc} to {end_dt_utc}")
                print(f"[TimeFilter] Data start (UTC): {data_start}")
                print(f"[TimeFilter] Seconds from start: {self.time_start:.1f} to {self.time_end:.1f}")

                # Ensure valid range (clamp to data bounds)
                if self.seismic_data:
                    self.time_start = max(0.0, self.time_start)
                    self.time_end = min(self.seismic_data.duration, self.time_end)
                    
                    # Additional validation: ensure we have a positive range after clamping
                    if self.time_end <= self.time_start:
                        self.time_filter_info.setText(
                            f"ERROR: Time range outside data bounds! "
                            f"(UTC: {start_dt_utc.strftime('%Y-%m-%d %H:%M')} to {end_dt_utc.strftime('%H:%M')}, "
                            f"data: {data_start.strftime('%Y-%m-%d %H:%M')})"
                        )
                        self.time_filter_info.setStyleSheet("color: red; font-size: 9px; font-weight: bold;")
                        self.time_start = 0.0
                        self.time_end = self.seismic_data.duration
                        return

                # Calculate duration and update info label with success feedback
                duration_seconds = self.time_end - self.time_start
                duration_str = f"{duration_seconds:.1f}s" if duration_seconds < 60 else f"{duration_seconds/60:.1f}min"
                tz_name = self.selected_timezone.split('(')[0].strip()
                self.time_filter_info.setText(f"Applied: {start_dt_from_picker.strftime('%H:%M:%S')} to {end_dt_from_picker.strftime('%H:%M:%S')} ({tz_name}) - {duration_str}")
                self.time_filter_info.setStyleSheet("color: green; font-size: 9px; font-weight: bold;")

                # Emit signal so main_window can update current_time_range for processing
                # The displayed times are in the selected timezone (local), which is
                # what processing_worker expects as 'start'/'end' (local times)
                self.time_range_applied.emit({
                    'enabled': True,
                    'start': start_dt_from_picker,
                    'end': end_dt_from_picker,
                    'timezone_offset': tz_offset_hours,
                    'timezone_name': self.selected_timezone,
                })

            # Refresh current view
            if self.radio_e.isChecked():
                self.show_component_signal('E')
            elif self.radio_n.isChecked():
                self.show_component_signal('N')
            elif self.radio_z.isChecked():
                self.show_component_signal('Z')
            elif self.radio_spec.isChecked():
                self.show_spectrogram()
            elif self.radio_time.isChecked():
                self.show_timeseries()

        def get_time_range(self):
            """
            Get current time range settings.

            Returns:
                dict with 'start' and 'end' in seconds, or None if filter not enabled
            """
            if self.time_filter_enabled and self.seismic_data:
                return {
                    'start': self.time_start,
                    'end': self.time_end
                }
            return None

        def _get_time_slice(self, time_vector, data):
            """
            Get time-sliced data based on current filter settings.

            Args:
                time_vector: Original time vector
                data: Original data array

            Returns:
                tuple: (sliced_time, sliced_data)
            """
            if not self.time_filter_enabled:
                return time_vector, data

            # Find indices for time range
            start_idx = np.searchsorted(time_vector, self.time_start)
            end_idx = np.searchsorted(time_vector, self.time_end)

            # Ensure valid range
            start_idx = max(0, start_idx)
            end_idx = min(len(data), end_idx)

            if start_idx >= end_idx:
                return time_vector, data  # Invalid range, return full data

            return time_vector[start_idx:end_idx], data[start_idx:end_idx]

        def show_component_signal(self, component: str):
            """
            Display single component signal with metadata.

            Args:
                component: 'E', 'N', or 'Z'
            """
            if not self.seismic_data:
                self.clear_preview()
                return

            self.current_view = component

            # Get component data
            comp_data = self.seismic_data.get_component(component)
            if not comp_data:
                self.clear_preview()
                return

            # IMPORTANT: Clear figure completely and recreate single subplot
            # This is necessary when switching from multi-subplot views (timeseries)
            self.fig.clear()
            self.ax = self.fig.add_subplot(111)

            time = comp_data.time_vector
            data = comp_data.data

            # Apply time slicing if enabled
            time, data = self._get_time_slice(time, data)

            # Component colors
            colors = {'E': '#d62728', 'N': '#2ca02c', 'Z': '#1f77b4'}
            color = colors.get(component, 'b')

            self.ax.plot(time, data, color=color, linewidth=0.6, alpha=0.9)
            self.ax.set_xlabel('Time (s)', fontsize=10)
            self.ax.set_ylabel(f'Amplitude ({comp_data.units})', fontsize=10)

            # Create comprehensive title with metadata
            duration = time[-1] - time[0] if len(time) > 0 else 0
            title = f'{component} Component Signal'
            if self.time_filter_enabled:
                title += f' (Filtered: {self.time_start:.1f}-{self.time_end:.1f}s)'
            title += f'\nDuration: {duration:.2f} s | '
            title += f'Sampling Rate: {comp_data.sampling_rate:.2f} Hz | '
            title += f'Samples: {len(data):,} | '
            title += f'Range: [{np.min(data):.2e}, {np.max(data):.2e}]'
            self.ax.set_title(title, fontsize=9, pad=10)

            self.ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)

            # Add statistics box
            stats_text = f'Mean: {np.mean(data):.2e}\n'
            stats_text += f'Std: {np.std(data):.2e}\n'
            stats_text += f'RMS: {np.sqrt(np.mean(data**2)):.2e}'
            self.ax.text(0.02, 0.98, stats_text,
                        transform=self.ax.transAxes,
                        verticalalignment='top',
                        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5),
                        fontsize=8)

            try:
                self.fig.tight_layout()
            except ValueError:
                pass  # Ignore tight_layout warnings
            self.canvas.draw()

        def show_spectrogram(self):
            """Display spectrogram of currently selected component."""
            if not self.seismic_data:
                self.clear_preview()
                return

            # Determine which component to show
            if self.radio_e.isChecked() or self.current_view == 'E':
                component = 'E'
            elif self.radio_n.isChecked() or self.current_view == 'N':
                component = 'N'
            elif self.radio_z.isChecked() or self.current_view == 'Z':
                component = 'Z'
            else:
                component = 'E'  # Default

            comp_data = self.seismic_data.get_component(component)
            if not comp_data:
                self.clear_preview()
                return

            # IMPORTANT: Clear figure completely and recreate single subplot
            # This is necessary when switching from multi-subplot views (timeseries)
            self.fig.clear()
            self.ax = self.fig.add_subplot(111)

            # Get data and apply time slicing
            time_vector = comp_data.time_vector
            data = comp_data.data

            # Apply time slicing if enabled
            time_vector, data = self._get_time_slice(time_vector, data)

            # Compute spectrogram
            fs = comp_data.sampling_rate

            # Calculate appropriate NFFT based on sampling rate
            # Use ~1 second windows for better frequency resolution
            nfft = min(2048, int(fs))
            noverlap = int(nfft * 0.75)  # 75% overlap

            # Use matplotlib's specgram
            try:
                spectrum, freqs, times, im = self.ax.specgram(
                    data,
                    Fs=fs,
                    NFFT=nfft,
                    noverlap=noverlap,
                    cmap='viridis',
                    scale='dB',
                    mode='magnitude'
                )

                # Adjust time axis to account for time slicing
                if self.time_filter_enabled and len(time_vector) > 0:
                    times = times + time_vector[0]  # Offset by start time

                self.ax.set_xlabel('Time (s)', fontsize=10)
                self.ax.set_ylabel('Frequency (Hz)', fontsize=10)

                duration = time_vector[-1] - time_vector[0] if len(time_vector) > 0 else 0
                title = f'{component} Component Spectrogram'
                if self.time_filter_enabled:
                    title += f' (Filtered: {self.time_start:.1f}-{self.time_end:.1f}s)'
                title += f'\nSampling Rate: {fs:.2f} Hz | Duration: {duration:.2f} s'
                self.ax.set_title(title, fontsize=9, pad=10)

                # Limit frequency range to 0-50 Hz (typical HVSR range)
                self.ax.set_ylim(0, min(50, fs/2))

                # Add colorbar
                self.fig.colorbar(im, ax=self.ax, label='Magnitude (dB)')

                self.fig.tight_layout()
            except Exception as e:
                self.ax.text(0.5, 0.5, f'Error computing spectrogram:\n{str(e)}',
                           horizontalalignment='center',
                           verticalalignment='center',
                           transform=self.ax.transAxes,
                           fontsize=12, color='red')

            self.canvas.draw()

        def show_timeseries(self):
            """Display all three components as time series (hvsrpy style)."""
            if not self.seismic_data:
                self.clear_preview()
                return

            # Clear figure and create 3 subplots
            self.fig.clear()

            components = ['E', 'N', 'Z']
            colors = {'E': '#d62728', 'N': '#2ca02c', 'Z': '#1f77b4'}
            comp_labels = {'E': 'East', 'N': 'North', 'Z': 'Vertical'}

            # Find normalization factor (like hvsrpy)
            norm_factor = 0.
            for comp in components:
                comp_data = self.seismic_data.get_component(comp)
                if comp_data:
                    c_max = np.max(np.abs(comp_data.data))
                    if c_max > norm_factor:
                        norm_factor = c_max

            axes = []
            for i, comp in enumerate(components):
                if i == 0:
                    ax = self.fig.add_subplot(3, 1, i + 1)
                else:
                    ax = self.fig.add_subplot(3, 1, i + 1, sharex=axes[0])
                axes.append(ax)

                comp_data = self.seismic_data.get_component(comp)

                if comp_data:
                    time = comp_data.time_vector
                    data = comp_data.data

                    # Apply time slicing if enabled
                    time, data = self._get_time_slice(time, data)

                    data = data / norm_factor  # Normalized

                    ax.plot(time, data, color=colors[comp], linewidth=0.6, alpha=0.9)
                    ax.set_ylabel(f'{comp_labels[comp]}\n(Normalized)', fontsize=9)
                    ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
                    ax.axhline(0, color='k', linewidth=0.5, linestyle='-', alpha=0.3)

                    # Set y-limits symmetric
                    ylim = max(abs(ax.get_ylim()[0]), abs(ax.get_ylim()[1]))
                    ax.set_ylim(-ylim, ylim)

                    if i == 0:
                        duration = time[-1] - time[0] if len(time) > 0 else 0
                        title = f'Three-Component Seismic Data (Normalized)'
                        if self.time_filter_enabled:
                            title += f' (Filtered: {self.time_start:.1f}-{self.time_end:.1f}s)'
                        title += f'\nSampling Rate: {comp_data.sampling_rate:.2f} Hz | '
                        title += f'Duration: {duration:.2f} s | '
                        title += f'Samples: {len(data):,}'
                        ax.set_title(title, fontsize=9, pad=10)

                    if i == 2:  # Bottom plot
                        ax.set_xlabel('Time (s)', fontsize=10)
                    else:
                        ax.set_xticklabels([])

            try:
                self.fig.tight_layout(pad=1.0)
            except ValueError:
                pass  # Ignore tight_layout warnings
            self.canvas.draw()

            # Store reference to main axis for future use
            self.ax = axes[0] if axes else None

        def clear_preview(self):
            """Clear preview canvas - show clean empty plot."""
            self.fig.clear()
            self.ax = self.fig.add_subplot(111)
            
            # Clean empty canvas with subtle grid
            self.ax.set_facecolor('white')
            self.ax.grid(True, alpha=0.2, linestyle='-', linewidth=0.5)
            
            self.ax.set_xlim(0, 1)
            self.ax.set_ylim(0, 1)
            self.ax.set_xlabel('Time (s)', fontsize=10, color='#999')
            self.ax.set_ylabel('Amplitude', fontsize=10, color='#999')
            
            try:
                self.fig.tight_layout()
            except ValueError:
                pass  # Ignore tight_layout warnings
            self.canvas.draw()

        def show_context_menu(self, position):
            """Show context menu for preview canvas."""
            from PyQt5.QtWidgets import QMenu, QFileDialog, QMessageBox, QApplication

            menu = QMenu(self)

            # Export figure action
            export_action = menu.addAction("Export Figure...")
            export_action.triggered.connect(self.export_figure)

            # Copy to clipboard action
            copy_action = menu.addAction("Copy to Clipboard")
            copy_action.triggered.connect(self.copy_to_clipboard)

            menu.addSeparator()

            # Grid toggle
            grid_action = menu.addAction("Toggle Grid")
            grid_action.setCheckable(True)
            grid_action.setChecked(True)
            grid_action.triggered.connect(self.toggle_grid)

            # Tight layout toggle
            tight_action = menu.addAction("Tight Layout")
            tight_action.setCheckable(True)
            tight_action.setChecked(True)
            tight_action.triggered.connect(lambda: self.fig.tight_layout())

            menu.addSeparator()

            # Refresh action
            refresh_action = menu.addAction("Refresh Plot")
            refresh_action.triggered.connect(lambda: self.canvas.draw())

            # Show menu
            menu.exec_(self.canvas.mapToGlobal(position))

        def export_figure(self):
            """Export figure to file."""
            from PyQt5.QtWidgets import QFileDialog
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Export Figure",
                "",
                "PNG Image (*.png);;PDF Document (*.pdf);;SVG Vector (*.svg);;All Files (*)"
            )
            if filename:
                try:
                    self.fig.savefig(filename, dpi=300, bbox_inches='tight')
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.information(self, "Export Successful", f"Figure saved to:\n{filename}")
                except Exception as e:
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.critical(self, "Export Failed", f"Failed to export figure:\n{str(e)}")

        def copy_to_clipboard(self):
            """Copy figure to clipboard."""
            try:
                import io
                from PyQt5.QtWidgets import QApplication
                from PyQt5.QtGui import QImage, QPixmap

                # Save figure to bytes buffer
                buf = io.BytesIO()
                self.fig.savefig(buf, format='png', dpi=150)
                buf.seek(0)

                # Load to QImage and copy to clipboard
                img = QImage()
                img.loadFromData(buf.read())
                clipboard = QApplication.clipboard()
                clipboard.setImage(img)

                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.information(self, "Success", "Figure copied to clipboard!")
            except Exception as e:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Copy Failed", f"Failed to copy to clipboard:\n{str(e)}")

        def toggle_grid(self):
            """Toggle grid visibility on all axes."""
            if hasattr(self, 'ax') and self.ax:
                current = self.ax.get_axisbelow()
                self.ax.grid(not current)
                self.canvas.draw()

        def toggle_detach(self):
            """Toggle between attached and detached modes."""
            if self.is_detached:
                self.attach_window()
            else:
                self.detach_window()

        def detach_window(self):
            """Detach preview canvas into separate window."""
            if self.is_detached:
                return

            # Create separate window
            self.detached_window = QMainWindow()
            self.detached_window.setWindowTitle("Preview Canvas - HVSR Pro")
            self.detached_window.resize(1000, 700)

            # Move this widget to the new window
            self.setParent(None)
            self.detached_window.setCentralWidget(self)

            # Show the window
            self.detached_window.show()

            # Update state
            self.is_detached = True

            # Update action safely
            try:
                if hasattr(self, 'detach_action') and self.detach_action is not None:
                    self.detach_action.setIcon(self.attach_icon)
                    self.detach_action.setText("Attach")
                    self.detach_action.setToolTip("Attach preview back to main window")
            except RuntimeError:
                pass  # Action was deleted, ignore

            # Emit signal
            self.detached.emit()

        def attach_window(self):
            """Attach preview canvas back to main window."""
            if not self.is_detached or not self.detached_window:
                return

            # Update state BEFORE closing window
            self.is_detached = False

            # Update action safely BEFORE closing
            try:
                if hasattr(self, 'detach_action') and self.detach_action is not None:
                    self.detach_action.setIcon(self.detach_icon)
                    self.detach_action.setText("Detach")
                    self.detach_action.setToolTip("Detach preview to separate window")
            except RuntimeError:
                pass  # Action was deleted, ignore

            # IMPORTANT: Emit signal BEFORE closing window
            # This allows parent to re-add widget before it's destroyed
            try:
                self.attached.emit()
            except RuntimeError:
                pass  # Widget already deleted

            # Now close detached window
            if self.detached_window:
                self.detached_window.close()
                self.detached_window = None


else:
    # Dummy class when PyQt5 not available
    class PreviewCanvas:
        def __init__(self, *args, **kwargs):
            raise ImportError("PyQt5 is required for GUI functionality")
