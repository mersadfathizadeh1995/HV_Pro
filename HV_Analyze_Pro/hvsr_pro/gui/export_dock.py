"""
Export Dock for HVSR Pro
=========================

Comprehensive export functionality for plots, data, and reports.
"""

from PyQt5.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QPushButton,
    QGroupBox, QCheckBox, QLabel, QFileDialog, QMessageBox,
    QScrollArea, QHBoxLayout, QComboBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont
from pathlib import Path
from datetime import datetime
import json
import csv


class ExportDock(QDockWidget):
    """
    Dock widget for exporting plots, data, and reports.

    Features:
    - Export plot as image (PNG, PDF, SVG)
    - Generate comprehensive report plots
    - Export results (CSV, JSON)
    - Save/Load sessions
    - Export statistics (mean, median, std, percentiles)

    Signals:
        export_plot_requested: Request to export current plot
        export_data_requested: Request to export data
        generate_report_requested: Request to generate report plots
        save_session_requested: Request to save session
        load_session_requested: Request to load session
    """

    export_plot_requested = pyqtSignal(str)  # format
    export_data_requested = pyqtSignal(str, dict)  # format, options
    generate_report_requested = pyqtSignal()
    save_session_requested = pyqtSignal(str)  # filepath
    load_session_requested = pyqtSignal(str)  # filepath

    def __init__(self, parent=None):
        """Initialize export dock."""
        super().__init__("Export", parent)
        self.setObjectName("ExportDock")

        # References (set by parent)
        self.result = None
        self.windows = None
        self.canvas_manager = None
        self.data = None

        # Create UI
        self._create_ui()

    def _create_ui(self):
        """Create dock UI."""
        # Main widget
        widget = QWidget(self)
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(8)

        # Title
        title = QLabel("Export & Save")
        title.setFont(QFont("Arial", 10, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # === PLOT EXPORT ===
        plot_group = self._create_plot_export_group()
        main_layout.addWidget(plot_group)

        # === DATA EXPORT ===
        data_group = self._create_data_export_group()
        main_layout.addWidget(data_group)

        # === STATISTICS EXPORT ===
        stats_group = self._create_stats_export_group()
        main_layout.addWidget(stats_group)

        # === REPORT GENERATION ===
        report_group = self._create_report_group()
        main_layout.addWidget(report_group)

        # === SESSION MANAGEMENT ===
        session_group = self._create_session_group()
        main_layout.addWidget(session_group)

        main_layout.addStretch()

        # Wrap in scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidget(widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.setWidget(scroll_area)

    def _create_plot_export_group(self) -> QGroupBox:
        """Create plot export group."""
        group = QGroupBox("Export Plot as Image")
        layout = QVBoxLayout(group)

        # Format buttons
        btn_layout = QHBoxLayout()

        self.export_png_btn = QPushButton("PNG")
        self.export_png_btn.setToolTip("Export as PNG image (high quality)")
        self.export_png_btn.clicked.connect(lambda: self.export_plot("png"))
        btn_layout.addWidget(self.export_png_btn)

        self.export_pdf_btn = QPushButton("PDF")
        self.export_pdf_btn.setToolTip("Export as PDF document (vector)")
        self.export_pdf_btn.clicked.connect(lambda: self.export_plot("pdf"))
        btn_layout.addWidget(self.export_pdf_btn)

        self.export_svg_btn = QPushButton("SVG")
        self.export_svg_btn.setToolTip("Export as SVG vector graphics")
        self.export_svg_btn.clicked.connect(lambda: self.export_plot("svg"))
        btn_layout.addWidget(self.export_svg_btn)

        layout.addLayout(btn_layout)

        # Info
        info = QLabel("Export current HVSR plot with all settings")
        info.setStyleSheet("QLabel { color: #666; font-size: 9px; }")
        info.setWordWrap(True)
        layout.addWidget(info)

        return group

    def _create_data_export_group(self) -> QGroupBox:
        """Create data export group."""
        group = QGroupBox("Export Results Data")
        layout = QVBoxLayout(group)

        # Export buttons
        btn_layout = QHBoxLayout()

        self.export_csv_btn = QPushButton("CSV")
        self.export_csv_btn.setToolTip("Export HVSR curve and peaks as CSV")
        self.export_csv_btn.clicked.connect(lambda: self.export_data("csv"))
        btn_layout.addWidget(self.export_csv_btn)

        self.export_json_btn = QPushButton("JSON")
        self.export_json_btn.setToolTip("Export complete results as JSON")
        self.export_json_btn.clicked.connect(lambda: self.export_data("json"))
        btn_layout.addWidget(self.export_json_btn)

        layout.addLayout(btn_layout)

        # Info
        info = QLabel("Export HVSR curve, peaks, and metadata")
        info.setStyleSheet("QLabel { color: #666; font-size: 9px; }")
        info.setWordWrap(True)
        layout.addWidget(info)

        return group

    def _create_stats_export_group(self) -> QGroupBox:
        """Create statistics export group."""
        group = QGroupBox("Export Statistics")
        layout = QVBoxLayout(group)

        # Statistics options
        self.export_mean_cb = QCheckBox("Mean curve")
        self.export_mean_cb.setChecked(True)
        layout.addWidget(self.export_mean_cb)

        self.export_median_cb = QCheckBox("Median curve")
        self.export_median_cb.setChecked(True)
        layout.addWidget(self.export_median_cb)

        self.export_std_cb = QCheckBox("Standard deviation (±1σ)")
        self.export_std_cb.setChecked(True)
        layout.addWidget(self.export_std_cb)

        self.export_percentile_cb = QCheckBox("Percentiles (16th, 84th)")
        self.export_percentile_cb.setChecked(False)
        layout.addWidget(self.export_percentile_cb)

        self.export_individual_cb = QCheckBox("Individual window curves")
        self.export_individual_cb.setChecked(False)
        layout.addWidget(self.export_individual_cb)

        # Export button
        self.export_stats_btn = QPushButton("Export Statistics")
        self.export_stats_btn.setToolTip("Export selected statistics to CSV")
        self.export_stats_btn.clicked.connect(self.export_statistics)
        layout.addWidget(self.export_stats_btn)

        return group

    def _create_report_group(self) -> QGroupBox:
        """Create report generation group."""
        group = QGroupBox("Generate Report Plots")
        layout = QVBoxLayout(group)

        self.generate_report_btn = QPushButton("Generate Comprehensive Report")
        self.generate_report_btn.setToolTip(
            "Generate multi-panel report with:\n"
            "- HVSR curve with peaks\n"
            "- Time series windows\n"
            "- Spectrograms\n"
            "- Quality statistics"
        )
        self.generate_report_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px; }"
        )
        self.generate_report_btn.clicked.connect(self.generate_report)
        layout.addWidget(self.generate_report_btn)

        # Info
        info = QLabel("Creates publication-ready multi-panel figure")
        info.setStyleSheet("QLabel { color: #666; font-size: 9px; }")
        info.setWordWrap(True)
        layout.addWidget(info)

        return group

    def _create_session_group(self) -> QGroupBox:
        """Create session management group."""
        group = QGroupBox("Session Management")
        layout = QVBoxLayout(group)

        # Save session
        self.save_session_btn = QPushButton("Save Session")
        self.save_session_btn.setToolTip("Save current analysis session (settings, results, peaks)")
        self.save_session_btn.clicked.connect(self.save_session)
        layout.addWidget(self.save_session_btn)

        # Load session
        self.load_session_btn = QPushButton("Load Session")
        self.load_session_btn.setToolTip("Load previously saved session")
        self.load_session_btn.clicked.connect(self.load_session)
        layout.addWidget(self.load_session_btn)

        # Info
        info = QLabel("Save/restore complete analysis state")
        info.setStyleSheet("QLabel { color: #666; font-size: 9px; }")
        info.setWordWrap(True)
        layout.addWidget(info)

        return group

    def export_plot(self, format_type: str):
        """Export plot as image."""
        if not self.canvas_manager or not self.canvas_manager.canvas:
            QMessageBox.warning(self, "No Plot", "No plot available to export.")
            return

        # Get file extension and filter
        ext_map = {
            'png': ('PNG Image', '*.png'),
            'pdf': ('PDF Document', '*.pdf'),
            'svg': ('SVG Vector', '*.svg')
        }

        desc, pattern = ext_map.get(format_type, ('Image', '*.*'))

        filename, _ = QFileDialog.getSaveFileName(
            self,
            f"Export Plot as {desc}",
            f"hvsr_plot.{format_type}",
            f"{desc} ({pattern});;All Files (*)"
        )

        if filename:
            try:
                # Get the figure from canvas manager
                fig = self.canvas_manager.canvas.fig
                fig.savefig(filename, dpi=300, bbox_inches='tight')
                QMessageBox.information(self, "Export Successful", f"Plot saved to:\n{filename}")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Failed to export plot:\n{str(e)}")

    def export_data(self, format_type: str):
        """Export results data."""
        if not self.result:
            QMessageBox.warning(self, "No Data", "No HVSR results available to export.")
            return

        self.export_data_requested.emit(format_type, {})

    def export_statistics(self):
        """Export statistics based on selected options."""
        if not self.result:
            QMessageBox.warning(self, "No Data", "No HVSR results available to export.")
            return

        # Get export options
        options = {
            'mean': self.export_mean_cb.isChecked(),
            'median': self.export_median_cb.isChecked(),
            'std': self.export_std_cb.isChecked(),
            'percentile': self.export_percentile_cb.isChecked(),
            'individual': self.export_individual_cb.isChecked()
        }

        # Get filename
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Statistics",
            "hvsr_statistics.csv",
            "CSV Files (*.csv);;All Files (*)"
        )

        if filename:
            try:
                self._write_statistics_csv(filename, options)
                QMessageBox.information(self, "Export Successful", f"Statistics saved to:\n{filename}")
            except Exception as e:
                QMessageBox.critical(self, "Export Failed", f"Failed to export statistics:\n{str(e)}")

    def _write_statistics_csv(self, filename: str, options: dict):
        """Write statistics to CSV file."""
        import numpy as np

        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)

            # Header
            header = ['Frequency (Hz)']
            if options['mean']:
                header.append('Mean H/V')
            if options['median']:
                header.append('Median H/V')
            if options['std']:
                header.extend(['Mean + 1σ', 'Mean - 1σ'])
            if options['percentile']:
                header.extend(['16th Percentile', '84th Percentile'])
            if options['individual'] and self.windows:
                for i in range(self.windows.n_windows):
                    header.append(f'Window {i+1}')

            writer.writerow(header)

            # Data rows
            frequencies = self.result.frequency
            for i, freq in enumerate(frequencies):
                row = [freq]

                if options['mean']:
                    row.append(self.result.mean_curve[i])
                if options['median'] and hasattr(self.result, 'median_curve'):
                    row.append(self.result.median_curve[i])
                if options['std']:
                    row.append(self.result.mean_curve[i] + self.result.std_curve[i])
                    row.append(self.result.mean_curve[i] - self.result.std_curve[i])
                if options['percentile'] and hasattr(self.result, 'percentile_16'):
                    row.append(self.result.percentile_16[i])
                    row.append(self.result.percentile_84[i])
                if options['individual'] and self.windows:
                    for win_idx in range(self.windows.n_windows):
                        if hasattr(self.result, 'window_curves') and self.result.window_curves is not None:
                            row.append(self.result.window_curves[win_idx][i])
                        else:
                            row.append('')

                writer.writerow(row)

    def generate_report(self):
        """Generate comprehensive report plots."""
        if not self.result:
            QMessageBox.warning(self, "No Data", "No HVSR results available for report generation.")
            return

        # Open comprehensive export dialog
        from hvsr_pro.gui.export_dialog import ExportDialog

        dialog = ExportDialog(
            parent=self,
            result=self.result,
            windows=self.windows,
            data=self.data
        )
        dialog.exec_()

    def save_session(self):
        """Save current session."""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Session",
            "hvsr_session.json",
            "JSON Files (*.json);;All Files (*)"
        )

        if filename:
            self.save_session_requested.emit(filename)

    def load_session(self):
        """Load saved session."""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load Session",
            "",
            "JSON Files (*.json);;All Files (*)"
        )

        if filename:
            self.load_session_requested.emit(filename)

    def set_references(self, result, windows, canvas_manager, data=None):
        """
        Set references to result, windows, canvas manager, and data.

        Args:
            result: HVSRResult instance
            windows: WindowCollection instance
            canvas_manager: PlotWindowManager instance
            data: SeismicData instance (optional)
        """
        self.result = result
        self.windows = windows
        self.canvas_manager = canvas_manager
        self.data = data

        # Enable/disable buttons based on availability
        has_result = result is not None
        self.export_png_btn.setEnabled(has_result)
        self.export_pdf_btn.setEnabled(has_result)
        self.export_svg_btn.setEnabled(has_result)
        self.export_csv_btn.setEnabled(has_result)
        self.export_json_btn.setEnabled(has_result)
        self.export_stats_btn.setEnabled(has_result)
        self.generate_report_btn.setEnabled(has_result)
        self.save_session_btn.setEnabled(has_result)
