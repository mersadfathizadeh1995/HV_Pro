"""
MCP Analysis Tools
===================

Tools for loading data, configuring, processing, detecting peaks,
exporting results/plots/reports, and managing sessions.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from hvsr_pro.mcp.server import mcp, _get_analysis

logger = logging.getLogger(__name__)


# ===================================================================
# Data loading
# ===================================================================

@mcp.tool()
def load_seismic_data(
    file_path: str,
    format: str = "auto",
    degrees_from_north: Optional[float] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    timezone_offset: int = 0,
    session_id: str = "default",
) -> Dict[str, Any]:
    """Load a seismic data file for HVSR analysis.

    Args:
        file_path: Absolute path to the seismic data file (or first of
            multiple files separated by ``|``).
        format: File format hint (``auto``, ``miniseed``, ``saf``, …).
        degrees_from_north: Sensor orientation for multi-component files.
        start_time: Optional start of time window (ISO 8601).
        end_time: Optional end of time window (ISO 8601).
        timezone_offset: Hours offset from UTC.
        session_id: Session identifier (for managing multiple analyses).

    Returns:
        Summary of the loaded data (duration, sampling rate, etc.).
    """
    analysis = _get_analysis(session_id)
    paths = file_path.split("|")
    input_arg: Any = paths[0] if len(paths) == 1 else paths

    analysis.load_data(
        input_arg,
        format=format,
        degrees_from_north=degrees_from_north,
        start_time=start_time,
        end_time=end_time,
        timezone_offset=timezone_offset,
    )
    return analysis.get_summary()


# ===================================================================
# Configuration
# ===================================================================

@mcp.tool()
def configure_analysis(
    config_json: str,
    session_id: str = "default",
) -> Dict[str, Any]:
    """Replace the full analysis configuration.

    Args:
        config_json: JSON string representing an ``HVSRAnalysisConfig``
            (or a partial dict -- missing keys keep their defaults).
        session_id: Session identifier.

    Returns:
        The effective configuration after applying changes.
    """
    from hvsr_pro.api.config import HVSRAnalysisConfig

    analysis = _get_analysis(session_id)
    data = json.loads(config_json)
    analysis.config = HVSRAnalysisConfig.from_dict(data)
    return analysis.config.to_dict()


@mcp.tool()
def set_processing_params(
    session_id: str = "default",
    window_length: Optional[float] = None,
    overlap: Optional[float] = None,
    smoothing_method: Optional[str] = None,
    smoothing_bandwidth: Optional[float] = None,
    horizontal_method: Optional[str] = None,
    freq_min: Optional[float] = None,
    freq_max: Optional[float] = None,
    n_frequencies: Optional[int] = None,
    use_parallel: Optional[bool] = None,
    n_cores: Optional[int] = None,
) -> Dict[str, Any]:
    """Adjust individual processing parameters without replacing the whole config.

    Only the parameters that are explicitly provided are changed; the rest
    keep their current value.

    Returns the updated processing section of the config.
    """
    analysis = _get_analysis(session_id)
    p = analysis.config.processing
    if window_length is not None:
        p.window_length = window_length
    if overlap is not None:
        p.overlap = overlap
    if smoothing_method is not None:
        p.smoothing_method = smoothing_method
    if smoothing_bandwidth is not None:
        p.smoothing_bandwidth = smoothing_bandwidth
    if horizontal_method is not None:
        p.horizontal_method = horizontal_method
    if freq_min is not None:
        p.freq_min = freq_min
    if freq_max is not None:
        p.freq_max = freq_max
    if n_frequencies is not None:
        p.n_frequencies = n_frequencies
    if use_parallel is not None:
        p.use_parallel = use_parallel
    if n_cores is not None:
        p.n_cores = n_cores
    return p.to_dict()


# ===================================================================
# Processing
# ===================================================================

@mcp.tool()
def run_hvsr_analysis(session_id: str = "default") -> Dict[str, Any]:
    """Run the complete HVSR processing pipeline.

    Executes data loading (if not already loaded), windowing, quality
    control, spectral computation, Cox FDWRA, and post-HVSR QC.

    Returns a JSON summary including peak frequency, window counts, and
    QC details.
    """
    analysis = _get_analysis(session_id)
    errors = analysis.config.validate()
    if errors:
        return {"success": False, "validation_errors": errors}

    result = analysis.process()
    return {"success": True, "summary": result.get_summary()}


@mcp.tool()
def run_azimuthal_analysis(session_id: str = "default") -> Dict[str, Any]:
    """Run azimuthal HVSR analysis (requires a prior ``run_hvsr_analysis``).

    Computes HVSR at multiple azimuths to detect directional site effects.

    Returns a summary of the azimuthal result.
    """
    analysis = _get_analysis(session_id)
    az_result = analysis.process_azimuthal()
    return {
        "n_azimuths": az_result.n_azimuths,
        "n_frequencies": az_result.n_frequencies,
        "mean_fn_frequency": float(az_result.mean_fn_frequency),
        "std_fn_frequency": float(az_result.std_fn_frequency),
    }


# ===================================================================
# Peak detection
# ===================================================================

@mcp.tool()
def detect_peaks(
    session_id: str = "default",
    mode: str = "auto_multi",
    n_peaks: int = 3,
    min_prominence: float = 0.3,
    min_amplitude: float = 1.0,
    use_median: bool = True,
) -> Dict[str, Any]:
    """Detect peaks on the computed HVSR curve.

    Must be called **after** ``run_hvsr_analysis``.

    Args:
        session_id: Session identifier.
        mode: Detection mode:
            ``auto_primary`` -- single highest-amplitude peak;
            ``auto_top_n`` -- top *n_peaks* by prominence;
            ``auto_multi`` -- all peaks above *min_prominence*.
        n_peaks: Number of peaks for ``auto_top_n`` mode.
        min_prominence: Minimum peak prominence (lower = more peaks).
        min_amplitude: Minimum H/V ratio to consider a peak.
        use_median: Use median curve (recommended) or mean.

    Returns:
        Dict with ``peaks`` list and ``n_peaks`` count.
    """
    analysis = _get_analysis(session_id)
    peaks = analysis.detect_peaks(
        mode=mode,
        n_peaks=n_peaks,
        min_prominence=min_prominence,
        min_amplitude=min_amplitude,
        use_median=use_median,
    )
    return {"n_peaks": len(peaks), "peaks": peaks}


# ===================================================================
# Results & export
# ===================================================================

@mcp.tool()
def get_analysis_results(session_id: str = "default") -> Dict[str, Any]:
    """Get the full summary of the last analysis run."""
    analysis = _get_analysis(session_id)
    return analysis.get_summary()


@mcp.tool()
def export_results(
    output_path: str,
    format: str = "json",
    session_id: str = "default",
) -> str:
    """Save HVSR results to a file.

    Args:
        output_path: Absolute path for the output file.
        format: ``json``, ``csv``, or ``mat``.
        session_id: Session identifier.

    Returns:
        Confirmation message with the saved path.
    """
    analysis = _get_analysis(session_id)
    analysis.save_results(output_path, fmt=format)
    return f"Results saved to {output_path}"


@mcp.tool()
def export_plot(
    output_path: str,
    plot_type: str = "hvsr",
    dpi: int = 150,
    session_id: str = "default",
) -> str:
    """Render and save a plot of the HVSR results.

    Args:
        output_path: Absolute path for the image file.
        plot_type: ``hvsr``, ``windows``, ``quality``, ``statistics``,
            or ``dashboard``.
        dpi: Image resolution.
        session_id: Session identifier.

    Returns:
        Confirmation message.
    """
    analysis = _get_analysis(session_id)
    analysis.save_plot(output_path, plot_type=plot_type, dpi=dpi)
    return f"Plot saved to {output_path}"


# ===================================================================
# Report generation
# ===================================================================

@mcp.tool()
def generate_report(
    output_dir: str,
    base_name: str = "hvsr",
    dpi: int = 150,
    session_id: str = "default",
) -> Dict[str, Any]:
    """Generate a comprehensive analysis report with all data files and plots.

    Creates a complete report directory containing:

    **Data files:**
        ``{base}_curve_complete.csv``, ``{base}_for_inversion.txt``,
        ``{base}_peaks.csv``, ``{base}_metadata.json``,
        ``{base}_summary.json``, ``analysis_config.json``

    **Plot files:**
        ``hvsr_curve.png``, ``hvsr_statistics.png``,
        ``hvsr_with_windows.png``, ``quality_metrics.png``,
        ``window_timeline.png``, ``peak_analysis.png``,
        ``complete_dashboard.png``

    Args:
        output_dir: Absolute path for the report directory.
        base_name: Prefix for data file names (default ``hvsr``).
        dpi: Plot resolution.
        session_id: Session identifier.

    Returns:
        Dict mapping logical names to absolute file paths.
    """
    analysis = _get_analysis(session_id)
    files = analysis.generate_report(output_dir, base_name=base_name, dpi=dpi)
    return {"report_dir": output_dir, "files": files, "n_files": len(files)}


# ===================================================================
# Session management
# ===================================================================

@mcp.tool()
def save_session(
    session_dir: str,
    session_id: str = "default",
) -> str:
    """Persist the analysis state (config + results + pickles) to a directory.

    The saved session can be reopened in the GUI or reloaded with
    ``load_session``.
    """
    analysis = _get_analysis(session_id)
    path = analysis.save_session(session_dir)
    return f"Session saved to {path}"


@mcp.tool()
def load_session(
    session_dir: str,
    session_id: str = "default",
) -> Dict[str, Any]:
    """Restore a previously saved analysis session.

    Returns the summary of the restored state.
    """
    analysis = _get_analysis(session_id)
    analysis.load_session(session_dir)
    return analysis.get_summary()


@mcp.tool()
def validate_config(
    config_json: str,
) -> Dict[str, Any]:
    """Validate an analysis configuration without running it.

    Args:
        config_json: JSON string of the config to validate.

    Returns:
        ``{"valid": true}`` or ``{"valid": false, "errors": [...]}``.
    """
    from hvsr_pro.api.config import HVSRAnalysisConfig

    cfg = HVSRAnalysisConfig.from_dict(json.loads(config_json))
    errors = cfg.validate()
    if errors:
        return {"valid": False, "errors": errors}
    return {"valid": True}
