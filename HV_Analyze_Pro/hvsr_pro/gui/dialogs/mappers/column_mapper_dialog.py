"""
Seismic Data Column Mapper Dialog
===================================

Allows users to map columns in CSV/text files to seismic data components.

Based on the column mapping pattern from dc_cut module.
"""

try:
    from PyQt5.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel,
        QComboBox, QTextEdit, QScrollArea, QCheckBox,
        QDialogButtonBox, QPushButton
    )
    from PyQt5.QtCore import Qt
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


if HAS_PYQT5:

    class SeismicColumnMapperDialog(QDialog):
        """
        Column mapping dialog for seismic data files.

        Allows user to map columns to data types (E, N, Z components, Time, etc.).
        """

        def __init__(self, columns_data, file_path="", parent=None, column_headers=None):
            """
            Initialize column mapper dialog.

            Args:
                columns_data: List of column arrays (numpy arrays or lists)
                file_path: Path to the file being mapped
                parent: Parent widget
                column_headers: Optional list of column header names from file
            """
            super().__init__(parent)
            self.setWindowTitle("Map Seismic Data Columns")
            self.resize(900, 600)
            self.columns_data = columns_data  # List of column arrays
            self.file_path = file_path
            self.mapping = {}  # {col_idx: type_str}
            self.column_headers = column_headers  # Store detected headers

            v = QVBoxLayout(self)

            # Title with file info
            if file_path:
                from pathlib import Path
                filename = Path(file_path).name
                title = QLabel(f"<b>File:</b> {filename}<br><b>Map each column to its data type:</b>")
            else:
                title = QLabel("<b>Map each column to its data type:</b>")
            title.setWordWrap(True)
            v.addWidget(title)

            # Status label
            self.status_label = QLabel("")
            self.status_label.setStyleSheet("font-weight: bold;")
            v.addWidget(self.status_label)

            # Scroll area for columns
            scroll = QScrollArea(self)
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

            # Container for columns
            container = QWidget()
            self.col_layout = QHBoxLayout(container)
            self.col_layout.setSpacing(4)
            scroll.setWidget(container)
            v.addWidget(scroll, 1)

            # Column type options
            self.type_options = [
                "Skipped",
                "E Component (East)",
                "N Component (North)",
                "Z Component (Vertical)",
                "Time (seconds)",
                "Time (datetime)",
                "Sampling Rate",
                "Metadata"
            ]

            # Create column widgets
            self.combo_boxes = []
            for i, col_data in enumerate(columns_data):
                col_widget = self._make_column_widget(i, col_data)
                self.col_layout.addWidget(col_widget)

            # Help text
            help_text = QLabel(
                "<i>Note: At minimum, you must map E, N, and Z components. "
                "Time column is optional (auto-generated if not provided).</i>"
            )
            help_text.setWordWrap(True)
            help_text.setStyleSheet("color: gray; font-size: 9pt; padding: 5px;")
            v.addWidget(help_text)

            # Remember mapping checkbox
            self.chk_remember = QCheckBox("Remember this mapping for similar files", self)
            self.chk_remember.setToolTip("Save column mapping as default for files with same number of columns")
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

        def _make_column_widget(self, col_idx, col_data):
            """Create widget for one column."""
            import numpy as np

            w = QWidget()
            w.setMinimumWidth(130)
            w.setMaximumWidth(220)
            vbox = QVBoxLayout(w)
            vbox.setContentsMargins(2, 2, 2, 2)

            # Column header - use detected header if available
            if self.column_headers and col_idx < len(self.column_headers):
                header_text = self.column_headers[col_idx]
                lbl = QLabel(f"<b>Column {col_idx + 1}</b><br><small>{header_text}</small>")
            else:
                lbl = QLabel(f"<b>Column {col_idx + 1}</b>")
            lbl.setAlignment(Qt.AlignCenter)
            vbox.addWidget(lbl)

            # Type selector
            combo = QComboBox(w)
            combo.addItems(self.type_options)
            combo.currentTextChanged.connect(lambda: self._validate())
            self.combo_boxes.append(combo)
            vbox.addWidget(combo)

            # Statistics label
            try:
                arr = np.array(col_data, dtype=float)
                arr_clean = arr[np.isfinite(arr)]  # Remove NaN/inf
                if arr_clean.size > 0:
                    stats = f"Min: {np.min(arr_clean):.3g}\n"
                    stats += f"Max: {np.max(arr_clean):.3g}\n"
                    stats += f"Mean: {np.mean(arr_clean):.3g}\n"
                    stats += f"Std: {np.std(arr_clean):.3g}"
                else:
                    stats = "No valid data"
            except:
                stats = "Non-numeric"

            stats_label = QLabel(stats)
            stats_label.setStyleSheet("font-size: 8pt; color: #666; background: #f0f0f0; padding: 3px; border: 1px solid #ccc;")
            stats_label.setAlignment(Qt.AlignLeft)
            vbox.addWidget(stats_label)

            # Data preview (scrollable)
            preview = QTextEdit(w)
            preview.setReadOnly(True)
            preview.setMaximumHeight(350)

            # Show sample of data (first 50 rows)
            preview_text = "\n".join([
                f"{val:.6g}" if isinstance(val, (int, float)) else str(val)
                for val in col_data[:50]
            ])
            if len(col_data) > 50:
                preview_text += f"\n\n... ({len(col_data) - 50} more rows)"

            preview.setPlainText(preview_text)
            vbox.addWidget(preview, 1)

            return w

        def _auto_detect(self):
            """Auto-detect column types based on data patterns and headers."""
            import numpy as np

            if len(self.combo_boxes) == 0:
                return

            # First, try to use column headers if available
            if self.column_headers:
                for i, header in enumerate(self.column_headers):
                    if i >= len(self.combo_boxes):
                        break

                    header_upper = header.upper()

                    # Detect based on header text
                    if 'TIME' in header_upper or 'T[' in header_upper:
                        self.combo_boxes[i].setCurrentText("Time (seconds)")
                    elif 'E-W' in header_upper or 'EAST' in header_upper or header_upper == 'E':
                        self.combo_boxes[i].setCurrentText("E Component (East)")
                    elif 'N-S' in header_upper or 'NORTH' in header_upper or header_upper == 'N':
                        self.combo_boxes[i].setCurrentText("N Component (North)")
                    elif header_upper == 'Z' or 'VERT' in header_upper or 'UP' in header_upper or 'DOWN' in header_upper:
                        self.combo_boxes[i].setCurrentText("Z Component (Vertical)")
                    elif 'FREQ' in header_upper:
                        self.combo_boxes[i].setCurrentText("Metadata")
                    elif 'AZIM' in header_upper or 'SLOW' in header_upper:
                        self.combo_boxes[i].setCurrentText("Metadata")

            # Then, use data-based auto-detection for any unmapped columns
            time_col_idx = None

            for i, col_data in enumerate(self.columns_data):
                if i >= len(self.combo_boxes):
                    break

                # Skip if already mapped
                if self.combo_boxes[i].currentText() != "Skipped":
                    continue

                try:
                    arr = np.array(col_data, dtype=float)
                    arr = arr[np.isfinite(arr)]  # Remove NaN/inf

                    if arr.size < 2:
                        continue

                    min_val = float(np.min(arr))
                    max_val = float(np.max(arr))
                    is_monotonic = np.all(np.diff(arr) >= 0)

                    # Detect time: monotonically increasing, reasonable range
                    if is_monotonic and min_val >= 0:
                        if max_val > 10000:  # Likely datetime timestamp
                            self.combo_boxes[i].setCurrentText("Time (datetime)")
                            time_col_idx = i
                        elif max_val < 1000000:  # Likely time in seconds
                            self.combo_boxes[i].setCurrentText("Time (seconds)")
                            time_col_idx = i

                except:
                    pass

            # If we still have unmapped columns, try to map E, N, Z
            remaining_cols = [i for i in range(len(self.combo_boxes)) if self.combo_boxes[i].currentText() == "Skipped"]

            if len(remaining_cols) == 3:
                # Likely E, N, Z components
                self.combo_boxes[remaining_cols[0]].setCurrentText("E Component (East)")
                self.combo_boxes[remaining_cols[1]].setCurrentText("N Component (North)")
                self.combo_boxes[remaining_cols[2]].setCurrentText("Z Component (Vertical)")

            elif len(remaining_cols) > 3:
                # Map first 3 remaining as E, N, Z
                self.combo_boxes[remaining_cols[0]].setCurrentText("E Component (East)")
                if len(remaining_cols) > 1:
                    self.combo_boxes[remaining_cols[1]].setCurrentText("N Component (North)")
                if len(remaining_cols) > 2:
                    self.combo_boxes[remaining_cols[2]].setCurrentText("Z Component (Vertical)")

        def _validate(self):
            """Validate required columns are mapped."""
            types = [cb.currentText() for cb in self.combo_boxes]

            has_e = "E Component (East)" in types
            has_n = "N Component (North)" in types
            has_z = "Z Component (Vertical)" in types

            # Check for duplicates
            used_types = [t for t in types if t != "Skipped" and t != "Metadata"]
            has_duplicates = len(used_types) != len(set(used_types))

            if has_duplicates:
                self.status_label.setText("<span style='color:red;'>Error: Cannot map same type to multiple columns</span>")
                self.btn_ok.setEnabled(False)
            elif has_e and has_n and has_z:
                self.status_label.setText("<span style='color:green;'>Valid mapping - Ready to import</span>")
                self.btn_ok.setEnabled(True)
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
            Return column mapping dict.

            Returns:
                dict: {type_str: col_idx} mapping
            """
            mapping = {}
            for i, cb in enumerate(self.combo_boxes):
                type_str = cb.currentText()
                if type_str != "Skipped":
                    mapping[type_str] = i
            return mapping

        def should_remember(self):
            """Return whether user wants to remember this mapping."""
            return self.chk_remember.isChecked()


else:
    # Dummy class when PyQt5 not available
    class SeismicColumnMapperDialog:
        def __init__(self, *args, **kwargs):
            raise ImportError("PyQt5 is required for GUI functionality")
