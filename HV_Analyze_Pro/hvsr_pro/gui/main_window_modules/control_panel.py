"""
Control Panel Module
====================

Control panel components for the main window.
Provides factory functions for creating settings groups.
"""

from typing import Dict, Any, Callable, Optional

try:
    from PyQt5.QtWidgets import (
        QWidget, QGroupBox, QVBoxLayout, QHBoxLayout, QFormLayout,
        QLabel, QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
        QCheckBox
    )
    from PyQt5.QtCore import Qt, pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


if HAS_PYQT5:
    class SettingsGroup(QGroupBox):
        """
        Base class for settings group boxes.
        
        Provides common functionality for grouped settings.
        """
        
        settings_changed = pyqtSignal(dict)
        
        def __init__(self, title: str, parent=None):
            super().__init__(title, parent)
            self._init_ui()
        
        def _init_ui(self):
            """Initialize UI - override in subclass."""
            self.layout = QVBoxLayout(self)
        
        def get_settings(self) -> Dict[str, Any]:
            """Get all settings - override in subclass."""
            return {}
        
        def set_settings(self, settings: Dict[str, Any]):
            """Set settings - override in subclass."""
            pass
        
        def _emit_changed(self):
            """Emit settings changed signal."""
            self.settings_changed.emit(self.get_settings())


    class ProcessingSettingsGroup(SettingsGroup):
        """Processing settings group with frequency and window controls."""
        
        def __init__(self, parent=None):
            super().__init__("Processing Settings", parent)
        
        def _init_ui(self):
            """Initialize processing settings UI."""
            layout = QFormLayout(self)
            
            # Frequency range
            freq_layout = QHBoxLayout()
            
            self.freq_min_spin = QDoubleSpinBox()
            self.freq_min_spin.setRange(0.01, 100.0)
            self.freq_min_spin.setValue(0.2)
            self.freq_min_spin.setSingleStep(0.1)
            self.freq_min_spin.setSuffix(" Hz")
            freq_layout.addWidget(self.freq_min_spin)
            
            freq_layout.addWidget(QLabel("-"))
            
            self.freq_max_spin = QDoubleSpinBox()
            self.freq_max_spin.setRange(1.0, 1000.0)
            self.freq_max_spin.setValue(20.0)
            self.freq_max_spin.setSingleStep(1.0)
            self.freq_max_spin.setSuffix(" Hz")
            freq_layout.addWidget(self.freq_max_spin)
            
            layout.addRow("Frequency Range:", freq_layout)
            
            # Frequency points
            self.freq_points_spin = QSpinBox()
            self.freq_points_spin.setRange(50, 500)
            self.freq_points_spin.setValue(100)
            layout.addRow("Frequency Points:", self.freq_points_spin)
            
            # Window length
            self.window_length_spin = QDoubleSpinBox()
            self.window_length_spin.setRange(10.0, 600.0)
            self.window_length_spin.setValue(30.0)
            self.window_length_spin.setSuffix(" s")
            layout.addRow("Window Length:", self.window_length_spin)
            
            # Overlap
            self.overlap_spin = QSpinBox()
            self.overlap_spin.setRange(0, 90)
            self.overlap_spin.setValue(50)
            self.overlap_spin.setSuffix(" %")
            layout.addRow("Overlap:", self.overlap_spin)
            
            # Smoothing
            self.smoothing_combo = QComboBox()
            self.smoothing_combo.addItem("Konno-Ohmachi (b=40)", "konno_ohmachi")
            self.smoothing_combo.addItem("None", "none")
            layout.addRow("Smoothing:", self.smoothing_combo)
        
        def get_settings(self) -> Dict[str, Any]:
            """Get processing settings."""
            return {
                'freq_min': self.freq_min_spin.value(),
                'freq_max': self.freq_max_spin.value(),
                'freq_points': self.freq_points_spin.value(),
                'window_length': self.window_length_spin.value(),
                'overlap': self.overlap_spin.value(),
                'smoothing': self.smoothing_combo.currentData(),
            }
        
        def set_settings(self, settings: Dict[str, Any]):
            """Set processing settings."""
            if 'freq_min' in settings:
                self.freq_min_spin.setValue(settings['freq_min'])
            if 'freq_max' in settings:
                self.freq_max_spin.setValue(settings['freq_max'])
            if 'freq_points' in settings:
                self.freq_points_spin.setValue(settings['freq_points'])
            if 'window_length' in settings:
                self.window_length_spin.setValue(settings['window_length'])
            if 'overlap' in settings:
                self.overlap_spin.setValue(settings['overlap'])
            if 'smoothing' in settings:
                idx = self.smoothing_combo.findData(settings['smoothing'])
                if idx >= 0:
                    self.smoothing_combo.setCurrentIndex(idx)


    class QCSettingsGroup(SettingsGroup):
        """Quality control settings group."""
        
        def __init__(self, parent=None):
            super().__init__("Quality Control", parent)
        
        def _init_ui(self):
            """Initialize QC settings UI."""
            layout = QVBoxLayout(self)
            
            # QC Mode
            qc_layout = QHBoxLayout()
            qc_layout.addWidget(QLabel("QC Mode:"))
            
            self.qc_combo = QComboBox()
            self.qc_combo.addItem("None", "none")
            self.qc_combo.addItem("SESAME", "sesame")
            self.qc_combo.addItem("Balanced", "balanced")
            self.qc_combo.addItem("Aggressive", "aggressive")
            qc_layout.addWidget(self.qc_combo)
            
            layout.addLayout(qc_layout)
            
            # Cox FDWRA
            self.cox_check = QCheckBox("Enable Cox FDWRA Rejection")
            self.cox_check.setChecked(True)
            layout.addWidget(self.cox_check)
            
            # Cox settings
            cox_layout = QHBoxLayout()
            cox_layout.addWidget(QLabel("  n-value:"))
            self.cox_n_spin = QDoubleSpinBox()
            self.cox_n_spin.setRange(0.5, 10.0)
            self.cox_n_spin.setValue(2.0)
            self.cox_n_spin.setSingleStep(0.5)
            cox_layout.addWidget(self.cox_n_spin)
            
            cox_layout.addWidget(QLabel("Min iter:"))
            self.cox_iter_spin = QSpinBox()
            self.cox_iter_spin.setRange(1, 20)
            self.cox_iter_spin.setValue(1)
            cox_layout.addWidget(self.cox_iter_spin)
            
            layout.addLayout(cox_layout)
        
        def get_settings(self) -> Dict[str, Any]:
            """Get QC settings."""
            return {
                'qc_mode': self.qc_combo.currentData(),
                'cox_enabled': self.cox_check.isChecked(),
                'cox_n': self.cox_n_spin.value(),
                'cox_min_iter': self.cox_iter_spin.value(),
            }
        
        def set_settings(self, settings: Dict[str, Any]):
            """Set QC settings."""
            if 'qc_mode' in settings:
                idx = self.qc_combo.findData(settings['qc_mode'])
                if idx >= 0:
                    self.qc_combo.setCurrentIndex(idx)
            if 'cox_enabled' in settings:
                self.cox_check.setChecked(settings['cox_enabled'])
            if 'cox_n' in settings:
                self.cox_n_spin.setValue(settings['cox_n'])
            if 'cox_min_iter' in settings:
                self.cox_iter_spin.setValue(settings['cox_min_iter'])


    class ParallelSettingsGroup(SettingsGroup):
        """Parallel processing settings group."""
        
        def __init__(self, parent=None):
            super().__init__("Parallel Processing", parent)
        
        def _init_ui(self):
            """Initialize parallel settings UI."""
            import multiprocessing
            max_cores = multiprocessing.cpu_count()
            
            layout = QHBoxLayout(self)
            
            self.parallel_check = QCheckBox("Enable parallel processing")
            self.parallel_check.setChecked(True)
            layout.addWidget(self.parallel_check)
            
            layout.addWidget(QLabel("Cores:"))
            
            self.cores_spin = QSpinBox()
            self.cores_spin.setRange(1, max_cores)
            self.cores_spin.setValue(max(1, max_cores - 1))
            layout.addWidget(self.cores_spin)
            
            layout.addWidget(QLabel(f"/ {max_cores}"))
        
        def get_settings(self) -> Dict[str, Any]:
            """Get parallel settings."""
            return {
                'parallel_enabled': self.parallel_check.isChecked(),
                'n_cores': self.cores_spin.value(),
            }
        
        def set_settings(self, settings: Dict[str, Any]):
            """Set parallel settings."""
            if 'parallel_enabled' in settings:
                self.parallel_check.setChecked(settings['parallel_enabled'])
            if 'n_cores' in settings:
                self.cores_spin.setValue(settings['n_cores'])


else:
    class SettingsGroup:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass
    
    class ProcessingSettingsGroup(SettingsGroup):
        pass
    
    class QCSettingsGroup(SettingsGroup):
        pass
    
    class ParallelSettingsGroup(SettingsGroup):
        pass
