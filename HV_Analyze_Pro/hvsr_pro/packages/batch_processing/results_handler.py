"""
Results Handler
================

Loads HVSR results from processed station directories, runs automatic
peak detection, displays statistics, and exports analysis results.
"""

import os
import glob
import numpy as np


def load_hvsr_results(processed_results: list, hvsr_settings: dict,
                      log_fn=None) -> list:
    """Load HVSR results from processed station directories.

    Uses the time-window name (from the Time Windows table) as the
    array / topic name so that the Results tab groups stations by
    their configured window name.  Also tries to load interactively-
    picked peaks from the Peaks&Median MAT or CSV files that
    ``hvsr_making_peak.py`` saves.

    Parameters
    ----------
    processed_results : list[dict]
        Each dict has keys: station_name, station_id, dir, window_name, ...
    hvsr_settings : dict
        HVSR settings including window_length.
    log_fn : callable, optional
        Logging function.

    Returns
    -------
    list of StationResult
    """
    from scipy.io import loadmat
    from hvsr_pro.packages.batch_processing.processing import StationResult, Peak

    _log = log_fn or (lambda msg: None)
    station_results = []

    for result in processed_results:
        station_name = result['station_name']
        station_dir = result['dir']
        station_id = result['station_id']
        window_name = result.get('window_name', 'Default')

        fig_label = result.get('window_name', '')
        if fig_label:
            task_label = f"{station_name}_{fig_label}"
        else:
            task_label = station_name
        tw = hvsr_settings.get('window_length', 120)

        # ── Priority 1: Load from per-station JSON (has full data) ────────
        json_candidates = [
            os.path.join(station_dir, f"HVSR_{task_label}_result.json"),
            os.path.join(station_dir, f"HVSR_{station_name}_result.json"),
        ]
        json_path = None
        for p in json_candidates:
            if os.path.exists(p):
                json_path = p
                break
        if json_path is None:
            for fname in os.listdir(station_dir):
                if fname.endswith('_result.json') and fname.startswith('HVSR_'):
                    json_path = os.path.join(station_dir, fname)
                    break

        if json_path is not None:
            try:
                from hvsr_pro.packages.batch_processing.processing.structures import HVSRResult
                hvsr_obj = HVSRResult.load(json_path)
                peaks = [Peak(
                    frequency=p.frequency, amplitude=p.amplitude,
                    prominence=p.prominence, width=p.width,
                    left_freq=p.left_freq, right_freq=p.right_freq,
                    quality=p.quality, peak_type=p.peak_type,
                ) for p in hvsr_obj.peaks]

                station_result = StationResult(
                    station_id=station_id,
                    station_name=station_name,
                    topic=window_name,
                    frequencies=hvsr_obj.frequencies,
                    mean_hvsr=hvsr_obj.mean_hvsr,
                    std_hvsr=hvsr_obj.std_hvsr,
                    median_hvsr=hvsr_obj.median_hvsr,
                    percentile_16=hvsr_obj.percentile_16,
                    percentile_84=hvsr_obj.percentile_84,
                    peaks=peaks,
                    valid_windows=hvsr_obj.valid_windows,
                    total_windows=hvsr_obj.total_windows,
                    mat_path="",
                    output_dir=station_dir,
                    processing_params=hvsr_obj.processing_params,
                    metadata=hvsr_obj.metadata,
                )
                station_results.append(station_result)
                _log(f"Loaded HVSR from JSON for {window_name}/{station_name} "
                     f"({len(hvsr_obj.frequencies)} freq points, {len(peaks)} peaks)")
                continue
            except Exception as e:
                _log(f"  Warning: JSON load failed for {json_path}: {e}, falling back to MAT")

        # ── Priority 2: Fall back to MAT file ─────────────────────────────
        candidate_paths = [
            os.path.join(station_dir, f"HVSR_Median_{tw}Sec_{task_label}.mat"),
            os.path.join(station_dir, f"HVSR_{station_name}.mat"),
            os.path.join(station_dir, f"HVSRData_{station_name}.mat"),
        ]
        hvsr_mat_path = None
        for p in candidate_paths:
            if os.path.exists(p):
                hvsr_mat_path = p
                break

        if hvsr_mat_path is None:
            for fname in os.listdir(station_dir):
                if fname.lower().startswith('hvsr') and fname.endswith('.mat'):
                    hvsr_mat_path = os.path.join(station_dir, fname)
                    break

        if hvsr_mat_path is None:
            _log(f"Warning: No HVSR data found for {window_name}/{station_name}")
            continue

        try:
            data = loadmat(hvsr_mat_path, squeeze_me=True)

            frequencies = None
            for key in ('Frequency', 'frequencies', 'freq', 'Freq', 'f'):
                if key in data:
                    frequencies = np.atleast_1d(data[key]).astype(float)
                    break

            mean_hvsr = None
            for key in ('HVmean', 'HVMedian', 'mean_hvsr', 'hvsr_mean', 'HVSR'):
                if key in data:
                    mean_hvsr = np.atleast_1d(data[key]).astype(float)
                    break

            std_hvsr = None
            for key in ('HVStd', 'std_hvsr', 'hvsr_std', 'STD'):
                if key in data:
                    std_hvsr = np.atleast_1d(data[key]).astype(float)
                    break

            if frequencies is None or mean_hvsr is None:
                _log(f"Warning: Could not parse HVSR data in {hvsr_mat_path}")
                continue

            if std_hvsr is None:
                std_hvsr = np.zeros_like(mean_hvsr)

            median_hvsr = None
            for key in ('HVMedian', 'median_hvsr'):
                if key in data:
                    median_hvsr = np.atleast_1d(data[key]).astype(float)
                    break
            percentile_16 = None
            for key in ('HVPer16th', 'percentile_16'):
                if key in data:
                    percentile_16 = np.atleast_1d(data[key]).astype(float)
                    break
            percentile_84 = None
            for key in ('HVPer84th', 'percentile_84'):
                if key in data:
                    percentile_84 = np.atleast_1d(data[key]).astype(float)
                    break

            total_windows = 0
            valid_windows = 0
            vel_key = 'VelFreqHV'
            if vel_key in data:
                vel = data[vel_key]
                if vel.ndim == 2:
                    total_windows = vel.shape[1]
                    valid_windows = total_windows

            # ── Load peaks (interactive or saved) ──
            peaks = []

            peaks_mat_path = os.path.join(
                station_dir,
                f"Peaks&Median_HVSR_{tw}Sec_{task_label}.mat"
            )
            if os.path.exists(peaks_mat_path):
                try:
                    pk_data = loadmat(peaks_mat_path, squeeze_me=True)
                    if 'HVSRPeaks' in pk_data:
                        pk_arr = np.atleast_2d(pk_data['HVSRPeaks'])
                        if pk_arr.shape[0] == 2:
                            for ci in range(pk_arr.shape[1]):
                                peaks.append(Peak(
                                    frequency=float(pk_arr[0, ci]),
                                    amplitude=float(pk_arr[1, ci]),
                                ))
                        elif pk_arr.shape[1] == 2:
                            for ri in range(pk_arr.shape[0]):
                                peaks.append(Peak(
                                    frequency=float(pk_arr[ri, 0]),
                                    amplitude=float(pk_arr[ri, 1]),
                                ))
                        _log(f"  Loaded {len(peaks)} peak(s) from MAT for {task_label}")
                except Exception as e:
                    _log(f"  Warning: Could not load peaks MAT: {e}")

            if not peaks:
                import csv as csv_mod
                csv_pattern = os.path.join(station_dir, f"Peaks*{task_label}*.csv")
                csv_files = glob.glob(csv_pattern)
                if csv_files:
                    try:
                        with open(csv_files[0], 'r') as f:
                            reader = csv_mod.reader(f)
                            header = next(reader, None)
                            for row in reader:
                                if len(row) >= 2:
                                    peaks.append(Peak(
                                        frequency=float(row[0]),
                                        amplitude=float(row[1]),
                                    ))
                        _log(f"  Loaded {len(peaks)} peak(s) from CSV for {task_label}")
                    except Exception as e:
                        _log(f"  Warning: Could not load peaks CSV: {e}")

            station_result = StationResult(
                station_id=station_id,
                station_name=station_name,
                topic=window_name,
                frequencies=frequencies,
                mean_hvsr=mean_hvsr,
                std_hvsr=std_hvsr,
                median_hvsr=median_hvsr,
                percentile_16=percentile_16,
                percentile_84=percentile_84,
                peaks=peaks,
                valid_windows=valid_windows,
                total_windows=total_windows,
                mat_path=hvsr_mat_path,
                output_dir=station_dir,
            )
            station_results.append(station_result)
            _log(f"Loaded HVSR data from MAT for {window_name}/{station_name}")

        except Exception as e:
            _log(f"Warning: Could not load HVSR data for {station_name}: {e}")

    return station_results


def run_analysis(station_results: list, hvsr_settings: dict,
                 log_fn=None):
    """Run peak detection and build AutomaticWorkflowResult.

    When ``auto_mode`` is True the function detects peaks automatically
    for every station and computes combined statistics.

    When ``auto_mode`` is False (interactive / manual mode) the function
    builds the workflow result *without* forcing peak detection so the
    user can pick peaks manually on the results canvas.

    Parameters
    ----------
    station_results : list of StationResult
    hvsr_settings : dict
    log_fn : callable, optional

    Returns
    -------
    AutomaticWorkflowResult
    """
    from hvsr_pro.packages.batch_processing.processing import (
        run_automatic_peak_detection, detect_peaks,
        AutomaticWorkflowResult,
    )

    _log = log_fn or (lambda msg: None)
    settings = hvsr_settings
    auto_mode = settings.get('auto_mode', False)

    if auto_mode:
        _use_hvsr_pro = False
        try:
            from hvsr_pro.processing.windows.peaks import detect_peaks as hvsr_pro_detect
            _use_hvsr_pro = True
            _log("Using hvsr_pro peak detection for automatic analysis")
        except ImportError:
            _log("hvsr_pro not available, using local peak detection")

        _peak_fn = hvsr_pro_detect if _use_hvsr_pro else detect_peaks

        for sr in station_results:
            if not sr.peaks:
                sr.peaks = _peak_fn(
                    sr.frequencies, sr.mean_hvsr,
                    min_prominence=settings.get('min_prominence', 0.5),
                    min_amplitude=settings.get('min_amplitude', 2.0),
                    freq_range=(settings.get('freq_min', 0.2),
                                settings.get('freq_max', 20.0)),
                )[:settings.get('auto_npeaks', settings.get('num_peaks', 3))]

        result = run_automatic_peak_detection(
            station_results,
            min_prominence=settings.get('min_prominence', 0.5),
            min_amplitude=settings.get('min_amplitude', 2.0),
            n_peaks=settings.get('auto_npeaks', settings.get('num_peaks', 3)),
            frequency_tolerance=settings.get('freq_tolerance', 0.3),
        )
        _log(f"Detected {len(result.combined_peaks)} combined peaks")
    else:
        _log("Interactive mode: skipping automatic peak detection")
        result = AutomaticWorkflowResult(
            station_results=station_results,
            topics=list(set(s.topic for s in station_results)),
        )
        result.compute_median_hvsr()

    return result


def display_peak_statistics(result, log_fn=None):
    """Display peak statistics in the log."""
    _log = log_fn or (lambda msg: None)

    _log("\n" + "=" * 50)
    _log("AUTOMATIC PEAK DETECTION RESULTS")
    _log("=" * 50)

    _log(f"\nStations analyzed: {result.n_stations}")
    _log(f"Combined peaks detected: {len(result.combined_peaks)}")

    if result.peak_statistics:
        _log("\nPeak Statistics:")
        _log("-" * 40)
        for stat in result.peak_statistics:
            _log(stat.summary_string())

    _log("=" * 50 + "\n")


def export_automatic_results(result, output_dir: str, hvsr_settings: dict,
                             log_fn=None):
    """Export automatic analysis results to Excel and MAT files."""
    from hvsr_pro.packages.batch_processing.processing import OutputOrganizer

    _log = log_fn or (lambda msg: None)
    settings = hvsr_settings

    try:
        organizer = OutputOrganizer(output_dir, site_name="HVSR_Auto")

        station_dicts = [s.to_dict() for s in result.station_results]

        if settings.get('export_excel', True):
            try:
                excel_path = organizer.export_hvsr_excel(station_dicts)
                _log(f"Exported HVSR data to: {excel_path}")

                peaks_path = organizer.export_peaks_excel(station_dicts)
                _log(f"Exported peaks summary to: {peaks_path}")
            except Exception as e:
                _log(f"Warning: Excel export failed: {e}")

        if settings.get('export_mat', True):
            try:
                mat_path = organizer.export_hvsr_mat(station_dicts)
                _log(f"Exported MAT data to: {mat_path}")
            except Exception as e:
                _log(f"Warning: MAT export failed: {e}")

        try:
            import json
            json_path = os.path.join(output_dir, "automatic_results.json")
            result.save(json_path)
            _log(f"Saved results summary to: {json_path}")
        except Exception as e:
            _log(f"Warning: JSON export failed: {e}")

        try:
            combined_path = os.path.join(output_dir, "HVSR_Combined_All_Stations.json")
            result.save_as_station_format(combined_path)
            _log(f"Saved combined station-format JSON to: {combined_path}")
        except Exception as e:
            _log(f"Warning: Combined JSON export failed: {e}")

    except Exception as e:
        _log(f"Error during export: {e}")
