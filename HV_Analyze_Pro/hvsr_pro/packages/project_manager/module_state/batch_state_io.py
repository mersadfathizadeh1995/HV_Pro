"""
Batch Processing state I/O — save and restore batch processing state
to/from a project folder.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional


def save_batch_state(
    batch_dir: str | Path,
    station_entries: List[Dict[str, Any]],
    processed_results: Optional[List[Dict[str, Any]]] = None,
    data_worker_results: Optional[List[Dict[str, Any]]] = None,
    settings: Optional[Dict[str, Any]] = None,
    time_windows: Optional[Dict[str, Any]] = None,
    manual_peaks: Optional[List] = None,
    fig_settings: Optional[Dict[str, Any]] = None,
) -> None:
    """Save batch processing state to a project batch folder.

    Parameters
    ----------
    batch_dir : path
        Project batch subfolder (e.g. ``project/batch_processing/batch_001/``).
    station_entries : list of dict
        Each dict: ``{"station_num": int, "files": [str], "name": str}``.
    processed_results : list of dict, optional
        Workflow result summaries (peaks, valid_windows, etc.).
    data_worker_results : list of dict, optional
        Raw data-worker entries (station_name, dir, window_name, mat_path).
        Used to reload HVSR results from disk on restore.
    settings : dict, optional
        Processing settings snapshot.
    time_windows : dict, optional
        Time window configuration (timezone, windows, station_assignments).
    manual_peaks : list, optional
        User-picked median peaks from the Results canvas.
    fig_settings : dict, optional
        Figure export preferences.
    """
    batch_dir = Path(batch_dir)
    batch_dir.mkdir(parents=True, exist_ok=True)

    state = {
        "station_entries": station_entries,
        "processed_results": processed_results or [],
        "data_worker_results": data_worker_results or [],
        "time_windows": time_windows or {},
        "manual_peaks": manual_peaks or [],
        "fig_settings": fig_settings,
    }
    with open(batch_dir / "state.json", "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False, default=str)

    if settings:
        with open(batch_dir / "settings.json", "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False, default=str)


def load_batch_state(
    batch_dir: str | Path,
) -> Dict[str, Any]:
    """Load batch processing state from a project batch folder.

    Returns
    -------
    dict
        Keys: ``station_entries``, ``processed_results``, ``settings``.
        Any missing key returns an empty list/dict.
    """
    batch_dir = Path(batch_dir)
    result: Dict[str, Any] = {
        "station_entries": [],
        "processed_results": [],
        "data_worker_results": [],
        "settings": {},
        "time_windows": {},
        "manual_peaks": [],
        "fig_settings": None,
    }

    state_file = batch_dir / "state.json"
    if state_file.exists():
        with open(state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        result["station_entries"] = data.get("station_entries", [])
        result["processed_results"] = data.get("processed_results", [])
        result["data_worker_results"] = data.get("data_worker_results", [])
        result["time_windows"] = data.get("time_windows", {})
        result["manual_peaks"] = data.get("manual_peaks", [])
        result["fig_settings"] = data.get("fig_settings")

    settings_file = batch_dir / "settings.json"
    if settings_file.exists():
        with open(settings_file, "r", encoding="utf-8") as f:
            result["settings"] = json.load(f)

    return result


def has_batch_state(batch_dir: str | Path) -> bool:
    """Check if a batch folder has saved state."""
    batch_dir = Path(batch_dir)
    return (batch_dir / "state.json").exists()
