"""
Processing module for HVSR Pro
===============================

Contains window management, rejection algorithms, and HVSR processing.
"""

from hvsr_pro.processing.window_manager import WindowManager
from hvsr_pro.processing.window_structures import Window, WindowState, WindowCollection
from hvsr_pro.processing.rejection_engine import RejectionEngine
from hvsr_pro.processing.rejection_algorithms import (
    BaseRejectionAlgorithm,
    QualityThresholdRejection,
    StatisticalOutlierRejection,
    RejectionResult
)
from hvsr_pro.processing.rejection_advanced import (
    STALTARejection,
    FrequencyDomainRejection,
    AmplitudeRejection
)
from hvsr_pro.processing.hvsr_processor import HVSRProcessor
from hvsr_pro.processing.hvsr_structures import HVSRResult, WindowSpectrum, Peak

__all__ = [
    'WindowManager',
    'Window',
    'WindowState',
    'WindowCollection',
    'RejectionEngine',
    'BaseRejectionAlgorithm',
    'QualityThresholdRejection',
    'StatisticalOutlierRejection',
    'STALTARejection',
    'FrequencyDomainRejection',
    'AmplitudeRejection',
    'RejectionResult',
    'HVSRProcessor',
    'HVSRResult',
    'WindowSpectrum',
    'Peak',
]
