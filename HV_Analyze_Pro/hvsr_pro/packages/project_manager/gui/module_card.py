"""
Module Card — a clickable card widget representing one HV Pro module
in the Project Hub dashboard.
"""

from __future__ import annotations

from typing import Optional

from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QLabel, QPushButton, QSizePolicy, QWidget,
)


class ModuleCard(QFrame):
    """A card widget for a single module (Batch, Bedrock, etc.).

    Parameters
    ----------
    title : str
        Module display name.
    icon_text : str
        Emoji or short text shown as icon.
    item_label : str
        What items this module creates (e.g. "batches", "maps").
    parent : QWidget, optional
    """

    open_requested = pyqtSignal()

    def __init__(
        self,
        title: str,
        icon_text: str = "📦",
        item_label: str = "items",
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self._title = title
        self._icon_text = icon_text
        self._item_label = item_label
        self._item_count = 0

        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.setMinimumSize(160, 120)
        self.setMaximumSize(200, 140)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.setStyleSheet("""
            ModuleCard {
                background-color: #ffffff;
                border: 1px solid #ddd;
                border-radius: 8px;
            }
            ModuleCard:hover {
                border-color: #3498db;
                background-color: #f8fbfe;
            }
        """)

        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        # Icon + title
        icon_label = QLabel(self._icon_text)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_font = QFont()
        icon_font.setPointSize(18)
        icon_label.setFont(icon_font)
        layout.addWidget(icon_label)

        title_label = QLabel(self._title)
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(9)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # Item count
        self._count_label = QLabel(f"0 {self._item_label}")
        self._count_label.setAlignment(Qt.AlignCenter)
        self._count_label.setStyleSheet("color: #888; font-size: 8pt;")
        layout.addWidget(self._count_label)

        # Open button
        btn = QPushButton("Open")
        btn.setMinimumHeight(26)
        btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 8pt;
                font-weight: bold;
                padding: 4px 12px;
            }
            QPushButton:hover { background-color: #2980b9; }
        """)
        btn.clicked.connect(self.open_requested.emit)
        layout.addWidget(btn, alignment=Qt.AlignCenter)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_item_count(self, count: int) -> None:
        self._item_count = count
        self._count_label.setText(f"{count} {self._item_label}")

    def set_button_text(self, text: str) -> None:
        """Change the action button label (e.g. 'Generate' for Reports)."""
        btn = self.findChild(QPushButton)
        if btn:
            btn.setText(text)
