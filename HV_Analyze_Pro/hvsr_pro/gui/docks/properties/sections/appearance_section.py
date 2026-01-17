"""
Appearance Section
==================

Colors, line widths, and visual style controls.
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
    from hvsr_pro.gui.components import CollapsibleSection, ColorPickerButton


if HAS_PYQT5:
    class AppearanceSection(CollapsibleSection):
        """
        Colors and style section.
        
        Signals:
            settings_changed: Emitted when settings change (dict)
        """
        
        settings_changed = pyqtSignal(dict)
        
        def __init__(self, parent=None):
            super().__init__("Colors & Style", parent)
            self._init_content()
        
        def _init_content(self):
            """Initialize section content."""
            # Background color
            bg_layout = QHBoxLayout()
            bg_layout.addWidget(QLabel("Background:"))
            self.bg_combo = QComboBox()
            self.bg_combo.addItem("White", "white")
            self.bg_combo.addItem("Light Gray", "light_gray")
            self.bg_combo.addItem("Gray", "gray")
            self.bg_combo.currentIndexChanged.connect(self._on_settings_changed)
            bg_layout.addWidget(self.bg_combo)
            self.add_layout(bg_layout)
            
            # Line colors section
            colors_label = QLabel("Line Colors (click to change):")
            colors_label.setStyleSheet("font-weight: bold; margin-top: 5px;")
            self.add_widget(colors_label)
            
            # Mean color
            mean_layout = QHBoxLayout()
            mean_layout.addWidget(QLabel("  Mean:"))
            self.mean_color_btn = ColorPickerButton("#1976D2")
            self.mean_color_btn.color_changed.connect(self._on_color_changed)
            mean_layout.addWidget(self.mean_color_btn)
            mean_layout.addStretch()
            self.add_layout(mean_layout)
            
            # Median color
            median_layout = QHBoxLayout()
            median_layout.addWidget(QLabel("  Median:"))
            self.median_color_btn = ColorPickerButton("#D32F2F")
            self.median_color_btn.color_changed.connect(self._on_color_changed)
            median_layout.addWidget(self.median_color_btn)
            median_layout.addStretch()
            self.add_layout(median_layout)
            
            # Std bands color
            std_layout = QHBoxLayout()
            std_layout.addWidget(QLabel("  Std Bands:"))
            self.std_color_btn = ColorPickerButton("#FF5722")
            self.std_color_btn.color_changed.connect(self._on_color_changed)
            std_layout.addWidget(self.std_color_btn)
            std_layout.addStretch()
            self.add_layout(std_layout)
            
            # Percentile color
            perc_layout = QHBoxLayout()
            perc_layout.addWidget(QLabel("  Percentile:"))
            self.percentile_color_btn = ColorPickerButton("#9C27B0")
            self.percentile_color_btn.color_changed.connect(self._on_color_changed)
            perc_layout.addWidget(self.percentile_color_btn)
            perc_layout.addStretch()
            self.add_layout(perc_layout)
            
            # Peak marker color
            peak_layout = QHBoxLayout()
            peak_layout.addWidget(QLabel("  Peak Marker:"))
            self.peak_color_btn = ColorPickerButton("#4CAF50")
            self.peak_color_btn.color_changed.connect(self._on_color_changed)
            peak_layout.addWidget(self.peak_color_btn)
            peak_layout.addStretch()
            self.add_layout(peak_layout)
            
            # Line widths section
            widths_label = QLabel("Line Widths:")
            widths_label.setStyleSheet("font-weight: bold; margin-top: 5px;")
            self.add_widget(widths_label)
            
            # Mean line width
            mean_lw_layout = QHBoxLayout()
            mean_lw_layout.addWidget(QLabel("  Mean:"))
            self.mean_lw_spin = QDoubleSpinBox()
            self.mean_lw_spin.setRange(0.5, 5.0)
            self.mean_lw_spin.setValue(2.0)
            self.mean_lw_spin.setSingleStep(0.5)
            self.mean_lw_spin.valueChanged.connect(self._on_settings_changed)
            mean_lw_layout.addWidget(self.mean_lw_spin)
            self.add_layout(mean_lw_layout)
            
            # Median line width
            median_lw_layout = QHBoxLayout()
            median_lw_layout.addWidget(QLabel("  Median:"))
            self.median_lw_spin = QDoubleSpinBox()
            self.median_lw_spin.setRange(0.5, 5.0)
            self.median_lw_spin.setValue(1.5)
            self.median_lw_spin.setSingleStep(0.5)
            self.median_lw_spin.valueChanged.connect(self._on_settings_changed)
            median_lw_layout.addWidget(self.median_lw_spin)
            self.add_layout(median_lw_layout)
            
            # Std line width
            std_lw_layout = QHBoxLayout()
            std_lw_layout.addWidget(QLabel("  Std Bands:"))
            self.std_lw_spin = QDoubleSpinBox()
            self.std_lw_spin.setRange(0.5, 5.0)
            self.std_lw_spin.setValue(1.5)
            self.std_lw_spin.setSingleStep(0.5)
            self.std_lw_spin.valueChanged.connect(self._on_settings_changed)
            std_lw_layout.addWidget(self.std_lw_spin)
            self.add_layout(std_lw_layout)
            
            # Opacity section
            opacity_label = QLabel("Opacity:")
            opacity_label.setStyleSheet("font-weight: bold; margin-top: 5px;")
            self.add_widget(opacity_label)
            
            alpha_layout = QHBoxLayout()
            alpha_layout.addWidget(QLabel("  Windows:"))
            self.alpha_spin = QDoubleSpinBox()
            self.alpha_spin.setRange(0.1, 1.0)
            self.alpha_spin.setValue(0.5)
            self.alpha_spin.setSingleStep(0.1)
            self.alpha_spin.valueChanged.connect(self._on_settings_changed)
            alpha_layout.addWidget(self.alpha_spin)
            self.add_layout(alpha_layout)
        
        def _on_color_changed(self, color: str):
            """Handle color change."""
            self.settings_changed.emit(self.get_settings())
        
        def _on_settings_changed(self, value=None):
            """Handle settings change."""
            self.settings_changed.emit(self.get_settings())
        
        def get_settings(self) -> Dict[str, Any]:
            """Get appearance settings."""
            return {
                'background_color': self.bg_combo.currentData(),
                'mean_color': self.mean_color_btn.get_color(),
                'median_color': self.median_color_btn.get_color(),
                'std_color': self.std_color_btn.get_color(),
                'percentile_color': self.percentile_color_btn.get_color(),
                'peak_marker_color': self.peak_color_btn.get_color(),
                'mean_linewidth': self.mean_lw_spin.value(),
                'median_linewidth': self.median_lw_spin.value(),
                'std_linewidth': self.std_lw_spin.value(),
                'window_alpha': self.alpha_spin.value(),
            }
        
        def set_settings(self, settings: Dict[str, Any]):
            """Set appearance settings."""
            if 'background_color' in settings:
                index = self.bg_combo.findData(settings['background_color'])
                if index >= 0:
                    self.bg_combo.setCurrentIndex(index)
            
            if 'mean_color' in settings:
                self.mean_color_btn.set_color(settings['mean_color'])
            if 'median_color' in settings:
                self.median_color_btn.set_color(settings['median_color'])
            if 'std_color' in settings:
                self.std_color_btn.set_color(settings['std_color'])
            if 'percentile_color' in settings:
                self.percentile_color_btn.set_color(settings['percentile_color'])
            if 'peak_marker_color' in settings:
                self.peak_color_btn.set_color(settings['peak_marker_color'])
            
            if 'mean_linewidth' in settings:
                self.mean_lw_spin.setValue(settings['mean_linewidth'])
            if 'median_linewidth' in settings:
                self.median_lw_spin.setValue(settings['median_linewidth'])
            if 'std_linewidth' in settings:
                self.std_lw_spin.setValue(settings['std_linewidth'])
            if 'window_alpha' in settings:
                self.alpha_spin.setValue(settings['window_alpha'])

else:
    class AppearanceSection:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass
