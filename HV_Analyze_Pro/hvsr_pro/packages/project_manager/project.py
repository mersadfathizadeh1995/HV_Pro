"""
Project data model for HV Pro.

Manages project metadata, station registry, module tracking,
directory structure, and JSON persistence via ``project.hvpro``.
"""

from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .station_registry import StationRegistry, RegistryStation


# ---------------------------------------------------------------------------
# Supporting dataclasses
# ---------------------------------------------------------------------------

@dataclass
class ModuleState:
    """Tracks items created within a single module (e.g. batch_001)."""
    items: List[str] = field(default_factory=list)
    last_active: Optional[str] = None

    def add_item(self, item_id: str) -> None:
        if item_id not in self.items:
            self.items.append(item_id)
        self.last_active = item_id

    def to_dict(self) -> dict:
        return {"items": list(self.items), "last_active": self.last_active}

    @classmethod
    def from_dict(cls, d: dict) -> "ModuleState":
        return cls(items=list(d.get("items", [])),
                   last_active=d.get("last_active"))


@dataclass
class ActivityEntry:
    """Single entry in the recent-activity log."""
    ts: str
    module: str
    msg: str

    def to_dict(self) -> dict:
        return {"ts": self.ts, "module": self.module, "msg": self.msg}

    @classmethod
    def from_dict(cls, d: dict) -> "ActivityEntry":
        return cls(ts=d["ts"], module=d["module"], msg=d["msg"])


# ---------------------------------------------------------------------------
# Module name constants
# ---------------------------------------------------------------------------

MODULE_BATCH = "batch_processing"
MODULE_BEDROCK = "bedrock_mapping"
MODULE_HVSTRIP = "hv_strip"
MODULE_INVERSION = "inversion"
MODULE_HVSR_ANALYSIS = "hvsr_analysis"

_ALL_MODULES = [MODULE_BATCH, MODULE_BEDROCK, MODULE_HVSTRIP,
                MODULE_INVERSION, MODULE_HVSR_ANALYSIS]


# ---------------------------------------------------------------------------
# Project class
# ---------------------------------------------------------------------------

HVPRO_VERSION = "3.0"
PROJECT_FILENAME = "project.hvpro"


@dataclass
class Project:
    """Core project data model.

    Attributes
    ----------
    name : str
        Human-readable project name.
    path : Path
        Root directory of the project on disk.
    author : str
        Project author / creator.
    description : str
        Free-text description.
    registry : StationRegistry
        Master station list (may be empty).
    modules : dict[str, ModuleState]
        Per-module tracking (items created, last active).
    recent_activity : list[ActivityEntry]
        Timestamped log of significant events.
    created : str
        ISO-8601 creation timestamp.
    modified : str
        ISO-8601 last-modified timestamp.
    """

    name: str
    path: Path
    author: str = ""
    description: str = ""
    registry: StationRegistry = field(default_factory=StationRegistry)
    modules: Dict[str, ModuleState] = field(default_factory=dict)
    recent_activity: List[ActivityEntry] = field(default_factory=list)
    created: str = ""
    modified: str = ""

    # ------------------------------------------------------------------
    # Factory methods
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        name: str,
        path: str | Path,
        author: str = "",
        description: str = "",
    ) -> "Project":
        """Create a brand-new project: make directories and write ``project.hvpro``."""
        root = Path(path)
        root.mkdir(parents=True, exist_ok=True)

        now = datetime.now(timezone.utc).isoformat()

        modules = {m: ModuleState() for m in _ALL_MODULES}

        proj = cls(
            name=name,
            path=root,
            author=author,
            description=description,
            registry=StationRegistry(),
            modules=modules,
            recent_activity=[],
            created=now,
            modified=now,
        )

        # Create standard subdirectories
        for subdir in proj._standard_subdirs():
            subdir.mkdir(parents=True, exist_ok=True)

        proj.save()
        return proj

    @classmethod
    def load(cls, hvpro_path: str | Path) -> "Project":
        """Load an existing project from a ``project.hvpro`` file."""
        hvpro_path = Path(hvpro_path)
        if not hvpro_path.exists():
            raise FileNotFoundError(f"Project file not found: {hvpro_path}")

        with open(hvpro_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        root = hvpro_path.parent

        # Parse station registry
        reg_data = data.get("station_registry", {})
        registry = StationRegistry.from_dict(reg_data)

        # Parse modules
        modules: Dict[str, ModuleState] = {}
        for m in _ALL_MODULES:
            md = data.get("modules", {}).get(m, {})
            modules[m] = ModuleState.from_dict(md) if md else ModuleState()

        # Parse activity log
        activity = [
            ActivityEntry.from_dict(e)
            for e in data.get("recent_activity", [])
        ]

        return cls(
            name=data.get("name", root.name),
            path=root,
            author=data.get("author", ""),
            description=data.get("description", ""),
            registry=registry,
            modules=modules,
            recent_activity=activity,
            created=data.get("created", ""),
            modified=data.get("modified", ""),
        )

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self) -> Path:
        """Write ``project.hvpro`` to disk.  Returns the file path."""
        self.modified = datetime.now(timezone.utc).isoformat()

        data: Dict[str, Any] = {
            "hvpro_version": HVPRO_VERSION,
            "name": self.name,
            "created": self.created,
            "modified": self.modified,
            "author": self.author,
            "description": self.description,
            "station_registry": self.registry.to_dict(),
            "modules": {m: ms.to_dict() for m, ms in self.modules.items()},
            "recent_activity": [a.to_dict() for a in self.recent_activity[-50:]],
        }

        out = self.hvpro_file
        with open(out, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return out

    def clone_to(self, dest: Path, new_name: Optional[str] = None) -> "Project":
        """Deep-copy this project to *dest* and return the new Project.

        Copies every file/folder (raw_data, module folders, etc.) then
        rewrites the ``.hvpro`` manifest with an optional *new_name*.
        """
        dest = Path(dest)
        if dest.exists():
            raise FileExistsError(f"Destination already exists: {dest}")
        shutil.copytree(str(self.path), str(dest))
        new_proj = Project.open(dest)
        if new_name:
            new_proj.name = new_name
        new_proj.created = datetime.now(timezone.utc).isoformat()
        new_proj.log_activity("project", f"Cloned from {self.name}")
        new_proj.save()
        return new_proj

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    @property
    def hvpro_file(self) -> Path:
        return self.path / PROJECT_FILENAME

    def raw_data_dir(self) -> Path:
        return self.path / "raw_data"

    def batch_dir(self, batch_id: str = "batch_001") -> Path:
        return self.path / "batch_processing" / batch_id

    def bedrock_dir(self, map_id: str = "map_001") -> Path:
        return self.path / "bedrock_mapping" / map_id

    def strip_dir(self, profile_id: str = "profile_001") -> Path:
        return self.path / "hv_strip" / profile_id

    def inversion_dir(self, item_id: str = "inv_001") -> Path:
        return self.path / "inversion" / item_id

    def analysis_dir(self, item_id: str = "analysis_001") -> Path:
        return self.path / "hvsr_analysis" / item_id

    def reports_dir(self) -> Path:
        return self.path / "reports"

    def _standard_subdirs(self) -> List[Path]:
        return [
            self.raw_data_dir(),
            self.path / "batch_processing",
            self.path / "bedrock_mapping",
            self.path / "hv_strip",
            self.path / "inversion",
            self.path / "hvsr_analysis",
            self.reports_dir(),
        ]

    # ------------------------------------------------------------------
    # Module helpers
    # ------------------------------------------------------------------

    def ensure_module_dir(self, module: str, item_id: str) -> Path:
        """Create and register a module item directory (e.g. batch_001)."""
        if module == MODULE_BATCH:
            d = self.batch_dir(item_id)
        elif module == MODULE_BEDROCK:
            d = self.bedrock_dir(item_id)
        elif module == MODULE_HVSTRIP:
            d = self.strip_dir(item_id)
        elif module == MODULE_INVERSION:
            d = self.inversion_dir(item_id)
        elif module == MODULE_HVSR_ANALYSIS:
            d = self.analysis_dir(item_id)
        else:
            d = self.path / module / item_id

        d.mkdir(parents=True, exist_ok=True)

        ms = self.modules.setdefault(module, ModuleState())
        ms.add_item(item_id)

        return d

    def next_item_id(self, module: str, prefix: str = "") -> str:
        """Generate next sequential item ID for a module.

        E.g. ``next_item_id(MODULE_BATCH, "batch_")`` → ``"batch_002"``
        if ``batch_001`` already exists.
        """
        ms = self.modules.get(module, ModuleState())
        existing_nums = []
        for item in ms.items:
            if item.startswith(prefix):
                try:
                    num = int(item[len(prefix):])
                    existing_nums.append(num)
                except ValueError:
                    pass
        next_num = max(existing_nums, default=0) + 1
        return f"{prefix}{next_num:03d}"

    # ------------------------------------------------------------------
    # Activity log
    # ------------------------------------------------------------------

    def log_activity(self, module: str, msg: str) -> None:
        """Append an entry to the activity log."""
        self.recent_activity.append(ActivityEntry(
            ts=datetime.now(timezone.utc).isoformat(),
            module=module,
            msg=msg,
        ))
        # Keep last 100 entries
        if len(self.recent_activity) > 100:
            self.recent_activity = self.recent_activity[-100:]

    # ------------------------------------------------------------------
    # Representation
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        n_stations = len(self.registry.stations)
        return (f"Project(name={self.name!r}, stations={n_stations}, "
                f"path={self.path})")
