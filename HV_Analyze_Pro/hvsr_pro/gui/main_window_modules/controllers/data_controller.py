"""
Data Controller
===============

Handles data loading and file operations for the main window.
"""

from pathlib import Path
from typing import Optional, Dict, Any, List, Callable, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field

try:
    from PyQt5.QtWidgets import QWidget, QMessageBox, QProgressDialog
    from PyQt5.QtCore import Qt, QObject, pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


@dataclass
class LoadResult:
    """Result from a data loading operation."""
    success: bool
    data: Any = None
    mode: str = 'single'
    files: List[str] = field(default_factory=list)
    groups: Dict = field(default_factory=dict)
    time_range: Optional[Dict] = None
    metadata_list: List[Dict] = field(default_factory=list)
    error_message: str = ''
    
    @property
    def time_range_seconds(self) -> Optional[Dict]:
        """Convert time range to seconds format."""
        if not self.time_range or not self.time_range.get('enabled'):
            return None
        start_dt = self.time_range.get('start')
        end_dt = self.time_range.get('end')
        if start_dt and end_dt:
            duration_seconds = (end_dt - start_dt).total_seconds()
            return {'start': 0.0, 'end': duration_seconds}
        return None


if HAS_PYQT5:
    class DataController(QObject):
        """
        Controller for data loading and management.
        
        Handles:
        - File loading (MiniSEED, ASCII)
        - Time range application
        - Data merging
        - Preview updates
        
        Signals:
            loading_started: Emitted when loading begins
            loading_finished: Emitted with LoadResult when complete
            loading_error: Emitted with error message on failure
            info_message: Emitted with info messages during loading
        """
        
        loading_started = pyqtSignal()
        loading_finished = pyqtSignal(object)  # LoadResult
        loading_error = pyqtSignal(str)
        info_message = pyqtSignal(str)
        
        def __init__(self, parent: QWidget):
            """
            Initialize data controller.
            
            Args:
                parent: Parent widget (main window)
            """
            super().__init__(parent)
            self.parent = parent
            self.current_data = None
            self.current_files: List[str] = []
            self.time_range: Optional[Dict] = None
            self.load_mode: str = 'single'
        
        def load_from_dialog_result(self, result: dict) -> LoadResult:
            """
            Load data from DataInputDialog result.
            
            This is the main entry point for loading data.
            
            Args:
                result: Dictionary from DataInputDialog containing:
                    - mode: 'single', 'multi_type1', or 'multi_type2'
                    - files: List of file paths
                    - groups: Dict of file groups (for multi_type2)
                    - options: Loading options (channel_mapping, etc.)
                    - time_range: Optional time range dict
            
            Returns:
                LoadResult with success status and loaded data
            """
            from hvsr_pro.core import HVSRDataHandler
            
            mode = result.get('mode', 'single')
            files = result.get('files', [])
            groups = result.get('groups', {})
            options = result.get('options', {})
            time_range = result.get('time_range')
            
            self.loading_started.emit()
            
            # Log time range if enabled
            if time_range and time_range.get('enabled'):
                start = time_range['start']
                end = time_range['end']
                tz_name = time_range.get('timezone_name', 'UTC')
                self.info_message.emit(
                    f"Time range selected: {start.strftime('%Y-%m-%d %H:%M')} to {end.strftime('%H:%M')} ({tz_name})"
                )
            
            try:
                handler = HVSRDataHandler()
                
                if mode == 'single':
                    return self._load_single(handler, files, time_range)
                elif mode == 'multi_type1':
                    return self._load_multi_type1(handler, files, options, time_range)
                elif mode == 'multi_type2':
                    return self._load_multi_type2(handler, groups, time_range)
                elif mode == 'multi_component':
                    component_files = result.get('component_files', {})
                    # Include format in options (it's stored at top level in result)
                    options['format'] = result.get('format', 'auto')
                    return self._load_multi_component(handler, component_files, options, time_range)
                else:
                    return LoadResult(
                        success=False,
                        error_message=f"Unknown load mode: {mode}"
                    )
                    
            except Exception as e:
                import traceback
                error_msg = f"Failed to load data: {str(e)}"
                self.loading_error.emit(error_msg)
                return LoadResult(
                    success=False,
                    error_message=f"{error_msg}\n{traceback.format_exc()}"
                )
        
        def _load_single(self, handler, files: List[str], time_range: Optional[Dict]) -> LoadResult:
            """Load single file mode."""
            if not files:
                return LoadResult(success=False, error_message="No files provided")
            
            file_path = files[0]
            self.info_message.emit(f"Loading: {Path(file_path).name}...")
            
            data = handler.load_data(file_path)
            
            # Get file metadata
            file_size = Path(file_path).stat().st_size / (1024 * 1024)  # MB
            metadata = {
                'duration': data.duration,
                'sampling_rate': data.east.sampling_rate,
                'size_mb': file_size,
                'status': 'loaded',
                'file_path': file_path,
                'display_name': file_path
            }
            
            # Store state
            self.current_data = data
            self.current_files = [file_path]
            self.time_range = time_range
            self.load_mode = 'single'
            
            self.info_message.emit(f"Loaded: {Path(file_path).name}")
            
            result = LoadResult(
                success=True,
                data=data,
                mode='single',
                files=[file_path],
                time_range=time_range,
                metadata_list=[metadata]
            )
            
            self.loading_finished.emit(result)
            return result
        
        def _load_multi_type1(
            self, 
            handler, 
            files: List[str], 
            options: Dict,
            time_range: Optional[Dict]
        ) -> LoadResult:
            """Load multiple files with E,N,Z in each."""
            if not files:
                return LoadResult(success=False, error_message="No files provided")
            
            self.info_message.emit(f"Loading {len(files)} MiniSEED files...")
            
            # Extract channel mapping from options if provided
            channel_mapping = options.get('channel_mapping', None)
            if channel_mapping:
                self.info_message.emit(f"Using channel mapping: {channel_mapping}")
                data = handler.load_multi_miniseed_type1(files, channel_mapping=channel_mapping)
            else:
                data = handler.load_multi_miniseed_type1(files)
            
            # Build metadata for each file
            metadata_list = []
            for file_path in files:
                file_size = Path(file_path).stat().st_size / (1024 * 1024)
                file_duration = data.duration / len(files)  # Approximate
                metadata = {
                    'duration': file_duration,
                    'sampling_rate': data.east.sampling_rate,
                    'size_mb': file_size,
                    'status': 'loaded',
                    'file_path': file_path,
                    'display_name': file_path
                }
                metadata_list.append(metadata)
            
            # Store state
            self.current_data = data
            self.current_files = files
            self.time_range = time_range
            self.load_mode = 'multi_type1'
            
            self.info_message.emit(f"Loaded {len(files)} files (merged chronologically)")
            
            result = LoadResult(
                success=True,
                data=data,
                mode='multi_type1',
                files=files,
                time_range=time_range,
                metadata_list=metadata_list
            )
            
            self.loading_finished.emit(result)
            return result
        
        def _load_multi_type2(
            self,
            handler,
            groups: Dict,
            time_range: Optional[Dict]
        ) -> LoadResult:
            """Load separate E, N, Z files."""
            if not groups:
                return LoadResult(success=False, error_message="No file groups provided")
            
            complete = sum(1 for g in groups.values() if 'E' in g and 'N' in g and 'Z' in g)
            self.info_message.emit(f"Loading {complete} file groups...")
            
            data = handler.load_multi_miniseed_type2(groups)
            
            # Build metadata for each group
            metadata_list = []
            all_files = []
            file_duration_per_group = data.duration / complete if complete > 0 else data.duration
            
            for group_name, group_files in groups.items():
                if all(c in group_files for c in ['E', 'N', 'Z']):
                    # Calculate size for this group
                    group_size = sum(
                        Path(str(f)).stat().st_size for f in group_files.values()
                    ) / (1024 * 1024)
                    
                    display_name = f"{group_name} (E/N/Z)"
                    metadata = {
                        'duration': file_duration_per_group,
                        'sampling_rate': data.east.sampling_rate,
                        'size_mb': group_size,
                        'status': 'loaded',
                        'file_path': display_name,
                        'display_name': display_name,
                        'group_name': group_name
                    }
                    metadata_list.append(metadata)
                    
                    # Collect all files
                    for comp_path in group_files.values():
                        all_files.append(str(comp_path))
            
            # Store state
            self.current_data = data
            self.current_files = all_files
            self.time_range = time_range
            self.load_mode = 'multi_type2'
            
            self.info_message.emit(f"Loaded {complete} groups (3-component streams)")
            
            result = LoadResult(
                success=True,
                data=data,
                mode='multi_type2',
                files=all_files,
                groups=groups,
                time_range=time_range,
                metadata_list=metadata_list
            )
            
            self.loading_finished.emit(result)
            return result
        
        def _load_multi_component(
            self,
            handler,
            component_files: Dict[str, str],
            options: Dict,
            time_range: Optional[Dict]
        ) -> LoadResult:
            """
            Load multi-component files (SAC, PEER formats).
            
            These formats store each component in a separate file.
            
            Args:
                handler: HVSRDataHandler instance
                component_files: Dict mapping component (N, E, Z) to file path
                options: Loading options (format, degrees_from_north, etc.)
                time_range: Optional time range
                
            Returns:
                LoadResult with loaded data
            """
            if not component_files:
                return LoadResult(success=False, error_message="No component files provided")
            
            # Extract file paths in correct order
            files = []
            for comp in ['N', 'E', 'Z']:
                if comp in component_files:
                    files.append(str(component_files[comp]))
            
            if len(files) != 3:
                return LoadResult(
                    success=False,
                    error_message=f"Expected 3 component files, got {len(files)}"
                )
            
            # Get format and orientation from options
            file_format = options.get('format', 'auto')
            degrees_from_north = options.get('degrees_from_north')
            
            self.info_message.emit(f"Loading 3 component files ({file_format} format)...")
            
            # Load using multi-component method
            data = handler.load_multi_component(
                files,
                format=file_format,
                degrees_from_north=degrees_from_north
            )
            
            # Calculate total size
            total_size = sum(Path(f).stat().st_size for f in files) / (1024 * 1024)
            
            # Build metadata
            metadata = {
                'duration': data.duration,
                'sampling_rate': data.east.sampling_rate,
                'size_mb': total_size,
                'status': 'loaded',
                'file_path': f"{Path(files[0]).stem} (N/E/Z)",
                'display_name': f"{Path(files[0]).stem} (N/E/Z)",
                'format': file_format
            }
            
            # Store state
            self.current_data = data
            self.current_files = files
            self.time_range = time_range
            self.load_mode = 'multi_component'
            
            self.info_message.emit(f"Loaded 3 component files successfully")
            
            result = LoadResult(
                success=True,
                data=data,
                mode='multi_component',
                files=files,
                time_range=time_range,
                metadata_list=[metadata]
            )
            
            self.loading_finished.emit(result)
            return result
        
        def load_single_file(
            self, 
            file_path: str,
            column_mapping: Optional[Dict] = None,
            time_range: Optional[Dict] = None,
            progress_callback: Optional[Callable] = None
        ):
            """
            Load a single data file (legacy method).
            
            Args:
                file_path: Path to file
                column_mapping: Column mapping for CSV files
                time_range: Time range to extract
                progress_callback: Progress callback function
            """
            from hvsr_pro.loaders import MiniSeedLoader, TxtDataLoader
            
            path = Path(file_path)
            
            if path.suffix.lower() in ['.mseed', '.miniseed']:
                loader = MiniSeedLoader()
            else:
                loader = TxtDataLoader(column_mapping=column_mapping)
            
            try:
                data = loader.load(file_path)
                
                if time_range and time_range.get('enabled'):
                    data = self._apply_time_range(data, time_range)
                
                self.current_data = data
                self.current_files = [file_path]
                self.time_range = time_range
                
                return data
                
            except Exception as e:
                QMessageBox.critical(
                    self.parent, "Error",
                    f"Failed to load file:\n{str(e)}"
                )
                return None
        
        def load_multiple_files(
            self,
            file_paths: List[str],
            channel_mapping: Optional[Dict[str, Dict]] = None,
            time_range: Optional[Dict] = None,
            merge_method: str = 'chronological',
            progress_callback: Optional[Callable] = None
        ):
            """
            Load and merge multiple files (legacy method).
            """
            from hvsr_pro.loaders import MiniSeedLoader
            
            if not file_paths:
                return None
            
            loader = MiniSeedLoader()
            
            try:
                data = loader.load_multiple(
                    file_paths,
                    channel_mapping=channel_mapping,
                    merge=True
                )
                
                if time_range and time_range.get('enabled'):
                    data = self._apply_time_range(data, time_range)
                
                self.current_data = data
                self.current_files = file_paths
                self.time_range = time_range
                
                return data
                
            except Exception as e:
                QMessageBox.critical(
                    self.parent, "Error",
                    f"Failed to load files:\n{str(e)}"
                )
                return None
        
        def load_file_groups(
            self,
            groups: Dict[str, Dict[str, str]],
            time_range: Optional[Dict] = None,
            progress_callback: Optional[Callable] = None
        ):
            """
            Load grouped E/N/Z files (legacy method).
            """
            from hvsr_pro.loaders import MiniSeedLoader
            
            if not groups:
                return None
            
            loader = MiniSeedLoader()
            
            try:
                all_files = []
                for base_name, components in groups.items():
                    for comp, path in components.items():
                        all_files.append(str(path))
                
                data = loader.load_grouped(groups)
                
                if time_range and time_range.get('enabled'):
                    data = self._apply_time_range(data, time_range)
                
                self.current_data = data
                self.current_files = all_files
                self.time_range = time_range
                
                return data
                
            except Exception as e:
                QMessageBox.critical(
                    self.parent, "Error",
                    f"Failed to load file groups:\n{str(e)}"
                )
                return None
        
        def _apply_time_range(self, data, time_range: Dict):
            """Apply time range filter to data."""
            if not time_range or not time_range.get('enabled'):
                return data
            
            start_dt = time_range.get('start_dt') or time_range.get('start')
            end_dt = time_range.get('end_dt') or time_range.get('end')
            tz_offset = time_range.get('timezone_offset', 0)
            
            if start_dt and end_dt:
                utc_offset = timedelta(hours=tz_offset)
                start_utc = start_dt - utc_offset
                end_utc = end_dt - utc_offset
                data = data.trim(start_utc, end_utc)
            
            return data
        
        def get_data_info(self) -> Dict[str, Any]:
            """Get information about currently loaded data."""
            if self.current_data is None:
                return {'loaded': False}
            
            data = self.current_data
            
            return {
                'loaded': True,
                'files': self.current_files,
                'n_files': len(self.current_files),
                'time_range': self.time_range,
                'sampling_rate': getattr(data, 'sampling_rate', None),
                'duration': getattr(data, 'duration', None),
            }
        
        def clear(self):
            """Clear loaded data."""
            self.current_data = None
            self.current_files = []
            self.time_range = None

else:
    @dataclass
    class LoadResult:
        """Dummy class when PyQt5 not available."""
        success: bool = False
        data: Any = None
        mode: str = 'single'
        files: List[str] = field(default_factory=list)
        groups: Dict = field(default_factory=dict)
        time_range: Optional[Dict] = None
        metadata_list: List[Dict] = field(default_factory=list)
        error_message: str = ''
    
    class DataController:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass
