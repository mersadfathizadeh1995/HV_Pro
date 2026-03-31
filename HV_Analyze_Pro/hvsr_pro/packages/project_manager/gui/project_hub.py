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
    QFileDialog, QInputDialog,
)

from ..project import (
    Project, MODULE_BATCH, MODULE_BEDROCK, MODULE_HVSTRIP, MODULE_INVERSION,
    MODULE_HVSR_ANALYSIS,
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
    open_inversion_requested = pyqtSignal(str)
    open_hvsr_requested = pyqtSignal(str)
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

        save_as_action = QAction("Save Project &As...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self._on_save_as)
        file_menu.addAction(save_as_action)

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
        self.card_batch.open_item_requested.connect(
            lambda bid: self._on_open_batch(bid))
        self.card_batch.new_item_requested.connect(
            lambda: self._on_new_item(MODULE_BATCH, "batch_"))
        self.card_batch.delete_item_requested.connect(
            lambda iid: self._on_delete_item(MODULE_BATCH, iid))
        cards_grid.addWidget(self.card_batch, 0, 0)

        self.card_bedrock = ModuleCard("Bedrock\nMapping", "🗺️", "maps")
        self.card_bedrock.open_requested.connect(self._on_open_bedrock)
        self.card_bedrock.open_item_requested.connect(
            lambda mid: self._on_open_bedrock(mid))
        self.card_bedrock.new_item_requested.connect(
            lambda: self._on_new_item(MODULE_BEDROCK, "map_"))
        self.card_bedrock.delete_item_requested.connect(
            lambda iid: self._on_delete_item(MODULE_BEDROCK, iid))
        cards_grid.addWidget(self.card_bedrock, 0, 1)

        self.card_hvstrip = ModuleCard("HV Strip\nProgressive", "📈", "profiles")
        self.card_hvstrip.open_requested.connect(self._on_open_hvstrip)
        self.card_hvstrip.open_item_requested.connect(
            lambda pid: self._on_open_hvstrip(pid))
        self.card_hvstrip.new_item_requested.connect(
            lambda: self._on_new_item(MODULE_HVSTRIP, "profile_"))
        self.card_hvstrip.delete_item_requested.connect(
            lambda iid: self._on_delete_item(MODULE_HVSTRIP, iid))
        cards_grid.addWidget(self.card_hvstrip, 0, 2)

        # Row 1
        self.card_inversion = ModuleCard("Invert\nHVSR", "🔄", "inversions")
        self.card_inversion.open_requested.connect(self._on_open_inversion)
        self.card_inversion.open_item_requested.connect(
            lambda iid: self._on_open_inversion(iid))
        self.card_inversion.new_item_requested.connect(
            lambda: self._on_new_item(MODULE_INVERSION, "inv_"))
        self.card_inversion.delete_item_requested.connect(
            lambda iid: self._on_delete_item(MODULE_INVERSION, iid))
        cards_grid.addWidget(self.card_inversion, 1, 0)

        self.card_hvsr = ModuleCard("HVSR\nAnalysis", "📊", "analyses")
        self.card_hvsr.open_requested.connect(self._on_open_hvsr)
        self.card_hvsr.open_item_requested.connect(
            lambda aid: self._on_open_hvsr(aid))
        self.card_hvsr.new_item_requested.connect(
            lambda: self._on_new_item(MODULE_HVSR_ANALYSIS, "analysis_"))
        self.card_hvsr.delete_item_requested.connect(
            lambda iid: self._on_delete_item(MODULE_HVSR_ANALYSIS, iid))
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

        # Reload registry from disk in case another module updated it
        try:
            fresh = Project.load(p.hvpro_file)
            p.registry = fresh.registry
            p.modules = fresh.modules
            p.recent_activity = fresh.recent_activity
        except Exception:
            pass

        # Refresh station table
        self.station_table.set_registry(p.registry)

        # Module card counts & item lists
        for module_name, card in [
            (MODULE_BATCH, self.card_batch),
            (MODULE_BEDROCK, self.card_bedrock),
            (MODULE_HVSTRIP, self.card_hvstrip),
            (MODULE_INVERSION, self.card_inversion),
            (MODULE_HVSR_ANALYSIS, self.card_hvsr),
        ]:
            ms = p.modules.get(module_name)
            if ms:
                card.set_items(ms.items, ms.last_active)
            else:
                card.set_items([])

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

    def _on_save_as(self) -> None:
        """Clone the project to a new location."""
        dest = QFileDialog.getExistingDirectory(
            self, "Select destination folder for project copy",
            str(self._project.path.parent))
        if not dest:
            return
        new_name, ok = QInputDialog.getText(
            self, "Project Name",
            "Name for the copied project:",
            text=self._project.name + " (copy)")
        if not ok or not new_name.strip():
            return
        dest_path = Path(dest) / new_name.strip().replace(" ", "_")
        try:
            self._project.registry = self.station_table.get_registry()
            new_project = self._project.clone_to(dest_path, new_name.strip())
            QMessageBox.information(
                self, "Save As",
                f"Project saved as:\n{dest_path}")
            self.project_cloned = new_project  # parent can pick this up
            self.statusBar().showMessage(
                f"Saved copy: {new_name.strip()}", 5000)
        except Exception as exc:
            QMessageBox.critical(
                self, "Save As Failed", str(exc))

    def _on_open_batch(self, item_id: str = None) -> None:
        if item_id:
            batch_id = item_id
        else:
            ms = self._project.modules.get(MODULE_BATCH)
            if ms and ms.last_active:
                batch_id = ms.last_active
            else:
                batch_id = self._project.next_item_id(MODULE_BATCH, "batch_")
        self._project.ensure_module_dir(MODULE_BATCH, batch_id)
        self._project.save()
        self.open_batch_requested.emit(batch_id)

    def _on_open_bedrock(self, item_id: str = None) -> None:
        if item_id:
            map_id = item_id
        else:
            ms = self._project.modules.get(MODULE_BEDROCK)
            if ms and ms.last_active:
                map_id = ms.last_active
            else:
                map_id = self._project.next_item_id(MODULE_BEDROCK, "map_")
        self._project.ensure_module_dir(MODULE_BEDROCK, map_id)
        self._project.save()
        self.open_bedrock_requested.emit(map_id)

    def _on_open_hvstrip(self, item_id: str = None) -> None:
        if item_id:
            profile_id = item_id
        else:
            ms = self._project.modules.get(MODULE_HVSTRIP)
            if ms and ms.last_active:
                profile_id = ms.last_active
            else:
                profile_id = self._project.next_item_id(MODULE_HVSTRIP, "profile_")
        self._project.ensure_module_dir(MODULE_HVSTRIP, profile_id)
        self._project.save()
        self.open_hvstrip_requested.emit(profile_id)

    def _on_open_inversion(self, item_id: str = None) -> None:
        if item_id:
            inv_id = item_id
        else:
            ms = self._project.modules.get(MODULE_INVERSION)
            if ms and ms.last_active:
                inv_id = ms.last_active
            else:
                inv_id = self._project.next_item_id(MODULE_INVERSION, "inv_")
        self._project.ensure_module_dir(MODULE_INVERSION, inv_id)
        self._project.save()
        self.open_inversion_requested.emit(inv_id)

    def _on_open_hvsr(self, item_id: str = None) -> None:
        if item_id:
            analysis_id = item_id
        else:
            ms = self._project.modules.get(MODULE_HVSR_ANALYSIS)
            if ms and ms.last_active:
                analysis_id = ms.last_active
            else:
                analysis_id = self._project.next_item_id(
                    MODULE_HVSR_ANALYSIS, "analysis_"
                )
        self._project.ensure_module_dir(MODULE_HVSR_ANALYSIS, analysis_id)
        self._project.save()
        self.open_hvsr_requested.emit(analysis_id)

    # ------------------------------------------------------------------
    # Item management
    # ------------------------------------------------------------------

    def _on_new_item(self, module: str, prefix: str) -> None:
        """Create a new item for the given module and open it."""
        item_id = self._project.next_item_id(module, prefix)
        self._project.ensure_module_dir(module, item_id)
        self._project.save()
        self._refresh()

        # Emit the appropriate signal
        signal_map = {
            MODULE_BATCH: self.open_batch_requested,
            MODULE_BEDROCK: self.open_bedrock_requested,
            MODULE_HVSTRIP: self.open_hvstrip_requested,
            MODULE_INVERSION: self.open_inversion_requested,
            MODULE_HVSR_ANALYSIS: self.open_hvsr_requested,
        }
        sig = signal_map.get(module)
        if sig:
            sig.emit(item_id)

    def _on_delete_item(self, module: str, item_id: str) -> None:
        """Delete a module item after confirmation."""
        reply = QMessageBox.question(
            self, "Delete Item",
            f"Delete '{item_id}'? This removes all data in that folder.",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        import shutil
        item_dir = self._project.ensure_module_dir(module, item_id)
        if item_dir.exists():
            shutil.rmtree(str(item_dir), ignore_errors=True)
        ms = self._project.modules.get(module)
        if ms and item_id in ms.items:
            ms.items.remove(item_id)
            if ms.last_active == item_id:
                ms.last_active = ms.items[-1] if ms.items else None
        self._project.save()
        self._refresh()
        self.statusBar().showMessage(f"Deleted {item_id}.", 3000)

    def showEvent(self, event) -> None:
        """Refresh when the hub window becomes visible (e.g. after closing batch)."""
        super().showEvent(event)
        self._refresh()

    def closeEvent(self, event: QCloseEvent) -> None:
        # Auto-save on close
        self._project.registry = self.station_table.get_registry()
        self._project.save()
        super().closeEvent(event)
