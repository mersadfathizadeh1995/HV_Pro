"""
HVSR Pro Export Workers
=======================

Background threads for data and plot export operations.
"""

from pathlib import Path
from typing import Dict, Optional, Callable
from datetime import datetime
import numpy as np

try:
    from PyQt5.QtCore import QThread, pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False
    class QThread:
        pass
    class pyqtSignal:
        def __init__(self, *args): pass


class DataExportWorker(QThread):
    """Worker thread for data export operations."""

    progress = pyqtSignal(int, str)  # progress value, status message
    finished = pyqtSignal(bool, str)  # success, message
    error = pyqtSignal(str)  # error message

    def __init__(self, export_func: Callable, files_data: Dict, output_dir: str, options: Dict):
        super().__init__()
        self.export_func = export_func
        self.files_data = files_data
        self.output_dir = output_dir
        self.options = options

    def run(self):
        """Run export operation."""
        try:
            # Check if combined mode is enabled
            if self.options.get('combined', False):
                self._export_combined()
            else:
                self._export_individual()
        except Exception as e:
            import traceback
            self.error.emit(f"{str(e)}\n{traceback.format_exc()}")
            self.finished.emit(False, f"Export failed: {str(e)}")
    
    def _export_individual(self):
        """Export each file individually."""
        total_files = len(self.files_data)
        for i, (file_path, data) in enumerate(self.files_data.items()):
            filename = Path(file_path).stem
            self.progress.emit(
                int((i / total_files) * 100),
                f"Exporting {filename}..."
            )

            # Call export function
            self.export_func(data, self.output_dir, filename, self.options)

        self.progress.emit(100, "Export complete!")
        self.finished.emit(True, f"Successfully exported {total_files} file(s)")
    
    def _export_combined(self):
        """Merge all files and export as single combined file."""
        self.progress.emit(10, "Merging files...")
        
        # Collect all data arrays
        e_arrays = []
        n_arrays = []
        z_arrays = []
        sampling_rate = None
        first_start_time = None
        
        for file_path, data in self.files_data.items():
            # Extract component data
            e_data = data.east.data if hasattr(data.east, 'data') else data.east
            n_data = data.north.data if hasattr(data.north, 'data') else data.north
            z_data = data.vertical.data if hasattr(data.vertical, 'data') else data.vertical
            
            e_arrays.append(e_data)
            n_arrays.append(n_data)
            z_arrays.append(z_data)
            
            # Get sampling rate
            if sampling_rate is None:
                sampling_rate = data.east.sampling_rate if hasattr(data.east, 'sampling_rate') else data.sampling_rate
            
            # Get start time from first file
            if first_start_time is None:
                if hasattr(data, 'start_time') and data.start_time:
                    first_start_time = data.start_time
        
        self.progress.emit(40, "Concatenating data...")
        
        # Concatenate all arrays
        combined_e = np.concatenate(e_arrays)
        combined_n = np.concatenate(n_arrays)
        combined_z = np.concatenate(z_arrays)
        
        self.progress.emit(60, "Creating merged data object...")
        
        # Create a combined data object
        try:
            from hvsr_pro.core.data_structures import SeismicData, ComponentData
            
            east_comp = ComponentData(
                name='E',
                data=combined_e,
                sampling_rate=sampling_rate,
                start_time=first_start_time
            )
            north_comp = ComponentData(
                name='N',
                data=combined_n,
                sampling_rate=sampling_rate,
                start_time=first_start_time
            )
            vertical_comp = ComponentData(
                name='Z',
                data=combined_z,
                sampling_rate=sampling_rate,
                start_time=first_start_time
            )
            
            combined_data = SeismicData(
                east=east_comp,
                north=north_comp,
                vertical=vertical_comp,
                station_name='COMBINED',
                metadata={'merged_from': len(self.files_data), 'merge_time': datetime.now().isoformat()}
            )
        except Exception:
            # Fallback: create simple object
            class CombinedData:
                def __init__(self, e, n, z, fs, start_time, n_files):
                    self.east = type('Component', (), {'data': e, 'sampling_rate': fs})()
                    self.north = type('Component', (), {'data': n, 'sampling_rate': fs})()
                    self.vertical = type('Component', (), {'data': z, 'sampling_rate': fs})()
                    self.sampling_rate = fs
                    self.start_time = start_time
                    self.duration = len(e) / fs if fs else len(e)
                    self.metadata = {'merged_from': n_files}
            
            combined_data = CombinedData(combined_e, combined_n, combined_z, 
                                          sampling_rate, first_start_time, len(self.files_data))
        
        self.progress.emit(80, "Exporting combined file...")
        
        # Generate a combined filename based on first and last files
        file_names = list(self.files_data.keys())
        if len(file_names) == 1:
            combined_filename = Path(file_names[0]).stem + "_combined"
        else:
            first_name = Path(file_names[0]).stem
            last_name = Path(file_names[-1]).stem
            combined_filename = f"{first_name}_to_{last_name}_merged"
        
        # Call export function with combined data
        self.export_func(combined_data, self.output_dir, combined_filename, self.options)
        
        self.progress.emit(100, "Export complete!")
        self.finished.emit(True, f"Successfully merged and exported {len(self.files_data)} file(s) as single combined file")


class PlotExportWorker(QThread):
    """Background worker for generating and exporting plots."""
    
    progress = pyqtSignal(int, str)  # progress, message
    finished = pyqtSignal(list)  # list of saved files
    error = pyqtSignal(str)
    
    def __init__(self, result, windows, data, output_dir, plot_types, dpi=150):
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
            import traceback
            self.error.emit(f"Export error: {str(e)}\n\n{traceback.format_exc()}")


# Backward compatibility alias
ExportWorker = PlotExportWorker

