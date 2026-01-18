"""
Multi-Component Tab
===================

Tab for loading formats with separate component files (SAC, PEER).
"""

from pathlib import Path
from typing import Dict, Any, Optional, List

try:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
        QPushButton, QLabel, QComboBox, QDoubleSpinBox,
        QCheckBox, QMessageBox
    )
    from PyQt5.QtCore import Qt, pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False

if HAS_PYQT5:
    from hvsr_pro.gui.dialogs.data_input.base_tab import DataInputTabBase
    from hvsr_pro.gui.dialogs.data_input.time_range_panel import TimeRangePanel
    from hvsr_pro.gui.widgets.multi_file_browser import MultiFileBrowser
    from hvsr_pro.loaders import FORMAT_INFO, get_file_filter


if HAS_PYQT5:
    class MultiComponentTab(DataInputTabBase):
        """
        Tab for loading formats requiring 3 separate component files.
        
        Used for:
        - SAC (Seismic Analysis Code)
        - PEER (Pacific Earthquake Engineering Research)
        
        Features:
        - Format selector (SAC or PEER)
        - Multi-file browser for 3 components
        - Degrees from north input
        - Time range selection (optional)
        
        Signals:
            format_changed: Emitted when format is changed (str)
        """
        
        format_changed = pyqtSignal(str)
        
        def __init__(self, parent=None):
            self.selected_format = 'sac'
            self.component_files = {}
            self.degrees_from_north = None
            super().__init__(parent)
        
        def _init_ui(self):
            """Initialize the user interface."""
            layout = QVBoxLayout(self)
            
            # Instructions
            info = QLabel(
                "Load 3 separate files (one per component) for SAC or PEER format.\n"
                "Best for: SAC files from standard seismic equipment, PEER ground motion records."
            )
            info.setWordWrap(True)
            layout.addWidget(info)
            
            # Format selector
            format_group = QGroupBox("Format Selection")
            format_layout = QHBoxLayout(format_group)
            
            format_layout.addWidget(QLabel("Format:"))
            
            self.format_combo = QComboBox()
            self.format_combo.addItem("SAC (Seismic Analysis Code)", "sac")
            self.format_combo.addItem("PEER NGA (Ground Motion)", "peer")
            self.format_combo.currentIndexChanged.connect(self._on_format_changed)
            format_layout.addWidget(self.format_combo)
            
            format_layout.addStretch()
            
            # Format info label
            self.format_info_label = QLabel()
            self.format_info_label.setStyleSheet("color: gray; font-style: italic;")
            format_layout.addWidget(self.format_info_label)
            
            layout.addWidget(format_group)
            
            # File selection group
            file_group = QGroupBox("Component Files")
            file_layout = QVBoxLayout(file_group)
            
            # Multi-file browser
            self.file_browser = MultiFileBrowser(
                component_labels=['N', 'E', 'Z'],
                file_filter=self._get_file_filter()
            )
            self.file_browser.files_selected.connect(self._on_files_selected)
            self.file_browser.files_cleared.connect(self._on_files_cleared)
            file_layout.addWidget(self.file_browser)
            
            layout.addWidget(file_group)
            
            # Orientation group
            orientation_group = QGroupBox("Sensor Orientation (Optional)")
            orientation_layout = QHBoxLayout(orientation_group)
            
            self.use_custom_rotation = QCheckBox("Specify degrees from north:")
            self.use_custom_rotation.toggled.connect(self._on_rotation_toggled)
            orientation_layout.addWidget(self.use_custom_rotation)
            
            self.rotation_spin = QDoubleSpinBox()
            self.rotation_spin.setRange(0, 360)
            self.rotation_spin.setSingleStep(1)
            self.rotation_spin.setDecimals(1)
            self.rotation_spin.setSuffix("°")
            self.rotation_spin.setValue(0)
            self.rotation_spin.setEnabled(False)
            self.rotation_spin.setToolTip(
                "Rotation of sensor's north component relative to magnetic north.\n"
                "Clockwise positive (0-360°)."
            )
            orientation_layout.addWidget(self.rotation_spin)
            
            orientation_layout.addStretch()
            
            orientation_info = QLabel(
                "<i>Leave unchecked to use orientation from file metadata.</i>"
            )
            orientation_info.setStyleSheet("color: gray;")
            orientation_layout.addWidget(orientation_info)
            
            layout.addWidget(orientation_group)
            
            # Time range panel
            self.time_range_panel = TimeRangePanel(title="Time Range (Optional)")
            layout.addWidget(self.time_range_panel)
            
            layout.addStretch()
            
            # Initial update
            self._update_format_info()
        
        def _on_format_changed(self, index: int):
            """Handle format selection change."""
            self.selected_format = self.format_combo.currentData()
            
            # Update file filter
            self.file_browser.set_file_filter(self._get_file_filter())
            
            # Update info
            self._update_format_info()
            
            # Clear files when format changes
            self.file_browser.clear()
            
            self.format_changed.emit(self.selected_format)
        
        def _get_file_filter(self) -> str:
            """Get file filter for current format."""
            format_info = FORMAT_INFO.get(self.selected_format, {})
            extensions = format_info.get('extensions', ['.*'])
            
            ext_str = " ".join(f"*{ext}" for ext in extensions)
            name = format_info.get('name', self.selected_format.upper())
            
            return f"{name} Files ({ext_str});;All Files (*)"
        
        def _update_format_info(self):
            """Update format information label."""
            format_info = FORMAT_INFO.get(self.selected_format, {})
            description = format_info.get('description', '')
            self.format_info_label.setText(description)
        
        def _on_files_selected(self, files: Dict[str, str]):
            """Handle files selected in browser."""
            self.component_files = files
            
            # Update internal file list for base class
            self._files = list(files.values())
            self.files_changed.emit(self._files)
            self._validate()
        
        def _on_files_cleared(self):
            """Handle files cleared."""
            self.component_files = {}
            self._files = []
            self.files_changed.emit(self._files)
            self._validate()
        
        def _on_rotation_toggled(self, checked: bool):
            """Handle rotation checkbox toggle."""
            self.rotation_spin.setEnabled(checked)
            
            if checked:
                self.degrees_from_north = self.rotation_spin.value()
            else:
                self.degrees_from_north = None
        
        def _validate(self) -> bool:
            """Validate current selections."""
            # Need all 3 component files
            is_valid = len(self.component_files) == 3
            
            if not is_valid:
                message = f"Select all 3 component files ({len(self.component_files)}/3 selected)"
            else:
                message = ""
            
            if self._is_valid != is_valid or self._validation_message != message:
                self._is_valid = is_valid
                self._validation_message = message
                self.validation_changed.emit(is_valid, message)
            
            return is_valid
        
        def get_files(self) -> List[str]:
            """Get list of selected files."""
            return list(self.component_files.values())
        
        def get_component_files(self) -> Dict[str, str]:
            """Get component to file mapping."""
            return dict(self.component_files)
        
        def get_format(self) -> str:
            """Get selected format."""
            return self.selected_format
        
        def get_degrees_from_north(self) -> Optional[float]:
            """Get degrees from north setting."""
            if self.use_custom_rotation.isChecked():
                return self.rotation_spin.value()
            return None
        
        def get_time_range(self) -> Dict[str, Any]:
            """Get time range settings."""
            return self.time_range_panel.get_time_range()
        
        def get_result(self) -> Dict[str, Any]:
            """Get complete result dictionary."""
            result = super().get_result()
            result['format'] = self.selected_format
            result['component_files'] = self.component_files
            result['degrees_from_north'] = self.get_degrees_from_north()
            result['time_range'] = self.get_time_range()
            return result
        
        def clear(self):
            """Clear all selections."""
            super().clear()
            self.file_browser.clear()
            self.component_files = {}
            self.use_custom_rotation.setChecked(False)
            self.rotation_spin.setValue(0)
            self.time_range_panel.set_enabled(False)


else:
    class MultiComponentTab:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass
