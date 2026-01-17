"""
Figure Exporter
===============

Functions for exporting HVSR comparison figures.
"""

from typing import Any, Optional


def export_comparison_figure(
    filename: str,
    result: Any,
    windows: Any,
    options: dict
) -> None:
    """
    Export Raw vs Adjusted HVSR comparison figure.
    
    Args:
        filename: Output file path
        result: HVSRResult object
        windows: WindowCollection object
        options: Figure options including:
            - show_rejected: bool
            - rejected_color: str
            - rejected_alpha: float
            - rejected_linewidth: float
            - title_fontsize: int
            - axis_fontsize: int
            - spacing: float
            - dpi: int
    """
    from hvsr_pro.visualization.comparison_plot import plot_raw_vs_adjusted_from_result
    
    # Generate figure
    fig = plot_raw_vs_adjusted_from_result(
        hvsr_result=result,
        windows=windows,
        station_name="",
        save_path=filename
    )
    
    return fig


def export_waveform_figure(
    filename: str,
    data: Any,
    windows: Any,
    options: dict
) -> None:
    """
    Export 3C waveform plot with rejection markers.
    
    Args:
        filename: Output file path
        data: SeismicData object
        windows: WindowCollection object
        options: Figure options including:
            - title_fontsize: int
            - axis_fontsize: int
            - spacing: float (hspace)
            - dpi: int
    """
    from hvsr_pro.visualization.waveform_plot import plot_seismic_recordings_3c
    
    # Get figure options
    dpi = options.get('dpi', 300)
    title_fontsize = options.get('title_fontsize', 11)
    axis_fontsize = options.get('axis_fontsize', 10)
    hspace = options.get('spacing', 0.5)
    
    # Generate figure
    fig = plot_seismic_recordings_3c(
        data=data,
        windows=windows,
        normalize=True,
        dpi=dpi,
        save_path=filename,
        title="3-Component Seismic Recording with QC",
        title_fontsize=title_fontsize,
        axis_fontsize=axis_fontsize,
        hspace=hspace
    )
    
    return fig


def export_prepost_figure(
    filename: str,
    data: Any,
    result: Any,
    windows: Any,
    options: dict
) -> None:
    """
    Export comprehensive pre/post rejection figure.
    
    Args:
        filename: Output file path
        data: SeismicData object
        result: HVSRResult object
        windows: WindowCollection object
        options: Figure options including:
            - title_fontsize: int
            - axis_fontsize: int
            - spacing: float
            - dpi: int
    """
    from hvsr_pro.visualization.waveform_plot import plot_pre_and_post_rejection
    
    # Get figure options
    dpi = options.get('dpi', 300)
    title_fontsize = options.get('title_fontsize', 11)
    axis_fontsize = options.get('axis_fontsize', 10)
    spacing = options.get('spacing', 0.5)
    
    # Generate figure
    fig = plot_pre_and_post_rejection(
        data=data,
        hvsr_result=result,
        windows=windows,
        station_name="",
        dpi=dpi,
        save_path=filename,
        title_fontsize=title_fontsize,
        axis_fontsize=axis_fontsize,
        hspace=spacing,
        wspace=spacing
    )
    
    return fig
