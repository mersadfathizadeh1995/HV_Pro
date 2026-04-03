"""
Session I/O
============

Save / restore an analysis session to a directory of JSON + pickle
files, compatible with the GUI's ``SessionManager``.
"""
from __future__ import annotations

import json
import logging
import pickle
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

logger = logging.getLogger(__name__)


def save_session(
    config,       # HVSRAnalysisConfig
    data,         # SeismicData | None
    windows,      # WindowCollection | None
    result,       # AnalysisResult | None
    session_dir: Union[str, Path],
) -> Path:
    """Persist config + results + pickles to *session_dir*."""
    sd = Path(session_dir)
    sd.mkdir(parents=True, exist_ok=True)

    cfg_path = sd / "analysis_config.json"
    config.save(cfg_path)

    if windows is not None:
        with open(sd / "windows.pkl", "wb") as f:
            pickle.dump(windows, f)

    r = result
    if r is not None and r.hvsr_result is not None:
        with open(sd / "hvsr_result.pkl", "wb") as f:
            pickle.dump(r.hvsr_result, f)
        if r.azimuthal_result is not None:
            with open(sd / "azimuthal_result.pkl", "wb") as f:
                pickle.dump(r.azimuthal_result, f)

    if data is not None:
        with open(sd / "seismic_data.pkl", "wb") as f:
            pickle.dump(data, f)

    from hvsr_pro.config.session import SessionState, FileInfo
    from hvsr_pro.config.session import ProcessingSettings as SPS
    from hvsr_pro.config.session import QCSettings as SQC

    p = config.processing
    qc = config.qc
    state = SessionState(
        version="2.0",
        created=datetime.now().isoformat(),
        session_folder=str(sd),
        processing=SPS(
            window_length=p.window_length,
            overlap=p.overlap,
            smoothing_bandwidth=p.smoothing_bandwidth,
            f_min=p.freq_min,
            f_max=p.freq_max,
            n_frequencies=p.n_frequencies,
        ),
        qc=SQC(
            enabled=qc.enabled,
            mode=qc.mode,
            cox_fdwra_enabled=qc.cox_fdwra.enabled,
            cox_n=qc.cox_fdwra.n,
            cox_max_iterations=qc.cox_fdwra.max_iterations,
            cox_min_iterations=qc.cox_fdwra.min_iterations,
            cox_distribution=qc.cox_fdwra.distribution,
        ),
        windows_file="windows.pkl",
        hvsr_result_file="hvsr_result.pkl",
        seismic_data_file="seismic_data.pkl",
        has_results=r is not None and r.hvsr_result is not None,
        has_full_data=True,
        has_azimuthal=r is not None and r.azimuthal_result is not None,
        azimuthal_result_file="azimuthal_result.pkl" if (
            r is not None and r.azimuthal_result is not None
        ) else "",
    )

    if r is not None and r.hvsr_result is not None:
        pk = r.hvsr_result.primary_peak
        if pk:
            state.peak_frequency = pk.frequency
            state.peak_amplitude = pk.amplitude
        state.n_total_windows = r.hvsr_result.total_windows
        state.n_active_windows = r.hvsr_result.valid_windows

    if windows is not None:
        from hvsr_pro.config.session import WindowState as WS
        for i, w in enumerate(windows.windows):
            state.window_states.append(WS(
                index=i,
                active=w.state.is_usable() if hasattr(w.state, "is_usable") else w.active,
                rejection_reason=getattr(w, "rejection_reason", None),
            ))

    with open(sd / "session.json", "w", encoding="utf-8") as f:
        json.dump(state.to_dict(), f, indent=2, ensure_ascii=False)

    return sd


def load_session(
    session_dir: Union[str, Path],
) -> Tuple[Any, Any, Any, Any]:
    """Restore from a session directory.

    Returns ``(config, data, windows, result)`` where *result* is an
    ``AnalysisResult`` or ``None``.
    """
    from hvsr_pro.api.config import HVSRAnalysisConfig
    from hvsr_pro.api.standard.analysis import AnalysisResult

    sd = Path(session_dir)
    config = None
    data = None
    windows = None
    hvsr_result = None
    az_result = None

    cfg_path = sd / "analysis_config.json"
    if cfg_path.exists():
        config = HVSRAnalysisConfig.load(cfg_path)
    else:
        config = HVSRAnalysisConfig()

    if (sd / "seismic_data.pkl").exists():
        with open(sd / "seismic_data.pkl", "rb") as f:
            data = pickle.load(f)

    if (sd / "windows.pkl").exists():
        with open(sd / "windows.pkl", "rb") as f:
            windows = pickle.load(f)

    if (sd / "hvsr_result.pkl").exists():
        with open(sd / "hvsr_result.pkl", "rb") as f:
            hvsr_result = pickle.load(f)

    if (sd / "azimuthal_result.pkl").exists():
        with open(sd / "azimuthal_result.pkl", "rb") as f:
            az_result = pickle.load(f)

    result = None
    if hvsr_result is not None:
        result = AnalysisResult(
            hvsr_result=hvsr_result,
            windows=windows,
            data=data,
            config=config,
            azimuthal_result=az_result,
        )

    return config, data, windows, result
