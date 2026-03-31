"""
HVSR Analysis state I/O — save and restore standard HVSR analysis
state to/from a project folder.

Reuses the same pickle + JSON format that SessionManager uses,
but writes to the project's ``hvsr_analysis/analysis_NNN/`` directory.
"""

from __future__ import annotations

import json
import logging
import pickle
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# File names (matching SessionManager conventions)
SETTINGS_FILE = "session.json"
WINDOWS_FILE = "windows.pkl"
HVSR_RESULT_FILE = "hvsr_result.pkl"
SEISMIC_DATA_FILE = "seismic_data.pkl"
AZIMUTHAL_RESULT_FILE = "azimuthal_result.pkl"


def save_hvsr_state(
    analysis_dir: str | Path,
    state_dict: Dict[str, Any],
    windows: Any = None,
    hvsr_result: Any = None,
    seismic_data: Any = None,
    azimuthal_result: Any = None,
) -> bool:
    """Save standard HVSR analysis state to a project analysis folder.

    Parameters
    ----------
    analysis_dir : path
        Project analysis subfolder
        (e.g. ``project/hvsr_analysis/analysis_001/``).
    state_dict : dict
        Serialisable settings / metadata (will be written as JSON).
    windows : object, optional
        WindowCollection to pickle.
    hvsr_result : object, optional
        HVSRResult to pickle.
    seismic_data : object, optional
        SeismicData to pickle.
    azimuthal_result : object, optional
        AzimuthalHVSRResult to pickle.

    Returns
    -------
    bool
        ``True`` on success.
    """
    analysis_dir = Path(analysis_dir)
    analysis_dir.mkdir(parents=True, exist_ok=True)

    try:
        # Pickle binary objects
        if windows is not None:
            with open(analysis_dir / WINDOWS_FILE, "wb") as f:
                pickle.dump(windows, f)
            state_dict["windows_file"] = WINDOWS_FILE

        if hvsr_result is not None:
            with open(analysis_dir / HVSR_RESULT_FILE, "wb") as f:
                pickle.dump(hvsr_result, f)
            state_dict["hvsr_result_file"] = HVSR_RESULT_FILE

        if seismic_data is not None:
            with open(analysis_dir / SEISMIC_DATA_FILE, "wb") as f:
                pickle.dump(seismic_data, f)
            state_dict["seismic_data_file"] = SEISMIC_DATA_FILE

        if azimuthal_result is not None:
            with open(analysis_dir / AZIMUTHAL_RESULT_FILE, "wb") as f:
                pickle.dump(azimuthal_result, f)
            state_dict["azimuthal_result_file"] = AZIMUTHAL_RESULT_FILE

        # JSON settings
        with open(analysis_dir / SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(state_dict, f, indent=2, ensure_ascii=False, default=str)

        logger.info("HVSR state saved to %s", analysis_dir)
        return True

    except Exception as e:
        logger.error("Failed to save HVSR state: %s", e)
        return False


def load_hvsr_state(
    analysis_dir: str | Path,
) -> Dict[str, Any]:
    """Load standard HVSR analysis state from a project analysis folder.

    Returns
    -------
    dict
        Keys: ``state_dict``, ``windows``, ``hvsr_result``,
        ``seismic_data``, ``azimuthal_result``.
        Any unavailable item is ``None``.
    """
    analysis_dir = Path(analysis_dir)
    result: Dict[str, Any] = {
        "state_dict": {},
        "windows": None,
        "hvsr_result": None,
        "seismic_data": None,
        "azimuthal_result": None,
    }

    settings_path = analysis_dir / SETTINGS_FILE
    if settings_path.exists():
        with open(settings_path, "r", encoding="utf-8") as f:
            result["state_dict"] = json.load(f)

    for key, filename in [
        ("windows", WINDOWS_FILE),
        ("hvsr_result", HVSR_RESULT_FILE),
        ("seismic_data", SEISMIC_DATA_FILE),
        ("azimuthal_result", AZIMUTHAL_RESULT_FILE),
    ]:
        pkl_path = analysis_dir / filename
        if pkl_path.exists():
            try:
                with open(pkl_path, "rb") as f:
                    result[key] = pickle.load(f)
            except Exception as e:
                logger.warning("Could not load %s: %s", pkl_path.name, e)

    return result


def has_hvsr_state(analysis_dir: str | Path) -> bool:
    """Check if an analysis folder has saved state."""
    return (Path(analysis_dir) / SETTINGS_FILE).exists()
