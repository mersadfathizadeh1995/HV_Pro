"""
QC Settings Data Structures
============================

Unified settings dataclasses for all QC/rejection algorithms.
Provides a single source of truth for QC configuration.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Tuple
import json
from pathlib import Path


@dataclass
class AlgorithmSettings:
    """
    Base settings for a rejection algorithm.
    
    Attributes:
        enabled: Whether algorithm is active
        params: Algorithm-specific parameters
    """
    enabled: bool = False
    params: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'enabled': self.enabled,
            'params': self.params.copy()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AlgorithmSettings':
        """Create from dictionary."""
        return cls(
            enabled=data.get('enabled', False),
            params=data.get('params', {}).copy()
        )


@dataclass
class AmplitudeSettings(AlgorithmSettings):
    """Settings for amplitude rejection algorithm."""
    enabled: bool = True
    params: Dict[str, Any] = field(default_factory=dict)
    # No specific parameters - uses internal defaults


@dataclass 
class QualityThresholdSettings(AlgorithmSettings):
    """Settings for quality threshold rejection."""
    enabled: bool = False
    params: Dict[str, Any] = field(default_factory=lambda: {
        'threshold': 0.5  # Overall quality score threshold (0-1, lower is stricter)
    })


@dataclass
class STALTASettings(AlgorithmSettings):
    """Settings for STA/LTA rejection algorithm."""
    enabled: bool = False
    params: Dict[str, Any] = field(default_factory=lambda: {
        'sta_length': 1.0,    # Short-term average window (seconds)
        'lta_length': 30.0,   # Long-term average window (seconds)
        'min_ratio': 0.15,    # Minimum STA/LTA ratio
        'max_ratio': 2.5      # Maximum STA/LTA ratio
    })


@dataclass
class FrequencyDomainSettings(AlgorithmSettings):
    """Settings for frequency domain rejection."""
    enabled: bool = False
    params: Dict[str, Any] = field(default_factory=lambda: {
        'spike_threshold': 3.0  # Threshold for spectral spike detection (sigma)
    })


@dataclass
class StatisticalOutlierSettings(AlgorithmSettings):
    """Settings for statistical outlier rejection."""
    enabled: bool = False
    params: Dict[str, Any] = field(default_factory=lambda: {
        'method': 'iqr',      # Detection method: 'iqr' or 'zscore'
        'threshold': 2.0      # IQR multiplier or z-score threshold
    })


@dataclass
class HVSRAmplitudeSettings(AlgorithmSettings):
    """Settings for HVSR peak amplitude rejection (post-HVSR)."""
    enabled: bool = False
    params: Dict[str, Any] = field(default_factory=lambda: {
        'min_amplitude': 1.0  # Minimum HVSR peak amplitude
    })


@dataclass
class FlatPeakSettings(AlgorithmSettings):
    """Settings for flat peak detection (post-HVSR)."""
    enabled: bool = False
    params: Dict[str, Any] = field(default_factory=lambda: {
        'flatness_threshold': 0.15  # Peak flatness threshold
    })


@dataclass
class CoxFDWRASettings:
    """
    Settings for Cox et al. (2020) FDWRA algorithm.
    
    This is the industry-standard post-HVSR rejection algorithm
    for ensuring peak frequency consistency across windows.
    """
    enabled: bool = False
    n: float = 2.0                    # Standard deviation multiplier
    max_iterations: int = 50          # Maximum iterations
    min_iterations: int = 1           # Minimum iterations before convergence check
    distribution_fn: str = 'lognormal'  # Distribution for fn: 'lognormal' or 'normal'
    distribution_mc: str = 'lognormal'  # Distribution for mean curve
    search_range_hz: Optional[Tuple[float, float]] = None  # Frequency search range
    convergence_threshold_diff: float = 0.01  # Convergence threshold for difference
    convergence_threshold_std: float = 0.01   # Convergence threshold for std
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'enabled': self.enabled,
            'n': self.n,
            'max_iterations': self.max_iterations,
            'min_iterations': self.min_iterations,
            'distribution_fn': self.distribution_fn,
            'distribution_mc': self.distribution_mc,
            'search_range_hz': self.search_range_hz,
            'convergence_threshold_diff': self.convergence_threshold_diff,
            'convergence_threshold_std': self.convergence_threshold_std
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CoxFDWRASettings':
        """Create from dictionary."""
        search_range = data.get('search_range_hz')
        if search_range is not None and isinstance(search_range, (list, tuple)):
            search_range = tuple(search_range)
        
        return cls(
            enabled=data.get('enabled', False),
            n=data.get('n', 2.0),
            max_iterations=data.get('max_iterations', 50),
            min_iterations=data.get('min_iterations', 1),
            distribution_fn=data.get('distribution_fn', 'lognormal'),
            distribution_mc=data.get('distribution_mc', 'lognormal'),
            search_range_hz=search_range,
            convergence_threshold_diff=data.get('convergence_threshold_diff', 0.01),
            convergence_threshold_std=data.get('convergence_threshold_std', 0.01)
        )


@dataclass
class IsolationForestSettings(AlgorithmSettings):
    """Settings for Isolation Forest ML rejection (optional)."""
    enabled: bool = False
    params: Dict[str, Any] = field(default_factory=lambda: {
        'contamination': 0.1,    # Expected proportion of outliers
        'n_estimators': 100,     # Number of trees
        'random_state': 42       # Random seed for reproducibility
    })


@dataclass
class QCSettings:
    """
    Complete QC configuration.
    
    Provides a unified structure for all QC/rejection settings,
    supporting both preset modes and custom algorithm configuration.
    
    Attributes:
        enabled: Master QC enable/disable
        mode: 'preset' or 'custom'
        preset: Preset name if mode is 'preset'
        
        Pre-HVSR algorithms (time-domain):
        - amplitude: Amplitude rejection
        - quality_threshold: Quality threshold rejection
        - sta_lta: STA/LTA rejection
        - frequency_domain: Frequency domain rejection
        - statistical_outlier: Statistical outlier rejection
        
        Post-HVSR algorithms (frequency-domain):
        - hvsr_amplitude: HVSR peak amplitude rejection
        - flat_peak: Flat peak detection
        
        Cox FDWRA:
        - cox_fdwra: Cox et al. (2020) FDWRA settings
        
        ML algorithms (optional):
        - isolation_forest: Isolation Forest settings
    
    Example:
        >>> settings = QCSettings()
        >>> settings.mode = 'custom'
        >>> settings.sta_lta.enabled = True
        >>> settings.sta_lta.params['min_ratio'] = 0.1
        >>> settings.cox_fdwra.enabled = True
    """
    # Master settings
    enabled: bool = True
    mode: str = 'preset'  # 'preset' or 'custom'
    preset: str = 'balanced'  # conservative, balanced, aggressive, sesame, publication
    
    # Pre-HVSR algorithms (time-domain)
    amplitude: AmplitudeSettings = field(default_factory=AmplitudeSettings)
    quality_threshold: QualityThresholdSettings = field(default_factory=QualityThresholdSettings)
    sta_lta: STALTASettings = field(default_factory=STALTASettings)
    frequency_domain: FrequencyDomainSettings = field(default_factory=FrequencyDomainSettings)
    statistical_outlier: StatisticalOutlierSettings = field(default_factory=StatisticalOutlierSettings)
    
    # Post-HVSR algorithms (frequency-domain)
    hvsr_amplitude: HVSRAmplitudeSettings = field(default_factory=HVSRAmplitudeSettings)
    flat_peak: FlatPeakSettings = field(default_factory=FlatPeakSettings)
    
    # Cox FDWRA
    cox_fdwra: CoxFDWRASettings = field(default_factory=CoxFDWRASettings)
    
    # ML algorithms (optional)
    isolation_forest: IsolationForestSettings = field(default_factory=IsolationForestSettings)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary for serialization."""
        return {
            'enabled': self.enabled,
            'mode': self.mode,
            'preset': self.preset,
            'algorithms': {
                'amplitude': self.amplitude.to_dict(),
                'quality_threshold': self.quality_threshold.to_dict(),
                'sta_lta': self.sta_lta.to_dict(),
                'frequency_domain': self.frequency_domain.to_dict(),
                'statistical_outlier': self.statistical_outlier.to_dict(),
                'hvsr_amplitude': self.hvsr_amplitude.to_dict(),
                'flat_peak': self.flat_peak.to_dict(),
                'isolation_forest': self.isolation_forest.to_dict(),
            },
            'cox_fdwra': self.cox_fdwra.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'QCSettings':
        """Create QCSettings from dictionary."""
        settings = cls(
            enabled=data.get('enabled', True),
            mode=data.get('mode', 'preset'),
            preset=data.get('preset', 'balanced')
        )
        
        # Load algorithm settings
        algos = data.get('algorithms', {})
        
        if 'amplitude' in algos:
            settings.amplitude = AmplitudeSettings.from_dict(algos['amplitude'])
        if 'quality_threshold' in algos:
            settings.quality_threshold = QualityThresholdSettings.from_dict(algos['quality_threshold'])
        if 'sta_lta' in algos:
            settings.sta_lta = STALTASettings.from_dict(algos['sta_lta'])
        if 'frequency_domain' in algos:
            settings.frequency_domain = FrequencyDomainSettings.from_dict(algos['frequency_domain'])
        if 'statistical_outlier' in algos:
            settings.statistical_outlier = StatisticalOutlierSettings.from_dict(algos['statistical_outlier'])
        if 'hvsr_amplitude' in algos:
            settings.hvsr_amplitude = HVSRAmplitudeSettings.from_dict(algos['hvsr_amplitude'])
        if 'flat_peak' in algos:
            settings.flat_peak = FlatPeakSettings.from_dict(algos['flat_peak'])
        if 'isolation_forest' in algos:
            settings.isolation_forest = IsolationForestSettings.from_dict(algos['isolation_forest'])
        
        # Load Cox FDWRA settings
        if 'cox_fdwra' in data:
            settings.cox_fdwra = CoxFDWRASettings.from_dict(data['cox_fdwra'])
        
        return settings
    
    def save(self, filepath: str) -> None:
        """Save settings to JSON file."""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, filepath: str) -> 'QCSettings':
        """Load settings from JSON file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls.from_dict(data)
    
    def apply_preset(self, preset: str) -> None:
        """
        Apply a preset configuration.
        
        Args:
            preset: Preset name (conservative, balanced, aggressive, sesame, publication)
        """
        # Reset all to defaults
        self.amplitude = AmplitudeSettings()
        self.quality_threshold = QualityThresholdSettings()
        self.sta_lta = STALTASettings()
        self.frequency_domain = FrequencyDomainSettings()
        self.statistical_outlier = StatisticalOutlierSettings()
        self.hvsr_amplitude = HVSRAmplitudeSettings()
        self.flat_peak = FlatPeakSettings()
        self.cox_fdwra = CoxFDWRASettings()
        self.isolation_forest = IsolationForestSettings()
        
        # Apply preset-specific settings
        if preset == 'conservative':
            self.amplitude.enabled = True
            self.quality_threshold.enabled = True
            self.quality_threshold.params['threshold'] = 0.2
            
        elif preset == 'balanced':
            self.amplitude.enabled = True
            
        elif preset == 'aggressive':
            self.amplitude.enabled = True
            self.quality_threshold.enabled = True
            self.quality_threshold.params['threshold'] = 0.35
            self.sta_lta.enabled = True
            self.sta_lta.params = {
                'sta_length': 1.0,
                'lta_length': 30.0,
                'min_ratio': 0.08,
                'max_ratio': 3.5
            }
            self.frequency_domain.enabled = True
            self.frequency_domain.params['spike_threshold'] = 4.0
            self.statistical_outlier.enabled = True
            self.statistical_outlier.params['threshold'] = 2.5
            
        elif preset == 'sesame':
            self.amplitude.enabled = True
            self.quality_threshold.enabled = True
            self.quality_threshold.params['threshold'] = 0.3
            self.cox_fdwra.enabled = True
            
        elif preset == 'publication':
            self.amplitude.enabled = True
            self.hvsr_amplitude.enabled = True
            self.hvsr_amplitude.params['min_amplitude'] = 1.0
            self.flat_peak.enabled = True
            self.flat_peak.params['flatness_threshold'] = 0.15
            self.cox_fdwra.enabled = True
        
        self.mode = 'preset'
        self.preset = preset
    
    def get_enabled_pre_hvsr_algorithms(self) -> list:
        """Get list of enabled pre-HVSR algorithm names."""
        enabled = []
        if self.amplitude.enabled:
            enabled.append('amplitude')
        if self.quality_threshold.enabled:
            enabled.append('quality_threshold')
        if self.sta_lta.enabled:
            enabled.append('sta_lta')
        if self.frequency_domain.enabled:
            enabled.append('frequency_domain')
        if self.statistical_outlier.enabled:
            enabled.append('statistical_outlier')
        return enabled
    
    def get_enabled_post_hvsr_algorithms(self) -> list:
        """Get list of enabled post-HVSR algorithm names."""
        enabled = []
        if self.hvsr_amplitude.enabled:
            enabled.append('hvsr_amplitude')
        if self.flat_peak.enabled:
            enabled.append('flat_peak')
        return enabled
    
    @property
    def custom_algorithms(self) -> Dict[str, Any]:
        """
        Get custom algorithms settings as a dictionary.
        
        This property provides backward compatibility with code that
        expects a dictionary of algorithm settings.
        
        Returns:
            Dictionary with all algorithm settings
        """
        return {
            'amplitude': self.amplitude.to_dict(),
            'quality_threshold': self.quality_threshold.to_dict(),
            'sta_lta': self.sta_lta.to_dict(),
            'frequency_domain': self.frequency_domain.to_dict(),
            'statistical_outlier': self.statistical_outlier.to_dict(),
            'hvsr_amplitude': self.hvsr_amplitude.to_dict(),
            'flat_peak': self.flat_peak.to_dict(),
            'cox_fdwra': self.cox_fdwra.to_dict(),
            'isolation_forest': self.isolation_forest.to_dict(),
        }
    
    def __repr__(self) -> str:
        status = "enabled" if self.enabled else "disabled"
        if self.mode == 'preset':
            return f"QCSettings({status}, preset='{self.preset}')"
        else:
            pre = len(self.get_enabled_pre_hvsr_algorithms())
            post = len(self.get_enabled_post_hvsr_algorithms())
            cox = "cox" if self.cox_fdwra.enabled else ""
            return f"QCSettings({status}, custom: {pre} pre-HVSR, {post} post-HVSR{', ' + cox if cox else ''})"


# Preset descriptions for UI
PRESET_DESCRIPTIONS = {
    "conservative": "Only rejects obvious problems (dead channels, clipping). Best for noisy data.",
    "balanced": "Amplitude checks only. Recommended for most datasets.",
    "aggressive": "Strict QC with STA/LTA, frequency, and statistical checks. For clean data.",
    "sesame": "SESAME-compliant processing with Cox FDWRA for publication-quality results.",
    "publication": "4-condition rejection: HVSR amplitude, peak consistency, flat peaks."
}


def get_preset_names() -> list:
    """Get list of available preset names."""
    return list(PRESET_DESCRIPTIONS.keys())


def get_preset_description(preset: str) -> str:
    """Get description for a preset."""
    return PRESET_DESCRIPTIONS.get(preset, "")
