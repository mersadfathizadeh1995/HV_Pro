"""
Data Export Section
===================

Export HVSR results data as CSV or JSON with optional interpolation.
"""

try:
    from PyQt5.QtWidgets import (
        QWidget, QHBoxLayout, QPushButton, QLabel,
        QSpinBox, QCheckBox
    )
    from PyQt5.QtCore import pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False

if HAS_PYQT5:
    from hvsr_pro.gui.components import CollapsibleSection


if HAS_PYQT5:
    class DataExportSection(CollapsibleSection):
        """
        Data export section with format and interpolation options.
        
        Signals:
            export_requested: Emitted when export is requested (str format, dict options)
        """
        
        export_requested = pyqtSignal(str, dict)
        
        def __init__(self, parent=None):
            super().__init__("Export Results Data", parent)
            self._init_content()
        
        def _init_content(self):
            """Initialize section content."""
            # Point count for interpolation
            points_container = QWidget()
            points_layout = QHBoxLayout(points_container)
            points_layout.setContentsMargins(0, 0, 0, 0)
            points_layout.addWidget(QLabel("Output Points:"))
            
            self.export_points_spin = QSpinBox()
            self.export_points_spin.setRange(10, 1000)
            self.export_points_spin.setValue(100)
            self.export_points_spin.setSingleStep(10)
            self.export_points_spin.setToolTip(
                "Number of frequency points in exported curve.\n"
                "Use 0 or same as original to keep original points.\n"
                "Interpolation is used when changing point count."
            )
            points_layout.addWidget(self.export_points_spin)
            
            self.use_original_points_cb = QCheckBox("Use Original")
            self.use_original_points_cb.setChecked(True)
            self.use_original_points_cb.setToolTip("Use original frequency points (no interpolation)")
            self.use_original_points_cb.toggled.connect(
                lambda checked: self.export_points_spin.setEnabled(not checked)
            )
            points_layout.addWidget(self.use_original_points_cb)
            
            self.add_widget(points_container)
            
            # Export buttons
            btn_container = QWidget()
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(0, 0, 0, 0)
            
            self.export_csv_btn = QPushButton("CSV")
            self.export_csv_btn.setToolTip("Export HVSR curve and peaks as CSV")
            self.export_csv_btn.clicked.connect(lambda: self._emit_export("csv"))
            btn_layout.addWidget(self.export_csv_btn)
            
            self.export_json_btn = QPushButton("JSON")
            self.export_json_btn.setToolTip("Export complete results as JSON")
            self.export_json_btn.clicked.connect(lambda: self._emit_export("json"))
            btn_layout.addWidget(self.export_json_btn)
            
            self.export_excel_btn = QPushButton("Excel")
            self.export_excel_btn.setToolTip("Export HVSR results as Excel (.xlsx) with multiple sheets")
            self.export_excel_btn.clicked.connect(lambda: self._emit_export("xlsx"))
            btn_layout.addWidget(self.export_excel_btn)
            
            self.add_widget(btn_container)
            
            # Info label
            info = QLabel("Export HVSR curve, peaks, and metadata")
            info.setStyleSheet("QLabel { color: #666; font-size: 9px; }")
            info.setWordWrap(True)
            self.add_widget(info)
        
        def _emit_export(self, format_type: str):
            """Emit export signal with options."""
            options = self.get_options()
            self.export_requested.emit(format_type, options)
        
        def get_options(self) -> dict:
            """Get current export options."""
            options = {}
            if not self.use_original_points_cb.isChecked():
                options['n_points'] = self.export_points_spin.value()
            return options
        
        def set_enabled(self, enabled: bool):
            """Enable or disable export buttons."""
            self.export_csv_btn.setEnabled(enabled)
            self.export_json_btn.setEnabled(enabled)
            self.export_excel_btn.setEnabled(enabled)


else:
    class DataExportSection:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass
