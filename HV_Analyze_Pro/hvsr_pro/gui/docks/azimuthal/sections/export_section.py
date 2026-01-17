"""
Export Section
==============

Export buttons and DPI settings for azimuthal plots.
"""

try:
    from PyQt5.QtWidgets import (
        QWidget, QHBoxLayout, QLabel, QSpinBox, QPushButton
    )
    from PyQt5.QtCore import pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False

if HAS_PYQT5:
    from hvsr_pro.gui.components import CollapsibleSection


if HAS_PYQT5:
    class ExportSection(CollapsibleSection):
        """
        Export options section.
        
        Signals:
            export_plot_requested: Emitted when plot export is requested (str format)
            export_data_requested: Emitted when data export is requested (str format)
            export_report_requested: Emitted when full report export is requested
        """
        
        export_plot_requested = pyqtSignal(str)
        export_data_requested = pyqtSignal(str)
        export_report_requested = pyqtSignal()
        
        def __init__(self, parent=None):
            super().__init__("Export", parent)
            self._init_content()
        
        def _init_content(self):
            """Initialize section content."""
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
            self.add_widget(dpi_container)
            
            # Export plot buttons
            btn_container = QWidget()
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(0, 0, 0, 0)
            
            self.export_png_btn = QPushButton("PNG")
            self.export_png_btn.clicked.connect(lambda: self.export_plot_requested.emit("png"))
            btn_layout.addWidget(self.export_png_btn)
            
            self.export_pdf_btn = QPushButton("PDF")
            self.export_pdf_btn.clicked.connect(lambda: self.export_plot_requested.emit("pdf"))
            btn_layout.addWidget(self.export_pdf_btn)
            
            self.export_svg_btn = QPushButton("SVG")
            self.export_svg_btn.clicked.connect(lambda: self.export_plot_requested.emit("svg"))
            btn_layout.addWidget(self.export_svg_btn)
            
            self.add_widget(btn_container)
            
            # Export data buttons
            self.export_csv_btn = QPushButton("Export Data (CSV)")
            self.export_csv_btn.clicked.connect(lambda: self.export_data_requested.emit("csv"))
            self.add_widget(self.export_csv_btn)
            
            self.export_json_btn = QPushButton("Export Data (JSON)")
            self.export_json_btn.clicked.connect(lambda: self.export_data_requested.emit("json"))
            self.add_widget(self.export_json_btn)
            
            # Export Report button
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
            self.export_report_btn.clicked.connect(self.export_report_requested.emit)
            self.export_report_btn.setToolTip("Export comprehensive report with all figures and data")
            self.add_widget(self.export_report_btn)
        
        def get_dpi(self) -> int:
            """Get DPI setting."""
            return self.dpi_spin.value()
        
        def set_dpi(self, dpi: int):
            """Set DPI value."""
            self.dpi_spin.setValue(dpi)
        
        def set_enabled(self, enabled: bool):
            """Enable or disable export buttons."""
            self.export_png_btn.setEnabled(enabled)
            self.export_pdf_btn.setEnabled(enabled)
            self.export_svg_btn.setEnabled(enabled)
            self.export_csv_btn.setEnabled(enabled)
            self.export_json_btn.setEnabled(enabled)
            self.export_report_btn.setEnabled(enabled)


else:
    class ExportSection:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass
