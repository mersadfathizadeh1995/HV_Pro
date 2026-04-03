"""
Batch Processing API — Report Generation Orchestrator
=====================================================

Headless API for orchestrated batch report generation. Pure Python, NO Qt.

Coordinates per-station figure generation, combined figures, results
tables, and median data export into a structured report directory::

    curves/          Per-station HVSR curve figures
    histogram/       Combined histogram figures
    table/           Results summary CSV
    median/          Median data in CSV / JSON / MAT
    statistics/      Combined statistics figures

Uses :class:`ReportConfig` for declarative control over DPI, formats,
parallelism, and which report sections to include.
"""

from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from ..processing.automatic_workflow import AutomaticWorkflowResult
from .config import BatchConfig, OutputSettings
from .export import export_median_data, export_results_table_csv
from .figures import generate_combined_figures, generate_station_figures
from .hvsr_engine import StationHVSRResult

logger = logging.getLogger(__name__)

__all__ = [
    "ReportConfig",
    "generate_full_report",
]

# Default figure types produced per station
_DEFAULT_FIGURE_TYPES: List[str] = [
    "standard",
    "hvsr_pro",
    "statistics",
    "spectrogram",
    "azimuth",
    "peak_analysis",
    "waveform_rejection",
    "pre_post_rejection",
    "mean_vs_median",
    "quality_histogram",
    "selected_metrics",
    "window_timeline",
    "window_timeseries",
]

# Sub-directory names inside the report output
_DIR_CURVES = "curves"
_DIR_HISTOGRAM = "histogram"
_DIR_TABLE = "table"
_DIR_MEDIAN = "median"
_DIR_STATISTICS = "statistics"


# ────────────────────────────────────────────────────────────────────
# Configuration
# ────────────────────────────────────────────────────────────────────

@dataclass
class ReportConfig:
    """
    Declarative configuration for batch report generation.

    Parameters
    ----------
    dpi : int
        Figure resolution in dots-per-inch.
    format : str
        Image format: ``"png"``, ``"pdf"``, or ``"svg"``.
    figure_types : List[str]
        Which figure types to generate per station.
        Defaults to a comprehensive built-in list.
    parallel_workers : int
        Number of threads for concurrent figure generation.
    include_per_station : bool
        Generate individual station figures in ``curves/``.
    include_combined : bool
        Generate combined / batch-level figures.
    include_tables : bool
        Export the results summary CSV.
    include_median_data : bool
        Export combined median curves (CSV / JSON / MAT).
    """

    dpi: int = 300
    format: str = "png"
    figure_types: List[str] = field(default_factory=lambda: list(_DEFAULT_FIGURE_TYPES))
    parallel_workers: int = 4
    include_per_station: bool = True
    include_combined: bool = True
    include_tables: bool = True
    include_median_data: bool = True


# ────────────────────────────────────────────────────────────────────
# Report Generation
# ────────────────────────────────────────────────────────────────────

def generate_full_report(
    hvsr_results: List[StationHVSRResult],
    workflow_result: AutomaticWorkflowResult,
    config: BatchConfig,
    output_dir: str,
    report_config: Optional[ReportConfig] = None,
    site_name: str = "SITE",
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> Dict[str, str]:
    """
    Orchestrate a complete batch report.

    Creates a structured directory tree under *output_dir* and populates
    it with per-station figures, combined figures, summary tables, and
    median data exports.

    Parameters
    ----------
    hvsr_results : List[StationHVSRResult]
        Per-station HVSR results from the processing engine.
    workflow_result : AutomaticWorkflowResult
        Aggregated workflow result (combined curves, peak statistics).
    config : BatchConfig
        The batch configuration used for this analysis.
    output_dir : str
        Root directory for the report output.
    report_config : ReportConfig, optional
        Report generation settings.  Uses defaults when ``None``.
    site_name : str
        Human-readable site / project name for labelling.
    progress_callback : callable, optional
        ``callback(current, total, message)`` invoked after each step
        to report progress to the caller.

    Returns
    -------
    Dict[str, str]
        Manifest mapping logical names to absolute file paths.
        Keys follow the pattern ``"station/<name>/<figure_type>"``,
        ``"combined/<figure_type>"``, ``"table/results_csv"``,
        ``"median/<format>"``, etc.
    """
    rcfg = report_config or ReportConfig()
    manifest: Dict[str, str] = {}

    # Count total steps for progress reporting
    total_steps = _count_steps(hvsr_results, rcfg)
    current_step = 0

    def _progress(msg: str) -> None:
        nonlocal current_step
        current_step += 1
        if progress_callback is not None:
            progress_callback(current_step, total_steps, msg)

    # ── Create sub-directories ─────────────────────────────────────
    subdirs = {
        _DIR_CURVES: os.path.join(output_dir, _DIR_CURVES),
        _DIR_HISTOGRAM: os.path.join(output_dir, _DIR_HISTOGRAM),
        _DIR_TABLE: os.path.join(output_dir, _DIR_TABLE),
        _DIR_MEDIAN: os.path.join(output_dir, _DIR_MEDIAN),
        _DIR_STATISTICS: os.path.join(output_dir, _DIR_STATISTICS),
    }
    for subdir_path in subdirs.values():
        os.makedirs(subdir_path, exist_ok=True)
    logger.info("Report directory structure created under %s", output_dir)

    # ── Per-station figures ────────────────────────────────────────
    if rcfg.include_per_station and hvsr_results:
        logger.info(
            "Generating per-station figures (%d stations, %d workers)",
            len(hvsr_results),
            rcfg.parallel_workers,
        )
        station_manifest = _generate_per_station_figures(
            hvsr_results=hvsr_results,
            curves_dir=subdirs[_DIR_CURVES],
            figure_types=rcfg.figure_types,
            dpi=rcfg.dpi,
            parallel_workers=rcfg.parallel_workers,
            progress_fn=_progress,
        )
        manifest.update(station_manifest)

    # ── Combined figures ───────────────────────────────────────────
    if rcfg.include_combined:
        logger.info("Generating combined figures")
        try:
            combined_files = generate_combined_figures(
                workflow_result,
                subdirs[_DIR_HISTOGRAM],
                rcfg.figure_types,
                rcfg.dpi,
            )
            for fig_type, fpath in combined_files.items():
                manifest[f"combined/{fig_type}"] = fpath
            logger.info("Combined figures: %d files", len(combined_files))
        except Exception:
            logger.exception("Failed to generate combined figures")
        _progress("Combined figures")

    # ── Results table ──────────────────────────────────────────────
    if rcfg.include_tables:
        logger.info("Exporting results table CSV")
        try:
            table_path = export_results_table_csv(
                workflow_result.station_results,
                subdirs[_DIR_TABLE],
            )
            manifest["table/results_csv"] = table_path
            logger.info("Results table saved: %s", table_path)
        except Exception:
            logger.exception("Failed to export results table")
        _progress("Results table")

    # ── Median data ────────────────────────────────────────────────
    if rcfg.include_median_data:
        logger.info("Exporting median data")
        try:
            median_files = export_median_data(
                workflow_result.station_results,
                subdirs[_DIR_MEDIAN],
            )
            for fmt, fpath in median_files.items():
                manifest[f"median/{fmt}"] = fpath
            logger.info("Median exports: %d files", len(median_files))
        except Exception:
            logger.exception("Failed to export median data")
        _progress("Median data export")

    logger.info(
        "Report generation complete — %d artefacts for site '%s'",
        len(manifest),
        site_name,
    )
    return manifest


# ────────────────────────────────────────────────────────────────────
# Internal helpers
# ────────────────────────────────────────────────────────────────────

def _count_steps(
    hvsr_results: List[StationHVSRResult],
    rcfg: ReportConfig,
) -> int:
    """Estimate the total number of progress steps."""
    steps = 0
    if rcfg.include_per_station:
        steps += len(hvsr_results)
    if rcfg.include_combined:
        steps += 1
    if rcfg.include_tables:
        steps += 1
    if rcfg.include_median_data:
        steps += 1
    return steps


def _generate_per_station_figures(
    hvsr_results: List[StationHVSRResult],
    curves_dir: str,
    figure_types: List[str],
    dpi: int,
    parallel_workers: int,
    progress_fn: Callable[[str], None],
) -> Dict[str, str]:
    """
    Generate figures for every station, optionally in parallel.

    Returns a manifest fragment with keys like
    ``"station/<name>/<figure_type>"``.
    """
    manifest: Dict[str, str] = {}

    def _gen_one(result: StationHVSRResult) -> Dict[str, str]:
        station_dir = os.path.join(curves_dir, result.station_name)
        os.makedirs(station_dir, exist_ok=True)
        return generate_station_figures(
            result,
            station_dir,
            figure_types,
            dpi,
        )

    workers = max(1, min(parallel_workers, len(hvsr_results)))

    if workers == 1:
        # Sequential — simpler stack traces on failure
        for res in hvsr_results:
            try:
                files = _gen_one(res)
                for fig_type, fpath in files.items():
                    manifest[f"station/{res.station_name}/{fig_type}"] = fpath
            except Exception:
                logger.exception(
                    "Figure generation failed for station %s",
                    res.station_name,
                )
            progress_fn(f"Station {res.station_name}")
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            future_to_name = {
                pool.submit(_gen_one, res): res.station_name
                for res in hvsr_results
            }
            for future in as_completed(future_to_name):
                name = future_to_name[future]
                try:
                    files = future.result()
                    for fig_type, fpath in files.items():
                        manifest[f"station/{name}/{fig_type}"] = fpath
                except Exception:
                    logger.exception(
                        "Figure generation failed for station %s", name,
                    )
                progress_fn(f"Station {name}")

    return manifest
