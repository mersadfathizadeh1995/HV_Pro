"""
QC Dialogs
==========

Dialog windows for quality control settings.
"""

from .advanced_qc_dialog import AdvancedQCDialog
from .algorithm_settings_dialogs import (
    open_algorithm_settings_dialog,
    AmplitudeSettingsDialog,
    STALTASettingsDialog,
    SpectralSpikeSettingsDialog,
    StatisticalOutlierSettingsDialog,
    FDWRASettingsDialog,
    HVSRAmplitudeSettingsDialog,
    FlatPeakSettingsDialog,
    ALGORITHM_DEFAULTS
)

__all__ = [
    'AdvancedQCDialog',
    'open_algorithm_settings_dialog',
    'AmplitudeSettingsDialog',
    'STALTASettingsDialog',
    'SpectralSpikeSettingsDialog',
    'StatisticalOutlierSettingsDialog',
    'FDWRASettingsDialog',
    'HVSRAmplitudeSettingsDialog',
    'FlatPeakSettingsDialog',
    'ALGORITHM_DEFAULTS'
]
