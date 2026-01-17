"""
Session Controller
==================

Handles session save/load operations for the main window.
Manages full application state persistence including settings,
windows, HVSR results, and azimuthal analysis data.
"""

from pathlib import Path
from typing import Optional, Dict, Any, Callable, List, Tuple
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


@dataclass 
class SaveResult:
    """Result from save operation."""
    success: bool
    session_folder: str = ''
    info_message: str = ''
    error_message: str = ''


@dataclass
class LoadResult:
    """Result from load operation."""
    success: bool
    state: Any = None
    windows: Any = None
    hvsr_result: Any = None
    seismic_data: Any = None
    azimuthal_result: Any = None
    error_message: str = ''


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
            info_message: Emitted with info messages
        """
        
        session_saved = pyqtSignal(str)
        session_loaded = pyqtSignal(dict)
        restore_requested = pyqtSignal(object, object, object)  # hvsr_result, windows, data
        info_message = pyqtSignal(str)
        
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
        
        def ensure_work_directory(self) -> Optional[str]:
            """
            Ensure a work directory is set, prompting user if needed.
            
            Returns:
                Work directory path or None if user cancelled
            """
            work_dir = self.work_directory or getattr(self.parent, '_work_directory', '')
            
            if not work_dir:
                reply = QMessageBox.question(
                    self.parent, "Work Directory Required",
                    "Please set a work directory first to save sessions.\n\n"
                    "Would you like to select a work directory now?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                if reply == QMessageBox.Yes:
                    work_dir = QFileDialog.getExistingDirectory(
                        self.parent, "Select Work Directory"
                    )
                    if work_dir:
                        self.work_directory = work_dir
                        self.parent._work_directory = work_dir
                        if hasattr(self.parent, 'data_load_tab') and hasattr(self.parent.data_load_tab, 'work_dir_edit'):
                            self.parent.data_load_tab.work_dir_edit.setText(work_dir)
                    else:
                        return None
                else:
                    return None
            
            return work_dir
        
        def save_full_session(self, main_window=None) -> SaveResult:
            """
            Save complete session from main window state.
            
            This is the main entry point for saving sessions.
            Extracts all state from main_window and saves to disk.
            
            Args:
                main_window: The HVSRMainWindow instance (uses self.parent if None)
                
            Returns:
                SaveResult with success status and details
            """
            from hvsr_pro.config.session import (
                SessionManager, SessionState,
                ProcessingSettings as SessionProcessingSettings,
                QCSettings as SessionQCSettings,
                FileInfo, WindowState
            )
            
            mw = main_window or self.parent
            
            # Ensure work directory
            work_dir = self.ensure_work_directory()
            if not work_dir:
                return SaveResult(success=False, error_message="No work directory selected")
            
            try:
                manager = SessionManager(work_directory=work_dir)
                
                # Build session state
                state = SessionState()
                state.work_directory = work_dir
                
                # File info
                current_file = getattr(mw, 'current_file', '')
                if isinstance(current_file, list):
                    current_file = ';'.join(str(f) for f in current_file)
                state.file_info = FileInfo(
                    path=str(current_file) if current_file else '',
                    load_mode=getattr(mw, 'load_mode', 'single')
                )
                
                # Processing settings
                state.processing = SessionProcessingSettings(
                    window_length=mw.window_length_spin.value() if hasattr(mw, 'window_length_spin') else 60.0,
                    overlap=mw.overlap_spin.value() / 100.0 if hasattr(mw, 'overlap_spin') else 0.5,
                    smoothing_bandwidth=mw.smoothing_spin.value() if hasattr(mw, 'smoothing_spin') else 40.0,
                    f_min=mw.freq_min_spin.value() if hasattr(mw, 'freq_min_spin') else 0.2,
                    f_max=mw.freq_max_spin.value() if hasattr(mw, 'freq_max_spin') else 20.0,
                    n_frequencies=getattr(mw, 'n_freq_spin', None)
                        and mw.n_freq_spin.value() or 100
                )
                
                # QC settings
                state.qc = SessionQCSettings(
                    enabled=mw.qc_enable_check.isChecked() if hasattr(mw, 'qc_enable_check') else True,
                    mode=mw.qc_combo.currentData() if hasattr(mw, 'qc_combo') else 'balanced',
                    cox_fdwra_enabled=mw.cox_fdwra_check.isChecked() if hasattr(mw, 'cox_fdwra_check') else False,
                    cox_n=mw.cox_n_spin.value() if hasattr(mw, 'cox_n_spin') else 2.0,
                    cox_max_iterations=mw.cox_iterations_spin.value() if hasattr(mw, 'cox_iterations_spin') else 50,
                    cox_min_iterations=mw.cox_min_iterations_spin.value() if hasattr(mw, 'cox_min_iterations_spin') else 1,
                    cox_distribution=mw.cox_dist_combo.currentText() if hasattr(mw, 'cox_dist_combo') else 'lognormal'
                )
                
                # Window states
                windows = getattr(mw, 'windows', None)
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
                
                # HVSR results
                hvsr_result = getattr(mw, 'hvsr_result', None)
                if hvsr_result:
                    state.has_results = True
                    state.peak_frequency = self._extract_peak_frequency(hvsr_result)
                    state.peak_amplitude = self._extract_peak_amplitude(hvsr_result)
                
                # Get seismic data and azimuthal result
                seismic_data = getattr(mw, 'seismic_data', None) or getattr(mw, 'data', None)
                azimuthal_result = None
                if hasattr(mw, 'azimuthal_tab') and hasattr(mw.azimuthal_tab, 'result'):
                    azimuthal_result = mw.azimuthal_tab.result
                
                # Save full session
                session_folder = manager.save_full_session(
                    state=state,
                    windows=windows,
                    hvsr_result=hvsr_result,
                    seismic_data=seismic_data,
                    azimuthal_result=azimuthal_result
                )
                
                if session_folder:
                    self.current_session_path = session_folder
                    self.add_to_recent(session_folder)
                    
                    # Build info message
                    info_msg = f"Session saved successfully to:\n{session_folder}\n\n"
                    info_msg += "Saved data:\n"
                    info_msg += "  - Settings and metadata\n"
                    if windows:
                        info_msg += f"  - Window collection ({state.n_total_windows} windows)\n"
                    if hvsr_result:
                        if state.peak_frequency is not None:
                            info_msg += f"  - HVSR results (f0 = {state.peak_frequency:.3f} Hz)\n"
                        else:
                            info_msg += "  - HVSR results\n"
                    if seismic_data:
                        info_msg += "  - Original seismic data\n"
                    if azimuthal_result:
                        info_msg += "  - Azimuthal processing results\n"
                    
                    self.info_message.emit(f"Session saved: {Path(session_folder).name}")
                    self.session_saved.emit(session_folder)
                    
                    return SaveResult(
                        success=True,
                        session_folder=session_folder,
                        info_message=info_msg
                    )
                else:
                    return SaveResult(
                        success=False,
                        error_message="Failed to save session. Check the log for details."
                    )
                    
            except Exception as e:
                import traceback
                return SaveResult(
                    success=False,
                    error_message=f"Failed to save session:\n{str(e)}\n{traceback.format_exc()}"
                )
        
        def load_full_session(self, session_path: str = None) -> LoadResult:
            """
            Load complete session and return all components.
            
            This is the main entry point for loading sessions.
            
            Args:
                session_path: Path to session.json file (prompts if None)
                
            Returns:
                LoadResult with all session components
            """
            from hvsr_pro.config.session import SessionManager
            
            # Get file path if not provided
            if not session_path:
                work_dir = self.work_directory or getattr(self.parent, '_work_directory', '')
                default_dir = work_dir if work_dir else str(Path.home())
                
                # Check for sessions folder
                sessions_dir = Path(default_dir) / 'sessions'
                if sessions_dir.exists():
                    default_dir = str(sessions_dir)
                
                file_path, _ = QFileDialog.getOpenFileName(
                    self.parent, "Load Session",
                    default_dir,
                    "Session Files (session.json);;All Files (*)"
                )
                
                if not file_path:
                    return LoadResult(success=False, error_message="No file selected")
                    
                session_path = file_path
            
            try:
                manager = SessionManager(
                    work_directory=self.work_directory or str(Path(session_path).parent.parent)
                )
                
                # Load session data
                state, windows, hvsr_result, seismic_data, azimuthal_result = \
                    manager.load_full_session(session_path)
                
                if not state:
                    return LoadResult(
                        success=False,
                        error_message="Failed to load session. The file may be corrupted or invalid."
                    )
                
                self.current_session_path = session_path
                self.add_to_recent(session_path)
                
                self.info_message.emit(f"Session loaded: {Path(session_path).parent.name}")
                
                return LoadResult(
                    success=True,
                    state=state,
                    windows=windows,
                    hvsr_result=hvsr_result,
                    seismic_data=seismic_data,
                    azimuthal_result=azimuthal_result
                )
                
            except Exception as e:
                import traceback
                return LoadResult(
                    success=False,
                    error_message=f"Failed to load session:\n{str(e)}\n{traceback.format_exc()}"
                )
        
        def apply_session_state(self, main_window, load_result: LoadResult):
            """
            Apply loaded session state to the main window.
            
            Args:
                main_window: The HVSRMainWindow instance
                load_result: LoadResult from load_full_session
            """
            if not load_result.success or not load_result.state:
                return
            
            state = load_result.state
            mw = main_window
            
            # Work directory
            mw._work_directory = state.work_directory
            self.work_directory = state.work_directory
            if hasattr(mw, 'data_load_tab') and hasattr(mw.data_load_tab, 'work_dir_edit'):
                mw.data_load_tab.work_dir_edit.setText(state.work_directory)
            
            # Processing settings
            if hasattr(state, 'processing'):
                if hasattr(mw, 'window_length_spin'):
                    mw.window_length_spin.setValue(state.processing.window_length)
                if hasattr(mw, 'overlap_spin'):
                    mw.overlap_spin.setValue(int(state.processing.overlap * 100))
                if hasattr(mw, 'smoothing_spin'):
                    mw.smoothing_spin.setValue(state.processing.smoothing_bandwidth)
                if hasattr(mw, 'freq_min_spin'):
                    mw.freq_min_spin.setValue(state.processing.f_min)
                if hasattr(mw, 'freq_max_spin'):
                    mw.freq_max_spin.setValue(state.processing.f_max)
                if hasattr(mw, 'n_freq_spin') and hasattr(state.processing, 'n_frequencies'):
                    mw.n_freq_spin.setValue(state.processing.n_frequencies)
            
            # QC settings
            if hasattr(state, 'qc'):
                if hasattr(mw, 'qc_enable_check'):
                    mw.qc_enable_check.setChecked(state.qc.enabled)
                if hasattr(mw, 'qc_combo'):
                    idx = mw.qc_combo.findData(state.qc.mode)
                    if idx >= 0:
                        mw.qc_combo.setCurrentIndex(idx)
                if hasattr(mw, 'cox_fdwra_check'):
                    mw.cox_fdwra_check.setChecked(state.qc.cox_fdwra_enabled)
                if hasattr(mw, 'cox_n_spin'):
                    mw.cox_n_spin.setValue(state.qc.cox_n)
                if hasattr(mw, 'cox_iterations_spin'):
                    mw.cox_iterations_spin.setValue(state.qc.cox_max_iterations)
                if hasattr(mw, 'cox_min_iterations_spin'):
                    mw.cox_min_iterations_spin.setValue(state.qc.cox_min_iterations)
                if hasattr(mw, 'cox_dist_combo'):
                    mw.cox_dist_combo.setCurrentText(state.qc.cox_distribution)
            
            # File info
            if hasattr(state, 'file_info') and state.file_info.path:
                mw.current_file = state.file_info.path
                mw.load_mode = state.file_info.load_mode
                
                # Restore to data load tab
                if hasattr(mw, 'data_load_tab'):
                    if hasattr(mw.data_load_tab, 'file_path_edit'):
                        mw.data_load_tab.file_path_edit.setText(state.file_info.path)
                    elif hasattr(mw.data_load_tab, 'file_label'):
                        mw.data_load_tab.file_label.setText(f"File: {state.file_info.path}")
                
                # Check if file exists
                if not Path(state.file_info.path).exists():
                    self.info_message.emit(f"Warning: Original file not found: {state.file_info.path}")
                else:
                    self.info_message.emit(f"Original file path restored: {state.file_info.path}")
            
            # Store seismic_data
            if load_result.seismic_data is not None:
                mw.seismic_data = load_result.seismic_data
        
        def _extract_peak_frequency(self, hvsr_result) -> Optional[float]:
            """Extract peak frequency from HVSRResult."""
            if hasattr(hvsr_result, 'peak_frequency') and hvsr_result.peak_frequency is not None:
                return float(hvsr_result.peak_frequency)
            elif hasattr(hvsr_result, 'f0') and hvsr_result.f0 is not None:
                return float(hvsr_result.f0)
            elif hasattr(hvsr_result, 'peaks') and hvsr_result.peaks:
                if isinstance(hvsr_result.peaks, list) and len(hvsr_result.peaks) > 0:
                    first_peak = hvsr_result.peaks[0]
                    if isinstance(first_peak, dict) and 'frequency' in first_peak:
                        return float(first_peak['frequency'])
                    elif hasattr(first_peak, 'frequency'):
                        return float(first_peak.frequency)
            return None
        
        def _extract_peak_amplitude(self, hvsr_result) -> Optional[float]:
            """Extract peak amplitude from HVSRResult."""
            if hasattr(hvsr_result, 'peak_amplitude') and hvsr_result.peak_amplitude is not None:
                return float(hvsr_result.peak_amplitude)
            elif hasattr(hvsr_result, 'a0') and hvsr_result.a0 is not None:
                return float(hvsr_result.a0)
            return None
        
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
            Save complete session to disk (legacy interface).
            
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
            Load session from disk (legacy interface).
            """
            result = self.load_full_session(session_path)
            
            if result.success:
                return {
                    'state': result.state,
                    'windows': result.windows,
                    'hvsr_result': result.hvsr_result,
                    'seismic_data': result.seismic_data,
                    'azimuthal_result': result.azimuthal_result,
                }
            return None
        
        def get_recent_sessions(self) -> List[str]:
            """Get list of recent sessions."""
            return self._recent_sessions.copy()
        
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
                pass  # Would update existing session
            elif self.work_directory:
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
            """Extract current GUI state from main window."""
            state = GUIState()
            
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
            
            if hasattr(main_window, 'qc_enable_check'):
                state.qc_enabled = main_window.qc_enable_check.isChecked()
            if hasattr(main_window, 'qc_combo'):
                state.qc_mode = main_window.qc_combo.currentData()
            
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
            
            state.file_path = str(getattr(main_window, 'current_file', ''))
            state.load_mode = getattr(main_window, 'load_mode', 'single')
            state.work_directory = self.work_directory or ''
            
            return state
        
        def apply_gui_state(self, main_window, state: GUIState):
            """Apply GUI state to main window."""
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
            
            if hasattr(main_window, 'qc_enable_check'):
                main_window.qc_enable_check.setChecked(state.qc_enabled)
            if hasattr(main_window, 'qc_combo'):
                idx = main_window.qc_combo.findData(state.qc_mode)
                if idx >= 0:
                    main_window.qc_combo.setCurrentIndex(idx)
            
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
            
            self.work_directory = state.work_directory
            if hasattr(main_window, 'data_load_tab') and hasattr(main_window.data_load_tab, 'work_dir_edit'):
                main_window.data_load_tab.work_dir_edit.setText(state.work_directory)
        
        def enable_buttons_after_restore(self, main_window):
            """Enable action buttons after session restore."""
            button_names = ['export_plot_btn', 'report_btn', 'export_btn', 'save_btn']
            for btn_name in button_names:
                if hasattr(main_window, btn_name):
                    getattr(main_window, btn_name).setEnabled(True)
            
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
            self._recent_sessions = self._recent_sessions[:10]
        
        def clear_recent_sessions(self):
            """Clear recent sessions list."""
            self._recent_sessions = []


else:
    @dataclass
    class SaveResult:
        success: bool = False
        session_folder: str = ''
        info_message: str = ''
        error_message: str = ''
    
    @dataclass
    class LoadResult:
        success: bool = False
        state: Any = None
        windows: Any = None
        hvsr_result: Any = None
        seismic_data: Any = None
        azimuthal_result: Any = None
        error_message: str = ''
    
    class SessionController:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass
