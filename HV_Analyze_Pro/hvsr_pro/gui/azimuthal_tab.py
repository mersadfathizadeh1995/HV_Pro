"""
Azimuthal Processing Tab for HVSR Pro
======================================

GUI tab for azimuthal HVSR analysis with 3D visualization.
"""

from typing import Optional
import numpy as np

try:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
        QPushButton, QLabel, QSpinBox, QDoubleSpinBox,
        QComboBox, QCheckBox, QProgressBar, QTextEdit,
        QFileDialog, QMessageBox, QSplitter, QScrollArea
    )
    from PyQt5.QtCore import Qt, QThread, pyqtSignal
    from PyQt5.QtGui import QFont
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False

try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
except ImportError:
    pass

from hvsr_pro.gui.collapsible_data_panel import CollapsibleDataPanel


class AzimuthalProcessingThread(QThread):
    """Background thread for azimuthal HVSR processing."""
    
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(object)  # AzimuthalHVSRResult
    error = pyqtSignal(str)
    
    def __init__(self, windows, settings):
        super().__init__()
        self.windows = windows
        self.settings = settings
    
    def run(self):
        """Execute azimuthal processing."""
        try:
            from hvsr_pro.processing.azimuthal import AzimuthalHVSRProcessor
            
            # Create processor
            processor = AzimuthalHVSRProcessor(
                azimuths=np.arange(
                    self.settings['azimuth_start'],
                    self.settings['azimuth_end'],
                    self.settings['azimuth_step']
                ),
                smoothing_bandwidth=self.settings['smoothing_bandwidth'],
                f_min=self.settings['f_min'],
                f_max=self.settings['f_max'],
                n_frequencies=self.settings['n_frequencies'],
                parallel=self.settings['parallel'],
                n_workers=self.settings.get('n_workers')
            )
            
            # Process with progress callback
            def progress_callback(progress, message):
                self.progress.emit(progress, message)
            
            result = processor.process(self.windows, progress_callback=progress_callback)
            
            self.finished.emit(result)
            
        except Exception as e:
            import traceback
            self.error.emit(f"{str(e)}\n\n{traceback.format_exc()}")


if HAS_PYQT5:
    
    class AzimuthalTab(QWidget):
        """
        Tab widget for azimuthal HVSR processing.
        
        Features:
        - Configure azimuth range and step
        - Process HVSR at multiple rotation angles
        - Display 3D surface, 2D contour, and HVSR curves
        - Export results and plots
        """
        
        def __init__(self, parent=None):
            super().__init__(parent)
            
            # State
            self.windows = None  # WindowCollection from processing
            self.result = None   # AzimuthalHVSRResult
            self.processing_thread = None
            self._data = None    # SeismicData reference
            
            # Setup UI
            self.init_ui()
        
        def init_ui(self):
            """Initialize the user interface."""
            outer_layout = QVBoxLayout(self)
            outer_layout.setContentsMargins(5, 5, 5, 5)
            outer_layout.setSpacing(5)
            
            # Collapsible data panel at top (shared info)
            self.data_panel = CollapsibleDataPanel(title="Loaded Data")
            # Starts collapsed by default
            outer_layout.addWidget(self.data_panel)
            
            # Main content area
            main_layout = QHBoxLayout()
            main_layout.setContentsMargins(0, 0, 0, 0)
            
            # Left panel - Settings
            settings_panel = self.create_settings_panel()
            
            # Right panel - Canvas and results
            results_panel = self.create_results_panel()
            
            # Splitter
            splitter = QSplitter(Qt.Horizontal)
            splitter.addWidget(settings_panel)
            splitter.addWidget(results_panel)
            splitter.setSizes([300, 700])
            
            main_layout.addWidget(splitter)
            outer_layout.addLayout(main_layout, 1)  # stretch factor 1
        
        def create_settings_panel(self) -> QWidget:
            """Create the settings panel."""
            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.setContentsMargins(5, 5, 5, 5)
            
            # Title
            title = QLabel("Azimuthal HVSR Analysis")
            title.setFont(QFont("Arial", 11, QFont.Bold))
            title.setAlignment(Qt.AlignCenter)
            layout.addWidget(title)
            
            # Info
            info_label = QLabel(
                "Compute HVSR at multiple rotation angles to analyze "
                "directional site response characteristics."
            )
            info_label.setWordWrap(True)
            info_label.setStyleSheet("QLabel { color: #666; padding: 5px; }")
            layout.addWidget(info_label)
            
            # === AZIMUTH SETTINGS ===
            azimuth_group = QGroupBox("Azimuth Range")
            az_layout = QVBoxLayout(azimuth_group)
            
            # Start azimuth
            start_layout = QHBoxLayout()
            start_layout.addWidget(QLabel("Start (deg):"))
            self.azimuth_start_spin = QSpinBox()
            self.azimuth_start_spin.setRange(0, 175)
            self.azimuth_start_spin.setValue(0)
            start_layout.addWidget(self.azimuth_start_spin)
            az_layout.addLayout(start_layout)
            
            # End azimuth
            end_layout = QHBoxLayout()
            end_layout.addWidget(QLabel("End (deg):"))
            self.azimuth_end_spin = QSpinBox()
            self.azimuth_end_spin.setRange(5, 180)
            self.azimuth_end_spin.setValue(180)
            end_layout.addWidget(self.azimuth_end_spin)
            az_layout.addLayout(end_layout)
            
            # Step
            step_layout = QHBoxLayout()
            step_layout.addWidget(QLabel("Step (deg):"))
            self.azimuth_step_spin = QSpinBox()
            self.azimuth_step_spin.setRange(1, 45)
            self.azimuth_step_spin.setValue(5)
            self.azimuth_step_spin.setToolTip("Smaller steps = finer resolution but slower processing")
            step_layout.addWidget(self.azimuth_step_spin)
            az_layout.addLayout(step_layout)
            
            # Info about number of azimuths
            self.n_azimuths_label = QLabel("36 azimuths will be computed")
            self.n_azimuths_label.setStyleSheet("QLabel { color: #888; font-size: 9px; }")
            az_layout.addWidget(self.n_azimuths_label)
            
            # Connect to update label
            self.azimuth_start_spin.valueChanged.connect(self._update_n_azimuths_label)
            self.azimuth_end_spin.valueChanged.connect(self._update_n_azimuths_label)
            self.azimuth_step_spin.valueChanged.connect(self._update_n_azimuths_label)
            
            layout.addWidget(azimuth_group)
            
            # === PROCESSING SETTINGS ===
            proc_group = QGroupBox("Processing Settings")
            proc_layout = QVBoxLayout(proc_group)
            
            # Smoothing bandwidth
            smooth_layout = QHBoxLayout()
            smooth_layout.addWidget(QLabel("Konno-Ohmachi (b):"))
            self.smoothing_spin = QDoubleSpinBox()
            self.smoothing_spin.setRange(10, 100)
            self.smoothing_spin.setValue(40)
            self.smoothing_spin.setSingleStep(5)
            smooth_layout.addWidget(self.smoothing_spin)
            proc_layout.addLayout(smooth_layout)
            
            # Frequency range
            fmin_layout = QHBoxLayout()
            fmin_layout.addWidget(QLabel("Min Freq (Hz):"))
            self.freq_min_spin = QDoubleSpinBox()
            self.freq_min_spin.setRange(0.1, 100.0)
            self.freq_min_spin.setValue(0.2)
            self.freq_min_spin.setDecimals(2)
            fmin_layout.addWidget(self.freq_min_spin)
            proc_layout.addLayout(fmin_layout)
            
            fmax_layout = QHBoxLayout()
            fmax_layout.addWidget(QLabel("Max Freq (Hz):"))
            self.freq_max_spin = QDoubleSpinBox()
            self.freq_max_spin.setRange(0.1, 100.0)
            self.freq_max_spin.setValue(20.0)
            self.freq_max_spin.setDecimals(1)
            fmax_layout.addWidget(self.freq_max_spin)
            proc_layout.addLayout(fmax_layout)
            
            # Number of frequency points
            nfreq_layout = QHBoxLayout()
            nfreq_layout.addWidget(QLabel("Freq Points:"))
            self.n_freq_spin = QSpinBox()
            self.n_freq_spin.setRange(50, 500)
            self.n_freq_spin.setValue(100)
            nfreq_layout.addWidget(self.n_freq_spin)
            proc_layout.addLayout(nfreq_layout)
            
            # Parallel processing
            self.parallel_check = QCheckBox("Enable parallel processing")
            self.parallel_check.setChecked(True)
            self.parallel_check.toggled.connect(self._on_parallel_toggled)
            proc_layout.addWidget(self.parallel_check)
            
            # Number of workers
            workers_layout = QHBoxLayout()
            workers_layout.addWidget(QLabel("CPU Cores:"))
            self.n_workers_spin = QSpinBox()
            from multiprocessing import cpu_count
            max_cores = cpu_count()
            self.n_workers_spin.setRange(1, max_cores)
            self.n_workers_spin.setValue(max(1, max_cores - 1))  # Leave one core free
            self.n_workers_spin.setToolTip(f"Number of CPU cores to use (max: {max_cores})")
            workers_layout.addWidget(self.n_workers_spin)
            proc_layout.addLayout(workers_layout)
            
            layout.addWidget(proc_group)
            
            # === PROCESS BUTTON ===
            self.process_btn = QPushButton("Process Azimuthal HVSR")
            self.process_btn.setEnabled(False)
            self.process_btn.clicked.connect(self.start_processing)
            self.process_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    font-weight: bold;
                    padding: 10px;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
                QPushButton:disabled {
                    background-color: #BDBDBD;
                }
            """)
            layout.addWidget(self.process_btn)
            
            # === PROGRESS ===
            self.progress_bar = QProgressBar()
            self.progress_bar.setVisible(False)
            self.progress_bar.setTextVisible(True)
            layout.addWidget(self.progress_bar)
            
            self.status_label = QLabel("Load data and run Processing first")
            self.status_label.setWordWrap(True)
            self.status_label.setStyleSheet("QLabel { color: #666; }")
            layout.addWidget(self.status_label)
            
            # === RESULTS INFO ===
            self.results_text = QTextEdit()
            self.results_text.setReadOnly(True)
            self.results_text.setMaximumHeight(150)
            self.results_text.setPlaceholderText("Results will appear here...")
            layout.addWidget(self.results_text)
            
            # === EXPORT GROUP ===
            export_group = QGroupBox("Export")
            export_layout = QVBoxLayout(export_group)
            
            # Export plot buttons
            btn_layout = QHBoxLayout()
            
            self.export_png_btn = QPushButton("PNG")
            self.export_png_btn.clicked.connect(lambda: self.export_plot("png"))
            self.export_png_btn.setEnabled(False)
            btn_layout.addWidget(self.export_png_btn)
            
            self.export_pdf_btn = QPushButton("PDF")
            self.export_pdf_btn.clicked.connect(lambda: self.export_plot("pdf"))
            self.export_pdf_btn.setEnabled(False)
            btn_layout.addWidget(self.export_pdf_btn)
            
            self.export_svg_btn = QPushButton("SVG")
            self.export_svg_btn.clicked.connect(lambda: self.export_plot("svg"))
            self.export_svg_btn.setEnabled(False)
            btn_layout.addWidget(self.export_svg_btn)
            
            export_layout.addLayout(btn_layout)
            
            # Export data
            self.export_data_btn = QPushButton("Export Data (CSV)")
            self.export_data_btn.clicked.connect(self.export_data)
            self.export_data_btn.setEnabled(False)
            export_layout.addWidget(self.export_data_btn)
            
            layout.addWidget(export_group)
            
            layout.addStretch()
            
            # Wrap in scroll area
            scroll = QScrollArea()
            scroll.setWidget(widget)
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll.setMaximumWidth(350)
            
            return scroll
        
        def create_results_panel(self) -> QWidget:
            """Create the results/canvas panel."""
            widget = QWidget()
            layout = QVBoxLayout(widget)
            layout.setContentsMargins(5, 5, 5, 5)
            
            # View selector
            view_layout = QHBoxLayout()
            view_layout.addWidget(QLabel("View:"))
            
            self.view_combo = QComboBox()
            self.view_combo.addItem("Summary (3D + 2D + Curves)", "summary")
            self.view_combo.addItem("3D Surface Only", "3d")
            self.view_combo.addItem("2D Contour Only", "2d")
            self.view_combo.currentIndexChanged.connect(self.update_plot)
            view_layout.addWidget(self.view_combo)
            
            view_layout.addStretch()
            
            # Colormap selector
            view_layout.addWidget(QLabel("Colormap:"))
            self.cmap_combo = QComboBox()
            self.cmap_combo.addItems(["plasma", "viridis", "inferno", "magma", "jet", "turbo"])
            self.cmap_combo.currentIndexChanged.connect(self.update_plot)
            view_layout.addWidget(self.cmap_combo)
            
            layout.addLayout(view_layout)
            
            # Matplotlib canvas
            self.figure = plt.figure(figsize=(10, 8), dpi=100)
            self.canvas = FigureCanvas(self.figure)
            self.toolbar = NavigationToolbar(self.canvas, self)
            
            layout.addWidget(self.toolbar)
            layout.addWidget(self.canvas, 1)
            
            # Show placeholder
            self._show_placeholder()
            
            return widget
        
        def _show_placeholder(self):
            """Show placeholder when no data."""
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, "No azimuthal analysis yet.\n\n"
                   "1. First run standard HVSR processing\n"
                   "2. Then run azimuthal analysis here",
                   ha='center', va='center', fontsize=12, color='gray',
                   transform=ax.transAxes)
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis('off')
            self.canvas.draw()
        
        def _update_n_azimuths_label(self):
            """Update the label showing number of azimuths."""
            start = self.azimuth_start_spin.value()
            end = self.azimuth_end_spin.value()
            step = self.azimuth_step_spin.value()
            n_azimuths = len(np.arange(start, end, step))
            self.n_azimuths_label.setText(f"{n_azimuths} azimuths will be computed")
        
        def _on_parallel_toggled(self, checked: bool):
            """Handle parallel processing checkbox toggle."""
            self.n_workers_spin.setEnabled(checked)
        
        def set_windows(self, windows, data=None):
            """
            Set window collection from standard processing.
            
            Args:
                windows: WindowCollection from HVSRProcessor
                data: SeismicData object (optional)
            """
            self.windows = windows
            if data:
                self._data = data
            
            if windows and windows.n_active > 0:
                self.process_btn.setEnabled(True)
                self.status_label.setText(f"Ready: {windows.n_active} windows available")
            else:
                self.process_btn.setEnabled(False)
                self.status_label.setText("No windows available. Run Processing first.")
        
        def set_data(self, data, file_path: str = None):
            """
            Set seismic data reference.
            
            Args:
                data: SeismicData object
                file_path: Path to the data file
            """
            self._data = data
            # Data panel is updated separately via update_from_data_load_tab
        
        def start_processing(self):
            """Start azimuthal processing."""
            if not self.windows:
                QMessageBox.warning(self, "No Data", "Please run standard HVSR processing first.")
                return
            
            # Gather settings
            settings = {
                'azimuth_start': self.azimuth_start_spin.value(),
                'azimuth_end': self.azimuth_end_spin.value(),
                'azimuth_step': self.azimuth_step_spin.value(),
                'smoothing_bandwidth': self.smoothing_spin.value(),
                'f_min': self.freq_min_spin.value(),
                'f_max': self.freq_max_spin.value(),
                'n_frequencies': self.n_freq_spin.value(),
                'parallel': self.parallel_check.isChecked(),
                'n_workers': self.n_workers_spin.value() if self.parallel_check.isChecked() else 1
            }
            
            # Start thread
            self.processing_thread = AzimuthalProcessingThread(self.windows, settings)
            self.processing_thread.progress.connect(self.on_progress)
            self.processing_thread.finished.connect(self.on_processing_finished)
            self.processing_thread.error.connect(self.on_processing_error)
            
            # Update UI
            self.process_btn.setEnabled(False)
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.status_label.setText("Processing...")
            
            self.processing_thread.start()
        
        def on_progress(self, value: int, message: str):
            """Handle progress updates."""
            self.progress_bar.setValue(value)
            self.status_label.setText(message)
        
        def on_processing_finished(self, result):
            """Handle processing completion."""
            self.result = result
            
            # Update UI
            self.progress_bar.setVisible(False)
            self.process_btn.setEnabled(True)
            self.status_label.setText("Processing complete!")
            
            # Enable export buttons
            self.export_png_btn.setEnabled(True)
            self.export_pdf_btn.setEnabled(True)
            self.export_svg_btn.setEnabled(True)
            self.export_data_btn.setEnabled(True)
            
            # Display results info
            peak_freq, peak_amp = result.mean_curve_peak()
            mean_fn = result.mean_fn_frequency()
            std_fn = result.std_fn_frequency()
            
            info = f"Azimuthal Analysis Results\n"
            info += f"========================\n"
            info += f"Azimuths: {result.n_azimuths} ({result.azimuths[0]:.0f} to {result.azimuths[-1]:.0f} deg)\n"
            info += f"Frequencies: {result.n_frequencies} points\n"
            info += f"\nOverall Peak:\n"
            info += f"  Frequency: {peak_freq:.3f} Hz\n"
            info += f"  Amplitude: {peak_amp:.2f}\n"
            info += f"\nFundamental Frequency (all azimuths):\n"
            info += f"  Mean: {mean_fn:.3f} Hz\n"
            info += f"  Std (log): {std_fn:.3f}\n"
            
            self.results_text.setText(info)
            
            # Update plot
            self.update_plot()
        
        def on_processing_error(self, error_msg: str):
            """Handle processing error."""
            self.progress_bar.setVisible(False)
            self.process_btn.setEnabled(True)
            self.status_label.setText("Error during processing")
            
            QMessageBox.critical(self, "Processing Error", error_msg)
        
        def update_plot(self):
            """Update the plot based on current view selection."""
            if not self.result:
                return
            
            from hvsr_pro.processing.azimuthal import (
                plot_azimuthal_contour_2d,
                plot_azimuthal_contour_3d,
                plot_azimuthal_summary
            )
            
            view = self.view_combo.currentData()
            cmap = self.cmap_combo.currentText()
            
            self.figure.clear()
            
            try:
                if view == "summary":
                    plot_azimuthal_summary(
                        self.result,
                        figsize=(10, 8),
                        dpi=100
                    )
                    # Copy to our figure
                    self.figure.clear()
                    fig, axes = plot_azimuthal_summary(self.result)
                    # Replace figure
                    self.figure = fig
                    self.canvas.figure = fig
                    
                elif view == "3d":
                    ax = self.figure.add_subplot(111, projection='3d')
                    plot_azimuthal_contour_3d(
                        self.result,
                        ax=ax,
                        cmap=cmap
                    )
                    
                elif view == "2d":
                    ax = self.figure.add_subplot(111)
                    plot_azimuthal_contour_2d(
                        self.result,
                        ax=ax,
                        cmap=cmap
                    )
                
                self.canvas.draw()
                
            except Exception as e:
                self.status_label.setText(f"Plot error: {str(e)}")
        
        def export_plot(self, format_type: str):
            """Export current plot."""
            if not self.result:
                return
            
            ext_map = {
                'png': ('PNG Image', '*.png'),
                'pdf': ('PDF Document', '*.pdf'),
                'svg': ('SVG Vector', '*.svg')
            }
            
            desc, pattern = ext_map.get(format_type, ('Image', '*.*'))
            
            filename, _ = QFileDialog.getSaveFileName(
                self,
                f"Export Azimuthal Plot as {desc}",
                f"azimuthal_hvsr.{format_type}",
                f"{desc} ({pattern});;All Files (*)"
            )
            
            if filename:
                try:
                    self.figure.savefig(filename, dpi=300, bbox_inches='tight')
                    QMessageBox.information(self, "Export Successful", 
                                          f"Plot saved to:\n{filename}")
                except Exception as e:
                    QMessageBox.critical(self, "Export Failed", str(e))
        
        def export_data(self):
            """Export azimuthal results to CSV."""
            if not self.result:
                return
            
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Export Azimuthal Data",
                "azimuthal_hvsr_data.csv",
                "CSV Files (*.csv);;All Files (*)"
            )
            
            if filename:
                try:
                    import csv
                    
                    with open(filename, 'w', newline='') as f:
                        writer = csv.writer(f)
                        
                        # Header
                        header = ['Frequency (Hz)'] + [f'Azimuth {az:.0f} deg' 
                                                      for az in self.result.azimuths]
                        writer.writerow(header)
                        
                        # Data rows
                        for i, freq in enumerate(self.result.frequencies):
                            row = [freq] + [self.result.mean_curves_per_azimuth[j, i] 
                                           for j in range(self.result.n_azimuths)]
                            writer.writerow(row)
                    
                    QMessageBox.information(self, "Export Successful",
                                          f"Data saved to:\n{filename}")
                except Exception as e:
                    QMessageBox.critical(self, "Export Failed", str(e))


else:
    # Dummy class when PyQt5 not available
    class AzimuthalTab:
        def __init__(self):
            raise ImportError("PyQt5 is required for GUI functionality")

