"""
Project Hub — main dashboard window for an HV Pro project.

Shows the station registry table, module cards, and recent activity.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QCloseEvent
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QStatusBar, QScrollArea, QFrame, QTextEdit, QSplitter,
    QAction, QMenuBar, QMessageBox, QGroupBox, QGridLayout,
)

from ..project import (
    Project, MODULE_BATCH, MODULE_BEDROCK, MODULE_HVSTRIP, MODULE_INVERSION,
)
from ..project_io import add_recent_project
from .module_card import ModuleCard
from .station_table import StationTableWidget


class ProjectHubWindow(QMainWindow):
    """Main dashboard for an HV Pro project.

    Signals
    -------
    open_batch_requested : str
        Emitted with batch_id when user clicks Open on Batch Processing card.
    open_bedrock_requested : str
        Emitted with map_id when user clicks Open on Bedrock Mapping card.
    open_hvstrip_requested : str
        Emitted with profile_id when user clicks Open on HV Strip card.
    open_inversion_requested : str
        Emitted when user clicks Open on Invert HVSR card.
    open_hvsr_requested
        Emitted when user clicks Open on HVSR Analysis card.
    generate_reports_requested
        Emitted when user clicks Generate on Reports card.
    """

    open_batch_requested = pyqtSignal(str)
    open_bedrock_requested = pyqtSignal(str)
    open_hvstrip_requested = pyqtSignal(str)
    open_inversion_requested = pyqtSignal()
    open_hvsr_requested = pyqtSignal()
    generate_reports_requested = pyqtSignal()

    def __init__(
        self,
        project: Project,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._project = project

        self.setWindowTitle(f"HV Pro — {project.name}")
        self.setMinimumSize(800, 600)

        add_recent_project(str(project.hvpro_file))

        self._build_menu()
        self._build_ui()
        self._refresh()

        # Status bar
        sb = QStatusBar()
        sb.showMessage(f"📁 {project.path}")
        self.setStatusBar(sb)

    # ------------------------------------------------------------------
    # Menu bar
    # ------------------------------------------------------------------

    def _build_menu(self) -> None:
        mb = self.menuBar()

        file_menu = mb.addMenu("&File")

        save_action = QAction("&Save Project", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._on_save)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        close_action = QAction("&Close Project", self)
        close_action.triggered.connect(self.close)
        file_menu.addAction(close_action)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(15, 10, 15, 10)
        main_layout.setSpacing(10)

        # --- Splitter: station table (top) + bottom panel ---
        splitter = QSplitter(Qt.Vertical)

        # Top: Station Registry Table
        self.station_table = StationTableWidget()
        self.station_table.set_registry(self._project.registry)
        self.station_table.registry_changed.connect(self._on_registry_changed)
        splitter.addWidget(self.station_table)

        # Bottom panel
        bottom = QWidget()
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(0, 5, 0, 0)
        bottom_layout.setSpacing(10)

        # --- Module cards ---
        cards_group = QGroupBox("Modules")
        cards_grid = QGridLayout(cards_group)
        cards_grid.setSpacing(12)

        # Row 0
        self.card_batch = ModuleCard("Batch\nProcessing", "📦", "batches")
        self.card_batch.open_requested.connect(self._on_open_batch)
        cards_grid.addWidget(self.card_batch, 0, 0)

        self.card_bedrock = ModuleCard("Bedrock\nMapping", "🗺️", "maps")
        self.card_bedrock.open_requested.connect(self._on_open_bedrock)
        cards_grid.addWidget(self.card_bedrock, 0, 1)

        self.card_hvstrip = ModuleCard("HV Strip\nProgressive", "📈", "profiles")
        self.card_hvstrip.open_requested.connect(self._on_open_hvstrip)
        cards_grid.addWidget(self.card_hvstrip, 0, 2)

        # Row 1
        self.card_inversion = ModuleCard("Invert\nHVSR", "🔄", "items")
        self.card_inversion.open_requested.connect(
            self.open_inversion_requested.emit
        )
        cards_grid.addWidget(self.card_inversion, 1, 0)

        self.card_hvsr = ModuleCard("HVSR\nAnalysis", "📊", "stations")
        self.card_hvsr.open_requested.connect(self.open_hvsr_requested.emit)
        cards_grid.addWidget(self.card_hvsr, 1, 1)

        self.card_reports = ModuleCard("Reports", "📄", "")
        self.card_reports.set_button_text("Generate")
        self.card_reports.open_requested.connect(
            self.generate_reports_requested.emit
        )
        cards_grid.addWidget(self.card_reports, 1, 2)

        bottom_layout.addWidget(cards_group)

        # --- Recent Activity ---
        activity_group = QGroupBox("Recent Activity")
        activity_layout = QVBoxLayout(activity_group)

        self.activity_log = QTextEdit()
        self.activity_log.setReadOnly(True)
        self.activity_log.setMaximumHeight(100)
        self.activity_log.setStyleSheet("font-size: 8pt; color: #555;")
        activity_layout.addWidget(self.activity_log)

        bottom_layout.addWidget(activity_group)

        splitter.addWidget(bottom)
        splitter.setStretchFactor(0, 2)  # Station table gets more space
        splitter.setStretchFactor(1, 3)

        main_layout.addWidget(splitter)

    # ------------------------------------------------------------------
    # Refresh / Sync
    # ------------------------------------------------------------------

    def _refresh(self) -> None:
        """Refresh all UI elements from the project state."""
        p = self._project

        # Module card counts
        for module_name, card in [
            (MODULE_BATCH, self.card_batch),
            (MODULE_BEDROCK, self.card_bedrock),
            (MODULE_HVSTRIP, self.card_hvstrip),
            (MODULE_INVERSION, self.card_inversion),
        ]:
            ms = p.modules.get(module_name)
            card.set_item_count(len(ms.items) if ms else 0)

        # Activity log
        self.activity_log.clear()
        for entry in reversed(p.recent_activity[-20:]):
            self.activity_log.append(f"• {entry.msg}  —  {entry.ts[:16]}")

        if not p.recent_activity:
            self.activity_log.setPlainText("No activity yet.")

    @property
    def project(self) -> Project:
        return self._project

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _on_registry_changed(self) -> None:
        self._project.registry = self.station_table.get_registry()
        self._project.save()

    def _on_save(self) -> None:
        self._project.registry = self.station_table.get_registry()
        self._project.save()
        self.statusBar().showMessage("Project saved.", 3000)

    def _on_open_batch(self) -> None:
        ms = self._project.modules.get(MODULE_BATCH)
        if ms and ms.last_active:
            batch_id = ms.last_active
        else:
            batch_id = self._project.next_item_id(MODULE_BATCH, "batch_")
        self._project.ensure_module_dir(MODULE_BATCH, batch_id)
        self._project.save()
        self.open_batch_requested.emit(batch_id)

    def _on_open_bedrock(self) -> None:
        ms = self._project.modules.get(MODULE_BEDROCK)
        if ms and ms.last_active:
            map_id = ms.last_active
        else:
            map_id = self._project.next_item_id(MODULE_BEDROCK, "map_")
        self._project.ensure_module_dir(MODULE_BEDROCK, map_id)
        self._project.save()
        self.open_bedrock_requested.emit(map_id)

    def _on_open_hvstrip(self) -> None:
        ms = self._project.modules.get(MODULE_HVSTRIP)
        if ms and ms.last_active:
            profile_id = ms.last_active
        else:
            profile_id = self._project.next_item_id(MODULE_HVSTRIP, "profile_")
        self._project.ensure_module_dir(MODULE_HVSTRIP, profile_id)
        self._project.save()
        self.open_hvstrip_requested.emit(profile_id)

    def closeEvent(self, event: QCloseEvent) -> None:
        # Auto-save on close
        self._project.registry = self.station_table.get_registry()
        self._project.save()
        super().closeEvent(event)
