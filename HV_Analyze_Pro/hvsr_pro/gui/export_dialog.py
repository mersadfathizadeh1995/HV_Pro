"""
Advanced Export Dialog for HVSR Pro
====================================

Comprehensive visualization export with multiple plot types.
"""

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QCheckBox,
    QPushButton, QLabel, QLineEdit, QFileDialog, QComboBox,
    QSpinBox, QProgressBar, QMessageBox, QScrollArea, QWidget
)
from PyQt5.QtCore import Qt, pyqtSignal, QThread
from pathlib import Path
from typing import Dict, List, Optional
import traceback


class ExportWorker(QThread):
    """Background worker for generating plots."""
    progress = pyqtSignal(int, str)  # progress, message
    finished = pyqtSignal(list)  # list of saved files
    error = pyqtSignal(str)
    
    def __init__(self, result, windows, data, output_dir, plot_types, dpi):
        super().__init__()
        self.result = result
        self.windows = windows
        self.data = data
        self.output_dir = Path(output_dir)
        self.plot_types = plot_types
        self.dpi = dpi
        self.saved_files = []
    
    def run(self):
        """Generate selected plots."""
        try:
            from hvsr_pro.visualization.plotter import HVSRPlotter
            import matplotlib.pyplot as plt
            
            plotter = HVSRPlotter()
            total = len(self.plot_types)
            
            for i, plot_type in enumerate(self.plot_types):
                self.progress.emit(int((i / total) * 100), f"Generating {plot_type}...")
                
                try:
                    filepath = self.output_dir / f"{plot_type}.png"
                    
                    if plot_type == 'hvsr_curve':
                        fig = plotter.plot_result(self.result, show_peaks=True, 
                                                 title='HVSR Curve (Publication Quality)')
                        fig.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
                        plt.close(fig)
                        
                    elif plot_type == 'hvsr_with_windows':
                        fig = plotter.plot_with_windows(self.result, 
                                                       title='HVSR with Individual Windows')
                        fig.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
                        plt.close(fig)
                        
                    elif plot_type == 'mean_vs_median':
                        fig = plotter.plot_mean_vs_median(self.result)
                        fig.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
                        plt.close(fig)
                        
                    elif plot_type == 'quality_metrics':
                        fig = plotter.plot_quality_metrics(self.windows)
                        fig.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
                        plt.close(fig)
                        
                    elif plot_type == 'quality_histogram':
                        fig = plotter.plot_quality_histogram(self.windows)
                        fig.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
                        plt.close(fig)
                        
                    elif plot_type == 'selected_metrics':
                        fig = plotter.plot_selected_metrics(self.windows)
                        fig.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
                        plt.close(fig)
                        
                    elif plot_type == 'statistics_dashboard':
                        fig = plotter.plot_statistics(self.result)
                        fig.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
                        plt.close(fig)
                        
                    elif plot_type == 'window_timeline':
                        fig = plotter.plot_window_timeline(self.windows)
                        fig.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
                        plt.close(fig)
                        
                    elif plot_type == 'window_timeseries':
                        fig = plotter.plot_window_timeseries(self.windows, self.data)
                        fig.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
                        plt.close(fig)
                        
                    elif plot_type == 'window_spectrogram':
                        fig = plotter.plot_window_spectrogram(self.windows, self.data)
                        fig.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
                        plt.close(fig)
                        
                    elif plot_type == 'peak_analysis':
                        if self.result.primary_peak:
                            fig = plotter.plot_peak_details(self.result)
                            fig.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
                            plt.close(fig)
                        else:
                            self.progress.emit(int((i / total) * 100), 
                                             f"Skipping {plot_type} (no peaks)...")
                            continue
                        
                    elif plot_type == 'complete_dashboard':
                        fig = plotter.plot_dashboard(self.result, self.windows)
                        fig.savefig(filepath, dpi=self.dpi, bbox_inches='tight')
                        plt.close(fig)
                    
                    self.saved_files.append(str(filepath))
                    
                except Exception as e:
                    self.progress.emit(int((i / total) * 100), 
                                     f"Error generating {plot_type}: {str(e)}")
                    continue
            
            self.progress.emit(100, "Complete!")
            self.finished.emit(self.saved_files)
            
        except Exception as e:
            self.error.emit(f"Export error: {str(e)}\n\n{traceback.format_exc()}")


class ExportDialog(QDialog):
    """
    Advanced export dialog for HVSR visualizations.
    
    Allows selection of multiple plot types and export settings.
    """
    
    def __init__(self, parent=None, result=None, windows=None, data=None):
        super().__init__(parent)
        self.result = result
        self.windows = windows
        self.data = data
        self.worker = None
        
        self.setWindowTitle("Generate Visualization Report")
        self.resize(600, 700)
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize user interface."""
        layout = QVBoxLayout(self)
        
        # Create scroll area for checkboxes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Title
        title = QLabel("Select plots to generate:")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        scroll_layout.addWidget(title)
        
        # Checkbox groups
        self.checkboxes = {}
        
        # Group 1: HVSR Analysis Plots
        hvsr_group = QGroupBox("HVSR Analysis Plots")
        hvsr_layout = QVBoxLayout(hvsr_group)
        
        hvsr_plots = [
            ('hvsr_curve', 'Main HVSR Curve (publication quality)'),
            ('hvsr_with_windows', 'HVSR with Individual Windows'),
            ('mean_vs_median', 'Mean vs Median Comparison'),
        ]
        
        for key, label in hvsr_plots:
            cb = QCheckBox(label)
            cb.setChecked(True)
            self.checkboxes[key] = cb
            hvsr_layout.addWidget(cb)
        
        scroll_layout.addWidget(hvsr_group)
        
        # Group 2: Statistics & Quality
        stats_group = QGroupBox("Statistics & Quality")
        stats_layout = QVBoxLayout(stats_group)
        
        stats_plots = [
            ('quality_metrics', 'Window Quality Metrics'),
            ('quality_histogram', 'Quality Distribution Histogram'),
            ('selected_metrics', 'Selected Metrics Comparison'),
            ('statistics_dashboard', 'Statistics Dashboard'),
        ]
        
        for key, label in stats_plots:
            cb = QCheckBox(label)
            cb.setChecked(True)
            self.checkboxes[key] = cb
            stats_layout.addWidget(cb)
        
        scroll_layout.addWidget(stats_group)
        
        # Group 3: Time Series & Spectrograms
        ts_group = QGroupBox("Time Series & Spectrograms")
        ts_layout = QVBoxLayout(ts_group)
        
        ts_plots = [
            ('window_timeline', 'Window Timeline View'),
            ('window_timeseries', 'Window Timeseries (3-component)'),
            ('window_spectrogram', 'Window Spectrogram'),
        ]
        
        for key, label in ts_plots:
            cb = QCheckBox(label)
            cb.setChecked(False)  # These are slower, off by default
            self.checkboxes[key] = cb
            ts_layout.addWidget(cb)
        
        scroll_layout.addWidget(ts_group)
        
        # Group 4: Peak Analysis
        peak_group = QGroupBox("Peak Analysis")
        peak_layout = QVBoxLayout(peak_group)
        
        peak_plots = [
            ('peak_analysis', 'Peak Identification Details'),
        ]
        
        for key, label in peak_plots:
            cb = QCheckBox(label)
            cb.setChecked(True)
            self.checkboxes[key] = cb
            peak_layout.addWidget(cb)
        
        scroll_layout.addWidget(peak_group)
        
        # Group 5: Complete Report
        complete_group = QGroupBox("Complete Report")
        complete_layout = QVBoxLayout(complete_group)
        
        complete_plots = [
            ('complete_dashboard', 'All-in-One Dashboard'),
        ]
        
        for key, label in complete_plots:
            cb = QCheckBox(label)
            cb.setChecked(True)
            self.checkboxes[key] = cb
            complete_layout.addWidget(cb)
        
        scroll_layout.addWidget(complete_group)
        
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        # Quick selection buttons
        quick_layout = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.select_all)
        quick_layout.addWidget(select_all_btn)
        
        select_none_btn = QPushButton("Select None")
        select_none_btn.clicked.connect(self.select_none)
        quick_layout.addWidget(select_none_btn)
        
        select_fast_btn = QPushButton("Fast Set (no timeseries)")
        select_fast_btn.clicked.connect(self.select_fast)
        quick_layout.addWidget(select_fast_btn)
        
        layout.addLayout(quick_layout)
        
        # Output settings
        settings_group = QGroupBox("Output Settings")
        settings_layout = QVBoxLayout(settings_group)
        
        # DPI
        dpi_layout = QHBoxLayout()
        dpi_layout.addWidget(QLabel("DPI (Resolution):"))
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 600)
        self.dpi_spin.setValue(300)
        self.dpi_spin.setSuffix(" dpi")
        dpi_layout.addWidget(self.dpi_spin)
        dpi_layout.addStretch()
        settings_layout.addLayout(dpi_layout)
        
        # Output directory
        dir_layout = QHBoxLayout()
        dir_layout.addWidget(QLabel("Output Directory:"))
        self.dir_edit = QLineEdit()
        self.dir_edit.setPlaceholderText("Select output directory...")
        dir_layout.addWidget(self.dir_edit)
        
        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self.browse_directory)
        dir_layout.addWidget(browse_btn)
        settings_layout.addLayout(dir_layout)
        
        layout.addWidget(settings_group)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("")
        self.progress_label.setVisible(False)
        layout.addWidget(self.progress_label)
        
        # Action buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.generate_btn = QPushButton("Generate Plots")
        self.generate_btn.clicked.connect(self.generate_plots)
        self.generate_btn.setStyleSheet("font-weight: bold; padding: 8px 16px;")
        button_layout.addWidget(self.generate_btn)
        
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.reject)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def select_all(self):
        """Select all checkboxes."""
        for cb in self.checkboxes.values():
            cb.setChecked(True)
    
    def select_none(self):
        """Deselect all checkboxes."""
        for cb in self.checkboxes.values():
            cb.setChecked(False)
    
    def select_fast(self):
        """Select fast-generating plots only."""
        slow_plots = ['window_timeseries', 'window_spectrogram']
        for key, cb in self.checkboxes.items():
            cb.setChecked(key not in slow_plots)
    
    def browse_directory(self):
        """Browse for output directory."""
        directory = QFileDialog.getExistingDirectory(
            self, "Select Output Directory"
        )
        if directory:
            self.dir_edit.setText(directory)
    
    def generate_plots(self):
        """Generate selected plots."""
        # Get selected plots
        selected = [key for key, cb in self.checkboxes.items() if cb.isChecked()]
        
        if not selected:
            QMessageBox.warning(self, "No Plots Selected", 
                              "Please select at least one plot type to generate.")
            return
        
        # Get output directory
        output_dir = self.dir_edit.text()
        if not output_dir:
            QMessageBox.warning(self, "No Directory", 
                              "Please select an output directory.")
            return
        
        # Create directory if needed
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        # Disable generate button
        self.generate_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        
        # Start worker thread
        dpi = self.dpi_spin.value()
        self.worker = ExportWorker(self.result, self.windows, self.data, 
                                   output_dir, selected, dpi)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()
    
    def on_progress(self, value, message):
        """Update progress."""
        self.progress_bar.setValue(value)
        self.progress_label.setText(message)
    
    def on_finished(self, saved_files):
        """Handle completion."""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.generate_btn.setEnabled(True)
        
        QMessageBox.information(
            self, "Export Complete",
            f"Successfully generated {len(saved_files)} plots!\n\n"
            f"Output directory:\n{self.dir_edit.text()}"
        )
        
        self.accept()
    
    def on_error(self, error_msg):
        """Handle error."""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.generate_btn.setEnabled(True)
        
        QMessageBox.critical(self, "Export Error", error_msg)
