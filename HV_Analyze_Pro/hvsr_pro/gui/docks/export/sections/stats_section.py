"""
Statistics Export Section
=========================

Export HVSR statistics (mean, median, std, percentiles, individual windows).
"""

try:
    from PyQt5.QtWidgets import QPushButton, QCheckBox
    from PyQt5.QtCore import pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False

if HAS_PYQT5:
    from hvsr_pro.gui.components import CollapsibleSection


if HAS_PYQT5:
    class StatsExportSection(CollapsibleSection):
        """
        Statistics export section with checkboxes for different statistics.
        
        Signals:
            export_requested: Emitted when export is requested (dict options)
        """
        
        export_requested = pyqtSignal(dict)
        
        def __init__(self, parent=None):
            super().__init__("Export Statistics", parent)
            self._init_content()
        
        def _init_content(self):
            """Initialize section content."""
            # Statistics options
            self.export_mean_cb = QCheckBox("Mean curve")
            self.export_mean_cb.setChecked(True)
            self.add_widget(self.export_mean_cb)
            
            self.export_median_cb = QCheckBox("Median curve")
            self.export_median_cb.setChecked(True)
            self.add_widget(self.export_median_cb)
            
            self.export_std_cb = QCheckBox("Standard deviation")
            self.export_std_cb.setChecked(True)
            self.add_widget(self.export_std_cb)
            
            self.export_percentile_cb = QCheckBox("Percentiles (16th, 84th)")
            self.export_percentile_cb.setChecked(False)
            self.add_widget(self.export_percentile_cb)
            
            self.export_individual_cb = QCheckBox("Individual window curves")
            self.export_individual_cb.setChecked(False)
            self.add_widget(self.export_individual_cb)
            
            # Export button
            self.export_stats_btn = QPushButton("Export Statistics")
            self.export_stats_btn.setToolTip("Export selected statistics to CSV")
            self.export_stats_btn.clicked.connect(self._emit_export)
            self.add_widget(self.export_stats_btn)
        
        def _emit_export(self):
            """Emit export signal with options."""
            options = self.get_options()
            self.export_requested.emit(options)
        
        def get_options(self) -> dict:
            """Get current export options."""
            return {
                'mean': self.export_mean_cb.isChecked(),
                'median': self.export_median_cb.isChecked(),
                'std': self.export_std_cb.isChecked(),
                'percentile': self.export_percentile_cb.isChecked(),
                'individual': self.export_individual_cb.isChecked()
            }
        
        def set_enabled(self, enabled: bool):
            """Enable or disable export button."""
            self.export_stats_btn.setEnabled(enabled)


else:
    class StatsExportSection:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass
