"""
Preset Section
==============

Style preset selection for properties dock.
"""

from typing import Dict, Callable

try:
    from PyQt5.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QComboBox
    from PyQt5.QtCore import pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False

if HAS_PYQT5:
    from hvsr_pro.gui.components import CollapsibleSection


if HAS_PYQT5:
    class PresetSection(CollapsibleSection):
        """
        Style preset selection section.
        
        Signals:
            preset_changed: Emitted when preset selection changes (str preset_name)
        """
        
        preset_changed = pyqtSignal(str)
        
        PRESETS = {
            "analysis": "Interactive analysis with all windows visible",
            "publication": "Clean, professional style with shaded uncertainty",
            "minimal": "Simple mean curve only, ideal for presentations",
            "custom": "Custom settings - adjust options below",
        }
        
        def __init__(self, parent=None):
            super().__init__("Plot Style Presets", parent)
            self._init_content()
        
        def _init_content(self):
            """Initialize section content."""
            # Preset dropdown
            preset_layout = QHBoxLayout()
            preset_layout.addWidget(QLabel("Style:"))
            
            self.preset_combo = QComboBox()
            self.preset_combo.addItem("Analysis (Current)", "analysis")
            self.preset_combo.addItem("Publication Quality", "publication")
            self.preset_combo.addItem("Minimal", "minimal")
            self.preset_combo.addItem("Custom", "custom")
            self.preset_combo.currentIndexChanged.connect(self._on_preset_changed)
            preset_layout.addWidget(self.preset_combo)
            
            self.add_layout(preset_layout)
            
            # Description label
            self.desc_label = QLabel(self.PRESETS["analysis"])
            self.desc_label.setWordWrap(True)
            self.desc_label.setStyleSheet("QLabel { color: #666; font-size: 9px; }")
            self.add_widget(self.desc_label)
        
        def _on_preset_changed(self, index: int):
            """Handle preset change."""
            preset = self.preset_combo.itemData(index)
            self.desc_label.setText(self.PRESETS.get(preset, ""))
            self.preset_changed.emit(preset)
        
        def get_preset(self) -> str:
            """Get current preset name."""
            return self.preset_combo.currentData()
        
        def set_preset(self, preset: str):
            """Set preset by name."""
            index = self.preset_combo.findData(preset)
            if index >= 0:
                self.preset_combo.setCurrentIndex(index)

else:
    class PresetSection:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass
