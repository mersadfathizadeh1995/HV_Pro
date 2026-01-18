"""
Multi-File Browser Widget
=========================

Widget for selecting 3 component files (for SAC/PEER formats).
"""

from pathlib import Path
from typing import Dict, List, Optional

try:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
        QPushButton, QLabel, QLineEdit, QFileDialog,
        QGroupBox, QMessageBox
    )
    from PyQt5.QtCore import pyqtSignal, Qt
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False

from hvsr_pro.loaders.orientation import detect_component_from_filename


if HAS_PYQT5:
    class MultiFileBrowser(QWidget):
        """
        Widget for selecting 3 component files.
        
        Used for formats like SAC and PEER that require separate files
        for each component (N, E, Z).
        
        Features:
        - 3 file path inputs with component labels
        - Browse buttons for each file
        - Auto-detect component from filename
        - Browse all 3 at once option
        - Validation that all 3 files are selected
        
        Signals:
            files_selected: Emitted when all 3 files are selected
                           Dict[str, str] mapping component to path
            files_cleared: Emitted when files are cleared
        """
        
        files_selected = pyqtSignal(dict)  # {'N': path, 'E': path, 'Z': path}
        files_cleared = pyqtSignal()
        
        def __init__(
            self,
            component_labels: List[str] = None,
            file_filter: str = "All Files (*)",
            parent=None
        ):
            """
            Initialize multi-file browser.
            
            Args:
                component_labels: Labels for components (default: ['N', 'E', 'Z'])
                file_filter: File dialog filter string
                parent: Parent widget
            """
            super().__init__(parent)
            
            self.component_labels = component_labels or ['N', 'E', 'Z']
            self.file_filter = file_filter
            
            self.file_inputs: Dict[str, QLineEdit] = {}
            self.browse_buttons: Dict[str, QPushButton] = {}
            
            self._init_ui()
        
        def _init_ui(self):
            """Initialize the user interface."""
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            
            # Component file inputs
            grid = QGridLayout()
            grid.setSpacing(5)
            
            for i, comp in enumerate(self.component_labels):
                # Label
                label = QLabel(f"Component {comp}:")
                label.setMinimumWidth(100)
                grid.addWidget(label, i, 0)
                
                # Path input
                path_edit = QLineEdit()
                path_edit.setPlaceholderText(f"Select {comp} component file...")
                path_edit.setReadOnly(True)
                path_edit.textChanged.connect(self._on_file_changed)
                self.file_inputs[comp] = path_edit
                grid.addWidget(path_edit, i, 1)
                
                # Browse button
                browse_btn = QPushButton("Browse")
                browse_btn.setMaximumWidth(80)
                browse_btn.clicked.connect(lambda checked, c=comp: self._browse_file(c))
                self.browse_buttons[comp] = browse_btn
                grid.addWidget(browse_btn, i, 2)
            
            layout.addLayout(grid)
            
            # Action buttons
            btn_layout = QHBoxLayout()
            
            self.browse_all_btn = QPushButton("Browse All 3 Files...")
            self.browse_all_btn.clicked.connect(self._browse_all)
            btn_layout.addWidget(self.browse_all_btn)
            
            self.auto_assign_btn = QPushButton("Auto-Assign Components")
            self.auto_assign_btn.setToolTip(
                "Automatically assign components based on filenames"
            )
            self.auto_assign_btn.clicked.connect(self._auto_assign)
            self.auto_assign_btn.setEnabled(False)
            btn_layout.addWidget(self.auto_assign_btn)
            
            self.clear_btn = QPushButton("Clear")
            self.clear_btn.clicked.connect(self.clear)
            btn_layout.addWidget(self.clear_btn)
            
            btn_layout.addStretch()
            
            layout.addLayout(btn_layout)
            
            # Status label
            self.status_label = QLabel()
            self.status_label.setStyleSheet("color: gray; font-style: italic;")
            layout.addWidget(self.status_label)
            
            self._update_status()
        
        def _browse_file(self, component: str):
            """Browse for a single component file."""
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                f"Select {component} Component File",
                "",
                self.file_filter
            )
            
            if file_path:
                self.file_inputs[component].setText(file_path)
        
        def _browse_all(self):
            """Browse for all 3 files at once."""
            files, _ = QFileDialog.getOpenFileNames(
                self,
                "Select 3 Component Files (N, E, Z)",
                "",
                self.file_filter
            )
            
            if not files:
                return
            
            if len(files) != 3:
                QMessageBox.warning(
                    self,
                    "Selection Error",
                    f"Please select exactly 3 files, got {len(files)}."
                )
                return
            
            # Try to auto-assign components
            assignments = self._try_auto_assign(files)
            
            if assignments:
                for comp, path in assignments.items():
                    self.file_inputs[comp].setText(path)
            else:
                # Just assign in order
                for comp, path in zip(self.component_labels, files):
                    self.file_inputs[comp].setText(path)
                
                QMessageBox.information(
                    self,
                    "Auto-Assignment",
                    "Could not auto-detect components from filenames.\n"
                    "Files assigned in selection order. Please verify."
                )
        
        def _auto_assign(self):
            """Re-assign components based on current file names."""
            current_files = [
                self.file_inputs[comp].text()
                for comp in self.component_labels
                if self.file_inputs[comp].text()
            ]
            
            if len(current_files) < 3:
                QMessageBox.warning(
                    self,
                    "Cannot Auto-Assign",
                    "Please select all 3 files first."
                )
                return
            
            assignments = self._try_auto_assign(current_files)
            
            if assignments:
                for comp, path in assignments.items():
                    self.file_inputs[comp].setText(path)
                QMessageBox.information(
                    self,
                    "Auto-Assignment",
                    "Components assigned based on filenames."
                )
            else:
                QMessageBox.warning(
                    self,
                    "Auto-Assignment Failed",
                    "Could not determine components from filenames.\n"
                    "Please assign manually."
                )
        
        def _try_auto_assign(self, filepaths: List[str]) -> Optional[Dict[str, str]]:
            """
            Try to auto-assign components from filenames.
            
            Returns:
                Dict mapping component to filepath, or None if failed
            """
            assignments = {}
            unassigned = list(filepaths)
            
            for filepath in filepaths:
                filename = Path(filepath).name
                component = detect_component_from_filename(filename)
                
                if component and component in self.component_labels:
                    if component not in assignments:
                        assignments[component] = filepath
                        unassigned.remove(filepath)
            
            # Check if we got all components
            if len(assignments) == len(self.component_labels):
                return assignments
            
            return None
        
        def _on_file_changed(self):
            """Handle file path change."""
            self._update_status()
            
            # Enable auto-assign if we have files
            has_files = any(
                self.file_inputs[comp].text()
                for comp in self.component_labels
            )
            self.auto_assign_btn.setEnabled(has_files)
            
            # Emit signal if all files selected
            if self.is_complete():
                self.files_selected.emit(self.get_files())
        
        def _update_status(self):
            """Update status label."""
            selected = sum(
                1 for comp in self.component_labels
                if self.file_inputs[comp].text()
            )
            total = len(self.component_labels)
            
            if selected == total:
                self.status_label.setText(f"All {total} files selected")
                self.status_label.setStyleSheet("color: green;")
            elif selected > 0:
                self.status_label.setText(f"{selected}/{total} files selected")
                self.status_label.setStyleSheet("color: orange;")
            else:
                self.status_label.setText("No files selected")
                self.status_label.setStyleSheet("color: gray; font-style: italic;")
        
        def get_files(self) -> Dict[str, str]:
            """
            Get selected files.
            
            Returns:
                Dict mapping component to file path
            """
            return {
                comp: self.file_inputs[comp].text()
                for comp in self.component_labels
                if self.file_inputs[comp].text()
            }
        
        def set_files(self, files: Dict[str, str]):
            """
            Set file paths.
            
            Args:
                files: Dict mapping component to file path
            """
            for comp, path in files.items():
                if comp in self.file_inputs:
                    self.file_inputs[comp].setText(path)
        
        def is_complete(self) -> bool:
            """Check if all files are selected."""
            return all(
                self.file_inputs[comp].text()
                for comp in self.component_labels
            )
        
        def clear(self):
            """Clear all file selections."""
            for comp in self.component_labels:
                self.file_inputs[comp].clear()
            
            self._update_status()
            self.files_cleared.emit()
        
        def set_file_filter(self, filter_str: str):
            """Set the file dialog filter."""
            self.file_filter = filter_str


else:
    class MultiFileBrowser:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass
