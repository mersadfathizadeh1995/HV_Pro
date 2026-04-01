"""
HVSR Curve Plotting for HVSR Pro
=================================

Functions for plotting HVSR curves with uncertainty, peaks, and statistics.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from typing import Optional, List, Tuple, Dict, Any
from pathlib import Path

from hvsr_pro.processing.hvsr import HVSRResult, Peak


def _calculate_smart_annotation_position(peak_x, peak_y, ax, x_data, y_data):
    """
    Calculate smart annotation position that avoids overlaps.
    
    Args:
        peak_x: Peak x-coordinate (frequency)
        peak_y: Peak y-coordinate (amplitude)
        ax: Matplotlib axes
        x_data: Full x data array
        y_data: Full y data array
    
    Returns:
        (x_offset, y_offset, horizontal_alignment, vertical_alignment)
    """
    # Get axis limits
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    
    # Normalize peak position (0 to 1)
    # Handle log scale for x-axis
    if ax.get_xscale() == 'log':
        x_norm = (np.log10(peak_x) - np.log10(xlim[0])) / (np.log10(xlim[1]) - np.log10(xlim[0]))
    else:
        x_norm = (peak_x - xlim[0]) / (xlim[1] - xlim[0])
    
    y_norm = (peak_y - ylim[0]) / (ylim[1] - ylim[0])
    
    # Determine best position based on peak location
    # Priority: Avoid top 20% (title area) and edges
    
    # Default offsets (in points)
    x_offset = 20
    y_offset = 20
    ha = 'left'
    va = 'bottom'
    
    # If peak is in upper region (y > 0.7), place annotation below
    if y_norm > 0.7:
        y_offset = -30
        va = 'top'
    # If peak is in lower region (y < 0.3), place annotation above
    elif y_norm < 0.3:
        y_offset = 30
        va = 'bottom'
    # Middle region - place above by default
    else:
        y_offset = 25
        va = 'bottom'
    
    # Horizontal positioning
    # If peak is on right side, place annotation to the left
    if x_norm > 0.7:
        x_offset = -25
        ha = 'right'
    # If peak is on left side, place annotation to the right
    elif x_norm < 0.3:
        x_offset = 25
        ha = 'left'
    # Center region - slightly to the right
    else:
        x_offset = 30
        ha = 'left'
    
    return x_offset, y_offset, ha, va


def plot_hvsr_curve(result: HVSRResult,
                   ax: Optional[Axes] = None,
                   show_uncertainty: bool = True,
                   show_peaks: bool = True,
                   show_median: bool = True,
                   show_mean: bool = False,
                   uncertainty_type: str = 'percentile',
                   title: Optional[str] = None,
                   **kwargs) -> Axes:
    """
    Plot HVSR curve with optional uncertainty and peaks.
    
    Args:
        result: HVSRResult object
        ax: Matplotlib axes (creates new if None)
        show_uncertainty: Show uncertainty band
        show_peaks: Mark detected peaks
        show_median: Show median curve (primary)
        show_mean: Show mean curve (secondary)
        uncertainty_type: 'percentile' (16-84) or 'std' (±1σ)
        title: Plot title
        **kwargs: Additional plot kwargs
        
    Returns:
        Matplotlib axes
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 6))

    frequencies = result.frequencies

    # Choose reference curve for degenerate check and Y-limits
    ref_curve = result.median_hvsr if result.median_hvsr is not None else result.mean_hvsr
    ref_max = np.max(np.abs(ref_curve))
    data_range = np.ptp(ref_curve)
    is_degenerate = (data_range < 1e-10) or (ref_max < 1e-10)

    line_color = kwargs.pop('color', '#1976D2')
    line_width = kwargs.pop('linewidth', 1.5)

    # Plot uncertainty band first (behind curves), clipped at zero
    if show_uncertainty and not is_degenerate:
        if uncertainty_type == 'percentile':
            lower = np.maximum(result.percentile_16, 0)
            upper = result.percentile_84
            label = '16th-84th percentile'
        elif uncertainty_type == 'std':
            lower = np.maximum(result.mean_hvsr - result.std_hvsr, 0)
            upper = result.mean_hvsr + result.std_hvsr
            label = 'Mean ± 1σ'
        else:
            raise ValueError(f"Unknown uncertainty_type: {uncertainty_type}")

        ax.fill_between(frequencies, lower, upper,
                       alpha=0.2, color='#9C27B0', label=label)

    # Plot median (primary curve) if requested
    if show_median and not is_degenerate and result.median_hvsr is not None:
        ax.semilogx(frequencies, result.median_hvsr,
                   color='#D32F2F', linewidth=2.5, linestyle='-',
                   label='Median H/V', zorder=101)

    # Plot mean HVSR (secondary curve) — only if explicitly requested
    if show_mean and not is_degenerate:
        ax.semilogx(frequencies, result.mean_hvsr,
                   color=line_color, linewidth=line_width,
                   label='Mean H/V', zorder=100, alpha=0.6, **kwargs)

    # If neither median nor mean shown, plot median as fallback
    if not show_median and not show_mean and not is_degenerate:
        ax.semilogx(frequencies, result.median_hvsr if result.median_hvsr is not None else result.mean_hvsr,
                   color='#D32F2F', linewidth=2.5, linestyle='-',
                   label='H/V', zorder=101)
    
    # Mark peaks
    if show_peaks and result.peaks:
        for i, peak in enumerate(result.peaks[:3]):  # Top 3 peaks
            marker_size = 10 if i == 0 else 8  # Larger for primary
            marker_color = 'red' if i == 0 else 'orange'
            
            ax.plot(peak.frequency, peak.amplitude, 
                   'o', color=marker_color, markersize=marker_size,
                   markeredgecolor='black', markeredgewidth=1,
                   zorder=5)
            
            # Annotate primary peak
            if i == 0:
                x_off, y_off, ha, va = _calculate_smart_annotation_position(
                    peak.frequency, peak.amplitude, ax, frequencies, ref_curve
                )
                
                ax.annotate(f'$f_0$ = {peak.frequency:.2f} Hz\nA = {peak.amplitude:.2f}',
                           xy=(peak.frequency, peak.amplitude),
                           xytext=(x_off, y_off), textcoords='offset points',
                           bbox=dict(boxstyle='round,pad=0.5', fc='yellow', alpha=0.7),
                           arrowprops=dict(arrowstyle='->', connectionstyle='arc3,rad=0.2'),
                           fontsize=10, fontweight='bold',
                           horizontalalignment=ha, verticalalignment=va)
    
    # Formatting
    ax.set_xlabel('Frequency (Hz)', fontsize=12)
    ax.set_ylabel('H/V Spectral Ratio', fontsize=12)

    if title:
        ax.set_title(title, fontsize=14, fontweight='bold')
    else:
        ax.set_title(f'HVSR Curve ({result.valid_windows} windows)',
                    fontsize=14, fontweight='bold')

    ax.grid(True, which='both', alpha=0.3, linestyle=':')
    ax.legend(loc='best', fontsize=10)
    ax.set_xlim(frequencies[0], frequencies[-1])

    # Y-limit based on median (robust) or percentile_84
    if not is_degenerate:
        ylim_candidates = [np.max(ref_curve) * 1.5]
        if result.percentile_84 is not None:
            ylim_candidates.append(np.max(result.percentile_84) * 1.2)
        ax.set_ylim(0, max(ylim_candidates))

    # Handle degenerate data
    if is_degenerate:
        ax.set_ylim(-0.1, 0.1)
        ax.text(0.5, 0.5,
               '⚠️ WARNING: HVSR values are extremely small or zero\n'
               'Check input data quality',
               transform=ax.transAxes,
               ha='center', va='center',
               fontsize=11, color='red',
               bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))

    # Add acceptance rate info
    acc_text = f'Acceptance: {result.acceptance_rate:.1%}'
    ax.text(0.02, 0.98, acc_text, transform=ax.transAxes,
           verticalalignment='top', fontsize=9,
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    return ax


def plot_hvsr_comparison(results: List[HVSRResult],
                        labels: List[str],
                        ax: Optional[Axes] = None,
                        colors: Optional[List[str]] = None,
                        title: str = "HVSR Comparison") -> Axes:
    """
    Compare multiple HVSR results on same plot.
    
    Args:
        results: List of HVSRResult objects
        labels: List of labels for each result
        ax: Matplotlib axes
        colors: List of colors
        title: Plot title
        
    Returns:
        Matplotlib axes
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(12, 6))
    
    if colors is None:
        colors = plt.cm.tab10(np.linspace(0, 1, len(results)))
    
    for result, label, color in zip(results, labels, colors):
        ax.semilogx(result.frequencies, result.mean_hvsr,
                   linewidth=2, label=label, color=color)
        
        # Mark primary peak
        if result.primary_peak:
            ax.plot(result.primary_peak.frequency, 
                   result.primary_peak.amplitude,
                   'o', color=color, markersize=8,
                   markeredgecolor='black', markeredgewidth=1)
    
    ax.set_xlabel('Frequency (Hz)', fontsize=12)
    ax.set_ylabel('H/V Spectral Ratio', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.grid(True, which='both', alpha=0.3, linestyle=':')
    ax.legend(loc='best', fontsize=10)
    
    return ax


def plot_hvsr_components(result: HVSRResult,
                        window_index: int = 0,
                        fig: Optional[Figure] = None) -> Figure:
    """
    Plot individual component spectra and H/V for a window.
    
    Args:
        result: HVSRResult with window_spectra
        window_index: Index of window to plot
        fig: Matplotlib figure
        
    Returns:
        Matplotlib figure
    """
    if not result.window_spectra:
        raise ValueError("HVSRResult has no window_spectra")
    
    if window_index >= len(result.window_spectra):
        raise ValueError(f"window_index {window_index} out of range")
    
    window_spec = result.window_spectra[window_index]
    
    if fig is None:
        fig = plt.figure(figsize=(12, 10))
    
    # Subplot 1: East spectrum
    ax1 = fig.add_subplot(4, 1, 1)
    ax1.semilogx(window_spec.frequencies, window_spec.east_spectrum, 'r-', linewidth=1.5)
    ax1.set_ylabel('East', fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.set_title(f'Window {window_spec.window_index} - Component Spectra', fontweight='bold')
    
    # Subplot 2: North spectrum
    ax2 = fig.add_subplot(4, 1, 2)
    ax2.semilogx(window_spec.frequencies, window_spec.north_spectrum, 'g-', linewidth=1.5)
    ax2.set_ylabel('North', fontsize=10)
    ax2.grid(True, alpha=0.3)
    
    # Subplot 3: Vertical spectrum
    ax3 = fig.add_subplot(4, 1, 3)
    ax3.semilogx(window_spec.frequencies, window_spec.vertical_spectrum, 'b-', linewidth=1.5)
    ax3.set_ylabel('Vertical', fontsize=10)
    ax3.grid(True, alpha=0.3)
    
    # Subplot 4: H/V ratio
    ax4 = fig.add_subplot(4, 1, 4)
    ax4.semilogx(window_spec.frequencies, window_spec.hvsr, 'k-', linewidth=2)
    ax4.set_ylabel('H/V Ratio', fontsize=10)
    ax4.set_xlabel('Frequency (Hz)', fontsize=10)
    ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    return fig


def plot_peak_analysis(peak: Peak,
                       frequencies: np.ndarray,
                       hvsr: np.ndarray,
                       ax: Optional[Axes] = None) -> Axes:
    """
    Detailed plot of a single peak with width and prominence.
    
    Args:
        peak: Peak object
        frequencies: Frequency array
        hvsr: HVSR curve
        ax: Matplotlib axes
        
    Returns:
        Matplotlib axes
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 6))
    
    # Plot HVSR curve
    ax.semilogx(frequencies, hvsr, 'b-', linewidth=2, label='H/V')
    
    # Mark peak
    ax.plot(peak.frequency, peak.amplitude, 'ro', markersize=12,
           markeredgecolor='black', markeredgewidth=2, label='Peak', zorder=5)
    
    # Show peak width
    if peak.left_freq > 0 and peak.right_freq > 0:
        half_height = peak.amplitude - peak.prominence / 2
        ax.hlines(half_height, peak.left_freq, peak.right_freq,
                 colors='orange', linestyles='--', linewidth=2,
                 label=f'Width = {peak.width:.2f} Hz')
        ax.plot([peak.left_freq, peak.right_freq], 
               [half_height, half_height],
               'o', color='orange', markersize=6)
    
    # Show prominence
    baseline = peak.amplitude - peak.prominence
    ax.vlines(peak.frequency, baseline, peak.amplitude,
             colors='green', linestyles=':', linewidth=2,
             label=f'Prominence = {peak.prominence:.2f}')
    
    # Annotations with smart positioning
    x_off, y_off, ha, va = _calculate_smart_annotation_position(
        peak.frequency, peak.amplitude, ax, 
        frequencies, hvsr
    )
    
    # Use LaTeX formatting for subscript to ensure proper rendering when saving
    ax.annotate(f'$f_0$ = {peak.frequency:.3f} Hz\n'
               f'A = {peak.amplitude:.2f}\n'
               f'Q = {peak.quality:.2f}',
               xy=(peak.frequency, peak.amplitude),
               xytext=(x_off, y_off), textcoords='offset points',
               bbox=dict(boxstyle='round,pad=0.7', fc='yellow', alpha=0.8),
               arrowprops=dict(arrowstyle='->', lw=2),
               fontsize=11, fontweight='bold',
               horizontalalignment=ha, verticalalignment=va)
    
    ax.set_xlabel('Frequency (Hz)', fontsize=12)
    ax.set_ylabel('H/V Ratio', fontsize=12)
    ax.set_title('Peak Analysis', fontsize=14, fontweight='bold')
    ax.grid(True, which='both', alpha=0.3)
    ax.legend(loc='best', fontsize=10)
    
    return ax


def plot_hvsr_statistics(result: HVSRResult,
                        fig: Optional[Figure] = None) -> Figure:
    """
    Multi-panel plot showing mean, median, std, and peaks.
    
    Args:
        result: HVSRResult object
        fig: Matplotlib figure
        
    Returns:
        Matplotlib figure
    """
    if fig is None:
        fig = plt.figure(figsize=(14, 10))
    
    # Panel 1: Median with uncertainty
    ax1 = fig.add_subplot(2, 2, 1)
    plot_hvsr_curve(result, ax=ax1, show_peaks=True, show_median=True, show_mean=False,
                   title='Median H/V with Uncertainty')
    
    # Panel 2: Mean vs Median
    ax2 = fig.add_subplot(2, 2, 2)
    ax2.semilogx(result.frequencies, result.mean_hvsr, 'b-', 
                linewidth=2, label='Mean')
    ax2.semilogx(result.frequencies, result.median_hvsr, 'g--',
                linewidth=2, label='Median')
    ax2.set_xlabel('Frequency (Hz)', fontsize=10)
    ax2.set_ylabel('H/V Ratio', fontsize=10)
    ax2.set_title('Mean vs Median', fontsize=12, fontweight='bold')
    ax2.grid(True, which='both', alpha=0.3)
    ax2.legend()
    
    # Panel 3: Standard deviation
    ax3 = fig.add_subplot(2, 2, 3)
    ax3.semilogx(result.frequencies, result.std_hvsr, 'r-', linewidth=2)
    ax3.fill_between(result.frequencies, 0, result.std_hvsr, alpha=0.3, color='red')
    ax3.set_xlabel('Frequency (Hz)', fontsize=10)
    ax3.set_ylabel('Standard Deviation', fontsize=10)
    ax3.set_title('H/V Variability', fontsize=12, fontweight='bold')
    ax3.grid(True, which='both', alpha=0.3)
    
    # Panel 4: Peak summary
    ax4 = fig.add_subplot(2, 2, 4)
    ax4.axis('off')
    
    # Create text summary
    summary_text = f"HVSR Analysis Summary\n{'='*40}\n\n"
    summary_text += f"Windows: {result.valid_windows}/{result.total_windows}\n"
    summary_text += f"Acceptance Rate: {result.acceptance_rate:.1%}\n\n"
    summary_text += f"Peaks Detected: {len(result.peaks)}\n\n"
    
    if result.peaks:
        summary_text += "Primary Peak:\n"
        peak = result.primary_peak
        summary_text += f"  Frequency: {peak.frequency:.3f} Hz\n"
        summary_text += f"  Amplitude: {peak.amplitude:.2f}\n"
        summary_text += f"  Prominence: {peak.prominence:.2f}\n"
        summary_text += f"  Width: {peak.width:.3f} Hz\n"
        summary_text += f"  Quality: {peak.quality:.2f}\n\n"
        
        if len(result.peaks) > 1:
            summary_text += f"Secondary Peaks:\n"
            for i, p in enumerate(result.peaks[1:4], 2):
                summary_text += f"  {i}. {p.frequency:.2f} Hz (A={p.amplitude:.2f})\n"
    else:
        summary_text += "No significant peaks detected\n"
    
    ax4.text(0.1, 0.9, summary_text, transform=ax4.transAxes,
            fontsize=11, verticalalignment='top', family='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.suptitle(f'HVSR Statistical Analysis', fontsize=16, fontweight='bold', y=0.98)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    
    return fig


def save_hvsr_plot(result: HVSRResult,
                  filepath: str,
                  plot_type: str = 'standard',
                  dpi: int = 150,
                  **kwargs) -> None:
    """
    Save HVSR plot to file.
    
    Args:
        result: HVSRResult object
        filepath: Output file path
        plot_type: 'standard', 'components', 'statistics'
        dpi: Resolution in dots per inch
        **kwargs: Additional kwargs for plot functions
    """
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    
    if plot_type == 'standard':
        fig, ax = plt.subplots(figsize=(10, 6))
        plot_hvsr_curve(result, ax=ax, **kwargs)
        
    elif plot_type == 'statistics':
        fig = plot_hvsr_statistics(result)
        
    elif plot_type == 'components':
        if not result.window_spectra:
            raise ValueError("No window spectra available")
        fig = plot_hvsr_components(result, window_index=kwargs.get('window_index', 0))
        
    else:
        raise ValueError(f"Unknown plot_type: {plot_type}")
    
    fig.savefig(filepath, dpi=dpi, bbox_inches='tight')
    plt.close(fig)
