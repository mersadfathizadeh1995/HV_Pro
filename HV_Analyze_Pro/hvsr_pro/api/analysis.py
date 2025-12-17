"""
HVSR Pro API - Analysis Class
=============================

High-level interface for HVSR analysis.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
import json
import numpy as np


@dataclass
class ProcessingConfig:
    """Configuration for HVSR processing."""
    window_length: float = 30.0
    overlap: float = 0.5
    smoothing_bandwidth: float = 40.0
    freq_min: float = 0.2
    freq_max: float = 20.0
    n_frequencies: int = 100
    qc_mode: Optional[str] = 'balanced'
    apply_cox_fdwra: bool = False
    parallel: bool = False
    n_cores: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'window_length': self.window_length,
            'overlap': self.overlap,
            'smoothing_bandwidth': self.smoothing_bandwidth,
            'freq_min': self.freq_min,
            'freq_max': self.freq_max,
            'n_frequencies': self.n_frequencies,
            'qc_mode': self.qc_mode,
            'apply_cox_fdwra': self.apply_cox_fdwra,
            'parallel': self.parallel,
            'n_cores': self.n_cores
        }


class HVSRAnalysis:
    """
    High-level API for HVSR analysis.
    
    This class provides a simple interface for loading seismic data,
    configuring processing parameters, and computing HVSR curves.
    
    Example:
        >>> analysis = HVSRAnalysis()
        >>> analysis.load_data('data.mseed')
        >>> analysis.configure(window_length=30, qc_mode='balanced')
        >>> result = analysis.process()
        >>> print(f"Peak: {result.primary_peak.frequency} Hz")
        >>> analysis.save_results('results.json')
    """
    
    def __init__(self):
        """Initialize HVSR Analysis."""
        self._data = None
        self._windows = None
        self._result = None
        self._config = ProcessingConfig()
        self._time_range = None
        self._file_path = None
    
    @property
    def data(self):
        """Get loaded seismic data."""
        return self._data
    
    @property
    def windows(self):
        """Get window collection."""
        return self._windows
    
    @property
    def result(self):
        """Get HVSR result."""
        return self._result
    
    @property
    def config(self) -> ProcessingConfig:
        """Get processing configuration."""
        return self._config
    
    def load_data(self, 
                  file_path: Union[str, Path],
                  start_time: Optional[str] = None,
                  end_time: Optional[str] = None,
                  timezone_offset: int = 0) -> 'HVSRAnalysis':
        """
        Load seismic data from a file.
        
        Args:
            file_path: Path to the data file (MiniSEED, ASCII, CSV)
            start_time: Optional start time filter (ISO format)
            end_time: Optional end time filter (ISO format)
            timezone_offset: Timezone offset from UTC in hours
            
        Returns:
            self for method chaining
            
        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is not supported
        """
        from hvsr_pro.core import HVSRDataHandler
        
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        self._file_path = file_path
        
        # Load data
        handler = HVSRDataHandler()
        self._data = handler.load_data(str(file_path))
        
        # Apply time range filter if specified
        if start_time or end_time:
            self._time_range = {
                'enabled': True,
                'start': datetime.fromisoformat(start_time) if start_time else None,
                'end': datetime.fromisoformat(end_time) if end_time else None,
                'timezone_offset': timezone_offset
            }
            
            if start_time and end_time:
                self._data = handler.slice_by_time(
                    self._data,
                    self._time_range['start'],
                    self._time_range['end'],
                    timezone_offset
                )
        
        return self
    
    def configure(self, **kwargs) -> 'HVSRAnalysis':
        """
        Configure processing parameters.
        
        Args:
            window_length: Window length in seconds (default: 30)
            overlap: Window overlap as fraction 0-1 (default: 0.5)
            smoothing_bandwidth: Konno-Ohmachi smoothing b (default: 40)
            freq_min: Minimum frequency in Hz (default: 0.2)
            freq_max: Maximum frequency in Hz (default: 20)
            n_frequencies: Number of frequency points (default: 100)
            qc_mode: Quality control mode (default: 'balanced')
                Options: 'conservative', 'balanced', 'aggressive', 'sesame', 'publication', None
            apply_cox_fdwra: Apply Cox FDWRA rejection (default: False)
            parallel: Enable parallel processing (default: False)
            n_cores: Number of CPU cores for parallel processing
            
        Returns:
            self for method chaining
        """
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
            else:
                raise ValueError(f"Unknown configuration parameter: {key}")
        
        return self
    
    def process(self) -> 'HVSRResult':
        """
        Process the loaded data to compute HVSR.
        
        Returns:
            HVSRResult object containing computed HVSR curves and statistics
            
        Raises:
            ValueError: If no data is loaded
        """
        if self._data is None:
            raise ValueError("No data loaded. Call load_data() first.")
        
        from hvsr_pro.processing import WindowManager, RejectionEngine, HVSRProcessor
        
        # Create windows
        manager = WindowManager(
            window_length=self._config.window_length,
            overlap=self._config.overlap
        )
        self._windows = manager.create_windows(self._data, calculate_quality=True)
        
        # Apply QC if enabled
        if self._config.qc_mode:
            engine = RejectionEngine()
            engine.create_default_pipeline(mode=self._config.qc_mode)
            engine.evaluate(self._windows, auto_apply=True)
        
        # Compute HVSR
        processor = HVSRProcessor(
            smoothing_bandwidth=self._config.smoothing_bandwidth,
            f_min=self._config.freq_min,
            f_max=self._config.freq_max,
            n_frequencies=self._config.n_frequencies,
            parallel=self._config.parallel
        )
        self._result = processor.process(
            self._windows,
            detect_peaks_flag=True,
            save_window_spectra=True
        )
        
        # Apply Cox FDWRA if enabled
        if self._config.apply_cox_fdwra and self._config.qc_mode:
            engine = RejectionEngine()
            fdwra_result = engine.evaluate_fdwra(
                self._windows,
                self._result,
                n=2.0,
                distribution_fn="lognormal",
                distribution_mc="lognormal",
                search_range_hz=(self._config.freq_min, self._config.freq_max),
                auto_apply=True
            )
            
            # Recompute HVSR if windows were rejected
            if fdwra_result['n_rejected'] > 0 and self._windows.n_active > 0:
                self._result = processor.process(
                    self._windows,
                    detect_peaks_flag=True,
                    save_window_spectra=True
                )
        
        return self._result
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the analysis.
        
        Returns:
            Dictionary containing analysis summary
        """
        summary = {
            'file': str(self._file_path) if self._file_path else None,
            'config': self._config.to_dict()
        }
        
        if self._data:
            summary['data'] = {
                'duration_seconds': self._data.duration,
                'sampling_rate': self._data.east.sampling_rate,
                'n_samples': len(self._data.east.data),
                'start_time': str(self._data.start_time) if self._data.start_time else None
            }
        
        if self._windows:
            summary['windows'] = {
                'total': self._windows.n_windows,
                'active': self._windows.n_active,
                'acceptance_rate': self._windows.acceptance_rate
            }
        
        if self._result:
            summary['result'] = {
                'total_windows': self._result.total_windows,
                'valid_windows': self._result.valid_windows,
                'frequencies': {
                    'min': float(self._result.frequencies[0]),
                    'max': float(self._result.frequencies[-1]),
                    'n_points': len(self._result.frequencies)
                }
            }
            if self._result.primary_peak:
                summary['result']['primary_peak'] = {
                    'frequency': self._result.primary_peak.frequency,
                    'amplitude': self._result.primary_peak.amplitude
                }
        
        return summary
    
    def save_results(self, 
                     output_path: Union[str, Path],
                     format: str = 'json') -> None:
        """
        Save processing results to a file.
        
        Args:
            output_path: Output file path
            format: Output format ('json', 'csv', 'mat')
        """
        if self._result is None:
            raise ValueError("No results to save. Call process() first.")
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if format == 'json':
            self._save_json(output_path)
        elif format == 'csv':
            self._save_csv(output_path)
        elif format == 'mat':
            self._save_mat(output_path)
        else:
            raise ValueError(f"Unknown format: {format}")
    
    def _save_json(self, output_path: Path) -> None:
        """Save results as JSON."""
        data = {
            'config': self._config.to_dict(),
            'summary': self.get_summary(),
            'frequencies': self._result.frequencies.tolist(),
            'mean_hvsr': self._result.mean_hvsr.tolist(),
            'median_hvsr': self._result.median_hvsr.tolist(),
            'std_hvsr': self._result.std_hvsr.tolist(),
            'percentile_16': self._result.percentile_16.tolist(),
            'percentile_84': self._result.percentile_84.tolist(),
            'peaks': [
                {'frequency': p.frequency, 'amplitude': p.amplitude}
                for p in self._result.peaks
            ] if self._result.peaks else []
        }
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _save_csv(self, output_path: Path) -> None:
        """Save results as CSV."""
        import csv
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['frequency', 'mean_hvsr', 'median_hvsr', 'std_hvsr', 
                           'percentile_16', 'percentile_84'])
            for i, freq in enumerate(self._result.frequencies):
                writer.writerow([
                    freq,
                    self._result.mean_hvsr[i],
                    self._result.median_hvsr[i],
                    self._result.std_hvsr[i],
                    self._result.percentile_16[i],
                    self._result.percentile_84[i]
                ])
    
    def _save_mat(self, output_path: Path) -> None:
        """Save results as MATLAB .mat file."""
        try:
            from scipy.io import savemat
        except ImportError:
            raise ImportError("scipy is required for MAT export. Install with: pip install scipy")
        
        mat_data = {
            'frequency': self._result.frequencies,
            'mean_hvsr': self._result.mean_hvsr,
            'median_hvsr': self._result.median_hvsr,
            'std_hvsr': self._result.std_hvsr,
            'percentile_16': self._result.percentile_16,
            'percentile_84': self._result.percentile_84,
            'total_windows': self._result.total_windows,
            'valid_windows': self._result.valid_windows
        }
        
        if self._result.primary_peak:
            mat_data['peak_frequency'] = self._result.primary_peak.frequency
            mat_data['peak_amplitude'] = self._result.primary_peak.amplitude
        
        savemat(str(output_path), mat_data)
    
    def load_results(self, file_path: Union[str, Path]) -> 'HVSRAnalysis':
        """
        Load previously saved results from a JSON file.
        
        Args:
            file_path: Path to the results JSON file
            
        Returns:
            self for method chaining
        """
        from hvsr_pro.processing.hvsr import HVSRResult, Peak
        
        file_path = Path(file_path)
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Reconstruct config
        if 'config' in data:
            for key, value in data['config'].items():
                if hasattr(self._config, key):
                    setattr(self._config, key, value)
        
        # Reconstruct result
        peaks = [
            Peak(frequency=p['frequency'], amplitude=p['amplitude'])
            for p in data.get('peaks', [])
        ]
        
        self._result = HVSRResult(
            frequencies=np.array(data['frequencies']),
            mean_hvsr=np.array(data['mean_hvsr']),
            median_hvsr=np.array(data['median_hvsr']),
            std_hvsr=np.array(data['std_hvsr']),
            percentile_16=np.array(data['percentile_16']),
            percentile_84=np.array(data['percentile_84']),
            window_spectra=[],
            peaks=peaks,
            total_windows=data.get('summary', {}).get('result', {}).get('total_windows', 0),
            valid_windows=data.get('summary', {}).get('result', {}).get('valid_windows', 0),
            metadata={}
        )
        
        return self
    
    def save_plots(self, 
                   output_dir: Union[str, Path],
                   plot_types: Optional[List[str]] = None,
                   dpi: int = 150) -> List[Path]:
        """
        Save visualization plots.
        
        Args:
            output_dir: Directory to save plots
            plot_types: List of plot types to save. Options:
                'hvsr', 'windows', 'quality', 'statistics', 'dashboard'
                Default: ['hvsr', 'quality']
            dpi: Resolution of saved plots
            
        Returns:
            List of saved file paths
        """
        if self._result is None:
            raise ValueError("No results to plot. Call process() first.")
        
        from hvsr_pro.visualization import HVSRPlotter
        import matplotlib.pyplot as plt
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if plot_types is None:
            plot_types = ['hvsr', 'quality']
        
        plotter = HVSRPlotter()
        saved_files = []
        
        for plot_type in plot_types:
            try:
                if plot_type == 'hvsr':
                    fig = plotter.plot_result(self._result, show_peaks=True)
                elif plot_type == 'windows' and self._result.window_spectra:
                    fig = plotter.plot_with_windows(self._result)
                elif plot_type == 'quality' and self._windows:
                    fig = plotter.plot_quality_metrics(self._windows)
                elif plot_type == 'statistics':
                    fig = plotter.plot_statistics(self._result)
                elif plot_type == 'dashboard' and self._windows:
                    fig = plotter.plot_dashboard(self._result, self._windows)
                else:
                    continue
                
                filepath = output_dir / f"{plot_type}.png"
                fig.savefig(filepath, dpi=dpi, bbox_inches='tight')
                plt.close(fig)
                saved_files.append(filepath)
                
            except Exception:
                continue
        
        return saved_files
    
    def save_plot(self,
                  output_path: Union[str, Path],
                  plot_type: str = 'hvsr',
                  dpi: int = 150) -> None:
        """
        Save a single plot.
        
        Args:
            output_path: Path to save the plot
            plot_type: Type of plot to save
            dpi: Resolution of saved plot
        """
        if self._result is None:
            raise ValueError("No results to plot. Call process() first.")
        
        from hvsr_pro.visualization import HVSRPlotter
        import matplotlib.pyplot as plt
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        plotter = HVSRPlotter()
        
        if plot_type == 'hvsr':
            fig = plotter.plot_result(self._result, show_peaks=True)
        elif plot_type == 'windows' and self._result.window_spectra:
            fig = plotter.plot_with_windows(self._result)
        elif plot_type == 'quality' and self._windows:
            fig = plotter.plot_quality_metrics(self._windows)
        elif plot_type == 'statistics':
            fig = plotter.plot_statistics(self._result)
        elif plot_type == 'comparison' and self._windows:
            from hvsr_pro.visualization.comparison_plot import plot_raw_vs_adjusted_from_result
            fig = plot_raw_vs_adjusted_from_result(self._result, self._windows)
        else:
            raise ValueError(f"Unknown or unavailable plot type: {plot_type}")
        
        fig.savefig(output_path, dpi=dpi, bbox_inches='tight')
        plt.close(fig)

