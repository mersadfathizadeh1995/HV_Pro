"""
MCP Introspection Tools
========================

Read-only tools for discovering supported formats, smoothing methods,
QC presets, QC algorithms, horizontal methods, and default configs.
"""
from __future__ import annotations

from typing import Any, Dict, List

from hvsr_pro.mcp.server import mcp


# ===================================================================
# Introspection tools (6)
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
