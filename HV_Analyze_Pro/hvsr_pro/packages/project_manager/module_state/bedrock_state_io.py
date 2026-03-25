"""
Bedrock Mapping state I/O — save and restore bedrock mapping state
to/from a project folder.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np


def _ndarray_to_list(obj: Any) -> Any:
    """JSON serializer helper for numpy arrays."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    return str(obj)


def save_bedrock_state(
    bedrock_dir: str | Path,
    stations_data: Optional[List[Dict[str, Any]]] = None,
    surface_data: Optional[Dict[str, Any]] = None,
    bedrock_data: Optional[Dict[str, Any]] = None,
    interpolation_settings: Optional[Dict[str, Any]] = None,
    depth_data: Optional[Dict[str, Any]] = None,
) -> None:
    """Save bedrock mapping state to a project folder.

    Parameters
    ----------
    bedrock_dir : path
        Project bedrock subfolder (e.g. ``project/bedrock_mapping/map_001/``).
    stations_data : list of dict
        Station collection as list of dicts.
    surface_data : dict
        Surface elevation data (x, y, z arrays).
    bedrock_data : dict
        Bedrock elevation data.
    interpolation_settings : dict
        Interpolation method and parameters.
    depth_data : dict
        Depth-to-bedrock results.
    """
    bedrock_dir = Path(bedrock_dir)
    bedrock_dir.mkdir(parents=True, exist_ok=True)

    state = {
        "stations_data": stations_data or [],
        "surface_data": surface_data,
        "bedrock_data": bedrock_data,
        "interpolation_settings": interpolation_settings or {},
        "depth_data": depth_data,
    }

    with open(bedrock_dir / "state.json", "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False, default=_ndarray_to_list)

    # Also save stations as CSV for easy viewing
    if stations_data:
        import csv
        csv_path = bedrock_dir / "stations.csv"
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            if stations_data:
                writer = csv.DictWriter(f, fieldnames=stations_data[0].keys())
                writer.writeheader()
                writer.writerows(stations_data)


def load_bedrock_state(
    bedrock_dir: str | Path,
) -> Dict[str, Any]:
    """Load bedrock mapping state from a project folder.

    Returns
    -------
    dict
        Keys: ``stations_data``, ``surface_data``, ``bedrock_data``,
        ``interpolation_settings``, ``depth_data``.
    """
    bedrock_dir = Path(bedrock_dir)
    result: Dict[str, Any] = {
        "stations_data": [],
        "surface_data": None,
        "bedrock_data": None,
        "interpolation_settings": {},
        "depth_data": None,
    }

    state_file = bedrock_dir / "state.json"
    if state_file.exists():
        with open(state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        result.update(data)

    return result


def has_bedrock_state(bedrock_dir: str | Path) -> bool:
    """Check if a bedrock folder has saved state."""
    bedrock_dir = Path(bedrock_dir)
    return (bedrock_dir / "state.json").exists()
