"""
Advanced Options Tab
====================

Tab for advanced data loading options.
"""

from typing import Dict, Any

try:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QGroupBox, QCheckBox, QLabel
    )
    from PyQt5.QtCore import pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False

if HAS_PYQT5:
    from hvsr_pro.gui.dialogs.data_input.base_tab import DataInputTabBase


if HAS_PYQT5:
    class AdvancedOptionsTab(DataInputTabBase):
        """
        Tab for advanced options.
        
        Features:
        - Merge options
        - Sampling rate verification
        
        Signals:
            options_updated: Emitted when options change (dict)
        """
        
        options_updated = pyqtSignal(dict)
        
        def __init__(self, parent=None):
            super().__init__(parent)
        
        def _init_ui(self):
            """Initialize the user interface."""
            layout = QVBoxLayout(self)
            
            # Info about time range
            info_group = QGroupBox("Time Range Selection")
            info_layout = QVBoxLayout(info_group)
            
            info_label = QLabel(
                "Time range selection is now available in each tab:\n\n"
                "- Single File tab - Extract time slice from single file\n"
                "- Multi-File Type 1 tab - Extract time slice from merged files\n"
                "- Multi-File Type 2 tab - Extract time slice from grouped files\n\n"
                "Switch to the appropriate tab to use this feature."
            )
            info_label.setWordWrap(True)
            info_layout.addWidget(info_label)
            
            layout.addWidget(info_group)
            
            # Merge options
            merge_group = QGroupBox("Merging Options")
            merge_layout = QVBoxLayout(merge_group)
            
            self.merge_continuous = QCheckBox("Merge continuous segments")
            self.merge_continuous.setChecked(True)
            self.merge_continuous.stateChanged.connect(self._on_options_changed)
            merge_layout.addWidget(self.merge_continuous)
            
            self.verify_sampling = QCheckBox("Verify consistent sampling rate")
            self.verify_sampling.setChecked(True)
            self.verify_sampling.stateChanged.connect(self._on_options_changed)
            merge_layout.addWidget(self.verify_sampling)
            
            layout.addWidget(merge_group)
            
            layout.addStretch()
        
        def _on_options_changed(self):
            """Handle options change."""
            options = self.get_advanced_options()
            self.set_options(options)
            self.options_updated.emit(options)
        
        def get_advanced_options(self) -> Dict[str, Any]:
            """Get advanced options."""
            return {
                'merge_continuous': self.merge_continuous.isChecked(),
                'verify_sampling_rate': self.verify_sampling.isChecked(),
            }
        
        def set_advanced_options(self, options: Dict[str, Any]):
            """Set advanced options."""
            if 'merge_continuous' in options:
                self.merge_continuous.setChecked(options['merge_continuous'])
            if 'verify_sampling_rate' in options:
                self.verify_sampling.setChecked(options['verify_sampling_rate'])
        
        def _validate(self) -> bool:
            """Always valid - just options."""
            self._is_valid = True
            self._validation_message = ""
            return True
        
        def get_result(self) -> Dict[str, Any]:
            """Get complete result dictionary."""
            return {
                'files': [],
                'options': self.get_advanced_options(),
                'is_valid': True,
            }

else:
    class AdvancedOptionsTab:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass
