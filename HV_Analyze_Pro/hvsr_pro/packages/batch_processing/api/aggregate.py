"""
Batch Processing API — Aggregation & Combined Analysis
======================================================

Converts per-station HVSR results into combined statistics:
    - Combined median / mean / std / percentile curves
    - Cross-station peak detection and matching
    - Peak statistics with SESAME compliance
    - Topic (diameter/group) based sub-analysis

Delegates core math to ``processing/automatic_workflow.py`` which
already implements the combined-median algorithm.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np

from .config import PeakSettings, ProcessingSettings
from .hvsr_engine import StationHVSRResult

# Reuse existing dataclasses from processing/
from ..processing.automatic_workflow import (
    AutomaticWorkflowResult,
    PeakStatistics,
    StationResult,
    run_automatic_peak_detection,
)
from ..processing.peaks import detect_peaks
from ..processing.structures import Peak

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────
# Conversion: engine result → processing dataclass
# ────────────────────────────────────────────────────────────────────

def _to_station_result(
    hvsr_result: StationHVSRResult,
    topic: str = "",
) -> StationResult:
    """
    Convert a ``StationHVSRResult`` (from hvsr_engine) to a
    ``StationResult`` (expected by automatic_workflow.py).
    """
    return StationResult(
        station_id=hvsr_result.station_id,
        station_name=hvsr_result.station_name,
        topic=topic or hvsr_result.window_name,
        frequencies=hvsr_result.frequencies,
        mean_hvsr=hvsr_result.mean_hvsr,
        std_hvsr=hvsr_result.std_hvsr,
        median_hvsr=hvsr_result.median_hvsr,
        percentile_16=hvsr_result.percentile_16,
        percentile_84=hvsr_result.percentile_84,
        peaks=list(hvsr_result.peaks),
        valid_windows=hvsr_result.valid_windows,
        total_windows=hvsr_result.total_windows,
        mat_path="",
        output_dir=hvsr_result.output_dir,
        processing_params={},
    )


# ────────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────────

def build_station_results(
    hvsr_results: List[StationHVSRResult],
    topic_map: Optional[Dict[str, str]] = None,
) -> List[StationResult]:
    """
    Convert engine results to ``StationResult`` objects.

    Parameters
    ----------
    hvsr_results : list[StationHVSRResult]
        Per-station HVSR results from ``process_batch_hvsr()``.
    topic_map : dict[str, str], optional
        Maps ``station_name`` → topic string.
        If not provided, uses ``window_name`` as topic.

    Returns
    -------
    list[StationResult]
    """
    station_results = []
    for hr in hvsr_results:
        if not hr.success:
            continue
        topic = ""
        if topic_map:
            topic = topic_map.get(hr.station_name, "")
        station_results.append(_to_station_result(hr, topic))
    return station_results


def compute_combined_median(
    station_results: List[StationResult],
    freq_min: float = 0.2,
    freq_max: float = 50.0,
    n_frequencies: int = 200,
) -> AutomaticWorkflowResult:
    """
    Compute combined median HVSR across all stations.

    Each station's median curve is interpolated onto a common log-spaced
    frequency grid, then stacked: median-of-medians, mean, std,
    16th/84th percentiles.

    Parameters
    ----------
    station_results : list[StationResult]
        Per-station results.
    freq_min, freq_max : float
        Frequency range for the common grid.
    n_frequencies : int
        Number of log-spaced frequency points.

    Returns
    -------
    AutomaticWorkflowResult
        With combined curves computed (no peaks yet).
    """
    result = AutomaticWorkflowResult(
        station_results=station_results,
        topics=list(set(s.topic for s in station_results)),
    )
    # Inject processing params so compute_median_hvsr uses our grid
    result.processing_params = {
        "f_min": freq_min,
        "f_max": freq_max,
        "n_frequencies": n_frequencies,
    }
    # Propagate to first station so compute_median_hvsr picks it up
    if station_results:
        station_results[0].processing_params = dict(result.processing_params)

    result.compute_median_hvsr()
    return result


def detect_combined_peaks(
    workflow_result: AutomaticWorkflowResult,
    min_prominence: float = 0.5,
    min_amplitude: float = 2.0,
    n_peaks: int = 3,
) -> List[Peak]:
    """
    Detect peaks on the combined median HVSR curve.

    Parameters
    ----------
    workflow_result : AutomaticWorkflowResult
        Must have combined curves computed.
    min_prominence : float
        Minimum peak prominence.
    min_amplitude : float
        Minimum H/V amplitude.
    n_peaks : int
        Maximum peaks to return.

    Returns
    -------
    list[Peak]
    """
    return workflow_result.detect_combined_peaks(
        min_prominence=min_prominence,
        min_amplitude=min_amplitude,
        n_peaks=n_peaks,
    )


def compute_peak_statistics(
    workflow_result: AutomaticWorkflowResult,
    frequency_tolerance: float = 0.3,
) -> List[PeakStatistics]:
    """
    Compute cross-station peak statistics with SESAME compliance.

    For each combined peak, finds matching peaks in individual stations
    (within ±tolerance × frequency) and computes mean/std/min/max for
    both frequency and amplitude.

    Parameters
    ----------
    workflow_result : AutomaticWorkflowResult
        Must have combined peaks detected.
    frequency_tolerance : float
        Relative tolerance (0.3 = ±30%) for matching.

    Returns
    -------
    list[PeakStatistics]
    """
    return workflow_result.compute_peak_statistics(frequency_tolerance)


def group_by_topic(
    station_results: List[StationResult],
) -> Dict[str, List[StationResult]]:
    """
    Group station results by topic.

    Parameters
    ----------
    station_results : list[StationResult]

    Returns
    -------
    dict[str, list[StationResult]]
        Topic name → list of stations.
    """
    groups: Dict[str, List[StationResult]] = {}
    for sr in station_results:
        groups.setdefault(sr.topic, []).append(sr)
    return groups


def compute_topic_medians(
    station_results: List[StationResult],
    freq_min: float = 0.2,
    freq_max: float = 50.0,
    n_frequencies: int = 200,
) -> Dict[str, AutomaticWorkflowResult]:
    """
    Compute combined median for each topic group separately.

    Returns
    -------
    dict[str, AutomaticWorkflowResult]
        Topic → workflow result with combined curves.
    """
    groups = group_by_topic(station_results)
    topic_results = {}
    for topic, members in groups.items():
        if members:
            topic_results[topic] = compute_combined_median(
                members, freq_min, freq_max, n_frequencies,
            )
    return topic_results


def run_automatic_analysis(
    hvsr_results: List[StationHVSRResult],
    peak_settings: Optional[PeakSettings] = None,
    processing: Optional[ProcessingSettings] = None,
    topic_map: Optional[Dict[str, str]] = None,
) -> AutomaticWorkflowResult:
    """
    Full automatic analysis pipeline.

    Converts engine results → station results → combined median →
    peak detection → peak statistics.

    Parameters
    ----------
    hvsr_results : list[StationHVSRResult]
        Per-station results from ``process_batch_hvsr()``.
    peak_settings : PeakSettings, optional
        Peak detection parameters (defaults used if not provided).
    processing : ProcessingSettings, optional
        For frequency grid parameters.
    topic_map : dict[str, str], optional
        station_name → topic mapping.

    Returns
    -------
    AutomaticWorkflowResult
    """
    if peak_settings is None:
        peak_settings = PeakSettings()
    if processing is None:
        processing = ProcessingSettings()

    # Convert engine results to StationResult
    station_results = build_station_results(hvsr_results, topic_map)

    if not station_results:
        logger.warning("No successful station results to aggregate")
        return AutomaticWorkflowResult()

    # Delegate to existing workflow
    result = run_automatic_peak_detection(
        station_results=station_results,
        min_prominence=peak_settings.min_prominence,
        min_amplitude=peak_settings.min_amplitude,
        n_peaks=peak_settings.n_peaks,
        frequency_tolerance=peak_settings.freq_tolerance,
    )

    logger.info(
        "Automatic analysis: %d stations, %d combined peaks, %d peak stats",
        result.n_stations,
        len(result.combined_peaks),
        len(result.peak_statistics),
    )

    return result
