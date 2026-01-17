"""
Figure Exporter
===============

Functions for exporting azimuthal plots to image files.
"""

from typing import Any, Optional


def export_plot_to_file(
    figure: Any,
    filename: str,
    dpi: int = 300,
    bbox_inches: str = 'tight',
    facecolor: str = 'white'
) -> None:
    """
    Export a matplotlib figure to file.
    
    Args:
        figure: Matplotlib figure object
        filename: Output file path
        dpi: Resolution in dots per inch
        bbox_inches: Bounding box ('tight' recommended)
        facecolor: Background color
    """
    figure.savefig(
        filename,
        dpi=dpi,
        bbox_inches=bbox_inches,
        facecolor=facecolor
    )


def get_format_info(format_type: str) -> tuple:
    """
    Get format description and file pattern.
    
    Args:
        format_type: Format type ('png', 'pdf', 'svg')
        
    Returns:
        Tuple of (description, file pattern)
    """
    ext_map = {
        'png': ('PNG Image', '*.png'),
        'pdf': ('PDF Document', '*.pdf'),
        'svg': ('SVG Vector', '*.svg')
    }
    return ext_map.get(format_type, ('Image', '*.*'))
