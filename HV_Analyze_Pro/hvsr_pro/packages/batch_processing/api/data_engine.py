"""
Batch Processing API — Data Preparation Engine (Phase 1)
========================================================

Converts raw seismic files into ArrayData.mat files for each
(station × time_window) combination. This is the headless equivalent
of ``workers/data_worker.py``.

Three pipelines:
    1. **full_duration** — no time windows, use entire file
    2. **miniseed_with_windows** — ObsPy read+merge+trim by UTCDateTime
    3. **generic_with_windows** — hvsr_pro loaders (no time-window trimming)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from .config import StationDef, TimeWindowDef

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────
# Result dataclass
# ────────────────────────────────────────────────────────────────────

@dataclass
class DataResult:
    """Result of data preparation for one (station × window)."""

    station_id: int
    station_name: str
    window_name: str
    output_dir: str           # directory containing the MAT file
    mat_path: str             # full path to ArrayData_STN##.mat
    sampling_rate: float
    data_length_seconds: float
    success: bool = True
    error: str = ""


# ────────────────────────────────────────────────────────────────────
# Format detection
# ────────────────────────────────────────────────────────────────────

_MINISEED_EXTENSIONS = {".miniseed", ".mseed"}


def _is_miniseed(path: str) -> bool:
    """Check if a file is MiniSEED format by extension."""
    _, ext = os.path.splitext(path)
    return ext.lower() in _MINISEED_EXTENSIONS


def _all_files_are_miniseed(station_files: Dict[int, List[str]]) -> bool:
    """Return True if every file across all stations is MiniSEED."""
    for files in station_files.values():
        for f in files:
            if not _is_miniseed(f):
                return False
    return True


# ────────────────────────────────────────────────────────────────────
# Component extraction (shared by all pipelines)
# ────────────────────────────────────────────────────────────────────

def _extract_components_from_stream(stream) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Extract Z, N, E component arrays from an ObsPy Stream.

    Channel mapping: last character of channel code.
    Z → vertical, N/1 → north, E/2 → east.
    """
    arrays_z, arrays_n, arrays_e = [], [], []

    for tr in stream:
        comp = tr.stats.channel[-1].upper() if tr.stats.channel else "Z"
        if len(tr.data) == 0:
            continue
        data = tr.data.astype(np.float64)
        if comp == "Z":
            arrays_z.append(data)
        elif comp in ("N", "1"):
            arrays_n.append(data)
        elif comp in ("E", "2"):
            arrays_e.append(data)

    def _concat(arrays):
        if len(arrays) > 1:
            return np.concatenate(arrays)
        elif len(arrays) == 1:
            return arrays[0]
        return np.array([], dtype=np.float64)

    return _concat(arrays_z), _concat(arrays_n), _concat(arrays_e)


# ────────────────────────────────────────────────────────────────────
# MAT file writer
# ────────────────────────────────────────────────────────────────────

def _save_arrays(
    z: np.ndarray,
    n: np.ndarray,
    e: np.ndarray,
    fs: float,
    station_id: int,
    station_name: str,
    window_name: str,
    output_dir: str,
) -> DataResult:
    """Save Z/N/E arrays to ``ArrayData_{station}.mat`` and return result."""
    from scipy.io import savemat

    win_dir = os.path.join(output_dir, window_name)
    stn_dir = os.path.join(win_dir, station_name)
    os.makedirs(stn_dir, exist_ok=True)

    mat_path = os.path.join(stn_dir, f"ArrayData_{station_name}.mat")
    savemat(mat_path, {
        "Array1Z": z,
        "Array1N": n,
        "Array1E": e,
        "Fs_Hz": fs,
    })

    data_len = len(z) / fs if len(z) > 0 else 0.0

    return DataResult(
        station_id=station_id,
        station_name=station_name,
        window_name=window_name,
        output_dir=stn_dir,
        mat_path=mat_path,
        sampling_rate=fs,
        data_length_seconds=data_len,
    )


# ────────────────────────────────────────────────────────────────────
# Pipeline 1: Full Duration (no time windows)
# ────────────────────────────────────────────────────────────────────

def _process_full_duration(
    station_files: Dict[int, List[str]],
    output_dir: str,
    all_miniseed: bool,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> List[DataResult]:
    """Process all stations using the full file duration."""
    results = []
    total = len(station_files)
    win_name = "FullDuration"

    if all_miniseed:
        from obspy import read, Stream

        for idx, (stn_id, files) in enumerate(sorted(station_files.items())):
            pct = 15 + int(80 * (idx + 1) / max(1, total))
            station_name = f"STN{stn_id:02d}"
            if progress_callback:
                progress_callback(pct, f"Loading {station_name} (MiniSEED full duration)...")

            combined = Stream()
            fs_detected = None

            for f in files:
                try:
                    st = read(f)
                    combined += st
                    if fs_detected is None and len(st) > 0:
                        fs_detected = st[0].stats.sampling_rate
                except Exception as exc:
                    logger.warning("Could not read %s: %s", os.path.basename(f), exc)

            if len(combined) == 0:
                logger.warning("No readable files for Station #%d", stn_id)
                continue

            try:
                combined.merge(method=1, fill_value=0)
            except Exception as exc:
                logger.warning("Merge issue for Station #%d: %s", stn_id, exc)

            fs = fs_detected or 200.0
            z, n, e = _extract_components_from_stream(combined)

            if len(z) == 0 and len(n) == 0 and len(e) == 0:
                logger.warning("No component data for %s", station_name)
                continue

            result = _save_arrays(z, n, e, fs, stn_id, station_name, win_name, output_dir)
            results.append(result)
            logger.info("%s: %.1fs saved", station_name, result.data_length_seconds)

    else:
        # Generic formats via hvsr_pro loaders
        try:
            from hvsr_pro.packages.batch_processing.data_adapter import load_and_convert
        except ImportError:
            logger.error("hvsr_pro loaders not available for non-MiniSEED files")
            return results

        for idx, (stn_id, files) in enumerate(sorted(station_files.items())):
            pct = 15 + int(80 * (idx + 1) / max(1, total))
            station_name = f"STN{stn_id:02d}"
            if progress_callback:
                progress_callback(pct, f"Loading {station_name} (generic full duration)...")

            try:
                z, n, e, fs = load_and_convert(files[0])
            except Exception as exc:
                logger.warning("Could not load %s: %s", station_name, exc)
                results.append(DataResult(
                    station_id=stn_id, station_name=station_name,
                    window_name=win_name, output_dir="", mat_path="",
                    sampling_rate=0.0, data_length_seconds=0.0,
                    success=False, error=str(exc),
                ))
                continue

            result = _save_arrays(z, n, e, fs, stn_id, station_name, win_name, output_dir)
            results.append(result)

    return results


# ────────────────────────────────────────────────────────────────────
# Pipeline 2: MiniSEED with time-window trimming
# ────────────────────────────────────────────────────────────────────

def _process_miniseed_with_windows(
    station_files: Dict[int, List[str]],
    time_windows: List[TimeWindowDef],
    output_dir: str,
    station_assignments: Optional[Dict[str, List[int]]] = None,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> List[DataResult]:
    """Process MiniSEED files with ObsPy time-window trimming."""
    from obspy import read, UTCDateTime, Stream

    results = []

    # 1. Load all station data once
    if progress_callback:
        progress_callback(10, "Loading MiniSEED station data...")

    station_streams: Dict[int, Tuple] = {}  # stn_id → (stream, fs, start, end)

    for stn_id, files in sorted(station_files.items()):
        combined = Stream()
        fs_detected = None

        for f in files:
            try:
                st = read(f)
                combined += st
                if fs_detected is None and len(st) > 0:
                    fs_detected = st[0].stats.sampling_rate
            except Exception as exc:
                logger.warning("Could not read %s: %s", os.path.basename(f), exc)

        if len(combined) == 0:
            logger.warning("No readable files for Station #%d", stn_id)
            continue

        data_start = min(tr.stats.starttime for tr in combined)
        data_end = max(tr.stats.endtime for tr in combined)

        try:
            combined.merge(method=1, fill_value=0)
        except Exception as exc:
            logger.warning("Merge issue for Station #%d: %s", stn_id, exc)

        station_streams[stn_id] = (combined, fs_detected or 200.0, data_start, data_end)

    # 2. Build per-station window assignment index
    stn_to_windows: Dict[int, set] = {}
    if station_assignments:
        for win_idx, window in enumerate(time_windows):
            assigned = station_assignments.get(window.name, [])
            for stn_id in assigned:
                stn_to_windows.setdefault(stn_id, set()).add(win_idx)

    # 3. Count tasks for progress
    if stn_to_windows:
        total_tasks = sum(
            len(wins) for stn_id, wins in stn_to_windows.items()
            if stn_id in station_streams
        )
    else:
        total_tasks = len(time_windows) * len(station_streams)
    total_tasks = max(total_tasks, 1)

    # 4. Process each (window × station)
    task_idx = 0
    for win_idx, window in enumerate(time_windows):
        start_utc = UTCDateTime(window.start_utc)
        end_utc = UTCDateTime(window.end_utc)

        if progress_callback:
            progress_callback(
                15 + int(80 * task_idx / total_tasks),
                f"Window '{window.name}' ({win_idx+1}/{len(time_windows)})...",
            )

        for stn_id, (stream_orig, fs, data_start, data_end) in station_streams.items():
            # Skip if station not assigned to this window
            if stn_to_windows and win_idx not in stn_to_windows.get(stn_id, set()):
                continue

            task_idx += 1
            station_name = f"STN{stn_id:02d}"

            if progress_callback:
                pct = 15 + int(80 * task_idx / total_tasks)
                progress_callback(pct, f"  {window.name}/{station_name}...")

            stream_copy = stream_orig.copy()
            stream_copy.trim(starttime=start_utc, endtime=end_utc)

            if len(stream_copy) == 0 or all(len(tr.data) == 0 for tr in stream_copy):
                logger.warning(
                    "No data for %s/%s (requested %s–%s, available %s–%s)",
                    window.name, station_name, start_utc, end_utc, data_start, data_end,
                )
                continue

            z, n, e = _extract_components_from_stream(stream_copy)

            if len(z) == 0 and len(n) == 0 and len(e) == 0:
                logger.warning("No component data for %s/%s", window.name, station_name)
                continue

            result = _save_arrays(z, n, e, fs, stn_id, station_name, window.name, output_dir)
            results.append(result)

    return results


# ────────────────────────────────────────────────────────────────────
# Pipeline 3: Generic formats (no time-window trimming)
# ────────────────────────────────────────────────────────────────────

def _process_generic_with_windows(
    station_files: Dict[int, List[str]],
    time_windows: List[TimeWindowDef],
    output_dir: str,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> List[DataResult]:
    """Process non-MiniSEED files (no time-window trimming capability)."""
    try:
        from hvsr_pro.packages.batch_processing.data_adapter import load_and_convert
    except ImportError:
        logger.error("hvsr_pro loaders not available")
        return []

    results = []
    total_tasks = max(len(time_windows) * len(station_files), 1)

    # Load all station data once
    station_data: Dict[int, Tuple] = {}
    for stn_id, files in sorted(station_files.items()):
        try:
            z, n, e, fs = load_and_convert(files[0])
            station_data[stn_id] = (z, n, e, fs)
        except Exception as exc:
            logger.warning("Could not load STN%02d: %s", stn_id, exc)

    # Process each (window × station)
    task_idx = 0
    for win_idx, window in enumerate(time_windows):
        for stn_id, (z, n, e, fs) in station_data.items():
            task_idx += 1
            station_name = f"STN{stn_id:02d}"

            if progress_callback:
                pct = 15 + int(80 * task_idx / total_tasks)
                progress_callback(pct, f"  {window.name}/{station_name}...")

            result = _save_arrays(z, n, e, fs, stn_id, station_name, window.name, output_dir)
            results.append(result)

    return results


# ────────────────────────────────────────────────────────────────────
# Public API
# ────────────────────────────────────────────────────────────────────

def prepare_station_data(
    stations: List[StationDef],
    output_dir: str,
    time_windows: Optional[List[TimeWindowDef]] = None,
    station_assignments: Optional[Dict[str, List[int]]] = None,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> List[DataResult]:
    """
    Prepare seismic data for batch HVSR analysis.

    Converts raw seismic files into ArrayData.mat files for each
    (station × time_window) combination.

    Parameters
    ----------
    stations : list[StationDef]
        Station definitions with associated file paths.
    output_dir : str
        Base output directory for all ArrayData files.
    time_windows : list[TimeWindowDef], optional
        Time windows for data extraction. If ``None`` or empty,
        uses full file duration.
    station_assignments : dict[str, list[int]], optional
        Maps window name → list of station numbers.
        If not provided, all stations are processed in every window.
    progress_callback : callable, optional
        ``callback(percent: int, message: str)`` for progress reporting.

    Returns
    -------
    list[DataResult]
        One result per (station × window) successfully processed.
    """
    if progress_callback:
        progress_callback(5, "Preparing station data...")

    os.makedirs(output_dir, exist_ok=True)

    # Build station_files dict: station_num → [file_paths]
    station_files: Dict[int, List[str]] = {}
    for stn in stations:
        if stn.files:
            station_files[stn.station_num] = list(stn.files)

    if not station_files:
        logger.error("No station files to process")
        return []

    # Detect formats
    all_miniseed = _all_files_are_miniseed(station_files)
    use_full_duration = not time_windows

    if use_full_duration:
        results = _process_full_duration(
            station_files, output_dir, all_miniseed, progress_callback,
        )
    elif all_miniseed:
        results = _process_miniseed_with_windows(
            station_files, time_windows, output_dir,
            station_assignments, progress_callback,
        )
    else:
        results = _process_generic_with_windows(
            station_files, time_windows, output_dir, progress_callback,
        )

    if progress_callback:
        progress_callback(95, f"Data preparation complete: {len(results)} file(s)")

    logger.info(
        "Data preparation: %d results from %d station(s)",
        len(results), len(station_files),
    )

    return results
