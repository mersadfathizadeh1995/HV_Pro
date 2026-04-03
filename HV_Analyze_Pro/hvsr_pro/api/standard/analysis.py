"""
HVSR Pro API -- Analysis Pipeline (Thin Facade)
=================================================

``HVSRAnalysis`` holds analysis state and delegates to focused modules
inside ``hvsr_pro.api.standard.*``:

- ``loader`` -- data I/O
- ``peaks`` -- peak detection (3 modes)
- ``export`` -- save_results / save_plot / generate_report
- ``session_io`` -- save_session / load_session
- ``qc_wiring`` -- QC helper functions

Usage::

    from hvsr_pro.api import HVSRAnalysis
    analysis = HVSRAnalysis()
    analysis.load_data("record.mseed")
    result = analysis.process()
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from hvsr_pro.api.config import HVSRAnalysisConfig

logger = logging.getLogger(__name__)

ProgressCallback = Optional[Callable[[int, str], None]]


# ---------------------------------------------------------------------------
# Result containers  (kept here -- lightweight, widely imported)
# ---------------------------------------------------------------------------

@dataclass
class QCSummary:
    """Human-readable summary of what QC did."""

    phase1_applied: bool = False
    phase2_applied: bool = False
    fdwra_applied: bool = False
    post_hvsr_applied: bool = False
    total_windows: int = 0
    active_windows: int = 0
    phase1_detail: Optional[str] = None
    fdwra_detail: Optional[str] = None
    post_hvsr_detail: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phase1_applied": self.phase1_applied,
            "phase2_applied": self.phase2_applied,
            "fdwra_applied": self.fdwra_applied,
            "post_hvsr_applied": self.post_hvsr_applied,
            "total_windows": self.total_windows,
            "active_windows": self.active_windows,
            "phase1_detail": self.phase1_detail,
            "fdwra_detail": self.fdwra_detail,
            "post_hvsr_detail": self.post_hvsr_detail,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


@dataclass
class AnalysisResult:
    """Bundle returned by ``HVSRAnalysis.process()``."""

    hvsr_result: Any  # HVSRResult
    windows: Any  # WindowCollection
    data: Any  # SeismicData
    config: HVSRAnalysisConfig
    qc_summary: QCSummary = field(default_factory=QCSummary)
    azimuthal_result: Any = None

    def get_summary(self) -> Dict[str, Any]:
        summary: Dict[str, Any] = {"config": self.config.to_dict()}

        if self.data is not None:
            summary["data"] = {
                "duration_seconds": self.data.duration,
                "sampling_rate": self.data.east.sampling_rate,
                "n_samples": len(self.data.east.data),
                "start_time": str(self.data.start_time) if self.data.start_time else None,
            }

        if self.windows is not None:
            summary["windows"] = {
                "total": self.windows.n_windows,
                "active": self.windows.n_active,
                "acceptance_rate": self.windows.acceptance_rate,
            }

        r = self.hvsr_result
        if r is not None:
            summary["result"] = {
                "total_windows": r.total_windows,
                "valid_windows": r.valid_windows,
                "frequencies": {
                    "min": float(r.frequencies[0]),
                    "max": float(r.frequencies[-1]),
                    "n_points": len(r.frequencies),
                },
            }
            if r.primary_peak:
                summary["result"]["primary_peak"] = {
                    "frequency": r.primary_peak.frequency,
                    "amplitude": r.primary_peak.amplitude,
                }

        summary["qc"] = self.qc_summary.to_dict()
        return summary


# ---------------------------------------------------------------------------
# Auto-decimation helper
# ---------------------------------------------------------------------------

def _auto_decimate(data, freq_max: float, _progress=None):
    """Downsample *data* when sampling rate far exceeds what *freq_max* needs.

    Target sampling rate is ``2.5 * freq_max`` (Nyquist headroom).
    Uses ``scipy.signal.decimate`` with an order-8 Chebyshev Type I
    anti-alias filter, applied in stages if the factor > 13.
    Operates on a *copy* so the original data object is not mutated.
    """
    import copy
    from scipy.signal import decimate as _decimate

    sr = data.east.sampling_rate
    target_sr = 2.5 * freq_max
    if sr <= target_sr:
        return data

    factor = int(sr / target_sr)
    if factor < 2:
        return data

    new_sr = sr / factor
    if _progress:
        _progress(
            25,
            f"Decimating {sr:.0f} Hz -> {new_sr:.1f} Hz (factor {factor}) "
            f"for freq_max={freq_max} Hz...",
        )

    data = copy.copy(data)
    for comp in (data.east, data.north, data.vertical):
        remaining = factor
        arr = comp.data.astype(float)
        while remaining > 1:
            step = min(remaining, 13)
            arr = _decimate(arr, step, ftype="iir", zero_phase=True)
            remaining //= step
        comp.data = arr
        comp.sampling_rate = new_sr

    return data


# ---------------------------------------------------------------------------
# Main analysis class  (thin facade)
# ---------------------------------------------------------------------------

class HVSRAnalysis:
    """Headless, config-driven HVSR processing pipeline."""

    def __init__(self, config: Optional[HVSRAnalysisConfig] = None):
        self._config = config or HVSRAnalysisConfig()
        self._data = None
        self._windows = None
        self._result: Optional[AnalysisResult] = None
        self._raw_result = None  # pre-QC result for comparison plots

    # -- properties --------------------------------------------------------

    @property
    def config(self) -> HVSRAnalysisConfig:
        return self._config

    @config.setter
    def config(self, value: HVSRAnalysisConfig):
        self._config = value

    @property
    def data(self):
        return self._data

    @property
    def windows(self):
        return self._windows

    @property
    def result(self) -> Optional[AnalysisResult]:
        return self._result

    # -- configuration helpers ---------------------------------------------

    def configure(self, **kwargs) -> "HVSRAnalysis":
        for key, value in kwargs.items():
            if hasattr(self._config.processing, key):
                setattr(self._config.processing, key, value)
            else:
                raise ValueError(f"Unknown processing parameter: {key}")
        return self

    # -- data loading (delegates to loader) --------------------------------

    def load_data(
        self,
        file_path: Union[str, Path, List[str], Dict[str, str]],
        *,
        format: str = "auto",
        degrees_from_north: Optional[float] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        timezone_offset: int = 0,
    ) -> "HVSRAnalysis":
        from hvsr_pro.api.standard.loader import load_seismic_data

        self._data = load_seismic_data(
            self._config, file_path,
            format=format,
            degrees_from_north=degrees_from_north,
            start_time=start_time,
            end_time=end_time,
            timezone_offset=timezone_offset,
        )
        return self

    # -- main pipeline (orchestration stays here) --------------------------

    def process(self, *, progress_callback: ProgressCallback = None) -> AnalysisResult:
        """Run the full HVSR pipeline."""
        if self._data is None:
            raise ValueError("No data loaded. Call load_data() first.")

        from hvsr_pro.processing import WindowManager, RejectionEngine, HVSRProcessor
        from hvsr_pro.api.standard.qc_wiring import (
            apply_custom_qc_phase1,
            should_apply_fdwra,
            build_post_hvsr_algos,
            make_dummy_result,
        )

        cfg = self._config
        p = cfg.processing
        qc_cfg = cfg.qc
        qc_summary = QCSummary()

        def _progress(pct: int, msg: str):
            if progress_callback is not None:
                progress_callback(pct, msg)

        from hvsr_pro.core import HVSRDataHandler
        data = self._data
        handler = HVSRDataHandler()

        if p.manual_sampling_rate:
            _progress(12, f"Overriding sampling rate to {p.manual_sampling_rate:.4f} Hz...")
            data.east.sampling_rate = p.manual_sampling_rate
            data.north.sampling_rate = p.manual_sampling_rate
            data.vertical.sampling_rate = p.manual_sampling_rate

        rt = cfg.time_range.to_runtime_dict()
        if rt is not None:
            _progress(15, "Applying time range filter...")
            data = handler.slice_by_time(data, rt["start"], rt["end"], rt["timezone_offset"])
            _progress(20, f"Sliced to {data.duration / 3600:.2f} hours")

        # -- Step 1.8: auto-decimate if sampling rate >> freq_max ----------
        data = _auto_decimate(data, p.freq_max, _progress)

        _progress(30, "Creating windows...")
        wm = WindowManager(window_length=p.window_length, overlap=p.overlap)
        windows = wm.create_windows(data, calculate_quality=True)
        qc_summary.total_windows = windows.n_windows

        engine = RejectionEngine()
        qc_disabled = not qc_cfg.enabled
        eval_result = None

        if qc_disabled:
            _progress(50, "Quality control disabled (skipping)...")
        elif not qc_cfg.phase1_enabled:
            _progress(50, "Phase 1 QC disabled (skipping pre-HVSR rejection)...")
        elif qc_cfg.mode == "sesame":
            _progress(50, "Applying quality control (SESAME standard)...")
            engine.create_default_pipeline(mode="sesame")
            eval_result = engine.evaluate(windows, auto_apply=True)
            qc_summary.phase1_applied = True
        elif qc_cfg.mode == "custom":
            _progress(50, "Applying quality control (custom settings)...")
            apply_custom_qc_phase1(engine, qc_cfg)
            eval_result = engine.evaluate(windows, auto_apply=True)
            qc_summary.phase1_applied = True
        else:
            _progress(50, f"Unknown QC mode '{qc_cfg.mode}', using SESAME standard...")
            engine.create_default_pipeline(mode="sesame")
            eval_result = engine.evaluate(windows, auto_apply=True)
            qc_summary.phase1_applied = True

        qc_msg = (
            f"QC: {windows.n_active}/{windows.n_windows} windows active "
            f"({windows.acceptance_rate * 100:.1f}%)"
        )
        if eval_result is not None:
            qc_msg += f"  [{RejectionEngine.format_qc_summary(eval_result)}]"
            qc_summary.phase1_detail = qc_msg
        _progress(60, qc_msg)

        if windows.n_active == 0:
            _progress(65, f"ERROR: No windows passed QC (0/{windows.n_windows})")
            dummy = make_dummy_result(p, windows, "No windows passed QC")
            qc_summary.active_windows = 0
            qc_summary.errors.append("No windows passed QC")
            self._windows = windows
            self._result = AnalysisResult(
                hvsr_result=dummy, windows=windows, data=data,
                config=cfg, qc_summary=qc_summary,
            )
            return self._result

        if windows.n_active < 10 and windows.n_windows > 50:
            qc_summary.warnings.append(
                f"Only {windows.n_active} windows passed QC out of {windows.n_windows}"
            )

        _progress(70, "Computing HVSR...")
        processor = HVSRProcessor(
            smoothing_method=p.smoothing_method,
            smoothing_bandwidth=p.smoothing_bandwidth,
            horizontal_method=p.horizontal_method,
            f_min=p.freq_min,
            f_max=p.freq_max,
            n_frequencies=p.n_frequencies,
            parallel=p.use_parallel,
            n_cores=p.n_cores,
            statistics_method=p.statistics_method,
            peak_basis=p.peak_basis,
            min_prominence=p.min_prominence,
            min_amplitude=p.min_amplitude,
        )
        result = processor.process(windows, detect_peaks_flag=True, save_window_spectra=True)

        # Snapshot before FDWRA / post-HVSR QC for comparison plots
        import copy
        self._raw_result = copy.deepcopy(result)

        apply_fdwra = should_apply_fdwra(qc_cfg)
        if apply_fdwra:
            _progress(85, "Applying Cox FDWRA (peak consistency)...")
            raw_window_spectra = list(result.window_spectra)
            cox = qc_cfg.cox_fdwra
            fdwra_result = engine.evaluate_fdwra(
                windows, result,
                n=cox.n,
                max_iterations=cox.max_iterations,
                min_iterations=cox.min_iterations,
                distribution_fn=cox.distribution,
                distribution_mc=cox.distribution,
                search_range_hz=(p.freq_min, p.freq_max),
                auto_apply=True,
            )
            n_rej = fdwra_result["n_rejected"]
            iters = fdwra_result["iterations"]
            qc_summary.fdwra_applied = True
            qc_summary.fdwra_detail = (
                f"Cox FDWRA: {n_rej} rejected, converged in {iters} iterations"
            )
            _progress(90, qc_summary.fdwra_detail)

            if n_rej > 0:
                if windows.n_active == 0:
                    _progress(92, "ERROR: Cox FDWRA rejected all windows")
                    dummy = make_dummy_result(p, windows, "Cox FDWRA rejected all windows")
                    qc_summary.active_windows = 0
                    qc_summary.errors.append("Cox FDWRA rejected all windows")
                    self._windows = windows
                    self._result = AnalysisResult(
                        hvsr_result=dummy, windows=windows, data=data,
                        config=cfg, qc_summary=qc_summary,
                    )
                    return self._result
                _progress(92, "Recomputing HVSR after Cox FDWRA...")
                result = processor.process(windows, detect_peaks_flag=True, save_window_spectra=True)
                result.metadata["raw_window_spectra"] = raw_window_spectra
            else:
                result.metadata["raw_window_spectra"] = raw_window_spectra

        if qc_cfg.enabled and qc_cfg.phase2_enabled and windows.n_active > 0:
            post_algos = build_post_hvsr_algos(qc_cfg)
            if post_algos:
                _progress(95, "Applying post-HVSR rejection algorithms...")
                engine.post_hvsr_algorithms = post_algos
                post_result = engine.evaluate_post_hvsr(windows, result, auto_apply=True)
                n_post = post_result.get("n_rejected", 0)
                qc_summary.post_hvsr_applied = True
                qc_summary.post_hvsr_detail = (
                    f"Post-HVSR: {n_post} rejected, {windows.n_active} remaining"
                )
                if n_post > 0 and windows.n_active > 0:
                    _progress(97, f"Post-HVSR: {n_post} windows rejected, recomputing...")
                    result = processor.process(
                        windows, detect_peaks_flag=True, save_window_spectra=True
                    )
                _progress(98, qc_summary.post_hvsr_detail)

        qc_summary.active_windows = windows.n_active
        qc_summary.phase2_applied = qc_summary.fdwra_applied or qc_summary.post_hvsr_applied
        _progress(100, "Complete!")

        self._windows = windows
        self._result = AnalysisResult(
            hvsr_result=result, windows=windows, data=data,
            config=cfg, qc_summary=qc_summary,
        )
        return self._result

    # -- azimuthal ---------------------------------------------------------

    def process_azimuthal(self, *, progress_callback: ProgressCallback = None) -> Any:
        if self._windows is None:
            raise ValueError("Run process() before process_azimuthal().")
        from hvsr_pro.processing.azimuthal import AzimuthalHVSRProcessor

        az = AzimuthalHVSRProcessor()
        az_result = az.process(self._windows, progress_callback=progress_callback)
        if self._result is not None:
            self._result.azimuthal_result = az_result
        return az_result

    # -- peak detection (delegates to peaks module) ------------------------

    def detect_peaks(
        self,
        mode: str = "auto_multi",
        n_peaks: int = 3,
        min_prominence: float = 0.3,
        min_amplitude: float = 1.0,
        freq_range: Optional[tuple] = None,
        use_median: bool = True,
    ) -> List[Dict[str, Any]]:
        if self._result is None or self._result.hvsr_result is None:
            raise ValueError("No results. Call process() first.")

        from hvsr_pro.api.standard import peaks as _peaks

        r = self._result.hvsr_result
        p = self._config.processing
        f_range = freq_range or (p.freq_min, p.freq_max)

        if mode == "auto_primary":
            return _peaks.detect_primary_peak(
                r, min_prominence=min_prominence,
                min_amplitude=min_amplitude, freq_range=f_range,
                use_median=use_median,
            )
        elif mode == "auto_top_n":
            return _peaks.detect_top_n_peaks(
                r, n_peaks=n_peaks, prominence=min_prominence,
                freq_range=f_range, use_median=use_median,
            )
        else:
            return _peaks.detect_multi_peaks(
                r, prominence=min_prominence,
                freq_range=f_range, use_median=use_median,
            )

    # -- export (delegates to export module) -------------------------------

    def save_results(self, output_path: Union[str, Path], fmt: str = "json") -> None:
        from hvsr_pro.api.standard.export import save_results
        save_results(self._result, self._config, output_path, fmt=fmt)

    def save_plot(
        self, output_path: Union[str, Path],
        plot_type: str = "hvsr", dpi: int = 150,
        show_median: bool = True, show_mean: bool = False,
    ) -> None:
        from hvsr_pro.api.standard.export import save_plot
        save_plot(self._result, self._windows, output_path,
                  plot_type=plot_type, dpi=dpi,
                  show_median=show_median, show_mean=show_mean,
                  data=self._data, style=self._config.plot_style,
                  raw_result=getattr(self, '_raw_result', None))

    def generate_report(
        self, output_dir: Union[str, Path],
        base_name: str = "hvsr", dpi: int = 150,
    ) -> Dict[str, str]:
        from hvsr_pro.api.standard.export import generate_report
        return generate_report(
            self._result, self._windows, self._config,
            output_dir, base_name=base_name, dpi=dpi,
            data=self._data,
            raw_result=getattr(self, '_raw_result', None),
        )

    # -- session I/O (delegates to session_io module) ----------------------

    def save_session(self, session_dir: Union[str, Path]) -> Path:
        from hvsr_pro.api.standard.session_io import save_session
        return save_session(
            self._config, self._data, self._windows,
            self._result, session_dir,
        )

    def load_session(self, session_dir: Union[str, Path]) -> "HVSRAnalysis":
        from hvsr_pro.api.standard.session_io import load_session

        config, data, windows, result = load_session(session_dir)
        self._config = config
        self._data = data
        self._windows = windows
        self._result = result
        return self

    # -- summary -----------------------------------------------------------

    def get_summary(self) -> Dict[str, Any]:
        if self._result is not None:
            return self._result.get_summary()
        summary: Dict[str, Any] = {"config": self._config.to_dict()}
        if self._data:
            summary["data"] = {
                "duration_seconds": self._data.duration,
                "sampling_rate": self._data.east.sampling_rate,
                "n_samples": len(self._data.east.data),
                "start_time": str(self._data.start_time) if self._data.start_time else None,
            }
        return summary
