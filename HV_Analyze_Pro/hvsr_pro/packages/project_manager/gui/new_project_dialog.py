"""
New Project Dialog — lets the user define a project name, location, and
optionally import a station registry CSV.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit,
    QFileDialog, QMessageBox, QGroupBox, QWidget,
)


class NewProjectDialog(QDialog):
    """Dialog for creating a new HV Pro project."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("New Project")
        self.setMinimumSize(500, 400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._project_name: Optional[str] = None
        self._project_location: Optional[str] = None
        self._author: str = ""
        self._description: str = ""
        self._csv_path: Optional[str] = None

        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(12)

        title = QLabel("Create New Project")
        title_font = QFont()
        title_font.setPointSize(13)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # --- Project info ---
        info_group = QGroupBox("Project Information")
        form = QFormLayout(info_group)
        form.setSpacing(8)

        self.edit_name = QLineEdit()
        self.edit_name.setPlaceholderText("e.g. Site_Investigation_2026")
        form.addRow("Name:", self.edit_name)

        loc_layout = QHBoxLayout()
        self.edit_location = QLineEdit()
        self.edit_location.setPlaceholderText("Select project directory...")
        self.edit_location.setReadOnly(True)
        loc_layout.addWidget(self.edit_location)
        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self._browse_location)
        loc_layout.addWidget(btn_browse)
        form.addRow("Location:", loc_layout)

        self.edit_author = QLineEdit()
        self.edit_author.setPlaceholderText("Your name (optional)")
        form.addRow("Author:", self.edit_author)

        self.edit_description = QTextEdit()
        self.edit_description.setPlaceholderText("Brief project description (optional)")
        self.edit_description.setMaximumHeight(60)
        form.addRow("Description:", self.edit_description)

        layout.addWidget(info_group)

        # --- Station registry import ---
        csv_group = QGroupBox("Station Registry (optional)")
        csv_layout = QVBoxLayout(csv_group)

        csv_info = QLabel(
            "Import a CSV/Excel file with station information.\n"
            "Columns can include: id, name, x, y, elevation, vs_avg\n"
            "All columns except 'id' are optional."
        )
        csv_info.setStyleSheet("color: #666; font-size: 8pt;")
        csv_info.setWordWrap(True)
        csv_layout.addWidget(csv_info)

        csv_btn_layout = QHBoxLayout()
        self.edit_csv = QLineEdit()
        self.edit_csv.setPlaceholderText("No file selected")
        self.edit_csv.setReadOnly(True)
        csv_btn_layout.addWidget(self.edit_csv)
        btn_csv = QPushButton("Import CSV...")
        btn_csv.clicked.connect(self._browse_csv)
        csv_btn_layout.addWidget(btn_csv)
        csv_layout.addLayout(csv_btn_layout)

        self.csv_status = QLabel("")
        self.csv_status.setStyleSheet("font-size: 8pt;")
        csv_layout.addWidget(self.csv_status)

        layout.addWidget(csv_group)

        # --- Buttons ---
        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setMinimumWidth(80)
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

        self.btn_create = QPushButton("Create Project")
        self.btn_create.setMinimumWidth(120)
        self.btn_create.setDefault(True)
        self.btn_create.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2980b9; }
            QPushButton:pressed { background-color: #2471a3; }
        """)
        self.btn_create.clicked.connect(self._on_create)
        btn_layout.addWidget(self.btn_create)

        layout.addLayout(btn_layout)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _browse_location(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Select Project Directory",
            os.path.expanduser("~"),
        )
        if folder:
            self.edit_location.setText(folder)

    def _browse_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Station Registry",
            "",
            "Data Files (*.csv *.txt *.xlsx *.xls);;All Files (*)",
        )
        if path:
            self.edit_csv.setText(path)
            self._csv_path = path
            # Try parsing to show preview
            try:
                from ..station_registry import StationRegistry
                reg = StationRegistry.from_file(path)
                n = len(reg.stations)
                n_coords = len(reg.stations_with_coords())
                self.csv_status.setText(
                    f"✓ {n} stations found ({n_coords} with coordinates)"
                )
                self.csv_status.setStyleSheet("color: green; font-size: 8pt;")
            except Exception as e:
                self.csv_status.setText(f"⚠ Error: {e}")
                self.csv_status.setStyleSheet("color: red; font-size: 8pt;")
                self._csv_path = None

    def _on_create(self) -> None:
        name = self.edit_name.text().strip()
        location = self.edit_location.text().strip()

        if not name:
            QMessageBox.warning(self, "Missing Name", "Please enter a project name.")
            return
        if not location:
            QMessageBox.warning(self, "Missing Location",
                                "Please select a project directory.")
            return

        self._project_name = name
        self._project_location = str(Path(location) / name)
        self._author = self.edit_author.text().strip()
        self._description = self.edit_description.toPlainText().strip()
        self.accept()

    # ------------------------------------------------------------------
    # Result accessors
    # ------------------------------------------------------------------

    @property
    def project_name(self) -> Optional[str]:
        return self._project_name

    @property
    def project_location(self) -> Optional[str]:
        return self._project_location

    @property
    def author(self) -> str:
        return self._author

    @property
    def description(self) -> str:
        return self._description

    @property
    def csv_path(self) -> Optional[str]:
        return self._csv_path
