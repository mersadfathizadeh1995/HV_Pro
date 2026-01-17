"""
MiniSEED Channel Mapper Dialog
================================

Allows users to map MiniSEED channel codes to seismic data components (E, N, Z).

Useful when MiniSEED files have non-standard channel naming.

Enhanced version with data preview similar to column mapper dialog.
"""

try:
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel,
        QComboBox, QGroupBox, QScrollArea, QCheckBox,
        QDialogButtonBox, QTableWidget, QTableWidgetItem, QHeaderView,
        QTextEdit, QSplitter, QFrame
    )
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QColor, QFont
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


if HAS_PYQT5:

    class ChannelMapperDialog(QDialog):
        """
        Channel mapping dialog for MiniSEED files.

        Allows user to map channel codes to components (E, N, Z).
        
        Enhanced features:
        - Data preview for each channel (similar to column mapper)
        - Statistics display
        - Visual indicator of data characteristics
        """

        def __init__(self, channels_info, file_path="", parent=None, channel_data=None):
            """
            Initialize channel mapper dialog.

            Args:
                channels_info: List of dicts with channel information:
                              [{'code': 'HHE', 'location': '00', 'sampling_rate': 100, 'npts': 10000}, ...]
                file_path: Path to the file being mapped
                parent: Parent widget
                channel_data: Optional dict mapping channel code to numpy array of sample data
                             for preview purposes
            """
            super().__init__(parent)
            self.setWindowTitle("Map MiniSEED Channels")
            self.resize(900, 650)
            self.channels_info = channels_info
            self.file_path = file_path
            self.mapping = {}  # {component: channel_code}
            self.channel_data = channel_data or {}

            v = QVBoxLayout(self)

            # Title with file info
            if file_path:
                from pathlib import Path
                filename = Path(file_path).name if not isinstance(file_path, str) else file_path
                title = QLabel(f"<b>File:</b> {filename}<br><b>Map each channel to its component type:</b>")
            else:
                title = QLabel("<b>Map each channel to its component type:</b>")
            title.setWordWrap(True)
            v.addWidget(title)

            # Status label
            self.status_label = QLabel("")
            self.status_label.setStyleSheet("font-weight: bold;")
            v.addWidget(self.status_label)

            # Main content - horizontal scroll area with channel cards
            scroll = QScrollArea(self)
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            
            # Container for channel cards
            container = QWidget()
            self.channel_layout = QHBoxLayout(container)
            self.channel_layout.setSpacing(8)
            scroll.setWidget(container)
            
            # Create channel cards (similar to column mapper)
            self.mapping_combos = []
            for i, ch_info in enumerate(channels_info):
                card = self._create_channel_card(i, ch_info)
                self.channel_layout.addWidget(card)
            
            # Add stretch at end
            self.channel_layout.addStretch()
            
            v.addWidget(scroll, 1)

            # Summary table (compact view)
            summary_group = QGroupBox("Channel Summary")
            summary_layout = QVBoxLayout(summary_group)
            
            self.summary_table = QTableWidget()
            self.summary_table.setColumnCount(5)
            self.summary_table.setHorizontalHeaderLabels([
                "Channel", "Samples", "Rate (Hz)", "Duration (s)", "Mapping"
            ])
            self.summary_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
            self.summary_table.setMaximumHeight(150)
            self.summary_table.setAlternatingRowColors(True)
            
            # Populate summary
            self.summary_table.setRowCount(len(channels_info))
            for i, ch_info in enumerate(channels_info):
                code = ch_info.get('code', '?')
                npts = ch_info.get('npts', 0)
                sr = ch_info.get('sampling_rate', 0)
                duration = npts / sr if sr > 0 else 0
                
                self.summary_table.setItem(i, 0, QTableWidgetItem(code))
                self.summary_table.setItem(i, 1, QTableWidgetItem(f"{npts:,}"))
                self.summary_table.setItem(i, 2, QTableWidgetItem(f"{sr:.1f}"))
                self.summary_table.setItem(i, 3, QTableWidgetItem(f"{duration:.1f}"))
                # Mapping column updated by combo box changes
                self.summary_table.setItem(i, 4, QTableWidgetItem("Skipped"))
            
            summary_layout.addWidget(self.summary_table)
            v.addWidget(summary_group)

            # Help text
            help_text = QLabel(
                "<i><b>Tips:</b> Channels ending in E/1 -> East, N/2 -> North, Z/3 -> Vertical. "
                "Auto-detection is applied but review carefully for non-standard names.</i>"
            )
            help_text.setWordWrap(True)
            help_text.setStyleSheet("color: #666; font-size: 9pt; padding: 5px; background: #f5f5f5; border-radius: 3px;")
            v.addWidget(help_text)

            # Remember mapping checkbox
            self.chk_remember = QCheckBox("Remember this mapping for similar files", self)
            self.chk_remember.setToolTip("Save channel mapping as default for files with same channel structure")
            v.addWidget(self.chk_remember)

            # Buttons
            btns = QDialogButtonBox(self)
            btns.setStandardButtons(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            self.btn_ok = btns.button(QDialogButtonBox.Ok)
            btns.accepted.connect(self.accept)
            btns.rejected.connect(self.reject)
            v.addWidget(btns)

            # Auto-detect and validate
            self._auto_detect()
            self._validate()
        
        def _create_channel_card(self, index: int, ch_info: dict) -> QWidget:
            """Create a card widget for one channel with preview."""
            import numpy as np
            
            card = QFrame()
            card.setFrameStyle(QFrame.Box | QFrame.Raised)
            card.setMinimumWidth(160)
            card.setMaximumWidth(220)
            card.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border: 1px solid #ccc;
                    border-radius: 4px;
                    padding: 4px;
                }
            """)
            
            layout = QVBoxLayout(card)
            layout.setContentsMargins(8, 8, 8, 8)
            layout.setSpacing(6)
            
            # Channel header
            code = ch_info.get('code', 'Unknown')
            header = QLabel(f"<b style='font-size: 12pt;'>{code}</b>")
            header.setAlignment(Qt.AlignCenter)
            layout.addWidget(header)
            
            # Mapping combo box
            combo = QComboBox()
            combo.addItems(["Skipped", "E Component (East)", "N Component (North)", "Z Component (Vertical)"])
            combo.currentTextChanged.connect(lambda text, idx=index: self._on_combo_changed(idx, text))
            self.mapping_combos.append(combo)
            layout.addWidget(combo)
            
            # Channel info
            info_text = ""
            location = ch_info.get('location', '')
            if location:
                info_text += f"Loc: {location}\n"
            
            sr = ch_info.get('sampling_rate', 0)
            npts = ch_info.get('npts', 0)
            duration = npts / sr if sr > 0 else 0
            
            info_text += f"Rate: {sr:.1f} Hz\n"
            info_text += f"Samples: {npts:,}\n"
            info_text += f"Duration: {duration:.1f}s"
            
            info_label = QLabel(info_text)
            info_label.setStyleSheet("color: #666; font-size: 9pt; background: #f5f5f5; padding: 4px; border-radius: 3px;")
            layout.addWidget(info_label)
            
            # Statistics if data is available
            channel_code = code
            if channel_code in self.channel_data:
                data = self.channel_data[channel_code]
                try:
                    arr = np.array(data)
                    arr_clean = arr[np.isfinite(arr)]
                    if arr_clean.size > 0:
                        stats = f"Min: {np.min(arr_clean):.3g}\n"
                        stats += f"Max: {np.max(arr_clean):.3g}\n"
                        stats += f"Mean: {np.mean(arr_clean):.3g}\n"
                        stats += f"Std: {np.std(arr_clean):.3g}"
                        
                        stats_label = QLabel(stats)
                        stats_label.setStyleSheet("font-size: 8pt; color: #333; background: #e8f5e9; padding: 3px; border: 1px solid #c8e6c9;")
                        stats_label.setAlignment(Qt.AlignLeft)
                        layout.addWidget(stats_label)
                except Exception:
                    pass
            
            # Data preview (if available)
            if channel_code in self.channel_data:
                data = self.channel_data[channel_code]
                preview = QTextEdit()
                preview.setReadOnly(True)
                preview.setMaximumHeight(100)
                preview.setStyleSheet("font-size: 8pt; font-family: monospace;")
                
                # Show sample of data (first 20 values)
                try:
                    preview_text = "\n".join([
                        f"{val:.6g}" for val in data[:20]
                    ])
                    if len(data) > 20:
                        preview_text += f"\n... ({len(data) - 20} more)"
                    preview.setPlainText(preview_text)
                except Exception:
                    preview.setPlainText("(preview unavailable)")
                
                layout.addWidget(preview)
            
            return card
        
        def _on_combo_changed(self, index: int, text: str):
            """Handle combo box change - update summary table."""
            if index < self.summary_table.rowCount():
                mapping_item = self.summary_table.item(index, 4)
                if mapping_item:
                    # Extract short mapping text
                    if "East" in text:
                        mapping_item.setText("-> East")
                        mapping_item.setForeground(QColor(0, 128, 0))
                    elif "North" in text:
                        mapping_item.setText("-> North")
                        mapping_item.setForeground(QColor(0, 100, 200))
                    elif "Vertical" in text:
                        mapping_item.setText("-> Vertical")
                        mapping_item.setForeground(QColor(200, 100, 0))
                    else:
                        mapping_item.setText("Skipped")
                        mapping_item.setForeground(QColor(128, 128, 128))
            
            self._validate()

        def _auto_detect(self):
            """Auto-detect channel mappings based on standard naming conventions."""
            # Standard MiniSEED channel naming:
            # - Last character indicates component: E/1 = East, N/2 = North, Z/3 = Vertical
            # - Common patterns: HHE/HHN/HHZ, BHE/BHN/BHZ, EHE/EHN/EHZ, etc.

            for i, ch_info in enumerate(self.channels_info):
                code = ch_info.get('code', '').upper()

                if not code:
                    continue

                # Get last character
                last_char = code[-1] if code else ''

                # Map based on last character
                if last_char in ['E', '1']:
                    self.mapping_combos[i].setCurrentText("E Component (East)")
                elif last_char in ['N', '2']:
                    self.mapping_combos[i].setCurrentText("N Component (North)")
                elif last_char in ['Z', '3']:
                    self.mapping_combos[i].setCurrentText("Z Component (Vertical)")
                else:
                    # Try to detect from full code
                    if 'EAST' in code or 'E' in code:
                        self.mapping_combos[i].setCurrentText("E Component (East)")
                    elif 'NORTH' in code or 'N' in code:
                        self.mapping_combos[i].setCurrentText("N Component (North)")
                    elif 'VERT' in code or 'Z' in code or 'UP' in code:
                        self.mapping_combos[i].setCurrentText("Z Component (Vertical)")

        def _validate(self):
            """Validate required components are mapped."""
            types = [combo.currentText() for combo in self.mapping_combos]

            has_e = "E Component (East)" in types
            has_n = "N Component (North)" in types
            has_z = "Z Component (Vertical)" in types

            # Check for duplicates
            component_types = [t for t in types if t != "Skipped"]
            has_duplicates = len(component_types) != len(set(component_types))

            if has_duplicates:
                self.status_label.setText("<span style='color:red;'>Error: Cannot map same component to multiple channels</span>")
                self.btn_ok.setEnabled(False)
                # Highlight duplicates in summary table
                for i, combo in enumerate(self.mapping_combos):
                    if i < self.summary_table.rowCount():
                        mapping_item = self.summary_table.item(i, 4)
                        if mapping_item and combo.currentText() != "Skipped" and component_types.count(combo.currentText()) > 1:
                            mapping_item.setBackground(QColor(255, 200, 200))
                        elif mapping_item:
                            mapping_item.setBackground(QColor(255, 255, 255))

            elif has_e and has_n and has_z:
                self.status_label.setText("<span style='color:green;'>Valid mapping - All components mapped</span>")
                self.btn_ok.setEnabled(True)
                # Clear any highlighting in summary table
                for i in range(self.summary_table.rowCount()):
                    mapping_item = self.summary_table.item(i, 4)
                    if mapping_item:
                        mapping_item.setBackground(QColor(255, 255, 255))

            else:
                missing = []
                if not has_e:
                    missing.append("E Component")
                if not has_n:
                    missing.append("N Component")
                if not has_z:
                    missing.append("Z Component")
                self.status_label.setText(f"<span style='color:red;'>Missing required: {', '.join(missing)}</span>")
                self.btn_ok.setEnabled(False)

        def get_mapping(self):
            """
            Return channel mapping dict.

            Returns:
                dict: {component: channel_code} mapping
                      e.g., {'E': 'HHE', 'N': 'HHN', 'Z': 'HHZ'}
            """
            mapping = {}
            for i, combo in enumerate(self.mapping_combos):
                component_text = combo.currentText()
                if component_text != "Skipped":
                    # Extract component letter
                    if "E Component" in component_text:
                        component = 'E'
                    elif "N Component" in component_text:
                        component = 'N'
                    elif "Z Component" in component_text:
                        component = 'Z'
                    else:
                        continue

                    channel_code = self.channels_info[i].get('code', '')
                    mapping[component] = channel_code

            return mapping

        def should_remember(self):
            """Return whether user wants to remember this mapping."""
            return self.chk_remember.isChecked()


else:
    # Dummy class when PyQt5 not available
    class ChannelMapperDialog:
        def __init__(self, *args, **kwargs):
            raise ImportError("PyQt5 is required for GUI functionality")
