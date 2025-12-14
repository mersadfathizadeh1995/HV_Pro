from __future__ import annotations

"""array_write_miniseed.py

Convert ArrayData.mat file into individual MiniSEED files for Geopsy processing.
Python equivalent of MATLAB ArrayWriteMiniseed.m

Input: ArrayData.mat (from circular_array_reduction.py)
Output: Individual MiniSEED files for each station and component
        Format: AR.STN01.{ArrayName}.HNZ, AR.STN01.{ArrayName}.HNN, AR.STN01.{ArrayName}.HNE, etc.
        
For a 10-station single circular array, this creates 30 files (10 stations × 3 components).
These files can be imported into Geopsy for HFK and MSPAC analysis.
"""

import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import numpy as np
from scipy.io import loadmat

try:
    from obspy import Trace, Stream, UTCDateTime
    from obspy.core import Stats
except ImportError as e:
    raise ImportError(
        "ObsPy is required for array_write_miniseed. Install with 'pip install obspy'."
    ) from e


# -----------------------------------------------------------------------------
# Utility helpers
# -----------------------------------------------------------------------------

def _matlab_datenum_to_datetime(datenum: float) -> datetime:
    """Convert MATLAB datenum to Python datetime."""
    # MATLAB datenum: days since 0000-01-00
    # Python ordinal: days since 0001-01-01
    # Offset is 366 days
    days = datenum - 366
    return datetime.fromordinal(int(days)) + timedelta(days=days % 1)


def _matlab_datenum_to_utcdatetime(datenum: float) -> UTCDateTime:
    """Convert MATLAB datenum to ObsPy UTCDateTime."""
    dt = _matlab_datenum_to_datetime(datenum)
    return UTCDateTime(dt)


# -----------------------------------------------------------------------------
# Core processing
# -----------------------------------------------------------------------------

def write_miniseed_files(
    mat_path: Path,
    output_dir: Path,
    array_name: str = "A1",
    network: str = "AR",
    sampling_rate: Optional[float] = None,
    use_relative_time: bool = True,
    verbose: bool = True,
):
    """Convert ArrayData.mat to individual MiniSEED files for Geopsy.

    Parameters
    ----------
    mat_path
        Path to the ArrayData.mat file created by circular_array_reduction.py
    output_dir
        Directory where MiniSEED files will be written
    array_name
        Name for this array (e.g., "A1", "B1", "C1"). Used in filename.
    network
        Network code (default "AR")
    sampling_rate
        Sampling rate in Hz. If None, will try to read from mat file.
    use_relative_time
        If True, use integer day as start time (MATLAB relativetime=1)
        If False, use actual time from TArray1Z
    verbose
        Print progress messages

    Output
    ------
    Creates files like:
        AR.STN01.A1.HNZ.YYYY.DDD
        AR.STN01.A1.HNN.YYYY.DDD
        AR.STN01.A1.HNE.YYYY.DDD
        ...
        AR.STN10.A1.HNZ.YYYY.DDD
        etc.
    """
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"Array Write MiniSEED - Geopsy Export")
        print(f"{'='*60}")
        print(f"Input: {mat_path}")
        print(f"Output directory: {output_dir}")
        print(f"Array name: {array_name}")
        print(f"{'='*60}\n")

    # Load the .mat file
    data = loadmat(str(mat_path))
    
    # Get arrays
    Array1Z = data['Array1Z']
    Array1N = data['Array1N']
    Array1E = data['Array1E']
    TArray1Z = data['TArray1Z']
    
    # Get sampling rate
    if sampling_rate is None:
        if 'Fs_Hz' in data:
            sampling_rate = float(data['Fs_Hz'].flatten()[0])
        else:
            sampling_rate = 100.0  # MATLAB default
            if verbose:
                print(f"Warning: No Fs_Hz in mat file, using default {sampling_rate} Hz")
    
    num_samples, num_stations = Array1Z.shape
    
    # Get station IDs (if available) - these preserve original station numbers
    # e.g., [1, 2, 4, 5, 6, 7, 8, 9, 10] when station 3 was excluded
    if 'station_ids' in data:
        station_ids = data['station_ids'].flatten().astype(int).tolist()
    else:
        # Fallback to sequential numbering for backward compatibility
        station_ids = list(range(1, num_stations + 1))
    
    if verbose:
        print(f"Data shape: {num_samples} samples × {num_stations} stations")
        print(f"Sampling rate: {sampling_rate} Hz")
        print(f"Duration: {num_samples / sampling_rate:.2f} seconds")
        print()

    # Determine start time
    # MATLAB: if relativetime, Rtime=fix(TArray1Z{1,1}); else Rtime=TArray1Z{1,1};
    if TArray1Z.size > 0 and TArray1Z[0, 0].size > 0:
        first_time = TArray1Z[0, 0].flatten()[0]
        if use_relative_time:
            # fix() in MATLAB = floor for positive numbers
            start_datenum = np.floor(first_time)
        else:
            start_datenum = first_time
        start_time = _matlab_datenum_to_utcdatetime(start_datenum)
    else:
        # Fallback to current time
        start_time = UTCDateTime.now()
        if verbose:
            print(f"Warning: No TArray1Z data, using current time as start")
    
    if verbose:
        print(f"Start time: {start_time}")
        print()

    # Create output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Components to process
    components = [
        ('HNZ', Array1Z),
        ('HNN', Array1N),
        ('HNE', Array1E),
    ]

    files_created = []

    # Loop through stations - use original station IDs (not sequential)
    for station_idx in range(num_stations):
        station_num = station_ids[station_idx]  # Use original station number
        
        # Station code: STN01, STN02, ..., STN10
        if station_num < 10:
            station_code = f"STN0{station_num}"
        else:
            station_code = f"STN{station_num}"
        
        if verbose:
            print(f"Station {station_num:02d} ({station_code}):")

        # Loop through components
        for channel_code, array_data in components:
            # Extract this station's data (MATLAB: Array1Z(:,q))
            trace_data = array_data[:, station_idx].astype(np.float64)
            
            # Create ObsPy Trace
            stats = Stats()
            stats.network = network
            stats.station = station_code
            stats.location = array_name  # Use array name as location code
            stats.channel = channel_code
            stats.sampling_rate = sampling_rate
            stats.starttime = start_time
            stats.npts = len(trace_data)
            
            trace = Trace(data=trace_data, header=stats)
            
            # Create Stream and write
            stream = Stream([trace])
            
            # Filename format: NN.SSSSS.LL.CCC (like MATLAB mkmseed)
            # ObsPy will append .YYYY.DDD automatically
            base_filename = f"{network}.{station_code}.{array_name}.{channel_code}"
            output_path = output_dir / base_filename
            
            # Write as MiniSEED
            # Note: ObsPy automatically creates proper filename with year and day
            stream.write(str(output_path), format='MSEED')
            
            files_created.append(output_path)
            
            if verbose:
                print(f"  ✓ {base_filename}")

    if verbose:
        print(f"\n{'='*60}")
        print(f"✓ Successfully created {len(files_created)} MiniSEED files")
        print(f"  Location: {output_dir}")
        print(f"\nFiles can now be imported into Geopsy for:")
        print(f"  - HFK analysis (all 3 components)")
        print(f"  - MSPAC analysis (Z component only)")
        print(f"  - H/V Spectral Ratio")
        print(f"{'='*60}")

    return files_created


# -----------------------------------------------------------------------------
# CLI entry-point
# -----------------------------------------------------------------------------

def _cli():
    p = argparse.ArgumentParser(
        description="Convert ArrayData.mat to MiniSEED files for Geopsy"
    )
    p.add_argument("mat_file", type=Path, help="Path to ArrayData.mat file")
    p.add_argument("--out", type=Path, default=".", help="Output directory")
    p.add_argument("--name", type=str, default="A1", help="Array name (e.g., A1, B1)")
    p.add_argument("--network", type=str, default="AR", help="Network code")
    p.add_argument("--sr", type=float, default=None, help="Sampling rate (Hz)")
    p.add_argument("--absolute-time", action="store_true", 
                   help="Use absolute time instead of relative")
    p.add_argument("--quiet", action="store_true", help="Suppress verbose output")
    
    args = p.parse_args()
    
    write_miniseed_files(
        mat_path=args.mat_file,
        output_dir=args.out,
        array_name=args.name,
        network=args.network,
        sampling_rate=args.sr,
        use_relative_time=not args.absolute_time,
        verbose=not args.quiet,
    )


if __name__ == "__main__":
    _cli()
