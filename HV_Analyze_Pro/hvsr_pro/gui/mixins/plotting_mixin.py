"""
Plotting Mixin
==============

Mixin providing HVSR plotting functionality for the main window.
"""

import numpy as np
from typing import List, Dict, Any, Optional

try:
    from PyQt5.QtWidgets import QMessageBox, QFileDialog
    HAS_PYQT5 = True
except ImportError:
    HAS_PYQT5 = False


class PlottingMixin:
    """
    Mixin providing HVSR plotting functionality.
    
    This mixin should be used with HVSRMainWindow and provides:
    - plot_results_separate_window(): Plot results in separate window
    - refresh_plot(): Refresh plot with current settings
    - replot_with_properties(): Replot with property settings
    - recalculate_mean_from_visible_windows(): Update mean from visible windows
    - on_properties_changed(): Handle property changes
    - _get_color_palette(): Get color palette for window curves
    
    Expected attributes on the main class:
    - hvsr_result: HVSRResult
    - windows: WindowCollection
    - data: SeismicData
    - plot_manager: PlotWindowManager
    - layers_dock: WindowLayersDock
    - window_lines: Dict[int, matplotlib line]
    - stat_lines: Dict[str, matplotlib line]
    """
    
    # Color palette for window curves
    COLOR_PALETTE = [
        '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
        '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
        '#aec7e8', '#ffbb78', '#98df8a', '#ff9896', '#c5b0d5',
        '#c49c94', '#f7b6d2', '#c7c7c7', '#dbdb8d', '#9edae5'
    ]
    
    def plot_results_separate_window(self, result, windows, data):
        """Plot results in separate plot window."""
        # Check for QC failure
        if hasattr(result, 'metadata') and result.metadata.get('qc_failure', False):
            return
        
        # Recreate axes
        self.plot_manager._create_axes()
        ax_timeline, ax_hvsr, ax_stats = self.plot_manager.get_axes()
        
        # Plot timeline (if visible)
        if ax_timeline is not None:
            self._plot_timeline(ax_timeline, windows)
        
        # Plot HVSR curves
        self._plot_hvsr_curves(ax_hvsr, result, windows)
        
        # Plot quality statistics (if visible)
        if ax_stats is not None:
            self._plot_quality_stats(ax_stats, windows)
        
        # Finalize
        self.plot_manager.fig.tight_layout()
        self.plot_manager.canvas.draw()
        
        # Rebuild layer dock
        self.layers_dock.rebuild(self.window_lines, self.stat_lines)
        
        # Show plot window
        self.plot_manager.show_separate()
        self.add_info("Plot window opened")
    
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
    
    def _plot_hvsr_curves(self, ax, result, windows):
        """Plot individual HVSR curves and statistics."""
        self.window_lines = {}
        color_palette = self._get_color_palette()
        
        # Plot all windows (active and rejected)
        for i, window in enumerate(windows.windows):
            if i < len(result.window_spectra):
                if window.is_active():
                    color = color_palette[i % len(color_palette)]
                    alpha = 0.5
                else:
                    color = 'gray'
                    alpha = 0.3
                
                window_spectrum = result.window_spectra[i]
                window_hvsr = window_spectrum.hvsr
                
                line, = ax.plot(
                    result.frequencies, window_hvsr,
                    color=color, linewidth=0.8, alpha=alpha,
                    visible=window.is_active() and window.visible,
                    label=f'W{i+1}' if i < 5 else ''
                )
                self.window_lines[i] = line
        
        # Plot mean and std
        mean_line, = ax.plot(
            result.frequencies, result.mean_hvsr,
            'k-', linewidth=2.5, label='Mean', zorder=100
        )
        
        std_plus, = ax.plot(
            result.frequencies,
            result.mean_hvsr + result.std_hvsr,
            'k--', linewidth=1.5, label='+1\u03c3', zorder=99
        )
        
        std_minus, = ax.plot(
            result.frequencies,
            result.mean_hvsr - result.std_hvsr,
            'k--', linewidth=1.5, label='-1\u03c3', zorder=99
        )
        
        self.stat_lines = {
            'mean': mean_line,
            'std_plus': std_plus,
            'std_minus': std_minus
        }
        
        # Configure axes
        ax.set_xscale('log')
        ax.set_xlabel('Frequency (Hz)')
        ax.set_ylabel('H/V Ratio')
        ax.set_title('HVSR Curve - Individual Windows Mode')
        ax.grid(True, which='both', alpha=0.3)
        ax.legend(loc='upper right', fontsize=8)
    
    def _plot_quality_stats(self, ax, windows):
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
    
    def refresh_plot(self):
        """Refresh plot with current panel visibility settings."""
        if not self.hvsr_result or not self.windows or not self.data:
            return
        
        self.plot_results_separate_window(self.hvsr_result, self.windows, self.data)
        self.add_info("Plot refreshed")
    
    def _get_color_palette(self) -> List[str]:
        """Get color palette for window curves."""
        return self.COLOR_PALETTE
    
    def recalculate_mean_from_visible_windows(self):
        """
        Recalculate mean HVSR from currently visible windows in real-time.
        
        Provides instant visual feedback when user toggles window visibility.
        """
        if not self.hvsr_result or not self.windows or not self.stat_lines:
            return
        
        # Collect visible window HVSR curves
        visible_hvsr_curves = []
        
        for i, window in enumerate(self.windows.windows):
            if window.should_include_in_hvsr() and i < len(self.hvsr_result.window_spectra):
                window_spectrum = self.hvsr_result.window_spectra[i]
                visible_hvsr_curves.append(window_spectrum.hvsr)
        
        if not visible_hvsr_curves:
            # No visible windows - hide mean lines
            for line in self.stat_lines.values():
                line.set_visible(False)
            self.plot_manager.fig.canvas.draw_idle()
            self.add_info("WARNING: No visible windows - mean hidden")
            return
        
        # Compute new mean and std
        visible_hvsr_array = np.array(visible_hvsr_curves)
        new_mean = np.mean(visible_hvsr_array, axis=0)
        new_std = np.std(visible_hvsr_array, axis=0)
        
        # Update lines
        if 'mean' in self.stat_lines:
            self.stat_lines['mean'].set_ydata(new_mean)
        if 'std_plus' in self.stat_lines:
            self.stat_lines['std_plus'].set_ydata(new_mean + new_std)
        if 'std_minus' in self.stat_lines:
            self.stat_lines['std_minus'].set_ydata(new_mean - new_std)
        
        # Redraw
        self.plot_manager.fig.canvas.draw_idle()
        
        self.add_info(f"Mean recalculated from {len(visible_hvsr_curves)} visible windows")
    
    def on_properties_changed(self, properties):
        """
        Handle plot properties changes from properties dock.
        
        Args:
            properties: PlotProperties object with new settings
        """
        if not self.hvsr_result or not self.windows or not self.data:
            self.add_info("No data to apply properties to")
            return
        
        self.add_info(f"Properties applied: {properties.style_preset} style")
        
        # Store data in plot manager
        self.plot_manager.set_plot_data(self.hvsr_result, self.windows, self.data)
        
        # Replot with properties
        self.replot_with_properties(properties)
    
    def replot_with_properties(self, properties):
        """
        Replot with given properties.
        
        Args:
            properties: PlotProperties object
        """
        # Recreate axes
        self.plot_manager._create_axes()
        ax_timeline, ax_hvsr, ax_stats = self.plot_manager.get_axes()
        
        result = self.hvsr_result
        windows = self.windows
        
        # Plot timeline (if visible)
        if ax_timeline is not None:
            self._plot_timeline(ax_timeline, windows)
        
        # Initialize line tracking
        self.window_lines = {}
        color_palette = self._get_color_palette()
        
        # Set background color
        bg_color = self.plot_manager.get_background_color(properties)
        ax_hvsr.set_facecolor(bg_color)
        
        # Plot individual windows (if enabled)
        if properties.show_windows:
            for i, window in enumerate(windows.windows):
                if i < len(result.window_spectra):
                    if window.is_active():
                        color = color_palette[i % len(color_palette)]
                        alpha = properties.window_alpha
                    else:
                        color = 'gray'
                        alpha = properties.window_alpha * 0.6
                    
                    window_spectrum = result.window_spectra[i]
                    window_hvsr = window_spectrum.hvsr
                    
                    line, = ax_hvsr.plot(
                        result.frequencies, window_hvsr,
                        color=color, linewidth=0.8, alpha=alpha,
                        visible=window.is_active() and window.visible
                    )
                    self.window_lines[i] = line
        
        # Plot percentile shading (if enabled)
        if properties.show_percentile_shading and result.percentile_16 is not None:
            perc_color = getattr(properties, 'percentile_color', '#9C27B0')
            ax_hvsr.fill_between(
                result.frequencies,
                result.percentile_16,
                result.percentile_84,
                color=perc_color, alpha=0.2, zorder=50,
                label='16th-84th percentile'
            )
        
        # Plot mean curve (if enabled)
        self.stat_lines = {}
        if properties.show_mean:
            mean_color = getattr(properties, 'mean_color', '#1976D2')
            mean_line, = ax_hvsr.plot(
                result.frequencies, result.mean_hvsr,
                color=mean_color, linewidth=properties.mean_linewidth,
                label='Mean H/V', zorder=100
            )
            self.stat_lines['mean'] = mean_line
        
        # Plot std bands (if enabled)
        if properties.show_std_bands and result.std_hvsr is not None:
            std_color = getattr(properties, 'std_color', '#FF5722')
            std_lw = getattr(properties, 'std_linewidth', 1.5)
            std_plus, = ax_hvsr.plot(
                result.frequencies,
                result.mean_hvsr + result.std_hvsr,
                color=std_color, linestyle='--', linewidth=std_lw,
                label='+1\u03c3', zorder=99
            )
            std_minus, = ax_hvsr.plot(
                result.frequencies,
                result.mean_hvsr - result.std_hvsr,
                color=std_color, linestyle='--', linewidth=std_lw,
                label='-1\u03c3', zorder=99
            )
            self.stat_lines['std_plus'] = std_plus
            self.stat_lines['std_minus'] = std_minus
        
        # Plot median (if enabled)
        if properties.show_median and result.median_hvsr is not None:
            median_color = getattr(properties, 'median_color', '#D32F2F')
            median_lw = getattr(properties, 'median_linewidth', 1.5)
            median_line, = ax_hvsr.plot(
                result.frequencies, result.median_hvsr,
                color=median_color, linewidth=median_lw,
                label='Median', zorder=98
            )
            self.stat_lines['median'] = median_line
        
        # Set Y-axis limits
        y_min, y_max = self.plot_manager.calculate_y_limits(properties, result)
        ax_hvsr.set_ylim(y_min, y_max)
        
        # Configure axes
        ax_hvsr.set_xscale('log')
        ax_hvsr.set_xlabel('Frequency (Hz)')
        ax_hvsr.set_ylabel('H/V Spectral Ratio')
        ax_hvsr.set_title('HVSR Curve')
        ax_hvsr.set_xlim(result.frequencies[0], result.frequencies[-1])
        
        # Grid (if enabled)
        if properties.show_grid:
            ax_hvsr.grid(True, which='both', alpha=0.3)
        
        # Legend (if enabled)
        if properties.show_legend:
            ax_hvsr.legend(loc='upper right', fontsize=9)
        
        # Acceptance badge (if enabled)
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
        
        # Add peak markers
        if properties.show_peak_labels and hasattr(self, 'peak_picker_dock'):
            peaks = self.peak_picker_dock.peaks
            if peaks:
                self.plot_manager.add_peak_markers(peaks, label_style=properties.peak_label_style)
        
        # Plot stats panel (if visible)
        if ax_stats is not None:
            self._plot_quality_stats(ax_stats, windows)
            if properties.show_grid:
                ax_stats.grid(True, alpha=0.3)
        
        # Finalize
        self.plot_manager.fig.tight_layout()
        self.plot_manager.canvas.draw()
        
        # Rebuild layer dock
        self.layers_dock.rebuild(self.window_lines, self.stat_lines)
        
        # Show plot window
        self.plot_manager.show_separate()
    
    def export_figure(self):
        """Export current plot as image (alias for export_plot_image)."""
        self.export_plot_image()
    
    def export_plot_image(self):
        """Export current plot view as high-DPI image."""
        if self.hvsr_result is None or self.plot_manager.fig is None:
            QMessageBox.warning(
                self, "No Plot",
                "No plot to export. Please process data first."
            )
            return
        
        # Ask user for file path and format
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Export Plot as Image",
            "",
            "PNG Image (*.png);;PDF Document (*.pdf);;SVG Vector (*.svg)"
        )
        
        if not file_path:
            return
        
        try:
            # Determine format from filter
            if 'PDF' in selected_filter:
                if not file_path.lower().endswith('.pdf'):
                    file_path += '.pdf'
                dpi = 300
            elif 'SVG' in selected_filter:
                if not file_path.lower().endswith('.svg'):
                    file_path += '.svg'
                dpi = 150
            else:
                if not file_path.lower().endswith('.png'):
                    file_path += '.png'
                dpi = 300
            
            # Save figure
            self.plot_manager.fig.savefig(
                file_path,
                dpi=dpi,
                bbox_inches='tight',
                facecolor='white',
                edgecolor='none'
            )
            
            self.add_info(f"Plot exported to: {file_path}")
            QMessageBox.information(
                self, "Export Complete",
                f"Plot saved to:\n{file_path}"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self, "Export Error",
                f"Failed to export plot:\n{str(e)}"
            )
            self.add_info(f"ERROR - Export failed: {str(e)}")

