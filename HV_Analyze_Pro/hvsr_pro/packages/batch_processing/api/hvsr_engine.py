"""
Batch Processing API — HVSR Processing Engine (Phase 2)
=======================================================

Headless HVSR processing for batch analysis. Converts ArrayData.mat
files into per-station HVSR results with full QC pipeline.

This is the headless equivalent of ``workers/hvsr_worker.py``.

Pipeline per station (10 steps):
    1. Load MAT → SeismicData
    2. Create windows (WindowManager)
    3. Phase 1 QC: STA/LTA, amplitude, statistical (RejectionEngine)
    4. Compute HVSR (HVSRProcessor with all settings)
    5. Phase 2 QC: FDWRA
    6. Phase 3 QC: HVSR amplitude, flat peak, curve outlier
    7. Recompute HVSR if windows rejected
    8. Resample to log-spaced frequency grid
    9. Save per-station outputs (JSON, MAT, CSV)
   10. Build StationResult
"""

from __future__ import annotations

import csv
import json
import logging
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from .config import ProcessingSettings, QCSettings, PeakSettings, OutputSettings
from .data_engine import DataResult

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────
# Result dataclass
# ────────────────────────────────────────────────────────────────────

@dataclass
class StationHVSRResult:
    """Complete HVSR result for one station (or station × window)."""

    station_name: str
    window_name: str
    station_id: int = 0

    # Resampled curves on common log grid
    frequencies: Optional[np.ndarray] = None      # log-spaced grid
    mean_hvsr: Optional[np.ndarray] = None
    median_hvsr: Optional[np.ndarray] = None
    std_hvsr: Optional[np.ndarray] = None
    percentile_16: Optional[np.ndarray] = None
    percentile_84: Optional[np.ndarray] = None

    # Per-window HVSR curves (resampled)
    per_window_hvsr: List[np.ndarray] = field(default_factory=list)
    rejected_mask: Optional[np.ndarray] = None
    rejected_reasons: Optional[list] = None

    # Peak info
    peaks: list = field(default_factory=list)

    # Window counts
    valid_windows: int = 0
    total_windows: int = 0

    # Raw objects (retained for figure generation)
    hvsr_result: Any = None        # HVSRProcessor result
    window_collection: Any = None  # WindowCollection
    seismic_data: Any = None       # SeismicData

    # Output files generated
    output_files: Dict[str, str] = field(default_factory=dict)
    output_dir: str = ""

    # Status
    success: bool = True
    error: str = ""

    # Processing params (for figure generation)
    window_length: float = 120.0


# ────────────────────────────────────────────────────────────────────
# Log-grid resampling
# ────────────────────────────────────────────────────────────────────

def _resample_to_log_grid(
    freq_in: np.ndarray,
    arrays: Dict[str, np.ndarray],
    f_min: float,
    f_max: float,
    n_points: int = 300,
) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
    """Resample statistical arrays onto a common log-spaced grid."""
    freq_out = np.logspace(
        np.log10(max(f_min, freq_in[0])),
        np.log10(min(f_max, freq_in[-1])),
        n_points,
    )
    resampled = {}
    for key, arr in arrays.items():
        if arr is not None and len(arr) == len(freq_in):
            resampled[key] = np.interp(freq_out, freq_in, arr)
        else:
            resampled[key] = arr
    return freq_out, resampled


# ────────────────────────────────────────────────────────────────────
# MAT file loader
# ────────────────────────────────────────────────────────────────────

def _load_mat_to_seismic_data(mat_path: str):
    """Load ArrayData.mat → SeismicData."""
    from scipy.io import loadmat
    from hvsr_pro.core.data_structures import SeismicData, ComponentData

    mat = loadmat(mat_path)

    z_data = n_data = e_data = fs = None

    # Pass 1: flexible key matching
    for key in mat:
        if key.startswith("__"):
            continue
        ku = key.upper()
        if "Z" in ku and "ARRAY" in ku:
            z_data = mat[key].flatten()
        elif "N" in ku and "ARRAY" in ku:
            n_data = mat[key].flatten()
        elif "E" in ku and "ARRAY" in ku:
            e_data = mat[key].flatten()
        elif key.lower() in ("fs_hz", "fs", "sampling_rate"):
            fs = float(mat[key].flatten()[0])

    # Pass 2: strict key matching
    if z_data is None:
        for key in mat:
            if key.endswith("Z") and key.startswith("Array"):
                z_data = mat[key].flatten()
            elif key.endswith("N") and key.startswith("Array"):
                n_data = mat[key].flatten()
            elif key.endswith("E") and key.startswith("Array"):
                e_data = mat[key].flatten()

    if z_data is None or n_data is None or e_data is None:
        raise ValueError(
            f"Could not find Z/N/E in {mat_path}. Keys: {list(mat.keys())}"
        )

    if fs is None:
        fs = 100.0
        logger.warning("No sampling rate in %s, using default %.0f Hz", mat_path, fs)

    min_len = min(len(z_data), len(n_data), len(e_data))
    east = ComponentData(name="E", data=e_data[:min_len].astype(np.float64), sampling_rate=fs)
    north = ComponentData(name="N", data=n_data[:min_len].astype(np.float64), sampling_rate=fs)
    vertical = ComponentData(name="Z", data=z_data[:min_len].astype(np.float64), sampling_rate=fs)

    return SeismicData(
        east=east, north=north, vertical=vertical,
        station_name=Path(mat_path).stem,
        source_file=mat_path,
    )


# ────────────────────────────────────────────────────────────────────
# Output writers
# ────────────────────────────────────────────────────────────────────

def _save_result_json(
    out_dir: str, fig_label: str, result, task_info: dict,
    freq_rs: np.ndarray, rs: dict, per_window_hvsr: list,
) -> str:
    """Save full HVSR result as JSON."""
    peaks_list = []
    if hasattr(result, "peaks") and result.peaks:
        for pk in result.peaks:
            peaks_list.append({
                "frequency": float(pk.frequency),
                "amplitude": float(pk.amplitude),
                "prominence": float(getattr(pk, "prominence", 0)),
                "width": float(getattr(pk, "width", 0)),
                "left_freq": float(getattr(pk, "left_freq", 0)),
                "right_freq": float(getattr(pk, "right_freq", 0)),
                "quality": float(getattr(pk, "quality", 1.0)),
            })

    acc_rate = (
        result.valid_windows / result.total_windows
        if result.total_windows > 0
        else 0.0
    )

    data = {
        "station_id": task_info.get("station_id", ""),
        "window_name": task_info.get("window_name", ""),
        "frequencies": freq_rs.tolist(),
        "mean_hvsr": rs["mean_hvsr"].tolist(),
        "median_hvsr": rs["median_hvsr"].tolist(),
        "std_hvsr": rs["std_hvsr"].tolist(),
        "percentile_16": rs["percentile_16"].tolist(),
        "percentile_84": rs["percentile_84"].tolist(),
        "valid_windows": int(result.valid_windows),
        "total_windows": int(result.total_windows),
        "acceptance_rate": float(acc_rate),
        "peaks": peaks_list,
        "processing_params": (
            result.processing_params
            if hasattr(result, "processing_params")
            else {}
        ),
        "timestamp": datetime.now().isoformat(),
        "metadata": task_info.get("metadata", {}),
    }

    if per_window_hvsr:
        data["per_window_hvsr"] = [w.tolist() for w in per_window_hvsr]

    json_path = os.path.join(out_dir, f"HVSR_{fig_label}_result.json")
    with open(json_path, "w") as f:
        json.dump(data, f, indent=2)
    return json_path


def _save_median_mat(
    out_dir: str, fig_label: str, tw: int,
    freq_rs: np.ndarray, rs: dict, per_window_hvsr: list, result,
) -> str:
    """Save statistical arrays as MAT file."""
    from scipy.io import savemat

    mat_dict = {
        "Frequency": freq_rs,
        "HVmean": rs["mean_hvsr"],
        "HVMedian": rs["median_hvsr"],
        "HVStd": rs["std_hvsr"],
        "HVPer16th": rs["percentile_16"],
        "HVPer84th": rs["percentile_84"],
        "ValidWindows": int(result.valid_windows),
        "TotalWindows": int(result.total_windows),
    }
    if per_window_hvsr:
        mat_dict["VelFreqHV"] = np.column_stack(per_window_hvsr)

    mat_path = os.path.join(out_dir, f"HVSR_Median_{tw}Sec_{fig_label}.mat")
    savemat(mat_path, mat_dict)
    return mat_path


def _save_peaks_mat(out_dir: str, fig_label: str, result) -> Optional[str]:
    """Save peak data as MAT file."""
    if not (hasattr(result, "peaks") and result.peaks):
        return None
    from scipy.io import savemat

    freqs = [float(p.frequency) for p in result.peaks]
    amps = [float(p.amplitude) for p in result.peaks]
    widths = [float(getattr(p, "width", 0)) for p in result.peaks]

    mat_path = os.path.join(out_dir, f"Peaks_{fig_label}.mat")
    savemat(mat_path, {
        "HVSRPeaks": np.array([freqs, amps]),
        "PeakWidths": np.array(widths),
    })
    return mat_path


def _save_peaks_csv(out_dir: str, fig_label: str, result) -> Optional[str]:
    """Save peak data as CSV."""
    if not (hasattr(result, "peaks") and result.peaks):
        return None

    csv_path = os.path.join(out_dir, f"Peaks_{fig_label}.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Frequency_Hz", "Amplitude", "Prominence",
            "Width_Hz", "Left_Hz", "Right_Hz", "Quality",
        ])
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
    return csv_path


def _save_stats_csv(
    out_dir: str, fig_label: str,
    freq_rs: np.ndarray, rs: dict,
) -> str:
    """Save statistical curves as CSV."""
    csv_path = os.path.join(out_dir, f"HVSR_{fig_label}_median_data.csv")
    with open(csv_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Frequency_Hz", "Median", "Mean", "Std",
            "Percentile_16", "Percentile_84",
        ])
        for i in range(len(freq_rs)):
            writer.writerow([
                f"{freq_rs[i]:.6f}",
                f"{rs['median_hvsr'][i]:.6f}",
                f"{rs['mean_hvsr'][i]:.6f}",
                f"{rs['std_hvsr'][i]:.6f}",
                f"{rs['percentile_16'][i]:.6f}",
                f"{rs['percentile_84'][i]:.6f}",
            ])
    return csv_path


# ────────────────────────────────────────────────────────────────────
# Main per-station processing function
# ────────────────────────────────────────────────────────────────────

def process_station_hvsr(
    data_result: DataResult,
    processing: ProcessingSettings,
    qc: QCSettings,
    peaks: PeakSettings,
    output: OutputSettings,
    output_dir: str,
    progress_callback: Optional[Callable[[str, int], None]] = None,
) -> StationHVSRResult:
    """
    Process a single station through the full HVSR pipeline.

    Parameters
    ----------
    data_result : DataResult
        Result from data preparation (contains mat_path, station info).
    processing : ProcessingSettings
        HVSR processing parameters.
    qc : QCSettings
        Quality control configuration.
    peaks : PeakSettings
        Peak detection parameters.
    output : OutputSettings
        Output file generation flags.
    output_dir : str
        Directory for per-station output files.
    progress_callback : callable, optional
        ``callback(label: str, percent: int)``

    Returns
    -------
    StationHVSRResult
    """
    from hvsr_pro.processing import WindowManager, RejectionEngine, HVSRProcessor

    label = f"{data_result.station_name}/{data_result.window_name}"

    def _progress(pct, msg=""):
        if progress_callback:
            progress_callback(label, pct)

    try:
        # ── Step 1: Load MAT → SeismicData ──
        _progress(10, "Loading data")
        data = _load_mat_to_seismic_data(data_result.mat_path)

        # ── Step 2: Create windows ──
        _progress(20, "Creating windows")
        manager = WindowManager(
            window_length=processing.window_length,
            overlap=processing.overlap,
        )
        windows = manager.create_windows(data, calculate_quality=True)
        logger.info("%s: %d windows created", label, windows.n_windows)

        # ── Step 3: Phase 1 QC (pre-HVSR) ──
        _progress(30, "Phase 1 QC")
        engine = RejectionEngine()

        if qc.stalta_enabled:
            from hvsr_pro.processing.rejection import STALTARejection
            engine.add_algorithm(STALTARejection(
                sta_length=qc.stalta.sta_length,
                lta_length=qc.stalta.lta_length,
                min_ratio=qc.stalta.min_ratio,
                max_ratio=qc.stalta.max_ratio,
            ))

        if qc.amplitude_enabled:
            from hvsr_pro.processing.rejection import AmplitudeRejection
            engine.add_algorithm(AmplitudeRejection(
                max_amplitude=qc.amplitude.max_amplitude,
                min_rms=qc.amplitude.min_rms,
                clipping_threshold=qc.amplitude.clipping_threshold,
                clipping_max_percent=qc.amplitude.clipping_max_percent,
                preset=qc.amplitude.preset,
            ))

        if qc.statistical_enabled:
            from hvsr_pro.processing.rejection import StatisticalOutlierRejection
            engine.add_algorithm(StatisticalOutlierRejection(
                method=qc.statistical.method,
                threshold=qc.statistical.threshold,
                metric=qc.statistical.metric,
            ))

        if engine.algorithms:
            eval_result = engine.evaluate(windows, auto_apply=True)
            logger.info("%s: QC Phase 1 — %d/%d passed",
                        label, windows.n_active, windows.n_windows)

        if windows.n_active == 0:
            raise ValueError(f"No windows passed Phase 1 QC for {label}")

        # ── Step 4: Compute HVSR ──
        _progress(50, "Computing HVSR")

        # Map processing settings to legacy format names
        smoothing_method = processing.smoothing_method
        _sm_lower = smoothing_method.lower().replace("-", "").replace("_", "").replace(" ", "")
        _SM_MAP = {
            "konnoohmachi": "konno_ohmachi",
            "parzen": "parzen",
            "savitzkygolay": "savitzky_golay",
            "linearrectangular": "linear_rectangular",
            "logrectangular": "log_rectangular",
            "lineartriangular": "linear_triangular",
            "logtriangular": "log_triangular",
            "none": "none",
        }
        smoothing_method = _SM_MAP.get(_sm_lower, smoothing_method)

        horizontal_method = processing.horizontal_method
        _h_map = {
            "geo": "geometric_mean",
            "quad": "quadratic_mean",
            "energy": "energy_density",
        }
        horizontal_method = _h_map.get(horizontal_method, horizontal_method)

        processor = HVSRProcessor(
            smoothing_method=smoothing_method,
            smoothing_bandwidth=processing.smoothing_bandwidth,
            horizontal_method=horizontal_method,
            f_min=processing.freq_min,
            f_max=processing.freq_max,
            n_frequencies=processing.n_frequencies,
            taper=processing.taper,
            detrend=processing.detrend,
            statistics_method=processing.statistics_method,
            std_ddof=processing.std_ddof,
            min_prominence=peaks.min_prominence,
            min_amplitude=peaks.min_amplitude,
            peak_basis=peaks.peak_basis,
        )
        result = processor.process(
            windows, detect_peaks_flag=True, save_window_spectra=True,
        )

        logger.info("%s: HVSR computed, %d valid windows",
                    label, result.valid_windows)

        # ── Step 5: Phase 2 QC — FDWRA ──
        _progress(70, "FDWRA")
        if qc.fdwra_enabled:
            fdwra_result = engine.evaluate_fdwra(
                windows, result,
                n=qc.fdwra.n,
                max_iterations=qc.fdwra.max_iterations,
                min_iterations=qc.fdwra.min_iterations,
                distribution_fn=qc.fdwra.distribution_fn,
                distribution_mc=qc.fdwra.distribution_mc,
                search_range_hz=(processing.freq_min, processing.freq_max),
                auto_apply=True,
            )
            n_rej = fdwra_result.get("n_rejected", 0)
            if n_rej > 0 and windows.n_active > 0:
                logger.info("%s: FDWRA rejected %d windows, recomputing", label, n_rej)
                result = processor.process(
                    windows, detect_peaks_flag=True, save_window_spectra=True,
                )

        # ── Step 6: Phase 3 QC — post-HVSR ──
        _progress(80, "Post-HVSR QC")
        has_post = (
            qc.hvsr_amplitude_enabled
            or qc.flat_peak_enabled
            or qc.curve_outlier_enabled
        )
        if has_post and windows.n_active > 0:
            from hvsr_pro.processing.rejection import (
                HVSRAmplitudeRejection,
                FlatPeakRejection,
                CurveOutlierRejection,
            )
            engine.post_hvsr_algorithms = []

            if qc.hvsr_amplitude_enabled:
                engine.post_hvsr_algorithms.append(
                    HVSRAmplitudeRejection(
                        min_amplitude=qc.hvsr_amplitude.min_amplitude,
                        max_amplitude=qc.hvsr_amplitude.max_amplitude,
                    )
                )
            if qc.flat_peak_enabled:
                engine.post_hvsr_algorithms.append(
                    FlatPeakRejection(
                        flatness_threshold=qc.flat_peak.flatness_threshold,
                    )
                )
            if qc.curve_outlier_enabled:
                engine.post_hvsr_algorithms.append(
                    CurveOutlierRejection(
                        threshold=qc.curve_outlier.threshold,
                        max_iterations=qc.curve_outlier.max_iterations,
                        metric=qc.curve_outlier.metric,
                    )
                )

            post_result = engine.evaluate_post_hvsr(
                windows, result, auto_apply=True,
            )
            n_post_rej = post_result.get("n_rejected", 0)
            if n_post_rej > 0 and windows.n_active > 0:
                logger.info("%s: Post-HVSR QC rejected %d windows", label, n_post_rej)
                result = processor.process(
                    windows, detect_peaks_flag=True, save_window_spectra=True,
                )

        # ── Step 7: Resample to log grid ──
        _progress(85, "Resampling")
        spec_arrays = {
            "mean_hvsr": result.mean_hvsr,
            "median_hvsr": result.median_hvsr,
            "std_hvsr": result.std_hvsr,
            "percentile_16": result.percentile_16,
            "percentile_84": result.percentile_84,
        }
        freq_rs, rs = _resample_to_log_grid(
            result.frequencies, spec_arrays,
            processing.freq_min, processing.freq_max,
            n_points=processing.n_frequencies,
        )

        # Per-window resampled curves
        per_window_hvsr = []
        if result.window_spectra:
            for ws in result.window_spectra:
                if ws.is_valid and ws.hvsr is not None:
                    per_window_hvsr.append(
                        np.interp(freq_rs, ws.frequencies, ws.hvsr)
                    )

        # Rejection mask
        rejected_mask = np.array(
            [not w.is_active() for w in windows.windows]
        ) if windows else np.zeros(1, dtype=bool)

        # ── Step 8: Save outputs ──
        _progress(90, "Saving outputs")
        os.makedirs(output_dir, exist_ok=True)
        fig_label = data_result.station_name
        if data_result.window_name:
            fig_label = f"{data_result.station_name}_{data_result.window_name}"

        output_files = {}
        task_info = {
            "station_id": data_result.station_name,
            "window_name": data_result.window_name,
            "metadata": {
                "mat_path": data_result.mat_path,
                "output_dir": output_dir,
                "fig_label": fig_label,
            },
        }

        if output.save_json:
            output_files["json"] = _save_result_json(
                output_dir, fig_label, result, task_info,
                freq_rs, rs, per_window_hvsr,
            )

        if output.save_mat:
            output_files["mat"] = _save_median_mat(
                output_dir, fig_label, int(processing.window_length),
                freq_rs, rs, per_window_hvsr, result,
            )
            pk_mat = _save_peaks_mat(output_dir, fig_label, result)
            if pk_mat:
                output_files["peaks_mat"] = pk_mat

        if output.save_csv:
            output_files["stats_csv"] = _save_stats_csv(
                output_dir, fig_label, freq_rs, rs,
            )
            pk_csv = _save_peaks_csv(output_dir, fig_label, result)
            if pk_csv:
                output_files["peaks_csv"] = pk_csv

        _progress(100, "Done")

        return StationHVSRResult(
            station_name=data_result.station_name,
            window_name=data_result.window_name,
            station_id=data_result.station_id,
            frequencies=freq_rs,
            mean_hvsr=rs["mean_hvsr"],
            median_hvsr=rs["median_hvsr"],
            std_hvsr=rs["std_hvsr"],
            percentile_16=rs["percentile_16"],
            percentile_84=rs["percentile_84"],
            per_window_hvsr=per_window_hvsr,
            rejected_mask=rejected_mask,
            peaks=list(result.peaks) if hasattr(result, "peaks") else [],
            valid_windows=result.valid_windows,
            total_windows=result.total_windows,
            hvsr_result=result,
            window_collection=windows,
            seismic_data=data,
            output_files=output_files,
            output_dir=output_dir,
        )

    except Exception as exc:
        logger.error("%s failed: %s", label, exc, exc_info=True)
        return StationHVSRResult(
            station_name=data_result.station_name,
            window_name=data_result.window_name,
            station_id=data_result.station_id,
            success=False,
            error=str(exc),
        )


# ────────────────────────────────────────────────────────────────────
# Batch processing (sequential or parallel)
# ────────────────────────────────────────────────────────────────────

def process_batch_hvsr(
    data_results: List[DataResult],
    processing: ProcessingSettings,
    qc: QCSettings,
    peaks: PeakSettings,
    output: OutputSettings,
    base_output_dir: str,
    parallel: bool = False,
    n_workers: int = 4,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> List[StationHVSRResult]:
    """
    Process all stations through the HVSR pipeline.

    Parameters
    ----------
    data_results : list[DataResult]
        Results from data preparation.
    processing : ProcessingSettings
        HVSR processing parameters.
    qc : QCSettings
        Quality control configuration.
    peaks : PeakSettings
        Peak detection parameters.
    output : OutputSettings
        Output file generation flags.
    base_output_dir : str
        Base output directory.
    parallel : bool
        Use parallel processing (ProcessPoolExecutor).
    n_workers : int
        Number of parallel workers.
    progress_callback : callable, optional
        ``callback(percent: int, message: str)``

    Returns
    -------
    list[StationHVSRResult]
    """
    total = len(data_results)
    results = []

    if progress_callback:
        progress_callback(0, f"Processing 0/{total} stations")

    # Sequential processing (more reliable, better error isolation)
    for i, dr in enumerate(data_results):
        station_out = dr.output_dir or os.path.join(
            base_output_dir, dr.window_name, dr.station_name,
        )

        stn_result = process_station_hvsr(
            data_result=dr,
            processing=processing,
            qc=qc,
            peaks=peaks,
            output=output,
            output_dir=station_out,
        )
        results.append(stn_result)

        if progress_callback:
            pct = int((i + 1) / total * 100)
            status = "✓" if stn_result.success else "✗"
            progress_callback(
                pct,
                f"{status} {dr.station_name} ({i+1}/{total})",
            )

    successful = sum(1 for r in results if r.success)
    logger.info(
        "Batch HVSR: %d/%d stations completed successfully",
        successful, total,
    )

    return results
