"""
Data Load Tab for HVSR Pro
===========================

Main tab widget for loading seismic data and previewing before processing.

Features:
- Loaded files list (left column)
- Preview canvas (center/right)
- File loading controls
- Preview mode selection
"""

from pathlib import Path
from typing import Optional

try:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
        QGroupBox, QPushButton, QLabel, QComboBox,
        QLineEdit, QFileDialog
    )
    from PyQt5.QtCore import Qt, pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


if HAS_PYQT5:
    from hvsr_pro.gui.widgets import LoadedDataTree
    from hvsr_pro.gui.canvas import PreviewCanvas

    class DataLoadTab(QWidget):
        """
        Data Load Tab - handles file loading and preview.

        Layout:
        - Left: Loaded files list (30%)
        - Right: Preview canvas (70%)
        - Top: File loading controls
        """

        # Signals
        load_file_requested = pyqtSignal()
        file_selected = pyqtSignal(str)  # file_path
        preview_mode_changed = pyqtSignal(str)  # mode
        data_cleared = pyqtSignal()  # Emitted when all files are cleared

        def __init__(self, parent=None):
            super().__init__(parent)

            # Storage for loaded data objects
            self.data_cache = {}  # file_path -> {'data': SeismicData, 'time_range': dict}
            self.data_groups = {}  # group_id -> {'name': str, 'files': {file_path: metadata}}

            # Current group ID for auto-grouping
            self.current_group_id = None
            self.group_counter = 0

            # Visibility flags
            self.show_loaded_list = True

            # Create UI
            self.init_ui()

        def init_ui(self):
            """Initialize user interface."""
            layout = QVBoxLayout(self)

            # === TOP: Work Directory ===
            work_dir_group = QGroupBox("Work Directory")
            work_dir_layout = QHBoxLayout()
            
            self.work_dir_edit = QLineEdit()
            self.work_dir_edit.setPlaceholderText("Set working directory for temp files and default browse location...")
            self.work_dir_edit.setToolTip(
                "Working directory for:\n"
                "- Temporary files\n"
                "- Default browse location for open/save dialogs\n"
                "- Session save location"
            )
            work_dir_layout.addWidget(self.work_dir_edit)
            
            self.browse_work_dir_btn = QPushButton("Browse...")
            self.browse_work_dir_btn.clicked.connect(self.on_browse_work_directory)
            self.browse_work_dir_btn.setMaximumWidth(80)
            work_dir_layout.addWidget(self.browse_work_dir_btn)
            
            work_dir_group.setLayout(work_dir_layout)
            layout.addWidget(work_dir_group)

            # === File Loading Controls ===
            controls_group = QGroupBox("Data Import")
            controls_layout = QVBoxLayout()

            # Load button
            self.load_btn = QPushButton("Load Data File")
            self.load_btn.clicked.connect(self.on_load_file)
            self.load_btn.setShortcut("Ctrl+O")
            self.load_btn.setToolTip("Load seismic data file (Ctrl+O)\nSupported formats: .txt, .csv, .mseed")
            self.load_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border-radius: 4px;
                    padding: 8px;
                    font-weight: bold;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
            controls_layout.addWidget(self.load_btn)

            # Export button
            self.export_btn = QPushButton("Export Reduced Data")
            self.export_btn.clicked.connect(self.on_export_data)
            self.export_btn.setShortcut("Ctrl+E")
            self.export_btn.setToolTip("Export selected files with optional time reduction (Ctrl+E)\nSupports .mat, .mseed, and .csv formats")
            self.export_btn.setEnabled(False)  # Disabled until files are loaded
            self.export_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border-radius: 4px;
                    padding: 8px;
                    font-weight: bold;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
                QPushButton:disabled {
                    background-color: #cccccc;
                }
            """)
            controls_layout.addWidget(self.export_btn)

            controls_group.setLayout(controls_layout)
            layout.addWidget(controls_group)

            # === MAIN: Splitter with Tree and Preview ===
            self.splitter = QSplitter(Qt.Horizontal)

            # Left: Loaded Files Tree
            self.loaded_tree = LoadedDataTree(self)
            self.loaded_tree.file_selected.connect(self.on_file_selected_from_tree)
            self.loaded_tree.group_selected.connect(self.on_group_selected_from_tree)
            self.loaded_tree.load_more_requested.connect(self.on_load_file)
            self.loaded_tree.file_removed.connect(self.on_file_removed)
            self.loaded_tree.group_removed.connect(self.on_group_removed)
            self.loaded_tree.files_cleared.connect(self.on_files_cleared)
            self.splitter.addWidget(self.loaded_tree)

            # Right: Preview Canvas
            self.preview_canvas = PreviewCanvas(self)
            self.preview_canvas.detached.connect(self.on_preview_detached)
            self.preview_canvas.attached.connect(self.on_preview_attached)
            self.splitter.addWidget(self.preview_canvas)

            # Set splitter proportions (30% tree, 70% preview)
            self.splitter.setStretchFactor(0, 0)  # Don't stretch tree
            self.splitter.setStretchFactor(1, 1)  # Only stretch preview

            # Set fixed width for loaded tree
            self.loaded_tree.setMinimumWidth(250)
            self.loaded_tree.setMaximumWidth(400)

            layout.addWidget(self.splitter)

            # === BOTTOM: Status Info ===
            self.status_label = QLabel("No data loaded. Click 'Load Data File' to begin.")
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: #f0f0f0;
                    padding: 8px;
                    border-radius: 4px;
                    color: #666;
                }
            """)
            layout.addWidget(self.status_label)

        def on_load_file(self):
            """Handle load file button click."""
            self.load_file_requested.emit()

        def on_browse_work_directory(self):
            """Handle browse work directory button click."""
            current_dir = self.work_dir_edit.text() or str(Path.home())
            
            directory = QFileDialog.getExistingDirectory(
                self,
                "Select Work Directory",
                current_dir,
                QFileDialog.ShowDirsOnly
            )
            
            if directory:
                self.set_work_directory(directory)
        
        def set_work_directory(self, directory: str):
            """Set the work directory.
            
            Args:
                directory: Path to work directory
            """
            self.work_dir_edit.setText(directory)
            
            # Notify parent window
            parent = self.parent()
            while parent:
                if hasattr(parent, '_work_directory'):
                    parent._work_directory = directory
                    break
                parent = parent.parent() if hasattr(parent, 'parent') else None
        
        def get_work_directory(self) -> str:
            """Get the current work directory."""
            return self.work_dir_edit.text()

        def on_export_data(self):
            """Handle export data button click."""
            from hvsr_pro.gui.dialogs import DataExportDialog

            # Get selected item info
            selected_info = self.loaded_tree.get_selected_item_info()

            if not selected_info:
                # No selection - export all files
                if not self.data_cache:
                    from PyQt5.QtWidgets import QMessageBox
                    QMessageBox.warning(
                        self,
                        "No Data",
                        "No data files loaded. Please load data files first."
                    )
                    return

                files_to_export = self.data_cache.copy()
            elif selected_info['type'] == 'file':
                # Single file selected
                file_path = selected_info['path']
                files_to_export = {file_path: self.data_cache[file_path]}
            else:
                # Group selected - export all files in group
                file_paths = selected_info['files']
                files_to_export = {fp: self.data_cache[fp] for fp in file_paths if fp in self.data_cache}

            if not files_to_export:
                from PyQt5.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self,
                    "No Data",
                    "No data available for export."
                )
                return

            # Get time range from preview canvas if time filtering is enabled
            time_range = None
            if hasattr(self.preview_canvas, 'time_filter_enabled') and self.preview_canvas.time_filter_enabled:
                time_range = {
                    'start': self.preview_canvas.time_start,
                    'end': self.preview_canvas.time_end
                }

            # Prepare files data (extract SeismicData objects)
            files_data = {}
            for file_path, cached_data in files_to_export.items():
                files_data[file_path] = cached_data['data']

            # Open export dialog
            from PyQt5.QtWidgets import QDialog
            dialog = DataExportDialog(files_data, time_range, self)
            result = dialog.exec_()

            # Check if user wants to reload the exported data
            if result == QDialog.Accepted and dialog.should_reload_exported:
                self.reload_exported_data(dialog.exported_files_info)

        def reload_exported_data(self, export_info: dict):
            """
            Reload exported (time-reduced) data back into preview and add to data tree.

            Args:
                export_info: Dict with 'output_dir', 'format', 'file_count'
            """
            from PyQt5.QtWidgets import QMessageBox, QProgressDialog
            from PyQt5.QtCore import Qt
            from pathlib import Path
            from datetime import datetime

            try:
                output_dir = Path(export_info['output_dir'])
                file_format = export_info['format']

                # Find exported files
                if file_format == 'mat':
                    exported_files = list(output_dir.glob('*.mat'))
                elif file_format == 'mseed':
                    exported_files = list(output_dir.glob('*.mseed'))
                elif file_format == 'csv':
                    exported_files = list(output_dir.glob('*.csv'))
                else:
                    QMessageBox.warning(
                        self,
                        "Unsupported Format",
                        f"Cannot reload .{file_format} files automatically."
                    )
                    return

                if not exported_files:
                    QMessageBox.warning(
                        self,
                        "No Files Found",
                        f"No exported {file_format} files found in:\n{output_dir}"
                    )
                    return

                # Create progress dialog
                progress = QProgressDialog(
                    "Loading exported files...",
                    "Cancel",
                    0,
                    len(exported_files),
                    self
                )
                progress.setWindowModality(Qt.WindowModal)
                progress.setWindowTitle("Reloading Exported Data")
                progress.show()

                # Start a new group for the reloaded data
                reload_group_name = f"Exported (Reduced) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                self.start_new_group(reload_group_name)

                # Load each file
                loaded_count = 0
                failed_files = []

                for i, exported_file in enumerate(exported_files):
                    if progress.wasCanceled():
                        break

                    progress.setValue(i)
                    progress.setLabelText(f"Loading {exported_file.name}...")

                    try:
                        # Load the file using appropriate loader
                        if file_format == 'mat':
                            seismic_data = self._load_mat_file(str(exported_file))
                        elif file_format == 'mseed':
                            seismic_data = self._load_miniseed_file(str(exported_file))
                        elif file_format == 'csv':
                            seismic_data = self._load_csv_file(str(exported_file))
                        else:
                            continue

                        if seismic_data:
                            # Add to data cache
                            file_path_str = str(exported_file)
                            self.data_cache[file_path_str] = {
                                'data': seismic_data,
                                'time_range': None  # Already reduced
                            }

                            # Get metadata
                            metadata = {
                                'duration': seismic_data.duration if hasattr(seismic_data, 'duration') else 0,
                                'sampling_rate': seismic_data.sampling_rate if hasattr(seismic_data, 'sampling_rate') else 0,
                                'size_mb': exported_file.stat().st_size / (1024 * 1024),
                                'status': 'loaded'
                            }

                            # Add to current group in data tree
                            if self.current_group_id and self.current_group_id in self.data_groups:
                                self.data_groups[self.current_group_id]['files'][file_path_str] = metadata

                            # Update the tree display
                            self.loaded_tree.update_file_in_current_group(file_path_str, metadata)

                            loaded_count += 1
                        else:
                            failed_files.append(exported_file.name)

                    except Exception as e:
                        print(f"Failed to load {exported_file.name}: {str(e)}")
                        failed_files.append(exported_file.name)

                progress.setValue(len(exported_files))
                progress.close()

                # Update status
                self.update_status(f"Reloaded {loaded_count} of {len(exported_files)} exported file(s)")

                # Enable export button if files were loaded
                if loaded_count > 0:
                    self.export_btn.setEnabled(True)

                    # Select the group in tree to preview
                    self.loaded_tree.select_current_group()

                # Show result message
                result_msg = f"Successfully loaded {loaded_count} of {len(exported_files)} exported file(s)"
                if failed_files:
                    result_msg += f"\n\nFailed to load {len(failed_files)} file(s):\n" + "\n".join(failed_files[:5])
                    if len(failed_files) > 5:
                        result_msg += f"\n... and {len(failed_files) - 5} more"

                QMessageBox.information(
                    self,
                    "Data Reloaded",
                    result_msg
                )

            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Reload Failed",
                    f"Failed to reload exported data:\n\n{str(e)}"
                )

        def _load_mat_file(self, file_path: str):
            """Load .mat file and return SeismicData object."""
            try:
                from scipy.io import loadmat
                from hvsr_pro.core.data_structures import SeismicData, ComponentData

                mat_data = loadmat(file_path)

                # Extract components
                e_data = mat_data['E'].flatten()
                n_data = mat_data['N'].flatten()
                z_data = mat_data['Z'].flatten()
                fs = float(mat_data['Fs'][0][0])

                # Get start time if available
                from datetime import datetime
                if 'starttime_iso' in mat_data:
                    start_time = datetime.fromisoformat(str(mat_data['starttime_iso'][0]))
                else:
                    start_time = datetime.now()

                # Create ComponentData objects
                east = ComponentData(name='E', data=e_data, sampling_rate=fs, start_time=start_time)
                north = ComponentData(name='N', data=n_data, sampling_rate=fs, start_time=start_time)
                vertical = ComponentData(name='Z', data=z_data, sampling_rate=fs, start_time=start_time)

                return SeismicData(east=east, north=north, vertical=vertical, source_file=file_path)

            except Exception as e:
                print(f"Error loading .mat file: {str(e)}")
                return None

        def _load_miniseed_file(self, file_path: str):
            """Load MiniSEED file and return SeismicData object."""
            try:
                from hvsr_pro.loaders.miniseed_loader import MiniseedLoader
                loader = MiniseedLoader()
                return loader.load(file_path)
            except Exception as e:
                print(f"Error loading .mseed file: {str(e)}")
                return None

        def _load_csv_file(self, file_path: str):
            """Load CSV file and return SeismicData object."""
            try:
                import numpy as np
                from hvsr_pro.core.data_structures import SeismicData, ComponentData
                from datetime import datetime

                # Read CSV
                data = np.loadtxt(file_path, delimiter=',', skiprows=5)  # Skip metadata rows

                # Assume columns: time, E, N, Z
                time_vec = data[:, 0]
                e_data = data[:, 1]
                n_data = data[:, 2]
                z_data = data[:, 3]

                # Calculate sampling rate
                fs = 1.0 / np.mean(np.diff(time_vec)) if len(time_vec) > 1 else 100.0

                # Create ComponentData objects
                east = ComponentData(name='E', data=e_data, sampling_rate=fs, start_time=datetime.now())
                north = ComponentData(name='N', data=n_data, sampling_rate=fs, start_time=datetime.now())
                vertical = ComponentData(name='Z', data=z_data, sampling_rate=fs, start_time=datetime.now())

                return SeismicData(east=east, north=north, vertical=vertical, source_file=file_path)

            except Exception as e:
                print(f"Error loading .csv file: {str(e)}")
                return None

        def on_file_selected_from_tree(self, file_path: str):
            """
            Handle single file selection from tree.

            Args:
                file_path: Path to the selected file
            """
            # Emit signal to main window
            self.file_selected.emit(file_path)

            # Update preview if data is cached
            if file_path in self.data_cache:
                cached = self.data_cache[file_path]
                data = cached['data']
                time_range = cached.get('time_range')
                self.preview_canvas.set_data(data, time_range)
                self.update_status(f"Previewing: {Path(file_path).name}")
            else:
                self.update_status(f"Selected: {Path(file_path).name} (loading...)")

        def on_group_selected_from_tree(self, group_id: str, file_paths: list):
            """
            Handle group selection from tree - preview all files in group.

            Args:
                group_id: Group identifier
                file_paths: List of file paths in the group
            """
            if not file_paths:
                return

            # Get group info
            group_info = self.data_groups.get(group_id)
            group_name = group_info['name'] if group_info else group_id

            # Collect SeismicData objects for all files in group
            data_objects = []
            for file_path in file_paths:
                if file_path in self.data_cache:
                    data_objects.append(self.data_cache[file_path]['data'])

            if not data_objects:
                self.update_status(f"No data available for group '{group_name}'")
                return

            # Preview multiple files
            self.preview_canvas.set_data_from_files(data_objects)
            self.update_status(f"Previewing group '{group_name}' ({len(data_objects)} files)")

        def on_file_removed(self, file_path: str):
            """
            Handle file removal.

            Args:
                file_path: Path to the removed file
            """
            # Remove from cache
            if file_path in self.data_cache:
                del self.data_cache[file_path]

            # Remove from groups
            for group_id, group in list(self.data_groups.items()):
                if file_path in group['files']:
                    del group['files'][file_path]
                    # If group is empty, remove it
                    if not group['files']:
                        del self.data_groups[group_id]

            # Clear preview if this was the selected file
            self.preview_canvas.clear_preview()
            self.update_status("File removed")

        def on_group_removed(self, group_id: str):
            """
            Handle group removal.

            Args:
                group_id: Group identifier
            """
            # Remove all files in group from cache
            if group_id in self.data_groups:
                group = self.data_groups[group_id]
                for file_path in list(group['files'].keys()):
                    if file_path in self.data_cache:
                        del self.data_cache[file_path]

                # Remove group
                del self.data_groups[group_id]

            # Clear preview
            self.preview_canvas.clear_preview()
            self.update_status("Group removed")

        def on_files_cleared(self):
            """Handle all files cleared."""
            self.data_cache.clear()
            self.data_groups.clear()
            self.current_group_id = None
            self.preview_canvas.clear_preview()
            self.update_status("All files cleared")

            # Disable export button
            self.export_btn.setEnabled(False)
            
            # Emit signal to notify main window and other tabs
            self.data_cleared.emit()

        def add_loaded_file(self, file_path: str, data, metadata: dict, time_range=None, group_name=None):
            """
            Add a loaded file to the tree and cache.

            Args:
                file_path: Path to the file
                data: SeismicData object
                metadata: Dict with 'duration', 'sampling_rate', 'size_mb', 'status'
                time_range: Optional dict with 'start' and 'end' times in seconds
                group_name: Optional custom group name (auto-generated if None)
            """
            from datetime import datetime

            # Add to cache
            self.data_cache[file_path] = {'data': data, 'time_range': time_range}

            # Create new group if needed (or if current group no longer exists)
            need_new_group = (
                self.current_group_id is None or 
                self.current_group_id not in self.data_groups
            )
            
            if need_new_group:
                self.group_counter += 1
                self.current_group_id = f"group_{self.group_counter}"

                # Auto-generate group name if not provided
                if group_name is None:
                    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                    group_name = f"Session {timestamp}"

                # Create group in data_groups dict
                self.data_groups[self.current_group_id] = {
                    'name': group_name,
                    'files': {}
                }

            # Safety check: ensure group exists before accessing
            if self.current_group_id not in self.data_groups:
                # This should never happen, but create group as fallback
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                self.data_groups[self.current_group_id] = {
                    'name': group_name if group_name else f"Session {timestamp}",
                    'files': {}
                }

            # Add file to current group
            group = self.data_groups[self.current_group_id]
            group['files'][file_path] = metadata

            # Update tree view
            self.loaded_tree.add_file_group(
                self.current_group_id,
                group['name'],
                group['files']
            )

            # Update status
            count = len(self.data_cache)
            self.update_status(f"{count} file(s) loaded")

            # Enable export button
            self.export_btn.setEnabled(True)
            
            # Automatically preview the newly loaded data
            try:
                self.preview_canvas.set_data(data, time_range)
                self.update_status(f"Previewing: {Path(file_path).name} ({count} file(s) loaded)")
            except Exception as e:
                print(f"Preview error: {e}")
            
            # Select the file in the tree
            try:
                self.loaded_tree.select_file(file_path)
            except Exception as e:
                print(f"Tree selection error: {e}")

        def get_loaded_data(self, file_path: str):
            """
            Get loaded data for a file.

            Args:
                file_path: Path to the file

            Returns:
                SeismicData object or None
            """
            return self.data_cache.get(file_path)

        def get_current_data(self):
            """
            Get currently selected/previewed data.

            Returns:
                SeismicData object or None (single file) or list (group selection)
            """
            selected_info = self.loaded_tree.get_selected_item_info()
            if selected_info:
                if selected_info['type'] == 'file':
                    return self.data_cache.get(selected_info['path'])
                elif selected_info['type'] == 'group':
                    # Return list of data objects for group
                    data_objects = []
                    for file_path in selected_info['files']:
                        if file_path in self.data_cache:
                            data_objects.append(self.data_cache[file_path]['data'])
                    return data_objects if data_objects else None
            return None

        def start_new_group(self, group_name=None):
            """
            Start a new group for subsequent file loads.

            Args:
                group_name: Optional custom group name
            """
            self.current_group_id = None

        def get_all_loaded_files(self):
            """
            Get list of all loaded file paths.

            Returns:
                List of file paths
            """
            return list(self.data_cache.keys())

        def update_status(self, message: str):
            """
            Update status label.

            Args:
                message: Status message to display
            """
            self.status_label.setText(message)

        def toggle_loaded_list_visibility(self):
            """Toggle visibility of loaded files tree."""
            self.show_loaded_list = not self.show_loaded_list
            self.loaded_tree.setVisible(self.show_loaded_list)

        def set_loaded_list_visible(self, visible: bool):
            """
            Set visibility of loaded files tree.

            Args:
                visible: True to show, False to hide
            """
            self.show_loaded_list = visible
            self.loaded_tree.setVisible(visible)

        def on_preview_detached(self):
            """Handle preview canvas detached."""
            self.update_status("Preview canvas detached")

        def on_preview_attached(self):
            """Handle preview canvas re-attached."""
            # Re-add to splitter
            self.splitter.addWidget(self.preview_canvas)
            self.preview_canvas.show()
            self.update_status("Preview canvas attached")


else:
    # Dummy class when PyQt5 not available
    class DataLoadTab:
        def __init__(self, *args, **kwargs):
            raise ImportError("PyQt5 is required for GUI functionality")
