"""
HVSR Pro API -- Introspection Helpers
======================================

Thin wrappers over existing registries that return JSON-safe dicts.
Useful for MCP tools, CLI help, and automated documentation.
"""

from __future__ import annotations

from typing import Any, Dict, List


def get_supported_formats() -> List[Dict[str, Any]]:
    """Return every supported file format with metadata.

    Each dict contains: ``id``, ``name``, ``extensions``, ``multi_file``,
    ``description``.
    """
    from hvsr_pro.loaders import FORMAT_INFO

    result = []
    for fmt_id, info in FORMAT_INFO.items():
        result.append({
            "id": fmt_id,
            "name": info.get("name", fmt_id),
            "extensions": info.get("extensions", []),
            "multi_file": info.get("multi_file", False),
            "description": info.get("description", ""),
        })
    return result


def get_smoothing_methods() -> List[Dict[str, Any]]:
    """Return all available smoothing methods with default bandwidths.

    Each dict contains: ``name``, ``default_bandwidth``,
    ``bandwidth_range``, ``description``.
    """
    from hvsr_pro.processing.smoothing.settings import list_available_methods
    return list_available_methods()


def get_qc_presets() -> List[Dict[str, str]]:
    """Return available QC preset names and descriptions."""
    from hvsr_pro.processing.rejection.presets import (
        get_available_presets,
        get_preset_description,
    )

    return [
        {"name": name, "description": get_preset_description(name)}
        for name in get_available_presets()
    ]


def get_qc_algorithm_info() -> Dict[str, Dict[str, Any]]:
    """Return per-algorithm parameter schemas.

    Keys are algorithm ids (``amplitude``, ``sta_lta``, …).
    Values describe each tuneable parameter with type, default, and
    human-readable description.
    """
    return {
        "amplitude": {
            "phase": "pre-hvsr",
            "description": "Reject windows with extreme amplitudes, clipping, or near-zero RMS.",
            "params": {
                "max_amplitude": {"type": "float", "default": None, "description": "Maximum allowed amplitude (auto if None)"},
                "min_rms": {"type": "float", "default": 1e-10, "description": "Minimum RMS to avoid dead channels"},
                "clipping_threshold": {"type": "float", "default": 0.95, "description": "Fraction of max range indicating clipping"},
            },
        },
        "quality_threshold": {
            "phase": "pre-hvsr",
            "description": "Reject windows whose composite quality score falls below a threshold.",
            "params": {
                "threshold": {"type": "float", "default": 0.5, "range": [0, 1], "description": "Minimum quality score (0-1)"},
            },
        },
        "sta_lta": {
            "phase": "pre-hvsr",
            "description": "Short-Term / Long-Term Average ratio for transient detection.",
            "params": {
                "sta_length": {"type": "float", "default": 1.0, "description": "STA window length (seconds)"},
                "lta_length": {"type": "float", "default": 30.0, "description": "LTA window length (seconds)"},
                "min_ratio": {"type": "float", "default": 0.2, "description": "Minimum STA/LTA ratio"},
                "max_ratio": {"type": "float", "default": 2.5, "description": "Maximum STA/LTA ratio"},
            },
        },
        "frequency_domain": {
            "phase": "pre-hvsr",
            "description": "Detect and reject spectral spikes (narrow-band noise).",
            "params": {
                "spike_threshold": {"type": "float", "default": 3.0, "description": "Sigma threshold for spike detection"},
            },
        },
        "statistical_outlier": {
            "phase": "pre-hvsr",
            "description": "Flag outlier windows by IQR or Z-score on quality metrics.",
            "params": {
                "method": {"type": "str", "default": "iqr", "choices": ["iqr", "zscore"], "description": "Detection method"},
                "threshold": {"type": "float", "default": 2.0, "description": "IQR multiplier or Z-score cutoff"},
            },
        },
        "hvsr_amplitude": {
            "phase": "post-hvsr",
            "description": "Reject windows whose HVSR peak amplitude is too low.",
            "params": {
                "min_amplitude": {"type": "float", "default": 1.0, "description": "Minimum H/V ratio at peak"},
            },
        },
        "flat_peak": {
            "phase": "post-hvsr",
            "description": "Reject windows with a flat (non-distinct) HVSR peak.",
            "params": {
                "flatness_threshold": {"type": "float", "default": 0.15, "description": "Flatness metric threshold"},
            },
        },
        "curve_outlier": {
            "phase": "post-hvsr",
            "description": "Iterative median-MAD sigma clipping on full H/V curves.",
            "params": {
                "threshold": {"type": "float", "default": 3.0, "description": "MAD-sigma threshold"},
                "max_iterations": {"type": "int", "default": 5, "description": "Maximum clipping iterations"},
                "metric": {"type": "str", "default": "mean", "choices": ["mean", "median"], "description": "Central-tendency metric"},
            },
        },
        "cox_fdwra": {
            "phase": "post-hvsr",
            "description": "Cox et al. (2020) peak-frequency consistency rejection.",
            "params": {
                "n": {"type": "float", "default": 2.0, "description": "Standard deviation multiplier"},
                "max_iterations": {"type": "int", "default": 50, "description": "Max FDWRA iterations"},
                "min_iterations": {"type": "int", "default": 1, "description": "Min iterations before convergence check"},
                "distribution": {"type": "str", "default": "lognormal", "choices": ["lognormal", "normal"], "description": "Distribution assumption"},
            },
        },
    }


def get_horizontal_methods() -> List[Dict[str, str]]:
    """Return available horizontal-component combination methods."""
    return [
        {"id": "geometric_mean", "description": "Geometric mean of H1 and H2 spectra (SESAME recommended)"},
        {"id": "arithmetic_mean", "description": "Arithmetic mean of H1 and H2 spectra"},
        {"id": "quadratic", "description": "Quadratic (RMS) mean of H1 and H2 spectra"},
        {"id": "maximum", "description": "Maximum of H1 and H2 spectra at each frequency"},
    ]
