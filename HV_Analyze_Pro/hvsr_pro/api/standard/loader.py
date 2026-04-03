"""
Data Loader
============

Pure functions for loading seismic data.  Accepts an
``HVSRAnalysisConfig`` and returns a ``SeismicData`` object.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


def load_seismic_data(
    config,
    file_path: Union[str, Path, List[str], Dict[str, str]],
    *,
    format: str = "auto",
    degrees_from_north: Optional[float] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    timezone_offset: int = 0,
) -> Any:
    """Load seismic data according to *config* and return ``SeismicData``.

    Parameters
    ----------
    config : HVSRAnalysisConfig
        The active configuration (``data_load`` / ``time_range`` fields
        may be mutated to reflect what was actually loaded).
    file_path
        A single path, a list of MiniSEED paths, or a dict mapping
        component letters to paths (``{'N': …, 'E': …, 'Z': …}``).
    format, degrees_from_north, start_time, end_time, timezone_offset
        Override individual ``DataLoadConfig`` / ``TimeRangeConfig``
        fields for this call only.

    Returns
    -------
    SeismicData
    """
    from hvsr_pro.core import HVSRDataHandler

    handler = HVSRDataHandler()
    dl = config.data_load

    if format != "auto":
        dl.file_format = format
    if degrees_from_north is not None:
        dl.degrees_from_north = degrees_from_north

    if isinstance(file_path, dict):
        dl.load_mode = "multi_component"
        files = [str(file_path.get(c)) for c in ("N", "E", "Z") if c in file_path]
        data = handler.load_multi_component(
            files,
            format=dl.file_format,
            degrees_from_north=dl.degrees_from_north,
        )
    elif isinstance(file_path, (list, tuple)):
        if len(file_path) <= 3 and dl.file_format != "auto":
            dl.load_mode = "multi_component"
            data = handler.load_multi_component(
                [str(p) for p in file_path],
                format=dl.file_format,
                degrees_from_north=dl.degrees_from_north,
            )
        else:
            dl.load_mode = "multi_type1"
            data = handler.load_multi_miniseed_type1([str(p) for p in file_path])
    else:
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"File not found: {p}")
        dl.load_mode = "single"
        data = handler.load_data(str(p), format=dl.file_format)

    if start_time or end_time:
        tr = config.time_range
        tr.enabled = True
        tr.start = start_time
        tr.end = end_time
        tr.timezone_offset = timezone_offset
        rt = tr.to_runtime_dict()
        if rt:
            data = handler.slice_by_time(
                data, rt["start"], rt["end"], rt["timezone_offset"]
            )

    return data
