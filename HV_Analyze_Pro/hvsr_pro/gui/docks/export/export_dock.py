"""
Export Dock for HVSR Pro
=========================

Comprehensive export functionality for plots, data, and reports.
Uses modular section components and pure exporter functions.
"""

from PyQt5.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QLabel,
    QFileDialog, QMessageBox, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont

from .sections import (
    PlotExportSection,
    DataExportSection,
    StatsExportSection,
    ComparisonFiguresSection,
    ReportSection,
    SessionSection,
)
from .exporters import (
    export_csv,
    export_json,
    export_statistics_csv,
    export_comparison_figure,
    export_waveform_figure,
    export_prepost_figure,
)


class ExportDock(QDockWidget):
    """
    Dock widget for exporting plots, data, and reports.

    Features:
    - Export plot as image (PNG, PDF, SVG)
    - Generate comprehensive report plots
    - Export results (CSV, JSON)
    - Save/Load sessions
    - Export statistics (mean, median, std, percentiles)
    - Comparison figures with customizable rejected window display

    Signals:
        save_session_requested: Request to save session
        load_session_requested: Request to load session
    """

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
        self._connect_signals()

    def _create_ui(self):
        """Create dock UI with collapsible sections."""
        # Main widget
        widget = QWidget(self)
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(4)

        # Title
        title = QLabel("Export & Save")
        title.setFont(QFont("Arial", 10, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # === SECTIONS ===
        self.plot_section = PlotExportSection()
        main_layout.addWidget(self.plot_section)

        self.data_section = DataExportSection()
        main_layout.addWidget(self.data_section)

        self.stats_section = StatsExportSection()
        main_layout.addWidget(self.stats_section)

        self.comparison_section = ComparisonFiguresSection()
        main_layout.addWidget(self.comparison_section)

        self.report_section = ReportSection()
        main_layout.addWidget(self.report_section)

        self.session_section = SessionSection()
        main_layout.addWidget(self.session_section)

        main_layout.addStretch()

        # Wrap in scroll area
        scroll_area = QScrollArea()
        scroll_area.setWidget(widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.setWidget(scroll_area)

    def _connect_signals(self):
        """Connect section signals to handlers."""
        # Plot export
        self.plot_section.export_requested.connect(self._export_plot)

        # Data export
        self.data_section.export_requested.connect(self._export_data)

        # Statistics export
        self.stats_section.export_requested.connect(self._export_statistics)

        # Comparison figures
        self.comparison_section.export_comparison_requested.connect(
            self._export_comparison_figure
        )
        self.comparison_section.export_waveform_requested.connect(
            self._export_waveform_figure
        )
        self.comparison_section.export_prepost_requested.connect(
            self._export_prepost_figure
        )

        # Report
        self.report_section.generate_requested.connect(self._generate_report)

        # Session
        self.session_section.save_requested.connect(self._save_session)
        self.session_section.load_requested.connect(self._load_session)

    # =========================================================================
    # EXPORT HANDLERS
    # =========================================================================

    def _export_plot(self, format_type: str):
        """Export current plot as image."""
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
                fig = self.canvas_manager.fig
                fig.savefig(filename, dpi=300, bbox_inches='tight')
                QMessageBox.information(
                    self, "Export Successful",
                    f"Plot saved to:\n{filename}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self, "Export Failed",
                    f"Failed to export plot:\n{str(e)}"
                )

    def _export_data(self, format_type: str, options: dict):
        """Export results data (CSV or JSON)."""
        if not self.result:
            QMessageBox.warning(
                self, "No Data",
                "No HVSR results available to export."
            )
            return

        # Get filename
        filename, _ = QFileDialog.getSaveFileName(
            self,
            f"Export HVSR Results as {format_type.upper()}",
            f"hvsr_results.{format_type}",
            f"{format_type.upper()} Files (*.{format_type});;All Files (*)"
        )

        if filename:
            try:
                if format_type == 'csv':
                    export_csv(filename, self.result, options)
                elif format_type == 'json':
                    export_json(filename, self.result, self.windows, options)
                elif format_type == 'xlsx':
                    from .exporters.data_exporter import export_excel
                    export_excel(filename, self.result, self.windows, options)
                QMessageBox.information(
                    self, "Export Successful",
                    f"Data saved to:\n{filename}"
                )
            except Exception as e:
                import traceback
                QMessageBox.critical(
                    self, "Export Failed",
                    f"Failed to export:\n{str(e)}\n\n{traceback.format_exc()}"
                )

    def _export_statistics(self, options: dict):
        """Export statistics based on selected options."""
        if not self.result:
            QMessageBox.warning(
                self, "No Data",
                "No HVSR results available to export."
            )
            return

        # Add point count if custom (from data section)
        if not self.data_section.use_original_points_cb.isChecked():
            options['n_points'] = self.data_section.export_points_spin.value()

        # Get filename
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Statistics",
            "hvsr_statistics.csv",
            "CSV Files (*.csv);;All Files (*)"
        )

        if filename:
            try:
                export_statistics_csv(filename, self.result, self.windows, options)
                QMessageBox.information(
                    self, "Export Successful",
                    f"Statistics saved to:\n{filename}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self, "Export Failed",
                    f"Failed to export statistics:\n{str(e)}"
                )

    def _export_comparison_figure(self, options: dict):
        """Export Raw vs Adjusted HVSR comparison figure."""
        if not self.result:
            QMessageBox.warning(self, "No Data", "No HVSR results available.")
            return

        fmt = options.get('format', 'png')
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Raw vs Adjusted Comparison",
            f"hvsr_comparison.{fmt}",
            f"{fmt.upper()} Files (*.{fmt});;All Files (*)"
        )

        if not filename:
            return

        try:
            export_comparison_figure(filename, self.result, self.windows, options)
            QMessageBox.information(
                self, "Export Successful",
                f"Comparison figure saved to:\n{filename}"
            )
        except Exception as e:
            import traceback
            QMessageBox.critical(
                self, "Export Failed",
                f"Failed to export comparison figure:\n{str(e)}\n\n{traceback.format_exc()}"
            )

    def _export_waveform_figure(self, options: dict):
        """Export 3C waveform plot with rejection markers."""
        if not self.result:
            QMessageBox.warning(
                self, "No Data",
                "No HVSR results available. Please run HVSR processing first."
            )
            return
        if not self.data:
            QMessageBox.warning(
                self, "No Seismic Data",
                "Seismic data not available.\n\n"
                "This can happen when:\n"
                "- Loading a session without the original data file\n"
                "- The data was not properly saved with the session\n\n"
                "Please reload the original seismic data file."
            )
            return

        fmt = options.get('format', 'png')
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export 3C Waveform Plot",
            f"hvsr_waveforms.{fmt}",
            f"{fmt.upper()} Files (*.{fmt});;All Files (*)"
        )

        if not filename:
            return

        try:
            export_waveform_figure(filename, self.data, self.windows, options)
            dpi = options.get('dpi', 300)
            QMessageBox.information(
                self, "Export Successful",
                f"Waveform figure saved to:\n{filename}\n"
                f"Resolution: {dpi} DPI"
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Export Failed",
                f"Failed to export waveform figure:\n{str(e)}"
            )

    def _export_prepost_figure(self, options: dict):
        """Export comprehensive pre/post rejection figure."""
        if not self.result:
            QMessageBox.warning(
                self, "No Data",
                "No HVSR results available. Please run HVSR processing first."
            )
            return
        if not self.data:
            QMessageBox.warning(
                self, "No Seismic Data",
                "Seismic data not available.\n\n"
                "This can happen when:\n"
                "- Loading a session without the original data file\n"
                "- The data was not properly saved with the session\n\n"
                "Please reload the original seismic data file."
            )
            return

        fmt = options.get('format', 'png')
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Export Pre/Post Rejection Figure",
            f"hvsr_prepost_rejection.{fmt}",
            f"{fmt.upper()} Files (*.{fmt});;All Files (*)"
        )

        if not filename:
            return

        try:
            export_prepost_figure(
                filename, self.data, self.result, self.windows, options
            )
            dpi = options.get('dpi', 300)
            QMessageBox.information(
                self, "Export Successful",
                f"Pre/Post rejection figure saved to:\n{filename}\n"
                f"Resolution: {dpi} DPI"
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Export Failed",
                f"Failed to export pre/post rejection figure:\n{str(e)}"
            )

    def _generate_report(self):
        """Generate comprehensive report plots."""
        if not self.result:
            QMessageBox.warning(
                self, "No Data",
                "No HVSR results available for report generation."
            )
            return

        from hvsr_pro.gui.dialogs import ExportDialog

        dialog = ExportDialog(
            parent=self,
            result=self.result,
            windows=self.windows,
            data=self.data
        )
        dialog.exec_()

    def _save_session(self):
        """Save current session."""
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save Session",
            "hvsr_session.json",
            "JSON Files (*.json);;All Files (*)"
        )

        if filename:
            self.save_session_requested.emit(filename)

    def _load_session(self):
        """Load saved session."""
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Load Session",
            "",
            "JSON Files (*.json);;All Files (*)"
        )

        if filename:
            self.load_session_requested.emit(filename)

    # =========================================================================
    # PUBLIC INTERFACE
    # =========================================================================

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

        # Enable/disable sections based on availability
        has_result = result is not None
        has_data = data is not None

        self.plot_section.set_enabled(has_result)
        self.data_section.set_enabled(has_result)
        self.stats_section.set_enabled(has_result)
        self.comparison_section.set_enabled(has_result, has_data)
        self.report_section.set_enabled(has_result)
        self.session_section.set_save_enabled(has_result)

    def get_rejected_window_options(self) -> dict:
        """Get current rejected window display options.

        Returns:
            dict: Options for displaying rejected windows in comparison figures
        """
        return self.comparison_section.get_rejected_window_options()
