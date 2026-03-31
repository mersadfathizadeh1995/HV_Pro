"""
HV Strip Progressive state I/O — save and restore HV Strip analysis
state to/from a project folder.
"""

from __future__ import annotations

import json
import logging
import pickle
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

STATE_FILE = "state.json"
RESULTS_FILE = "strip_results.pkl"
MODEL_FILE = "model_data.pkl"


def save_hvstrip_state(
    profile_dir: str | Path,
    config: Optional[Dict[str, Any]] = None,
    results: Any = None,
    model_data: Any = None,
) -> bool:
    """Save HV Strip analysis state to a project profile folder.

    Parameters
    ----------
    profile_dir : path
        Project profile subfolder (e.g. ``project/hv_strip/profile_001/``).
    config : dict, optional
        Strip analysis configuration.
    results : object, optional
        Strip results to pickle.
    model_data : object, optional
        Soil model data to pickle.

    Returns
    -------
    bool
        ``True`` on success.
    """
    profile_dir = Path(profile_dir)
    profile_dir.mkdir(parents=True, exist_ok=True)

    try:
        state = {
            "config": config or {},
            "has_results": results is not None,
            "has_model": model_data is not None,
        }

        with open(profile_dir / STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False, default=str)

        if results is not None:
            with open(profile_dir / RESULTS_FILE, "wb") as f:
                pickle.dump(results, f)

        if model_data is not None:
            with open(profile_dir / MODEL_FILE, "wb") as f:
                pickle.dump(model_data, f)

        logger.info("HV Strip state saved to %s", profile_dir)
        return True

    except Exception as e:
        logger.error("Failed to save HV Strip state: %s", e)
        return False


def load_hvstrip_state(
    profile_dir: str | Path,
) -> Dict[str, Any]:
    """Load HV Strip state from a project profile folder.

    Returns
    -------
    dict
        Keys: ``config``, ``results``, ``model_data``.
    """
    profile_dir = Path(profile_dir)
    result: Dict[str, Any] = {
        "config": {},
        "results": None,
        "model_data": None,
    }

    state_file = profile_dir / STATE_FILE
    if state_file.exists():
        with open(state_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        result["config"] = data.get("config", {})

    for key, filename in [
        ("results", RESULTS_FILE),
        ("model_data", MODEL_FILE),
    ]:
        pkl_path = profile_dir / filename
        if pkl_path.exists():
            try:
                with open(pkl_path, "rb") as f:
                    result[key] = pickle.load(f)
            except Exception as e:
                logger.warning("Could not load %s: %s", pkl_path.name, e)

    return result


def has_hvstrip_state(profile_dir: str | Path) -> bool:
    """Check if a profile folder has saved state."""
    return (Path(profile_dir) / STATE_FILE).exists()
