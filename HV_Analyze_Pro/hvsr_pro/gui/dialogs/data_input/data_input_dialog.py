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
        SingleFileTab, MultiType1Tab, MultiType2Tab, AdvancedOptionsTab
    )
    from hvsr_pro.gui.dialogs.data_input.preview_panel import PreviewPanel


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
            self.advanced_tab = AdvancedOptionsTab(self)
            
            # Add tabs
            self.tabs.addTab(self.single_tab, "Single File")
            self.tabs.addTab(self.type1_tab, "Multi-File (3-channel)")
            self.tabs.addTab(self.type2_tab, "Multi-File (Separate E,N,Z)")
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
            
            # Connect file selection signals to preview
            self.single_tab.file_selected.connect(self._on_file_selected_for_preview)
            
            # Connect Type1 files_changed signal for preview
            self.type1_tab.files_changed.connect(self._on_files_changed_for_preview)
            
            # Connect Type2 selection changes
            self.type2_tab.files_changed.connect(self._on_files_changed_for_preview)
            
            # Connect preview_requested signals
            self.single_tab.preview_requested.connect(self._update_preview)
            self.type1_tab.preview_requested.connect(self._update_preview)
            self.type2_tab.preview_requested.connect(self._update_preview)
        
        def _on_tab_changed(self, index: int):
            """Handle tab change to update load mode."""
            mode_map = {0: 'single', 1: 'multi_type1', 2: 'multi_type2', 3: 'advanced'}
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
                    self.type2_tab.is_valid()
                )
                self.load_btn.setEnabled(has_any_data)
        
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
            else:
                tab_result = self.advanced_tab.get_result()
            
            # Validate we have files
            files = tab_result.get('files', [])
            groups = tab_result.get('groups', {})
            
            if not files and not groups:
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
                'time_range': time_range,
                'options': {
                    'merge_continuous': advanced_options.get('merge_continuous', True),
                    'verify_sampling_rate': advanced_options.get('verify_sampling_rate', True),
                    'column_mapping': tab_result.get('column_mapping'),
                    'channel_mapping': tab_result.get('channel_mapping'),
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
