"""
Data Controller
===============

Handles data loading and file operations for the main window.
"""

from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, timedelta

try:
    from PyQt5.QtWidgets import QWidget, QMessageBox, QProgressDialog
    from PyQt5.QtCore import Qt
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


if HAS_PYQT5:
    class DataController:
        """
        Controller for data loading and management.
        
        Handles:
        - File loading (MiniSEED, ASCII)
        - Time range application
        - Data merging
        - Preview updates
        """
        
        def __init__(self, parent: QWidget):
            """
            Initialize data controller.
            
            Args:
                parent: Parent widget (main window)
            """
            self.parent = parent
            self.current_data = None
            self.current_files: List[str] = []
            self.time_range: Optional[Dict] = None
        
        def load_single_file(
            self, 
            file_path: str,
            column_mapping: Optional[Dict] = None,
            time_range: Optional[Dict] = None,
            progress_callback: Optional[Callable] = None
        ):
            """
            Load a single data file.
            
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
            Load and merge multiple files.
            
            Args:
                file_paths: List of file paths
                channel_mapping: Per-file channel mapping
                time_range: Time range to extract
                merge_method: How to merge files
                progress_callback: Progress callback function
            """
            from hvsr_pro.loaders import MiniSeedLoader
            
            if not file_paths:
                return None
            
            loader = MiniSeedLoader()
            
            try:
                # Load with channel mapping
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
            Load grouped E/N/Z files.
            
            Args:
                groups: Dict of {base_name: {'E': path, 'N': path, 'Z': path}}
                time_range: Time range to extract
                progress_callback: Progress callback function
            """
            from hvsr_pro.loaders import MiniSeedLoader
            
            if not groups:
                return None
            
            loader = MiniSeedLoader()
            
            try:
                # Collect all files
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
                # Apply timezone offset
                utc_offset = timedelta(hours=tz_offset)
                start_utc = start_dt - utc_offset
                end_utc = end_dt - utc_offset
                
                # Trim data
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
    class DataController:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass
