"""
Processing module for HVSR Pro
===============================

Contains window management, rejection algorithms, and HVSR processing.

Submodules:
    - windows: Window management and structures
    - rejection: Quality control and rejection algorithms
    - hvsr: HVSR processing engine
    - azimuthal: Azimuthal HVSR processing
    - smoothing: Spectral smoothing methods
"""

# Window management (new modular structure)
from hvsr_pro.processing.windows import (
    WindowManager,
    Window,
    WindowState,
    WindowCollection,
    detect_peaks,
    identify_fundamental_peak,
    refine_peak_frequency,
)

# Rejection system (new modular structure)
from hvsr_pro.processing.rejection import (
    RejectionEngine,
    BaseRejectionAlgorithm,
    RejectionResult,
    QualityThresholdRejection,
    StatisticalOutlierRejection,
    AmplitudeRejection,
    STALTARejection,
    FrequencyDomainRejection,
    HVSRAmplitudeRejection,
    FlatPeakRejection,
    CoxFDWRARejection,
    create_preset_pipeline,
    get_available_presets,
    get_preset_description,
)

# HVSR processing (new modular structure)
from hvsr_pro.processing.hvsr import (
    HVSRProcessor,
    HVSRResult,
    WindowSpectrum,
    Peak,
    compute_fft,
    konno_ohmachi_smoothing,
    konno_ohmachi_smoothing_fast,
    calculate_horizontal_spectrum,
    calculate_hvsr,
    logspace_frequencies,
)

# Smoothing methods (new modular structure)
from hvsr_pro.processing.smoothing import (
    SmoothingMethod,
    SmoothingConfig,
    SMOOTHING_OPERATORS,
    get_smoothing_function,
    apply_smoothing,
)

__all__ = [
    # Window management
    'WindowManager',
    'Window',
    'WindowState',
    'WindowCollection',
    # Rejection
    'RejectionEngine',
    'BaseRejectionAlgorithm',
    'RejectionResult',
    'QualityThresholdRejection',
    'StatisticalOutlierRejection',
    'AmplitudeRejection',
    'STALTARejection',
    'FrequencyDomainRejection',
    'HVSRAmplitudeRejection',
    'FlatPeakRejection',
    'CoxFDWRARejection',
    'create_preset_pipeline',
    'get_available_presets',
    'get_preset_description',
    # HVSR
    'HVSRProcessor',
    'HVSRResult',
    'WindowSpectrum',
    'Peak',
    # Smoothing
    'SmoothingMethod',
    'SmoothingConfig',
    'SMOOTHING_OPERATORS',
    'get_smoothing_function',
    'apply_smoothing',
]
