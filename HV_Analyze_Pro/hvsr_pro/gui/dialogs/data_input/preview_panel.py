"""
Preview Panel
=============

Visual preview panel for seismic data with matplotlib.
Extracted from data_input_dialog.py.
"""

from pathlib import Path
from typing import Optional, Dict, List
import numpy as np

try:
    from PyQt5.QtWidgets import (
        QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
        QPushButton, QLabel, QRadioButton, QButtonGroup
    )
    from PyQt5.QtCore import pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False

try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


if HAS_PYQT5 and HAS_MATPLOTLIB:
    class PreviewPanel(QWidget):
        """
        Visual preview panel for seismic data.
        
        Features:
        - Component selection (All, E, N, Z)
        - Automatic data loading from files
        - Waveform visualization
        - Statistics display
        
        Signals:
            data_loaded: Emitted when preview data is loaded (dict)
            error_occurred: Emitted on error (str)
        """
        
        data_loaded = pyqtSignal(dict)
        error_occurred = pyqtSignal(str)
        
        def __init__(self, parent=None):
            super().__init__(parent)
            self.preview_data = None
            self._init_ui()
        
        def _init_ui(self):
            """Initialize the user interface."""
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            
            # Main group
            self.group_box = QGroupBox("Visual Preview")
            group_layout = QVBoxLayout(self.group_box)
            
            # View mode selection
            mode_layout = QHBoxLayout()
            self.button_group = QButtonGroup(self)
            
            self.radio_all = QRadioButton("All Components")
            self.radio_all.setChecked(True)
            self.radio_all.toggled.connect(lambda c: c and self._update_plot())
            self.button_group.addButton(self.radio_all)
            mode_layout.addWidget(self.radio_all)
            
            self.radio_e = QRadioButton("E")
            self.radio_e.toggled.connect(lambda c: c and self._update_plot())
            self.button_group.addButton(self.radio_e)
            mode_layout.addWidget(self.radio_e)
            
            self.radio_n = QRadioButton("N")
            self.radio_n.toggled.connect(lambda c: c and self._update_plot())
            self.button_group.addButton(self.radio_n)
            mode_layout.addWidget(self.radio_n)
            
            self.radio_z = QRadioButton("Z")
            self.radio_z.toggled.connect(lambda c: c and self._update_plot())
            self.button_group.addButton(self.radio_z)
            mode_layout.addWidget(self.radio_z)
            
            mode_layout.addStretch()
            
            # Refresh button
            self.refresh_btn = QPushButton("Refresh")
            self.refresh_btn.setMaximumWidth(80)
            self.refresh_btn.clicked.connect(self._on_refresh_clicked)
            mode_layout.addWidget(self.refresh_btn)
            
            group_layout.addLayout(mode_layout)
            
            # Matplotlib canvas
            self.figure = Figure(figsize=(5, 2.5), dpi=80)
            self.canvas = FigureCanvas(self.figure)
            self.canvas.setMinimumHeight(150)
            self.canvas.setMaximumHeight(250)
            group_layout.addWidget(self.canvas)
            
            # Status label
            self.status_label = QLabel("Load a file to see preview")
            self.status_label.setStyleSheet("color: gray; font-size: 9pt;")
            group_layout.addWidget(self.status_label)
            
            layout.addWidget(self.group_box)
            
            # Show empty state
            self._show_empty()
        
        def _on_refresh_clicked(self):
            """Handle refresh button click."""
            self._update_plot()
        
        def load_from_file(self, file_path: str):
            """
            Load preview data from a file.
            
            Args:
                file_path: Path to the file
            """
            self._set_status("Loading...", "orange")
            
            try:
                path = Path(file_path)
                
                if path.suffix.lower() in ['.mseed', '.miniseed']:
                    self._load_miniseed(file_path)
                elif path.suffix.lower() in ['.txt', '.csv', '.dat', '.asc']:
                    self._load_text(file_path)
                else:
                    self._show_empty()
                    self._set_status(f"Unsupported format: {path.suffix}", "orange")
                    
            except Exception as e:
                self._show_error(str(e))
                self.error_occurred.emit(str(e))
        
        def load_from_files(self, file_paths: List[str]):
            """
            Load preview data from multiple files.
            
            Args:
                file_paths: List of file paths
            """
            if not file_paths:
                self._show_empty()
                return
            
            self._set_status(f"Loading {len(file_paths)} files...", "orange")
            
            try:
                from obspy import read, Stream
                
                combined_stream = Stream()
                for fp in file_paths[:10]:  # Limit for speed
                    try:
                        stream = read(str(fp))
                        combined_stream += stream
                    except Exception:
                        continue
                
                if len(combined_stream) == 0:
                    self._show_empty()
                    return
                
                combined_stream.merge(method=1, fill_value='interpolate')
                self._extract_stream_data(combined_stream)
                
            except ImportError:
                self._show_error("ObsPy not installed")
            except Exception as e:
                self._show_error(str(e))
        
        def _load_miniseed(self, file_path: str):
            """Load from MiniSEED file."""
            try:
                from obspy import read
                
                stream = read(file_path)
                if len(stream) == 0:
                    self._show_empty()
                    return
                
                self._extract_stream_data(stream)
                
            except ImportError:
                self._show_error("ObsPy not installed")
            except Exception as e:
                self._show_error(str(e))
        
        def _extract_stream_data(self, stream):
            """Extract component data from ObsPy stream."""
            preview_data = {
                'E': None, 'N': None, 'Z': None,
                'sampling_rate': stream[0].stats.sampling_rate
            }
            
            for trace in stream:
                channel = trace.stats.channel.upper()
                
                if channel.endswith('E') or channel.endswith('1'):
                    preview_data['E'] = trace.data
                elif channel.endswith('N') or channel.endswith('2'):
                    preview_data['N'] = trace.data
                elif channel.endswith('Z') or channel.endswith('3'):
                    preview_data['Z'] = trace.data
            
            self.preview_data = preview_data
            self._update_plot()
            self.data_loaded.emit(preview_data)
        
        def _load_text(self, file_path: str):
            """Load from text/CSV file."""
            try:
                encodings = ['utf-8', 'latin-1', 'cp1252']
                lines = None
                
                for encoding in encodings:
                    try:
                        with open(file_path, 'r', encoding=encoding) as f:
                            lines = f.readlines()
                        break
                    except:
                        continue
                
                if not lines:
                    self._show_error("Could not read file")
                    return
                
                # Parse numeric data
                data_rows = []
                for line in lines:
                    stripped = line.strip()
                    if not stripped or stripped.startswith('#'):
                        continue
                    
                    parts = stripped.split()
                    try:
                        row = [float(p) for p in parts]
                        if len(row) >= 3:
                            data_rows.append(row)
                    except ValueError:
                        continue
                
                if len(data_rows) < 10:
                    self._show_error("Not enough numeric data")
                    return
                
                data = np.array(data_rows)
                
                preview_data = {
                    'E': data[:, 0] if data.shape[1] > 0 else None,
                    'N': data[:, 1] if data.shape[1] > 1 else None,
                    'Z': data[:, 2] if data.shape[1] > 2 else None,
                    'sampling_rate': 100.0  # Assume default
                }
                
                self.preview_data = preview_data
                self._update_plot()
                self.data_loaded.emit(preview_data)
                
            except Exception as e:
                self._show_error(str(e))
        
        def _update_plot(self):
            """Update the plot based on current data and view mode."""
            if self.preview_data is None:
                self._show_empty()
                return
            
            try:
                self.figure.clear()
                
                if self.radio_all.isChecked():
                    self._plot_all_components()
                elif self.radio_e.isChecked():
                    self._plot_single('E')
                elif self.radio_n.isChecked():
                    self._plot_single('N')
                elif self.radio_z.isChecked():
                    self._plot_single('Z')
                
                self.figure.tight_layout()
                self.canvas.draw()
                
            except Exception as e:
                self._show_error(str(e))
        
        def _plot_all_components(self):
            """Plot all three components."""
            data = self.preview_data
            colors = {'E': '#d62728', 'N': '#2ca02c', 'Z': '#1f77b4'}
            labels = {'E': 'East (E)', 'N': 'North (N)', 'Z': 'Vertical (Z)'}
            components = ['E', 'N', 'Z']
            
            fs = data.get('sampling_rate', 100)
            
            # Find normalization factor
            norm_factor = 1
            for comp in components:
                if comp in data and data[comp] is not None:
                    c_max = np.max(np.abs(data[comp]))
                    if c_max > norm_factor:
                        norm_factor = c_max
            
            axes = []
            for i, comp in enumerate(components):
                if i == 0:
                    ax = self.figure.add_subplot(3, 1, i + 1)
                else:
                    ax = self.figure.add_subplot(3, 1, i + 1, sharex=axes[0])
                axes.append(ax)
                
                if comp in data and data[comp] is not None:
                    comp_data = data[comp]
                    n_samples = len(comp_data)
                    time_vec = np.arange(n_samples) / fs
                    
                    comp_data_norm = comp_data / norm_factor
                    ax.plot(time_vec, comp_data_norm, color=colors[comp], 
                           linewidth=0.5, alpha=0.8)
                    ax.set_ylabel(labels[comp], fontsize=8)
                    ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
                    ax.axhline(0, color='k', linewidth=0.3, alpha=0.5)
                    
                    if i == 0:
                        duration = n_samples / fs
                        ax.set_title(f'Preview | {duration:.1f}s | {fs:.0f} Hz', 
                                   fontsize=9, pad=5)
                    
                    if i == 2:
                        ax.set_xlabel('Time (s)', fontsize=8)
                    else:
                        ax.tick_params(labelbottom=False)
                else:
                    ax.text(0.5, 0.5, f'{comp} not available',
                           ha='center', va='center', fontsize=9, color='gray',
                           transform=ax.transAxes)
                    ax.set_xticks([])
                    ax.set_yticks([])
            
            # Update status
            n_samples = len(data.get('E', data.get('N', data.get('Z', []))))
            duration = n_samples / fs if fs > 0 else 0
            self._set_status(f"{n_samples:,} samples | {duration:.1f}s | {fs:.0f} Hz", "green")
        
        def _plot_single(self, component: str):
            """Plot single component with detail."""
            data = self.preview_data
            colors = {'E': '#d62728', 'N': '#2ca02c', 'Z': '#1f77b4'}
            labels = {'E': 'East (E)', 'N': 'North (N)', 'Z': 'Vertical (Z)'}
            
            ax = self.figure.add_subplot(111)
            
            if component in data and data[component] is not None:
                comp_data = data[component]
                fs = data.get('sampling_rate', 100)
                n_samples = len(comp_data)
                time_vec = np.arange(n_samples) / fs
                
                ax.plot(time_vec, comp_data, color=colors[component], 
                       linewidth=0.5, alpha=0.9)
                ax.set_xlabel('Time (s)', fontsize=9)
                ax.set_ylabel('Amplitude', fontsize=9)
                ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
                
                # Add statistics
                stats = f'Min: {np.min(comp_data):.2e}\n'
                stats += f'Max: {np.max(comp_data):.2e}\n'
                stats += f'Mean: {np.mean(comp_data):.2e}\n'
                stats += f'Std: {np.std(comp_data):.2e}'
                ax.text(0.02, 0.98, stats, transform=ax.transAxes,
                       verticalalignment='top', fontsize=7,
                       bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
                
                duration = n_samples / fs
                ax.set_title(f'{labels[component]} | {n_samples:,} samples | {duration:.1f}s',
                           fontsize=9, pad=5)
                
                self._set_status(f"{labels[component]}: {n_samples:,} samples", "green")
            else:
                ax.text(0.5, 0.5, f'{component} not available',
                       ha='center', va='center', fontsize=12, color='gray',
                       transform=ax.transAxes)
                ax.set_xticks([])
                ax.set_yticks([])
        
        def _show_empty(self):
            """Show empty state."""
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, 'No data to preview\n\nSelect a file to see waveform',
                   ha='center', va='center', fontsize=12, color='gray',
                   transform=ax.transAxes)
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_frame_on(False)
            self.canvas.draw()
        
        def _show_error(self, error_msg: str):
            """Show error state."""
            self.figure.clear()
            ax = self.figure.add_subplot(111)
            ax.text(0.5, 0.5, f'Error:\n{error_msg}',
                   ha='center', va='center', fontsize=10, color='red',
                   transform=ax.transAxes)
            ax.set_xticks([])
            ax.set_yticks([])
            ax.set_frame_on(False)
            self.canvas.draw()
            self._set_status(f"Error: {error_msg[:50]}...", "red")
        
        def _set_status(self, text: str, color: str = "gray"):
            """Update status label."""
            self.status_label.setText(text)
            self.status_label.setStyleSheet(f"color: {color}; font-size: 9pt;")
        
        def clear(self):
            """Clear preview data and display."""
            self.preview_data = None
            self._show_empty()
            self._set_status("Load a file to see preview", "gray")
        
        def set_data(self, data: Dict):
            """
            Set preview data directly.
            
            Args:
                data: Dict with 'E', 'N', 'Z' arrays and 'sampling_rate'
            """
            self.preview_data = data
            self._update_plot()

else:
    class PreviewPanel:
        """Dummy class when dependencies not available."""
        def __init__(self, *args, **kwargs):
            pass
