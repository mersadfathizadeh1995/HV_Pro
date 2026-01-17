"""
Data Exporter
=============

Functions for exporting azimuthal HVSR data to CSV and JSON formats.
"""

import csv
import json
from typing import Any
import numpy as np


def write_csv(filename: str, result: Any) -> None:
    """
    Write mean curves CSV file.
    
    Args:
        filename: Output file path
        result: AzimuthalHVSRResult object
    """
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Header
        header = ['Frequency (Hz)'] + [
            f'Azimuth {az:.0f} deg' for az in result.azimuths
        ]
        writer.writerow(header)
        
        # Data rows
        for i, freq in enumerate(result.frequencies):
            row = [freq]
            for j in range(len(result.azimuths)):
                val = result.mean_curves_per_azimuth[j, i]
                row.append(val if not np.isnan(val) else '')
            writer.writerow(row)


def write_json(filename: str, result: Any) -> None:
    """
    Write full results JSON file.
    
    Args:
        filename: Output file path
        result: AzimuthalHVSRResult object
    """
    def to_list(arr):
        """Convert numpy array to list, handling NaN values."""
        if arr is None:
            return None
        output = []
        for row in arr:
            if hasattr(row, '__iter__'):
                output.append([None if np.isnan(x) else float(x) for x in row])
            else:
                output.append(None if np.isnan(row) else float(row))
        return output
    
    data = {
        'frequencies': result.frequencies.tolist(),
        'azimuths': result.azimuths.tolist(),
        'mean_curves_per_azimuth': to_list(result.mean_curves_per_azimuth),
        'std_curves_per_azimuth': to_list(result.std_curves_per_azimuth) if result.std_curves_per_azimuth is not None else None,
        'metadata': result.metadata if hasattr(result, 'metadata') else {}
    }
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)


def write_individual_csv(filename: str, result: Any) -> None:
    """
    Write individual window curves CSV file.
    
    Args:
        filename: Output file path
        result: AzimuthalHVSRResult object
    """
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Header: Frequency, then each azimuth/window combination
        header = ['Frequency (Hz)']
        if result.hvsr_per_azimuth is not None:
            n_windows = result.hvsr_per_azimuth.shape[1]
            for az in result.azimuths:
                for w in range(n_windows):
                    header.append(f'Az{az:.0f}_W{w+1}')
        writer.writerow(header)
        
        # Data
        if result.hvsr_per_azimuth is not None:
            for i, freq in enumerate(result.frequencies):
                row = [freq]
                for j in range(len(result.azimuths)):
                    for w in range(n_windows):
                        val = result.hvsr_per_azimuth[j, w, i]
                        row.append(val if not np.isnan(val) else '')
                writer.writerow(row)


def write_peaks_csv(filename: str, result: Any) -> None:
    """
    Write peak frequencies per azimuth to CSV.
    
    Args:
        filename: Output file path
        result: AzimuthalHVSRResult object
    """
    peak_freqs, peak_amps = result.mean_curve_peak_by_azimuth()
    
    with open(filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Azimuth (deg)', 'Peak Frequency (Hz)', 'Peak Amplitude'])
        
        for i, az in enumerate(result.azimuths):
            writer.writerow([az, peak_freqs[i], peak_amps[i]])
