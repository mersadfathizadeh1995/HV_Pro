"""
Bedrock Mapping state I/O — save and restore bedrock mapping state
to/from a project folder.

Saves JSON metadata + numpy ``.npz`` files for interpolated grids.
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


# ── GridData / DepthResult serialization ───────────────────────────

def _save_grid(path: Path, grid) -> None:
    """Serialize a GridData dataclass to an ``.npz`` file."""
    arrays = {
        "x_grid": grid.x_grid,
        "y_grid": grid.y_grid,
        "z_grid": grid.z_grid,
    }
    if grid.mask is not None:
        arrays["mask"] = grid.mask
    meta = {
        "x_min": float(grid.x_min),
        "x_max": float(grid.x_max),
        "y_min": float(grid.y_min),
        "y_max": float(grid.y_max),
        "resolution": int(grid.resolution),
        "method": str(grid.method),
    }
    arrays["_meta"] = np.array(json.dumps(meta), dtype=object)
    np.savez_compressed(str(path), **arrays)


def _load_grid(path: Path):
    """Deserialize a ``.npz`` file back to a GridData object."""
    from hvsr_pro.packages.bedrock_mapping.core.interpolation import GridData
    data = np.load(str(path), allow_pickle=True)
    meta = json.loads(str(data["_meta"]))
    mask = data["mask"] if "mask" in data else None
    return GridData(
        x_grid=data["x_grid"],
        y_grid=data["y_grid"],
        z_grid=data["z_grid"],
        x_min=meta["x_min"],
        x_max=meta["x_max"],
        y_min=meta["y_min"],
        y_max=meta["y_max"],
        resolution=meta["resolution"],
        method=meta["method"],
        mask=mask,
    )


def _save_depth(path: Path, dr) -> None:
    """Serialize a DepthResult dataclass to an ``.npz`` file."""
    arrays = {
        "x_grid": dr.x_grid,
        "y_grid": dr.y_grid,
        "depth_grid": dr.depth_grid,
        "surface_grid": dr.surface_grid,
        "bedrock_grid": dr.bedrock_grid,
    }
    if dr.mask is not None:
        arrays["mask"] = dr.mask
    meta = {
        "x_min": float(dr.x_min),
        "x_max": float(dr.x_max),
        "y_min": float(dr.y_min),
        "y_max": float(dr.y_max),
        "resolution": int(dr.resolution),
        "trim_mode": str(dr.trim_mode),
    }
    if dr.trim_boundary is not None:
        meta["trim_boundary"] = [list(p) for p in dr.trim_boundary]
    arrays["_meta"] = np.array(json.dumps(meta), dtype=object)
    np.savez_compressed(str(path), **arrays)


def _load_depth(path: Path):
    """Deserialize a ``.npz`` file back to a DepthResult object."""
    from hvsr_pro.packages.bedrock_mapping.core.bedrock import DepthResult
    data = np.load(str(path), allow_pickle=True)
    meta = json.loads(str(data["_meta"]))
    mask = data["mask"] if "mask" in data else None
    trim_boundary = meta.get("trim_boundary")
    if trim_boundary:
        trim_boundary = [tuple(p) for p in trim_boundary]
    return DepthResult(
        x_grid=data["x_grid"],
        y_grid=data["y_grid"],
        depth_grid=data["depth_grid"],
        surface_grid=data["surface_grid"],
        bedrock_grid=data["bedrock_grid"],
        x_min=meta["x_min"],
        x_max=meta["x_max"],
        y_min=meta["y_min"],
        y_max=meta["y_max"],
        resolution=meta["resolution"],
        mask=mask,
        trim_mode=meta.get("trim_mode", "none"),
        trim_boundary=trim_boundary,
    )


# ── Main save / load functions ─────────────────────────────────

def save_bedrock_state(
    bedrock_dir: str | Path,
    stations_data: Optional[List[Dict[str, Any]]] = None,
    surface_data: Optional[Dict[str, Any]] = None,
    bedrock_data: Optional[Dict[str, Any]] = None,
    interpolation_settings: Optional[Dict[str, Any]] = None,
    depth_data: Optional[Dict[str, Any]] = None,
    surface_grid=None,
    bedrock_grid=None,
    depth_result=None,
    display_settings: Optional[Dict[str, Any]] = None,
) -> None:
    """Save bedrock mapping state to a project folder.

    Parameters
    ----------
    bedrock_dir : path
        Project bedrock subfolder (e.g. ``project/bedrock_mapping/map_001/``).
    stations_data : list of dict
        Station collection as list of dicts.
    surface_data : dict
        Surface elevation source data (x, y, z lists).
    bedrock_data : dict
        Bedrock elevation source data.
    interpolation_settings : dict
        Interpolation method, resolution, etc.
    depth_data : dict
        Depth-to-bedrock scalar results.
    surface_grid : GridData, optional
        Interpolated surface grid (saved as ``.npz``).
    bedrock_grid : GridData, optional
        Interpolated bedrock grid (saved as ``.npz``).
    depth_result : DepthResult, optional
        Computed depth result (saved as ``.npz``).
    display_settings : dict, optional
        Contour configs, layer visibility, legend configs.
    """
    bedrock_dir = Path(bedrock_dir)
    bedrock_dir.mkdir(parents=True, exist_ok=True)

    state = {
        "stations_data": stations_data or [],
        "surface_data": surface_data,
        "bedrock_data": bedrock_data,
        "interpolation_settings": interpolation_settings or {},
        "depth_data": depth_data,
        "display_settings": display_settings,
        "has_surface_grid": surface_grid is not None,
        "has_bedrock_grid": bedrock_grid is not None,
        "has_depth_result": depth_result is not None,
    }

    with open(bedrock_dir / "state.json", "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False, default=_ndarray_to_list)

    # Save grids as compressed numpy archives
    if surface_grid is not None:
        _save_grid(bedrock_dir / "surface_grid.npz", surface_grid)
    if bedrock_grid is not None:
        _save_grid(bedrock_dir / "bedrock_grid.npz", bedrock_grid)
    if depth_result is not None:
        _save_depth(bedrock_dir / "depth_result.npz", depth_result)

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
        ``interpolation_settings``, ``depth_data``, ``display_settings``,
        and optionally ``surface_grid``, ``bedrock_grid``, ``depth_result``
        (reconstructed objects).
    """
    bedrock_dir = Path(bedrock_dir)
    result: Dict[str, Any] = {
        "stations_data": [],
        "surface_data": None,
        "bedrock_data": None,
        "interpolation_settings": {},
        "depth_data": None,
        "display_settings": None,
        "surface_grid": None,
        "bedrock_grid": None,
        "depth_result": None,
    }

    state_file = bedrock_dir / "state.json"
    if state_file.exists():
        with open(state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        result.update(data)

    # Restore grid objects from .npz files
    surface_npz = bedrock_dir / "surface_grid.npz"
    if surface_npz.exists():
        try:
            result["surface_grid"] = _load_grid(surface_npz)
        except Exception:
            pass

    bedrock_npz = bedrock_dir / "bedrock_grid.npz"
    if bedrock_npz.exists():
        try:
            result["bedrock_grid"] = _load_grid(bedrock_npz)
        except Exception:
            pass

    depth_npz = bedrock_dir / "depth_result.npz"
    if depth_npz.exists():
        try:
            result["depth_result"] = _load_depth(depth_npz)
        except Exception:
            pass

    return result


def has_bedrock_state(bedrock_dir: str | Path) -> bool:
    """Check if a bedrock folder has saved state."""
    bedrock_dir = Path(bedrock_dir)
    return (bedrock_dir / "state.json").exists()
