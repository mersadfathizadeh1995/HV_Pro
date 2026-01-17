"""
Legend Section
==============

Legend position and size options for azimuthal plots.
"""

try:
    from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QComboBox, QSpinBox
    from PyQt5.QtCore import pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False

if HAS_PYQT5:
    from hvsr_pro.gui.components import CollapsibleSection


if HAS_PYQT5:
    class LegendSection(CollapsibleSection):
        """
        Legend options section.
        
        Signals:
            legend_changed: Emitted when legend options change
        """
        
        legend_changed = pyqtSignal()
        
        # Available legend positions
        LEGEND_POSITIONS = [
            ("Outside Right", "outside_right"),
            ("Outside Bottom", "outside_bottom"),
            ("Upper Right", "upper right"),
            ("Upper Left", "upper left"),
            ("Lower Right", "lower right"),
            ("Lower Left", "lower left"),
            ("None (Hide)", "none"),
        ]
        
        def __init__(self, parent=None):
            super().__init__("Legend", parent)
            self._init_content()
        
        def _init_content(self):
            """Initialize section content."""
            # Legend position
            pos_container = QWidget()
            pos_layout = QHBoxLayout(pos_container)
            pos_layout.setContentsMargins(0, 0, 0, 0)
            pos_layout.addWidget(QLabel("Position:"))
            
            self.legend_pos_combo = QComboBox()
            for label, value in self.LEGEND_POSITIONS:
                self.legend_pos_combo.addItem(label, value)
            self.legend_pos_combo.currentIndexChanged.connect(self._on_changed)
            pos_layout.addWidget(self.legend_pos_combo)
            self.add_widget(pos_container)
            
            # Legend font size
            size_container = QWidget()
            size_layout = QHBoxLayout(size_container)
            size_layout.setContentsMargins(0, 0, 0, 0)
            size_layout.addWidget(QLabel("Font Size:"))
            
            self.legend_size_spin = QSpinBox()
            self.legend_size_spin.setRange(6, 14)
            self.legend_size_spin.setValue(8)
            self.legend_size_spin.valueChanged.connect(self._on_changed)
            size_layout.addWidget(self.legend_size_spin)
            self.add_widget(size_container)
        
        def _on_changed(self):
            """Handle legend option change."""
            self.legend_changed.emit()
        
        def get_position(self) -> str:
            """Get legend position."""
            return self.legend_pos_combo.currentData()
        
        def get_fontsize(self) -> int:
            """Get legend font size."""
            return self.legend_size_spin.value()
        
        def set_position(self, position: str):
            """Set legend position."""
            index = self.legend_pos_combo.findData(position)
            if index >= 0:
                self.legend_pos_combo.setCurrentIndex(index)
        
        def set_fontsize(self, size: int):
            """Set legend font size."""
            self.legend_size_spin.setValue(size)


else:
    class LegendSection:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass
