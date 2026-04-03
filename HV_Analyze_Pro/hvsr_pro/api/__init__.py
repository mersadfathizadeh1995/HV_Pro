"""
HVSR Pro API
============

High-level programmatic API for HVSR analysis.

Quick start::

    from hvsr_pro.api import HVSRAnalysis
    from hvsr_pro.api.config import HVSRAnalysisConfig

    analysis = HVSRAnalysis()
    analysis.load_data("seismic_data.mseed")
    result = analysis.process()
    print(f"Peak frequency: {result.hvsr_result.primary_peak.frequency} Hz")
    analysis.save_results("results.json")
"""

from hvsr_pro.api.standard import HVSRAnalysis, AnalysisResult, QCSummary
from hvsr_pro.api.config import (
    HVSRAnalysisConfig,
    ProcessingConfig,
    DataLoadConfig,
    TimeRangeConfig,
    QCConfig,
    CoxFDWRAConfig,
)
from hvsr_pro.api.batch import batch_process
from hvsr_pro.api.introspection import (
    get_supported_formats,
    get_smoothing_methods,
    get_qc_presets,
    get_qc_algorithm_info,
    get_horizontal_methods,
)

__all__ = [
    # Core
    "HVSRAnalysis",
    "AnalysisResult",
    "QCSummary",
    # Config
    "HVSRAnalysisConfig",
    "ProcessingConfig",
    "DataLoadConfig",
    "TimeRangeConfig",
    "QCConfig",
    "CoxFDWRAConfig",
    # Batch
    "batch_process",
    # Introspection
    "get_supported_formats",
    "get_smoothing_methods",
    "get_qc_presets",
    "get_qc_algorithm_info",
    "get_horizontal_methods",
]
