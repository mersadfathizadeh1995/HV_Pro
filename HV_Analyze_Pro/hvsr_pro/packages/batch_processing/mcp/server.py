"""
Batch Processing MCP Server
============================

FastMCP server exposing the batch HVSR analysis pipeline as tools.

Launch:
    fastmcp run hvsr_pro.packages.batch_processing.mcp.server:mcp
    python -m hvsr_pro.packages.batch_processing.mcp
"""

from __future__ import annotations

from typing import Any, Dict

from mcp.server.fastmcp import FastMCP

# ── FastMCP instance ─────────────────────────────────────────────────

mcp = FastMCP(
    "HVSR Batch Processing",
    instructions=(
        "HVSR Batch Processing server for multi-station seismic analysis.\n\n"
        "Typical workflow:\n"
        "1. import_stations_from_folder() or import_stations_from_csv()\n"
        "2. add_time_window() or import_time_windows_csv()\n"
        "3. set_processing_params() — window length, frequency range, smoothing\n"
        "4. set_qc_params() — (optional) quality-control tuning\n"
        "5. set_peak_params() — (optional) peak detection settings\n"
        "6. validate_setup() — pre-flight check\n"
        "7. prepare_data() — Phase 1: extract & convert raw files\n"
        "8. process_hvsr() — Phase 2: HVSR computation (parallel)\n"
        "9. run_analysis() — Phase 3: combined median + peak detection\n"
        "10. get_results_summary() — view combined results\n"
        "11. generate_report() or export_results() — save outputs\n\n"
        "Call get_batch_defaults() to see all configurable parameters.\n"
        "Call list_supported_formats() to discover supported file types."
    ),
)

# ── Session management ───────────────────────────────────────────────

_sessions: Dict[str, Any] = {}


def _get_batch(session_id: str = "default"):
    """Return the BatchAnalysis for *session_id*, creating if needed."""
    from ..api.batch_analysis import BatchAnalysis

    if session_id not in _sessions:
        _sessions[session_id] = BatchAnalysis()
    return _sessions[session_id]


# ── Register tool modules (imported for side effects) ────────────────
# Each module uses @mcp.tool() to register its tools.

import hvsr_pro.packages.batch_processing.mcp.setup_tools  # noqa: F401, E402
import hvsr_pro.packages.batch_processing.mcp.config_tools  # noqa: F401, E402
import hvsr_pro.packages.batch_processing.mcp.analysis_tools  # noqa: F401, E402
import hvsr_pro.packages.batch_processing.mcp.results_tools  # noqa: F401, E402
