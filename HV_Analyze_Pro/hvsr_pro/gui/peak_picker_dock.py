"""
Peak Picker Dock for HVSR Pro
==============================

Interactive peak selection and management with multiple detection modes.
Allows auto-detection and manual peak marking.
"""

from PyQt5.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QComboBox, QSpinBox, QDoubleSpinBox, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog,
    QMessageBox, QAbstractItemView, QCheckBox
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from pathlib import Path
from datetime import datetime
import csv
import json
from typing import List, Dict, Optional


class PeakPickerDock(QDockWidget):
    """
    Dock widget for peak selection and management.
    
    Features:
    - Multiple detection modes (Auto Top N, Auto Multi, Manual)
    - Dynamic settings panel based on mode
    - Peak list table with delete functionality
    - CSV and JSON export
    - Integration with plot markers
    
    Signals:
        peaks_changed: Emitted when peak list changes
        manual_mode_requested: Emitted when user wants to manually pick peak
        detect_peaks_requested: Emitted when user clicks detect button
    """
    
    peaks_changed = pyqtSignal(list)  # List of peak dicts
    manual_mode_requested = pyqtSignal(bool)  # True=activate, False=deactivate
    detect_peaks_requested = pyqtSignal(str, dict)  # mode, settings
    
    def __init__(self, parent=None):
        """
        Initialize peak picker dock.
        
        Args:
            parent: Parent window (main window)
        """
        super().__init__("Peak Picker", parent)
        self.setObjectName("PeakPickerDock")
        
        # Data
        self.peaks = []  # List of peak dictionaries
        self.current_mode = "auto_top_n"
        
        # References (set by parent)
        self.hvsr_result = None
        self.frequencies = None
        self.mean_hvsr = None
        
        # Set dock features
        self.setFeatures(
            QDockWidget.DockWidgetMovable |
            QDockWidget.DockWidgetFloatable
        )
        
        # Create UI
        self._create_ui()
        
        # Connect signals
        self._connect_signals()
    
    def _create_ui(self):
        """Create dock UI."""
        # Main widget
        widget = QWidget(self)
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(8)
        
        # Mode selector
        mode_group = self._create_mode_selector()
        main_layout.addWidget(mode_group)
        
        # Settings panel (dynamic)
        self.settings_group = self._create_settings_panel()
        main_layout.addWidget(self.settings_group)
        
        # Action buttons
        action_layout = self._create_action_buttons()
        main_layout.addLayout(action_layout)
        
        # Peak list table
        table_group = self._create_peak_table()
        main_layout.addWidget(table_group)
        
        # Export buttons
        export_layout = self._create_export_buttons()
        main_layout.addLayout(export_layout)
        
        # Status label
        self.status_label = QLabel("No peaks detected")
        self.status_label.setStyleSheet("QLabel { color: gray; font-size: 10px; }")
        main_layout.addWidget(self.status_label)
        
        self.setWidget(widget)
    
    def _create_mode_selector(self) -> QGroupBox:
        """Create mode selection group."""
        group = QGroupBox("Detection Mode")
        layout = QVBoxLayout(group)
        
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Auto Top N Peaks", "auto_top_n")
        self.mode_combo.addItem("Auto Multi-Peak", "auto_multi")
        self.mode_combo.addItem("Manual Picking", "manual")
        self.mode_combo.setToolTip(
            "Auto Top N: Find N highest peaks\n"
            "Auto Multi: Find all peaks above threshold\n"
            "Manual: Click on curve to mark peaks"
        )
        layout.addWidget(self.mode_combo)
        
        return group
    
    def _create_settings_panel(self) -> QGroupBox:
        """Create dynamic settings panel."""
        group = QGroupBox("Settings")
        self.settings_layout = QVBoxLayout(group)
        
        # Auto Top N settings
        self.top_n_widget = self._create_top_n_settings()
        self.settings_layout.addWidget(self.top_n_widget)
        
        # Auto Multi settings
        self.multi_widget = self._create_multi_settings()
        self.settings_layout.addWidget(self.multi_widget)
        self.multi_widget.setVisible(False)
        
        # Manual settings
        self.manual_widget = self._create_manual_settings()
        self.settings_layout.addWidget(self.manual_widget)
        self.manual_widget.setVisible(False)
        
        return group
    
    def _create_top_n_settings(self) -> QWidget:
        """Create Auto Top N settings."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # N peaks
        n_layout = QHBoxLayout()
        n_layout.addWidget(QLabel("Number of Peaks:"))
        self.n_peaks_spin = QSpinBox()
        self.n_peaks_spin.setRange(1, 10)
        self.n_peaks_spin.setValue(3)
        self.n_peaks_spin.setToolTip("How many peaks to find (highest prominence)")
        n_layout.addWidget(self.n_peaks_spin)
        layout.addLayout(n_layout)
        
        # Prominence
        prom_layout = QHBoxLayout()
        prom_layout.addWidget(QLabel("Min Prominence:"))
        self.prominence_spin = QDoubleSpinBox()
        self.prominence_spin.setRange(0.1, 5.0)
        self.prominence_spin.setSingleStep(0.1)
        self.prominence_spin.setValue(0.5)
        self.prominence_spin.setDecimals(1)
        self.prominence_spin.setToolTip("Minimum peak prominence")
        prom_layout.addWidget(self.prominence_spin)
        layout.addLayout(prom_layout)
        
        # Frequency range
        freq_layout = QHBoxLayout()
        freq_layout.addWidget(QLabel("Freq Range (Hz):"))
        self.freq_min_spin = QDoubleSpinBox()
        self.freq_min_spin.setRange(0.1, 50.0)
        self.freq_min_spin.setValue(0.2)
        self.freq_min_spin.setDecimals(1)
        self.freq_min_spin.setToolTip("Minimum frequency to search")
        freq_layout.addWidget(self.freq_min_spin)
        
        freq_layout.addWidget(QLabel("-"))
        self.freq_max_spin = QDoubleSpinBox()
        self.freq_max_spin.setRange(0.1, 50.0)
        self.freq_max_spin.setValue(20.0)
        self.freq_max_spin.setDecimals(1)
        self.freq_max_spin.setToolTip("Maximum frequency to search")
        freq_layout.addWidget(self.freq_max_spin)
        layout.addLayout(freq_layout)
        
        return widget
    
    def _create_multi_settings(self) -> QWidget:
        """Create Auto Multi-Peak settings."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # Prominence threshold
        prom_layout = QHBoxLayout()
        prom_layout.addWidget(QLabel("Prominence Threshold:"))
        self.multi_prom_spin = QDoubleSpinBox()
        self.multi_prom_spin.setRange(0.1, 5.0)
        self.multi_prom_spin.setSingleStep(0.1)
        self.multi_prom_spin.setValue(0.3)
        self.multi_prom_spin.setDecimals(1)
        self.multi_prom_spin.setToolTip("Minimum prominence for peak detection")
        prom_layout.addWidget(self.multi_prom_spin)
        layout.addLayout(prom_layout)
        
        # Min distance
        dist_layout = QHBoxLayout()
        dist_layout.addWidget(QLabel("Min Peak Distance:"))
        self.min_distance_spin = QSpinBox()
        self.min_distance_spin.setRange(3, 50)
        self.min_distance_spin.setValue(5)
        self.min_distance_spin.setToolTip("Minimum samples between peaks")
        dist_layout.addWidget(self.min_distance_spin)
        layout.addLayout(dist_layout)
        
        # Frequency range
        freq_layout = QHBoxLayout()
        freq_layout.addWidget(QLabel("Freq Range (Hz):"))
        self.multi_freq_min_spin = QDoubleSpinBox()
        self.multi_freq_min_spin.setRange(0.1, 50.0)
        self.multi_freq_min_spin.setValue(0.2)
        self.multi_freq_min_spin.setDecimals(1)
        freq_layout.addWidget(self.multi_freq_min_spin)
        
        freq_layout.addWidget(QLabel("-"))
        self.multi_freq_max_spin = QDoubleSpinBox()
        self.multi_freq_max_spin.setRange(0.1, 50.0)
        self.multi_freq_max_spin.setValue(20.0)
        self.multi_freq_max_spin.setDecimals(1)
        freq_layout.addWidget(self.multi_freq_max_spin)
        layout.addLayout(freq_layout)
        
        return widget
    
    def _create_manual_settings(self) -> QWidget:
        """Create Manual picking settings."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        info = QLabel(
            "Click on HVSR curve to mark peak.\n"
            "Drag to position label, release to confirm.\n"
            "Click 'Add Manual Peak' to activate picking mode."
        )
        info.setWordWrap(True)
        info.setStyleSheet("QLabel { color: #555; font-size: 10px; }")
        layout.addWidget(info)
        
        return widget
    
    def _create_action_buttons(self) -> QHBoxLayout:
        """Create action button layout."""
        layout = QHBoxLayout()
        
        # Detect peaks button (for auto modes)
        self.detect_btn = QPushButton("Detect Peaks")
        self.detect_btn.setToolTip("Run peak detection with current settings")
        self.detect_btn.setStyleSheet("QPushButton { font-weight: bold; background-color: #4CAF50; color: white; }")
        layout.addWidget(self.detect_btn)
        
        # Add manual peak button (for manual mode)
        self.add_manual_btn = QPushButton("Add Manual Peak")
        self.add_manual_btn.setToolTip("Activate manual peak picking mode")
        self.add_manual_btn.setVisible(False)
        self.add_manual_btn.setCheckable(True)
        layout.addWidget(self.add_manual_btn)
        
        # Clear all button
        self.clear_btn = QPushButton("Clear All")
        self.clear_btn.setToolTip("Remove all peaks")
        layout.addWidget(self.clear_btn)
        
        # Undo last button
        self.undo_btn = QPushButton("Undo Last")
        self.undo_btn.setToolTip("Remove last added peak")
        self.undo_btn.setEnabled(False)
        layout.addWidget(self.undo_btn)
        
        return layout
    
    def _create_peak_table(self) -> QGroupBox:
        """Create peak list table."""
        group = QGroupBox("Peak List")
        layout = QVBoxLayout(group)
        
        self.peak_table = QTableWidget(0, 6)
        self.peak_table.setHorizontalHeaderLabels([
            '#', 'Freq (Hz)', 'Amp', 'Source', 'f₀', 'Del'
        ])
        
        # Configure columns
        header = self.peak_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        
        self.peak_table.setColumnWidth(0, 30)   # #
        self.peak_table.setColumnWidth(4, 40)   # f₀ checkbox
        self.peak_table.setColumnWidth(5, 40)   # Delete button
        
        # Make read-only except delete buttons
        self.peak_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.peak_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.peak_table.setSelectionMode(QAbstractItemView.SingleSelection)
        
        # Enable sorting
        self.peak_table.setSortingEnabled(True)
        
        layout.addWidget(self.peak_table)
        
        return group
    
    def _create_export_buttons(self) -> QHBoxLayout:
        """Create export button layout."""
        layout = QHBoxLayout()
        
        self.export_csv_btn = QPushButton("Export CSV")
        self.export_csv_btn.setToolTip("Export peak list to CSV file")
        self.export_csv_btn.setEnabled(False)
        layout.addWidget(self.export_csv_btn)
        
        self.export_json_btn = QPushButton("Export JSON")
        self.export_json_btn.setToolTip("Export peak list to JSON file")
        self.export_json_btn.setEnabled(False)
        layout.addWidget(self.export_json_btn)
        
        return layout
    
    def _connect_signals(self):
        """Connect internal signals."""
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        self.detect_btn.clicked.connect(self.on_detect_clicked)
        self.add_manual_btn.toggled.connect(self.on_manual_toggled)
        self.clear_btn.clicked.connect(self.clear_all_peaks)
        self.undo_btn.clicked.connect(self.undo_last_peak)
        self.export_csv_btn.clicked.connect(self.export_to_csv)
        self.export_json_btn.clicked.connect(self.export_to_json)
    
    def on_mode_changed(self, index: int):
        """Handle mode selection change."""
        mode = self.mode_combo.itemData(index)
        self.current_mode = mode
        
        # Show/hide appropriate settings
        self.top_n_widget.setVisible(mode == "auto_top_n")
        self.multi_widget.setVisible(mode == "auto_multi")
        self.manual_widget.setVisible(mode == "manual")
        
        # Show/hide appropriate buttons
        is_manual = (mode == "manual")
        self.detect_btn.setVisible(not is_manual)
        self.add_manual_btn.setVisible(is_manual)
        
        # Update status
        mode_names = {
            "auto_top_n": "Auto Top N",
            "auto_multi": "Auto Multi-Peak",
            "manual": "Manual Picking"
        }
        self.status_label.setText(f"Mode: {mode_names.get(mode, 'Unknown')}")
    
    def on_detect_clicked(self):
        """Handle detect peaks button click."""
        if self.hvsr_result is None:
            QMessageBox.warning(self, "No Data", "Please load and process HVSR data first.")
            return
        
        # Get settings based on mode
        settings = self.get_current_settings()
        
        # Emit signal for parent to handle
        self.detect_peaks_requested.emit(self.current_mode, settings)
    
    def on_manual_toggled(self, checked: bool):
        """Handle manual peak picking button toggle."""
        if checked:
            if self.hvsr_result is None:
                QMessageBox.warning(self, "No Data", "Please load and process HVSR data first.")
                self.add_manual_btn.setChecked(False)
                return
            
            self.add_manual_btn.setText("Picking Active...")
            self.add_manual_btn.setStyleSheet("QPushButton { background-color: #FF9800; }")
        else:
            self.add_manual_btn.setText("Add Manual Peak")
            self.add_manual_btn.setStyleSheet("")
        
        # Emit signal to parent
        self.manual_mode_requested.emit(checked)
    
    def get_current_settings(self) -> Dict:
        """Get settings for current mode."""
        if self.current_mode == "auto_top_n":
            return {
                'n_peaks': self.n_peaks_spin.value(),
                'prominence': self.prominence_spin.value(),
                'freq_min': self.freq_min_spin.value(),
                'freq_max': self.freq_max_spin.value()
            }
        elif self.current_mode == "auto_multi":
            return {
                'prominence': self.multi_prom_spin.value(),
                'min_distance': self.min_distance_spin.value(),
                'freq_min': self.multi_freq_min_spin.value(),
                'freq_max': self.multi_freq_max_spin.value()
            }
        else:
            return {}
    
    def set_hvsr_data(self, hvsr_result, frequencies, mean_hvsr):
        """Set HVSR data reference."""
        self.hvsr_result = hvsr_result
        self.frequencies = frequencies
        self.mean_hvsr = mean_hvsr
    
    def add_peak(self, frequency: float, amplitude: float, source: str, is_f0: bool = False):
        """
        Add a peak to the list.
        
        Args:
            frequency: Peak frequency in Hz
            amplitude: Peak amplitude (H/V ratio)
            source: Source of peak ('Auto Top N', 'Auto Multi', 'Manual')
            is_f0: Whether this peak is marked as fundamental frequency
        """
        peak = {
            'frequency': frequency,
            'amplitude': amplitude,
            'source': source,
            'is_f0': is_f0,
            'timestamp': datetime.now()
        }
        
        self.peaks.append(peak)
        self._update_table()
        self.peaks_changed.emit(self.peaks)
        
        # Update status
        self.status_label.setText(f"{len(self.peaks)} peak(s) detected")
        
        # Enable buttons
        self.undo_btn.setEnabled(True)
        self.export_csv_btn.setEnabled(True)
        self.export_json_btn.setEnabled(True)
    
    def add_peaks(self, peaks_list: List[Dict]):
        """
        Add multiple peaks at once.
        
        Args:
            peaks_list: List of peak dictionaries
        """
        for peak_data in peaks_list:
            peak = {
                'frequency': peak_data['frequency'],
                'amplitude': peak_data['amplitude'],
                'source': peak_data.get('source', 'Auto'),
                'is_f0': peak_data.get('is_f0', False),
                'timestamp': datetime.now()
            }
            self.peaks.append(peak)
        
        self._update_table()
        self.peaks_changed.emit(self.peaks)
        
        # Update status
        self.status_label.setText(f"{len(self.peaks)} peak(s) detected")
        
        # Enable buttons
        if self.peaks:
            self.undo_btn.setEnabled(True)
            self.export_csv_btn.setEnabled(True)
            self.export_json_btn.setEnabled(True)
    
    def delete_peak(self, row: int):
        """Delete peak at given row."""
        if 0 <= row < len(self.peaks):
            self.peaks.pop(row)
            self._update_table()
            self.peaks_changed.emit(self.peaks)
            
            # Update status
            self.status_label.setText(f"{len(self.peaks)} peak(s) detected")
            
            # Update buttons
            if not self.peaks:
                self.undo_btn.setEnabled(False)
                self.export_csv_btn.setEnabled(False)
                self.export_json_btn.setEnabled(False)
    
    def clear_all_peaks(self):
        """Clear all peaks."""
        if not self.peaks:
            return
        
        reply = QMessageBox.question(
            self, 'Clear All Peaks',
            f'Remove all {len(self.peaks)} peaks?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.peaks.clear()
            self._update_table()
            self.peaks_changed.emit(self.peaks)
            
            self.status_label.setText("No peaks detected")
            self.undo_btn.setEnabled(False)
            self.export_csv_btn.setEnabled(False)
            self.export_json_btn.setEnabled(False)
    
    def undo_last_peak(self):
        """Remove last added peak."""
        if self.peaks:
            self.peaks.pop()
            self._update_table()
            self.peaks_changed.emit(self.peaks)
            
            self.status_label.setText(f"{len(self.peaks)} peak(s) detected")
            
            if not self.peaks:
                self.undo_btn.setEnabled(False)
                self.export_csv_btn.setEnabled(False)
                self.export_json_btn.setEnabled(False)
    
    def _update_table(self):
        """Update peak table display."""
        self.peak_table.setSortingEnabled(False)
        self.peak_table.setRowCount(0)
        
        for i, peak in enumerate(self.peaks):
            row = self.peak_table.rowCount()
            self.peak_table.insertRow(row)
            
            # Column 0: #
            num_item = QTableWidgetItem(str(i + 1))
            num_item.setTextAlignment(Qt.AlignCenter)
            self.peak_table.setItem(row, 0, num_item)
            
            # Column 1: Frequency
            freq_item = QTableWidgetItem(f"{peak['frequency']:.2f}")
            freq_item.setTextAlignment(Qt.AlignCenter)
            self.peak_table.setItem(row, 1, freq_item)
            
            # Column 2: Amplitude
            amp_item = QTableWidgetItem(f"{peak['amplitude']:.2f}")
            amp_item.setTextAlignment(Qt.AlignCenter)
            self.peak_table.setItem(row, 2, amp_item)
            
            # Column 3: Source
            source_item = QTableWidgetItem(peak['source'])
            source_item.setTextAlignment(Qt.AlignCenter)
            
            # Color code by source
            if 'Manual' in peak['source']:
                source_item.setForeground(QColor('#4CAF50'))  # Green
            elif 'Multi' in peak['source']:
                source_item.setForeground(QColor('#FF9800'))  # Orange
            else:
                source_item.setForeground(QColor('#2196F3'))  # Blue
            
            self.peak_table.setItem(row, 3, source_item)
            
            # Column 4: f₀ checkbox
            f0_checkbox = QCheckBox()
            f0_checkbox.setChecked(peak.get('is_f0', False))
            f0_checkbox.setStyleSheet("QCheckBox { margin-left: 12px; }")
            f0_checkbox.setToolTip("Mark as fundamental frequency (f₀)")
            f0_checkbox.stateChanged.connect(lambda state, r=i: self.on_f0_toggled(r, state))
            
            # Center the checkbox
            checkbox_widget = QWidget()
            checkbox_layout = QHBoxLayout(checkbox_widget)
            checkbox_layout.addWidget(f0_checkbox)
            checkbox_layout.setAlignment(Qt.AlignCenter)
            checkbox_layout.setContentsMargins(0, 0, 0, 0)
            self.peak_table.setCellWidget(row, 4, checkbox_widget)
            
            # Column 5: Delete button
            delete_btn = QPushButton('×')
            delete_btn.setStyleSheet("QPushButton { color: red; font-weight: bold; }")
            delete_btn.setToolTip(f"Delete peak at {peak['frequency']:.2f} Hz")
            delete_btn.clicked.connect(lambda checked, r=i: self.delete_peak(r))
            self.peak_table.setCellWidget(row, 5, delete_btn)
        
        self.peak_table.setSortingEnabled(True)
    
    def on_f0_toggled(self, peak_index: int, state: int):
        """
        Handle f₀ checkbox toggle.
        Only one peak can be f₀ at a time.
        
        Args:
            peak_index: Index of peak in self.peaks list
            state: Qt.CheckState value (0=unchecked, 2=checked)
        """
        if state == 2:  # Checked
            # Uncheck all other peaks
            for i, peak in enumerate(self.peaks):
                if i != peak_index:
                    peak['is_f0'] = False
                else:
                    peak['is_f0'] = True
            
            # Rebuild table to reflect changes
            self._update_table()
            
            # Emit signal to update plot
            self.peaks_changed.emit(self.peaks)
            
            freq = self.peaks[peak_index]['frequency']
            print(f"[PeakPickerDock] f₀ set to {freq:.2f} Hz")
        else:  # Unchecked
            self.peaks[peak_index]['is_f0'] = False
            self.peaks_changed.emit(self.peaks)
    
    def export_to_csv(self):
        """Export peaks to CSV file."""
        if not self.peaks:
            QMessageBox.information(self, "No Peaks", "No peaks to export.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Peaks to CSV", "", "CSV Files (*.csv)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    
                    # Write header
                    writer.writerow([
                        'Peak_Number', 'Frequency_Hz', 'Amplitude', 'Source', 'Is_f0', 'DateTime'
                    ])
                    
                    # Write peaks
                    for i, peak in enumerate(self.peaks, 1):
                        writer.writerow([
                            i,
                            f"{peak['frequency']:.3f}",
                            f"{peak['amplitude']:.3f}",
                            peak['source'],
                            'Yes' if peak.get('is_f0', False) else 'No',
                            peak['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                        ])
                
                QMessageBox.information(self, "Export Successful", f"Exported {len(self.peaks)} peaks to:\n{file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export CSV:\n{str(e)}")
    
    def export_to_json(self):
        """Export peaks to JSON file."""
        if not self.peaks:
            QMessageBox.information(self, "No Peaks", "No peaks to export.")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Peaks to JSON", "", "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                # Prepare data
                export_data = {
                    'export_datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'total_peaks': len(self.peaks),
                    'fundamental_frequency': next((p['frequency'] for p in self.peaks if p.get('is_f0', False)), None),
                    'peaks': [
                        {
                            'peak_number': i + 1,
                            'frequency_hz': peak['frequency'],
                            'amplitude': peak['amplitude'],
                            'source': peak['source'],
                            'is_f0': peak.get('is_f0', False),
                            'datetime': peak['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                        }
                        for i, peak in enumerate(self.peaks)
                    ]
                }
                
                with open(file_path, 'w') as f:
                    json.dump(export_data, f, indent=2)
                
                QMessageBox.information(self, "Export Successful", f"Exported {len(self.peaks)} peaks to:\n{file_path}")
                
            except Exception as e:
                QMessageBox.critical(self, "Export Error", f"Failed to export JSON:\n{str(e)}")
    
    def get_peaks(self) -> List[Dict]:
        """Get current peak list."""
        return self.peaks.copy()
