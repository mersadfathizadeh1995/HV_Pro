"""
Axis Section
============

X and Y axis control for properties dock.
"""

from typing import Dict, Any

try:
    from PyQt5.QtWidgets import (
        QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QDoubleSpinBox
    )
    from PyQt5.QtCore import pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False

if HAS_PYQT5:
    from hvsr_pro.gui.components import CollapsibleSection


if HAS_PYQT5:
    class AxisSection(CollapsibleSection):
        """
        Axis control section (Y-axis and X-axis combined).
        
        Signals:
            y_settings_changed: Emitted when Y-axis settings change (dict)
            x_settings_changed: Emitted when X-axis settings change (dict)
        """
        
        y_settings_changed = pyqtSignal(dict)
        x_settings_changed = pyqtSignal(dict)
        
        def __init__(self, parent=None, axis: str = "y"):
            """
            Initialize axis section.
            
            Args:
                parent: Parent widget
                axis: 'y' for Y-axis, 'x' for X-axis, 'both' for both
            """
            self._axis = axis
            title = {
                'y': "Y-Axis Limits",
                'x': "X-Axis (Frequency) Limits",
                'both': "Axis Limits"
            }.get(axis, "Axis Limits")
            
            super().__init__(title, parent)
            self._init_content()
        
        def _init_content(self):
            """Initialize section content."""
            if self._axis in ['y', 'both']:
                self._create_y_controls()
            
            if self._axis in ['x', 'both']:
                self._create_x_controls()
        
        def _create_y_controls(self):
            """Create Y-axis controls."""
            # Mode dropdown
            mode_layout = QHBoxLayout()
            mode_layout.addWidget(QLabel("Y Mode:"))
            
            self.ymode_combo = QComboBox()
            self.ymode_combo.addItem("Auto (Data-driven)", "auto")
            self.ymode_combo.addItem("Mean +/- Std", "mean_std")
            self.ymode_combo.addItem("Percentile-based", "percentile")
            self.ymode_combo.addItem("Manual", "manual")
            self.ymode_combo.currentIndexChanged.connect(self._on_y_changed)
            mode_layout.addWidget(self.ymode_combo)
            self.add_layout(mode_layout)
            
            # Std multiplier
            std_layout = QHBoxLayout()
            std_layout.addWidget(QLabel("Std Mult:"))
            self.std_spin = QDoubleSpinBox()
            self.std_spin.setRange(0.5, 5.0)
            self.std_spin.setValue(2.0)
            self.std_spin.setSingleStep(0.5)
            std_layout.addWidget(self.std_spin)
            self.add_layout(std_layout)
            
            # Percentile
            perc_layout = QHBoxLayout()
            perc_layout.addWidget(QLabel("Percentile:"))
            self.percentile_spin = QDoubleSpinBox()
            self.percentile_spin.setRange(80.0, 99.9)
            self.percentile_spin.setValue(95.0)
            self.percentile_spin.setSuffix("%")
            perc_layout.addWidget(self.percentile_spin)
            self.add_layout(perc_layout)
            
            # Manual limits
            manual_layout = QHBoxLayout()
            manual_layout.addWidget(QLabel("Y Min:"))
            self.ymin_spin = QDoubleSpinBox()
            self.ymin_spin.setRange(0.0, 100.0)
            self.ymin_spin.setValue(0.0)
            manual_layout.addWidget(self.ymin_spin)
            
            manual_layout.addWidget(QLabel("Max:"))
            self.ymax_spin = QDoubleSpinBox()
            self.ymax_spin.setRange(0.1, 100.0)
            self.ymax_spin.setValue(10.0)
            manual_layout.addWidget(self.ymax_spin)
            self.add_layout(manual_layout)
        
        def _create_x_controls(self):
            """Create X-axis controls."""
            # Mode dropdown
            mode_layout = QHBoxLayout()
            mode_layout.addWidget(QLabel("X Mode:"))
            
            self.xmode_combo = QComboBox()
            self.xmode_combo.addItem("Auto (Data-driven)", "auto")
            self.xmode_combo.addItem("Manual", "manual")
            self.xmode_combo.currentIndexChanged.connect(self._on_x_changed)
            mode_layout.addWidget(self.xmode_combo)
            self.add_layout(mode_layout)
            
            # Scale
            scale_layout = QHBoxLayout()
            scale_layout.addWidget(QLabel("Scale:"))
            self.xscale_combo = QComboBox()
            self.xscale_combo.addItem("Logarithmic", "log")
            self.xscale_combo.addItem("Linear", "linear")
            scale_layout.addWidget(self.xscale_combo)
            self.add_layout(scale_layout)
            
            # Manual limits
            manual_layout = QHBoxLayout()
            manual_layout.addWidget(QLabel("X Min:"))
            self.xmin_spin = QDoubleSpinBox()
            self.xmin_spin.setRange(0.01, 1000.0)
            self.xmin_spin.setValue(0.1)
            self.xmin_spin.setDecimals(2)
            manual_layout.addWidget(self.xmin_spin)
            
            manual_layout.addWidget(QLabel("Max:"))
            self.xmax_spin = QDoubleSpinBox()
            self.xmax_spin.setRange(0.1, 1000.0)
            self.xmax_spin.setValue(50.0)
            manual_layout.addWidget(self.xmax_spin)
            self.add_layout(manual_layout)
        
        def _on_y_changed(self, index: int = None):
            """Emit Y settings changed signal."""
            self.y_settings_changed.emit(self.get_y_settings())
        
        def _on_x_changed(self, index: int = None):
            """Emit X settings changed signal."""
            self.x_settings_changed.emit(self.get_x_settings())
        
        def get_y_settings(self) -> Dict[str, Any]:
            """Get Y-axis settings."""
            if self._axis not in ['y', 'both']:
                return {}
            
            return {
                'y_mode': self.ymode_combo.currentData(),
                'y_std_multiplier': self.std_spin.value(),
                'y_percentile': self.percentile_spin.value(),
                'y_min': self.ymin_spin.value(),
                'y_max': self.ymax_spin.value(),
            }
        
        def get_x_settings(self) -> Dict[str, Any]:
            """Get X-axis settings."""
            if self._axis not in ['x', 'both']:
                return {}
            
            return {
                'x_mode': self.xmode_combo.currentData(),
                'x_scale': self.xscale_combo.currentData(),
                'x_min': self.xmin_spin.value(),
                'x_max': self.xmax_spin.value(),
            }
        
        def set_y_settings(self, settings: Dict[str, Any]):
            """Set Y-axis settings."""
            if self._axis not in ['y', 'both']:
                return
            
            if 'y_mode' in settings:
                index = self.ymode_combo.findData(settings['y_mode'])
                if index >= 0:
                    self.ymode_combo.setCurrentIndex(index)
            
            if 'y_std_multiplier' in settings:
                self.std_spin.setValue(settings['y_std_multiplier'])
            if 'y_percentile' in settings:
                self.percentile_spin.setValue(settings['y_percentile'])
            if 'y_min' in settings:
                self.ymin_spin.setValue(settings['y_min'])
            if 'y_max' in settings:
                self.ymax_spin.setValue(settings['y_max'])
        
        def set_x_settings(self, settings: Dict[str, Any]):
            """Set X-axis settings."""
            if self._axis not in ['x', 'both']:
                return
            
            if 'x_mode' in settings:
                index = self.xmode_combo.findData(settings['x_mode'])
                if index >= 0:
                    self.xmode_combo.setCurrentIndex(index)
            
            if 'x_scale' in settings:
                index = self.xscale_combo.findData(settings['x_scale'])
                if index >= 0:
                    self.xscale_combo.setCurrentIndex(index)
            
            if 'x_min' in settings:
                self.xmin_spin.setValue(settings['x_min'])
            if 'x_max' in settings:
                self.xmax_spin.setValue(settings['x_max'])

else:
    class AxisSection:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass
