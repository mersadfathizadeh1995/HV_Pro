"""
Theme Section
=============

Colormap and theme settings for azimuthal plots.
"""

try:
    from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QComboBox
    from PyQt5.QtCore import pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False

if HAS_PYQT5:
    from hvsr_pro.gui.components import CollapsibleSection


if HAS_PYQT5:
    class ThemeSection(CollapsibleSection):
        """
        Theme and colormap selection section.
        
        Signals:
            theme_changed: Emitted when colormap selection changes
        """
        
        theme_changed = pyqtSignal()
        
        # Available colormaps for surface/contour plots
        SURFACE_COLORMAPS = [
            "plasma", "viridis", "inferno", "magma",
            "jet", "turbo", "coolwarm", "RdBu_r", "seismic"
        ]
        
        # Available colormaps for curve plots
        CURVE_COLORMAPS = [
            "viridis", "plasma", "rainbow", "tab20", "hsv"
        ]
        
        def __init__(self, parent=None):
            super().__init__("Theme & Colors", parent)
            self._init_content()
        
        def _init_content(self):
            """Initialize section content."""
            # Colormap selector for surfaces
            cmap_container = QWidget()
            cmap_layout = QHBoxLayout(cmap_container)
            cmap_layout.setContentsMargins(0, 0, 0, 0)
            cmap_layout.addWidget(QLabel("Colormap:"))
            
            self.cmap_combo = QComboBox()
            self.cmap_combo.addItems(self.SURFACE_COLORMAPS)
            self.cmap_combo.setToolTip("Color scheme for surface and contour plots")
            self.cmap_combo.currentIndexChanged.connect(self._on_changed)
            cmap_layout.addWidget(self.cmap_combo)
            self.add_widget(cmap_container)
            
            # Curve colormap selector
            curve_cmap_container = QWidget()
            curve_cmap_layout = QHBoxLayout(curve_cmap_container)
            curve_cmap_layout.setContentsMargins(0, 0, 0, 0)
            curve_cmap_layout.addWidget(QLabel("Curves:"))
            
            self.curve_cmap_combo = QComboBox()
            self.curve_cmap_combo.addItems(self.CURVE_COLORMAPS)
            self.curve_cmap_combo.setToolTip("Color scheme for individual HVSR curves")
            self.curve_cmap_combo.currentIndexChanged.connect(self._on_changed)
            curve_cmap_layout.addWidget(self.curve_cmap_combo)
            self.add_widget(curve_cmap_container)
        
        def _on_changed(self):
            """Handle colormap change."""
            self.theme_changed.emit()
        
        def get_cmap(self) -> str:
            """Get current surface colormap."""
            return self.cmap_combo.currentText()
        
        def get_curve_cmap(self) -> str:
            """Get current curve colormap."""
            return self.curve_cmap_combo.currentText()
        
        def set_cmap(self, cmap: str):
            """Set surface colormap."""
            index = self.cmap_combo.findText(cmap)
            if index >= 0:
                self.cmap_combo.setCurrentIndex(index)
        
        def set_curve_cmap(self, cmap: str):
            """Set curve colormap."""
            index = self.curve_cmap_combo.findText(cmap)
            if index >= 0:
                self.curve_cmap_combo.setCurrentIndex(index)


else:
    class ThemeSection:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass
