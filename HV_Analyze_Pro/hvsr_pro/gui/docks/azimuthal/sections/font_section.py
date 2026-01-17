"""
Font Section
============

Font size controls for azimuthal plots.
"""

try:
    from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel, QSpinBox
    from PyQt5.QtCore import pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False

if HAS_PYQT5:
    from hvsr_pro.gui.components import CollapsibleSection


if HAS_PYQT5:
    class FontSection(CollapsibleSection):
        """
        Font size controls section.
        
        Signals:
            fonts_changed: Emitted when any font size changes
        """
        
        fonts_changed = pyqtSignal()
        
        def __init__(self, parent=None):
            super().__init__("Fonts", parent)
            self.set_collapsed(True)  # Start collapsed
            self._init_content()
        
        def _init_content(self):
            """Initialize section content."""
            # Title font size
            title_container = QWidget()
            title_layout = QHBoxLayout(title_container)
            title_layout.setContentsMargins(0, 0, 0, 0)
            title_layout.addWidget(QLabel("Title:"))
            
            self.title_size_spin = QSpinBox()
            self.title_size_spin.setRange(10, 20)
            self.title_size_spin.setValue(14)
            self.title_size_spin.valueChanged.connect(self._on_changed)
            title_layout.addWidget(self.title_size_spin)
            self.add_widget(title_container)
            
            # Axis label font size
            axis_container = QWidget()
            axis_layout = QHBoxLayout(axis_container)
            axis_layout.setContentsMargins(0, 0, 0, 0)
            axis_layout.addWidget(QLabel("Axis Labels:"))
            
            self.axis_size_spin = QSpinBox()
            self.axis_size_spin.setRange(8, 14)
            self.axis_size_spin.setValue(10)
            self.axis_size_spin.valueChanged.connect(self._on_changed)
            axis_layout.addWidget(self.axis_size_spin)
            self.add_widget(axis_container)
            
            # Tick label font size
            tick_container = QWidget()
            tick_layout = QHBoxLayout(tick_container)
            tick_layout.setContentsMargins(0, 0, 0, 0)
            tick_layout.addWidget(QLabel("Tick Labels:"))
            
            self.tick_size_spin = QSpinBox()
            self.tick_size_spin.setRange(6, 12)
            self.tick_size_spin.setValue(8)
            self.tick_size_spin.valueChanged.connect(self._on_changed)
            tick_layout.addWidget(self.tick_size_spin)
            self.add_widget(tick_container)
        
        def _on_changed(self):
            """Handle font size change."""
            self.fonts_changed.emit()
        
        def get_title_fontsize(self) -> int:
            """Get title font size."""
            return self.title_size_spin.value()
        
        def get_axis_fontsize(self) -> int:
            """Get axis label font size."""
            return self.axis_size_spin.value()
        
        def get_tick_fontsize(self) -> int:
            """Get tick label font size."""
            return self.tick_size_spin.value()
        
        def set_title_fontsize(self, size: int):
            """Set title font size."""
            self.title_size_spin.setValue(size)
        
        def set_axis_fontsize(self, size: int):
            """Set axis label font size."""
            self.axis_size_spin.setValue(size)
        
        def set_tick_fontsize(self, size: int):
            """Set tick label font size."""
            self.tick_size_spin.setValue(size)


else:
    class FontSection:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass
