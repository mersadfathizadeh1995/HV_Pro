"""
Enhanced Data Input Dialog for HVSR Pro
========================================

Modular dialog for loading various data formats using reusable tab components.
This is the refactored version that uses modular tab components.

Modes:
- Single files (ASCII txt, MiniSEED)
- Multiple MiniSEED files (Type 1: 3-channel per file)
- Separate component MiniSEED files (Type 2: E, N, Z separate)
- Automatic pattern matching and file grouping
- Visual waveform preview with time range selection
"""

from pathlib import Path
from typing import List, Dict, Optional, Any

try:
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
        QPushButton, QLabel, QMessageBox, QScrollArea, QFrame
    )
    from PyQt5.QtCore import Qt, pyqtSignal
    from PyQt5.QtGui import QFont
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False

# Import modular components
if HAS_PYQT5:
    from hvsr_pro.gui.components import CollapsibleGroupBox
    from hvsr_pro.gui.dialogs.data_input.tabs import (
        SingleFileTab, MultiType1Tab, MultiType2Tab, MultiComponentTab,
        AdvancedOptionsTab
    )
    from hvsr_pro.gui.dialogs.data_input.preview_panel import PreviewPanel
    from hvsr_pro.gui.dialogs.mappers import ComponentMapperDialog
    from hvsr_pro.loaders.preview import get_preview


if HAS_PYQT5:
    class DataInputDialog(QDialog):
        """
        Enhanced data input dialog with modular tab components.
        
        This refactored version uses modular components from the tabs/ folder
        for cleaner, more maintainable code.
        
        Signals:
            files_selected: Emitted with loaded file info when user clicks Load
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
            self.load_mode = 'single'
            self.component_mapping = None  # User-defined component mapping
            self.mapping_orientation = None  # User-defined orientation
            
            self._init_ui()
            self._connect_signals()
        
        def _init_ui(self):
            """Initialize user interface with modular components."""
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
            
            # === TAB WIDGET WITH MODULAR COMPONENTS ===
            self.tabs = QTabWidget()
            self.tabs.currentChanged.connect(self._on_tab_changed)
            
            # Create tab components (modular)
            self.single_tab = SingleFileTab(self)
            self.type1_tab = MultiType1Tab(self)
            self.type2_tab = MultiType2Tab(self)
            self.multi_component_tab = MultiComponentTab(self)
            self.advanced_tab = AdvancedOptionsTab(self)
            
            # Add tabs
            self.tabs.addTab(self.single_tab, "Single File")
            self.tabs.addTab(self.type1_tab, "Multi-File (3-channel)")
            self.tabs.addTab(self.type2_tab, "Multi-File (Separate E,N,Z)")
            self.tabs.addTab(self.multi_component_tab, "SAC/PEER Files")
            self.tabs.addTab(self.advanced_tab, "Advanced Options")
            
            scroll_layout.addWidget(self.tabs)
            
            # === COLLAPSIBLE PREVIEW SECTION ===
            self.preview_group = CollapsibleGroupBox("Data Preview (click to expand/collapse)")
            preview_layout = QVBoxLayout()
            
            # Use modular PreviewPanel
            try:
                self.preview_panel = PreviewPanel(self)
                preview_layout.addWidget(self.preview_panel)
            except Exception as e:
                # Fallback if PreviewPanel not available
                fallback_label = QLabel(f"(Visual preview unavailable: {str(e)})")
                fallback_label.setStyleSheet("color: gray; font-style: italic;")
                preview_layout.addWidget(fallback_label)
                self.preview_panel = None
            
            self.preview_group.add_layout(preview_layout)
            self.preview_group.set_collapsed(True)  # Start collapsed
            scroll_layout.addWidget(self.preview_group)
            
            # Set scroll content
            scroll_area.setWidget(scroll_content)
            main_layout.addWidget(scroll_area, 1)  # stretch factor 1
            
            # === BUTTONS (outside scroll area) ===
            button_layout = QHBoxLayout()
            
            # Preview & Map Components button
            self.map_btn = QPushButton("Preview && Map Components...")
            self.map_btn.setToolTip(
                "Open component mapper to verify and customize\n"
                "how channels are assigned to E, N, Z components"
            )
            self.map_btn.clicked.connect(self._open_component_mapper)
            self.map_btn.setEnabled(False)
            button_layout.addWidget(self.map_btn)
            
            button_layout.addStretch()
            
            cancel_btn = QPushButton("Cancel")
            cancel_btn.clicked.connect(self.reject)
            button_layout.addWidget(cancel_btn)
            
            self.load_btn = QPushButton("Load Data")
            self.load_btn.clicked.connect(self._accept_files)
            self.load_btn.setEnabled(False)
            self.load_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    font-weight: bold;
                    padding: 8px 16px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
                QPushButton:disabled {
                    background-color: #ccc;
                    color: #888;
                }
            """)
            button_layout.addWidget(self.load_btn)
            
            main_layout.addLayout(button_layout)
        
        def _connect_signals(self):
            """Connect signals from tab components."""
            # Connect validation signals to update Load button
            self.single_tab.validation_changed.connect(self._on_validation_changed)
            self.type1_tab.validation_changed.connect(self._on_validation_changed)
            self.type2_tab.validation_changed.connect(self._on_validation_changed)
            self.multi_component_tab.validation_changed.connect(self._on_validation_changed)
            
            # Connect file selection signals to preview
            self.single_tab.file_selected.connect(self._on_file_selected_for_preview)
            
            # Connect Type1 files_changed signal for preview
            self.type1_tab.files_changed.connect(self._on_files_changed_for_preview)
            
            # Connect Type2 selection changes
            self.type2_tab.files_changed.connect(self._on_files_changed_for_preview)
            
            # Connect multi-component files changed
            self.multi_component_tab.files_changed.connect(self._on_files_changed_for_preview)
            
            # Connect preview_requested signals
            self.single_tab.preview_requested.connect(self._update_preview)
            self.type1_tab.preview_requested.connect(self._update_preview)
            self.type2_tab.preview_requested.connect(self._update_preview)
            self.multi_component_tab.preview_requested.connect(self._update_preview)
        
        def _on_tab_changed(self, index: int):
            """Handle tab change to update load mode."""
            mode_map = {
                0: 'single', 
                1: 'multi_type1', 
                2: 'multi_type2', 
                3: 'multi_component',
                4: 'advanced'
            }
            self.load_mode = mode_map.get(index, 'single')
            
            # Update Load button based on current tab's validation
            # Guard against being called during initialization
            if hasattr(self, 'load_btn'):
                self._update_load_button()
        
        def _on_validation_changed(self, is_valid: bool, message: str):
            """Handle validation state change from tabs."""
            # Guard against being called during initialization
            if hasattr(self, 'load_btn'):
                self._update_load_button()
            # Also update Map button
            if hasattr(self, 'map_btn'):
                self._update_map_button()
        
        def _update_load_button(self):
            """Update Load button enabled state based on current tab."""
            current_tab = self.tabs.currentWidget()
            if hasattr(current_tab, 'is_valid'):
                self.load_btn.setEnabled(current_tab.is_valid())
            else:
                # Advanced tab - always allow load if other tabs have data
                has_any_data = (
                    self.single_tab.is_valid() or
                    self.type1_tab.is_valid() or
                    self.type2_tab.is_valid() or
                    self.multi_component_tab.is_valid()
                )
                self.load_btn.setEnabled(has_any_data)
        
        def _update_map_button(self):
            """Update Map button enabled state based on file selection."""
            # Enable map button when files are selected
            current_tab = self.tabs.currentWidget()
            
            # Check if current tab has files
            has_files = False
            if hasattr(current_tab, 'get_files'):
                files = current_tab.get_files()
                has_files = len(files) > 0
            
            self.map_btn.setEnabled(has_files)
        
        def _open_component_mapper(self):
            """Open the component mapper dialog."""
            # Get files from current tab
            current_tab = self.tabs.currentWidget()
            
            files = []
            if hasattr(current_tab, 'get_files'):
                files = current_tab.get_files()
            
            if not files:
                QMessageBox.warning(
                    self,
                    "No Files",
                    "Please select files first before mapping components."
                )
                return
            
            # Determine format
            format_name = None
            if hasattr(current_tab, 'get_format'):
                format_name = current_tab.get_format()
            elif hasattr(current_tab, 'selected_format'):
                format_name = current_tab.selected_format
            
            # Get preview data
            try:
                preview = get_preview(files, format=format_name, n_samples=2000)
            except Exception as e:
                QMessageBox.warning(
                    self,
                    "Preview Error",
                    f"Could not load preview: {str(e)}"
                )
                return
            
            if preview.error:
                QMessageBox.warning(
                    self,
                    "Preview Error",
                    f"Preview error: {preview.error}"
                )
                return
            
            # Open component mapper dialog
            dialog = ComponentMapperDialog(preview, self)
            
            if dialog.exec_() == QDialog.Accepted:
                # Store mapping results
                result = dialog.get_result()
                self.component_mapping = result.get('mapping')
                self.mapping_orientation = result.get('orientation')
                
                # Show confirmation
                mapping_str = ", ".join(
                    f"{comp}={idx}" for comp, idx in self.component_mapping.items()
                )
                QMessageBox.information(
                    self,
                    "Mapping Set",
                    f"Component mapping set: {mapping_str}\n\n"
                    "This mapping will be used when loading the data."
                )
        
        def _on_file_selected_for_preview(self, file_path: str):
            """Handle single file selection for preview."""
            self._update_preview(file_path)
            # Expand preview panel when file is selected
            if hasattr(self, 'preview_group'):
                self.preview_group.set_collapsed(False)
        
        def _on_files_changed_for_preview(self, files: list):
            """Handle multiple files selection for preview."""
            if files and len(files) > 0:
                # Preview the first file
                self._update_preview(files[0])
                # Expand preview panel
                if hasattr(self, 'preview_group'):
                    self.preview_group.set_collapsed(False)
        
        def _update_preview(self, file_path: str):
            """Update preview panel with file data."""
            if not file_path:
                return
            if self.preview_panel and hasattr(self.preview_panel, 'load_from_file'):
                try:
                    self.preview_panel.load_from_file(file_path)
                except Exception as e:
                    print(f"Preview error: {e}")
        
        def _accept_files(self):
            """Accept selected files and emit signal."""
            # Get result based on current mode
            if self.load_mode == 'single':
                tab_result = self.single_tab.get_result()
            elif self.load_mode == 'multi_type1':
                tab_result = self.type1_tab.get_result()
            elif self.load_mode == 'multi_type2':
                tab_result = self.type2_tab.get_result()
            elif self.load_mode == 'multi_component':
                tab_result = self.multi_component_tab.get_result()
            else:
                tab_result = self.advanced_tab.get_result()
            
            # Validate we have files
            files = tab_result.get('files', [])
            groups = tab_result.get('groups', {})
            component_files = tab_result.get('component_files', {})
            
            if not files and not groups and not component_files:
                QMessageBox.warning(self, "No Files", "Please select files to load.")
                return
            
            # Get advanced options
            advanced_options = self.advanced_tab.get_advanced_options()
            
            # Prepare time range
            time_range = tab_result.get('time_range', None)
            if time_range and time_range.get('enabled'):
                # Remap keys for backward compatibility
                time_range = {
                    'enabled': True,
                    'start': time_range.get('start_dt'),
                    'end': time_range.get('end_dt'),
                    'timezone_offset': time_range.get('timezone_offset', 0),
                    'timezone_name': time_range.get('timezone_name', 'UTC'),
                }
            
            # Build result dict
            result = {
                'mode': self.load_mode,
                'files': files,
                'groups': groups,
                'component_files': component_files,
                'format': tab_result.get('format', 'auto'),
                'time_range': time_range,
                'options': {
                    'merge_continuous': advanced_options.get('merge_continuous', True),
                    'verify_sampling_rate': advanced_options.get('verify_sampling_rate', True),
                    'column_mapping': tab_result.get('column_mapping'),
                    'channel_mapping': tab_result.get('channel_mapping'),
                    'degrees_from_north': tab_result.get('degrees_from_north') or self.mapping_orientation,
                    # Component mapping from mapper dialog
                    'component_mapping': self.component_mapping,
                }
            }
            
            self.files_selected.emit(result)
            self.accept()
        
        # === BACKWARD COMPATIBILITY PROPERTIES ===
        
        @property
        def selected_files(self) -> List[str]:
            """Get selected files (backward compatibility)."""
            current_tab = self.tabs.currentWidget()
            if hasattr(current_tab, 'get_files'):
                return current_tab.get_files()
            return []
        
        @property
        def grouped_files(self) -> Dict:
            """Get grouped files (backward compatibility)."""
            if self.load_mode == 'multi_type2':
                return self.type2_tab.get_groups()
            return {}
        
        @property
        def merge_continuous(self):
            """Get merge continuous checkbox (backward compatibility)."""
            return self.advanced_tab.merge_continuous
        
        @property
        def verify_sampling_rate(self):
            """Get verify sampling rate checkbox (backward compatibility)."""
            return self.advanced_tab.verify_sampling

else:
    class DataInputDialog:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            raise ImportError("PyQt5 is required for DataInputDialog")
