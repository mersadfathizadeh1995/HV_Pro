"""
Batch Results & Export MCP Tools
=================================

Registers 5 tools for retrieving HVSR batch results, exporting data,
and generating reports.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import numpy as np

from .server import mcp, _get_batch


# ── Helpers ──────────────────────────────────────────────────────────


def _numpy_to_python(obj: Any) -> Any:
    """Recursively convert numpy types to native Python types."""
    if isinstance(obj, np.ndarray):
        return [_numpy_to_python(v) for v in obj.tolist()]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, dict):
        return {k: _numpy_to_python(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_numpy_to_python(v) for v in obj]
    return obj


# ── 1. get_results_summary ───────────────────────────────────────────


@mcp.tool()
def get_results_summary(session_id: str = "default") -> Dict[str, Any]:
    """Return a combined results overview for all stations in the batch.

    Includes the combined median HVSR curve, detected peaks, and a
    per-station summary with success status and primary f0.
    """
    try:
        batch = _get_batch(session_id)

        combined = batch.get_combined_result()
        combined = _numpy_to_python(combined)

        hvsr_results = batch.get_hvsr_results()
        per_station: List[Dict[str, Any]] = []
        for res in hvsr_results:
            primary_f0 = None
            if res.peaks:
                pk = res.peaks[0]
                primary_f0 = float(
                    pk.frequency if hasattr(pk, "frequency") else pk["frequency"]
                )

            per_station.append({
                "name": res.station_name,
                "success": res.success,
                "n_peaks": len(res.peaks) if res.peaks else 0,
                "primary_f0": primary_f0,
                "valid_windows": int(res.valid_windows),
                "total_windows": int(res.total_windows),
            })

        return {
            "n_stations": len(per_station),
            "combined": combined,
            "per_station": per_station,
        }
    except Exception as e:
        return {"error": str(e)}


# ── 2. get_station_result ────────────────────────────────────────────


@mcp.tool()
def get_station_result(
    station_name: str,
    session_id: str = "default",
) -> Dict[str, Any]:
    """Return detailed HVSR result for a single station.

    Includes the full frequency/HVSR arrays, detected peaks, window
    counts, and rejection reasons.
    """
    try:
        batch = _get_batch(session_id)
        hvsr_results = batch.get_hvsr_results()

        target = None
        for res in hvsr_results:
            if res.station_name == station_name:
                target = res
                break

        if target is None:
            return {"error": f"Station '{station_name}' not found in results."}

        peaks = []
        for p in (target.peaks or []):
            freq = float(p.frequency if hasattr(p, "frequency") else p["frequency"])
            amp = float(p.amplitude if hasattr(p, "amplitude") else p["amplitude"])
            prom = float(
                getattr(p, "prominence", 0.0) if hasattr(p, "prominence")
                else p.get("prominence", 0.0) if isinstance(p, dict) else 0.0
            )
            peaks.append({"frequency": freq, "amplitude": amp, "prominence": prom})

        return {
            "station_name": station_name,
            "success": target.success,
            "frequencies": _numpy_to_python(
                target.frequencies.tolist() if target.frequencies is not None else []
            ),
            "median_hvsr": _numpy_to_python(
                target.median_hvsr.tolist() if target.median_hvsr is not None else []
            ),
            "mean_hvsr": _numpy_to_python(
                target.mean_hvsr.tolist() if target.mean_hvsr is not None else []
            ),
            "std_hvsr": _numpy_to_python(
                target.std_hvsr.tolist() if target.std_hvsr is not None else []
            ),
            "peaks": peaks,
            "valid_windows": int(target.valid_windows),
            "total_windows": int(target.total_windows),
            "error": target.error,
        }
    except Exception as e:
        return {"error": str(e)}


# ── 3. generate_report ───────────────────────────────────────────────


@mcp.tool()
def generate_report(
    output_dir: str,
    dpi: int = 300,
    session_id: str = "default",
) -> Dict[str, Any]:
    """Generate a full batch analysis report with plots and data files.

    Creates a directory of plots, CSVs, and metadata at *output_dir*.
    Returns a manifest listing all generated files.
    """
    try:
        batch = _get_batch(session_id)
        files = batch.generate_report(output_dir, dpi)

        return {
            "report_dir": output_dir,
            "files": _numpy_to_python(files),
            "n_files": len(files) if isinstance(files, dict) else 0,
        }
    except Exception as e:
        return {"error": str(e)}


# ── 4. export_results ────────────────────────────────────────────────


@mcp.tool()
def export_results(
    output_dir: str,
    formats: Optional[List[str]] = None,
    session_id: str = "default",
) -> Dict[str, Any]:
    """Export batch results in one or more formats.

    Supported formats: CSV, JSON, MAT, Excel.
    If *formats* is not specified all formats are exported.
    """
    try:
        batch = _get_batch(session_id)
        files = batch.export_results(output_dir)

        return {
            "output_dir": output_dir,
            "files": _numpy_to_python(files),
        }
    except Exception as e:
        return {"error": str(e)}


# ── 5. detect_combined_peaks ─────────────────────────────────────────


@mcp.tool()
def detect_combined_peaks(
    min_prominence: float = 0.5,
    min_amplitude: float = 2.0,
    n_peaks: int = 3,
    session_id: str = "default",
) -> Dict[str, Any]:
    """Re-detect peaks on the combined median HVSR curve.

    Useful for adjusting peak-detection thresholds after an initial
    analysis without reprocessing all stations.
    """
    try:
        batch = _get_batch(session_id)
        raw_peaks = batch.detect_combined_peaks(
            min_prominence, min_amplitude, n_peaks
        )

        peaks = []
        for p in (raw_peaks or []):
            peaks.append({
                "frequency": float(p.frequency),
                "amplitude": float(p.amplitude),
                "prominence": float(getattr(p, "prominence", 0)),
                "peak_type": getattr(p, "peak_type", ""),
            })

        return {
            "n_peaks": len(peaks),
            "peaks": peaks,
        }
    except Exception as e:
        return {"error": str(e)}
