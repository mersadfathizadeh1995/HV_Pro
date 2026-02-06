"""
Unified Quality Control Panel
=============================

New unified QC panel with hierarchical checkboxes and per-algorithm settings.
Replaces both QCSettingsPanel and CoxSettingsPanel.

Features:
- Master "Enable Quality Control" checkbox
- SESAME Standard / Custom mode selection
- Phase 1 (Pre-HVSR) checkbox with algorithms
- Phase 2 (Post-HVSR) checkbox with algorithms
- Settings dialog for each algorithm
- Custom settings persistence
"""

from typing import Dict, Any, Optional
from pathlib import Path
import json

try:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
        QLabel, QCheckBox, QPushButton, QRadioButton, 
        QButtonGroup, QFrame, QGridLayout, QMessageBox
    )
    from PyQt5.QtCore import Qt, pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False

from hvsr_pro.processing.rejection.settings import QCSettings


# SESAME Standard defaults (matching hvsrpy)
SESAME_DEFAULTS = {
    'phase1_enabled': True,
    'phase2_enabled': True,
    'algorithms': {
        # Phase 1 (Pre-HVSR)
        'amplitude': {'enabled': True, 'params': {}},
        'sta_lta': {
            'enabled': True,
            'params': {
                'sta_length': 1.0,
                'lta_length': 30.0,
                'min_ratio': 0.2,
                'max_ratio': 2.5
            }
        },
        'spectral_spike': {'enabled': False, 'params': {'spike_threshold': 3.0}},
        'statistical_outlier': {'enabled': False, 'params': {'method': 'iqr', 'threshold': 2.0}},
        # Phase 2 (Post-HVSR)
        'fdwra': {
            'enabled': True,
            'params': {
                'n': 2.0,
                'max_iterations': 50,
                'min_iterations': 1,
                'distribution_fn': 'lognormal',
                'distribution_mc': 'lognormal'
            }
        },
        'hvsr_amplitude': {'enabled': False, 'params': {'min_amplitude': 1.0}},
        'flat_peak': {'enabled': False, 'params': {'flatness_threshold': 0.15}}
    }
}


def get_custom_settings_path() -> Path:
    """Get path to custom settings file."""
    return Path.home() / '.hvsr_pro' / 'qc_custom_settings.json'


def load_custom_settings() -> Dict[str, Any]:
    """Load custom settings from file, return SESAME defaults if not found."""
    path = get_custom_settings_path()
    if path.exists():
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return SESAME_DEFAULTS.copy()


def save_custom_settings(settings: Dict[str, Any]) -> bool:
    """Save custom settings to file. Returns True on success."""
    path = get_custom_settings_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(settings, f, indent=2)
        return True
    except IOError:
        return False


if HAS_PYQT5:
    class UnifiedQCPanel(QWidget):
        """
        Unified Quality Control Panel with hierarchical checkboxes.
        
        Replaces both QCSettingsPanel and CoxSettingsPanel.
        
        Checkbox Hierarchy:
        - Master: "Enable Quality Control" - disables all when unchecked
        - Phase 1: Enables/disables all Phase 1 (Pre-HVSR) algorithms
        - Phase 2: Enables/disables all Phase 2 (Post-HVSR) algorithms
        - Individual: Enable/disable each algorithm
        
        Signals:
            settings_changed: Emitted when any setting changes
        """
        
        settings_changed = pyqtSignal(object)  # Dict with all settings
        
        def __init__(self, parent=None):
            super().__init__(parent)
            self._block_signals = False
            self._mode = 'sesame'  # 'sesame' or 'custom'
            self._custom_settings = load_custom_settings()
            self._init_ui()
            self._connect_signals()
            self._apply_sesame_defaults()
        
        def _init_ui(self):
            """Initialize the user interface."""
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(5)
            
            # Main group
            main_group = QGroupBox("Quality Control")
            main_layout = QVBoxLayout(main_group)
            main_layout.setSpacing(8)
            
            # === MASTER ENABLE ===
            self.master_enable = QCheckBox("Enable Quality Control")
            self.master_enable.setChecked(True)
            self.master_enable.setToolTip(
                "Master switch to enable/disable all quality control.\n"
                "When unchecked, no window rejection is applied."
            )
            self.master_enable.setStyleSheet("font-weight: bold;")
            main_layout.addWidget(self.master_enable)
            
            # === MODE SELECTION ===
            mode_frame = QFrame()
            mode_layout = QHBoxLayout(mode_frame)
            mode_layout.setContentsMargins(0, 5, 0, 5)
            
            mode_layout.addWidget(QLabel("Mode:"))
            
            self.mode_group = QButtonGroup()
            self._sesame_radio = QRadioButton("SESAME Standard")
            self._custom_radio = QRadioButton("Custom")
            self._sesame_radio.setChecked(True)
            self.mode_group.addButton(self._sesame_radio, 0)
            self.mode_group.addButton(self._custom_radio, 1)
            
            self._sesame_radio.setToolTip(
                "SESAME Standard settings (matches hvsrpy defaults):\n"
                "- Phase 1: Amplitude + STA/LTA\n"
                "- Phase 2: Peak Frequency Consistency (FDWRA)"
            )
            self._custom_radio.setToolTip("Custom settings (modifiable and persistent)")
            
            mode_layout.addWidget(self._sesame_radio)
            mode_layout.addWidget(self._custom_radio)
            mode_layout.addStretch()
            
            self.save_custom_btn = QPushButton("Save Custom Settings")
            self.save_custom_btn.setToolTip("Save current custom settings for future sessions")
            self.save_custom_btn.setEnabled(False)  # Only enabled in custom mode
            mode_layout.addWidget(self.save_custom_btn)
            
            main_layout.addWidget(mode_frame)
            
            # === PHASE 1: PRE-HVSR ===
            self.phase1_group = self._create_phase1_section()
            main_layout.addWidget(self.phase1_group)
            
            # === PHASE 2: POST-HVSR ===
            self.phase2_group = self._create_phase2_section()
            main_layout.addWidget(self.phase2_group)
            
            layout.addWidget(main_group)
        
        def _create_phase1_section(self) -> QGroupBox:
            """Create Phase 1 (Pre-HVSR) algorithms section."""
            group = QGroupBox()
            layout = QVBoxLayout(group)
            layout.setSpacing(4)
            
            # Phase header with checkbox
            header_layout = QHBoxLayout()
            self.phase1_enable = QCheckBox("Phase 1: Pre-HVSR (Time-Domain)")
            self.phase1_enable.setChecked(True)
            self.phase1_enable.setToolTip(
                "Enable/disable all Phase 1 algorithms.\n"
                "These run BEFORE HVSR computation on raw waveforms."
            )
            self.phase1_enable.setStyleSheet("font-weight: bold;")
            header_layout.addWidget(self.phase1_enable)
            header_layout.addStretch()
            
            self.phase1_count_label = QLabel("[2 active]")
            self.phase1_count_label.setStyleSheet("color: #666;")
            header_layout.addWidget(self.phase1_count_label)
            
            layout.addLayout(header_layout)
            
            # Algorithm rows
            self.amplitude_row = self._create_algorithm_row(
                "Amplitude Check",
                "Rejects windows with clipping, dead channels, or extreme amplitudes.\n"
                "Always recommended.",
                'amplitude'
            )
            layout.addWidget(self.amplitude_row['widget'])
            
            self.stalta_row = self._create_algorithm_row(
                "STA/LTA Transient Detection",
                "Rejects windows with unusual energy bursts using Short-Term/Long-Term Average ratio.\n"
                "Good for detecting earthquakes or traffic.\n"
                "Default: sta=1s, lta=30s, min=0.2, max=2.5 (matches hvsrpy)",
                'sta_lta'
            )
            layout.addWidget(self.stalta_row['widget'])
            
            self.spectral_row = self._create_algorithm_row(
                "Spectral Spike Detection",
                "Rejects windows with narrow-band noise (e.g., machine vibration).\n"
                "Analyzes frequency content for anomalies.",
                'spectral_spike'
            )
            layout.addWidget(self.spectral_row['widget'])
            
            self.statistical_row = self._create_algorithm_row(
                "Statistical Outlier Detection",
                "Rejects windows that are statistical outliers using IQR or Z-score method.",
                'statistical_outlier'
            )
            layout.addWidget(self.statistical_row['widget'])
            
            return group
        
        def _create_phase2_section(self) -> QGroupBox:
            """Create Phase 2 (Post-HVSR) algorithms section."""
            group = QGroupBox()
            layout = QVBoxLayout(group)
            layout.setSpacing(4)
            
            # Phase header with checkbox
            header_layout = QHBoxLayout()
            self.phase2_enable = QCheckBox("Phase 2: Post-HVSR (Peak Quality)")
            self.phase2_enable.setChecked(True)
            self.phase2_enable.setToolTip(
                "Enable/disable all Phase 2 algorithms.\n"
                "These run AFTER HVSR computation on computed curves."
            )
            self.phase2_enable.setStyleSheet("font-weight: bold;")
            header_layout.addWidget(self.phase2_enable)
            header_layout.addStretch()
            
            self.phase2_count_label = QLabel("[1 active]")
            self.phase2_count_label.setStyleSheet("color: #666;")
            header_layout.addWidget(self.phase2_count_label)
            
            layout.addLayout(header_layout)
            
            # Algorithm rows
            self.fdwra_row = self._create_algorithm_row(
                "Peak Frequency Consistency (FDWRA)",
                "Industry-standard algorithm.\n"
                "Iteratively removes windows whose peak frequencies deviate from the group consensus.\n"
                "Essential for publication-quality results.\n"
                "Default: n=2.0, max_iter=50, distribution=lognormal (matches hvsrpy)",
                'fdwra'
            )
            layout.addWidget(self.fdwra_row['widget'])
            
            self.hvsr_amp_row = self._create_algorithm_row(
                "HVSR Peak Amplitude > 1.0",
                "Rejects windows where H/V ratio peak is below 1.0,\n"
                "indicating poor site response.",
                'hvsr_amplitude'
            )
            layout.addWidget(self.hvsr_amp_row['widget'])
            
            self.flat_peak_row = self._create_algorithm_row(
                "Flat Peak Detection",
                "Rejects windows with flat, wide, or multiple peaks,\n"
                "indicating unclear resonance.",
                'flat_peak'
            )
            layout.addWidget(self.flat_peak_row['widget'])
            
            return group
        
        def _create_algorithm_row(self, name: str, tooltip: str, algo_key: str) -> Dict[str, Any]:
            """Create a row for an algorithm with checkbox and settings button."""
            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(20, 2, 0, 2)  # Indent for hierarchy
            
            checkbox = QCheckBox(name)
            checkbox.setToolTip(tooltip)
            layout.addWidget(checkbox)
            
            layout.addStretch()
            
            settings_btn = QPushButton("Settings...")
            settings_btn.setFixedWidth(80)
            settings_btn.setToolTip(f"Configure {name} parameters")
            settings_btn.clicked.connect(lambda: self._open_settings_dialog(algo_key, name))
            layout.addWidget(settings_btn)
            
            return {
                'widget': widget,
                'checkbox': checkbox,
                'settings_btn': settings_btn,
                'key': algo_key
            }
        
        def _connect_signals(self):
            """Connect internal signals."""
            # Master enable
            self.master_enable.toggled.connect(self._on_master_toggled)
            
            # Mode selection
            self._sesame_radio.toggled.connect(self._on_mode_changed)
            self._custom_radio.toggled.connect(self._on_mode_changed)
            
            # Save button
            self.save_custom_btn.clicked.connect(self._on_save_custom_clicked)
            
            # Phase enables
            self.phase1_enable.toggled.connect(self._on_phase1_toggled)
            self.phase2_enable.toggled.connect(self._on_phase2_toggled)
            
            # Individual algorithm checkboxes
            for row in self._get_phase1_rows():
                row['checkbox'].toggled.connect(self._on_algorithm_toggled)
            for row in self._get_phase2_rows():
                row['checkbox'].toggled.connect(self._on_algorithm_toggled)
        
        def _get_phase1_rows(self):
            """Get all Phase 1 algorithm rows."""
            return [self.amplitude_row, self.stalta_row, self.spectral_row, self.statistical_row]
        
        def _get_phase2_rows(self):
            """Get all Phase 2 algorithm rows."""
            return [self.fdwra_row, self.hvsr_amp_row, self.flat_peak_row]
        
        def _on_master_toggled(self, checked: bool):
            """Handle master enable checkbox toggle."""
            # Enable/disable everything
            self._sesame_radio.setEnabled(checked)
            self._custom_radio.setEnabled(checked)
            self.save_custom_btn.setEnabled(checked and self._mode == 'custom')
            self.phase1_enable.setEnabled(checked)
            self.phase2_enable.setEnabled(checked)
            
            # Update phase sections
            self._update_phase1_enabled()
            self._update_phase2_enabled()
            
            self._emit_settings_changed()
        
        def _on_mode_changed(self, checked: bool):
            """Handle SESAME/Custom mode change."""
            if self._sesame_radio.isChecked():
                self._mode = 'sesame'
                self.save_custom_btn.setEnabled(False)
                self._apply_sesame_defaults()
            else:
                self._mode = 'custom'
                self.save_custom_btn.setEnabled(self.master_enable.isChecked())
                self._apply_custom_settings()
            
            self._emit_settings_changed()
        
        def _on_save_custom_clicked(self):
            """Handle Save Custom Settings button click."""
            settings = self._collect_current_settings()
            if save_custom_settings(settings):
                self._custom_settings = settings
                QMessageBox.information(
                    self, "Settings Saved",
                    "Custom QC settings have been saved.\n"
                    "They will be loaded automatically next time."
                )
            else:
                QMessageBox.warning(
                    self, "Save Failed",
                    "Failed to save custom settings.\n"
                    "Check file permissions."
                )
        
        def _on_phase1_toggled(self, checked: bool):
            """Handle Phase 1 checkbox toggle."""
            self._update_phase1_enabled()
            self._emit_settings_changed()
        
        def _on_phase2_toggled(self, checked: bool):
            """Handle Phase 2 checkbox toggle."""
            self._update_phase2_enabled()
            self._emit_settings_changed()
        
        def _on_algorithm_toggled(self, checked: bool):
            """Handle individual algorithm checkbox toggle."""
            self._update_active_counts()
            self._emit_settings_changed()
        
        def _update_phase1_enabled(self):
            """Update Phase 1 algorithm widgets enabled state."""
            enabled = self.master_enable.isChecked() and self.phase1_enable.isChecked()
            for row in self._get_phase1_rows():
                row['checkbox'].setEnabled(enabled)
                row['settings_btn'].setEnabled(enabled)
            self._update_active_counts()
        
        def _update_phase2_enabled(self):
            """Update Phase 2 algorithm widgets enabled state."""
            enabled = self.master_enable.isChecked() and self.phase2_enable.isChecked()
            for row in self._get_phase2_rows():
                row['checkbox'].setEnabled(enabled)
                row['settings_btn'].setEnabled(enabled)
            self._update_active_counts()
        
        def _update_active_counts(self):
            """Update the active algorithm count labels."""
            # Phase 1 count
            phase1_active = sum(
                1 for row in self._get_phase1_rows() 
                if row['checkbox'].isChecked() and row['checkbox'].isEnabled()
            )
            self.phase1_count_label.setText(f"[{phase1_active} active]")
            
            # Phase 2 count
            phase2_active = sum(
                1 for row in self._get_phase2_rows() 
                if row['checkbox'].isChecked() and row['checkbox'].isEnabled()
            )
            self.phase2_count_label.setText(f"[{phase2_active} active]")
        
        def _apply_sesame_defaults(self):
            """Apply SESAME standard defaults to UI."""
            self._block_signals = True
            
            defaults = SESAME_DEFAULTS
            algos = defaults['algorithms']
            
            # Phase enables
            self.phase1_enable.setChecked(defaults.get('phase1_enabled', True))
            self.phase2_enable.setChecked(defaults.get('phase2_enabled', True))
            
            # Phase 1 algorithms
            self.amplitude_row['checkbox'].setChecked(algos['amplitude']['enabled'])
            self.stalta_row['checkbox'].setChecked(algos['sta_lta']['enabled'])
            self.spectral_row['checkbox'].setChecked(algos['spectral_spike']['enabled'])
            self.statistical_row['checkbox'].setChecked(algos['statistical_outlier']['enabled'])
            
            # Phase 2 algorithms
            self.fdwra_row['checkbox'].setChecked(algos['fdwra']['enabled'])
            self.hvsr_amp_row['checkbox'].setChecked(algos['hvsr_amplitude']['enabled'])
            self.flat_peak_row['checkbox'].setChecked(algos['flat_peak']['enabled'])
            
            self._update_phase1_enabled()
            self._update_phase2_enabled()
            self._update_active_counts()
            
            self._block_signals = False
        
        def _apply_custom_settings(self):
            """Apply custom settings to UI."""
            self._block_signals = True
            
            settings = self._custom_settings
            algos = settings.get('algorithms', SESAME_DEFAULTS['algorithms'])
            
            # Phase enables
            self.phase1_enable.setChecked(settings.get('phase1_enabled', True))
            self.phase2_enable.setChecked(settings.get('phase2_enabled', True))
            
            # Phase 1 algorithms
            self.amplitude_row['checkbox'].setChecked(
                algos.get('amplitude', {}).get('enabled', True))
            self.stalta_row['checkbox'].setChecked(
                algos.get('sta_lta', {}).get('enabled', True))
            self.spectral_row['checkbox'].setChecked(
                algos.get('spectral_spike', {}).get('enabled', False))
            self.statistical_row['checkbox'].setChecked(
                algos.get('statistical_outlier', {}).get('enabled', False))
            
            # Phase 2 algorithms
            self.fdwra_row['checkbox'].setChecked(
                algos.get('fdwra', {}).get('enabled', True))
            self.hvsr_amp_row['checkbox'].setChecked(
                algos.get('hvsr_amplitude', {}).get('enabled', False))
            self.flat_peak_row['checkbox'].setChecked(
                algos.get('flat_peak', {}).get('enabled', False))
            
            self._update_phase1_enabled()
            self._update_phase2_enabled()
            self._update_active_counts()
            
            self._block_signals = False
        
        def _collect_current_settings(self) -> Dict[str, Any]:
            """Collect current UI settings into a dictionary."""
            return {
                'phase1_enabled': self.phase1_enable.isChecked(),
                'phase2_enabled': self.phase2_enable.isChecked(),
                'algorithms': {
                    'amplitude': {
                        'enabled': self.amplitude_row['checkbox'].isChecked(),
                        'params': self._get_algorithm_params('amplitude')
                    },
                    'sta_lta': {
                        'enabled': self.stalta_row['checkbox'].isChecked(),
                        'params': self._get_algorithm_params('sta_lta')
                    },
                    'spectral_spike': {
                        'enabled': self.spectral_row['checkbox'].isChecked(),
                        'params': self._get_algorithm_params('spectral_spike')
                    },
                    'statistical_outlier': {
                        'enabled': self.statistical_row['checkbox'].isChecked(),
                        'params': self._get_algorithm_params('statistical_outlier')
                    },
                    'fdwra': {
                        'enabled': self.fdwra_row['checkbox'].isChecked(),
                        'params': self._get_algorithm_params('fdwra')
                    },
                    'hvsr_amplitude': {
                        'enabled': self.hvsr_amp_row['checkbox'].isChecked(),
                        'params': self._get_algorithm_params('hvsr_amplitude')
                    },
                    'flat_peak': {
                        'enabled': self.flat_peak_row['checkbox'].isChecked(),
                        'params': self._get_algorithm_params('flat_peak')
                    }
                }
            }
        
        def _get_algorithm_params(self, algo_key: str) -> Dict[str, Any]:
            """Get current parameters for an algorithm."""
            if self._mode == 'sesame':
                return SESAME_DEFAULTS['algorithms'].get(algo_key, {}).get('params', {})
            else:
                return self._custom_settings.get('algorithms', {}).get(algo_key, {}).get('params', {})
        
        def _open_settings_dialog(self, algo_key: str, algo_name: str):
            """Open settings dialog for an algorithm."""
            # Import here to avoid circular imports
            from hvsr_pro.gui.dialogs.qc.algorithm_settings_dialogs import open_algorithm_settings_dialog
            
            current_params = self._get_algorithm_params(algo_key)
            new_params = open_algorithm_settings_dialog(self, algo_key, algo_name, current_params)
            
            if new_params is not None:
                # Update custom settings with new params
                if 'algorithms' not in self._custom_settings:
                    self._custom_settings['algorithms'] = {}
                if algo_key not in self._custom_settings['algorithms']:
                    self._custom_settings['algorithms'][algo_key] = {'enabled': True, 'params': {}}
                self._custom_settings['algorithms'][algo_key]['params'] = new_params
                
                # If in SESAME mode, switch to custom
                if self._mode == 'sesame':
                    self._custom_radio.setChecked(True)
                
                self._emit_settings_changed()
        
        def _emit_settings_changed(self):
            """Emit settings_changed signal."""
            if not self._block_signals:
                self.settings_changed.emit(self.get_settings())
        
        # === PUBLIC API ===
        
        def get_settings(self) -> Dict[str, Any]:
            """
            Get current QC settings as a dictionary.
            
            Returns dictionary compatible with processing_worker:
            {
                'enabled': bool,
                'mode': 'sesame' | 'custom',
                'phase1_enabled': bool,
                'phase2_enabled': bool,
                'algorithms': {...},
                'cox_fdwra': {...}  # For backward compatibility
            }
            """
            settings = self._collect_current_settings()
            
            # Add master state
            settings['enabled'] = self.master_enable.isChecked()
            settings['mode'] = self._mode
            
            # Add FDWRA settings in old format for backward compatibility
            fdwra_params = settings['algorithms']['fdwra']['params']
            settings['cox_fdwra'] = {
                'enabled': settings['algorithms']['fdwra']['enabled'],
                'n': fdwra_params.get('n', 2.0),
                'max_iterations': fdwra_params.get('max_iterations', 50),
                'min_iterations': fdwra_params.get('min_iterations', 1),
                'distribution_fn': fdwra_params.get('distribution_fn', 'lognormal'),
                'distribution_mc': fdwra_params.get('distribution_mc', 'lognormal')
            }
            
            return settings
        
        def get_qc_settings_object(self) -> QCSettings:
            """
            Get current settings as QCSettings object.
            
            Provides compatibility with existing code expecting QCSettings.
            """
            settings = self.get_settings()
            
            qc = QCSettings()
            qc.enabled = settings['enabled']
            qc.mode = 'custom'  # Always custom since we have explicit settings
            
            algos = settings['algorithms']
            
            # Pre-HVSR
            qc.amplitude.enabled = algos['amplitude']['enabled']
            qc.sta_lta.enabled = algos['sta_lta']['enabled']
            qc.sta_lta.params = algos['sta_lta']['params']
            qc.frequency_domain.enabled = algos['spectral_spike']['enabled']
            qc.frequency_domain.params = {'spike_threshold': algos['spectral_spike']['params'].get('spike_threshold', 3.0)}
            qc.statistical_outlier.enabled = algos['statistical_outlier']['enabled']
            qc.statistical_outlier.params = algos['statistical_outlier']['params']
            
            # Post-HVSR
            qc.hvsr_amplitude.enabled = algos['hvsr_amplitude']['enabled']
            qc.hvsr_amplitude.params = algos['hvsr_amplitude']['params']
            qc.flat_peak.enabled = algos['flat_peak']['enabled']
            qc.flat_peak.params = algos['flat_peak']['params']
            
            # FDWRA
            fdwra = algos['fdwra']
            qc.cox_fdwra.enabled = fdwra['enabled']
            qc.cox_fdwra.n = fdwra['params'].get('n', 2.0)
            qc.cox_fdwra.max_iterations = fdwra['params'].get('max_iterations', 50)
            qc.cox_fdwra.min_iterations = fdwra['params'].get('min_iterations', 1)
            qc.cox_fdwra.distribution_fn = fdwra['params'].get('distribution_fn', 'lognormal')
            qc.cox_fdwra.distribution_mc = fdwra['params'].get('distribution_mc', 'lognormal')
            
            return qc
        
        def is_qc_enabled(self) -> bool:
            """Check if QC is enabled (master checkbox)."""
            return self.master_enable.isChecked()
        
        def is_phase1_enabled(self) -> bool:
            """Check if Phase 1 is enabled."""
            return self.master_enable.isChecked() and self.phase1_enable.isChecked()
        
        def is_phase2_enabled(self) -> bool:
            """Check if Phase 2 is enabled."""
            return self.master_enable.isChecked() and self.phase2_enable.isChecked()
        
        def is_fdwra_enabled(self) -> bool:
            """Check if FDWRA is enabled."""
            return (self.master_enable.isChecked() and 
                    self.phase2_enable.isChecked() and 
                    self.fdwra_row['checkbox'].isChecked())
        
        def get_fdwra_params(self) -> Dict[str, Any]:
            """Get FDWRA parameters."""
            return self._get_algorithm_params('fdwra')


else:
    class UnifiedQCPanel:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            raise ImportError("PyQt5 is required for GUI functionality")
