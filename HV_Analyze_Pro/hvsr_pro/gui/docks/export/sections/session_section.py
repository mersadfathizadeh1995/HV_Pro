"""
Session Section
===============

Save and load analysis sessions.
"""

try:
    from PyQt5.QtWidgets import QPushButton, QLabel
    from PyQt5.QtCore import pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False

if HAS_PYQT5:
    from hvsr_pro.gui.components import CollapsibleSection


if HAS_PYQT5:
    class SessionSection(CollapsibleSection):
        """
        Session management section.
        
        Signals:
            save_requested: Emitted when save session is requested
            load_requested: Emitted when load session is requested
        """
        
        save_requested = pyqtSignal()
        load_requested = pyqtSignal()
        
        def __init__(self, parent=None):
            super().__init__("Session Management", parent)
            self._init_content()
        
        def _init_content(self):
            """Initialize section content."""
            # Save session button
            self.save_session_btn = QPushButton("Save Session")
            self.save_session_btn.setToolTip("Save current analysis session (settings, results, peaks)")
            self.save_session_btn.clicked.connect(self.save_requested.emit)
            self.add_widget(self.save_session_btn)
            
            # Load session button
            self.load_session_btn = QPushButton("Load Session")
            self.load_session_btn.setToolTip("Load previously saved session")
            self.load_session_btn.clicked.connect(self.load_requested.emit)
            self.add_widget(self.load_session_btn)
            
            # Info label
            info = QLabel("Save/restore complete analysis state")
            info.setStyleSheet("QLabel { color: #666; font-size: 9px; }")
            info.setWordWrap(True)
            self.add_widget(info)
        
        def set_save_enabled(self, enabled: bool):
            """Enable or disable save button."""
            self.save_session_btn.setEnabled(enabled)


else:
    class SessionSection:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass
