"""
Azimuthal Properties Dock
=========================

Properties and export panel for azimuthal HVSR analysis tab.
Includes comprehensive export report functionality.
"""

import os
from pathlib import Path
from typing import Optional, Dict, Any

try:
    from PyQt5.QtWidgets import (
        QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QComboBox, QSpinBox, QCheckBox,
        QScrollArea, QFileDialog, QMessageBox, QDoubleSpinBox,
        QGroupBox, QGridLayout, QProgressDialog, QDialog,
        QDialogButtonBox
    )
    from PyQt5.QtCore import Qt, pyqtSignal
    from PyQt5.QtGui import QFont
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False

from hvsr_pro.gui.components import CollapsibleSection


if HAS_PYQT5:
    
    class ExportReportDialog(QDialog):
        """Dialog for selecting which outputs to include in the export report."""
        
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("Export Azimuthal Report")
            self.setModal(True)
            self.setMinimumWidth(400)
            
            self._create_ui()
        
        def _create_ui(self):
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
        
        def _select_all(self):
            """Select all checkboxes."""
            for cb in [self.cb_summary, self.cb_3d, self.cb_2d, self.cb_polar,
                       self.cb_curves, self.cb_csv_mean, self.cb_csv_individual,
                       self.cb_json, self.cb_peaks]:
                cb.setChecked(True)
        
        def _select_none(self):
            """Deselect all checkboxes."""
            for cb in [self.cb_summary, self.cb_3d, self.cb_2d, self.cb_polar,
                       self.cb_curves, self.cb_csv_mean, self.cb_csv_individual,
                       self.cb_json, self.cb_peaks]:
                cb.setChecked(False)
        
        def get_selections(self) -> Dict[str, Any]:
            """Get selected options."""
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
    
    
    class AzimuthalPropertiesDock(QDockWidget):
        """
        Dock widget for azimuthal plot properties and export options.
        
        Features:
        - Theme/colormap selection
        - Figure type selector
        - Legend position/size controls
        - Font size controls
        - Export options (PNG, PDF, SVG, CSV, JSON)
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
            # Allow dock to be resized smaller
            self.setMinimumWidth(180)
            self.setMaximumWidth(400)
            
            # Result reference
            self.result = None
            self.figure = None
            self._parent = parent  # Store parent for accessing azimuthal tab
            
            self._create_ui()
        
        def _create_ui(self):
            """Create the dock UI."""
            widget = QWidget()
            main_layout = QVBoxLayout(widget)
            main_layout.setContentsMargins(5, 5, 5, 5)
            main_layout.setSpacing(4)
            
            # Title
            title = QLabel("Azimuthal Plot Options")
            title.setFont(QFont("Arial", 10, QFont.Bold))
            title.setAlignment(Qt.AlignCenter)
            main_layout.addWidget(title)
            
            # === THEME SECTION ===
            theme_section = self._create_theme_section()
            main_layout.addWidget(theme_section)
            
            # === FIGURE TYPE SECTION ===
            figure_section = self._create_figure_section()
            main_layout.addWidget(figure_section)
            
            # === LEGEND SECTION ===
            legend_section = self._create_legend_section()
            main_layout.addWidget(legend_section)
            
            # === FONT SECTION ===
            font_section = self._create_font_section()
            main_layout.addWidget(font_section)
            
            # === EXPORT SECTION ===
            export_section = self._create_export_section()
            main_layout.addWidget(export_section)
            
            # === APPLY BUTTON ===
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
        
        def _create_theme_section(self) -> CollapsibleSection:
            """Create theme/colormap section."""
            section = CollapsibleSection("Theme & Colors")
            
            # Colormap selector
            cmap_container = QWidget()
            cmap_layout = QHBoxLayout(cmap_container)
            cmap_layout.setContentsMargins(0, 0, 0, 0)
            cmap_layout.addWidget(QLabel("Colormap:"))
            self.cmap_combo = QComboBox()
            self.cmap_combo.addItems([
                "plasma", "viridis", "inferno", "magma", 
                "jet", "turbo", "coolwarm", "RdBu_r", "seismic"
            ])
            self.cmap_combo.setToolTip("Color scheme for surface and contour plots")
            cmap_layout.addWidget(self.cmap_combo)
            section.add_widget(cmap_container)
            
            # Curve colormap (for individual curves)
            curve_cmap_container = QWidget()
            curve_cmap_layout = QHBoxLayout(curve_cmap_container)
            curve_cmap_layout.setContentsMargins(0, 0, 0, 0)
            curve_cmap_layout.addWidget(QLabel("Curves:"))
            self.curve_cmap_combo = QComboBox()
            self.curve_cmap_combo.addItems([
                "viridis", "plasma", "rainbow", "tab20", "hsv"
            ])
            self.curve_cmap_combo.setToolTip("Color scheme for individual HVSR curves")
            curve_cmap_layout.addWidget(self.curve_cmap_combo)
            section.add_widget(curve_cmap_container)
            
            return section
        
        def _create_figure_section(self) -> CollapsibleSection:
            """Create figure type section."""
            section = CollapsibleSection("Figure Type")
            
            # Figure type selector
            type_container = QWidget()
            type_layout = QHBoxLayout(type_container)
            type_layout.setContentsMargins(0, 0, 0, 0)
            type_layout.addWidget(QLabel("View:"))
            self.figure_type_combo = QComboBox()
            self.figure_type_combo.addItem("Summary (3D + 2D + Curves)", "summary")
            self.figure_type_combo.addItem("3D Surface Only", "3d")
            self.figure_type_combo.addItem("2D Contour Only", "2d")
            self.figure_type_combo.addItem("Polar Plot", "polar")
            self.figure_type_combo.addItem("Individual Curves", "curves")
            type_layout.addWidget(self.figure_type_combo)
            section.add_widget(type_container)
            
            # Show panel labels
            self.show_labels_cb = QCheckBox("Show panel labels (a, b, c)")
            self.show_labels_cb.setChecked(True)
            section.add_widget(self.show_labels_cb)
            
            # Show peak markers
            self.show_peaks_cb = QCheckBox("Show peak markers")
            self.show_peaks_cb.setChecked(True)
            section.add_widget(self.show_peaks_cb)
            
            # Show individual curves
            self.show_individual_cb = QCheckBox("Show individual curves")
            self.show_individual_cb.setChecked(True)
            section.add_widget(self.show_individual_cb)
            
            return section
        
        def _create_legend_section(self) -> CollapsibleSection:
            """Create legend options section."""
            section = CollapsibleSection("Legend")
            
            # Legend position
            pos_container = QWidget()
            pos_layout = QHBoxLayout(pos_container)
            pos_layout.setContentsMargins(0, 0, 0, 0)
            pos_layout.addWidget(QLabel("Position:"))
            self.legend_pos_combo = QComboBox()
            self.legend_pos_combo.addItem("Outside Right", "outside_right")
            self.legend_pos_combo.addItem("Outside Bottom", "outside_bottom")
            self.legend_pos_combo.addItem("Upper Right", "upper right")
            self.legend_pos_combo.addItem("Upper Left", "upper left")
            self.legend_pos_combo.addItem("Lower Right", "lower right")
            self.legend_pos_combo.addItem("Lower Left", "lower left")
            self.legend_pos_combo.addItem("None (Hide)", "none")
            pos_layout.addWidget(self.legend_pos_combo)
            section.add_widget(pos_container)
            
            # Legend font size
            size_container = QWidget()
            size_layout = QHBoxLayout(size_container)
            size_layout.setContentsMargins(0, 0, 0, 0)
            size_layout.addWidget(QLabel("Font Size:"))
            self.legend_size_spin = QSpinBox()
            self.legend_size_spin.setRange(6, 14)
            self.legend_size_spin.setValue(8)
            size_layout.addWidget(self.legend_size_spin)
            section.add_widget(size_container)
            
            return section
        
        def _create_font_section(self) -> CollapsibleSection:
            """Create font options section."""
            section = CollapsibleSection("Fonts")
            section.set_collapsed(True)  # Start collapsed
            
            # Title font size
            title_container = QWidget()
            title_layout = QHBoxLayout(title_container)
            title_layout.setContentsMargins(0, 0, 0, 0)
            title_layout.addWidget(QLabel("Title:"))
            self.title_size_spin = QSpinBox()
            self.title_size_spin.setRange(10, 20)
            self.title_size_spin.setValue(14)
            title_layout.addWidget(self.title_size_spin)
            section.add_widget(title_container)
            
            # Axis label font size
            axis_container = QWidget()
            axis_layout = QHBoxLayout(axis_container)
            axis_layout.setContentsMargins(0, 0, 0, 0)
            axis_layout.addWidget(QLabel("Axis Labels:"))
            self.axis_size_spin = QSpinBox()
            self.axis_size_spin.setRange(8, 14)
            self.axis_size_spin.setValue(10)
            axis_layout.addWidget(self.axis_size_spin)
            section.add_widget(axis_container)
            
            # Tick label font size
            tick_container = QWidget()
            tick_layout = QHBoxLayout(tick_container)
            tick_layout.setContentsMargins(0, 0, 0, 0)
            tick_layout.addWidget(QLabel("Tick Labels:"))
            self.tick_size_spin = QSpinBox()
            self.tick_size_spin.setRange(6, 12)
            self.tick_size_spin.setValue(8)
            tick_layout.addWidget(self.tick_size_spin)
            section.add_widget(tick_container)
            
            return section
        
        def _create_export_section(self) -> CollapsibleSection:
            """Create export section."""
            section = CollapsibleSection("Export")
            
            # DPI setting
            dpi_container = QWidget()
            dpi_layout = QHBoxLayout(dpi_container)
            dpi_layout.setContentsMargins(0, 0, 0, 0)
            dpi_layout.addWidget(QLabel("DPI:"))
            self.dpi_spin = QSpinBox()
            self.dpi_spin.setRange(72, 1200)
            self.dpi_spin.setValue(300)
            self.dpi_spin.setSingleStep(50)
            self.dpi_spin.setToolTip("Figure resolution (72-1200 DPI)")
            dpi_layout.addWidget(self.dpi_spin)
            section.add_widget(dpi_container)
            
            # Export plot buttons
            btn_container = QWidget()
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(0, 0, 0, 0)
            
            self.export_png_btn = QPushButton("PNG")
            self.export_png_btn.clicked.connect(lambda: self._export_plot("png"))
            btn_layout.addWidget(self.export_png_btn)
            
            self.export_pdf_btn = QPushButton("PDF")
            self.export_pdf_btn.clicked.connect(lambda: self._export_plot("pdf"))
            btn_layout.addWidget(self.export_pdf_btn)
            
            self.export_svg_btn = QPushButton("SVG")
            self.export_svg_btn.clicked.connect(lambda: self._export_plot("svg"))
            btn_layout.addWidget(self.export_svg_btn)
            
            section.add_widget(btn_container)
            
            # Export data buttons
            self.export_csv_btn = QPushButton("Export Data (CSV)")
            self.export_csv_btn.clicked.connect(lambda: self._export_data("csv"))
            section.add_widget(self.export_csv_btn)
            
            self.export_json_btn = QPushButton("Export Data (JSON)")
            self.export_json_btn.clicked.connect(lambda: self._export_data("json"))
            section.add_widget(self.export_json_btn)
            
            # Export Report button (comprehensive)
            self.export_report_btn = QPushButton("Export Full Report...")
            self.export_report_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    font-weight: bold;
                    padding: 6px;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
            """)
            self.export_report_btn.clicked.connect(self._export_report)
            self.export_report_btn.setToolTip("Export comprehensive report with all figures and data")
            section.add_widget(self.export_report_btn)
            
            return section
        
        def _on_apply_clicked(self):
            """Handle Apply button click - emit signal to update plot."""
            options = self.get_options()
            self.plot_options_changed.emit(options)
        
        def get_options(self) -> dict:
            """Get current plot options as dictionary."""
            return {
                'cmap': self.cmap_combo.currentText(),
                'curve_cmap': self.curve_cmap_combo.currentText(),
                'figure_type': self.figure_type_combo.currentData(),
                'show_panel_labels': self.show_labels_cb.isChecked(),
                'show_peaks': self.show_peaks_cb.isChecked(),
                'show_individual_curves': self.show_individual_cb.isChecked(),
                'legend_loc': self.legend_pos_combo.currentData(),
                'legend_fontsize': self.legend_size_spin.value(),
                'title_fontsize': self.title_size_spin.value(),
                'axis_fontsize': self.axis_size_spin.value(),
                'tick_fontsize': self.tick_size_spin.value(),
                'dpi': self.dpi_spin.value(),
            }
        
        def set_result(self, result, figure=None):
            """Set the azimuthal result for export."""
            self.result = result
            self.figure = figure
            
            # Enable/disable export buttons
            has_result = result is not None
            self.export_png_btn.setEnabled(has_result)
            self.export_pdf_btn.setEnabled(has_result)
            self.export_svg_btn.setEnabled(has_result)
            self.export_csv_btn.setEnabled(has_result)
            self.export_json_btn.setEnabled(has_result)
            self.export_report_btn.setEnabled(has_result)
        
        def _get_current_figure(self):
            """Get current figure from azimuthal tab if available."""
            # Try to get figure from parent's azimuthal tab
            if self._parent and hasattr(self._parent, 'azimuthal_tab'):
                tab = self._parent.azimuthal_tab
                if hasattr(tab, 'figure') and tab.figure is not None:
                    return tab.figure
            return self.figure
        
        def _export_plot(self, format_type: str):
            """Export plot to file."""
            if not self.result:
                QMessageBox.warning(
                    self, "No Results", 
                    "No azimuthal processing results available.\n\n"
                    "Please run azimuthal processing first."
                )
                return
            
            # Get figure from azimuthal tab
            fig = self._get_current_figure()
            if fig is None:
                QMessageBox.warning(
                    self, "No Plot", 
                    "No azimuthal plot available.\n\n"
                    "Please click 'Apply Changes' to generate the plot first."
                )
                return
            
            ext_map = {
                'png': ('PNG Image', '*.png'),
                'pdf': ('PDF Document', '*.pdf'),
                'svg': ('SVG Vector', '*.svg')
            }
            
            desc, pattern = ext_map.get(format_type, ('Image', '*.*'))
            
            filename, _ = QFileDialog.getSaveFileName(
                self,
                f"Export Azimuthal Plot as {desc}",
                f"azimuthal_hvsr.{format_type}",
                f"{desc} ({pattern});;All Files (*)"
            )
            
            if filename:
                try:
                    fig.savefig(
                        filename, 
                        dpi=self.dpi_spin.value(),
                        bbox_inches='tight',
                        facecolor='white'
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
            if not self.result:
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
                    self._write_csv(filename)
            
            elif format_type == "json":
                filename, _ = QFileDialog.getSaveFileName(
                    self,
                    "Export Azimuthal Data",
                    "azimuthal_hvsr_data.json",
                    "JSON Files (*.json);;All Files (*)"
                )
                if filename:
                    self._write_json(filename)
        
        def _write_csv(self, filename: str):
            """Write data to CSV file."""
            import csv
            import numpy as np
            
            try:
                with open(filename, 'w', newline='') as f:
                    writer = csv.writer(f)
                    
                    # Header
                    header = ['Frequency (Hz)'] + [
                        f'Azimuth {az:.0f} deg' for az in self.result.azimuths
                    ]
                    writer.writerow(header)
                    
                    # Data rows
                    for i, freq in enumerate(self.result.frequencies):
                        row = [freq]
                        for j in range(len(self.result.azimuths)):
                            val = self.result.mean_curves_per_azimuth[j, i]
                            row.append(val if not np.isnan(val) else '')
                        writer.writerow(row)
                
                QMessageBox.information(
                    self, "Export Successful",
                    f"Data saved to:\n{filename}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self, "Export Failed",
                    f"Failed to export data:\n{str(e)}"
                )
        
        def _write_json(self, filename: str):
            """Write data to JSON file."""
            import json
            import numpy as np
            
            try:
                # Convert numpy arrays to lists, handling NaN values
                def to_list(arr):
                    if arr is None:
                        return None
                    return [[None if np.isnan(x) else float(x) for x in row] 
                            if hasattr(row, '__iter__') else (None if np.isnan(row) else float(row))
                            for row in arr]
                
                data = {
                    'frequencies': self.result.frequencies.tolist(),
                    'azimuths': self.result.azimuths.tolist(),
                    'mean_curves_per_azimuth': to_list(self.result.mean_curves_per_azimuth),
                    'std_curves_per_azimuth': to_list(self.result.std_curves_per_azimuth) if self.result.std_curves_per_azimuth is not None else None,
                    'metadata': {
                        'n_azimuths': len(self.result.azimuths),
                        'n_frequencies': len(self.result.frequencies),
                        'processing_info': self.result.metadata if hasattr(self.result, 'metadata') else {}
                    }
                }
                
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)
                
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
            if not self.result:
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
            
            try:
                created_files = self._generate_report(output_dir, selections, progress)
                
                progress.close()
                
                # Show summary
                summary = f"Report exported successfully!\n\nFiles created ({len(created_files)}):\n"
                for f in created_files[:10]:  # Show first 10
                    summary += f"  • {Path(f).name}\n"
                if len(created_files) > 10:
                    summary += f"  ... and {len(created_files) - 10} more\n"
                summary += f"\nLocation:\n{output_dir}"
                
                QMessageBox.information(self, "Export Complete", summary)
                
            except Exception as e:
                progress.close()
                import traceback
                QMessageBox.critical(
                    self, "Export Failed",
                    f"Failed to generate report:\n{str(e)}\n\n{traceback.format_exc()}"
                )
        
        def _generate_report(self, output_dir: str, selections: dict, progress) -> list:
            """Generate report files."""
            import matplotlib.pyplot as plt
            import numpy as np
            
            from hvsr_pro.processing.azimuthal import (
                plot_azimuthal_contour_2d,
                plot_azimuthal_contour_3d,
                plot_azimuthal_summary
            )
            
            created_files = []
            current_step = 0
            options = self.get_options()
            dpi = selections['dpi']
            fmt = selections['format']
            formats = ['png', 'pdf', 'svg'] if fmt == 'all formats' else [fmt]
            
            # === GENERATE FIGURES ===
            figures_sel = selections['figures']
            
            if figures_sel.get('summary'):
                progress.setLabelText("Generating summary plot...")
                for ext in formats:
                    if progress.wasCanceled():
                        return created_files
                    
                    fig, _ = plot_azimuthal_summary(
                        self.result,
                        figsize=(12, 10),
                        dpi=dpi,
                        cmap=options['cmap'],
                        legend_loc=options['legend_loc'],
                        plot_mean_curve_peak_by_azimuth=options['show_peaks'],
                        plot_individual_curves=options['show_individual_curves'],
                        show_panel_labels=options['show_panel_labels'],
                        title_fontsize=options['title_fontsize'],
                        axis_fontsize=options['axis_fontsize'],
                        tick_fontsize=options['tick_fontsize'],
                        legend_fontsize=options['legend_fontsize']
                    )
                    filepath = os.path.join(output_dir, f"azimuthal_summary.{ext}")
                    fig.savefig(filepath, dpi=dpi, bbox_inches='tight', facecolor='white')
                    plt.close(fig)
                    created_files.append(filepath)
                
                current_step += 1
                progress.setValue(current_step)
            
            if figures_sel.get('3d'):
                progress.setLabelText("Generating 3D surface plot...")
                for ext in formats:
                    if progress.wasCanceled():
                        return created_files
                    
                    fig = plt.figure(figsize=(10, 8), dpi=dpi)
                    ax = fig.add_subplot(111, projection='3d')
                    plot_azimuthal_contour_3d(
                        self.result,
                        ax=ax,
                        cmap=options['cmap'],
                        plot_mean_curve_peak_by_azimuth=options['show_peaks']
                    )
                    ax.set_xlabel("Frequency (Hz)", fontsize=options['axis_fontsize'])
                    ax.set_ylabel("Azimuth (deg)", fontsize=options['axis_fontsize'])
                    ax.set_zlabel("HVSR Amplitude", fontsize=options['axis_fontsize'])
                    fig.suptitle("3D Azimuthal HVSR", fontsize=options['title_fontsize'], fontweight='bold')
                    
                    filepath = os.path.join(output_dir, f"azimuthal_3d.{ext}")
                    fig.savefig(filepath, dpi=dpi, bbox_inches='tight', facecolor='white')
                    plt.close(fig)
                    created_files.append(filepath)
                
                current_step += 1
                progress.setValue(current_step)
            
            if figures_sel.get('2d'):
                progress.setLabelText("Generating 2D contour plot...")
                for ext in formats:
                    if progress.wasCanceled():
                        return created_files
                    
                    fig, ax = plt.subplots(figsize=(10, 6), dpi=dpi)
                    plot_azimuthal_contour_2d(
                        self.result,
                        ax=ax,
                        cmap=options['cmap'],
                        plot_mean_curve_peak_by_azimuth=options['show_peaks']
                    )
                    ax.set_xlabel("Frequency (Hz)", fontsize=options['axis_fontsize'])
                    ax.set_ylabel("Azimuth (deg)", fontsize=options['axis_fontsize'])
                    fig.suptitle("2D Azimuthal HVSR Contour", fontsize=options['title_fontsize'], fontweight='bold')
                    
                    filepath = os.path.join(output_dir, f"azimuthal_2d.{ext}")
                    fig.savefig(filepath, dpi=dpi, bbox_inches='tight', facecolor='white')
                    plt.close(fig)
                    created_files.append(filepath)
                
                current_step += 1
                progress.setValue(current_step)
            
            if figures_sel.get('polar'):
                progress.setLabelText("Generating polar plot...")
                try:
                    from hvsr_pro.processing.azimuthal import plot_azimuthal_polar
                    for ext in formats:
                        if progress.wasCanceled():
                            return created_files
                        
                        fig = plt.figure(figsize=(8, 8), dpi=dpi)
                        ax = fig.add_subplot(111, projection='polar')
                        plot_azimuthal_polar(
                            self.result,
                            ax=ax,
                            cmap=options['cmap'],
                            title_fontsize=options['title_fontsize'],
                            axis_fontsize=options['axis_fontsize'],
                            tick_fontsize=options['tick_fontsize']
                        )
                        
                        filepath = os.path.join(output_dir, f"azimuthal_polar.{ext}")
                        fig.savefig(filepath, dpi=dpi, bbox_inches='tight', facecolor='white')
                        plt.close(fig)
                        created_files.append(filepath)
                except Exception as e:
                    print(f"Warning: Could not generate polar plot: {e}")
                
                current_step += 1
                progress.setValue(current_step)
            
            if figures_sel.get('curves'):
                progress.setLabelText("Generating individual curves plot...")
                try:
                    from hvsr_pro.processing.azimuthal import plot_azimuthal_curves
                    for ext in formats:
                        if progress.wasCanceled():
                            return created_files
                        
                        fig, ax = plt.subplots(figsize=(10, 6), dpi=dpi)
                        plot_azimuthal_curves(
                            self.result,
                            ax=ax,
                            cmap=options['cmap'],
                            title_fontsize=options['title_fontsize'],
                            axis_fontsize=options['axis_fontsize'],
                            tick_fontsize=options['tick_fontsize'],
                            legend_fontsize=options['legend_fontsize']
                        )
                        
                        filepath = os.path.join(output_dir, f"azimuthal_curves.{ext}")
                        fig.savefig(filepath, dpi=dpi, bbox_inches='tight', facecolor='white')
                        plt.close(fig)
                        created_files.append(filepath)
                except Exception as e:
                    print(f"Warning: Could not generate curves plot: {e}")
                
                current_step += 1
                progress.setValue(current_step)
            
            # === GENERATE DATA FILES ===
            data_sel = selections['data']
            
            if data_sel.get('csv_mean'):
                progress.setLabelText("Exporting mean curves CSV...")
                filepath = os.path.join(output_dir, "azimuthal_mean_curves.csv")
                self._write_csv_to_file(filepath)
                created_files.append(filepath)
                current_step += 1
                progress.setValue(current_step)
            
            if data_sel.get('csv_individual'):
                progress.setLabelText("Exporting individual curves CSV...")
                filepath = os.path.join(output_dir, "azimuthal_individual_curves.csv")
                self._write_individual_csv(filepath)
                created_files.append(filepath)
                current_step += 1
                progress.setValue(current_step)
            
            if data_sel.get('json'):
                progress.setLabelText("Exporting JSON data...")
                filepath = os.path.join(output_dir, "azimuthal_results.json")
                self._write_json_to_file(filepath)
                created_files.append(filepath)
                current_step += 1
                progress.setValue(current_step)
            
            if data_sel.get('peaks'):
                progress.setLabelText("Exporting peak frequencies...")
                filepath = os.path.join(output_dir, "azimuthal_peak_frequencies.csv")
                self._write_peaks_csv(filepath)
                created_files.append(filepath)
                current_step += 1
                progress.setValue(current_step)
            
            return created_files
        
        def _write_csv_to_file(self, filename: str):
            """Write mean curves CSV without dialog."""
            import csv
            import numpy as np
            
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                header = ['Frequency (Hz)'] + [f'Azimuth {az:.0f} deg' for az in self.result.azimuths]
                writer.writerow(header)
                
                for i, freq in enumerate(self.result.frequencies):
                    row = [freq]
                    for j in range(len(self.result.azimuths)):
                        val = self.result.mean_curves_per_azimuth[j, i]
                        row.append(val if not np.isnan(val) else '')
                    writer.writerow(row)
        
        def _write_individual_csv(self, filename: str):
            """Write individual window curves CSV."""
            import csv
            import numpy as np
            
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                
                # Header: Frequency, then each azimuth/window combination
                header = ['Frequency (Hz)']
                if self.result.hvsr_per_azimuth is not None:
                    n_windows = self.result.hvsr_per_azimuth.shape[1]
                    for az in self.result.azimuths:
                        for w in range(n_windows):
                            header.append(f'Az{az:.0f}_W{w+1}')
                writer.writerow(header)
                
                # Data
                if self.result.hvsr_per_azimuth is not None:
                    for i, freq in enumerate(self.result.frequencies):
                        row = [freq]
                        for j in range(len(self.result.azimuths)):
                            for w in range(n_windows):
                                val = self.result.hvsr_per_azimuth[j, w, i]
                                row.append(val if not np.isnan(val) else '')
                        writer.writerow(row)
        
        def _write_json_to_file(self, filename: str):
            """Write JSON without dialog."""
            import json
            import numpy as np
            
            def to_list(arr):
                if arr is None:
                    return None
                result = []
                for row in arr:
                    if hasattr(row, '__iter__'):
                        result.append([None if np.isnan(x) else float(x) for x in row])
                    else:
                        result.append(None if np.isnan(row) else float(row))
                return result
            
            data = {
                'frequencies': self.result.frequencies.tolist(),
                'azimuths': self.result.azimuths.tolist(),
                'mean_curves_per_azimuth': to_list(self.result.mean_curves_per_azimuth),
                'std_curves_per_azimuth': to_list(self.result.std_curves_per_azimuth) if self.result.std_curves_per_azimuth is not None else None,
                'metadata': self.result.metadata if hasattr(self.result, 'metadata') else {}
            }
            
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
        
        def _write_peaks_csv(self, filename: str):
            """Write peak frequencies per azimuth to CSV."""
            import csv
            
            peak_freqs, peak_amps = self.result.mean_curve_peak_by_azimuth()
            
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Azimuth (deg)', 'Peak Frequency (Hz)', 'Peak Amplitude'])
                
                for i, az in enumerate(self.result.azimuths):
                    writer.writerow([az, peak_freqs[i], peak_amps[i]])


else:
    class AzimuthalPropertiesDock:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass
