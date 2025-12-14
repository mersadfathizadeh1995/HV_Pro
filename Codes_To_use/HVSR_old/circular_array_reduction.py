from __future__ import annotations

"""circular_array_reduction.py

Process miniseed files from a circular array with multiple stations (1-10 stations)
and create a MATLAB-compatible .mat file exactly matching the MATLAB MiniseedArrayReduction format.

Replicates the MATLAB workflow:
1. Loop through each station
2. Load and concatenate ALL hourly miniseed files into continuous arrays
3. Extract the specified time window from the continuous data
4. Store in cell arrays {1, num_stations}
5. Convert cell arrays to matrices (num_samples x num_stations)

Each station has 3 components: HNZ, HNN, HNE
Output contains Array1Z, Array1N, Array1E matrices where each column is a station.
"""

import argparse
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional

import numpy as np
import pandas as pd
from scipy.io import savemat

from rdmseed_py import rdmseed


# -----------------------------------------------------------------------------
# Utility helpers
# -----------------------------------------------------------------------------

def _matlab_datenum(dt: datetime) -> float:
    """Convert datetime -> MATLAB datenum."""
    return dt.toordinal() + 366 + (
        dt - datetime(dt.year, dt.month, dt.day)
    ).total_seconds() / 86400.0


def _hourly_files_in_range(start: datetime, end: datetime) -> List[datetime]:
    """Generate all hourly datetimes that fall between *start* and *end* (inclusive)."""
    current = start.replace(minute=0, second=0, microsecond=0)
    # Extend to cover the hour containing the end time
    end_hour = end.replace(minute=0, second=0, microsecond=0)
    if end > end_hour:
        end_hour += timedelta(hours=1)
    
    hours = []
    while current <= end_hour:
        hours.append(current)
        current += timedelta(hours=1)
    return hours


# -----------------------------------------------------------------------------
# Station pattern extraction helpers
# -----------------------------------------------------------------------------

def extract_station_prefix(sample_file: Path) -> str:
    """Extract the station-specific prefix from a sample miniseed file.
    
    Example: AR.STN01.centaur-3_0655_20251002_180000.miniseed
    Returns: Full path prefix like D:/data/AR.STN01.centaur-3_0655_
    
    The returned prefix includes the directory path so files can be found.
    """
    import re
    stem = sample_file.stem
    # Find the pattern _YYYYMMDD_HHMMSS at the end
    match = re.match(r"(.+?)_\d{8}_\d{6}$", stem)
    if match:
        # Return the full path prefix (directory + prefix)
        return str(sample_file.parent / match.group(1)) + "_"
    else:
        # Fallback: just use the whole stem with directory
        warnings.warn(f"Could not detect date pattern in {sample_file.name}, using full stem as prefix")
        return str(sample_file.parent / stem) + "_"


def extract_station_number(prefix: str) -> Optional[int]:
    """Extract station number from prefix.
    
    Example: AR.STN01.centaur-3_0655_ -> 1
    """
    import re
    match = re.search(r"STN(\d+)", prefix)
    if match:
        return int(match.group(1))
    return None


# -----------------------------------------------------------------------------
# Core processing - Matches MATLAB MiniseedArrayReduction logic
# -----------------------------------------------------------------------------

def process_circular_array(
    csv_path: Path,
    station_patterns: Dict[int, str],  # station_number -> file_prefix
    sampling_rate: float,
    output_dir: Path | None = None,
    verbose: bool = True,
):
    """Process circular array data from multiple stations - MATLAB compatible.

    Replicates MATLAB MiniseedArrayReduction.m workflow:
    - Loops through each station
    - Loads and concatenates ALL hourly files into continuous HNZ, HNN, HNE arrays
    - Extracts the time window specified in CSV
    - Creates Array1Z/N/E matrices (num_samples x num_stations)

    Parameters
    ----------
    csv_path
        CSV file containing ONE time window with columns:
        S_Year, S_Month, S_Day, S_Hour, S_Min, S_Sec, E_Year, E_Month, E_Day, E_Hour, E_Min, E_Sec
    station_patterns
        Dictionary mapping station number (1-10) to filename prefix pattern.
        Example: {1: "AR.STN01.centaur-3_0655_", 2: "AR.STN02.centaur-3_0656_", ...}
    sampling_rate
        Nominal sampling rate (Hz).
    output_dir
        Directory where the .mat output will be written. Defaults to current directory.
    verbose
        Emit progress messages.
    """

    df = pd.read_csv(csv_path)

    if df.empty:
        raise ValueError("Start/End CSV contains no rows")
    
    # Take only the FIRST row (single time window)
    if len(df) > 1:
        warnings.warn(f"CSV contains {len(df)} rows, but only the FIRST time window will be processed.")
    
    row = df.iloc[0]

    # Parse start/end datetime
    start_dt = datetime(
        int(row['S_Year']), int(row['S_Month']), int(row['S_Day']),
        int(row['S_Hour']), int(row['S_Min']), int(row['S_Sec'])
    )
    end_dt = datetime(
        int(row['E_Year']), int(row['E_Month']), int(row['E_Day']),
        int(row['E_Hour']), int(row['E_Min']), int(row['E_Sec'])
    )

    num_stations = len(station_patterns)
    station_ids = sorted(station_patterns.keys())

    if verbose:
        print(f"\n{'='*60}")
        print(f"Processing circular array reduction")
        print(f"Stations: {num_stations} ({station_ids})")
        print(f"Time window: {start_dt} -> {end_dt}")
        print(f"{'='*60}\n")

    # Cell arrays to store data for each station (like MATLAB cell arrays)
    # In MATLAB: TArray1Z{1,station} = time_vector
    # In Python: TArray1Z_cells[station] = time_vector
    TArray1Z_cells = {}
    TArray1N_cells = {}
    TArray1E_cells = {}
    
    Array1Z_cells = {}
    Array1N_cells = {}
    Array1E_cells = {}

    # MATLAB-style loop: for e=1:length(filename)
    for station_id in station_ids:
        prefix = station_patterns[station_id]
        
        if verbose:
            print(f"Station {station_id:02d}: {prefix}")

        # Initialize continuous arrays for this station (like MATLAB HNZ, HNN, HNE)
        HNZ_time_list = []
        HNZ_amp_list = []
        HNN_time_list = []
        HNN_amp_list = []
        HNE_time_list = []
        HNE_amp_list = []

        # Get all hourly files needed to cover the time window
        hourly_times = _hourly_files_in_range(start_dt, end_dt)
        
        if verbose:
            print(f"  Loading {len(hourly_times)} hourly files...")

        # MATLAB nested loops: for p=1:length(Date), for f=1:length(Hours)
        for hour_dt in hourly_times:
            # Format: prefix + YYYYMMDD_HHMMSS.miniseed
            file_name = prefix + hour_dt.strftime("%Y%m%d_%H0000.miniseed")
            path = Path(file_name)
            
            if not path.is_file():
                if verbose:
                    print(f"    Missing: {path.name}")
                continue

            try:
                XX, _ = rdmseed(str(path), plot=False, verbose=False)
                
                # Accumulate data by channel (MATLAB lines 46-87)
                for blk in XX:
                    if blk.ChannelIdentifier == "HNZ":
                        HNZ_time_list.append(blk.t)
                        HNZ_amp_list.append(blk.d)
                    elif blk.ChannelIdentifier == "HNN":
                        HNN_time_list.append(blk.t)
                        HNN_amp_list.append(blk.d)
                    elif blk.ChannelIdentifier == "HNE":
                        HNE_time_list.append(blk.t)
                        HNE_amp_list.append(blk.d)
                
                if verbose:
                    print(f"    ✓ {path.name}")
                    
            except Exception as e:
                if verbose:
                    print(f"    ✗ {path.name}: {e}")
                continue

        # Check if we got any data
        if not HNZ_time_list:
            warnings.warn(f"No data found for station {station_id}")
            # Create empty arrays
            Array1Z_cells[station_id] = np.array([])
            Array1N_cells[station_id] = np.array([])
            Array1E_cells[station_id] = np.array([])
            TArray1Z_cells[station_id] = np.array([])
            TArray1N_cells[station_id] = np.array([])
            TArray1E_cells[station_id] = np.array([])
            continue

        # Concatenate all blocks into continuous arrays (MATLAB lines 91-95)
        HNZ_t = np.concatenate(HNZ_time_list)
        HNZ_d = np.concatenate(HNZ_amp_list)
        HNN_t = np.concatenate(HNN_time_list) if HNN_time_list else np.array([])
        HNN_d = np.concatenate(HNN_amp_list) if HNN_amp_list else np.array([])
        HNE_t = np.concatenate(HNE_time_list) if HNE_time_list else np.array([])
        HNE_d = np.concatenate(HNE_amp_list) if HNE_amp_list else np.array([])

        if verbose:
            print(f"  Concatenated: Z={len(HNZ_t)}, N={len(HNN_t)}, E={len(HNE_t)} samples")

        # Find time records (MATLAB lines 109-127)
        # Convert start/end to MATLAB datenum
        start_datenum = _matlab_datenum(start_dt)
        end_datenum = _matlab_datenum(end_dt)

        # Find indices closest to start and end times
        # MATLAB: ZQS=abs(HNZ(:,1)-StimeS(s,1)); ZStarts(s,1)=find(ZQS==min(ZQS));
        if len(HNZ_t) > 0:
            z_start_idx = np.argmin(np.abs(HNZ_t - start_datenum))
            z_end_idx = np.argmin(np.abs(HNZ_t - end_datenum))
        else:
            z_start_idx = z_end_idx = 0
            
        if len(HNN_t) > 0:
            n_start_idx = np.argmin(np.abs(HNN_t - start_datenum))
            n_end_idx = np.argmin(np.abs(HNN_t - end_datenum))
        else:
            n_start_idx = n_end_idx = 0
            
        if len(HNE_t) > 0:
            e_start_idx = np.argmin(np.abs(HNE_t - start_datenum))
            e_end_idx = np.argmin(np.abs(HNE_t - end_datenum))
        else:
            e_start_idx = e_end_idx = 0

        # Extract the time window (MATLAB lines 135-150)
        # TArray1Z{:,e}=HNZ(ZStarts(1,1):ZEnds(1,1),1);
        # Array1Z{:,e}=HNZ(ZStarts(1,1):ZEnds(1,1),2);
        TArray1Z_cells[station_id] = HNZ_t[z_start_idx:z_end_idx+1]
        TArray1N_cells[station_id] = HNN_t[n_start_idx:n_end_idx+1] if len(HNN_t) > 0 else np.array([])
        TArray1E_cells[station_id] = HNE_t[e_start_idx:e_end_idx+1] if len(HNE_t) > 0 else np.array([])
        
        Array1Z_cells[station_id] = HNZ_d[z_start_idx:z_end_idx+1]
        Array1N_cells[station_id] = HNN_d[n_start_idx:n_end_idx+1] if len(HNN_d) > 0 else np.array([])
        Array1E_cells[station_id] = HNE_d[e_start_idx:e_end_idx+1] if len(HNE_d) > 0 else np.array([])

        if verbose:
            print(f"  Extracted window: {len(Array1Z_cells[station_id])} samples\n")

    # Convert cell arrays to matrices (MATLAB lines 179-187)
    # Array1Z=cell2mat(Array1Z);
    # In MATLAB, cell2mat with {1,10} creates a matrix with 10 columns
    
    if verbose:
        print(f"Converting cell arrays to matrices...")
    
    # Find the minimum length across all stations for each component
    z_lengths = [len(Array1Z_cells[s]) for s in station_ids if len(Array1Z_cells[s]) > 0]
    n_lengths = [len(Array1N_cells[s]) for s in station_ids if len(Array1N_cells[s]) > 0]
    e_lengths = [len(Array1E_cells[s]) for s in station_ids if len(Array1E_cells[s]) > 0]
    
    if z_lengths:
        min_len_z = min(z_lengths)
        min_len_n = min(n_lengths) if n_lengths else 0
        min_len_e = min(e_lengths) if e_lengths else 0
        
        # Use the overall minimum to ensure all components align
        min_len = min(min_len_z, min_len_n, min_len_e) if (min_len_n > 0 and min_len_e > 0) else min_len_z
        
        if verbose:
            print(f"  Aligning all stations to {min_len} samples")
        
        # Stack columns (each station is a column)
        z_columns = [Array1Z_cells[s][:min_len] for s in station_ids]
        n_columns = [Array1N_cells[s][:min_len] if len(Array1N_cells[s]) >= min_len else np.zeros(min_len) for s in station_ids]
        e_columns = [Array1E_cells[s][:min_len] if len(Array1E_cells[s]) >= min_len else np.zeros(min_len) for s in station_ids]
        
        Array1Z = np.column_stack(z_columns)
        Array1N = np.column_stack(n_columns)
        Array1E = np.column_stack(e_columns)
    else:
        # No data - create empty arrays
        Array1Z = np.zeros((0, num_stations))
        Array1N = np.zeros((0, num_stations))
        Array1E = np.zeros((0, num_stations))
        min_len = 0

    # Create time vector (MATLAB line 189)
    # time1=0:1/100:((length(Array1E)-1)*1/100);
    time1 = np.arange(Array1Z.shape[0], dtype=float) / sampling_rate

    # Convert cell arrays to object arrays for MATLAB compatibility
    # Keep the cell structure for TArrays
    TArray1Z = np.empty((1, num_stations), dtype=object)
    TArray1N = np.empty((1, num_stations), dtype=object)
    TArray1E = np.empty((1, num_stations), dtype=object)
    
    for idx, station_id in enumerate(station_ids):
        TArray1Z[0, idx] = TArray1Z_cells[station_id][:min_len] if len(TArray1Z_cells[station_id]) >= min_len else TArray1Z_cells[station_id]
        TArray1N[0, idx] = TArray1N_cells[station_id][:min_len] if len(TArray1N_cells[station_id]) >= min_len else TArray1N_cells[station_id]
        TArray1E[0, idx] = TArray1E_cells[station_id][:min_len] if len(TArray1E_cells[station_id]) >= min_len else TArray1E_cells[station_id]

    # Prepare output dictionary in MATLAB format (MATLAB lines 191-194)
    out_dict = {
        "TArray1Z": TArray1Z,
        "TArray1N": TArray1N,
        "TArray1E": TArray1E,
        "Array1Z": Array1Z,
        "Array1N": Array1N,
        "Array1E": Array1E,
        "time1": time1,
        "Fs_Hz": float(sampling_rate),
        "station_ids": np.array(station_ids, dtype=np.int32),  # Preserve original station numbers
    }

    output_dir = output_dir or Path.cwd()
    output_dir.mkdir(parents=True, exist_ok=True)
    mat_path = output_dir / "ArrayData.mat"
    savemat(mat_path, out_dict)

    if verbose:
        print(f"\n{'='*60}")
        print(f"✓ Successfully created {mat_path.resolve()}")
        print(f"  Array dimensions: {Array1Z.shape[0]} samples × {Array1Z.shape[1]} stations")
        print(f"  Duration: {Array1Z.shape[0] / sampling_rate:.2f} seconds")
        print(f"  Sampling rate: {sampling_rate} Hz")
        print(f"{'='*60}")

    return mat_path


# -----------------------------------------------------------------------------
# CLI entry-point
# -----------------------------------------------------------------------------

def _cli():  # pragma: no cover
    p = argparse.ArgumentParser(
        description="Circular Array MiniSEED Reduction - MATLAB MiniseedArrayReduction.m equivalent"
    )
    p.add_argument("csv", type=Path, help="CSV file with start/end time window (single row)")
    p.add_argument("--sr", type=float, default=100.0, help="Sampling rate (Hz), default=100")
    p.add_argument("--out", type=Path, default=".", help="Output directory")
    p.add_argument("--quiet", action="store_true", help="Suppress verbose output")
    args = p.parse_args()

    print("For interactive use, please use the GUI (NewTab3_CircularArray).")
    print("This CLI requires station patterns to be defined programmatically.")
    print(f"\nCSV file: {args.csv}")
    print(f"Sampling rate: {args.sr} Hz")
    print(f"Output directory: {args.out}")


if __name__ == "__main__":  # pragma: no cover
    _cli()
