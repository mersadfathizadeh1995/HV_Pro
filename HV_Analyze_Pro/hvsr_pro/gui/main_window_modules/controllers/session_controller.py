"""
Session Controller
==================

Handles session save/load operations for the main window.
"""

from pathlib import Path
from typing import Optional, Dict, Any, Callable
import json

try:
    from PyQt5.QtWidgets import QWidget, QMessageBox, QFileDialog
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


if HAS_PYQT5:
    class SessionController:
        """
        Controller for session management.
        
        Handles:
        - Session saving (settings + processed data)
        - Session loading and restoration
        - Work directory management
        """
        
        def __init__(self, parent: QWidget):
            """
            Initialize session controller.
            
            Args:
                parent: Parent widget (main window)
            """
            self.parent = parent
            self.work_directory: Optional[str] = None
            self.current_session_path: Optional[str] = None
        
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

else:
    class SessionController:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass
