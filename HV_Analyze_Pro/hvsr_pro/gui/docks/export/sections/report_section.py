"""
Report Section
==============

Generate comprehensive report plots.
"""

try:
    from PyQt5.QtWidgets import QPushButton, QLabel
    from PyQt5.QtCore import pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False

if HAS_PYQT5:
    from hvsr_pro.gui.components import CollapsibleSection


if HAS_PYQT5:
    class ReportSection(CollapsibleSection):
        """
        Report generation section.
        
        Signals:
            generate_requested: Emitted when report generation is requested
        """
        
        generate_requested = pyqtSignal()
        
        def __init__(self, parent=None):
            super().__init__("Generate Report", parent)
            self._init_content()
        
        def _init_content(self):
            """Initialize section content."""
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
            self.generate_report_btn.clicked.connect(self.generate_requested.emit)
            self.add_widget(self.generate_report_btn)
            
            # Info label
            info = QLabel("Creates publication-ready multi-panel figure")
            info.setStyleSheet("QLabel { color: #666; font-size: 9px; }")
            info.setWordWrap(True)
            self.add_widget(info)
        
        def set_enabled(self, enabled: bool):
            """Enable or disable generate button."""
            self.generate_report_btn.setEnabled(enabled)


else:
    class ReportSection:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass
