"""
Visualization module for HVSR Pro
==================================

Interactive and static plotting for HVSR analysis.
"""

from hvsr_pro.visualization.plotter import HVSRPlotter
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
from hvsr_pro.visualization.comparison_plot import (
    plot_raw_vs_adjusted_hvsr,
    plot_raw_vs_adjusted_from_result,
    create_comparison_figure
)
from hvsr_pro.visualization.waveform_plot import (
    plot_seismic_recordings_3c,
    plot_pre_and_post_rejection
)

__all__ = [
    'HVSRPlotter',
    'plot_hvsr_curve',
    'plot_hvsr_comparison',
    'plot_hvsr_components',
    'plot_peak_analysis',
    'plot_hvsr_statistics',
    'save_hvsr_plot',
    'plot_window_time_series',
    'plot_window_spectrogram',
    'plot_window_collection_overview',
    'plot_quality_metrics_grid',
    'plot_window_comparison',
    'plot_rejection_timeline',
    # New MATLAB-style comparison plots
    'plot_raw_vs_adjusted_hvsr',
    'plot_raw_vs_adjusted_from_result',
    'create_comparison_figure',
    # New waveform plots
    'plot_seismic_recordings_3c',
    'plot_pre_and_post_rejection',
]
