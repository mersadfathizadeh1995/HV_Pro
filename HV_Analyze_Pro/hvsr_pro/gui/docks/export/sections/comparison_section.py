"""
Comparison Figures Section
==========================

Export comparison figures with customizable rejected window display.
"""

try:
    from PyQt5.QtWidgets import (
        QWidget, QHBoxLayout, QPushButton, QLabel,
        QCheckBox, QSlider, QSpinBox, QDoubleSpinBox, QComboBox
    )
    from PyQt5.QtCore import Qt, pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False

if HAS_PYQT5:
    from hvsr_pro.gui.components import CollapsibleSection, ColorPickerButton


if HAS_PYQT5:
    class ComparisonFiguresSection(CollapsibleSection):
        """
        Comparison figures section with rejected window options and figure export buttons.
        
        Signals:
            export_comparison_requested: Request Raw vs Adjusted figure
            export_waveform_requested: Request 3C waveform figure
            export_prepost_requested: Request Pre/Post rejection figure
        """
        
        export_comparison_requested = pyqtSignal(dict)
        export_waveform_requested = pyqtSignal(dict)
        export_prepost_requested = pyqtSignal(dict)
        
        def __init__(self, parent=None):
            super().__init__("Comparison Figures", parent)
            self._init_content()
        
        def _init_content(self):
            """Initialize section content."""
            # Info label
            info = QLabel("Publication-quality comparison figures:")
            info.setStyleSheet("QLabel { color: #333; font-weight: bold; }")
            self.add_widget(info)
            
            # === REJECTED WINDOW DISPLAY OPTIONS ===
            self._create_rejected_window_options()
            
            # Separator
            self._add_separator()
            
            # === FIGURE LAYOUT OPTIONS ===
            self._create_figure_layout_options()
            
            # Separator
            self._add_separator()
            
            # === EXPORT BUTTONS ===
            self._create_export_buttons()
            
            # Format selector
            self._create_format_selector()
        
        def _create_rejected_window_options(self):
            """Create rejected window display options."""
            rejected_label = QLabel("Adjusted Panel - Rejected Windows:")
            rejected_label.setStyleSheet("QLabel { color: #555; font-size: 9px; margin-top: 5px; }")
            self.add_widget(rejected_label)
            
            # Show rejected windows checkbox
            self.show_rejected_cb = QCheckBox("Show rejected windows")
            self.show_rejected_cb.setChecked(True)
            self.show_rejected_cb.setToolTip("Show or hide rejected windows in the adjusted (bottom) panel")
            self.show_rejected_cb.toggled.connect(self._on_rejected_options_changed)
            self.add_widget(self.show_rejected_cb)
            
            # Color picker for rejected windows
            color_container = QWidget()
            color_layout = QHBoxLayout(color_container)
            color_layout.setContentsMargins(0, 0, 0, 0)
            color_layout.addWidget(QLabel("Color:"))
            self.rejected_color_btn = ColorPickerButton(initial_color="#808080")
            self.rejected_color_btn.setToolTip("Color for rejected window curves")
            self.rejected_color_btn.setFixedWidth(80)
            color_layout.addWidget(self.rejected_color_btn)
            color_layout.addStretch()
            self.add_widget(color_container)
            
            # Opacity slider for rejected windows
            opacity_container = QWidget()
            opacity_layout = QHBoxLayout(opacity_container)
            opacity_layout.setContentsMargins(0, 0, 0, 0)
            opacity_layout.addWidget(QLabel("Opacity:"))
            self.rejected_opacity_slider = QSlider(Qt.Horizontal)
            self.rejected_opacity_slider.setRange(0, 100)
            self.rejected_opacity_slider.setValue(30)
            self.rejected_opacity_slider.setToolTip("Opacity of rejected window curves (0-100%)")
            opacity_layout.addWidget(self.rejected_opacity_slider)
            self.rejected_opacity_label = QLabel("30%")
            self.rejected_opacity_label.setFixedWidth(35)
            self.rejected_opacity_slider.valueChanged.connect(
                lambda v: self.rejected_opacity_label.setText(f"{v}%")
            )
            opacity_layout.addWidget(self.rejected_opacity_label)
            self.add_widget(opacity_container)
            
            # Line width for rejected windows
            lw_container = QWidget()
            lw_layout = QHBoxLayout(lw_container)
            lw_layout.setContentsMargins(0, 0, 0, 0)
            lw_layout.addWidget(QLabel("Line Width:"))
            self.rejected_linewidth_spin = QDoubleSpinBox()
            self.rejected_linewidth_spin.setRange(0.1, 3.0)
            self.rejected_linewidth_spin.setValue(0.5)
            self.rejected_linewidth_spin.setSingleStep(0.1)
            self.rejected_linewidth_spin.setToolTip("Line width for rejected window curves")
            lw_layout.addWidget(self.rejected_linewidth_spin)
            lw_layout.addStretch()
            self.add_widget(lw_container)
        
        def _create_figure_layout_options(self):
            """Create figure layout options."""
            layout_label = QLabel("Figure Layout Options:")
            layout_label.setStyleSheet("QLabel { color: #555; font-size: 9px; margin-top: 5px; }")
            self.add_widget(layout_label)
            
            # Title font size
            title_fs_container = QWidget()
            title_fs_layout = QHBoxLayout(title_fs_container)
            title_fs_layout.setContentsMargins(0, 0, 0, 0)
            title_fs_layout.addWidget(QLabel("Title Font:"))
            self.fig_title_fontsize_spin = QSpinBox()
            self.fig_title_fontsize_spin.setRange(8, 24)
            self.fig_title_fontsize_spin.setValue(11)
            self.fig_title_fontsize_spin.setToolTip("Font size for subplot titles")
            title_fs_layout.addWidget(self.fig_title_fontsize_spin)
            title_fs_layout.addStretch()
            self.add_widget(title_fs_container)
            
            # Axis font size
            axis_fs_container = QWidget()
            axis_fs_layout = QHBoxLayout(axis_fs_container)
            axis_fs_layout.setContentsMargins(0, 0, 0, 0)
            axis_fs_layout.addWidget(QLabel("Axis Font:"))
            self.fig_axis_fontsize_spin = QSpinBox()
            self.fig_axis_fontsize_spin.setRange(8, 20)
            self.fig_axis_fontsize_spin.setValue(10)
            self.fig_axis_fontsize_spin.setToolTip("Font size for axis labels")
            axis_fs_layout.addWidget(self.fig_axis_fontsize_spin)
            axis_fs_layout.addStretch()
            self.add_widget(axis_fs_container)
            
            # Subplot spacing
            spacing_container = QWidget()
            spacing_layout = QHBoxLayout(spacing_container)
            spacing_layout.setContentsMargins(0, 0, 0, 0)
            spacing_layout.addWidget(QLabel("Spacing:"))
            self.fig_spacing_spin = QDoubleSpinBox()
            self.fig_spacing_spin.setRange(0.2, 0.8)
            self.fig_spacing_spin.setValue(0.5)
            self.fig_spacing_spin.setSingleStep(0.1)
            self.fig_spacing_spin.setToolTip("Spacing between subplots (0.2 = tight, 0.8 = loose)")
            spacing_layout.addWidget(self.fig_spacing_spin)
            spacing_layout.addStretch()
            self.add_widget(spacing_container)
            
            # DPI setting
            dpi_container = QWidget()
            dpi_layout = QHBoxLayout(dpi_container)
            dpi_layout.setContentsMargins(0, 0, 0, 0)
            dpi_layout.addWidget(QLabel("DPI:"))
            self.fig_dpi_spin = QSpinBox()
            self.fig_dpi_spin.setRange(72, 1200)
            self.fig_dpi_spin.setValue(300)
            self.fig_dpi_spin.setSingleStep(50)
            self.fig_dpi_spin.setToolTip("Figure resolution (72-1200 DPI)")
            dpi_layout.addWidget(self.fig_dpi_spin)
            dpi_layout.addStretch()
            self.add_widget(dpi_container)
        
        def _create_export_buttons(self):
            """Create export buttons."""
            # Raw vs Adjusted comparison figure
            self.export_comparison_btn = QPushButton("Raw vs Adjusted HVSR")
            self.export_comparison_btn.setToolTip(
                "Export dual-panel comparison figure:\n"
                "- Top: Raw HVSR results (all windows)\n"
                "- Bottom: Adjusted HVSR (after rejection)\n"
                "- Statistics boxes, frequency uncertainty bands"
            )
            self.export_comparison_btn.clicked.connect(
                lambda: self.export_comparison_requested.emit(self.get_options())
            )
            self.add_widget(self.export_comparison_btn)
            
            # 3C Waveform plot
            self.export_waveform_btn = QPushButton("3C Waveform with Rejection")
            self.export_waveform_btn.setToolTip(
                "Export 3-component seismic recording plot:\n"
                "- North-South, East-West, Vertical components\n"
                "- Color-coded accepted/rejected windows"
            )
            self.export_waveform_btn.clicked.connect(
                lambda: self.export_waveform_requested.emit(self.get_options())
            )
            self.add_widget(self.export_waveform_btn)
            
            # Pre/Post rejection combined figure
            self.export_prepost_btn = QPushButton("Pre/Post Rejection (5-panel)")
            self.export_prepost_btn.setToolTip(
                "Export comprehensive pre/post rejection figure:\n"
                "- Left: 3C waveforms with rejection markers\n"
                "- Right top: HVSR before rejection\n"
                "- Right bottom: HVSR after rejection"
            )
            self.export_prepost_btn.clicked.connect(
                lambda: self.export_prepost_requested.emit(self.get_options())
            )
            self.add_widget(self.export_prepost_btn)
        
        def _create_format_selector(self):
            """Create format selector."""
            format_container = QWidget()
            format_layout = QHBoxLayout(format_container)
            format_layout.setContentsMargins(0, 0, 0, 0)
            format_layout.addWidget(QLabel("Format:"))
            self.figure_format_combo = QComboBox()
            self.figure_format_combo.addItem("PNG (Raster)", "png")
            self.figure_format_combo.addItem("PDF (Vector)", "pdf")
            self.figure_format_combo.addItem("SVG (Vector)", "svg")
            format_layout.addWidget(self.figure_format_combo)
            self.add_widget(format_container)
        
        def _add_separator(self):
            """Add a separator line."""
            separator = QLabel("")
            separator.setStyleSheet("QLabel { border-top: 1px solid #ccc; margin: 5px 0; }")
            separator.setFixedHeight(2)
            self.add_widget(separator)
        
        def _on_rejected_options_changed(self, checked: bool):
            """Handle rejected window visibility toggle."""
            self.rejected_color_btn.setEnabled(checked)
            self.rejected_opacity_slider.setEnabled(checked)
            self.rejected_linewidth_spin.setEnabled(checked)
        
        def get_rejected_window_options(self) -> dict:
            """Get current rejected window display options."""
            return {
                'show_rejected': self.show_rejected_cb.isChecked(),
                'rejected_color': self.rejected_color_btn.get_color(),
                'rejected_alpha': self.rejected_opacity_slider.value() / 100.0,
                'rejected_linewidth': self.rejected_linewidth_spin.value(),
            }
        
        def get_figure_options(self) -> dict:
            """Get current figure layout options."""
            return {
                'title_fontsize': self.fig_title_fontsize_spin.value(),
                'axis_fontsize': self.fig_axis_fontsize_spin.value(),
                'spacing': self.fig_spacing_spin.value(),
                'dpi': self.fig_dpi_spin.value(),
                'format': self.figure_format_combo.currentData(),
            }
        
        def get_options(self) -> dict:
            """Get all options combined."""
            options = self.get_rejected_window_options()
            options.update(self.get_figure_options())
            return options
        
        def set_enabled(self, has_result: bool, has_data: bool = False):
            """Enable or disable export buttons based on data availability."""
            self.export_comparison_btn.setEnabled(has_result)
            self.export_waveform_btn.setEnabled(has_result and has_data)
            self.export_prepost_btn.setEnabled(has_result and has_data)


else:
    class ComparisonFiguresSection:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass
