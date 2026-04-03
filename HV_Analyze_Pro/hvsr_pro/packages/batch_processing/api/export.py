"""
Batch Processing API — Export Engine
=====================================

All export formats for batch HVSR results: per-station outputs,
combined statistics, results tables, and median data in multiple
formats (JSON, CSV, MAT, Excel).

Delegates heavy lifting to ``processing/output_organizer.py`` and
``report_export.py`` — this module provides a clean API surface.
"""

from __future__ import annotations

import csv
import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np

from ..processing.automatic_workflow import (
    AutomaticWorkflowResult,
    StationResult,
)
from ..processing.structures import Peak

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────
# Results Table CSV
# ────────────────────────────────────────────────────────────────────

def export_results_table_csv(
    station_results: List[StationResult],
    output_dir: str,
    filename: str = "HVSR_Results_Table.csv",
) -> str:
    """
    Export a summary table of all stations and their primary peaks.

    Columns: Station, Topic, F0_Hz, Amplitude, Prominence,
             Valid_Windows, Total_Windows, Accept_Rate

    Returns the output file path.
    """
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, filename)

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Station", "Topic", "F0_Hz", "Amplitude", "Prominence",
            "Valid_Windows", "Total_Windows", "Accept_Rate",
        ])
        for sr in station_results:
            primary = sr.primary_peak
            f0 = f"{primary.frequency:.4f}" if primary else ""
            amp = f"{primary.amplitude:.4f}" if primary else ""
            prom = f"{getattr(primary, 'prominence', 0):.4f}" if primary else ""
            acc = (
                f"{sr.valid_windows / sr.total_windows:.2%}"
                if sr.total_windows > 0
                else "N/A"
            )
            writer.writerow([
                sr.station_name,
                sr.topic,
                f0,
                amp,
                prom,
                sr.valid_windows,
                sr.total_windows,
                acc,
            ])

    logger.info("Results table: %s (%d stations)", path, len(station_results))
    return path


# ────────────────────────────────────────────────────────────────────
# Median data export (CSV + Excel + JSON + MAT)
# ────────────────────────────────────────────────────────────────────

def export_median_data(
    station_results: List[StationResult],
    output_dir: str,
) -> Dict[str, str]:
    """
    Export combined median curves in all formats.

    Delegates to ``report_export.export_median_data()`` which produces:
        - HVSR_Median_Combined.xlsx (multi-sheet, if openpyxl available)
        - HVSR_Median_Combined.csv
        - HVSR_Median_<Array>.csv (per topic)
        - HVSR_Median_Combined.json
        - HVSR_Median_Combined.mat

    Returns dict of format → file path.
    """
    from ..report_export import export_median_data as _export

    os.makedirs(output_dir, exist_ok=True)
    files = {}

    def _log(msg):
        logger.info(msg)

    _export(output_dir, station_results, log_fn=_log)

    # Collect generated files
    for f in os.listdir(output_dir):
        full = os.path.join(output_dir, f)
        if f.endswith(".xlsx"):
            files["excel"] = full
        elif f.endswith(".csv"):
            files.setdefault("csv", [])
            if isinstance(files["csv"], list):
                files["csv"].append(full)
            else:
                files["csv"] = [files["csv"], full]
        elif f.endswith(".json"):
            files["json"] = full
        elif f.endswith(".mat"):
            files["mat"] = full

    return files


def export_median_json_hvsr_format(
    station_results: List[StationResult],
    output_path: str,
    n_peaks: int = 3,
    hvsr_settings: Optional[dict] = None,
    manual_peaks: Optional[list] = None,
) -> str:
    """
    Export grand median as hvsr_pro-compatible JSON.

    The output matches ``HVSRResult.to_dict()`` structure so it can
    be loaded by the standard analysis tools.
    """
    from ..report_export import export_median_json_hvsr_format as _export

    return _export(
        output_path=output_path,
        checked=station_results,
        n_peaks=n_peaks,
        hvsr_settings=hvsr_settings,
        manual_peaks=manual_peaks,
        log_fn=lambda msg: logger.info(msg),
    )


# ────────────────────────────────────────────────────────────────────
# Workflow result export
# ────────────────────────────────────────────────────────────────────

def export_workflow_result(
    workflow_result: AutomaticWorkflowResult,
    output_dir: str,
    site_name: str = "SITE",
) -> Dict[str, str]:
    """
    Export the complete workflow result (station results + combined).

    Saves:
        - ``<site>_workflow_result.json`` — full serialized result
        - ``<site>_combined_result.json`` — combined in hvsr_pro format

    Returns dict of name → path.
    """
    os.makedirs(output_dir, exist_ok=True)
    files = {}

    # Full workflow JSON
    workflow_path = os.path.join(output_dir, f"{site_name}_workflow_result.json")
    workflow_result.save(workflow_path)
    files["workflow_json"] = workflow_path

    # Combined in hvsr_pro format
    combined_path = os.path.join(output_dir, f"{site_name}_combined_result.json")
    workflow_result.save_as_station_format(combined_path)
    files["combined_json"] = combined_path

    logger.info("Workflow result exported to %s", output_dir)
    return files


# ────────────────────────────────────────────────────────────────────
# Full batch report generation
# ────────────────────────────────────────────────────────────────────

def generate_batch_report(
    workflow_result: AutomaticWorkflowResult,
    output_dir: str,
    site_name: str = "SITE",
    dpi: int = 300,
    hvsr_settings: Optional[dict] = None,
    manual_peaks: Optional[list] = None,
) -> Dict[str, str]:
    """
    Generate a complete batch report directory.

    Creates the standard report structure::

        report/
        ├── table/HVSR_Results_Table.csv
        ├── curves/HVSR_AllMedians.{png,pdf}
        ├── curves/HVSR_AllMedians_Enhanced.{png,pdf}
        ├── histogram/HVSR_F0_Histogram.{png,pdf}
        ├── histogram/HVSR_F0_Histogram_Enhanced.{png,pdf}
        ├── median/HVSR_Median_Combined.{xlsx,csv,json,mat}
        ├── median/HVSR_Median_<Array>.{csv,xlsx}
        └── median/HVSR_Median_Result.json

    Parameters
    ----------
    workflow_result : AutomaticWorkflowResult
    output_dir : str
        Report root directory.
    site_name : str
    dpi : int
    hvsr_settings : dict, optional
    manual_peaks : list, optional

    Returns
    -------
    dict[str, str]
        Logical name → file path for all generated files.
    """
    from ..report_export import (
        export_enhanced_curve,
        export_enhanced_histogram,
    )

    checked = workflow_result.station_results
    files = {}

    # Create subdirectories
    table_dir = os.path.join(output_dir, "table")
    curves_dir = os.path.join(output_dir, "curves")
    hist_dir = os.path.join(output_dir, "histogram")
    median_dir = os.path.join(output_dir, "median")

    for d in (table_dir, curves_dir, hist_dir, median_dir):
        os.makedirs(d, exist_ok=True)

    def _log(msg):
        logger.info(msg)

    # 1. Results table
    try:
        files["results_table"] = export_results_table_csv(
            checked, table_dir,
        )
    except Exception as exc:
        logger.error("Results table failed: %s", exc)

    # 2. Curves (basic + enhanced)
    try:
        from ..report_export import compute_median_stats
        stats = compute_median_stats(checked)

        # Basic curves figure
        _generate_basic_curves(
            checked, stats, curves_dir, dpi,
        )
        files["curves_basic"] = os.path.join(curves_dir, "HVSR_AllMedians.png")
    except Exception as exc:
        logger.error("Basic curves figure failed: %s", exc)

    try:
        export_enhanced_curve(curves_dir, checked, log_fn=_log)
        files["curves_enhanced"] = os.path.join(
            curves_dir, "HVSR_AllMedians_Enhanced.png",
        )
    except Exception as exc:
        logger.error("Enhanced curves figure failed: %s", exc)

    # 3. Histogram (basic + enhanced)
    try:
        _generate_basic_histogram(checked, hist_dir, dpi)
        files["histogram_basic"] = os.path.join(
            hist_dir, "HVSR_F0_Histogram.png",
        )
    except Exception as exc:
        logger.error("Basic histogram failed: %s", exc)

    try:
        export_enhanced_histogram(hist_dir, checked, log_fn=_log)
        files["histogram_enhanced"] = os.path.join(
            hist_dir, "HVSR_F0_Histogram_Enhanced.png",
        )
    except Exception as exc:
        logger.error("Enhanced histogram failed: %s", exc)

    # 4. Median data
    try:
        median_files = export_median_data(checked, median_dir)
        files.update({f"median_{k}": v for k, v in median_files.items()})
    except Exception as exc:
        logger.error("Median data export failed: %s", exc)

    # 5. Median result JSON (hvsr_pro format)
    try:
        result_json = os.path.join(median_dir, "HVSR_Median_Result.json")
        export_median_json_hvsr_format(
            checked, result_json,
            n_peaks=3,
            hvsr_settings=hvsr_settings,
            manual_peaks=manual_peaks,
        )
        files["median_result_json"] = result_json
    except Exception as exc:
        logger.error("Median result JSON failed: %s", exc)

    # 6. Workflow result
    try:
        wf_files = export_workflow_result(
            workflow_result, output_dir, site_name,
        )
        files.update(wf_files)
    except Exception as exc:
        logger.error("Workflow result export failed: %s", exc)

    logger.info("Batch report: %d files in %s", len(files), output_dir)
    return files


# ────────────────────────────────────────────────────────────────────
# Basic figure helpers (no external dependencies beyond matplotlib)
# ────────────────────────────────────────────────────────────────────

def _generate_basic_curves(
    checked: List[StationResult],
    stats: dict,
    output_dir: str,
    dpi: int = 300,
):
    """Generate a basic all-medians curves figure."""
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
    """Generate a basic F0 histogram figure."""
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
