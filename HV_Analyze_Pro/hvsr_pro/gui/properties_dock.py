"""
Properties dock for real-time plot appearance control.

Provides interactive controls for:
- Plot style presets (Publication, Analysis, Minimal)
- Y-axis limits (Auto, Mean±Std, Percentile, Manual)
- Curve visibility toggles
- Peak annotation styles
- Background and theme options
- Acceptance badge display
"""

from dataclasses import dataclass, asdict
from typing import Optional

try:
    from PyQt5.QtWidgets import (
        QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
        QGroupBox, QComboBox, QPushButton, QCheckBox,
        QLabel, QDoubleSpinBox, QSpinBox, QFrame, QScrollArea,
        QRadioButton
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
    show_std_bands: bool = True
    show_percentile_shading: bool = False
    show_median: bool = False

    # Annotations and stats
    show_acceptance_badge: bool = True
    show_peak_labels: bool = True
    peak_label_style: str = "full"  # full, freq_only, amp_only, minimal
    show_legend: bool = True
    show_grid: bool = False

    # Aesthetics
    background_color: str = "white"  # white, gray, light_gray
    mean_linewidth: float = 2.0
    window_alpha: float = 0.5
    
    def to_dict(self):
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary."""
        return cls(**data)
    
    def get_publication_preset(self):
        """Get publication-quality preset."""
        self.style_preset = "publication"
        self.y_mode = "mean_std"
        self.y_std_multiplier = 2.0
        self.show_mean = True
        self.show_windows = False
        self.show_std_bands = False
        self.show_percentile_shading = True
        self.show_median = False
        self.show_acceptance_badge = True
        self.show_peak_labels = True
        self.peak_label_style = "full"
        self.show_legend = True
        self.show_grid = False
        self.background_color = "white"
        self.mean_linewidth = 2.5
        self.window_alpha = 0.5
    
    def get_analysis_preset(self):
        """Get analysis mode preset (current default)."""
        self.style_preset = "analysis"
        self.y_mode = "auto"
        self.show_mean = True
        self.show_windows = True
        self.show_std_bands = True
        self.show_percentile_shading = False
        self.show_median = False
        self.show_acceptance_badge = False
        self.show_peak_labels = True
        self.peak_label_style = "full"
        self.show_legend = True
        self.show_grid = False
        self.background_color = "white"
        self.mean_linewidth = 2.0
        self.window_alpha = 0.5
    
    def get_minimal_preset(self):
        """Get minimal preset."""
        self.style_preset = "minimal"
        self.y_mode = "mean_std"
        self.y_std_multiplier = 2.0
        self.show_mean = True
        self.show_windows = False
        self.show_std_bands = False
        self.show_percentile_shading = False
        self.show_median = False
        self.show_acceptance_badge = False
        self.show_peak_labels = True
        self.peak_label_style = "freq_only"
        self.show_legend = False
        self.show_grid = False
        self.background_color = "white"
        self.mean_linewidth = 2.0
        self.window_alpha = 0.5


if HAS_PYQT5:
    
    class CollapsibleSection(QWidget):
        """Collapsible section widget for organizing properties."""
        
        def __init__(self, title: str, parent=None):
            super().__init__(parent)
            self.is_collapsed = False
            
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(2)
            
            # Header button
            self.toggle_btn = QPushButton(f"▼ {title}")
            self.toggle_btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 5px;
                    background-color: #E0E0E0;
                    border: none;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #D0D0D0;
                }
            """)
            self.toggle_btn.clicked.connect(self.toggle)
            layout.addWidget(self.toggle_btn)
            
            # Content widget
            self.content_widget = QWidget()
            self.content_layout = QVBoxLayout(self.content_widget)
            self.content_layout.setContentsMargins(10, 5, 5, 5)
            layout.addWidget(self.content_widget)
        
        def toggle(self):
            """Toggle section collapsed state."""
            self.is_collapsed = not self.is_collapsed
            self.content_widget.setVisible(not self.is_collapsed)
            
            # Update button text
            title = self.toggle_btn.text()[2:]  # Remove arrow
            arrow = "▶" if self.is_collapsed else "▼"
            self.toggle_btn.setText(f"{arrow} {title}")
        
        def add_widget(self, widget):
            """Add widget to content area."""
            self.content_layout.addWidget(widget)
        
        def add_layout(self, layout):
            """Add layout to content area."""
            self.content_layout.addLayout(layout)
    
    
    class PropertiesDock(QDockWidget):
        """
        Dock widget for controlling plot appearance properties.
        
        Features:
        - Plot style presets
        - Y-axis control
        - Curve visibility
        - Peak annotations
        - Background/theme
        - Real-time updates
        
        Signals:
            properties_changed: Emitted when any property changes
            visualization_mode_changed: Emitted when visualization mode changes
        """

        properties_changed = pyqtSignal(object)  # PlotProperties object
        visualization_mode_changed = pyqtSignal(str)  # mode: 'statistical', 'windows', or 'both'

        def __init__(self, parent=None):
            super().__init__("Properties", parent)
            
            # Properties object
            self.properties = PlotProperties()
            
            # Create UI
            self._create_ui()
            
            # Initialize with analysis preset
            self.apply_preset("analysis")
        
        def _create_ui(self):
            """Create the properties UI."""
            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.setSpacing(5)
            
            # Title
            title = QLabel("Plot Appearance")
            title.setFont(QFont("Arial", 10, QFont.Bold))
            title.setAlignment(Qt.AlignCenter)
            layout.addWidget(title)
            
            # === STYLE PRESETS ===
            preset_section = self._create_preset_section()
            layout.addWidget(preset_section)
            
            # === Y-AXIS CONTROL ===
            yaxis_section = self._create_yaxis_section()
            layout.addWidget(yaxis_section)

            # === X-AXIS CONTROL ===
            xaxis_section = self._create_xaxis_section()
            layout.addWidget(xaxis_section)

            # === VISUALIZATION MODE ===
            vizmode_section = self._create_visualization_mode_section()
            layout.addWidget(vizmode_section)

            # === CURVE VISIBILITY ===
            curves_section = self._create_curves_section()
            layout.addWidget(curves_section)
            
            # === ANNOTATIONS ===
            annot_section = self._create_annotations_section()
            layout.addWidget(annot_section)
            
            # === APPEARANCE ===
            appearance_section = self._create_appearance_section()
            layout.addWidget(appearance_section)
            
            # === ACTION BUTTONS ===
            btn_layout = QHBoxLayout()
            
            apply_btn = QPushButton("Apply")
            apply_btn.setStyleSheet("QPushButton { font-weight: bold; background-color: #4CAF50; color: white; }")
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
        
        def _create_preset_section(self) -> CollapsibleSection:
            """Create plot style preset section."""
            section = CollapsibleSection("Plot Style Presets")
            
            # Preset dropdown
            preset_layout = QHBoxLayout()
            preset_layout.addWidget(QLabel("Style:"))
            
            self.preset_combo = QComboBox()
            self.preset_combo.addItem("📊 Analysis (Current)", "analysis")
            self.preset_combo.addItem("📄 Publication Quality", "publication")
            self.preset_combo.addItem("📝 Minimal", "minimal")
            self.preset_combo.addItem("⚙️ Custom", "custom")
            self.preset_combo.currentIndexChanged.connect(self.on_preset_changed)
            preset_layout.addWidget(self.preset_combo)
            
            section.add_layout(preset_layout)
            
            # Description label
            self.preset_desc = QLabel("Interactive analysis with all windows visible")
            self.preset_desc.setWordWrap(True)
            self.preset_desc.setStyleSheet("QLabel { color: #666; font-size: 9px; }")
            section.add_widget(self.preset_desc)
            
            return section
        
        def _create_yaxis_section(self) -> CollapsibleSection:
            """Create Y-axis control section."""
            section = CollapsibleSection("Y-Axis Limits")
            
            # Mode dropdown
            mode_layout = QHBoxLayout()
            mode_layout.addWidget(QLabel("Mode:"))
            
            self.ymode_combo = QComboBox()
            self.ymode_combo.addItem("Auto (Data-driven)", "auto")
            self.ymode_combo.addItem("Mean ± Std", "mean_std")
            self.ymode_combo.addItem("Percentile-based", "percentile")
            self.ymode_combo.addItem("Manual", "manual")
            self.ymode_combo.currentIndexChanged.connect(self.on_ymode_changed)
            mode_layout.addWidget(self.ymode_combo)
            
            section.add_layout(mode_layout)
            
            # Std multiplier (for mean_std mode)
            std_layout = QHBoxLayout()
            std_layout.addWidget(QLabel("Std Multiplier:"))
            self.std_spin = QDoubleSpinBox()
            self.std_spin.setRange(0.5, 5.0)
            self.std_spin.setValue(2.0)
            self.std_spin.setSingleStep(0.5)
            self.std_spin.setToolTip("Y-max = mean_max + N×std_max")
            std_layout.addWidget(self.std_spin)
            section.add_layout(std_layout)
            self.std_widget = std_layout.parentWidget()
            
            # Percentile (for percentile mode)
            perc_layout = QHBoxLayout()
            perc_layout.addWidget(QLabel("Percentile:"))
            self.percentile_spin = QDoubleSpinBox()
            self.percentile_spin.setRange(80.0, 99.9)
            self.percentile_spin.setValue(95.0)
            self.percentile_spin.setSingleStep(1.0)
            self.percentile_spin.setSuffix("%")
            perc_layout.addWidget(self.percentile_spin)
            section.add_layout(perc_layout)
            
            # Manual limits
            manual_layout = QHBoxLayout()
            manual_layout.addWidget(QLabel("Min:"))
            self.ymin_spin = QDoubleSpinBox()
            self.ymin_spin.setRange(0.0, 100.0)
            self.ymin_spin.setValue(0.0)
            self.ymin_spin.setSingleStep(0.5)
            manual_layout.addWidget(self.ymin_spin)
            
            manual_layout.addWidget(QLabel("Max:"))
            self.ymax_spin = QDoubleSpinBox()
            self.ymax_spin.setRange(0.1, 100.0)
            self.ymax_spin.setValue(10.0)
            self.ymax_spin.setSingleStep(0.5)
            manual_layout.addWidget(self.ymax_spin)
            
            section.add_layout(manual_layout)

            return section

        def _create_xaxis_section(self) -> CollapsibleSection:
            """Create X-axis control section."""
            section = CollapsibleSection("X-Axis (Frequency) Limits")

            # Mode dropdown
            mode_layout = QHBoxLayout()
            mode_layout.addWidget(QLabel("Mode:"))

            self.xmode_combo = QComboBox()
            self.xmode_combo.addItem("Auto (Data-driven)", "auto")
            self.xmode_combo.addItem("Manual", "manual")
            self.xmode_combo.currentIndexChanged.connect(self.on_xmode_changed)
            mode_layout.addWidget(self.xmode_combo)

            section.add_layout(mode_layout)

            # Scale selection
            scale_layout = QHBoxLayout()
            scale_layout.addWidget(QLabel("Scale:"))

            self.xscale_combo = QComboBox()
            self.xscale_combo.addItem("Logarithmic", "log")
            self.xscale_combo.addItem("Linear", "linear")
            scale_layout.addWidget(self.xscale_combo)

            section.add_layout(scale_layout)

            # Manual limits
            manual_layout = QHBoxLayout()
            manual_layout.addWidget(QLabel("Min (Hz):"))
            self.xmin_spin = QDoubleSpinBox()
            self.xmin_spin.setRange(0.01, 1000.0)
            self.xmin_spin.setValue(0.1)
            self.xmin_spin.setSingleStep(0.1)
            self.xmin_spin.setDecimals(2)
            manual_layout.addWidget(self.xmin_spin)

            manual_layout.addWidget(QLabel("Max (Hz):"))
            self.xmax_spin = QDoubleSpinBox()
            self.xmax_spin.setRange(0.1, 1000.0)
            self.xmax_spin.setValue(50.0)
            self.xmax_spin.setSingleStep(1.0)
            self.xmax_spin.setDecimals(1)
            manual_layout.addWidget(self.xmax_spin)

            section.add_layout(manual_layout)

            return section

        def _create_visualization_mode_section(self) -> CollapsibleSection:
            """Create visualization mode section."""
            section = CollapsibleSection("Visualization Mode")

            # Radio buttons for visualization modes
            self.viz_rb_statistical = QRadioButton("Statistical View")
            self.viz_rb_statistical.setToolTip("Mean + uncertainty band (clean, publication-ready)")
            self.viz_rb_statistical.toggled.connect(self._on_viz_mode_changed)
            section.add_widget(self.viz_rb_statistical)

            self.viz_rb_windows = QRadioButton("Individual Windows")
            self.viz_rb_windows.setToolTip("All window curves + mean (best for QC)")
            self.viz_rb_windows.toggled.connect(self._on_viz_mode_changed)
            section.add_widget(self.viz_rb_windows)

            self.viz_rb_both = QRadioButton("Both (Combined)")
            self.viz_rb_both.setToolTip("All curves + statistics (comprehensive)")
            self.viz_rb_both.toggled.connect(self._on_viz_mode_changed)
            section.add_widget(self.viz_rb_both)

            # Set default
            self.viz_rb_windows.setChecked(True)

            # Info label
            info_label = QLabel("Changes apply immediately to plot")
            info_label.setStyleSheet("QLabel { color: #666; font-size: 9px; font-style: italic; }")
            section.add_widget(info_label)

            return section

        def _on_viz_mode_changed(self):
            """Handle visualization mode change."""
            if not self.sender().isChecked():
                return  # Only respond to the checked button

            mode = 'windows'  # default
            if self.viz_rb_statistical.isChecked():
                mode = 'statistical'
            elif self.viz_rb_windows.isChecked():
                mode = 'windows'
            elif self.viz_rb_both.isChecked():
                mode = 'both'

            # Update property
            self.properties.visualization_mode = mode

            # Emit signal for immediate update
            self.visualization_mode_changed.emit(mode)

        def _create_curves_section(self) -> CollapsibleSection:
            """Create curve visibility section."""
            section = CollapsibleSection("Curve Display")
            
            self.show_mean_cb = QCheckBox("Show Mean Curve")
            self.show_mean_cb.setChecked(True)
            section.add_widget(self.show_mean_cb)
            
            self.show_windows_cb = QCheckBox("Show Individual Windows")
            self.show_windows_cb.setChecked(True)
            section.add_widget(self.show_windows_cb)
            
            self.show_std_cb = QCheckBox("Show ±1σ Bands (dashed)")
            self.show_std_cb.setChecked(True)
            section.add_widget(self.show_std_cb)
            
            self.show_percentile_cb = QCheckBox("Show Percentile Shading (16th-84th)")
            self.show_percentile_cb.setChecked(False)
            section.add_widget(self.show_percentile_cb)
            
            self.show_median_cb = QCheckBox("Show Median Curve")
            self.show_median_cb.setChecked(False)
            section.add_widget(self.show_median_cb)
            
            return section
        
        def _create_annotations_section(self) -> CollapsibleSection:
            """Create annotations section."""
            section = CollapsibleSection("Annotations & Statistics")
            
            self.show_badge_cb = QCheckBox("Show Acceptance Rate Badge")
            self.show_badge_cb.setChecked(True)
            section.add_widget(self.show_badge_cb)
            
            self.show_peaks_cb = QCheckBox("Show Peak Labels")
            self.show_peaks_cb.setChecked(True)
            section.add_widget(self.show_peaks_cb)
            
            # Peak label style
            style_layout = QHBoxLayout()
            style_layout.addWidget(QLabel("  Label Style:"))
            self.peak_style_combo = QComboBox()
            self.peak_style_combo.addItem("Full (freq + amp)", "full")
            self.peak_style_combo.addItem("Frequency only", "freq_only")
            self.peak_style_combo.addItem("Amplitude only", "amp_only")
            self.peak_style_combo.addItem("Minimal (marker only)", "minimal")
            style_layout.addWidget(self.peak_style_combo)
            section.add_layout(style_layout)
            
            self.show_legend_cb = QCheckBox("Show Legend")
            self.show_legend_cb.setChecked(True)
            section.add_widget(self.show_legend_cb)
            
            self.show_grid_cb = QCheckBox("Show Grid Lines")
            self.show_grid_cb.setChecked(False)
            section.add_widget(self.show_grid_cb)
            
            return section
        
        def _create_appearance_section(self) -> CollapsibleSection:
            """Create appearance section."""
            section = CollapsibleSection("Colors & Style")
            
            # Background color
            bg_layout = QHBoxLayout()
            bg_layout.addWidget(QLabel("Background:"))
            self.bg_combo = QComboBox()
            self.bg_combo.addItem("White", "white")
            self.bg_combo.addItem("Light Gray", "light_gray")
            self.bg_combo.addItem("Gray", "gray")
            bg_layout.addWidget(self.bg_combo)
            section.add_layout(bg_layout)
            
            # Mean line width
            lw_layout = QHBoxLayout()
            lw_layout.addWidget(QLabel("Mean Line Width:"))
            self.linewidth_spin = QDoubleSpinBox()
            self.linewidth_spin.setRange(0.5, 5.0)
            self.linewidth_spin.setValue(2.0)
            self.linewidth_spin.setSingleStep(0.5)
            lw_layout.addWidget(self.linewidth_spin)
            section.add_layout(lw_layout)
            
            # Window alpha
            alpha_layout = QHBoxLayout()
            alpha_layout.addWidget(QLabel("Window Opacity:"))
            self.alpha_spin = QDoubleSpinBox()
            self.alpha_spin.setRange(0.1, 1.0)
            self.alpha_spin.setValue(0.5)
            self.alpha_spin.setSingleStep(0.1)
            alpha_layout.addWidget(self.alpha_spin)
            section.add_layout(alpha_layout)
            
            return section
        
        def on_preset_changed(self, index: int):
            """Handle preset selection change."""
            preset = self.preset_combo.itemData(index)
            
            descriptions = {
                "analysis": "Interactive analysis with all windows visible",
                "publication": "Clean, professional style with shaded uncertainty",
                "minimal": "Simple mean curve only, ideal for presentations",
                "custom": "Custom settings - adjust options below"
            }
            
            self.preset_desc.setText(descriptions.get(preset, ""))
            
            if preset != "custom":
                self.apply_preset(preset)
        
        def on_ymode_changed(self, index: int):
            """Handle Y-axis mode change."""
            mode = self.ymode_combo.itemData(index)

            # Show/hide relevant controls
            # For now, just update property
            self.properties.y_mode = mode

        def on_xmode_changed(self, index: int):
            """Handle X-axis mode change."""
            mode = self.xmode_combo.itemData(index)

            # Update property
            self.properties.x_mode = mode

            # Enable/disable manual controls
            is_manual = (mode == "manual")
            self.xmin_spin.setEnabled(is_manual)
            self.xmax_spin.setEnabled(is_manual)

        def apply_preset(self, preset: str):
            """Apply a preset and update UI."""
            if preset == "publication":
                self.properties.get_publication_preset()
            elif preset == "analysis":
                self.properties.get_analysis_preset()
            elif preset == "minimal":
                self.properties.get_minimal_preset()
            
            # Update UI to match properties
            self._update_ui_from_properties()
        
        def _update_ui_from_properties(self):
            """Update UI widgets to match current properties."""
            # Y-axis
            y_mode_index = self.ymode_combo.findData(self.properties.y_mode)
            if y_mode_index >= 0:
                self.ymode_combo.setCurrentIndex(y_mode_index)

            self.std_spin.setValue(self.properties.y_std_multiplier)
            self.percentile_spin.setValue(self.properties.y_percentile)
            self.ymin_spin.setValue(self.properties.y_min)
            self.ymax_spin.setValue(self.properties.y_max)

            # X-axis
            x_mode_index = self.xmode_combo.findData(self.properties.x_mode)
            if x_mode_index >= 0:
                self.xmode_combo.setCurrentIndex(x_mode_index)

            x_scale_index = self.xscale_combo.findData(self.properties.x_scale)
            if x_scale_index >= 0:
                self.xscale_combo.setCurrentIndex(x_scale_index)

            self.xmin_spin.setValue(self.properties.x_min)
            self.xmax_spin.setValue(self.properties.x_max)

            # Enable/disable manual controls based on mode
            is_manual = (self.properties.x_mode == "manual")
            self.xmin_spin.setEnabled(is_manual)
            self.xmax_spin.setEnabled(is_manual)

            # Visualization mode
            if self.properties.visualization_mode == "statistical":
                self.viz_rb_statistical.setChecked(True)
            elif self.properties.visualization_mode == "windows":
                self.viz_rb_windows.setChecked(True)
            elif self.properties.visualization_mode == "both":
                self.viz_rb_both.setChecked(True)

            # Curves
            self.show_mean_cb.setChecked(self.properties.show_mean)
            self.show_windows_cb.setChecked(self.properties.show_windows)
            self.show_std_cb.setChecked(self.properties.show_std_bands)
            self.show_percentile_cb.setChecked(self.properties.show_percentile_shading)
            self.show_median_cb.setChecked(self.properties.show_median)
            
            # Annotations
            self.show_badge_cb.setChecked(self.properties.show_acceptance_badge)
            self.show_peaks_cb.setChecked(self.properties.show_peak_labels)
            
            style_index = self.peak_style_combo.findData(self.properties.peak_label_style)
            if style_index >= 0:
                self.peak_style_combo.setCurrentIndex(style_index)
            
            self.show_legend_cb.setChecked(self.properties.show_legend)
            self.show_grid_cb.setChecked(self.properties.show_grid)
            
            # Appearance
            bg_index = self.bg_combo.findData(self.properties.background_color)
            if bg_index >= 0:
                self.bg_combo.setCurrentIndex(bg_index)
            
            self.linewidth_spin.setValue(self.properties.mean_linewidth)
            self.alpha_spin.setValue(self.properties.window_alpha)
        
        def _read_ui_to_properties(self):
            """Read UI values into properties object."""
            # Preset
            preset_index = self.preset_combo.currentIndex()
            self.properties.style_preset = self.preset_combo.itemData(preset_index)
            
            # Y-axis
            ymode_index = self.ymode_combo.currentIndex()
            self.properties.y_mode = self.ymode_combo.itemData(ymode_index)
            self.properties.y_std_multiplier = self.std_spin.value()
            self.properties.y_percentile = self.percentile_spin.value()
            self.properties.y_min = self.ymin_spin.value()
            self.properties.y_max = self.ymax_spin.value()

            # X-axis
            xmode_index = self.xmode_combo.currentIndex()
            self.properties.x_mode = self.xmode_combo.itemData(xmode_index)

            xscale_index = self.xscale_combo.currentIndex()
            self.properties.x_scale = self.xscale_combo.itemData(xscale_index)

            self.properties.x_min = self.xmin_spin.value()
            self.properties.x_max = self.xmax_spin.value()

            # Visualization mode
            if self.viz_rb_statistical.isChecked():
                self.properties.visualization_mode = "statistical"
            elif self.viz_rb_windows.isChecked():
                self.properties.visualization_mode = "windows"
            elif self.viz_rb_both.isChecked():
                self.properties.visualization_mode = "both"

            # Curves
            self.properties.show_mean = self.show_mean_cb.isChecked()
            self.properties.show_windows = self.show_windows_cb.isChecked()
            self.properties.show_std_bands = self.show_std_cb.isChecked()
            self.properties.show_percentile_shading = self.show_percentile_cb.isChecked()
            self.properties.show_median = self.show_median_cb.isChecked()
            
            # Annotations
            self.properties.show_acceptance_badge = self.show_badge_cb.isChecked()
            self.properties.show_peak_labels = self.show_peaks_cb.isChecked()
            
            style_index = self.peak_style_combo.currentIndex()
            self.properties.peak_label_style = self.peak_style_combo.itemData(style_index)
            
            self.properties.show_legend = self.show_legend_cb.isChecked()
            self.properties.show_grid = self.show_grid_cb.isChecked()
            
            # Appearance
            bg_index = self.bg_combo.currentIndex()
            self.properties.background_color = self.bg_combo.itemData(bg_index)
            
            self.properties.mean_linewidth = self.linewidth_spin.value()
            self.properties.window_alpha = self.alpha_spin.value()
        
        def apply_properties(self):
            """Apply current properties and emit signal."""
            # Read UI into properties
            self._read_ui_to_properties()
            
            # If user changed anything, mark as custom
            if self.properties.style_preset != "custom":
                # Check if values differ from preset
                # For simplicity, just mark as custom when Apply is clicked
                pass
            
            # Emit signal
            self.properties_changed.emit(self.properties)
            
            print(f"[PropertiesDock] Properties applied: {self.properties.style_preset} mode")
        
        def reset_to_defaults(self):
            """Reset to analysis preset (default)."""
            self.preset_combo.setCurrentIndex(0)  # Analysis
            self.apply_preset("analysis")
            self.apply_properties()
        
        def get_properties(self) -> PlotProperties:
            """Get current properties."""
            self._read_ui_to_properties()
            return self.properties


if not HAS_PYQT5:
    class PropertiesDock:
        """Dummy class when PyQt5 not available."""
        def __init__(self):
            raise ImportError("PyQt5 is required for GUI functionality")
