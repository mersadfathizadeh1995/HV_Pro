"""
Peak Detection
==============

Mirrors the GUI's three peak-detection modes as standalone functions.

Each function accepts an ``HVSRResult``, runs the appropriate
algorithm from ``hvsr_pro.processing.windows.peaks``, stores the
detected peaks back into ``hvsr_result.peaks``, and returns a list
of plain dicts suitable for JSON serialisation.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _get_curve(hvsr_result, use_median: bool):
    return hvsr_result.median_hvsr if use_median else hvsr_result.mean_hvsr


def _to_peak_objects(peak_dicts: List[Dict]) -> list:
    """Convert plain dicts to ``Peak`` dataclass instances."""
    from hvsr_pro.processing.hvsr.structures import Peak

    return [
        Peak(
            frequency=d["frequency"],
            amplitude=d["amplitude"],
            prominence=d.get("prominence", 0),
        )
        for d in peak_dicts
    ]


# ------------------------------------------------------------------
# Public API -- one function per GUI mode
# ------------------------------------------------------------------

def detect_primary_peak(
    hvsr_result,
    *,
    min_prominence: float = 0.5,
    min_amplitude: float = 1.0,
    freq_range: Optional[Tuple[float, float]] = None,
    use_median: bool = True,
) -> List[Dict[str, Any]]:
    """Detect the single highest-amplitude peak (``auto_primary``).

    Returns a list with zero or one peak dict.
    """
    from hvsr_pro.processing.windows.peaks import detect_peaks as _detect

    curve = _get_curve(hvsr_result, use_median)
    f_range = freq_range or (float(hvsr_result.frequencies[0]),
                              float(hvsr_result.frequencies[-1]))

    raw = _detect(
        hvsr_result.frequencies, curve,
        min_prominence=min_prominence,
        min_amplitude=min_amplitude,
        freq_range=f_range,
    )
    raw = raw[:1]

    peak_dicts = [
        {"frequency": pk.frequency, "amplitude": pk.amplitude,
         "prominence": pk.prominence, "source": "Auto Primary"}
        for pk in raw
    ]

    hvsr_result.peaks = list(raw)
    return peak_dicts


def detect_top_n_peaks(
    hvsr_result,
    *,
    n_peaks: int = 3,
    prominence: float = 0.5,
    freq_range: Optional[Tuple[float, float]] = None,
    use_median: bool = True,
) -> List[Dict[str, Any]]:
    """Detect the top *n_peaks* by prominence (``auto_top_n``).

    Mirrors the GUI "Auto Top N" mode.
    """
    from hvsr_pro.processing.windows.peaks import find_top_n_peaks as _find

    curve = _get_curve(hvsr_result, use_median)
    f_range = freq_range or (float(hvsr_result.frequencies[0]),
                              float(hvsr_result.frequencies[-1]))

    peak_dicts = _find(
        hvsr_result.frequencies, curve,
        n_peaks=n_peaks,
        prominence=prominence,
        freq_range=f_range,
    )

    hvsr_result.peaks = _to_peak_objects(peak_dicts)
    return peak_dicts


def detect_multi_peaks(
    hvsr_result,
    *,
    prominence: float = 0.3,
    min_distance: int = 5,
    freq_range: Optional[Tuple[float, float]] = None,
    use_median: bool = True,
) -> List[Dict[str, Any]]:
    """Detect all peaks above a prominence threshold (``auto_multi``).

    Mirrors the GUI "Auto Multi-Peak" mode.
    """
    from hvsr_pro.processing.windows.peaks import find_multi_peaks as _find

    curve = _get_curve(hvsr_result, use_median)
    f_range = freq_range or (float(hvsr_result.frequencies[0]),
                              float(hvsr_result.frequencies[-1]))

    peak_dicts = _find(
        hvsr_result.frequencies, curve,
        prominence=prominence,
        min_distance=min_distance,
        freq_range=f_range,
    )

    hvsr_result.peaks = _to_peak_objects(peak_dicts)
    return peak_dicts
