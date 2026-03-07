"""
Batch HVSR Worker
=================

Replaces the subprocess-based ParallelHVSRManager with direct
in-process HVSRProcessor calls from hvsr_pro.

Processes multiple (station, time_window) combinations using
hvsr_pro's WindowManager, RejectionEngine, and HVSRProcessor.

Output files per station (matches HVSR_old format):
  - HVSR_{station}_{window}_result.json   (full result JSON)
  - HVSR_Median_{tw}Sec_{label}.mat       (statistical arrays)
  - Peaks_{label}.mat                      (peak freq/amp/width)
  - Peaks_{label}.csv                      (peak table)
  - HVSR_{label}_median_data.csv           (freq, median, std, p16, p84)
  - HVSR_{label}.png / .pdf               (figure, optional)
"""

import csv
import os
import json
import logging
import traceback
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

import numpy as np

try:
    from PyQt5.QtCore import QThread, pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False

    class QThread:
        pass

    class pyqtSignal:
        def __init__(self, *args):
            pass

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

from dataclasses import dataclass


@dataclass
class BatchTask:
    """A single HVSR processing task."""
    station_id: str
    window_name: str
    mat_path: str
    output_dir: str
    label: str = ""


# ---------------------------------------------------------------------------
# Resampling helper
# ---------------------------------------------------------------------------

def _resample_to_log_grid(
    freq_in: np.ndarray,
    arrays: Dict[str, np.ndarray],
    f_min: float,
    f_max: float,
    n_points: int = 300,
) -> tuple:
    """Resample arrays onto a common log-spaced frequency grid.

    Returns (freq_out, resampled_dict) where resampled_dict has the same
    keys as *arrays* but with interpolated values.
    """
    freq_out = np.logspace(np.log10(max(f_min, freq_in[0])),
                           np.log10(min(f_max, freq_in[-1])),
                           n_points)
    resampled = {}
    for key, arr in arrays.items():
        if arr is not None and len(arr) == len(freq_in):
            resampled[key] = np.interp(freq_out, freq_in, arr)
        else:
            resampled[key] = arr
    return freq_out, resampled


# ---------------------------------------------------------------------------
# Worker
# ---------------------------------------------------------------------------

class BatchHVSRWorker(QThread):
    """
    Background worker for batch HVSR processing.

    Uses hvsr_pro's HVSRProcessor directly instead of subprocesses.
    Processes each (station, time_window) task sequentially, with
    progress signals for the UI.
    """

    log_line = pyqtSignal(str)
    progress = pyqtSignal(int, str)
    task_progress = pyqtSignal(str, int)
    finished = pyqtSignal(bool, str)
    # Emits per-station data for interactive mode: (task_label, data_dict)
    station_data_ready = pyqtSignal(str, object)

    def __init__(self, tasks: List[BatchTask], hvsr_settings: Dict[str, Any],
                 parent=None):
        super().__init__(parent)
        self.tasks = tasks
        self.hvsr_settings = hvsr_settings
        self._stop_requested = False
        self.station_results = []  # stores intermediate data for interactive mode

    def stop(self):
        self._stop_requested = True

    # ------------------------------------------------------------------
    #  Main loop
    # ------------------------------------------------------------------

    def run(self):
        try:
            total_tasks = len(self.tasks)
            completed = 0
            failed = 0

            self.log_line.emit(f"Starting batch HVSR processing: {total_tasks} tasks")
            self.progress.emit(0, f"Processing 0/{total_tasks}")

            for i, task in enumerate(self.tasks):
                if self._stop_requested:
                    self.log_line.emit("Processing cancelled by user")
                    self.finished.emit(False, "Cancelled")
                    return

                task_label = f"{task.station_id} / {task.window_name}"
                self.log_line.emit(f"\n--- Task {i+1}/{total_tasks}: {task_label} ---")
                self.task_progress.emit(task_label, 0)

                try:
                    self._process_single_task(task)
                    completed += 1
                    self.log_line.emit(f"  Completed: {task_label}")
                except Exception as e:
                    failed += 1
                    self.log_line.emit(f"  FAILED: {task_label}: {e}")
                    logger.error(f"Task {task_label} failed:\n{traceback.format_exc()}")

                pct = int((i + 1) / total_tasks * 100)
                self.progress.emit(pct, f"Processing {i+1}/{total_tasks}")
                self.task_progress.emit(task_label, 100)

            msg = f"Completed: {completed}/{total_tasks} tasks"
            if failed > 0:
                msg += f" ({failed} failed)"

            self.log_line.emit(f"\n{msg}")
            self.progress.emit(100, msg)
            self.finished.emit(True, msg)

        except Exception as e:
            error_msg = f"Batch processing failed: {e}"
            self.log_line.emit(error_msg)
            self.finished.emit(False, error_msg)

    # ------------------------------------------------------------------
    #  Single task
    # ------------------------------------------------------------------

    def _process_single_task(self, task: BatchTask):
        from hvsr_pro.core.data_structures import SeismicData, ComponentData
        from hvsr_pro.processing import WindowManager, RejectionEngine, HVSRProcessor

        settings = self.hvsr_settings
        window_length = settings.get('window_length', 120)
        overlap = settings.get('overlap', 0.5)
        smoothing_bw = settings.get('konno_ohmachi_bandwidth', 40)
        smoothing_method = settings.get('smoothing_method', 'konno_ohmachi')
        freq_min = settings.get('freq_min', 0.2)
        freq_max = settings.get('freq_max', 30.0)
        n_frequencies = settings.get('n_frequencies', 300)
        horizontal_method = settings.get('horizontal_method', 'geometric_mean')
        taper = settings.get('taper', 'tukey')
        detrend = settings.get('detrend', 'linear')
        statistics_method = settings.get('statistics_method', 'lognormal')
        std_ddof = settings.get('std_ddof', 1)
        min_prominence = settings.get('min_prominence', 0.5)
        min_amplitude = settings.get('min_amplitude', 2.0)
        peak_basis = settings.get('peak_basis', 'median')

        self.task_progress.emit(task.label or task.station_id, 10)

        # 1. Load data
        self.log_line.emit(f"  Loading: {task.mat_path}")
        data = self._load_mat_to_seismic_data(task.mat_path)
        if data is None:
            raise ValueError(f"Could not load data from {task.mat_path}")

        self.task_progress.emit(task.label or task.station_id, 20)

        # 2. Create windows
        self.log_line.emit(
            f"  Creating windows (length={window_length}s, overlap={overlap})")
        manager = WindowManager(window_length=window_length, overlap=overlap)
        windows = manager.create_windows(data, calculate_quality=True)
        self.log_line.emit(f"  Created {windows.n_windows} windows")
        self.task_progress.emit(task.label or task.station_id, 30)

        # 3. QC (Phase 1 - pre-HVSR)
        engine = RejectionEngine()
        qc = settings.get('qc_settings', {})

        if qc.get('qc_stalta', True):
            from hvsr_pro.processing.rejection import STALTARejection
            p = qc.get('sta_lta_params', {})
            engine.add_algorithm(STALTARejection(
                sta_length=p.get('sta_length', 1.0),
                lta_length=p.get('lta_length', 30.0),
                min_ratio=p.get('min_ratio', 0.2),
                max_ratio=p.get('max_ratio', 2.5),
            ))

        if qc.get('qc_amplitude', True):
            from hvsr_pro.processing.rejection import AmplitudeRejection
            engine.add_algorithm(AmplitudeRejection())

        if qc.get('qc_statistical', False):
            from hvsr_pro.processing.rejection import StatisticalOutlierRejection
            p = qc.get('statistical_params', {})
            engine.add_algorithm(StatisticalOutlierRejection(
                method=p.get('method', 'iqr'),
                threshold=p.get('threshold', 2.0),
            ))

        if engine.algorithms:
            engine.evaluate(windows, auto_apply=True)
            self.log_line.emit(
                f"  QC: {windows.n_active}/{windows.n_windows} windows passed")

        self.task_progress.emit(task.label or task.station_id, 50)
        if windows.n_active == 0:
            raise ValueError("No windows passed QC")

        # 4. HVSR
        self.log_line.emit(
            f"  Computing HVSR ({smoothing_method}, bw={smoothing_bw})")
        processor = HVSRProcessor(
            smoothing_method=smoothing_method,
            smoothing_bandwidth=smoothing_bw,
            horizontal_method=horizontal_method,
            f_min=freq_min, f_max=freq_max,
            n_frequencies=n_frequencies,
            taper=taper,
            detrend=detrend,
            statistics_method=statistics_method,
            std_ddof=std_ddof,
            min_prominence=min_prominence,
            min_amplitude=min_amplitude,
            peak_basis=peak_basis,
        )
        result = processor.process(
            windows, detect_peaks_flag=True, save_window_spectra=True)

        self.log_line.emit(
            f"  HVSR computed: {result.valid_windows} valid windows")
        if result.primary_peak:
            self.log_line.emit(
                f"  Primary peak: {result.primary_peak.frequency:.2f} Hz")

        self.task_progress.emit(task.label or task.station_id, 75)

        # 5. Cox FDWRA (Phase 2 - post-HVSR)
        if qc.get('qc_fdwra', True):
            fdwra_p = qc.get('fdwra_params', {})
            fdwra_result = engine.evaluate_fdwra(
                windows, result,
                n=fdwra_p.get('n', 2.0),
                max_iterations=fdwra_p.get('max_iterations', 50),
                min_iterations=fdwra_p.get('min_iterations', 1),
                distribution_fn=fdwra_p.get('distribution_fn', 'lognormal'),
                distribution_mc=fdwra_p.get('distribution_mc', 'lognormal'),
                search_range_hz=(freq_min, freq_max),
                auto_apply=True,
            )
            n_rej = fdwra_result.get('n_rejected', 0)
            if n_rej > 0:
                self.log_line.emit(
                    f"  FDWRA: {n_rej} windows rejected, recomputing...")
                if windows.n_active > 0:
                    result = processor.process(
                        windows, detect_peaks_flag=True,
                        save_window_spectra=True)

        self.task_progress.emit(task.label or task.station_id, 85)

        # ── Build fig_label used across all output filenames ──
        fig_label = task.station_id
        if task.window_name:
            fig_label = f"{task.station_id}_{task.window_name}"

        # ── Resample to common log-spaced grid ──
        raw_freq = result.frequencies
        spec_arrays = {
            'mean_hvsr': result.mean_hvsr,
            'median_hvsr': result.median_hvsr,
            'std_hvsr': result.std_hvsr,
            'percentile_16': result.percentile_16,
            'percentile_84': result.percentile_84,
        }
        freq_rs, rs = _resample_to_log_grid(
            raw_freq, spec_arrays, freq_min, freq_max, n_points=300)

        # Collect per-window HVSR curves (resampled)
        per_window_hvsr = []
        if result.window_spectra:
            for ws in result.window_spectra:
                if ws.is_valid and ws.hvsr is not None:
                    per_window_hvsr.append(
                        np.interp(freq_rs, ws.frequencies, ws.hvsr))

        # ── Outputs ──
        out_dir = task.output_dir
        os.makedirs(out_dir, exist_ok=True)

        tw = settings.get('window_length', 120)

        self._save_result_json(out_dir, fig_label, result, task, windows,
                               freq_rs, rs, per_window_hvsr)
        self._save_median_mat(out_dir, fig_label, tw, freq_rs, rs,
                              per_window_hvsr, result)
        self._save_peaks_mat(out_dir, fig_label, result)
        self._save_peaks_csv(out_dir, fig_label, result)
        self._save_stats_csv(out_dir, fig_label, freq_rs, rs)

        if settings.get('save_png', True) or settings.get('save_pdf', False):
            self._generate_all_figures(
                out_dir, fig_label, freq_rs, rs, per_window_hvsr,
                result, windows, data, settings)

        # Store intermediate data for interactive mode
        combined_hv = np.column_stack(per_window_hvsr) if per_window_hvsr else rs['mean_hvsr'].reshape(-1, 1)
        rejected_mask = np.array([not w.is_active() for w in windows.windows]) if windows else np.zeros(1, dtype=bool)
        station_data = {
            'task': task,
            'fig_label': fig_label,
            'freq_rs': freq_rs,
            'rs': rs,
            'combined_hv': combined_hv,
            'rejected_mask': rejected_mask,
            'result': result,
            'windows': windows,
            'data': data,
            'out_dir': out_dir,
            'per_window_hvsr': per_window_hvsr,
        }
        self.station_results.append(station_data)

        self.task_progress.emit(task.label or task.station_id, 100)

    # ------------------------------------------------------------------
    #  Data loading
    # ------------------------------------------------------------------

    def _load_mat_to_seismic_data(self, mat_path: str):
        try:
            from scipy.io import loadmat
            from hvsr_pro.core.data_structures import SeismicData, ComponentData

            mat = loadmat(mat_path)

            z_data = n_data = e_data = fs = None

            for key in mat:
                if key.startswith('__'):
                    continue
                ku = key.upper()
                if 'Z' in ku and 'ARRAY' in ku:
                    z_data = mat[key].flatten()
                elif 'N' in ku and 'ARRAY' in ku:
                    n_data = mat[key].flatten()
                elif 'E' in ku and 'ARRAY' in ku:
                    e_data = mat[key].flatten()
                elif key.lower() in ('fs_hz', 'fs', 'sampling_rate'):
                    fs = float(mat[key].flatten()[0])

            if z_data is None:
                for key in mat:
                    if key.endswith('Z') and key.startswith('Array'):
                        z_data = mat[key].flatten()
                    elif key.endswith('N') and key.startswith('Array'):
                        n_data = mat[key].flatten()
                    elif key.endswith('E') and key.startswith('Array'):
                        e_data = mat[key].flatten()

            if z_data is None or n_data is None or e_data is None:
                logger.error(
                    f"Could not find Z/N/E in {mat_path}. Keys: {list(mat.keys())}")
                return None

            if fs is None:
                fs = 100.0
                logger.warning(
                    f"No sampling rate in {mat_path}, using default {fs} Hz")

            min_len = min(len(z_data), len(n_data), len(e_data))
            east = ComponentData(
                name='E', data=e_data[:min_len].astype(np.float64),
                sampling_rate=fs)
            north = ComponentData(
                name='N', data=n_data[:min_len].astype(np.float64),
                sampling_rate=fs)
            vertical = ComponentData(
                name='Z', data=z_data[:min_len].astype(np.float64),
                sampling_rate=fs)

            return SeismicData(
                east=east, north=north, vertical=vertical,
                station_name=Path(mat_path).stem,
                source_file=mat_path,
            )
        except Exception as e:
            logger.error(f"Failed to load MAT {mat_path}: {e}")
            return None

    # ------------------------------------------------------------------
    #  JSON output  (Todo 1 + 3)
    # ------------------------------------------------------------------

    def _save_result_json(self, out_dir, fig_label, result, task, windows,
                          freq_rs, rs, per_window_hvsr):
        """Save full HVSR result JSON matching results_handler expectations."""

        json_name = f"HVSR_{fig_label}_result.json"
        json_path = os.path.join(out_dir, json_name)
        os.makedirs(os.path.dirname(os.path.abspath(json_path)), exist_ok=True)

        peaks_list = []
        if hasattr(result, 'peaks') and result.peaks:
            for pk in result.peaks:
                peaks_list.append({
                    'frequency': float(pk.frequency),
                    'amplitude': float(pk.amplitude),
                    'prominence': float(getattr(pk, 'prominence', 0)),
                    'width': float(getattr(pk, 'width', 0)),
                    'left_freq': float(getattr(pk, 'left_freq', 0)),
                    'right_freq': float(getattr(pk, 'right_freq', 0)),
                    'quality': float(getattr(pk, 'quality', 1.0)),
                })

        acc_rate = (result.valid_windows / result.total_windows
                    if result.total_windows > 0 else 0.0)

        data = {
            'station_id': task.station_id,
            'window_name': task.window_name,
            'frequencies': freq_rs.tolist(),
            'mean_hvsr': rs['mean_hvsr'].tolist(),
            'median_hvsr': rs['median_hvsr'].tolist(),
            'std_hvsr': rs['std_hvsr'].tolist(),
            'percentile_16': rs['percentile_16'].tolist(),
            'percentile_84': rs['percentile_84'].tolist(),
            'valid_windows': int(result.valid_windows),
            'total_windows': int(result.total_windows),
            'acceptance_rate': float(acc_rate),
            'peaks': peaks_list,
            'processing_params': (result.processing_params
                                  if hasattr(result, 'processing_params')
                                  else {}),
            'timestamp': datetime.now().isoformat(),
            'metadata': {
                'mat_path': task.mat_path,
                'output_dir': task.output_dir,
                'fig_label': fig_label,
            },
        }

        if per_window_hvsr:
            data['per_window_hvsr'] = [w.tolist() for w in per_window_hvsr]

        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)

        self.log_line.emit(f"  Saved JSON: {json_name}")

    # ------------------------------------------------------------------
    #  MAT output  (Todo 4)
    # ------------------------------------------------------------------

    def _save_median_mat(self, out_dir, fig_label, tw, freq_rs, rs,
                         per_window_hvsr, result):
        try:
            from scipy.io import savemat
        except ImportError:
            self.log_line.emit("  Warning: scipy not available, skipping MAT")
            return

        mat_name = f"HVSR_Median_{tw}Sec_{fig_label}.mat"
        mat_path = os.path.join(out_dir, mat_name)

        mat_dict = {
            'Frequency': freq_rs,
            'HVmean': rs['mean_hvsr'],
            'HVMedian': rs['median_hvsr'],
            'HVStd': rs['std_hvsr'],
            'HVPer16th': rs['percentile_16'],
            'HVPer84th': rs['percentile_84'],
            'ValidWindows': int(result.valid_windows),
            'TotalWindows': int(result.total_windows),
        }

        if per_window_hvsr:
            mat_dict['VelFreqHV'] = np.column_stack(per_window_hvsr)

        savemat(mat_path, mat_dict)
        self.log_line.emit(f"  Saved MAT: {mat_name}")

    # ------------------------------------------------------------------
    #  Peaks MAT + CSV  (Todo 5)
    # ------------------------------------------------------------------

    def _save_peaks_mat(self, out_dir, fig_label, result):
        if not (hasattr(result, 'peaks') and result.peaks):
            return
        try:
            from scipy.io import savemat
        except ImportError:
            return

        freqs = [float(p.frequency) for p in result.peaks]
        amps = [float(p.amplitude) for p in result.peaks]
        widths = [float(getattr(p, 'width', 0)) for p in result.peaks]

        mat_name = f"Peaks_{fig_label}.mat"
        mat_path = os.path.join(out_dir, mat_name)
        savemat(mat_path, {
            'HVSRPeaks': np.array([freqs, amps]),
            'PeakWidths': np.array(widths),
        })
        self.log_line.emit(f"  Saved Peaks MAT: {mat_name}")

    def _save_peaks_csv(self, out_dir, fig_label, result):
        if not (hasattr(result, 'peaks') and result.peaks):
            return

        csv_name = f"Peaks_{fig_label}.csv"
        csv_path = os.path.join(out_dir, csv_name)
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Frequency_Hz', 'Amplitude', 'Prominence',
                'Width_Hz', 'Left_Hz', 'Right_Hz', 'Quality'])
            for pk in result.peaks:
                writer.writerow([
                    f"{pk.frequency:.4f}",
                    f"{pk.amplitude:.4f}",
                    f"{getattr(pk, 'prominence', 0):.4f}",
                    f"{getattr(pk, 'width', 0):.4f}",
                    f"{getattr(pk, 'left_freq', 0):.4f}",
                    f"{getattr(pk, 'right_freq', 0):.4f}",
                    f"{getattr(pk, 'quality', 1.0):.4f}",
                ])
        self.log_line.emit(f"  Saved Peaks CSV: {csv_name}")

    # ------------------------------------------------------------------
    #  Statistics CSV  (Todo 6)
    # ------------------------------------------------------------------

    def _save_stats_csv(self, out_dir, fig_label, freq_rs, rs):
        csv_name = f"HVSR_{fig_label}_median_data.csv"
        csv_path = os.path.join(out_dir, csv_name)
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Frequency_Hz', 'Median', 'Mean', 'Std',
                'Percentile_16', 'Percentile_84'])
            for i in range(len(freq_rs)):
                writer.writerow([
                    f"{freq_rs[i]:.6f}",
                    f"{rs['median_hvsr'][i]:.6f}",
                    f"{rs['mean_hvsr'][i]:.6f}",
                    f"{rs['std_hvsr'][i]:.6f}",
                    f"{rs['percentile_16'][i]:.6f}",
                    f"{rs['percentile_84'][i]:.6f}",
                ])
        self.log_line.emit(f"  Saved Stats CSV: {csv_name}")

    # ------------------------------------------------------------------
    #  Figure  (Todo 7)
    # ------------------------------------------------------------------

    def _save_figure(self, out_dir, fig_label, freq_rs, rs,
                     per_window_hvsr, result, *,
                     save_png=True, save_pdf=False, dpi=300):
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
        except ImportError:
            self.log_line.emit("  Warning: matplotlib not available, skipping figure")
            return

        fig, ax = plt.subplots(figsize=(10, 6))

        if per_window_hvsr:
            for wh in per_window_hvsr:
                ax.semilogx(freq_rs, wh, color='#cccccc', alpha=0.3,
                            linewidth=0.5)

        ax.semilogx(freq_rs, rs['mean_hvsr'], 'b-', linewidth=1.5,
                     label='Mean')
        ax.semilogx(freq_rs, rs['median_hvsr'], 'r-', linewidth=1.5,
                     label='Median')
        ax.fill_between(freq_rs, rs['percentile_16'], rs['percentile_84'],
                        alpha=0.2, color='blue', label='16th-84th %ile')

        if hasattr(result, 'peaks') and result.peaks:
            for pk in result.peaks:
                amp = float(pk.amplitude)
                freq = float(pk.frequency)
                ax.axvline(freq, color='green', linestyle='--', alpha=0.6)
                ax.annotate(f'{freq:.2f} Hz',
                            xy=(freq, amp),
                            xytext=(5, 5), textcoords='offset points',
                            fontsize=8, color='green')

        ax.set_xlabel('Frequency (Hz)')
        ax.set_ylabel('H/V Ratio')
        ax.set_title(f'HVSR - {fig_label}')
        ax.legend(loc='upper right', fontsize=8)
        ax.grid(True, which='both', alpha=0.3)
        ax.set_xlim(freq_rs[0], freq_rs[-1])
        fig.tight_layout()

        if save_png:
            png_path = os.path.join(out_dir, f"HVSR_{fig_label}.png")
            fig.savefig(png_path, dpi=dpi, bbox_inches='tight')
            self.log_line.emit(f"  Saved PNG: HVSR_{fig_label}.png")
        if save_pdf:
            pdf_path = os.path.join(out_dir, f"HVSR_{fig_label}.pdf")
            fig.savefig(pdf_path, bbox_inches='tight')
            self.log_line.emit(f"  Saved PDF: HVSR_{fig_label}.pdf")

        plt.close(fig)

    # ------------------------------------------------------------------
    #  Comprehensive Figure Generation (replaces _save_figure for batch)
    # ------------------------------------------------------------------

    def _generate_all_figures(self, out_dir, fig_label, freq_rs, rs,
                              per_window_hvsr, result, windows, data, settings):
        """Generate all configured figures using figure_gen module."""
        try:
            from hvsr_pro.packages.batch_processing.figure_gen import (
                generate_hvsr_figures, build_hvsr_pro_objects)
        except ImportError:
            self.log_line.emit("  Warning: figure_gen not available, using basic figure")
            self._save_figure(out_dir, fig_label, freq_rs, rs,
                              per_window_hvsr, result,
                              save_png=settings.get('save_png', True),
                              save_pdf=settings.get('save_pdf', False),
                              dpi=settings.get('auto_fig_dpi', 300))
            return

        dpi = settings.get('auto_fig_dpi', 300)
        save_png = settings.get('save_png', True)
        save_pdf = settings.get('save_pdf', False)

        # Build combined_hv matrix (n_freq x n_windows) from per-window curves
        if per_window_hvsr:
            combined_hv = np.column_stack(per_window_hvsr)
        else:
            combined_hv = rs['mean_hvsr'].reshape(-1, 1)

        n_windows_total = windows.n_windows if windows else combined_hv.shape[1]

        # Build rejection mask and accepted indices
        rejected_mask = np.zeros(n_windows_total, dtype=bool)
        rejected_reasons = [''] * n_windows_total
        accepted_indices = list(range(combined_hv.shape[1]))

        if windows is not None:
            win_list = windows.windows
            rej_idx = 0
            for wi, win in enumerate(win_list):
                if not win.is_active():
                    rejected_mask[wi] = True
                    rejected_reasons[wi] = getattr(win, 'rejection_reason', '') or 'rejected'

        # Use the HVSRResult directly if available (it's already an hvsr_pro object)
        hvsr_result_obj = result
        window_collection = windows
        seismic_data = data

        hv_mean = rs['mean_hvsr']
        hv_std = rs['std_hvsr']
        hv_mean_plus_std = hv_mean + hv_std
        hv_mean_minus_std = np.maximum(hv_mean - hv_std, 0)
        hv_16 = rs['percentile_16']
        hv_84 = rs['percentile_84']

        fig_config = settings.get('figure_export_config', {})
        fig_title = f'HVSR - {fig_label}'

        peaks = result.peaks if hasattr(result, 'peaks') else []

        n_saved = generate_hvsr_figures(
            hvsr_result_obj=hvsr_result_obj,
            window_collection=window_collection,
            seismic_data=seismic_data,
            peaks=peaks,
            freq_ref=freq_rs,
            hv_mean=hv_mean,
            hv_std=hv_std,
            hv_mean_plus_std=hv_mean_plus_std,
            hv_mean_minus_std=hv_mean_minus_std,
            hv_16=hv_16,
            hv_84=hv_84,
            combined_hv=combined_hv,
            rejected_mask=rejected_mask[:combined_hv.shape[1]],
            accepted_indices=accepted_indices,
            n_windows=n_windows_total,
            output_dir=out_dir,
            fig_label=fig_label,
            fig_title=fig_title,
            fig_config=fig_config,
            fig_standard=settings.get('auto_fig_standard', True),
            fig_hvsr_pro=settings.get('auto_fig_hvsr_pro', True),
            fig_statistics=settings.get('auto_fig_statistics', True),
            save_png=save_png,
            save_pdf=save_pdf,
            dpi=dpi,
            ann_font_pt=settings.get('peak_font', 10),
        )
        self.log_line.emit(f"  Generated {n_saved} figures for {fig_label}")
