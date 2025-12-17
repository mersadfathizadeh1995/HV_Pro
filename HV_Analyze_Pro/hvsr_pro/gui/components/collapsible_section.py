"""
Collapsible Section
===================

A lightweight collapsible section widget.
Extracted from properties_dock.py.
"""

try:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QFrame, QPushButton
    )
    from PyQt5.QtCore import Qt, pyqtSignal
    from PyQt5.QtGui import QFont
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


if HAS_PYQT5:
    class CollapsibleSection(QWidget):
        """
        A lightweight collapsible section widget.
        
        Features:
        - Simple header with toggle button
        - Content container for child widgets
        - Minimal styling
        
        Signals:
            toggled: Emitted when collapsed state changes (bool is_collapsed)
        """
        
        toggled = pyqtSignal(bool)
        
        def __init__(self, title: str, parent=None):
            super().__init__(parent)
            self._title = title
            self._is_collapsed = False
            
            self._init_ui()
        
        def _init_ui(self):
            """Initialize the user interface."""
            main_layout = QVBoxLayout(self)
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.setSpacing(2)
            
            # Header button
            self.header_btn = QPushButton(f"v {self._title}")
            self.header_btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 5px;
                    background-color: #f0f0f0;
                    border: 1px solid #ccc;
                    border-radius: 3px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #e0e0e0;
                }
            """)
            self.header_btn.clicked.connect(self.toggle)
            main_layout.addWidget(self.header_btn)
            
            # Content container
            self.content = QWidget()
            self.content_layout = QVBoxLayout(self.content)
            self.content_layout.setContentsMargins(10, 5, 10, 5)
            self.content_layout.setSpacing(5)
            main_layout.addWidget(self.content)
        
        def toggle(self):
            """Toggle the section's collapsed state."""
            self._is_collapsed = not self._is_collapsed
            self.content.setVisible(not self._is_collapsed)
            
            # Update header text
            arrow = ">" if self._is_collapsed else "v"
            self.header_btn.setText(f"{arrow} {self._title}")
            
            self.toggled.emit(self._is_collapsed)
        
        def is_collapsed(self) -> bool:
            """Check if section is collapsed."""
            return self._is_collapsed
        
        def set_collapsed(self, collapsed: bool):
            """Set collapsed state."""
            if self._is_collapsed != collapsed:
                self.toggle()
        
        def expand(self):
            """Expand the section."""
            if self._is_collapsed:
                self.toggle()
        
        def collapse(self):
            """Collapse the section."""
            if not self._is_collapsed:
                self.toggle()
        
        def add_widget(self, widget):
            """Add a widget to the content area."""
            self.content_layout.addWidget(widget)
        
        def add_layout(self, layout):
            """Add a layout to the content area."""
            self.content_layout.addLayout(layout)
        
        def get_content_layout(self) -> QVBoxLayout:
            """Get the content layout."""
            return self.content_layout
        
        def set_title(self, title: str):
            """Set the section title."""
            self._title = title
            arrow = ">" if self._is_collapsed else "v"
            self.header_btn.setText(f"{arrow} {title}")

else:
    class CollapsibleSection:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass

