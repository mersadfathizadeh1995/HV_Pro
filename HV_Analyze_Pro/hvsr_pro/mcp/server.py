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
    from hvsr_pro.api.standard.analysis import HVSRAnalysis

    if session_id not in _sessions:
        _sessions[session_id] = HVSRAnalysis()
    return _sessions[session_id]


# ---------------------------------------------------------------------------
# Import tool modules -- registration happens at import time
# ---------------------------------------------------------------------------
import hvsr_pro.mcp.introspection_tools  # noqa: F401,E402
import hvsr_pro.mcp.analysis_tools       # noqa: F401,E402
