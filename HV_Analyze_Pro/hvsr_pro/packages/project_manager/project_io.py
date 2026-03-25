"""
Project I/O helpers.

Handles reading/writing ``project.hvpro`` and the recent-projects list.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List, Optional

RECENT_FILE_DIR = Path.home() / ".hvpro"
RECENT_FILE = RECENT_FILE_DIR / "recent.json"
MAX_RECENT = 20


# ---------------------------------------------------------------------------
# Recent projects list
# ---------------------------------------------------------------------------

def load_recent_projects() -> List[str]:
    """Return list of recent project.hvpro paths (newest first)."""
    if not RECENT_FILE.exists():
        return []
    try:
        with open(RECENT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        paths = data.get("recent", [])
        # Filter to only existing projects
        return [p for p in paths if Path(p).exists()]
    except (json.JSONDecodeError, OSError):
        return []


def add_recent_project(hvpro_path: str | Path) -> None:
    """Add a project to the top of the recent list."""
    hvpro_path = str(Path(hvpro_path).resolve())
    recent = load_recent_projects()

    # Remove if already present
    recent = [p for p in recent if p != hvpro_path]
    # Add to top
    recent.insert(0, hvpro_path)
    # Trim
    recent = recent[:MAX_RECENT]

    RECENT_FILE_DIR.mkdir(parents=True, exist_ok=True)
    with open(RECENT_FILE, "w", encoding="utf-8") as f:
        json.dump({"recent": recent}, f, indent=2)


def remove_recent_project(hvpro_path: str | Path) -> None:
    """Remove a project from the recent list."""
    hvpro_path = str(Path(hvpro_path).resolve())
    recent = load_recent_projects()
    recent = [p for p in recent if p != hvpro_path]
    RECENT_FILE_DIR.mkdir(parents=True, exist_ok=True)
    with open(RECENT_FILE, "w", encoding="utf-8") as f:
        json.dump({"recent": recent}, f, indent=2)
