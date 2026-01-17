"""
Session Controller
==================

Handles session save/load operations for the main window.
Manages full application state persistence including settings,
windows, HVSR results, and azimuthal analysis data.
"""

from pathlib import Path
from typing import Optional, Dict, Any, Callable, List
from dataclasses import dataclass, field
import json

try:
    from PyQt5.QtWidgets import QWidget, QMessageBox, QFileDialog
    from PyQt5.QtCore import QObject, pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


@dataclass
class GUIState:
    """Represents the current state of GUI settings."""
    # Processing settings
    window_length: float = 60.0
    overlap: float = 0.5
    smoothing_bandwidth: float = 40.0
    freq_min: float = 0.2
    freq_max: float = 20.0
    n_frequencies: int = 100
    
    # QC settings
    qc_enabled: bool = True
    qc_mode: str = 'balanced'
    
    # Cox FDWRA settings
    cox_enabled: bool = False
    cox_n: float = 2.0
    cox_max_iterations: int = 20
    cox_min_iterations: int = 1
    cox_distribution: str = 'lognormal'
    
    # File info
    file_path: str = ''
    load_mode: str = 'single'
    
    # Additional state
    work_directory: str = ''


if HAS_PYQT5:
    class SessionController(QObject):
        """
        Controller for session management.
        
        Handles:
        - Session saving (settings + processed data)
        - Session loading and restoration
        - Work directory management
        - GUI state extraction and restoration
        
        Signals:
            session_saved: Emitted with session path after successful save
            session_loaded: Emitted with session data after successful load
            restore_requested: Emitted when GUI needs to be restored
        """
        
        session_saved = pyqtSignal(str)
        session_loaded = pyqtSignal(dict)
        restore_requested = pyqtSignal(object, object, object)  # hvsr_result, windows, data
        
        def __init__(self, parent: QWidget):
            """
            Initialize session controller.
            
            Args:
                parent: Parent widget (main window)
            """
            super().__init__(parent)
            self.parent = parent
            self.work_directory: Optional[str] = None
            self.current_session_path: Optional[str] = None
            self._recent_sessions: List[str] = []
        
        def set_work_directory(self, path: str):
            """Set the work directory for sessions and temp files."""
            self.work_directory = path
        
        def get_work_directory(self) -> Optional[str]:
            """Get current work directory."""
            return self.work_directory
        
        def save_session(
            self,
            settings: Dict[str, Any],
            windows=None,
            hvsr_result=None,
            seismic_data=None,
            azimuthal_result=None,
            file_info: Optional[Dict] = None,
            progress_callback: Optional[Callable] = None
        ) -> Optional[str]:
            """
            Save complete session to disk.
            
            Args:
                settings: Application settings
                windows: WindowCollection object
                hvsr_result: HVSRResult object
                seismic_data: SeismicData object
                azimuthal_result: AzimuthalHVSRResult object
                file_info: Original file information
                progress_callback: Progress callback
                
            Returns:
                Session path if successful, None otherwise
            """
            from hvsr_pro.config.session import SessionManager
            
            # Determine save location
            default_dir = self.work_directory or str(Path.home())
            
            session_dir = QFileDialog.getExistingDirectory(
                self.parent,
                "Select Session Save Location",
                default_dir
            )
            
            if not session_dir:
                return None
            
            try:
                manager = SessionManager(session_dir)
                
                session_path = manager.save_full_session(
                    settings=settings,
                    windows=windows,
                    hvsr_result=hvsr_result,
                    seismic_data=seismic_data,
                    azimuthal_result=azimuthal_result,
                    file_info=file_info
                )
                
                self.current_session_path = session_path
                
                QMessageBox.information(
                    self.parent, "Session Saved",
                    f"Session saved successfully to:\n{session_path}"
                )
                
                return session_path
                
            except Exception as e:
                QMessageBox.critical(
                    self.parent, "Error",
                    f"Failed to save session:\n{str(e)}"
                )
                return None
        
        def load_session(
            self,
            session_path: Optional[str] = None,
            progress_callback: Optional[Callable] = None
        ) -> Optional[Dict[str, Any]]:
            """
            Load session from disk.
            
            Args:
                session_path: Path to session folder (prompts if None)
                progress_callback: Progress callback
                
            Returns:
                Session data dict if successful, None otherwise
            """
            from hvsr_pro.config.session import SessionManager
            
            if not session_path:
                default_dir = self.work_directory or str(Path.home())
                
                session_path = QFileDialog.getExistingDirectory(
                    self.parent,
                    "Select Session Folder",
                    default_dir
                )
            
            if not session_path:
                return None
            
            try:
                manager = SessionManager(Path(session_path).parent)
                
                state, windows, hvsr_result, seismic_data, azimuthal_result = \
                    manager.load_full_session(session_path)
                
                self.current_session_path = session_path
                
                return {
                    'state': state,
                    'windows': windows,
                    'hvsr_result': hvsr_result,
                    'seismic_data': seismic_data,
                    'azimuthal_result': azimuthal_result,
                }
                
            except Exception as e:
                QMessageBox.critical(
                    self.parent, "Error",
                    f"Failed to load session:\n{str(e)}"
                )
                return None
        
        def get_recent_sessions(self) -> list:
            """Get list of recent sessions."""
            # Could be enhanced to track recent sessions
            return []
        
        def quick_save(
            self,
            settings: Dict[str, Any],
            windows=None,
            hvsr_result=None,
            seismic_data=None,
            azimuthal_result=None,
            file_info: Optional[Dict] = None
        ) -> Optional[str]:
            """Quick save to current session path or work directory."""
            if self.current_session_path:
                # Save to existing location
                pass  # Implementation would update existing session
            elif self.work_directory:
                # Create new session in work directory
                from hvsr_pro.config.session import SessionManager
                manager = SessionManager(self.work_directory)
                return manager.save_full_session(
                    settings=settings,
                    windows=windows,
                    hvsr_result=hvsr_result,
                    seismic_data=seismic_data,
                    azimuthal_result=azimuthal_result,
                    file_info=file_info
                )
            return None
        
        def extract_gui_state(self, main_window) -> GUIState:
            """
            Extract current GUI state from main window.
            
            Args:
                main_window: The HVSRMainWindow instance
            
            Returns:
                GUIState object with current settings
            """
            state = GUIState()
            
            # Processing settings
            if hasattr(main_window, 'window_length_spin'):
                state.window_length = main_window.window_length_spin.value()
            if hasattr(main_window, 'overlap_spin'):
                state.overlap = main_window.overlap_spin.value() / 100.0
            if hasattr(main_window, 'smoothing_spin'):
                state.smoothing_bandwidth = main_window.smoothing_spin.value()
            if hasattr(main_window, 'freq_min_spin'):
                state.freq_min = main_window.freq_min_spin.value()
            if hasattr(main_window, 'freq_max_spin'):
                state.freq_max = main_window.freq_max_spin.value()
            if hasattr(main_window, 'n_freq_spin'):
                state.n_frequencies = main_window.n_freq_spin.value()
            
            # QC settings
            if hasattr(main_window, 'qc_enable_check'):
                state.qc_enabled = main_window.qc_enable_check.isChecked()
            if hasattr(main_window, 'qc_combo'):
                state.qc_mode = main_window.qc_combo.currentData()
            
            # Cox FDWRA settings
            if hasattr(main_window, 'cox_fdwra_check'):
                state.cox_enabled = main_window.cox_fdwra_check.isChecked()
            if hasattr(main_window, 'cox_n_spin'):
                state.cox_n = main_window.cox_n_spin.value()
            if hasattr(main_window, 'cox_iterations_spin'):
                state.cox_max_iterations = main_window.cox_iterations_spin.value()
            if hasattr(main_window, 'cox_min_iterations_spin'):
                state.cox_min_iterations = main_window.cox_min_iterations_spin.value()
            if hasattr(main_window, 'cox_dist_combo'):
                state.cox_distribution = main_window.cox_dist_combo.currentText()
            
            # File info
            state.file_path = str(getattr(main_window, 'current_file', ''))
            state.load_mode = getattr(main_window, 'load_mode', 'single')
            state.work_directory = self.work_directory or ''
            
            return state
        
        def apply_gui_state(self, main_window, state: GUIState):
            """
            Apply GUI state to main window.
            
            Args:
                main_window: The HVSRMainWindow instance
                state: GUIState object with settings to apply
            """
            # Processing settings
            if hasattr(main_window, 'window_length_spin'):
                main_window.window_length_spin.setValue(state.window_length)
            if hasattr(main_window, 'overlap_spin'):
                main_window.overlap_spin.setValue(int(state.overlap * 100))
            if hasattr(main_window, 'smoothing_spin'):
                main_window.smoothing_spin.setValue(state.smoothing_bandwidth)
            if hasattr(main_window, 'freq_min_spin'):
                main_window.freq_min_spin.setValue(state.freq_min)
            if hasattr(main_window, 'freq_max_spin'):
                main_window.freq_max_spin.setValue(state.freq_max)
            if hasattr(main_window, 'n_freq_spin'):
                main_window.n_freq_spin.setValue(state.n_frequencies)
            
            # QC settings
            if hasattr(main_window, 'qc_enable_check'):
                main_window.qc_enable_check.setChecked(state.qc_enabled)
            if hasattr(main_window, 'qc_combo'):
                idx = main_window.qc_combo.findData(state.qc_mode)
                if idx >= 0:
                    main_window.qc_combo.setCurrentIndex(idx)
            
            # Cox FDWRA settings
            if hasattr(main_window, 'cox_fdwra_check'):
                main_window.cox_fdwra_check.setChecked(state.cox_enabled)
            if hasattr(main_window, 'cox_n_spin'):
                main_window.cox_n_spin.setValue(state.cox_n)
            if hasattr(main_window, 'cox_iterations_spin'):
                main_window.cox_iterations_spin.setValue(state.cox_max_iterations)
            if hasattr(main_window, 'cox_min_iterations_spin'):
                main_window.cox_min_iterations_spin.setValue(state.cox_min_iterations)
            if hasattr(main_window, 'cox_dist_combo'):
                main_window.cox_dist_combo.setCurrentText(state.cox_distribution)
            
            # Work directory
            self.work_directory = state.work_directory
            if hasattr(main_window, 'data_load_tab') and hasattr(main_window.data_load_tab, 'work_dir_edit'):
                main_window.data_load_tab.work_dir_edit.setText(state.work_directory)
        
        def enable_buttons_after_restore(self, main_window):
            """
            Enable action buttons after session restore.
            
            Args:
                main_window: The HVSRMainWindow instance
            """
            button_names = ['export_plot_btn', 'report_btn', 'export_btn', 'save_btn']
            for btn_name in button_names:
                if hasattr(main_window, btn_name):
                    getattr(main_window, btn_name).setEnabled(True)
            
            # Window manipulation buttons
            if hasattr(main_window, 'reject_all_btn'):
                main_window.reject_all_btn.setEnabled(True)
            if hasattr(main_window, 'accept_all_btn'):
                main_window.accept_all_btn.setEnabled(True)
            if hasattr(main_window, 'recompute_btn'):
                main_window.recompute_btn.setEnabled(True)
        
        def add_to_recent(self, session_path: str):
            """Add session to recent sessions list."""
            if session_path in self._recent_sessions:
                self._recent_sessions.remove(session_path)
            self._recent_sessions.insert(0, session_path)
            # Keep only last 10
            self._recent_sessions = self._recent_sessions[:10]
        
        def get_recent_sessions(self) -> List[str]:
            """Get list of recent sessions."""
            return self._recent_sessions.copy()
        
        def clear_recent_sessions(self):
            """Clear recent sessions list."""
            self._recent_sessions = []


else:
    class SessionController:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass
