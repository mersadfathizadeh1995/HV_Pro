"""
Export Utilities for HVSR Pro
===============================

Functions to export HVSR data in various formats.
"""

import numpy as np
import csv
from pathlib import Path
from typing import Optional
from hvsr_pro.processing.hvsr import HVSRResult


def export_hvsr_curve_csv(hvsr_result: HVSRResult,
                          filepath: str,
                          include_windows: bool = False,
                          include_percentiles: bool = True) -> None:
    """
    Export HVSR curve data to CSV file.
    
    Creates a CSV file with columns for frequency and HVSR statistics,
    suitable for import into MATLAB, Python, Excel, or other tools.
    
    Args:
        hvsr_result: HVSRResult object to export
        filepath: Output CSV file path
        include_windows: Include individual window curves (default: False)
        include_percentiles: Include 16th and 84th percentiles (default: True)
    
    CSV Format:
        frequency, mean_hvsr, median_hvsr, std_hvsr, [p16, p84], [window_1, window_2, ...]
    """
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Build header
        header = ['frequency_hz', 'mean_hvsr', 'median_hvsr', 'std_hvsr']
        
        if include_percentiles:
            header.extend(['percentile_16', 'percentile_84'])
        
        if include_windows and hvsr_result.window_spectra:
            for i in range(len(hvsr_result.window_spectra)):
                header.append(f'window_{i+1}')
        
        writer.writerow(header)
        
        # Write metadata as comments
        writer.writerow(['# HVSR Curve Data Export'])
        writer.writerow([f'# Valid Windows: {hvsr_result.valid_windows}/{hvsr_result.total_windows}'])
        writer.writerow([f'# Acceptance Rate: {hvsr_result.acceptance_rate:.1%}'])
        if hvsr_result.processing_params:
            for key, value in hvsr_result.processing_params.items():
                writer.writerow([f'# {key}: {value}'])
        writer.writerow([])  # Empty line
        
        # Write data
        for i in range(len(hvsr_result.frequencies)):
            row = [
                hvsr_result.frequencies[i],
                hvsr_result.mean_hvsr[i],
                hvsr_result.median_hvsr[i],
                hvsr_result.std_hvsr[i]
            ]
            
            if include_percentiles:
                row.append(hvsr_result.percentile_16[i])
                row.append(hvsr_result.percentile_84[i])
            
            if include_windows and hvsr_result.window_spectra:
                for ws in hvsr_result.window_spectra:
                    row.append(ws.hvsr[i])
            
            writer.writerow(row)


def export_hvsr_curve_for_inversion(hvsr_result: HVSRResult,
                                    filepath: str,
                                    use_median: bool = True,
                                    frequency_range: Optional[tuple] = None) -> None:
    """
    Export HVSR curve in format optimized for inversion codes.
    
    Creates a simple two-column file (frequency, HVSR) suitable for
    inversion programs like Dinver, Geopsy, etc.
    
    Args:
        hvsr_result: HVSRResult object to export
        filepath: Output file path
        use_median: Use median instead of mean (default: True, recommended for inversion)
        frequency_range: (f_min, f_max) to limit export range, None = all frequencies
    
    File Format:
        # HVSR Curve for Inversion
        # Frequency(Hz)  HVSR
        0.2000  1.234
        0.2105  1.345
        ...
    """
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    
    # Select curve to export
    hvsr_curve = hvsr_result.median_hvsr if use_median else hvsr_result.mean_hvsr
    frequencies = hvsr_result.frequencies
    
    # Apply frequency range filter if specified
    if frequency_range is not None:
        f_min, f_max = frequency_range
        mask = (frequencies >= f_min) & (frequencies <= f_max)
        frequencies = frequencies[mask]
        hvsr_curve = hvsr_curve[mask]
    
    # Get std curve for uncertainty
    std_curve = hvsr_result.std_hvsr
    if frequency_range is not None:
        f_min, f_max = frequency_range
        mask = (hvsr_result.frequencies >= f_min) & (hvsr_result.frequencies <= f_max)
        std_curve = std_curve[mask]
    
    with open(filepath, 'w') as f:
        # Header
        f.write(f"# HVSR Curve for Inversion (Enhanced with Uncertainty)\n")
        f.write(f"# Statistics: {'Median' if use_median else 'Mean'}\n")
        f.write(f"# Valid Windows: {hvsr_result.valid_windows}/{hvsr_result.total_windows}\n")
        f.write(f"# Acceptance Rate: {hvsr_result.acceptance_rate:.1%}\n")
        f.write(f"# Frequency Range: {frequencies[0]:.4f} - {frequencies[-1]:.4f} Hz\n")
        f.write(f"# Number of Points: {len(frequencies)}\n")
        f.write(f"#\n")
        f.write(f"# Column Format:\n")
        f.write(f"#   1. Frequency (Hz)\n")
        f.write(f"#   2. HVSR ({'Median' if use_median else 'Mean'})\n")
        f.write(f"#   3. HVSR Standard Deviation\n")
        f.write(f"#\n")
        f.write(f"# Frequency(Hz)  HVSR         StdDev\n")
        
        # Data - 3 columns
        for freq, hvsr, std in zip(frequencies, hvsr_curve, std_curve):
            f.write(f"{freq:.4f}  {hvsr:.6f}  {std:.6f}\n")


def export_peaks_csv(hvsr_result: HVSRResult, filepath: str) -> None:
    """
    Export detected peaks to CSV file.
    
    Args:
        hvsr_result: HVSRResult object with peaks
        filepath: Output CSV file path
    """
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        
        # Header
        writer.writerow(['peak_number', 'frequency_hz', 'amplitude', 
                        'prominence', 'width_hz', 'left_freq_hz', 
                        'right_freq_hz', 'quality'])
        
        # Metadata
        writer.writerow(['# HVSR Peaks Export'])
        writer.writerow([f'# Number of Peaks: {len(hvsr_result.peaks)}'])
        writer.writerow([])
        
        # Data
        for i, peak in enumerate(hvsr_result.peaks, 1):
            peak_dict = peak.to_dict()
            writer.writerow([
                i,
                peak_dict['frequency'],
                peak_dict['amplitude'],
                peak_dict['prominence'],
                peak_dict['width'],
                peak_dict['left_freq'],
                peak_dict['right_freq'],
                peak_dict['quality']
            ])


def export_complete_dataset(hvsr_result: HVSRResult,
                           output_dir: str,
                           base_filename: str = "hvsr") -> dict:
    """
    Export complete HVSR dataset with multiple files.
    
    Creates a comprehensive export package including:
    - HVSR curve CSV (all statistics)
    - HVSR curve for inversion (median only)
    - Peaks CSV
    - Metadata JSON
    
    Args:
        hvsr_result: HVSRResult object to export
        output_dir: Output directory path
        base_filename: Base filename for all exports (default: "hvsr")
    
    Returns:
        Dictionary with paths to created files
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    created_files = {}
    
    # 1. Full HVSR curve CSV
    curve_csv = output_path / f"{base_filename}_curve_complete.csv"
    export_hvsr_curve_csv(hvsr_result, str(curve_csv), 
                         include_windows=False, include_percentiles=True)
    created_files['curve_complete'] = str(curve_csv)
    
    # 2. HVSR curve for inversion (median)
    inv_file = output_path / f"{base_filename}_for_inversion.txt"
    export_hvsr_curve_for_inversion(hvsr_result, str(inv_file), use_median=True)
    created_files['inversion'] = str(inv_file)
    
    # 3. Peaks CSV
    if hvsr_result.peaks:
        peaks_csv = output_path / f"{base_filename}_peaks.csv"
        export_peaks_csv(hvsr_result, str(peaks_csv))
        created_files['peaks'] = str(peaks_csv)
    
    # 4. Metadata JSON
    metadata_json = output_path / f"{base_filename}_metadata.json"
    hvsr_result.save(str(metadata_json), include_windows=False)
    created_files['metadata'] = str(metadata_json)
    
    return created_files
