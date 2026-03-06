"""
Figure Export Settings Dialog
==============================

Lets the user customise titles, colors, fill style, axis limits, and
figure size for the enhanced publication figures before exporting.
"""
try:
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
        QGroupBox, QFormLayout, QLabel, QLineEdit, QComboBox,
        QDoubleSpinBox, QSpinBox, QCheckBox, QPushButton,
        QColorDialog, QDialogButtonBox, QGridLayout,
    )
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QColor

    _HAS_QT = True
except ImportError:
    _HAS_QT = False

from typing import Dict, Any


# ── Default presets ──────────────────────────────────────────────────
DEFAULT_SETTINGS: Dict[str, Any] = {
    # Histogram
    'hist_title': 'F0 Frequency Distribution',
    'hist_xlabel': 'Frequency (Hz)',
    'hist_ylabel': 'Number of Stations',
    'hist_color': '#d62728',
    'hist_edgecolor': '#ffffff',
    'hist_fill': True,
    'hist_alpha': 0.85,
    'hist_fig_w': 10.0,
    'hist_fig_h': 6.0,
    'hist_xlim_auto': True,
    'hist_xlim_min': 0.0,
    'hist_xlim_max': 10.0,
    # Curve
    'curve_title': 'HVSR — All Stations',
    'curve_xlabel': 'Frequency (Hz)',
    'curve_ylabel': 'H/V Spectral Ratio',
    'curve_fig_w': 14.0,
    'curve_fig_h': 8.0,
    'curve_xlim_auto': True,
    'curve_xlim_min': 0.1,
    'curve_xlim_max': 30.0,
    'curve_ylim_auto': True,
    'curve_ylim_min': 0.0,
    'curve_ylim_max': 20.0,
    'curve_grand_color': '#000000',
    'curve_std_color': '#808080',
    'curve_std_alpha': 0.15,
}


if _HAS_QT:

    class _ColorButton(QPushButton):
        """Small button that shows/picks a color."""

        def __init__(self, initial_hex: str = '#000000', parent=None):
            super().__init__(parent)
            self._color = initial_hex
            self.setFixedSize(50, 24)
            self._apply_style()
            self.clicked.connect(self._pick)

        def _apply_style(self):
            self.setStyleSheet(
                f"background-color: {self._color}; border: 1px solid #888;")

        def _pick(self):
            c = QColorDialog.getColor(QColor(self._color), self, "Pick Color")
            if c.isValid():
                self._color = c.name()
                self._apply_style()

        def color(self) -> str:
            return self._color

        def set_color(self, hex_color: str):
            self._color = hex_color
            self._apply_style()


    class FigureExportSettingsDialog(QDialog):
        """Dialog for configuring export figure appearance."""

        def __init__(self, parent=None, current_settings: Dict[str, Any] = None):
            super().__init__(parent)
            self.setWindowTitle("Figure Export Settings")
            self.setMinimumWidth(520)
            self._settings = dict(DEFAULT_SETTINGS)
            if current_settings:
                self._settings.update(current_settings)
            self._build_ui()

        # ── UI ───────────────────────────────────────────────────────
        def _build_ui(self):
            main = QVBoxLayout(self)

            tabs = QTabWidget()
            tabs.addTab(self._build_histogram_tab(), "Histogram")
            tabs.addTab(self._build_curve_tab(), "HVSR Curve")
            main.addWidget(tabs)

            btns = QDialogButtonBox(
                QDialogButtonBox.Ok | QDialogButtonBox.Cancel
                | QDialogButtonBox.RestoreDefaults)
            btns.accepted.connect(self.accept)
            btns.rejected.connect(self.reject)
            btns.button(QDialogButtonBox.RestoreDefaults).clicked.connect(
                self._reset_defaults)
            main.addWidget(btns)

        # ── Histogram tab ────────────────────────────────────────────
        def _build_histogram_tab(self) -> QWidget:
            w = QWidget()
            layout = QVBoxLayout(w)

            # Titles
            g_title = QGroupBox("Labels")
            form = QFormLayout(g_title)
            self.hist_title_edit = QLineEdit(self._settings['hist_title'])
            form.addRow("Title:", self.hist_title_edit)
            self.hist_xlabel_edit = QLineEdit(self._settings['hist_xlabel'])
            form.addRow("X Label:", self.hist_xlabel_edit)
            self.hist_ylabel_edit = QLineEdit(self._settings['hist_ylabel'])
            form.addRow("Y Label:", self.hist_ylabel_edit)
            layout.addWidget(g_title)

            # Appearance
            g_app = QGroupBox("Appearance")
            grid = QGridLayout(g_app)
            row = 0

            grid.addWidget(QLabel("Bar Color:"), row, 0)
            self.hist_color_btn = _ColorButton(self._settings['hist_color'])
            grid.addWidget(self.hist_color_btn, row, 1)

            grid.addWidget(QLabel("Edge Color:"), row, 2)
            self.hist_edge_btn = _ColorButton(self._settings['hist_edgecolor'])
            grid.addWidget(self.hist_edge_btn, row, 3)
            row += 1

            self.hist_fill_check = QCheckBox("Filled bars")
            self.hist_fill_check.setChecked(self._settings['hist_fill'])
            grid.addWidget(self.hist_fill_check, row, 0, 1, 2)

            grid.addWidget(QLabel("Alpha:"), row, 2)
            self.hist_alpha_spin = QDoubleSpinBox()
            self.hist_alpha_spin.setRange(0.1, 1.0)
            self.hist_alpha_spin.setDecimals(2)
            self.hist_alpha_spin.setSingleStep(0.05)
            self.hist_alpha_spin.setValue(self._settings['hist_alpha'])
            grid.addWidget(self.hist_alpha_spin, row, 3)
            layout.addWidget(g_app)

            # Size & Limits
            g_size = QGroupBox("Figure Size & Axis Limits")
            form2 = QFormLayout(g_size)

            sz_row = QHBoxLayout()
            self.hist_w_spin = QDoubleSpinBox()
            self.hist_w_spin.setRange(4.0, 30.0); self.hist_w_spin.setDecimals(1)
            self.hist_w_spin.setValue(self._settings['hist_fig_w'])
            sz_row.addWidget(QLabel("W:")); sz_row.addWidget(self.hist_w_spin)
            self.hist_h_spin = QDoubleSpinBox()
            self.hist_h_spin.setRange(3.0, 20.0); self.hist_h_spin.setDecimals(1)
            self.hist_h_spin.setValue(self._settings['hist_fig_h'])
            sz_row.addWidget(QLabel("H:")); sz_row.addWidget(self.hist_h_spin)
            sz_row.addWidget(QLabel("inches"))
            form2.addRow("Figure Size:", sz_row)

            xlim_row = QHBoxLayout()
            self.hist_xlim_auto = QCheckBox("Auto")
            self.hist_xlim_auto.setChecked(self._settings['hist_xlim_auto'])
            xlim_row.addWidget(self.hist_xlim_auto)
            self.hist_xlim_min_spin = QDoubleSpinBox()
            self.hist_xlim_min_spin.setRange(0.0, 100.0); self.hist_xlim_min_spin.setDecimals(2)
            self.hist_xlim_min_spin.setValue(self._settings['hist_xlim_min'])
            xlim_row.addWidget(self.hist_xlim_min_spin)
            xlim_row.addWidget(QLabel("–"))
            self.hist_xlim_max_spin = QDoubleSpinBox()
            self.hist_xlim_max_spin.setRange(0.0, 200.0); self.hist_xlim_max_spin.setDecimals(2)
            self.hist_xlim_max_spin.setValue(self._settings['hist_xlim_max'])
            xlim_row.addWidget(self.hist_xlim_max_spin)
            xlim_row.addWidget(QLabel("Hz"))
            form2.addRow("X Limits:", xlim_row)

            self.hist_xlim_auto.toggled.connect(
                lambda on: (self.hist_xlim_min_spin.setEnabled(not on),
                            self.hist_xlim_max_spin.setEnabled(not on)))
            self.hist_xlim_auto.toggled.emit(self.hist_xlim_auto.isChecked())

            layout.addWidget(g_size)
            layout.addStretch()
            return w

        # ── Curve tab ────────────────────────────────────────────────
        def _build_curve_tab(self) -> QWidget:
            w = QWidget()
            layout = QVBoxLayout(w)

            # Titles
            g_title = QGroupBox("Labels")
            form = QFormLayout(g_title)
            self.curve_title_edit = QLineEdit(self._settings['curve_title'])
            form.addRow("Title:", self.curve_title_edit)
            self.curve_xlabel_edit = QLineEdit(self._settings['curve_xlabel'])
            form.addRow("X Label:", self.curve_xlabel_edit)
            self.curve_ylabel_edit = QLineEdit(self._settings['curve_ylabel'])
            form.addRow("Y Label:", self.curve_ylabel_edit)
            layout.addWidget(g_title)

            # Colors
            g_colors = QGroupBox("Colors")
            grid = QGridLayout(g_colors)
            row = 0

            grid.addWidget(QLabel("Grand Median:"), row, 0)
            self.curve_grand_btn = _ColorButton(self._settings['curve_grand_color'])
            grid.addWidget(self.curve_grand_btn, row, 1)

            grid.addWidget(QLabel("Std Band:"), row, 2)
            self.curve_std_btn = _ColorButton(self._settings['curve_std_color'])
            grid.addWidget(self.curve_std_btn, row, 3)
            row += 1

            grid.addWidget(QLabel("Std Alpha:"), row, 0)
            self.curve_std_alpha_spin = QDoubleSpinBox()
            self.curve_std_alpha_spin.setRange(0.05, 0.6)
            self.curve_std_alpha_spin.setDecimals(2)
            self.curve_std_alpha_spin.setSingleStep(0.05)
            self.curve_std_alpha_spin.setValue(self._settings['curve_std_alpha'])
            grid.addWidget(self.curve_std_alpha_spin, row, 1)
            layout.addWidget(g_colors)

            # Size & Limits
            g_size = QGroupBox("Figure Size & Axis Limits")
            form2 = QFormLayout(g_size)

            sz_row = QHBoxLayout()
            self.curve_w_spin = QDoubleSpinBox()
            self.curve_w_spin.setRange(4.0, 30.0); self.curve_w_spin.setDecimals(1)
            self.curve_w_spin.setValue(self._settings['curve_fig_w'])
            sz_row.addWidget(QLabel("W:")); sz_row.addWidget(self.curve_w_spin)
            self.curve_h_spin = QDoubleSpinBox()
            self.curve_h_spin.setRange(3.0, 20.0); self.curve_h_spin.setDecimals(1)
            self.curve_h_spin.setValue(self._settings['curve_fig_h'])
            sz_row.addWidget(QLabel("H:")); sz_row.addWidget(self.curve_h_spin)
            sz_row.addWidget(QLabel("inches"))
            form2.addRow("Figure Size:", sz_row)

            xlim_row = QHBoxLayout()
            self.curve_xlim_auto = QCheckBox("Auto")
            self.curve_xlim_auto.setChecked(self._settings['curve_xlim_auto'])
            xlim_row.addWidget(self.curve_xlim_auto)
            self.curve_xlim_min_spin = QDoubleSpinBox()
            self.curve_xlim_min_spin.setRange(0.001, 100.0)
            self.curve_xlim_min_spin.setDecimals(3)
            self.curve_xlim_min_spin.setValue(self._settings['curve_xlim_min'])
            xlim_row.addWidget(self.curve_xlim_min_spin)
            xlim_row.addWidget(QLabel("–"))
            self.curve_xlim_max_spin = QDoubleSpinBox()
            self.curve_xlim_max_spin.setRange(0.01, 200.0)
            self.curve_xlim_max_spin.setDecimals(2)
            self.curve_xlim_max_spin.setValue(self._settings['curve_xlim_max'])
            xlim_row.addWidget(self.curve_xlim_max_spin)
            xlim_row.addWidget(QLabel("Hz"))
            form2.addRow("X Limits:", xlim_row)

            self.curve_xlim_auto.toggled.connect(
                lambda on: (self.curve_xlim_min_spin.setEnabled(not on),
                            self.curve_xlim_max_spin.setEnabled(not on)))
            self.curve_xlim_auto.toggled.emit(self.curve_xlim_auto.isChecked())

            ylim_row = QHBoxLayout()
            self.curve_ylim_auto = QCheckBox("Auto (smart)")
            self.curve_ylim_auto.setChecked(self._settings['curve_ylim_auto'])
            ylim_row.addWidget(self.curve_ylim_auto)
            self.curve_ylim_min_spin = QDoubleSpinBox()
            self.curve_ylim_min_spin.setRange(-50.0, 100.0)
            self.curve_ylim_min_spin.setDecimals(1)
            self.curve_ylim_min_spin.setValue(self._settings['curve_ylim_min'])
            ylim_row.addWidget(self.curve_ylim_min_spin)
            ylim_row.addWidget(QLabel("–"))
            self.curve_ylim_max_spin = QDoubleSpinBox()
            self.curve_ylim_max_spin.setRange(0.1, 500.0)
            self.curve_ylim_max_spin.setDecimals(1)
            self.curve_ylim_max_spin.setValue(self._settings['curve_ylim_max'])
            ylim_row.addWidget(self.curve_ylim_max_spin)
            form2.addRow("Y Limits:", ylim_row)

            self.curve_ylim_auto.toggled.connect(
                lambda on: (self.curve_ylim_min_spin.setEnabled(not on),
                            self.curve_ylim_max_spin.setEnabled(not on)))
            self.curve_ylim_auto.toggled.emit(self.curve_ylim_auto.isChecked())

            layout.addWidget(g_size)
            layout.addStretch()
            return w

        # ── Collect / Reset ──────────────────────────────────────────
        def get_settings(self) -> Dict[str, Any]:
            return {
                'hist_title': self.hist_title_edit.text(),
                'hist_xlabel': self.hist_xlabel_edit.text(),
                'hist_ylabel': self.hist_ylabel_edit.text(),
                'hist_color': self.hist_color_btn.color(),
                'hist_edgecolor': self.hist_edge_btn.color(),
                'hist_fill': self.hist_fill_check.isChecked(),
                'hist_alpha': self.hist_alpha_spin.value(),
                'hist_fig_w': self.hist_w_spin.value(),
                'hist_fig_h': self.hist_h_spin.value(),
                'hist_xlim_auto': self.hist_xlim_auto.isChecked(),
                'hist_xlim_min': self.hist_xlim_min_spin.value(),
                'hist_xlim_max': self.hist_xlim_max_spin.value(),
                'curve_title': self.curve_title_edit.text(),
                'curve_xlabel': self.curve_xlabel_edit.text(),
                'curve_ylabel': self.curve_ylabel_edit.text(),
                'curve_fig_w': self.curve_w_spin.value(),
                'curve_fig_h': self.curve_h_spin.value(),
                'curve_xlim_auto': self.curve_xlim_auto.isChecked(),
                'curve_xlim_min': self.curve_xlim_min_spin.value(),
                'curve_xlim_max': self.curve_xlim_max_spin.value(),
                'curve_ylim_auto': self.curve_ylim_auto.isChecked(),
                'curve_ylim_min': self.curve_ylim_min_spin.value(),
                'curve_ylim_max': self.curve_ylim_max_spin.value(),
                'curve_grand_color': self.curve_grand_btn.color(),
                'curve_std_color': self.curve_std_btn.color(),
                'curve_std_alpha': self.curve_std_alpha_spin.value(),
            }

        def _reset_defaults(self):
            self._settings = dict(DEFAULT_SETTINGS)
            # Histogram
            self.hist_title_edit.setText(self._settings['hist_title'])
            self.hist_xlabel_edit.setText(self._settings['hist_xlabel'])
            self.hist_ylabel_edit.setText(self._settings['hist_ylabel'])
            self.hist_color_btn.set_color(self._settings['hist_color'])
            self.hist_edge_btn.set_color(self._settings['hist_edgecolor'])
            self.hist_fill_check.setChecked(self._settings['hist_fill'])
            self.hist_alpha_spin.setValue(self._settings['hist_alpha'])
            self.hist_w_spin.setValue(self._settings['hist_fig_w'])
            self.hist_h_spin.setValue(self._settings['hist_fig_h'])
            self.hist_xlim_auto.setChecked(self._settings['hist_xlim_auto'])
            self.hist_xlim_min_spin.setValue(self._settings['hist_xlim_min'])
            self.hist_xlim_max_spin.setValue(self._settings['hist_xlim_max'])
            # Curve
            self.curve_title_edit.setText(self._settings['curve_title'])
            self.curve_xlabel_edit.setText(self._settings['curve_xlabel'])
            self.curve_ylabel_edit.setText(self._settings['curve_ylabel'])
            self.curve_w_spin.setValue(self._settings['curve_fig_w'])
            self.curve_h_spin.setValue(self._settings['curve_fig_h'])
            self.curve_xlim_auto.setChecked(self._settings['curve_xlim_auto'])
            self.curve_xlim_min_spin.setValue(self._settings['curve_xlim_min'])
            self.curve_xlim_max_spin.setValue(self._settings['curve_xlim_max'])
            self.curve_ylim_auto.setChecked(self._settings['curve_ylim_auto'])
            self.curve_ylim_min_spin.setValue(self._settings['curve_ylim_min'])
            self.curve_ylim_max_spin.setValue(self._settings['curve_ylim_max'])
            self.curve_grand_btn.set_color(self._settings['curve_grand_color'])
            self.curve_std_btn.set_color(self._settings['curve_std_color'])
            self.curve_std_alpha_spin.setValue(self._settings['curve_std_alpha'])

else:
    class FigureExportSettingsDialog:
        pass
