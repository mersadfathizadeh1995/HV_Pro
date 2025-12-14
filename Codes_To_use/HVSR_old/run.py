from __future__ import annotations

"""Convenience entry-point to perform MiniSEED reduction in one command.

Example
-------
python run.py \
    --csv intervals.csv \
    --data-dir /path/to/miniseed \
    --pattern "AR.STN{station:02d}.centaur-3_0655_{date}_{hour:02d}0000.miniseed" \
    --station 86 \
    --sampling-rate 500 \
    --output results/
"""

from pathlib import Path

# ─────────────────────────  USER - S E T T I N G S  ──────────────────────────
CSV_PATH = Path(r"D:\Research\Softwars\HVSR\Test_station1\windows.csv")  # ← your CSV
DATA_DIR = Path(r"D:\Research\Softwars\HVSR\Test_station1")  # ← folder with .miniseed files
# Provide ONLY the constant prefix that every MiniSEED filename starts with:
#   e.g. "AR.STN{station:02d}.centaur-3_0655_"  or  "AR.STN01.centaur-3_0655_"
PATTERN_PREFIX = "AR.STN{station:02d}.centaur-3_0655_"
STATION_ID = 1  # integer that replaces {station} if present in PATTERN_PREFIX
SAMPLING_RATE = 500.0  # Hz
OUTPUT_DIR = Path(r"D:\Research\Softwars\HVSR\Test_station1\array")  # where ArrayData_HV*.mat is written
VERBOSE = True  # set False for quiet mode
# ──────────────────────────────────────────────────────────────────────────────

# ---------------------------------------------------------------------------
# nothing below needs editing
# ---------------------------------------------------------------------------
from miniseed_array_reduction import process_station


def _build_pattern(prefix: str, station_id: int) -> str:
    """Return a full format-string with {date} and {hour} placeholders appended."""

    if "{station" in prefix:
        prefix = prefix.format(station=station_id)
    # Ensure the prefix ends with an underscore so we do not double-insert one
    if not prefix.endswith("_"):
        prefix += "_"
    return f"{prefix}{{date}}_{{hour:02d}}0000.miniseed"


def main() -> None:
    pattern_str = _build_pattern(PATTERN_PREFIX, STATION_ID)
    pattern_path = str((DATA_DIR / pattern_str).resolve())

    process_station(
        csv_path=CSV_PATH.resolve(),
        pattern=pattern_path,
        sampling_rate=SAMPLING_RATE,
        station_id=STATION_ID,
        output_dir=OUTPUT_DIR.resolve(),
        verbose=VERBOSE,
    )


if __name__ == "__main__":
    main()










