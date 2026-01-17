"""
Data Export Dialog for HVSR Pro
=================================

Dialog for exporting time-reduced seismic data.

Features:
- Output directory selection
- Format selection (.mat, .mseed, .csv)
- Time window application
- Export mode (individual files vs combined)
- Progress tracking
"""

from pathlib import Path
from typing import Optional, List, Dict

try:
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
        QPushButton, QLabel, QFileDialog, QComboBox,
        QCheckBox, QLineEdit, QProgressBar, QMessageBox,
        QRadioButton, QButtonGroup, QDateTimeEdit
    )
    from PyQt5.QtCore import Qt, pyqtSignal, QThread, QDateTime
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


if HAS_PYQT5:
    # Import worker from workers module
    from hvsr_pro.gui.workers import DataExportWorker as ExportWorker


if HAS_PYQT5:

    class DataExportDialog(QDialog):
        """
        Dialog for exporting reduced/filtered seismic data.

        Features:
        - Select output directory
        - Choose export format (.mat, .mseed, .csv)
        - Apply time window filter
        - Export individual files or combined
        - Progress indicator
        """

        def __init__(self, files_data: Dict, time_range: Optional[Dict] = None, parent=None):
            """
            Initialize export dialog.

            Args:
                files_data: Dict of {file_path: SeismicData} to export
                time_range: Optional dict with 'start' and 'end' for time window
                parent: Parent widget
            """
            super().__init__(parent)
            self.setWindowTitle("Export Reduced Data")
            self.setMinimumWidth(600)
            self.setMinimumHeight(500)

            self.files_data = files_data
            self.time_range = time_range
            self.output_dir = None
            self.export_worker = None

            # Flag to indicate if user wants to reload exported data
            self.should_reload_exported = False
            self.exported_files_info = None

            # Store data start time for time range calculation
            self.data_start_datetime = None
            self.data_duration = None
            self.selected_timezone = 'UTC+0 (GMT)'  # Default timezone

            # Extract data info from first file
            if files_data:
                first_data = list(files_data.values())[0]
                if hasattr(first_data, 'start_time') and first_data.start_time:
                    self.data_start_datetime = first_data.start_time
                    if hasattr(self.data_start_datetime, 'tzinfo') and self.data_start_datetime.tzinfo is not None:
                        self.data_start_datetime = self.data_start_datetime.replace(tzinfo=None)
                if hasattr(first_data, 'duration'):
                    self.data_duration = first_data.duration

            self.init_ui()

        def init_ui(self):
            """Initialize user interface."""
            layout = QVBoxLayout(self)

            # Title
            title = QLabel(f"Export {len(self.files_data)} file(s) with optional time reduction")
            title.setStyleSheet("font-size: 12pt; font-weight: bold; padding: 10px;")
            layout.addWidget(title)

            # === OUTPUT DIRECTORY ===
            output_group = QGroupBox("Output Directory")
            output_layout = QVBoxLayout()

            dir_layout = QHBoxLayout()
            self.output_path_edit = QLineEdit()
            self.output_path_edit.setReadOnly(True)
            self.output_path_edit.setPlaceholderText("Select output directory...")
            dir_layout.addWidget(self.output_path_edit)

            self.browse_btn = QPushButton("Browse...")
            self.browse_btn.clicked.connect(self.select_output_directory)
            dir_layout.addWidget(self.browse_btn)

            output_layout.addLayout(dir_layout)
            output_group.setLayout(output_layout)
            layout.addWidget(output_group)

            # === FORMAT SELECTION ===
            format_group = QGroupBox("Export Format")
            format_layout = QVBoxLayout()

            self.format_combo = QComboBox()
            self.format_combo.addItems([
                '.mat (MATLAB format)',
                '.mseed (MiniSEED format)',
                '.csv (Comma-Separated Values)'
            ])
            self.format_combo.setCurrentIndex(0)  # Default to .mat
            self.format_combo.currentIndexChanged.connect(self.on_format_changed)
            format_layout.addWidget(self.format_combo)

            # Format info
            self.format_info = QLabel()
            self.format_info.setWordWrap(True)
            self.format_info.setStyleSheet("color: gray; font-size: 9pt; padding: 5px;")
            self.update_format_info()
            format_layout.addWidget(self.format_info)

            format_group.setLayout(format_layout)
            layout.addWidget(format_group)

            # === TIME WINDOW OPTIONS ===
            time_group = QGroupBox("Time Window Filter")
            time_layout = QVBoxLayout()

            # Enable checkbox
            self.apply_time_window_cb = QCheckBox("Use Custom Time Range (default: export full data)")
            self.apply_time_window_cb.setChecked(bool(self.time_range))
            self.apply_time_window_cb.stateChanged.connect(self.on_time_filter_toggled)
            time_layout.addWidget(self.apply_time_window_cb)

            # Timezone selector (matching preview_canvas.py)
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
            self.timezone_combo.setEnabled(bool(self.time_range))
            self.timezone_combo.setToolTip("Select the timezone for the date/time inputs below.\nTimes will be converted to UTC for processing.")
            tz_layout.addWidget(self.timezone_combo)
            tz_layout.addStretch()
            time_layout.addLayout(tz_layout)

            # Info about timezone
            tz_info = QLabel("Note: Enter times in the selected timezone. They will be converted to UTC for data processing.")
            tz_info.setStyleSheet("color: #FF9800; font-size: 9px; font-style: italic;")
            tz_info.setWordWrap(True)
            time_layout.addWidget(tz_info)

            # DateTime inputs
            datetime_layout = QVBoxLayout()

            # Start datetime
            start_layout = QHBoxLayout()
            start_layout.addWidget(QLabel("Start Time:"))
            self.datetime_start = QDateTimeEdit()
            self.datetime_start.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
            self.datetime_start.setCalendarPopup(True)
            self.datetime_start.setEnabled(bool(self.time_range))
            self.datetime_start.dateTimeChanged.connect(self.on_time_range_changed)
            start_layout.addWidget(self.datetime_start)
            datetime_layout.addLayout(start_layout)

            # End datetime
            end_layout = QHBoxLayout()
            end_layout.addWidget(QLabel("End Time:"))
            self.datetime_end = QDateTimeEdit()
            self.datetime_end.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
            self.datetime_end.setCalendarPopup(True)
            self.datetime_end.setEnabled(bool(self.time_range))
            self.datetime_end.dateTimeChanged.connect(self.on_time_range_changed)
            end_layout.addWidget(self.datetime_end)
            datetime_layout.addLayout(end_layout)

            time_layout.addLayout(datetime_layout)

            # Initialize datetime pickers with data range
            if self.data_start_datetime:
                from PyQt5.QtCore import QDateTime, Qt
                start_qdatetime = QDateTime(self.data_start_datetime)
                start_qdatetime.setTimeSpec(Qt.UTC)

                # Block signals during initialization
                self.datetime_start.blockSignals(True)
                self.datetime_end.blockSignals(True)

                self.datetime_start.setTimeSpec(Qt.UTC)
                self.datetime_start.setDateTime(start_qdatetime)

                if self.data_duration:
                    end_qdatetime = start_qdatetime.addMSecs(int(self.data_duration * 1000))
                else:
                    end_qdatetime = start_qdatetime.addSecs(3600)  # Default 1 hour

                self.datetime_end.setTimeSpec(Qt.UTC)
                self.datetime_end.setDateTime(end_qdatetime)

                # If time_range provided, set those times
                if self.time_range:
                    start_sec = self.time_range.get('start', 0)
                    end_sec = self.time_range.get('end', 0)
                    self.datetime_start.setDateTime(start_qdatetime.addMSecs(int(start_sec * 1000)))
                    self.datetime_end.setDateTime(start_qdatetime.addMSecs(int(end_sec * 1000)))

                self.datetime_start.blockSignals(False)
                self.datetime_end.blockSignals(False)

            # Info label
            self.time_filter_info = QLabel("Using full data range")
            self.time_filter_info.setStyleSheet("color: gray; font-size: 9px;")
            time_layout.addWidget(self.time_filter_info)

            # Update info if time range is set
            if self.time_range:
                self.update_time_filter_info()

            time_group.setLayout(time_layout)
            layout.addWidget(time_group)

            # === EXPORT MODE ===
            mode_group = QGroupBox("Export Mode")
            mode_layout = QVBoxLayout()

            self.export_mode_group = QButtonGroup(self)

            self.individual_rb = QRadioButton("Export each file separately")
            self.individual_rb.setChecked(True)
            self.individual_rb.setToolTip("Create one output file for each input file")
            self.export_mode_group.addButton(self.individual_rb)
            mode_layout.addWidget(self.individual_rb)

            self.combined_rb = QRadioButton("Export as single combined file")
            self.combined_rb.setToolTip("Concatenate all files and export as one")
            self.export_mode_group.addButton(self.combined_rb)
            mode_layout.addWidget(self.combined_rb)

            mode_group.setLayout(mode_layout)
            layout.addWidget(mode_group)

            # === ADDITIONAL OPTIONS ===
            options_group = QGroupBox("Options")
            options_layout = QVBoxLayout()

            self.preserve_sampling_cb = QCheckBox("Preserve original sampling rate")
            self.preserve_sampling_cb.setChecked(True)
            self.preserve_sampling_cb.setToolTip("Keep the original sampling rate (no resampling)")
            options_layout.addWidget(self.preserve_sampling_cb)

            self.include_metadata_cb = QCheckBox("Include metadata in export")
            self.include_metadata_cb.setChecked(True)
            self.include_metadata_cb.setToolTip("Export file metadata along with data")
            options_layout.addWidget(self.include_metadata_cb)

            options_group.setLayout(options_layout)
            layout.addWidget(options_group)

            # === PROGRESS BAR ===
            self.progress_bar = QProgressBar()
            self.progress_bar.setVisible(False)
            layout.addWidget(self.progress_bar)

            self.status_label = QLabel("")
            self.status_label.setStyleSheet("color: gray; font-style: italic;")
            self.status_label.setVisible(False)
            layout.addWidget(self.status_label)

            # === BUTTONS ===
            button_layout = QHBoxLayout()
            button_layout.addStretch()

            self.export_btn = QPushButton("Export")
            self.export_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    padding: 8px 16px;
                    font-weight: bold;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
                QPushButton:disabled {
                    background-color: #cccccc;
                }
            """)
            self.export_btn.clicked.connect(self.start_export)
            button_layout.addWidget(self.export_btn)

            self.cancel_btn = QPushButton("Cancel")
            self.cancel_btn.clicked.connect(self.reject)
            button_layout.addWidget(self.cancel_btn)

            layout.addLayout(button_layout)

        def on_time_filter_toggled(self, state):
            """Handle time filter checkbox toggle."""
            from PyQt5.QtCore import Qt
            enabled = (state == Qt.Checked)

            self.datetime_start.setEnabled(enabled)
            self.datetime_end.setEnabled(enabled)
            self.timezone_combo.setEnabled(enabled)

            if enabled:
                self.update_time_filter_info()
            else:
                self.time_filter_info.setText("Using full data range")
                self.time_filter_info.setStyleSheet("color: gray; font-size: 9px;")

        def on_timezone_changed(self, tz_text):
            """Handle timezone selection change."""
            self.selected_timezone = tz_text
            self.update_time_filter_info()

        def on_time_range_changed(self):
            """Handle time range value changes."""
            if self.apply_time_window_cb.isChecked():
                self.update_time_filter_info()

        def update_time_filter_info(self):
            """Update time filter info label."""
            if not self.apply_time_window_cb.isChecked():
                return

            start_str = self.datetime_start.dateTime().toString("yyyy-MM-dd HH:mm:ss")
            end_str = self.datetime_end.dateTime().toString("yyyy-MM-dd HH:mm:ss")
            tz_name = self.selected_timezone.split('(')[0].strip()

            # Calculate duration
            start_dt = self.datetime_start.dateTime().toPyDateTime()
            end_dt = self.datetime_end.dateTime().toPyDateTime()
            duration_sec = (end_dt - start_dt).total_seconds()
            duration_hr = duration_sec / 3600

            self.time_filter_info.setText(
                f"Range in {tz_name}: {start_str} to {end_str} (Duration: {duration_hr:.2f}h)"
            )
            self.time_filter_info.setStyleSheet("color: green; font-size: 9px;")

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

            # Match UTC+/-N pattern
            match = re.search(r'UTC([+-])(\d+)', tz_text)
            if match:
                sign = 1 if match.group(1) == '+' else -1
                hours = int(match.group(2))
                return sign * hours

            return 0.0  # Default to UTC if parsing fails

        def select_output_directory(self):
            """Open directory selection dialog."""
            directory = QFileDialog.getExistingDirectory(
                self,
                "Select Output Directory",
                "",
                QFileDialog.ShowDirsOnly
            )

            if directory:
                self.output_dir = directory
                self.output_path_edit.setText(directory)

        def on_format_changed(self, index):
            """Handle format selection change."""
            self.update_format_info()

        def update_format_info(self):
            """Update format information label."""
            format_text = self.format_combo.currentText()

            if '.mat' in format_text:
                info = "MATLAB format (.mat) - Compatible with MATLAB and scipy.io.loadmat\n" \
                       "Contains: E, N, Z components, sampling rate, time vector, metadata"
            elif '.mseed' in format_text:
                info = "MiniSEED format (.mseed) - Standard seismological data format\n" \
                       "Compatible with ObsPy and seismological software"
            elif '.csv' in format_text:
                info = "CSV format (.csv) - Human-readable text format\n" \
                       "Contains: time, E, N, Z columns with header"
            else:
                info = ""

            self.format_info.setText(info)

        def get_export_options(self) -> Dict:
            """
            Get export options from UI.

            Returns:
                Dict with export options
            """
            # Determine format
            format_text = self.format_combo.currentText()
            if '.mat' in format_text:
                file_format = 'mat'
            elif '.mseed' in format_text:
                file_format = 'mseed'
            elif '.csv' in format_text:
                file_format = 'csv'
            else:
                file_format = 'mat'

            # Calculate time range from datetime pickers if enabled
            time_range = None
            if self.apply_time_window_cb.isChecked() and self.data_start_datetime:
                from datetime import timedelta

                # Get user input times (in UTC timespec)
                start_dt_from_picker = self.datetime_start.dateTime().toPyDateTime()
                end_dt_from_picker = self.datetime_end.dateTime().toPyDateTime()

                # Get timezone offset
                tz_offset_hours = self._parse_timezone_offset(self.selected_timezone)

                # Convert from selected timezone to UTC
                if tz_offset_hours != 0:
                    tz_offset_delta = timedelta(hours=tz_offset_hours)
                    start_dt_utc = start_dt_from_picker - tz_offset_delta
                    end_dt_utc = end_dt_from_picker - tz_offset_delta
                else:
                    start_dt_utc = start_dt_from_picker
                    end_dt_utc = end_dt_from_picker

                # Handle timezone awareness
                data_start = self.data_start_datetime
                if hasattr(data_start, 'tzinfo') and data_start.tzinfo is not None:
                    # Data is timezone-aware, make UTC times aware too
                    import pytz
                    utc = pytz.UTC
                    if start_dt_utc.tzinfo is None:
                        start_dt_utc = utc.localize(start_dt_utc)
                    if end_dt_utc.tzinfo is None:
                        end_dt_utc = utc.localize(end_dt_utc)
                else:
                    # Data is naive, make UTC times naive
                    if start_dt_utc.tzinfo is not None:
                        start_dt_utc = start_dt_utc.replace(tzinfo=None)
                    if end_dt_utc.tzinfo is not None:
                        end_dt_utc = end_dt_utc.replace(tzinfo=None)

                # Convert to seconds from data start
                time_start_sec = (start_dt_utc - data_start).total_seconds()
                time_end_sec = (end_dt_utc - data_start).total_seconds()

                # Ensure valid range
                time_start_sec = max(0.0, time_start_sec)
                if self.data_duration:
                    time_end_sec = min(self.data_duration, time_end_sec)

                time_range = {
                    'start': time_start_sec,
                    'end': time_end_sec
                }

                # Debug output
                print(f"DEBUG Export Dialog: User entered (in {self.selected_timezone}):")
                print(f"  Start: {start_dt_from_picker}")
                print(f"  End: {end_dt_from_picker}")
                print(f"DEBUG: Converted to UTC:")
                print(f"  Start: {start_dt_utc}")
                print(f"  End: {end_dt_utc}")
                print(f"DEBUG: Seconds from data start:")
                print(f"  time_start: {time_start_sec}s ({time_start_sec/3600:.2f}h)")
                print(f"  time_end: {time_end_sec}s ({time_end_sec/3600:.2f}h)")

            return {
                'format': file_format,
                'apply_time_window': self.apply_time_window_cb.isChecked(),
                'time_range': time_range,
                'combined': self.combined_rb.isChecked(),
                'preserve_sampling': self.preserve_sampling_cb.isChecked(),
                'include_metadata': self.include_metadata_cb.isChecked()
            }

        def start_export(self):
            """Start export process."""
            # Validate output directory
            if not self.output_dir:
                QMessageBox.warning(
                    self,
                    "No Output Directory",
                    "Please select an output directory first."
                )
                return

            # Get export options
            options = self.get_export_options()

            # Show progress
            self.progress_bar.setVisible(True)
            self.status_label.setVisible(True)
            self.export_btn.setEnabled(False)
            self.browse_btn.setEnabled(False)

            # Import export function
            from hvsr_pro.gui.utils import export_seismic_data

            # Create worker thread
            self.export_worker = ExportWorker(
                export_seismic_data,
                self.files_data,
                self.output_dir,
                options
            )
            self.export_worker.progress.connect(self.on_export_progress)
            self.export_worker.finished.connect(self.on_export_finished)
            self.export_worker.error.connect(self.on_export_error)
            self.export_worker.start()

        def on_export_progress(self, value: int, message: str):
            """Handle export progress update."""
            self.progress_bar.setValue(value)
            self.status_label.setText(message)

        def on_export_finished(self, success: bool, message: str):
            """Handle export completion."""
            self.progress_bar.setVisible(False)
            self.status_label.setVisible(False)
            self.export_btn.setEnabled(True)
            self.browse_btn.setEnabled(True)

            if success:
                # Ask user if they want to reload the exported data into preview
                reply = QMessageBox.question(
                    self,
                    "Export Complete",
                    f"{message}\n\nFiles saved to:\n{self.output_dir}\n\n"
                    "Would you like to load the exported (time-reduced) data back into the preview?\n\n"
                    "This will show you exactly what was exported and allow you to verify the data.",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes  # Default to Yes
                )

                if reply == QMessageBox.Yes:
                    # Store flag to reload data
                    self.should_reload_exported = True
                    # Store the export directory for reloading
                    self.exported_files_info = {
                        'output_dir': self.output_dir,
                        'format': self.get_export_options()['format'],
                        'file_count': len(self.files_data)
                    }

                self.accept()
            else:
                QMessageBox.critical(
                    self,
                    "Export Failed",
                    message
                )

        def on_export_error(self, error_msg: str):
            """Handle export error."""
            QMessageBox.critical(
                self,
                "Export Error",
                f"An error occurred during export:\n\n{error_msg}"
            )


else:
    # Dummy class when PyQt5 not available
    class DataExportDialog:
        def __init__(self, *args, **kwargs):
            raise ImportError("PyQt5 is required for GUI functionality")
