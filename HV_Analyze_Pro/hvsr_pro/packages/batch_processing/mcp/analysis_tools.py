"""
MCP tools for batch HVSR analysis execution.

Provides four phase-oriented tools:
    1. validate_setup  – pre-flight configuration validation
    2. prepare_data    – Phase 1: data loading & preparation
    3. process_hvsr    – Phase 2: HVSR computation per station
    4. run_analysis    – Phase 3: combined multi-station analysis
"""

from __future__ import annotations

from typing import Any, Dict, List

from .server import mcp, _get_batch


# ── 1. Pre-flight validation ───────────────────────────────────────

@mcp.tool()
def validate_setup(session_id: str = "default") -> Dict[str, Any]:
    """Validate the current batch configuration before running.

    Checks config parameters, file paths, and time-window definitions.
    Call this *before* ``prepare_data`` to catch problems early.

    Returns
    -------
    dict
        ``{"valid": bool, "errors": {"config": [...], "files": [...], "time_windows": [...]}}``
    """
    try:
        from ..api.validation import validate_all

        batch = _get_batch(session_id)
        errors = validate_all(batch._config)
        is_valid = all(len(v) == 0 for v in errors.values())
        return {"valid": is_valid, "errors": errors}
    except Exception as e:
        return {
            "valid": False,
            "errors": {
                "config": [str(e)],
                "files": [],
                "time_windows": [],
            },
        }


# ── 2. Data preparation (Phase 1) ──────────────────────────────────

@mcp.tool()
def prepare_data(session_id: str = "default") -> Dict[str, Any]:
    """Load and prepare seismic data for every station in the batch.

    This is Phase 1 of the batch workflow.  It reads raw files, applies
    time-window trimming, and writes intermediate MAT files.

    Returns
    -------
    dict
        ``{"success": bool, "n_stations": int,
           "results": [{"station": str, "success": bool,
                         "duration_s": float, "sampling_rate": float}, ...],
           "error": str | None}``
    """
    try:
        batch = _get_batch(session_id)
        data_results = batch.prepare_data()

        results: List[Dict[str, Any]] = []
        for r in data_results:
            results.append({
                "station": r.station_name,
                "success": r.success,
                "duration_s": float(r.data_length_seconds),
                "sampling_rate": float(r.sampling_rate),
            })

        all_ok = all(r["success"] for r in results)
        return {
            "success": all_ok,
            "n_stations": len(results),
            "results": results,
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "n_stations": 0,
            "results": [],
            "error": str(e),
        }


# ── 3. HVSR processing (Phase 2) ───────────────────────────────────

@mcp.tool()
def process_hvsr(
    parallel: bool = True,
    n_workers: int = 4,
    session_id: str = "default",
) -> Dict[str, Any]:
    """Compute HVSR curves and detect peaks for every station.

    This is Phase 2 of the batch workflow.  Each station is processed
    independently (optionally in parallel) to produce H/V spectral
    ratios and peak detections.

    Parameters
    ----------
    parallel : bool
        Enable multi-process execution (default ``True``).
    n_workers : int
        Number of parallel workers (default ``4``).

    Returns
    -------
    dict
        ``{"success": bool, "n_stations": int,
           "results": [{"station": str, "success": bool,
                         "n_peaks": int, "primary_frequency": float,
                         "valid_windows": int, "total_windows": int}, ...]}``
    """
    try:
        batch = _get_batch(session_id)
        station_results = batch.process_hvsr(
            parallel=parallel, n_workers=n_workers
        )

        results: List[Dict[str, Any]] = []
        for r in station_results:
            primary_freq = 0.0
            if r.peaks:
                primary_freq = float(r.peaks[0].frequency)

            results.append({
                "station": r.station_name,
                "success": r.success,
                "n_peaks": len(r.peaks),
                "primary_frequency": primary_freq,
                "valid_windows": int(r.valid_windows),
                "total_windows": int(r.total_windows),
            })

        all_ok = all(r["success"] for r in results)
        return {
            "success": all_ok,
            "n_stations": len(results),
            "results": results,
        }
    except Exception as e:
        return {
            "success": False,
            "n_stations": 0,
            "results": [],
            "error": str(e),
        }


# ── 4. Combined analysis (Phase 3) ─────────────────────────────────

@mcp.tool()
def run_analysis(session_id: str = "default") -> Dict[str, Any]:
    """Run the combined multi-station analysis.

    This is Phase 3 of the batch workflow.  It merges per-station HVSR
    curves, detects combined peaks, and computes cross-station peak
    statistics.

    Returns
    -------
    dict
        ``{"success": bool, "n_stations": int,
           "combined_peaks": [{"frequency": float, "amplitude": float,
                                "prominence": float}, ...],
           "peak_statistics": [{"frequency_mean": float,
                                 "frequency_std": float,
                                 "amplitude_mean": float,
                                 "n_matching_stations": int}, ...]}``
    """
    try:
        batch = _get_batch(session_id)
        workflow_result = batch.run_analysis()

        combined_peaks: List[Dict[str, Any]] = []
        for p in workflow_result.combined_peaks:
            combined_peaks.append({
                "frequency": float(p.frequency),
                "amplitude": float(p.amplitude),
                "prominence": float(p.prominence),
            })

        peak_statistics: List[Dict[str, Any]] = []
        for ps in workflow_result.peak_statistics:
            peak_statistics.append({
                "frequency_mean": float(ps.mean_frequency),
                "frequency_std": float(ps.std_frequency),
                "amplitude_mean": float(ps.mean_amplitude),
                "n_matching_stations": int(ps.station_count),
            })

        return {
            "success": True,
            "n_stations": int(workflow_result.n_stations),
            "combined_peaks": combined_peaks,
            "peak_statistics": peak_statistics,
        }
    except Exception as e:
        return {
            "success": False,
            "n_stations": 0,
            "combined_peaks": [],
            "peak_statistics": [],
            "error": str(e),
        }
