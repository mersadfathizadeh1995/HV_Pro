"""
Export Report Dialog
====================

Dialog for selecting which outputs to include in the azimuthal export report.
"""

from typing import Dict, Any

try:
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
        QPushButton, QLabel, QComboBox, QSpinBox, QCheckBox,
        QWidget, QGridLayout, QDialogButtonBox
    )
    from PyQt5.QtGui import QFont
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


if HAS_PYQT5:
    class ExportReportDialog(QDialog):
        """
        Dialog for selecting which outputs to include in the export report.
        
        Allows user to select:
        - Figures: summary, 3D, 2D, polar, curves
        - Data files: CSV mean, CSV individual, JSON, peaks CSV
        - Settings: format, DPI
        """
        
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("Export Azimuthal Report")
            self.setModal(True)
            self.setMinimumWidth(400)
            
            self._create_ui()
        
        def _create_ui(self):
            """Create the dialog UI."""
            layout = QVBoxLayout(self)
            
            # Title
            title = QLabel("Select Outputs to Export")
            title.setFont(QFont("Arial", 11, QFont.Bold))
            layout.addWidget(title)
            
            # Figures section
            fig_group = QGroupBox("Figures")
            fig_layout = QVBoxLayout(fig_group)
            
            self.cb_summary = QCheckBox("Summary Plot (3D + 2D + Curves)")
            self.cb_summary.setChecked(True)
            fig_layout.addWidget(self.cb_summary)
            
            self.cb_3d = QCheckBox("3D Surface Plot")
            self.cb_3d.setChecked(True)
            fig_layout.addWidget(self.cb_3d)
            
            self.cb_2d = QCheckBox("2D Contour Plot")
            self.cb_2d.setChecked(True)
            fig_layout.addWidget(self.cb_2d)
            
            self.cb_polar = QCheckBox("Polar Plot")
            self.cb_polar.setChecked(True)
            fig_layout.addWidget(self.cb_polar)
            
            self.cb_curves = QCheckBox("Individual Curves Plot")
            self.cb_curves.setChecked(True)
            fig_layout.addWidget(self.cb_curves)
            
            layout.addWidget(fig_group)
            
            # Data section
            data_group = QGroupBox("Data Files")
            data_layout = QVBoxLayout(data_group)
            
            self.cb_csv_mean = QCheckBox("Mean Curves CSV (all azimuths)")
            self.cb_csv_mean.setChecked(True)
            data_layout.addWidget(self.cb_csv_mean)
            
            self.cb_csv_individual = QCheckBox("Individual Window Curves CSV")
            self.cb_csv_individual.setChecked(False)
            data_layout.addWidget(self.cb_csv_individual)
            
            self.cb_json = QCheckBox("Full Results JSON")
            self.cb_json.setChecked(True)
            data_layout.addWidget(self.cb_json)
            
            self.cb_peaks = QCheckBox("Peak Frequencies CSV (per azimuth)")
            self.cb_peaks.setChecked(True)
            data_layout.addWidget(self.cb_peaks)
            
            layout.addWidget(data_group)
            
            # Format settings
            settings_group = QGroupBox("Settings")
            settings_layout = QGridLayout(settings_group)
            
            settings_layout.addWidget(QLabel("Figure Format:"), 0, 0)
            self.format_combo = QComboBox()
            self.format_combo.addItems(["PNG", "PDF", "SVG", "All Formats"])
            settings_layout.addWidget(self.format_combo, 0, 1)
            
            settings_layout.addWidget(QLabel("DPI:"), 1, 0)
            self.dpi_spin = QSpinBox()
            self.dpi_spin.setRange(72, 600)
            self.dpi_spin.setValue(300)
            settings_layout.addWidget(self.dpi_spin, 1, 1)
            
            layout.addWidget(settings_group)
            
            # Select all / none buttons
            btn_container = QWidget()
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(0, 0, 0, 0)
            
            select_all_btn = QPushButton("Select All")
            select_all_btn.clicked.connect(self._select_all)
            btn_layout.addWidget(select_all_btn)
            
            select_none_btn = QPushButton("Select None")
            select_none_btn.clicked.connect(self._select_none)
            btn_layout.addWidget(select_none_btn)
            
            layout.addWidget(btn_container)
            
            # Dialog buttons
            buttons = QDialogButtonBox(
                QDialogButtonBox.Ok | QDialogButtonBox.Cancel
            )
            buttons.accepted.connect(self.accept)
            buttons.rejected.connect(self.reject)
            layout.addWidget(buttons)
        
        def _get_all_checkboxes(self) -> list:
            """Get all checkboxes."""
            return [
                self.cb_summary, self.cb_3d, self.cb_2d, self.cb_polar,
                self.cb_curves, self.cb_csv_mean, self.cb_csv_individual,
                self.cb_json, self.cb_peaks
            ]
        
        def _select_all(self):
            """Select all checkboxes."""
            for cb in self._get_all_checkboxes():
                cb.setChecked(True)
        
        def _select_none(self):
            """Deselect all checkboxes."""
            for cb in self._get_all_checkboxes():
                cb.setChecked(False)
        
        def get_selections(self) -> Dict[str, Any]:
            """
            Get selected options.
            
            Returns:
                Dictionary with 'figures', 'data', 'format', and 'dpi' keys
            """
            return {
                'figures': {
                    'summary': self.cb_summary.isChecked(),
                    '3d': self.cb_3d.isChecked(),
                    '2d': self.cb_2d.isChecked(),
                    'polar': self.cb_polar.isChecked(),
                    'curves': self.cb_curves.isChecked(),
                },
                'data': {
                    'csv_mean': self.cb_csv_mean.isChecked(),
                    'csv_individual': self.cb_csv_individual.isChecked(),
                    'json': self.cb_json.isChecked(),
                    'peaks': self.cb_peaks.isChecked(),
                },
                'format': self.format_combo.currentText().lower(),
                'dpi': self.dpi_spin.value()
            }


else:
    class ExportReportDialog:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass
