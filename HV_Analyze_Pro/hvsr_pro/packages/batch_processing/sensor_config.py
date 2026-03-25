"""
Sensor Configuration System
============================

Defines how filenames are matched to physical sensors.
A sensor is a recording instrument that may be deployed at multiple
stations over different time periods.

SensorConfig: one sensor definition with display name + regex patterns
SensorConfigManager: load/save/match operations
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class SensorConfig:
    """Definition of a single sensor for file routing.

    Parameters
    ----------
    sensor_id : str
        Unique identifier (e.g. "1", "sensor_A").
    display_name : str
        Human-readable name (e.g. "Centaur 0655").
    file_patterns : list[str]
        Regex patterns that match filenames belonging to this sensor.
        Any matching pattern means the file belongs to this sensor.
    """

    sensor_id: str
    display_name: str
    file_patterns: List[str] = field(default_factory=list)

    def matches(self, filename: str) -> bool:
        """Return True if *filename* matches any of this sensor's patterns."""
        for pat in self.file_patterns:
            try:
                if re.search(pat, filename, re.IGNORECASE):
                    return True
            except re.error:
                continue
        return False

    def to_dict(self) -> dict:
        return {
            "sensor_id": self.sensor_id,
            "display_name": self.display_name,
            "file_patterns": list(self.file_patterns),
        }

    @classmethod
    def from_dict(cls, d: dict) -> SensorConfig:
        return cls(
            sensor_id=str(d["sensor_id"]),
            display_name=str(d.get("display_name", d["sensor_id"])),
            file_patterns=list(d.get("file_patterns", [])),
        )


# ---------------------------------------------------------------------------
# Default centaur serial mapping (0655→sensor 1, 0656→sensor 2, ...)
# ---------------------------------------------------------------------------

def _default_centaur_configs(n_sensors: int = 6, base_serial: int = 655) -> List[SensorConfig]:
    """Generate default SensorConfigs for Nanometrics Centaur recorders."""
    configs = []
    for i in range(n_sensors):
        serial = base_serial + i
        stn_num = i + 1
        configs.append(SensorConfig(
            sensor_id=str(stn_num),
            display_name=f"Centaur {serial:04d}",
            file_patterns=[
                rf"centaur-3_{serial:04d}_",          # serial in filename
                rf"\.STN{stn_num:02d}\.",              # station number pattern
            ],
        ))
    return configs


# ---------------------------------------------------------------------------
# Manager: load/save/match
# ---------------------------------------------------------------------------

class SensorConfigManager:
    """Manages a collection of sensor configurations.

    Provides file→sensor matching and persistence.
    """

    def __init__(self, configs: Optional[List[SensorConfig]] = None):
        self.configs: List[SensorConfig] = configs or []

    # ------------------------------------------------------------------
    # Factory helpers
    # ------------------------------------------------------------------

    @classmethod
    def default(cls, n_sensors: int = 6) -> SensorConfigManager:
        """Create a manager with default Centaur serial configs."""
        return cls(_default_centaur_configs(n_sensors))

    # ------------------------------------------------------------------
    # Matching
    # ------------------------------------------------------------------

    def match_file(self, filename: str) -> Optional[SensorConfig]:
        """Return the first SensorConfig that matches *filename*, or None."""
        for cfg in self.configs:
            if cfg.matches(filename):
                return cfg
        return None

    def match_files(self, filenames: List[str]) -> Dict[str, List[str]]:
        """Match a list of filenames to sensors.

        Returns
        -------
        dict mapping sensor_id → [filenames].
        Files matching no sensor are placed under key "__unmatched__".
        """
        result: Dict[str, List[str]] = {}
        for fname in filenames:
            cfg = self.match_file(fname)
            key = cfg.sensor_id if cfg else "__unmatched__"
            result.setdefault(key, []).append(fname)
        return result

    def route_files_to_stations(
        self,
        file_paths: List[str],
        sensor_station_map: Dict[str, List[int]],
    ) -> Tuple[Dict[int, List[str]], List[str]]:
        """Route files to stations via sensor matching.

        Parameters
        ----------
        file_paths : list[str]
            Full file paths.
        sensor_station_map : dict
            Maps sensor_id → [station_numbers].
            E.g. {"1": [1, 7, 13, 19], "2": [2, 8, 14, 20], ...}

        Returns
        -------
        (station_files, unmatched) where station_files maps
        station_num → [file_paths] and unmatched is a list of paths
        that matched no sensor.

        Note: when a sensor maps to multiple stations, files go
        into ALL stations (disambiguation by time window is done later).
        """
        station_files: Dict[int, List[str]] = {}
        unmatched: List[str] = []

        for fpath in file_paths:
            fname = os.path.basename(fpath)
            cfg = self.match_file(fname)

            if cfg is None:
                unmatched.append(fpath)
                continue

            stations = sensor_station_map.get(cfg.sensor_id, [])
            if not stations:
                unmatched.append(fpath)
                continue

            for stn_num in stations:
                station_files.setdefault(stn_num, []).append(fpath)

        return station_files, unmatched

    def get_sensor(self, sensor_id: str) -> Optional[SensorConfig]:
        """Find a sensor config by ID."""
        for cfg in self.configs:
            if cfg.sensor_id == sensor_id:
                return cfg
        return None

    def sensor_ids(self) -> List[str]:
        return [c.sensor_id for c in self.configs]

    # ------------------------------------------------------------------
    # Auto-detect from filenames
    # ------------------------------------------------------------------

    @classmethod
    def auto_detect(cls, filenames: List[str]) -> SensorConfigManager:
        """Try to auto-detect sensor definitions from a set of filenames.

        Currently detects Centaur serial patterns (centaur-3_NNNN_).
        """
        serials: Dict[int, List[str]] = {}
        for fname in filenames:
            m = re.search(r'centaur-3_(\d{4})_', fname, re.IGNORECASE)
            if m:
                serial = int(m.group(1))
                serials.setdefault(serial, []).append(fname)

        if not serials:
            return cls()

        configs = []
        for i, serial in enumerate(sorted(serials.keys()), start=1):
            configs.append(SensorConfig(
                sensor_id=str(i),
                display_name=f"Centaur {serial:04d}",
                file_patterns=[
                    rf"centaur-3_{serial:04d}_",
                ],
            ))

        return cls(configs)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "version": 1,
            "sensors": [c.to_dict() for c in self.configs],
        }

    @classmethod
    def from_dict(cls, d: dict) -> SensorConfigManager:
        sensors = [SensorConfig.from_dict(s) for s in d.get("sensors", [])]
        return cls(sensors)

    def save(self, path: str | Path) -> None:
        """Save sensor configs to a JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str | Path) -> SensorConfigManager:
        """Load sensor configs from a JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def build_sensor_station_map(
        self, stations: list,
    ) -> Dict[str, List[int]]:
        """Build sensor_id → [station_nums] from a list of RegistryStation.

        Parameters
        ----------
        stations : list of RegistryStation
            Each station should have a `sensor` field and `batch_station_num`.
        """
        mapping: Dict[str, List[int]] = {}
        for stn in stations:
            sid = stn.sensor
            if sid is None:
                continue
            num = stn.batch_station_num
            if num is None:
                # Try extracting from ID
                import re
                m = re.search(r'(\d+)', stn.id)
                if m:
                    num = int(m.group(1))
            if num is not None:
                mapping.setdefault(str(sid), []).append(num)
        return mapping

    def __len__(self) -> int:
        return len(self.configs)

    def __repr__(self) -> str:
        return f"SensorConfigManager({len(self.configs)} sensors)"
