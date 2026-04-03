"""
Batch Processing API — Input Validation
========================================

Headless validation utilities for batch HVSR processing configurations.
Pure Python — no Qt dependencies.

Each validator returns a list of human-readable error or warning strings.
An empty list means the input is valid.

Functions
---------
validate_batch_config
    Check a :class:`BatchConfig` for structural and range errors.
validate_station_files
    Verify station file paths exist and have supported extensions.
validate_time_windows
    Ensure time windows are well-formed and non-overlapping.
validate_all
    Convenience wrapper that runs all three validators at once.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Dict, List

from hvsr_pro.packages.batch_processing.api.config import (
    BatchConfig,
    StationDef,
    TimeWindowDef,
)

__all__ = [
    "validate_batch_config",
    "validate_station_files",
    "validate_time_windows",
    "validate_all",
]

logger = logging.getLogger(__name__)

# Extensions recognised by ObsPy / HV Pro loaders (lower-case, with dot).
_SUPPORTED_EXTENSIONS = frozenset({
    ".miniseed", ".mseed",
    ".sac",
    ".saf",
    ".gcf",
    ".txt",
    ".csv",
    ".seg2", ".sg2",
    ".segy", ".sgy",
    ".dat",
    ".asc",
})


# ────────────────────────────────────────────────────────────────────
# BatchConfig validation
# ────────────────────────────────────────────────────────────────────

def validate_batch_config(config: BatchConfig) -> List[str]:
    """Validate a complete :class:`BatchConfig` for range and structural errors.

    Parameters
    ----------
    config : BatchConfig
        The batch configuration to validate.

    Returns
    -------
    List[str]
        Error/warning messages.  Empty when everything is valid.
    """
    errors: List[str] = []

    # ── Stations ──────────────────────────────────────────────────
    if not config.stations:
        errors.append("No stations defined — at least one station is required.")

    # ── Output directory ──────────────────────────────────────────
    if not config.output_dir:
        errors.append("Output directory is not set.")

    # ── Processing settings ───────────────────────────────────────
    proc = config.processing

    if proc.window_length <= 0:
        errors.append(
            f"window_length must be > 0 (got {proc.window_length})."
        )

    if not (0.0 <= proc.overlap < 1.0):
        errors.append(
            f"overlap must be in [0.0, 1.0) (got {proc.overlap})."
        )

    if proc.freq_min <= 0:
        errors.append(
            f"freq_min must be > 0 (got {proc.freq_min})."
        )

    if proc.freq_max <= proc.freq_min:
        errors.append(
            f"freq_max ({proc.freq_max}) must be greater than "
            f"freq_min ({proc.freq_min})."
        )

    if proc.n_frequencies <= 0:
        errors.append(
            f"n_frequencies must be > 0 (got {proc.n_frequencies})."
        )

    # ── Peak detection settings ───────────────────────────────────
    pk = config.peaks

    if pk.min_prominence <= 0:
        errors.append(
            f"min_prominence must be > 0 (got {pk.min_prominence})."
        )

    if pk.min_amplitude <= 0:
        errors.append(
            f"min_amplitude must be > 0 (got {pk.min_amplitude})."
        )

    if pk.n_peaks <= 0:
        errors.append(
            f"n_peaks must be > 0 (got {pk.n_peaks})."
        )

    # ── QC settings ───────────────────────────────────────────────
    qc = config.qc

    if qc.stalta_enabled:
        sta = qc.stalta
        if sta.sta_length <= 0:
            errors.append(
                f"STA/LTA: sta_length must be > 0 (got {sta.sta_length})."
            )
        if sta.lta_length <= sta.sta_length:
            errors.append(
                f"STA/LTA: lta_length ({sta.lta_length}) must be greater "
                f"than sta_length ({sta.sta_length})."
            )

    if errors:
        logger.warning(
            "Batch config validation found %d issue(s).", len(errors)
        )
    else:
        logger.debug("Batch config validation passed.")

    return errors


# ────────────────────────────────────────────────────────────────────
# Station file validation
# ────────────────────────────────────────────────────────────────────

def validate_station_files(stations: List[StationDef]) -> List[str]:
    """Verify that every station has files that exist and are supported.

    Parameters
    ----------
    stations : List[StationDef]
        Station definitions to validate.

    Returns
    -------
    List[str]
        Error messages.  Empty when all files are valid.
    """
    errors: List[str] = []

    seen_nums: Dict[int, str] = {}

    for stn in stations:
        label = stn.station_name or f"Station {stn.station_num}"

        # Duplicate station numbers
        if stn.station_num in seen_nums:
            errors.append(
                f"Duplicate station number {stn.station_num}: "
                f"'{label}' conflicts with '{seen_nums[stn.station_num]}'."
            )
        else:
            seen_nums[stn.station_num] = label

        # At least one file
        if not stn.files:
            errors.append(f"{label}: no data files assigned.")
            continue

        for fpath in stn.files:
            # File existence
            if not os.path.isfile(fpath):
                errors.append(f"{label}: file not found — {fpath}")
                continue

            # Supported extension
            _, ext = os.path.splitext(fpath)
            if ext.lower() not in _SUPPORTED_EXTENSIONS:
                errors.append(
                    f"{label}: unsupported file extension '{ext}' — {fpath}"
                )

    if errors:
        logger.warning(
            "Station file validation found %d issue(s).", len(errors)
        )
    else:
        logger.debug("Station file validation passed.")

    return errors


# ────────────────────────────────────────────────────────────────────
# Time-window validation
# ────────────────────────────────────────────────────────────────────

_ISO_FORMATS = ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S")


def _parse_utc(value: str) -> datetime | None:
    """Try to parse a UTC timestamp string; return *None* on failure."""
    for fmt in _ISO_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def validate_time_windows(windows: List[TimeWindowDef]) -> List[str]:
    """Validate a list of time-window definitions.

    Parameters
    ----------
    windows : List[TimeWindowDef]
        Time windows to validate.

    Returns
    -------
    List[str]
        Error and warning messages.  Empty when everything is valid.
    """
    errors: List[str] = []

    seen_names: set[str] = set()
    parsed: list[tuple[str, datetime, datetime]] = []

    for win in windows:
        label = win.name or "(unnamed)"

        # Unique names
        if win.name in seen_names:
            errors.append(f"Duplicate time-window name: '{win.name}'.")
        else:
            seen_names.add(win.name)

        # Parse timestamps
        start = _parse_utc(win.start_utc)
        end = _parse_utc(win.end_utc)

        if start is None:
            errors.append(
                f"Window '{label}': invalid or empty start_utc "
                f"('{win.start_utc}')."
            )
        if end is None:
            errors.append(
                f"Window '{label}': invalid or empty end_utc "
                f"('{win.end_utc}')."
            )

        if start is not None and end is not None:
            if end <= start:
                errors.append(
                    f"Window '{label}': end_utc must be after start_utc "
                    f"(start={win.start_utc}, end={win.end_utc})."
                )
            else:
                parsed.append((label, start, end))

    # Overlap check (warnings, not errors)
    parsed.sort(key=lambda t: t[1])
    for i in range(len(parsed) - 1):
        name_a, _start_a, end_a = parsed[i]
        name_b, start_b, _end_b = parsed[i + 1]
        if end_a > start_b:
            errors.append(
                f"WARNING: windows '{name_a}' and '{name_b}' overlap."
            )

    if errors:
        logger.warning(
            "Time-window validation found %d issue(s).", len(errors)
        )
    else:
        logger.debug("Time-window validation passed.")

    return errors


# ────────────────────────────────────────────────────────────────────
# Convenience wrapper
# ────────────────────────────────────────────────────────────────────

def validate_all(config: BatchConfig) -> Dict[str, List[str]]:
    """Run every validator against a :class:`BatchConfig` at once.

    Parameters
    ----------
    config : BatchConfig
        The batch configuration to validate.

    Returns
    -------
    Dict[str, List[str]]
        ``{"config": [...], "files": [...], "time_windows": [...]}``.
        Each value is an empty list when that category is valid.
    """
    results = {
        "config": validate_batch_config(config),
        "files": validate_station_files(config.stations),
        "time_windows": validate_time_windows(
            config.time_config.windows
        ),
    }

    total = sum(len(v) for v in results.values())
    if total:
        logger.info("validate_all: %d total issue(s) found.", total)
    else:
        logger.info("validate_all: configuration is valid.")

    return results
