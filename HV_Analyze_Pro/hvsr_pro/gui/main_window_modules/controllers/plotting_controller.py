"""
Plotting Controller
===================

Controller for managing HVSR plot visualization.
Handles plot creation, updates, and style management.
"""

from typing import Dict, Optional, List, Any, Tuple
import numpy as np

try:
    from PyQt5.QtCore import QObject, pyqtSignal
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


# Default color palette for window curves
DEFAULT_COLOR_PALETTE = [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
    '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
    '#c49c94', '#f7b6d2', '#c7c7c7', '#dbdb8d', '#9edae5'
]


if HAS_PYQT5:
    class PlottingController(QObject):
        """
        Controller for HVSR visualization.
        
        Manages:
        - Plotting HVSR results in separate window
        - Window line management
        - Statistical curve updates
        - Real-time mean recalculation
        - Plot property application
        
        Signals:
            plot_updated: Emitted when plot is updated
            mean_recalculated: Emitted when mean is recalculated from visible windows
        """
        
        plot_updated = pyqtSignal()
        mean_recalculated = pyqtSignal(int)  # number of visible windows
        
        def __init__(self, plot_manager=None, parent=None):
            super().__init__(parent)
            self.plot_manager = plot_manager
            self.window_lines = {}  # {window_index: matplotlib_line}
            self.stat_lines = {}    # {'mean': line, 'std_plus': line, 'std_minus': line}
            self._hvsr_result = None
            self._windows = None
            self._data = None
        
        def set_plot_manager(self, plot_manager):
            """Set the plot manager reference."""
            self.plot_manager = plot_manager
        
        def set_data(self, hvsr_result, windows, data):
            """
            Set data for plotting.
            
            Args:
                hvsr_result: HVSRResult object
                windows: WindowCollection object
                data: SeismicData object
            """
            self._hvsr_result = hvsr_result
            self._windows = windows
            self._data = data
        
        def get_color_palette(self) -> List[str]:
            """Get the color palette for window curves."""
            return DEFAULT_COLOR_PALETTE.copy()
        
        def plot_hvsr_results(self, hvsr_result, windows, data, properties=None) -> Dict:
            """
            Plot HVSR results in the plot manager window.
            
            Args:
                hvsr_result: HVSRResult object
                windows: WindowCollection object
                data: SeismicData object
                properties: Optional PlotProperties for styling
            
            Returns:
                Dict with {'window_lines': {...}, 'stat_lines': {...}}
            """
            if self.plot_manager is None:
                return {}
            
            self._hvsr_result = hvsr_result
            self._windows = windows
            self._data = data
            
            # Check for QC failure
            if hasattr(hvsr_result, 'metadata') and hvsr_result.metadata.get('qc_failure', False):
                # Show QC failure message on plot instead of empty
                self.plot_manager._create_axes()
                ax_timeline, ax_hvsr, ax_stats = self.plot_manager.get_axes()
                
                ax_hvsr.text(0.5, 0.5, 'QC Failure: No windows passed quality control\n\nPlease adjust QC settings or check data quality.', 
                             ha='center', va='center', fontsize=12, color='red',
                             transform=ax_hvsr.transAxes, wrap=True)
                ax_hvsr.set_title('HVSR Curve (QC Failed)', color='red')
                
                self.plot_manager.fig.tight_layout()
                self.plot_manager.canvas.draw()
                return {}
            
            # Recreate axes
            self.plot_manager._create_axes()
            ax_timeline, ax_hvsr, ax_stats = self.plot_manager.get_axes()
            
            # Plot timeline if visible
            if ax_timeline is not None:
                self._plot_timeline(ax_timeline, windows)
            
            # Plot HVSR curves
            self._plot_hvsr_curves(ax_hvsr, hvsr_result, windows, properties)
            
            # Plot statistics if visible
            if ax_stats is not None:
                self._plot_statistics(ax_stats, windows)
            
            # Finalize
            self.plot_manager.fig.tight_layout()
            self.plot_manager.canvas.draw()
            
            self.plot_updated.emit()
            
            return {
                'window_lines': self.window_lines,
                'stat_lines': self.stat_lines
            }
        
        def _plot_timeline(self, ax, windows):
            """Plot window timeline."""
            ax.clear()
            ax.set_title('Window Timeline (Click to Toggle State)')
            ax.set_xlabel('Time (s)')
            ax.set_ylabel('Window')
            
            for i, window in enumerate(windows.windows):
                color = 'green' if window.is_active() else 'gray'
                ax.barh(i, window.duration, left=window.start_time,
                       height=0.8, color=color, alpha=0.7)
            
            ax.set_ylim(-1, len(windows.windows))
            ax.invert_yaxis()
        
        @staticmethod
        def _compute_smart_ylim(hvsr_result):
            """Compute a robust Y-axis upper limit that ignores extreme outliers."""
            candidates = [np.max(hvsr_result.mean_hvsr) * 1.5]
            if hvsr_result.percentile_84 is not None:
                candidates.append(np.max(hvsr_result.percentile_84) * 1.2)
            if hvsr_result.std_hvsr is not None:
                candidates.append(np.max(hvsr_result.mean_hvsr + hvsr_result.std_hvsr) * 1.1)
            return max(candidates)
        
        def _plot_hvsr_curves(self, ax, hvsr_result, windows, properties=None):
            """Plot HVSR curves on axis."""
            self.window_lines = {}
            color_palette = self.get_color_palette()
            
            spectra_by_index = {}
            for spectrum in hvsr_result.window_spectra:
                spectra_by_index[spectrum.window_index] = spectrum
            
            # Plot individual windows
            plotted_count = 0
            n_active = 0
            for i, window in enumerate(windows.windows):
                window_idx = window.index
                if window.is_active():
                    n_active += 1
                
                if window_idx in spectra_by_index:
                    plotted_count += 1
                    window_spectrum = spectra_by_index[window_idx]
                    window_hvsr = window_spectrum.hvsr
                    
                    if window.is_active():
                        color = color_palette[i % len(color_palette)]
                        alpha = 0.5
                    else:
                        color = 'gray'
                        alpha = 0.3
                    
                    line, = ax.plot(
                        hvsr_result.frequencies, window_hvsr,
                        color=color, linewidth=0.8, alpha=alpha,
                        visible=window.is_active() and window.visible,
                        label=f'W{window_idx+1}' if plotted_count <= 5 else ''
                    )
                    self.window_lines[window_idx] = line
            
            # Percentile shading (16th-84th), clipped at zero
            percentile_fill = None
            if (hasattr(hvsr_result, 'percentile_16') and hvsr_result.percentile_16 is not None
                    and hasattr(hvsr_result, 'percentile_84') and hvsr_result.percentile_84 is not None):
                percentile_fill = ax.fill_between(
                    hvsr_result.frequencies,
                    np.maximum(hvsr_result.percentile_16, 0),
                    hvsr_result.percentile_84,
                    color='#9C27B0', alpha=0.15, zorder=50,
                    label='16th-84th percentile'
                )
            
            # Median (primary curve - thick, solid)
            median_line = None
            if hasattr(hvsr_result, 'median_hvsr') and hvsr_result.median_hvsr is not None:
                median_line, = ax.plot(
                    hvsr_result.frequencies, hvsr_result.median_hvsr,
                    color='#D32F2F', linewidth=2.5, linestyle='-',
                    label='Median H/V', zorder=101
                )
            
            # Mean (secondary curve - thinner)
            mean_line, = ax.plot(
                hvsr_result.frequencies, hvsr_result.mean_hvsr,
                color='#1976D2', linewidth=1.5, linestyle='-',
                label='Mean H/V', zorder=100
            )
            
            # Std bands (clipped at zero)
            std_plus, = ax.plot(
                hvsr_result.frequencies,
                hvsr_result.mean_hvsr + hvsr_result.std_hvsr,
                color='#FF5722', linestyle='--', linewidth=1.0,
                alpha=0.7, label='+1σ', zorder=99
            )
            
            std_minus, = ax.plot(
                hvsr_result.frequencies,
                np.maximum(hvsr_result.mean_hvsr - hvsr_result.std_hvsr, 0),
                color='#FF5722', linestyle='--', linewidth=1.0,
                alpha=0.7, label='-1σ', zorder=99
            )
            
            self.stat_lines = {
                'mean': mean_line,
                'std_plus': std_plus,
                'std_minus': std_minus,
            }
            if median_line is not None:
                self.stat_lines['median'] = median_line
            if percentile_fill is not None:
                self.stat_lines['percentile_fill'] = percentile_fill
            
            # Smart Y-limit
            smart_ylim = self._compute_smart_ylim(hvsr_result)
            ax.set_ylim(0, smart_ylim)
            
            # Axis settings
            ax.set_xscale('log')
            ax.set_xlabel('Frequency (Hz)')
            ax.set_ylabel('H/V Spectral Ratio')
            ax.set_title('HVSR Curve')
            ax.grid(True, which='both', linestyle=':', alpha=0.3)
            ax.legend(loc='upper right', fontsize=8)
            
            # Acceptance badge
            n_total = windows.n_windows
            acceptance_pct = (n_active / n_total * 100) if n_total > 0 else 0
            ax.text(
                0.02, 0.98,
                f'{n_active}/{n_total} windows ({acceptance_pct:.0f}%)',
                transform=ax.transAxes, fontsize=9,
                verticalalignment='top',
                bbox=dict(boxstyle='round,pad=0.4', facecolor='wheat', alpha=0.7)
            )
        
        def _plot_statistics(self, ax, windows):
            """Plot window quality statistics."""
            ax.clear()
            ax.set_title('Window Quality Statistics')
            ax.set_xlabel('Window Index')
            ax.set_ylabel('Quality Score')
            
            qualities = [w.quality_metrics.get('overall', 0.0) for w in windows.windows]
            colors = ['green' if w.is_active() else 'gray' for w in windows.windows]
            ax.scatter(range(len(windows.windows)), qualities, c=colors, alpha=0.7, s=50)
            ax.axhline(0.5, color='red', linestyle='--', alpha=0.5, label='Threshold')
            ax.legend()
            ax.grid(True, alpha=0.3)
        
        def update_line_visibility(self, mode: str):
            """
            Update line visibility based on view mode.
            
            Args:
                mode: 'statistical', 'windows', or 'both'
            """
            if not self.window_lines or not self.stat_lines:
                return
            
            if mode == 'statistical':
                # Hide individual windows, show statistics
                for line in self.window_lines.values():
                    line.set_visible(False)
                for line in self.stat_lines.values():
                    line.set_visible(True)
            
            elif mode == 'windows':
                # Show windows based on their visibility flags
                if self._windows:
                    for idx, line in self.window_lines.items():
                        window = self._windows.get_window(idx)
                        if window:
                            line.set_visible(window.is_active() and window.visible)
                for line in self.stat_lines.values():
                    line.set_visible(True)
            
            elif mode == 'both':
                # Show everything
                if self._windows:
                    for idx, line in self.window_lines.items():
                        window = self._windows.get_window(idx)
                        if window:
                            line.set_visible(window.is_active() and window.visible)
                for line in self.stat_lines.values():
                    line.set_visible(True)
            
            # Redraw
            if self.plot_manager:
                self.plot_manager.fig.canvas.draw_idle()
        
        def recalculate_mean_from_visible(self):
            """
            Recalculate mean, median, std, and percentiles from currently
            visible/active windows and update all stat lines in real-time.
            """
            if not self._hvsr_result or not self._windows or not self.stat_lines:
                return
            
            spectra_by_index = {s.window_index: s for s in self._hvsr_result.window_spectra}
            
            visible_hvsr_curves = []
            for window in self._windows.windows:
                window_idx = window.index
                if window.should_include_in_hvsr() and window_idx in spectra_by_index:
                    visible_hvsr_curves.append(spectra_by_index[window_idx].hvsr)
            
            if not visible_hvsr_curves:
                for line in self.stat_lines.values():
                    line.set_visible(False)
                if self.plot_manager:
                    self.plot_manager.fig.canvas.draw_idle()
                self.mean_recalculated.emit(0)
                return
            
            arr = np.array(visible_hvsr_curves)
            new_mean = np.mean(arr, axis=0)
            new_std = np.std(arr, axis=0)
            new_median = np.median(arr, axis=0)
            new_p16 = np.percentile(arr, 16, axis=0)
            new_p84 = np.percentile(arr, 84, axis=0)
            
            if 'mean' in self.stat_lines:
                self.stat_lines['mean'].set_ydata(new_mean)
            if 'std_plus' in self.stat_lines:
                self.stat_lines['std_plus'].set_ydata(new_mean + new_std)
            if 'std_minus' in self.stat_lines:
                self.stat_lines['std_minus'].set_ydata(np.maximum(new_mean - new_std, 0))
            if 'median' in self.stat_lines:
                self.stat_lines['median'].set_ydata(new_median)
            
            # Update percentile fill (replace the PolyCollection paths)
            if 'percentile_fill' in self.stat_lines:
                fill = self.stat_lines['percentile_fill']
                ax = fill.axes
                if ax is not None:
                    fill.remove()
                    new_fill = ax.fill_between(
                        self._hvsr_result.frequencies,
                        np.maximum(new_p16, 0),
                        new_p84,
                        color='#9C27B0', alpha=0.15, zorder=50,
                        label='16th-84th percentile'
                    )
                    self.stat_lines['percentile_fill'] = new_fill
            
            if self.plot_manager:
                self.plot_manager.fig.canvas.draw_idle()
            
            self.mean_recalculated.emit(len(visible_hvsr_curves))
        
        def refresh_plot(self):
            """Refresh plot with current data."""
            if self._hvsr_result and self._windows and self._data:
                self.plot_hvsr_results(self._hvsr_result, self._windows, self._data)
        
        def apply_properties(self, properties):
            """
            Apply plot properties to current visualization.
            
            Args:
                properties: PlotProperties object with style settings
            """
            if not self._hvsr_result or not self._windows or not self._data:
                return
            
            if self.plot_manager is None:
                return
            
            # Store data in plot manager
            self.plot_manager.set_plot_data(self._hvsr_result, self._windows, self._data)
            
            # Replot with properties
            self._replot_with_properties(properties)
        
        def _replot_with_properties(self, properties):
            """Replot with given properties."""
            # Recreate axes
            self.plot_manager._create_axes()
            ax_timeline, ax_hvsr, ax_stats = self.plot_manager.get_axes()
            
            result = self._hvsr_result
            windows = self._windows
            
            # Plot timeline if visible
            if ax_timeline is not None:
                self._plot_timeline(ax_timeline, windows)
            
            # Plot HVSR with properties
            self.window_lines = {}
            color_palette = self.get_color_palette()
            
            # Set background color
            bg_color = self.plot_manager.get_background_color(properties)
            ax_hvsr.set_facecolor(bg_color)
            
            # Plot windows if enabled
            if properties.show_windows:
                # Build index map for spectra
                spectra_by_index = {s.window_index: s for s in result.window_spectra}
                
                for i, window in enumerate(windows.windows):
                    window_idx = window.index
                    
                    if window_idx in spectra_by_index:
                        if window.is_active():
                            color = color_palette[i % len(color_palette)]
                            alpha = properties.window_alpha
                        else:
                            color = 'gray'
                            alpha = properties.window_alpha * 0.6
                        
                        window_spectrum = spectra_by_index[window_idx]
                        window_hvsr = window_spectrum.hvsr
                        
                        line, = ax_hvsr.plot(
                            result.frequencies, window_hvsr,
                            color=color, linewidth=0.8, alpha=alpha,
                            visible=window.is_active() and window.visible
                        )
                        self.window_lines[window_idx] = line
            
            self.stat_lines = {}
            
            # Plot percentile shading if enabled (clipped at zero)
            if properties.show_percentile_shading and result.percentile_16 is not None:
                perc_color = getattr(properties, 'percentile_color', '#9C27B0')
                percentile_fill = ax_hvsr.fill_between(
                    result.frequencies,
                    np.maximum(result.percentile_16, 0),
                    result.percentile_84,
                    color=perc_color, alpha=0.2, zorder=50,
                    label='16th-84th percentile'
                )
                self.stat_lines['percentile_fill'] = percentile_fill
            
            # Plot median if enabled (primary curve)
            if properties.show_median and result.median_hvsr is not None:
                median_color = getattr(properties, 'median_color', '#D32F2F')
                median_lw = getattr(properties, 'median_linewidth', 2.5)
                median_line, = ax_hvsr.plot(
                    result.frequencies, result.median_hvsr,
                    color=median_color, linewidth=median_lw,
                    label='Median H/V', zorder=101
                )
                self.stat_lines['median'] = median_line
            
            # Plot mean if enabled (secondary)
            if properties.show_mean:
                mean_color = getattr(properties, 'mean_color', '#1976D2')
                mean_line, = ax_hvsr.plot(
                    result.frequencies, result.mean_hvsr,
                    color=mean_color, linewidth=properties.mean_linewidth,
                    label='Mean H/V', zorder=100
                )
                self.stat_lines['mean'] = mean_line
            
            # Plot std bands if enabled (clipped at zero)
            if properties.show_std_bands and result.std_hvsr is not None:
                std_color = getattr(properties, 'std_color', '#FF5722')
                std_lw = getattr(properties, 'std_linewidth', 1.5)
                std_plus, = ax_hvsr.plot(
                    result.frequencies,
                    result.mean_hvsr + result.std_hvsr,
                    color=std_color, linestyle='--', linewidth=std_lw,
                    label='+1σ', zorder=99
                )
                std_minus, = ax_hvsr.plot(
                    result.frequencies,
                    np.maximum(result.mean_hvsr - result.std_hvsr, 0),
                    color=std_color, linestyle='--', linewidth=std_lw,
                    label='-1σ', zorder=99
                )
                self.stat_lines['std_plus'] = std_plus
                self.stat_lines['std_minus'] = std_minus
            
            # Set Y-axis limits (smart auto or manual)
            if properties.y_mode == 'auto':
                smart_ylim = self._compute_smart_ylim(result)
                ax_hvsr.set_ylim(0, smart_ylim)
            else:
                y_min, y_max = self.plot_manager.calculate_y_limits(properties, result)
                ax_hvsr.set_ylim(max(y_min, 0), y_max)
            
            # Axis settings
            ax_hvsr.set_xscale('log')
            ax_hvsr.set_xlabel('Frequency (Hz)')
            ax_hvsr.set_ylabel('H/V Spectral Ratio')
            ax_hvsr.set_title('HVSR Curve')
            ax_hvsr.set_xlim(result.frequencies[0], result.frequencies[-1])
            
            # Grid
            if properties.show_grid:
                ax_hvsr.grid(True, which='both', alpha=0.3)
            
            # Legend
            if properties.show_legend:
                ax_hvsr.legend(loc='upper right', fontsize=9)
            
            # Acceptance badge
            if properties.show_acceptance_badge:
                acceptance_rate = windows.acceptance_rate * 100
                badge_text = f'Acceptance: {acceptance_rate:.1f}%'
                ax_hvsr.text(
                    0.02, 0.98, badge_text,
                    transform=ax_hvsr.transAxes,
                    fontsize=10, verticalalignment='top',
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='white',
                            edgecolor='black', alpha=0.8)
                )
            
            # Plot stats panel if visible
            if ax_stats is not None:
                self._plot_statistics(ax_stats, windows)
                if properties.show_grid:
                    ax_stats.grid(True, alpha=0.3)
            
            # Finalize
            self.plot_manager.fig.tight_layout()
            self.plot_manager.canvas.draw()
            
            self.plot_updated.emit()
        
        def get_window_lines(self) -> Dict:
            """Get the window lines dictionary."""
            return self.window_lines
        
        def get_stat_lines(self) -> Dict:
            """Get the stat lines dictionary."""
            return self.stat_lines


else:
    class PlottingController:
        """Dummy class when PyQt5 not available."""
        def __init__(self, *args, **kwargs):
            raise ImportError("PyQt5 is required for GUI functionality")
