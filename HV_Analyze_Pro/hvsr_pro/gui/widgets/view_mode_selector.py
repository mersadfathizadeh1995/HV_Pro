"""
View Mode Selector for HVSR Pro
================================

Widget for selecting between visualization modes.
"""

from PyQt5.QtWidgets import QGroupBox, QVBoxLayout, QRadioButton
from PyQt5.QtCore import pyqtSignal


class ViewModeSelector(QGroupBox):
    """
    Widget for selecting HVSR visualization mode.
    
    Modes:
    - Statistical: Mean + uncertainty band (publication-ready)
    - Windows: All individual curves + mean (QC/exploration)
    - Both: Combined view (comprehensive)
    
    Signals:
        mode_changed(str): Emitted when mode changes
            Args: mode ('statistical', 'windows', or 'both')
    """
    
    mode_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        """
        Initialize view mode selector.
        
        Args:
            parent: Parent widget
        """
        super().__init__("Visualization Mode", parent)
        
        # Create layout
        layout = QVBoxLayout(self)
        
        # Radio buttons
        self.rb_statistical = QRadioButton("Statistical View")
        self.rb_statistical.setToolTip("Mean + uncertainty band (clean, publication-ready)")
        
        self.rb_windows = QRadioButton("Individual Windows")
        self.rb_windows.setToolTip("All window curves + mean (best for QC)")
        
        self.rb_both = QRadioButton("Both (Combined)")
        self.rb_both.setToolTip("All curves + statistics (comprehensive)")
        
        # Set default
        self.rb_windows.setChecked(True)
        
        # Add to layout
        layout.addWidget(self.rb_statistical)
        layout.addWidget(self.rb_windows)
        layout.addWidget(self.rb_both)
        
        # Connect signals
        self.rb_statistical.toggled.connect(self._on_mode_changed)
        self.rb_windows.toggled.connect(self._on_mode_changed)
        self.rb_both.toggled.connect(self._on_mode_changed)
    
    def _on_mode_changed(self):
        """Handle mode change."""
        if self.sender().isChecked():  # Only respond to the checked button
            mode = self.get_mode()
            self.mode_changed.emit(mode)
    
    def get_mode(self) -> str:
        """
        Get currently selected mode.
        
        Returns:
            str: 'statistical', 'windows', or 'both'
        """
        if self.rb_statistical.isChecked():
            return 'statistical'
        elif self.rb_windows.isChecked():
            return 'windows'
        else:
            return 'both'
    
    def set_mode(self, mode: str):
        """
        Set visualization mode.
        
        Args:
            mode: 'statistical', 'windows', or 'both'
        """
        if mode == 'statistical':
            self.rb_statistical.setChecked(True)
        elif mode == 'windows':
            self.rb_windows.setChecked(True)
        elif mode == 'both':
            self.rb_both.setChecked(True)
        else:
            pass
