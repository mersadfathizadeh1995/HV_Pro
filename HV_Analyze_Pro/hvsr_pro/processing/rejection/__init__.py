"""
Rejection Algorithms Package for HVSR Pro
==========================================

Modular window rejection system with multiple algorithm types.

Modules:
    - base: Base classes and interfaces
    - engine: Rejection engine coordinator
    - presets: Pre-configured QC pipelines
    - settings: Unified settings dataclasses
    - algorithms: Individual rejection algorithms
"""

from hvsr_pro.processing.rejection.base import (
    BaseRejectionAlgorithm,
    RejectionResult,
)
from hvsr_pro.processing.rejection.engine import RejectionEngine
from hvsr_pro.processing.rejection.presets import (
    create_preset_pipeline,
    get_available_presets,
    get_preset_description,
)
from hvsr_pro.processing.rejection.settings import (
    QCSettings,
    AlgorithmSettings,
    AmplitudeSettings,
    QualityThresholdSettings,
    STALTASettings,
    FrequencyDomainSettings,
    StatisticalOutlierSettings,
    HVSRAmplitudeSettings,
    FlatPeakSettings,
    CoxFDWRASettings,
    IsolationForestSettings,
    PRESET_DESCRIPTIONS,
    get_preset_names,
)
from hvsr_pro.processing.rejection.algorithms import (
    # Statistical
    QualityThresholdRejection,
    StatisticalOutlierRejection,
    # Time-domain
    AmplitudeRejection,
    STALTARejection,
    # Frequency-domain
    FrequencyDomainRejection,
    # HVSR-specific
    HVSRAmplitudeRejection,
    FlatPeakRejection,
    CoxFDWRARejection,
)

__all__ = [
    # Base
    'BaseRejectionAlgorithm',
    'RejectionResult',
    # Engine
    'RejectionEngine',
    # Presets
    'create_preset_pipeline',
    'get_available_presets',
    'get_preset_description',
    # Settings
    'QCSettings',
    'AlgorithmSettings',
    'AmplitudeSettings',
    'QualityThresholdSettings',
    'STALTASettings',
    'FrequencyDomainSettings',
    'StatisticalOutlierSettings',
    'HVSRAmplitudeSettings',
    'FlatPeakSettings',
    'CoxFDWRASettings',
    'IsolationForestSettings',
    'PRESET_DESCRIPTIONS',
    'get_preset_names',
    # Algorithms
    'QualityThresholdRejection',
    'StatisticalOutlierRejection',
    'AmplitudeRejection',
    'STALTARejection',
    'FrequencyDomainRejection',
    'HVSRAmplitudeRejection',
    'FlatPeakRejection',
    'CoxFDWRARejection',
]

