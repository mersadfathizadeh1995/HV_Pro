"""
Automatic Workflow Tab - combines all processing steps into one interface.
Features:
- Organized station-based MiniSEED file selection (table view)
- CSV import/export for time windows
- Output directory selection
- Time window with timezone options (CST, CDT, GMT+0)
- HVSR settings via popup dialog with peak selection options
- Parallel HVSR curve generation for multiple stations
- Option to apply same time window to all stations
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QCheckBox, QTextEdit, QFileDialog, QMessageBox, QProgressBar,
    QDialog, QListWidget, QListWidgetItem, QAbstractItemView,
    QTableWidget, QTableWidgetItem, QHeaderView, QInputDialog,
    QFormLayout
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QColor
from datetime import datetime, timedelta
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import multiprocessing
import os
import sys
import csv
import subprocess
import numpy as np


# Time Window CSV Columns
_TIME_COLS = [
    "Figure",
    "S_Year", "S_Month", "S_Day", "S_Hour", "S_Min", "S_Sec",
    "E_Year", "E_Month", "E_Day", "E_Hour", "E_Min", "E_Sec",
]


# HVSR Settings Dialog
class HVSRSettingsDialog(QDialog):
    """Popup dialog for HVSR settings including peak selection."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("HVSR Settings")
        self.setModal(True)
        self.setMinimumWidth(450)
        
        self.settings = {}
        self._build_ui()
        self._load_defaults()
    
    def _build_ui(self):
        layout = QVBoxLayout(self)
        
        # HVSR Parameters Group
        hvsr_group = QGroupBox("HVSR Parameters")
        hvsr_layout = QGridLayout(hvsr_group)
        
        hvsr_layout.addWidget(QLabel("Frequency Min (Hz):"), 0, 0)
        self.freq_min = QDoubleSpinBox()
        self.freq_min.setRange(0.01, 100)
        self.freq_min.setValue(0.2)
        self.freq_min.setDecimals(2)
        hvsr_layout.addWidget(self.freq_min, 0, 1)
        
        hvsr_layout.addWidget(QLabel("Frequency Max (Hz):"), 0, 2)
        self.freq_max = QDoubleSpinBox()
        self.freq_max.setRange(0.1, 100)
        self.freq_max.setValue(30.0)
        self.freq_max.setDecimals(2)
        hvsr_layout.addWidget(self.freq_max, 0, 3)
        
        hvsr_layout.addWidget(QLabel("Smoothing Type:"), 1, 0)
        self.smoothing_type = QComboBox()
        self.smoothing_type.addItems(["Konno-Ohmachi", "Parzen", "None"])
        hvsr_layout.addWidget(self.smoothing_type, 1, 1)
        
        hvsr_layout.addWidget(QLabel("KO Bandwidth:"), 1, 2)
        self.smoothing_bw = QSpinBox()
        self.smoothing_bw.setRange(10, 120)
        self.smoothing_bw.setValue(40)
        hvsr_layout.addWidget(self.smoothing_bw, 1, 3)
        
        hvsr_layout.addWidget(QLabel("Time Window (s):"), 2, 0)
        self.window_length = QSpinBox()
        self.window_length.setRange(10, 600)
        self.window_length.setValue(120)
        hvsr_layout.addWidget(self.window_length, 2, 1)
        
        hvsr_layout.addWidget(QLabel("Averaging:"), 2, 2)
        self.averaging = QComboBox()
        self.averaging.addItems(["geo", "quad", "energy", "N", "E"])
        hvsr_layout.addWidget(self.averaging, 2, 3)
        
        layout.addWidget(hvsr_group)
        
        # Peak Selection Group
        peak_group = QGroupBox("Peak Selection")
        peak_layout = QGridLayout(peak_group)
        
        peak_layout.addWidget(QLabel("Number of Peaks:"), 0, 0)
        self.num_peaks = QSpinBox()
        self.num_peaks.setRange(1, 10)
        self.num_peaks.setValue(2)
        peak_layout.addWidget(self.num_peaks, 0, 1)
        
        self.auto_peaks = QCheckBox("Unlimited peaks (click as many as needed)")
        self.auto_peaks.setChecked(False)
        self.auto_peaks.stateChanged.connect(self._on_auto_peaks_changed)
        peak_layout.addWidget(self.auto_peaks, 1, 0, 1, 2)
        
        peak_layout.addWidget(QLabel("Peak Label Font (pt):"), 2, 0)
        self.peak_font = QSpinBox()
        self.peak_font.setRange(6, 30)
        self.peak_font.setValue(10)
        peak_layout.addWidget(self.peak_font, 2, 1)
        
        layout.addWidget(peak_group)
        
        # Processing Options Group
        proc_group = QGroupBox("Processing Options")
        proc_layout = QGridLayout(proc_group)
        
        proc_layout.addWidget(QLabel("Start Skip (min):"), 0, 0)
        self.start_skip = QSpinBox()
        self.start_skip.setRange(0, 120)
        self.start_skip.setValue(0)
        proc_layout.addWidget(self.start_skip, 0, 1)
        
        proc_layout.addWidget(QLabel("Process Length (min):"), 0, 2)
        self.process_len = QSpinBox()
        self.process_len.setRange(1, 240)
        self.process_len.setValue(20)
        proc_layout.addWidget(self.process_len, 0, 3)
        
        self.save_png = QCheckBox("Save PNG")
        self.save_png.setChecked(True)
        proc_layout.addWidget(self.save_png, 1, 0)
        
        self.save_pdf = QCheckBox("Save PDF")
        self.save_pdf.setChecked(False)
        proc_layout.addWidget(self.save_pdf, 1, 1)
        
        # Parallel processing option
        proc_layout.addWidget(QLabel("Max Parallel:"), 1, 2)
        self.max_parallel = QSpinBox()
        self.max_parallel.setRange(1, multiprocessing.cpu_count())
        self.max_parallel.setValue(min(4, multiprocessing.cpu_count()))
        self.max_parallel.setToolTip("Maximum number of HVSR curves to process in parallel")
        proc_layout.addWidget(self.max_parallel, 1, 3)
        
        layout.addWidget(proc_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        self.reset_btn = QPushButton("Reset to Defaults")
        self.reset_btn.clicked.connect(self._load_defaults)
        btn_layout.addWidget(self.reset_btn)
        btn_layout.addStretch()
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        self.ok_btn = QPushButton("OK")
        self.ok_btn.clicked.connect(self.accept)
        self.ok_btn.setDefault(True)
        btn_layout.addWidget(self.ok_btn)
        layout.addLayout(btn_layout)
    
    def _on_auto_peaks_changed(self, state):
        self.num_peaks.setEnabled(not self.auto_peaks.isChecked())
    
    def _load_defaults(self):
        self.freq_min.setValue(0.2)
        self.freq_max.setValue(30.0)
        self.smoothing_type.setCurrentText("Konno-Ohmachi")
        self.smoothing_bw.setValue(40)
        self.window_length.setValue(120)
        self.averaging.setCurrentText("geo")
        self.num_peaks.setValue(2)
        self.auto_peaks.setChecked(False)
        self.peak_font.setValue(10)
        self.start_skip.setValue(0)
        self.process_len.setValue(20)
        self.save_png.setChecked(True)
        self.save_pdf.setChecked(False)
        self.max_parallel.setValue(min(4, multiprocessing.cpu_count()))
    
    def get_settings(self):
        return {
            'freq_min': self.freq_min.value(),
            'freq_max': self.freq_max.value(),
            'smoothing_type': self.smoothing_type.currentText(),
            'smoothing_bw': self.smoothing_bw.value(),
            'window_length': self.window_length.value(),
            'averaging': self.averaging.currentText(),
            'num_peaks': self.num_peaks.value(),
            'auto_peaks': self.auto_peaks.isChecked(),
            'peak_font': self.peak_font.value(),
            'start_skip': self.start_skip.value(),
            'process_len': self.process_len.value(),
            'save_png': self.save_png.isChecked(),
            'save_pdf': self.save_pdf.isChecked(),
            'max_parallel': self.max_parallel.value(),
        }
    
    def set_settings(self, settings):
        if 'freq_min' in settings:
            self.freq_min.setValue(settings['freq_min'])
        if 'freq_max' in settings:
            self.freq_max.setValue(settings['freq_max'])
        if 'smoothing_type' in settings:
            self.smoothing_type.setCurrentText(settings['smoothing_type'])
        if 'smoothing_bw' in settings:
            self.smoothing_bw.setValue(settings['smoothing_bw'])
        if 'window_length' in settings:
            self.window_length.setValue(settings['window_length'])
        if 'averaging' in settings:
            self.averaging.setCurrentText(settings['averaging'])
        if 'num_peaks' in settings:
            self.num_peaks.setValue(settings['num_peaks'])
        if 'auto_peaks' in settings:
            self.auto_peaks.setChecked(settings['auto_peaks'])
        if 'peak_font' in settings:
            self.peak_font.setValue(settings['peak_font'])
        if 'start_skip' in settings:
            self.start_skip.setValue(settings['start_skip'])
        if 'process_len' in settings:
            self.process_len.setValue(settings['process_len'])
        if 'save_png' in settings:
            self.save_png.setChecked(settings['save_png'])
        if 'save_pdf' in settings:
            self.save_pdf.setChecked(settings['save_pdf'])
        if 'max_parallel' in settings:
            self.max_parallel.setValue(settings['max_parallel'])


# Background Worker Thread for data processing
class DataProcessWorker(QThread):
    """Worker thread for processing MiniSEED to ArrayData.mat - ONE PER STATION."""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, params):
        super().__init__()
        self.params = params
    
    def run(self):
        try:
            self._run_workflow()
        except Exception as e:
            import traceback
            self.finished.emit(False, f"Error: {str(e)}\n{traceback.format_exc()}")
    
    def _run_workflow(self):
        """Execute the data processing workflow - creates ONE ArrayData.mat per station."""
        from obspy import read, UTCDateTime, Stream
        from scipy.io import savemat
        
        params = self.params
        
        self.progress.emit(5, "Parsing parameters...")
        
        time_window = params.get('time_window')  # Single time window (start, end) - already in UTC
        station_files = params['station_files']  # Dict: {station_id: [file_list]}
        output_dir = params['output_dir']
        
        if not station_files:
            self.finished.emit(False, "No MiniSEED files selected!")
            return
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Parse time window (already converted to UTC by the GUI)
        start_utc = UTCDateTime(time_window['start']) if time_window else None
        end_utc = UTCDateTime(time_window['end']) if time_window else None
        
        if start_utc and end_utc:
            self.progress.emit(8, f"Time window (UTC): {start_utc} to {end_utc}")
        
        self.progress.emit(10, "Processing stations...")
        
        total_stations = len(station_files)
        results = []
        
        for stn_idx, (stn_id, files) in enumerate(sorted(station_files.items())):
            progress_pct = 10 + int(80 * stn_idx / max(1, total_stations))
            self.progress.emit(progress_pct, f"Processing Station #{stn_id} ({stn_idx+1}/{total_stations})...")
            
            # Read all files for this station
            station_name = f"STN{stn_id:02d}"
            
            # First, read ALL files into a combined stream
            combined_stream = Stream()
            fs_detected = None
            
            for f in files:
                try:
                    st = read(f)
                    combined_stream += st
                    # Get sampling rate from first trace
                    if fs_detected is None and len(st) > 0:
                        fs_detected = st[0].stats.sampling_rate
                except Exception as e:
                    self.progress.emit(progress_pct, f"Warning: Could not read {os.path.basename(f)}: {e}")
            
            if len(combined_stream) == 0:
                self.progress.emit(progress_pct, f"Warning: No readable files for Station #{stn_id}")
                continue
            
            # Log the time range of the data
            data_start = min(tr.stats.starttime for tr in combined_stream)
            data_end = max(tr.stats.endtime for tr in combined_stream)
            self.progress.emit(progress_pct, f"Station #{stn_id} data range: {data_start} to {data_end}")
            
            # Merge traces (handles gaps and overlaps)
            try:
                combined_stream.merge(method=1, fill_value=0)
            except Exception as e:
                self.progress.emit(progress_pct, f"Warning: Merge issue for Station #{stn_id}: {e}")
            
            # Trim to time window if specified
            if start_utc and end_utc:
                combined_stream.trim(starttime=start_utc, endtime=end_utc)
                if len(combined_stream) == 0 or all(len(tr.data) == 0 for tr in combined_stream):
                    self.progress.emit(progress_pct, f"Warning: No data in time window for Station #{stn_id}")
                    self.progress.emit(progress_pct, f"  Requested: {start_utc} to {end_utc}")
                    self.progress.emit(progress_pct, f"  Available: {data_start} to {data_end}")
                    continue
            
            # Separate by component
            Array1Z = []
            Array1N = []
            Array1E = []
            
            for tr in combined_stream:
                comp = tr.stats.channel[-1].upper() if tr.stats.channel else 'Z'
                if len(tr.data) > 0:
                    if comp == 'Z':
                        Array1Z.append(tr.data.astype(np.float64))
                    elif comp == 'N' or comp == '1':
                        Array1N.append(tr.data.astype(np.float64))
                    elif comp == 'E' or comp == '2':
                        Array1E.append(tr.data.astype(np.float64))
            
            # Concatenate arrays for this station
            if Array1Z:
                Array1Z = np.concatenate(Array1Z) if len(Array1Z) > 1 else Array1Z[0]
            else:
                Array1Z = np.array([])
            
            if Array1N:
                Array1N = np.concatenate(Array1N) if len(Array1N) > 1 else Array1N[0]
            else:
                Array1N = np.array([])
                
            if Array1E:
                Array1E = np.concatenate(Array1E) if len(Array1E) > 1 else Array1E[0]
            else:
                Array1E = np.array([])
            
            # Check if we have data
            if len(Array1Z) == 0 and len(Array1N) == 0 and len(Array1E) == 0:
                self.progress.emit(progress_pct, f"Warning: No data for Station #{stn_id}")
                continue
            
            # Create station output folder
            stn_dir = os.path.join(output_dir, station_name)
            os.makedirs(stn_dir, exist_ok=True)
            
            # Save ArrayData.mat for this station
            mat_dict = {
                'Array1Z': Array1Z,
                'Array1N': Array1N,
                'Array1E': Array1E,
                'Fs_Hz': fs_detected or 200.0,
            }
            
            mat_path = os.path.join(stn_dir, f"ArrayData_{station_name}.mat")
            savemat(mat_path, mat_dict)
            
            # Log data length
            data_len_sec = len(Array1Z) / (fs_detected or 200.0) if len(Array1Z) > 0 else 0
            self.progress.emit(progress_pct, f"Station #{stn_id}: {data_len_sec:.1f}s of data")
            
            results.append({
                'station_id': stn_id,
                'station_name': station_name,
                'dir': stn_dir,
                'mat_path': mat_path,
                'fs': fs_detected or 200.0,
                'data_length_sec': data_len_sec,
            })
        
        self.progress.emit(95, "Finalizing...")
        self.params['results'] = results
        self.progress.emit(100, "Data processing complete!")
        self.finished.emit(True, f"Data processing complete. Created {len(results)} ArrayData files for {len(results)} stations.")


# Parallel HVSR Manager
class ParallelHVSRManager(QThread):
    """Manages parallel HVSR processing for multiple stations."""
    log_line = pyqtSignal(str)
    progress = pyqtSignal(int, str)  # overall_percent, message
    task_progress = pyqtSignal(str, int)  # station_name, percent
    finished = pyqtSignal(bool, str)
    
    def __init__(self, tasks, max_parallel, cwd, parent=None):
        super().__init__(parent)
        self.tasks = tasks  # List of (station_name, env_dict)
        self.max_parallel = max_parallel
        self._cwd = cwd
        self._stop_requested = False
    
    def stop(self):
        self._stop_requested = True
    
    def run(self):
        total = len(self.tasks)
        completed = 0
        active_procs = {}
        pending = list(self.tasks)
        results = {}
        
        self.progress.emit(0, f"Starting HVSR analysis for {total} station(s)...")
        self.log_line.emit(f"Processing {total} stations with max {self.max_parallel} parallel workers")
        
        while (pending or active_procs) and not self._stop_requested:
            # Start new processes up to max_parallel
            while pending and len(active_procs) < self.max_parallel:
                station_name, env = pending.pop(0)
                self.log_line.emit(f"[{station_name}] Starting HVSR analysis...")
                self.task_progress.emit(station_name, 5)
                
                cmd = [sys.executable, "hvsr_making_peak.py"]
                try:
                    proc = subprocess.Popen(
                        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                        text=True, env=env, cwd=self._cwd
                    )
                    active_procs[station_name] = {'proc': proc, 'started': True}
                    self.task_progress.emit(station_name, 20)
                except Exception as e:
                    self.log_line.emit(f"[{station_name}] Failed to start: {e}")
                    results[station_name] = -1
                    completed += 1
                    self.task_progress.emit(station_name, -1)
            
            # Check running processes
            finished_stations = []
            for station_name, info in active_procs.items():
                proc = info['proc']
                
                # Read any available output (non-blocking would be better but this works)
                if proc.poll() is not None:
                    # Process finished
                    self.task_progress.emit(station_name, 80)
                    
                    if proc.stdout:
                        for line in proc.stdout:
                            line_stripped = line.rstrip()
                            if line_stripped:
                                self.log_line.emit(f"[{station_name}] {line_stripped}")
                    
                    results[station_name] = proc.returncode
                    finished_stations.append(station_name)
                    completed += 1
                    
                    pct = int(100 * completed / total)
                    status = "OK" if proc.returncode == 0 else f"Error (code {proc.returncode})"
                    self.progress.emit(pct, f"Completed {completed}/{total}: {station_name} - {status}")
                    self.task_progress.emit(station_name, 100 if proc.returncode == 0 else -1)
                    self.log_line.emit(f"[{station_name}] Finished: {status}")
            
            for stn in finished_stations:
                del active_procs[stn]
            
            # Small delay to prevent busy waiting
            if active_procs:
                self.msleep(100)
        
        if self._stop_requested:
            # Kill remaining processes
            for info in active_procs.values():
                info['proc'].terminate()
            self.finished.emit(False, "HVSR analysis cancelled")
        else:
            success_count = sum(1 for r in results.values() if r == 0)
            self.finished.emit(True, f"HVSR analysis complete: {success_count}/{total} successful")


# Main Automatic Tab Widget
class NewTab0_Automatic(QWidget):
    """Automatic workflow tab that combines all processing steps."""
    
    def __init__(self):
        super().__init__()
        self.hvsr_settings = {}
        self.data_worker = None
        self.hvsr_manager = None
        self.processed_results = []
        self.hvsr_task_status = {}  # Track status of each HVSR task
        self._build_ui()
    
    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title = QLabel("Automatic Workflow")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)
        
        # 1. Station Files Section
        input_group = QGroupBox("1. Station MiniSEED Files (One per Station)")
        input_layout = QVBoxLayout(input_group)
        
        self.station_table = QTableWidget(0, 3)
        self.station_table.setHorizontalHeaderLabels(["Station #", "Files", "Actions"])
        self.station_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.station_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.station_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.station_table.setMinimumHeight(120)
        input_layout.addWidget(self.station_table)
        
        stn_btn_layout = QHBoxLayout()
        
        self.add_station_btn = QPushButton("Add Station")
        self.add_station_btn.clicked.connect(self._add_station_row)
        stn_btn_layout.addWidget(self.add_station_btn)
        
        self.remove_station_btn = QPushButton("Remove Selected")
        self.remove_station_btn.clicked.connect(self._remove_station_row)
        stn_btn_layout.addWidget(self.remove_station_btn)
        
        self.auto_detect_btn = QPushButton("Auto-Detect from Folder")
        self.auto_detect_btn.clicked.connect(self._auto_detect_stations)
        stn_btn_layout.addWidget(self.auto_detect_btn)
        
        self.clear_all_btn = QPushButton("Clear All")
        self.clear_all_btn.clicked.connect(self._clear_all_stations)
        stn_btn_layout.addWidget(self.clear_all_btn)
        
        stn_btn_layout.addStretch()
        input_layout.addLayout(stn_btn_layout)
        
        # Output directory
        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Output Directory:"))
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("Select output directory...")
        output_layout.addWidget(self.output_dir_edit)
        self.output_browse_btn = QPushButton("Browse...")
        self.output_browse_btn.clicked.connect(self._browse_output_dir)
        output_layout.addWidget(self.output_browse_btn)
        input_layout.addLayout(output_layout)
        
        main_layout.addWidget(input_group)
        
        # 2. Time Window Section
        time_group = QGroupBox("2. Time Window (Applied to ALL Stations)")
        time_layout = QVBoxLayout(time_group)
        
        # Same time for all checkbox
        same_time_layout = QHBoxLayout()
        self.same_time_checkbox = QCheckBox("Use same time window for all stations")
        self.same_time_checkbox.setChecked(True)
        self.same_time_checkbox.setToolTip("When checked, the time window below will be applied to ALL stations")
        self.same_time_checkbox.setStyleSheet("font-weight: bold; color: #2196F3;")
        same_time_layout.addWidget(self.same_time_checkbox)
        same_time_layout.addStretch()
        
        tz_label = QLabel("Input times are in:")
        same_time_layout.addWidget(tz_label)
        self.tz_combo = QComboBox()
        self.tz_combo.addItems([
            "UTC/GMT (data files are UTC)",
            "CST (local, will add +6h to UTC)", 
            "CDT (local, will add +5h to UTC)"
        ])
        self.tz_combo.setToolTip("Select the timezone of your INPUT times.\nMiniSEED files are typically in UTC.")
        same_time_layout.addWidget(self.tz_combo)
        
        time_layout.addLayout(same_time_layout)
        
        # Time input (simplified - just start and end)
        time_input_layout = QGridLayout()
        
        time_input_layout.addWidget(QLabel("Start Time:"), 0, 0)
        self.start_time_edit = QLineEdit()
        self.start_time_edit.setPlaceholderText("YYYY-MM-DD HH:MM:SS")
        time_input_layout.addWidget(self.start_time_edit, 0, 1)
        
        time_input_layout.addWidget(QLabel("End Time:"), 0, 2)
        self.end_time_edit = QLineEdit()
        self.end_time_edit.setPlaceholderText("YYYY-MM-DD HH:MM:SS")
        time_input_layout.addWidget(self.end_time_edit, 0, 3)
        
        time_layout.addLayout(time_input_layout)
        
        # CSV import/export for advanced use
        csv_layout = QHBoxLayout()
        csv_layout.addWidget(QLabel("Advanced (multiple windows):"))
        self.import_csv_btn = QPushButton("Import CSV")
        self.import_csv_btn.clicked.connect(self._import_csv)
        csv_layout.addWidget(self.import_csv_btn)
        
        self.export_csv_btn = QPushButton("Export CSV")
        self.export_csv_btn.clicked.connect(self._export_csv)
        csv_layout.addWidget(self.export_csv_btn)
        csv_layout.addStretch()
        
        time_layout.addLayout(csv_layout)
        
        # Hidden time table for CSV import (simplified UI)
        self.time_table = QTableWidget(0, len(_TIME_COLS))
        self.time_table.setHorizontalHeaderLabels(_TIME_COLS)
        self.time_table.setVisible(False)  # Hidden by default
        time_layout.addWidget(self.time_table)
        
        main_layout.addWidget(time_group)
        
        # 3. HVSR Settings (Button Only)
        hvsr_group = QGroupBox("3. HVSR Settings")
        hvsr_layout = QHBoxLayout(hvsr_group)
        
        self.hvsr_settings_btn = QPushButton("Configure HVSR Settings...")
        self.hvsr_settings_btn.clicked.connect(self._open_hvsr_settings)
        hvsr_layout.addWidget(self.hvsr_settings_btn)
        
        self.hvsr_status_label = QLabel("(Using defaults: 2 peaks, 4 parallel)")
        self.hvsr_status_label.setStyleSheet("color: gray; font-style: italic;")
        hvsr_layout.addWidget(self.hvsr_status_label)
        
        hvsr_layout.addStretch()
        main_layout.addWidget(hvsr_group)
        
        # 4. Progress & Run
        run_group = QGroupBox("4. Run Workflow")
        run_layout = QVBoxLayout(run_group)
        
        # Overall progress
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(QLabel("Overall:"))
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        run_layout.addLayout(progress_layout)
        
        self.progress_label = QLabel("Ready to run...")
        run_layout.addWidget(self.progress_label)
        
        # HVSR task status display (shows each station's status)
        self.task_status_label = QLabel("")
        self.task_status_label.setStyleSheet("color: #666; font-size: 11px;")
        self.task_status_label.setWordWrap(True)
        run_layout.addWidget(self.task_status_label)
        
        btn_layout = QHBoxLayout()
        
        self.run_btn = QPushButton("Run Workflow (Process Data)")
        self.run_btn.setMinimumHeight(35)
        self.run_btn.setFont(QFont("Arial", 11, QFont.Bold))
        self.run_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        self.run_btn.clicked.connect(self._run_workflow)
        btn_layout.addWidget(self.run_btn)
        
        self.hvsr_btn = QPushButton("Generate HVSR Curves (Parallel)")
        self.hvsr_btn.setMinimumHeight(35)
        self.hvsr_btn.setFont(QFont("Arial", 11, QFont.Bold))
        self.hvsr_btn.setStyleSheet("background-color: #2196F3; color: white;")
        self.hvsr_btn.clicked.connect(self._run_hvsr_parallel)
        self.hvsr_btn.setEnabled(False)
        btn_layout.addWidget(self.hvsr_btn)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel_workflow)
        btn_layout.addWidget(self.cancel_btn)
        
        run_layout.addLayout(btn_layout)
        main_layout.addWidget(run_group)
        
        # Log Section
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)
        
        main_layout.addWidget(log_group)
        
        self._init_hvsr_defaults()
    
    # Station Table Methods
    def _add_station_row(self, station_num=None, files=None):
        row = self.station_table.rowCount()
        self.station_table.insertRow(row)
        
        stn_spin = QSpinBox()
        stn_spin.setRange(1, 99)
        if station_num:
            stn_spin.setValue(station_num)
        else:
            existing = self._get_existing_station_nums()
            next_num = 1
            while next_num in existing:
                next_num += 1
            stn_spin.setValue(next_num)
        self.station_table.setCellWidget(row, 0, stn_spin)
        
        files_item = QTableWidgetItem()
        files_item.setData(Qt.UserRole, files or [])
        files_item.setText(self._format_files_text(files or []))
        files_item.setFlags(files_item.flags() & ~Qt.ItemIsEditable)
        self.station_table.setItem(row, 1, files_item)
        
        action_widget = QWidget()
        action_layout = QHBoxLayout(action_widget)
        action_layout.setContentsMargins(2, 2, 2, 2)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(lambda checked, r=row: self._browse_station_files(r))
        action_layout.addWidget(browse_btn)
        
        self.station_table.setCellWidget(row, 2, action_widget)
        self._log(f"Added station row #{stn_spin.value()}")
    
    def _get_existing_station_nums(self):
        nums = []
        for r in range(self.station_table.rowCount()):
            spin = self.station_table.cellWidget(r, 0)
            if spin:
                nums.append(spin.value())
        return nums
    
    def _format_files_text(self, files):
        if not files:
            return "(No files selected)"
        elif len(files) == 1:
            return os.path.basename(files[0])
        else:
            return f"{len(files)} files: {os.path.basename(files[0])}, ..."
    
    def _browse_station_files(self, row):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select MiniSEED Files for Station", "",
            "MiniSEED Files (*.mseed *.miniseed);;All Files (*.*)"
        )
        if files:
            item = self.station_table.item(row, 1)
            if item:
                existing = item.data(Qt.UserRole) or []
                all_files = existing + [f for f in files if f not in existing]
                item.setData(Qt.UserRole, all_files)
                item.setText(self._format_files_text(all_files))
                
                stn_spin = self.station_table.cellWidget(row, 0)
                stn_num = stn_spin.value() if stn_spin else row + 1
                self._log(f"Added {len(files)} file(s) to Station #{stn_num}")
    
    def _remove_station_row(self):
        rows = set(idx.row() for idx in self.station_table.selectedIndexes())
        for r in sorted(rows, reverse=True):
            self.station_table.removeRow(r)
        if rows:
            self._log(f"Removed {len(rows)} station row(s)")
    
    def _auto_detect_stations(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder with MiniSEED Files")
        if not folder:
            return
        
        import re
        
        station_files = {}
        for fname in os.listdir(folder):
            if fname.lower().endswith(('.mseed', '.miniseed')):
                match = re.search(r'STN(\d+)', fname, re.IGNORECASE)
                if match:
                    stn_num = int(match.group(1))
                else:
                    match = re.search(r'(\d{1,2})[_.]', fname)
                    if match:
                        stn_num = int(match.group(1))
                    else:
                        continue
                
                if stn_num not in station_files:
                    station_files[stn_num] = []
                station_files[stn_num].append(os.path.join(folder, fname))
        
        if not station_files:
            QMessageBox.warning(self, "No Files Found", 
                "No MiniSEED files with station numbers found.\n"
                "Expected format: STN01_*.mseed or similar.")
            return
        
        self.station_table.setRowCount(0)
        for stn_num in sorted(station_files.keys()):
            self._add_station_row(station_num=stn_num, files=station_files[stn_num])
        
        self._log(f"Auto-detected {len(station_files)} stations from folder")
    
    def _clear_all_stations(self):
        self.station_table.setRowCount(0)
        self._log("Cleared all stations")
    
    def _get_station_files(self):
        result = {}
        for r in range(self.station_table.rowCount()):
            spin = self.station_table.cellWidget(r, 0)
            item = self.station_table.item(r, 1)
            if spin and item:
                stn_id = spin.value()
                files = item.data(Qt.UserRole) or []
                if files:
                    if stn_id in result:
                        result[stn_id].extend(files)
                    else:
                        result[stn_id] = list(files)  # Copy the list
        return result
    
    # Time Window Methods
    def _get_tz_offset(self):
        """Get timezone offset in hours (to convert input time to UTC)."""
        tz_idx = self.tz_combo.currentIndex()
        if tz_idx == 0:
            return 0  # UTC/GMT - no conversion
        elif tz_idx == 1:
            return 6  # CST - add 6 hours to get UTC
        elif tz_idx == 2:
            return 5  # CDT - add 5 hours to get UTC
        else:
            return 0  # Default to UTC
    
    def _get_time_window(self):
        """Get the single time window from the input fields."""
        start_str = self.start_time_edit.text().strip()
        end_str = self.end_time_edit.text().strip()
        
        if not start_str or not end_str:
            return None
        
        try:
            offset = self._get_tz_offset()
            start_dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M:%S") + timedelta(hours=offset)
            end_dt = datetime.strptime(end_str, "%Y-%m-%d %H:%M:%S") + timedelta(hours=offset)
            return {'start': start_dt, 'end': end_dt}
        except ValueError:
            return None
    
    def _import_csv(self):
        """Import time window from CSV - uses first row only when 'same time for all' is checked."""
        path, _ = QFileDialog.getOpenFileName(self, "Open CSV", "", "CSV files (*.csv)")
        if not path:
            return
        
        try:
            with open(path, newline="") as f:
                reader = csv.reader(f)
                rows = list(reader)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not read CSV:\n{e}")
            return
        
        # Find first data row
        header = rows[0] if rows else []
        start_row = 1 if header and header[0].strip().lower() == "figure" else 0
        
        if start_row >= len(rows):
            QMessageBox.warning(self, "Empty CSV", "No data rows found in CSV.")
            return
        
        # Parse first data row
        row = rows[start_row]
        if len(row) < 13:
            QMessageBox.warning(self, "Invalid CSV", "CSV row has fewer than 13 columns.")
            return
        
        try:
            # Extract start time
            sy, sm, sd, sh, smi, ss = int(row[1]), int(row[2]), int(row[3]), int(row[4]), int(row[5]), int(row[6])
            # Extract end time
            ey, em, ed, eh, emi, es = int(row[7]), int(row[8]), int(row[9]), int(row[10]), int(row[11]), int(row[12])
            
            start_str = f"{sy:04d}-{sm:02d}-{sd:02d} {sh:02d}:{smi:02d}:{ss:02d}"
            end_str = f"{ey:04d}-{em:02d}-{ed:02d} {eh:02d}:{emi:02d}:{es:02d}"
            
            self.start_time_edit.setText(start_str)
            self.end_time_edit.setText(end_str)
            
            self._log(f"Imported time window from CSV: {start_str} to {end_str}")
        except (ValueError, IndexError) as e:
            QMessageBox.warning(self, "Parse Error", f"Could not parse CSV row: {e}")
    
    def _export_csv(self):
        """Export current time window to CSV."""
        time_window = self._get_time_window()
        if not time_window:
            QMessageBox.warning(self, "No Time", "Please enter a valid time window first.")
            return
        
        path, _ = QFileDialog.getSaveFileName(self, "Save CSV", "time_window.csv", "CSV files (*.csv)")
        if not path:
            return
        
        try:
            with open(path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(_TIME_COLS)
                
                start = time_window['start']
                end = time_window['end']
                
                writer.writerow([
                    "HV1",
                    start.year, start.month, start.day, start.hour, start.minute, start.second,
                    end.year, end.month, end.day, end.hour, end.minute, end.second
                ])
            
            self._log(f"Exported time window to {path}")
            QMessageBox.information(self, "Saved", f"Time window exported to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not write CSV:\n{e}")
    
    # Other Methods
    def _browse_output_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if folder:
            self.output_dir_edit.setText(folder)
    
    def _init_hvsr_defaults(self):
        self.hvsr_settings = {
            'freq_min': 0.2,
            'freq_max': 30.0,
            'smoothing_type': 'Konno-Ohmachi',
            'smoothing_bw': 40,
            'window_length': 120,
            'averaging': 'geo',
            'num_peaks': 2,
            'auto_peaks': False,
            'peak_font': 10,
            'start_skip': 0,
            'process_len': 20,
            'save_png': True,
            'save_pdf': False,
            'max_parallel': min(4, multiprocessing.cpu_count()),
        }
    
    def _open_hvsr_settings(self):
        dialog = HVSRSettingsDialog(self)
        dialog.set_settings(self.hvsr_settings)
        if dialog.exec_() == QDialog.Accepted:
            self.hvsr_settings = dialog.get_settings()
            peaks_txt = "unlimited" if self.hvsr_settings['auto_peaks'] else str(self.hvsr_settings['num_peaks'])
            self.hvsr_status_label.setText(
                f"(Custom: {peaks_txt} peaks, {self.hvsr_settings['max_parallel']} parallel)")
            self.hvsr_status_label.setStyleSheet("color: green; font-style: italic;")
            self._log("HVSR settings updated")
    
    def _log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        self.log_text.ensureCursorVisible()
    
    def _validate_inputs(self):
        errors = []
        
        station_files = self._get_station_files()
        if not station_files:
            errors.append("No station files configured")
        
        if not self.output_dir_edit.text().strip():
            errors.append("No output directory selected")
        
        if self.same_time_checkbox.isChecked():
            time_window = self._get_time_window()
            if not time_window:
                errors.append("Invalid or missing time window (use format: YYYY-MM-DD HH:MM:SS)")
        
        return errors
    
    def _run_workflow(self):
        errors = self._validate_inputs()
        if errors:
            QMessageBox.warning(self, "Validation Error", "\n".join(errors))
            return
        
        time_window = self._get_time_window()
        
        params = {
            'station_files': self._get_station_files(),
            'output_dir': self.output_dir_edit.text(),
            'time_window': time_window,
            'hvsr_settings': self.hvsr_settings,
        }
        
        self.run_btn.setEnabled(False)
        self.hvsr_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        
        self.data_worker = DataProcessWorker(params)
        self.data_worker.progress.connect(self._on_progress)
        self.data_worker.finished.connect(self._on_data_finished)
        self.data_worker.start()
        
        self._log("Data processing started...")
    
    def _run_hvsr_parallel(self):
        """Run HVSR curve generation for all processed stations in parallel."""
        if not self.processed_results:
            QMessageBox.warning(self, "No Data", "Please run data processing first.")
            return
        
        # Build list of tasks - ONE per station
        tasks = []
        cwd = os.path.dirname(__file__)
        
        self.hvsr_task_status.clear()
        
        for result in self.processed_results:
            station_name = result['station_name']
            mat_path = result['mat_path']
            out_dir = result['dir']
            fs = result['fs']
            
            env = os.environ.copy()
            env.update({
                "HV_ARRAY": str(mat_path),
                "HV_OUTDIR": str(out_dir),
                "HV_FIG": station_name,  # Figure name = station name
                "HV_TITLE": station_name,
                "HV_FS": str(fs),
                "HV_TW": str(self.hvsr_settings.get('window_length', 120)),
                "HV_KO": str(self.hvsr_settings.get('smoothing_bw', 40)),
                "HV_FMIN": str(self.hvsr_settings.get('freq_min', 0.2)),
                "HV_PROC": str(self.hvsr_settings.get('process_len', 20)),
                "HV_SKIP": str(self.hvsr_settings.get('start_skip', 0)),
                "HV_PFONT": str(self.hvsr_settings.get('peak_font', 10)),
                "HV_AVG": self.hvsr_settings.get('averaging', 'geo'),
                "HV_SAVE": "1" if self.hvsr_settings.get('save_png', True) else "0",
                "HV_PDF": "1" if self.hvsr_settings.get('save_pdf', False) else "0",
            })
            
            if self.hvsr_settings.get('auto_peaks', False):
                env["HV_NUMPK"] = ""
            else:
                env["HV_NUMPK"] = str(self.hvsr_settings.get('num_peaks', 2))
            
            tasks.append((station_name, env))
            self.hvsr_task_status[station_name] = 0
        
        self._update_task_status_display()
        
        max_parallel = self.hvsr_settings.get('max_parallel', 4)
        
        self._log(f"Starting parallel HVSR analysis for {len(tasks)} station(s) with {max_parallel} workers...")
        
        self.run_btn.setEnabled(False)
        self.hvsr_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_label.setText(f"HVSR: Processing 0/{len(tasks)} stations...")
        
        self.hvsr_manager = ParallelHVSRManager(tasks, max_parallel, cwd, self)
        self.hvsr_manager.log_line.connect(self._log)
        self.hvsr_manager.progress.connect(self._on_hvsr_progress)
        self.hvsr_manager.task_progress.connect(self._on_task_progress)
        self.hvsr_manager.finished.connect(self._on_hvsr_finished)
        self.hvsr_manager.start()
    
    def _update_task_status_display(self):
        """Update the task status display label."""
        if not self.hvsr_task_status:
            self.task_status_label.setText("")
            return
        
        status_parts = []
        for stn, pct in sorted(self.hvsr_task_status.items()):
            if pct == 100:
                status_parts.append(f"{stn}: Done")
            elif pct == -1:
                status_parts.append(f"{stn}: Error")
            elif pct > 0:
                status_parts.append(f"{stn}: {pct}%")
            else:
                status_parts.append(f"{stn}: Waiting")
        
        self.task_status_label.setText(" | ".join(status_parts))
    
    def _on_task_progress(self, station_name, pct):
        """Handle progress update for a single station task."""
        self.hvsr_task_status[station_name] = pct
        self._update_task_status_display()
    
    def _on_hvsr_progress(self, pct, message):
        """Handle overall HVSR progress."""
        self.progress_bar.setValue(pct)
        self.progress_label.setText(message)
    
    def _on_hvsr_finished(self, success, message):
        """Handle HVSR completion."""
        self.run_btn.setEnabled(True)
        self.hvsr_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        
        self._log(message)
        self.progress_label.setText(message)
        
        if success:
            QMessageBox.information(self, "Complete", message)
        else:
            QMessageBox.warning(self, "HVSR Status", message)
    
    def _cancel_workflow(self):
        if self.data_worker and self.data_worker.isRunning():
            self.data_worker.terminate()
            self._log("Data processing cancelled by user")
            self._on_data_finished(False, "Data processing cancelled")
        
        if self.hvsr_manager and self.hvsr_manager.isRunning():
            self.hvsr_manager.stop()
            self._log("HVSR analysis cancellation requested...")
    
    def _on_progress(self, percent, message):
        self.progress_bar.setValue(percent)
        self.progress_label.setText(message)
        self._log(message)
    
    def _on_data_finished(self, success, message):
        self.run_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        
        if success:
            self.progress_label.setText("Data processing complete!")
            self._log("Data processing complete!")
            
            if self.data_worker and hasattr(self.data_worker, 'params'):
                self.processed_results = self.data_worker.params.get('results', [])
            
            if self.processed_results:
                self.hvsr_btn.setEnabled(True)
                station_info = ", ".join([r['station_name'] for r in self.processed_results])
                self._log(f"Ready to generate HVSR curves for: {station_info}")
                QMessageBox.information(self, "Success", 
                    f"{message}\n\nStations ready: {station_info}\n\nClick 'Generate HVSR Curves (Parallel)' to create interactive plots.")
            else:
                QMessageBox.information(self, "Success", message)
        else:
            self.progress_label.setText("Processing failed!")
            self._log(f"Failed: {message}")
            QMessageBox.warning(self, "Error", message)
