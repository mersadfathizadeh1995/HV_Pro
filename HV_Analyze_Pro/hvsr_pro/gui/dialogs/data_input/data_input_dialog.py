"""
Enhanced Data Input Dialog for HVSR Pro
========================================

Multi-tab dialog for loading various data formats:
- Single files (ASCII txt, MiniSEED)
- Multiple MiniSEED files (Type 1: 3-channel per file)
- Separate component MiniSEED files (Type 2: E, N, Z separate)
- Automatic pattern matching and file grouping
- Visual waveform preview with time range selection
"""

from pathlib import Path
from typing import List, Dict, Optional, Tuple
import re
import numpy as np

try:
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
        QPushButton, QLabel, QLineEdit, QFileDialog, QListWidget,
        QGroupBox, QRadioButton, QCheckBox, QTextEdit, QComboBox,
        QMessageBox, QListWidgetItem, QTableWidget, QTableWidgetItem,
        QHeaderView, QSpinBox, QDoubleSpinBox, QDateTimeEdit, QSplitter,
        QButtonGroup, QFrame
    )
    from PyQt5.QtCore import Qt, pyqtSignal
    from PyQt5.QtGui import QFont, QColor
    HAS_PYQT5 = True
    
    # Try to import matplotlib for visual preview
    try:
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
        HAS_MATPLOTLIB = True
    except ImportError:
        HAS_MATPLOTLIB = False
        
except ImportError:
    HAS_PYQT5 = False
    HAS_MATPLOTLIB = False


if HAS_PYQT5:
    
    class CollapsibleGroupBox(QWidget):
        """A collapsible group box widget with toggle button."""
        
        def __init__(self, title: str = "", parent=None):
            super().__init__(parent)
            self._is_collapsed = False
            
            # Main layout
            main_layout = QVBoxLayout(self)
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.setSpacing(0)
            
            # Header frame with toggle button
            self.header_frame = QFrame()
            self.header_frame.setStyleSheet("""
                QFrame {
                    background-color: #f0f0f0;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                }
                QFrame:hover {
                    background-color: #e0e0e0;
                }
            """)
            self.header_frame.setCursor(Qt.PointingHandCursor)
            header_layout = QHBoxLayout(self.header_frame)
            header_layout.setContentsMargins(8, 4, 8, 4)
            
            # Toggle indicator
            self.toggle_indicator = QLabel("[+]")
            self.toggle_indicator.setStyleSheet("font-size: 10pt; color: #555; font-weight: bold;")
            header_layout.addWidget(self.toggle_indicator)
            
            # Title label
            self.title_label = QLabel(title)
            self.title_label.setStyleSheet("font-weight: bold; font-size: 10pt;")
            header_layout.addWidget(self.title_label)
            header_layout.addStretch()
            
            main_layout.addWidget(self.header_frame)
            
            # Content container
            self.content_widget = QWidget()
            self.content_layout = QVBoxLayout(self.content_widget)
            self.content_layout.setContentsMargins(5, 5, 5, 5)
            main_layout.addWidget(self.content_widget)
            
            # Make header clickable
            self.header_frame.mousePressEvent = self._on_header_clicked
            
        def _on_header_clicked(self, event):
            """Toggle collapsed state on header click."""
            self.setCollapsed(not self._is_collapsed)
            
        def setCollapsed(self, collapsed: bool):
            """Set the collapsed state."""
            self._is_collapsed = collapsed
            self.content_widget.setVisible(not collapsed)
            self.toggle_indicator.setText("[+]" if collapsed else "[-]")
            
        def isCollapsed(self) -> bool:
            """Return whether the group box is collapsed."""
            return self._is_collapsed
            
        def setContentLayout(self, layout):
            """Set the content layout."""
            # Clear existing content layout
            while self.content_layout.count():
                item = self.content_layout.takeAt(0)
                if item.widget():
                    item.widget().setParent(None)
            
            # If layout has items, move them to content_layout
            if layout is not None:
                while layout.count():
                    item = layout.takeAt(0)
                    if item.widget():
                        self.content_layout.addWidget(item.widget())
                    elif item.layout():
                        self.content_layout.addLayout(item.layout())



    
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
            self.resize(900, 700)
            self.setMinimumSize(600, 400)
            
            # Make dialog resizable
            self.setSizeGripEnabled(True)
            
            # Storage
            self.selected_files = []
            self.grouped_files = {}
            self.load_mode = 'single'
            self.type1_all_files = []  # All detected Type 1 files
            self.type2_all_groups = {}  # All detected Type 2 groups
            
            self.init_ui()
            
        def init_ui(self):
            """Initialize user interface."""
            from PyQt5.QtWidgets import QScrollArea
            
            main_layout = QVBoxLayout(self)
            
            # Title
            title = QLabel("Load Seismic Data")
            title_font = QFont()
            title_font.setPointSize(14)
            title_font.setBold(True)
            title.setFont(title_font)
            title.setAlignment(Qt.AlignCenter)
            main_layout.addWidget(title)
            
            # Create scroll area for main content
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            scroll_area.setFrameShape(QFrame.NoFrame)
            
            # Container widget for scrollable content
            scroll_content = QWidget()
            scroll_layout = QVBoxLayout(scroll_content)
            scroll_layout.setContentsMargins(5, 5, 5, 5)
            
            # Tab widget
            self.tabs = QTabWidget()
            self.tabs.addTab(self.create_single_file_tab(), "Single File")
            self.tabs.addTab(self.create_multi_type1_tab(), "Multi-File (3-channel)")
            self.tabs.addTab(self.create_multi_type2_tab(), "Multi-File (Separate E,N,Z)")
            self.tabs.addTab(self.create_advanced_tab(), "Advanced Options")
            scroll_layout.addWidget(self.tabs)
            
            # Collapsible Preview section
            self.preview_group = CollapsibleGroupBox("Data Preview (click to expand/collapse)")
            preview_layout = QVBoxLayout()
            
            # Simple text preview (collapsible)
            self.preview_text = QTextEdit()
            self.preview_text.setReadOnly(True)
            self.preview_text.setMaximumHeight(150)
            self.preview_text.setPlaceholderText("Select a file to see preview info...")
            preview_layout.addWidget(self.preview_text)
            
            # Visual preview panel (matplotlib canvas) - also collapsible
            if HAS_MATPLOTLIB:
                visual_group = QGroupBox("Visual Preview")
                visual_layout = QVBoxLayout(visual_group)
                
                # View mode buttons
                view_mode_layout = QHBoxLayout()
                self.preview_button_group = QButtonGroup(self)
                
                self.preview_radio_all = QRadioButton("All Components")
                self.preview_radio_all.setChecked(True)
                self.preview_radio_all.toggled.connect(lambda checked: checked and self.update_visual_preview())
                self.preview_button_group.addButton(self.preview_radio_all)
                view_mode_layout.addWidget(self.preview_radio_all)
                
                self.preview_radio_e = QRadioButton("E")
                self.preview_radio_e.toggled.connect(lambda checked: checked and self.update_visual_preview())
                self.preview_button_group.addButton(self.preview_radio_e)
                view_mode_layout.addWidget(self.preview_radio_e)
                
                self.preview_radio_n = QRadioButton("N")
                self.preview_radio_n.toggled.connect(lambda checked: checked and self.update_visual_preview())
                self.preview_button_group.addButton(self.preview_radio_n)
                view_mode_layout.addWidget(self.preview_radio_n)
                
                self.preview_radio_z = QRadioButton("Z")
                self.preview_radio_z.toggled.connect(lambda checked: checked and self.update_visual_preview())
                self.preview_button_group.addButton(self.preview_radio_z)
                view_mode_layout.addWidget(self.preview_radio_z)
                
                view_mode_layout.addStretch()
                
                # Refresh button
                refresh_btn = QPushButton("Refresh")
                refresh_btn.clicked.connect(self.refresh_visual_preview)
                refresh_btn.setMaximumWidth(80)
                view_mode_layout.addWidget(refresh_btn)
                
                visual_layout.addLayout(view_mode_layout)
                
                # Matplotlib figure and canvas
                self.preview_fig = Figure(figsize=(5, 2.5), dpi=80)
                self.preview_canvas = FigureCanvas(self.preview_fig)
                self.preview_canvas.setMinimumHeight(150)
                self.preview_canvas.setMaximumHeight(250)
                visual_layout.addWidget(self.preview_canvas)
                
                # Status label for preview
                self.preview_status = QLabel("Load a file to see preview")
                self.preview_status.setStyleSheet("color: gray; font-size: 9pt;")
                visual_layout.addWidget(self.preview_status)
                
                preview_layout.addWidget(visual_group)
                
                # Initialize preview data storage
                self.preview_data = None
            else:
                # Fallback if matplotlib not available
                fallback_label = QLabel("(Visual preview requires matplotlib)")
                fallback_label.setStyleSheet("color: gray; font-style: italic;")
                preview_layout.addWidget(fallback_label)
            
            self.preview_group.setContentLayout(preview_layout)
            self.preview_group.setCollapsed(True)  # Start collapsed
            scroll_layout.addWidget(self.preview_group)
            
            # Set scroll content
            scroll_area.setWidget(scroll_content)
            main_layout.addWidget(scroll_area, 1)  # stretch factor 1
            
            # Buttons (outside scroll area)
            button_layout = QHBoxLayout()
            button_layout.addStretch()
            
            cancel_btn = QPushButton("Cancel")
            cancel_btn.clicked.connect(self.reject)
            button_layout.addWidget(cancel_btn)
            
            self.load_btn = QPushButton("Load Data")
            self.load_btn.clicked.connect(self.accept_files)
            self.load_btn.setEnabled(False)
            button_layout.addWidget(self.load_btn)
            
            main_layout.addLayout(button_layout)
        
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
            self.use_column_mapping = QCheckBox("Enable Column Mapping (for CSV/text files)")
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

            layout.addWidget(dir_group)

            # Storage for per-file channel mapping and channel info
            self.channel_mapping_type1 = {}  # {file_path: {'E': 'HHE', 'N': 'HHN', 'Z': 'HHZ'}}
            self.type1_file_channels = {}  # {file_path: [{'code': 'HHE', ...}, ...]}

            # File list with enhanced display
            files_group = QGroupBox("Detected Files")
            files_layout = QVBoxLayout(files_group)
            
            # Use a table for better display with channel info
            self.type1_file_table = QTableWidget()
            self.type1_file_table.setColumnCount(4)
            self.type1_file_table.setHorizontalHeaderLabels([
                "File Name", "Channels", "Mapping Status", "Select"
            ])
            self.type1_file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
            self.type1_file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
            self.type1_file_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
            self.type1_file_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
            self.type1_file_table.setSelectionBehavior(QTableWidget.SelectRows)
            self.type1_file_table.setSelectionMode(QTableWidget.ExtendedSelection)
            self.type1_file_table.setAlternatingRowColors(True)
            files_layout.addWidget(self.type1_file_table)
            
            # Selection and mapping buttons
            button_layout = QHBoxLayout()
            
            select_all_btn = QPushButton("Select All")
            select_all_btn.clicked.connect(self.type1_select_all)
            button_layout.addWidget(select_all_btn)
            
            select_none_btn = QPushButton("Select None")
            select_none_btn.clicked.connect(self.type1_select_none)
            button_layout.addWidget(select_none_btn)
            
            button_layout.addStretch()
            
            # Per-file channel mapping button
            self.map_channels_btn = QPushButton("Map Channels for Selected")
            self.map_channels_btn.clicked.connect(self.map_channels_for_selected)
            self.map_channels_btn.setEnabled(False)
            self.map_channels_btn.setToolTip(
                "Map channels to E/N/Z components for selected files.\n"
                "Select one or more files, then click to configure channel mapping.\n"
                "Similar files will share the same mapping."
            )
            self.map_channels_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FF9800;
                    color: white;
                    font-weight: bold;
                    padding: 6px 12px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #F57C00;
                }
                QPushButton:disabled {
                    background-color: #ccc;
                    color: #888;
                }
            """)
            button_layout.addWidget(self.map_channels_btn)
            
            files_layout.addLayout(button_layout)
            
            count_label = QLabel("0 files detected | 0 selected | 0 mapped")
            self.type1_count_label = count_label
            files_layout.addWidget(count_label)
            
            # Info label for channel mapping
            mapping_info_type1 = QLabel(
                "<i>Tip: Select files and click 'Map Channels' to configure how channels are mapped to E/N/Z components. "
                "Files with standard naming (ending in E/N/Z) are auto-detected.</i>"
            )
            mapping_info_type1.setWordWrap(True)
            mapping_info_type1.setStyleSheet("color: #666; font-size: 9pt; padding: 5px; background: #f5f5f5; border-radius: 3px;")
            files_layout.addWidget(mapping_info_type1)
            
            layout.addWidget(files_group)
            
            # Connect table selection change
            self.type1_file_table.itemSelectionChanged.connect(self.on_type1_table_selection_changed)
            
            # Keep old list widget for backward compatibility (hidden)
            self.type1_file_list = QListWidget()
            self.type1_file_list.setVisible(False)
            
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
                
                # Update text preview
                file_size = Path(file_path).stat().st_size / (1024 * 1024)
                preview_text = f"File: {Path(file_path).name}\n"
                preview_text += f"Size: {file_size:.2f} MB\n"
                preview_text += f"Type: {'MiniSEED' if file_ext in ['.mseed', '.miniseed'] else 'Text/CSV'}\n"
                preview_text += f"\nReady to load"
                self.preview_text.setPlainText(preview_text)
                
                # Load visual preview
                self.load_preview_data_from_file(file_path)

        def _show_column_mapper(self, file_path: str):
            """Show column mapping dialog for CSV/text file."""
            try:
                import numpy as np
                from pathlib import Path
                from hvsr_pro.gui.dialogs import SeismicColumnMapperDialog

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
                    mapping_text = "Column Mapping Applied Successfully!\n\n"
                    mapping_text += f"File: {Path(file_path).name}\n"
                    mapping_text += f"Total Columns: {len(columns_data)}\n\n"
                    mapping_text += "Mapped Columns:\n"
                    for type_str, col_idx in sorted(self.column_mapping.items(), key=lambda x: x[1]):
                        mapping_text += f"  Column {col_idx + 1} -> {type_str}\n"
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
            """
            Legacy method for bulk channel mapping.
            Now replaced by per-file mapping via map_channels_for_selected().
            This method is kept for backward compatibility but simplified.
            """
            # Simply update the table and let user use the new per-file mapping
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
            """Detect Type 1 MiniSEED files (3-channel per file) and populate table with channel info."""
            from PyQt5.QtWidgets import QProgressDialog, QCheckBox
            from PyQt5.QtCore import Qt

            path = Path(dir_path)
            mseed_files = sorted(list(path.glob("*.mseed")) + list(path.glob("*.miniseed")))

            self.type1_file_list.clear()
            self.type1_all_files = []  # Store all detected files
            self.type1_file_channels = {}  # Store channel info per file
            self.channel_mapping_type1 = {}  # Reset mappings
            
            # Clear table
            self.type1_file_table.setRowCount(0)

            if not mseed_files:
                self.type1_count_label.setText("0 files detected | 0 selected | 0 mapped")
                self.load_btn.setEnabled(False)
                self.preview_text.setText("No MiniSEED files found in directory.")
                return

            # Progress dialog for scanning files
            progress = QProgressDialog(
                "Scanning files for channel information...",
                "Cancel",
                0,
                len(mseed_files),
                self
            )
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(500)  # Only show if takes > 500ms

            try:
                from obspy import read
                HAS_OBSPY = True
            except ImportError:
                HAS_OBSPY = False

            # Populate table with file info
            self.type1_file_table.setRowCount(len(mseed_files))
            
            for i, file in enumerate(mseed_files):
                progress.setValue(i)
                if progress.wasCanceled():
                    break
                
                file_path = str(file)
                self.type1_all_files.append(file_path)
                
                # Get channel info if ObsPy is available
                channels_str = "N/A"
                channels_info = []
                mapping_status = "Unknown"
                
                if HAS_OBSPY:
                    try:
                        stream = read(file_path, headonly=True)
                        channel_codes = [tr.stats.channel for tr in stream]
                        channels_str = ", ".join(channel_codes)
                        
                        # Store channel info
                        channels_info = [{
                            'code': tr.stats.channel,
                            'location': tr.stats.location,
                            'sampling_rate': tr.stats.sampling_rate,
                            'npts': tr.stats.npts,
                            'station': tr.stats.station,
                            'network': tr.stats.network
                        } for tr in stream]
                        self.type1_file_channels[file_path] = channels_info
                        
                        # Check if auto-detection would work
                        if self._can_auto_detect_channels(channel_codes):
                            mapping_status = "Auto-detect"
                        else:
                            mapping_status = "Needs mapping"
                    except Exception as e:
                        channels_str = f"Error: {str(e)[:20]}"
                        mapping_status = "Error"
                
                # File name
                name_item = QTableWidgetItem(file.name)
                name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
                name_item.setData(Qt.UserRole, file_path)  # Store full path
                self.type1_file_table.setItem(i, 0, name_item)
                
                # Channels
                channels_item = QTableWidgetItem(channels_str)
                channels_item.setFlags(channels_item.flags() & ~Qt.ItemIsEditable)
                self.type1_file_table.setItem(i, 1, channels_item)
                
                # Mapping status
                status_item = QTableWidgetItem(mapping_status)
                status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
                if "Auto" in mapping_status:
                    status_item.setForeground(QColor(0, 128, 0))  # Green
                elif "Needs" in mapping_status:
                    status_item.setForeground(QColor(255, 152, 0))  # Orange
                elif "Error" in mapping_status:
                    status_item.setForeground(QColor(255, 0, 0))  # Red
                self.type1_file_table.setItem(i, 2, status_item)
                
                # Selection checkbox
                checkbox = QCheckBox()
                checkbox.setChecked(False)  # Unchecked by default - user selects which to load
                checkbox.stateChanged.connect(self.update_type1_count)
                checkbox_widget = QWidget()
                checkbox_layout = QHBoxLayout(checkbox_widget)
                checkbox_layout.addWidget(checkbox)
                checkbox_layout.setAlignment(Qt.AlignCenter)
                checkbox_layout.setContentsMargins(0, 0, 0, 0)
                self.type1_file_table.setCellWidget(i, 3, checkbox_widget)
                
                # Also add to old list for compatibility
                self.type1_file_list.addItem(file.name)
            
            progress.setValue(len(mseed_files))
            
            # Don't select by default - user chooses which files to load
            self.type1_file_list.clearSelection()
            
            count = len(mseed_files)
            self.type1_count_label.setText(f"{count} files found - select files to load | 0 selected | 0 mapped")

            if count > 0:
                self.load_mode = 'multi_type1'
                # Don't enable load button until files are selected
                self.load_btn.setEnabled(False)
                self.preview_text.setText(
                    f"{count} MiniSEED files found in directory.\n\n"
                    "Check the files you want to load, then click 'Load Selected Data'.\n"
                    "Use 'Select All' to quickly select all files."
                )
            else:
                self.load_btn.setEnabled(False)
                self.preview_text.setText("No MiniSEED files found in directory.")
        
        def _can_auto_detect_channels(self, channel_codes: List[str]) -> bool:
            """Check if channels can be auto-detected based on naming conventions."""
            # Look for standard E/N/Z endings
            has_e = any(c.upper().endswith('E') or c.upper().endswith('1') for c in channel_codes)
            has_n = any(c.upper().endswith('N') or c.upper().endswith('2') for c in channel_codes)
            has_z = any(c.upper().endswith('Z') or c.upper().endswith('3') for c in channel_codes)
            return has_e and has_n and has_z
        
        def type1_select_all(self):
            """Select all files in Type 1 table."""
            for i in range(self.type1_file_table.rowCount()):
                checkbox_widget = self.type1_file_table.cellWidget(i, 3)
                if checkbox_widget:
                    checkbox = checkbox_widget.findChild(QCheckBox)
                    if checkbox:
                        checkbox.setChecked(True)
            self.type1_file_list.selectAll()
            self.update_type1_count()
        
        def type1_select_none(self):
            """Deselect all files in Type 1 table."""
            for i in range(self.type1_file_table.rowCount()):
                checkbox_widget = self.type1_file_table.cellWidget(i, 3)
                if checkbox_widget:
                    checkbox = checkbox_widget.findChild(QCheckBox)
                    if checkbox:
                        checkbox.setChecked(False)
            self.type1_file_list.clearSelection()
            self.update_type1_count()
        
        def on_type1_table_selection_changed(self):
            """Handle table row selection change."""
            selected_rows = self.type1_file_table.selectionModel().selectedRows()
            self.map_channels_btn.setEnabled(len(selected_rows) > 0)
        
        def update_type1_count(self):
            """Update count label for Type 1 files."""
            total = self.type1_file_table.rowCount()
            selected = 0
            mapped = len(self.channel_mapping_type1)
            
            for i in range(total):
                checkbox_widget = self.type1_file_table.cellWidget(i, 3)
                if checkbox_widget:
                    checkbox = checkbox_widget.findChild(QCheckBox)
                    if checkbox and checkbox.isChecked():
                        selected += 1
            
            if selected > 0:
                self.type1_count_label.setText(f"{total} files | {selected} selected | {mapped} mapped")
            else:
                self.type1_count_label.setText(f"{total} files found - select files to load | 0 selected | {mapped} mapped")
            self.load_btn.setEnabled(selected > 0)
            
            # Update selected files list
            self.selected_files = self._get_selected_type1_files()
            
            # Update text preview
            if selected > 0:
                selected_paths = [Path(f) for f in self.selected_files]
                self.update_preview_type1(selected_paths)
                
                # Load visual preview from first selected file
                if self.selected_files and HAS_MATPLOTLIB:
                    self.load_preview_data_from_file(self.selected_files[0])
            else:
                self.preview_text.setText("No files selected")
                if HAS_MATPLOTLIB and hasattr(self, '_show_empty_preview'):
                    self._show_empty_preview()
        
        def _get_selected_type1_files(self) -> List[str]:
            """Get list of selected Type 1 file paths."""
            selected = []
            for i in range(self.type1_file_table.rowCount()):
                checkbox_widget = self.type1_file_table.cellWidget(i, 3)
                if checkbox_widget:
                    checkbox = checkbox_widget.findChild(QCheckBox)
                    if checkbox and checkbox.isChecked():
                        name_item = self.type1_file_table.item(i, 0)
                        if name_item:
                            file_path = name_item.data(Qt.UserRole)
                            if file_path:
                                selected.append(file_path)
            return selected
        
        def map_channels_for_selected(self):
            """Show channel mapping dialog for selected files in table."""
            from hvsr_pro.gui.dialogs import ChannelMapperDialog
            from PyQt5.QtWidgets import QDialog
            
            # Get selected rows from table
            selected_rows = self.type1_file_table.selectionModel().selectedRows()
            if not selected_rows:
                QMessageBox.warning(
                    self,
                    "No Selection",
                    "Please select one or more files in the table to map channels."
                )
                return

            # Get file paths and channel info for selected files
            selected_files = []
            for row_index in selected_rows:
                row = row_index.row()
                name_item = self.type1_file_table.item(row, 0)
                if name_item:
                    file_path = name_item.data(Qt.UserRole)
                    if file_path:
                        selected_files.append(file_path)
            
            if not selected_files:
                return
            
            # Group selected files by channel structure
            channel_groups = {}  # {signature: {'channels_info': [...], 'files': [...]}}
            
            for file_path in selected_files:
                if file_path in self.type1_file_channels:
                    channels_info = self.type1_file_channels[file_path]
                    # Use sorted channel codes as signature
                    signature = tuple(sorted(ch['code'] for ch in channels_info))
                    
                    if signature not in channel_groups:
                        channel_groups[signature] = {
                            'channels_info': channels_info,
                            'files': []
                        }
                    channel_groups[signature]['files'].append(file_path)
            
            if not channel_groups:
                QMessageBox.warning(
                    self,
                    "No Channel Info",
                    "No channel information available for selected files.\n"
                    "Make sure ObsPy is installed and files are valid MiniSEED."
                )
                return
            
            # Show mapping dialog for each unique channel structure
            all_mappings = {}
            
            for signature, group_data in channel_groups.items():
                channels_info = group_data['channels_info']
                group_files = group_data['files']
                
                # Info message
                info_msg = f"{len(group_files)} file(s) with channels: {', '.join(signature)}"
                sample_file = Path(group_files[0]).name
                
                dlg = ChannelMapperDialog(channels_info, sample_file, self)
                dlg.setWindowTitle(f"Map Channels - {info_msg}")
                
                if dlg.exec_() == QDialog.Accepted:
                    mapping = dlg.get_mapping()
                    all_mappings[signature] = mapping
                    
                    # Store mapping for all files with this structure
                    for file_path in group_files:
                        self.channel_mapping_type1[file_path] = mapping
                else:
                    # User cancelled - don't abort, just skip this group
                    continue
            
            # Update table status indicators
            self._update_type1_mapping_status()
            
            # Update count
            self.update_type1_count()
            
            # Show summary
            if all_mappings:
                mapping_text = f"Channel mapping configured for {len(self.channel_mapping_type1)} file(s)\n\n"
                for signature, mapping in all_mappings.items():
                    mapping_text += f"Channels {', '.join(signature)}:\n"
                    for component, channel_code in sorted(mapping.items()):
                        mapping_text += f"  {component} -> {channel_code}\n"
                    mapping_text += "\n"

                self.preview_text.setPlainText(mapping_text + "Ready to load.")
        
        def _update_type1_mapping_status(self):
            """Update mapping status column in Type 1 table."""
            for i in range(self.type1_file_table.rowCount()):
                name_item = self.type1_file_table.item(i, 0)
                if name_item:
                    file_path = name_item.data(Qt.UserRole)
                    status_item = self.type1_file_table.item(i, 2)
                    
                    if file_path in self.channel_mapping_type1:
                        # Has custom mapping
                        mapping = self.channel_mapping_type1[file_path]
                        status_text = f"Mapped ({mapping.get('E', '?')}/{mapping.get('N', '?')}/{mapping.get('Z', '?')})"
                        status_item.setText(status_text)
                        status_item.setForeground(QColor(0, 128, 0))  # Green
                    # Keep original status if not mapped
        
        def update_type1_selection(self):
            """Update count label when selection changes (backward compatibility)."""
            # This method is kept for backward compatibility with the old QListWidget
            # The new table uses update_type1_count instead
            self.update_type1_count()
        
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
                
                # Do NOT auto-select - user chooses which groups to load
                item.setSelected(False)
            
            # Connect selection change
            self.type2_group_list.itemSelectionChanged.connect(self.update_type2_selection)
            
            count = len(groups)
            complete_count = sum(1 for g in groups.values() 
                                if 'E' in g and 'N' in g and 'Z' in g)
            
            self.type2_count_label.setText(
                f"{count} groups found ({complete_count} complete) - select groups to load | 0 selected"
            )
            
            # Initialize grouped_files as empty - user must select
            self.grouped_files = {}
            
            if complete_count > 0:
                self.load_mode = 'multi_type2'
                # Don't enable load button until groups are selected
                self.load_btn.setEnabled(False)
                self.preview_text.setText(
                    f"{count} file groups found ({complete_count} complete E+N+Z).\n\n"
                    "Select the groups you want to load, then click 'Load Selected Data'.\n"
                    "Use 'Select All' to quickly select all groups."
                )
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
            total_complete = sum(1 for g in self.type2_all_groups.values() 
                                if all(c in g for c in ['E', 'N', 'Z']))
            
            if complete_selected > 0:
                self.type2_count_label.setText(
                    f"{total} groups ({total_complete} complete) | {complete_selected} selected"
                )
            else:
                self.type2_count_label.setText(
                    f"{total} groups found ({total_complete} complete) - select groups to load | 0 selected"
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
            file_type = 'MiniSEED' if path.suffix.lower() in ['.mseed', '.miniseed'] else 'Text/CSV'
            
            preview = f"Single File Mode\n"
            preview += f"--------------------\n"
            preview += f"File: {path.name}\n"
            preview += f"Size: {size_mb:.2f} MB\n"
            preview += f"Type: {file_type}\n"
            preview += f"\nReady to load"
            
            self.preview_text.setText(preview)
            
            # Load visual preview
            if HAS_MATPLOTLIB:
                self.load_preview_data_from_file(file_path)
        
        def update_preview_type1(self, files: List[Path]):
            """Update preview for Type 1 files."""
            total_size = sum(f.stat().st_size for f in files) / (1024 * 1024)
            
            # Estimate duration (rough: 1 MB ≈ 50 seconds at 200 Hz)
            estimated_hours = (total_size / 60) / 60
            
            preview = f"Multi-File (3-channel)\n"
            preview += f"--------------------\n"
            preview += f"Files: {len(files)}\n"
            preview += f"Total Size: {total_size:.2f} MB\n"
            preview += f"Est. Duration: ~{estimated_hours:.1f}h\n"
            preview += f"\nFirst: {files[0].name}\n"
            if len(files) > 1:
                preview += f"Last: {files[-1].name}\n"
            preview += f"\nFiles will be merged"
            
            # Warning for large datasets
            if len(files) > 10 or estimated_hours > 10:
                preview += f"\n\nLarge dataset!"
                preview += f"\nEst. windows: ~{int(estimated_hours * 120)}"
            
            self.preview_text.setText(preview)
            
            # Load visual preview from merged files
            if HAS_MATPLOTLIB:
                self.load_preview_data_from_files(files)
        
        def update_preview_type2(self, groups: Dict[str, Dict[str, Path]]):
            """Update preview for Type 2 files."""
            complete_groups = [g for g in groups.values() 
                             if 'E' in g and 'N' in g and 'Z' in g]
            
            total_files = sum(len(g) for g in complete_groups)
            total_size = sum(
                sum(f.stat().st_size for f in g.values())
                for g in complete_groups
            ) / (1024 * 1024)
            
            preview = f"Separate E/N/Z Files\n"
            preview += f"--------------------\n"
            preview += f"Complete Groups: {len(complete_groups)}\n"
            preview += f"Total Files: {total_files}\n"
            preview += f"Total Size: {total_size:.2f} MB\n"
            
            if complete_groups:
                first_group = list(groups.keys())[0]
                preview += f"\nFirst: {first_group}\n"
            
            preview += f"\nGroups will be merged"
            
            self.preview_text.setText(preview)
            
            # Load visual preview from first group if available
            if HAS_MATPLOTLIB and complete_groups:
                first_group_name = list(groups.keys())[0]
                first_group = groups[first_group_name]
                if 'E' in first_group:
                    self.load_preview_data_from_file(str(first_group['E']))
        
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

        # =====================================================================
        # VISUAL PREVIEW METHODS
        # =====================================================================
        
        def update_visual_preview(self):
            """Update the visual preview based on current data and view mode."""
            if not HAS_MATPLOTLIB or not hasattr(self, 'preview_fig'):
                return
            
            if self.preview_data is None:
                self._show_empty_preview()
                return
            
            try:
                self.preview_fig.clear()
                
                # Determine which view to show
                if hasattr(self, 'preview_radio_all') and self.preview_radio_all.isChecked():
                    self._plot_all_components()
                elif hasattr(self, 'preview_radio_e') and self.preview_radio_e.isChecked():
                    self._plot_single_component('E')
                elif hasattr(self, 'preview_radio_n') and self.preview_radio_n.isChecked():
                    self._plot_single_component('N')
                elif hasattr(self, 'preview_radio_z') and self.preview_radio_z.isChecked():
                    self._plot_single_component('Z')
                else:
                    self._plot_all_components()
                
                self.preview_fig.tight_layout()
                self.preview_canvas.draw()
                
            except Exception as e:
                self._show_error_preview(str(e))
        
        def _show_empty_preview(self):
            """Show empty preview with message."""
            if not HAS_MATPLOTLIB or not hasattr(self, 'preview_fig'):
                return
            
            self.preview_fig.clear()
            ax = self.preview_fig.add_subplot(111)
            ax.text(0.5, 0.5, 'No data to preview\n\nSelect a file to see waveform',
                   ha='center', va='center', fontsize=12, color='gray',
                   transform=ax.transAxes)
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_frame_on(False)
            self.preview_canvas.draw()
        
        def _show_error_preview(self, error_msg: str):
            """Show error message in preview."""
            if not HAS_MATPLOTLIB or not hasattr(self, 'preview_fig'):
                return
            
            self.preview_fig.clear()
            ax = self.preview_fig.add_subplot(111)
            ax.text(0.5, 0.5, f'Error loading preview:\n{error_msg}',
                   ha='center', va='center', fontsize=10, color='red',
                   transform=ax.transAxes)
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_frame_on(False)
            self.preview_canvas.draw()
            
            if hasattr(self, 'preview_status'):
                self.preview_status.setText(f"Error: {error_msg[:50]}...")
                self.preview_status.setStyleSheet("color: red; font-size: 9pt;")
        
        def _plot_all_components(self):
            """Plot all three components (E, N, Z) in subplots."""
            if self.preview_data is None:
                return
            
            data = self.preview_data
            colors = {'E': '#d62728', 'N': '#2ca02c', 'Z': '#1f77b4'}
            labels = {'E': 'East (E)', 'N': 'North (N)', 'Z': 'Vertical (Z)'}
            
            # Get time range parameters
            time_start = 0
            time_end = None
            use_time_range = False
            
            if self.load_mode == 'single' and hasattr(self, 'single_use_time_range') and self.single_use_time_range.isChecked():
                use_time_range = True
                start_dt = self.single_start_datetime.dateTime().toPyDateTime()
                end_dt = self.single_end_datetime.dateTime().toPyDateTime()
                duration_selected = (end_dt - start_dt).total_seconds()
            elif self.load_mode == 'multi_type1' and hasattr(self, 'type1_use_time_range') and self.type1_use_time_range.isChecked():
                use_time_range = True
                start_dt = self.type1_start_datetime.dateTime().toPyDateTime()
                end_dt = self.type1_end_datetime.dateTime().toPyDateTime()
                duration_selected = (end_dt - start_dt).total_seconds()
            
            # Create subplots
            axes = []
            components = ['E', 'N', 'Z']
            
            # Get sampling rate and create time vector
            fs = data.get('sampling_rate', 100)
            
            # Find normalization factor
            norm_factor = 0
            for comp in components:
                if comp in data and data[comp] is not None:
                    c_max = np.max(np.abs(data[comp]))
                    if c_max > norm_factor:
                        norm_factor = c_max
            
            if norm_factor == 0:
                norm_factor = 1
            
            for i, comp in enumerate(components):
                if i == 0:
                    ax = self.preview_fig.add_subplot(3, 1, i + 1)
                else:
                    ax = self.preview_fig.add_subplot(3, 1, i + 1, sharex=axes[0])
                axes.append(ax)
                
                if comp in data and data[comp] is not None:
                    comp_data = data[comp]
                    n_samples = len(comp_data)
                    time_vec = np.arange(n_samples) / fs
                    
                    # Normalize data for display
                    comp_data_norm = comp_data / norm_factor
                    
                    ax.plot(time_vec, comp_data_norm, color=colors[comp], linewidth=0.5, alpha=0.8)
                    ax.set_ylabel(labels[comp], fontsize=8)
                    ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
                    ax.axhline(0, color='k', linewidth=0.3, alpha=0.5)
                    
                    # Highlight selected time range if enabled
                    if use_time_range and duration_selected > 0:
                        # Calculate the relative position in the data
                        total_duration = n_samples / fs
                        # Shade the unselected regions
                        ax.axvspan(0, time_start, alpha=0.2, color='gray', label='Not selected')
                        if time_end is not None and time_end < total_duration:
                            ax.axvspan(time_end, total_duration, alpha=0.2, color='gray')
                    
                    if i == 0:
                        duration = n_samples / fs
                        ax.set_title(f'Waveform Preview | Duration: {duration:.1f}s | Rate: {fs:.0f} Hz', 
                                   fontsize=9, pad=5)
                    
                    if i == 2:
                        ax.set_xlabel('Time (s)', fontsize=8)
                    else:
                        ax.tick_params(labelbottom=False)
                else:
                    ax.text(0.5, 0.5, f'{comp} data not available',
                           ha='center', va='center', fontsize=9, color='gray',
                           transform=ax.transAxes)
                    ax.set_xticks([])
                    ax.set_yticks([])
            
            if hasattr(self, 'preview_status'):
                n_samples = len(data.get('E', data.get('N', data.get('Z', []))))
                duration = n_samples / fs if fs > 0 else 0
                self.preview_status.setText(f"Preview: {n_samples:,} samples | {duration:.1f}s | {fs:.0f} Hz")
                self.preview_status.setStyleSheet("color: green; font-size: 9pt;")
        
        def _plot_single_component(self, component: str):
            """Plot a single component with more detail."""
            if self.preview_data is None:
                return
            
            data = self.preview_data
            colors = {'E': '#d62728', 'N': '#2ca02c', 'Z': '#1f77b4'}
            labels = {'E': 'East (E)', 'N': 'North (N)', 'Z': 'Vertical (Z)'}
            
            ax = self.preview_fig.add_subplot(111)
            
            if component in data and data[component] is not None:
                comp_data = data[component]
                fs = data.get('sampling_rate', 100)
                n_samples = len(comp_data)
                time_vec = np.arange(n_samples) / fs
                
                ax.plot(time_vec, comp_data, color=colors[component], linewidth=0.5, alpha=0.9)
                ax.set_xlabel('Time (s)', fontsize=9)
                ax.set_ylabel(f'Amplitude', fontsize=9)
                ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
                
                # Add statistics
                stats_text = f'Min: {np.min(comp_data):.2e}\n'
                stats_text += f'Max: {np.max(comp_data):.2e}\n'
                stats_text += f'Mean: {np.mean(comp_data):.2e}\n'
                stats_text += f'Std: {np.std(comp_data):.2e}'
                ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                       verticalalignment='top', fontsize=7,
                       bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
                
                duration = n_samples / fs
                ax.set_title(f'{labels[component]} | {n_samples:,} samples | {duration:.1f}s | {fs:.0f} Hz',
                           fontsize=9, pad=5)
                
                if hasattr(self, 'preview_status'):
                    self.preview_status.setText(f"{labels[component]}: {n_samples:,} samples")
                    self.preview_status.setStyleSheet("color: green; font-size: 9pt;")
            else:
                ax.text(0.5, 0.5, f'{component} data not available',
                       ha='center', va='center', fontsize=12, color='gray',
                       transform=ax.transAxes)
                ax.set_xticks([])
                ax.set_yticks([])
        
        def refresh_visual_preview(self):
            """Force refresh the visual preview by reloading data."""
            if self.load_mode == 'single' and self.selected_files:
                self.load_preview_data_from_file(self.selected_files[0])
            elif self.load_mode == 'multi_type1' and self.selected_files:
                # Load preview from first selected file
                self.load_preview_data_from_file(self.selected_files[0])
            elif self.load_mode == 'multi_type2' and self.grouped_files:
                # Load preview from first group
                first_group = list(self.grouped_files.keys())[0] if self.grouped_files else None
                if first_group and 'E' in self.grouped_files[first_group]:
                    self.load_preview_data_from_file(str(self.grouped_files[first_group]['E']))
            else:
                self._show_empty_preview()
        
        def load_preview_data_from_file(self, file_path: str):
            """
            Load preview data from a file (quick scan, not full load).
            
            Args:
                file_path: Path to the file to preview
            """
            if not HAS_MATPLOTLIB:
                return
            
            try:
                path = Path(file_path)
                
                if hasattr(self, 'preview_status'):
                    self.preview_status.setText(f"Loading preview: {path.name}...")
                    self.preview_status.setStyleSheet("color: orange; font-size: 9pt;")
                
                # Process events to show status update
                from PyQt5.QtWidgets import QApplication
                QApplication.processEvents()
                
                if path.suffix.lower() in ['.mseed', '.miniseed']:
                    self._load_miniseed_preview(file_path)
                elif path.suffix.lower() in ['.txt', '.csv', '.dat', '.asc']:
                    self._load_text_preview(file_path)
                else:
                    self.preview_data = None
                    self._show_empty_preview()
                    if hasattr(self, 'preview_status'):
                        self.preview_status.setText(f"Unsupported format: {path.suffix}")
                        self.preview_status.setStyleSheet("color: orange; font-size: 9pt;")
                
            except Exception as e:
                self.preview_data = None
                self._show_error_preview(str(e))
        
        def load_preview_data_from_files(self, file_paths: List[Path]):
            """
            Load preview data from multiple MiniSEED files (merged).
            
            Args:
                file_paths: List of paths to the files to preview
            """
            if not HAS_MATPLOTLIB or not file_paths:
                return
            
            try:
                if hasattr(self, 'preview_status'):
                    self.preview_status.setText(f"Loading preview from {len(file_paths)} files...")
                    self.preview_status.setStyleSheet("color: orange; font-size: 9pt;")
                
                # Process events to show status update
                from PyQt5.QtWidgets import QApplication
                QApplication.processEvents()
                
                if not HAS_OBSPY:
                    self.preview_data = None
                    self._show_error_preview("ObsPy not installed")
                    return
                
                from obspy import read, Stream
                
                # Read and merge all streams
                combined_stream = Stream()
                for file_path in file_paths[:10]:  # Limit to first 10 for preview speed
                    try:
                        stream = read(str(file_path))
                        combined_stream += stream
                    except Exception:
                        continue
                
                if len(combined_stream) == 0:
                    self.preview_data = None
                    self._show_empty_preview()
                    return
                
                # Merge traces with same ID
                combined_stream.merge(method=1, fill_value='interpolate')
                
                # Extract data for each component
                preview_data = {
                    'E': None, 'N': None, 'Z': None,
                    'sampling_rate': combined_stream[0].stats.sampling_rate
                }
                
                for trace in combined_stream:
                    channel = trace.stats.channel.upper()
                    
                    # Map channel to component
                    if channel.endswith('E') or channel.endswith('1'):
                        preview_data['E'] = trace.data
                    elif channel.endswith('N') or channel.endswith('2'):
                        preview_data['N'] = trace.data
                    elif channel.endswith('Z') or channel.endswith('3'):
                        preview_data['Z'] = trace.data
                
                self.preview_data = preview_data
                self.update_visual_preview()
                
                if hasattr(self, 'preview_status'):
                    n_samples = len(preview_data.get('E', []) or preview_data.get('Z', []) or [])
                    fs = preview_data.get('sampling_rate', 0)
                    duration = n_samples / fs if fs > 0 else 0
                    self.preview_status.setText(f"Preview: {len(file_paths)} files | {n_samples:,} samples | {duration:.1f}s")
                    self.preview_status.setStyleSheet("color: green; font-size: 9pt;")
                
            except Exception as e:
                self.preview_data = None
                self._show_error_preview(str(e))
        
        def _load_miniseed_preview(self, file_path: str):
            """Load preview data from MiniSEED file."""
            try:
                from obspy import read
                
                # Read the file
                stream = read(file_path)
                
                if len(stream) == 0:
                    self.preview_data = None
                    self._show_empty_preview()
                    return
                
                # Extract data for each component
                preview_data = {
                    'E': None, 'N': None, 'Z': None,
                    'sampling_rate': stream[0].stats.sampling_rate
                }
                
                for trace in stream:
                    channel = trace.stats.channel.upper()
                    
                    # Map channel to component
                    if channel.endswith('E') or channel.endswith('1'):
                        preview_data['E'] = trace.data
                    elif channel.endswith('N') or channel.endswith('2'):
                        preview_data['N'] = trace.data
                    elif channel.endswith('Z') or channel.endswith('3'):
                        preview_data['Z'] = trace.data
                
                self.preview_data = preview_data
                self.update_visual_preview()
                
            except ImportError:
                self.preview_data = None
                self._show_error_preview("ObsPy not installed")
            except Exception as e:
                self.preview_data = None
                self._show_error_preview(str(e))
        
        def _load_text_preview(self, file_path: str):
            """Load preview data from text/CSV file."""
            try:
                # Read file with different encodings
                encodings = ['utf-8', 'latin-1', 'cp1252']
                lines = None
                
                for encoding in encodings:
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            lines = f.readlines()
                        break
                    except:
                        continue
                
                if not lines:
                    self.preview_data = None
                    self._show_error_preview("Could not read file")
                    return
                
                # Find data start and parse
                data_rows = []
                for line in lines:
                    line_stripped = line.strip()
                    if not line_stripped or line_stripped.startswith('#'):
                        continue
                    
                    try:
                        values = [float(x) for x in line_stripped.split()]
                        if len(values) >= 4:  # Time, E, N, Z
                            data_rows.append(values[:4])
                    except:
                        continue
                
                if not data_rows:
                    self.preview_data = None
                    self._show_error_preview("No numeric data found")
                    return
                
                # Convert to numpy array
                data_array = np.array(data_rows)
                
                # Calculate sampling rate from time column
                time_data = data_array[:, 0]
                dt = np.median(np.diff(time_data)) if len(time_data) > 1 else 0.01
                fs = 1.0 / dt if dt > 0 else 100.0
                
                self.preview_data = {
                    'E': data_array[:, 1],
                    'N': data_array[:, 2],
                    'Z': data_array[:, 3],
                    'sampling_rate': fs
                }
                
                self.update_visual_preview()
                
            except Exception as e:
                self.preview_data = None
                self._show_error_preview(str(e))


else:
    # Dummy class when PyQt5 not available
    class DataInputDialog:
        def __init__(self, *args, **kwargs):
            raise ImportError("PyQt5 is required for GUI functionality")
