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
    statistics_method: Optional[str] = None,
    peak_basis: Optional[str] = None,
    min_prominence: Optional[float] = None,
    min_amplitude: Optional[float] = None,
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
    if statistics_method is not None:
        p.statistics_method = statistics_method
    if peak_basis is not None:
        p.peak_basis = peak_basis
    if min_prominence is not None:
        p.min_prominence = min_prominence
    if min_amplitude is not None:
        p.min_amplitude = min_amplitude
    return p.to_dict()


# ===================================================================
# QC configuration
# ===================================================================

@mcp.tool()
def set_qc_params(
    session_id: str = "default",
    # Master switches
    enabled: Optional[bool] = None,
    mode: Optional[str] = None,
    phase1_enabled: Optional[bool] = None,
    phase2_enabled: Optional[bool] = None,
    # STA/LTA algorithm (Phase 1)
    sta_lta_enabled: Optional[bool] = None,
    sta_length: Optional[float] = None,
    lta_length: Optional[float] = None,
    sta_lta_min_ratio: Optional[float] = None,
    sta_lta_max_ratio: Optional[float] = None,
    # Amplitude algorithm (Phase 1)
    amplitude_enabled: Optional[bool] = None,
    clipping_threshold: Optional[float] = None,
    min_rms: Optional[float] = None,
    # Statistical Outlier algorithm (Phase 1)
    statistical_outlier_enabled: Optional[bool] = None,
    statistical_outlier_method: Optional[str] = None,
    statistical_outlier_threshold: Optional[float] = None,
    # Frequency Domain algorithm (Phase 1)
    frequency_domain_enabled: Optional[bool] = None,
    spike_threshold: Optional[float] = None,
    # Post-HVSR: Curve Outlier algorithm (Phase 2)
    curve_outlier_enabled: Optional[bool] = None,
    curve_outlier_threshold: Optional[float] = None,
    curve_outlier_max_iterations: Optional[int] = None,
    # Post-HVSR: HVSR Amplitude algorithm (Phase 2)
    hvsr_amplitude_enabled: Optional[bool] = None,
    hvsr_amplitude_min: Optional[float] = None,
    # Post-HVSR: Flat Peak algorithm (Phase 2)
    flat_peak_enabled: Optional[bool] = None,
    flatness_threshold: Optional[float] = None,
) -> Dict[str, Any]:
    """Adjust quality-control parameters without replacing the whole config.

    Only the parameters that are explicitly provided are changed; the rest
    keep their current value.  Use ``list_qc_algorithms`` to discover
    available algorithms and their defaults.

    Args:
        enabled: Master QC switch (True/False).
        mode: QC preset — ``"sesame"`` or ``"custom"``.
        phase1_enabled: Enable/disable pre-HVSR window rejection.
        phase2_enabled: Enable/disable post-HVSR curve rejection.
        sta_lta_enabled: Enable STA/LTA transient detection.
        sta_length: Short-term average window (seconds).
        lta_length: Long-term average window (seconds).
        sta_lta_min_ratio: Minimum STA/LTA ratio threshold.
        sta_lta_max_ratio: Maximum STA/LTA ratio threshold.
        amplitude_enabled: Enable amplitude/clipping check.
        clipping_threshold: Fraction of full-scale considered clipping (0-1).
        min_rms: Minimum RMS amplitude (rejects dead channels).
        statistical_outlier_enabled: Enable statistical outlier detection.
        statistical_outlier_method: ``"iqr"`` or ``"zscore"``.
        statistical_outlier_threshold: Deviation threshold.
        frequency_domain_enabled: Enable frequency-domain spike detection.
        spike_threshold: Spectral spike threshold (std devs).
        curve_outlier_enabled: Enable post-HVSR curve outlier rejection.
        curve_outlier_threshold: Outlier threshold (std devs).
        curve_outlier_max_iterations: Max rejection iterations.
        hvsr_amplitude_enabled: Enable post-HVSR amplitude check.
        hvsr_amplitude_min: Minimum H/V amplitude to keep a window.
        flat_peak_enabled: Enable flat-peak rejection.
        flatness_threshold: Flatness threshold for peak rejection.

    Returns:
        The updated QC configuration as a dict.
    """
    analysis = _get_analysis(session_id)
    qc = analysis.config.qc

    # Master switches
    if enabled is not None:
        qc.enabled = enabled
    if mode is not None:
        qc.mode = mode
    if phase1_enabled is not None:
        qc.phase1_enabled = phase1_enabled
    if phase2_enabled is not None:
        qc.phase2_enabled = phase2_enabled

    # Auto-switch to "custom" when algorithm-level params are changed
    # (otherwise SESAME mode ignores individual algorithm settings)
    algo_params = [
        sta_lta_enabled, sta_length, lta_length, sta_lta_min_ratio,
        sta_lta_max_ratio, amplitude_enabled, clipping_threshold, min_rms,
        statistical_outlier_enabled, statistical_outlier_method,
        statistical_outlier_threshold, frequency_domain_enabled,
        spike_threshold, curve_outlier_enabled, curve_outlier_threshold,
        curve_outlier_max_iterations, hvsr_amplitude_enabled,
        hvsr_amplitude_min, flat_peak_enabled, flatness_threshold,
    ]
    if mode is None and any(p is not None for p in algo_params):
        qc.mode = "custom"

    # STA/LTA
    if sta_lta_enabled is not None:
        qc.sta_lta.enabled = sta_lta_enabled
    if sta_length is not None:
        qc.sta_lta.sta_length = sta_length
    if lta_length is not None:
        qc.sta_lta.lta_length = lta_length
    if sta_lta_min_ratio is not None:
        qc.sta_lta.min_ratio = sta_lta_min_ratio
    if sta_lta_max_ratio is not None:
        qc.sta_lta.max_ratio = sta_lta_max_ratio

    # Amplitude
    if amplitude_enabled is not None:
        qc.amplitude.enabled = amplitude_enabled
    if clipping_threshold is not None:
        qc.amplitude.clipping_threshold = clipping_threshold
    if min_rms is not None:
        qc.amplitude.min_rms = min_rms

    # Statistical Outlier
    if statistical_outlier_enabled is not None:
        qc.statistical_outlier.enabled = statistical_outlier_enabled
    if statistical_outlier_method is not None:
        qc.statistical_outlier.method = statistical_outlier_method
    if statistical_outlier_threshold is not None:
        qc.statistical_outlier.threshold = statistical_outlier_threshold

    # Frequency Domain
    if frequency_domain_enabled is not None:
        qc.frequency_domain.enabled = frequency_domain_enabled
    if spike_threshold is not None:
        qc.frequency_domain.spike_threshold = spike_threshold

    # Post-HVSR: Curve Outlier
    if curve_outlier_enabled is not None:
        qc.curve_outlier.enabled = curve_outlier_enabled
    if curve_outlier_threshold is not None:
        qc.curve_outlier.threshold = curve_outlier_threshold
    if curve_outlier_max_iterations is not None:
        qc.curve_outlier.max_iterations = curve_outlier_max_iterations

    # Post-HVSR: HVSR Amplitude
    if hvsr_amplitude_enabled is not None:
        qc.hvsr_amplitude.enabled = hvsr_amplitude_enabled
    if hvsr_amplitude_min is not None:
        qc.hvsr_amplitude.min_amplitude = hvsr_amplitude_min

    # Post-HVSR: Flat Peak
    if flat_peak_enabled is not None:
        qc.flat_peak.enabled = flat_peak_enabled
    if flatness_threshold is not None:
        qc.flat_peak.flatness_threshold = flatness_threshold

    return qc.to_dict()


@mcp.tool()
def set_fdwra_params(
    session_id: str = "default",
    enabled: Optional[bool] = None,
    n: Optional[float] = None,
    max_iterations: Optional[int] = None,
    min_iterations: Optional[int] = None,
    distribution: Optional[str] = None,
) -> Dict[str, Any]:
    """Adjust Cox FDWRA (Frequency-Dependent Window Rejection) parameters.

    The FDWRA algorithm iteratively removes windows whose individual H/V
    curves deviate from the median at each frequency.  Call this before
    ``run_hvsr_analysis`` to customise or disable FDWRA.

    Args:
        enabled: Enable or disable FDWRA entirely.
        n: Rejection threshold in standard deviations (default 2.0).
        max_iterations: Maximum number of rejection passes (default 50).
        min_iterations: Minimum passes before stopping (default 1).
        distribution: Statistical distribution — ``"lognormal"`` or
            ``"normal"`` (default ``"lognormal"``).

    Returns:
        The updated FDWRA configuration as a dict.
    """
    analysis = _get_analysis(session_id)
    fdwra = analysis.config.qc.cox_fdwra

    if enabled is not None:
        fdwra.enabled = enabled
    if n is not None:
        fdwra.n = n
    if max_iterations is not None:
        fdwra.max_iterations = max_iterations
    if min_iterations is not None:
        fdwra.min_iterations = min_iterations
    if distribution is not None:
        fdwra.distribution = distribution

    return fdwra.to_dict()


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


# ===================================================================
# Plot styling
# ===================================================================

@mcp.tool()
def configure_plot_style(
    dpi: Optional[int] = None,
    title_fontsize: Optional[int] = None,
    axis_fontsize: Optional[int] = None,
    legend_fontsize: Optional[int] = None,
    show_median: Optional[bool] = None,
    show_mean: Optional[bool] = None,
    show_uncertainty: Optional[bool] = None,
    uncertainty_type: Optional[str] = None,
    show_rejected_windows: Optional[bool] = None,
    rejected_color: Optional[str] = None,
    rejected_alpha: Optional[float] = None,
    rejected_linewidth: Optional[float] = None,
    figure_format: Optional[str] = None,
    session_id: str = "default",
) -> Dict[str, Any]:
    """Configure plot appearance for exported figures.

    Only the parameters explicitly provided are changed; the rest keep
    their current values.

    Returns the updated plot style configuration.
    """
    analysis = _get_analysis(session_id)
    style = analysis.config.plot_style
    updates = {
        k: v for k, v in {
            "dpi": dpi, "title_fontsize": title_fontsize,
            "axis_fontsize": axis_fontsize, "legend_fontsize": legend_fontsize,
            "show_median": show_median, "show_mean": show_mean,
            "show_uncertainty": show_uncertainty, "uncertainty_type": uncertainty_type,
            "show_rejected_windows": show_rejected_windows,
            "rejected_color": rejected_color, "rejected_alpha": rejected_alpha,
            "rejected_linewidth": rejected_linewidth, "figure_format": figure_format,
        }.items() if v is not None
    }
    for k, v in updates.items():
        setattr(style, k, v)
    return style.to_dict()


# ===================================================================
# Plot export
# ===================================================================

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
            ``dashboard``, ``mean_vs_median``, ``quality_histogram``,
            ``selected_metrics``, ``window_timeline``,
            ``window_timeseries``, ``window_spectrogram``,
            ``peak_analysis``, ``raw_vs_adjusted``,
            ``waveform_rejection``, or ``pre_post_rejection``.
        dpi: Image resolution.
        session_id: Session identifier.

    Returns:
        Confirmation message.
    """
    analysis = _get_analysis(session_id)
    analysis.save_plot(output_path, plot_type=plot_type, dpi=dpi,
                       show_median=True, show_mean=False)
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
        ``complete_dashboard.png``, ``mean_vs_median.png``,
        ``quality_histogram.png``, ``selected_metrics.png``,
        ``window_timeseries.png``, ``window_spectrogram.png``,
        ``raw_vs_adjusted.png``, ``waveform_rejection.png``,
        ``pre_post_rejection.png``

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
