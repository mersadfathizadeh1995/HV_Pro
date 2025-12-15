"""
Data Export Functions for HVSR Pro
===================================

Functions for exporting seismic data to various formats.

Supported Formats:
- .mat (MATLAB format) - Compatible with scipy.io.loadmat
- .mseed (MiniSEED) - Standard seismological format
- .csv (Comma-Separated Values) - Human-readable text

Based on HVSR_old/miniseed_array_reduction.py format specification.
"""

import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict


def export_seismic_data(data, output_dir: str, filename: str, options: Dict):
    """
    Export seismic data to specified format.

    Args:
        data: SeismicData object
        output_dir: Output directory path
        filename: Base filename (without extension)
        options: Dict with export options:
                - format: 'mat', 'mseed', or 'csv'
                - apply_time_window: bool
                - time_range: dict with 'start' and 'end'
                - combined: bool (not used here, handled at dialog level)
                - preserve_sampling: bool
                - include_metadata: bool
    """
    file_format = options.get('format', 'mat')

    if file_format == 'mat':
        export_to_mat(data, output_dir, filename, options)
    elif file_format == 'mseed':
        export_to_mseed(data, output_dir, filename, options)
    elif file_format == 'csv':
        export_to_csv(data, output_dir, filename, options)
    else:
        raise ValueError(f"Unsupported export format: {file_format}")


def export_to_mat(data, output_dir: str, filename: str, options: Dict):
    """
    Export seismic data to MATLAB .mat file.

    Format compatible with HVSR_old/miniseed_array_reduction.py:
    - E, N, Z: component arrays
    - Fs: sampling rate
    - t: time vector
    - starttime_matlab: MATLAB datenum
    - metadata: additional information

    Args:
        data: SeismicData object
        output_dir: Output directory path
        filename: Base filename (without extension)
        options: Export options dict
    """
    try:
        from scipy.io import savemat
    except ImportError:
        raise ImportError("scipy is required for .mat export. Install with: pip install scipy")

    # Apply time window if requested
    if options.get('apply_time_window') and options.get('time_range'):
        data = apply_time_window(data, options['time_range'])

    # Extract component data
    e_data = data.E.data if hasattr(data.E, 'data') else data.E
    n_data = data.N.data if hasattr(data.N, 'data') else data.N
    z_data = data.Z.data if hasattr(data.Z, 'data') else data.Z

    # Get sampling rate
    fs = data.E.sampling_rate if hasattr(data.E, 'sampling_rate') else data.sampling_rate

    # Generate time vector
    nsamples = len(e_data)
    t = np.arange(nsamples) / fs

    # Get start time
    if hasattr(data, 'start_time') and data.start_time:
        start_dt = data.start_time
    else:
        start_dt = datetime.now()

    # Convert to MATLAB datenum
    # MATLAB datenum = days since January 1, 0000
    # Python ordinal = days since January 1, 0001
    # MATLAB datenum = ordinal + 366 + fractional day
    matlab_datenum = start_dt.toordinal() + 366 + (
        start_dt - datetime(start_dt.year, start_dt.month, start_dt.day)
    ).total_seconds() / 86400.0

    # Prepare data structure
    mat_data = {
        'E': e_data,
        'N': n_data,
        'Z': z_data,
        'Fs': fs,
        't': t,
        'starttime_matlab': matlab_datenum,
        'starttime_iso': start_dt.isoformat(),
        'duration': nsamples / fs,
        'nsamples': nsamples
    }

    # Add metadata if requested
    if options.get('include_metadata', True):
        metadata = {
            'export_time': datetime.now().isoformat(),
            'time_window_applied': options.get('apply_time_window', False),
            'sampling_rate': fs,
            'start_time': start_dt.isoformat()
        }

        # Add original file metadata if available
        if hasattr(data, 'metadata'):
            for key, value in data.metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    metadata[key] = value

        mat_data['metadata'] = metadata

    # Create output path
    output_path = Path(output_dir) / f"{filename}.mat"

    # Save to .mat file
    savemat(str(output_path), mat_data, do_compression=True)


def export_to_mseed(data, output_dir: str, filename: str, options: Dict):
    """
    Export seismic data to MiniSEED format.

    Args:
        data: SeismicData object
        output_dir: Output directory path
        filename: Base filename (without extension)
        options: Export options dict
    """
    try:
        from obspy import Stream, Trace
        from obspy.core import UTCDateTime
    except ImportError:
        raise ImportError("obspy is required for .mseed export. Install with: pip install obspy")

    # Apply time window if requested
    if options.get('apply_time_window') and options.get('time_range'):
        data = apply_time_window(data, options['time_range'])

    # Extract component data
    e_data = data.E.data if hasattr(data.E, 'data') else data.E
    n_data = data.N.data if hasattr(data.N, 'data') else data.N
    z_data = data.Z.data if hasattr(data.Z, 'data') else data.Z

    # Get sampling rate
    fs = data.E.sampling_rate if hasattr(data.E, 'sampling_rate') else data.sampling_rate

    # Get start time
    if hasattr(data, 'start_time') and data.start_time:
        start_time = UTCDateTime(data.start_time)
    else:
        start_time = UTCDateTime()

    # Create ObsPy stream with three traces
    stream = Stream()

    # Create traces for each component
    for component, component_data in [('E', e_data), ('N', n_data), ('Z', z_data)]:
        trace = Trace(data=component_data)
        trace.stats.sampling_rate = fs
        trace.stats.starttime = start_time
        trace.stats.channel = component
        trace.stats.station = 'STA'
        trace.stats.network = 'XX'

        # Add metadata if available
        if hasattr(data, 'metadata') and options.get('include_metadata', True):
            for key, value in data.metadata.items():
                if isinstance(value, (str, int, float)):
                    trace.stats[key] = value

        stream.append(trace)

    # Create output path
    output_path = Path(output_dir) / f"{filename}.mseed"

    # Write to MiniSEED file
    stream.write(str(output_path), format='MSEED')


def export_to_csv(data, output_dir: str, filename: str, options: Dict):
    """
    Export seismic data to CSV format.

    CSV structure:
    time,E,N,Z
    0.000,val1,val2,val3
    0.010,val1,val2,val3
    ...

    Args:
        data: SeismicData object
        output_dir: Output directory path
        filename: Base filename (without extension)
        options: Export options dict
    """
    import csv

    # Apply time window if requested
    if options.get('apply_time_window') and options.get('time_range'):
        data = apply_time_window(data, options['time_range'])

    # Extract component data
    e_data = data.E.data if hasattr(data.E, 'data') else data.E
    n_data = data.N.data if hasattr(data.N, 'data') else data.N
    z_data = data.Z.data if hasattr(data.Z, 'data') else data.Z

    # Get sampling rate
    fs = data.E.sampling_rate if hasattr(data.E, 'sampling_rate') else data.sampling_rate

    # Generate time vector
    nsamples = len(e_data)
    t = np.arange(nsamples) / fs

    # Create output path
    output_path = Path(output_dir) / f"{filename}.csv"

    # Write to CSV
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)

        # Write header
        header = ['time_sec', 'E', 'N', 'Z']
        writer.writerow(header)

        # Write metadata as comments if requested
        if options.get('include_metadata', True):
            if hasattr(data, 'start_time') and data.start_time:
                writer.writerow([f'# Start time: {data.start_time.isoformat()}'])
            writer.writerow([f'# Sampling rate: {fs} Hz'])
            writer.writerow([f'# Duration: {nsamples / fs:.2f} seconds'])
            writer.writerow([f'# Samples: {nsamples}'])
            writer.writerow(['#'])

        # Write data rows
        for i in range(nsamples):
            row = [f'{t[i]:.6f}', e_data[i], n_data[i], z_data[i]]
            writer.writerow(row)


def apply_time_window(data, time_range: Dict):
    """
    Apply time window to seismic data.

    Args:
        data: SeismicData object
        time_range: Dict with 'start' and 'end' in seconds

    Returns:
        SeismicData object with reduced time window
    """
    start_sec = time_range.get('start', 0)
    end_sec = time_range.get('end', None)

    # Get sampling rate
    fs = data.E.sampling_rate if hasattr(data.E, 'sampling_rate') else data.sampling_rate

    # Calculate sample indices
    start_idx = int(start_sec * fs)
    end_idx = int(end_sec * fs) if end_sec is not None else None

    # Extract component data
    e_data = data.E.data if hasattr(data.E, 'data') else data.E
    n_data = data.N.data if hasattr(data.N, 'data') else data.N
    z_data = data.Z.data if hasattr(data.Z, 'data') else data.Z

    # Slice data
    e_sliced = e_data[start_idx:end_idx]
    n_sliced = n_data[start_idx:end_idx]
    z_sliced = z_data[start_idx:end_idx]

    # Create new data object with sliced data
    # Try to use proper SeismicData class
    try:
        from hvsr_pro.data.seismic import SeismicData

        # Calculate new start time
        if hasattr(data, 'start_time') and data.start_time:
            from datetime import timedelta
            new_start_time = data.start_time + timedelta(seconds=start_sec)
        else:
            new_start_time = None

        sliced_data = SeismicData(
            e=e_sliced,
            n=n_sliced,
            z=z_sliced,
            sampling_rate=fs,
            start_time=new_start_time
        )
    except Exception:
        # Fallback: create simple object
        class SlicedData:
            def __init__(self, e, n, z, fs, start_time):
                self.E = type('Component', (), {'data': e, 'sampling_rate': fs})()
                self.N = type('Component', (), {'data': n, 'sampling_rate': fs})()
                self.Z = type('Component', (), {'data': z, 'sampling_rate': fs})()
                self.sampling_rate = fs
                self.start_time = start_time
                self.duration = len(e) / fs if fs else len(e)
                self.metadata = getattr(data, 'metadata', {})

        # Calculate new start time
        if hasattr(data, 'start_time') and data.start_time:
            from datetime import timedelta
            new_start_time = data.start_time + timedelta(seconds=start_sec)
        else:
            new_start_time = None

        sliced_data = SlicedData(e_sliced, n_sliced, z_sliced, fs, new_start_time)

    return sliced_data
