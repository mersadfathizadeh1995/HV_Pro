"""
HVSR Pro MCP Server
====================

Exposes the HVSR analysis pipeline as MCP tools so that any
LLM-based agent can drive the full workflow programmatically.

Launch (stdio transport -- Cursor / Claude Desktop)::

    fastmcp run hvsr_pro.mcp.server:mcp

Launch (HTTP / SSE for debugging)::

    fastmcp dev hvsr_pro.mcp.server:mcp
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastmcp import FastMCP

logger = logging.getLogger(__name__)

mcp = FastMCP(
    "HVSR Pro",
    instructions=(
        "HVSR Pro is a seismology application for Horizontal-to-Vertical "
        "Spectral Ratio analysis of ambient vibration recordings.  Use "
        "these tools to load seismic data, configure processing, run the "
        "HVSR pipeline, and export results.  Always call list_formats or "
        "get_analysis_defaults before asking the user for parameters."
    ),
)

# ---------------------------------------------------------------------------
# Session-state store  (one analysis per session for now)
# ---------------------------------------------------------------------------
_sessions: Dict[str, Any] = {}


def _get_analysis(session_id: str = "default"):
    """Return the HVSRAnalysis for *session_id*, creating if needed."""
    from hvsr_pro.api.analysis import HVSRAnalysis

    if session_id not in _sessions:
        _sessions[session_id] = HVSRAnalysis()
    return _sessions[session_id]


# ===================================================================
# Introspection tools
# ===================================================================

@mcp.tool()
def list_formats() -> List[Dict[str, Any]]:
    """List all seismic file formats that HVSR Pro can load.

    Returns a list of dicts with keys: id, name, extensions, multi_file,
    description.
    """
    from hvsr_pro.api.introspection import get_supported_formats
    return get_supported_formats()


@mcp.tool()
def list_smoothing_methods() -> List[Dict[str, Any]]:
    """List available spectral smoothing methods with default bandwidths."""
    from hvsr_pro.api.introspection import get_smoothing_methods
    return get_smoothing_methods()


@mcp.tool()
def list_qc_presets() -> List[Dict[str, str]]:
    """List available quality-control presets (e.g. SESAME)."""
    from hvsr_pro.api.introspection import get_qc_presets
    return get_qc_presets()


@mcp.tool()
def list_qc_algorithms() -> Dict[str, Dict[str, Any]]:
    """Describe every QC rejection algorithm with its tuneable parameters."""
    from hvsr_pro.api.introspection import get_qc_algorithm_info
    return get_qc_algorithm_info()


@mcp.tool()
def list_horizontal_methods() -> List[Dict[str, str]]:
    """List available horizontal-component combination methods."""
    from hvsr_pro.api.introspection import get_horizontal_methods
    return get_horizontal_methods()


@mcp.tool()
def get_analysis_defaults() -> Dict[str, Any]:
    """Return the default HVSRAnalysisConfig as a JSON dict.

    Useful for showing the user what parameters are available before
    they customise anything.
    """
    from hvsr_pro.api.config import HVSRAnalysisConfig
    return HVSRAnalysisConfig.sesame_default().to_dict()


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
