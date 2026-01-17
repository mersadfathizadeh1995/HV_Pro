"""
Loaded Data List Widget for HVSR Pro
=====================================

Custom list widget for displaying loaded seismic data files with metadata.

Features:
- Display file information (name, size, duration, sampling rate)
- File type icons
- Status indicators
- Context menu for file operations
- Multiple selection support
"""

from pathlib import Path
from typing import Optional, Dict, List

try:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QListWidget,
        QListWidgetItem, QPushButton, QLabel, QMenu,
        QMessageBox
    )
    from PyQt5.QtCore import Qt, pyqtSignal
    from PyQt5.QtGui import QFont, QColor, QIcon
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


if HAS_PYQT5:

    class LoadedDataListItem(QListWidgetItem):
        """Custom list item for loaded data file."""

        def __init__(self, file_path: str, metadata: dict):
            """
            Initialize loaded data item.

            Args:
                file_path: Full path to the data file
                metadata: Dict with 'duration', 'sampling_rate', 'size_mb', 'status'
            """
            super().__init__()

            self.file_path = file_path
            self.metadata = metadata

            # Format display text
            self.update_display()

        def update_display(self):
            """Update display text based on metadata."""
            path = Path(self.file_path)
            filename = path.name
            size_mb = self.metadata.get('size_mb', 0)
            duration = self.metadata.get('duration', 0)
            sampling_rate = self.metadata.get('sampling_rate', 0)
            status = self.metadata.get('status', 'loaded')

            # Status icons
            status_icons = {
                'loaded': '[OK]',
                'processing': '[...]',
                'error': '[X]',
                'pending': '[ ]'
            }
            icon = status_icons.get(status, '[ ]')

            # File type icon
            if path.suffix in ['.mseed', '.miniseed']:
                file_icon = '[MS]'
            else:
                file_icon = '[TXT]'

            # Build display text
            text = f"{icon} {file_icon} {filename}\n"
            text += f"   {duration:.1f}s @ {sampling_rate:.1f} Hz | {size_mb:.2f} MB"

            self.setText(text)

            # Color coding based on status
            if status == 'error':
                self.setForeground(QColor('red'))
            elif status == 'processing':
                self.setForeground(QColor('orange'))
            else:
                self.setForeground(QColor('black'))


    class LoadedDataList(QWidget):
        """
        Widget for managing and displaying loaded data files.

        Features:
        - List of loaded files with metadata
        - Add/remove files
        - File selection
        - Context menu operations
        """

        # Signals
        file_selected = pyqtSignal(str)  # file_path
        file_removed = pyqtSignal(str)  # file_path
        files_cleared = pyqtSignal()
        load_more_requested = pyqtSignal()

        def __init__(self, parent=None):
            super().__init__(parent)

            # Storage: file_path -> metadata
            self.loaded_files = {}

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

            # List widget
            self.list_widget = QListWidget()
            self.list_widget.setSelectionMode(QListWidget.ExtendedSelection)
            self.list_widget.itemClicked.connect(self.on_item_clicked)
            self.list_widget.itemDoubleClicked.connect(self.on_item_double_clicked)
            self.list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
            self.list_widget.customContextMenuRequested.connect(self.show_context_menu)

            # Set font for list items
            list_font = QFont("Courier New", 9)
            self.list_widget.setFont(list_font)

            layout.addWidget(self.list_widget)

            # Button panel
            button_layout = QHBoxLayout()

            self.load_more_btn = QPushButton("Load More")
            self.load_more_btn.clicked.connect(self.on_load_more)
            self.load_more_btn.setToolTip("Load additional data files")
            button_layout.addWidget(self.load_more_btn)

            self.remove_btn = QPushButton("Remove")
            self.remove_btn.clicked.connect(self.remove_selected)
            self.remove_btn.setEnabled(False)
            self.remove_btn.setToolTip("Remove selected files")
            button_layout.addWidget(self.remove_btn)

            layout.addLayout(button_layout)

            # Clear all button
            self.clear_all_btn = QPushButton("Clear All")
            self.clear_all_btn.clicked.connect(self.clear_all)
            self.clear_all_btn.setEnabled(False)
            self.clear_all_btn.setToolTip("Remove all loaded files")
            layout.addWidget(self.clear_all_btn)

            # Connect selection changed
            self.list_widget.itemSelectionChanged.connect(self.on_selection_changed)

        def add_file(self, file_path: str, metadata: dict):
            """
            Add file to the loaded data list.

            Args:
                file_path: Full path to the data file
                metadata: Dict with 'duration', 'sampling_rate', 'size_mb', 'status'
            """
            # Check if already loaded
            if file_path in self.loaded_files:
                # Update metadata
                self.loaded_files[file_path] = metadata
                # Find and update item
                for i in range(self.list_widget.count()):
                    item = self.list_widget.item(i)
                    if isinstance(item, LoadedDataListItem) and item.file_path == file_path:
                        item.metadata = metadata
                        item.update_display()
                        break
                return

            # Add new file
            self.loaded_files[file_path] = metadata
            item = LoadedDataListItem(file_path, metadata)
            self.list_widget.addItem(item)

            # Update UI
            self.update_count_label()
            self.clear_all_btn.setEnabled(True)

        def remove_file(self, file_path: str):
            """
            Remove file from the loaded data list.

            Args:
                file_path: Full path to the data file
            """
            if file_path not in self.loaded_files:
                return

            # Remove from storage
            del self.loaded_files[file_path]

            # Remove from list widget
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                if isinstance(item, LoadedDataListItem) and item.file_path == file_path:
                    self.list_widget.takeItem(i)
                    break

            # Emit signal
            self.file_removed.emit(file_path)

            # Update UI
            self.update_count_label()
            if self.list_widget.count() == 0:
                self.clear_all_btn.setEnabled(False)

        def remove_selected(self):
            """Remove selected files from list."""
            selected_items = self.list_widget.selectedItems()

            if not selected_items:
                return

            # Confirm removal
            reply = QMessageBox.question(
                self,
                "Confirm Removal",
                f"Remove {len(selected_items)} selected file(s)?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                for item in selected_items:
                    if isinstance(item, LoadedDataListItem):
                        self.remove_file(item.file_path)

        def clear_all(self):
            """Clear all loaded files."""
            if self.list_widget.count() == 0:
                return

            # Confirm clear
            reply = QMessageBox.question(
                self,
                "Confirm Clear",
                f"Remove all {self.list_widget.count()} loaded file(s)?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            if reply == QMessageBox.Yes:
                self.loaded_files.clear()
                self.list_widget.clear()
                self.files_cleared.emit()
                self.update_count_label()
                self.clear_all_btn.setEnabled(False)

        def get_selected_file(self) -> Optional[str]:
            """
            Get currently selected file path.

            Returns:
                File path if one item selected, None otherwise
            """
            selected_items = self.list_widget.selectedItems()
            if len(selected_items) == 1:
                item = selected_items[0]
                if isinstance(item, LoadedDataListItem):
                    return item.file_path
            return None

        def get_selected_files(self) -> List[str]:
            """
            Get all selected file paths.

            Returns:
                List of file paths
            """
            selected_items = self.list_widget.selectedItems()
            return [item.file_path for item in selected_items
                   if isinstance(item, LoadedDataListItem)]

        def get_all_files(self) -> List[str]:
            """
            Get all loaded file paths.

            Returns:
                List of all file paths
            """
            return list(self.loaded_files.keys())

        def update_file_status(self, file_path: str, status: str):
            """
            Update status of a file.

            Args:
                file_path: Full path to the data file
                status: 'loaded', 'processing', 'error', 'pending'
            """
            if file_path in self.loaded_files:
                self.loaded_files[file_path]['status'] = status

                # Update display
                for i in range(self.list_widget.count()):
                    item = self.list_widget.item(i)
                    if isinstance(item, LoadedDataListItem) and item.file_path == file_path:
                        item.metadata['status'] = status
                        item.update_display()
                        break

        def update_count_label(self):
            """Update file count label."""
            count = len(self.loaded_files)
            if count == 0:
                self.count_label.setText("No files loaded")
            elif count == 1:
                self.count_label.setText("1 file loaded")
            else:
                self.count_label.setText(f"{count} files loaded")

        def on_item_clicked(self, item):
            """Handle item click."""
            if isinstance(item, LoadedDataListItem):
                self.file_selected.emit(item.file_path)

        def on_item_double_clicked(self, item):
            """Handle item double click - emit selection."""
            if isinstance(item, LoadedDataListItem):
                self.file_selected.emit(item.file_path)

        def on_selection_changed(self):
            """Handle selection change."""
            selected_count = len(self.list_widget.selectedItems())
            self.remove_btn.setEnabled(selected_count > 0)

        def on_load_more(self):
            """Handle 'Load More' button click."""
            self.load_more_requested.emit()

        def show_context_menu(self, position):
            """Show context menu for list items."""
            item = self.list_widget.itemAt(position)

            if not item or not isinstance(item, LoadedDataListItem):
                return

            menu = QMenu(self)

            # Remove action
            remove_action = menu.addAction("Remove")
            remove_action.triggered.connect(lambda: self.remove_file(item.file_path))

            # Show info action
            info_action = menu.addAction("Show Info")
            info_action.triggered.connect(lambda: self.show_file_info(item))

            menu.addSeparator()

            # Copy path action
            copy_action = menu.addAction("Copy Path")
            copy_action.triggered.connect(lambda: self.copy_file_path(item.file_path))

            # Show menu
            menu.exec_(self.list_widget.mapToGlobal(position))

        def show_file_info(self, item: LoadedDataListItem):
            """Show detailed file information."""
            path = Path(item.file_path)
            metadata = item.metadata

            info_text = f"<h3>{path.name}</h3>"
            info_text += f"<p><b>Path:</b> {item.file_path}</p>"
            info_text += f"<p><b>Size:</b> {metadata.get('size_mb', 0):.2f} MB</p>"
            info_text += f"<p><b>Duration:</b> {metadata.get('duration', 0):.2f} seconds</p>"
            info_text += f"<p><b>Sampling Rate:</b> {metadata.get('sampling_rate', 0):.2f} Hz</p>"
            info_text += f"<p><b>Status:</b> {metadata.get('status', 'unknown')}</p>"

            QMessageBox.information(self, "File Information", info_text)

        def copy_file_path(self, file_path: str):
            """Copy file path to clipboard."""
            from PyQt5.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(file_path)


else:
    # Dummy class when PyQt5 not available
    class LoadedDataList:
        def __init__(self, *args, **kwargs):
            raise ImportError("PyQt5 is required for GUI functionality")
