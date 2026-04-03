"""
Batch Processing – MCP Configuration Tools
============================================

Four ``@mcp.tool()`` endpoints for adjusting processing, QC,
peak-detection, and output parameters on a :class:`BatchAnalysis`
session.
"""

from __future__ import annotations

from typing import Optional

from .server import mcp, _get_batch


# ── 1. Processing parameters ────────────────────────────────────────


@mcp.tool()
def set_processing_params(
    window_length: Optional[float] = None,
    overlap: Optional[float] = None,
    freq_min: Optional[float] = None,
    freq_max: Optional[float] = None,
    n_frequencies: Optional[int] = None,
    smoothing_method: Optional[str] = None,
    smoothing_bandwidth: Optional[float] = None,
    horizontal_method: Optional[str] = None,
    taper: Optional[str] = None,
    detrend: Optional[str] = None,
    statistics_method: Optional[str] = None,
    session_id: str = "default",
) -> dict:
    """Adjust HVSR processing parameters. Only provided values are changed."""
    try:
        batch = _get_batch(session_id)
        kwargs = {
            k: v
            for k, v in locals().items()
            if v is not None and k not in ("session_id", "batch")
        }
        batch.set_processing(**kwargs)
        return batch._config.processing.to_dict()
    except Exception as e:
        return {"error": str(e)}


# ── 2. Quality-control parameters ───────────────────────────────────


@mcp.tool()
def set_qc_params(
    # Master / algorithm enable flags
    stalta_enabled: Optional[bool] = None,
    amplitude_enabled: Optional[bool] = None,
    statistical_enabled: Optional[bool] = None,
    fdwra_enabled: Optional[bool] = None,
    hvsr_amplitude_enabled: Optional[bool] = None,
    flat_peak_enabled: Optional[bool] = None,
    curve_outlier_enabled: Optional[bool] = None,
    # STA/LTA sub-params  (prefix: stalta_)
    sta_length: Optional[float] = None,
    lta_length: Optional[float] = None,
    sta_lta_min_ratio: Optional[float] = None,
    sta_lta_max_ratio: Optional[float] = None,
    # Amplitude sub-params  (prefix: amplitude_)
    clipping_threshold: Optional[float] = None,
    min_rms: Optional[float] = None,
    # Statistical sub-params  (prefix: statistical_)
    statistical_method: Optional[str] = None,
    statistical_threshold: Optional[float] = None,
    # FDWRA sub-params  (prefix: fdwra_)
    fdwra_n: Optional[float] = None,
    fdwra_max_iterations: Optional[int] = None,
    fdwra_distribution: Optional[str] = None,
    # HVSR amplitude sub-params  (prefix: hvsr_amplitude_)
    hvsr_amplitude_min: Optional[float] = None,
    # Flat-peak sub-params  (prefix: flat_peak_)
    flatness_threshold: Optional[float] = None,
    # Curve-outlier sub-params  (prefix: curve_outlier_)
    curve_outlier_threshold: Optional[float] = None,
    curve_outlier_max_iterations: Optional[int] = None,
    session_id: str = "default",
) -> dict:
    """Adjust quality-control parameters. Only provided values are changed.

    Enable flags (e.g. ``stalta_enabled``) are set directly on the QC
    config.  Sub-parameters are forwarded with their algorithm prefix so
    ``BatchAnalysis.set_qc`` can route them to the correct sub-config
    (e.g. ``sta_length`` → ``stalta_sta_length``).
    """
    try:
        batch = _get_batch(session_id)

        # Map of (tool param name) → (BatchAnalysis.set_qc kwarg name).
        # Enable flags go through directly; sub-params need the prefix
        # expected by the prefix-stripping logic in set_qc().
        _PREFIX_MAP = {
            "sta_length": "stalta_sta_length",
            "lta_length": "stalta_lta_length",
            "sta_lta_min_ratio": "stalta_sta_lta_min_ratio",
            "sta_lta_max_ratio": "stalta_sta_lta_max_ratio",
            "clipping_threshold": "amplitude_clipping_threshold",
            "min_rms": "amplitude_min_rms",
            "statistical_method": "statistical_method",
            "statistical_threshold": "statistical_threshold",
            "fdwra_n": "fdwra_n",
            "fdwra_max_iterations": "fdwra_max_iterations",
            "fdwra_distribution": "fdwra_distribution",
            "hvsr_amplitude_min": "hvsr_amplitude_min",
            "flatness_threshold": "flat_peak_flatness_threshold",
            "curve_outlier_threshold": "curve_outlier_threshold",
            "curve_outlier_max_iterations": "curve_outlier_max_iterations",
        }

        kwargs: dict = {}
        loc = locals()
        for name in (
            "stalta_enabled", "amplitude_enabled", "statistical_enabled",
            "fdwra_enabled", "hvsr_amplitude_enabled", "flat_peak_enabled",
            "curve_outlier_enabled",
        ):
            if loc[name] is not None:
                kwargs[name] = loc[name]

        for tool_name, qc_name in _PREFIX_MAP.items():
            val = loc[tool_name]
            if val is not None:
                kwargs[qc_name] = val

        batch.set_qc(**kwargs)
        return batch._config.qc.to_dict()
    except Exception as e:
        return {"error": str(e)}


# ── 3. Peak-detection parameters ────────────────────────────────────


@mcp.tool()
def set_peak_params(
    auto_mode: Optional[bool] = None,
    peak_basis: Optional[str] = None,
    min_prominence: Optional[float] = None,
    min_amplitude: Optional[float] = None,
    n_peaks: Optional[int] = None,
    freq_tolerance: Optional[float] = None,
    session_id: str = "default",
) -> dict:
    """Adjust peak-detection parameters. Only provided values are changed."""
    try:
        batch = _get_batch(session_id)
        kwargs = {
            k: v
            for k, v in locals().items()
            if v is not None and k not in ("session_id", "batch")
        }
        batch.set_peaks(**kwargs)
        return batch._config.peaks.to_dict()
    except Exception as e:
        return {"error": str(e)}


# ── 4. Output parameters ────────────────────────────────────────────


@mcp.tool()
def set_output_params(
    save_png: Optional[bool] = None,
    save_pdf: Optional[bool] = None,
    figure_dpi: Optional[int] = None,
    save_json: Optional[bool] = None,
    save_csv: Optional[bool] = None,
    save_mat: Optional[bool] = None,
    export_excel: Optional[bool] = None,
    generate_standard_figure: Optional[bool] = None,
    generate_hvsr_pro_figure: Optional[bool] = None,
    generate_statistics_figure: Optional[bool] = None,
    output_dir: Optional[str] = None,
    session_id: str = "default",
) -> dict:
    """Adjust output and export parameters. Only provided values are changed.

    If *output_dir* is provided it is also propagated to the top-level
    batch configuration via ``batch.configure(output_dir=...)``.
    """
    try:
        batch = _get_batch(session_id)
        kwargs = {
            k: v
            for k, v in locals().items()
            if v is not None and k not in ("session_id", "batch")
        }
        batch.set_output(**kwargs)
        if output_dir is not None:
            batch.configure(output_dir=output_dir)
        return batch._config.output.to_dict()
    except Exception as e:
        return {"error": str(e)}
