"""
Publication-Quality Raw vs Adjusted HVSR Comparison Figure.

This module creates publication-quality dual-panel figures showing:
- Top panel: Raw HVSR results (all windows before rejection)
- Bottom panel: Adjusted HVSR results (accepted windows after rejection)

Each panel includes:
- Individual HVSR curves (with alpha transparency for many windows)
- Mean curve (solid black)
- +/- Standard deviation curves (dashed black)
- Gray shaded frequency uncertainty band
- Individual peak markers (asterisks)
- Mean peak marker (red circle)
- Statistics text box
- Compact legend (no individual window labels for large datasets)
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from matplotlib.lines import Line2D
from typing import Optional, Dict, Any, List, Tuple

# Style constants
AXIS_FONT_SIZE = 14
LEGEND_FONT_SIZE = 10
FONT_FAMILY = 'serif'
TITLE_FONT_SIZE = 22

# Maximum windows to show individual labels (above this, use summary)
MAX_LABELED_WINDOWS = 15

# Default style settings
DEFAULT_STYLE = {
    'individual_curve_linewidth': 0.8,
    'individual_curve_alpha': 0.5,  # Transparency for many windows
    'mean_curve_linewidth': 2.0,
    'std_curve_linewidth': 2.0,
    'peak_marker_size': 8,
    'mean_peak_marker_size': 10,
    'uncertainty_band_alpha': 0.2,
    'spine_linewidth': 1.75,
}


def plot_raw_vs_adjusted_hvsr(
    frequency: np.ndarray,
    hvsr_all_windows: np.ndarray,
    hvsr_accepted_windows: np.ndarray,
    window_indices_all: List[int],
    window_indices_accepted: List[int],
    peak_freq_all: np.ndarray,
    peak_amp_all: np.ndarray,
    station_name: str = "",
    freq_range: Optional[Tuple[float, float]] = None,
    legend_columns: int = 5,
    figsize: Tuple[float, float] = (12, 10),
    dpi: int = 150,
    save_path: Optional[str] = None,
    style: Optional[Dict[str, Any]] = None
) -> Figure:
    """
    Create MATLAB-style dual-panel HVSR comparison figure.
    
    This function creates a publication-quality figure with two subplots:
    - Top: Raw HVSR results (all windows before QC rejection)
    - Bottom: Adjusted HVSR results (only accepted windows)
    
    CRITICAL: Follow MATLAB code exactly for visual consistency:
    - Lines 901-990: Raw HVSR panel
    - Lines 993-1084: Adjusted HVSR panel
    
    Args:
        frequency: Frequency array (Hz), shape (n_freq,)
        hvsr_all_windows: HVSR values for all windows, shape (n_freq, n_windows)
        hvsr_accepted_windows: HVSR values for accepted windows, shape (n_freq, n_accepted)
        window_indices_all: List of window indices [0, 1, 2, ...] for labeling T1, T2...
        window_indices_accepted: List of indices for accepted windows
        peak_freq_all: Peak frequencies for all windows, shape (n_windows,)
        peak_amp_all: Peak amplitudes for all windows, shape (n_windows,)
        station_name: Station name/ID for title
        freq_range: Frequency range (f_min, f_max) for display, None for auto
        legend_columns: Number of columns in legend
        figsize: Figure size in inches (width, height)
        dpi: Figure DPI
        save_path: Path to save figure (optional)
        style: Custom style dictionary (optional)
        
    Returns:
        matplotlib Figure object
    """
    # Merge custom style with defaults
    plot_style = DEFAULT_STYLE.copy()
    if style:
        plot_style.update(style)
    
    # Create figure with two subplots
    fig, (ax_raw, ax_adj) = plt.subplots(2, 1, figsize=figsize, dpi=dpi)
    
    # Determine frequency range if not provided
    if freq_range is None:
        freq_range = (frequency[0], frequency[-1])
    
    # Calculate accepted mask for peak data
    accepted_mask = np.isin(window_indices_all, window_indices_accepted)
    peak_freq_accepted = peak_freq_all[accepted_mask]
    peak_amp_accepted = peak_amp_all[accepted_mask]
    
    # === TOP PANEL: All Computed HVSR ===
    _plot_hvsr_panel(
        ax=ax_raw,
        frequency=frequency,
        hvsr_windows=hvsr_all_windows,
        window_indices=window_indices_all,
        peak_freq=peak_freq_all,
        peak_amp=peak_amp_all,
        title="All Computed HVSR (before final QC)",
        freq_range=freq_range,
        legend_columns=legend_columns,
        style=plot_style
    )
    
    # === BOTTOM PANEL: Adjusted HVSR (after QC) ===
    _plot_hvsr_panel(
        ax=ax_adj,
        frequency=frequency,
        hvsr_windows=hvsr_accepted_windows,
        window_indices=window_indices_accepted,
        peak_freq=peak_freq_accepted,
        peak_amp=peak_amp_accepted,
        title="Accepted HVSR (after QC rejection)",
        freq_range=freq_range,
        legend_columns=legend_columns,
        style=plot_style
    )
    
    # Main title
    fig.suptitle(f'HVSR station {station_name}', fontsize=TITLE_FONT_SIZE, 
                 fontfamily=FONT_FAMILY, fontweight='bold')
    
    plt.tight_layout(rect=[0, 0, 0.85, 0.96])  # Leave space for legend
    
    if save_path:
        fig.savefig(save_path, dpi=dpi, bbox_inches='tight')
        print(f"Figure saved to: {save_path}")
    
    return fig


def _plot_hvsr_panel(
    ax: Axes,
    frequency: np.ndarray,
    hvsr_windows: np.ndarray,
    window_indices: List[int],
    peak_freq: np.ndarray,
    peak_amp: np.ndarray,
    title: str,
    freq_range: Tuple[float, float],
    legend_columns: int,
    style: Dict[str, Any],
    show_legend: bool = True
) -> None:
    """
    Plot single HVSR panel (used for both raw and adjusted).
    
    Args:
        ax: Matplotlib axes to plot on
        frequency: Frequency array
        hvsr_windows: HVSR values, shape (n_freq, n_windows)
        window_indices: Window indices for labeling
        peak_freq: Peak frequencies
        peak_amp: Peak amplitudes
        title: Panel title ("Raw HVSR results" or "Adjusted HVSR results")
        freq_range: Frequency range for display
        legend_columns: Number of columns in legend
        style: Style dictionary
        show_legend: Whether to show legend (default: True)
    """
    n_windows = hvsr_windows.shape[1] if hvsr_windows.ndim > 1 else 1
    
    # Handle single window case
    if hvsr_windows.ndim == 1:
        hvsr_windows = hvsr_windows.reshape(-1, 1)
    
    # Handle empty case
    if n_windows == 0:
        ax.text(0.5, 0.5, 'No windows', transform=ax.transAxes,
               ha='center', va='center', fontsize=14)
        return
    
    # Determine if we have many windows (use alpha and no individual labels)
    many_windows = n_windows > MAX_LABELED_WINDOWS
    
    # Get alpha value for curves
    curve_alpha = style.get('individual_curve_alpha', 0.5) if many_windows else 1.0
    
    # 1. Plot individual windows with colors
    if n_windows <= 20:
        colors = plt.cm.tab20(np.linspace(0, 1, max(n_windows, 1)))
    else:
        # Use a consistent color for all when many windows
        colors = plt.cm.viridis(np.linspace(0.3, 0.7, min(n_windows, 100)))
    
    for i in range(n_windows):
        if i < hvsr_windows.shape[1]:
            color = colors[i % len(colors)]
            # Only add label for first few windows if not too many
            label = None
            if not many_windows and i < MAX_LABELED_WINDOWS:
                idx = window_indices[i] if i < len(window_indices) else i
                label = f'T{idx+1}'
            ax.plot(frequency, hvsr_windows[:, i], 
                    color=color, 
                    linewidth=style['individual_curve_linewidth'],
                    alpha=curve_alpha,
                    label=label)
    
    # 2. Calculate and plot mean curve (solid black, linewidth=2)
    hv_mean = np.mean(hvsr_windows, axis=1)
    ax.plot(frequency, hv_mean, 'k-', 
            linewidth=style['mean_curve_linewidth'], 
            label='Mean', zorder=10)
    
    # 3. Calculate and plot +/- std curves (dashed black, linewidth=2)
    hv_std = np.std(hvsr_windows, axis=1)
    ax.plot(frequency, hv_mean + hv_std, 'k--', 
            linewidth=style['std_curve_linewidth'], 
            label='+1 Std', zorder=9)
    ax.plot(frequency, hv_mean - hv_std, 'k--', 
            linewidth=style['std_curve_linewidth'], 
            label='-1 Std', zorder=9)
    
    # 4. Plot individual peak markers (black asterisks)
    if len(peak_freq) > 0:
        ax.plot(peak_freq, peak_amp, 'k*', 
                markersize=style['peak_marker_size'], 
                label=r'$f_I$ (individual peaks)', zorder=11)
    
    # 5. Find and plot mean peak (red filled circle)
    freq_mask = (frequency >= freq_range[0]) & (frequency <= freq_range[1])
    if np.any(freq_mask):
        freq_subset = frequency[freq_mask]
        mean_subset = hv_mean[freq_mask]
        peak_idx = np.argmax(mean_subset)
        mean_peak_freq = freq_subset[peak_idx]
        mean_peak_amp = mean_subset[peak_idx]
    else:
        peak_idx = np.argmax(hv_mean)
        mean_peak_freq = frequency[peak_idx]
        mean_peak_amp = hv_mean[peak_idx]
    
    ax.plot(mean_peak_freq, mean_peak_amp, 'o', 
            markersize=style['mean_peak_marker_size'],
            markerfacecolor='red', 
            markeredgecolor='red',
            label=r'$f_0$ (mean peak)', zorder=12)
    
    # 6. Gray shaded frequency uncertainty band
    if len(peak_freq) > 0:
        freq_mean = np.mean(peak_freq)
        freq_std = np.std(peak_freq)
        
        # Get y limits for shading
        y_max = np.max(hvsr_windows) * 1.15
        
        # Draw uncertainty band
        ax.fill_betweenx([0, y_max], 
                        freq_mean - freq_std, 
                        freq_mean + freq_std,
                        color='gray', 
                        alpha=style['uncertainty_band_alpha'],
                        zorder=1,
                        label='Freq. uncertainty')
    else:
        freq_mean = mean_peak_freq
        freq_std = 0
        y_max = np.max(hvsr_windows) * 1.15
    
    # 7. Statistics text box (white background, black border)
    stats_text = (
        f'Windows shown = {n_windows}\n'
        f'Mean $f_0$ = {freq_mean:.2f} Hz\n'
        f'Mean amplitude = {mean_peak_amp:.1f}\n'
        f'$f_0$ std dev = {freq_std:.3f} Hz'
    )
    props = dict(boxstyle='round', facecolor='white', edgecolor='black', linewidth=1)
    ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=9,
            verticalalignment='top', bbox=props, fontfamily=FONT_FAMILY,
            zorder=15)
    
    # 8. Panel subtitle (top right)
    ax.text(0.98, 0.98, title, transform=ax.transAxes, fontsize=12,
            verticalalignment='top', horizontalalignment='right',
            fontweight='bold', fontfamily=FONT_FAMILY,
            bbox=dict(boxstyle='round', facecolor='white', edgecolor='none'),
            zorder=15)
    
    # 9. Axis formatting
    ax.set_xscale('log')
    ax.set_xlabel('Frequency (Hz)', fontsize=AXIS_FONT_SIZE, fontfamily=FONT_FAMILY)
    ax.set_ylabel('HVSR', fontsize=AXIS_FONT_SIZE, fontfamily=FONT_FAMILY)
    ax.tick_params(axis='both', which='both', direction='out', labelsize=AXIS_FONT_SIZE-2)
    ax.minorticks_on()
    
    # Set axis limits
    ax.set_xlim(freq_range)
    ax.set_ylim(0, y_max)
    
    # 10. Compact legend (only show key elements, not individual windows)
    if show_legend:
        # Create custom legend handles (no individual window labels)
        legend_handles = [
            Line2D([0], [0], color='gray', linewidth=1, alpha=0.7, label=f'Individual curves (n={n_windows})'),
            Line2D([0], [0], color='black', linewidth=2, label='Mean'),
            Line2D([0], [0], color='black', linewidth=2, linestyle='--', label='+/- 1 Std'),
            Line2D([0], [0], marker='*', color='black', linestyle='None', markersize=8, label='Individual peaks'),
            Line2D([0], [0], marker='o', color='red', linestyle='None', markersize=8, label='Mean peak ($f_0$)'),
            mpatches.Patch(color='gray', alpha=0.3, label='Freq. uncertainty'),
        ]
        ax.legend(handles=legend_handles, loc='center left', bbox_to_anchor=(1.02, 0.5),
                  fontsize=LEGEND_FONT_SIZE, frameon=True, fancybox=True)
    
    # Set spine linewidth
    for spine in ax.spines.values():
        spine.set_linewidth(style['spine_linewidth'])


def plot_raw_vs_adjusted_from_result(
    hvsr_result,
    windows,
    station_name: str = "",
    freq_range: Optional[Tuple[float, float]] = None,
    save_path: Optional[str] = None,
    **kwargs
) -> Figure:
    """
    Create Raw vs Adjusted figure directly from HVSRResult and WindowCollection.
    
    This shows:
    - Top panel: All computed HVSR spectra (before Cox FDWRA rejection)
    - Bottom panel: Only spectra from windows that are still active (passed all QC)
    
    Uses raw_window_spectra from result.metadata if available (stored before Cox FDWRA).
    
    Args:
        hvsr_result: HVSRResult object from processor
        windows: WindowCollection object
        station_name: Station name/ID
        freq_range: Frequency range for display
        save_path: Path to save figure
        **kwargs: Additional arguments passed to plot_raw_vs_adjusted_hvsr()
        
    Returns:
        matplotlib Figure object
    """
    # Extract frequency array
    frequency = hvsr_result.frequencies
    
    # Get counts
    total_windows = len(windows.windows) if windows else 0
    n_currently_active = sum(1 for w in windows.windows if w.is_active()) if windows else 0
    
    # Build set of active window indices for quick lookup
    active_window_indices = set()
    for i, w in enumerate(windows.windows):
        if w.is_active():
            active_window_indices.add(i)
    
    # Check if we have raw spectra stored before Cox FDWRA
    raw_spectra = hvsr_result.metadata.get('raw_window_spectra', None)
    if raw_spectra is None:
        # No raw spectra stored, use current window_spectra for both panels
        raw_spectra = hvsr_result.window_spectra
    
    # Collect all computed spectra (for top "Raw/Computed" panel)
    # Use raw_spectra which contains spectra BEFORE Cox FDWRA rejection
    all_hvsr = []
    all_indices = []
    all_peak_freq = []
    all_peak_amp = []
    
    for i, spectrum in enumerate(raw_spectra):
        hvsr_curve = spectrum.hvsr
        win_idx = spectrum.window_index if spectrum.window_index is not None else i
        
        all_hvsr.append(hvsr_curve)
        all_indices.append(win_idx)
        
        peak_idx = np.argmax(hvsr_curve)
        peak_f = frequency[peak_idx]
        peak_a = hvsr_curve[peak_idx]
        all_peak_freq.append(peak_f)
        all_peak_amp.append(peak_a)
    
    # Collect accepted spectra (for bottom "Adjusted" panel)
    # Use current window_spectra which only contains active windows
    accepted_hvsr = []
    accepted_indices = []
    accepted_peak_freq = []
    accepted_peak_amp = []
    
    for i, spectrum in enumerate(hvsr_result.window_spectra):
        hvsr_curve = spectrum.hvsr
        win_idx = spectrum.window_index if spectrum.window_index is not None else i
        
        # Only include if window is still active
        if win_idx in active_window_indices:
            accepted_hvsr.append(hvsr_curve)
            accepted_indices.append(win_idx)
            
            peak_idx = np.argmax(hvsr_curve)
            accepted_peak_freq.append(frequency[peak_idx])
            accepted_peak_amp.append(hvsr_curve[peak_idx])
    
    # Convert to numpy arrays
    hvsr_all_windows = np.column_stack(all_hvsr) if all_hvsr else np.array([]).reshape(len(frequency), 0)
    hvsr_accepted_windows = np.column_stack(accepted_hvsr) if accepted_hvsr else np.array([]).reshape(len(frequency), 0)
    peak_freq_all = np.array(all_peak_freq)
    peak_amp_all = np.array(all_peak_amp)
    
    # Build informative station title
    n_computed = len(all_hvsr)
    n_accepted = len(accepted_hvsr)
    n_rejected_total = total_windows - n_currently_active
    
    station_info = f"{station_name}" if station_name else "HVSR Station"
    station_info += f"\n[Total: {total_windows} | Computed: {n_computed} | Accepted: {n_accepted} | Rejected: {n_rejected_total}]"
    
    # Call main plotting function
    return plot_raw_vs_adjusted_hvsr(
        frequency=frequency,
        hvsr_all_windows=hvsr_all_windows,
        hvsr_accepted_windows=hvsr_accepted_windows,
        window_indices_all=all_indices,
        window_indices_accepted=accepted_indices,
        peak_freq_all=peak_freq_all,
        peak_amp_all=peak_amp_all,
        station_name=station_info,
        freq_range=freq_range,
        save_path=save_path,
        **kwargs
    )


# Alias for backward compatibility
create_comparison_figure = plot_raw_vs_adjusted_hvsr

