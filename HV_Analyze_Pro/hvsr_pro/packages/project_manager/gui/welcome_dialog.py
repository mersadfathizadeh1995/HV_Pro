"""
Welcome Dialog — shown at application startup.

Provides options to:
- Create a new project
- Open an existing project
- Select from recent projects
- Quick Analysis (no project)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QPixmap
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QFileDialog, QCheckBox,
    QFrame, QSizePolicy, QWidget,
)

from ..project_io import load_recent_projects, add_recent_project


class WelcomeDialog(QDialog):
    """Startup dialog for HV Analyze Pro.

    Signals
    -------
    project_created : str
        Emitted with the new project directory path.
    project_opened : str
        Emitted with the path to ``project.hvpro``.
    quick_analysis_requested : (no args)
        User wants to skip project mode.
    """

    project_created = pyqtSignal(str)
    project_opened = pyqtSignal(str)
    quick_analysis_requested = pyqtSignal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setWindowTitle("HV Analyze Pro")
        self.setMinimumSize(520, 480)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._result_action: Optional[str] = None
        self._result_path: Optional[str] = None

        self._build_ui()
        self._populate_recent()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 25, 30, 20)
        layout.setSpacing(12)

        # --- Header ---
        header = QLabel("🌊  HV Analyze Pro")
        header.setAlignment(Qt.AlignCenter)
        header_font = QFont()
        header_font.setPointSize(18)
        header_font.setBold(True)
        header.setFont(header_font)
        layout.addWidget(header)

        subtitle = QLabel("Horizontal-to-Vertical Spectral Ratio Analysis Suite")
        subtitle.setAlignment(Qt.AlignCenter)
        sub_font = QFont()
        sub_font.setPointSize(9)
        subtitle.setFont(sub_font)
        subtitle.setStyleSheet("color: #666;")
        layout.addWidget(subtitle)

        layout.addSpacing(10)

        # --- Action buttons ---
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(20)

        self.btn_new = self._make_action_button("📁", "New\nProject")
        self.btn_new.clicked.connect(self._on_new_project)
        btn_layout.addWidget(self.btn_new)

        self.btn_open = self._make_action_button("📂", "Open\nProject")
        self.btn_open.clicked.connect(self._on_open_project)
        btn_layout.addWidget(self.btn_open)

        layout.addLayout(btn_layout)

        layout.addSpacing(8)

        # --- Separator ---
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep)

        # --- Recent projects ---
        recent_label = QLabel("Recent Projects")
        recent_font = QFont()
        recent_font.setPointSize(10)
        recent_font.setBold(True)
        recent_label.setFont(recent_font)
        layout.addWidget(recent_label)

        self.recent_list = QListWidget()
        self.recent_list.setAlternatingRowColors(True)
        self.recent_list.setMinimumHeight(120)
        self.recent_list.doubleClicked.connect(self._on_recent_double_click)
        layout.addWidget(self.recent_list, stretch=1)

        # --- Quick Analysis ---
        layout.addSpacing(5)

        self.btn_quick = QPushButton("⚡  Quick Analysis (no project)")
        self.btn_quick.setMinimumHeight(36)
        self.btn_quick.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: 1px solid #ccc;
                border-radius: 4px;
                font-size: 10pt;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        self.btn_quick.clicked.connect(self._on_quick_analysis)
        layout.addWidget(self.btn_quick)

        # --- Don't show checkbox ---
        self.chk_dont_show = QCheckBox("Don't show at startup")
        self.chk_dont_show.setStyleSheet("color: #888; font-size: 8pt;")
        layout.addWidget(self.chk_dont_show, alignment=Qt.AlignRight)

    def _make_action_button(self, icon_text: str, label: str) -> QPushButton:
        btn = QPushButton(f"{icon_text}\n{label}")
        btn.setMinimumSize(180, 90)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                border: 2px solid #3498db;
                border-radius: 8px;
                font-size: 11pt;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #eaf4fc;
                border-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #d4e9f7;
            }
        """)
        return btn

    # ------------------------------------------------------------------
    # Recent projects
    # ------------------------------------------------------------------

    def _populate_recent(self) -> None:
        self.recent_list.clear()
        recent = load_recent_projects()

        if not recent:
            item = QListWidgetItem("No recent projects")
            item.setFlags(Qt.NoItemFlags)
            item.setForeground(Qt.gray)
            self.recent_list.addItem(item)
            return

        for path in recent:
            p = Path(path)
            project_name = p.parent.name
            item = QListWidgetItem(f"  {project_name}  —  {p.parent}")
            item.setData(Qt.UserRole, str(path))
            self.recent_list.addItem(item)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _on_new_project(self) -> None:
        self._result_action = "new"
        self.accept()

    def _on_open_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open HV Pro Project",
            "",
            "HV Pro Project (*.hvpro);;All Files (*)",
        )
        if path:
            self._result_path = path
            self._result_action = "open"
            add_recent_project(path)
            self.accept()

    def _on_recent_double_click(self) -> None:
        item = self.recent_list.currentItem()
        if item is None:
            return
        path = item.data(Qt.UserRole)
        if path and Path(path).exists():
            self._result_path = path
            self._result_action = "open"
            add_recent_project(path)
            self.accept()

    def _on_quick_analysis(self) -> None:
        self._result_action = "quick"
        self.accept()

    # ------------------------------------------------------------------
    # Result accessors
    # ------------------------------------------------------------------

    @property
    def result_action(self) -> Optional[str]:
        """'new', 'open', 'quick', or None if cancelled."""
        return self._result_action

    @property
    def result_path(self) -> Optional[str]:
        """Path to project.hvpro (for 'open' action)."""
        return self._result_path

    @property
    def dont_show_at_startup(self) -> bool:
        return self.chk_dont_show.isChecked()
