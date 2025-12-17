"""
Window Visualization for HVSR Pro
==================================

Functions for plotting time series, spectrograms, and quality metrics.
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from matplotlib.patches import Rectangle
from typing import Optional, List, Tuple
from scipy import signal as scipy_signal

from hvsr_pro.processing.windows import Window, WindowCollection


def plot_window_time_series(window: Window,
                            ax: Optional[Axes] = None,
                            show_components: str = 'all') -> Axes:
    """
    Plot time series for a single window.
    
    Args:
        window: Window object
        ax: Matplotlib axes
        show_components: 'all', 'horizontal', 'vertical', 'east', 'north'
        
    Returns:
        Matplotlib axes
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(12, 6))
    
    sampling_rate = window.data.sampling_rate
    n_samples = window.data.n_samples
    time = np.arange(n_samples) / sampling_rate
    
    if show_components == 'all':
        ax.plot(time, window.data.east.data, 'r-', linewidth=0.8, label='East', alpha=0.7)
        ax.plot(time, window.data.north.data, 'g-', linewidth=0.8, label='North', alpha=0.7)
        ax.plot(time, window.data.vertical.data, 'b-', linewidth=0.8, label='Vertical', alpha=0.7)
    elif show_components == 'horizontal':
        ax.plot(time, window.data.east.data, 'r-', linewidth=1, label='East')
        ax.plot(time, window.data.north.data, 'g-', linewidth=1, label='North')
    elif show_components == 'vertical':
        ax.plot(time, window.data.vertical.data, 'b-', linewidth=1, label='Vertical')
    elif show_components == 'east':
        ax.plot(time, window.data.east.data, 'r-', linewidth=1, label='East')
    elif show_components == 'north':
        ax.plot(time, window.data.north.data, 'g-', linewidth=1, label='North')
    
    ax.set_xlabel('Time (s)', fontsize=11)
    ax.set_ylabel('Amplitude', fontsize=11)
    ax.set_title(f'Window {window.index} - Time Series '
                f'({"ACTIVE" if window.is_active() else "REJECTED"})',
                fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(loc='best')
    
    # Show window state
    if window.is_rejected():
        ax.text(0.02, 0.98, f'REJECTED: {window.rejection_reason}',
               transform=ax.transAxes, verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='red', alpha=0.5),
               fontsize=9, color='white', fontweight='bold')
    
    return ax


def plot_window_spectrogram(window: Window,
                            component: str = 'vertical',
                            ax: Optional[Axes] = None,
                            **kwargs) -> Axes:
    """
    Plot spectrogram for a window component.
    
    Args:
        window: Window object
        component: 'east', 'north', 'vertical'
        ax: Matplotlib axes
        **kwargs: Additional spectrogram parameters
        
    Returns:
        Matplotlib axes
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(12, 6))
    
    # Get component data
    if component == 'east':
        data = window.data.east.data
        color_label = 'East'
    elif component == 'north':
        data = window.data.north.data
        color_label = 'North'
    elif component == 'vertical':
        data = window.data.vertical.data
        color_label = 'Vertical'
    else:
        raise ValueError(f"Unknown component: {component}")
    
    sampling_rate = window.data.sampling_rate
    
    # Compute spectrogram
    nperseg = kwargs.pop('nperseg', min(256, len(data) // 8))
    noverlap = kwargs.pop('noverlap', nperseg // 2)
    
    f, t, Sxx = scipy_signal.spectrogram(data, fs=sampling_rate,
                                         nperseg=nperseg, noverlap=noverlap,
                                         **kwargs)
    
    # Plot
    pcm = ax.pcolormesh(t, f, 10 * np.log10(Sxx + 1e-20), 
                       shading='gouraud', cmap='viridis')
    
    ax.set_ylabel('Frequency (Hz)', fontsize=11)
    ax.set_xlabel('Time (s)', fontsize=11)
    ax.set_title(f'Window {window.index} - {color_label} Spectrogram',
                fontsize=12, fontweight='bold')
    ax.set_ylim(0, min(50, sampling_rate / 2))  # Limit to 50 Hz or Nyquist
    
    # Colorbar
    cbar = plt.colorbar(pcm, ax=ax)
    cbar.set_label('Power (dB)', fontsize=10)
    
    return ax


def plot_window_collection_overview(windows: WindowCollection,
                                    max_windows: int = 50,
                                    fig: Optional[Figure] = None) -> Figure:
    """
    Overview plot of window collection showing active/rejected.
    
    Args:
        windows: WindowCollection object
        max_windows: Maximum number of windows to show
        fig: Matplotlib figure
        
    Returns:
        Matplotlib figure
    """
    if fig is None:
        fig = plt.figure(figsize=(14, 8))
    
    n_show = min(max_windows, windows.n_windows)
    window_indices = np.linspace(0, windows.n_windows - 1, n_show, dtype=int)
    
    # Panel 1: Window status timeline
    ax1 = fig.add_subplot(3, 1, 1)
    
    active_idx = []
    rejected_idx = []
    
    for idx in window_indices:
        window = windows.windows[idx]
        if window.is_active():
            active_idx.append(idx)
        else:
            rejected_idx.append(idx)
    
    if active_idx:
        ax1.scatter(active_idx, [1] * len(active_idx), c='green', s=50,
                   marker='o', label=f'Active ({windows.n_active})', alpha=0.7)
    if rejected_idx:
        ax1.scatter(rejected_idx, [1] * len(rejected_idx), c='red', s=50,
                   marker='x', label=f'Rejected ({windows.n_rejected})', alpha=0.7)
    
    ax1.set_xlabel('Window Index', fontsize=10)
    ax1.set_ylabel('Status', fontsize=10)
    ax1.set_title(f'Window Collection Status ({windows.n_windows} windows)',
                 fontsize=12, fontweight='bold')
    ax1.set_yticks([])
    ax1.set_xlim(-1, windows.n_windows)
    ax1.legend(loc='best')
    ax1.grid(True, axis='x', alpha=0.3)
    
    # Panel 2: Quality metrics distribution
    ax2 = fig.add_subplot(3, 1, 2)
    
    quality_scores = []
    for window in windows.windows:
        if 'overall' in window.quality_metrics:
            quality_scores.append(window.quality_metrics['overall'])
    
    if quality_scores:
        ax2.hist(quality_scores, bins=30, color='blue', alpha=0.7, edgecolor='black')
        ax2.axvline(np.median(quality_scores), color='red', linestyle='--',
                   linewidth=2, label=f'Median = {np.median(quality_scores):.2f}')
        ax2.set_xlabel('Overall Quality Score', fontsize=10)
        ax2.set_ylabel('Count', fontsize=10)
        ax2.set_title('Quality Score Distribution', fontsize=12, fontweight='bold')
        ax2.legend()
        ax2.grid(True, alpha=0.3, axis='y')
    
    # Panel 3: Rejection reasons
    ax3 = fig.add_subplot(3, 1, 3)
    ax3.axis('off')
    
    rejection_counts = {}
    for window in windows.windows:
        if window.is_rejected() and window.rejection_reason:
            # Extract main reason (before first comma or parenthesis)
            reason = window.rejection_reason.split(',')[0].split('(')[0].strip()
            rejection_counts[reason] = rejection_counts.get(reason, 0) + 1
    
    if rejection_counts:
        reasons = list(rejection_counts.keys())
        counts = list(rejection_counts.values())
        
        # Sort by count
        sorted_pairs = sorted(zip(counts, reasons), reverse=True)
        counts, reasons = zip(*sorted_pairs)
        
        # Show top 10
        reasons = reasons[:10]
        counts = counts[:10]
        
        y_pos = np.arange(len(reasons))
        ax3_bar = fig.add_axes([0.1, 0.05, 0.85, 0.18])
        ax3_bar.barh(y_pos, counts, color='coral', edgecolor='black')
        ax3_bar.set_yticks(y_pos)
        ax3_bar.set_yticklabels(reasons, fontsize=9)
        ax3_bar.set_xlabel('Count', fontsize=10)
        ax3_bar.set_title('Rejection Reasons (Top 10)', fontsize=12, fontweight='bold')
        ax3_bar.grid(True, alpha=0.3, axis='x')
    else:
        ax3.text(0.5, 0.5, 'No rejections', transform=ax3.transAxes,
                ha='center', va='center', fontsize=14)
    
    plt.tight_layout()
    return fig


def plot_quality_metrics_grid(windows: WindowCollection,
                              metric_names: Optional[List[str]] = None,
                              max_windows: int = 100,
                              fig: Optional[Figure] = None) -> Figure:
    """
    Grid of quality metrics for window collection.
    
    Args:
        windows: WindowCollection object
        metric_names: List of metric names to plot (None = all)
        max_windows: Maximum windows to include
        fig: Matplotlib figure
        
    Returns:
        Matplotlib figure
    """
    # Get all available metrics
    all_metrics = set()
    for window in windows.windows[:max_windows]:
        all_metrics.update(window.quality_metrics.keys())
    
    if metric_names is None:
        metric_names = sorted(list(all_metrics))
    
    if not metric_names:
        raise ValueError("No quality metrics available")
    
    # Prepare data
    n_metrics = len(metric_names)
    n_rows = (n_metrics + 1) // 2
    
    if fig is None:
        fig = plt.figure(figsize=(14, 4 * n_rows))
    
    for i, metric_name in enumerate(metric_names, 1):
        ax = fig.add_subplot(n_rows, 2, i)
        
        # Extract metric values
        window_indices = []
        metric_values = []
        colors = []
        
        for window in windows.windows[:max_windows]:
            if metric_name in window.quality_metrics:
                window_indices.append(window.index)
                metric_values.append(window.quality_metrics[metric_name])
                colors.append('green' if window.is_active() else 'red')
        
        if metric_values:
            ax.scatter(window_indices, metric_values, c=colors, s=20, alpha=0.6)
            ax.axhline(np.median(metric_values), color='blue', linestyle='--',
                      linewidth=1.5, alpha=0.7, label=f'Median = {np.median(metric_values):.2f}')
            
            ax.set_xlabel('Window Index', fontsize=9)
            ax.set_ylabel(metric_name.replace('_', ' ').title(), fontsize=9)
            ax.set_title(f'{metric_name.replace("_", " ").title()}', fontsize=10, fontweight='bold')
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=8)
    
    plt.suptitle('Quality Metrics Overview', fontsize=14, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    
    return fig


def plot_window_comparison(windows: List[Window],
                           labels: Optional[List[str]] = None,
                           fig: Optional[Figure] = None) -> Figure:
    """
    Compare multiple windows side-by-side.
    
    Args:
        windows: List of Window objects
        labels: Labels for each window
        fig: Matplotlib figure
        
    Returns:
        Matplotlib figure
    """
    n_windows = len(windows)
    
    if labels is None:
        labels = [f'Window {w.index}' for w in windows]
    
    if fig is None:
        fig = plt.figure(figsize=(14, 3 * n_windows))
    
    for i, (window, label) in enumerate(zip(windows, labels), 1):
        # Time series
        ax = fig.add_subplot(n_windows, 1, i)
        plot_window_time_series(window, ax=ax, show_components='all')
        ax.set_title(label, fontsize=11, fontweight='bold')
    
    plt.tight_layout()
    return fig


def plot_rejection_timeline(windows: WindowCollection,
                           ax: Optional[Axes] = None) -> Axes:
    """
    Timeline showing when windows were rejected.
    
    Args:
        windows: WindowCollection object
        ax: Matplotlib axes
        
    Returns:
        Matplotlib axes
    """
    if ax is None:
        fig, ax = plt.subplots(figsize=(14, 6))
    
    # Calculate total duration from source data or windows
    if windows.windows:
        total_duration = windows.source_data.duration
    else:
        total_duration = 100  # Default if no windows
    
    # Create timeline
    for window in windows.windows:
        color = 'green' if window.is_active() else 'lightgray'
        alpha = 1.0 if window.is_active() else 0.3
        
        # Draw rectangle for window
        rect = Rectangle((window.start_time, 0), window.duration, 1,
                         facecolor=color, edgecolor='black',
                         linewidth=0.5, alpha=alpha)
        ax.add_patch(rect)
    
    ax.set_xlim(0, total_duration)
    ax.set_ylim(0, 1)
    ax.set_xlabel('Time (s)', fontsize=12)
    ax.set_ylabel('Windows', fontsize=12)
    ax.set_title(f'Window Rejection Timeline (Green=Active, Gray=Rejected)',
                fontsize=13, fontweight='bold')
    ax.set_yticks([])
    ax.grid(True, axis='x', alpha=0.3)
    
    # Add statistics
    stats_text = f'Active: {windows.n_active}/{windows.n_windows} ({windows.acceptance_rate:.1%})'
    ax.text(0.02, 0.95, stats_text, transform=ax.transAxes,
           verticalalignment='top', fontsize=10,
           bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.7))
    
    return ax
