"""
Station Registry — flexible parser and data model.

Handles CSV, Excel, or TXT files with varying column sets.
All fields except ``id`` are optional (nullable).
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


# ---------------------------------------------------------------------------
# Single station
# ---------------------------------------------------------------------------

@dataclass
class RegistryStation:
    """One station in the master registry.

    Only *id* is required.  All other fields may be ``None`` if the
    source CSV did not provide them.
    """
    id: str
    sensor: Optional[str] = None
    name: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None
    elevation: Optional[float] = None
    vs_avg: Optional[float] = None

    # Populated later by modules
    data_files: List[str] = field(default_factory=list)
    batch_station_num: Optional[int] = None
    f0: Optional[float] = None
    f0_std: Optional[float] = None
    bedrock_depth: Optional[float] = None

    @property
    def display_name(self) -> str:
        return self.name or self.id

    @property
    def has_coordinates(self) -> bool:
        return self.x is not None and self.y is not None

    @property
    def has_vs(self) -> bool:
        return self.vs_avg is not None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sensor": self.sensor,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "elevation": self.elevation,
            "vs_avg": self.vs_avg,
            "data_files": list(self.data_files),
            "batch_station_num": self.batch_station_num,
            "f0": self.f0,
            "f0_std": self.f0_std,
            "bedrock_depth": self.bedrock_depth,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RegistryStation":
        return cls(
            id=d["id"],
            sensor=d.get("sensor"),
            name=d.get("name"),
            x=d.get("x"),
            y=d.get("y"),
            elevation=d.get("elevation"),
            vs_avg=d.get("vs_avg"),
            data_files=list(d.get("data_files", [])),
            batch_station_num=d.get("batch_station_num"),
            f0=d.get("f0"),
            f0_std=d.get("f0_std"),
            bedrock_depth=d.get("bedrock_depth"),
        )


# ---------------------------------------------------------------------------
# Column mapping — maps various CSV header names to our fields
# ---------------------------------------------------------------------------

_COLUMN_ALIASES: Dict[str, List[str]] = {
    "id":        ["id", "station_id", "station", "stn", "stn_id", "point_id"],
    "sensor":    ["sensor", "sensor_id", "sensor_num", "instrument", "sensor_name"],
    "name":      ["name", "station_name", "stn_name", "label", "description"],
    "x":         ["x", "lon", "longitude", "easting", "long"],
    "y":         ["y", "lat", "latitude", "northing"],
    "elevation": ["elevation", "elev", "z", "height", "altitude", "surface_elevation"],
    "vs_avg":    ["vs_avg", "vs", "vs30", "vs_average", "shear_velocity", "v_s"],
}


def _resolve_column(header: str) -> Optional[str]:
    """Map a CSV column header to a RegistryStation field name."""
    h = header.strip().lower().replace(" ", "_").replace("-", "_")
    for field_name, aliases in _COLUMN_ALIASES.items():
        if h in aliases:
            return field_name
    return None


def _safe_float(val: Any) -> Optional[float]:
    """Convert a value to float, returning None for empty/invalid."""
    if val is None:
        return None
    s = str(val).strip()
    if not s or s.lower() in ("nan", "none", "null", "na", "", "-"):
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Station Registry
# ---------------------------------------------------------------------------

@dataclass
class StationRegistry:
    """Master station list for a project.

    Can be populated from a CSV/Excel/TXT file or built manually.
    """
    stations: List[RegistryStation] = field(default_factory=list)
    coordinate_system: str = "WGS84"
    source_file: Optional[str] = None

    # ------------------------------------------------------------------
    # Factory: from CSV / TXT
    # ------------------------------------------------------------------

    @classmethod
    def from_csv(cls, path: str | Path, encoding: str = "utf-8") -> "StationRegistry":
        """Parse a CSV or TXT file into a StationRegistry.

        Columns are matched flexibly using aliases.
        Only ``id`` (or a reasonable first-column fallback) is required.
        """
        path = Path(path)

        # Read all rows
        rows: List[dict] = []
        with open(path, "r", encoding=encoding, newline="") as f:
            # Sniff delimiter
            sample = f.read(4096)
            f.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
            except csv.Error:
                dialect = csv.excel  # type: ignore[assignment]
            reader = csv.DictReader(f, dialect=dialect)
            for row in reader:
                rows.append(row)

        if not rows:
            return cls(source_file=str(path))

        # Build column mapping
        raw_headers = list(rows[0].keys())
        col_map: Dict[str, str] = {}  # csv_header → field_name
        for h in raw_headers:
            field_name = _resolve_column(h)
            if field_name and field_name not in col_map.values():
                col_map[h] = field_name

        # If no 'id' column found, use the first column as id
        if "id" not in col_map.values():
            first_col = raw_headers[0]
            col_map[first_col] = "id"

        # Parse stations
        stations: List[RegistryStation] = []
        for row in rows:
            fields: Dict[str, Any] = {}
            for csv_col, field_name in col_map.items():
                raw = row.get(csv_col)
                if field_name in ("id", "name", "sensor"):
                    fields[field_name] = str(raw).strip() if raw else None
                else:
                    fields[field_name] = _safe_float(raw)

            station_id = fields.get("id")
            if not station_id:
                continue  # skip rows with no id

            stations.append(RegistryStation(
                id=station_id,
                sensor=fields.get("sensor"),
                name=fields.get("name"),
                x=fields.get("x"),
                y=fields.get("y"),
                elevation=fields.get("elevation"),
                vs_avg=fields.get("vs_avg"),
            ))

        return cls(stations=stations, source_file=str(path))

    @classmethod
    def from_excel(cls, path: str | Path, sheet: int = 0) -> "StationRegistry":
        """Parse an Excel file.  Requires ``openpyxl`` or ``xlrd``."""
        try:
            import pandas as pd
        except ImportError:
            raise ImportError("pandas is required to read Excel files")

        df = pd.read_excel(path, sheet_name=sheet)

        # Reuse CSV logic by writing to temp CSV
        import tempfile
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8", newline=""
        ) as tmp:
            df.to_csv(tmp, index=False)
            tmp_path = tmp.name

        try:
            reg = cls.from_csv(tmp_path)
            reg.source_file = str(path)
            return reg
        finally:
            os.unlink(tmp_path)

    @classmethod
    def from_file(cls, path: str | Path) -> "StationRegistry":
        """Auto-detect format and parse."""
        path = Path(path)
        ext = path.suffix.lower()
        if ext in (".xlsx", ".xls"):
            return cls.from_excel(path)
        else:
            return cls.from_csv(path)

    # ------------------------------------------------------------------
    # Serialization (for project.hvpro JSON)
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "source_file": self.source_file,
            "coordinate_system": self.coordinate_system,
            "stations": [s.to_dict() for s in self.stations],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "StationRegistry":
        stations = [
            RegistryStation.from_dict(sd)
            for sd in d.get("stations", [])
        ]
        return cls(
            stations=stations,
            coordinate_system=d.get("coordinate_system", "WGS84"),
            source_file=d.get("source_file"),
        )

    # ------------------------------------------------------------------
    # Lookup helpers
    # ------------------------------------------------------------------

    def get_station(self, station_id: str) -> Optional[RegistryStation]:
        """Find a station by id (case-insensitive)."""
        sid = station_id.lower()
        for s in self.stations:
            if s.id.lower() == sid:
                return s
        return None

    def get_by_batch_num(self, num: int) -> Optional[RegistryStation]:
        """Find a station by its batch station number."""
        for s in self.stations:
            if s.batch_station_num == num:
                return s
        return None

    def station_ids(self) -> List[str]:
        return [s.id for s in self.stations]

    def stations_with_coords(self) -> List[RegistryStation]:
        return [s for s in self.stations if s.has_coordinates]

    def stations_missing_coords(self) -> List[RegistryStation]:
        return [s for s in self.stations if not s.has_coordinates]

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add_station(self, station: RegistryStation) -> None:
        """Add a station, replacing any existing station with the same id."""
        self.stations = [s for s in self.stations if s.id != station.id]
        self.stations.append(station)

    def remove_station(self, station_id: str) -> bool:
        before = len(self.stations)
        self.stations = [s for s in self.stations if s.id != station_id]
        return len(self.stations) < before

    def update_from_batch_results(
        self,
        results: Sequence[dict],
    ) -> int:
        """Update f0 values from batch processing results.

        Parameters
        ----------
        results : list of dict
            Each dict should have keys: ``station_name`` (or ``station_id``),
            ``f0``, and optionally ``f0_std``.

        Returns
        -------
        int
            Number of stations updated.
        """
        updated = 0
        for r in results:
            stn_name = r.get("station_name", r.get("station_id", ""))
            # Try direct id match
            stn = self.get_station(stn_name)
            # Try extracting number from name and matching batch_station_num
            if stn is None:
                import re
                m = re.search(r"(\d+)", stn_name)
                if m:
                    num = int(m.group(1))
                    stn = self.get_by_batch_num(num)
            if stn is not None:
                stn.f0 = _safe_float(r.get("f0"))
                stn.f0_std = _safe_float(r.get("f0_std"))
                updated += 1
        return updated

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def to_dataframe(self):
        """Export as a pandas DataFrame (for bedrock mapping import)."""
        import pandas as pd
        records = []
        for s in self.stations:
            records.append({
                "id": s.id,
                "sensor": s.sensor,
                "name": s.display_name,
                "x": s.x,
                "y": s.y,
                "elevation": s.elevation,
                "f0": s.f0,
                "f0_std": s.f0_std,
                "vs_avg": s.vs_avg,
                "bedrock_depth": s.bedrock_depth,
            })
        return pd.DataFrame(records)

    def to_csv(self, path: str | Path) -> None:
        """Write the registry to a CSV file."""
        path = Path(path)
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "id", "sensor", "name", "x", "y", "elevation", "vs_avg",
                "f0", "f0_std", "bedrock_depth",
            ])
            for s in self.stations:
                writer.writerow([
                    s.id, s.sensor, s.display_name, s.x, s.y, s.elevation, s.vs_avg,
                    s.f0, s.f0_std, s.bedrock_depth,
                ])

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __len__(self) -> int:
        return len(self.stations)

    def __repr__(self) -> str:
        n = len(self.stations)
        n_coords = len(self.stations_with_coords())
        return f"StationRegistry({n} stations, {n_coords} with coords)"
