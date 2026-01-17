"""
Azimuthal Properties Dock
=========================

Main dock widget for azimuthal plot properties and export options.
Composes modular section components for a clean, maintainable architecture.
"""

from pathlib import Path
from typing import Optional

try:
    from PyQt5.QtWidgets import (
        QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QScrollArea, QFileDialog, QMessageBox,
        QProgressDialog, QDialog
    )
    from PyQt5.QtCore import Qt, pyqtSignal
    from PyQt5.QtGui import QFont
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


if HAS_PYQT5:
    from .sections import (
        ThemeSection,
        FigureSection,
        LegendSection,
        FontSection,
        ExportSection,
    )
    from .dialogs import ExportReportDialog
    from .exporters import (
        write_csv, write_json,
        export_plot_to_file, get_format_info,
        ReportGenerator
    )


if HAS_PYQT5:
    class AzimuthalDock(QDockWidget):
        """
        Dock widget for azimuthal plot properties and export options.
        
        Features:
        - Theme/colormap selection (ThemeSection)
        - Figure type selector (FigureSection)
        - Legend position/size controls (LegendSection)
        - Font size controls (FontSection)
        - Export options (ExportSection)
        - Comprehensive export report
        
        Signals:
            plot_options_changed: Emitted when any plot option changes
            export_requested: Emitted when export is requested (format, options)
        """
        
        plot_options_changed = pyqtSignal(dict)
        export_requested = pyqtSignal(str, dict)
        
        def __init__(self, parent=None):
            super().__init__("Azimuthal Properties", parent)
            self.setObjectName("AzimuthalPropertiesDock")
            
            # Set dock features for proper resizing
            self.setFeatures(
                QDockWidget.DockWidgetMovable |
                QDockWidget.DockWidgetFloatable |
                QDockWidget.DockWidgetClosable
            )
            self.setMinimumWidth(180)
            self.setMaximumWidth(400)
            
            # Result and figure references
            self.result = None
            self.figure = None
            self._parent = parent
            
            self._create_ui()
            self._connect_signals()
        
        def _create_ui(self):
            """Create the dock UI using section components."""
            widget = QWidget()
            main_layout = QVBoxLayout(widget)
            main_layout.setContentsMargins(5, 5, 5, 5)
            main_layout.setSpacing(4)
            
            # Title
            title = QLabel("Azimuthal Plot Options")
            title.setFont(QFont("Arial", 10, QFont.Bold))
            title.setAlignment(Qt.AlignCenter)
            main_layout.addWidget(title)
            
            # Add sections
            self.theme_section = ThemeSection()
            main_layout.addWidget(self.theme_section)
            
            self.figure_section = FigureSection()
            main_layout.addWidget(self.figure_section)
            
            self.legend_section = LegendSection()
            main_layout.addWidget(self.legend_section)
            
            self.font_section = FontSection()
            main_layout.addWidget(self.font_section)
            
            self.export_section = ExportSection()
            main_layout.addWidget(self.export_section)
            
            # Apply button
            apply_container = QWidget()
            apply_layout = QHBoxLayout(apply_container)
            apply_layout.setContentsMargins(5, 10, 5, 5)
            
            self.apply_btn = QPushButton("Apply Changes")
            self.apply_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    font-weight: bold;
                    padding: 8px 16px;
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
                QPushButton:pressed {
                    background-color: #3d8b40;
                }
            """)
            self.apply_btn.clicked.connect(self._on_apply_clicked)
            apply_layout.addWidget(self.apply_btn)
            main_layout.addWidget(apply_container)
            
            main_layout.addStretch()
            
            # Wrap in scroll area
            scroll = QScrollArea()
            scroll.setWidget(widget)
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            
            self.setWidget(scroll)
        
        def _connect_signals(self):
            """Connect section signals to handlers."""
            # Export section signals
            self.export_section.export_plot_requested.connect(self._export_plot)
            self.export_section.export_data_requested.connect(self._export_data)
            self.export_section.export_report_requested.connect(self._export_report)
        
        def _on_apply_clicked(self):
            """Handle Apply button click."""
            options = self.get_options()
            self.plot_options_changed.emit(options)
        
        def get_options(self) -> dict:
            """Get current plot options as dictionary."""
            return {
                'cmap': self.theme_section.get_cmap(),
                'curve_cmap': self.theme_section.get_curve_cmap(),
                'figure_type': self.figure_section.get_figure_type(),
                'show_panel_labels': self.figure_section.get_show_panel_labels(),
                'show_peaks': self.figure_section.get_show_peaks(),
                'show_individual_curves': self.figure_section.get_show_individual_curves(),
                'legend_loc': self.legend_section.get_position(),
                'legend_fontsize': self.legend_section.get_fontsize(),
                'title_fontsize': self.font_section.get_title_fontsize(),
                'axis_fontsize': self.font_section.get_axis_fontsize(),
                'tick_fontsize': self.font_section.get_tick_fontsize(),
                'dpi': self.export_section.get_dpi(),
            }
        
        def set_result(self, result, figure=None):
            """Set the azimuthal result for export."""
            self.result = result
            self.figure = figure
            
            # Enable/disable export buttons
            has_result = result is not None
            self.export_section.set_enabled(has_result)
        
        def _get_current_figure(self):
            """Get current figure from azimuthal tab if available."""
            if self._parent and hasattr(self._parent, 'azimuthal_tab'):
                tab = self._parent.azimuthal_tab
                if hasattr(tab, 'figure') and tab.figure is not None:
                    return tab.figure
            return self.figure
        
        def _get_current_result(self):
            """Get current result from azimuthal tab if not set directly."""
            if self.result is not None:
                return self.result
            # Try to get from azimuthal tab
            if self._parent and hasattr(self._parent, 'azimuthal_tab'):
                tab = self._parent.azimuthal_tab
                if hasattr(tab, 'result') and tab.result is not None:
                    return tab.result
            return None
        
        def _export_plot(self, format_type: str):
            """Export plot to file."""
            result = self._get_current_result()
            if not result:
                QMessageBox.warning(
                    self, "No Results",
                    "No azimuthal processing results available.\n\n"
                    "Please run azimuthal processing first."
                )
                return
            
            fig = self._get_current_figure()
            if fig is None:
                QMessageBox.warning(
                    self, "No Plot",
                    "No azimuthal plot available.\n\n"
                    "Please click 'Apply Changes' to generate the plot first."
                )
                return
            
            desc, pattern = get_format_info(format_type)
            
            filename, _ = QFileDialog.getSaveFileName(
                self,
                f"Export Azimuthal Plot as {desc}",
                f"azimuthal_hvsr.{format_type}",
                f"{desc} ({pattern});;All Files (*)"
            )
            
            if filename:
                try:
                    export_plot_to_file(
                        fig, filename,
                        dpi=self.export_section.get_dpi()
                    )
                    QMessageBox.information(
                        self, "Export Successful",
                        f"Plot saved to:\n{filename}"
                    )
                except Exception as e:
                    QMessageBox.critical(
                        self, "Export Failed",
                        f"Failed to export plot:\n{str(e)}"
                    )
        
        def _export_data(self, format_type: str):
            """Export data to file."""
            result = self._get_current_result()
            if not result:
                QMessageBox.warning(self, "No Data", "No azimuthal results available.")
                return
            
            if format_type == "csv":
                filename, _ = QFileDialog.getSaveFileName(
                    self,
                    "Export Azimuthal Data",
                    "azimuthal_hvsr_data.csv",
                    "CSV Files (*.csv);;All Files (*)"
                )
                if filename:
                    try:
                        write_csv(filename, result)
                        QMessageBox.information(
                            self, "Export Successful",
                            f"Data saved to:\n{filename}"
                        )
                    except Exception as e:
                        QMessageBox.critical(
                            self, "Export Failed",
                            f"Failed to export data:\n{str(e)}"
                        )
            
            elif format_type == "json":
                filename, _ = QFileDialog.getSaveFileName(
                    self,
                    "Export Azimuthal Data",
                    "azimuthal_hvsr_data.json",
                    "JSON Files (*.json);;All Files (*)"
                )
                if filename:
                    try:
                        write_json(filename, result)
                        QMessageBox.information(
                            self, "Export Successful",
                            f"Data saved to:\n{filename}"
                        )
                    except Exception as e:
                        import traceback
                        QMessageBox.critical(
                            self, "Export Failed",
                            f"Failed to export data:\n{str(e)}\n\n{traceback.format_exc()}"
                        )
        
        def _export_report(self):
            """Export comprehensive report with all figures and data."""
            result = self._get_current_result()
            if not result:
                QMessageBox.warning(
                    self, "No Results",
                    "No azimuthal processing results available.\n\n"
                    "Please run azimuthal processing first."
                )
                return
            
            # Show selection dialog
            dialog = ExportReportDialog(self)
            if dialog.exec_() != QDialog.Accepted:
                return
            
            selections = dialog.get_selections()
            
            # Select output directory
            output_dir = QFileDialog.getExistingDirectory(
                self,
                "Select Output Directory for Report",
                "",
                QFileDialog.ShowDirsOnly
            )
            
            if not output_dir:
                return
            
            # Create progress dialog
            n_total = sum(selections['figures'].values()) + sum(selections['data'].values())
            progress = QProgressDialog("Generating report...", "Cancel", 0, n_total, self)
            progress.setWindowTitle("Export Report")
            progress.setWindowModality(Qt.WindowModal)
            progress.show()
            
            def update_progress(label: str, step: int):
                if progress.wasCanceled():
                    raise InterruptedError("Export cancelled")
                progress.setLabelText(label)
                progress.setValue(step)
            
            try:
                generator = ReportGenerator(result, self.get_options())
                created_files = generator.generate(output_dir, selections, update_progress)
                
                progress.close()
                
                # Show summary
                summary = f"Report exported successfully!\n\nFiles created ({len(created_files)}):\n"
                for f in created_files[:10]:
                    summary += f"  - {Path(f).name}\n"
                if len(created_files) > 10:
                    summary += f"  ... and {len(created_files) - 10} more\n"
                summary += f"\nLocation:\n{output_dir}"
                
                QMessageBox.information(self, "Export Complete", summary)
                
            except InterruptedError:
                progress.close()
                QMessageBox.information(self, "Cancelled", "Export was cancelled.")
            except Exception as e:
                progress.close()
                import traceback
                QMessageBox.critical(
                    self, "Export Failed",
                    f"Failed to generate report:\n{str(e)}\n\n{traceback.format_exc()}"
                )


else:
    class AzimuthalDock:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass


# Backward compatibility alias
AzimuthalPropertiesDock = AzimuthalDock
