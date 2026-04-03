"""
Data Process Worker
====================

Background QThread that processes seismic data into ArrayData.mat files
for each (TimeWindow × Station) combination.

Supports:
- MiniSEED via ObsPy (default, with time-window trimming)
- All other formats via hvsr_pro loaders (SAF, SAC, GCF, PEER, etc.)
"""

from PyQt5.QtCore import QThread, pyqtSignal
import numpy as np
import os


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
        """Execute the data processing workflow - creates ArrayData.mat for each (TimeWindow × Station).

        Delegates to the headless API (data_engine) for actual processing,
        keeping QThread signal infrastructure for GUI progress.
        """
        params = self.params
        self.progress.emit(5, "Parsing parameters...")

        station_files = params['station_files']  # Dict: {station_id: [file_list]}
        output_dir = params['output_dir']
        time_windows = params.get('time_windows', [])
        station_assignments = params.get('station_assignments', {})

        if not station_files:
            self.finished.emit(False, "No station files selected!")
            return

        os.makedirs(output_dir, exist_ok=True)

        # ── Convert to API objects ──
        from hvsr_pro.packages.batch_processing.api.config import (
            StationDef, TimeWindowDef,
        )
        from hvsr_pro.packages.batch_processing.api.data_engine import (
            prepare_station_data,
        )

        stations = []
        for stn_id, files in sorted(station_files.items()):
            stations.append(StationDef(
                station_num=int(stn_id) if isinstance(stn_id, (int, float)) else stn_id,
                station_name=f"STN{int(stn_id):02d}" if isinstance(stn_id, (int, float)) else str(stn_id),
                files=list(files),
            ))

        api_windows = []
        for tw in time_windows:
            api_windows.append(TimeWindowDef(
                name=tw.get('name', 'Window'),
                start_utc=tw.get('start_utc', ''),
                end_utc=tw.get('end_utc', ''),
            ))

        # Convert station_assignments: {window_name: [station_nums]}
        api_assignments = {}
        for wname, stn_list in station_assignments.items():
            api_assignments[wname] = [
                int(s) if isinstance(s, (int, float)) else s
                for s in stn_list
            ]

        self.progress.emit(10, "Starting data processing via API...")

        # ── Call API ──
        try:
            data_results = prepare_station_data(
                stations=stations,
                time_windows=api_windows,
                output_dir=output_dir,
                station_assignments=api_assignments,
                progress_callback=lambda pct, msg: self.progress.emit(pct, msg),
            )
        except Exception as e:
            self.finished.emit(False, f"Data processing failed: {e}")
            return

        # ── Convert back to legacy result format ──
        results = []
        for dr in data_results:
            if dr.success:
                results.append({
                    'station_id': dr.station_id,
                    'station_name': dr.station_name,
                    'window_name': dr.window_name,
                    'dir': dr.output_dir,
                    'mat_path': dr.mat_path,
                    'fs': dr.sampling_rate,
                    'data_length_sec': dr.data_length_seconds,
                })

        if not results:
            self.finished.emit(False, "No data files were created successfully!")
            return

        self.progress.emit(95, "Finalizing...")
        self.params['results'] = results
        self.progress.emit(100, "Data processing complete!")

        # Summary message
        unique_windows = set(r['window_name'] for r in results)
        unique_stations = set(r['station_name'] for r in results)
        self.finished.emit(True,
            f"Data processing complete.\n"
            f"Created {len(results)} ArrayData files:\n"
            f"  • {len(unique_windows)} time window(s): {', '.join(sorted(unique_windows))}\n"
            f"  • {len(unique_stations)} station(s): {', '.join(sorted(unique_stations))}")

    # ------------------------------------------------------------------
    #  Format detection
    # ------------------------------------------------------------------

    @staticmethod
    def _all_files_are_miniseed(station_files: dict) -> bool:
        """Check if ALL station files are MiniSEED format."""
        from hvsr_pro.packages.batch_processing.data_adapter import is_miniseed
        for files in station_files.values():
            for f in files:
                if not is_miniseed(f):
                    return False
        return True

    # ------------------------------------------------------------------
    #  Full-duration path (no time windows — use entire file)
    # ------------------------------------------------------------------

    def _process_full_duration(self, station_files, output_dir, all_miniseed):
        """Process all station data using the full file duration (no time-window trimming).

        Creates a single synthetic window named 'FullDuration' and saves
        the complete recording for each station.
        """
        total_stations = len(station_files)
        self.progress.emit(8, f"Processing {total_stations} station(s) — full duration (no time windows)")

        results = []
        win_name = "FullDuration"

        if all_miniseed:
            from obspy import read, Stream

            self.progress.emit(10, "Loading MiniSEED station data (full duration)...")

            for idx, (stn_id, files) in enumerate(sorted(station_files.items())):
                progress_pct = 15 + int(80 * (idx + 1) / max(1, total_stations))
                station_name = f"STN{stn_id:02d}"
                self.progress.emit(progress_pct, f"  {station_name}...")

                combined_stream = Stream()
                fs_detected = None

                for f in files:
                    try:
                        st = read(f)
                        combined_stream += st
                        if fs_detected is None and len(st) > 0:
                            fs_detected = st[0].stats.sampling_rate
                    except Exception as e:
                        self.progress.emit(progress_pct, f"Warning: Could not read {os.path.basename(f)}: {e}")

                if len(combined_stream) == 0:
                    self.progress.emit(progress_pct, f"Warning: No readable files for Station #{stn_id}")
                    continue

                try:
                    combined_stream.merge(method=1, fill_value=0)
                except Exception as e:
                    self.progress.emit(progress_pct, f"Warning: Merge issue for Station #{stn_id}: {e}")

                fs = fs_detected or 200.0
                Array1Z, Array1N, Array1E = [], [], []

                for tr in combined_stream:
                    comp = tr.stats.channel[-1].upper() if tr.stats.channel else 'Z'
                    if len(tr.data) > 0:
                        if comp == 'Z':
                            Array1Z.append(tr.data.astype(np.float64))
                        elif comp in ('N', '1'):
                            Array1N.append(tr.data.astype(np.float64))
                        elif comp in ('E', '2'):
                            Array1E.append(tr.data.astype(np.float64))

                Array1Z = np.concatenate(Array1Z) if len(Array1Z) > 1 else (Array1Z[0] if Array1Z else np.array([]))
                Array1N = np.concatenate(Array1N) if len(Array1N) > 1 else (Array1N[0] if Array1N else np.array([]))
                Array1E = np.concatenate(Array1E) if len(Array1E) > 1 else (Array1E[0] if Array1E else np.array([]))

                if len(Array1Z) == 0 and len(Array1N) == 0 and len(Array1E) == 0:
                    self.progress.emit(progress_pct, f"  Warning: No component data for {station_name}")
                    continue

                result_entry = self._save_arrays(
                    Array1Z, Array1N, Array1E, fs, stn_id, station_name,
                    win_name, output_dir, progress_pct)
                if result_entry:
                    results.append(result_entry)

        else:
            # Generic formats via hvsr_pro loaders
            from hvsr_pro.packages.batch_processing.data_adapter import load_and_convert, is_available, get_format_name

            if not is_available():
                self.finished.emit(False,
                    "Non-MiniSEED files detected but hvsr_pro loaders are not available.\n"
                    "Please ensure hvsr_pro is installed or use MiniSEED files.")
                return None

            first_file = next(iter(next(iter(station_files.values()))))
            fmt_name = get_format_name(first_file)
            self.progress.emit(10, f"Loading station data — full duration ({fmt_name})...")

            for idx, (stn_id, files) in enumerate(sorted(station_files.items())):
                progress_pct = 15 + int(80 * (idx + 1) / max(1, total_stations))
                station_name = f"STN{stn_id:02d}"
                self.progress.emit(progress_pct, f"  {station_name}...")

                try:
                    z, n, e, fs = load_and_convert(files[0])
                    duration_sec = len(z) / fs if len(z) > 0 else 0
                    self.progress.emit(progress_pct,
                        f"  {station_name}: {duration_sec:.1f}s loaded ({fmt_name})")
                except Exception as exc:
                    self.progress.emit(progress_pct, f"Warning: Could not load {station_name}: {exc}")
                    continue

                result_entry = self._save_arrays(
                    z, n, e, fs, stn_id, station_name,
                    win_name, output_dir, progress_pct)
                if result_entry:
                    results.append(result_entry)

        if not results:
            self.finished.emit(False, "No station data could be loaded.")
            return None

        return results

    # ------------------------------------------------------------------
    #  MiniSEED path (ObsPy — supports time-window trimming)
    # ------------------------------------------------------------------

    def _process_miniseed(self, station_files, time_windows, output_dir):
        """Process MiniSEED files using ObsPy with time-window trimming."""
        from obspy import read, UTCDateTime, Stream
        from scipy.io import savemat

        total_windows = len(time_windows)
        total_stations = len(station_files)

        results = []

        # Read all station data once
        self.progress.emit(10, "Loading MiniSEED station data...")
        station_streams = {}

        for stn_id, files in sorted(station_files.items()):
            combined_stream = Stream()
            fs_detected = None

            for f in files:
                try:
                    st = read(f)
                    combined_stream += st
                    if fs_detected is None and len(st) > 0:
                        fs_detected = st[0].stats.sampling_rate
                except Exception as e:
                    self.progress.emit(10, f"Warning: Could not read {os.path.basename(f)}: {e}")

            if len(combined_stream) == 0:
                self.progress.emit(10, f"Warning: No readable files for Station #{stn_id}")
                continue

            data_start = min(tr.stats.starttime for tr in combined_stream)
            data_end = max(tr.stats.endtime for tr in combined_stream)
            self.progress.emit(10, f"Station #{stn_id} data range: {data_start} to {data_end}")

            try:
                combined_stream.merge(method=1, fill_value=0)
            except Exception as e:
                self.progress.emit(10, f"Warning: Merge issue for Station #{stn_id}: {e}")

            station_streams[stn_id] = (combined_stream, fs_detected or 200.0, data_start, data_end)

        # Build per-station time window assignments
        station_assignments = self.params.get('station_assignments', {})
        # station_assignments maps config_name → [station_ids]
        # Build reverse: station_id → set of window_indices
        stn_to_windows = {}
        if station_assignments:
            for win_idx, window in enumerate(time_windows):
                win_name = window.get('name', f'Window_{win_idx+1}')
                assigned_stns = station_assignments.get(win_name, [])
                for stn_id in assigned_stns:
                    stn_to_windows.setdefault(stn_id, set()).add(win_idx)

        # Count total tasks for progress
        if stn_to_windows:
            total_tasks = sum(
                len(wins) for stn_id, wins in stn_to_windows.items()
                if stn_id in station_streams
            )
            if total_tasks == 0:
                total_tasks = 1
        else:
            total_tasks = total_windows * total_stations

        self.progress.emit(8, f"Processing {total_tasks} tasks [MiniSEED]")

        # Process each time window × station combination
        task_idx = 0
        for win_idx, window in enumerate(time_windows):
            win_name = window.get('name', f'Window_{win_idx+1}')
            start_utc = UTCDateTime(window['start_utc'])
            end_utc = UTCDateTime(window['end_utc'])

            self.progress.emit(15 + int(80 * task_idx / max(1, total_tasks)),
                              f"Processing window '{win_name}' ({win_idx+1}/{total_windows})...")

            win_dir = os.path.join(output_dir, win_name)
            os.makedirs(win_dir, exist_ok=True)

            for stn_id, (stream_orig, fs, data_start, data_end) in station_streams.items():
                # Skip this station if per-station assignments exist and
                # this station is NOT assigned to this window
                if stn_to_windows and win_idx not in stn_to_windows.get(stn_id, set()):
                    continue

                task_idx += 1
                progress_pct = 15 + int(80 * task_idx / max(1, total_tasks))

                station_name = f"STN{stn_id:02d}"
                self.progress.emit(progress_pct, f"  {win_name}/{station_name}...")

                stream_copy = stream_orig.copy()
                stream_copy.trim(starttime=start_utc, endtime=end_utc)

                if len(stream_copy) == 0 or all(len(tr.data) == 0 for tr in stream_copy):
                    self.progress.emit(progress_pct, f"  Warning: No data for {win_name}/{station_name}")
                    self.progress.emit(progress_pct, f"    Requested: {start_utc} to {end_utc}")
                    self.progress.emit(progress_pct, f"    Available: {data_start} to {data_end}")
                    continue

                Array1Z, Array1N, Array1E = [], [], []

                for tr in stream_copy:
                    comp = tr.stats.channel[-1].upper() if tr.stats.channel else 'Z'
                    if len(tr.data) > 0:
                        if comp == 'Z':
                            Array1Z.append(tr.data.astype(np.float64))
                        elif comp in ('N', '1'):
                            Array1N.append(tr.data.astype(np.float64))
                        elif comp in ('E', '2'):
                            Array1E.append(tr.data.astype(np.float64))

                Array1Z = np.concatenate(Array1Z) if len(Array1Z) > 1 else (Array1Z[0] if Array1Z else np.array([]))
                Array1N = np.concatenate(Array1N) if len(Array1N) > 1 else (Array1N[0] if Array1N else np.array([]))
                Array1E = np.concatenate(Array1E) if len(Array1E) > 1 else (Array1E[0] if Array1E else np.array([]))

                if len(Array1Z) == 0 and len(Array1N) == 0 and len(Array1E) == 0:
                    self.progress.emit(progress_pct, f"  Warning: No component data for {win_name}/{station_name}")
                    continue

                result_entry = self._save_arrays(
                    Array1Z, Array1N, Array1E, fs, stn_id, station_name,
                    win_name, output_dir, progress_pct)
                if result_entry:
                    results.append(result_entry)

        return results

    # ------------------------------------------------------------------
    #  Generic path (hvsr_pro loaders — SAF, SAC, GCF, PEER, etc.)
    # ------------------------------------------------------------------

    def _process_generic(self, station_files, time_windows, output_dir):
        """Process non-MiniSEED files using hvsr_pro loaders via data_adapter.

        For non-MiniSEED formats, each file is loaded as a complete
        three-component record. Time-window trimming is done by sample
        index rather than ObsPy UTCDateTime.
        """
        from hvsr_pro.packages.batch_processing.data_adapter import load_and_convert, is_available, get_format_name

        if not is_available():
            self.finished.emit(False,
                "Non-MiniSEED files detected but hvsr_pro loaders are not available.\n"
                "Please ensure hvsr_pro is installed or use MiniSEED files.")
            return None

        total_windows = len(time_windows)
        total_stations = len(station_files)
        total_tasks = total_windows * total_stations

        # Detect format of first file for logging
        first_file = next(iter(next(iter(station_files.values()))))
        fmt_name = get_format_name(first_file)
        self.progress.emit(8, f"Processing {total_windows} window(s) × {total_stations} station(s) = {total_tasks} tasks [{fmt_name}]")

        results = []

        # Load all station data once
        self.progress.emit(10, f"Loading station data ({fmt_name} format)...")
        station_data = {}  # {stn_id: (Z, N, E, fs)}

        for stn_id, files in sorted(station_files.items()):
            station_name = f"STN{stn_id:02d}"
            try:
                z, n, e, fs = load_and_convert(files[0])
                station_data[stn_id] = (z, n, e, fs)
                duration_sec = len(z) / fs if len(z) > 0 else 0
                self.progress.emit(10, f"Station #{stn_id}: {duration_sec:.1f}s of data loaded ({fmt_name})")
            except Exception as exc:
                self.progress.emit(10, f"Warning: Could not load {station_name}: {exc}")

        if not station_data:
            self.finished.emit(False, "No station data could be loaded.")
            return None

        # Process each time window × station
        task_idx = 0
        for win_idx, window in enumerate(time_windows):
            win_name = window.get('name', f'Window_{win_idx+1}')
            self.progress.emit(15 + int(80 * task_idx / max(1, total_tasks)),
                              f"Processing window '{win_name}' ({win_idx+1}/{total_windows})...")

            for stn_id, (z, n, e, fs) in station_data.items():
                task_idx += 1
                progress_pct = 15 + int(80 * task_idx / max(1, total_tasks))
                station_name = f"STN{stn_id:02d}"
                self.progress.emit(progress_pct, f"  {win_name}/{station_name}...")

                result_entry = self._save_arrays(
                    z, n, e, fs, stn_id, station_name,
                    win_name, output_dir, progress_pct)
                if result_entry:
                    results.append(result_entry)

        return results

    # ------------------------------------------------------------------
    #  Shared: save Z/N/E arrays to MAT
    # ------------------------------------------------------------------

    def _save_arrays(self, Array1Z, Array1N, Array1E, fs,
                     stn_id, station_name, win_name, output_dir, progress_pct):
        """Save component arrays to ArrayData.mat and return result dict."""
        from scipy.io import savemat

        win_dir = os.path.join(output_dir, win_name)
        stn_dir = os.path.join(win_dir, station_name)
        os.makedirs(stn_dir, exist_ok=True)

        mat_dict = {
            'Array1Z': Array1Z,
            'Array1N': Array1N,
            'Array1E': Array1E,
            'Fs_Hz': fs,
        }

        mat_path = os.path.join(stn_dir, f"ArrayData_{station_name}.mat")
        savemat(mat_path, mat_dict)

        data_len_sec = len(Array1Z) / fs if len(Array1Z) > 0 else 0
        self.progress.emit(progress_pct, f"  {win_name}/{station_name}: {data_len_sec:.1f}s of data")

        return {
            'station_id': stn_id,
            'station_name': station_name,
            'window_name': win_name,
            'dir': stn_dir,
            'mat_path': mat_path,
            'fs': fs,
            'data_length_sec': data_len_sec,
        }
