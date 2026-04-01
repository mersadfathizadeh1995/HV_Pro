"""
Rejection Algorithms
====================

Individual rejection algorithm implementations.

Categories:
    - Statistical: Quality threshold, outlier detection
    - Time-domain: Amplitude, STA/LTA
    - Frequency-domain: Spectral analysis
    - HVSR-specific: Peak amplitude, flat peak, Cox FDWRA
    - Machine Learning: Isolation Forest, ensemble methods
"""

from hvsr_pro.processing.rejection.algorithms.statistical import (
    QualityThresholdRejection,
    StatisticalOutlierRejection,
)
from hvsr_pro.processing.rejection.algorithms.amplitude import (
    AmplitudeRejection,
)
from hvsr_pro.processing.rejection.algorithms.stalta import (
    STALTARejection,
)
from hvsr_pro.processing.rejection.algorithms.frequency import (
    FrequencyDomainRejection,
)
from hvsr_pro.processing.rejection.algorithms.hvsr_qc import (
    HVSRAmplitudeRejection,
    FlatPeakRejection,
)
from hvsr_pro.processing.rejection.algorithms.curve_outlier import (
    CurveOutlierRejection,
)
from hvsr_pro.processing.rejection.algorithms.cox_fdwra import (
    CoxFDWRARejection,
)

# Optional ML algorithms
try:
    from hvsr_pro.processing.rejection.algorithms.ml import (
        IsolationForestRejection,
        EnsembleRejection,
    )
    HAS_ML = True
except ImportError:
    HAS_ML = False

__all__ = [
    # Statistical
    'QualityThresholdRejection',
    'StatisticalOutlierRejection',
    # Time-domain
    'AmplitudeRejection',
    'STALTARejection',
    # Frequency-domain
    'FrequencyDomainRejection',
    # HVSR-specific
    'HVSRAmplitudeRejection',
    'FlatPeakRejection',
    'CurveOutlierRejection',
    'CoxFDWRARejection',
]

# Add ML algorithms if available
if HAS_ML:
    __all__.extend(['IsolationForestRejection', 'EnsembleRejection'])

