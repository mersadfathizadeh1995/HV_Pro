"""
Cox FDWRA Settings Panel
========================

.. deprecated:: 2.0
    This module is deprecated. Use :class:`unified_qc_panel.UnifiedQCPanel` instead.
    FDWRA settings are now integrated into the unified panel as
    "Peak Frequency Consistency (FDWRA)" in Phase 2.

Panel containing Frequency-Domain Window Rejection Algorithm settings.
"""

from dataclasses import dataclass
from typing import Optional

try:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QGridLayout,
        QLabel, QSpinBox, QDoubleSpinBox, QCheckBox, QComboBox
    )
    from PyQt5.QtCore import pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


@dataclass
class CoxFDWRASettings:
    """Data class for Cox FDWRA settings."""
    enabled: bool = False
    n_value: float = 2.0
    max_iterations: int = 20
    min_iterations: int = 1
    distribution: str = 'lognormal'


if HAS_PYQT5:
    class CoxSettingsPanel(QGroupBox):
        """
        Panel for configuring Cox FDWRA (Frequency-Domain Window Rejection Algorithm).
        
        Features:
        - Enable/disable Cox FDWRA
        - N-value (standard deviation multiplier)
        - Maximum iterations
        - Minimum iterations
        - Distribution type selection
        
        Signals:
            settings_changed: Emitted when any setting changes
        """
        
        settings_changed = pyqtSignal(object)  # CoxFDWRASettings
        
        def __init__(self, parent=None):
            super().__init__("Cox FDWRA (Frequency-Domain)", parent)
            self._init_ui()
            self._connect_signals()
        
        def _init_ui(self):
            """Initialize the user interface."""
            layout = QVBoxLayout(self)
            
            # Enable checkbox
            self.enable_check = QCheckBox("Enable Cox FDWRA")
            self.enable_check.setChecked(False)
            self.enable_check.setToolTip(
                "Apply Cox et al. (2020) Frequency-Domain Window Rejection\n"
                "after HVSR computation to ensure peak frequency consistency.\n"
                "Industry-standard for publication-quality HVSR analysis."
            )
            layout.addWidget(self.enable_check)
            
            # Parameters grid
            params_layout = QGridLayout()
            params_layout.setColumnStretch(1, 1)
            
            # N-value
            params_layout.addWidget(QLabel("n-value:"), 0, 0)
            self.n_spin = QDoubleSpinBox()
            self.n_spin.setRange(0.5, 10.0)
            self.n_spin.setValue(2.0)
            self.n_spin.setDecimals(1)
            self.n_spin.setSingleStep(0.5)
            self.n_spin.setEnabled(False)
            self.n_spin.setToolTip(
                "Standard deviation multiplier (lower = stricter rejection)\n"
                "Typical values: 1.5-3.0"
            )
            params_layout.addWidget(self.n_spin, 0, 1)
            
            # Max iterations
            params_layout.addWidget(QLabel("Max Iter:"), 1, 0)
            self.max_iterations_spin = QSpinBox()
            self.max_iterations_spin.setRange(1, 50)
            self.max_iterations_spin.setValue(20)
            self.max_iterations_spin.setEnabled(False)
            self.max_iterations_spin.setToolTip("Maximum iterations for convergence")
            params_layout.addWidget(self.max_iterations_spin, 1, 1)
            
            # Min iterations
            params_layout.addWidget(QLabel("Min Iter:"), 2, 0)
            self.min_iterations_spin = QSpinBox()
            self.min_iterations_spin.setRange(1, 20)
            self.min_iterations_spin.setValue(1)
            self.min_iterations_spin.setEnabled(False)
            self.min_iterations_spin.setToolTip(
                "Minimum iterations before checking convergence.\n"
                "Set higher to force more rejection passes even if convergence is reached early."
            )
            params_layout.addWidget(self.min_iterations_spin, 2, 1)
            
            # Distribution
            params_layout.addWidget(QLabel("Distribution:"), 3, 0)
            self.dist_combo = QComboBox()
            self.dist_combo.addItems(["lognormal", "normal"])
            self.dist_combo.setEnabled(False)
            self.dist_combo.setToolTip("Statistical distribution for peak modeling")
            params_layout.addWidget(self.dist_combo, 3, 1)
            
            layout.addLayout(params_layout)
        
        def _connect_signals(self):
            """Connect internal signals."""
            # Enable toggle controls parameter widgets
            self.enable_check.toggled.connect(self._on_enable_toggled)
            
            # All value changes emit settings_changed
            self.enable_check.toggled.connect(self._emit_settings_changed)
            self.n_spin.valueChanged.connect(self._emit_settings_changed)
            self.max_iterations_spin.valueChanged.connect(self._emit_settings_changed)
            self.min_iterations_spin.valueChanged.connect(self._emit_settings_changed)
            self.dist_combo.currentIndexChanged.connect(self._emit_settings_changed)
        
        def _on_enable_toggled(self, enabled: bool):
            """Handle enable checkbox toggle."""
            self.n_spin.setEnabled(enabled)
            self.max_iterations_spin.setEnabled(enabled)
            self.min_iterations_spin.setEnabled(enabled)
            self.dist_combo.setEnabled(enabled)
        
        def _emit_settings_changed(self):
            """Emit settings_changed signal with current settings."""
            self.settings_changed.emit(self.get_settings())
        
        def get_settings(self) -> CoxFDWRASettings:
            """
            Get current Cox FDWRA settings.
            
            Returns:
                CoxFDWRASettings object with current values
            """
            return CoxFDWRASettings(
                enabled=self.enable_check.isChecked(),
                n_value=self.n_spin.value(),
                max_iterations=self.max_iterations_spin.value(),
                min_iterations=self.min_iterations_spin.value(),
                distribution=self.dist_combo.currentText()
            )
        
        def set_settings(self, settings: CoxFDWRASettings):
            """
            Set Cox FDWRA settings from a CoxFDWRASettings object.
            
            Args:
                settings: CoxFDWRASettings object with values to apply
            """
            self.blockSignals(True)
            
            self.enable_check.setChecked(settings.enabled)
            self.n_spin.setValue(settings.n_value)
            self.max_iterations_spin.setValue(settings.max_iterations)
            self.min_iterations_spin.setValue(settings.min_iterations)
            self.dist_combo.setCurrentText(settings.distribution)
            
            self.blockSignals(False)
            self._emit_settings_changed()
        
        def is_enabled(self) -> bool:
            """Check if Cox FDWRA is enabled."""
            return self.enable_check.isChecked()


else:
    class CoxSettingsPanel:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            raise ImportError("PyQt5 is required for GUI functionality")
