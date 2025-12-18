"""
Session Management for HVSR Pro
================================

Save and load application state for resuming work sessions.
Supports full session persistence including computed results.
"""

import json
import logging
import pickle
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict, field

logger = logging.getLogger(__name__)

__all__ = ['SessionManager', 'SessionState', 'save_session', 'load_session']


@dataclass
class ProcessingSettings:
    """Processing parameters for HVSR analysis."""
    window_length: float = 60.0
    overlap: float = 0.5
    smoothing_bandwidth: float = 40.0
    f_min: float = 0.2
    f_max: float = 20.0
    n_frequencies: int = 100


@dataclass
class QCSettings:
    """Quality control settings."""
    enabled: bool = True
    mode: str = 'balanced'
    cox_fdwra_enabled: bool = False
    cox_n: float = 2.0
    cox_max_iterations: int = 50
    cox_min_iterations: int = 1
    cox_distribution: str = 'lognormal'


@dataclass
class FileInfo:
    """Information about loaded files."""
    path: str = ''
    load_mode: str = 'single'  # 'single', 'multi_type1', 'multi_type2'
    time_range_start: Optional[str] = None
    time_range_end: Optional[str] = None
    timezone: str = 'UTC'


@dataclass
class WindowState:
    """State of a single window."""
    index: int = 0
    active: bool = True
    rejection_reason: Optional[str] = None


@dataclass
class SessionState:
    """Complete application state with full data persistence."""
    # Metadata
    version: str = '2.0'  # Updated version for full persistence
    created: str = field(default_factory=lambda: datetime.now().isoformat())
    modified: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # File info
    file_info: FileInfo = field(default_factory=FileInfo)
    work_directory: str = ''
    session_folder: str = ''  # Path to session folder containing all data
    
    # Processing settings
    processing: ProcessingSettings = field(default_factory=ProcessingSettings)
    
    # QC settings
    qc: QCSettings = field(default_factory=QCSettings)
    
    # Window states (index: active)
    window_states: List[WindowState] = field(default_factory=list)
    
    # Binary data file paths (relative to session folder)
    windows_file: str = ''          # Pickled WindowCollection
    hvsr_result_file: str = ''      # Pickled HVSRResult
    seismic_data_file: str = ''     # Pickled SeismicData (optional)
    azimuthal_result_file: str = '' # Pickled AzimuthalHVSRResult (optional)
    
    # Results summary
    has_results: bool = False
    has_full_data: bool = False     # True if binary data files exist
    has_azimuthal: bool = False     # True if azimuthal processing was done
    peak_frequency: Optional[float] = None
    peak_amplitude: Optional[float] = None
    n_total_windows: int = 0
    n_active_windows: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'version': self.version,
            'created': self.created,
            'modified': datetime.now().isoformat(),
            'file_info': asdict(self.file_info),
            'work_directory': self.work_directory,
            'session_folder': self.session_folder,
            'processing': asdict(self.processing),
            'qc': asdict(self.qc),
            'window_states': [asdict(w) for w in self.window_states],
            'windows_file': self.windows_file,
            'hvsr_result_file': self.hvsr_result_file,
            'seismic_data_file': self.seismic_data_file,
            'azimuthal_result_file': self.azimuthal_result_file,
            'has_results': self.has_results,
            'has_full_data': self.has_full_data,
            'has_azimuthal': self.has_azimuthal,
            'peak_frequency': self.peak_frequency,
            'peak_amplitude': self.peak_amplitude,
            'n_total_windows': self.n_total_windows,
            'n_active_windows': self.n_active_windows
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SessionState':
        """Create SessionState from dictionary."""
        state = cls()
        
        state.version = data.get('version', '1.0')
        state.created = data.get('created', '')
        state.modified = data.get('modified', '')
        
        # File info
        fi = data.get('file_info', {})
        state.file_info = FileInfo(
            path=fi.get('path', ''),
            load_mode=fi.get('load_mode', 'single'),
            time_range_start=fi.get('time_range_start'),
            time_range_end=fi.get('time_range_end'),
            timezone=fi.get('timezone', 'UTC')
        )
        
        state.work_directory = data.get('work_directory', '')
        state.session_folder = data.get('session_folder', '')
        
        # Processing settings
        ps = data.get('processing', {})
        state.processing = ProcessingSettings(
            window_length=ps.get('window_length', 60.0),
            overlap=ps.get('overlap', 0.5),
            smoothing_bandwidth=ps.get('smoothing_bandwidth', 40.0),
            f_min=ps.get('f_min', 0.2),
            f_max=ps.get('f_max', 20.0),
            n_frequencies=ps.get('n_frequencies', 100)
        )
        
        # QC settings
        qc = data.get('qc', {})
        state.qc = QCSettings(
            enabled=qc.get('enabled', True),
            mode=qc.get('mode', 'balanced'),
            cox_fdwra_enabled=qc.get('cox_fdwra_enabled', False),
            cox_n=qc.get('cox_n', 2.0),
            cox_max_iterations=qc.get('cox_max_iterations', 50),
            cox_min_iterations=qc.get('cox_min_iterations', 1),
            cox_distribution=qc.get('cox_distribution', 'lognormal')
        )
        
        # Window states
        state.window_states = [
            WindowState(
                index=w.get('index', 0),
                active=w.get('active', True),
                rejection_reason=w.get('rejection_reason')
            )
            for w in data.get('window_states', [])
        ]
        
        # Binary data file paths
        state.windows_file = data.get('windows_file', '')
        state.hvsr_result_file = data.get('hvsr_result_file', '')
        state.seismic_data_file = data.get('seismic_data_file', '')
        state.azimuthal_result_file = data.get('azimuthal_result_file', '')
        
        # Results
        state.has_results = data.get('has_results', False)
        state.has_full_data = data.get('has_full_data', False)
        state.has_azimuthal = data.get('has_azimuthal', False)
        state.peak_frequency = data.get('peak_frequency')
        state.peak_amplitude = data.get('peak_amplitude')
        state.n_total_windows = data.get('n_total_windows', 0)
        state.n_active_windows = data.get('n_active_windows', 0)
        
        return state


class SessionManager:
    """
    Manages saving and loading of application sessions with full data persistence.
    
    Session structure:
        work_directory/
          sessions/
            session_YYYYMMDD_HHMMSS/
              session.json           # Settings + metadata
              windows.pkl            # WindowCollection (pickled)
              hvsr_result.pkl        # HVSRResult (pickled)
              seismic_data.pkl       # Original SeismicData (optional)
    
    Example:
        >>> manager = SessionManager(work_directory="/path/to/work")
        >>> manager.save_full_session(state, windows, hvsr_result, seismic_data)
        >>> state, windows, hvsr_result, seismic_data = manager.load_full_session("session_folder")
    """
    
    FILE_EXTENSION = '.hvsr_session'
    SESSIONS_FOLDER = 'sessions'
    SETTINGS_FILE = 'session.json'
    WINDOWS_FILE = 'windows.pkl'
    HVSR_RESULT_FILE = 'hvsr_result.pkl'
    SEISMIC_DATA_FILE = 'seismic_data.pkl'
    FILE_FILTER = 'HVSR Session (session.json);;All Files (*)'
    
    def __init__(self, work_directory: str = None):
        """
        Initialize session manager.
        
        Args:
            work_directory: Default directory for session files
        """
        self.work_directory = Path(work_directory) if work_directory else Path.home()
    
    def get_sessions_directory(self) -> Path:
        """Get the sessions directory, creating it if necessary."""
        sessions_dir = self.work_directory / self.SESSIONS_FOLDER
        sessions_dir.mkdir(parents=True, exist_ok=True)
        return sessions_dir
    
    def create_session_folder(self) -> Path:
        """Create a new timestamped session folder."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        session_folder = self.get_sessions_directory() / f"session_{timestamp}"
        session_folder.mkdir(parents=True, exist_ok=True)
        return session_folder
    
    AZIMUTHAL_RESULT_FILE = 'azimuthal_result.pkl'
    
    def save_full_session(self,
                         state: SessionState,
                         windows=None,
                         hvsr_result=None,
                         seismic_data=None,
                         azimuthal_result=None) -> Optional[Path]:
        """
        Save complete session including computed data.
        
        Args:
            state: SessionState with settings
            windows: WindowCollection to save (optional)
            hvsr_result: HVSRResult to save (optional)
            seismic_data: SeismicData to save (optional)
            azimuthal_result: AzimuthalHVSRResult to save (optional)
            
        Returns:
            Path to session folder if successful, None otherwise
        """
        try:
            # Create session folder
            session_folder = self.create_session_folder()
            state.session_folder = str(session_folder)
            
            # Save windows
            if windows is not None:
                windows_path = session_folder / self.WINDOWS_FILE
                with open(windows_path, 'wb') as f:
                    pickle.dump(windows, f)
                state.windows_file = self.WINDOWS_FILE
                logger.info(f"Saved windows to: {windows_path}")
            
            # Save HVSR result
            if hvsr_result is not None:
                result_path = session_folder / self.HVSR_RESULT_FILE
                with open(result_path, 'wb') as f:
                    pickle.dump(hvsr_result, f)
                state.hvsr_result_file = self.HVSR_RESULT_FILE
                logger.info(f"Saved HVSR result to: {result_path}")
            
            # Save seismic data (optional, can be large)
            if seismic_data is not None:
                data_path = session_folder / self.SEISMIC_DATA_FILE
                with open(data_path, 'wb') as f:
                    pickle.dump(seismic_data, f)
                state.seismic_data_file = self.SEISMIC_DATA_FILE
                logger.info(f"Saved seismic data to: {data_path}")
            
            # Save azimuthal result (optional)
            if azimuthal_result is not None:
                azimuthal_path = session_folder / self.AZIMUTHAL_RESULT_FILE
                with open(azimuthal_path, 'wb') as f:
                    pickle.dump(azimuthal_result, f)
                state.azimuthal_result_file = self.AZIMUTHAL_RESULT_FILE
                state.has_azimuthal = True
                logger.info(f"Saved azimuthal result to: {azimuthal_path}")
            
            # Update state flags
            state.has_full_data = bool(state.windows_file or state.hvsr_result_file)
            
            # Save settings JSON
            settings_path = session_folder / self.SETTINGS_FILE
            with open(settings_path, 'w', encoding='utf-8') as f:
                json.dump(state.to_dict(), f, indent=2, ensure_ascii=False)
            
            logger.info(f"Full session saved to: {session_folder}")
            return session_folder
            
        except Exception as e:
            logger.error(f"Failed to save full session: {e}")
            return None
    
    def load_full_session(self, session_path: str) -> tuple:
        """
        Load complete session including computed data.
        
        Args:
            session_path: Path to session folder or session.json file
            
        Returns:
            Tuple of (SessionState, windows, hvsr_result, seismic_data, azimuthal_result)
            Any item may be None if not available
        """
        try:
            session_path = Path(session_path)
            
            # Determine session folder
            if session_path.is_file():
                session_folder = session_path.parent
            else:
                session_folder = session_path
            
            # Load settings
            settings_path = session_folder / self.SETTINGS_FILE
            if not settings_path.exists():
                logger.error(f"Session settings not found: {settings_path}")
                return None, None, None, None, None
            
            with open(settings_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            state = SessionState.from_dict(data)
            state.session_folder = str(session_folder)
            
            # Load windows
            windows = None
            if state.windows_file:
                windows_path = session_folder / state.windows_file
                if windows_path.exists():
                    with open(windows_path, 'rb') as f:
                        windows = pickle.load(f)
                    logger.info(f"Loaded windows from: {windows_path}")
            
            # Load HVSR result
            hvsr_result = None
            if state.hvsr_result_file:
                result_path = session_folder / state.hvsr_result_file
                if result_path.exists():
                    with open(result_path, 'rb') as f:
                        hvsr_result = pickle.load(f)
                    logger.info(f"Loaded HVSR result from: {result_path}")
            
            # Load seismic data
            seismic_data = None
            if state.seismic_data_file:
                data_path = session_folder / state.seismic_data_file
                if data_path.exists():
                    with open(data_path, 'rb') as f:
                        seismic_data = pickle.load(f)
                    logger.info(f"Loaded seismic data from: {data_path}")
            
            # Load azimuthal result
            azimuthal_result = None
            if state.azimuthal_result_file:
                azimuthal_path = session_folder / state.azimuthal_result_file
                if azimuthal_path.exists():
                    with open(azimuthal_path, 'rb') as f:
                        azimuthal_result = pickle.load(f)
                    logger.info(f"Loaded azimuthal result from: {azimuthal_path}")
            
            logger.info(f"Full session loaded from: {session_folder}")
            return state, windows, hvsr_result, seismic_data, azimuthal_result
            
        except Exception as e:
            logger.error(f"Failed to load full session: {e}")
            return None, None, None, None, None
    
    def save_session(self, filepath: str, state: SessionState) -> bool:
        """
        Save session state to file (settings only, for backward compatibility).
        
        Args:
            filepath: Path to save session file
            state: SessionState to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            filepath = Path(filepath)
            
            # Ensure correct extension
            if filepath.suffix.lower() not in ['.hvsr_session', '.json']:
                filepath = filepath.with_suffix(self.FILE_EXTENSION)
            
            # Convert to dict and save
            data = state.to_dict()
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Session saved to: {filepath}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            return False
    
    def load_session(self, filepath: str) -> Optional[SessionState]:
        """
        Load session state from file (settings only, for backward compatibility).
        
        Args:
            filepath: Path to session file
            
        Returns:
            SessionState if successful, None otherwise
        """
        try:
            filepath = Path(filepath)
            
            if not filepath.exists():
                logger.error(f"Session file not found: {filepath}")
                return None
            
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            state = SessionState.from_dict(data)
            logger.info(f"Session loaded from: {filepath}")
            return state
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid session file format: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
            return None
    
    def list_sessions(self) -> List[Dict[str, Any]]:
        """
        List all available sessions in the work directory.
        
        Returns:
            List of session info dictionaries with 'path', 'created', 'has_full_data'
        """
        sessions = []
        sessions_dir = self.get_sessions_directory()
        
        for session_folder in sessions_dir.iterdir():
            if session_folder.is_dir():
                settings_path = session_folder / self.SETTINGS_FILE
                if settings_path.exists():
                    try:
                        with open(settings_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        sessions.append({
                            'path': str(session_folder),
                            'name': session_folder.name,
                            'created': data.get('created', ''),
                            'has_full_data': data.get('has_full_data', False),
                            'has_results': data.get('has_results', False),
                            'n_windows': data.get('n_total_windows', 0),
                            'peak_frequency': data.get('peak_frequency')
                        })
                    except Exception:
                        pass
        
        # Sort by creation date (newest first)
        sessions.sort(key=lambda x: x.get('created', ''), reverse=True)
        return sessions
    
    def delete_session(self, session_path: str) -> bool:
        """
        Delete a session folder and all its contents.
        
        Args:
            session_path: Path to session folder
            
        Returns:
            True if successful, False otherwise
        """
        try:
            session_folder = Path(session_path)
            if session_folder.exists() and session_folder.is_dir():
                shutil.rmtree(session_folder)
                logger.info(f"Deleted session: {session_folder}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete session: {e}")
            return False
    
    def get_default_filename(self) -> str:
        """Generate default session filename with timestamp."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"hvsr_session_{timestamp}{self.FILE_EXTENSION}"


# Convenience functions
def save_session(filepath: str, state: SessionState) -> bool:
    """Save session to file (settings only)."""
    manager = SessionManager()
    return manager.save_session(filepath, state)


def load_session(filepath: str) -> Optional[SessionState]:
    """Load session from file (settings only)."""
    manager = SessionManager()
    return manager.load_session(filepath)
