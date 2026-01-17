"""
Figure Section
==============

Figure type and display options for azimuthal plots.
"""

try:
    from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QComboBox, QCheckBox
    from PyQt5.QtCore import pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False

if HAS_PYQT5:
    from hvsr_pro.gui.components import CollapsibleSection


if HAS_PYQT5:
    class FigureSection(CollapsibleSection):
        """
        Figure type and display options section.
        
        Signals:
            figure_options_changed: Emitted when any option changes
        """
        
        figure_options_changed = pyqtSignal()
        
        # Available figure types
        FIGURE_TYPES = [
            ("Summary (3D + 2D + Curves)", "summary"),
            ("3D Surface Only", "3d"),
            ("2D Contour Only", "2d"),
            ("Polar Plot", "polar"),
            ("Individual Curves", "curves"),
        ]
        
        def __init__(self, parent=None):
            super().__init__("Figure Type", parent)
            self._init_content()
        
        def _init_content(self):
            """Initialize section content."""
            # Figure type selector
            type_container = QWidget()
            type_layout = QHBoxLayout(type_container)
            type_layout.setContentsMargins(0, 0, 0, 0)
            type_layout.addWidget(QLabel("View:"))
            
            self.figure_type_combo = QComboBox()
            for label, value in self.FIGURE_TYPES:
                self.figure_type_combo.addItem(label, value)
            self.figure_type_combo.currentIndexChanged.connect(self._on_changed)
            type_layout.addWidget(self.figure_type_combo)
            self.add_widget(type_container)
            
            # Show panel labels checkbox
            self.show_labels_cb = QCheckBox("Show panel labels (a, b, c)")
            self.show_labels_cb.setChecked(True)
            self.show_labels_cb.stateChanged.connect(self._on_changed)
            self.add_widget(self.show_labels_cb)
            
            # Show peak markers checkbox
            self.show_peaks_cb = QCheckBox("Show peak markers")
            self.show_peaks_cb.setChecked(True)
            self.show_peaks_cb.stateChanged.connect(self._on_changed)
            self.add_widget(self.show_peaks_cb)
            
            # Show individual curves checkbox
            self.show_individual_cb = QCheckBox("Show individual curves")
            self.show_individual_cb.setChecked(True)
            self.show_individual_cb.stateChanged.connect(self._on_changed)
            self.add_widget(self.show_individual_cb)
        
        def _on_changed(self):
            """Handle option change."""
            self.figure_options_changed.emit()
        
        def get_figure_type(self) -> str:
            """Get current figure type."""
            return self.figure_type_combo.currentData()
        
        def get_show_panel_labels(self) -> bool:
            """Get show panel labels setting."""
            return self.show_labels_cb.isChecked()
        
        def get_show_peaks(self) -> bool:
            """Get show peaks setting."""
            return self.show_peaks_cb.isChecked()
        
        def get_show_individual_curves(self) -> bool:
            """Get show individual curves setting."""
            return self.show_individual_cb.isChecked()
        
        def set_figure_type(self, fig_type: str):
            """Set figure type."""
            index = self.figure_type_combo.findData(fig_type)
            if index >= 0:
                self.figure_type_combo.setCurrentIndex(index)


else:
    class FigureSection:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass
