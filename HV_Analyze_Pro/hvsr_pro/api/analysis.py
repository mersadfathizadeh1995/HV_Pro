"""
Backward-compatibility shim.

All real logic lives in ``hvsr_pro.api.standard.analysis``.
This file re-exports the public names so that existing code using
``from hvsr_pro.api.analysis import HVSRAnalysis`` keeps working.
"""
from hvsr_pro.api.standard.analysis import (  # noqa: F401
    HVSRAnalysis,
    AnalysisResult,
    QCSummary,
    ProgressCallback,
)

__all__ = ["HVSRAnalysis", "AnalysisResult", "QCSummary", "ProgressCallback"]
