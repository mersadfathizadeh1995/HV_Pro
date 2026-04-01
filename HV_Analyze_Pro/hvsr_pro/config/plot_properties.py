"""
Plot Properties Configuration
==============================

Dataclass for managing plot appearance properties.
Extracted from properties_dock.py for reuse across the application.
"""

from dataclasses import dataclass, asdict, field
from typing import Optional, Dict, Any


@dataclass
class PlotProperties:
    """
    Data class for plot appearance properties.
    
    Attributes:
        style_preset: Plot style preset (publication, analysis, minimal, custom)
        y_mode: Y-axis mode (auto, mean_std, percentile, manual)
        y_min: Manual Y-axis minimum
        y_max: Manual Y-axis maximum
        y_std_multiplier: Standard deviation multiplier for mean_std mode
        y_percentile: Percentile value for percentile mode
        x_mode: X-axis mode (auto, manual)
        x_min: Manual X-axis minimum
        x_max: Manual X-axis maximum
        x_scale: X-axis scale (log, linear)
        visualization_mode: Display mode (statistical, windows, both)
        show_mean: Show mean HVSR curve
        show_windows: Show individual window curves
        show_std_bands: Show standard deviation bands
        show_percentile_shading: Show percentile shading
        show_median: Show median HVSR curve
        show_acceptance_badge: Show acceptance rate badge
        show_peak_labels: Show peak frequency labels
        peak_label_style: Peak label style (full, freq_only, amp_only, minimal)
        show_legend: Show plot legend
        show_grid: Show plot grid
        background_color: Plot background color
        mean_linewidth: Mean curve line width
        window_alpha: Individual window curve opacity
        mean_color: Mean curve color (hex)
        median_color: Median curve color (hex)
        std_color: Standard deviation bands color (hex)
        percentile_color: Percentile shading color (hex)
        peak_marker_color: Peak marker color (hex)
        median_linewidth: Median curve line width
        std_linewidth: Standard deviation line width
    """

    # Style preset
    style_preset: str = "analysis"

    # Y-axis control
    y_mode: str = "auto"
    y_min: float = 0.0
    y_max: float = 10.0
    y_std_multiplier: float = 2.0
    y_percentile: float = 95.0

    # X-axis control
    x_mode: str = "auto"
    x_min: float = 0.1
    x_max: float = 50.0
    x_scale: str = "log"

    # Visualization mode
    visualization_mode: str = "windows"

    # Curve visibility
    show_mean: bool = True
    show_windows: bool = True
    show_std_bands: bool = False
    show_percentile_shading: bool = True
    show_median: bool = True

    # Annotations and stats
    show_acceptance_badge: bool = True
    show_peak_labels: bool = True
    peak_label_style: str = "full"
    show_legend: bool = True
    show_grid: bool = True

    # Aesthetics
    background_color: str = "white"
    mean_linewidth: float = 1.5
    window_alpha: float = 0.5
    
    # Line colors
    mean_color: str = "#1976D2"
    median_color: str = "#D32F2F"
    std_color: str = "#FF5722"
    percentile_color: str = "#9C27B0"
    peak_marker_color: str = "#4CAF50"
    
    # Line widths
    median_linewidth: float = 2.5
    std_linewidth: float = 1.5
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PlotProperties':
        """Create from dictionary, ignoring unknown keys."""
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered_data)
    
    def apply_publication_preset(self) -> None:
        """Apply publication-quality preset settings."""
        self.style_preset = "publication"
        self.y_mode = "auto"
        self.y_std_multiplier = 2.0
        self.show_mean = True
        self.show_windows = False
        self.show_std_bands = False
        self.show_percentile_shading = True
        self.show_median = True
        self.show_acceptance_badge = True
        self.show_peak_labels = True
        self.peak_label_style = "full"
        self.show_legend = True
        self.show_grid = False
        self.background_color = "white"
        self.mean_linewidth = 1.5
        self.median_linewidth = 2.5
        self.window_alpha = 0.5
    
    def apply_analysis_preset(self) -> None:
        """Apply analysis mode preset (default)."""
        self.style_preset = "analysis"
        self.y_mode = "auto"
        self.show_mean = True
        self.show_windows = True
        self.show_std_bands = False
        self.show_percentile_shading = True
        self.show_median = True
        self.show_acceptance_badge = True
        self.show_peak_labels = True
        self.peak_label_style = "full"
        self.show_legend = True
        self.show_grid = True
        self.background_color = "white"
        self.mean_linewidth = 1.5
        self.median_linewidth = 2.5
        self.window_alpha = 0.5
    
    def apply_minimal_preset(self) -> None:
        """Apply minimal preset settings."""
        self.style_preset = "minimal"
        self.y_mode = "auto"
        self.y_std_multiplier = 2.0
        self.show_mean = False
        self.show_windows = False
        self.show_std_bands = False
        self.show_percentile_shading = True
        self.show_median = True
        self.show_acceptance_badge = False
        self.show_peak_labels = True
        self.peak_label_style = "freq_only"
        self.show_legend = False
        self.show_grid = False
        self.background_color = "white"
        self.mean_linewidth = 1.5
        self.median_linewidth = 2.5
        self.window_alpha = 0.5
    
    def apply_preset(self, preset_name: str) -> None:
        """
        Apply a preset by name.
        
        Args:
            preset_name: One of 'publication', 'analysis', 'minimal'
        """
        presets = {
            'publication': self.apply_publication_preset,
            'analysis': self.apply_analysis_preset,
            'minimal': self.apply_minimal_preset,
        }
        if preset_name in presets:
            presets[preset_name]()
        else:
            raise ValueError(f"Unknown preset: {preset_name}")
    
    def copy(self) -> 'PlotProperties':
        """Create a copy of this PlotProperties instance."""
        return PlotProperties.from_dict(self.to_dict())


# Preset instances for convenience
PUBLICATION_PRESET = PlotProperties()
PUBLICATION_PRESET.apply_publication_preset()

ANALYSIS_PRESET = PlotProperties()
ANALYSIS_PRESET.apply_analysis_preset()

MINIMAL_PRESET = PlotProperties()
MINIMAL_PRESET.apply_minimal_preset()

# Default properties
DEFAULT_PLOT_PROPERTIES = PlotProperties()
