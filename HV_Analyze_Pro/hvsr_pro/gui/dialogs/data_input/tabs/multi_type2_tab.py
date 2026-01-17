"""
Multi-File Type 2 Tab
=====================

Tab for loading separate E, N, Z MiniSEED files.
"""

from pathlib import Path
from typing import Dict, Any, List

try:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
        QPushButton, QLabel, QLineEdit, QFileDialog,
        QListWidget, QListWidgetItem
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
        detect_type2_files, group_component_files
    )


if HAS_PYQT5:
    class MultiType2Tab(DataInputTabBase):
        """
        Tab for loading separate E, N, Z files.
        
        Features:
        - Directory browsing
        - Automatic pattern matching
        - Group selection
        - Time range selection
        
        Signals:
            directory_selected: Emitted when directory is selected
            groups_detected: Emitted when groups are detected (count)
        """
        
        directory_selected = pyqtSignal(str)
        groups_detected = pyqtSignal(int)
        
        def __init__(self, parent=None):
            self.all_groups = {}
            self.group_names = []
            self.selected_groups = {}
            super().__init__(parent)
        
        def _init_ui(self):
            """Initialize the user interface."""
            layout = QVBoxLayout(self)
            
            # Instructions
            info = QLabel(
                "Load MiniSEED files where E, N, Z components are in separate files.\n"
                "Example: XX01_E.miniseed, XX01_N.miniseed, XX01_Z.miniseed\n"
                "Files will be automatically grouped by pattern matching."
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
            
            # Pattern matching results
            pattern_group = QGroupBox("Detected File Groups")
            pattern_layout = QVBoxLayout(pattern_group)
            
            pattern_info = QLabel("Detected file groups (E, N, Z):")
            pattern_layout.addWidget(pattern_info)
            
            self.group_list = QListWidget()
            self.group_list.setSelectionMode(QListWidget.MultiSelection)
            self.group_list.itemSelectionChanged.connect(self._on_selection_changed)
            pattern_layout.addWidget(self.group_list)
            
            # Buttons
            btn_layout = QHBoxLayout()
            
            self.select_all_btn = QPushButton("Select All")
            self.select_all_btn.clicked.connect(lambda: self.group_list.selectAll())
            btn_layout.addWidget(self.select_all_btn)
            
            self.select_none_btn = QPushButton("Select None")
            self.select_none_btn.clicked.connect(lambda: self.group_list.clearSelection())
            btn_layout.addWidget(self.select_none_btn)
            
            pattern_layout.addLayout(btn_layout)
            
            self.count_label = QLabel("0 groups detected | 0 selected")
            pattern_layout.addWidget(self.count_label)
            
            layout.addWidget(pattern_group)
            
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
                self._detect_groups(dir_path)
                self.directory_selected.emit(dir_path)
        
        def _detect_groups(self, dir_path: str):
            """Detect file groups in directory."""
            self.group_list.clear()
            self.all_groups = {}
            self.group_names = []
            self.selected_groups = {}
            
            # Detect groups
            groups = detect_type2_files(dir_path)
            self.all_groups = groups
            
            # Populate list
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
                
                self.group_list.addItem(item)
                self.group_names.append(base_name)
                
                # Do not auto-select
                item.setSelected(False)
            
            self._update_count()
            self.groups_detected.emit(len(groups))
        
        def _on_selection_changed(self):
            """Handle selection change."""
            self._update_selection()
            self._update_count()
        
        def _update_selection(self):
            """Update selected groups based on list selection."""
            selected_indices = [
                self.group_list.row(item) 
                for item in self.group_list.selectedItems()
            ]
            
            selected_names = [self.group_names[i] for i in selected_indices]
            
            self.selected_groups = {
                name: self.all_groups[name] 
                for name in selected_names
            }
            
            # Update files list (for base class)
            all_files = []
            for name, components in self.selected_groups.items():
                for comp, path in components.items():
                    all_files.append(str(path))
            
            self._files = all_files
        
        def _update_count(self):
            """Update count label."""
            total = len(self.all_groups)
            total_complete = sum(
                1 for g in self.all_groups.values() 
                if all(c in g for c in ['E', 'N', 'Z'])
            )
            
            selected_complete = sum(
                1 for g in self.selected_groups.values()
                if all(c in g for c in ['E', 'N', 'Z'])
            )
            
            if selected_complete > 0:
                self.count_label.setText(
                    f"{total} groups ({total_complete} complete) | {selected_complete} selected"
                )
            else:
                self.count_label.setText(
                    f"{total} groups ({total_complete} complete) | 0 selected"
                )
            
            # Validation
            self._is_valid = selected_complete > 0
            self.validation_changed.emit(
                self._is_valid,
                "" if self._is_valid else "No complete groups selected"
            )
        
        def get_groups(self) -> Dict[str, Dict[str, Path]]:
            """Get selected groups."""
            return self.selected_groups
        
        def get_time_range(self) -> Dict[str, Any]:
            """Get time range settings."""
            return self.time_range_panel.get_time_range()
        
        def get_result(self) -> Dict[str, Any]:
            """Get complete result dictionary."""
            result = super().get_result()
            result['groups'] = self.get_groups()
            result['time_range'] = self.get_time_range()
            return result
        
        def clear(self):
            """Clear all selections."""
            super().clear()
            self.dir_path_edit.clear()
            self.group_list.clear()
            self.all_groups = {}
            self.group_names = []
            self.selected_groups = {}
            self._update_count()

else:
    class MultiType2Tab:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass
