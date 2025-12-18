"""
Azimuthal Properties Dock
=========================

Properties and export panel for azimuthal HVSR analysis tab.
"""

from typing import Optional

try:
    from PyQt5.QtWidgets import (
        QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
        QPushButton, QLabel, QComboBox, QSpinBox, QCheckBox,
        QScrollArea, QFileDialog, QMessageBox, QDoubleSpinBox
    )
    from PyQt5.QtCore import Qt, pyqtSignal
    from PyQt5.QtGui import QFont
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False

from hvsr_pro.gui.components import CollapsibleSection


if HAS_PYQT5:
    
    class AzimuthalPropertiesDock(QDockWidget):
        """
        Dock widget for azimuthal plot properties and export options.
        
        Features:
        - Theme/colormap selection
        - Figure type selector
        - Legend position/size controls
        - Font size controls
        - Export options (PNG, PDF, SVG, CSV, JSON)
        
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
            self.cmap_combo.currentIndexChanged.connect(self._emit_options_changed)
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
            self.curve_cmap_combo.currentIndexChanged.connect(self._emit_options_changed)
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
            self.figure_type_combo.currentIndexChanged.connect(self._emit_options_changed)
            type_layout.addWidget(self.figure_type_combo)
            section.add_widget(type_container)
            
            # Show panel labels
            self.show_labels_cb = QCheckBox("Show panel labels (a, b, c)")
            self.show_labels_cb.setChecked(True)
            self.show_labels_cb.toggled.connect(self._emit_options_changed)
            section.add_widget(self.show_labels_cb)
            
            # Show peak markers
            self.show_peaks_cb = QCheckBox("Show peak markers")
            self.show_peaks_cb.setChecked(True)
            self.show_peaks_cb.toggled.connect(self._emit_options_changed)
            section.add_widget(self.show_peaks_cb)
            
            # Show individual curves
            self.show_individual_cb = QCheckBox("Show individual curves")
            self.show_individual_cb.setChecked(True)
            self.show_individual_cb.toggled.connect(self._emit_options_changed)
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
            self.legend_pos_combo.addItem("Upper Right", "upper_right")
            self.legend_pos_combo.addItem("Upper Left", "upper_left")
            self.legend_pos_combo.addItem("None (Hide)", "none")
            self.legend_pos_combo.currentIndexChanged.connect(self._emit_options_changed)
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
            self.legend_size_spin.valueChanged.connect(self._emit_options_changed)
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
            self.title_size_spin.valueChanged.connect(self._emit_options_changed)
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
            self.axis_size_spin.valueChanged.connect(self._emit_options_changed)
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
            self.tick_size_spin.valueChanged.connect(self._emit_options_changed)
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
            self.dpi_spin.setRange(72, 600)
            self.dpi_spin.setValue(300)
            self.dpi_spin.setSingleStep(50)
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
            
            return section
        
        def _emit_options_changed(self):
            """Emit signal with current options."""
            options = self.get_options()
            self.plot_options_changed.emit(options)
        
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
        
        def _export_plot(self, format_type: str):
            """Export plot to file."""
            if not self.figure:
                QMessageBox.warning(self, "No Plot", "No azimuthal plot available.")
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
                    self.figure.savefig(
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
                        row = [freq] + [
                            self.result.mean_curves_per_azimuth[j, i]
                            for j in range(self.result.n_azimuths)
                        ]
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
            
            try:
                data = {
                    'frequencies': self.result.frequencies.tolist(),
                    'azimuths': self.result.azimuths.tolist(),
                    'mean_curves_per_azimuth': self.result.mean_curves_per_azimuth.tolist(),
                    'metadata': {
                        'n_azimuths': self.result.n_azimuths,
                        'n_frequencies': self.result.n_frequencies,
                    }
                }
                
                with open(filename, 'w') as f:
                    json.dump(data, f, indent=2)
                
                QMessageBox.information(
                    self, "Export Successful",
                    f"Data saved to:\n{filename}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self, "Export Failed",
                    f"Failed to export data:\n{str(e)}"
                )


else:
    class AzimuthalPropertiesDock:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass

