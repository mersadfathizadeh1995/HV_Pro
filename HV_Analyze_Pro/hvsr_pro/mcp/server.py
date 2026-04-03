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

import logging
from typing import Any, Dict

from fastmcp import FastMCP

logger = logging.getLogger(__name__)

mcp = FastMCP(
    "HVSR Pro",
    instructions=(
        "HVSR Pro is a seismology application for Horizontal-to-Vertical "
        "Spectral Ratio analysis of ambient vibration recordings.\n\n"
        "Typical workflow:\n"
        "1. load_seismic_data() — Load seismic file(s) with optional time range\n"
        "2. set_processing_params() — Adjust windowing, smoothing, frequency range\n"
        "3. set_qc_params() — (Optional) Tune quality-control algorithms\n"
        "4. set_fdwra_params() — (Optional) Enable/disable or tune FDWRA\n"
        "5. run_hvsr_analysis() — Execute the full processing pipeline\n"
        "6. detect_peaks() — Identify resonance peaks on the H/V curve\n"
        "7. export_plot() or generate_report() — Save figures and data\n\n"
        "Call get_analysis_defaults() to see all configurable parameters. "
        "Call list_formats() to discover supported file types."
    ),
)

# ---------------------------------------------------------------------------
# Session-state store  (one analysis per session for now)
# ---------------------------------------------------------------------------
_sessions: Dict[str, Any] = {}


def _get_analysis(session_id: str = "default"):
    """Return the HVSRAnalysis for *session_id*, creating if needed."""
    from hvsr_pro.api.standard.analysis import HVSRAnalysis

    if session_id not in _sessions:
        _sessions[session_id] = HVSRAnalysis()
    return _sessions[session_id]


# ---------------------------------------------------------------------------
# Import tool modules -- registration happens at import time
# ---------------------------------------------------------------------------
import hvsr_pro.mcp.introspection_tools  # noqa: F401,E402
import hvsr_pro.mcp.analysis_tools       # noqa: F401,E402
