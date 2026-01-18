"""
Component Mapper Dialog
========================

Universal component mapping dialog for all seismic data formats.
Allows users to verify and override auto-detected component assignments.
"""

import numpy as np
from typing import Dict, Any, Optional, List
from pathlib import Path

try:
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
        QGroupBox, QLabel, QComboBox, QDoubleSpinBox,
        QCheckBox, QPushButton, QDialogButtonBox,
        QScrollArea, QWidget, QFrame, QSplitter,
        QTableWidget, QTableWidgetItem, QHeaderView
    )
    from PyQt5.QtCore import Qt, pyqtSignal
    from PyQt5.QtGui import QFont
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False

try:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

from hvsr_pro.loaders.preview import PreviewData, ChannelPreview, get_preview


if HAS_PYQT5:
    class ComponentMapperDialog(QDialog):
        """
        Universal component mapping dialog for seismic data.
        
        Features:
        - Shows waveform preview for each channel
        - Displays auto-detected component assignments
        - Allows manual override of component mapping
        - Shows channel statistics (min, max, mean, duration)
        - Supports orientation (degrees from north) override
        - "Remember mapping" option for similar files
        
        Usage:
            >>> preview = get_preview('data.saf')
            >>> dialog = ComponentMapperDialog(preview)
            >>> if dialog.exec_() == QDialog.Accepted:
            ...     mapping = dialog.get_mapping()
            ...     orientation = dialog.get_orientation()
        """
        
        # Signal emitted when mapping changes
        mapping_changed = pyqtSignal(dict)
        
        def __init__(
            self,
            preview: PreviewData,
            parent=None,
            title: str = "Map Seismic Components"
        ):
            """
            Initialize component mapper dialog.
            
            Args:
                preview: PreviewData from loader preview
                parent: Parent widget
                title: Dialog title
            """
            super().__init__(parent)
            self.setWindowTitle(title)
            self.setMinimumSize(900, 700)
            
            self.preview = preview
            self.mapping = {}  # {component: channel_index}
            self.orientation = None  # degrees from north
            self.remember_mapping = False
            
            self._init_ui()
            self._load_preview_data()
            self._connect_signals()
        
        def _init_ui(self):
            """Initialize the user interface."""
            layout = QVBoxLayout(self)
            
            # Header with file info
            header = self._create_header()
            layout.addWidget(header)
            
            # Main content area with splitter
            splitter = QSplitter(Qt.Horizontal)
            
            # Left: Channel list and mapping
            left_panel = self._create_mapping_panel()
            splitter.addWidget(left_panel)
            
            # Right: Waveform preview
            if HAS_MATPLOTLIB:
                right_panel = self._create_preview_panel()
                splitter.addWidget(right_panel)
                splitter.setSizes([400, 500])
            
            layout.addWidget(splitter, 1)
            
            # Orientation settings
            orientation_group = self._create_orientation_group()
            layout.addWidget(orientation_group)
            
            # Options and buttons
            options_layout = QHBoxLayout()
            
            self.remember_check = QCheckBox("Remember this mapping for similar files")
            self.remember_check.setToolTip("Save mapping as default for files with same format/structure")
            options_layout.addWidget(self.remember_check)
            
            options_layout.addStretch()
            
            # Status label
            self.status_label = QLabel()
            self.status_label.setStyleSheet("font-weight: bold;")
            options_layout.addWidget(self.status_label)
            
            layout.addLayout(options_layout)
            
            # Dialog buttons
            button_box = QDialogButtonBox(
                QDialogButtonBox.Ok | QDialogButtonBox.Cancel
            )
            self.ok_button = button_box.button(QDialogButtonBox.Ok)
            button_box.accepted.connect(self.accept)
            button_box.rejected.connect(self.reject)
            layout.addWidget(button_box)
        
        def _create_header(self) -> QWidget:
            """Create header with file information."""
            header = QFrame()
            header.setFrameStyle(QFrame.StyledPanel)
            layout = QHBoxLayout(header)
            
            # Format info
            format_label = QLabel(f"<b>Format:</b> {self.preview.format}")
            layout.addWidget(format_label)
            
            # Channel count
            channels_label = QLabel(f"<b>Channels:</b> {self.preview.n_channels}")
            layout.addWidget(channels_label)
            
            # Duration
            if self.preview.duration_seconds > 0:
                duration_str = f"{self.preview.duration_seconds:.1f} s"
                if self.preview.duration_seconds > 60:
                    minutes = int(self.preview.duration_seconds // 60)
                    seconds = self.preview.duration_seconds % 60
                    duration_str = f"{minutes}m {seconds:.1f}s"
                duration_label = QLabel(f"<b>Duration:</b> {duration_str}")
                layout.addWidget(duration_label)
            
            layout.addStretch()
            
            # Error/warning
            if self.preview.error:
                error_label = QLabel(f"<span style='color: red;'>{self.preview.error}</span>")
                layout.addWidget(error_label)
            
            return header
        
        def _create_mapping_panel(self) -> QWidget:
            """Create the component mapping panel."""
            panel = QGroupBox("Component Mapping")
            layout = QVBoxLayout(panel)
            
            # Instructions
            info = QLabel(
                "<i>Assign each channel to a component (E=East, N=North, Z=Vertical).</i>"
            )
            info.setWordWrap(True)
            layout.addWidget(info)
            
            # Mapping table
            self.mapping_table = QTableWidget()
            self.mapping_table.setColumnCount(5)
            self.mapping_table.setHorizontalHeaderLabels([
                "Channel", "Auto-Detected", "Assign To", "Samples", "Range"
            ])
            
            # Set column widths
            header = self.mapping_table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.Stretch)
            header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
            
            layout.addWidget(self.mapping_table)
            
            # Quick actions
            actions_layout = QHBoxLayout()
            
            auto_detect_btn = QPushButton("Auto-Detect")
            auto_detect_btn.setToolTip("Reset to auto-detected mapping")
            auto_detect_btn.clicked.connect(self._auto_detect_mapping)
            actions_layout.addWidget(auto_detect_btn)
            
            clear_btn = QPushButton("Clear All")
            clear_btn.setToolTip("Clear all component assignments")
            clear_btn.clicked.connect(self._clear_mapping)
            actions_layout.addWidget(clear_btn)
            
            actions_layout.addStretch()
            
            layout.addLayout(actions_layout)
            
            return panel
        
        def _create_preview_panel(self) -> QWidget:
            """Create the waveform preview panel."""
            panel = QGroupBox("Waveform Preview")
            layout = QVBoxLayout(panel)
            
            # Create matplotlib figure
            self.figure = Figure(figsize=(5, 6))
            self.canvas = FigureCanvas(self.figure)
            layout.addWidget(self.canvas)
            
            return panel
        
        def _create_orientation_group(self) -> QGroupBox:
            """Create orientation settings group."""
            group = QGroupBox("Sensor Orientation")
            layout = QHBoxLayout(group)
            
            self.use_custom_orientation = QCheckBox("Specify degrees from north:")
            self.use_custom_orientation.toggled.connect(self._on_orientation_toggle)
            layout.addWidget(self.use_custom_orientation)
            
            self.orientation_spin = QDoubleSpinBox()
            self.orientation_spin.setRange(0, 360)
            self.orientation_spin.setSingleStep(1)
            self.orientation_spin.setDecimals(1)
            self.orientation_spin.setSuffix(" deg")
            self.orientation_spin.setValue(0)
            self.orientation_spin.setEnabled(False)
            self.orientation_spin.setToolTip(
                "Rotation of sensor's north component relative to magnetic north.\n"
                "Clockwise positive (0-360 degrees)."
            )
            layout.addWidget(self.orientation_spin)
            
            layout.addStretch()
            
            info_label = QLabel(
                "<i>Leave unchecked to use orientation from file metadata.</i>"
            )
            info_label.setStyleSheet("color: gray;")
            layout.addWidget(info_label)
            
            return group
        
        def _connect_signals(self):
            """Connect internal signals."""
            pass  # Mapping combos connected in _load_preview_data
        
        def _load_preview_data(self):
            """Load preview data into UI."""
            # Populate mapping table
            self.mapping_table.setRowCount(len(self.preview.channels))
            self.channel_combos = []
            
            for i, channel in enumerate(self.preview.channels):
                # Channel name
                name_item = QTableWidgetItem(channel.name)
                name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
                self.mapping_table.setItem(i, 0, name_item)
                
                # Auto-detected
                detected = channel.detected_component or "Unknown"
                detected_item = QTableWidgetItem(detected)
                detected_item.setFlags(detected_item.flags() & ~Qt.ItemIsEditable)
                if detected != "Unknown":
                    detected_item.setForeground(Qt.darkGreen)
                self.mapping_table.setItem(i, 1, detected_item)
                
                # Component selector
                combo = QComboBox()
                combo.addItem("Skip", None)
                combo.addItem("E (East)", "E")
                combo.addItem("N (North)", "N")
                combo.addItem("Z (Vertical)", "Z")
                
                # Set initial selection from auto-detected
                if channel.detected_component:
                    idx = combo.findData(channel.detected_component)
                    if idx >= 0:
                        combo.setCurrentIndex(idx)
                
                combo.currentIndexChanged.connect(self._on_mapping_changed)
                self.mapping_table.setCellWidget(i, 2, combo)
                self.channel_combos.append(combo)
                
                # Sample count
                samples_item = QTableWidgetItem(f"{channel.full_length:,}")
                samples_item.setFlags(samples_item.flags() & ~Qt.ItemIsEditable)
                self.mapping_table.setItem(i, 3, samples_item)
                
                # Range
                range_str = f"{channel.min_val:.2g} to {channel.max_val:.2g}"
                range_item = QTableWidgetItem(range_str)
                range_item.setFlags(range_item.flags() & ~Qt.ItemIsEditable)
                self.mapping_table.setItem(i, 4, range_item)
            
            # Update waveform preview
            self._update_waveform_preview()
            
            # Validate initial mapping
            self._validate_mapping()
        
        def _update_waveform_preview(self):
            """Update the waveform preview plot."""
            if not HAS_MATPLOTLIB:
                return
            
            self.figure.clear()
            
            n_channels = len(self.preview.channels)
            if n_channels == 0:
                return
            
            # Create subplots for each channel
            axes = self.figure.subplots(n_channels, 1, sharex=True)
            if n_channels == 1:
                axes = [axes]
            
            colors = {'E': '#e74c3c', 'N': '#2ecc71', 'Z': '#3498db', None: '#95a5a6'}
            
            for i, (ax, channel) in enumerate(zip(axes, self.preview.channels)):
                data = channel.data
                if len(data) == 0:
                    continue
                
                # Create time axis
                if channel.sampling_rate > 0:
                    time = np.arange(len(data)) / channel.sampling_rate
                else:
                    time = np.arange(len(data))
                
                # Get color based on component
                component = channel.detected_component
                color = colors.get(component, colors[None])
                
                ax.plot(time, data, color=color, linewidth=0.5)
                
                # Label
                label = channel.name
                if component:
                    label += f" ({component})"
                ax.set_ylabel(label, fontsize=8)
                ax.tick_params(axis='both', labelsize=7)
                
                # Grid
                ax.grid(True, alpha=0.3)
            
            # X-axis label on bottom plot
            axes[-1].set_xlabel('Time (s)', fontsize=8)
            
            self.figure.tight_layout()
            self.canvas.draw()
        
        def _on_mapping_changed(self):
            """Handle mapping combo box change."""
            self._validate_mapping()
            self._update_waveform_preview()
            self.mapping_changed.emit(self.get_mapping())
        
        def _on_orientation_toggle(self, checked: bool):
            """Handle orientation checkbox toggle."""
            self.orientation_spin.setEnabled(checked)
        
        def _validate_mapping(self):
            """Validate current component mapping."""
            # Check for required components
            assigned = {}
            for i, combo in enumerate(self.channel_combos):
                component = combo.currentData()
                if component:
                    if component in assigned:
                        # Duplicate assignment
                        self.status_label.setText(
                            f"<span style='color: red;'>Error: {component} assigned to multiple channels</span>"
                        )
                        self.ok_button.setEnabled(False)
                        return
                    assigned[component] = i
            
            # Check if all required components are assigned
            missing = []
            for comp in ['E', 'N', 'Z']:
                if comp not in assigned:
                    missing.append(comp)
            
            if missing:
                self.status_label.setText(
                    f"<span style='color: orange;'>Missing: {', '.join(missing)}</span>"
                )
                self.ok_button.setEnabled(False)
            else:
                self.status_label.setText(
                    "<span style='color: green;'>Valid mapping - Ready to load</span>"
                )
                self.ok_button.setEnabled(True)
            
            self.mapping = assigned
        
        def _auto_detect_mapping(self):
            """Reset to auto-detected mapping."""
            for i, channel in enumerate(self.preview.channels):
                combo = self.channel_combos[i]
                if channel.detected_component:
                    idx = combo.findData(channel.detected_component)
                    if idx >= 0:
                        combo.setCurrentIndex(idx)
                else:
                    combo.setCurrentIndex(0)  # Skip
            
            self._validate_mapping()
        
        def _clear_mapping(self):
            """Clear all component assignments."""
            for combo in self.channel_combos:
                combo.setCurrentIndex(0)  # Skip
            self._validate_mapping()
        
        def get_mapping(self) -> Dict[str, int]:
            """
            Get current component mapping.
            
            Returns:
                Dictionary mapping component (E, N, Z) to channel index
            """
            mapping = {}
            for i, combo in enumerate(self.channel_combos):
                component = combo.currentData()
                if component:
                    mapping[component] = i
            return mapping
        
        def get_orientation(self) -> Optional[float]:
            """
            Get orientation setting.
            
            Returns:
                Degrees from north, or None to use file metadata
            """
            if self.use_custom_orientation.isChecked():
                return self.orientation_spin.value()
            return None
        
        def should_remember(self) -> bool:
            """Check if user wants to remember this mapping."""
            return self.remember_check.isChecked()
        
        def get_result(self) -> Dict[str, Any]:
            """
            Get complete result dictionary.
            
            Returns:
                Dictionary with mapping, orientation, and options
            """
            return {
                'mapping': self.get_mapping(),
                'orientation': self.get_orientation(),
                'remember': self.should_remember(),
                'format': self.preview.format,
                'n_channels': self.preview.n_channels
            }


else:
    class ComponentMapperDialog:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            raise ImportError("PyQt5 is required for GUI functionality")
