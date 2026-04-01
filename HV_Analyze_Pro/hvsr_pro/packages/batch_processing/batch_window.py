"""
Batch Processing Window
=======================

Main window for batch HVSR processing of multiple stations.
Adapted from HVSR_old's NewTab0_Automatic.py.

Uses HV_Pro's HVSRProcessor directly instead of subprocesses.
Opens as a separate window from the main app via Tools > Batch Processing.
"""

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QTextEdit, QFileDialog, QMessageBox,
    QProgressBar, QDialog, QTableWidget, QHeaderView, QTabWidget, QSplitter,
    QStatusBar
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from datetime import datetime
import multiprocessing
import os
import numpy as np

# Package-local imports
from hvsr_pro.packages.batch_processing.dialogs.hvsr_settings import HVSRSettingsDialog
from hvsr_pro.packages.batch_processing.dialogs.time_windows import TimeWindowsDialog
from hvsr_pro.packages.batch_processing.workers.data_worker import DataProcessWorker
from hvsr_pro.packages.batch_processing.workers.hvsr_worker import BatchHVSRWorker, BatchTask
from hvsr_pro.packages.batch_processing.station_manager import StationManager
from hvsr_pro.packages.batch_processing import report_export
from hvsr_pro.packages.batch_processing import results_handler

try:
    from hvsr_pro.packages.batch_processing.processing import (
        StationResult, PeakStatistics, AutomaticWorkflowResult,
        run_automatic_peak_detection, OutputOrganizer, organize_by_topic,
        Peak, detect_peaks, find_top_n_peaks
    )
    PROCESSING_AVAILABLE = True
except ImportError:
    PROCESSING_AVAILABLE = False


class BatchProcessingWindow(QMainWindow):
    """
    Separate window for batch HVSR processing.
    
    Features:
    - Station-based file management (table view)
    - Time window configuration with timezone support
    - HVSR settings dialog (QC, smoothing, frequency range)
    - Parallel processing using HV_Pro's HVSRProcessor
    - Results display with table, canvas, layer tree, histogram
    - Report generation (Excel, CSV, figures)
    """

    def __init__(self, parent=None, project_context=None):
        """
        Parameters
        ----------
        parent : QWidget, optional
        project_context : dict, optional
            If launched from Project Manager, contains:
            - 'project': Project instance
            - 'batch_id': str (e.g. 'batch_001')
        """
        super().__init__(parent)
        self.setWindowTitle("HVSR Pro - Batch Processing")
        self.resize(1200, 800)
        self.setMinimumSize(900, 600)
        
        # Project integration
        self._project_context = project_context
        
        # State
        self.hvsr_settings = {}
        self.data_worker = None
        self.hvsr_worker = None
        self.processed_results = []
        self.hvsr_task_status = {}
        self._workflow_result = None
        self._manual_median_peaks = []
        self._time_windows_data = {'timezone': 'CST', 'windows': []}
        self._fig_export_settings = None
        self._last_checked_ids = None  # Cache for selection change optimization
        self._station_files_cache = []  # Python-level cache for save safety
        
        # Build UI
        self._build_ui()
        self._init_hvsr_defaults()
        
        # Status bar
        self.statusBar().showMessage("Ready")
        
        # Apply project context after UI is built
        if self._project_context:
            self._apply_project_context()

    # ==================================================================
    #  Project Manager Integration
    # ==================================================================

    def _apply_project_context(self):
        """Configure batch window from project context."""
        ctx = self._project_context
        if not ctx:
            return

        project = ctx.get('project')
        batch_id = ctx.get('batch_id')
        if not project:
            return

        # Set output directory to project batch folder
        batch_dir = project.ensure_module_dir('batch_processing', batch_id)
        if hasattr(self, 'output_dir_edit'):
            self.output_dir_edit.setText(str(batch_dir))

        self.setWindowTitle(f"HVSR Pro - Batch Processing — {project.name}")

        # Try restoring saved state first; if none, pre-populate from registry
        restored = self._restore_project_state(project, batch_id)
        if not restored and project.registry and project.registry.stations:
            self._pre_populate_from_registry(project)

    def _pre_populate_from_registry(self, project):
        """Add station rows from the project's station registry."""
        registry = project.registry
        if not registry or not registry.stations:
            return

        import re
        changed = False
        for stn in registry.stations:
            stn_num = None
            m = re.search(r'(\d+)', stn.id)
            if m:
                stn_num = int(m.group(1))
                if stn.batch_station_num != stn_num:
                    stn.batch_station_num = stn_num
                    changed = True

            self._station_mgr.add_station_row(
                station_num=stn_num, files=None, sensor=stn.sensor,
            )

        if changed:
            project.save()
        self._log(f"Loaded {len(registry.stations)} stations from project registry")

    def _write_project_csvs(self):
        """Write batch_peaks.csv, combined_results.csv, and update registry f0."""
        ctx = self._project_context
        if not ctx:
            return
        project = ctx.get('project')
        batch_id = ctx.get('batch_id')
        if not project or not batch_id:
            return

        try:
            from hvsr_pro.packages.project_manager.data_bridge import (
                write_batch_peaks_csv, write_combined_results_csv,
            )

            batch_dir = project.ensure_module_dir('batch_processing', batch_id)

            # Convert workflow results to the dict format data_bridge expects
            result_dicts = self._workflow_result_to_dicts()
            if not result_dicts:
                return

            write_batch_peaks_csv(result_dicts, batch_dir / 'batch_peaks.csv')
            write_combined_results_csv(project, result_dicts, batch_id)

            # Update the registry with f0 values from batch results
            registry = project.registry
            if registry:
                n_updated = registry.update_from_batch_results(result_dicts)
                if n_updated > 0:
                    self._log(f"Updated f0 for {n_updated} station(s) in registry")

            project.log_activity('batch_processing', f'Results saved to {batch_id}')
            project.save()
            self._log("Project CSVs written: batch_peaks.csv, combined_results.csv")
        except Exception as e:
            self._log(f"Warning: failed to write project CSVs: {e}")

    def _workflow_result_to_dicts(self):
        """Convert _workflow_result.station_results to list-of-dicts for data_bridge."""
        if not self._workflow_result:
            return []
        dicts = []
        for sr in self._workflow_result.station_results:
            peaks = []
            if hasattr(sr, 'peaks') and sr.peaks:
                for p in sr.peaks:
                    peaks.append({
                        'frequency': getattr(p, 'frequency', getattr(p, 'freq', None)),
                        'amplitude': getattr(p, 'amplitude', getattr(p, 'amp', None)),
                    })
            dicts.append({
                'station_name': sr.station_name,
                'station_id': getattr(sr, 'station_id', None),
                'peaks': peaks,
                'valid_windows': getattr(sr, 'valid_windows', 0),
                'total_windows': getattr(sr, 'total_windows', 0),
                'output_dir': getattr(sr, 'output_dir',
                               self.output_dir_edit.text() if hasattr(self, 'output_dir_edit') else ''),
            })
        return dicts

    def _save_project_state(self):
        """Save batch state to the project folder on close."""
        ctx = self._project_context
        if not ctx:
            return
        project = ctx.get('project')
        batch_id = ctx.get('batch_id')
        if not project or not batch_id:
            return

        try:
            from hvsr_pro.packages.project_manager.module_state.batch_state_io import (
                save_batch_state,
            )

            batch_dir = project.ensure_module_dir('batch_processing', batch_id)

            # Collect station entries from the table
            station_entries = []
            table_has_data = False
            for row in range(self.station_table.rowCount()):
                spin = self.station_table.cellWidget(
                    row, StationManager._COL_STATION)
                files_item = self.station_table.item(
                    row, StationManager._COL_FILES)
                sensor_item = self.station_table.item(
                    row, StationManager._COL_SENSOR)
                files = files_item.data(Qt.UserRole) if files_item else []
                if files:
                    table_has_data = True
                station_entries.append({
                    'station_num': spin.value() if spin else row + 1,
                    'files': [str(f) for f in files] if files else [],
                    'sensor': sensor_item.text() if sensor_item else None,
                })

            # If table had no file data (e.g. called during widget
            # destruction) fall back to the Python-level cache.
            if not table_has_data and self._station_files_cache:
                station_entries = self._station_files_cache
            else:
                # Update the cache for future safety-net use
                self._station_files_cache = station_entries

            result_dicts = self._workflow_result_to_dicts()

            save_batch_state(
                batch_dir,
                station_entries=station_entries,
                processed_results=result_dicts,
                data_worker_results=self.processed_results or [],
                settings=self.hvsr_settings,
                time_windows=self._time_windows_data,
                manual_peaks=self._manual_median_peaks,
                fig_settings=self._fig_export_settings,
            )

            project.log_activity('batch_processing', f'State saved for {batch_id}')
            project.save()
        except Exception as e:
            import traceback
            self._log(f"Warning: failed to save project state: {e}")
            print(f"[BatchProcessing] Save failed: {e}\n{traceback.format_exc()}")

    def _restore_project_state(self, project, batch_id):
        """Restore batch state from a previous session. Returns True if restored."""
        try:
            from hvsr_pro.packages.project_manager.module_state.batch_state_io import (
                has_batch_state, load_batch_state,
            )

            batch_dir = project.ensure_module_dir('batch_processing', batch_id)
            if batch_dir is None or not has_batch_state(batch_dir):
                return False

            state = load_batch_state(batch_dir)

            # Restore station entries
            entries_list = state.get('station_entries', [])
            for entry in entries_list:
                self._station_mgr.add_station_row(
                    station_num=entry.get('station_num'),
                    files=entry.get('files'),
                    sensor=entry.get('sensor'),
                )
            # Populate the Python-level cache from restored entries
            self._station_files_cache = entries_list

            # Restore settings
            saved_settings = state.get('settings', {})
            if saved_settings:
                self.hvsr_settings.update(saved_settings)

            # Restore extra state
            tw = state.get('time_windows')
            if tw:
                self._time_windows_data = tw
            mp = state.get('manual_peaks')
            if mp:
                self._manual_median_peaks = mp
            fs = state.get('fig_settings')
            if fs:
                self._fig_export_settings = fs

            # Restore output dir
            if hasattr(self, 'output_dir_edit'):
                self.output_dir_edit.setText(str(batch_dir))

            # Restore data-worker results (needed by load_hvsr_results)
            dw_results = state.get('data_worker_results', [])
            if dw_results:
                self.processed_results = dw_results
            else:
                # Fallback: reconstruct from directory structure
                dw_results = self._scan_batch_dir_for_results(str(batch_dir))
                if dw_results:
                    self.processed_results = dw_results

            # If we have processed results, schedule Results tab population
            if self.processed_results:
                if hasattr(self, 'hvsr_btn'):
                    self.hvsr_btn.setEnabled(True)
                QTimer.singleShot(500, self._reload_results_from_disk)

            self._log(f"Restored batch state from {batch_id}")
            return True
        except Exception as e:
            import traceback
            self._log(f"Warning: failed to restore state: {e}")
            print(f"[BatchProcessing] Restore failed: {e}\n{traceback.format_exc()}")
            return False

    def _scan_batch_dir_for_results(self, batch_dir):
        """Reconstruct data-worker results by scanning directory structure.

        Handles projects saved before data_worker_results was persisted.
        Looks for T_*/STN*/ directories containing result JSON files.
        """
        import os
        import glob

        results = []
        batch_path = str(batch_dir)

        # Look for time-window directories (T_01, T_02, etc.)
        for entry in sorted(os.listdir(batch_path)):
            tw_dir = os.path.join(batch_path, entry)
            if not os.path.isdir(tw_dir) or entry.startswith('.'):
                continue
            # Skip known non-station directories
            if entry.lower() in ('report', '__pycache__'):
                continue

            # Look for station subdirectories
            has_station = False
            for stn_entry in sorted(os.listdir(tw_dir)):
                stn_dir = os.path.join(tw_dir, stn_entry)
                if not os.path.isdir(stn_dir):
                    continue

                # Check if this dir has result files
                result_jsons = glob.glob(
                    os.path.join(stn_dir, "HVSR_*_result.json"))
                mat_files = glob.glob(
                    os.path.join(stn_dir, "HVSR_Median_*.mat"))
                if not result_jsons and not mat_files:
                    continue

                has_station = True
                # Extract station_id from station_name if possible
                stn_name = stn_entry
                stn_id = 0
                try:
                    stn_id = int(''.join(c for c in stn_name if c.isdigit()) or '0')
                except ValueError:
                    pass

                results.append({
                    'station_id': stn_id,
                    'station_name': stn_name,
                    'window_name': entry,
                    'dir': stn_dir,
                    'mat_path': os.path.join(
                        stn_dir, f"ArrayData_{stn_name}.mat"),
                })

        return results

    def _reload_results_from_disk(self):
        """Reload HVSR results from disk and populate the Results tab."""
        if not self.processed_results:
            return
        if not PROCESSING_AVAILABLE:
            self._log("Processing modules not available; cannot reload results.")
            return

        try:
            self._log("Reloading HVSR results from disk...")
            station_results = results_handler.load_hvsr_results(
                self.processed_results, self.hvsr_settings, log_fn=self._log)

            if not station_results:
                self._log("No saved results found on disk.")
                return

            result = results_handler.run_analysis(
                station_results, self.hvsr_settings, log_fn=self._log)

            self._populate_results_tab(result)
            self._log(f"Restored {len(station_results)} station result(s) "
                      f"in Results tab.")
        except Exception as e:
            import traceback
            self._log(f"Warning: could not reload results: {e}\n"
                      f"{traceback.format_exc()}")

    def closeEvent(self, event):
        """Save project state before closing."""
        if self._project_context:
            self._save_project_state()
            # Write CSVs if we have results
            if self._workflow_result:
                self._write_project_csvs()
        super().closeEvent(event)

    # ==================================================================
    #  UI Construction
    # ==================================================================

    def _build_ui(self):
        """Build the main window UI."""
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(4, 4, 4, 4)

        # Top-level tab widget: Analysis | Results & Summary
        self.mode_tabs = QTabWidget()
        main_layout.addWidget(self.mode_tabs)

        # Tab A: Analysis
        self._analysis_tab = QWidget()
        self.mode_tabs.addTab(self._analysis_tab, "Analysis")

        # Tab B: Results & Summary
        self._results_tab = QWidget()
        self.mode_tabs.addTab(self._results_tab, "Results && Summary")
        self.mode_tabs.setTabEnabled(1, False)

        self._build_analysis_tab()
        self._build_results_tab()

    # ==================================================================
    #  Tab B - Results & Summary
    # ==================================================================

    def _build_results_tab(self):
        """Build the Results & Summary tab."""
        try:
            from hvsr_pro.packages.batch_processing.widgets import (
                ResultsTableWidget, ResultsCanvasWidget,
                ResultsLayerTree, ResultsHistogramWidget,
            )
        except ImportError:
            layout = QVBoxLayout(self._results_tab)
            layout.addWidget(QLabel("Results widgets not available."))
            return

        layout = QVBoxLayout(self._results_tab)
        layout.setContentsMargins(2, 2, 2, 2)

        h_splitter = QSplitter(Qt.Horizontal)

        # LEFT column: table + histogram
        left_splitter = QSplitter(Qt.Vertical)
        self.results_table = ResultsTableWidget()
        left_splitter.addWidget(self.results_table)
        self.results_histogram = ResultsHistogramWidget()
        left_splitter.addWidget(self.results_histogram)
        left_splitter.setStretchFactor(0, 6)
        left_splitter.setStretchFactor(1, 4)
        h_splitter.addWidget(left_splitter)

        # CENTER column: HVSR curve canvas
        self.results_canvas = ResultsCanvasWidget()
        h_splitter.addWidget(self.results_canvas)

        # RIGHT column: layer tree
        self.results_layer_tree = ResultsLayerTree()
        h_splitter.addWidget(self.results_layer_tree)

        h_splitter.setStretchFactor(0, 32)
        h_splitter.setStretchFactor(1, 50)
        h_splitter.setStretchFactor(2, 18)
        layout.addWidget(h_splitter)

        # Export toolbar
        export_bar = QHBoxLayout()
        self.btn_generate_report = QPushButton("Generate Report (Excel + Figures)")
        self.btn_generate_report.setMinimumHeight(30)
        self.btn_generate_report.setStyleSheet("background-color: #4CAF50; color: white;")
        self.btn_generate_report.clicked.connect(self._generate_report)
        export_bar.addWidget(self.btn_generate_report)
        export_bar.addStretch()
        layout.addLayout(export_bar)

        # Wire signals
        self.results_table.selection_changed.connect(self._on_results_selection_changed)
        self.results_layer_tree.station_visibility_changed.connect(
            self.results_canvas.set_station_visible)
        self.results_layer_tree.array_median_visibility_changed.connect(
            self.results_canvas.set_array_median_visible)
        self.results_layer_tree.grand_median_visibility_changed.connect(
            self.results_canvas.set_grand_median_visible)
        self.results_layer_tree.std_band_visibility_changed.connect(
            self.results_canvas.set_std_band_visible)
        self.results_layer_tree.combined_std_visibility_changed.connect(
            self.results_canvas.set_combined_std_visible)
        self.results_layer_tree.peak_group_visibility_changed.connect(
            self.results_canvas.set_peak_group_visible)
        self.results_canvas.manual_peaks_changed.connect(
            self._on_manual_peaks_changed)

    def _on_manual_peaks_changed(self, peaks):
        self._manual_median_peaks = peaks

    def _populate_results_tab(self, workflow_result):
        """Fill the Results tab from an AutomaticWorkflowResult."""
        self._workflow_result = workflow_result

        if not hasattr(self, 'results_table'):
            return

        station_results = workflow_result.station_results
        array_names = sorted(set(s.topic for s in station_results))

        self.results_table.populate(station_results)
        self.results_canvas.plot_all(station_results, array_names)
        
        n_peaks = self.hvsr_settings.get('auto_npeaks', 3)
        self.results_canvas.pick_max_spin.setValue(n_peaks)
        self._manual_median_peaks = []
        self.results_canvas.clear_manual_peaks()

        station_colors = {}
        for sr in station_results:
            line = self.results_canvas.get_station_line(sr.topic, sr.station_name)
            if line:
                station_colors[(sr.topic, sr.station_name)] = line.get_color()

        self.results_layer_tree.build(station_results, array_names, station_colors)
        self.results_histogram.set_data(station_results, array_names)

        self.mode_tabs.setTabEnabled(1, True)
        self.mode_tabs.setCurrentIndex(1)

        # Auto-write project CSVs when results are ready
        if self._project_context:
            self._write_project_csvs()

    def _on_results_selection_changed(self):
        if not hasattr(self, 'results_table'):
            return
        checked = self.results_table.get_checked_results()
        checked_ids = frozenset(
            (sr.topic, sr.station_name) for sr in checked)
        if checked_ids == self._last_checked_ids:
            return
        self._last_checked_ids = checked_ids
        self.results_canvas.replot_grand_median(checked)
        if hasattr(self, 'results_histogram'):
            self.results_histogram.refresh(checked)

    def _generate_report(self):
        """Export combined report."""
        if not hasattr(self, 'results_table'):
            return

        checked = self.results_table.get_checked_results()
        if not checked:
            QMessageBox.warning(self, "No Stations", "No stations selected for report.")
            return

        from hvsr_pro.packages.batch_processing.dialogs.figure_export_settings import (
            FigureExportSettingsDialog, DEFAULT_SETTINGS,
        )
        dlg = FigureExportSettingsDialog(self, self._fig_export_settings)
        if dlg.exec_() != QDialog.Accepted:
            return
        fig_settings = dlg.get_settings()
        self._fig_export_settings = fig_settings

        output_dir = self.output_dir_edit.text().strip()
        if not output_dir:
            output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
            if not output_dir:
                return

        report_dir = os.path.join(output_dir, "Report")

        try:
            import csv as csv_mod
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            curves_dir = os.path.join(report_dir, "curves")
            hist_dir = os.path.join(report_dir, "histogram")
            table_dir = os.path.join(report_dir, "table")
            median_dir = os.path.join(report_dir, "median")
            for d in (curves_dir, hist_dir, table_dir, median_dir):
                os.makedirs(d, exist_ok=True)

            # Table export (fast, sequential)
            self.progress_label.setText("Exporting table...")
            csv_path = os.path.join(table_dir, "HVSR_Results_Table.csv")
            with open(csv_path, 'w', newline='') as f:
                writer = csv_mod.writer(f)
                writer.writerow(["Array", "Station", "Valid/Total",
                                 "F0_Hz", "A0", "F1_Hz", "A1", "F2_Hz", "A2"])
                for sr in checked:
                    peaks_sorted = sorted(sr.peaks, key=lambda p: p.frequency) if sr.peaks else []
                    row = [sr.topic, sr.station_name,
                           f"{sr.valid_windows}/{sr.total_windows}"]
                    for i in range(3):
                        if i < len(peaks_sorted):
                            row.extend([f"{peaks_sorted[i].frequency:.3f}",
                                        f"{peaks_sorted[i].amplitude:.3f}"])
                        else:
                            row.extend(["", ""])
                    writer.writerow(row)
            self._log(f"  table/  -> {csv_path}")

            # Qt-embedded figure saves (must be on main thread)
            self.progress_label.setText("Saving canvas snapshots...")
            fig_path = os.path.join(curves_dir, "HVSR_AllMedians.png")
            self.results_canvas.fig.savefig(fig_path, dpi=300, bbox_inches='tight')
            self._log(f"  curves/ -> {fig_path}")
            hist_path = os.path.join(hist_dir, "HVSR_F0_Histogram.png")
            self.results_histogram.fig.savefig(hist_path, dpi=300, bbox_inches='tight')
            self._log(f"  histogram/ -> {hist_path}")

            # Parallel export of independent operations
            self.progress_label.setText("Generating publication figures & data...")
            n_peaks = self.hvsr_settings.get('auto_npeaks', 3)
            manual_pks = self._manual_median_peaks
            json_hvsr_path = os.path.join(median_dir, "HVSR_Median_Result.json")

            def _export_curve():
                report_export.export_enhanced_curve(
                    curves_dir, checked, fig_settings)
                return "curves/ -> enhanced publication figure"

            def _export_histogram():
                report_export.export_enhanced_histogram(
                    hist_dir, checked, fig_settings)
                return "histogram/ -> enhanced publication figure"

            def _export_median():
                report_export.export_median_data(
                    median_dir, checked, log_fn=self._log)
                return "median/ -> Excel + CSV + JSON + MAT"

            def _export_json():
                report_export.export_median_json_hvsr_format(
                    json_hvsr_path, checked,
                    n_peaks=n_peaks,
                    hvsr_settings=self.hvsr_settings,
                    manual_peaks=manual_pks or None,
                    log_fn=self._log)
                return "median/ -> HVSR_Median_Result.json"

            with ThreadPoolExecutor(max_workers=4) as pool:
                futures = {
                    pool.submit(_export_curve): "enhanced_curve",
                    pool.submit(_export_histogram): "enhanced_hist",
                    pool.submit(_export_median): "median_data",
                    pool.submit(_export_json): "json_hvsr",
                }
                for future in as_completed(futures):
                    try:
                        msg = future.result()
                        self._log(f"  {msg}")
                    except Exception as ex:
                        self._log(f"  Warning: {futures[future]} failed: {ex}")

            self.progress_label.setText("Report generation complete")
            QMessageBox.information(self, "Report Generated",
                f"Report exported to:\n{report_dir}\n\n"
                f"Stations included: {len(checked)}")

        except Exception as e:
            import traceback
            self._log(f"Report error: {e}\n{traceback.format_exc()}")
            QMessageBox.warning(self, "Error", f"Report generation failed:\n{e}")

    # ==================================================================
    #  Tab A - Analysis
    # ==================================================================

    def _build_analysis_tab(self):
        analysis_layout = QVBoxLayout(self._analysis_tab)
        analysis_layout.setContentsMargins(10, 10, 10, 10)

        title = QLabel("Batch HVSR Processing")
        title.setFont(QFont("Arial", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        analysis_layout.addWidget(title)

        # 1. Station Files Section
        input_group = QGroupBox("1. Station Data Files")
        input_layout = QVBoxLayout(input_group)

        self.station_table = QTableWidget(0, 5)
        self.station_table.setHorizontalHeaderLabels(["Station #", "Sensor", "Filename", "Files", "Actions"])
        self.station_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.station_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.station_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Interactive)
        self.station_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.station_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.station_table.setColumnWidth(2, 200)
        self.station_table.setMinimumHeight(120)
        input_layout.addWidget(self.station_table)

        self._station_mgr = StationManager(self.station_table, log_fn=self._log)

        stn_btn_layout = QHBoxLayout()
        btn = QPushButton("Add Station")
        btn.clicked.connect(self._station_mgr.add_station_row)
        stn_btn_layout.addWidget(btn)

        btn = QPushButton("Remove Selected")
        btn.clicked.connect(self._station_mgr.remove_selected_rows)
        stn_btn_layout.addWidget(btn)

        btn = QPushButton("Batch Import")
        btn.clicked.connect(self._station_mgr.batch_import_files)
        btn.setToolTip("Select files and auto-group by station pattern")
        stn_btn_layout.addWidget(btn)

        btn = QPushButton("Sensor Import")
        btn.clicked.connect(self._sensor_aware_import)
        btn.setToolTip("Import files using sensor→station routing")
        stn_btn_layout.addWidget(btn)

        btn = QPushButton("Auto-Detect")
        btn.clicked.connect(self._station_mgr.auto_detect_stations)
        stn_btn_layout.addWidget(btn)

        btn = QPushButton("Clear All")
        btn.clicked.connect(self._station_mgr.clear_all)
        stn_btn_layout.addWidget(btn)

        btn = QPushButton("Sensor Config...")
        btn.setToolTip("Configure sensor file-matching patterns")
        btn.clicked.connect(self._open_sensor_editor)
        stn_btn_layout.addWidget(btn)

        stn_btn_layout.addStretch()
        input_layout.addLayout(stn_btn_layout)

        output_layout = QHBoxLayout()
        output_layout.addWidget(QLabel("Output Directory:"))
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("Select output directory...")
        output_layout.addWidget(self.output_dir_edit)
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_output_dir)
        output_layout.addWidget(browse_btn)
        input_layout.addLayout(output_layout)
        analysis_layout.addWidget(input_group)

        # 2. Time Windows
        time_group = QGroupBox("2. Time Windows (Applied to ALL Stations)")
        time_layout = QHBoxLayout(time_group)
        self.time_windows_btn = QPushButton("Configure Time Windows...")
        self.time_windows_btn.clicked.connect(self._open_time_windows_dialog)
        time_layout.addWidget(self.time_windows_btn)
        self.time_windows_status = QLabel("(No windows configured)")
        self.time_windows_status.setStyleSheet("color: gray; font-style: italic;")
        time_layout.addWidget(self.time_windows_status)
        time_layout.addStretch()
        analysis_layout.addWidget(time_group)

        # 3. HVSR Settings
        hvsr_group = QGroupBox("3. HVSR Settings")
        hvsr_layout = QHBoxLayout(hvsr_group)
        self.hvsr_settings_btn = QPushButton("Configure HVSR Settings...")
        self.hvsr_settings_btn.clicked.connect(self._open_hvsr_settings)
        hvsr_layout.addWidget(self.hvsr_settings_btn)
        self.hvsr_status_label = QLabel("(Using defaults)")
        self.hvsr_status_label.setStyleSheet("color: gray; font-style: italic;")
        hvsr_layout.addWidget(self.hvsr_status_label)
        hvsr_layout.addStretch()
        analysis_layout.addWidget(hvsr_group)

        # 4. Run
        run_group = QGroupBox("4. Run Workflow")
        run_layout = QVBoxLayout(run_group)

        progress_layout = QHBoxLayout()
        progress_layout.addWidget(QLabel("Overall:"))
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)
        run_layout.addLayout(progress_layout)

        self.progress_label = QLabel("Ready")
        run_layout.addWidget(self.progress_label)

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

        self.hvsr_btn = QPushButton("Generate HVSR Curves")
        self.hvsr_btn.setMinimumHeight(35)
        self.hvsr_btn.setFont(QFont("Arial", 11, QFont.Bold))
        self.hvsr_btn.setStyleSheet("background-color: #2196F3; color: white;")
        self.hvsr_btn.clicked.connect(self._run_hvsr)
        self.hvsr_btn.setEnabled(False)
        btn_layout.addWidget(self.hvsr_btn)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._cancel_workflow)
        btn_layout.addWidget(self.cancel_btn)

        run_layout.addLayout(btn_layout)
        analysis_layout.addWidget(run_group)

        # Log
        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout(log_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        log_layout.addWidget(self.log_text)
        analysis_layout.addWidget(log_group)

    # ==================================================================
    #  Dialogs
    # ==================================================================

    def _open_time_windows_dialog(self):
        existing = [{'name': w.get('name', ''), 'start_local': w.get('start_local', ''),
                      'end_local': w.get('end_local', '')}
                     for w in self._time_windows_data.get('windows', [])]

        dialog = TimeWindowsDialog(self, time_windows=existing,
                                   timezone=self._time_windows_data.get('timezone', 'CST'),
                                   station_ids=self._station_mgr.get_existing_station_nums(),
                                   station_assignments=self._time_windows_data.get('station_assignments', {}))
        if dialog.exec_() == QDialog.Accepted:
            result = dialog.get_result()
            self._time_windows_data = result
            n = len(result['windows'])
            if n == 0:
                self.time_windows_status.setText("(No windows configured)")
                self.time_windows_status.setStyleSheet("color: gray;")
            else:
                names = [w['name'] for w in result['windows']][:3]
                self.time_windows_status.setText(f"({n} window(s): {', '.join(names)})")
                self.time_windows_status.setStyleSheet("color: green;")

            assignments = result.get('station_assignments', {})
            n_assigned = sum(len(v) for v in assignments.values())
            if n_assigned > 0:
                self._log(f"Configured {n} time window(s), {n_assigned} station assignments")
            else:
                self._log(f"Configured {n} time window(s) (all stations)")

    def _browse_output_dir(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if folder:
            self.output_dir_edit.setText(folder)

    def _open_sensor_editor(self):
        """Open the Sensor Pattern Editor dialog."""
        from hvsr_pro.packages.batch_processing.dialogs.sensor_pattern_editor import SensorPatternEditor
        if not hasattr(self, '_sensor_manager'):
            from hvsr_pro.packages.batch_processing.sensor_config import SensorConfigManager
            self._sensor_manager = SensorConfigManager.default()

        dlg = SensorPatternEditor(self, manager=self._sensor_manager)
        if dlg.exec_() == dlg.Accepted:
            self._sensor_manager = dlg.get_manager()
            self._log(f"Sensor config updated: {len(self._sensor_manager)} sensors")

    def _sensor_aware_import(self):
        """Import files using sensor-based routing with registry data."""
        if not hasattr(self, '_sensor_manager'):
            from hvsr_pro.packages.batch_processing.sensor_config import SensorConfigManager
            self._sensor_manager = SensorConfigManager.default()

        # Build sensor→station map from project registry if available
        sensor_station_map = {}
        sensor_labels = {}
        ctx = getattr(self, '_project_context', None)
        if ctx:
            project = ctx.get('project')
            if project and project.registry and project.registry.stations:
                sensor_station_map = self._sensor_manager.build_sensor_station_map(
                    project.registry.stations
                )
                # Build labels: station_num → sensor display name
                for stn in project.registry.stations:
                    if stn.sensor is not None:
                        import re
                        m = re.search(r'(\d+)', stn.id)
                        if m:
                            num = int(m.group(1))
                            cfg = self._sensor_manager.get_sensor(str(stn.sensor))
                            sensor_labels[num] = cfg.display_name if cfg else str(stn.sensor)

        if not sensor_station_map:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.information(
                self, "Sensor Import",
                "No sensor→station mapping found.\n\n"
                "Make sure the station registry CSV has a 'sensor' column,\n"
                "or configure sensors via 'Sensor Config...'.\n\n"
                "Using standard batch import instead."
            )
            self._station_mgr.batch_import_files()
            return

        self._station_mgr.sensor_aware_import(
            self._sensor_manager, sensor_station_map, sensor_labels,
        )

    def _init_hvsr_defaults(self):
        from hvsr_pro.packages.batch_processing.dialogs.qc_settings import ALGORITHM_DEFAULTS
        self.hvsr_settings = {
            'freq_min': 0.2, 'freq_max': 30.0,
            'smoothing_type': 'Konno-Ohmachi', 'smoothing_bw': 40,
            'window_length': 120, 'overlap': 0.5,
            'horizontal_method': 'geometric_mean',
            'averaging': 'geo',
            'auto_npeaks': 3, 'peak_font': 10,
            'start_skip': 0, 'process_len': 20,
            'full_duration': False,
            'save_png': True, 'save_pdf': False,
            'max_parallel': min(4, multiprocessing.cpu_count()),
            'auto_mode': False,
            'min_prominence': 0.5, 'min_amplitude': 2.0,
            'n_frequencies': 200,
            'taper': 'tukey',
            'smoothing_method': 'konno_ohmachi',
            'qc_amplitude': True, 'qc_stalta': True,
            'qc_fdwra': True, 'qc_hvsr_amp': False,
            'qc_flat_peak': False, 'qc_curve_outlier': True,
            'qc_statistical': True,
            'qc_params': {
                'amplitude': ALGORITHM_DEFAULTS['amplitude'].copy(),
                'sta_lta': ALGORITHM_DEFAULTS['sta_lta'].copy(),
                'fdwra': ALGORITHM_DEFAULTS['fdwra'].copy(),
                'hvsr_amplitude': ALGORITHM_DEFAULTS['hvsr_amplitude'].copy(),
                'flat_peak': ALGORITHM_DEFAULTS['flat_peak'].copy(),
                'statistical_outlier': ALGORITHM_DEFAULTS['statistical_outlier'].copy(),
            },
        }

    def _open_hvsr_settings(self):
        dialog = HVSRSettingsDialog(self)
        dialog.set_settings(self.hvsr_settings)
        dialog.set_time_windows(self._time_windows_data.get('windows', []))
        if dialog.exec_() == QDialog.Accepted:
            self.hvsr_settings = dialog.get_settings()
            self.hvsr_status_label.setText("(Custom settings applied)")
            self.hvsr_status_label.setStyleSheet("color: green;")
            self._log("HVSR settings updated")

    # ==================================================================
    #  Logging
    # ==================================================================

    def _log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")
        self.log_text.ensureCursorVisible()
        self.statusBar().showMessage(message)

    # ==================================================================
    #  Workflow Execution
    # ==================================================================

    def _validate_inputs(self):
        errors = []
        station_files = self._station_mgr.get_station_files()
        if not station_files:
            errors.append("No station files configured")
        if not self.output_dir_edit.text().strip():
            errors.append("No output directory selected")
        return errors

    def _run_workflow(self):
        """Run data processing step."""
        errors = self._validate_inputs()
        if errors:
            QMessageBox.warning(self, "Validation Error", "\n".join(errors))
            return

        time_windows = self._time_windows_data.get('windows', [])
        primary_window = None
        if time_windows:
            win = time_windows[0]
            primary_window = {'start': win['start_utc'], 'end': win['end_utc'], 'name': win['name']}

        params = {
            'station_files': self._station_mgr.get_station_files(),
            'output_dir': self.output_dir_edit.text(),
            'time_window': primary_window,
            'time_windows': time_windows,
            'station_assignments': self._time_windows_data.get('station_assignments', {}),
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

    def _run_hvsr(self):
        """Run HVSR processing using HVSRProcessor directly."""
        if not self.processed_results:
            QMessageBox.warning(self, "No Data", "Run data processing first.")
            return

        # Build task list
        tasks = []
        self.hvsr_task_status.clear()

        for result in self.processed_results:
            station_name = result['station_name']
            window_name = result.get('window_name', '')
            mat_path = result['mat_path']
            out_dir = result['dir']

            task_label = f"{window_name}/{station_name}" if window_name else station_name

            tasks.append(BatchTask(
                station_id=station_name,
                window_name=window_name,
                mat_path=str(mat_path),
                output_dir=str(out_dir),
                label=task_label
            ))
            self.hvsr_task_status[task_label] = 0

        self._update_task_status_display()

        # Build QC settings for the worker
        _qc_p = self.hvsr_settings.get('qc_params', {})
        qc_settings = {
            'qc_stalta': self.hvsr_settings.get('qc_stalta', True),
            'qc_amplitude': self.hvsr_settings.get('qc_amplitude', True),
            'qc_fdwra': self.hvsr_settings.get('qc_fdwra', True),
            'qc_statistical': self.hvsr_settings.get('qc_statistical', False),
            'qc_hvsr_amp': self.hvsr_settings.get('qc_hvsr_amp', False),
            'qc_flat_peak': self.hvsr_settings.get('qc_flat_peak', False),
            'qc_curve_outlier': self.hvsr_settings.get('qc_curve_outlier', True),
            'sta_lta_params': _qc_p.get('sta_lta', {}),
            'amplitude_params': _qc_p.get('amplitude', {}),
            'fdwra_params': _qc_p.get('fdwra', {}),
            'statistical_params': _qc_p.get('statistical_outlier', {}),
            'hvsr_amplitude_params': _qc_p.get('hvsr_amplitude', {}),
            'flat_peak_params': _qc_p.get('flat_peak', {}),
            'curve_outlier_params': _qc_p.get('curve_outlier', {}),
        }

        worker_settings = {
            'window_length': self.hvsr_settings.get('window_length', 120),
            'overlap': self.hvsr_settings.get('overlap', 0.5),
            'konno_ohmachi_bandwidth': self.hvsr_settings.get('smoothing_bw', 40),
            'smoothing_method': self.hvsr_settings.get('smoothing_method', 'konno_ohmachi'),
            'freq_min': self.hvsr_settings.get('freq_min', 0.2),
            'freq_max': self.hvsr_settings.get('freq_max', 30.0),
            'n_frequencies': self.hvsr_settings.get('n_frequencies', 300),
            'horizontal_method': self.hvsr_settings.get('horizontal_method', 'geometric_mean'),
            'taper': self.hvsr_settings.get('taper', 'tukey'),
            'detrend': self.hvsr_settings.get('detrend', 'linear'),
            'statistics_method': self.hvsr_settings.get('statistics_method', 'lognormal'),
            'std_ddof': self.hvsr_settings.get('std_ddof', 1),
            'min_prominence': self.hvsr_settings.get('min_prominence', 0.5),
            'min_amplitude': self.hvsr_settings.get('min_amplitude', 2.0),
            'peak_basis': self.hvsr_settings.get('peak_basis', 'median'),
            'auto_npeaks': self.hvsr_settings.get('auto_npeaks', 3),
            'qc_settings': qc_settings,
            'save_png': self.hvsr_settings.get('save_png', True),
            'save_pdf': self.hvsr_settings.get('save_pdf', False),
            'auto_fig_dpi': self.hvsr_settings.get('auto_fig_dpi', 300),
            'auto_fig_standard': self.hvsr_settings.get('auto_fig_standard', True),
            'auto_fig_hvsr_pro': self.hvsr_settings.get('auto_fig_hvsr_pro', True),
            'auto_fig_statistics': self.hvsr_settings.get('auto_fig_statistics', True),
            'figure_export_config': self.hvsr_settings.get('figure_export_config', {}),
        }

        self._log(f"Starting HVSR processing for {len(tasks)} tasks...")
        self.run_btn.setEnabled(False)
        self.hvsr_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setValue(0)

        self.hvsr_worker = BatchHVSRWorker(tasks, worker_settings, self)
        self.hvsr_worker.log_line.connect(self._log)
        self.hvsr_worker.progress.connect(self._on_hvsr_progress)
        self.hvsr_worker.task_progress.connect(self._on_task_progress)
        self.hvsr_worker.finished.connect(self._on_hvsr_finished)
        self.hvsr_worker.start()

    # ==================================================================
    #  Progress & Callbacks
    # ==================================================================

    def _update_task_status_display(self):
        if not self.hvsr_task_status:
            self.task_status_label.setText("")
            return
        parts = []
        for stn, pct in sorted(self.hvsr_task_status.items()):
            if pct == 100:
                parts.append(f"{stn}: Done")
            elif pct == -1:
                parts.append(f"{stn}: Error")
            elif pct > 0:
                parts.append(f"{stn}: {pct}%")
            else:
                parts.append(f"{stn}: Waiting")
        self.task_status_label.setText(" | ".join(parts))

    def _on_task_progress(self, name, pct):
        self.hvsr_task_status[name] = pct
        self._update_task_status_display()

    def _on_hvsr_progress(self, pct, message):
        self.progress_bar.setValue(pct)
        self.progress_label.setText(message)

    def _on_hvsr_finished(self, success, message):
        self.run_btn.setEnabled(True)
        self.hvsr_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self._log(message)
        self.progress_label.setText(message)

        if success:
            auto_mode = self.hvsr_settings.get('auto_mode', False)
            if not auto_mode and self.hvsr_worker and self.hvsr_worker.station_results:
                self._run_interactive_peak_picking()
            elif PROCESSING_AVAILABLE:
                self._run_automatic_analysis()
            else:
                QMessageBox.information(self, "Complete", message)
        else:
            QMessageBox.warning(self, "Status", message)

    def _run_automatic_analysis(self):
        """Load results and populate the Results tab.

        When ``auto_mode`` is enabled the function runs automatic peak
        detection, exports results immediately, and populates the
        Results tab with peaks already placed on the canvas.

        When ``auto_mode`` is disabled (interactive / manual mode) the
        Results tab is populated *without* peaks so the user can click
        on the canvas to pick them manually and then generate a report.
        """
        if not PROCESSING_AVAILABLE:
            return

        auto_mode = self.hvsr_settings.get('auto_mode', False)

        self._log("Loading results and detecting peaks...")
        try:
            self.progress_label.setText("Loading HVSR results...")
            self.progress_bar.setValue(50)

            station_results = results_handler.load_hvsr_results(
                self.processed_results, self.hvsr_settings, log_fn=self._log)

            if not station_results:
                self._log("No results found")
                self.progress_bar.setValue(0)
                return

            self.progress_label.setText("Running peak detection...")
            self.progress_bar.setValue(70)

            result = results_handler.run_analysis(
                station_results, self.hvsr_settings, log_fn=self._log)

            self.progress_label.setText("Populating results tab...")
            self.progress_bar.setValue(90)

            if auto_mode:
                results_handler.display_peak_statistics(
                    result, log_fn=self._log)
                output_dir = self.output_dir_edit.text()
                if output_dir:
                    results_handler.export_automatic_results(
                        result, output_dir, self.hvsr_settings,
                        log_fn=self._log)
                    # Auto-export enhanced figures
                    try:
                        checked = result.station_results
                        report_dir = os.path.join(output_dir, "Report")
                        curves_dir = os.path.join(report_dir, "curves")
                        hist_dir = os.path.join(report_dir, "histogram")
                        os.makedirs(curves_dir, exist_ok=True)
                        os.makedirs(hist_dir, exist_ok=True)
                        report_export.export_enhanced_curve(
                            curves_dir, checked, log_fn=self._log)
                        report_export.export_enhanced_histogram(
                            hist_dir, checked, log_fn=self._log)
                        self._log("Auto-export: enhanced figures saved")
                    except Exception as fig_err:
                        self._log(f"Auto-export figures warning: {fig_err}")

            self._populate_results_tab(result)

            if auto_mode:
                self.progress_label.setText(
                    "Analysis complete - see Results tab")
            else:
                self.progress_label.setText(
                    "Pick peaks on the canvas, then click 'Generate Report'")
                self._log(
                    "Interactive mode: pick peaks on the canvas and click "
                    "'Generate Report' when ready.")
                if hasattr(self, 'results_canvas'):
                    self.results_canvas.btn_pick_peaks.setChecked(True)

        except Exception as e:
            import traceback
            self._log(f"Analysis error: {e}\n{traceback.format_exc()}")

    def _run_interactive_peak_picking(self):
        """Open interactive peak-picking dialog for each station."""
        from hvsr_pro.packages.batch_processing.dialogs.interactive_peak_dialog import (
            InteractivePeakDialog)

        station_results = self.hvsr_worker.station_results
        self._log(f"Interactive mode: {len(station_results)} stations to review")

        for i, sdata in enumerate(station_results):
            fig_label = sdata['fig_label']
            self._log(f"\n--- Interactive: {fig_label} ({i+1}/{len(station_results)}) ---")
            self.progress_label.setText(
                f"Interactive: {fig_label} ({i+1}/{len(station_results)})")

            rs = sdata['rs']
            dialog = InteractivePeakDialog(
                freq_ref=sdata['freq_rs'],
                combined_hv=sdata['combined_hv'],
                rejected_mask=sdata['rejected_mask'],
                hv_median=rs['median_hvsr'],
                hv_mean=rs['mean_hvsr'],
                hv_std=rs['std_hvsr'],
                fig_label=fig_label,
                settings=self.hvsr_settings,
                parent=self,
            )

            if dialog.exec_() == QDialog.Accepted:
                picked_peaks = dialog.get_peaks()
                if picked_peaks:
                    self._log(f"  Accepted {len(picked_peaks)} peaks for {fig_label}")
                    # Update result with user-picked peaks and regenerate figures
                    self._apply_interactive_peaks(sdata, picked_peaks)
                else:
                    self._log(f"  No peaks selected for {fig_label}")
            else:
                self._log(f"  Skipped {fig_label}")

        self.progress_label.setText("Interactive peak picking complete")
        self._log("Interactive peak picking complete for all stations")
        if PROCESSING_AVAILABLE:
            self._run_automatic_analysis()

    def _apply_interactive_peaks(self, sdata, picked_peaks):
        """Apply user-picked peaks and regenerate figures for a station."""
        from hvsr_pro.processing.hvsr.structures import Peak
        from hvsr_pro.packages.batch_processing.figure_gen import generate_hvsr_figures

        result = sdata['result']
        rs = sdata['rs']
        freq_rs = sdata['freq_rs']
        fig_label = sdata['fig_label']
        out_dir = sdata['out_dir']

        # Convert picked peaks to Peak objects
        new_peaks = []
        for freq, amp in picked_peaks:
            new_peaks.append(Peak(frequency=freq, amplitude=amp, prominence=0.0))

        # Update result peaks
        result.peaks = new_peaks

        # Save updated peaks to disk so load_hvsr_results can find them
        try:
            json_path = os.path.join(out_dir, f"HVSR_{fig_label}_result.json")
            if os.path.exists(json_path):
                result.save(json_path)
                self._log(f"  Saved updated peaks to {json_path}")
        except Exception as e:
            self._log(f"  Warning: could not save peaks to disk: {e}")

        # Regenerate figures with user-picked peaks
        combined_hv = sdata['combined_hv']
        rejected_mask = sdata['rejected_mask']
        accepted_indices = [i for i in range(combined_hv.shape[1])
                           if not rejected_mask[i]]

        hv_mean = rs['mean_hvsr']
        hv_std = rs['std_hvsr']

        try:
            n_saved = generate_hvsr_figures(
                hvsr_result_obj=result,
                window_collection=sdata['windows'],
                seismic_data=sdata['data'],
                peaks=new_peaks,
                freq_ref=freq_rs,
                hv_mean=hv_mean,
                hv_std=hv_std,
                hv_mean_plus_std=hv_mean + hv_std,
                hv_mean_minus_std=np.maximum(hv_mean - hv_std, 0),
                hv_16=rs['percentile_16'],
                hv_84=rs['percentile_84'],
                combined_hv=combined_hv,
                rejected_mask=rejected_mask,
                accepted_indices=accepted_indices,
                n_windows=combined_hv.shape[1],
                output_dir=out_dir,
                fig_label=fig_label,
                fig_title=f'HVSR - {fig_label}',
                fig_config=self.hvsr_settings.get('figure_export_config', {}),
                fig_standard=self.hvsr_settings.get('auto_fig_standard', True),
                fig_hvsr_pro=self.hvsr_settings.get('auto_fig_hvsr_pro', True),
                fig_statistics=self.hvsr_settings.get('auto_fig_statistics', True),
                save_png=self.hvsr_settings.get('save_png', True),
                save_pdf=self.hvsr_settings.get('save_pdf', False),
                dpi=self.hvsr_settings.get('auto_fig_dpi', 300),
            )
            self._log(f"  Regenerated {n_saved} figures with user-picked peaks")
        except Exception as e:
            self._log(f"  Figure regeneration failed: {e}")

    def _cancel_workflow(self):
        if self.data_worker and self.data_worker.isRunning():
            self.data_worker.terminate()
            self._log("Data processing cancelled")
            self._on_data_finished(False, "Cancelled")
        if self.hvsr_worker and self.hvsr_worker.isRunning():
            self.hvsr_worker.stop()
            self._log("HVSR cancellation requested...")

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
                n = len(self.processed_results)
                self._log(f"Ready to generate HVSR for {n} station/window combinations")
                QMessageBox.information(self, "Success",
                    f"{message}\n\nClick 'Generate HVSR Curves' to process.")
            else:
                QMessageBox.information(self, "Success", message)
        else:
            self.progress_label.setText("Processing failed!")
            self._log(f"Failed: {message}")
            QMessageBox.warning(self, "Error", message)
