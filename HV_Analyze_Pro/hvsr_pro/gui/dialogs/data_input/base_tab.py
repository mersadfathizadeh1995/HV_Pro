"""
Data Input Tab Base Class
=========================

Base class for data input tabs providing common interface.
"""

from typing import List, Dict, Any, Optional

try:
    from PyQt5.QtWidgets import QWidget, QVBoxLayout
    from PyQt5.QtCore import pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


if HAS_PYQT5:
    class DataInputTabBase(QWidget):
        """
        Base class for data input tabs.
        
        Provides common interface for:
        - File selection/listing
        - Option configuration
        - Validation
        - Preview requests
        
        Subclasses should implement:
        - _init_ui(): Create tab-specific UI
        - get_files(): Return selected files
        - get_options(): Return tab-specific options
        - validate(): Validate selections
        - clear(): Clear all selections
        
        Signals:
            files_changed: Emitted when file list changes (list of file paths)
            preview_requested: Emitted when preview is requested (file path)
            options_changed: Emitted when options change (dict)
            validation_changed: Emitted when validation state changes (bool, str)
        """
        
        # Signals
        files_changed = pyqtSignal(list)
        preview_requested = pyqtSignal(str)
        options_changed = pyqtSignal(dict)
        validation_changed = pyqtSignal(bool, str)  # (is_valid, message)
        
        def __init__(self, parent=None):
            super().__init__(parent)
            self._files = []
            self._options = {}
            self._is_valid = False
            self._validation_message = ""
            
            self._init_ui()
        
        def _init_ui(self):
            """Initialize the user interface. Override in subclass."""
            layout = QVBoxLayout(self)
            layout.setContentsMargins(10, 10, 10, 10)
        
        def get_files(self) -> List[str]:
            """
            Get list of selected files.
            
            Returns:
                List of file paths
            """
            return list(self._files)
        
        def set_files(self, files: List[str]):
            """
            Set list of selected files.
            
            Args:
                files: List of file paths
            """
            self._files = list(files)
            self.files_changed.emit(self._files)
            self._validate()
        
        def add_file(self, file_path: str):
            """
            Add a file to the selection.
            
            Args:
                file_path: Path to file
            """
            if file_path not in self._files:
                self._files.append(file_path)
                self.files_changed.emit(self._files)
                self._validate()
        
        def remove_file(self, file_path: str):
            """
            Remove a file from the selection.
            
            Args:
                file_path: Path to file
            """
            if file_path in self._files:
                self._files.remove(file_path)
                self.files_changed.emit(self._files)
                self._validate()
        
        def clear_files(self):
            """Clear all selected files."""
            self._files = []
            self.files_changed.emit(self._files)
            self._validate()
        
        def get_options(self) -> Dict[str, Any]:
            """
            Get tab-specific options.
            
            Returns:
                Dictionary of options
            """
            return dict(self._options)
        
        def set_options(self, options: Dict[str, Any]):
            """
            Set tab options.
            
            Args:
                options: Dictionary of options
            """
            self._options.update(options)
            self.options_changed.emit(self._options)
        
        def get_option(self, key: str, default=None) -> Any:
            """
            Get a specific option.
            
            Args:
                key: Option key
                default: Default value if not found
                
            Returns:
                Option value
            """
            return self._options.get(key, default)
        
        def set_option(self, key: str, value: Any):
            """
            Set a specific option.
            
            Args:
                key: Option key
                value: Option value
            """
            self._options[key] = value
            self.options_changed.emit(self._options)
        
        def validate(self) -> bool:
            """
            Validate current selections.
            
            Override in subclass for specific validation logic.
            
            Returns:
                True if valid, False otherwise
            """
            return self._validate()
        
        def _validate(self) -> bool:
            """
            Internal validation method.
            
            Override in subclass for specific validation logic.
            
            Returns:
                True if valid
            """
            # Default: valid if at least one file selected
            is_valid = len(self._files) > 0
            message = "" if is_valid else "No files selected"
            
            if self._is_valid != is_valid or self._validation_message != message:
                self._is_valid = is_valid
                self._validation_message = message
                self.validation_changed.emit(is_valid, message)
            
            return is_valid
        
        def is_valid(self) -> bool:
            """Check if current state is valid."""
            return self._is_valid
        
        def get_validation_message(self) -> str:
            """Get validation message."""
            return self._validation_message
        
        def clear(self):
            """Clear all selections and reset to defaults."""
            self.clear_files()
            self._options = {}
            self.options_changed.emit(self._options)
        
        def request_preview(self, file_path: Optional[str] = None):
            """
            Request preview of a file.
            
            Args:
                file_path: File to preview. If None, preview first selected file.
            """
            if file_path:
                self.preview_requested.emit(file_path)
            elif self._files:
                self.preview_requested.emit(self._files[0])
        
        def get_result(self) -> Dict[str, Any]:
            """
            Get complete result dictionary for this tab.
            
            Returns:
                Dictionary with 'files' and 'options' keys
            """
            return {
                'files': self.get_files(),
                'options': self.get_options(),
                'is_valid': self.is_valid(),
            }

else:
    class DataInputTabBase:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass

