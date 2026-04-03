"""
Batch Processing API — Figure Generation Engine
================================================

Headless matplotlib figure generation for batch HVSR results.

Per-station figures:
    - Standard window-curves figure
    - hvsr_pro HVSR curve
    - Statistics 4-panel
    - All detailed figure types from FigureExportDialog

Combined figures:
    - All-station median curves
    - Enhanced publication curves
    - F0 histogram
    - Enhanced histogram

Delegates per-station rendering to ``figure_gen.py`` and combined
rendering to ``report_export.py``, wrapping them with a clean API.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from ..processing.automatic_workflow import (
    AutomaticWorkflowResult,
    StationResult,
)
from .hvsr_engine import StationHVSRResult

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────
# Per-station figure generation
# ────────────────────────────────────────────────────────────────────

# Available per-station figure types
PER_STATION_FIGURE_TYPES = [
    "standard",           # Window curves + mean + peaks
    "hvsr_pro",           # Clean hvsr_pro HVSR curve
    "statistics",         # 4-panel statistics
    "hvsr_curve",         # HVSR with uncertainty
    "mean_vs_median",     # Mean vs median comparison
    "components",         # Component spectra
    "peak_analysis",      # Peak analysis detail
    "window_overview",    # Window collection overview
    "quality_grid",       # Quality metrics grid
    "rejection_timeline", # Rejection timeline
    "raw_vs_adjusted",    # Raw vs adjusted HVSR
    "pre_post_rejection", # Pre & post rejection waveform
    "waveform_3c",        # 3-component waveform
    "dashboard",          # Composite dashboard
    "peak_details",       # Peak detail view
    "with_windows",       # HVSR with individual windows
    "quality_histogram",  # Quality score distribution
    "window_timeseries",  # Window time series
    "window_spectrogram", # Window spectrogram
]

# Figures that require hvsr_pro visualization objects
_HVSR_PRO_FIGURE_TYPES = {
    "hvsr_pro", "statistics", "hvsr_curve", "mean_vs_median",
    "components", "peak_analysis", "window_overview", "quality_grid",
    "rejection_timeline", "raw_vs_adjusted", "pre_post_rejection",
    "waveform_3c", "dashboard", "peak_details", "with_windows",
    "quality_histogram", "window_timeseries", "window_spectrogram",
}

# All available per-station figure config keys
ALL_FIGURE_CONFIG_KEYS = [
    "fig_hvsr_curve",
    "fig_mean_vs_median",
    "fig_components",
    "fig_peak_analysis",
    "fig_window_overview",
    "fig_quality_grid",
    "fig_rejection_timeline",
    "fig_raw_vs_adjusted",
    "fig_pre_post_rejection",
    "fig_waveform_3c",
    "fig_dashboard",
    "fig_peak_details",
    "fig_with_windows",
    "fig_quality_histogram",
    "fig_window_timeseries",
    "fig_window_spectrogram",
]


def default_figure_config(all_enabled: bool = True) -> dict:
    """
    Return the default figure configuration dict.

    Parameters
    ----------
    all_enabled : bool
        If True, all figure types are enabled. If False, all disabled.
    """
    config = {
        "dpi": 300,
        "format": "png",
        "figsize": "Standard (10x7)",
        "auto_ylim": True,
        "ylim_method": "95th Percentile",
    }
    for key in ALL_FIGURE_CONFIG_KEYS:
        config[key] = all_enabled
    return config


def generate_station_figures(
    hvsr_result: StationHVSRResult,
    output_dir: str,
    figure_types: Optional[List[str]] = None,
    dpi: int = 300,
    save_png: bool = True,
    save_pdf: bool = False,
    fig_config: Optional[dict] = None,
) -> Dict[str, str]:
    """
    Generate all requested figures for a single station.

    Parameters
    ----------
    hvsr_result : StationHVSRResult
        Per-station HVSR result from the engine.
    output_dir : str
        Directory to save figures.
    figure_types : list[str], optional
        Which figure types to generate. If None, generates
        standard + hvsr_pro + statistics.
    dpi : int
        Figure resolution.
    save_png, save_pdf : bool
        Output formats.
    fig_config : dict, optional
        Detailed figure configuration. If not provided, defaults are
        used with figure_types determining which are enabled.

    Returns
    -------
    dict[str, str]
        Figure type → file path.
    """
    from ..figure_gen import generate_hvsr_figures, build_hvsr_pro_objects

    os.makedirs(output_dir, exist_ok=True)

    if figure_types is None:
        figure_types = ["standard", "hvsr_pro", "statistics"]

    # Build figure config from types
    if fig_config is None:
        fig_config = default_figure_config(all_enabled=False)
        for ft in figure_types:
            key = f"fig_{ft}"
            if key in fig_config:
                fig_config[key] = True

    fig_config["dpi"] = dpi
    fig_config.setdefault("format", "png")
    fig_config.setdefault("figsize", "Standard (10x7)")

    # Extract data arrays
    freq_ref = hvsr_result.frequencies
    hv_mean = hvsr_result.mean_hvsr
    hv_std = hvsr_result.std_hvsr
    hv_median = hvsr_result.median_hvsr
    hv_16 = hvsr_result.percentile_16
    hv_84 = hvsr_result.percentile_84
    peaks = list(hvsr_result.peaks)

    hv_mean_plus_std = hv_mean + hv_std
    hv_mean_minus_std = np.maximum(hv_mean - hv_std, 0)

    # combined_hv matrix and rejection info
    combined_hv = hvsr_result.per_window_hvsr
    rejected_mask = hvsr_result.rejected_mask
    n_windows = hvsr_result.total_windows

    if combined_hv is None or len(combined_hv) == 0:
        logger.warning("No per-window HVSR data for figures")
        return {}

    # Convert list of arrays to 2-D numpy array
    if isinstance(combined_hv, list):
        combined_hv = np.column_stack(combined_hv)  # (n_freq, n_windows)

    # Ensure combined_hv is (n_freq, n_windows) shape
    if combined_hv.ndim == 2:
        if combined_hv.shape[0] != len(freq_ref):
            combined_hv = combined_hv.T
    else:
        logger.warning("Unexpected combined_hv shape: %s", combined_hv.shape)
        return {}

    if rejected_mask is None:
        rejected_mask = np.zeros(n_windows, dtype=bool)

    # per_window_hvsr may only contain valid windows (not all n_windows).
    # Build accepted_indices relative to combined_hv's actual column count.
    # Also fix rejected_mask to match combined_hv columns so the figure
    # renderer correctly plots ALL valid curves (not skipping them).
    n_valid = combined_hv.shape[1]
    if n_valid < n_windows:
        accepted_indices = list(range(n_valid))
        # combined_hv only has valid windows — mark none as rejected
        rejected_mask = np.zeros(n_valid, dtype=bool)
    else:
        accepted_indices = [i for i in range(n_windows) if not rejected_mask[i]]

    # Build hvsr_pro objects for detailed figures
    hvsr_result_obj = None
    window_collection = None
    seismic_data = None

    if any(ft in _HVSR_PRO_FIGURE_TYPES for ft in figure_types):
        try:
            hvsr_result_obj, window_collection, seismic_data = (
                _build_hvsr_pro_objects_from_engine_result(hvsr_result)
            )
        except Exception as exc:
            logger.warning("Could not build hvsr_pro objects: %s", exc)

    fig_label = hvsr_result.station_name.replace(" ", "_")
    fig_title = f"HVSR - {hvsr_result.station_name}"

    # Delegate to existing generator
    n_saved = generate_hvsr_figures(
        hvsr_result_obj=hvsr_result_obj,
        window_collection=window_collection,
        seismic_data=seismic_data,
        peaks=peaks,
        freq_ref=freq_ref,
        hv_mean=hv_mean,
        hv_std=hv_std,
        hv_mean_plus_std=hv_mean_plus_std,
        hv_mean_minus_std=hv_mean_minus_std,
        hv_16=hv_16,
        hv_84=hv_84,
        combined_hv=combined_hv,
        rejected_mask=rejected_mask,
        accepted_indices=accepted_indices,
        n_windows=n_windows,
        output_dir=output_dir,
        fig_label=fig_label,
        fig_title=fig_title,
        fig_config=fig_config,
        fig_standard="standard" in figure_types,
        fig_hvsr_pro="hvsr_pro" in figure_types,
        fig_statistics="statistics" in figure_types,
        save_png=save_png,
        save_pdf=save_pdf,
        dpi=dpi,
    )

    # Collect generated files
    files = {}
    out = Path(output_dir)
    for f in out.iterdir():
        if f.is_file() and f.stem.startswith("HVSR_"):
            files[f.stem] = str(f)

    logger.info("Station %s: %d figures generated", hvsr_result.station_name, len(files))
    return files


def _build_hvsr_pro_objects_from_engine_result(
    hvsr_result: StationHVSRResult,
):
    """
    Build hvsr_pro visualization objects from engine result.

    Returns (HVSRResult, WindowCollection, SeismicData) or (None, None, None).
    """
    from ..figure_gen import build_hvsr_pro_objects

    freq_ref = hvsr_result.frequencies
    hv_mean = hvsr_result.mean_hvsr
    hv_median = hvsr_result.median_hvsr
    hv_std = hvsr_result.std_hvsr
    hv_16 = hvsr_result.percentile_16
    hv_84 = hvsr_result.percentile_84
    peaks = list(hvsr_result.peaks)
    combined_hv = hvsr_result.per_window_hvsr
    rejected_mask = hvsr_result.rejected_mask
    n_windows = hvsr_result.total_windows

    # Convert list of arrays to 2-D numpy array
    if isinstance(combined_hv, list) and len(combined_hv) > 0:
        combined_hv = np.column_stack(combined_hv)  # (n_freq, n_windows)

    if combined_hv is not None and hasattr(combined_hv, 'ndim') and combined_hv.ndim == 2:
        if combined_hv.shape[0] != len(freq_ref):
            combined_hv = combined_hv.T

    if rejected_mask is None:
        rejected_mask = np.zeros(n_windows, dtype=bool)

    n_valid = combined_hv.shape[1] if (combined_hv is not None and hasattr(combined_hv, 'shape') and combined_hv.ndim == 2) else 0
    if n_valid > 0 and n_valid < n_windows:
        accepted_indices = list(range(n_valid))
        # Keep original rejected_mask at full length (n_windows) — needed by
        # build_hvsr_pro_objects which loops over n_windows to build
        # WindowCollection entries.  Pad combined_hv with zero columns so
        # its column count matches n_windows for the hvsr_pro builder.
        pad_cols = n_windows - n_valid
        combined_hv = np.hstack([combined_hv, np.zeros((combined_hv.shape[0], pad_cols))])
    else:
        accepted_indices = [i for i in range(n_windows) if not rejected_mask[i]]
    rejected_reasons = hvsr_result.rejected_reasons or [""] * n_windows

    # Extract raw arrays from seismic data if available
    seismic = hvsr_result.seismic_data
    if seismic is not None:
        array_e = seismic.east.data if hasattr(seismic, "east") else np.array([])
        array_n = seismic.north.data if hasattr(seismic, "north") else np.array([])
        array_z = seismic.vertical.data if hasattr(seismic, "vertical") else np.array([])
        sample_rate = seismic.sampling_rate
    else:
        array_e = np.array([])
        array_n = np.array([])
        array_z = np.array([])
        sample_rate = 100.0

    # Per-window samples
    if sample_rate > 0 and hvsr_result.window_length > 0:
        n_per_win = int(sample_rate * hvsr_result.window_length)
    else:
        n_per_win = len(array_z) // max(n_windows, 1)

    # Cap n_windows to what the raw data can actually support
    if n_per_win > 0 and len(array_z) > 0:
        max_complete_windows = len(array_z) // n_per_win
        if n_windows > max_complete_windows:
            n_windows = max_complete_windows
            # Trim rejected_mask and rejected_reasons to match
            rejected_mask = rejected_mask[:n_windows]
            rejected_reasons = rejected_reasons[:n_windows]
            # Ensure combined_hv has at least n_windows columns
            if combined_hv.shape[1] > n_windows:
                combined_hv = combined_hv[:, :n_windows]

    return build_hvsr_pro_objects(
        freq_ref=freq_ref,
        hv_mean=hv_mean,
        hv_median=hv_median,
        hv_std=hv_std,
        hv_16=hv_16,
        hv_84=hv_84,
        peaks=peaks,
        combined_hv=combined_hv,
        accepted_indices=accepted_indices,
        n_windows=n_windows,
        rejected_mask=rejected_mask,
        rejected_reasons=rejected_reasons,
        array_e=array_e,
        array_n=array_n,
        array_z=array_z,
        sample_rate=sample_rate,
        n_per_win=n_per_win,
        fig_label=hvsr_result.station_name,
        time_win_sec=hvsr_result.window_length,
    )


# ────────────────────────────────────────────────────────────────────
# Combined / batch-level figures
# ────────────────────────────────────────────────────────────────────

# Available combined figure types
COMBINED_FIGURE_TYPES = [
    "all_medians",        # Basic all-station medians
    "enhanced_curves",    # Publication-quality enhanced curves
    "histogram",          # Basic F0 histogram
    "enhanced_histogram", # Publication-quality enhanced histogram
]


def generate_combined_figures(
    station_results: List[StationResult],
    output_dir: str,
    figure_types: Optional[List[str]] = None,
    dpi: int = 300,
    fig_settings: Optional[dict] = None,
) -> Dict[str, str]:
    """
    Generate combined/batch-level figures.

    Parameters
    ----------
    station_results : list[StationResult]
    output_dir : str
    figure_types : list[str], optional
        Which combined figures. Default: all types.
    dpi : int
    fig_settings : dict, optional
        Figure export settings overrides.

    Returns
    -------
    dict[str, str]
        Figure type → file path.
    """
    from ..report_export import (
        compute_median_stats,
        export_enhanced_curve,
        export_enhanced_histogram,
    )

    if figure_types is None:
        figure_types = list(COMBINED_FIGURE_TYPES)

    os.makedirs(output_dir, exist_ok=True)
    files = {}

    def _log(msg):
        logger.info(msg)

    # Basic all-medians
    if "all_medians" in figure_types:
        try:
            stats = compute_median_stats(station_results)
            _generate_basic_curves(station_results, stats, output_dir, dpi)
            files["all_medians"] = os.path.join(output_dir, "HVSR_AllMedians.png")
        except Exception as exc:
            logger.error("All medians figure failed: %s", exc)

    # Enhanced publication curves
    if "enhanced_curves" in figure_types:
        try:
            export_enhanced_curve(output_dir, station_results,
                                  fig_settings=fig_settings, log_fn=_log)
            files["enhanced_curves"] = os.path.join(
                output_dir, "HVSR_AllMedians_Enhanced.png",
            )
        except Exception as exc:
            logger.error("Enhanced curves figure failed: %s", exc)

    # Basic F0 histogram
    if "histogram" in figure_types:
        try:
            _generate_basic_histogram(station_results, output_dir, dpi)
            files["histogram"] = os.path.join(
                output_dir, "HVSR_F0_Histogram.png",
            )
        except Exception as exc:
            logger.error("Basic histogram failed: %s", exc)

    # Enhanced publication histogram
    if "enhanced_histogram" in figure_types:
        try:
            export_enhanced_histogram(output_dir, station_results,
                                      fig_settings=fig_settings, log_fn=_log)
            files["enhanced_histogram"] = os.path.join(
                output_dir, "HVSR_F0_Histogram_Enhanced.png",
            )
        except Exception as exc:
            logger.error("Enhanced histogram failed: %s", exc)

    logger.info("Combined figures: %d generated in %s", len(files), output_dir)
    return files


def generate_batch_station_figures(
    hvsr_results: List[StationHVSRResult],
    output_dir: str,
    figure_types: Optional[List[str]] = None,
    dpi: int = 300,
    save_png: bool = True,
    save_pdf: bool = False,
    fig_config: Optional[dict] = None,
    progress_callback=None,
) -> Dict[str, Dict[str, str]]:
    """
    Generate figures for all stations in a batch.

    Parameters
    ----------
    hvsr_results : list[StationHVSRResult]
    output_dir : str
        Root output directory. Each station gets a subdirectory.
    figure_types : list[str], optional
    dpi : int
    save_png, save_pdf : bool
    fig_config : dict, optional
    progress_callback : callable(int, str), optional

    Returns
    -------
    dict[str, dict[str, str]]
        Station name → {figure_type → file_path}.
    """
    all_files = {}
    total = len(hvsr_results)

    for idx, hr in enumerate(hvsr_results):
        if not hr.success:
            continue

        station_dir = os.path.join(output_dir, hr.station_name)
        try:
            files = generate_station_figures(
                hr, station_dir,
                figure_types=figure_types,
                dpi=dpi, save_png=save_png, save_pdf=save_pdf,
                fig_config=fig_config,
            )
            all_files[hr.station_name] = files
        except Exception as exc:
            logger.error("Figures for %s failed: %s", hr.station_name, exc)
            all_files[hr.station_name] = {"error": str(exc)}

        if progress_callback:
            progress_callback(
                int((idx + 1) / total * 100),
                f"Figures: {hr.station_name}",
            )

    logger.info("Batch figures: %d stations processed", len(all_files))
    return all_files


# ────────────────────────────────────────────────────────────────────
# Internal helpers (basic figures, no external Qt deps)
# ────────────────────────────────────────────────────────────────────

def _generate_basic_curves(
    checked: List[StationResult],
    stats: dict,
    output_dir: str,
    dpi: int = 300,
):
    """Basic all-medians curves figure (matplotlib Agg only)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    freq = stats["freq"]
    fig, ax = plt.subplots(figsize=(10, 7))

    for sr in checked:
        if len(sr.mean_hvsr) == len(freq):
            ax.semilogx(freq, sr.mean_hvsr, alpha=0.4, linewidth=0.8)

    ax.semilogx(freq, stats["grand_median"], "k-", linewidth=2.5, label="Grand Median")
    ax.fill_between(
        freq,
        stats["grand_median"] - stats["grand_std"],
        stats["grand_median"] + stats["grand_std"],
        alpha=0.2, color="gray", label="±1σ",
    )

    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("H/V Ratio")
    ax.set_title("HVSR All Station Medians")
    ax.legend()
    ax.grid(True, which="both", alpha=0.3)
    fig.tight_layout()

    for ext in ("png", "pdf"):
        fig.savefig(
            os.path.join(output_dir, f"HVSR_AllMedians.{ext}"),
            dpi=dpi, bbox_inches="tight",
        )
    plt.close(fig)


def _generate_basic_histogram(
    checked: List[StationResult],
    output_dir: str,
    dpi: int = 300,
):
    """Basic F0 histogram figure (matplotlib Agg only)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    all_f0 = []
    for sr in checked:
        if sr.peaks:
            primary = max(sr.peaks, key=lambda p: p.amplitude)
            all_f0.append(primary.frequency)

    if not all_f0:
        return

    fig, ax = plt.subplots(figsize=(8, 5))
    n_bins = min(20, max(5, len(all_f0) // 2))
    ax.hist(all_f0, bins=n_bins, edgecolor="black", alpha=0.7)

    mean_f = float(np.mean(all_f0))
    ax.axvline(mean_f, color="red", linestyle="--", linewidth=2,
               label=f"Mean = {mean_f:.3f} Hz")

    ax.set_xlabel("Fundamental Frequency (Hz)")
    ax.set_ylabel("Count")
    ax.set_title("F0 Histogram")
    ax.legend()
    fig.tight_layout()

    for ext in ("png", "pdf"):
        fig.savefig(
            os.path.join(output_dir, f"HVSR_F0_Histogram.{ext}"),
            dpi=dpi, bbox_inches="tight",
        )
    plt.close(fig)
