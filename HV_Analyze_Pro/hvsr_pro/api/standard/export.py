"""
Export Helpers
==============

Pure functions for saving results, plots, and comprehensive reports.
No class state -- each function receives the objects it needs.
"""
from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Comparison / waveform helper plots
# ------------------------------------------------------------------

def _plot_waveform_rejection(windows, data) -> "Figure":
    """3-panel (E/N/Z) waveform with green/gray window rejection overlay."""
    import numpy as np
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(3, 1, figsize=(14, 8), sharex=True)
    components = [
        ("East",     data.east.data,     "#1976D2"),
        ("North",    data.north.data,    "#388E3C"),
        ("Vertical", data.vertical.data, "#D32F2F"),
    ]
    sr = data.east.sampling_rate
    t = np.arange(len(data.east.data)) / sr

    for ax, (label, waveform, color) in zip(axes, components):
        ax.plot(t, waveform, color=color, linewidth=0.3, alpha=0.8)
        ax.set_ylabel(label, fontsize=10)
        ax.tick_params(labelsize=9)

        for w in windows.windows:
            s = int(w.start_sample)
            e = min(int(w.end_sample), len(waveform))
            if s >= len(waveform):
                continue
            c = "#4CAF50" if w.is_active() else "#9E9E9E"
            a = 0.15 if w.is_active() else 0.25
            ax.axvspan(s / sr, e / sr, color=c, alpha=a)

    axes[-1].set_xlabel("Time (s)", fontsize=10)
    axes[0].set_title("3-Component Waveform — Window Rejection Overlay", fontsize=12)

    # Legend
    from matplotlib.patches import Patch
    axes[0].legend(
        handles=[Patch(facecolor="#4CAF50", alpha=0.3, label="Active"),
                 Patch(facecolor="#9E9E9E", alpha=0.4, label="Rejected")],
        loc="upper right", fontsize=9,
    )
    fig.tight_layout()
    return fig


def _plot_pre_post_rejection(windows, data, raw_result, final_result) -> "Figure":
    """5-panel composite: left=3C waveforms, right top=pre-QC HVSR, right bottom=post-QC."""
    import numpy as np
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    fig = plt.figure(figsize=(16, 10))
    gs = fig.add_gridspec(3, 2, width_ratios=[1.2, 1], hspace=0.35, wspace=0.3)

    sr = data.east.sampling_rate
    t = np.arange(len(data.east.data)) / sr
    components = [
        ("East",     data.east.data,     "#1976D2"),
        ("North",    data.north.data,    "#388E3C"),
        ("Vertical", data.vertical.data, "#D32F2F"),
    ]

    # Left: 3 waveform panels
    for row, (label, waveform, color) in enumerate(components):
        ax = fig.add_subplot(gs[row, 0])
        ax.plot(t, waveform, color=color, linewidth=0.3, alpha=0.8)
        ax.set_ylabel(label, fontsize=9)
        ax.tick_params(labelsize=8)
        for w in windows.windows:
            s, e = int(w.start_sample), min(int(w.end_sample), len(waveform))
            if s >= len(waveform):
                continue
            c = "#4CAF50" if w.is_active() else "#9E9E9E"
            a = 0.15 if w.is_active() else 0.25
            ax.axvspan(s / sr, e / sr, color=c, alpha=a)
        if row == 0:
            ax.set_title("3C Waveform with Window Rejection", fontsize=11)
            ax.legend(
                handles=[Patch(facecolor="#4CAF50", alpha=0.3, label="Active"),
                         Patch(facecolor="#9E9E9E", alpha=0.4, label="Rejected")],
                loc="upper right", fontsize=8,
            )
        if row == 2:
            ax.set_xlabel("Time (s)", fontsize=9)

    # Right top: Pre-QC HVSR
    ax_pre = fig.add_subplot(gs[0:2, 1])
    ax_pre.semilogx(raw_result.frequencies, raw_result.median_hvsr,
                     color="#FF6F00", linewidth=1.5, label="Pre-QC Median")
    ax_pre.fill_between(raw_result.frequencies, raw_result.percentile_16,
                         raw_result.percentile_84, color="#FF6F00", alpha=0.15)
    ax_pre.axhline(1, color="gray", linestyle="--", alpha=0.5)
    pk = raw_result.primary_peak
    if pk:
        ax_pre.axvline(pk.frequency, color="#FF6F00", linestyle=":", alpha=0.6)
        ax_pre.annotate(f"{pk.frequency:.2f} Hz", xy=(pk.frequency, pk.amplitude),
                         fontsize=9, color="#E65100")
    ax_pre.set_ylabel("H/V Ratio", fontsize=9)
    ax_pre.set_title(f"Pre-QC HVSR ({raw_result.total_windows} windows)", fontsize=10)
    ax_pre.legend(fontsize=8)
    ax_pre.grid(True, alpha=0.3)

    # Right bottom: Post-QC HVSR
    ax_post = fig.add_subplot(gs[2, 1])
    ax_post.semilogx(final_result.frequencies, final_result.median_hvsr,
                      color="#D32F2F", linewidth=1.5, label="Post-QC Median")
    ax_post.fill_between(final_result.frequencies, final_result.percentile_16,
                          final_result.percentile_84, color="#D32F2F", alpha=0.15)
    ax_post.axhline(1, color="gray", linestyle="--", alpha=0.5)
    pk2 = final_result.primary_peak
    if pk2:
        ax_post.axvline(pk2.frequency, color="#D32F2F", linestyle=":", alpha=0.6)
        ax_post.annotate(f"{pk2.frequency:.2f} Hz", xy=(pk2.frequency, pk2.amplitude),
                          fontsize=9, color="#B71C1C")
    ax_post.set_xlabel("Frequency (Hz)", fontsize=9)
    ax_post.set_ylabel("H/V Ratio", fontsize=9)
    ax_post.set_title(f"Post-QC HVSR ({final_result.valid_windows} windows)", fontsize=10)
    ax_post.legend(fontsize=8)
    ax_post.grid(True, alpha=0.3)

    fig.suptitle("Pre/Post QC Rejection Analysis", fontsize=13, fontweight="bold")
    return fig


# ------------------------------------------------------------------
# Single-file exports
# ------------------------------------------------------------------

def save_results(
    result,       # AnalysisResult
    config,       # HVSRAnalysisConfig
    output_path: Union[str, Path],
    fmt: str = "json",
) -> None:
    """Save HVSR curves to *output_path* (``json``, ``csv``, or ``mat``)."""
    if result is None or result.hvsr_result is None:
        raise ValueError("No results to save. Call process() first.")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    r = result.hvsr_result

    if fmt == "json":
        payload = {
            "config": config.to_dict(),
            "summary": result.get_summary(),
            "frequencies": r.frequencies.tolist(),
            "mean_hvsr": r.mean_hvsr.tolist(),
            "median_hvsr": r.median_hvsr.tolist(),
            "std_hvsr": r.std_hvsr.tolist(),
            "percentile_16": r.percentile_16.tolist(),
            "percentile_84": r.percentile_84.tolist(),
            "peaks": [
                {"frequency": pk.frequency, "amplitude": pk.amplitude}
                for pk in (r.peaks or [])
            ],
        }
        with open(output_path, "w") as f:
            json.dump(payload, f, indent=2)
    elif fmt == "csv":
        with open(output_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["frequency", "mean_hvsr", "median_hvsr",
                             "std_hvsr", "percentile_16", "percentile_84"])
            for i in range(len(r.frequencies)):
                writer.writerow([
                    r.frequencies[i], r.mean_hvsr[i], r.median_hvsr[i],
                    r.std_hvsr[i], r.percentile_16[i], r.percentile_84[i],
                ])
    elif fmt == "mat":
        from scipy.io import savemat

        mat: Dict[str, Any] = {
            "frequency": r.frequencies,
            "mean_hvsr": r.mean_hvsr,
            "median_hvsr": r.median_hvsr,
            "std_hvsr": r.std_hvsr,
            "percentile_16": r.percentile_16,
            "percentile_84": r.percentile_84,
            "total_windows": r.total_windows,
            "valid_windows": r.valid_windows,
        }
        pk = r.primary_peak
        if pk:
            mat["peak_frequency"] = pk.frequency
            mat["peak_amplitude"] = pk.amplitude
        savemat(str(output_path), mat)
    else:
        raise ValueError(f"Unknown format: {fmt}")


def save_plot(
    result,       # AnalysisResult
    windows,      # WindowCollection | None
    output_path: Union[str, Path],
    plot_type: str = "hvsr",
    dpi: int = 150,
    show_median: bool = True,
    show_mean: bool = False,
    data=None,    # SeismicData | None — needed for timeseries/spectrogram
    style=None,   # PlotStyleConfig | None
    raw_result=None,  # HVSRResult | None — pre-QC result for comparison
) -> None:
    """Render and save a single plot to *output_path*.
    
    Supported plot_type values:
        hvsr, windows, quality, statistics, dashboard,
        mean_vs_median, quality_histogram, selected_metrics,
        window_timeline, window_timeseries, window_spectrogram,
        peak_analysis, raw_vs_adjusted, waveform_rejection,
        pre_post_rejection
    """
    if result is None or result.hvsr_result is None:
        raise ValueError("No results to plot. Call process() first.")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from hvsr_pro.visualization import HVSRPlotter

    # Merge explicit args with PlotStyleConfig (explicit args win)
    if style is not None:
        dpi = dpi if dpi != 150 else style.dpi
        show_median = show_median if show_median != True else style.show_median
        show_mean = show_mean if show_mean != False else style.show_mean

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plotter = HVSRPlotter()
    r = result.hvsr_result

    fig = None
    if plot_type == "hvsr":
        fig = plotter.plot_result(r, show_peaks=True,
                                  show_median=show_median, show_mean=show_mean)
    elif plot_type == "windows" and r.window_spectra:
        fig = plotter.plot_with_windows(r)
    elif plot_type == "quality" and windows:
        fig = plotter.plot_quality_metrics(windows)
    elif plot_type == "statistics":
        fig = plotter.plot_statistics(r)
    elif plot_type == "dashboard" and windows:
        fig = plotter.plot_dashboard(r, windows)
    elif plot_type == "mean_vs_median":
        fig = plotter.plot_mean_vs_median(r)
    elif plot_type == "quality_histogram" and windows:
        fig = plotter.plot_quality_histogram(windows)
    elif plot_type == "selected_metrics" and windows:
        fig = plotter.plot_selected_metrics(windows)
    elif plot_type == "window_timeline" and windows:
        fig = plotter.plot_timeline(windows)
    elif plot_type == "window_timeseries" and windows:
        fig = plotter.plot_window_timeseries(windows, data)
    elif plot_type == "window_spectrogram" and windows:
        fig = plotter.plot_window_spectrogram(windows, data)
    elif plot_type == "peak_analysis" and r.primary_peak:
        fig = plotter.plot_peak_details(r)
    elif plot_type == "raw_vs_adjusted" and raw_result is not None:
        fig = plotter.plot_comparison(
            [raw_result, r],
            ["Pre-QC (Raw)", "Post-QC (Adjusted)"],
            title="Raw vs Adjusted HVSR",
        )
    elif plot_type == "waveform_rejection" and windows and data is not None:
        fig = _plot_waveform_rejection(windows, data)
    elif plot_type == "pre_post_rejection" and windows and data is not None and raw_result is not None:
        fig = _plot_pre_post_rejection(windows, data, raw_result, r)
    
    if fig is None:
        raise ValueError(f"Unknown or unavailable plot type: {plot_type}")

    fig.savefig(output_path, dpi=dpi, bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------
# Full report
# ------------------------------------------------------------------

def generate_report(
    result,       # AnalysisResult
    windows,      # WindowCollection | None
    config,       # HVSRAnalysisConfig
    output_dir: Union[str, Path],
    base_name: str = "hvsr",
    dpi: int = 150,
    data=None,    # SeismicData | None — for timeseries/spectrogram plots
    raw_result=None,  # HVSRResult | None — pre-QC result for comparison
) -> Dict[str, str]:
    """Generate a comprehensive report directory.

    Returns a dict mapping logical names to absolute file paths.
    """
    if result is None or result.hvsr_result is None:
        raise ValueError("No results. Call process() first.")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    # Read plot style from config
    style = getattr(config, "plot_style", None)
    if style is not None:
        dpi = style.dpi
        show_median = style.show_median
        show_mean = style.show_mean
    else:
        show_median = True
        show_mean = False

    od = Path(output_dir)
    od.mkdir(parents=True, exist_ok=True)
    files: Dict[str, str] = {}
    r = result.hvsr_result

    # ---- data exports ------------------------------------------------
    from hvsr_pro.utils.export_utils import (
        export_hvsr_curve_csv,
        export_hvsr_curve_for_inversion,
        export_peaks_csv,
        export_complete_dataset,
    )

    try:
        dataset_files = export_complete_dataset(r, str(od), base_name)
        files.update(dataset_files)
    except Exception as exc:
        logger.warning("export_complete_dataset partially failed: %s", exc)
        csv_path = od / f"{base_name}_curve_complete.csv"
        export_hvsr_curve_csv(r, str(csv_path), include_windows=True)
        files["curve_csv"] = str(csv_path)

        inv_path = od / f"{base_name}_for_inversion.txt"
        export_hvsr_curve_for_inversion(r, str(inv_path))
        files["inversion_txt"] = str(inv_path)

        if r.peaks:
            pk_path = od / f"{base_name}_peaks.csv"
            export_peaks_csv(r, str(pk_path))
            files["peaks_csv"] = str(pk_path)

    # ---- config snapshot ---------------------------------------------
    cfg_path = od / "analysis_config.json"
    config.save(cfg_path)
    files["config_json"] = str(cfg_path)

    # ---- result summary JSON -----------------------------------------
    summary_path = od / f"{base_name}_summary.json"
    with open(summary_path, "w") as f:
        json.dump(result.get_summary(), f, indent=2, default=str)
    files["summary_json"] = str(summary_path)

    # ---- plots -------------------------------------------------------
    from hvsr_pro.visualization import HVSRPlotter
    plotter = HVSRPlotter()

    def _save(fig, name):
        p = od / name
        fig.savefig(p, dpi=dpi, bbox_inches="tight")
        plt.close(fig)
        files[name.replace(".png", "")] = str(p)

    try:
        _save(plotter.plot_result(r, show_peaks=True, show_median=show_median, show_mean=show_mean),
              "hvsr_curve.png")
    except Exception as exc:
        logger.warning("hvsr_curve plot failed: %s", exc)

    try:
        _save(plotter.plot_statistics(r), "hvsr_statistics.png")
    except Exception as exc:
        logger.warning("hvsr_statistics plot failed: %s", exc)

    if r.window_spectra:
        try:
            _save(plotter.plot_with_windows(r), "hvsr_with_windows.png")
        except Exception as exc:
            logger.warning("hvsr_with_windows plot failed: %s", exc)

    if windows:
        try:
            _save(plotter.plot_quality_metrics(windows), "quality_metrics.png")
        except Exception as exc:
            logger.warning("quality_metrics plot failed: %s", exc)

        try:
            _save(plotter.plot_timeline(windows), "window_timeline.png")
        except Exception as exc:
            logger.warning("window_timeline plot failed: %s", exc)

        try:
            _save(plotter.plot_quality_histogram(windows), "quality_histogram.png")
        except Exception as exc:
            logger.warning("quality_histogram plot failed: %s", exc)

        try:
            _save(plotter.plot_selected_metrics(windows), "selected_metrics.png")
        except Exception as exc:
            logger.warning("selected_metrics plot failed: %s", exc)

    # Mean vs Median comparison
    try:
        _save(plotter.plot_mean_vs_median(r), "mean_vs_median.png")
    except Exception as exc:
        logger.warning("mean_vs_median plot failed: %s", exc)

    # Window timeseries and spectrogram (need data)
    if windows and data is not None:
        try:
            _save(plotter.plot_window_timeseries(windows, data), "window_timeseries.png")
        except Exception as exc:
            logger.warning("window_timeseries plot failed: %s", exc)

        try:
            _save(plotter.plot_window_spectrogram(windows, data), "window_spectrogram.png")
        except Exception as exc:
            logger.warning("window_spectrogram plot failed: %s", exc)

    if r.primary_peak:
        try:
            _save(plotter.plot_peak_details(r), "peak_analysis.png")
        except Exception as exc:
            logger.warning("peak_analysis plot failed: %s", exc)

    if windows:
        try:
            _save(plotter.plot_dashboard(r, windows), "complete_dashboard.png")
        except Exception as exc:
            logger.warning("complete_dashboard plot failed: %s", exc)

    # Comparison / rejection plots (need raw_result and/or data)
    if raw_result is not None:
        try:
            _save(plotter.plot_comparison(
                [raw_result, r],
                ["Pre-QC (Raw)", "Post-QC (Adjusted)"],
                title="Raw vs Adjusted HVSR",
            ), "raw_vs_adjusted.png")
        except Exception as exc:
            logger.warning("raw_vs_adjusted plot failed: %s", exc)

    if windows and data is not None:
        try:
            _save(_plot_waveform_rejection(windows, data), "waveform_rejection.png")
        except Exception as exc:
            logger.warning("waveform_rejection plot failed: %s", exc)

    if windows and data is not None and raw_result is not None:
        try:
            _save(_plot_pre_post_rejection(windows, data, raw_result, r),
                  "pre_post_rejection.png")
        except Exception as exc:
            logger.warning("pre_post_rejection plot failed: %s", exc)

    return files
