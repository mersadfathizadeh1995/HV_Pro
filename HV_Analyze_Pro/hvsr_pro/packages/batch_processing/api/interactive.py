"""
Batch Processing API — Interactive Peak Management
===================================================

Headless API for post-analysis peak management: override detected peaks,
pick peaks on the combined median curve, accept/reject peaks, and
recompute cross-station statistics after manual edits.

Pure Python — NO Qt dependencies.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

import numpy as np
from scipy.signal import find_peaks

from ..processing.automatic_workflow import AutomaticWorkflowResult, PeakStatistics
from ..processing.structures import Peak
from .hvsr_engine import StationHVSRResult

logger = logging.getLogger(__name__)

__all__ = [
    "override_station_peaks",
    "pick_peaks_on_median",
    "accept_peak_selection",
    "recompute_statistics_with_overrides",
]


# ────────────────────────────────────────────────────────────────────
# Override peaks for a specific station
# ────────────────────────────────────────────────────────────────────

def override_station_peaks(
    hvsr_results: List[StationHVSRResult],
    station_name: str,
    peaks: List[Dict],
) -> bool:
    """
    Replace detected peaks for a specific station.

    Parameters
    ----------
    hvsr_results : list[StationHVSRResult]
        Full results list (mutated in-place).
    station_name : str
        Name of the station to update.
    peaks : list[dict]
        New peaks, each with keys: ``frequency``, ``amplitude``,
        and optionally ``prominence``, ``peak_type``.

    Returns
    -------
    bool
        ``True`` if station was found and updated, ``False`` otherwise.
    """
    for result in hvsr_results:
        if result.station_name == station_name:
            new_peaks = []
            for i, p in enumerate(peaks):
                new_peaks.append(Peak(
                    frequency=float(p["frequency"]),
                    amplitude=float(p["amplitude"]),
                    prominence=float(p.get("prominence", 0.0)),
                    peak_type=p.get("peak_type", "primary" if i == 0 else "secondary"),
                ))
            result.peaks = new_peaks
            logger.info(
                "Overrode peaks for station %s: %d peaks",
                station_name, len(new_peaks),
            )
            return True

    logger.warning("Station %s not found in results", station_name)
    return False


# ────────────────────────────────────────────────────────────────────
# Detect peaks on a combined/arbitrary median curve
# ────────────────────────────────────────────────────────────────────

def pick_peaks_on_median(
    frequencies: np.ndarray,
    median_hvsr: np.ndarray,
    min_prominence: float = 0.3,
    min_amplitude: float = 1.0,
    n_peaks: int = 3,
    freq_range: Optional[tuple] = None,
) -> List[Dict]:
    """
    Detect peaks on a median HVSR curve.

    Parameters
    ----------
    frequencies : np.ndarray
        Frequency array (Hz).
    median_hvsr : np.ndarray
        Median H/V ratio array.
    min_prominence : float
        Minimum peak prominence.
    min_amplitude : float
        Minimum H/V amplitude to consider.
    n_peaks : int
        Maximum number of peaks to return.
    freq_range : tuple(float, float), optional
        ``(freq_min, freq_max)`` to restrict search range.

    Returns
    -------
    list[dict]
        Each dict has: ``frequency``, ``amplitude``, ``prominence``,
        ``index``.
    """
    if len(frequencies) == 0 or len(median_hvsr) == 0:
        return []

    # Apply frequency range mask
    mask = np.ones(len(frequencies), dtype=bool)
    if freq_range is not None:
        mask &= (frequencies >= freq_range[0]) & (frequencies <= freq_range[1])

    # Apply amplitude threshold
    mask &= (median_hvsr >= min_amplitude)

    if not mask.any():
        logger.info("No frequencies pass amplitude threshold")
        return []

    # Find peaks
    indices, properties = find_peaks(
        median_hvsr,
        prominence=min_prominence,
        height=min_amplitude,
    )

    if len(indices) == 0:
        logger.info("No peaks found above thresholds")
        return []

    # Filter by frequency range
    if freq_range is not None:
        range_mask = (
            (frequencies[indices] >= freq_range[0]) &
            (frequencies[indices] <= freq_range[1])
        )
        indices = indices[range_mask]
        if "prominences" in properties:
            properties["prominences"] = properties["prominences"][range_mask]

    # Sort by prominence (descending) and take top n_peaks
    prominences = properties.get("prominences", np.zeros(len(indices)))
    sort_order = np.argsort(prominences)[::-1]
    indices = indices[sort_order[:n_peaks]]
    prominences = prominences[sort_order[:n_peaks]]

    # Sort final results by frequency
    freq_order = np.argsort(frequencies[indices])
    indices = indices[freq_order]
    prominences = prominences[freq_order]

    peaks = []
    for idx, prom in zip(indices, prominences):
        peaks.append({
            "frequency": float(frequencies[idx]),
            "amplitude": float(median_hvsr[idx]),
            "prominence": float(prom),
            "index": int(idx),
        })

    logger.info("Detected %d peaks on median curve", len(peaks))
    return peaks


# ────────────────────────────────────────────────────────────────────
# Accept/reject peak selection
# ────────────────────────────────────────────────────────────────────

def accept_peak_selection(
    workflow_result: AutomaticWorkflowResult,
    selected_indices: List[int],
) -> List[Peak]:
    """
    Filter combined peaks to keep only the selected ones.

    Parameters
    ----------
    workflow_result : AutomaticWorkflowResult
        Must have ``combined_peaks`` populated.
    selected_indices : list[int]
        Indices into ``workflow_result.combined_peaks`` to keep.

    Returns
    -------
    list[Peak]
        The filtered peaks (also stored back in ``workflow_result``).
    """
    if not workflow_result.combined_peaks:
        logger.warning("No combined peaks to filter")
        return []

    kept = []
    for i in selected_indices:
        if 0 <= i < len(workflow_result.combined_peaks):
            kept.append(workflow_result.combined_peaks[i])
        else:
            logger.warning("Peak index %d out of range (0-%d)", i,
                           len(workflow_result.combined_peaks) - 1)

    workflow_result.combined_peaks = kept
    logger.info("Accepted %d/%d combined peaks", len(kept),
                len(selected_indices))
    return kept


# ────────────────────────────────────────────────────────────────────
# Recompute statistics after peak overrides
# ────────────────────────────────────────────────────────────────────

def recompute_statistics_with_overrides(
    workflow_result: AutomaticWorkflowResult,
    freq_tolerance: float = 0.3,
) -> List[PeakStatistics]:
    """
    Recompute cross-station peak statistics after peak overrides.

    Call this after modifying individual station peaks via
    ``override_station_peaks`` to update the combined statistics.

    Parameters
    ----------
    workflow_result : AutomaticWorkflowResult
        Must have ``combined_peaks`` and ``station_results`` populated.
    freq_tolerance : float
        Relative frequency tolerance for cross-station matching
        (0.3 = ±30%).

    Returns
    -------
    list[PeakStatistics]
        Updated statistics (also stored in ``workflow_result``).
    """
    if not workflow_result.combined_peaks:
        logger.warning("No combined peaks for statistics recomputation")
        workflow_result.peak_statistics = []
        return []

    stats = workflow_result.compute_peak_statistics(freq_tolerance)
    logger.info("Recomputed statistics: %d peak groups", len(stats))
    return stats
