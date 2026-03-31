"""
HVSR Inversion state I/O — save and restore the full WizardController
state to/from a project folder.

Serialisation strategy
----------------------
- **state.json** — JSON-safe scalars: file paths, freq_range, sigma
  scale, peaks list, bounds/inversion settings (via ``dataclasses.asdict``),
  generated_bounds, inversion_results, selected_bounds_names, active tab.
- **hv_arrays.npz** — compressed numpy arrays: obs_f, obs_hv, sigma,
  obs_f_full, obs_hv_full, sigma_original.
- **comparison_results.pkl** — pickle for the comparison_results dict
  (may contain non-JSON-safe objects).
"""

from __future__ import annotations

import json
import logging
import pickle
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

STATE_FILE = "state.json"
ARRAYS_FILE = "hv_arrays.npz"
COMPARISON_FILE = "comparison_results.pkl"


# ── helpers ──────────────────────────────────────────────────────────

def _ndarray_to_list(obj):
    """``json.dump`` *default* callback: convert ndarray → list."""
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    return str(obj)


def _safe_asdict(dc) -> dict:
    """Convert a dataclass to dict, coercing numpy scalars."""
    d = asdict(dc)
    return json.loads(json.dumps(d, default=_ndarray_to_list))


def _tuple_or_none(val) -> Optional[Tuple]:
    if val is None:
        return None
    if isinstance(val, (list, tuple)) and len(val) >= 2:
        return tuple(val)
    return None


# ── public API ───────────────────────────────────────────────────────

def save_inversion_state(
    inv_dir: str | Path,
    *,
    controller=None,
    active_tab: int = 0,
) -> bool:
    """Save the full WizardController state to *inv_dir*.

    Parameters
    ----------
    inv_dir : path
        ``project/inversion/inv_001/``
    controller : WizardController
        The live controller whose state we persist.
    active_tab : int
        Currently visible tab index (so we can re-open to it).
    """
    if controller is None:
        logger.warning("save_inversion_state called with controller=None")
        return False

    inv_dir = Path(inv_dir)
    inv_dir.mkdir(parents=True, exist_ok=True)

    try:
        # ── numpy arrays → compressed .npz ──────────────────────
        arrays: Dict[str, np.ndarray] = {}
        for name in (
            "obs_f", "obs_hv", "sigma",
            "obs_f_full", "obs_hv_full", "sigma_original",
        ):
            arr = getattr(controller, name, None)
            if arr is not None:
                arrays[name] = np.asarray(arr)
        if arrays:
            np.savez_compressed(str(inv_dir / ARRAYS_FILE), **arrays)

        # ── peaks → list of dicts ───────────────────────────────
        peaks_list: List[dict] = []
        for p in (controller.peaks or []):
            peaks_list.append(_safe_asdict(p))

        # ── bounds & inversion settings ─────────────────────────
        bounds_cfg = _safe_asdict(controller.bounds_settings)
        inv_cfg = _safe_asdict(controller.inversion_settings)

        # ── global settings snapshot ────────────────────────────
        gs = controller.global_settings
        gs_dict = {
            "hvf_exe": gs.hvf_exe,
            "default_workers": gs.default_workers,
            "platform": gs.platform,
            "default_output_root": gs.default_output_root,
        }

        # ── state.json ──────────────────────────────────────────
        state: Dict[str, Any] = {
            "hv_file_path": controller.hv_file_path or "",
            "output_dir": controller.output_dir or "",
            "freq_range": list(controller.freq_range) if controller.freq_range else None,
            "sigma_scale": controller.sigma_scale,
            "sigma_uniform": controller.sigma_uniform,
            "metadata": controller.metadata,
            "peaks": peaks_list,
            "bounds_settings": bounds_cfg,
            "generated_bounds": controller.generated_bounds or {},
            "inversion_settings": inv_cfg,
            "selected_bounds_names": list(controller.selected_bounds_names or []),
            "inversion_results": controller.inversion_results or {},
            "global_settings": gs_dict,
            "active_tab": active_tab,
            "has_arrays": bool(arrays),
            "has_comparison": controller.comparison_results is not None,
        }
        with open(inv_dir / STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False,
                      default=_ndarray_to_list)

        # ── comparison results (pickle) ─────────────────────────
        if controller.comparison_results is not None:
            with open(inv_dir / COMPARISON_FILE, "wb") as f:
                pickle.dump(controller.comparison_results, f)

        logger.info("Inversion state saved to %s", inv_dir)
        return True

    except Exception as e:
        logger.error("Failed to save inversion state: %s", e, exc_info=True)
        return False


def load_inversion_state(
    inv_dir: str | Path,
) -> Dict[str, Any]:
    """Load inversion state from *inv_dir*.

    Returns
    -------
    dict
        Keys mirror the WizardController fields plus ``active_tab``.
        Numpy arrays are returned as np.ndarray; missing data is ``None``.
    """
    inv_dir = Path(inv_dir)
    result: Dict[str, Any] = {}

    # ── state.json ──────────────────────────────────────────────
    state_file = inv_dir / STATE_FILE
    if not state_file.exists():
        return result
    try:
        with open(state_file, "r", encoding="utf-8") as f:
            result = json.load(f)
    except Exception as e:
        logger.warning("Could not read %s: %s", state_file, e)
        return result

    # ── numpy arrays ────────────────────────────────────────────
    npz_path = inv_dir / ARRAYS_FILE
    if npz_path.exists():
        try:
            with np.load(str(npz_path)) as data:
                for name in (
                    "obs_f", "obs_hv", "sigma",
                    "obs_f_full", "obs_hv_full", "sigma_original",
                ):
                    if name in data:
                        result[name] = data[name]
        except Exception as e:
            logger.warning("Could not load arrays: %s", e)

    # ── comparison results (pickle) ─────────────────────────────
    comp_path = inv_dir / COMPARISON_FILE
    if comp_path.exists():
        try:
            with open(comp_path, "rb") as f:
                result["comparison_results"] = pickle.load(f)
        except Exception as e:
            logger.warning("Could not load comparison results: %s", e)

    return result


def restore_controller(controller, state: Dict[str, Any]) -> int:
    """Apply *state* (from ``load_inversion_state``) onto *controller*.

    Parameters
    ----------
    controller : WizardController
        A freshly constructed (or existing) controller to populate.
    state : dict
        The dict returned by ``load_inversion_state``.

    Returns
    -------
    int
        The ``active_tab`` index to switch to.
    """
    if not state:
        return 0

    # Scalars
    controller.hv_file_path = state.get("hv_file_path", "")
    controller.output_dir = state.get("output_dir", "")
    controller.sigma_scale = state.get("sigma_scale", 1.0)
    controller.sigma_uniform = state.get("sigma_uniform")
    controller.metadata = state.get("metadata")
    controller.freq_range = _tuple_or_none(state.get("freq_range"))

    # Numpy arrays
    for name in (
        "obs_f", "obs_hv", "sigma",
        "obs_f_full", "obs_hv_full", "sigma_original",
    ):
        val = state.get(name)
        if val is not None:
            setattr(controller, name, np.asarray(val))

    # Peaks
    try:
        try:
            from hvsr_pro.packages.invert_hvsr.invert_hvsr.gui.wizard_controller import PeakInfo
        except ImportError:
            from invert_hvsr.gui.wizard_controller import PeakInfo
        peaks_data = state.get("peaks", [])
        controller.peaks = [
            PeakInfo(
                frequency=p.get("frequency", 1.0),
                amplitude=p.get("amplitude", 0.0),
                std=p.get("std", 0.10),
                peak_type=p.get("peak_type", "primary"),
            )
            for p in peaks_data
        ]
    except Exception:
        controller.peaks = []

    # Bounds settings
    bs = state.get("bounds_settings", {})
    if bs:
        try:
            try:
                from hvsr_pro.packages.invert_hvsr.invert_hvsr.gui.wizard_controller import BoundsSettings
            except ImportError:
                from invert_hvsr.gui.wizard_controller import BoundsSettings
            controller.bounds_settings = BoundsSettings(
                n_layers=bs.get("n_layers", 7),
                scenarios=bs.get("scenarios", ["shallow", "medium_shallow", "medium_deep", "deep"]),
                vs_n=bs.get("vs_n"),
                bedrock_depth=_tuple_or_none(bs.get("bedrock_depth")),
                bedrock_vs=_tuple_or_none(bs.get("bedrock_vs")),
                surface_vs=_tuple_or_none(bs.get("surface_vs")),
                monotonic_vs=bs.get("monotonic_vs", False),
                max_depth=bs.get("max_depth", 500.0),
                lr_range=_tuple_or_none(bs.get("lr_range")) or (1.2, 2.5),
                bounds_margin=bs.get("bounds_margin", 0.15),
                validate=bs.get("validate", False),
                n_validation_models=bs.get("n_validation_models", 200),
                n_validation_workers=bs.get("n_validation_workers", 4),
            )
        except Exception:
            pass

    # Inversion settings
    ic = state.get("inversion_settings", {})
    if ic:
        try:
            try:
                from hvsr_pro.packages.invert_hvsr.invert_hvsr.gui.wizard_controller import InversionSettings
            except ImportError:
                from invert_hvsr.gui.wizard_controller import InversionSettings
            isettings = InversionSettings()
            for key, val in ic.items():
                if hasattr(isettings, key):
                    expected = getattr(isettings, key)
                    if isinstance(expected, tuple) and isinstance(val, list):
                        val = tuple(val)
                    setattr(isettings, key, val)
            controller.inversion_settings = isettings
        except Exception:
            pass

    # Generated bounds
    controller.generated_bounds = state.get("generated_bounds", {})
    controller.selected_bounds_names = state.get("selected_bounds_names", [])

    # Inversion results
    controller.inversion_results = state.get("inversion_results", {})

    # Comparison results
    if "comparison_results" in state:
        controller.comparison_results = state["comparison_results"]

    return state.get("active_tab", 0)


def has_inversion_state(inv_dir: str | Path) -> bool:
    """Check if an inversion folder has saved state."""
    return (Path(inv_dir) / STATE_FILE).exists()
