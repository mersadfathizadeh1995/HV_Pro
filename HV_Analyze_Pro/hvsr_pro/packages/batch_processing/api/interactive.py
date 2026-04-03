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
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
from scipy.signal import find_peaks

from hvsr_pro.packages.batch_processing.processing.structures import Peak
from hvsr_pro.packages.batch_processing.processing.automatic_workflow import (
    AutomaticWorkflowResult,
    PeakStatistics,
)
from hvsr_pro.packages.batch_processing.api.hvsr_engine import StationHVSRResult

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
    peaks: List[Dict[str, float]],
) -> StationHVSRResult:
    """Replace the detected peaks for a named station.

    Parameters
    ----------
    hvsr_results : list[StationHVSRResult]
        Full list of per-station HVSR results (mutated in-place).
    station_name : str
        Name of the station whose peaks should be replaced.
    peaks : list[dict]
        Each dict must contain ``frequency`` (float) and ``amplitude``
        (float).  Optional keys: ``prominence``, ``peak_type``.

    Returns
    -------
    StationHVSRResult
        The updated station result.

    Raises
    ------
    ValueError
        If *station_name* is not found in *hvsr_results* or if a peak
        dict is missing required keys.
    """
    target: Optional[StationHVSRResult] = None
    for result in hvsr_results:
        if result.station_name == station_name:
            target = result
            break

    if target is None:
        available = [r.station_name for r in hvsr_results]
        raise ValueError(
            f"Station '{station_name}' not found. "
            f"Available stations: {available}"
        )

    new_peaks: List[Peak] = []
    for idx, pk_dict in enumerate(peaks):
        if "frequency" not in pk_dict or "amplitude" not in pk_dict:
            raise ValueError(
                f"Peak dict at index {idx} must contain 'frequency' and "
                f"'amplitude' keys. Got: {list(pk_dict.keys())}"
            )
        default_type = "primary" if idx == 0 else "secondary"
        new_peaks.append(
            Peak(
                frequency=float(pk_dict["frequency"]),
                amplitude=float(pk_dict["amplitude"]),
                prominence=float(pk_dict.get("prominence", 0.0)),
                peak_type=pk_dict.get("peak_type", default_type),
            )
        )

    old_count = len(target.peaks)
    target.peaks = new_peaks

    logger.info(
        "Overrode peaks for station '%s': %d → %d peaks",
        station_name, old_count, len(new_peaks),
    )
    return target


# ────────────────────────────────────────────────────────────────────
# Detect peaks on a combined/arbitrary median curve
# ────────────────────────────────────────────────────────────────────

def pick_peaks_on_median(
    frequencies: np.ndarray,
    median_hvsr: np.ndarray,
    min_prominence: float = 0.3,
    min_amplitude: float = 1.0,
    n_peaks: int = 3,
    freq_range: Optional[Tuple[float, float]] = None,
) -> List[Dict[str, float]]:
    """Detect peaks on a combined median HVSR curve.

    Uses :func:`scipy.signal.find_peaks` with prominence filtering and
    returns the top *n_peaks* sorted by descending prominence.

    Parameters
    ----------
    frequencies : np.ndarray
        Frequency array corresponding to *median_hvsr*.
    median_hvsr : np.ndarray
        Median H/V spectral ratio values.
    min_prominence : float
        Minimum peak prominence to retain (default 0.3).
    min_amplitude : float
        Minimum H/V amplitude to consider a peak (default 1.0).
    n_peaks : int
        Maximum number of peaks to return (default 3).
    freq_range : tuple[float, float] | None
        Optional ``(f_min, f_max)`` band.  Peaks outside this range
        are discarded.

    Returns
    -------
    list[dict]
        Each dict has keys ``frequency``, ``amplitude``, and
        ``prominence``, sorted by descending prominence.

    Raises
    ------
    ValueError
        If *frequencies* and *median_hvsr* have mismatched lengths or
        are empty.
    """
    frequencies = np.asarray(frequencies, dtype=float)
    median_hvsr = np.asarray(median_hvsr, dtype=float)

    if frequencies.size == 0 or median_hvsr.size == 0:
        raise ValueError("frequencies and median_hvsr must be non-empty.")
    if frequencies.shape != median_hvsr.shape:
        raise ValueError(
            f"Shape mismatch: frequencies {frequencies.shape} vs "
            f"median_hvsr {median_hvsr.shape}"
        )

    # scipy peak detection
    indices, properties = find_peaks(
        median_hvsr, prominence=min_prominence,
    )

    if indices.size == 0:
        logger.info("No peaks found with min_prominence=%.3f", min_prominence)
        return []

    prominences = properties["prominences"]

    # Filter by amplitude
    amp_mask = median_hvsr[indices] >= min_amplitude
    indices = indices[amp_mask]
    prominences = prominences[amp_mask]

    # Filter by frequency range
    if freq_range is not None:
        f_min, f_max = freq_range
        freq_mask = (
            (frequencies[indices] >= f_min) & (frequencies[indices] <= f_max)
        )
        indices = indices[freq_mask]
        prominences = prominences[freq_mask]

    if indices.size == 0:
        logger.info("All peaks filtered out by amplitude / frequency constraints.")
        return []

    # Keep top n_peaks by prominence (descending)
    order = np.argsort(prominences)[::-1][:n_peaks]
    indices = indices[order]
    prominences = prominences[order]

    results: List[Dict[str, float]] = []
    for idx, prom in zip(indices, prominences):
        results.append({
            "frequency": float(frequencies[idx]),
            "amplitude": float(median_hvsr[idx]),
            "prominence": float(prom),
        })

    logger.info("Detected %d peak(s) on median HVSR curve.", len(results))
    return results


# ────────────────────────────────────────────────────────────────────
# Accept/reject peak selection
# ────────────────────────────────────────────────────────────────────

def accept_peak_selection(
    workflow_result: AutomaticWorkflowResult,
    selected_indices: Sequence[int],
) -> List[Peak]:
    """Keep only the peaks at *selected_indices* in the workflow result.

    The ``combined_peaks`` list on *workflow_result* is replaced
    in-place.  Peak types are re-assigned so the first retained peak
    is ``"primary"`` and the rest ``"secondary"``.

    Parameters
    ----------
    workflow_result : AutomaticWorkflowResult
        Workflow result whose ``combined_peaks`` will be filtered.
    selected_indices : sequence[int]
        Zero-based indices into the current ``combined_peaks`` list.

    Returns
    -------
    list[Peak]
        The new (filtered) list of combined peaks.

    Raises
    ------
    IndexError
        If any index in *selected_indices* is out of range.
    """
    current = workflow_result.combined_peaks
    if not current:
        logger.warning("combined_peaks is empty; nothing to select.")
        return []

    max_idx = len(current) - 1
    for i in selected_indices:
        if i < 0 or i > max_idx:
            raise IndexError(
                f"Index {i} out of range for combined_peaks "
                f"(length {len(current)})."
            )

    kept: List[Peak] = [current[i] for i in selected_indices]

    # Re-assign peak_type for the filtered list
    for order, peak in enumerate(kept):
        peak.peak_type = "primary" if order == 0 else "secondary"

    workflow_result.combined_peaks = kept

    logger.info(
        "Accepted %d of %d combined peaks.", len(kept), len(current),
    )
    return kept


# ────────────────────────────────────────────────────────────────────
# Recompute statistics after peak overrides
# ────────────────────────────────────────────────────────────────────

def recompute_statistics_with_overrides(
    station_results: List[StationHVSRResult],
    overrides: Dict[str, List[Peak]],
    freq_tolerance: float = 0.3,
) -> List[PeakStatistics]:
    """Recompute :class:`PeakStatistics` after station peaks have been edited.

    For each station in *overrides* the peaks on the corresponding
    :class:`StationHVSRResult` are replaced first.  Then an
    :class:`AutomaticWorkflowResult` is assembled from the full station
    list and its :meth:`~AutomaticWorkflowResult.compute_peak_statistics`
    method is called to produce fresh cross-station statistics.

    Parameters
    ----------
    station_results : list[StationHVSRResult]
        All station results (mutated in-place for overridden stations).
    overrides : dict[str, list[Peak]]
        Mapping of station name → replacement peak list.
    freq_tolerance : float
        Relative frequency tolerance passed to
        ``compute_peak_statistics`` (default 0.3 = ±30 %).

    Returns
    -------
    list[PeakStatistics]
        Updated statistics, one entry per combined peak.

    Raises
    ------
    ValueError
        If an override station name does not match any station result.
    """
    # Apply overrides to station results
    station_map: Dict[str, StationHVSRResult] = {
        r.station_name: r for r in station_results
    }

    for name, new_peaks in overrides.items():
        if name not in station_map:
            raise ValueError(
                f"Override station '{name}' not found in results. "
                f"Available: {list(station_map.keys())}"
            )
        old_count = len(station_map[name].peaks)
        station_map[name].peaks = list(new_peaks)
        logger.info(
            "Applied override for '%s': %d → %d peaks",
            name, old_count, len(new_peaks),
        )

    # Build a lightweight AutomaticWorkflowResult for statistics
    from hvsr_pro.packages.batch_processing.processing.automatic_workflow import (
        StationResult,
    )

    aw_stations: List[StationResult] = []
    for sr in station_results:
        aw_stations.append(
            StationResult(
                station_id=sr.station_id,
                station_name=sr.station_name,
                frequencies=sr.frequencies,
                mean_hvsr=sr.mean_hvsr,
                median_hvsr=sr.median_hvsr,
                std_hvsr=sr.std_hvsr,
                percentile_16=sr.percentile_16,
                percentile_84=sr.percentile_84,
                peaks=list(sr.peaks),
                valid_windows=sr.valid_windows,
                total_windows=sr.total_windows,
            )
        )

    workflow = AutomaticWorkflowResult(station_results=aw_stations)

    # Compute combined median & detect combined peaks
    workflow.compute_median_hvsr()
    workflow.detect_combined_peaks()

    # Compute cross-station peak statistics
    stats = workflow.compute_peak_statistics(frequency_tolerance=freq_tolerance)

    logger.info(
        "Recomputed statistics for %d combined peaks across %d stations.",
        len(stats), len(station_results),
    )
    return stats
