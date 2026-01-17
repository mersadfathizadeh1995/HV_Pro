"""
Annotations Section
===================

Annotations and statistics display controls.
"""

from typing import Dict, Any

try:
    from PyQt5.QtWidgets import (
        QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, QComboBox
    )
    from PyQt5.QtCore import pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False

if HAS_PYQT5:
    from hvsr_pro.gui.components import CollapsibleSection


if HAS_PYQT5:
    class AnnotationsSection(CollapsibleSection):
        """
        Annotations and statistics display section.
        
        Signals:
            settings_changed: Emitted when settings change (dict)
        """
        
        settings_changed = pyqtSignal(dict)
        
        def __init__(self, parent=None):
            super().__init__("Annotations & Statistics", parent)
            self._init_content()
        
        def _init_content(self):
            """Initialize section content."""
            self.show_badge_cb = QCheckBox("Show Acceptance Rate Badge")
            self.show_badge_cb.setChecked(True)
            self.show_badge_cb.stateChanged.connect(self._on_settings_changed)
            self.add_widget(self.show_badge_cb)
            
            self.show_peaks_cb = QCheckBox("Show Peak Labels")
            self.show_peaks_cb.setChecked(True)
            self.show_peaks_cb.stateChanged.connect(self._on_settings_changed)
            self.add_widget(self.show_peaks_cb)
            
            # Peak label style
            style_layout = QHBoxLayout()
            style_layout.addWidget(QLabel("  Label Style:"))
            self.peak_style_combo = QComboBox()
            self.peak_style_combo.addItem("Full (freq + amp)", "full")
            self.peak_style_combo.addItem("Frequency only", "freq_only")
            self.peak_style_combo.addItem("Amplitude only", "amp_only")
            self.peak_style_combo.addItem("Minimal (marker only)", "minimal")
            self.peak_style_combo.currentIndexChanged.connect(self._on_settings_changed)
            style_layout.addWidget(self.peak_style_combo)
            self.add_layout(style_layout)
            
            self.show_legend_cb = QCheckBox("Show Legend")
            self.show_legend_cb.setChecked(True)
            self.show_legend_cb.stateChanged.connect(self._on_settings_changed)
            self.add_widget(self.show_legend_cb)
            
            self.show_grid_cb = QCheckBox("Show Grid Lines")
            self.show_grid_cb.setChecked(False)
            self.show_grid_cb.stateChanged.connect(self._on_settings_changed)
            self.add_widget(self.show_grid_cb)
        
        def _on_settings_changed(self, state: int = None):
            """Handle settings change."""
            self.settings_changed.emit(self.get_settings())
        
        def get_settings(self) -> Dict[str, Any]:
            """Get annotation settings."""
            return {
                'show_acceptance_badge': self.show_badge_cb.isChecked(),
                'show_peak_labels': self.show_peaks_cb.isChecked(),
                'peak_label_style': self.peak_style_combo.currentData(),
                'show_legend': self.show_legend_cb.isChecked(),
                'show_grid': self.show_grid_cb.isChecked(),
            }
        
        def set_settings(self, settings: Dict[str, Any]):
            """Set annotation settings."""
            if 'show_acceptance_badge' in settings:
                self.show_badge_cb.setChecked(settings['show_acceptance_badge'])
            if 'show_peak_labels' in settings:
                self.show_peaks_cb.setChecked(settings['show_peak_labels'])
            if 'peak_label_style' in settings:
                index = self.peak_style_combo.findData(settings['peak_label_style'])
                if index >= 0:
                    self.peak_style_combo.setCurrentIndex(index)
            if 'show_legend' in settings:
                self.show_legend_cb.setChecked(settings['show_legend'])
            if 'show_grid' in settings:
                self.show_grid_cb.setChecked(settings['show_grid'])

else:
    class AnnotationsSection:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass
