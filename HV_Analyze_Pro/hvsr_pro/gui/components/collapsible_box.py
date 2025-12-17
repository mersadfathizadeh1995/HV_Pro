"""
Collapsible Group Box
=====================

A collapsible group box widget with toggle button.
Extracted from data_input_dialog.py.
"""

try:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QFrame, QToolButton
    )
    from PyQt5.QtCore import Qt, pyqtSignal
    from PyQt5.QtGui import QFont
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


if HAS_PYQT5:
    class CollapsibleGroupBox(QWidget):
        """
        A collapsible group box widget with toggle button.
        
        Features:
        - Click header to expand/collapse
        - Smooth transition
        - Customizable title
        - Content area for child widgets
        
        Signals:
            toggled: Emitted when collapsed state changes (bool is_collapsed)
        """
        
        toggled = pyqtSignal(bool)  # is_collapsed
        
        def __init__(self, title: str = "", parent=None):
            super().__init__(parent)
            self._is_collapsed = False
            self._title = title
            
            self._init_ui()
        
        def _init_ui(self):
            """Initialize the user interface."""
            # Main layout
            main_layout = QVBoxLayout(self)
            main_layout.setContentsMargins(0, 0, 0, 0)
            main_layout.setSpacing(0)
            
            # Header frame with toggle button
            self.header_frame = QFrame()
            self.header_frame.setStyleSheet("""
                QFrame {
                    background-color: #e8e8e8;
                    border: 1px solid #cccccc;
                    border-radius: 3px;
                    padding: 2px;
                }
                QFrame:hover {
                    background-color: #d0d0d0;
                }
            """)
            self.header_frame.setCursor(Qt.PointingHandCursor)
            self.header_frame.mousePressEvent = self._on_header_clicked
            
            header_layout = QHBoxLayout(self.header_frame)
            header_layout.setContentsMargins(5, 3, 5, 3)
            header_layout.setSpacing(5)
            
            # Toggle button (arrow indicator)
            self.toggle_btn = QToolButton()
            self.toggle_btn.setStyleSheet("""
                QToolButton {
                    border: none;
                    background: none;
                    font-size: 10px;
                }
            """)
            self.toggle_btn.setText("v")  # Down arrow when expanded
            self.toggle_btn.setFixedSize(16, 16)
            self.toggle_btn.clicked.connect(self.toggle)
            header_layout.addWidget(self.toggle_btn)
            
            # Title label
            from PyQt5.QtWidgets import QLabel
            self.title_label = QLabel(self._title)
            title_font = QFont()
            title_font.setBold(True)
            self.title_label.setFont(title_font)
            header_layout.addWidget(self.title_label)
            header_layout.addStretch()
            
            main_layout.addWidget(self.header_frame)
            
            # Content frame
            self.content_frame = QFrame()
            self.content_frame.setStyleSheet("""
                QFrame {
                    border: 1px solid #cccccc;
                    border-top: none;
                    border-radius: 0px 0px 3px 3px;
                    background-color: white;
                }
            """)
            
            self.content_layout = QVBoxLayout(self.content_frame)
            self.content_layout.setContentsMargins(10, 10, 10, 10)
            
            main_layout.addWidget(self.content_frame)
        
        def _on_header_clicked(self, event):
            """Handle header click."""
            self.toggle()
        
        def toggle(self):
            """Toggle collapsed state."""
            self._is_collapsed = not self._is_collapsed
            self.content_frame.setVisible(not self._is_collapsed)
            self.toggle_btn.setText(">" if self._is_collapsed else "v")
            self.toggled.emit(self._is_collapsed)
        
        def is_collapsed(self) -> bool:
            """Check if currently collapsed."""
            return self._is_collapsed
        
        def set_collapsed(self, collapsed: bool):
            """Set collapsed state."""
            if self._is_collapsed != collapsed:
                self.toggle()
        
        def expand(self):
            """Expand the content."""
            if self._is_collapsed:
                self.toggle()
        
        def collapse(self):
            """Collapse the content."""
            if not self._is_collapsed:
                self.toggle()
        
        def set_title(self, title: str):
            """Set the title text."""
            self._title = title
            self.title_label.setText(title)
        
        def get_title(self) -> str:
            """Get the title text."""
            return self._title
        
        def get_content_layout(self) -> QVBoxLayout:
            """Get the content layout for adding widgets."""
            return self.content_layout
        
        def add_widget(self, widget):
            """Add a widget to the content area."""
            self.content_layout.addWidget(widget)
        
        def add_layout(self, layout):
            """Add a layout to the content area."""
            self.content_layout.addLayout(layout)

else:
    class CollapsibleGroupBox:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass

