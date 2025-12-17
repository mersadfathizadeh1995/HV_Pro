"""
Azimuthal HVSR Plotting Functions
=================================

3D and 2D visualization for azimuthal HVSR analysis.
Adapted from hvsrpy by Joseph P. Vantassel (joseph.p.vantassel@gmail.com).
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.colors import Normalize
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.axes_grid1 import make_axes_locatable
from typing import Tuple, Optional, Dict, Any

from .azimuthal_result import AzimuthalHVSRResult

__all__ = [
    "plot_azimuthal_contour_2d",
    "plot_azimuthal_contour_3d",
    "plot_azimuthal_summary",
    "DEFAULT_AZIMUTHAL_KWARGS"
]


# Default plot styling
DEFAULT_AZIMUTHAL_KWARGS = {
    "individual_curve": {
        "linewidth": 0.3,
        "color": "#888888",
        "label": "Individual Curve",
    },
    "mean_curve": {
        "linewidth": 1.3,
        "color": "black",
        "label": "Mean Curve",
    },
    "std_curve": {
        "linewidth": 1.3,
        "color": "black",
        "linestyle": "--",
        "label": "Mean +/- 1 Std",
    },
    "peak_marker": {
        "marker": "s",
        "s": 16,
        "c": "lightgreen",
        "edgecolors": "black",
        "zorder": 4,
        "label": "Peak by Azimuth",
    },
    "peak_marker_2d": {
        "linestyle": "",
        "marker": "s",
        "markersize": 4,
        "markerfacecolor": "lightgreen",
        "markeredgewidth": 1,
        "markeredgecolor": "black",
        "zorder": 4,
        "label": "Peak by Azimuth",
    },
}


def plot_azimuthal_contour_2d(result: AzimuthalHVSRResult,
                              distribution_mc: str = "lognormal",
                              plot_mean_curve_peak_by_azimuth: bool = True,
                              fig: plt.Figure = None,
                              ax: plt.Axes = None,
                              subplots_kwargs: Dict = None,
                              contourf_kwargs: Dict = None,
                              cmap: str = "plasma") -> Tuple[plt.Figure, Tuple[plt.Axes, plt.Axes]]:
    """
    Create 2D contour plot of HVSR amplitude vs frequency and azimuth.
    
    Args:
        result: AzimuthalHVSRResult object
        distribution_mc: Distribution for mean curve ('lognormal' or 'normal')
        plot_mean_curve_peak_by_azimuth: Plot peak markers for each azimuth
        fig: Existing figure (optional)
        ax: Existing axes (optional)
        subplots_kwargs: Arguments for plt.subplots()
        contourf_kwargs: Arguments for ax.contourf()
        cmap: Colormap name
        
    Returns:
        (figure, (ax, colorbar_ax))
    """
    # Get mesh data
    mesh_freq, mesh_azi, mesh_amp = result.to_mesh(distribution_mc)
    
    # Create figure if needed
    ax_was_none = ax is None
    if ax is None:
        default_subplots_kwargs = dict(figsize=(6, 4), dpi=150)
        if subplots_kwargs:
            default_subplots_kwargs.update(subplots_kwargs)
        fig, ax = plt.subplots(**default_subplots_kwargs)
    
    # Default contourf settings
    default_contourf_kwargs = dict(cmap=cm.get_cmap(cmap), levels=15)
    if contourf_kwargs:
        default_contourf_kwargs.update(contourf_kwargs)
    
    # Plot contour
    contour = ax.contourf(mesh_freq, mesh_azi, mesh_amp, **default_contourf_kwargs)
    
    # Format axes
    ax.set_xscale("log")
    ax.set_xlim(result.frequencies[0], result.frequencies[-1])
    ax.set_xlabel("Frequency (Hz)")
    ax.set_ylabel("Azimuth (deg)")
    ax.set_yticks(np.arange(0, 180 + 30, 30))
    ax.set_ylim(0, 180)
    
    # Add colorbar
    divider = make_axes_locatable(ax)
    cax = divider.append_axes("top", size="5%", pad=0.05)
    
    # Determine colorbar ticks
    max_amp = np.max(mesh_amp)
    if max_amp < 6.5:
        ticks = np.arange(0, 7, 1)
    elif max_amp < 14:
        ticks = np.arange(0, 16, 2)
    else:
        ticks = np.arange(0, (max_amp // 5 + 1) * 5, 5)
    
    cbar = plt.colorbar(contour, cax=cax, orientation="horizontal", ticks=ticks)
    cax.xaxis.set_ticks_position("top")
    cax.set_xlabel("HVSR Amplitude", labelpad=5)
    
    # Plot peak markers
    if plot_mean_curve_peak_by_azimuth:
        peak_freqs, _ = result.mean_curve_peak_by_azimuth(distribution_mc)
        ax.plot(peak_freqs, result.azimuths, 
                **DEFAULT_AZIMUTHAL_KWARGS["peak_marker_2d"])
        # Position legend in lower right corner, away from data
        ax.legend(loc="lower right", fontsize=7, framealpha=0.9,
                 edgecolor='gray', fancybox=True)
    
    if ax_was_none:
        fig.tight_layout(rect=[0, 0, 1, 0.95])  # Leave room for colorbar
    
    return (fig, (ax, cax))


def plot_azimuthal_contour_3d(result: AzimuthalHVSRResult,
                              distribution_mc: str = "lognormal",
                              plot_mean_curve_peak_by_azimuth: bool = True,
                              ax: Axes3D = None,
                              camera_elevation: float = 35,
                              camera_azimuth: float = 250,
                              camera_distance: float = 13,
                              cmap: str = "plasma") -> Tuple[plt.Figure, Axes3D]:
    """
    Create 3D surface plot of HVSR amplitude vs frequency and azimuth.
    
    Args:
        result: AzimuthalHVSRResult object
        distribution_mc: Distribution for mean curve
        plot_mean_curve_peak_by_azimuth: Plot peak markers
        ax: Existing 3D axes (optional)
        camera_elevation: Camera elevation angle
        camera_azimuth: Camera azimuth angle
        camera_distance: Camera distance
        cmap: Colormap name
        
    Returns:
        (figure, axes)
    """
    # Get mesh data
    mesh_freq, mesh_azi, mesh_amp = result.to_mesh(distribution_mc)
    
    # Create figure/axes if needed
    ax_was_none = ax is None
    if ax is None:
        fig = plt.figure(figsize=(6, 5), dpi=150)
        ax = fig.add_subplot(projection="3d")
    else:
        fig = ax.get_figure()
    
    # Plot 3D surface (use log of frequency for better visualization)
    surf = ax.plot_surface(
        np.log10(mesh_freq), mesh_azi, mesh_amp,
        rstride=1, cstride=1,
        cmap=cm.get_cmap(cmap),
        linewidth=0,
        antialiased=True,
        alpha=0.9
    )
    
    # Format axes panes
    for coord in ['x', 'y', 'z']:
        getattr(ax, f"{coord}axis").pane.fill = False
        getattr(ax, f"{coord}axis").pane.set_edgecolor('white')
    
    # X-axis (frequency - log scale)
    ax.set_xticks(np.log10(np.array([0.1, 1, 10, 100])))
    ax.set_xticklabels(["0.1", "1", "10", "100"])
    ax.set_xlim(np.log10((result.frequencies[0], result.frequencies[-1])))
    ax.set_xlabel("Frequency (Hz)")
    
    # Y-axis (azimuth)
    ax.set_yticks(np.arange(0, 180 + 45, 45))
    ax.set_ylim(0, 180)
    ax.set_ylabel("Azimuth (deg)")
    
    # Z-axis (amplitude)
    ax.set_zlabel("HVSR Amplitude")
    
    # Set camera position
    ax.view_init(elev=camera_elevation, azim=camera_azimuth)
    ax.dist = camera_distance
    
    # Plot peak markers
    if plot_mean_curve_peak_by_azimuth:
        peak_freqs, peak_amps = result.mean_curve_peak_by_azimuth(distribution_mc)
        # Extend to wrap around
        peak_freqs_ext = np.append(peak_freqs, peak_freqs[0])
        peak_amps_ext = np.append(peak_amps, peak_amps[0])
        azimuths_ext = np.append(result.azimuths, 180.0)
        
        ax.scatter(
            np.log10(peak_freqs_ext), azimuths_ext, peak_amps_ext * 1.05,
            **DEFAULT_AZIMUTHAL_KWARGS["peak_marker"]
        )
        # Position legend in upper left, outside the 3D view area
        ax.legend(bbox_to_anchor=(0.0, 1.0), loc='upper left', fontsize=7,
                 framealpha=0.9, edgecolor='gray', fancybox=True)
    
    if ax_was_none:
        fig.tight_layout()
        fig.subplots_adjust(right=0.92)  # Make room for any overflow
    
    return (fig, ax)


def plot_azimuthal_summary(result: AzimuthalHVSRResult,
                           distribution_mc: str = "lognormal",
                           distribution_fn: str = "lognormal",
                           plot_mean_curve_peak_by_azimuth: bool = True,
                           plot_individual_curves: bool = True,
                           figsize: Tuple[float, float] = (12, 8),
                           dpi: int = 150,
                           legend_loc: str = "outside_right",
                           cmap: str = "plasma",
                           show_panel_labels: bool = True) -> Tuple[plt.Figure, Tuple[Axes3D, plt.Axes, plt.Axes]]:
    """
    Create comprehensive summary figure with 3D surface, 2D contour, and HVSR curves.
    
    Layout:
    - Top-left: 3D surface plot
    - Top-right: 2D contour plot  
    - Bottom: Traditional HVSR curves for each azimuth
    
    Args:
        result: AzimuthalHVSRResult object
        distribution_mc: Distribution for mean curve
        distribution_fn: Distribution for fundamental frequency
        plot_mean_curve_peak_by_azimuth: Show peak markers
        plot_individual_curves: Show individual azimuth curves in bottom panel
        figsize: Figure size
        dpi: DPI for figure
        legend_loc: Legend location ('outside_right', 'outside_bottom', 'upper_right', 'none')
        cmap: Colormap name for individual curves
        show_panel_labels: Whether to show (a), (b), (c) labels
        
    Returns:
        (figure, (ax_3d, ax_2d, ax_curves))
    """
    # Create figure with custom gridspec - add space for legend on right
    fig = plt.figure(figsize=figsize, dpi=dpi)
    
    # Adjust gridspec based on legend location
    if legend_loc == "outside_right":
        gs = fig.add_gridspec(nrows=4, ncols=2, wspace=0.35, hspace=0.35, 
                              width_ratios=(1.2, 0.8),
                              left=0.08, right=0.82, top=0.92, bottom=0.08)
    elif legend_loc == "outside_bottom":
        gs = fig.add_gridspec(nrows=4, ncols=2, wspace=0.3, hspace=0.4, 
                              width_ratios=(1.2, 0.8),
                              left=0.08, right=0.95, top=0.92, bottom=0.15)
    else:
        gs = fig.add_gridspec(nrows=4, ncols=2, wspace=0.3, hspace=0.35, 
                              width_ratios=(1.2, 0.8),
                              left=0.08, right=0.95, top=0.92, bottom=0.08)
    
    # 3D surface plot (top-left, spans 3 rows)
    ax_3d = fig.add_subplot(gs[0:3, 0:1], projection='3d')
    plot_azimuthal_contour_3d(
        result,
        distribution_mc=distribution_mc,
        ax=ax_3d,
        plot_mean_curve_peak_by_azimuth=plot_mean_curve_peak_by_azimuth,
        cmap=cmap
    )
    # Remove legend from 3D plot (will use combined legend)
    ax_3d.legend().remove() if ax_3d.get_legend() else None
    
    # 2D contour plot (top-right, spans 2 rows)
    ax_2d = fig.add_subplot(gs[0:2, 1:2])
    plot_azimuthal_contour_2d(
        result,
        distribution_mc=distribution_mc,
        ax=ax_2d,
        plot_mean_curve_peak_by_azimuth=plot_mean_curve_peak_by_azimuth,
        cmap=cmap
    )
    ax_2d.set_xlabel("")  # Remove x label (shared with bottom)
    # Remove legend from 2D plot (will use combined legend)
    ax_2d.legend().remove() if ax_2d.get_legend() else None
    
    # Traditional HVSR curves (bottom-right, spans 2 rows)
    ax_curves = fig.add_subplot(gs[2:4, 1:2])
    
    # Plot individual azimuth curves
    if plot_individual_curves:
        cmap_obj = cm.get_cmap(cmap if cmap != "plasma" else "viridis")
        n_azimuths = len(result.azimuths)
        for i, azimuth in enumerate(result.azimuths):
            color = cmap_obj(i / n_azimuths)
            ax_curves.plot(
                result.frequencies, 
                result.mean_curves_per_azimuth[i],
                color=color,
                linewidth=0.5,
                alpha=0.7
            )
    
    # Plot overall mean curve
    mean_curve = result.mean_curve(distribution_mc)
    std_curve = result.std_curve(distribution_mc)
    
    ax_curves.plot(result.frequencies, mean_curve,
                   color='black', linewidth=2, label='Mean (all azimuths)')
    
    # Plot +/- std
    if distribution_mc == "lognormal":
        std_plus = mean_curve * np.exp(std_curve)
        std_minus = mean_curve * np.exp(-std_curve)
    else:
        std_plus = mean_curve + std_curve
        std_minus = mean_curve - std_curve
    
    ax_curves.plot(result.frequencies, std_plus,
                   color='black', linewidth=1, linestyle='--', label='+/- 1 Std')
    ax_curves.plot(result.frequencies, std_minus,
                   color='black', linewidth=1, linestyle='--')
    
    # Mark peak
    peak_freq, peak_amp = result.mean_curve_peak(distribution_mc)
    ax_curves.plot(peak_freq, peak_amp, 'D', 
                   markersize=8, markerfacecolor='lightgreen',
                   markeredgecolor='black', markeredgewidth=1,
                   label=f'Peak: {peak_freq:.2f} Hz')
    
    ax_curves.set_xscale("log")
    ax_curves.set_xlabel("Frequency (Hz)")
    ax_curves.set_ylabel("HVSR Amplitude")
    ax_curves.grid(True, alpha=0.3)
    
    # Handle legend positioning
    if legend_loc == "outside_right":
        ax_curves.legend(bbox_to_anchor=(1.05, 1), loc='upper left', 
                        fontsize=8, frameon=True, fancybox=True)
    elif legend_loc == "outside_bottom":
        ax_curves.legend(bbox_to_anchor=(0.5, -0.15), loc='upper center',
                        fontsize=8, frameon=True, fancybox=True, ncol=3)
    elif legend_loc == "none":
        pass  # No legend
    else:  # Default: upper_right
        ax_curves.legend(loc="upper right", fontsize=8)
    
    # Add panel labels in upper-left corner with white background
    if show_panel_labels:
        label_style = dict(fontsize=11, fontweight='bold',
                          bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                                   edgecolor='gray', alpha=0.9))
        
        # 3D axes - position in upper left corner
        ax_3d.text2D(0.02, 0.98, '(a)', transform=ax_3d.transAxes,
                    verticalalignment='top', **label_style)
        
        # 2D axes - position below colorbar  
        ax_2d.text(0.02, 0.88, '(b)', transform=ax_2d.transAxes,
                  verticalalignment='top', **label_style)
        
        # Curves axes
        ax_curves.text(0.02, 0.98, '(c)', transform=ax_curves.transAxes,
                      verticalalignment='top', **label_style)
    
    # Add title
    fig.suptitle("Azimuthal HVSR Analysis", fontsize=14, fontweight='bold')
    
    return (fig, (ax_3d, ax_2d, ax_curves))


def save_azimuthal_plot(fig: plt.Figure, 
                        filepath: str, 
                        dpi: int = 300,
                        bbox_inches: str = 'tight'):
    """
    Save azimuthal plot to file.
    
    Args:
        fig: Figure to save
        filepath: Output file path
        dpi: Resolution
        bbox_inches: Bounding box option
    """
    fig.savefig(filepath, dpi=dpi, bbox_inches=bbox_inches)
    print(f"Saved azimuthal plot to: {filepath}")

