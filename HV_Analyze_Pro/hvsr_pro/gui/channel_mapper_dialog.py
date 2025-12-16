"""
MiniSEED Channel Mapper Dialog
================================

Allows users to map MiniSEED channel codes to seismic data components (E, N, Z).

Useful when MiniSEED files have non-standard channel naming.
"""

try:
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel,
        QComboBox, QGroupBox, QScrollArea, QCheckBox,
        QDialogButtonBox, QTableWidget, QTableWidgetItem, QHeaderView
    )
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QColor
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


if HAS_PYQT5:

    class ChannelMapperDialog(QDialog):
        """
        Channel mapping dialog for MiniSEED files.

        Allows user to map channel codes to components (E, N, Z).
        """

        def __init__(self, channels_info, file_path="", parent=None):
            """
            Initialize channel mapper dialog.

            Args:
                channels_info: List of dicts with channel information:
                              [{'code': 'HHE', 'location': '00', 'sampling_rate': 100, 'npts': 10000}, ...]
                file_path: Path to the file being mapped
                parent: Parent widget
            """
            super().__init__(parent)
            self.setWindowTitle("Map MiniSEED Channels")
            self.resize(700, 500)
            self.channels_info = channels_info
            self.file_path = file_path
            self.mapping = {}  # {component: channel_code}

            v = QVBoxLayout(self)

            # Title with file info
            if file_path:
                from pathlib import Path
                filename = Path(file_path).name
                title = QLabel(f"<b>File:</b> {filename}<br><b>Map channels to components (E, N, Z):</b>")
            else:
                title = QLabel("<b>Map channels to components (E, N, Z):</b>")
            title.setWordWrap(True)
            v.addWidget(title)

            # Status label
            self.status_label = QLabel("")
            self.status_label.setStyleSheet("font-weight: bold;")
            v.addWidget(self.status_label)

            # Channels table
            table_group = QGroupBox("Available Channels")
            table_layout = QVBoxLayout(table_group)

            self.table = QTableWidget()
            self.table.setColumnCount(5)
            self.table.setHorizontalHeaderLabels([
                "Channel Code", "Location", "Sampling Rate (Hz)", "Samples", "Map To"
            ])
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
            self.table.setAlternatingRowColors(True)

            # Populate table
            self.mapping_combos = []
            self.table.setRowCount(len(channels_info))

            for i, ch_info in enumerate(channels_info):
                # Channel code
                code_item = QTableWidgetItem(ch_info.get('code', 'Unknown'))
                code_item.setFlags(code_item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(i, 0, code_item)

                # Location
                loc_item = QTableWidgetItem(ch_info.get('location', ''))
                loc_item.setFlags(loc_item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(i, 1, loc_item)

                # Sampling rate
                sr = ch_info.get('sampling_rate', 0)
                sr_item = QTableWidgetItem(f"{sr:.1f}")
                sr_item.setFlags(sr_item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(i, 2, sr_item)

                # Number of samples
                npts = ch_info.get('npts', 0)
                npts_item = QTableWidgetItem(f"{npts:,}")
                npts_item.setFlags(npts_item.flags() & ~Qt.ItemIsEditable)
                self.table.setItem(i, 3, npts_item)

                # Mapping combo box
                combo = QComboBox()
                combo.addItems(["Skipped", "E Component (East)", "N Component (North)", "Z Component (Vertical)"])
                combo.currentTextChanged.connect(self._validate)
                self.mapping_combos.append(combo)
                self.table.setCellWidget(i, 4, combo)

            table_layout.addWidget(self.table)
            v.addWidget(table_group)

            # Help text
            help_text = QLabel(
                "<i><b>Auto-detection:</b> Channels are automatically mapped based on standard naming conventions "
                "(e.g., HHE→East, HHN→North, HHZ→Vertical). Review and adjust if needed.</i>"
            )
            help_text.setWordWrap(True)
            help_text.setStyleSheet("color: #666; font-size: 9pt; padding: 5px; background: #f0f0f0; border-radius: 3px;")
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
                self.status_label.setText("❌ <span style='color:red;'>Error: Cannot map same component to multiple channels</span>")
                self.btn_ok.setEnabled(False)
                # Highlight duplicates in red
                for i, combo in enumerate(self.mapping_combos):
                    if combo.currentText() != "Skipped" and component_types.count(combo.currentText()) > 1:
                        for col in range(self.table.columnCount() - 1):
                            item = self.table.item(i, col)
                            if item:
                                item.setBackground(QColor(255, 200, 200))
                    else:
                        for col in range(self.table.columnCount() - 1):
                            item = self.table.item(i, col)
                            if item:
                                item.setBackground(QColor(255, 255, 255))

            elif has_e and has_n and has_z:
                self.status_label.setText("✅ <span style='color:green;'>Valid mapping - All components mapped</span>")
                self.btn_ok.setEnabled(True)
                # Clear any highlighting
                for i in range(self.table.rowCount()):
                    for col in range(self.table.columnCount() - 1):
                        item = self.table.item(i, col)
                        if item:
                            item.setBackground(QColor(255, 255, 255))

            else:
                missing = []
                if not has_e:
                    missing.append("E Component")
                if not has_n:
                    missing.append("N Component")
                if not has_z:
                    missing.append("Z Component")
                self.status_label.setText(f"❌ <span style='color:red;'>Missing required: {', '.join(missing)}</span>")
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
