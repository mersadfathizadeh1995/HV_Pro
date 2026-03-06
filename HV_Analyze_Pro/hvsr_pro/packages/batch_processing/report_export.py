"""
Report Export
==============

Handles report generation: CSV/Excel tables, publication-quality figures,
and median data export (Excel + CSV + JSON + MAT).
"""

import os
import csv as csv_mod
import json
import numpy as np


def compute_full_median_stats(checked: list) -> dict:
    """Compute grand median, mean, std, and percentiles across stations.

    Parameters
    ----------
    checked : list
        List of StationResult objects (must have .topic, .frequencies, .mean_hvsr).

    Returns
    -------
    dict with keys: freq, grand_median, grand_mean, grand_std,
          percentile_16, percentile_84, valid_windows, total_windows,
          array_names, array_stats, n_total
    """
    base = compute_median_stats(checked)
    freq = base['freq']

    all_stack = [s.mean_hvsr for s in checked if len(s.mean_hvsr) == len(freq)]
    if all_stack:
        arr = np.array(all_stack)
        base['grand_mean'] = np.mean(arr, axis=0)
        base['percentile_16'] = np.percentile(arr, 16, axis=0)
        base['percentile_84'] = np.percentile(arr, 84, axis=0)
    else:
        base['grand_mean'] = np.zeros_like(freq)
        base['percentile_16'] = np.zeros_like(freq)
        base['percentile_84'] = np.zeros_like(freq)

    base['valid_windows'] = sum(getattr(s, 'valid_windows', 0) for s in checked)
    base['total_windows'] = sum(getattr(s, 'total_windows', 0) for s in checked)

    return base


def compute_median_stats(checked: list) -> dict:
    """Compute grand and per-array median + std.

    Parameters
    ----------
    checked : list
        List of StationResult objects (must have .topic, .frequencies, .mean_hvsr).

    Returns
    -------
    dict with keys: freq, grand_median, grand_std,
          array_names, array_stats, n_total
    """
    array_names = sorted(set(s.topic for s in checked))
    freq = checked[0].frequencies

    array_stats = {}
    for arr_name in array_names:
        stn_list = [s for s in checked if s.topic == arr_name]
        stack = [s.mean_hvsr for s in stn_list if len(s.mean_hvsr) == len(freq)]
        if stack:
            arr_data = np.array(stack)
            array_stats[arr_name] = {
                'median': np.median(arr_data, axis=0),
                'std': np.std(arr_data, axis=0),
                'n_stations': len(stack),
                'station_names': [s.station_name for s in stn_list],
            }

    all_stack = [s.mean_hvsr for s in checked if len(s.mean_hvsr) == len(freq)]
    grand_median = np.median(np.array(all_stack), axis=0) if all_stack else np.zeros_like(freq)
    grand_std = np.std(np.array(all_stack), axis=0) if all_stack else np.zeros_like(freq)

    return {
        'freq': freq, 'grand_median': grand_median, 'grand_std': grand_std,
        'array_names': array_names, 'array_stats': array_stats,
        'n_total': len(checked),
    }


def export_median_data(median_dir: str, checked: list, log_fn=None):
    """Export median curves as multi-sheet Excel, CSV, JSON, and MAT.

    Excel sheets (requires openpyxl):
        Combined  - Frequency, GrandMedian, GrandStd, per-array Median+Std
        <Array>   - one sheet per array with Frequency, Median, Std, station curves

    CSV files (always generated, no extra dependencies):
        HVSR_Median_Combined.csv          - grand + per-array medians
        HVSR_Median_<ArrayName>.csv       - one per array with station curves
    """
    from scipy.io import savemat

    _log = log_fn or (lambda msg: None)

    if not checked:
        return

    stats = compute_median_stats(checked)
    freq = stats['freq']
    array_names = stats['array_names']
    array_stats = stats['array_stats']
    grand_median = stats['grand_median']
    grand_std = stats['grand_std']

    # ── Multi-sheet Excel ──
    _excel_ok = False
    try:
        import pandas as pd
        xlsx_path = os.path.join(median_dir, "HVSR_Median_Combined.xlsx")
        with pd.ExcelWriter(xlsx_path, engine='openpyxl') as writer:
            combined = pd.DataFrame({'Frequency_Hz': freq,
                                     'GrandMedian': grand_median,
                                     'GrandStd': grand_std})
            for a in array_names:
                if a in array_stats:
                    combined[f'{a}_Median'] = array_stats[a]['median']
                    combined[f'{a}_Std'] = array_stats[a]['std']
            combined.to_excel(writer, sheet_name='Combined', index=False)

            for a in array_names:
                if a not in array_stats:
                    continue
                stn_list = [s for s in checked if s.topic == a]
                df = pd.DataFrame({'Frequency_Hz': freq,
                                   f'{a}_Median': array_stats[a]['median'],
                                   f'{a}_Std': array_stats[a]['std']})
                for s in stn_list:
                    if len(s.mean_hvsr) == len(freq):
                        df[s.station_name] = s.mean_hvsr
                safe_name = a[:31]
                df.to_excel(writer, sheet_name=safe_name, index=False)
        _log(f"  median/ -> {xlsx_path}")
        _excel_ok = True
    except ImportError:
        _log("  median/ -> openpyxl not available, skipping Excel")
    except Exception as exc:
        _log(f"  median/ -> Excel warning: {exc}")

    # ── CSV (always generated) ──
    csv_combined_path = os.path.join(median_dir, "HVSR_Median_Combined.csv")
    header = ['Frequency_Hz', 'GrandMedian', 'GrandStd']
    for a in array_names:
        if a in array_stats:
            header.extend([f'{a}_Median', f'{a}_Std'])
    with open(csv_combined_path, 'w', newline='') as f:
        writer = csv_mod.writer(f)
        writer.writerow(header)
        for i in range(len(freq)):
            row = [f"{freq[i]:.6f}", f"{grand_median[i]:.6f}",
                   f"{grand_std[i]:.6f}"]
            for a in array_names:
                if a in array_stats:
                    row.append(f"{array_stats[a]['median'][i]:.6f}")
                    row.append(f"{array_stats[a]['std'][i]:.6f}")
            writer.writerow(row)
    _log(f"  median/ -> {csv_combined_path}")

    for a in array_names:
        if a not in array_stats:
            continue
        safe_name = a.replace(" ", "_").replace("/", "_")
        csv_arr_path = os.path.join(median_dir, f"HVSR_Median_{safe_name}.csv")
        stn_list = [s for s in checked if s.topic == a
                    and len(s.mean_hvsr) == len(freq)]
        arr_header = ['Frequency_Hz', f'{a}_Median', f'{a}_Std']
        arr_header += [s.station_name for s in stn_list]
        with open(csv_arr_path, 'w', newline='') as f:
            writer = csv_mod.writer(f)
            writer.writerow(arr_header)
            for i in range(len(freq)):
                row = [f"{freq[i]:.6f}",
                       f"{array_stats[a]['median'][i]:.6f}",
                       f"{array_stats[a]['std'][i]:.6f}"]
                for s in stn_list:
                    row.append(f"{s.mean_hvsr[i]:.6f}")
                writer.writerow(row)
        _log(f"  median/ -> {csv_arr_path}")

    # ── JSON ──
    json_path = os.path.join(median_dir, "HVSR_Median_Combined.json")
    json_data = {
        "frequencies": freq.tolist(),
        "grand_median": grand_median.tolist(),
        "grand_std": grand_std.tolist(),
        "n_stations": stats['n_total'],
        "array_names": array_names,
        "arrays": {},
    }
    for a in array_names:
        if a in array_stats:
            json_data["arrays"][a] = {
                "median": array_stats[a]['median'].tolist(),
                "std": array_stats[a]['std'].tolist(),
                "n_stations": array_stats[a]['n_stations'],
                "station_names": array_stats[a]['station_names'],
            }
    with open(json_path, 'w') as f:
        json.dump(json_data, f, indent=2)
    _log(f"  median/ -> {json_path}")

    # ── MAT ──
    mat_path = os.path.join(median_dir, "HVSR_Median_Combined.mat")
    mat_data = {
        "Frequency": freq,
        "GrandMedian": grand_median,
        "GrandStd": grand_std,
        "n_stations": stats['n_total'],
    }
    for a in array_names:
        if a in array_stats:
            safe_key = a.replace(" ", "_").replace("-", "_")
            mat_data[f"{safe_key}_Median"] = array_stats[a]['median']
            mat_data[f"{safe_key}_Std"] = array_stats[a]['std']
    savemat(mat_path, mat_data)
    _log(f"  median/ -> {mat_path}")


def export_enhanced_curve(curves_dir: str, checked: list,
                          fig_settings: dict = None, log_fn=None):
    """Generate a large publication-quality HVSR curve figure."""
    from matplotlib.figure import Figure as MplFigure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from hvsr_pro.packages.batch_processing.dialogs.figure_export_settings import DEFAULT_SETTINGS

    _log = log_fn or (lambda msg: None)
    s = dict(DEFAULT_SETTINGS)
    if fig_settings:
        s.update(fig_settings)

    stats = compute_median_stats(checked)
    freq = stats['freq']
    array_names = stats['array_names']
    array_stats = stats['array_stats']

    from hvsr_pro.packages.batch_processing.widgets.results_canvas import ARRAY_COLORS, _station_color, _compute_smart_ylim

    fig = MplFigure(figsize=(s['curve_fig_w'], s['curve_fig_h']), dpi=300)
    canvas = FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)

    arrays = {}
    for sr in checked:
        arrays.setdefault(sr.topic, []).append(sr)

    for arr_idx, arr_name in enumerate(array_names):
        stations = arrays.get(arr_name, [])
        n = len(stations)
        for si, sr in enumerate(stations):
            color = _station_color(arr_idx, si, n)
            ax.plot(freq, sr.mean_hvsr, color=color, lw=0.8, alpha=0.6)

    for arr_idx, arr_name in enumerate(array_names):
        if arr_name not in array_stats:
            continue
        c = ARRAY_COLORS[arr_idx % len(ARRAY_COLORS)]
        med = array_stats[arr_name]['median']
        std = array_stats[arr_name]['std']
        ax.fill_between(freq, med - std, med + std, color=c, alpha=0.10)
        ax.plot(freq, med, color=c, lw=2.0, ls='--', label=f"{arr_name} Median")

    ax.fill_between(freq, stats['grand_median'] - stats['grand_std'],
                    stats['grand_median'] + stats['grand_std'],
                    color=s['curve_std_color'], alpha=s['curve_std_alpha'],
                    label='+-1 sigma')
    ax.plot(freq, stats['grand_median'], color=s['curve_grand_color'],
            lw=2.5, label='Grand Median')

    if s['curve_ylim_auto']:
        ylims = _compute_smart_ylim([sr.mean_hvsr for sr in checked], n_sigma=4)
        if ylims is not None:
            ax.set_ylim(*ylims)
    else:
        ax.set_ylim(s['curve_ylim_min'], s['curve_ylim_max'])

    ax.set_xscale('log')
    if not s['curve_xlim_auto']:
        ax.set_xlim(s['curve_xlim_min'], s['curve_xlim_max'])

    ax.set_xlabel(s['curve_xlabel'], fontsize=12)
    ax.set_ylabel(s['curve_ylabel'], fontsize=12)
    ax.set_title(s['curve_title'], fontsize=14)
    ax.grid(True, which='both', ls=':', alpha=0.4)
    ax.legend(fontsize=9, ncol=2, loc='upper right', frameon=True, framealpha=0.9)
    ax.tick_params(labelsize=10)
    fig.tight_layout()

    for ext in ('png', 'pdf'):
        out = os.path.join(curves_dir, f"HVSR_AllMedians_Enhanced.{ext}")
        fig.savefig(out, dpi=300, bbox_inches='tight')


def export_enhanced_histogram(hist_dir: str, checked: list,
                               fig_settings: dict = None, log_fn=None):
    """Generate a large publication-quality F0 histogram figure."""
    from matplotlib.figure import Figure as MplFigure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.ticker import MaxNLocator
    from hvsr_pro.packages.batch_processing.dialogs.figure_export_settings import DEFAULT_SETTINGS

    _log = log_fn or (lambda msg: None)
    s = dict(DEFAULT_SETTINGS)
    if fig_settings:
        s.update(fig_settings)

    all_f0 = []
    for sr in checked:
        peaks_sorted = sorted(sr.peaks, key=lambda p: p.frequency) if sr.peaks else []
        if peaks_sorted:
            all_f0.append(peaks_sorted[0].frequency)

    if not all_f0:
        return

    fig = MplFigure(figsize=(s['hist_fig_w'], s['hist_fig_h']), dpi=300)
    canvas = FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)

    if s['hist_xlim_auto']:
        f_min = min(all_f0) * 0.8
        f_max = max(all_f0) * 1.2
    else:
        f_min = s['hist_xlim_min']
        f_max = s['hist_xlim_max']

    n_bins = min(20, max(5, len(all_f0) // 2))
    bins = np.linspace(f_min, f_max, n_bins + 1)

    hist_kw = dict(bins=bins, linewidth=0.8, alpha=s['hist_alpha'])
    if s['hist_fill']:
        hist_kw.update(color=s['hist_color'], edgecolor=s['hist_edgecolor'])
    else:
        hist_kw.update(color='none', edgecolor=s['hist_color'], linewidth=1.5)
    ax.hist(all_f0, **hist_kw)

    mean_f = float(np.mean(all_f0))
    std_f = float(np.std(all_f0))
    ax.axvline(mean_f, color='black', ls='--', lw=2,
                label=f'Mean = {mean_f:.3f} +- {std_f:.3f} Hz')

    if not s['hist_xlim_auto']:
        ax.set_xlim(f_min, f_max)

    ax.set_xlabel(s['hist_xlabel'], fontsize=12)
    ax.set_ylabel(s['hist_ylabel'], fontsize=12)
    ax.set_title(s['hist_title'], fontsize=14)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.grid(True, axis='y', ls=':', alpha=0.4)
    ax.legend(fontsize=10, loc='upper right')
    ax.tick_params(labelsize=10)
    fig.tight_layout()

    for ext in ('png', 'pdf'):
        out = os.path.join(hist_dir, f"HVSR_F0_Histogram_Enhanced.{ext}")
        fig.savefig(out, dpi=300, bbox_inches='tight')


def detect_median_peaks(frequencies, median_hvsr, n_peaks=3,
                        hvsr_settings=None):
    """Detect peaks on the grand median HVSR curve.

    Parameters
    ----------
    frequencies : np.ndarray
        Frequency array (Hz).
    median_hvsr : np.ndarray
        Grand median HVSR curve.
    n_peaks : int
        Maximum number of peaks to return.
    hvsr_settings : dict, optional
        HVSR settings with freq_min, freq_max, min_prominence, etc.

    Returns
    -------
    list of Peak
        Detected peaks sorted by frequency (ascending).
    """
    from hvsr_pro.packages.batch_processing.processing import detect_peaks

    s = hvsr_settings or {}
    freq_min = s.get('freq_min', 0.2)
    freq_max = s.get('freq_max', 30.0)
    min_prom = s.get('min_prominence', 0.3)
    min_amp = s.get('min_amplitude', 1.0)

    peaks = detect_peaks(
        frequencies, median_hvsr,
        min_prominence=min_prom,
        min_amplitude=min_amp,
        freq_range=(freq_min, freq_max),
    )

    peaks.sort(key=lambda p: p.amplitude, reverse=True)
    peaks = peaks[:n_peaks]

    peaks.sort(key=lambda p: p.frequency)
    return peaks


def resample_to_log_grid(freq_orig, hvsr_orig, f_min, f_max, n_points):
    """Interpolate an HVSR curve onto a log-spaced frequency grid.

    Parameters
    ----------
    freq_orig : np.ndarray
        Original frequency array.
    hvsr_orig : np.ndarray
        Original HVSR curve.
    f_min, f_max : float
        Output frequency range.
    n_points : int
        Number of log-spaced points.

    Returns
    -------
    new_freq : np.ndarray
    new_hvsr : np.ndarray
    """
    new_freq = np.logspace(np.log10(f_min), np.log10(f_max), n_points)
    new_hvsr = np.interp(new_freq, freq_orig, hvsr_orig)
    return new_freq, new_hvsr


def export_median_json_hvsr_format(output_path: str, checked: list,
                                   n_peaks: int = 3,
                                   hvsr_settings: dict = None,
                                   manual_peaks: list = None,
                                   log_fn=None) -> str:
    """Export grand median curve as JSON in hvsr_pro-compatible format.

    The output format matches the structure of hvsr_pro's
    ``HVSRResult.to_dict()`` so it can be loaded back with
    ``HVSRResult.load()``.

    Parameters
    ----------
    output_path : str
        Destination JSON file path.
    checked : list
        List of StationResult objects.
    n_peaks : int
        Number of peaks to detect on the median curve.
    hvsr_settings : dict, optional
        HVSR processing settings (freq_min, freq_max, n_frequencies, etc.).
    manual_peaks : list, optional
        Manually selected peaks as list of dicts with 'frequency' and
        'amplitude' keys.  When provided, auto-detection is skipped.
    log_fn : callable, optional

    Returns
    -------
    str
        Path to the written JSON file.
    """
    from datetime import datetime

    _log = log_fn or (lambda msg: None)

    if not checked:
        _log("Warning: No station results to export.")
        return ""

    s = hvsr_settings or {}
    f_min = s.get('freq_min', 0.5)
    f_max = s.get('freq_max', 25.0)
    n_freq = s.get('n_frequencies', 100)

    out_freq = np.logspace(np.log10(f_min), np.log10(f_max), n_freq)

    orig_freq = checked[0].frequencies
    mean_stack = []
    median_stack = []
    std_stack = []
    for sr in checked:
        if len(sr.mean_hvsr) == len(orig_freq):
            _, res_mean = resample_to_log_grid(
                orig_freq, sr.mean_hvsr, f_min, f_max, n_freq)
            mean_stack.append(res_mean)
            med_curve = getattr(sr, 'median_hvsr', None)
            if med_curve is not None and len(med_curve) == len(orig_freq):
                _, res_med = resample_to_log_grid(
                    orig_freq, med_curve, f_min, f_max, n_freq)
                median_stack.append(res_med)
            else:
                median_stack.append(res_mean)
            std_curve = getattr(sr, 'std_hvsr', None)
            if std_curve is not None and len(std_curve) == len(orig_freq):
                _, res_std = resample_to_log_grid(
                    orig_freq, std_curve, f_min, f_max, n_freq)
                std_stack.append(res_std)

    if not mean_stack:
        _log("Warning: No valid curves to interpolate.")
        return ""

    mean_arr = np.array(mean_stack)
    median_arr = np.array(median_stack)
    grand_mean = np.mean(mean_arr, axis=0)
    grand_median = np.median(median_arr, axis=0)
    if std_stack:
        grand_std = np.median(np.array(std_stack), axis=0)
    else:
        grand_std = np.std(median_arr, axis=0)
    pct_16 = np.percentile(median_arr, 16, axis=0)
    pct_84 = np.percentile(median_arr, 84, axis=0)
    valid_w = sum(getattr(sr, 'valid_windows', 0) for sr in checked)
    total_w = sum(getattr(sr, 'total_windows', 0) for sr in checked)

    if manual_peaks:
        peaks_list = _format_manual_peaks(manual_peaks)
        peak_source = "manual"
    else:
        peaks = detect_median_peaks(out_freq, grand_median,
                                    n_peaks=n_peaks, hvsr_settings=s)
        peaks_list = _format_auto_peaks(peaks)
        peak_source = "auto"

    json_data = {
        "frequencies": out_freq.tolist(),
        "mean_hvsr": grand_mean.tolist(),
        "median_hvsr": grand_median.tolist(),
        "std_hvsr": grand_std.tolist(),
        "percentile_16": pct_16.tolist(),
        "percentile_84": pct_84.tolist(),
        "valid_windows": int(valid_w),
        "total_windows": int(total_w),
        "acceptance_rate": float(valid_w / total_w) if total_w > 0 else 0.0,
        "peaks": peaks_list,
        "processing_params": {
            "smoothing_bandwidth": float(s.get('smoothing_bw', 40.0)),
            "f_min": float(f_min),
            "f_max": float(f_max),
            "n_frequencies": n_freq,
            "horizontal_method": s.get('averaging', 'geometric_mean'),
            "taper": s.get('taper', 'hann'),
            "use_only_active": True,
        },
        "timestamp": datetime.now().isoformat(),
        "metadata": {
            "station_names": [sr.station_name for sr in checked],
            "n_stations": len(checked),
            "array_names": sorted(set(sr.topic for sr in checked)),
            "n_peaks_requested": n_peaks,
            "peak_source": peak_source,
        },
    }

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(json_data, f, indent=2)

    _log(f"  median/ -> {output_path} (hvsr_pro format, {len(peaks_list)} peaks, {peak_source})")
    return output_path


def _format_manual_peaks(manual_peaks: list) -> list:
    """Convert manual peak dicts to the JSON peaks list format."""
    result = []
    for i, pk in enumerate(manual_peaks):
        label = "primary" if i == 0 else f"secondary_{i}"
        result.append({
            'frequency': float(pk['frequency']),
            'amplitude': float(pk['amplitude']),
            'label': label,
        })
    return result


def _format_auto_peaks(peaks: list) -> list:
    """Convert auto-detected Peak objects to the JSON peaks list format."""
    result = []
    for i, pk in enumerate(peaks):
        label = "primary" if i == 0 else f"secondary_{i}"
        result.append({
            'frequency': float(pk.frequency),
            'amplitude': float(pk.amplitude),
            'prominence': float(pk.prominence),
            'width': float(pk.width),
            'left_freq': float(pk.left_freq),
            'right_freq': float(pk.right_freq),
            'quality': float(pk.quality),
            'label': label,
        })
    return result
