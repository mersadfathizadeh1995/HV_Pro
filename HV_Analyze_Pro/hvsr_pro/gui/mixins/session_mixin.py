"""
Session Management Mixin for HVSR Pro GUI
==========================================

Provides save/load session functionality for the main window.
"""

from pathlib import Path
from typing import Optional

try:
    from PyQt5.QtWidgets import QFileDialog, QMessageBox
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False

from hvsr_pro.config.session import (
    SessionManager, SessionState, 
    ProcessingSettings, QCSettings, FileInfo, WindowState
)


if HAS_PYQT5:
    
    class SessionMixin:
        """
        Mixin class providing session save/load functionality.
        
        Requires the main window to have:
        - Processing settings widgets
        - QC settings widgets
        - Window collection (self.windows)
        - HVSR result (self.hvsr_result)
        - File info (self.current_file, self.load_mode)
        - Work directory (self.work_directory)
        """
        
        def __init__(self):
            """Initialize session manager."""
            self._session_manager = SessionManager()
            self._current_session_path: Optional[str] = None
            self._work_directory: str = ''
        
        def save_session(self):
            """Save current session to file."""
            # Get default directory
            default_dir = self._work_directory or str(Path.home())
            default_name = self._session_manager.get_default_filename()
            
            filepath, _ = QFileDialog.getSaveFileName(
                self,
                "Save Session",
                str(Path(default_dir) / default_name),
                self._session_manager.FILE_FILTER
            )
            
            if not filepath:
                return
            
            # Build session state from current GUI state
            state = self._build_session_state()
            
            if self._session_manager.save_session(filepath, state):
                self._current_session_path = filepath
                self.add_info(f"Session saved: {Path(filepath).name}")
                QMessageBox.information(
                    self, "Session Saved",
                    f"Session saved successfully to:\n{filepath}"
                )
            else:
                QMessageBox.critical(
                    self, "Save Failed",
                    "Failed to save session. Check the log for details."
                )
        
        def load_session(self):
            """Load session from file."""
            # Get default directory
            default_dir = self._work_directory or str(Path.home())
            
            filepath, _ = QFileDialog.getOpenFileName(
                self,
                "Load Session",
                default_dir,
                self._session_manager.FILE_FILTER
            )
            
            if not filepath:
                return
            
            state = self._session_manager.load_session(filepath)
            
            if state:
                self._apply_session_state(state)
                self._current_session_path = filepath
                self.add_info(f"Session loaded: {Path(filepath).name}")
                QMessageBox.information(
                    self, "Session Loaded",
                    f"Session loaded successfully.\n\n"
                    f"File: {state.file_info.path}\n"
                    f"Windows: {state.n_total_windows} total, {state.n_active_windows} active"
                )
            else:
                QMessageBox.critical(
                    self, "Load Failed",
                    "Failed to load session. The file may be corrupted or invalid."
                )
        
        def _build_session_state(self) -> SessionState:
            """Build session state from current GUI state."""
            state = SessionState()
            
            # Work directory
            state.work_directory = getattr(self, '_work_directory', '')
            
            # File info
            current_file = getattr(self, 'current_file', '')
            if isinstance(current_file, list):
                current_file = str(current_file)
            state.file_info = FileInfo(
                path=str(current_file) if current_file else '',
                load_mode=getattr(self, 'load_mode', 'single'),
                time_range_start=None,
                time_range_end=None,
                timezone='UTC'
            )
            
            # Time range if available
            if hasattr(self, 'current_time_range') and self.current_time_range:
                tr = self.current_time_range
                if isinstance(tr, dict):
                    state.file_info.time_range_start = tr.get('start')
                    state.file_info.time_range_end = tr.get('end')
                    state.file_info.timezone = tr.get('timezone', 'UTC')
            
            # Processing settings
            state.processing = ProcessingSettings(
                window_length=self._get_widget_value('window_length_spin', 60.0),
                overlap=self._get_widget_value('overlap_spin', 50) / 100.0,
                smoothing_bandwidth=self._get_widget_value('smoothing_spin', 40.0),
                f_min=self._get_widget_value('freq_min_spin', 0.2),
                f_max=self._get_widget_value('freq_max_spin', 20.0),
                n_frequencies=self._get_widget_value('freq_points_spin', 100)
            )
            
            # QC settings
            state.qc = QCSettings(
                enabled=self._get_widget_checked('qc_enable_check', True),
                mode=self._get_combo_data('qc_combo', 'balanced'),
                cox_fdwra_enabled=self._get_widget_checked('cox_fdwra_check', False),
                cox_n=self._get_widget_value('cox_n_spin', 2.0),
                cox_max_iterations=self._get_widget_value('cox_iterations_spin', 50),
                cox_min_iterations=self._get_widget_value('cox_min_iterations_spin', 1),
                cox_distribution=self._get_combo_text('cox_dist_combo', 'lognormal')
            )
            
            # Window states
            windows = getattr(self, 'windows', None)
            if windows and hasattr(windows, 'windows'):
                state.window_states = [
                    WindowState(
                        index=i,
                        active=w.is_active(),
                        rejection_reason=getattr(w, 'rejection_reason', None)
                    )
                    for i, w in enumerate(windows.windows)
                ]
                state.n_total_windows = len(windows.windows)
                state.n_active_windows = windows.n_active
            
            # Results summary
            result = getattr(self, 'hvsr_result', None)
            if result:
                state.has_results = True
                if hasattr(result, 'peak_frequency'):
                    state.peak_frequency = float(result.peak_frequency)
                if hasattr(result, 'peak_amplitude'):
                    state.peak_amplitude = float(result.peak_amplitude)
            
            return state
        
        def _apply_session_state(self, state: SessionState):
            """Apply loaded session state to GUI."""
            # Work directory
            self._work_directory = state.work_directory
            if hasattr(self, 'work_dir_edit'):
                self.work_dir_edit.setText(state.work_directory)
            
            # Processing settings
            self._set_widget_value('window_length_spin', state.processing.window_length)
            self._set_widget_value('overlap_spin', int(state.processing.overlap * 100))
            self._set_widget_value('smoothing_spin', state.processing.smoothing_bandwidth)
            self._set_widget_value('freq_min_spin', state.processing.f_min)
            self._set_widget_value('freq_max_spin', state.processing.f_max)
            self._set_widget_value('freq_points_spin', state.processing.n_frequencies)
            
            # QC settings
            self._set_widget_checked('qc_enable_check', state.qc.enabled)
            self._set_combo_data('qc_combo', state.qc.mode)
            self._set_widget_checked('cox_fdwra_check', state.qc.cox_fdwra_enabled)
            self._set_widget_value('cox_n_spin', state.qc.cox_n)
            self._set_widget_value('cox_iterations_spin', state.qc.cox_max_iterations)
            self._set_widget_value('cox_min_iterations_spin', state.qc.cox_min_iterations)
            self._set_combo_text('cox_dist_combo', state.qc.cox_distribution)
            
            # Note: Window states would need to be reloaded when data is loaded
            # Store them for later application
            self._pending_window_states = state.window_states
            
            # File info - prompt user to load the file
            if state.file_info.path and Path(state.file_info.path).exists():
                reply = QMessageBox.question(
                    self, "Load Data File",
                    f"Session references data file:\n{state.file_info.path}\n\n"
                    "Would you like to load this file now?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                
                if reply == QMessageBox.Yes:
                    self._load_file_from_session(state.file_info)
        
        def _load_file_from_session(self, file_info: FileInfo):
            """Load file referenced in session."""
            # This should trigger the normal file loading process
            # Subclass needs to implement this based on its file loading mechanism
            if hasattr(self, 'load_file_directly'):
                self.load_file_directly(file_info.path, file_info.load_mode)
        
        def _get_widget_value(self, widget_name: str, default):
            """Get value from a spin box widget."""
            widget = getattr(self, widget_name, None)
            if widget and hasattr(widget, 'value'):
                return widget.value()
            return default
        
        def _set_widget_value(self, widget_name: str, value):
            """Set value on a spin box widget."""
            widget = getattr(self, widget_name, None)
            if widget and hasattr(widget, 'setValue'):
                widget.setValue(value)
        
        def _get_widget_checked(self, widget_name: str, default: bool) -> bool:
            """Get checked state from a checkbox."""
            widget = getattr(self, widget_name, None)
            if widget and hasattr(widget, 'isChecked'):
                return widget.isChecked()
            return default
        
        def _set_widget_checked(self, widget_name: str, checked: bool):
            """Set checked state on a checkbox."""
            widget = getattr(self, widget_name, None)
            if widget and hasattr(widget, 'setChecked'):
                widget.setChecked(checked)
        
        def _get_combo_text(self, widget_name: str, default: str) -> str:
            """Get current text from a combo box."""
            widget = getattr(self, widget_name, None)
            if widget and hasattr(widget, 'currentText'):
                return widget.currentText()
            return default
        
        def _set_combo_text(self, widget_name: str, text: str):
            """Set current text on a combo box."""
            widget = getattr(self, widget_name, None)
            if widget and hasattr(widget, 'setCurrentText'):
                widget.setCurrentText(text)
        
        def _get_combo_data(self, widget_name: str, default: str) -> str:
            """Get current data from a combo box."""
            widget = getattr(self, widget_name, None)
            if widget and hasattr(widget, 'currentData'):
                data = widget.currentData()
                return data if data else default
            return default
        
        def _set_combo_data(self, widget_name: str, data):
            """Set current item by data on a combo box."""
            widget = getattr(self, widget_name, None)
            if widget and hasattr(widget, 'findData'):
                index = widget.findData(data)
                if index >= 0:
                    widget.setCurrentIndex(index)
        
        def set_work_directory(self, directory: str):
            """Set the work directory."""
            self._work_directory = directory
            self._session_manager.work_directory = Path(directory)
        
        def get_work_directory(self) -> str:
            """Get the work directory."""
            return self._work_directory


else:
    class SessionMixin:
        """Dummy mixin when PyQt5 not available."""
        pass
