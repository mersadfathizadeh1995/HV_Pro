"""
Batch Processing API — Station Operations
==========================================

Pure-function station management: file grouping, sensor routing,
station/time-window import from CSV and folders.

No Qt dependencies — all functions work headlessly.
"""

from __future__ import annotations

import csv
import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from .config import (
    SensorDef,
    StationDef,
    TimeWindowDef,
    TZ_OFFSETS,
)


# ────────────────────────────────────────────────────────────────────
# Station Number Extraction
# ────────────────────────────────────────────────────────────────────

# Regex patterns in priority order (highest → lowest)
_STATION_PATTERNS = [
    # 1. STN01, STN02, … (case-insensitive)
    (re.compile(r'STN(\d{1,2})', re.IGNORECASE), None),
    # 2. Centaur serial → station mapping (0655→1, 0656→2, …, 0664→10)
    (re.compile(r'centaur-3_(\d{4})_', re.IGNORECASE), "centaur"),
    # 3. Generic station pattern (station01, station_02, station-3)
    (re.compile(r'station[_-]?(\d{1,2})', re.IGNORECASE), None),
    # 4. Letter prefix + digits at start (XX01, AR02, etc.)
    (re.compile(r'^[A-Za-z]{1,4}(\d{1,2})(?:[_.\-]|$)'), None),
    # 5. Trailing number before extension (_01.saf, -02.sac)
    (re.compile(r'[_-](\d{1,2})\.[a-zA-Z]+$'), None),
]


def extract_station_number(filename: str) -> Optional[int]:
    """
    Extract station number from a filename using multiple regex patterns.

    Supports:
        - ``AR.STN01.centaur-3_0655_*`` — STN pattern
        - ``centaur-3_0655_*`` — Centaur serial (0655→1, 0656→2, …)
        - ``station01.saf`` — generic station## pattern
        - ``XX01_pt1.txt`` — letter prefix + digits
        - ``_01.saf`` — trailing number before extension

    Parameters
    ----------
    filename : str
        Bare filename (not full path).

    Returns
    -------
    int or None
        Station number (1-based) or ``None`` if undetectable.
    """
    for pattern, kind in _STATION_PATTERNS:
        match = pattern.search(filename)
        if match:
            if kind == "centaur":
                centaur_id = int(match.group(1))
                if 655 <= centaur_id <= 664:
                    return centaur_id - 654
                continue  # outside known range — try next pattern
            return int(match.group(1))
    return None


# ────────────────────────────────────────────────────────────────────
# File Grouping
# ────────────────────────────────────────────────────────────────────

# Supported extensions (same as data_adapter.get_supported_extensions)
_SUPPORTED_EXTENSIONS = (
    ".txt", ".miniseed", ".mseed", ".saf", ".sac",
    ".gcf", ".peer", ".at2", ".csv",
)


def group_files_by_station(
    file_paths: List[str],
    extensions: Optional[Tuple[str, ...]] = None,
) -> Tuple[Dict[int, List[str]], List[str]]:
    """
    Group file paths by auto-detected station number.

    Parameters
    ----------
    file_paths : list[str]
        Full paths to seismic data files.
    extensions : tuple[str, ...], optional
        Filter to these extensions (case-insensitive).
        Defaults to all supported seismic formats.

    Returns
    -------
    (station_files, unmatched)
        ``station_files``: dict mapping station_num → list of paths.
        ``unmatched``: list of paths that could not be assigned.
    """
    if extensions is None:
        extensions = _SUPPORTED_EXTENSIONS

    station_files: Dict[int, List[str]] = {}
    unmatched: List[str] = []

    for fpath in file_paths:
        fname = os.path.basename(fpath)
        if not fname.lower().endswith(extensions):
            continue

        stn_num = extract_station_number(fname)
        if stn_num is not None:
            station_files.setdefault(stn_num, []).append(fpath)
        else:
            unmatched.append(fpath)

    return station_files, unmatched


# ────────────────────────────────────────────────────────────────────
# Station Import
# ────────────────────────────────────────────────────────────────────

def import_stations_from_folder(
    folder: str,
    extensions: Optional[Tuple[str, ...]] = None,
    recursive: bool = False,
) -> Tuple[List[StationDef], List[str]]:
    """
    Scan a folder for seismic files and group them into stations.

    Parameters
    ----------
    folder : str
        Path to the folder containing seismic data files.
    extensions : tuple[str, ...], optional
        Only include files with these extensions.
    recursive : bool
        If ``True``, also scan subdirectories.

    Returns
    -------
    (stations, unmatched)
        ``stations``: list of ``StationDef`` with files assigned.
        ``unmatched``: file paths that could not be assigned to a station.
    """
    if extensions is None:
        extensions = _SUPPORTED_EXTENSIONS

    file_paths = []
    if recursive:
        for root, _dirs, files in os.walk(folder):
            for f in files:
                if f.lower().endswith(extensions):
                    file_paths.append(os.path.join(root, f))
    else:
        for f in os.listdir(folder):
            full = os.path.join(folder, f)
            if os.path.isfile(full) and f.lower().endswith(extensions):
                file_paths.append(full)

    station_files, unmatched = group_files_by_station(
        file_paths, extensions
    )

    stations = []
    for stn_num in sorted(station_files.keys()):
        stations.append(StationDef(
            station_num=stn_num,
            files=sorted(station_files[stn_num]),
        ))

    return stations, unmatched


def import_stations_from_csv(csv_path: str) -> List[StationDef]:
    """
    Import station definitions from a CSV file.

    Expected CSV columns: ``station_num, station_name, files, sensor_id``
    where ``files`` is a pipe-separated list of absolute paths.

    Parameters
    ----------
    csv_path : str
        Path to the CSV file.

    Returns
    -------
    list[StationDef]
    """
    stations = []
    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stn_num = int(row.get("station_num", 0))
            if stn_num <= 0:
                continue
            files_str = row.get("files", "")
            files = [p.strip() for p in files_str.split("|") if p.strip()]
            stations.append(StationDef(
                station_num=stn_num,
                station_name=row.get("station_name", ""),
                files=files,
                sensor_id=row.get("sensor_id", ""),
                sensor_name=row.get("sensor_name", ""),
            ))
    return stations


# ────────────────────────────────────────────────────────────────────
# Sensor Operations
# ────────────────────────────────────────────────────────────────────

def create_default_sensors(n_sensors: int = 6) -> List[SensorDef]:
    """
    Create default Centaur sensor definitions.

    Generates sensors for Centaur serial numbers 0655–0660 (or more).
    Each sensor matches filenames containing its serial number.

    Parameters
    ----------
    n_sensors : int
        Number of sensors to create (default 6).

    Returns
    -------
    list[SensorDef]
    """
    sensors = []
    for i in range(n_sensors):
        serial = 655 + i
        stn_num = i + 1
        sensors.append(SensorDef(
            sensor_id=str(stn_num),
            display_name=f"Centaur {serial:04d}",
            file_patterns=[
                rf"centaur-3_{serial:04d}_",
                rf"\.STN{stn_num:02d}\.",
            ],
        ))
    return sensors


def auto_detect_sensors(filenames: List[str]) -> List[SensorDef]:
    """
    Auto-detect sensor definitions from a set of filenames.

    Currently detects Centaur serial patterns (``centaur-3_NNNN_``).

    Parameters
    ----------
    filenames : list[str]
        Filenames (not full paths) to scan.

    Returns
    -------
    list[SensorDef]
        Detected sensors, or empty list if none found.
    """
    serials: Dict[int, List[str]] = {}
    for fname in filenames:
        m = re.search(r'centaur-3_(\d{4})_', fname, re.IGNORECASE)
        if m:
            serial = int(m.group(1))
            serials.setdefault(serial, []).append(fname)

    if not serials:
        return []

    sensors = []
    for i, serial in enumerate(sorted(serials.keys()), start=1):
        sensors.append(SensorDef(
            sensor_id=str(i),
            display_name=f"Centaur {serial:04d}",
            file_patterns=[rf"centaur-3_{serial:04d}_"],
        ))
    return sensors


def route_files_via_sensors(
    file_paths: List[str],
    sensors: List[SensorDef],
    sensor_station_map: Dict[str, List[int]],
) -> Tuple[Dict[int, List[str]], List[str]]:
    """
    Route files to stations via sensor pattern matching.

    Each file is matched against sensor patterns. When a sensor maps
    to multiple stations, the file is added to ALL matched stations
    (disambiguation by time window is done later).

    Parameters
    ----------
    file_paths : list[str]
        Full file paths to route.
    sensors : list[SensorDef]
        Sensor definitions with regex file_patterns.
    sensor_station_map : dict[str, list[int]]
        Maps ``sensor_id`` → list of station numbers.

    Returns
    -------
    (station_files, unmatched)
    """
    station_files: Dict[int, List[str]] = {}
    unmatched: List[str] = []

    for fpath in file_paths:
        fname = os.path.basename(fpath)
        matched_sensor = None

        for sensor in sensors:
            for pat in sensor.file_patterns:
                try:
                    if re.search(pat, fname, re.IGNORECASE):
                        matched_sensor = sensor
                        break
                except re.error:
                    continue
            if matched_sensor:
                break

        if matched_sensor is None:
            unmatched.append(fpath)
            continue

        stations = sensor_station_map.get(matched_sensor.sensor_id, [])
        if not stations:
            unmatched.append(fpath)
            continue

        for stn_num in stations:
            station_files.setdefault(stn_num, []).append(fpath)

    return station_files, unmatched


# ────────────────────────────────────────────────────────────────────
# Time Window Import / Export
# ────────────────────────────────────────────────────────────────────

_DT_FMT = "%Y-%m-%d %H:%M:%S"


def import_time_windows_from_csv(
    csv_path: str,
    timezone: str = "UTC",
) -> List[TimeWindowDef]:
    """
    Import time windows from a 13-column CSV file.

    CSV columns: ``Config, S_Year, S_Month, S_Day, S_Hour, S_Min, S_Sec,
    E_Year, E_Month, E_Day, E_Hour, E_Min, E_Sec``

    Times in the CSV are interpreted as local time in the given timezone,
    then converted to UTC.

    Parameters
    ----------
    csv_path : str
        Path to the CSV file.
    timezone : str
        Timezone label (``"UTC"``, ``"CST"``, ``"CDT"``).

    Returns
    -------
    list[TimeWindowDef]
    """
    offset_hours = TZ_OFFSETS.get(timezone.upper(), 0)
    offset = timedelta(hours=offset_hours)
    windows = []

    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)  # skip header

        for row in reader:
            if len(row) < 13:
                continue
            try:
                name = row[0].strip()
                start_local = datetime(
                    int(row[1]), int(row[2]), int(row[3]),
                    int(row[4]), int(row[5]), int(row[6]),
                )
                end_local = datetime(
                    int(row[7]), int(row[8]), int(row[9]),
                    int(row[10]), int(row[11]), int(row[12]),
                )
                start_utc = start_local + offset
                end_utc = end_local + offset

                windows.append(TimeWindowDef(
                    name=name,
                    start_utc=start_utc.strftime(_DT_FMT),
                    end_utc=end_utc.strftime(_DT_FMT),
                    start_local=start_local.strftime(_DT_FMT),
                    end_local=end_local.strftime(_DT_FMT),
                ))
            except (ValueError, IndexError):
                continue

    return windows


def export_time_windows_to_csv(
    windows: List[TimeWindowDef],
    csv_path: str,
) -> str:
    """
    Export time windows to a 13-column CSV file (using local times).

    Parameters
    ----------
    windows : list[TimeWindowDef]
        Time windows to export.
    csv_path : str
        Output file path.

    Returns
    -------
    str
        The output path.
    """
    os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Config",
            "S_Year", "S_Month", "S_Day", "S_Hour", "S_Min", "S_Sec",
            "E_Year", "E_Month", "E_Day", "E_Hour", "E_Min", "E_Sec",
        ])
        for win in windows:
            s = datetime.strptime(win.start_local, _DT_FMT) if win.start_local else None
            e = datetime.strptime(win.end_local, _DT_FMT) if win.end_local else None
            if s and e:
                writer.writerow([
                    win.name,
                    s.year, s.month, s.day, s.hour, s.minute, s.second,
                    e.year, e.month, e.day, e.hour, e.minute, e.second,
                ])

    return csv_path


def convert_local_to_utc(
    local_str: str,
    timezone: str = "UTC",
) -> str:
    """
    Convert a local datetime string to UTC.

    Parameters
    ----------
    local_str : str
        Datetime in ``"%Y-%m-%d %H:%M:%S"`` format.
    timezone : str
        Source timezone label.

    Returns
    -------
    str
        UTC datetime in the same format.
    """
    offset_hours = TZ_OFFSETS.get(timezone.upper(), 0)
    dt = datetime.strptime(local_str, _DT_FMT)
    utc = dt + timedelta(hours=offset_hours)
    return utc.strftime(_DT_FMT)


def make_time_window(
    name: str,
    start: str,
    end: str,
    timezone: str = "UTC",
    assigned_stations: Optional[List[int]] = None,
) -> TimeWindowDef:
    """
    Create a ``TimeWindowDef`` from local times with timezone conversion.

    Parameters
    ----------
    name : str
        Window name.
    start, end : str
        Local datetime strings (``"%Y-%m-%d %H:%M:%S"`` or ISO 8601).
    timezone : str
        Timezone label.
    assigned_stations : list[int], optional
        Station numbers assigned to this window. ``None`` = all.

    Returns
    -------
    TimeWindowDef
    """
    # Normalize to standard format
    start_local = _normalize_dt(start)
    end_local = _normalize_dt(end)
    start_utc = convert_local_to_utc(start_local, timezone)
    end_utc = convert_local_to_utc(end_local, timezone)

    return TimeWindowDef(
        name=name,
        start_utc=start_utc,
        end_utc=end_utc,
        start_local=start_local,
        end_local=end_local,
        assigned_stations=assigned_stations,
    )


def _normalize_dt(dt_str: str) -> str:
    """Normalize datetime string to ``%Y-%m-%d %H:%M:%S``."""
    # Handle ISO 8601 with T separator
    dt_str = dt_str.replace("T", " ").strip()
    # Strip timezone suffix if present
    for suffix in ("Z", "+00:00"):
        if dt_str.endswith(suffix):
            dt_str = dt_str[: -len(suffix)]
    dt = datetime.strptime(dt_str, _DT_FMT)
    return dt.strftime(_DT_FMT)


# ────────────────────────────────────────────────────────────────────
# Sensor Config Persistence
# ────────────────────────────────────────────────────────────────────

import json
import logging

logger = logging.getLogger(__name__)


def save_sensor_config(
    sensors: List[SensorDef],
    json_path: str,
) -> str:
    """
    Save sensor definitions to a JSON file.

    Parameters
    ----------
    sensors : list[SensorDef]
        Sensor definitions to persist.
    json_path : str
        Output file path.

    Returns
    -------
    str
        The output path.
    """
    os.makedirs(os.path.dirname(json_path) or ".", exist_ok=True)
    data = [s.to_dict() for s in sensors]
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.info("Saved %d sensor configs to %s", len(sensors), json_path)
    return json_path


def load_sensor_config(json_path: str) -> List[SensorDef]:
    """
    Load sensor definitions from a JSON file.

    Parameters
    ----------
    json_path : str
        Path to the JSON file.

    Returns
    -------
    list[SensorDef]
    """
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    sensors = [SensorDef.from_dict(d) for d in data]
    logger.info("Loaded %d sensor configs from %s", len(sensors), json_path)
    return sensors


# ────────────────────────────────────────────────────────────────────
# Auto-distribute Stations to Time Windows
# ────────────────────────────────────────────────────────────────────

def auto_distribute_stations(
    stations: List[StationDef],
    windows: List[TimeWindowDef],
    mode: str = "all",
) -> Dict[str, List[int]]:
    """
    Auto-assign stations to time windows.

    Parameters
    ----------
    stations : list[StationDef]
        Available stations.
    windows : list[TimeWindowDef]
        Available time windows.
    mode : str
        ``"all"`` — assign all stations to all windows.
        ``"round_robin"`` — distribute stations evenly across windows.

    Returns
    -------
    dict[str, list[int]]
        Maps window name → list of station numbers.
    """
    station_nums = [s.station_num for s in stations]

    if mode == "round_robin":
        assignments: Dict[str, List[int]] = {w.name: [] for w in windows}
        for i, stn_num in enumerate(station_nums):
            win = windows[i % len(windows)]
            assignments[win.name].append(stn_num)
        return assignments

    # Default: all stations to all windows
    return {w.name: list(station_nums) for w in windows}
