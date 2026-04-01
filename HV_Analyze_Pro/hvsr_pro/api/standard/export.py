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
) -> None:
    """Render and save a single plot to *output_path*."""
    if result is None or result.hvsr_result is None:
        raise ValueError("No results to plot. Call process() first.")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from hvsr_pro.visualization import HVSRPlotter

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    plotter = HVSRPlotter()
    r = result.hvsr_result

    if plot_type == "hvsr":
        fig = plotter.plot_result(r, show_peaks=True)
    elif plot_type == "windows" and r.window_spectra:
        fig = plotter.plot_with_windows(r)
    elif plot_type == "quality" and windows:
        fig = plotter.plot_quality_metrics(windows)
    elif plot_type == "statistics":
        fig = plotter.plot_statistics(r)
    elif plot_type == "dashboard" and windows:
        fig = plotter.plot_dashboard(r, windows)
    else:
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
) -> Dict[str, str]:
    """Generate a comprehensive report directory.

    Returns a dict mapping logical names to absolute file paths.
    """
    if result is None or result.hvsr_result is None:
        raise ValueError("No results. Call process() first.")

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

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
        _save(plotter.plot_result(r, show_peaks=True), "hvsr_curve.png")
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

    return files
