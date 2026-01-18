"""
Default Settings and Presets
=============================

Configuration management for HVSR Pro.
"""

import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional


@dataclass
class WindowSettings:
    """Window creation settings."""
    window_length: float = 30.0
    overlap: float = 0.5
    taper_type: str = 'tukey'
    taper_width: float = 0.1
    min_window_length: Optional[float] = None


@dataclass
class ProcessingSettings:
    """HVSR processing settings."""
    smoothing_method: str = 'konno_ohmachi'
    smoothing_bandwidth: float = 40.0
    f_min: float = 0.2
    f_max: float = 20.0
    n_frequencies: int = 100
    horizontal_method: str = 'geometric_mean'
    taper: str = 'hann'
    parallel: bool = False
    n_workers: Optional[int] = None


@dataclass
class QCSettings:
    """Quality control settings."""
    preset: str = 'balanced'
    enabled: bool = True
    # Cox FDWRA settings
    cox_fdwra_enabled: bool = False
    cox_n: float = 2.0
    cox_max_iterations: int = 50
    cox_distribution: str = 'lognormal'
    # Custom thresholds
    amplitude_enabled: bool = True
    quality_threshold: float = 0.5
    quality_enabled: bool = False
    stalta_enabled: bool = False
    stalta_min_ratio: float = 0.2
    stalta_max_ratio: float = 2.5


@dataclass
class ExportSettings:
    """Export settings."""
    default_format: str = 'csv'
    include_metadata: bool = True
    output_points: int = 100
    figure_dpi: int = 150
    figure_format: str = 'png'


@dataclass
class PlotSettings:
    """Plot appearance settings."""
    mean_color: str = '#1f77b4'
    median_color: str = '#ff7f0e'
    std_color: str = '#2ca02c'
    percentile_color: str = '#d62728'
    peak_color: str = '#9467bd'
    mean_linewidth: float = 2.0
    median_linewidth: float = 2.0
    std_linewidth: float = 1.0
    show_std: bool = True
    show_percentiles: bool = True
    show_individual: bool = False


@dataclass
class ApplicationSettings:
    """Complete application settings."""
    window: WindowSettings = field(default_factory=WindowSettings)
    processing: ProcessingSettings = field(default_factory=ProcessingSettings)
    qc: QCSettings = field(default_factory=QCSettings)
    export: ExportSettings = field(default_factory=ExportSettings)
    plot: PlotSettings = field(default_factory=PlotSettings)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ApplicationSettings':
        """Create from dictionary."""
        return cls(
            window=WindowSettings(**data.get('window', {})),
            processing=ProcessingSettings(**data.get('processing', {})),
            qc=QCSettings(**data.get('qc', {})),
            export=ExportSettings(**data.get('export', {})),
            plot=PlotSettings(**data.get('plot', {})),
        )


# Default settings instance
DEFAULT_SETTINGS = ApplicationSettings()


def get_default_settings() -> ApplicationSettings:
    """Get a copy of default settings."""
    return ApplicationSettings()


def load_settings(filepath: str) -> ApplicationSettings:
    """
    Load settings from file.
    
    Args:
        filepath: Path to settings file (JSON)
        
    Returns:
        ApplicationSettings instance
    """
    path = Path(filepath)
    if not path.exists():
        return get_default_settings()
    
    with open(path, 'r') as f:
        data = json.load(f)
    
    return ApplicationSettings.from_dict(data)


def save_settings(settings: ApplicationSettings, filepath: str) -> None:
    """
    Save settings to file.
    
    Args:
        settings: Settings to save
        filepath: Output path (JSON)
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'w') as f:
        json.dump(settings.to_dict(), f, indent=2)


# Processing presets
PROCESSING_PRESETS = {
    'default': {
        'smoothing_method': 'konno_ohmachi',
        'smoothing_bandwidth': 40,
        'f_min': 0.2,
        'f_max': 20.0,
        'n_frequencies': 100,
        'horizontal_method': 'geometric_mean',
    },
    'high_resolution': {
        'smoothing_method': 'konno_ohmachi',
        'smoothing_bandwidth': 20,
        'f_min': 0.1,
        'f_max': 25.0,
        'n_frequencies': 200,
        'horizontal_method': 'geometric_mean',
    },
    'quick': {
        'smoothing_method': 'konno_ohmachi',
        'smoothing_bandwidth': 60,
        'f_min': 0.5,
        'f_max': 15.0,
        'n_frequencies': 50,
        'horizontal_method': 'geometric_mean',
    },
}


# Window presets
WINDOW_PRESETS = {
    'default': {
        'window_length': 30.0,
        'overlap': 0.5,
        'taper_type': 'tukey',
    },
    'short': {
        'window_length': 15.0,
        'overlap': 0.5,
        'taper_type': 'tukey',
    },
    'long': {
        'window_length': 60.0,
        'overlap': 0.5,
        'taper_type': 'tukey',
    },
    'high_overlap': {
        'window_length': 30.0,
        'overlap': 0.75,
        'taper_type': 'tukey',
    },
}

