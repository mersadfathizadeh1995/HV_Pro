"""
Enhanced Data Input Dialog for HVSR Pro
========================================

Multi-tab dialog for loading various data formats:
- Single files (ASCII txt, MiniSEED)
- Multiple MiniSEED files (Type 1: 3-channel per file)
- Separate component MiniSEED files (Type 2: E, N, Z separate)
- Automatic pattern matching and file grouping
"""

from pathlib import Path
from typing import List, Dict, Optional, Tuple
import re

try:
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
        QPushButton, QLabel, QLineEdit, QFileDialog, QListWidget,
        QGroupBox, QRadioButton, QCheckBox, QTextEdit, QComboBox,
        QMessageBox, QListWidgetItem, QTableWidget, QTableWidgetItem,
        QHeaderView, QSpinBox, QDoubleSpinBox, QDateTimeEdit
    )
    from PyQt5.QtCore import Qt, pyqtSignal
    from PyQt5.QtGui import QFont, QColor
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


if HAS_PYQT5:
    
    class DataInputDialog(QDialog):
        """
        Enhanced data input dialog with multiple loading modes.
        
        Modes:
        1. Single File - Load one ASCII or MiniSEED file
        2. Multiple MiniSEED (Type 1) - Multiple files with E,N,Z in each
        3. Multiple MiniSEED (Type 2) - Separate E, N, Z files
        4. Advanced - Time range selection, merging options
        """
        
        # Signal emitted with loaded file info
        files_selected = pyqtSignal(dict)  # {'mode': str, 'files': list, 'options': dict}
        
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("Load Seismic Data")
            self.setModal(True)
            self.resize(800, 600)
            
            # Storage
            self.selected_files = []
            self.grouped_files = {}
            self.load_mode = 'single'
            self.type1_all_files = []  # All detected Type 1 files
            self.type2_all_groups = {}  # All detected Type 2 groups
            
            self.init_ui()
            
        def init_ui(self):
            """Initialize user interface."""
            layout = QVBoxLayout(self)
            
            # Title
            title = QLabel("Load Seismic Data")
            title_font = QFont()
            title_font.setPointSize(14)
            title_font.setBold(True)
            title.setFont(title_font)
            title.setAlignment(Qt.AlignCenter)
            layout.addWidget(title)
            
            # Tab widget
            self.tabs = QTabWidget()
            self.tabs.addTab(self.create_single_file_tab(), "Single File")
            self.tabs.addTab(self.create_multi_type1_tab(), "Multi-File (3-channel)")
            self.tabs.addTab(self.create_multi_type2_tab(), "Multi-File (Separate E,N,Z)")
            self.tabs.addTab(self.create_advanced_tab(), "Advanced Options")
            layout.addWidget(self.tabs)
            
            # Preview section
            preview_group = QGroupBox("Preview")
            preview_layout = QVBoxLayout(preview_group)
            self.preview_text = QTextEdit()
            self.preview_text.setReadOnly(True)
            self.preview_text.setMaximumHeight(150)
            preview_layout.addWidget(self.preview_text)
            layout.addWidget(preview_group)
            
            # Buttons
            button_layout = QHBoxLayout()
            button_layout.addStretch()
            
            cancel_btn = QPushButton("Cancel")
            cancel_btn.clicked.connect(self.reject)
            button_layout.addWidget(cancel_btn)
            
            self.load_btn = QPushButton("Load Data")
            self.load_btn.clicked.connect(self.accept_files)
            self.load_btn.setEnabled(False)
            button_layout.addWidget(self.load_btn)
            
            layout.addLayout(button_layout)
        
        def create_single_file_tab(self) -> QWidget:
            """Create single file loading tab."""
            widget = QWidget()
            layout = QVBoxLayout(widget)
            
            # Instructions
            info = QLabel(
                "Load a single ASCII (.txt) or MiniSEED (.mseed) file.\n"
                "Best for: Simple datasets with all components in one file."
            )
            info.setWordWrap(True)
            layout.addWidget(info)
            
            # File selection
            file_group = QGroupBox("File Selection")
            file_layout = QVBoxLayout(file_group)
            
            select_layout = QHBoxLayout()
            self.single_file_path = QLineEdit()
            self.single_file_path.setPlaceholderText("No file selected")
            self.single_file_path.setReadOnly(True)
            select_layout.addWidget(self.single_file_path)
            
            browse_btn = QPushButton("Browse...")
            browse_btn.clicked.connect(self.browse_single_file)
            select_layout.addWidget(browse_btn)
            
            file_layout.addLayout(select_layout)

            # Column mapping checkbox (for CSV/text files) - Make it prominent
            self.use_column_mapping = QCheckBox("✓ Enable Column Mapping (for CSV/text files)")
            self.use_column_mapping.setChecked(False)
            self.use_column_mapping.setStyleSheet("""
                QCheckBox {
                    font-weight: bold;
                    color: #2196F3;
                    padding: 5px;
                    background-color: #E3F2FD;
                    border-radius: 3px;
                }
                QCheckBox:hover {
                    background-color: #BBDEFB;
                }
            """)
            self.use_column_mapping.setToolTip(
                "Enable this for CSV/text files where columns need to be manually mapped.\n"
                "When enabled, you'll be able to specify which column represents E, N, Z, Time, etc.\n\n"
                "Check this BEFORE browsing for CSV/text files."
            )
            file_layout.addWidget(self.use_column_mapping)

            # Info label for column mapping
            mapping_info = QLabel(
                "<i>Note: For custom CSV/text files, check the box above BEFORE browsing to map columns manually.</i>"
            )
            mapping_info.setWordWrap(True)
            mapping_info.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")
            file_layout.addWidget(mapping_info)

            layout.addWidget(file_group)

            # Storage for column mapping
            self.column_mapping = None

            # Time Range Selection (Same as Type 1)
            time_group = QGroupBox("Time Range (Optional)")
            time_layout = QVBoxLayout(time_group)
            
            # Enable checkbox
            self.single_use_time_range = QCheckBox("Extract specific time range only")
            self.single_use_time_range.setChecked(False)
            self.single_use_time_range.stateChanged.connect(self.on_single_time_range_toggled)
            time_layout.addWidget(self.single_use_time_range)
            
            # Start time
            start_layout = QHBoxLayout()
            start_layout.addWidget(QLabel("Start Time:"))
            self.single_start_datetime = QDateTimeEdit()
            self.single_start_datetime.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
            self.single_start_datetime.setCalendarPopup(True)
            self.single_start_datetime.setEnabled(False)
            self.single_start_datetime.dateTimeChanged.connect(self.update_single_time_preview)
            start_layout.addWidget(self.single_start_datetime)
            time_layout.addLayout(start_layout)
            
            # End time
            end_layout = QHBoxLayout()
            end_layout.addWidget(QLabel("End Time:"))
            self.single_end_datetime = QDateTimeEdit()
            self.single_end_datetime.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
            self.single_end_datetime.setCalendarPopup(True)
            self.single_end_datetime.setEnabled(False)
            self.single_end_datetime.dateTimeChanged.connect(self.update_single_time_preview)
            end_layout.addWidget(self.single_end_datetime)
            time_layout.addLayout(end_layout)
            
            # Timezone
            tz_layout = QHBoxLayout()
            tz_layout.addWidget(QLabel("Timezone:"))
            self.single_timezone = QComboBox()
            self.single_timezone.addItems([
                "UTC-12", "UTC-11", "UTC-10", "UTC-9", "UTC-8",
                "UTC-7 (MST)", "UTC-6 (CST)", "UTC-5 (CDT/EST)", "UTC-4 (EDT)",
                "UTC-3", "UTC-2", "UTC-1", "UTC+0 (GMT)",
                "UTC+1", "UTC+2", "UTC+3", "UTC+4", "UTC+5", "UTC+6",
                "UTC+7", "UTC+8", "UTC+9", "UTC+10", "UTC+11", "UTC+12"
            ])
            self.single_timezone.setCurrentText("UTC-5 (CDT/EST)")
            self.single_timezone.setEnabled(False)
            self.single_timezone.currentIndexChanged.connect(self.update_single_time_preview)
            tz_layout.addWidget(self.single_timezone)
            time_layout.addLayout(tz_layout)
            
            # Preview
            self.single_time_preview = QLabel("")
            self.single_time_preview.setWordWrap(True)
            self.single_time_preview.setStyleSheet("QLabel { background-color: #f0f0f0; padding: 5px; }")
            time_layout.addWidget(self.single_time_preview)
            
            layout.addWidget(time_group)
            
            layout.addStretch()
            return widget
        
        def create_multi_type1_tab(self) -> QWidget:
            """Create multi-file Type 1 tab (E,N,Z in each file)."""
            widget = QWidget()
            layout = QVBoxLayout(widget)
            
            # Instructions
            info = QLabel(
                "Load multiple MiniSEED files where each file contains E, N, Z channels.\n"
                "Example: Hourly files from continuous recording.\n"
                "Files will be automatically merged in chronological order."
            )
            info.setWordWrap(True)
            layout.addWidget(info)
            
            # Directory selection
            dir_group = QGroupBox("Directory Selection")
            dir_layout = QVBoxLayout(dir_group)
            
            select_layout = QHBoxLayout()
            self.type1_dir_path = QLineEdit()
            self.type1_dir_path.setPlaceholderText("No directory selected")
            self.type1_dir_path.setReadOnly(True)
            select_layout.addWidget(self.type1_dir_path)
            
            browse_btn = QPushButton("Browse Directory...")
            browse_btn.clicked.connect(self.browse_type1_directory)
            select_layout.addWidget(browse_btn)
            
            dir_layout.addLayout(select_layout)

            # Channel mapping checkbox (for MiniSEED files with multiple channels)
            self.use_channel_mapping_type1 = QCheckBox("✓ Enable Channel Mapping (map channels to E/N/Z)")
            self.use_channel_mapping_type1.setChecked(False)
            self.use_channel_mapping_type1.setStyleSheet("""
                QCheckBox {
                    font-weight: bold;
                    color: #FF9800;
                    padding: 5px;
                    background-color: #FFF3E0;
                    border-radius: 3px;
                }
                QCheckBox:hover {
                    background-color: #FFE0B2;
                }
            """)
            self.use_channel_mapping_type1.setToolTip(
                "Enable this for MiniSEED files where channel codes (HHE, HHN, HHZ, etc.) need to be mapped.\n"
                "When enabled, you'll be able to specify which channels represent E, N, Z components.\n\n"
                "Useful for non-standard channel naming conventions."
            )
            dir_layout.addWidget(self.use_channel_mapping_type1)

            # Info label for channel mapping
            mapping_info_type1 = QLabel(
                "<i>Note: For MiniSEED files with non-standard channel names, check the box above to manually map channels.</i>"
            )
            mapping_info_type1.setWordWrap(True)
            mapping_info_type1.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")
            dir_layout.addWidget(mapping_info_type1)

            layout.addWidget(dir_group)

            # Storage for channel mapping
            self.channel_mapping_type1 = None

            # File list
            files_group = QGroupBox("Detected Files")
            files_layout = QVBoxLayout(files_group)
            
            self.type1_file_list = QListWidget()
            self.type1_file_list.setSelectionMode(QListWidget.MultiSelection)
            files_layout.addWidget(self.type1_file_list)
            
            # Selection buttons
            button_layout = QHBoxLayout()
            select_all_btn = QPushButton("Select All")
            select_all_btn.clicked.connect(lambda: self.type1_file_list.selectAll())
            button_layout.addWidget(select_all_btn)
            
            select_none_btn = QPushButton("Select None")
            select_none_btn.clicked.connect(lambda: self.type1_file_list.clearSelection())
            button_layout.addWidget(select_none_btn)
            files_layout.addLayout(button_layout)
            
            count_label = QLabel("0 files detected | 0 selected")
            self.type1_count_label = count_label
            files_layout.addWidget(count_label)
            
            layout.addWidget(files_group)
            
            # Time Range Selection (PRIMARY FEATURE)
            time_group = QGroupBox("Time Range (Optional)")
            time_layout = QVBoxLayout(time_group)
            
            # Enable checkbox
            self.type1_use_time_range = QCheckBox("Extract specific time range only")
            self.type1_use_time_range.setChecked(False)
            self.type1_use_time_range.stateChanged.connect(self.on_time_range_toggled)
            time_layout.addWidget(self.type1_use_time_range)
            
            # Start time
            start_layout = QHBoxLayout()
            start_layout.addWidget(QLabel("Start Time:"))
            self.type1_start_datetime = QDateTimeEdit()
            self.type1_start_datetime.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
            self.type1_start_datetime.setCalendarPopup(True)
            self.type1_start_datetime.setEnabled(False)
            self.type1_start_datetime.dateTimeChanged.connect(self.update_time_preview)
            start_layout.addWidget(self.type1_start_datetime)
            time_layout.addLayout(start_layout)
            
            # End time
            end_layout = QHBoxLayout()
            end_layout.addWidget(QLabel("End Time:"))
            self.type1_end_datetime = QDateTimeEdit()
            self.type1_end_datetime.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
            self.type1_end_datetime.setCalendarPopup(True)
            self.type1_end_datetime.setEnabled(False)
            self.type1_end_datetime.dateTimeChanged.connect(self.update_time_preview)
            end_layout.addWidget(self.type1_end_datetime)
            time_layout.addLayout(end_layout)
            
            # Timezone
            tz_layout = QHBoxLayout()
            tz_layout.addWidget(QLabel("Timezone:"))
            self.type1_timezone = QComboBox()
            self.type1_timezone.addItems([
                "UTC-12", "UTC-11", "UTC-10", "UTC-9", "UTC-8",
                "UTC-7 (MST)", "UTC-6 (CST)", "UTC-5 (CDT/EST)", "UTC-4 (EDT)",
                "UTC-3", "UTC-2", "UTC-1", "UTC+0 (GMT)",
                "UTC+1", "UTC+2", "UTC+3", "UTC+4", "UTC+5", "UTC+6",
                "UTC+7", "UTC+8", "UTC+9", "UTC+10", "UTC+11", "UTC+12"
            ])
            self.type1_timezone.setCurrentText("UTC-5 (CDT/EST)")  # Default for user's location
            self.type1_timezone.setEnabled(False)
            self.type1_timezone.currentIndexChanged.connect(self.update_time_preview)
            tz_layout.addWidget(self.type1_timezone)
            time_layout.addLayout(tz_layout)
            
            # Preview
            self.type1_time_preview = QLabel("")
            self.type1_time_preview.setWordWrap(True)
            self.type1_time_preview.setStyleSheet("QLabel { background-color: #f0f0f0; padding: 5px; }")
            time_layout.addWidget(self.type1_time_preview)
            
            layout.addWidget(time_group)
            
            return widget
        
        def create_multi_type2_tab(self) -> QWidget:
            """Create multi-file Type 2 tab (separate E, N, Z files)."""
            widget = QWidget()
            layout = QVBoxLayout(widget)
            
            # Instructions
            info = QLabel(
                "Load MiniSEED files where E, N, Z components are in separate files.\n"
                "Example: XX01_pt1_corrected_E.miniseed, XX01_pt1_corrected_N.miniseed, XX01_pt1_corrected_Z.miniseed\n"
                "Files will be automatically grouped by pattern matching."
            )
            info.setWordWrap(True)
            layout.addWidget(info)
            
            # Directory selection
            dir_group = QGroupBox("Directory Selection")
            dir_layout = QVBoxLayout(dir_group)
            
            select_layout = QHBoxLayout()
            self.type2_dir_path = QLineEdit()
            self.type2_dir_path.setPlaceholderText("No directory selected")
            self.type2_dir_path.setReadOnly(True)
            select_layout.addWidget(self.type2_dir_path)
            
            browse_btn = QPushButton("Browse Directory...")
            browse_btn.clicked.connect(self.browse_type2_directory)
            select_layout.addWidget(browse_btn)
            
            dir_layout.addLayout(select_layout)
            layout.addWidget(dir_group)
            
            # Pattern matching
            pattern_group = QGroupBox("Pattern Matching")
            pattern_layout = QVBoxLayout(pattern_group)
            
            pattern_info = QLabel("Detected file groups (E, N, Z):")
            pattern_layout.addWidget(pattern_info)
            
            self.type2_group_list = QListWidget()
            self.type2_group_list.setSelectionMode(QListWidget.MultiSelection)
            pattern_layout.addWidget(self.type2_group_list)
            
            # Selection buttons
            button_layout = QHBoxLayout()
            select_all_btn = QPushButton("Select All")
            select_all_btn.clicked.connect(lambda: self.type2_group_list.selectAll())
            button_layout.addWidget(select_all_btn)
            
            select_none_btn = QPushButton("Select None")
            select_none_btn.clicked.connect(lambda: self.type2_group_list.clearSelection())
            button_layout.addWidget(select_none_btn)
            pattern_layout.addLayout(button_layout)
            
            count_label = QLabel("0 groups detected | 0 selected")
            self.type2_count_label = count_label
            pattern_layout.addWidget(count_label)
            
            layout.addWidget(pattern_group)
            
            # Time Range Selection (Same as Type 1)
            time_group = QGroupBox("Time Range (Optional)")
            time_layout = QVBoxLayout(time_group)
            
            # Enable checkbox
            self.type2_use_time_range = QCheckBox("Extract specific time range only")
            self.type2_use_time_range.setChecked(False)
            self.type2_use_time_range.stateChanged.connect(self.on_type2_time_range_toggled)
            time_layout.addWidget(self.type2_use_time_range)
            
            # Start time
            start_layout = QHBoxLayout()
            start_layout.addWidget(QLabel("Start Time:"))
            self.type2_start_datetime = QDateTimeEdit()
            self.type2_start_datetime.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
            self.type2_start_datetime.setCalendarPopup(True)
            self.type2_start_datetime.setEnabled(False)
            self.type2_start_datetime.dateTimeChanged.connect(self.update_type2_time_preview)
            start_layout.addWidget(self.type2_start_datetime)
            time_layout.addLayout(start_layout)
            
            # End time
            end_layout = QHBoxLayout()
            end_layout.addWidget(QLabel("End Time:"))
            self.type2_end_datetime = QDateTimeEdit()
            self.type2_end_datetime.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
            self.type2_end_datetime.setCalendarPopup(True)
            self.type2_end_datetime.setEnabled(False)
            self.type2_end_datetime.dateTimeChanged.connect(self.update_type2_time_preview)
            end_layout.addWidget(self.type2_end_datetime)
            time_layout.addLayout(end_layout)
            
            # Timezone
            tz_layout = QHBoxLayout()
            tz_layout.addWidget(QLabel("Timezone:"))
            self.type2_timezone = QComboBox()
            self.type2_timezone.addItems([
                "UTC-12", "UTC-11", "UTC-10", "UTC-9", "UTC-8",
                "UTC-7 (MST)", "UTC-6 (CST)", "UTC-5 (CDT/EST)", "UTC-4 (EDT)",
                "UTC-3", "UTC-2", "UTC-1", "UTC+0 (GMT)",
                "UTC+1", "UTC+2", "UTC+3", "UTC+4", "UTC+5", "UTC+6",
                "UTC+7", "UTC+8", "UTC+9", "UTC+10", "UTC+11", "UTC+12"
            ])
            self.type2_timezone.setCurrentText("UTC-5 (CDT/EST)")
            self.type2_timezone.setEnabled(False)
            self.type2_timezone.currentIndexChanged.connect(self.update_type2_time_preview)
            tz_layout.addWidget(self.type2_timezone)
            time_layout.addLayout(tz_layout)
            
            # Preview
            self.type2_time_preview = QLabel("")
            self.type2_time_preview.setWordWrap(True)
            self.type2_time_preview.setStyleSheet("QLabel { background-color: #f0f0f0; padding: 5px; }")
            time_layout.addWidget(self.type2_time_preview)
            
            layout.addWidget(time_group)
            
            return widget
        
        def create_advanced_tab(self) -> QWidget:
            """Create advanced options tab."""
            widget = QWidget()
            layout = QVBoxLayout(widget)
            
            # Info about time range
            info_group = QGroupBox("Time Range Selection")
            info_layout = QVBoxLayout(info_group)
            
            info_label = QLabel(
                "Time range selection is now available in each tab:\n\n"
                "• Single File tab - Extract time slice from single file\n"
                "• Multi-File Type 1 tab - Extract time slice from merged files\n"
                "• Multi-File Type 2 tab - Extract time slice from grouped files\n\n"
                "Switch to the appropriate tab to use this feature."
            )
            info_label.setWordWrap(True)
            info_layout.addWidget(info_label)
            
            layout.addWidget(info_group)
            
            # Merge options
            merge_group = QGroupBox("Merging Options")
            merge_layout = QVBoxLayout(merge_group)
            
            self.merge_continuous = QCheckBox("Merge continuous segments")
            self.merge_continuous.setChecked(True)
            merge_layout.addWidget(self.merge_continuous)
            
            self.verify_sampling_rate = QCheckBox("Verify consistent sampling rate")
            self.verify_sampling_rate.setChecked(True)
            merge_layout.addWidget(self.verify_sampling_rate)
            
            layout.addWidget(merge_group)
            
            layout.addStretch()
            return widget
        
        def browse_single_file(self):
            """Browse for single file."""
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select Seismic Data File",
                "",
                "Data Files (*.txt *.csv *.mseed *.miniseed);;Text/CSV (*.txt *.csv);;MiniSEED (*.mseed *.miniseed);;All Files (*)"
            )

            if not file_path:
                return

            self.single_file_path.setText(file_path)
            self.selected_files = [file_path]
            self.load_mode = 'single'

            # If column mapping is enabled and file is CSV/text, show mapper
            from pathlib import Path
            file_ext = Path(file_path).suffix.lower()

            if self.use_column_mapping.isChecked() and file_ext in ['.txt', '.csv', '.dat', '.asc']:
                self._show_column_mapper(file_path)
            else:
                # For non-CSV or when mapping disabled, just enable load button
                self.load_btn.setEnabled(True)
                self.preview_text.setPlainText(f"File selected: {Path(file_path).name}\n\nReady to load.")

        def _show_column_mapper(self, file_path: str):
            """Show column mapping dialog for CSV/text file."""
            try:
                import numpy as np
                from pathlib import Path
                from hvsr_pro.gui.column_mapper_dialog import SeismicColumnMapperDialog

                # Read file and detect encoding
                columns_data = []
                column_headers = None

                # Try different encodings
                encodings_to_try = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']

                for encoding in encodings_to_try:
                    try:
                        # Read the file to detect structure
                        with open(file_path, 'r', encoding=encoding) as f:
                            lines = f.readlines()

                        # Find where numeric data starts
                        data_start_row = None
                        header_row = None

                        for i, line in enumerate(lines[:20]):  # Check first 20 lines
                            # Try to parse as numbers
                            parts = line.strip().split()
                            if not parts:
                                continue

                            # Check if this line is ALL numeric (all parts can be converted to float)
                            numeric_count = 0
                            for part in parts:
                                try:
                                    float(part)
                                    numeric_count += 1
                                except:
                                    pass

                            # If ALL parts are numeric, this is likely data
                            # Require at least 2 columns and 100% numeric
                            if len(parts) >= 2 and numeric_count == len(parts):
                                data_start_row = i
                                # Check if previous line might be headers
                                if i > 0:
                                    prev_line = lines[i-1].strip().split()
                                    # Check if previous line has non-numeric text (likely headers)
                                    has_text = False
                                    for part in prev_line:
                                        try:
                                            float(part)
                                        except:
                                            has_text = True
                                            break
                                    if has_text and len(prev_line) == len(parts):
                                        header_row = i - 1
                                        column_headers = prev_line
                                break

                        if data_start_row is None:
                            continue  # Try next encoding

                        # Parse numeric data from the lines we already read
                        try:
                            # Extract numeric rows starting from data_start_row
                            numeric_rows = []
                            for line in lines[data_start_row:]:
                                parts = line.strip().split()
                                if not parts:
                                    continue

                                # Try to convert all parts to float
                                try:
                                    row = [float(p) for p in parts]
                                    numeric_rows.append(row)
                                except ValueError:
                                    # Stop at first non-numeric row
                                    break

                            if not numeric_rows:
                                continue  # Try next encoding

                            # Convert to numpy array
                            data = np.array(numeric_rows)

                            if data.ndim == 1:
                                # Single row - reshape
                                data = data.reshape(1, -1)

                            # Split into columns
                            columns_data = [data[:, i] for i in range(data.shape[1])]

                            if len(columns_data) > 0:
                                # Success! Exit encoding loop
                                break
                        except Exception as e:
                            print(f"Failed to parse with encoding {encoding}: {e}")
                            continue

                    except Exception as e:
                        print(f"Encoding {encoding} outer exception: {e}")
                        continue

                # If manual parsing approach failed, try pandas
                if not columns_data:
                    try:
                        import pandas as pd

                        for encoding in encodings_to_try:
                            try:
                                # Read with pandas, trying different delimiters
                                df = pd.read_csv(
                                    file_path,
                                    delim_whitespace=True,
                                    header=None,
                                    comment='#',
                                    encoding=encoding,
                                    skip_blank_lines=True
                                )

                                # Find first row with all numeric data
                                for start_row in range(min(20, len(df))):
                                    try:
                                        test_df = df.iloc[start_row:].apply(pd.to_numeric, errors='coerce')
                                        # Check if at least 80% of values are numeric
                                        if test_df.notna().sum().sum() > (test_df.size * 0.8):
                                            # Check if previous row could be headers
                                            if start_row > 0:
                                                header_candidates = df.iloc[start_row - 1].tolist()
                                                # Check if they're text (not all numeric)
                                                non_numeric = sum(1 for x in header_candidates if pd.isna(pd.to_numeric(x, errors='coerce')))
                                                if non_numeric > 0:
                                                    column_headers = [str(x) for x in header_candidates]

                                            df = test_df.dropna(how='all')
                                            columns_data = [df.iloc[:, i].values for i in range(len(df.columns))]
                                            break
                                    except:
                                        continue

                                if columns_data:
                                    break
                            except:
                                continue

                    except ImportError:
                        pass  # Pandas not available

                if not columns_data:
                    raise ValueError(
                        "Could not read file. The file may have:\n"
                        "- Non-numeric headers that couldn't be skipped\n"
                        "- Unsupported delimiter or encoding\n"
                        "- Invalid data format\n\n"
                        "Tried encodings: " + ", ".join(encodings_to_try)
                    )

                # Show mapper dialog with detected headers if available
                dlg = SeismicColumnMapperDialog(columns_data, file_path, self, column_headers=column_headers)
                if dlg.exec_() == QDialog.Accepted:
                    self.column_mapping = dlg.get_mapping()
                    self.load_btn.setEnabled(True)

                    # Show mapping summary in preview
                    mapping_text = "✓ Column Mapping Applied Successfully!\n\n"
                    mapping_text += f"File: {Path(file_path).name}\n"
                    mapping_text += f"Total Columns: {len(columns_data)}\n\n"
                    mapping_text += "Mapped Columns:\n"
                    for type_str, col_idx in sorted(self.column_mapping.items(), key=lambda x: x[1]):
                        mapping_text += f"  Column {col_idx + 1} → {type_str}\n"
                    mapping_text += "\nReady to load. Click 'Load Data' to proceed."
                    self.preview_text.setPlainText(mapping_text)
                else:
                    # User cancelled - clear file selection
                    self.single_file_path.clear()
                    self.selected_files = []
                    self.column_mapping = None
                    self.load_btn.setEnabled(False)

            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to read file for column mapping:\n{str(e)}\n\n"
                    f"Make sure the file is a valid text/CSV file with numeric data."
                )
                self.single_file_path.clear()
                self.selected_files = []
                self.column_mapping = None
                self.load_btn.setEnabled(False)

        def _show_channel_mapper_type1(self, mseed_files: List[Path]):
            """Show channel mapping dialog for MiniSEED files - handles multiple unique channel structures."""
            try:
                from hvsr_pro.gui.channel_mapper_dialog import ChannelMapperDialog

                try:
                    from obspy import read
                except ImportError:
                    QMessageBox.critical(
                        self,
                        "Error",
                        "ObsPy is required for MiniSEED channel mapping.\n"
                        "Please install ObsPy: pip install obspy"
                    )
                    self.use_channel_mapping_type1.setChecked(False)
                    self.load_btn.setEnabled(True)
                    self.update_preview_type1(mseed_files)
                    return

                # Step 1: Scan all files and group by unique channel structures
                from PyQt5.QtWidgets import QProgressDialog
                from PyQt5.QtCore import Qt

                progress = QProgressDialog(
                    "Scanning files for channel structures...",
                    "Cancel",
                    0,
                    len(mseed_files),
                    self
                )
                progress.setWindowModality(Qt.WindowModal)
                progress.setMinimumDuration(0)

                # Dictionary to group files by channel signature
                # signature = frozenset of channel codes
                channel_groups = {}  # {signature: {'channels_info': [...], 'files': [...]}}

                for i, file_path in enumerate(mseed_files):
                    progress.setValue(i)
                    if progress.wasCanceled():
                        self.use_channel_mapping_type1.setChecked(False)
                        self.load_btn.setEnabled(True)
                        self.update_preview_type1(mseed_files)
                        return

                    try:
                        stream = read(str(file_path))

                        # Extract channel codes
                        channel_codes = tuple(sorted(trace.stats.channel for trace in stream))
                        signature = channel_codes  # Use sorted tuple as signature

                        if signature not in channel_groups:
                            # Extract full channel info for this structure
                            channels_info = []
                            for trace in stream:
                                channel_info = {
                                    'code': trace.stats.channel,
                                    'location': trace.stats.location,
                                    'sampling_rate': trace.stats.sampling_rate,
                                    'npts': trace.stats.npts,
                                    'station': trace.stats.station,
                                    'network': trace.stats.network
                                }
                                channels_info.append(channel_info)

                            channel_groups[signature] = {
                                'channels_info': channels_info,
                                'files': []
                            }

                        channel_groups[signature]['files'].append(file_path)

                    except Exception as e:
                        print(f"Failed to read {file_path.name}: {e}")
                        continue

                progress.setValue(len(mseed_files))

                if not channel_groups:
                    QMessageBox.warning(
                        self,
                        "No Valid Files",
                        "No valid MiniSEED files could be read."
                    )
                    self.use_channel_mapping_type1.setChecked(False)
                    self.load_btn.setEnabled(True)
                    self.update_preview_type1(mseed_files)
                    return

                # Step 2: Show mapping dialog for each unique channel structure
                # Store mappings: {signature: mapping_dict}
                all_mappings = {}

                for signature, group_data in channel_groups.items():
                    channels_info = group_data['channels_info']
                    group_files = group_data['files']

                    # Show dialog with info about how many files have this structure
                    info_msg = f"{len(group_files)} file(s) with channels: {', '.join(signature)}"
                    sample_file = group_files[0]

                    dlg = ChannelMapperDialog(channels_info, str(sample_file), self)
                    dlg.setWindowTitle(f"Map Channels - {info_msg}")

                    if dlg.exec_() == QDialog.Accepted:
                        mapping = dlg.get_mapping()
                        all_mappings[signature] = mapping
                    else:
                        # User cancelled - abort entire process
                        self.use_channel_mapping_type1.setChecked(False)
                        self.channel_mapping_type1 = None
                        self.load_btn.setEnabled(True)
                        self.update_preview_type1(mseed_files)
                        return

                # Step 3: Store the mappings (we'll need to pass file-specific mappings to the loader)
                # For now, store as a dict: {file_path: mapping}
                self.channel_mapping_type1 = {}
                for signature, mapping in all_mappings.items():
                    for file_path in channel_groups[signature]['files']:
                        self.channel_mapping_type1[str(file_path)] = mapping

                self.load_btn.setEnabled(True)

                # Show mapping summary in preview
                mapping_text = "✓ Channel Mapping Applied Successfully!\n\n"
                mapping_text += f"Total Files: {len(mseed_files)}\n"
                mapping_text += f"Unique Channel Structures: {len(channel_groups)}\n\n"

                for signature, group_data in channel_groups.items():
                    mapping = all_mappings[signature]
                    mapping_text += f"Group: {', '.join(signature)} ({len(group_data['files'])} files)\n"
                    for component, channel_code in sorted(mapping.items()):
                        mapping_text += f"  {component} → {channel_code}\n"
                    mapping_text += "\n"

                mapping_text += "Ready to load. Click 'Load Data' to proceed."
                self.preview_text.setPlainText(mapping_text)

            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Failed to show channel mapper:\n{str(e)}"
                )
                self.use_channel_mapping_type1.setChecked(False)
                self.channel_mapping_type1 = None
                self.load_btn.setEnabled(True)
                self.update_preview_type1(mseed_files)

        def browse_type1_directory(self):
            """Browse for Type 1 directory (3-channel files)."""
            dir_path = QFileDialog.getExistingDirectory(
                self,
                "Select Directory with MiniSEED Files"
            )
            
            if dir_path:
                self.type1_dir_path.setText(dir_path)
                self.detect_type1_files(dir_path)
        
        def browse_type2_directory(self):
            """Browse for Type 2 directory (separate E,N,Z)."""
            dir_path = QFileDialog.getExistingDirectory(
                self,
                "Select Directory with MiniSEED Files"
            )
            
            if dir_path:
                self.type2_dir_path.setText(dir_path)
                self.detect_type2_files(dir_path)
        
        def detect_type1_files(self, dir_path: str):
            """Detect Type 1 MiniSEED files (3-channel per file)."""
            path = Path(dir_path)
            mseed_files = sorted(list(path.glob("*.mseed")) + list(path.glob("*.miniseed")))

            self.type1_file_list.clear()
            self.type1_all_files = []  # Store all detected files

            for file in mseed_files:
                self.type1_file_list.addItem(file.name)
                self.type1_all_files.append(str(file))

            # Select all by default
            self.type1_file_list.selectAll()

            # Connect selection change to update count
            self.type1_file_list.itemSelectionChanged.connect(self.update_type1_selection)

            count = len(mseed_files)
            self.type1_count_label.setText(f"{count} files detected | {count} selected")

            if count > 0:
                self.load_mode = 'multi_type1'

                # If channel mapping is enabled, show the channel mapper dialog
                if self.use_channel_mapping_type1.isChecked() and mseed_files:
                    self._show_channel_mapper_type1(mseed_files)
                else:
                    self.load_btn.setEnabled(True)
                    self.update_preview_type1(mseed_files)
            else:
                self.load_btn.setEnabled(False)
                self.preview_text.setText("No MiniSEED files found in directory.")
        
        def update_type1_selection(self):
            """Update count label when selection changes."""
            selected_indices = [self.type1_file_list.row(item) 
                               for item in self.type1_file_list.selectedItems()]
            self.selected_files = [self.type1_all_files[i] for i in selected_indices]
            
            total = len(self.type1_all_files)
            selected = len(selected_indices)
            self.type1_count_label.setText(f"{total} files detected | {selected} selected")
            
            # Update load button
            self.load_btn.setEnabled(selected > 0)
            
            # Update preview
            if selected > 0:
                selected_paths = [Path(self.type1_all_files[i]) for i in selected_indices]
                self.update_preview_type1(selected_paths)
            else:
                self.preview_text.setText("No files selected")
        
        def detect_type2_files(self, dir_path: str):
            """Detect Type 2 MiniSEED files (separate E, N, Z)."""
            path = Path(dir_path)
            all_files = list(path.glob("*.mseed")) + list(path.glob("*.miniseed"))
            
            # Group files by base name (removing _E, _N, _Z suffix)
            groups = self.group_component_files(all_files)
            
            self.type2_group_list.clear()
            self.type2_all_groups = groups  # Store all groups
            self.type2_group_names = []  # Store group names in order
            
            for base_name, components in sorted(groups.items()):
                has_e = 'E' in components
                has_n = 'N' in components
                has_z = 'Z' in components
                is_complete = has_e and has_n and has_z
                
                status = "OK" if is_complete else "INCOMPLETE"
                item_text = f"{status} | {base_name} [E:{has_e}, N:{has_n}, Z:{has_z}]"
                
                item = QListWidgetItem(item_text)
                if not is_complete:
                    item.setForeground(QColor('red'))
                
                self.type2_group_list.addItem(item)
                self.type2_group_names.append(base_name)
                
                # Auto-select complete groups only
                if is_complete:
                    item.setSelected(True)
            
            # Connect selection change
            self.type2_group_list.itemSelectionChanged.connect(self.update_type2_selection)
            
            count = len(groups)
            complete_count = sum(1 for g in groups.values() 
                                if 'E' in g and 'N' in g and 'Z' in g)
            
            self.type2_count_label.setText(
                f"{count} groups detected | {complete_count} selected"
            )
            
            # Update grouped_files with only complete ones
            self.update_type2_selection()
            
            if complete_count > 0:
                self.load_mode = 'multi_type2'
                self.load_btn.setEnabled(True)
            else:
                self.load_btn.setEnabled(False)
                self.preview_text.setText(
                    "No complete E+N+Z file groups found.\n"
                    "Please ensure files follow pattern: basename_E.mseed, basename_N.mseed, basename_Z.mseed"
                )
        
        def update_type2_selection(self):
            """Update selection for Type 2 groups."""
            selected_indices = [self.type2_group_list.row(item) 
                               for item in self.type2_group_list.selectedItems()]
            
            # Get selected group names
            selected_names = [self.type2_group_names[i] for i in selected_indices]
            
            # Filter to only selected groups
            self.grouped_files = {name: self.type2_all_groups[name] 
                                 for name in selected_names}
            
            # Count complete groups in selection
            complete_selected = sum(1 for name in selected_names
                                   if all(c in self.type2_all_groups[name] for c in ['E', 'N', 'Z']))
            
            total = len(self.type2_all_groups)
            self.type2_count_label.setText(
                f"{total} groups detected | {complete_selected} selected"
            )
            
            # Update load button
            self.load_btn.setEnabled(complete_selected > 0)
            
            # Update preview
            if complete_selected > 0:
                self.update_preview_type2(self.grouped_files)
            else:
                self.preview_text.setText("No complete groups selected")
        
        def group_component_files(self, files: List[Path]) -> Dict[str, Dict[str, Path]]:
            """
            Group files by component (E, N, Z).
            
            Detects patterns like:
            - XX01_pt1_corrected_E.miniseed
            - XX01_pt1_corrected_N.miniseed
            - XX01_pt1_corrected_Z.miniseed
            
            Returns:
                Dict mapping base_name -> {'E': path, 'N': path, 'Z': path}
            """
            groups = {}
            
            for file in files:
                name = file.stem  # Filename without extension
                
                # Try to detect component suffix
                component = None
                base_name = name
                
                # Pattern 1: _E, _N, _Z at end
                if name.endswith('_E'):
                    component = 'E'
                    base_name = name[:-2]
                elif name.endswith('_N'):
                    component = 'N'
                    base_name = name[:-2]
                elif name.endswith('_Z'):
                    component = 'Z'
                    base_name = name[:-2]
                
                # Pattern 2: .E, .N, .Z before extension
                elif '.E' in name:
                    component = 'E'
                    base_name = name.replace('.E', '')
                elif '.N' in name:
                    component = 'N'
                    base_name = name.replace('.N', '')
                elif '.Z' in name:
                    component = 'Z'
                    base_name = name.replace('.Z', '')
                
                if component:
                    if base_name not in groups:
                        groups[base_name] = {}
                    groups[base_name][component] = file
            
            return groups
        
        def update_preview_single(self, file_path: str):
            """Update preview for single file."""
            path = Path(file_path)
            size_mb = path.stat().st_size / (1024 * 1024)
            
            preview = f"Mode: Single File\n"
            preview += f"File: {path.name}\n"
            preview += f"Size: {size_mb:.2f} MB\n"
            preview += f"Type: {'MiniSEED' if path.suffix in ['.mseed', '.miniseed'] else 'ASCII'}\n"
            
            self.preview_text.setText(preview)
        
        def update_preview_type1(self, files: List[Path]):
            """Update preview for Type 1 files."""
            total_size = sum(f.stat().st_size for f in files) / (1024 * 1024)
            
            # Estimate duration (rough: 1 MB ≈ 50 seconds at 200 Hz)
            estimated_hours = (total_size / 60) / 60
            
            preview = f"Mode: Multi-File Type 1 (3-channel per file)\n"
            preview += f"Files: {len(files)}\n"
            preview += f"Total Size: {total_size:.2f} MB\n"
            preview += f"Estimated Duration: ~{estimated_hours:.1f} hours\n"
            preview += f"\nFirst file: {files[0].name}\n"
            if len(files) > 1:
                preview += f"Last file: {files[-1].name}\n"
            preview += f"\nFiles will be merged chronologically."
            
            # Warning for large datasets
            if len(files) > 10 or estimated_hours > 10:
                preview += f"\n\nWARNING: Large dataset!"
                preview += f"\nProcessing {len(files)} files may take several minutes."
                preview += f"\nRecommendation: Start with 3-5 files for testing."
                preview += f"\nExpected windows: ~{int(estimated_hours * 120)} (30s windows, 50% overlap)"
            
            self.preview_text.setText(preview)
        
        def update_preview_type2(self, groups: Dict[str, Dict[str, Path]]):
            """Update preview for Type 2 files."""
            complete_groups = [g for g in groups.values() 
                             if 'E' in g and 'N' in g and 'Z' in g]
            
            total_files = sum(len(g) for g in complete_groups)
            total_size = sum(
                sum(f.stat().st_size for f in g.values())
                for g in complete_groups
            ) / (1024 * 1024)
            
            preview = f"Mode: Multi-File Type 2 (separate E, N, Z)\n"
            preview += f"Complete Groups: {len(complete_groups)}\n"
            preview += f"Total Files: {total_files}\n"
            preview += f"Total Size: {total_size:.2f} MB\n"
            
            if complete_groups:
                first_group = list(groups.keys())[0]
                preview += f"\nFirst group: {first_group}\n"
            
            preview += f"\nEach group will be merged into 3-component stream."
            
            self.preview_text.setText(preview)
        
        def on_single_time_range_toggled(self, state):
            """Handle single file time range checkbox toggle."""
            enabled = (state == Qt.Checked)
            self.single_start_datetime.setEnabled(enabled)
            self.single_end_datetime.setEnabled(enabled)
            self.single_timezone.setEnabled(enabled)
            self.update_single_time_preview()
        
        def on_time_range_toggled(self, state):
            """Handle Type 1 time range checkbox toggle."""
            enabled = (state == Qt.Checked)
            self.type1_start_datetime.setEnabled(enabled)
            self.type1_end_datetime.setEnabled(enabled)
            self.type1_timezone.setEnabled(enabled)
            self.update_time_preview()
        
        def on_type2_time_range_toggled(self, state):
            """Handle Type 2 time range checkbox toggle."""
            enabled = (state == Qt.Checked)
            self.type2_start_datetime.setEnabled(enabled)
            self.type2_end_datetime.setEnabled(enabled)
            self.type2_timezone.setEnabled(enabled)
            self.update_type2_time_preview()
        
        def update_time_preview(self):
            """Update time range preview."""
            if not self.type1_use_time_range.isChecked():
                self.type1_time_preview.setText("")
                return
            
            # Get values
            start_dt = self.type1_start_datetime.dateTime().toPyDateTime()
            end_dt = self.type1_end_datetime.dateTime().toPyDateTime()
            tz_text = self.type1_timezone.currentText()
            
            # Parse timezone offset
            if "+" in tz_text:
                offset = int(tz_text.split("+")[1].split()[0])
            elif "-" in tz_text and tz_text.startswith("UTC"):
                offset = -int(tz_text.split("-")[1].split()[0])
            else:
                offset = 0
            
            # Calculate duration
            duration_seconds = (end_dt - start_dt).total_seconds()
            duration_hours = duration_seconds / 3600
            
            # Estimate windows (30s with 50% overlap = 120 windows/hour)
            est_windows = int(duration_hours * 120)
            
            # Build preview text
            preview = f"<b>Time Range Preview:</b><br>"
            preview += f"Local Time: {start_dt.strftime('%Y-%m-%d %H:%M:%S')} → {end_dt.strftime('%Y-%m-%d %H:%M:%S')}<br>"
            preview += f"Timezone: {tz_text} (UTC{offset:+d})<br>"
            
            if duration_seconds > 0:
                preview += f"Duration: {duration_hours:.2f} hours ({duration_seconds:.0f} seconds)<br>"
                preview += f"Estimated windows (30s, 50% overlap): ~{est_windows}"
            else:
                preview += "<b style='color:red;'>WARNING: End time must be after start time!</b>"
            
            self.type1_time_preview.setText(preview)
        
        def update_single_time_preview(self):
            """Update single file time range preview."""
            if not self.single_use_time_range.isChecked():
                self.single_time_preview.setText("")
                return
            
            # Get values
            start_dt = self.single_start_datetime.dateTime().toPyDateTime()
            end_dt = self.single_end_datetime.dateTime().toPyDateTime()
            tz_text = self.single_timezone.currentText()
            
            # Parse timezone offset
            if "+" in tz_text:
                offset = int(tz_text.split("+")[1].split()[0])
            elif "-" in tz_text and tz_text.startswith("UTC"):
                offset = -int(tz_text.split("-")[1].split()[0])
            else:
                offset = 0
            
            # Calculate duration
            duration_seconds = (end_dt - start_dt).total_seconds()
            duration_hours = duration_seconds / 3600
            
            # Estimate windows (30s with 50% overlap = 120 windows/hour)
            est_windows = int(duration_hours * 120)
            
            # Build preview text
            preview = f"<b>Time Range Preview:</b><br>"
            preview += f"Local Time: {start_dt.strftime('%Y-%m-%d %H:%M:%S')} → {end_dt.strftime('%Y-%m-%d %H:%M:%S')}<br>"
            preview += f"Timezone: {tz_text} (UTC{offset:+d})<br>"
            
            if duration_seconds > 0:
                preview += f"Duration: {duration_hours:.2f} hours ({duration_seconds:.0f} seconds)<br>"
                preview += f"Estimated windows (30s, 50% overlap): ~{est_windows}"
            else:
                preview += "<b style='color:red;'>WARNING: End time must be after start time!</b>"
            
            self.single_time_preview.setText(preview)
        
        def update_type2_time_preview(self):
            """Update Type 2 time range preview."""
            if not self.type2_use_time_range.isChecked():
                self.type2_time_preview.setText("")
                return
            
            # Get values
            start_dt = self.type2_start_datetime.dateTime().toPyDateTime()
            end_dt = self.type2_end_datetime.dateTime().toPyDateTime()
            tz_text = self.type2_timezone.currentText()
            
            # Parse timezone offset
            if "+" in tz_text:
                offset = int(tz_text.split("+")[1].split()[0])
            elif "-" in tz_text and tz_text.startswith("UTC"):
                offset = -int(tz_text.split("-")[1].split()[0])
            else:
                offset = 0
            
            # Calculate duration
            duration_seconds = (end_dt - start_dt).total_seconds()
            duration_hours = duration_seconds / 3600
            
            # Estimate windows (30s with 50% overlap = 120 windows/hour)
            est_windows = int(duration_hours * 120)
            
            # Build preview text
            preview = f"<b>Time Range Preview:</b><br>"
            preview += f"Local Time: {start_dt.strftime('%Y-%m-%d %H:%M:%S')} → {end_dt.strftime('%Y-%m-%d %H:%M:%S')}<br>"
            preview += f"Timezone: {tz_text} (UTC{offset:+d})<br>"
            
            if duration_seconds > 0:
                preview += f"Duration: {duration_hours:.2f} hours ({duration_seconds:.0f} seconds)<br>"
                preview += f"Estimated windows (30s, 50% overlap): ~{est_windows}"
            else:
                preview += "<b style='color:red;'>WARNING: End time must be after start time!</b>"
            
            self.type2_time_preview.setText(preview)
        
        def accept_files(self):
            """Accept selected files and emit signal."""
            if not self.selected_files and not self.grouped_files:
                QMessageBox.warning(self, "No Files", "Please select files to load.")
                return
            
            # Prepare time range data (check all modes)
            time_range = None
            
            # Check single file mode
            if self.load_mode == 'single' and hasattr(self, 'single_use_time_range') and self.single_use_time_range.isChecked():
                tz_text = self.single_timezone.currentText()
                # Parse timezone offset
                if "+" in tz_text:
                    offset = int(tz_text.split("+")[1].split()[0])
                elif "-" in tz_text and tz_text.startswith("UTC"):
                    offset = -int(tz_text.split("-")[1].split()[0])
                else:
                    offset = 0
                
                time_range = {
                    'enabled': True,
                    'start': self.single_start_datetime.dateTime().toPyDateTime(),
                    'end': self.single_end_datetime.dateTime().toPyDateTime(),
                    'timezone_offset': offset,
                    'timezone_name': tz_text
                }
            
            # Check Type 1 mode
            elif self.load_mode == 'multi_type1' and hasattr(self, 'type1_use_time_range') and self.type1_use_time_range.isChecked():
                tz_text = self.type1_timezone.currentText()
                # Parse timezone offset
                if "+" in tz_text:
                    offset = int(tz_text.split("+")[1].split()[0])
                elif "-" in tz_text and tz_text.startswith("UTC"):
                    offset = -int(tz_text.split("-")[1].split()[0])
                else:
                    offset = 0
                
                time_range = {
                    'enabled': True,
                    'start': self.type1_start_datetime.dateTime().toPyDateTime(),
                    'end': self.type1_end_datetime.dateTime().toPyDateTime(),
                    'timezone_offset': offset,
                    'timezone_name': tz_text
                }
            
            # Check Type 2 mode
            elif self.load_mode == 'multi_type2' and hasattr(self, 'type2_use_time_range') and self.type2_use_time_range.isChecked():
                tz_text = self.type2_timezone.currentText()
                # Parse timezone offset
                if "+" in tz_text:
                    offset = int(tz_text.split("+")[1].split()[0])
                elif "-" in tz_text and tz_text.startswith("UTC"):
                    offset = -int(tz_text.split("-")[1].split()[0])
                else:
                    offset = 0
                
                time_range = {
                    'enabled': True,
                    'start': self.type2_start_datetime.dateTime().toPyDateTime(),
                    'end': self.type2_end_datetime.dateTime().toPyDateTime(),
                    'timezone_offset': offset,
                    'timezone_name': tz_text
                }
            
            # Prepare output
            result = {
                'mode': self.load_mode,
                'files': self.selected_files,
                'groups': self.grouped_files,
                'time_range': time_range,
                'options': {
                    'merge_continuous': self.merge_continuous.isChecked(),
                    'verify_sampling_rate': self.verify_sampling_rate.isChecked(),
                    'column_mapping': self.column_mapping if hasattr(self, 'column_mapping') else None,
                    'channel_mapping': self.channel_mapping_type1 if hasattr(self, 'channel_mapping_type1') else None,
                }
            }

            self.files_selected.emit(result)
            self.accept()


else:
    # Dummy class when PyQt5 not available
    class DataInputDialog:
        def __init__(self, *args, **kwargs):
            raise ImportError("PyQt5 is required for GUI functionality")
