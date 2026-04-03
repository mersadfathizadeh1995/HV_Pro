"""
HVSR Pro API -- Batch Processing
=================================

Process multiple files using the same ``HVSRAnalysisConfig``.
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


def _process_single(
    file_path: Path,
    output_dir: Path,
    config_dict: Dict[str, Any],
    output_format: str,
) -> Dict[str, Any]:
    """Process one file (safe for multiprocessing)."""
    from hvsr_pro.api.analysis import HVSRAnalysis
    from hvsr_pro.api.config import HVSRAnalysisConfig

    entry: Dict[str, Any] = {"file": str(file_path), "success": False, "error": None}
    try:
        config = HVSRAnalysisConfig.from_dict(config_dict)
        analysis = HVSRAnalysis(config)
        analysis.load_data(file_path)
        result = analysis.process()

        base = file_path.stem
        if output_format in ("json", "all"):
            analysis.save_results(output_dir / f"{base}_results.json", fmt="json")
        if output_format in ("csv", "all"):
            analysis.save_results(output_dir / f"{base}_results.csv", fmt="csv")
        if output_format in ("mat", "all"):
            analysis.save_results(output_dir / f"{base}_results.mat", fmt="mat")

        entry["success"] = True
        entry["summary"] = result.get_summary()

        pk = result.hvsr_result.primary_peak
        if pk:
            entry["peak_frequency"] = pk.frequency
            entry["peak_amplitude"] = pk.amplitude
    except Exception as exc:
        entry["error"] = str(exc)
        logger.error("Failed to process %s: %s", file_path, exc)

    return entry


def batch_process(
    files: List[Union[str, Path]],
    output_dir: Union[str, Path],
    config: Optional[Any] = None,
    *,
    output_format: str = "json",
    parallel: bool = False,
    n_workers: Optional[int] = None,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Process multiple files in batch.

    Parameters
    ----------
    files : list of paths
        Input seismic files.
    output_dir : path
        Where to write per-file results.
    config : HVSRAnalysisConfig or dict, optional
        Shared configuration.  Defaults to ``HVSRAnalysisConfig()``.
    output_format : str
        ``"json"``, ``"csv"``, ``"mat"``, or ``"all"``.
    parallel : bool
        Run files in separate processes.
    n_workers : int, optional
        Worker count (defaults to ``cpu_count - 1``).
    progress_callback : callable, optional
        ``callback(current, total, message)`` for progress reporting.

    Returns
    -------
    dict
        Mapping ``file_path -> result_dict``.
    """
    from hvsr_pro.api.config import HVSRAnalysisConfig

    files = [Path(f) for f in files]
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if config is None:
        config = HVSRAnalysisConfig()
    if isinstance(config, dict):
        config = HVSRAnalysisConfig.from_dict(config)

    config_dict = config.to_dict()
    results: Dict[str, Dict[str, Any]] = {}
    total = len(files)

    if parallel:
        import os

        if n_workers is None:
            n_workers = max(1, os.cpu_count() - 1)
        with ProcessPoolExecutor(max_workers=n_workers) as pool:
            futures = {
                pool.submit(_process_single, f, output_dir, config_dict, output_format): f
                for f in files
            }
            for i, future in enumerate(as_completed(futures)):
                fp = futures[future]
                try:
                    results[str(fp)] = future.result()
                except Exception as exc:
                    results[str(fp)] = {"file": str(fp), "success": False, "error": str(exc)}
                if progress_callback:
                    progress_callback(i + 1, total, f"Processed {fp.name}")
    else:
        for i, fp in enumerate(files):
            if progress_callback:
                progress_callback(i, total, f"Processing {fp.name}")
            results[str(fp)] = _process_single(fp, output_dir, config_dict, output_format)
            if progress_callback:
                progress_callback(i + 1, total, f"Completed {fp.name}")

    _save_summary(results, output_dir / "batch_summary.json")
    return results


def _save_summary(results: Dict[str, Dict], path: Path) -> None:
    from datetime import datetime

    n_ok = sum(1 for r in results.values() if r.get("success"))
    payload = {
        "timestamp": datetime.now().isoformat(),
        "total_files": len(results),
        "successful": n_ok,
        "failed": len(results) - n_ok,
        "results": results,
    }
    with open(path, "w") as fh:
        json.dump(payload, fh, indent=2)
