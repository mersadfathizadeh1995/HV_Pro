"""
Plot Export Section
===================

Export current plot as image (PNG, PDF, SVG).
"""

try:
    from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel
    from PyQt5.QtCore import pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False

if HAS_PYQT5:
    from hvsr_pro.gui.components import CollapsibleSection


if HAS_PYQT5:
    class PlotExportSection(CollapsibleSection):
        """
        Plot export section with format buttons.
        
        Signals:
            export_requested: Emitted when export is requested (str format)
        """
        
        export_requested = pyqtSignal(str)
        
        def __init__(self, parent=None):
            super().__init__("Export Plot as Image", parent)
            self._init_content()
        
        def _init_content(self):
            """Initialize section content."""
            # Format buttons container
            btn_container = QWidget()
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(0, 0, 0, 0)
            
            self.export_png_btn = QPushButton("PNG")
            self.export_png_btn.setToolTip("Export as PNG image (high quality)")
            self.export_png_btn.clicked.connect(lambda: self.export_requested.emit("png"))
            btn_layout.addWidget(self.export_png_btn)
            
            self.export_pdf_btn = QPushButton("PDF")
            self.export_pdf_btn.setToolTip("Export as PDF document (vector)")
            self.export_pdf_btn.clicked.connect(lambda: self.export_requested.emit("pdf"))
            btn_layout.addWidget(self.export_pdf_btn)
            
            self.export_svg_btn = QPushButton("SVG")
            self.export_svg_btn.setToolTip("Export as SVG vector graphics")
            self.export_svg_btn.clicked.connect(lambda: self.export_requested.emit("svg"))
            btn_layout.addWidget(self.export_svg_btn)
            
            self.add_widget(btn_container)
            
            # Info label
            info = QLabel("Export current HVSR plot with all settings")
            info.setStyleSheet("QLabel { color: #666; font-size: 9px; }")
            info.setWordWrap(True)
            self.add_widget(info)
        
        def set_enabled(self, enabled: bool):
            """Enable or disable export buttons."""
            self.export_png_btn.setEnabled(enabled)
            self.export_pdf_btn.setEnabled(enabled)
            self.export_svg_btn.setEnabled(enabled)


else:
    class PlotExportSection:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass
