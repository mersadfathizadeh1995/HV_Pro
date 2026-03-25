"""
Data Bridge — merges results across modules.

Primary responsibility: after batch processing completes, combine the
station registry (coordinates, Vs) with batch peak results to produce
a ``combined_results.csv`` that bedrock mapping can consume directly.
"""

from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .project import Project


# ---------------------------------------------------------------------------
# batch_peaks.csv  (always writable — no coordinates needed)
# ---------------------------------------------------------------------------

def write_batch_peaks_csv(
    station_results: List[dict],
    output_path: str | Path,
    max_peaks: int = 3,
) -> Path:
    """Write a peaks-only CSV from batch results.

    Parameters
    ----------
    station_results : list of dict
        Each dict needs: ``station_name``, ``peaks`` (list of dicts with
        ``frequency`` and ``amplitude``), ``valid_windows``, ``total_windows``.
    output_path : path
        Where to write the CSV.
    max_peaks : int
        Maximum number of peaks to include per station.

    Returns
    -------
    Path
        The written file path.
    """
    output_path = Path(output_path)

    headers = ["station_name"]
    for i in range(max_peaks):
        headers.extend([f"f{i}", f"a{i}"])
    headers.extend(["valid_windows", "total_windows"])

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        for sr in station_results:
            row = [sr.get("station_name", "")]
            peaks = sr.get("peaks", [])
            # Sort by frequency ascending
            peaks_sorted = sorted(peaks, key=lambda p: p.get("frequency", 0))
            for i in range(max_peaks):
                if i < len(peaks_sorted):
                    row.append(peaks_sorted[i].get("frequency", ""))
                    row.append(peaks_sorted[i].get("amplitude", ""))
                else:
                    row.extend(["", ""])
            row.append(sr.get("valid_windows", ""))
            row.append(sr.get("total_windows", ""))
            writer.writerow(row)

    return output_path


# ---------------------------------------------------------------------------
# combined_results.csv  (includes coordinates when available)
# ---------------------------------------------------------------------------

def write_combined_results_csv(
    project: "Project",
    station_results: List[dict],
    batch_id: str,
    output_path: Optional[str | Path] = None,
    max_peaks: int = 3,
) -> Path:
    """Merge registry coordinates with batch peak results.

    If the project registry has coordinates for a station, they are included.
    If not, those fields are left empty — bedrock mapping will prompt the user
    to fill them in later.

    Parameters
    ----------
    project : Project
        The active project (provides station registry).
    station_results : list of dict
        Batch results.  Each needs ``station_name``, ``station_id``, ``peaks``.
    batch_id : str
        Which batch produced these results (e.g. "batch_001").
    output_path : path, optional
        Where to write.  Defaults to ``<project>/batch_processing/<batch_id>/combined_results.csv``.
    max_peaks : int
        Maximum peaks per station.

    Returns
    -------
    Path
        The written file path.
    """
    if output_path is None:
        output_path = project.batch_dir(batch_id) / "combined_results.csv"
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    headers = ["id", "name", "x", "y", "elevation", "vs_avg"]
    for i in range(max_peaks):
        headers.extend([f"f{i}", f"a{i}"])
    headers.extend(["valid_windows", "total_windows", "output_dir"])

    registry = project.registry

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(headers)

        for sr in station_results:
            stn_name = sr.get("station_name", "")
            stn_num = sr.get("station_id", 0)

            # Look up in registry
            reg_stn = registry.get_station(stn_name)
            if reg_stn is None:
                reg_stn = registry.get_by_batch_num(stn_num)

            row = [
                reg_stn.id if reg_stn else stn_name,
                reg_stn.display_name if reg_stn else stn_name,
                reg_stn.x if reg_stn else "",
                reg_stn.y if reg_stn else "",
                reg_stn.elevation if reg_stn else "",
                reg_stn.vs_avg if reg_stn else "",
            ]

            peaks = sr.get("peaks", [])
            peaks_sorted = sorted(peaks, key=lambda p: p.get("frequency", 0))
            for i in range(max_peaks):
                if i < len(peaks_sorted):
                    row.append(peaks_sorted[i].get("frequency", ""))
                    row.append(peaks_sorted[i].get("amplitude", ""))
                else:
                    row.extend(["", ""])

            row.append(sr.get("valid_windows", ""))
            row.append(sr.get("total_windows", ""))
            row.append(sr.get("output_dir", ""))
            writer.writerow(row)

    return output_path


# ---------------------------------------------------------------------------
# Read combined results for bedrock import
# ---------------------------------------------------------------------------

def read_combined_results(csv_path: str | Path) -> List[Dict[str, Any]]:
    """Read a combined_results.csv into a list of dicts.

    Returns dicts with keys matching bedrock mapping's expected columns:
    id, name, x, y, elevation, vs_avg, f0, a0, ...
    """
    csv_path = Path(csv_path)
    results: List[Dict[str, Any]] = []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            entry: Dict[str, Any] = {}
            for key, val in row.items():
                key = key.strip()
                val_s = str(val).strip() if val else ""
                if key in ("id", "name", "output_dir"):
                    entry[key] = val_s
                elif val_s and val_s.lower() not in ("", "none", "nan"):
                    try:
                        entry[key] = float(val_s)
                    except ValueError:
                        entry[key] = val_s
                else:
                    entry[key] = None
            results.append(entry)

    return results


def combined_results_to_bedrock_df(csv_path: str | Path):
    """Read combined_results.csv into a pandas DataFrame
    suitable for ``StationCollection.from_dataframe()``.

    Renames ``f0`` → ``f0`` (already correct), ensures proper dtypes.
    """
    import pandas as pd

    df = pd.read_csv(csv_path)

    # Rename columns to match bedrock mapping expectations
    rename_map = {}
    if "f0" in df.columns:
        pass  # already named correctly
    elif "f_0" in df.columns:
        rename_map["f_0"] = "f0"

    if rename_map:
        df.rename(columns=rename_map, inplace=True)

    # Ensure numeric types
    for col in ["x", "y", "elevation", "vs_avg", "f0", "a0"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df
