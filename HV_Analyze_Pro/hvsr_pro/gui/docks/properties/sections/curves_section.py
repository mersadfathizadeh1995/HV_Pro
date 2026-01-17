"""
Curves Section
==============

Curve visibility and visualization mode controls.
"""

from typing import Dict, Any

try:
    from PyQt5.QtWidgets import (
        QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QRadioButton
    )
    from PyQt5.QtCore import pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False

if HAS_PYQT5:
    from hvsr_pro.gui.components import CollapsibleSection


if HAS_PYQT5:
    class CurvesSection(CollapsibleSection):
        """
        Curve visibility and visualization mode section.
        
        Signals:
            visibility_changed: Emitted when curve visibility changes (dict)
            visualization_mode_changed: Emitted when viz mode changes (str)
        """
        
        visibility_changed = pyqtSignal(dict)
        visualization_mode_changed = pyqtSignal(str)
        
        def __init__(self, parent=None, include_viz_mode: bool = True):
            """
            Initialize curves section.
            
            Args:
                parent: Parent widget
                include_viz_mode: Include visualization mode radio buttons
            """
            self._include_viz_mode = include_viz_mode
            super().__init__("Curve Display", parent)
            self._init_content()
        
        def _init_content(self):
            """Initialize section content."""
            # Visualization mode radio buttons
            if self._include_viz_mode:
                mode_label = QLabel("Visualization Mode:")
                mode_label.setStyleSheet("font-weight: bold;")
                self.add_widget(mode_label)
                
                self.viz_rb_statistical = QRadioButton("Statistical View")
                self.viz_rb_statistical.setToolTip("Mean + uncertainty band")
                self.viz_rb_statistical.toggled.connect(self._on_viz_mode_changed)
                self.add_widget(self.viz_rb_statistical)
                
                self.viz_rb_windows = QRadioButton("Individual Windows")
                self.viz_rb_windows.setToolTip("All window curves + mean")
                self.viz_rb_windows.toggled.connect(self._on_viz_mode_changed)
                self.add_widget(self.viz_rb_windows)
                
                self.viz_rb_both = QRadioButton("Both (Combined)")
                self.viz_rb_both.setToolTip("All curves + statistics")
                self.viz_rb_both.toggled.connect(self._on_viz_mode_changed)
                self.add_widget(self.viz_rb_both)
                
                self.viz_rb_windows.setChecked(True)
            
            # Curve visibility checkboxes
            curves_label = QLabel("Show Curves:")
            curves_label.setStyleSheet("font-weight: bold; margin-top: 5px;")
            self.add_widget(curves_label)
            
            self.show_mean_cb = QCheckBox("Mean Curve")
            self.show_mean_cb.setChecked(True)
            self.show_mean_cb.stateChanged.connect(self._on_visibility_changed)
            self.add_widget(self.show_mean_cb)
            
            self.show_windows_cb = QCheckBox("Individual Windows")
            self.show_windows_cb.setChecked(True)
            self.show_windows_cb.stateChanged.connect(self._on_visibility_changed)
            self.add_widget(self.show_windows_cb)
            
            self.show_std_cb = QCheckBox("+/- 1 Std Bands")
            self.show_std_cb.setChecked(True)
            self.show_std_cb.stateChanged.connect(self._on_visibility_changed)
            self.add_widget(self.show_std_cb)
            
            self.show_percentile_cb = QCheckBox("Percentile Shading (16th-84th)")
            self.show_percentile_cb.setChecked(False)
            self.show_percentile_cb.stateChanged.connect(self._on_visibility_changed)
            self.add_widget(self.show_percentile_cb)
            
            self.show_median_cb = QCheckBox("Median Curve")
            self.show_median_cb.setChecked(False)
            self.show_median_cb.stateChanged.connect(self._on_visibility_changed)
            self.add_widget(self.show_median_cb)
        
        def _on_viz_mode_changed(self):
            """Handle visualization mode change."""
            if not self.sender().isChecked():
                return
            
            mode = 'windows'
            if hasattr(self, 'viz_rb_statistical') and self.viz_rb_statistical.isChecked():
                mode = 'statistical'
            elif hasattr(self, 'viz_rb_windows') and self.viz_rb_windows.isChecked():
                mode = 'windows'
            elif hasattr(self, 'viz_rb_both') and self.viz_rb_both.isChecked():
                mode = 'both'
            
            self.visualization_mode_changed.emit(mode)
        
        def _on_visibility_changed(self, state: int = None):
            """Handle curve visibility change."""
            self.visibility_changed.emit(self.get_visibility())
        
        def get_visibility(self) -> Dict[str, bool]:
            """Get curve visibility settings."""
            return {
                'show_mean': self.show_mean_cb.isChecked(),
                'show_windows': self.show_windows_cb.isChecked(),
                'show_std_bands': self.show_std_cb.isChecked(),
                'show_percentile_shading': self.show_percentile_cb.isChecked(),
                'show_median': self.show_median_cb.isChecked(),
            }
        
        def get_visualization_mode(self) -> str:
            """Get current visualization mode."""
            if not self._include_viz_mode:
                return 'windows'
            
            if self.viz_rb_statistical.isChecked():
                return 'statistical'
            elif self.viz_rb_both.isChecked():
                return 'both'
            return 'windows'
        
        def set_visibility(self, settings: Dict[str, bool]):
            """Set curve visibility settings."""
            if 'show_mean' in settings:
                self.show_mean_cb.setChecked(settings['show_mean'])
            if 'show_windows' in settings:
                self.show_windows_cb.setChecked(settings['show_windows'])
            if 'show_std_bands' in settings:
                self.show_std_cb.setChecked(settings['show_std_bands'])
            if 'show_percentile_shading' in settings:
                self.show_percentile_cb.setChecked(settings['show_percentile_shading'])
            if 'show_median' in settings:
                self.show_median_cb.setChecked(settings['show_median'])
        
        def set_visualization_mode(self, mode: str):
            """Set visualization mode."""
            if not self._include_viz_mode:
                return
            
            if mode == 'statistical':
                self.viz_rb_statistical.setChecked(True)
            elif mode == 'both':
                self.viz_rb_both.setChecked(True)
            else:
                self.viz_rb_windows.setChecked(True)

else:
    class CurvesSection:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass
