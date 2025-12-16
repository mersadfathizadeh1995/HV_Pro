"""
Collapsible Data Panel for HVSR Pro
====================================

A collapsible wrapper for the LoadedDataTree widget that can be shared
across Processing and Azimuthal tabs.

Features:
- Shows the same loaded files as the main Data Load tab
- Collapsible to save space
- Syncs selection with main tree
"""

from typing import Optional

try:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
        QTreeWidget, QTreeWidgetItem, QGroupBox, QSizePolicy
    )
    from PyQt5.QtCore import Qt, pyqtSignal
    from PyQt5.QtGui import QFont
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


if HAS_PYQT5:
    
    class CollapsibleDataPanel(QWidget):
        """
        Collapsible panel that displays loaded data files.
        
        This widget can be placed in Processing and Azimuthal tabs to show
        what data is currently loaded, without duplicating the full LoadedDataTree.
        
        When collapsed, it shows just a header bar with file count.
        When expanded, it shows a simplified tree view of loaded files.
        """
        
        # Signals
        file_selected = pyqtSignal(str)  # file_path
        
        def __init__(self, parent=None, title="Loaded Data"):
            super().__init__(parent)
            
            self._title = title
            self._is_collapsed = True  # Start collapsed
            self._data_handler = None
            self._loaded_files = {}  # file_path -> metadata
            
            self.init_ui()
            
        def init_ui(self):
            """Initialize the UI."""
            self.main_layout = QVBoxLayout(self)
            self.main_layout.setContentsMargins(0, 0, 0, 0)
            self.main_layout.setSpacing(0)
            
            # === Header Bar (always visible) ===
            self.header = QWidget()
            self.header.setStyleSheet("""
                QWidget {
                    background-color: #e8e8e8;
                    border: 1px solid #ccc;
                    border-radius: 3px;
                }
            """)
            header_layout = QHBoxLayout(self.header)
            header_layout.setContentsMargins(8, 4, 8, 4)
            header_layout.setSpacing(8)
            
            # Toggle button
            self.toggle_btn = QPushButton("[+]")
            self.toggle_btn.setFixedWidth(30)
            self.toggle_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                    font-weight: bold;
                    font-size: 12px;
                    color: #333;
                }
                QPushButton:hover {
                    color: #0066cc;
                }
            """)
            self.toggle_btn.clicked.connect(self.toggle)
            header_layout.addWidget(self.toggle_btn)
            
            # Title label
            self.title_label = QLabel(self._title)
            self.title_label.setStyleSheet("font-weight: bold; background: transparent; border: none;")
            header_layout.addWidget(self.title_label)
            
            # File count label
            self.count_label = QLabel("(0 files)")
            self.count_label.setStyleSheet("color: #666; background: transparent; border: none;")
            header_layout.addWidget(self.count_label)
            
            # Stretch to push everything left
            header_layout.addStretch()
            
            # Make header clickable
            self.header.mousePressEvent = lambda e: self.toggle()
            self.header.setCursor(Qt.PointingHandCursor)
            
            self.main_layout.addWidget(self.header)
            
            # === Content Area (collapsible) ===
            self.content = QWidget()
            self.content.setStyleSheet("""
                QWidget {
                    background-color: #f5f5f5;
                    border: 1px solid #ccc;
                    border-top: none;
                }
            """)
            content_layout = QVBoxLayout(self.content)
            content_layout.setContentsMargins(5, 5, 5, 5)
            content_layout.setSpacing(3)
            
            # Simple tree view for files
            self.file_tree = QTreeWidget()
            self.file_tree.setHeaderHidden(True)
            self.file_tree.setIndentation(15)
            self.file_tree.setMaximumHeight(150)
            self.file_tree.setMinimumHeight(80)
            self.file_tree.itemClicked.connect(self._on_item_clicked)
            self.file_tree.setStyleSheet("""
                QTreeWidget {
                    background-color: white;
                    border: 1px solid #ddd;
                    font-size: 11px;
                }
                QTreeWidget::item {
                    padding: 2px;
                }
                QTreeWidget::item:selected {
                    background-color: #0078d7;
                    color: white;
                }
            """)
            content_layout.addWidget(self.file_tree)
            
            self.main_layout.addWidget(self.content)
            
            # Start collapsed
            self.content.hide()
            
            # Set size policy
            self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)
            
        def toggle(self):
            """Toggle collapsed/expanded state."""
            self._is_collapsed = not self._is_collapsed
            self.content.setVisible(not self._is_collapsed)
            self.toggle_btn.setText("[+]" if self._is_collapsed else "[-]")
            
        def expand(self):
            """Expand the panel."""
            if self._is_collapsed:
                self.toggle()
                
        def collapse(self):
            """Collapse the panel."""
            if not self._is_collapsed:
                self.toggle()
                
        def set_data_handler(self, handler):
            """
            Set reference to the main data handler.
            
            Args:
                handler: HVSRDataHandler instance
            """
            self._data_handler = handler
            
        def update_from_data_load_tab(self, data_load_tab):
            """
            Sync loaded files from the main Data Load tab.
            
            Args:
                data_load_tab: DataLoadTab instance
            """
            self._loaded_files = {}
            
            # Get data from data_load_tab's cache
            if hasattr(data_load_tab, 'data_cache'):
                for file_path, cached in data_load_tab.data_cache.items():
                    metadata = {
                        'data': cached.get('data'),
                        'time_range': cached.get('time_range')
                    }
                    # Get additional metadata if available
                    data = cached.get('data')
                    if data:
                        metadata['duration'] = getattr(data, 'duration', 0)
                        metadata['sampling_rate'] = getattr(data, 'sampling_rate', 0)
                    self._loaded_files[file_path] = metadata
                    
            self._update_tree()
            
        def add_file(self, file_path: str, metadata: dict = None):
            """
            Add a file to the panel.
            
            Args:
                file_path: Path to the file
                metadata: Optional dict with file info
            """
            self._loaded_files[file_path] = metadata or {}
            self._update_tree()
            
        def clear_files(self):
            """Clear all files from the panel."""
            self._loaded_files.clear()
            self._update_tree()
            
        def _update_tree(self):
            """Update the tree widget with current files."""
            self.file_tree.clear()
            
            file_count = len(self._loaded_files)
            self.count_label.setText(f"({file_count} file{'s' if file_count != 1 else ''})")
            
            if not self._loaded_files:
                item = QTreeWidgetItem(["No data loaded"])
                item.setForeground(0, Qt.gray)
                item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
                self.file_tree.addTopLevelItem(item)
                return
                
            # Add files to tree
            from pathlib import Path
            for file_path, metadata in self._loaded_files.items():
                fname = Path(file_path).name
                
                # Create item with file name
                item = QTreeWidgetItem([fname])
                item.setData(0, Qt.UserRole, file_path)
                item.setToolTip(0, file_path)
                
                # Add details as children if metadata available
                if metadata:
                    duration = metadata.get('duration', 0)
                    sr = metadata.get('sampling_rate', 0)
                    
                    if duration:
                        dur_str = f"{duration:.1f}s" if duration < 3600 else f"{duration/3600:.1f}h"
                        child = QTreeWidgetItem([f"Duration: {dur_str}"])
                        child.setForeground(0, Qt.darkGray)
                        item.addChild(child)
                        
                    if sr:
                        child = QTreeWidgetItem([f"Sampling: {sr:.0f} Hz"])
                        child.setForeground(0, Qt.darkGray)
                        item.addChild(child)
                        
                self.file_tree.addTopLevelItem(item)
                
        def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
            """Handle tree item click."""
            file_path = item.data(0, Qt.UserRole)
            if file_path:
                self.file_selected.emit(file_path)
                
        def get_file_count(self) -> int:
            """Get number of loaded files."""
            return len(self._loaded_files)
            
        def get_selected_file(self) -> Optional[str]:
            """Get currently selected file path."""
            item = self.file_tree.currentItem()
            if item:
                return item.data(0, Qt.UserRole)
            return None


else:
    # Dummy class when PyQt5 not available
    class CollapsibleDataPanel:
        def __init__(self, *args, **kwargs):
            raise ImportError("PyQt5 is required for GUI functionality")
