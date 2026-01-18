"""
Single File Tab
===============

Tab for loading a single seismic data file.
"""

from pathlib import Path
from typing import Dict, Any, Optional

try:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
        QPushButton, QLabel, QLineEdit, QCheckBox, QFileDialog,
        QComboBox, QDateTimeEdit, QMessageBox, QDialog, QDoubleSpinBox
    )
    from PyQt5.QtCore import Qt, pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False

if HAS_PYQT5:
    from hvsr_pro.gui.dialogs.data_input.base_tab import DataInputTabBase
    from hvsr_pro.gui.dialogs.data_input.time_range_panel import TimeRangePanel
    from hvsr_pro.loaders import FORMAT_INFO, get_file_filter


if HAS_PYQT5:
    class SingleFileTab(DataInputTabBase):
        """
        Tab for loading a single file (ASCII, MiniSEED, SAF, GCF).
        
        Features:
        - Format selection (auto-detect or manual)
        - Browse for single file
        - Column mapping for CSV/text files
        - Time range selection
        - Degrees from north for orientation
        
        Signals:
            file_selected: Emitted when file is selected (str path)
            column_mapping_applied: Emitted when mapping is configured (dict)
            format_changed: Emitted when format is changed (str)
        """
        
        file_selected = pyqtSignal(str)
        column_mapping_applied = pyqtSignal(dict)
        format_changed = pyqtSignal(str)
        
        # Single-file formats (exclude SAC and PEER which need 3 files)
        SINGLE_FILE_FORMATS = {
            'auto': 'Auto-detect',
            'txt': 'ASCII Text',
            'miniseed': 'MiniSEED',
            'saf': 'SESAME ASCII Format',
            'gcf': 'Guralp GCF',
            'minishark': 'MiniShark',
            'srecord3c': 'SeismicRecording3C (JSON)',
        }
        
        def __init__(self, parent=None):
            self.column_mapping = None
            self.selected_format = 'auto'
            self.degrees_from_north = None
            super().__init__(parent)
        
        def _init_ui(self):
            """Initialize the user interface."""
            layout = QVBoxLayout(self)
            
            # Instructions
            info = QLabel(
                "Load a single file containing all 3 components.\n"
                "Supported: ASCII (.txt), MiniSEED (.mseed), SAF (.saf), GCF (.gcf), "
                "MiniShark (.minishark), SeismicRecording3C (.json)"
            )
            info.setWordWrap(True)
            layout.addWidget(info)
            
            # Format selection group
            format_group = QGroupBox("Format")
            format_layout = QHBoxLayout(format_group)
            
            format_layout.addWidget(QLabel("Format:"))
            
            self.format_combo = QComboBox()
            for fmt_id, fmt_name in self.SINGLE_FILE_FORMATS.items():
                self.format_combo.addItem(fmt_name, fmt_id)
            self.format_combo.currentIndexChanged.connect(self._on_format_changed)
            format_layout.addWidget(self.format_combo)
            
            format_layout.addStretch()
            
            # Format info
            self.format_info_label = QLabel()
            self.format_info_label.setStyleSheet("color: gray; font-style: italic;")
            format_layout.addWidget(self.format_info_label)
            
            layout.addWidget(format_group)
            
            # File selection group
            file_group = QGroupBox("File Selection")
            file_layout = QVBoxLayout(file_group)
            
            # File path row
            path_layout = QHBoxLayout()
            self.file_path_edit = QLineEdit()
            self.file_path_edit.setPlaceholderText("No file selected")
            self.file_path_edit.setReadOnly(True)
            path_layout.addWidget(self.file_path_edit)
            
            self.browse_btn = QPushButton("Browse...")
            self.browse_btn.clicked.connect(self._on_browse)
            path_layout.addWidget(self.browse_btn)
            
            file_layout.addLayout(path_layout)
            
            # Column mapping option (for TXT format)
            self.use_column_mapping = QCheckBox("Enable Column Mapping (for CSV/text files)")
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
                "Enable for CSV/text files where columns need manual mapping.\n"
                "Check this BEFORE browsing for CSV/text files."
            )
            file_layout.addWidget(self.use_column_mapping)
            
            mapping_info = QLabel(
                "<i>Note: For custom CSV/text files, check the box above BEFORE browsing.</i>"
            )
            mapping_info.setWordWrap(True)
            mapping_info.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")
            file_layout.addWidget(mapping_info)
            
            layout.addWidget(file_group)
            
            # Orientation group (for SAF/GCF)
            self.orientation_group = QGroupBox("Sensor Orientation (Optional)")
            orientation_layout = QHBoxLayout(self.orientation_group)
            
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
                "Clockwise positive (0-360°). SAF files may have this in header."
            )
            orientation_layout.addWidget(self.rotation_spin)
            
            orientation_layout.addStretch()
            
            layout.addWidget(self.orientation_group)
            self.orientation_group.setVisible(False)  # Hidden for txt/miniseed
            
            # Time range panel
            self.time_range_panel = TimeRangePanel(title="Time Range (Optional)")
            layout.addWidget(self.time_range_panel)
            
            layout.addStretch()
            
            # Initialize format info
            self._update_format_ui()
        
        def _on_format_changed(self, index: int):
            """Handle format selection change."""
            self.selected_format = self.format_combo.currentData()
            self._update_format_ui()
            
            # Clear current selection when format changes
            self.file_path_edit.clear()
            self.clear_files()
            
            self.format_changed.emit(self.selected_format)
        
        def _update_format_ui(self):
            """Update UI based on selected format."""
            fmt = self.selected_format
            
            # Update format info
            if fmt == 'auto':
                self.format_info_label.setText("Format will be auto-detected from file")
            else:
                format_info = FORMAT_INFO.get(fmt, {})
                self.format_info_label.setText(format_info.get('description', ''))
            
            # Show/hide column mapping (only for txt/auto)
            show_column_mapping = fmt in ('auto', 'txt')
            self.use_column_mapping.setVisible(show_column_mapping)
            
            # Show/hide orientation (for saf/gcf/minishark/srecord3c/auto)
            show_orientation = fmt in ('auto', 'saf', 'gcf', 'minishark', 'srecord3c')
            self.orientation_group.setVisible(show_orientation)
        
        def _get_file_filter(self) -> str:
            """Get file filter for current format."""
            fmt = self.selected_format
            
            if fmt == 'auto':
                return get_file_filter(single_file_only=True)
            
            format_info = FORMAT_INFO.get(fmt, {})
            extensions = format_info.get('extensions', ['.*'])
            
            ext_str = " ".join(f"*{ext}" for ext in extensions)
            name = format_info.get('name', fmt.upper())
            
            return f"{name} Files ({ext_str});;All Files (*)"
        
        def _on_rotation_toggled(self, checked: bool):
            """Handle rotation checkbox toggle."""
            self.rotation_spin.setEnabled(checked)
        
        def _on_browse(self):
            """Handle browse button click."""
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Select Seismic Data File",
                "",
                self._get_file_filter()
            )
            
            if not file_path:
                return
            
            path = Path(file_path)
            self.file_path_edit.setText(file_path)
            
            # Check if column mapping needed (for txt format or auto with txt extension)
            is_txt = path.suffix.lower() in ['.txt', '.csv', '.dat', '.asc']
            if self.use_column_mapping.isChecked() and is_txt:
                self._show_column_mapper(file_path)
            else:
                self.set_files([file_path])
                self.file_selected.emit(file_path)
        
        def _show_column_mapper(self, file_path: str):
            """Show column mapper dialog for CSV/text files."""
            try:
                from hvsr_pro.gui.dialogs import SeismicColumnMapperDialog
                import numpy as np
                
                # Read file and parse columns
                columns_data, column_headers = self._read_csv_columns(file_path)
                
                if not columns_data:
                    QMessageBox.warning(
                        self, "Error",
                        "Could not read file for column mapping."
                    )
                    return
                
                dlg = SeismicColumnMapperDialog(columns_data, file_path, self, 
                                               column_headers=column_headers)
                if dlg.exec_() == QDialog.Accepted:
                    self.column_mapping = dlg.get_mapping()
                    self.set_files([file_path])
                    self.set_option('column_mapping', self.column_mapping)
                    self.column_mapping_applied.emit(self.column_mapping)
                    self.file_selected.emit(file_path)
                else:
                    self.file_path_edit.clear()
                    self.clear_files()
                    self.column_mapping = None
                    
            except Exception as e:
                QMessageBox.critical(
                    self, "Error",
                    f"Failed to read file:\n{str(e)}"
                )
                self.file_path_edit.clear()
                self.clear_files()
        
        def _read_csv_columns(self, file_path: str):
            """Read CSV file and extract columns."""
            import numpy as np
            
            encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
            columns_data = []
            column_headers = None
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        lines = f.readlines()
                    
                    # Find data start
                    data_start_row = None
                    for i, line in enumerate(lines[:20]):
                        parts = line.strip().split()
                        if not parts:
                            continue
                        
                        # Check if all numeric
                        try:
                            [float(p) for p in parts]
                            if len(parts) >= 2:
                                data_start_row = i
                                # Check for headers
                                if i > 0:
                                    prev = lines[i-1].strip().split()
                                    if len(prev) == len(parts):
                                        try:
                                            [float(p) for p in prev]
                                        except ValueError:
                                            column_headers = prev
                                break
                        except ValueError:
                            continue
                    
                    if data_start_row is None:
                        continue
                    
                    # Parse data
                    numeric_rows = []
                    for line in lines[data_start_row:]:
                        parts = line.strip().split()
                        if not parts:
                            continue
                        try:
                            row = [float(p) for p in parts]
                            numeric_rows.append(row)
                        except ValueError:
                            break
                    
                    if numeric_rows:
                        data = np.array(numeric_rows)
                        columns_data = [data[:, i] for i in range(data.shape[1])]
                        break
                        
                except Exception:
                    continue
            
            return columns_data, column_headers
        
        def get_time_range(self) -> Dict[str, Any]:
            """Get time range settings."""
            return self.time_range_panel.get_time_range()
        
        def get_format(self) -> str:
            """Get selected format."""
            return self.selected_format
        
        def get_degrees_from_north(self) -> Optional[float]:
            """Get degrees from north setting."""
            if self.use_custom_rotation.isChecked():
                return self.rotation_spin.value()
            return None
        
        def get_result(self) -> Dict[str, Any]:
            """Get complete result dictionary."""
            result = super().get_result()
            result['format'] = self.selected_format
            result['time_range'] = self.get_time_range()
            result['column_mapping'] = self.column_mapping
            result['degrees_from_north'] = self.get_degrees_from_north()
            return result
        
        def clear(self):
            """Clear all selections."""
            super().clear()
            self.file_path_edit.clear()
            self.column_mapping = None
            self.use_column_mapping.setChecked(False)
            self.use_custom_rotation.setChecked(False)
            self.rotation_spin.setValue(0)
            self.time_range_panel.set_enabled(False)

else:
    class SingleFileTab:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass
