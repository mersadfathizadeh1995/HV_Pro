"""
Loaded Data Tree Widget for HVSR Pro
=====================================

Hierarchical tree widget for displaying loaded seismic data files with grouping.

Features:
- Tree structure with parent groups and child files
- Parent node = group of loaded files (collapsible)
- Child nodes = individual files
- Clicking parent previews ALL files in group
- Clicking child previews single file
- Context menu for file/group operations
"""

from pathlib import Path
from typing import Optional, Dict, List

try:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget,
        QTreeWidgetItem, QPushButton, QLabel, QMenu,
        QMessageBox
    )
    from PyQt5.QtCore import Qt, pyqtSignal
    from PyQt5.QtGui import QFont, QColor
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


if HAS_PYQT5:

    class LoadedDataTree(QWidget):
        """
        Widget for managing and displaying loaded data files in hierarchical tree.

        Features:
        - Tree view with parent groups and child files
        - Group selection (preview all files)
        - Individual file selection
        - Context menu operations
        - Add/remove files and groups
        """

        # Signals
        file_selected = pyqtSignal(str)  # file_path
        group_selected = pyqtSignal(str, list)  # group_id, list of file_paths
        file_removed = pyqtSignal(str)  # file_path
        group_removed = pyqtSignal(str)  # group_id
        files_cleared = pyqtSignal()
        load_more_requested = pyqtSignal()

        def __init__(self, parent=None):
            super().__init__(parent)

            # Storage
            # groups: group_id -> {'name': str, 'files': {file_path: metadata}, 'item': QTreeWidgetItem}
            self.groups = {}

            # Total file count across all groups
            self.total_file_count = 0

            # Create UI
            self.init_ui()

        def init_ui(self):
            """Initialize user interface."""
            layout = QVBoxLayout(self)

            # Title
            title = QLabel("Loaded Files")
            title_font = QFont()
            title_font.setPointSize(10)
            title_font.setBold(True)
            title.setFont(title_font)
            layout.addWidget(title)

            # File count label
            self.count_label = QLabel("0 files loaded")
            self.count_label.setStyleSheet("color: gray;")
            layout.addWidget(self.count_label)

            # Tree widget
            self.tree_widget = QTreeWidget()
            self.tree_widget.setColumnCount(2)
            self.tree_widget.setHeaderLabels(['File/Group', 'Details'])
            self.tree_widget.itemClicked.connect(self.on_item_clicked)
            self.tree_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
            self.tree_widget.setContextMenuPolicy(Qt.CustomContextMenu)
            self.tree_widget.customContextMenuRequested.connect(self.show_context_menu)

            # Set column widths
            self.tree_widget.setColumnWidth(0, 250)
            self.tree_widget.setColumnWidth(1, 100)

            # Set font for tree items
            tree_font = QFont("Courier New", 9)
            self.tree_widget.setFont(tree_font)

            layout.addWidget(self.tree_widget)

            # Button panel
            button_layout = QHBoxLayout()

            self.load_more_btn = QPushButton("Load More")
            self.load_more_btn.clicked.connect(self.on_load_more)
            self.load_more_btn.setToolTip("Load additional data files")
            button_layout.addWidget(self.load_more_btn)

            self.remove_btn = QPushButton("Remove")
            self.remove_btn.clicked.connect(self.remove_selected)
            self.remove_btn.setEnabled(False)
            self.remove_btn.setToolTip("Remove selected file or group")
            button_layout.addWidget(self.remove_btn)

            layout.addLayout(button_layout)

            # Clear all button
            self.clear_all_btn = QPushButton("Clear All")
            self.clear_all_btn.clicked.connect(self.clear_all)
            self.clear_all_btn.setEnabled(False)
            self.clear_all_btn.setToolTip("Remove all loaded files and groups")
            layout.addWidget(self.clear_all_btn)

            # Connect selection changed
            self.tree_widget.itemSelectionChanged.connect(self.on_selection_changed)

        def add_file_group(self, group_id: str, group_name: str, files_dict: dict):
            """
            Add a group of files as parent with children.

            Args:
                group_id: Unique identifier for the group
                group_name: Display name for the group
                files_dict: Dict of {file_path: metadata}
                           metadata should contain: 'duration', 'sampling_rate', 'size_mb', 'status'
            """
            # Check if group already exists
            if group_id in self.groups:
                # Update existing group
                self.update_group(group_id, group_name, files_dict)
                return

            # Create parent item for group
            file_count = len(files_dict)
            total_duration = sum(meta.get('duration', 0) for meta in files_dict.values())

            parent_item = QTreeWidgetItem([
                f"📁 {group_name}",
                f"{file_count} files | {total_duration:.1f}s total"
            ])

            # Store group metadata
            parent_item.setData(0, Qt.UserRole, {
                'type': 'group',
                'id': group_id,
                'name': group_name
            })

            # Make group name bold
            font = parent_item.font(0)
            font.setBold(True)
            parent_item.setFont(0, font)
            parent_item.setFont(1, font)

            # Set group color
            parent_item.setForeground(0, QColor('#2196F3'))  # Blue
            parent_item.setForeground(1, QColor('#2196F3'))

            self.tree_widget.addTopLevelItem(parent_item)

            # Add child items for each file
            for file_path, metadata in files_dict.items():
                self.add_file_to_group(parent_item, file_path, metadata)

            # Expand group by default
            parent_item.setExpanded(True)

            # Store group reference
            self.groups[group_id] = {
                'name': group_name,
                'files': files_dict.copy(),
                'item': parent_item
            }

            # Update UI
            self.total_file_count += file_count
            self.update_count_label()
            self.clear_all_btn.setEnabled(True)

        def add_file_to_group(self, parent_item: QTreeWidgetItem, file_path: str, metadata: dict):
            """
            Add a file as child to a group parent item.

            Args:
                parent_item: Parent QTreeWidgetItem
                file_path: Full path to the file
                metadata: Dict with 'duration', 'sampling_rate', 'size_mb', 'status'
            """
            filename = Path(file_path).name
            duration = metadata.get('duration', 0)
            sampling_rate = metadata.get('sampling_rate', 0)
            size_mb = metadata.get('size_mb', 0)
            status = metadata.get('status', 'loaded')

            # Status icons
            status_icons = {
                'loaded': '✓',
                'processing': '⚙',
                'error': '❌',
                'pending': '○'
            }
            icon = status_icons.get(status, '○')

            # Create child item
            child_item = QTreeWidgetItem([
                f"  {icon} 📊 {filename}",
                f"{duration:.1f}s @ {sampling_rate:.0f}Hz"
            ])

            # Store file metadata
            child_item.setData(0, Qt.UserRole, {
                'type': 'file',
                'path': file_path,
                'metadata': metadata
            })

            # Color coding based on status
            if status == 'error':
                child_item.setForeground(0, QColor('red'))
            elif status == 'processing':
                child_item.setForeground(0, QColor('orange'))

            parent_item.addChild(child_item)

        def update_group(self, group_id: str, group_name: str, files_dict: dict):
            """
            Update an existing group with new files.

            Args:
                group_id: Group identifier
                group_name: Updated group name
                files_dict: Updated files dictionary
            """
            if group_id not in self.groups:
                return

            group = self.groups[group_id]
            parent_item = group['item']

            # Update group data
            old_file_count = len(group['files'])
            new_file_count = len(files_dict)
            total_duration = sum(meta.get('duration', 0) for meta in files_dict.values())

            # Update parent item text
            parent_item.setText(0, f"📁 {group_name}")
            parent_item.setText(1, f"{new_file_count} files | {total_duration:.1f}s total")

            # Clear existing children
            parent_item.takeChildren()

            # Add updated files
            for file_path, metadata in files_dict.items():
                self.add_file_to_group(parent_item, file_path, metadata)

            # Update stored data
            group['name'] = group_name
            group['files'] = files_dict.copy()

            # Update total count
            self.total_file_count += (new_file_count - old_file_count)
            self.update_count_label()

        def remove_file(self, file_path: str):
            """
            Remove a specific file from the tree.

            Args:
                file_path: Path to the file to remove
            """
            # Find the file in groups
            for group_id, group in self.groups.items():
                if file_path in group['files']:
                    # Remove from group's file dict
                    del group['files'][file_path]

                    # Find and remove the tree item
                    parent_item = group['item']
                    for i in range(parent_item.childCount()):
                        child = parent_item.child(i)
                        data = child.data(0, Qt.UserRole)
                        if data['type'] == 'file' and data['path'] == file_path:
                            parent_item.removeChild(child)
                            break

                    # Update parent item details
                    file_count = len(group['files'])
                    total_duration = sum(meta.get('duration', 0) for meta in group['files'].values())
                    parent_item.setText(1, f"{file_count} files | {total_duration:.1f}s total")

                    # If group is now empty, remove the group
                    if file_count == 0:
                        self.remove_group(group_id)

                    # Emit signal
                    self.file_removed.emit(file_path)

                    # Update count
                    self.total_file_count -= 1
                    self.update_count_label()

                    return

        def remove_group(self, group_id: str):
            """
            Remove an entire group.

            Args:
                group_id: Group identifier
            """
            if group_id not in self.groups:
                return

            group = self.groups[group_id]
            parent_item = group['item']
            file_count = len(group['files'])

            # Remove from tree
            index = self.tree_widget.indexOfTopLevelItem(parent_item)
            self.tree_widget.takeTopLevelItem(index)

            # Remove from storage
            del self.groups[group_id]

            # Emit signal
            self.group_removed.emit(group_id)

            # Update count
            self.total_file_count -= file_count
            self.update_count_label()

            # Disable clear button if no more groups
            if len(self.groups) == 0:
                self.clear_all_btn.setEnabled(False)

        def remove_selected(self):
            """Remove selected file or group."""
            selected_items = self.tree_widget.selectedItems()

            if not selected_items:
                return

            item = selected_items[0]
            data = item.data(0, Qt.UserRole)

            if data['type'] == 'group':
                # Confirm group removal
                group_id = data['id']
                group = self.groups.get(group_id)
                if group:
                    file_count = len(group['files'])
                    reply = QMessageBox.question(
                        self,
                        "Confirm Removal",
                        f"Remove group '{group['name']}' with {file_count} file(s)?",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    )
                    if reply == QMessageBox.Yes:
                        self.remove_group(group_id)
            else:
                # Confirm file removal
                file_path = data['path']
                filename = Path(file_path).name
                reply = QMessageBox.question(
                    self,
                    "Confirm Removal",
                    f"Remove file '{filename}'?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self.remove_file(file_path)

        def clear_all(self):
            """Clear all groups and files."""
            if self.tree_widget.topLevelItemCount() == 0:
                return

            # Confirm clear
            reply = QMessageBox.question(
                self,
                "Confirm Clear",
                f"Remove all groups and {self.total_file_count} file(s)?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.groups.clear()
                self.tree_widget.clear()
                self.total_file_count = 0
                self.files_cleared.emit()
                self.update_count_label()
                self.clear_all_btn.setEnabled(False)

        def get_group_files(self, group_id: str) -> List[str]:
            """
            Get all file paths in a group.

            Args:
                group_id: Group identifier

            Returns:
                List of file paths
            """
            if group_id in self.groups:
                return list(self.groups[group_id]['files'].keys())
            return []

        def get_all_files(self) -> List[str]:
            """
            Get all loaded file paths across all groups.

            Returns:
                List of all file paths
            """
            all_files = []
            for group in self.groups.values():
                all_files.extend(group['files'].keys())
            return all_files

        def get_selected_item_info(self) -> Optional[dict]:
            """
            Get information about currently selected item.

            Returns:
                Dict with 'type' ('group' or 'file') and relevant data, or None
            """
            selected_items = self.tree_widget.selectedItems()
            if not selected_items:
                return None

            item = selected_items[0]
            data = item.data(0, Qt.UserRole)

            if data['type'] == 'group':
                group_id = data['id']
                return {
                    'type': 'group',
                    'id': group_id,
                    'files': self.get_group_files(group_id)
                }
            else:
                return {
                    'type': 'file',
                    'path': data['path']
                }

        def update_count_label(self):
            """Update file count label."""
            if self.total_file_count == 0:
                self.count_label.setText("No files loaded")
            elif self.total_file_count == 1:
                self.count_label.setText("1 file loaded")
            else:
                group_count = len(self.groups)
                self.count_label.setText(
                    f"{self.total_file_count} files loaded ({group_count} group{'s' if group_count != 1 else ''})"
                )

        def on_item_clicked(self, item, column):
            """Handle item click - emit appropriate signal."""
            data = item.data(0, Qt.UserRole)

            if data['type'] == 'group':
                # Parent clicked - get all child file paths
                group_id = data['id']
                file_paths = self.get_group_files(group_id)
                self.group_selected.emit(group_id, file_paths)
            else:
                # Child clicked - single file
                file_path = data['path']
                self.file_selected.emit(file_path)

        def on_item_double_clicked(self, item, column):
            """Handle item double click."""
            # Same behavior as single click for now
            self.on_item_clicked(item, column)

        def on_selection_changed(self):
            """Handle selection change."""
            selected_count = len(self.tree_widget.selectedItems())
            self.remove_btn.setEnabled(selected_count > 0)

        def on_load_more(self):
            """Handle 'Load More' button click."""
            self.load_more_requested.emit()

        def show_context_menu(self, position):
            """Show context menu for tree items."""
            item = self.tree_widget.itemAt(position)

            if not item:
                return

            data = item.data(0, Qt.UserRole)
            menu = QMenu(self)

            if data['type'] == 'group':
                # Group context menu
                group_id = data['id']

                # Expand/Collapse
                if item.isExpanded():
                    collapse_action = menu.addAction("Collapse")
                    collapse_action.triggered.connect(lambda: item.setExpanded(False))
                else:
                    expand_action = menu.addAction("Expand")
                    expand_action.triggered.connect(lambda: item.setExpanded(True))

                menu.addSeparator()

                # Preview group
                preview_action = menu.addAction("Preview All Files")
                preview_action.triggered.connect(lambda: self.on_item_clicked(item, 0))

                menu.addSeparator()

                # Remove group
                remove_action = menu.addAction("Remove Group")
                remove_action.triggered.connect(lambda: self.remove_group(group_id))
            else:
                # File context menu
                file_path = data['path']

                # Preview file
                preview_action = menu.addAction("Preview File")
                preview_action.triggered.connect(lambda: self.file_selected.emit(file_path))

                menu.addSeparator()

                # Remove file
                remove_action = menu.addAction("Remove File")
                remove_action.triggered.connect(lambda: self.remove_file(file_path))

                menu.addSeparator()

                # Copy path
                copy_action = menu.addAction("Copy Path")
                copy_action.triggered.connect(lambda: self.copy_file_path(file_path))

            # Show menu
            menu.exec_(self.tree_widget.mapToGlobal(position))

        def copy_file_path(self, file_path: str):
            """Copy file path to clipboard."""
            from PyQt5.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(file_path)

        def update_file_in_current_group(self, file_path: str, metadata: dict):
            """
            Add or update a file in the current group.

            Args:
                file_path: Path to the file
                metadata: File metadata dict
            """
            # Get current group
            current_items = self.selectedItems()
            if not current_items:
                # No selection - use the last added group (most recent)
                if not self.groups:
                    return
                group_id = list(self.groups.keys())[-1]
            else:
                item = current_items[0]
                data = item.data(0, Qt.UserRole)
                if data['type'] == 'group':
                    group_id = data['group_id']
                elif data['type'] == 'file':
                    # Get parent group
                    parent = item.parent()
                    if parent:
                        group_data = parent.data(0, Qt.UserRole)
                        group_id = group_data['group_id']
                    else:
                        return
                else:
                    return

            if group_id not in self.groups:
                return

            group = self.groups[group_id]
            parent_item = group['item']

            # Add file to group's file dict
            group['files'][file_path] = metadata

            # Add to tree
            self.add_file_to_group(parent_item, file_path, metadata)

            # Update parent item summary
            file_count = len(group['files'])
            total_duration = sum(meta.get('duration', 0) for meta in group['files'].values())
            parent_item.setText(1, f"{file_count} files | {total_duration:.1f}s total")

            # Update count
            self.total_file_count += 1
            self.update_count_label()

        def select_current_group(self):
            """Select the most recently added group in the tree."""
            if not self.groups:
                return

            # Get the last added group
            group_id = list(self.groups.keys())[-1]
            group = self.groups[group_id]
            parent_item = group['item']

            # Clear selection and select this group
            self.clearSelection()
            parent_item.setSelected(True)

            # Expand the group to show files
            parent_item.setExpanded(True)

            # Emit group selected signal
            self.group_selected.emit(group_id, list(group['files'].keys()))


else:
    # Dummy class when PyQt5 not available
    class LoadedDataTree:
        def __init__(self, *args, **kwargs):
            raise ImportError("PyQt5 is required for GUI functionality")
