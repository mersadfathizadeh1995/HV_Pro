"""
HVSR Inversion state I/O — save and restore inversion wizard state
to/from a project folder.
"""

from __future__ import annotations

import json
import logging
import pickle
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

STATE_FILE = "state.json"
RESULTS_FILE = "inversion_results.pkl"


def save_inversion_state(
    inv_dir: str | Path,
    wizard_state: Optional[Dict[str, Any]] = None,
    results: Any = None,
    settings: Optional[Dict[str, Any]] = None,
) -> bool:
    """Save inversion state to a project inversion folder.

    Parameters
    ----------
    inv_dir : path
        Project inversion subfolder (e.g. ``project/inversion/inv_001/``).
    wizard_state : dict, optional
        Wizard step data (current step, bounds, model config, etc.).
    results : object, optional
        Inversion results object to pickle.
    settings : dict, optional
        Algorithm settings snapshot.

    Returns
    -------
    bool
        ``True`` on success.
    """
    inv_dir = Path(inv_dir)
    inv_dir.mkdir(parents=True, exist_ok=True)

    try:
        state = {
            "wizard_state": wizard_state or {},
            "settings": settings or {},
            "has_results": results is not None,
        }

        with open(inv_dir / STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False, default=str)

        if results is not None:
            with open(inv_dir / RESULTS_FILE, "wb") as f:
                pickle.dump(results, f)

        logger.info("Inversion state saved to %s", inv_dir)
        return True

    except Exception as e:
        logger.error("Failed to save inversion state: %s", e)
        return False


def load_inversion_state(
    inv_dir: str | Path,
) -> Dict[str, Any]:
    """Load inversion state from a project inversion folder.

    Returns
    -------
    dict
        Keys: ``wizard_state``, ``settings``, ``results``.
    """
    inv_dir = Path(inv_dir)
    result: Dict[str, Any] = {
        "wizard_state": {},
        "settings": {},
        "results": None,
    }

    state_file = inv_dir / STATE_FILE
    if state_file.exists():
        with open(state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        result["wizard_state"] = data.get("wizard_state", {})
        result["settings"] = data.get("settings", {})

    results_file = inv_dir / RESULTS_FILE
    if results_file.exists():
        try:
            with open(results_file, "rb") as f:
                result["results"] = pickle.load(f)
        except Exception as e:
            logger.warning("Could not load inversion results: %s", e)

    return result


def has_inversion_state(inv_dir: str | Path) -> bool:
    """Check if an inversion folder has saved state."""
    return (Path(inv_dir) / STATE_FILE).exists()
