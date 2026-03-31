"""
Module Card — a clickable card widget representing one HV Pro module
in the Project Hub dashboard.
"""

from __future__ import annotations

from typing import List, Optional

from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSizePolicy, QWidget, QComboBox, QMenu, QAction,
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
    open_item_requested = pyqtSignal(str)
    new_item_requested = pyqtSignal()
    delete_item_requested = pyqtSignal(str)

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
        self.setMinimumSize(160, 150)
        self.setMaximumSize(220, 180)
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

        # Item dropdown (hidden when no items)
        self._item_combo = QComboBox()
        self._item_combo.setMaximumHeight(22)
        self._item_combo.setStyleSheet("font-size: 8pt;")
        self._item_combo.setContextMenuPolicy(Qt.CustomContextMenu)
        self._item_combo.customContextMenuRequested.connect(
            self._show_item_context_menu)
        self._item_combo.hide()
        layout.addWidget(self._item_combo)

        # Button row
        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)

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
        btn.clicked.connect(self._on_open_clicked)
        btn_row.addWidget(btn)

        new_btn = QPushButton("+")
        new_btn.setMinimumHeight(26)
        new_btn.setMaximumWidth(30)
        new_btn.setToolTip("Create new")
        new_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 4px;
                font-size: 10pt;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #229954; }
        """)
        new_btn.clicked.connect(self.new_item_requested.emit)
        btn_row.addWidget(new_btn)

        layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_item_count(self, count: int) -> None:
        self._item_count = count
        self._count_label.setText(f"{count} {self._item_label}")

    def set_items(self, items: List[str], last_active: Optional[str] = None) -> None:
        """Populate the item dropdown and update the count."""
        self._item_combo.blockSignals(True)
        self._item_combo.clear()
        for item_id in items:
            self._item_combo.addItem(item_id, item_id)
        self._item_combo.blockSignals(False)
        if items:
            self._item_combo.show()
            if last_active and last_active in items:
                self._item_combo.setCurrentText(last_active)
        else:
            self._item_combo.hide()
        self.set_item_count(len(items))

    def selected_item(self) -> Optional[str]:
        """Return the currently selected item id, or None."""
        if self._item_combo.count() == 0:
            return None
        return self._item_combo.currentData()

    def set_button_text(self, text: str) -> None:
        """Change the action button label (e.g. 'Generate' for Reports)."""
        btn = self.findChild(QPushButton)
        if btn:
            btn.setText(text)

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    def _on_open_clicked(self) -> None:
        sel = self.selected_item()
        if sel:
            self.open_item_requested.emit(sel)
        self.open_requested.emit()

    def _show_item_context_menu(self, pos) -> None:
        sel = self.selected_item()
        if not sel:
            return
        menu = QMenu(self)
        delete_action = QAction(f"Delete '{sel}'", self)
        delete_action.triggered.connect(
            lambda: self.delete_item_requested.emit(sel))
        menu.addAction(delete_action)
        menu.exec_(self._item_combo.mapToGlobal(pos))
