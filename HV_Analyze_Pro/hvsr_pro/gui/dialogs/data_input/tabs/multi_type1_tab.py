"""
Multi-File Type 1 Tab
=====================

Tab for loading multiple MiniSEED files with 3 channels each.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional

try:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
        QPushButton, QLabel, QLineEdit, QCheckBox, QFileDialog,
        QTableWidget, QTableWidgetItem, QHeaderView, QListWidget,
        QProgressDialog, QMessageBox, QDialog
    )
    from PyQt5.QtCore import Qt, pyqtSignal
    from PyQt5.QtGui import QColor
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False

if HAS_PYQT5:
    from hvsr_pro.gui.dialogs.data_input.base_tab import DataInputTabBase
    from hvsr_pro.gui.dialogs.data_input.time_range_panel import TimeRangePanel
    from hvsr_pro.gui.dialogs.data_input.file_detector import (
        detect_type1_files, can_auto_detect_channels
    )


if HAS_PYQT5:
    class MultiType1Tab(DataInputTabBase):
        """
        Tab for loading multiple MiniSEED files with 3 channels each.
        
        Features:
        - Directory browsing
        - File detection with channel info
        - Per-file channel mapping
        - Time range selection
        
        Signals:
            directory_selected: Emitted when directory is selected
            files_detected: Emitted when files are detected (count)
            channel_mapping_changed: Emitted when mapping changes
        """
        
        directory_selected = pyqtSignal(str)
        files_detected = pyqtSignal(int)
        channel_mapping_changed = pyqtSignal(dict)
        
        def __init__(self, parent=None):
            self.all_files = []
            self.file_channels = {}
            self.channel_mapping = {}
            super().__init__(parent)
        
        def _init_ui(self):
            """Initialize the user interface."""
            layout = QVBoxLayout(self)
            
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
            
            path_layout = QHBoxLayout()
            self.dir_path_edit = QLineEdit()
            self.dir_path_edit.setPlaceholderText("No directory selected")
            self.dir_path_edit.setReadOnly(True)
            path_layout.addWidget(self.dir_path_edit)
            
            self.browse_btn = QPushButton("Browse Directory...")
            self.browse_btn.clicked.connect(self._on_browse)
            path_layout.addWidget(self.browse_btn)
            
            dir_layout.addLayout(path_layout)
            layout.addWidget(dir_group)
            
            # File list table
            files_group = QGroupBox("Detected Files")
            files_layout = QVBoxLayout(files_group)
            
            self.file_table = QTableWidget()
            self.file_table.setColumnCount(4)
            self.file_table.setHorizontalHeaderLabels([
                "File Name", "Channels", "Mapping Status", "Select"
            ])
            self.file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
            self.file_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
            self.file_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
            self.file_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
            self.file_table.setSelectionBehavior(QTableWidget.SelectRows)
            self.file_table.setAlternatingRowColors(True)
            self.file_table.itemSelectionChanged.connect(self._on_selection_changed)
            files_layout.addWidget(self.file_table)
            
            # Buttons
            btn_layout = QHBoxLayout()
            
            self.select_all_btn = QPushButton("Select All")
            self.select_all_btn.clicked.connect(self._select_all)
            btn_layout.addWidget(self.select_all_btn)
            
            self.select_none_btn = QPushButton("Select None")
            self.select_none_btn.clicked.connect(self._select_none)
            btn_layout.addWidget(self.select_none_btn)
            
            btn_layout.addStretch()
            
            self.map_btn = QPushButton("Map Channels for Selected")
            self.map_btn.setEnabled(False)
            self.map_btn.clicked.connect(self._map_channels)
            self.map_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FF9800;
                    color: white;
                    font-weight: bold;
                    padding: 6px 12px;
                    border-radius: 4px;
                }
                QPushButton:hover { background-color: #F57C00; }
                QPushButton:disabled { background-color: #ccc; color: #888; }
            """)
            btn_layout.addWidget(self.map_btn)
            
            files_layout.addLayout(btn_layout)
            
            self.count_label = QLabel("0 files detected | 0 selected | 0 mapped")
            files_layout.addWidget(self.count_label)
            
            tip_label = QLabel(
                "<i>Tip: Select files and click 'Map Channels' to configure E/N/Z mapping.</i>"
            )
            tip_label.setWordWrap(True)
            tip_label.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")
            files_layout.addWidget(tip_label)
            
            layout.addWidget(files_group)
            
            # Time range panel
            self.time_range_panel = TimeRangePanel(title="Time Range (Optional)")
            layout.addWidget(self.time_range_panel)
        
        def _on_browse(self):
            """Handle browse button click."""
            dir_path = QFileDialog.getExistingDirectory(
                self, "Select Directory with MiniSEED Files"
            )
            
            if dir_path:
                self.dir_path_edit.setText(dir_path)
                self._detect_files(dir_path)
                self.directory_selected.emit(dir_path)
        
        def _detect_files(self, dir_path: str):
            """Detect MiniSEED files in directory."""
            progress = QProgressDialog(
                "Scanning files...", "Cancel", 0, 100, self
            )
            progress.setWindowModality(Qt.WindowModal)
            progress.setMinimumDuration(500)
            
            self.file_table.setRowCount(0)
            self.all_files = []
            self.file_channels = {}
            self.channel_mapping = {}
            
            # Use file detector
            mseed_files, file_channels = detect_type1_files(dir_path)
            
            self.all_files = [str(f) for f in mseed_files]
            self.file_channels = file_channels
            
            # Populate table
            self.file_table.setRowCount(len(mseed_files))
            
            for i, file in enumerate(mseed_files):
                progress.setValue(int((i / max(len(mseed_files), 1)) * 100))
                if progress.wasCanceled():
                    break
                
                file_path = str(file)
                
                # Get channel info
                channels_str = "N/A"
                mapping_status = "Unknown"
                
                if file_path in self.file_channels:
                    channels_info = self.file_channels[file_path]
                    channel_codes = [ch['code'] for ch in channels_info]
                    channels_str = ", ".join(channel_codes)
                    
                    if can_auto_detect_channels(channel_codes):
                        mapping_status = "Auto-detect"
                    else:
                        mapping_status = "Needs mapping"
                
                # File name
                name_item = QTableWidgetItem(file.name)
                name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
                name_item.setData(Qt.UserRole, file_path)
                self.file_table.setItem(i, 0, name_item)
                
                # Channels
                channels_item = QTableWidgetItem(channels_str)
                channels_item.setFlags(channels_item.flags() & ~Qt.ItemIsEditable)
                self.file_table.setItem(i, 1, channels_item)
                
                # Status
                status_item = QTableWidgetItem(mapping_status)
                status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
                if "Auto" in mapping_status:
                    status_item.setForeground(QColor(0, 128, 0))
                elif "Needs" in mapping_status:
                    status_item.setForeground(QColor(255, 152, 0))
                self.file_table.setItem(i, 2, status_item)
                
                # Checkbox
                checkbox = QCheckBox()
                checkbox.setChecked(False)
                checkbox.stateChanged.connect(self._update_count)
                
                checkbox_widget = QWidget()
                checkbox_layout = QHBoxLayout(checkbox_widget)
                checkbox_layout.addWidget(checkbox)
                checkbox_layout.setAlignment(Qt.AlignCenter)
                checkbox_layout.setContentsMargins(0, 0, 0, 0)
                self.file_table.setCellWidget(i, 3, checkbox_widget)
            
            progress.setValue(100)
            
            self._update_count()
            self.files_detected.emit(len(mseed_files))
        
        def _select_all(self):
            """Select all files."""
            for i in range(self.file_table.rowCount()):
                widget = self.file_table.cellWidget(i, 3)
                if widget:
                    checkbox = widget.findChild(QCheckBox)
                    if checkbox:
                        checkbox.setChecked(True)
            self._update_count()
        
        def _select_none(self):
            """Deselect all files."""
            for i in range(self.file_table.rowCount()):
                widget = self.file_table.cellWidget(i, 3)
                if widget:
                    checkbox = widget.findChild(QCheckBox)
                    if checkbox:
                        checkbox.setChecked(False)
            self._update_count()
        
        def _on_selection_changed(self):
            """Handle table selection change."""
            selected_rows = self.file_table.selectionModel().selectedRows()
            self.map_btn.setEnabled(len(selected_rows) > 0)
        
        def _update_count(self):
            """Update count label and files list."""
            total = self.file_table.rowCount()
            selected = 0
            selected_files = []
            
            for i in range(total):
                widget = self.file_table.cellWidget(i, 3)
                if widget:
                    checkbox = widget.findChild(QCheckBox)
                    if checkbox and checkbox.isChecked():
                        selected += 1
                        name_item = self.file_table.item(i, 0)
                        if name_item:
                            selected_files.append(name_item.data(Qt.UserRole))
            
            mapped = len(self.channel_mapping)
            self.count_label.setText(f"{total} files | {selected} selected | {mapped} mapped")
            
            self.set_files(selected_files)
        
        def _map_channels(self):
            """Show channel mapping dialog for selected files."""
            try:
                from hvsr_pro.gui.dialogs import ChannelMapperDialog
                
                selected_rows = self.file_table.selectionModel().selectedRows()
                if not selected_rows:
                    QMessageBox.warning(self, "No Selection", 
                                       "Select files to map channels.")
                    return
                
                # Get selected file paths
                selected_files = []
                for row_index in selected_rows:
                    row = row_index.row()
                    name_item = self.file_table.item(row, 0)
                    if name_item:
                        selected_files.append(name_item.data(Qt.UserRole))
                
                if not selected_files:
                    return
                
                # Group by channel structure
                channel_groups = {}
                for file_path in selected_files:
                    if file_path in self.file_channels:
                        channels_info = self.file_channels[file_path]
                        signature = tuple(sorted(ch['code'] for ch in channels_info))
                        
                        if signature not in channel_groups:
                            channel_groups[signature] = {
                                'channels_info': channels_info,
                                'files': []
                            }
                        channel_groups[signature]['files'].append(file_path)
                
                # Show dialog for each group
                for signature, group_data in channel_groups.items():
                    channels_info = group_data['channels_info']
                    group_files = group_data['files']
                    
                    sample_file = Path(group_files[0]).name
                    dlg = ChannelMapperDialog(channels_info, sample_file, self)
                    
                    if dlg.exec_() == QDialog.Accepted:
                        mapping = dlg.get_mapping()
                        for file_path in group_files:
                            self.channel_mapping[file_path] = mapping
                
                self._update_mapping_status()
                self._update_count()
                self.channel_mapping_changed.emit(self.channel_mapping)
                
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Channel mapping failed:\n{str(e)}")
        
        def _update_mapping_status(self):
            """Update mapping status in table."""
            for i in range(self.file_table.rowCount()):
                name_item = self.file_table.item(i, 0)
                if name_item:
                    file_path = name_item.data(Qt.UserRole)
                    status_item = self.file_table.item(i, 2)
                    
                    if file_path in self.channel_mapping:
                        mapping = self.channel_mapping[file_path]
                        status = f"Mapped ({mapping.get('E', '?')}/{mapping.get('N', '?')}/{mapping.get('Z', '?')})"
                        status_item.setText(status)
                        status_item.setForeground(QColor(0, 128, 0))
        
        def get_time_range(self) -> Dict[str, Any]:
            """Get time range settings."""
            return self.time_range_panel.get_time_range()
        
        def get_result(self) -> Dict[str, Any]:
            """Get complete result dictionary."""
            result = super().get_result()
            result['time_range'] = self.get_time_range()
            result['channel_mapping'] = self.channel_mapping
            return result
        
        def clear(self):
            """Clear all selections."""
            super().clear()
            self.dir_path_edit.clear()
            self.file_table.setRowCount(0)
            self.all_files = []
            self.file_channels = {}
            self.channel_mapping = {}
            self._update_count()

else:
    class MultiType1Tab:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass
