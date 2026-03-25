"""
Station Table Widget — editable table showing the station registry
in the Project Hub.
"""

from __future__ import annotations

from typing import List, Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor, QBrush
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QHeaderView, QLabel, QFileDialog, QMessageBox,
)

from ..station_registry import StationRegistry, RegistryStation


# Column indices
COL_ID = 0
COL_SENSOR = 1
COL_NAME = 2
COL_X = 3
COL_Y = 4
COL_ELEV = 5
COL_VS = 6
COL_F0 = 7
COL_STATUS = 8

_HEADERS = ["ID", "Sensor", "Name", "X", "Y", "Elevation", "Vs (m/s)", "f₀ (Hz)", "Status"]
_MISSING_BG = QColor(255, 245, 230)  # light orange for missing data


class StationTableWidget(QWidget):
    """Editable station registry table for the Project Hub.

    Signals
    -------
    registry_changed
        Emitted whenever the registry is modified (add/remove/edit).
    csv_imported : str
        Emitted with the CSV file path when a new file is imported.
    """

    registry_changed = pyqtSignal()
    csv_imported = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._registry: Optional[StationRegistry] = None
        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Header bar
        header_layout = QHBoxLayout()

        title = QLabel("Station Registry")
        title.setStyleSheet("font-weight: bold; font-size: 10pt;")
        header_layout.addWidget(title)

        self._count_label = QLabel("(0 stations)")
        self._count_label.setStyleSheet("color: #888;")
        header_layout.addWidget(self._count_label)

        header_layout.addStretch()

        btn_import = QPushButton("Import CSV...")
        btn_import.clicked.connect(self._on_import_csv)
        header_layout.addWidget(btn_import)

        btn_add = QPushButton("+")
        btn_add.setFixedWidth(30)
        btn_add.setToolTip("Add station manually")
        btn_add.clicked.connect(self._on_add_station)
        header_layout.addWidget(btn_add)

        btn_remove = QPushButton("−")
        btn_remove.setFixedWidth(30)
        btn_remove.setToolTip("Remove selected station")
        btn_remove.clicked.connect(self._on_remove_station)
        header_layout.addWidget(btn_remove)

        layout.addLayout(header_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(len(_HEADERS))
        self.table.setHorizontalHeaderLabels(_HEADERS)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.cellChanged.connect(self._on_cell_changed)

        layout.addWidget(self.table)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_registry(self, registry: StationRegistry) -> None:
        """Populate the table from a StationRegistry."""
        self._registry = registry
        self._refresh_table()

    def get_registry(self) -> StationRegistry:
        """Read current table contents back into a StationRegistry."""
        if self._registry is None:
            self._registry = StationRegistry()
        self._sync_registry_from_table()
        return self._registry

    # ------------------------------------------------------------------
    # Table population
    # ------------------------------------------------------------------

    def _refresh_table(self) -> None:
        self.table.blockSignals(True)
        self.table.setRowCount(0)

        if self._registry is None:
            self._count_label.setText("(0 stations)")
            self.table.blockSignals(False)
            return

        for stn in self._registry.stations:
            row = self.table.rowCount()
            self.table.insertRow(row)

            # ID (read-only)
            id_item = QTableWidgetItem(stn.id)
            id_item.setFlags(id_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, COL_ID, id_item)

            # Sensor
            sensor_item = QTableWidgetItem(stn.sensor or "")
            self.table.setItem(row, COL_SENSOR, sensor_item)

            # Name
            self.table.setItem(row, COL_NAME, QTableWidgetItem(stn.display_name))

            # X, Y, Elevation, Vs — editable, highlighted if missing
            for col, val in [
                (COL_X, stn.x), (COL_Y, stn.y),
                (COL_ELEV, stn.elevation), (COL_VS, stn.vs_avg),
            ]:
                text = f"{val:.6f}" if val is not None and col in (COL_X, COL_Y) else (
                    f"{val:.1f}" if val is not None else ""
                )
                item = QTableWidgetItem(text)
                if val is None:
                    item.setBackground(QBrush(_MISSING_BG))
                self.table.setItem(row, col, item)

            # f0 (read-only, filled by analysis)
            f0_item = QTableWidgetItem(f"{stn.f0:.2f}" if stn.f0 else "")
            f0_item.setFlags(f0_item.flags() & ~Qt.ItemIsEditable)
            f0_item.setForeground(QBrush(QColor("#2980b9")))
            self.table.setItem(row, COL_F0, f0_item)

            # Status
            status = "ready" if stn.has_coordinates and stn.has_vs else "incomplete"
            if stn.f0:
                status = "analyzed"
            status_item = QTableWidgetItem(status)
            status_item.setFlags(status_item.flags() & ~Qt.ItemIsEditable)
            if status == "incomplete":
                status_item.setForeground(QBrush(QColor("#e67e22")))
            elif status == "analyzed":
                status_item.setForeground(QBrush(QColor("#27ae60")))
            self.table.setItem(row, COL_STATUS, status_item)

        n = self.table.rowCount()
        self._count_label.setText(f"({n} stations)")
        self.table.blockSignals(False)

    def _sync_registry_from_table(self) -> None:
        """Read edited values back from the table into the registry."""
        if self._registry is None:
            return

        for row in range(self.table.rowCount()):
            if row >= len(self._registry.stations):
                break
            stn = self._registry.stations[row]

            name_item = self.table.item(row, COL_NAME)
            if name_item:
                stn.name = name_item.text().strip() or None

            sensor_item = self.table.item(row, COL_SENSOR)
            if sensor_item:
                stn.sensor = sensor_item.text().strip() or None

            for col, attr in [
                (COL_X, "x"), (COL_Y, "y"),
                (COL_ELEV, "elevation"), (COL_VS, "vs_avg"),
            ]:
                item = self.table.item(row, col)
                if item:
                    text = item.text().strip()
                    try:
                        setattr(stn, attr, float(text) if text else None)
                    except ValueError:
                        setattr(stn, attr, None)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_import_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Station Registry",
            "",
            "Data Files (*.csv *.txt *.xlsx *.xls);;All Files (*)",
        )
        if not path:
            return

        try:
            reg = StationRegistry.from_file(path)
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to parse file:\n{e}")
            return

        self._registry = reg
        self._refresh_table()
        self.csv_imported.emit(path)
        self.registry_changed.emit()

    def _on_add_station(self) -> None:
        if self._registry is None:
            self._registry = StationRegistry()

        n = len(self._registry.stations) + 1
        new_id = f"station_{n:03d}"
        self._registry.add_station(RegistryStation(id=new_id))
        self._refresh_table()
        self.registry_changed.emit()

    def _on_remove_station(self) -> None:
        row = self.table.currentRow()
        if row < 0 or self._registry is None:
            return
        if row < len(self._registry.stations):
            stn = self._registry.stations[row]
            self._registry.remove_station(stn.id)
            self._refresh_table()
            self.registry_changed.emit()

    def _on_cell_changed(self, row: int, col: int) -> None:
        self._sync_registry_from_table()
        self.registry_changed.emit()
