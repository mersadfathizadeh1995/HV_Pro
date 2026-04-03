"""
Sensor File Mapping Dialog
===========================

Shows how files are routed to stations via sensor patterns before
confirming a batch import. User can review and override assignments.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QBrush
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QDialogButtonBox, QGroupBox,
)


class SensorFileMappingDialog(QDialog):
    """Preview dialog showing file → sensor → station routing.

    Displayed after batch importing files when a sensor config + station
    registry are available.
    """

    def __init__(
        self,
        parent=None,
        station_files: Optional[Dict[int, List[str]]] = None,
        unmatched: Optional[List[str]] = None,
        sensor_labels: Optional[Dict[int, str]] = None,
    ):
        """
        Parameters
        ----------
        station_files : dict
            Maps station_num → [file_paths] (the routing result).
        unmatched : list
            Files that matched no sensor.
        sensor_labels : dict
            Maps station_num → sensor display name (for info).
        """
        super().__init__(parent)
        self.setWindowTitle("Sensor File Routing — Review")
        self.setMinimumSize(750, 450)

        self._station_files = station_files or {}
        self._unmatched = unmatched or []
        self._sensor_labels = sensor_labels or {}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        # Summary
        n_stations = len(self._station_files)
        n_files = sum(len(v) for v in self._station_files.values())
        n_unmatched = len(self._unmatched)

        summary = QLabel(
            f"<b>{n_files}</b> file(s) routed to <b>{n_stations}</b> station(s)"
            + (f", <span style='color:red'>{n_unmatched} unmatched</span>" if n_unmatched else "")
        )
        layout.addWidget(summary)

        # Routing table
        grp = QGroupBox("File → Station Routing")
        grp_layout = QVBoxLayout(grp)

        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels([
            "Station #", "Sensor", "# Files", "Sample Files",
        ])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self._table.setAlternatingRowColors(True)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)

        for stn_num in sorted(self._station_files.keys()):
            files = self._station_files[stn_num]
            row = self._table.rowCount()
            self._table.insertRow(row)

            self._table.setItem(row, 0, QTableWidgetItem(str(stn_num)))

            sensor = self._sensor_labels.get(stn_num, "—")
            self._table.setItem(row, 1, QTableWidgetItem(str(sensor)))

            self._table.setItem(row, 2, QTableWidgetItem(str(len(files))))

            sample = ", ".join(os.path.basename(f) for f in files[:3])
            if len(files) > 3:
                sample += f" (+{len(files)-3} more)"
            self._table.setItem(row, 3, QTableWidgetItem(sample))

        # Unmatched files
        if self._unmatched:
            row = self._table.rowCount()
            self._table.insertRow(row)

            item = QTableWidgetItem("—")
            item.setForeground(QBrush(QColor("#e74c3c")))
            self._table.setItem(row, 0, item)

            item2 = QTableWidgetItem("UNMATCHED")
            item2.setForeground(QBrush(QColor("#e74c3c")))
            self._table.setItem(row, 1, item2)

            self._table.setItem(row, 2, QTableWidgetItem(str(n_unmatched)))

            sample = ", ".join(os.path.basename(f) for f in self._unmatched[:3])
            if n_unmatched > 3:
                sample += f" (+{n_unmatched-3} more)"
            item3 = QTableWidgetItem(sample)
            item3.setForeground(QBrush(QColor("#e74c3c")))
            self._table.setItem(row, 3, item3)

        grp_layout.addWidget(self._table)
        layout.addWidget(grp)

        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_station_files(self) -> Dict[int, List[str]]:
        """Return the (possibly modified) station→files mapping."""
        return self._station_files
