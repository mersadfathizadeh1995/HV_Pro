"""
Properties dock for real-time plot appearance control.

Refactored version using modular section components.

Provides interactive controls for:
- Plot style presets (Publication, Analysis, Minimal)
- Y-axis and X-axis limits
- Curve visibility toggles
- Peak annotation styles
- Background and theme options
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any

try:
    from PyQt5.QtWidgets import (
        QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QScrollArea
    )
    from PyQt5.QtCore import pyqtSignal, Qt
    from PyQt5.QtGui import QFont
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


@dataclass
class PlotProperties:
    """Data class for plot appearance properties."""

    # Style preset
    style_preset: str = "analysis"  # publication, analysis, minimal, custom

    # Y-axis control
    y_mode: str = "auto"  # auto, mean_std, percentile, manual
    y_min: float = 0.0
    y_max: float = 10.0
    y_std_multiplier: float = 2.0
    y_percentile: float = 95.0

    # X-axis control
    x_mode: str = "auto"  # auto, manual
    x_min: float = 0.1
    x_max: float = 50.0
    x_scale: str = "log"  # log, linear

    # Visualization mode
    visualization_mode: str = "windows"  # statistical, windows, both

    # Curve visibility
    show_mean: bool = True
    show_windows: bool = True
    show_std_bands: bool = False
    show_percentile_shading: bool = True
    show_median: bool = True

    # Annotations and stats
    show_acceptance_badge: bool = True
    show_peak_labels: bool = True
    peak_label_style: str = "full"  # full, freq_only, amp_only, minimal
    show_legend: bool = True
    show_grid: bool = True

    # Aesthetics
    background_color: str = "white"  # white, gray, light_gray
    mean_linewidth: float = 1.5
    window_alpha: float = 0.5
    
    # Line colors
    mean_color: str = "#1976D2"  # Blue
    median_color: str = "#D32F2F"  # Red
    std_color: str = "#FF5722"  # Deep Orange
    percentile_color: str = "#9C27B0"  # Purple
    peak_marker_color: str = "#4CAF50"  # Green
    
    # Line widths
    median_linewidth: float = 2.5
    std_linewidth: float = 1.5
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'PlotProperties':
        """Create from dictionary."""
        return cls(**data)
    
    def apply_preset(self, preset: str):
        """Apply a named preset."""
        presets = {
            'publication': self._get_publication_settings,
            'analysis': self._get_analysis_settings,
            'minimal': self._get_minimal_settings,
        }
        if preset in presets:
            presets[preset]()
            self.style_preset = preset
    
    def _get_publication_settings(self):
        """Apply publication-quality preset."""
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
    
    def _get_analysis_settings(self):
        """Apply analysis mode preset (current default)."""
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
    
    def _get_minimal_settings(self):
        """Apply minimal preset."""
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
        self.show_grid = True
        self.background_color = "white"
        self.mean_linewidth = 1.5
        self.median_linewidth = 2.5
        self.window_alpha = 0.5


if HAS_PYQT5:
    # Import section components
    from .sections import (
        PresetSection,
        AxisSection,
        CurvesSection,
        AnnotationsSection,
        AppearanceSection,
    )
    
    class PropertiesDock(QDockWidget):
        """
        Dock widget for controlling plot appearance properties.
        
        Refactored to use modular section components.
        
        Signals:
            properties_changed: Emitted when any property changes
            visualization_mode_changed: Emitted when visualization mode changes
        """

        properties_changed = pyqtSignal(object)  # PlotProperties object
        visualization_mode_changed = pyqtSignal(str)

        def __init__(self, parent=None):
            super().__init__("Properties", parent)
            
            # Properties object
            self.properties = PlotProperties()
            
            # Create UI using section components
            self._create_ui()
            
            # Connect section signals
            self._connect_signals()
            
            # Initialize with analysis preset
            self.apply_preset("analysis")
        
        def _create_ui(self):
            """Create the properties UI using section components."""
            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.setSpacing(5)
            
            # Title
            title = QLabel("Plot Appearance")
            title.setFont(QFont("Arial", 10, QFont.Bold))
            title.setAlignment(Qt.AlignCenter)
            layout.addWidget(title)
            
            # === SECTIONS (using modular components) ===
            
            # Style Presets
            self.preset_section = PresetSection()
            layout.addWidget(self.preset_section)
            
            # Y-Axis Controls
            self.yaxis_section = AxisSection(axis='y')
            layout.addWidget(self.yaxis_section)
            
            # X-Axis Controls
            self.xaxis_section = AxisSection(axis='x')
            layout.addWidget(self.xaxis_section)
            
            # Curve Visibility & Visualization Mode
            self.curves_section = CurvesSection(include_viz_mode=True)
            layout.addWidget(self.curves_section)
            
            # Annotations & Statistics
            self.annotations_section = AnnotationsSection()
            layout.addWidget(self.annotations_section)
            
            # Colors & Style
            self.appearance_section = AppearanceSection()
            layout.addWidget(self.appearance_section)
            
            # === ACTION BUTTONS ===
            btn_layout = QHBoxLayout()
            
            apply_btn = QPushButton("Apply")
            apply_btn.setStyleSheet(
                "QPushButton { font-weight: bold; background-color: #4CAF50; color: white; }"
            )
            apply_btn.clicked.connect(self.apply_properties)
            btn_layout.addWidget(apply_btn)
            
            reset_btn = QPushButton("Reset")
            reset_btn.clicked.connect(self.reset_to_defaults)
            btn_layout.addWidget(reset_btn)
            
            layout.addLayout(btn_layout)
            layout.addStretch()

            # Wrap in scroll area
            scroll_area = QScrollArea()
            scroll_area.setWidget(widget)
            scroll_area.setWidgetResizable(True)
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            
            self.setWidget(scroll_area)
        
        def _connect_signals(self):
            """Connect signals from section components."""
            # Preset changes
            self.preset_section.preset_changed.connect(self._on_preset_changed)
            
            # Visualization mode changes
            self.curves_section.visualization_mode_changed.connect(
                self._on_visualization_mode_changed
            )
        
        def _on_preset_changed(self, preset: str):
            """Handle preset selection change."""
            if preset != "custom":
                self.apply_preset(preset)
        
        def _on_visualization_mode_changed(self, mode: str):
            """Handle visualization mode change."""
            self.properties.visualization_mode = mode
            self.visualization_mode_changed.emit(mode)
        
        def apply_preset(self, preset: str):
            """Apply a named preset and update UI."""
            self.properties.apply_preset(preset)
            self._update_ui_from_properties()
            self.properties_changed.emit(self.properties)
        
        def _update_ui_from_properties(self):
            """Update all UI controls from properties object."""
            p = self.properties
            
            # Y-axis
            self.yaxis_section.set_y_settings({
                'y_mode': p.y_mode,
                'y_std_multiplier': p.y_std_multiplier,
                'y_percentile': p.y_percentile,
                'y_min': p.y_min,
                'y_max': p.y_max,
            })
            
            # X-axis
            self.xaxis_section.set_x_settings({
                'x_mode': p.x_mode,
                'x_scale': p.x_scale,
                'x_min': p.x_min,
                'x_max': p.x_max,
            })
            
            # Curves
            self.curves_section.set_visibility({
                'show_mean': p.show_mean,
                'show_windows': p.show_windows,
                'show_std_bands': p.show_std_bands,
                'show_percentile_shading': p.show_percentile_shading,
                'show_median': p.show_median,
            })
            self.curves_section.set_visualization_mode(p.visualization_mode)
            
            # Annotations
            self.annotations_section.set_settings({
                'show_acceptance_badge': p.show_acceptance_badge,
                'show_peak_labels': p.show_peak_labels,
                'peak_label_style': p.peak_label_style,
                'show_legend': p.show_legend,
                'show_grid': p.show_grid,
            })
            
            # Appearance
            self.appearance_section.set_settings({
                'background_color': p.background_color,
                'mean_color': p.mean_color,
                'median_color': p.median_color,
                'std_color': p.std_color,
                'percentile_color': p.percentile_color,
                'peak_marker_color': p.peak_marker_color,
                'mean_linewidth': p.mean_linewidth,
                'median_linewidth': p.median_linewidth,
                'std_linewidth': p.std_linewidth,
                'window_alpha': p.window_alpha,
            })
        
        def _update_properties_from_ui(self):
            """Update properties object from all UI controls."""
            p = self.properties
            
            # Y-axis
            y_settings = self.yaxis_section.get_y_settings()
            p.y_mode = y_settings.get('y_mode', p.y_mode)
            p.y_std_multiplier = y_settings.get('y_std_multiplier', p.y_std_multiplier)
            p.y_percentile = y_settings.get('y_percentile', p.y_percentile)
            p.y_min = y_settings.get('y_min', p.y_min)
            p.y_max = y_settings.get('y_max', p.y_max)
            
            # X-axis
            x_settings = self.xaxis_section.get_x_settings()
            p.x_mode = x_settings.get('x_mode', p.x_mode)
            p.x_scale = x_settings.get('x_scale', p.x_scale)
            p.x_min = x_settings.get('x_min', p.x_min)
            p.x_max = x_settings.get('x_max', p.x_max)
            
            # Curves
            curves = self.curves_section.get_visibility()
            p.show_mean = curves.get('show_mean', p.show_mean)
            p.show_windows = curves.get('show_windows', p.show_windows)
            p.show_std_bands = curves.get('show_std_bands', p.show_std_bands)
            p.show_percentile_shading = curves.get('show_percentile_shading', p.show_percentile_shading)
            p.show_median = curves.get('show_median', p.show_median)
            p.visualization_mode = self.curves_section.get_visualization_mode()
            
            # Annotations
            annot = self.annotations_section.get_settings()
            p.show_acceptance_badge = annot.get('show_acceptance_badge', p.show_acceptance_badge)
            p.show_peak_labels = annot.get('show_peak_labels', p.show_peak_labels)
            p.peak_label_style = annot.get('peak_label_style', p.peak_label_style)
            p.show_legend = annot.get('show_legend', p.show_legend)
            p.show_grid = annot.get('show_grid', p.show_grid)
            
            # Appearance
            appear = self.appearance_section.get_settings()
            p.background_color = appear.get('background_color', p.background_color)
            p.mean_color = appear.get('mean_color', p.mean_color)
            p.median_color = appear.get('median_color', p.median_color)
            p.std_color = appear.get('std_color', p.std_color)
            p.percentile_color = appear.get('percentile_color', p.percentile_color)
            p.peak_marker_color = appear.get('peak_marker_color', p.peak_marker_color)
            p.mean_linewidth = appear.get('mean_linewidth', p.mean_linewidth)
            p.median_linewidth = appear.get('median_linewidth', p.median_linewidth)
            p.std_linewidth = appear.get('std_linewidth', p.std_linewidth)
            p.window_alpha = appear.get('window_alpha', p.window_alpha)
            
            # Mark as custom if user changed settings
            p.style_preset = "custom"
        
        def apply_properties(self):
            """Apply current UI settings to properties and emit signal."""
            self._update_properties_from_ui()
            self.properties_changed.emit(self.properties)
        
        def reset_to_defaults(self):
            """Reset to default analysis preset."""
            self.apply_preset("analysis")
            self.preset_section.set_preset("analysis")
        
        def get_properties(self) -> PlotProperties:
            """Get current properties object."""
            self._update_properties_from_ui()
            return self.properties
        
        def set_properties(self, properties: PlotProperties):
            """Set properties from external object."""
            self.properties = properties
            self._update_ui_from_properties()

else:
    # Dummy classes when PyQt5 not available
    class PropertiesDock:
        def __init__(self, *args, **kwargs):
            pass
