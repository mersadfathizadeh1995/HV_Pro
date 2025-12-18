"""
3-Component Seismic Waveform Plotting with Rejection Markers.

Reference: hvsrpy/postprocessing.py - plot_seismic_recordings_3c()

This module creates waveform plots showing:
- North-South (NS) component
- East-West (EW) component  
- Vertical (VT/Z) component

With window rejection markers to visualize which time windows were
accepted or rejected during quality control.
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from matplotlib.patches import Rectangle
from matplotlib.collections import PatchCollection
from typing import Optional, Dict, Any, List, Tuple, Union

# Style constants (defaults - can be overridden in function calls)
AXIS_FONT_SIZE = 10
TITLE_FONT_SIZE = 11
SUPTITLE_FONT_SIZE = 14
FONT_FAMILY = 'serif'

# Default style settings
DEFAULT_STYLE = {
    'accepted_color': '#888888',  # Gray for accepted windows
    'rejected_color': 'lightpink',  # Light pink for rejected windows
    'accepted_linewidth': 0.5,
    'rejected_linewidth': 0.5,
    'window_boundary_color': '#cccccc',
    'window_boundary_alpha': 0.3,
}


def plot_seismic_recordings_3c(
    data,
    windows=None,
    valid_mask: Optional[np.ndarray] = None,
    normalize: bool = True,
    figsize: Tuple[float, float] = (10, 8),
    dpi: int = 150,
    save_path: Optional[str] = None,
    style: Optional[Dict[str, Any]] = None,
    title: str = "3-Component Seismic Recording",
    title_fontsize: int = TITLE_FONT_SIZE,
    axis_fontsize: int = AXIS_FONT_SIZE,
    suptitle_fontsize: int = SUPTITLE_FONT_SIZE,
    hspace: float = 0.25
) -> Figure:
    """
    Plot 3-component seismic recording with optional window rejection markers.
    
    This creates a publication-quality figure with three subplots showing
    the North-South, East-West, and Vertical components, with optional
    highlighting of accepted/rejected windows.
    
    Args:
        data: SeismicData object with east, north, vertical components
        windows: Optional WindowCollection for rejection visualization
        valid_mask: Boolean array indicating valid (True) or rejected (False) windows
                   If windows is provided, this is extracted automatically
        normalize: Whether to normalize amplitudes (default: True)
        figsize: Figure size in inches
        dpi: Figure DPI
        save_path: Path to save figure (optional)
        style: Custom style dictionary (optional)
        title: Figure title
        title_fontsize: Font size for subplot titles
        axis_fontsize: Font size for axis labels
        suptitle_fontsize: Font size for main figure title
        hspace: Vertical spacing between subplots
        
    Returns:
        matplotlib Figure object
    """
    # Merge custom style with defaults
    plot_style = DEFAULT_STYLE.copy()
    if style:
        plot_style.update(style)
    
    # Extract valid mask from windows if not provided
    if valid_mask is None and windows is not None:
        valid_mask = np.array([w.is_active() for w in windows.windows])
    
    # Create figure with 3 subplots
    fig, axs = plt.subplots(3, 1, figsize=figsize, dpi=dpi, 
                           sharex=True, sharey=True,
                           gridspec_kw={'hspace': hspace})
    
    # Get component data
    components = [
        ('north', 'NS Recording', data.north),
        ('east', 'EW Recording', data.east),
        ('vertical', 'VT Recording', data.vertical),
    ]
    
    # Calculate normalization factor
    if normalize:
        max_amplitude = 0
        for name, label, component in components:
            comp_max = np.max(np.abs(component.data))
            if comp_max > max_amplitude:
                max_amplitude = comp_max
        normalization_factor = max_amplitude if max_amplitude > 0 else 1.0
    else:
        normalization_factor = 1.0
    
    # Get time array
    sampling_rate = data.sampling_rate
    n_samples = len(data.vertical.data)
    time = np.arange(n_samples) / sampling_rate
    
    # Plot each component
    for ax, (name, label, component) in zip(axs, components):
        amplitude = component.data / normalization_factor
        
        # If we have window information, plot with rejection markers
        if windows is not None and valid_mask is not None:
            _plot_with_windows(ax, time, amplitude, windows, valid_mask, plot_style)
        else:
            ax.plot(time, amplitude, color=plot_style['accepted_color'],
                   linewidth=plot_style['accepted_linewidth'])
        
        ax.set_title(label, fontsize=title_fontsize, fontfamily=FONT_FAMILY)
        ax.set_ylabel('Normalized\nAmplitude' if normalize else 'Amplitude\n(counts)',
                     fontsize=axis_fontsize, fontfamily=FONT_FAMILY)
        
        # Remove top and right spines
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        # Set y limits
        if normalize:
            ax.set_ylim(-1.1, 1.1)
    
    # Set x label on bottom subplot only
    axs[-1].set_xlabel('Time (s)', fontsize=axis_fontsize, fontfamily=FONT_FAMILY)
    axs[-1].set_xlim(0, time[-1])
    
    # Add main title
    fig.suptitle(title, fontsize=suptitle_fontsize, fontfamily=FONT_FAMILY, fontweight='bold')
    
    plt.tight_layout(rect=[0, 0, 1, 0.95])
    
    if save_path:
        fig.savefig(save_path, dpi=dpi, bbox_inches='tight')
        print(f"Figure saved to: {save_path}")
    
    return fig


def _plot_with_windows(
    ax: Axes,
    time: np.ndarray,
    amplitude: np.ndarray,
    windows,
    valid_mask: np.ndarray,
    style: Dict[str, Any]
) -> None:
    """
    Plot waveform with window-wise coloring based on rejection status.
    
    Args:
        ax: Matplotlib axes
        time: Time array
        amplitude: Amplitude array
        windows: WindowCollection
        valid_mask: Boolean array of window validity
        style: Style dictionary
    """
    # Get window parameters
    if len(windows.windows) == 0:
        ax.plot(time, amplitude, color=style['accepted_color'],
               linewidth=style['accepted_linewidth'])
        return
    
    # Calculate window boundaries in samples
    window_length_samples = windows.windows[0].n_samples
    
    # Get overlap from window manager if available
    # Estimate step from first two windows if possible
    if len(windows.windows) >= 2:
        step_samples = windows.windows[1].start_sample - windows.windows[0].start_sample
    else:
        step_samples = window_length_samples  # Assume no overlap
    
    sampling_rate = len(time) / (time[-1] - time[0]) if time[-1] > time[0] else 1.0
    
    # Plot each window segment
    for i, (window, is_valid) in enumerate(zip(windows.windows, valid_mask)):
        start_sample = window.start_sample
        end_sample = window.end_sample
        
        # Clip to valid range
        start_sample = max(0, start_sample)
        end_sample = min(len(amplitude), end_sample)
        
        if start_sample >= end_sample:
            continue
        
        # Get segment
        time_segment = time[start_sample:end_sample]
        amp_segment = amplitude[start_sample:end_sample]
        
        # Choose color based on validity
        if is_valid:
            color = style['accepted_color']
            linewidth = style['accepted_linewidth']
        else:
            color = style['rejected_color']
            linewidth = style['rejected_linewidth']
        
        ax.plot(time_segment, amp_segment, color=color, linewidth=linewidth)
    
    # Add window boundary markers
    for window in windows.windows:
        start_time = window.start_sample / sampling_rate
        ax.axvline(x=start_time, color=style['window_boundary_color'],
                  alpha=style['window_boundary_alpha'], linewidth=0.5, linestyle=':')


def plot_pre_and_post_rejection(
    data,
    hvsr_result,
    windows,
    station_name: str = "",
    figsize: Tuple[float, float] = (14, 11),
    dpi: int = 150,
    save_path: Optional[str] = None,
    distribution_mc: str = "lognormal",
    distribution_fn: str = "lognormal",
    title_fontsize: int = 11,
    axis_fontsize: int = 10,
    suptitle_fontsize: int = 14,
    hspace: float = 0.5,
    wspace: float = 0.5
) -> Figure:
    """
    Create a comprehensive pre- and post-rejection figure.
    
    This creates a 5-panel figure:
    - Left column: 3 waveform plots (NS, EW, VT) with rejection markers
    - Right top: HVSR curves before rejection
    - Right bottom: HVSR curves after rejection
    
    Args:
        data: SeismicData object
        hvsr_result: HVSRResult object
        windows: WindowCollection object
        station_name: Station name for title
        figsize: Figure size
        dpi: Figure DPI
        save_path: Path to save figure
        distribution_mc: Distribution for mean curve ("lognormal" or "normal")
        distribution_fn: Distribution for fn ("lognormal" or "normal")
        title_fontsize: Font size for subplot titles
        axis_fontsize: Font size for axis labels
        suptitle_fontsize: Font size for main figure title
        hspace: Vertical spacing between subplots
        wspace: Horizontal spacing between subplots
        
    Returns:
        matplotlib Figure object
    """
    from .comparison_plot import _plot_hvsr_panel, DEFAULT_STYLE as HVSR_STYLE
    
    fig = plt.figure(figsize=figsize, dpi=dpi)
    gs = fig.add_gridspec(nrows=6, ncols=6, hspace=hspace, wspace=wspace)
    
    # Left column: Waveforms
    ax_ns = fig.add_subplot(gs[0:2, 0:3])
    ax_ew = fig.add_subplot(gs[2:4, 0:3])
    ax_vt = fig.add_subplot(gs[4:6, 0:3])
    
    # Right column: HVSR plots
    ax_pre = fig.add_subplot(gs[0:3, 3:6])
    ax_post = fig.add_subplot(gs[3:6, 3:6])
    
    # Get number of window spectra (this is the authoritative count)
    n_spectra = len(hvsr_result.window_spectra)
    n_windows = len(windows.windows) if windows else 0
    
    # Create valid mask matching the window_spectra count
    # Use the minimum of n_windows and n_spectra to avoid index errors
    n_match = min(n_windows, n_spectra)
    if n_windows > 0:
        valid_mask_full = np.array([w.is_active() for w in windows.windows])
        # Truncate or extend to match spectra count
        if n_match < n_spectra:
            # Extend with True (assume extra spectra are valid)
            valid_mask = np.ones(n_spectra, dtype=bool)
            valid_mask[:n_match] = valid_mask_full[:n_match]
        else:
            # Truncate to match
            valid_mask = valid_mask_full[:n_spectra]
    else:
        valid_mask = np.ones(n_spectra, dtype=bool)
    
    # Plot waveforms (use full window mask for waveforms)
    if n_windows > 0:
        waveform_mask = np.array([w.is_active() for w in windows.windows])
        _plot_waveform_component(ax_ns, data.north, data.sampling_rate, windows, waveform_mask, 'NS Recording',
                                  title_fontsize=title_fontsize, axis_fontsize=axis_fontsize)
        _plot_waveform_component(ax_ew, data.east, data.sampling_rate, windows, waveform_mask, 'EW Recording',
                                  title_fontsize=title_fontsize, axis_fontsize=axis_fontsize)
        _plot_waveform_component(ax_vt, data.vertical, data.sampling_rate, windows, waveform_mask, 'VT Recording',
                                  title_fontsize=title_fontsize, axis_fontsize=axis_fontsize)
    else:
        # No windows, just plot the raw data
        sampling_rate = data.sampling_rate
        time = np.arange(len(data.vertical.data)) / sampling_rate
        for ax, comp_data, title in [(ax_ns, data.north.data, 'NS'), (ax_ew, data.east.data, 'EW'), (ax_vt, data.vertical.data, 'VT')]:
            ax.plot(time, comp_data / np.max(np.abs(comp_data)), color=DEFAULT_STYLE['accepted_color'], linewidth=0.5)
            ax.set_title(f'{title} Recording', fontsize=title_fontsize)
            ax.set_ylabel('Normalized\nAmplitude', fontsize=axis_fontsize)
    
    ax_vt.set_xlabel('Time (s)', fontsize=axis_fontsize)
    
    # Extract HVSR data for plotting
    frequency = hvsr_result.frequencies
    all_hvsr = np.column_stack([s.hvsr for s in hvsr_result.window_spectra])
    
    # Calculate peaks
    peak_freq = []
    peak_amp = []
    for spectrum in hvsr_result.window_spectra:
        peak_idx = np.argmax(spectrum.hvsr)
        peak_freq.append(frequency[peak_idx])
        peak_amp.append(spectrum.hvsr[peak_idx])
    peak_freq = np.array(peak_freq)
    peak_amp = np.array(peak_amp)
    
    # Pre-rejection: Use all windows
    _plot_hvsr_panel(
        ax=ax_pre,
        frequency=frequency,
        hvsr_windows=all_hvsr,
        window_indices=list(range(n_spectra)),
        peak_freq=peak_freq,
        peak_amp=peak_amp,
        title="Before Rejection",
        freq_range=(frequency[0], frequency[-1]),
        legend_columns=1,
        style=HVSR_STYLE,
        show_legend=False
    )
    
    # Post-rejection: Use only accepted windows
    # valid_mask now correctly matches n_spectra
    accepted_indices = [i for i in range(n_spectra) if valid_mask[i]]
    
    if accepted_indices:
        accepted_hvsr = all_hvsr[:, accepted_indices]
        accepted_peak_freq = peak_freq[accepted_indices]
        accepted_peak_amp = peak_amp[accepted_indices]
    else:
        # No accepted windows - show empty or all
        accepted_hvsr = all_hvsr
        accepted_peak_freq = peak_freq
        accepted_peak_amp = peak_amp
        accepted_indices = list(range(n_spectra))
    
    _plot_hvsr_panel(
        ax=ax_post,
        frequency=frequency,
        hvsr_windows=accepted_hvsr,
        window_indices=accepted_indices,
        peak_freq=accepted_peak_freq,
        peak_amp=accepted_peak_amp,
        title="After Rejection",
        freq_range=(frequency[0], frequency[-1]),
        legend_columns=1,
        style=HVSR_STYLE,
        show_legend=False
    )
    
    # Add lettering
    for ax, letter in zip([ax_ns, ax_pre, ax_ew, ax_post, ax_vt], 'abcde'):
        text = ax.text(0.02, 0.97, f'({letter})', transform=ax.transAxes,
                      fontsize=12, fontweight='bold', va='top')
        text.set_bbox(dict(facecolor='white', edgecolor='none', boxstyle='round', pad=0.15))
    
    # Main title
    title_str = f'HVSR Analysis - {station_name}' if station_name else 'HVSR Analysis'
    n_rejected = n_spectra - len(accepted_indices)
    title_str += f'\n({n_spectra} windows, {n_rejected} rejected)'
    fig.suptitle(title_str, fontsize=suptitle_fontsize, fontweight='bold', fontfamily=FONT_FAMILY)
    
    # Use tighter layout with more room for title and legend
    plt.tight_layout(rect=[0, 0.06, 1, 0.92])
    
    # Add legend at bottom
    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], color=DEFAULT_STYLE['accepted_color'], linewidth=2, label='Accepted Windows'),
        Line2D([0], [0], color=DEFAULT_STYLE['rejected_color'], linewidth=2, label='Rejected Windows'),
        Line2D([0], [0], color='black', linewidth=2, label='Mean HVSR'),
        Line2D([0], [0], color='black', linewidth=2, linestyle='--', label='+/- 1 Std'),
    ]
    fig.legend(handles=legend_elements, loc='lower center', ncol=4, fontsize=10,
              bbox_to_anchor=(0.5, 0.01))
    
    if save_path:
        fig.savefig(save_path, dpi=dpi, bbox_inches='tight')
        print(f"Figure saved to: {save_path}")
    
    return fig


def _plot_waveform_component(
    ax: Axes,
    component,
    sampling_rate: float,
    windows,
    valid_mask: np.ndarray,
    title: str,
    title_fontsize: int = TITLE_FONT_SIZE,
    axis_fontsize: int = AXIS_FONT_SIZE
) -> None:
    """Plot a single waveform component with rejection markers.
    
    Args:
        ax: Matplotlib axes
        component: Component data object
        sampling_rate: Sampling rate in Hz
        windows: WindowCollection
        valid_mask: Boolean array of window validity
        title: Subplot title
        title_fontsize: Font size for title
        axis_fontsize: Font size for axis labels
    """
    # Get data
    amplitude = component.data
    n_samples = len(amplitude)
    time = np.arange(n_samples) / sampling_rate
    
    # Normalize
    max_amp = np.max(np.abs(amplitude))
    if max_amp > 0:
        amplitude = amplitude / max_amp
    
    # Plot with window coloring
    _plot_with_windows(ax, time, amplitude, windows, valid_mask, DEFAULT_STYLE)
    
    ax.set_title(title, fontsize=title_fontsize, fontfamily=FONT_FAMILY)
    ax.set_ylabel('Normalized\nAmplitude', fontsize=axis_fontsize)
    ax.set_xlim(0, time[-1])
    ax.set_ylim(-1.1, 1.1)
    
    for spine in ['top', 'right']:
        ax.spines[spine].set_visible(False)

