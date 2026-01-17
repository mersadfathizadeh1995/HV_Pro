"""
Statistics Exporter
===================

Functions for exporting HVSR statistics to CSV format.
"""

import csv
from typing import Any, Optional
import numpy as np
from scipy import interpolate as scipy_interpolate


def export_statistics_csv(
    filename: str,
    result: Any,
    windows: Any,
    options: dict
) -> None:
    """
    Export HVSR statistics to CSV file.
    
    Args:
        filename: Output file path
        result: HVSRResult object
        windows: WindowCollection object
        options: Export options with keys:
            - mean: bool - export mean curve
            - median: bool - export median curve
            - std: bool - export std bands
            - percentile: bool - export percentiles
            - individual: bool - export individual windows
            - n_points: int (optional) - interpolation point count
    """
    # Get original frequencies and data
    orig_frequencies = result.frequencies if hasattr(result, 'frequencies') else result.frequency
    
    # Get base data - use explicit None checks
    mean_curve_raw = getattr(result, 'mean_hvsr', None)
    if mean_curve_raw is None:
        mean_curve_raw = getattr(result, 'mean_curve', None)
    
    median_curve_raw = getattr(result, 'median_hvsr', None)
    if median_curve_raw is None:
        median_curve_raw = getattr(result, 'median_curve', None)
    
    std_curve_raw = getattr(result, 'std_hvsr', None)
    if std_curve_raw is None:
        std_curve_raw = getattr(result, 'std_curve', None)
    
    perc_16_raw = getattr(result, 'percentile_16', None)
    perc_84_raw = getattr(result, 'percentile_84', None)
    
    # Check if interpolation is needed
    n_points = options.get('n_points')
    if n_points and n_points != len(orig_frequencies):
        # Create new frequency array (log-spaced for HVSR)
        new_frequencies = np.logspace(
            np.log10(orig_frequencies[0]),
            np.log10(orig_frequencies[-1]),
            n_points
        )
        
        # Interpolation function
        def interp_curve(curve):
            if curve is None:
                return None
            try:
                if len(curve) == 0:
                    return np.full(n_points, np.nan)
            except TypeError:
                return None
            f = scipy_interpolate.interp1d(
                orig_frequencies, curve, kind='linear',
                bounds_error=False, fill_value='extrapolate'
            )
            return f(new_frequencies)
        
        frequencies = new_frequencies
        mean_curve = interp_curve(mean_curve_raw)
        median_curve = interp_curve(median_curve_raw)
        std_curve = interp_curve(std_curve_raw)
        perc_16 = interp_curve(perc_16_raw)
        perc_84 = interp_curve(perc_84_raw)
    else:
        frequencies = orig_frequencies
        mean_curve = mean_curve_raw
        median_curve = median_curve_raw
        std_curve = std_curve_raw
        perc_16 = perc_16_raw
        perc_84 = perc_84_raw
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Header
        header = ['Frequency (Hz)']
        if options.get('mean', True):
            header.append('Mean H/V')
        if options.get('median', True):
            header.append('Median H/V')
        if options.get('std', True):
            header.extend(['Mean + 1s', 'Mean - 1s'])
        if options.get('percentile', False):
            header.extend(['16th Percentile', '84th Percentile'])
        if options.get('individual', False) and windows:
            for i in range(windows.n_windows):
                header.append(f'Window {i+1}')
        
        writer.writerow(header)
        
        # Data rows
        for i, freq in enumerate(frequencies):
            row = [freq]
            
            if options.get('mean', True):
                row.append(mean_curve[i] if mean_curve is not None else '')
            if options.get('median', True):
                row.append(median_curve[i] if median_curve is not None else '')
            if options.get('std', True):
                if mean_curve is not None and std_curve is not None:
                    row.append(mean_curve[i] + std_curve[i])
                    row.append(mean_curve[i] - std_curve[i])
                else:
                    row.extend(['', ''])
            if options.get('percentile', False):
                row.append(perc_16[i] if perc_16 is not None else '')
                row.append(perc_84[i] if perc_84 is not None else '')
            if options.get('individual', False) and windows and not n_points:
                # Individual windows only available without interpolation
                for win_idx in range(windows.n_windows):
                    if hasattr(result, 'window_curves') and result.window_curves is not None:
                        row.append(result.window_curves[win_idx][i])
                    else:
                        row.append('')
            
            writer.writerow(row)
