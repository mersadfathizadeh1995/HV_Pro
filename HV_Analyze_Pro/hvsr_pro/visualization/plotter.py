"""
HVSR Plotter - Main Visualization Coordinator
==============================================

High-level interface for all HVSR visualizations.
"""

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
import numpy as np

from hvsr_pro.processing.hvsr import HVSRResult
from hvsr_pro.processing.windows import WindowCollection, Window
from hvsr_pro.visualization.hvsr_plots import (
    plot_hvsr_curve,
    plot_hvsr_comparison,
    plot_hvsr_components,
    plot_peak_analysis,
    plot_hvsr_statistics,
    save_hvsr_plot
)
from hvsr_pro.visualization.window_plots import (
    plot_window_time_series,
    plot_window_spectrogram,
    plot_window_collection_overview,
    plot_quality_metrics_grid,
    plot_window_comparison,
    plot_rejection_timeline
)


class HVSRPlotter:
    """
    Main plotter class for HVSR visualizations.
    
    Provides high-level interface for creating HVSR plots, window
    visualizations, quality metrics, and complete analysis reports.
    
    Example:
        >>> plotter = HVSRPlotter()
        >>> plotter.plot_result(hvsr_result)
        >>> plotter.plot_windows(window_collection)
        >>> plotter.save_report(hvsr_result, windows, 'output/')
    """
    
    def __init__(self, style: str = 'seaborn-v0_8-darkgrid'):
        """
        Initialize plotter.
        
        Args:
            style: Matplotlib style to use
        """
        try:
            plt.style.use(style)
        except:
            # Fallback to default if style not available
            pass
        
        self.style = style
        self.default_dpi = 150
    
    def plot_result(self,
                   result: HVSRResult,
                   show_uncertainty: bool = True,
                   show_peaks: bool = True,
                   show_median: bool = True,
                   show_mean: bool = False,
                   title: Optional[str] = None,
                   save_path: Optional[str] = None) -> Figure:
        """
        Plot HVSR result with standard formatting.
        
        Args:
            result: HVSRResult object
            show_uncertainty: Show uncertainty band
            show_peaks: Mark peaks
            show_median: Show median curve (primary)
            show_mean: Show mean curve (secondary)
            title: Custom title
            save_path: Path to save figure
            
        Returns:
            Matplotlib figure
        """
        fig, ax = plt.subplots(figsize=(12, 7))
        
        plot_hvsr_curve(result, ax=ax,
                       show_uncertainty=show_uncertainty,
                       show_peaks=show_peaks,
                       show_median=show_median,
                       show_mean=show_mean,
                       title=title)
        
        plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=self.default_dpi, bbox_inches='tight')
        
        return fig
    
    def plot_windows(self,
                    windows: WindowCollection,
                    max_windows: int = 50,
                    save_path: Optional[str] = None) -> Figure:
        """
        Plot window collection overview.
        
        Args:
            windows: WindowCollection object
            max_windows: Maximum windows to show
            save_path: Path to save figure
            
        Returns:
            Matplotlib figure
        """
        fig = plot_window_collection_overview(windows, max_windows=max_windows)
        
        if save_path:
            fig.savefig(save_path, dpi=self.default_dpi, bbox_inches='tight')
        
        return fig
    
    def plot_statistics(self,
                       result: HVSRResult,
                       save_path: Optional[str] = None) -> Figure:
        """
        Plot comprehensive statistical analysis.
        
        Args:
            result: HVSRResult object
            save_path: Path to save figure
            
        Returns:
            Matplotlib figure
        """
        fig = plot_hvsr_statistics(result)
        
        if save_path:
            fig.savefig(save_path, dpi=self.default_dpi, bbox_inches='tight')
        
        return fig
    
    def plot_quality_metrics(self,
                            windows: WindowCollection,
                            metric_names: Optional[List[str]] = None,
                            max_windows: int = 100,
                            save_path: Optional[str] = None) -> Figure:
        """
        Plot quality metrics grid.
        
        Args:
            windows: WindowCollection object
            metric_names: Metrics to plot
            max_windows: Maximum windows
            save_path: Path to save figure
            
        Returns:
            Matplotlib figure
        """
        fig = plot_quality_metrics_grid(windows,
                                       metric_names=metric_names,
                                       max_windows=max_windows)
        
        if save_path:
            fig.savefig(save_path, dpi=self.default_dpi, bbox_inches='tight')
        
        return fig
    
    def plot_window(self,
                   window: Window,
                   show_spectrogram: bool = False,
                   component: str = 'vertical',
                   save_path: Optional[str] = None) -> Figure:
        """
        Plot detailed view of single window.
        
        Args:
            window: Window object
            show_spectrogram: Include spectrogram
            component: Component for spectrogram
            save_path: Path to save figure
            
        Returns:
            Matplotlib figure
        """
        if show_spectrogram:
            fig = plt.figure(figsize=(14, 10))
            
            # Time series
            ax1 = fig.add_subplot(2, 1, 1)
            plot_window_time_series(window, ax=ax1)
            
            # Spectrogram
            ax2 = fig.add_subplot(2, 1, 2)
            plot_window_spectrogram(window, component=component, ax=ax2)
            
            plt.tight_layout()
        else:
            fig, ax = plt.subplots(figsize=(14, 6))
            plot_window_time_series(window, ax=ax)
            plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=self.default_dpi, bbox_inches='tight')
        
        return fig
    
    def plot_timeline(self,
                     windows: WindowCollection,
                     save_path: Optional[str] = None) -> Figure:
        """
        Plot rejection timeline.
        
        Args:
            windows: WindowCollection object
            save_path: Path to save figure
            
        Returns:
            Matplotlib figure
        """
        fig, ax = plt.subplots(figsize=(14, 6))
        plot_rejection_timeline(windows, ax=ax)
        plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=self.default_dpi, bbox_inches='tight')
        
        return fig
    
    def plot_comparison(self,
                       results: List[HVSRResult],
                       labels: List[str],
                       title: str = "HVSR Comparison",
                       save_path: Optional[str] = None) -> Figure:
        """
        Compare multiple HVSR results.
        
        Args:
            results: List of HVSRResult objects
            labels: List of labels
            title: Plot title
            save_path: Path to save figure
            
        Returns:
            Matplotlib figure
        """
        fig, ax = plt.subplots(figsize=(12, 7))
        plot_hvsr_comparison(results, labels, ax=ax, title=title)
        plt.tight_layout()
        
        if save_path:
            fig.savefig(save_path, dpi=self.default_dpi, bbox_inches='tight')
        
        return fig
    
    def save_report(self,
                   result: HVSRResult,
                   windows: WindowCollection,
                   output_dir: str,
                   include_windows: bool = True,
                   include_quality: bool = True,
                   include_timeline: bool = True) -> Dict[str, str]:
        """
        Generate complete analysis report with all plots.
        
        Args:
            result: HVSRResult object
            windows: WindowCollection object
            output_dir: Output directory
            include_windows: Include window overview
            include_quality: Include quality metrics
            include_timeline: Include rejection timeline
            
        Returns:
            Dictionary of saved file paths
        """
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        saved_files = {}
        
        # 1. Main HVSR curve
        hvsr_path = output_path / "hvsr_curve.png"
        self.plot_result(result, save_path=str(hvsr_path))
        saved_files['hvsr_curve'] = str(hvsr_path)
        
        # 2. Statistical analysis
        stats_path = output_path / "hvsr_statistics.png"
        self.plot_statistics(result, save_path=str(stats_path))
        saved_files['statistics'] = str(stats_path)
        
        # 3. Window overview
        if include_windows:
            windows_path = output_path / "window_overview.png"
            self.plot_windows(windows, save_path=str(windows_path))
            saved_files['windows'] = str(windows_path)
        
        # 4. Quality metrics
        if include_quality:
            quality_path = output_path / "quality_metrics.png"
            self.plot_quality_metrics(windows, save_path=str(quality_path))
            saved_files['quality'] = str(quality_path)
        
        # 5. Rejection timeline
        if include_timeline:
            timeline_path = output_path / "rejection_timeline.png"
            self.plot_timeline(windows, save_path=str(timeline_path))
            saved_files['timeline'] = str(timeline_path)
        
        # 6. Peak analysis (if peaks exist)
        if result.primary_peak:
            peak_path = output_path / "peak_analysis.png"
            fig, ax = plt.subplots(figsize=(12, 7))
            plot_peak_analysis(result.primary_peak, result.frequencies,
                             result.mean_hvsr, ax=ax)
            plt.tight_layout()
            fig.savefig(peak_path, dpi=self.default_dpi, bbox_inches='tight')
            plt.close(fig)
            saved_files['peak'] = str(peak_path)
        
        return saved_files
    
    def create_interactive_dashboard(self,
                                    result: HVSRResult,
                                    windows: WindowCollection,
                                    figsize: Tuple[int, int] = (18, 12)) -> Figure:
        """
        Create comprehensive interactive dashboard.
        
        Args:
            result: HVSRResult object
            windows: WindowCollection object
            figsize: Figure size
            
        Returns:
            Matplotlib figure with subplots
        """
        fig = plt.figure(figsize=figsize)
        
        # Create grid
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)
        
        # Main HVSR curve (top left, large)
        ax1 = fig.add_subplot(gs[0:2, 0:2])
        plot_hvsr_curve(result, ax=ax1, show_peaks=True,
                       title='HVSR Curve with Uncertainty')
        
        # Peak analysis (top right)
        ax2 = fig.add_subplot(gs[0, 2])
        if result.primary_peak:
            plot_peak_analysis(result.primary_peak, result.frequencies,
                             result.mean_hvsr, ax=ax2)
            ax2.set_title('Primary Peak', fontsize=10, fontweight='bold')
        
        # Mean vs Median (middle right)
        ax3 = fig.add_subplot(gs[1, 2])
        ax3.semilogx(result.frequencies, result.mean_hvsr, 'b-', label='Mean')
        ax3.semilogx(result.frequencies, result.median_hvsr, 'g--', label='Median')
        ax3.set_xlabel('Frequency (Hz)', fontsize=9)
        ax3.set_ylabel('H/V', fontsize=9)
        ax3.set_title('Mean vs Median', fontsize=10, fontweight='bold')
        ax3.legend(fontsize=8)
        ax3.grid(True, alpha=0.3)
        
        # Window status timeline (bottom, full width)
        ax4 = fig.add_subplot(gs[2, :])
        plot_rejection_timeline(windows, ax=ax4)
        
        plt.suptitle('HVSR Analysis Dashboard', fontsize=16, fontweight='bold')
        
        return fig
    
    def plot_with_windows(self, result: HVSRResult, title: str = None,
                         show_rejected: bool = False) -> Figure:
        """Plot HVSR with individual window curves (active windows only by default)."""
        fig, ax = plt.subplots(figsize=(12, 7))
        
        # Plot individual active window curves
        if result.window_spectra:
            plotted = 0
            for spectrum in result.window_spectra:
                if not show_rejected and hasattr(spectrum, 'rejected') and spectrum.rejected:
                    continue
                ax.semilogx(result.frequencies, spectrum.hvsr, 
                           'gray', alpha=0.3, linewidth=0.5)
                plotted += 1
                if plotted >= 50:
                    break
        
        # Plot median curve and uncertainty
        plot_hvsr_curve(result, ax=ax, show_peaks=True, show_median=True,
                       show_mean=False,
                       title=title or 'HVSR with Individual Windows')
        
        return fig
    
    def plot_mean_vs_median(self, result: HVSRResult) -> Figure:
        """Plot mean vs median comparison."""
        fig, ax = plt.subplots(figsize=(12, 7))
        
        ax.semilogx(result.frequencies, result.mean_hvsr, 'b-', 
                   linewidth=2.5, label='Mean')
        ax.semilogx(result.frequencies, result.median_hvsr, 'g--',
                   linewidth=2.5, label='Median')
        
        # Mark peaks (use LaTeX for proper subscript rendering)
        if result.primary_peak:
            ax.plot(result.primary_peak.frequency, result.primary_peak.amplitude,
                   'ro', markersize=10, markeredgecolor='black', markeredgewidth=1,
                   label=f'Peak: $f_0$={result.primary_peak.frequency:.2f} Hz')
        
        ax.set_xlabel('Frequency (Hz)', fontsize=12)
        ax.set_ylabel('H/V Spectral Ratio', fontsize=12)
        ax.set_title('Mean vs Median HVSR', fontsize=14, fontweight='bold')
        ax.grid(True, which='both', alpha=0.3, linestyle=':')
        ax.legend(loc='best', fontsize=10)
        
        return fig
    
    def plot_quality_histogram(self, windows: WindowCollection) -> Figure:
        """Plot quality score distribution."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        qualities = [w.quality_metrics.get('overall', 0.0) for w in windows.windows]
        active = [q for w, q in zip(windows.windows, qualities) if w.is_active()]
        rejected = [q for w, q in zip(windows.windows, qualities) if not w.is_active()]
        
        ax.hist(active, bins=20, alpha=0.7, color='green', label=f'Active ({len(active)})', edgecolor='black')
        ax.hist(rejected, bins=20, alpha=0.7, color='gray', label=f'Rejected ({len(rejected)})', edgecolor='black')
        
        ax.axvline(0.5, color='red', linestyle='--', linewidth=2, label='Threshold')
        ax.set_xlabel('Quality Score', fontsize=12)
        ax.set_ylabel('Count', fontsize=12)
        ax.set_title('Window Quality Distribution', fontsize=14, fontweight='bold')
        ax.legend(fontsize=10)
        ax.grid(True, alpha=0.3)
        
        return fig
    
    def plot_selected_metrics(self, windows: WindowCollection) -> Figure:
        """Plot selected key metrics comparison."""
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        axes = axes.flatten()
        
        metrics = ['overall', 'snr', 'stationarity', 'amplitude']
        titles = ['Overall Quality', 'Signal-to-Noise Ratio', 'Stationarity', 'Amplitude']
        
        for i, (metric, title) in enumerate(zip(metrics, titles)):
            ax = axes[i]
            values = [w.quality_metrics.get(metric, 0.0) for w in windows.windows]
            colors = ['green' if w.is_active() else 'gray' for w in windows.windows]
            
            ax.scatter(range(len(values)), values, c=colors, alpha=0.6, s=30)
            ax.set_xlabel('Window Index', fontsize=10)
            ax.set_ylabel(title, fontsize=10)
            ax.set_title(title, fontsize=12, fontweight='bold')
            ax.grid(True, alpha=0.3)
            
            if metric == 'overall':
                ax.axhline(0.5, color='red', linestyle='--', alpha=0.5)
        
        plt.suptitle('Key Quality Metrics', fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        return fig
    
    def plot_window_timeline(self, windows: WindowCollection) -> Figure:
        """Plot window timeline."""
        return self.plot_timeline(windows)
    
    def plot_window_timeseries(self, windows: WindowCollection, data) -> Figure:
        """Plot window timeseries for selected windows."""
        fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
        
        # Plot first few windows as examples
        sample_windows = [w for w in windows.windows[:5] if w.is_active()]
        
        if sample_windows and data:
            for window in sample_windows:
                start_idx = int(window.start_time * data.sampling_rate)
                end_idx = int((window.start_time + window.duration) * data.sampling_rate)
                time = np.arange(len(data.east.data[start_idx:end_idx])) / data.sampling_rate
                
                axes[0].plot(time, data.east.data[start_idx:end_idx], alpha=0.7)
                axes[1].plot(time, data.north.data[start_idx:end_idx], alpha=0.7)
                axes[2].plot(time, data.vertical.data[start_idx:end_idx], alpha=0.7)
        
        axes[0].set_ylabel('East (m/s²)', fontsize=10)
        axes[1].set_ylabel('North (m/s²)', fontsize=10)
        axes[2].set_ylabel('Vertical (m/s²)', fontsize=10)
        axes[2].set_xlabel('Time (s)', fontsize=10)
        
        for ax in axes:
            ax.grid(True, alpha=0.3)
        
        plt.suptitle('Window Timeseries (3-Component)', fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        return fig
    
    def plot_window_spectrogram(self, windows: WindowCollection, data) -> Figure:
        """Plot spectrograms for sample windows."""
        fig, axes = plt.subplots(1, 3, figsize=(16, 5))
        
        # Plot spectrogram of first active window
        active_windows = [w for w in windows.windows if w.is_active()]
        if active_windows and data:
            window = active_windows[0]
            start_idx = int(window.start_time * data.sampling_rate)
            end_idx = int((window.start_time + window.duration) * data.sampling_rate)
            
            from scipy import signal
            
            for i, (ax, comp_data, label) in enumerate(zip(axes, 
                                                           [data.east.data, data.north.data, data.vertical.data],
                                                           ['East', 'North', 'Vertical'])):
                f, t, Sxx = signal.spectrogram(comp_data[start_idx:end_idx], 
                                               fs=data.sampling_rate, nperseg=256)
                ax.pcolormesh(t, f, 10 * np.log10(Sxx), shading='gouraud', cmap='viridis')
                ax.set_ylabel('Frequency (Hz)', fontsize=10)
                ax.set_xlabel('Time (s)', fontsize=10)
                ax.set_title(f'{label} Component', fontsize=12)
                ax.set_ylim([0, 50])
        
        plt.suptitle('Window Spectrogram', fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        return fig
    
    def plot_peak_details(self, result: HVSRResult) -> Figure:
        """Plot detailed peak analysis."""
        fig, ax = plt.subplots(figsize=(12, 7))
        
        if result.primary_peak:
            plot_peak_analysis(result.primary_peak, result.frequencies,
                             result.mean_hvsr, ax=ax)
        
        return fig
    
    def plot_dashboard(self, result: HVSRResult, windows: WindowCollection) -> Figure:
        """Create complete dashboard."""
        return self.create_interactive_dashboard(result, windows)
    
    def show_all(self):
        """Display all open figures."""
        plt.show()
    
    def close_all(self):
        """Close all figures."""
        plt.close('all')
