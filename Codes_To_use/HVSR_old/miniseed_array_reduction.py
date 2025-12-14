from __future__ import annotations

import argparse
import warnings
from datetime import datetime, timedelta
from pathlib import Path
from typing import List

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


def _daterange(start: datetime, end: datetime) -> List[datetime]:
    """Yield all hourly datetimes that fall between *start* and *end* (inclusive)."""

    # Align to hour start
    current = start.replace(minute=0, second=0, microsecond=0)
    while current <= end:
        yield current
        current += timedelta(hours=1)


# -----------------------------------------------------------------------------
# Core processing
# -----------------------------------------------------------------------------

def process_station(
    csv_path: Path,
    pattern: str,
    sampling_rate: float,
    station_id: int,
    output_dir: Path | None = None,
    verbose: bool = True,
):
    """Replicates MATLAB MiniseedArrayReduction for one station.

    Parameters
    ----------
    csv_path
        CSV file containing one or more rows with columns
        S_Year, S_Month, S_Day, S_Hour, S_Min, S_Sec, E_Year, E_Month, E_Day, E_Hour, E_Min, E_Sec
    pattern
        Filename *format string* for MiniSEED files. It must contain two
        positional placeholders: date (YYYYMMDD) and hour (HH). For example::

            "AR.STN{station:02d}.centaur-3_0655_{date}_{hour:02d}0000.miniseed"

        Additional formatting keywords allowed: ``station``.
    sampling_rate
        Nominal sampling rate (Hz).
    station_id
        Station number used when formatting *pattern*.
    output_dir
        Directory where the .mat output will be written. Defaults to current directory.
    verbose
        Emit progress messages.
    """

    df = pd.read_csv(csv_path)

    if df.empty:
        raise ValueError("Start/End CSV contains no rows")

    # Parse start/end datetimes
    starts = pd.to_datetime(
        df[[
            "S_Year",
            "S_Month",
            "S_Day",
            "S_Hour",
            "S_Min",
            "S_Sec",
        ]].rename(
            columns={
                "S_Year": "year",
                "S_Month": "month",
                "S_Day": "day",
                "S_Hour": "hour",
                "S_Min": "minute",
                "S_Sec": "second",
            }
        )
    )
    ends = pd.to_datetime(
        df[[
            "E_Year",
            "E_Month",
            "E_Day",
            "E_Hour",
            "E_Min",
            "E_Sec",
        ]].rename(
            columns={
                "E_Year": "year",
                "E_Month": "month",
                "E_Day": "day",
                "E_Hour": "hour",
                "E_Min": "minute",
                "E_Sec": "second",
            }
        )
    )

    if len(starts) != len(ends):
        raise ValueError("Mismatch between number of start and end rows")

    # Containers akin to MATLAB cell arrays (lists of np.ndarray)
    TArray1Z: List[np.ndarray] = []
    TArray1N: List[np.ndarray] = []
    TArray1E: List[np.ndarray] = []

    Array1Z: List[np.ndarray] = []
    Array1N: List[np.ndarray] = []
    Array1E: List[np.ndarray] = []

    for idx, (start_dt, end_dt) in enumerate(zip(starts, ends)):
        if pd.isna(start_dt) or pd.isna(end_dt):
            warnings.warn(f"Row {idx} in CSV contains NaN; skipping.")
            continue

        if verbose:
            print(f"Processing interval #{idx + 1}: {start_dt} -> {end_dt}")

        # Aggregate raw channel data across hourly MiniSEED files
        HNZ_time, HNZ_amp = [], []
        HNN_time, HNN_amp = [], []
        HNE_time, HNE_amp = [], []

        for hour_dt in _daterange(start_dt, end_dt):
            file_name = pattern.format(
                date=hour_dt.strftime("%Y%m%d"),
                hour=hour_dt.hour,
                station=station_id,
            )
            path = Path(file_name)
            if not path.is_file():
                if verbose:
                    print(f"  missing {path}; skipping")
                continue

            XX, _ = rdmseed(str(path), plot=False, verbose=False)
            for blk in XX:
                # Restrict to the requested time window at the very end
                if blk.ChannelIdentifier == "HNZ":
                    HNZ_time.append(blk.t)
                    HNZ_amp.append(blk.d)
                elif blk.ChannelIdentifier == "HNN":
                    HNN_time.append(blk.t)
                    HNN_amp.append(blk.d)
                elif blk.ChannelIdentifier == "HNE":
                    HNE_time.append(blk.t)
                    HNE_amp.append(blk.d)

        if not HNZ_time:
            warnings.warn(f"No MiniSEED data found for interval #{idx + 1}")
            continue

        # Concatenate
        HNZ_t = np.concatenate(HNZ_time)
        HNZ_d = np.concatenate(HNZ_amp)
        HNN_t = np.concatenate(HNN_time)
        HNN_d = np.concatenate(HNN_amp)
        HNE_t = np.concatenate(HNE_time)
        HNE_d = np.concatenate(HNE_amp)

        # Slice to exact start/end boundaries
        mask_z = (HNZ_t >= _matlab_datenum(start_dt)) & (HNZ_t <= _matlab_datenum(end_dt))
        mask_n = (HNN_t >= _matlab_datenum(start_dt)) & (HNN_t <= _matlab_datenum(end_dt))
        mask_e = (HNE_t >= _matlab_datenum(start_dt)) & (HNE_t <= _matlab_datenum(end_dt))

        TArray1Z.append(HNZ_t[mask_z])
        TArray1N.append(HNN_t[mask_n])
        TArray1E.append(HNE_t[mask_e])

        Array1Z.append(HNZ_d[mask_z])
        Array1N.append(HNN_d[mask_n])
        Array1E.append(HNE_d[mask_e])

    # Convert lists-of-arrays to ragged cell arrays equivalent (Python objects)
    # but also create concatenated matrices similar to MATLABʼs cell2mat call.
    # Ensure all three concatenated channels align in length to avoid mismatch.
    cat_z = np.concatenate(Array1Z, axis=0) if Array1Z else np.array([])
    cat_n = np.concatenate(Array1N, axis=0) if Array1N else np.array([])
    cat_e = np.concatenate(Array1E, axis=0) if Array1E else np.array([])

    if cat_z.size and cat_n.size and cat_e.size:
        min_len = min(cat_z.size, cat_n.size, cat_e.size)
        if not (cat_z.size == cat_n.size == cat_e.size):
            warnings.warn(
                f"Channel lengths differ (Z={cat_z.size}, N={cat_n.size}, E={cat_e.size}); "
                f"truncating to {min_len} samples for alignment.",
                RuntimeWarning,
            )
        cat_z = cat_z[:min_len]
        cat_n = cat_n[:min_len]
        cat_e = cat_e[:min_len]
    # Build time vector to match concatenated length (prefer E if present)
    total_len = cat_e.size or cat_z.size or cat_n.size
    time1 = np.arange(total_len, dtype=float) / sampling_rate

    out_dict = {
        "TArray1Z": pd.Series(TArray1Z, dtype=object).values,
        "TArray1N": pd.Series(TArray1N, dtype=object).values,
        "TArray1E": pd.Series(TArray1E, dtype=object).values,
        "Array1Z": cat_z,
        "Array1N": cat_n,
        "Array1E": cat_e,
        "time1": time1,
        "Fs_Hz": float(sampling_rate),
    }

    output_dir = output_dir or Path.cwd()
    output_dir.mkdir(parents=True, exist_ok=True)
    mat_path = output_dir / f"ArrayData_HV{station_id}.mat"
    savemat(mat_path, out_dict)

    if verbose:
        print(f"Saved results to {mat_path.resolve()}")


# -----------------------------------------------------------------------------
# CLI entry-point
# -----------------------------------------------------------------------------


def _cli():  # pragma: no cover
    p = argparse.ArgumentParser(description="Ported MiniseedArrayReduction to Python")
    p.add_argument("csv", type=Path, help="CSV file with start/end columns")
    p.add_argument("pattern", type=str, help="Filename pattern with {date} {hour} and {station}")
    p.add_argument("station", type=int, help="Station number")
    p.add_argument("--sr", type=float, default=500.0, help="Sampling rate (Hz)")
    p.add_argument("--out", type=Path, default=".", help="Output directory")
    p.add_argument("--quiet", action="store_true", help="Suppress verbose output")
    args = p.parse_args()

    process_station(
        csv_path=args.csv,
        pattern=args.pattern,
        sampling_rate=args.sr,
        station_id=args.station,
        output_dir=args.out,
        verbose=not args.quiet,
    )






if __name__ == "__main__":  # pragma: no cover
    _cli() 