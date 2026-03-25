"""
Sensor Pattern Editor Dialog
==============================

Allows users to define, test, and save sensor pattern configurations.
Each sensor gets a name, display label, and one or more regex patterns
that match filenames belonging to that sensor.
"""

from __future__ import annotations

import os
import re
from typing import List, Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QBrush
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QLabel, QLineEdit, QFileDialog,
    QMessageBox, QTextEdit, QSplitter, QDialogButtonBox,
)

from hvsr_pro.packages.batch_processing.sensor_config import (
    SensorConfig, SensorConfigManager,
)


class SensorPatternEditor(QDialog):
    """Dialog for defining and testing sensor file-matching patterns."""

    def __init__(self, parent=None, manager: Optional[SensorConfigManager] = None):
        super().__init__(parent)
        self.setWindowTitle("Sensor Pattern Editor")
        self.setMinimumSize(800, 550)

        self._manager = manager or SensorConfigManager.default()
        self._test_files: List[str] = []
        self._build_ui()
        self._refresh_table()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        splitter = QSplitter(Qt.Vertical)

        # --- Top: sensor config table ---
        top = QGroupBox("Sensor Definitions")
        top_layout = QVBoxLayout(top)

        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels([
            "Sensor ID", "Display Name", "File Patterns (regex, comma-separated)", "Matched",
        ])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Interactive)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._table.setAlternatingRowColors(True)
        top_layout.addWidget(self._table)

        btn_row = QHBoxLayout()
        btn_add = QPushButton("Add Sensor")
        btn_add.clicked.connect(self._on_add)
        btn_row.addWidget(btn_add)

        btn_remove = QPushButton("Remove Selected")
        btn_remove.clicked.connect(self._on_remove)
        btn_row.addWidget(btn_remove)

        btn_auto = QPushButton("Auto-Detect from Files...")
        btn_auto.clicked.connect(self._on_auto_detect)
        btn_row.addWidget(btn_auto)

        btn_defaults = QPushButton("Load Defaults (Centaur)")
        btn_defaults.clicked.connect(self._on_load_defaults)
        btn_row.addWidget(btn_defaults)

        btn_row.addStretch()

        btn_import = QPushButton("Import JSON...")
        btn_import.clicked.connect(self._on_import_json)
        btn_row.addWidget(btn_import)

        btn_export = QPushButton("Export JSON...")
        btn_export.clicked.connect(self._on_export_json)
        btn_row.addWidget(btn_export)

        top_layout.addLayout(btn_row)

        # --- Bottom: test panel ---
        bottom = QGroupBox("Test Matching")
        bottom_layout = QVBoxLayout(bottom)

        test_btn_row = QHBoxLayout()
        btn_load_files = QPushButton("Load Test Files...")
        btn_load_files.clicked.connect(self._on_load_test_files)
        test_btn_row.addWidget(btn_load_files)

        btn_test = QPushButton("Run Test")
        btn_test.clicked.connect(self._on_run_test)
        btn_test.setStyleSheet("font-weight: bold;")
        test_btn_row.addWidget(btn_test)

        self._test_count_label = QLabel("(0 files loaded)")
        test_btn_row.addWidget(self._test_count_label)
        test_btn_row.addStretch()
        bottom_layout.addLayout(test_btn_row)

        self._test_output = QTextEdit()
        self._test_output.setReadOnly(True)
        self._test_output.setMaximumHeight(180)
        bottom_layout.addWidget(self._test_output)

        splitter.addWidget(top)
        splitter.addWidget(bottom)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

        # Dialog buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------
    # Table ↔ manager sync
    # ------------------------------------------------------------------

    def _refresh_table(self) -> None:
        self._table.setRowCount(0)
        for cfg in self._manager.configs:
            row = self._table.rowCount()
            self._table.insertRow(row)

            self._table.setItem(row, 0, QTableWidgetItem(cfg.sensor_id))
            self._table.setItem(row, 1, QTableWidgetItem(cfg.display_name))
            self._table.setItem(row, 2, QTableWidgetItem(", ".join(cfg.file_patterns)))

            matched_item = QTableWidgetItem("—")
            matched_item.setFlags(matched_item.flags() & ~Qt.ItemIsEditable)
            self._table.setItem(row, 3, matched_item)

    def _read_table_to_manager(self) -> None:
        """Read edited table rows back into the manager."""
        configs = []
        for row in range(self._table.rowCount()):
            sid = (self._table.item(row, 0).text().strip()
                   if self._table.item(row, 0) else "")
            name = (self._table.item(row, 1).text().strip()
                    if self._table.item(row, 1) else sid)
            patterns_text = (self._table.item(row, 2).text().strip()
                             if self._table.item(row, 2) else "")

            patterns = [p.strip() for p in patterns_text.split(",") if p.strip()]

            if sid:
                configs.append(SensorConfig(
                    sensor_id=sid,
                    display_name=name or sid,
                    file_patterns=patterns,
                ))
        self._manager = SensorConfigManager(configs)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_add(self) -> None:
        n = self._table.rowCount() + 1
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._table.setItem(row, 0, QTableWidgetItem(str(n)))
        self._table.setItem(row, 1, QTableWidgetItem(f"Sensor {n}"))
        self._table.setItem(row, 2, QTableWidgetItem(""))
        matched_item = QTableWidgetItem("—")
        matched_item.setFlags(matched_item.flags() & ~Qt.ItemIsEditable)
        self._table.setItem(row, 3, matched_item)

    def _on_remove(self) -> None:
        rows = set(idx.row() for idx in self._table.selectedIndexes())
        for r in sorted(rows, reverse=True):
            self._table.removeRow(r)

    def _on_load_defaults(self) -> None:
        self._manager = SensorConfigManager.default()
        self._refresh_table()

    def _on_auto_detect(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Files for Auto-Detection", "",
            "Seismic Files (*.miniseed *.mseed *.saf *.sac);;All (*)",
        )
        if not files:
            return
        fnames = [os.path.basename(f) for f in files]
        self._manager = SensorConfigManager.auto_detect(fnames)
        if not self._manager.configs:
            QMessageBox.information(
                self, "Auto-Detect",
                "No sensor patterns detected from filenames.",
            )
            return
        self._refresh_table()
        self._test_files = files
        self._test_count_label.setText(f"({len(files)} files loaded)")

    def _on_import_json(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Import Sensor Config", "",
            "JSON Files (*.json);;All (*)",
        )
        if path:
            try:
                self._manager = SensorConfigManager.load(path)
                self._refresh_table()
            except Exception as e:
                QMessageBox.critical(self, "Import Error", str(e))

    def _on_export_json(self) -> None:
        self._read_table_to_manager()
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Sensor Config", "sensor_config.json",
            "JSON Files (*.json)",
        )
        if path:
            try:
                self._manager.save(path)
            except Exception as e:
                QMessageBox.critical(self, "Export Error", str(e))

    def _on_load_test_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Files to Test", "",
            "Seismic Files (*.miniseed *.mseed *.saf *.sac);;All (*)",
        )
        if files:
            self._test_files = files
            self._test_count_label.setText(f"({len(files)} files loaded)")

    def _on_run_test(self) -> None:
        self._read_table_to_manager()

        if not self._test_files:
            self._test_output.setPlainText("No test files loaded. Click 'Load Test Files...' first.")
            return

        fnames = [os.path.basename(f) for f in self._test_files]
        result = self._manager.match_files(fnames)

        lines = []
        total_matched = 0
        for sid in sorted(result.keys()):
            if sid == "__unmatched__":
                continue
            cfg = self._manager.get_sensor(sid)
            label = cfg.display_name if cfg else sid
            count = len(result[sid])
            total_matched += count
            lines.append(f"✓ Sensor {sid} ({label}): {count} files")
            for fn in result[sid][:3]:
                lines.append(f"    {fn}")
            if count > 3:
                lines.append(f"    ... +{count - 3} more")

        unmatched = result.get("__unmatched__", [])
        if unmatched:
            lines.append(f"\n✗ Unmatched: {len(unmatched)} files")
            for fn in unmatched[:5]:
                lines.append(f"    {fn}")
            if len(unmatched) > 5:
                lines.append(f"    ... +{len(unmatched) - 5} more")

        lines.insert(0, f"Matched {total_matched}/{len(fnames)} files "
                        f"across {len(result) - (1 if unmatched else 0)} sensors\n")

        self._test_output.setPlainText("\n".join(lines))

        # Update match counts in table
        for row in range(self._table.rowCount()):
            sid_item = self._table.item(row, 0)
            if sid_item:
                sid = sid_item.text().strip()
                count = len(result.get(sid, []))
                matched_item = self._table.item(row, 3)
                if matched_item:
                    matched_item.setText(str(count))
                    if count > 0:
                        matched_item.setForeground(QBrush(QColor("#27ae60")))
                    else:
                        matched_item.setForeground(QBrush(QColor("#e74c3c")))

    # ------------------------------------------------------------------
    # Public results
    # ------------------------------------------------------------------

    def get_manager(self) -> SensorConfigManager:
        """Return the SensorConfigManager after dialog closes."""
        self._read_table_to_manager()
        return self._manager
