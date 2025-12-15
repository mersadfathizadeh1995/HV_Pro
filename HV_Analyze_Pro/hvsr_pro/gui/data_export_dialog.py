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
        QRadioButton, QButtonGroup
    )
    from PyQt5.QtCore import Qt, pyqtSignal, QThread
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


if HAS_PYQT5:

    class ExportWorker(QThread):
        """Worker thread for export operations."""

        progress = pyqtSignal(int, str)  # progress value, status message
        finished = pyqtSignal(bool, str)  # success, message
        error = pyqtSignal(str)  # error message

        def __init__(self, export_func, files_data, output_dir, options):
            super().__init__()
            self.export_func = export_func
            self.files_data = files_data
            self.output_dir = output_dir
            self.options = options

        def run(self):
            """Run export operation."""
            try:
                total_files = len(self.files_data)
                for i, (file_path, data) in enumerate(self.files_data.items()):
                    filename = Path(file_path).stem
                    self.progress.emit(
                        int((i / total_files) * 100),
                        f"Exporting {filename}..."
                    )

                    # Call export function
                    self.export_func(data, self.output_dir, filename, self.options)

                self.progress.emit(100, "Export complete!")
                self.finished.emit(True, f"Successfully exported {total_files} file(s)")
            except Exception as e:
                self.error.emit(str(e))
                self.finished.emit(False, f"Export failed: {str(e)}")


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
            time_group = QGroupBox("Time Window")
            time_layout = QVBoxLayout()

            self.apply_time_window_cb = QCheckBox("Apply time window filter")
            if self.time_range:
                self.apply_time_window_cb.setChecked(True)
                time_info = f"Start: {self.time_range.get('start', 'N/A')}, End: {self.time_range.get('end', 'N/A')}"
                self.apply_time_window_cb.setText(f"Apply time window filter ({time_info})")
            else:
                self.apply_time_window_cb.setChecked(False)
                self.apply_time_window_cb.setEnabled(False)
                self.apply_time_window_cb.setText("Apply time window filter (no time window set)")

            time_layout.addWidget(self.apply_time_window_cb)

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

            return {
                'format': file_format,
                'apply_time_window': self.apply_time_window_cb.isChecked(),
                'time_range': self.time_range if self.apply_time_window_cb.isChecked() else None,
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
            from hvsr_pro.gui.data_exporters import export_seismic_data

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
                QMessageBox.information(
                    self,
                    "Export Complete",
                    f"{message}\n\nFiles saved to:\n{self.output_dir}"
                )
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
