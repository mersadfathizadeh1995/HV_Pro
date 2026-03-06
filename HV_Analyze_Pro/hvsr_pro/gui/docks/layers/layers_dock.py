"""
Window Layers Dock for HVSR Pro
================================

Professional layer management with scrollable list and real-time updates.
Based on DC_Cut's LayersDock architecture.
"""

from PyQt5.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QListView, QPushButton
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import (
    QStandardItemModel, QStandardItem, QIcon,
    QPixmap, QPainter, QColor
)
from matplotlib import colors as mcolors
import numpy as np


class WindowLayersDock(QDockWidget):
    """
    Dock widget for managing window layer visibility.
    
    Features:
    - Scrollable list of all windows with checkboxes
    - Color icons matching plot line colors
    - Quality scores displayed
    - Batch operations (All On, All Off, Invert)
    - Real-time mean recalculation on toggle
    
    Signals:
        visibility_changed(int, bool): Emitted when window visibility changes
            Args: (window_index, is_visible)
    """
    
    visibility_changed = pyqtSignal(int, bool)
    
    def __init__(self, parent=None):
        """
        Initialize layers dock.
        
        Args:
            parent: Parent window (main window)
        """
        super().__init__("Layers", parent)
        self.setObjectName("LayersDock")
        
        # References (set by parent)
        self.controller = None
        self.canvas_manager = None
        self.windows = None
        self.window_lines = {}  # {window_index: matplotlib_line}
        self.stat_lines = {}  # {'mean': line, 'std_plus': line, ...}
        
        # Set dock features
        self.setFeatures(
            QDockWidget.DockWidgetMovable |
            QDockWidget.DockWidgetFloatable
        )
        
        # Create UI
        self._create_ui()
    
    def _create_ui(self):
        """Create dock UI."""
        # Main widget
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        
        # Batch buttons
        btn_layout = QHBoxLayout()
        
        self.btn_all_on = QPushButton("All On")
        self.btn_all_on.setToolTip("Show all windows")
        self.btn_all_on.clicked.connect(lambda: self._set_all_layers(True))
        
        self.btn_all_off = QPushButton("All Off")
        self.btn_all_off.setToolTip("Hide all windows")
        self.btn_all_off.clicked.connect(lambda: self._set_all_layers(False))
        
        self.btn_invert = QPushButton("Invert")
        self.btn_invert.setToolTip("Invert visibility selection")
        self.btn_invert.clicked.connect(self._invert_selection)
        
        btn_layout.addWidget(self.btn_all_on)
        btn_layout.addWidget(self.btn_all_off)
        btn_layout.addWidget(self.btn_invert)
        
        layout.addLayout(btn_layout)
        
        # List view with model
        self.view = QListView()
        self.model = QStandardItemModel()
        self.view.setModel(self.model)
        self.view.setEditTriggers(QListView.NoEditTriggers)
        
        layout.addWidget(self.view)
        
        # Connect signals
        self.model.itemChanged.connect(self._on_item_changed)
        
        self.setWidget(widget)
    
    def set_references(self, canvas_manager, windows):
        """
        Set references to canvas manager and windows.
        
        Args:
            canvas_manager: PlotWindowManager instance
            windows: WindowCollection instance
        """
        self.canvas_manager = canvas_manager
        self.windows = windows
    
    def _make_icon(self, color_or_line, icon_type='circle'):
        """
        Generate colored icon.
        
        Args:
            color_or_line: Matplotlib color string or Line2D object
            icon_type: 'circle' for windows, 'line' for statistics
            
        Returns:
            QIcon
        """
        # Extract color
        if hasattr(color_or_line, 'get_color'):
            # It's a matplotlib line
            color = color_or_line.get_color() or color_or_line.get_markeredgecolor() or 'k'
        else:
            # It's a color string
            color = color_or_line
        
        # Convert to RGBA
        r, g, b, a = mcolors.to_rgba(color)
        r_255 = int(r * 255)
        g_255 = int(g * 255)
        b_255 = int(b * 255)
        
        # Create pixmap
        pixmap = QPixmap(16, 16)
        pixmap.fill(QColor(0, 0, 0, 0))  # Transparent background
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if icon_type == 'circle':
            # Filled circle for windows
            painter.setBrush(QColor(r_255, g_255, b_255))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(2, 2, 12, 12)
        else:
            # Horizontal line for statistics
            painter.setPen(QColor(r_255, g_255, b_255))
            painter.drawLine(2, 8, 14, 8)
        
        painter.end()
        
        return QIcon(pixmap)
    
    def rebuild(self, window_lines, stat_lines=None):
        """
        Rebuild layer list from current windows.
        
        Args:
            window_lines: Dict mapping window_index to matplotlib Line2D
            stat_lines: Dict mapping stat name to matplotlib Line2D
                Keys: 'mean', 'std_plus', 'std_minus'
        """
        if self.windows is None:
            return
        
        if not window_lines:
            return
        
        # Store references
        self.window_lines = window_lines
        self.stat_lines = stat_lines or {}
        
        # Disconnect signal temporarily
        self.model.itemChanged.disconnect(self._on_item_changed)
        
        # Clear model
        self.model.clear()
        
        # Add window entries
        for window in self.windows.windows:
            window_idx = window.index
            
            # Get line for this window
            line = window_lines.get(window_idx)
            if line is None:
                continue
            
            # Create icon
            icon = self._make_icon(line, 'circle')
            
            # Format label
            quality = window.quality_metrics.get('overall', 0.0)
            label = f"Window {window_idx + 1} (Q={quality:.2f})"
            
            # Add [REJ] suffix if rejected
            if not window.is_active():
                label += " [REJ]"
            
            # Create item
            item = QStandardItem(icon, label)
            item.setCheckable(True)
            
            # Set initial check state
            initial_visible = window.is_active() and window.visible
            check_state = Qt.Checked if initial_visible else Qt.Unchecked
            item.setCheckState(check_state)
            
            # Store window index
            item.setData(window_idx, Qt.UserRole)
            
            # Set text color based on state
            if not window.is_active():
                item.setForeground(QColor(150, 150, 150))  # Gray for rejected
            
            # Add to model
            self.model.appendRow(item)
        
        # Add statistics entries if provided
        if stat_lines:
            # Add separator (visual only)
            separator = QStandardItem("─" * 20)
            separator.setEnabled(False)
            self.model.appendRow(separator)
            
            stats_entries = [
                ("Mean H/V", "mean", 'black'),
                ("Median H/V", "median", '#1565C0'),
                ("+1σ", "std_plus", 'black'),
                ("-1σ", "std_minus", 'black'),
                ("16th-84th Percentile", "percentile_fill", '#9C27B0'),
            ]
            
            for label, data_id, color in stats_entries:
                if data_id in stat_lines:
                    icon = self._make_icon(color, 'line')
                    item = QStandardItem(icon, label)
                    item.setCheckable(True)
                    item.setCheckState(Qt.Checked)  # Default visible
                    item.setData(data_id, Qt.UserRole)
                    self.model.appendRow(item)
        
        # Reconnect signal
        self.model.itemChanged.connect(self._on_item_changed)
    
    def _on_item_changed(self, item):
        """
        Handle item checkbox toggle.
        
        Args:
            item: QStandardItem that changed
        """
        # Get item data
        role_data = item.data(Qt.UserRole)
        is_checked = (item.checkState() == Qt.Checked)
        
        # Handle statistics lines
        if isinstance(role_data, str):
            self._toggle_stat_line(role_data, is_checked)
            return
        
        # Handle window lines
        window_idx = role_data
        
        # Validate index - window_lines is a dict keyed by window_index
        if window_idx not in self.window_lines:
            return
        
        # Update matplotlib line visibility
        if window_idx in self.window_lines:
            line = self.window_lines[window_idx]
            line.set_visible(is_checked)
        
        # Update window object
        if self.windows:
            window = self.windows.get_window(window_idx)
            if window:
                window.visible = is_checked
        
        # Emit signal
        self.visibility_changed.emit(window_idx, is_checked)
        
        # Redraw canvas
        if self.canvas_manager:
            self.canvas_manager.fig.canvas.draw_idle()
    
    def _toggle_stat_line(self, stat_id, visible):
        """Toggle statistics line or fill visibility."""
        if stat_id in self.stat_lines:
            artist = self.stat_lines[stat_id]
            artist.set_visible(visible)
            if self.canvas_manager:
                self.canvas_manager.fig.canvas.draw_idle()
    
    def _set_all_layers(self, visible):
        """
        Batch set all layers visibility.
        
        Args:
            visible: True for all visible, False for all hidden
        """
        if not self.window_lines:
            return
        
        # Block signals
        self.model.blockSignals(True)
        
        # Set all checkboxes
        for row in range(self.model.rowCount()):
            item = self.model.item(row)
            if item and item.isCheckable():
                item.setCheckState(Qt.Checked if visible else Qt.Unchecked)
        
        # Unblock signals
        self.model.blockSignals(False)
        
        # Batch update lines
        for window_idx, line in self.window_lines.items():
            line.set_visible(visible)
            
            # Update window object
            if self.windows:
                window = self.windows.get_window(window_idx)
                if window:
                    window.visible = visible
        
        # Update stat lines
        for stat_line in self.stat_lines.values():
            stat_line.set_visible(visible)
        
        # Redraw once
        if self.canvas_manager:
            self.canvas_manager.fig.canvas.draw_idle()
        
    def _invert_selection(self):
        """Invert all checkbox states."""
        if not self.window_lines:
            return
        
        # Block signals
        self.model.blockSignals(True)
        
        # Invert all checkboxes
        for row in range(self.model.rowCount()):
            item = self.model.item(row)
            if item and item.isCheckable():
                current = item.checkState()
                new_state = Qt.Unchecked if current == Qt.Checked else Qt.Checked
                item.setCheckState(new_state)
        
        # Unblock signals
        self.model.blockSignals(False)
        
        # Update lines
        for window_idx, line in self.window_lines.items():
            # Get item
            item = None
            for row in range(self.model.rowCount()):
                test_item = self.model.item(row)
                if test_item and test_item.data(Qt.UserRole) == window_idx:
                    item = test_item
                    break
            
            if item:
                is_visible = (item.checkState() == Qt.Checked)
                line.set_visible(is_visible)
                
                # Update window object
                if self.windows:
                    window = self.windows.get_window(window_idx)
                    if window:
                        window.visible = is_visible
        
        # Redraw
        if self.canvas_manager:
            self.canvas_manager.fig.canvas.draw_idle()
