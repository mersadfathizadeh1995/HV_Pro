"""
Color Picker Button
===================

A button widget that opens a color picker dialog.
Extracted from properties_dock.py.
"""

try:
    from PyQt5.QtWidgets import QPushButton, QColorDialog
    from PyQt5.QtGui import QColor
    from PyQt5.QtCore import pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


if HAS_PYQT5:
    class ColorPickerButton(QPushButton):
        """
        A button that displays a color and opens a color picker when clicked.
        
        Features:
        - Shows current color as button background
        - Opens color picker dialog on click
        - Emits signal when color changes
        
        Signals:
            color_changed: Emitted when color is changed (str hex color)
        """
        
        color_changed = pyqtSignal(str)
        
        def __init__(self, initial_color: str = "#000000", parent=None):
            super().__init__(parent)
            self._color = initial_color
            
            self._update_style()
            self.clicked.connect(self._pick_color)
            
            self.setFixedSize(40, 25)
            self.setToolTip("Click to change color")
        
        def _update_style(self):
            """Update button style based on current color."""
            # Determine text color based on brightness
            color = QColor(self._color)
            brightness = (color.red() * 299 + color.green() * 587 + color.blue() * 114) / 1000
            text_color = "#000000" if brightness > 128 else "#ffffff"
            
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self._color};
                    color: {text_color};
                    border: 1px solid #888;
                    border-radius: 3px;
                    font-size: 10px;
                }}
                QPushButton:hover {{
                    border: 2px solid #333;
                }}
            """)
            self.setText("")  # No text, just color
        
        def _pick_color(self):
            """Open color picker dialog."""
            current = QColor(self._color)
            new_color = QColorDialog.getColor(current, self, "Select Color")
            
            if new_color.isValid():
                self._color = new_color.name()
                self._update_style()
                self.color_changed.emit(self._color)
        
        def get_color(self) -> str:
            """Get current color as hex string."""
            return self._color
        
        def set_color(self, color: str):
            """
            Set the button color.
            
            Args:
                color: Color as hex string (e.g., "#ff0000")
            """
            if color != self._color:
                self._color = color
                self._update_style()
                self.color_changed.emit(self._color)
        
        def set_color_no_signal(self, color: str):
            """
            Set color without emitting signal.
            
            Useful for initializing from settings.
            
            Args:
                color: Color as hex string
            """
            self._color = color
            self._update_style()

else:
    class ColorPickerButton:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            pass

