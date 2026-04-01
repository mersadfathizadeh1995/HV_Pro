"""
HVSR Pro API -- Analysis Pipeline
===================================

``HVSRAnalysis`` is the single, headless implementation of the HVSR
processing pipeline.  Both the GUI (``ProcessingThread``) and a future
MCP server delegate to this class.

Usage::

    from hvsr_pro.api import HVSRAnalysis
    from hvsr_pro.api.config import HVSRAnalysisConfig

    config = HVSRAnalysisConfig.sesame_default()
    analysis = HVSRAnalysis(config)
    analysis.load_data("record.mseed")
    result = analysis.process()

    print(result.hvsr_result.primary_peak)
    analysis.save_results("out.json")
"""

from __future__ import annotations

import json
import logging
import pickle
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

import numpy as np

from hvsr_pro.api.config import HVSRAnalysisConfig

logger = logging.getLogger(__name__)

ProgressCallback = Optional[Callable[[int, str], None]]


# ---------------------------------------------------------------------------
# Result container
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
    """Bundle returned by ``HVSRAnalysis.process()``.

    Carries the same triple that the GUI's
    ``ProcessingThread.finished.emit(result, windows, data)`` sends,
    plus a structured QC summary.
    """

    hvsr_result: Any  # HVSRResult
    windows: Any  # WindowCollection
    data: Any  # SeismicData
    config: HVSRAnalysisConfig
    qc_summary: QCSummary = field(default_factory=QCSummary)
    azimuthal_result: Any = None  # AzimuthalHVSRResult | None

    def get_summary(self) -> Dict[str, Any]:
        """Produce a JSON-safe summary dict."""
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
# Main analysis class
# ---------------------------------------------------------------------------

class HVSRAnalysis:
    """Headless, config-driven HVSR processing pipeline.

    Parameters
    ----------
    config : HVSRAnalysisConfig, optional
        Pre-built config.  Can also be set later with ``configure()``.
    """

    def __init__(self, config: Optional[HVSRAnalysisConfig] = None):
        self._config = config or HVSRAnalysisConfig()
        self._data = None
        self._windows = None
        self._result: Optional[AnalysisResult] = None

    # -- properties --------------------------------------------------------

    @property
    def config(self) -> HVSRAnalysisConfig:
        return self._config

    @config.setter
    def config(self, value: HVSRAnalysisConfig):
        self._config = value

    @property
    def data(self):
        """Loaded ``SeismicData``."""
        return self._data

    @property
    def windows(self):
        """``WindowCollection`` (available after ``process()``)."""
        return self._windows

    @property
    def result(self) -> Optional[AnalysisResult]:
        """Last ``AnalysisResult`` (available after ``process()``)."""
        return self._result

    # -- configuration helpers ---------------------------------------------

    def configure(self, **kwargs) -> "HVSRAnalysis":
        """Set processing parameters by keyword.

        Accepted top-level keys are the fields of ``ProcessingConfig``
        (e.g. ``window_length``, ``overlap``, ``freq_min``).  For deeper
        config, manipulate ``self.config`` directly.

        Returns ``self`` for method chaining.
        """
        for key, value in kwargs.items():
            if hasattr(self._config.processing, key):
                setattr(self._config.processing, key, value)
            else:
                raise ValueError(f"Unknown processing parameter: {key}")
        return self

    # -- data loading ------------------------------------------------------

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
        """Load seismic data from one or more files.

        Accepts a single path, a list of MiniSEED paths, or a dict
        mapping component letters to paths (``{'N': …, 'E': …, 'Z': …}``).

        Returns ``self`` for chaining.
        """
        from hvsr_pro.core import HVSRDataHandler

        handler = HVSRDataHandler()
        dl = self._config.data_load

        if format != "auto":
            dl.file_format = format
        if degrees_from_north is not None:
            dl.degrees_from_north = degrees_from_north

        if isinstance(file_path, dict):
            dl.load_mode = "multi_component"
            files = [str(file_path.get(c)) for c in ("N", "E", "Z") if c in file_path]
            self._data = handler.load_multi_component(
                files,
                format=dl.file_format,
                degrees_from_north=dl.degrees_from_north,
            )
        elif isinstance(file_path, (list, tuple)):
            if len(file_path) <= 3 and dl.file_format != "auto":
                dl.load_mode = "multi_component"
                self._data = handler.load_multi_component(
                    [str(p) for p in file_path],
                    format=dl.file_format,
                    degrees_from_north=dl.degrees_from_north,
                )
            else:
                dl.load_mode = "multi_type1"
                self._data = handler.load_multi_miniseed_type1([str(p) for p in file_path])
        else:
            p = Path(file_path)
            if not p.exists():
                raise FileNotFoundError(f"File not found: {p}")
            dl.load_mode = "single"
            self._data = handler.load_data(str(p), format=dl.file_format)

        if start_time or end_time:
            tr = self._config.time_range
            tr.enabled = True
            tr.start = start_time
            tr.end = end_time
            tr.timezone_offset = timezone_offset
            rt = tr.to_runtime_dict()
            if rt:
                self._data = handler.slice_by_time(
                    self._data, rt["start"], rt["end"], rt["timezone_offset"]
                )

        return self

    # -- main pipeline -----------------------------------------------------

    def process(self, *, progress_callback: ProgressCallback = None) -> AnalysisResult:
        """Run the full HVSR pipeline.

        This mirrors every step of the GUI's ``ProcessingThread.run()``
        so that changes here automatically apply everywhere.
        """
        if self._data is None:
            raise ValueError("No data loaded. Call load_data() first.")

        cfg = self._config
        p = cfg.processing
        qc_cfg = cfg.qc
        qc_summary = QCSummary()

        def _progress(pct: int, msg: str):
            if progress_callback is not None:
                progress_callback(pct, msg)

        from hvsr_pro.core import HVSRDataHandler
        from hvsr_pro.processing import WindowManager, RejectionEngine, HVSRProcessor
        from hvsr_pro.processing.hvsr import HVSRResult

        data = self._data
        handler = HVSRDataHandler()

        # -- Step 1.2: manual sampling-rate override -----------------------
        if p.manual_sampling_rate:
            _progress(12, f"Overriding sampling rate to {p.manual_sampling_rate:.4f} Hz...")
            data.east.sampling_rate = p.manual_sampling_rate
            data.north.sampling_rate = p.manual_sampling_rate
            data.vertical.sampling_rate = p.manual_sampling_rate

        # -- Step 1.5: time-range slice ------------------------------------
        rt = cfg.time_range.to_runtime_dict()
        if rt is not None:
            _progress(15, "Applying time range filter...")
            data = handler.slice_by_time(data, rt["start"], rt["end"], rt["timezone_offset"])
            _progress(20, f"Sliced to {data.duration / 3600:.2f} hours")

        # -- Step 2: create windows ----------------------------------------
        _progress(30, "Creating windows...")
        wm = WindowManager(window_length=p.window_length, overlap=p.overlap)
        windows = wm.create_windows(data, calculate_quality=True)
        qc_summary.total_windows = windows.n_windows

        # -- Step 3: Phase 1 QC (pre-HVSR) --------------------------------
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
            self._apply_custom_qc_phase1(engine, qc_cfg)
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

        # -- Step 3b: zero-window guard ------------------------------------
        if windows.n_active == 0:
            _progress(65, f"ERROR: No windows passed QC (0/{windows.n_windows})")
            dummy = self._make_dummy_result(p, windows, "No windows passed QC")
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

        # -- Step 4: compute HVSR ------------------------------------------
        _progress(70, "Computing HVSR...")
        processor = HVSRProcessor(
            smoothing_method=p.smoothing_method,
            smoothing_bandwidth=p.smoothing_bandwidth,
            horizontal_method=p.horizontal_method,
            f_min=p.freq_min,
            f_max=p.freq_max,
            n_frequencies=p.n_frequencies,
            parallel=p.use_parallel,
        )
        result = processor.process(windows, detect_peaks_flag=True, save_window_spectra=True)

        # -- Step 5: Cox FDWRA ---------------------------------------------
        apply_fdwra = self._should_apply_fdwra(qc_cfg)
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
                    dummy = self._make_dummy_result(p, windows, "Cox FDWRA rejected all windows")
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

        # -- Step 6: post-HVSR QC ------------------------------------------
        if qc_cfg.enabled and qc_cfg.phase2_enabled and windows.n_active > 0:
            post_algos = self._build_post_hvsr_algos(qc_cfg)
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

    def process_azimuthal(
        self, *, progress_callback: ProgressCallback = None
    ) -> Any:
        """Run azimuthal analysis on already-processed data.

        Returns the ``AzimuthalHVSRResult``.
        """
        if self._windows is None:
            raise ValueError("Run process() before process_azimuthal().")
        from hvsr_pro.processing.azimuthal import AzimuthalHVSRProcessor

        az = AzimuthalHVSRProcessor()
        az_result = az.process(self._windows, progress_callback=progress_callback)
        if self._result is not None:
            self._result.azimuthal_result = az_result
        return az_result

    # -- session save / load -----------------------------------------------

    def save_session(self, session_dir: Union[str, Path]) -> Path:
        """Persist config + results + pickles to *session_dir*."""
        sd = Path(session_dir)
        sd.mkdir(parents=True, exist_ok=True)

        cfg_path = sd / "analysis_config.json"
        self._config.save(cfg_path)

        if self._windows is not None:
            with open(sd / "windows.pkl", "wb") as f:
                pickle.dump(self._windows, f)

        r = self._result
        if r is not None and r.hvsr_result is not None:
            with open(sd / "hvsr_result.pkl", "wb") as f:
                pickle.dump(r.hvsr_result, f)
            if r.azimuthal_result is not None:
                with open(sd / "azimuthal_result.pkl", "wb") as f:
                    pickle.dump(r.azimuthal_result, f)

        if self._data is not None:
            with open(sd / "seismic_data.pkl", "wb") as f:
                pickle.dump(self._data, f)

        # Write a session.json compatible with SessionManager
        from hvsr_pro.config.session import SessionState, FileInfo
        from hvsr_pro.config.session import ProcessingSettings as SPS
        from hvsr_pro.config.session import QCSettings as SQC

        p = self._config.processing
        qc = self._config.qc
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

        if self._windows is not None:
            from hvsr_pro.config.session import WindowState as WS
            for i, w in enumerate(self._windows.windows):
                state.window_states.append(WS(
                    index=i,
                    active=w.state.is_usable if hasattr(w.state, "is_usable") else w.active,
                    rejection_reason=getattr(w, "rejection_reason", None),
                ))

        with open(sd / "session.json", "w", encoding="utf-8") as f:
            json.dump(state.to_dict(), f, indent=2, ensure_ascii=False)

        return sd

    def load_session(self, session_dir: Union[str, Path]) -> "HVSRAnalysis":
        """Restore from a session directory.

        Returns ``self`` for chaining.
        """
        sd = Path(session_dir)

        cfg_path = sd / "analysis_config.json"
        if cfg_path.exists():
            self._config = HVSRAnalysisConfig.load(cfg_path)

        if (sd / "seismic_data.pkl").exists():
            with open(sd / "seismic_data.pkl", "rb") as f:
                self._data = pickle.load(f)

        windows = None
        if (sd / "windows.pkl").exists():
            with open(sd / "windows.pkl", "rb") as f:
                windows = pickle.load(f)
            self._windows = windows

        hvsr_result = None
        if (sd / "hvsr_result.pkl").exists():
            with open(sd / "hvsr_result.pkl", "rb") as f:
                hvsr_result = pickle.load(f)

        az_result = None
        if (sd / "azimuthal_result.pkl").exists():
            with open(sd / "azimuthal_result.pkl", "rb") as f:
                az_result = pickle.load(f)

        if hvsr_result is not None:
            self._result = AnalysisResult(
                hvsr_result=hvsr_result,
                windows=windows,
                data=self._data,
                config=self._config,
                azimuthal_result=az_result,
            )

        return self

    # -- export helpers ----------------------------------------------------

    def save_results(self, output_path: Union[str, Path], fmt: str = "json") -> None:
        """Save HVSR curves to *output_path*.

        *fmt* is ``"json"``, ``"csv"``, or ``"mat"``.
        """
        if self._result is None or self._result.hvsr_result is None:
            raise ValueError("No results to save. Call process() first.")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        r = self._result.hvsr_result
        if fmt == "json":
            payload = {
                "config": self._config.to_dict(),
                "summary": self._result.get_summary(),
                "frequencies": r.frequencies.tolist(),
                "mean_hvsr": r.mean_hvsr.tolist(),
                "median_hvsr": r.median_hvsr.tolist(),
                "std_hvsr": r.std_hvsr.tolist(),
                "percentile_16": r.percentile_16.tolist(),
                "percentile_84": r.percentile_84.tolist(),
                "peaks": [
                    {"frequency": pk.frequency, "amplitude": pk.amplitude}
                    for pk in (r.peaks or [])
                ],
            }
            with open(output_path, "w") as f:
                json.dump(payload, f, indent=2)
        elif fmt == "csv":
            import csv

            with open(output_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["frequency", "mean_hvsr", "median_hvsr",
                                 "std_hvsr", "percentile_16", "percentile_84"])
                for i in range(len(r.frequencies)):
                    writer.writerow([
                        r.frequencies[i], r.mean_hvsr[i], r.median_hvsr[i],
                        r.std_hvsr[i], r.percentile_16[i], r.percentile_84[i],
                    ])
        elif fmt == "mat":
            from scipy.io import savemat

            mat = {
                "frequency": r.frequencies,
                "mean_hvsr": r.mean_hvsr,
                "median_hvsr": r.median_hvsr,
                "std_hvsr": r.std_hvsr,
                "percentile_16": r.percentile_16,
                "percentile_84": r.percentile_84,
                "total_windows": r.total_windows,
                "valid_windows": r.valid_windows,
            }
            pk = r.primary_peak
            if pk:
                mat["peak_frequency"] = pk.frequency
                mat["peak_amplitude"] = pk.amplitude
            savemat(str(output_path), mat)
        else:
            raise ValueError(f"Unknown format: {fmt}")

    def save_plot(
        self,
        output_path: Union[str, Path],
        plot_type: str = "hvsr",
        dpi: int = 150,
    ) -> None:
        """Render and save a plot to *output_path*."""
        if self._result is None or self._result.hvsr_result is None:
            raise ValueError("No results to plot. Call process() first.")

        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from hvsr_pro.visualization import HVSRPlotter

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        plotter = HVSRPlotter()
        r = self._result.hvsr_result

        if plot_type == "hvsr":
            fig = plotter.plot_result(r, show_peaks=True)
        elif plot_type == "windows" and r.window_spectra:
            fig = plotter.plot_with_windows(r)
        elif plot_type == "quality" and self._windows:
            fig = plotter.plot_quality_metrics(self._windows)
        elif plot_type == "statistics":
            fig = plotter.plot_statistics(r)
        elif plot_type == "dashboard" and self._windows:
            fig = plotter.plot_dashboard(r, self._windows)
        else:
            raise ValueError(f"Unknown or unavailable plot type: {plot_type}")

        fig.savefig(output_path, dpi=dpi, bbox_inches="tight")
        plt.close(fig)

    def get_summary(self) -> Dict[str, Any]:
        """Return a JSON-safe summary of the last analysis."""
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

    # -- internals ---------------------------------------------------------

    @staticmethod
    def _make_dummy_result(p, windows, message: str):
        from hvsr_pro.processing.hvsr import HVSRResult

        freqs = np.logspace(np.log10(p.freq_min), np.log10(p.freq_max), p.n_frequencies)
        ones = np.ones_like(freqs)
        return HVSRResult(
            frequencies=freqs,
            mean_hvsr=ones,
            median_hvsr=ones,
            std_hvsr=np.zeros_like(freqs),
            percentile_16=ones * 0.9,
            percentile_84=ones * 1.1,
            window_spectra=[],
            peaks=[],
            total_windows=windows.n_windows,
            valid_windows=0,
            metadata={"qc_failure": True, "message": message},
        )

    @staticmethod
    def _apply_custom_qc_phase1(engine, qc_cfg):
        """Wire pre-HVSR (Phase 1) algorithms from ``QCConfig``."""
        from hvsr_pro.processing.rejection import (
            AmplitudeRejection,
            QualityThresholdRejection,
            STALTARejection,
            FrequencyDomainRejection,
            StatisticalOutlierRejection,
        )

        a = qc_cfg.amplitude
        if a.enabled:
            engine.add_algorithm(AmplitudeRejection(
                max_amplitude=a.max_amplitude,
                min_rms=a.min_rms,
                clipping_threshold=a.clipping_threshold,
            ))

        qt = qc_cfg.quality_threshold
        if qt.enabled:
            engine.add_algorithm(QualityThresholdRejection(threshold=qt.threshold))

        sl = qc_cfg.sta_lta
        if sl.enabled:
            engine.add_algorithm(STALTARejection(
                sta_length=sl.sta_length,
                lta_length=sl.lta_length,
                min_ratio=sl.min_ratio,
                max_ratio=sl.max_ratio,
            ))

        fd = qc_cfg.frequency_domain
        if fd.enabled:
            engine.add_algorithm(FrequencyDomainRejection(spike_threshold=fd.spike_threshold))

        so = qc_cfg.statistical_outlier
        if so.enabled:
            engine.add_algorithm(StatisticalOutlierRejection(
                method=so.method, threshold=so.threshold,
            ))

    @staticmethod
    def _should_apply_fdwra(qc_cfg) -> bool:
        if not qc_cfg.enabled or not qc_cfg.phase2_enabled:
            return False
        if qc_cfg.cox_fdwra.enabled:
            return True
        if qc_cfg.mode == "sesame":
            return True
        return False

    @staticmethod
    def _build_post_hvsr_algos(qc_cfg) -> list:
        from hvsr_pro.processing.rejection import (
            HVSRAmplitudeRejection,
            FlatPeakRejection,
            CurveOutlierRejection,
        )

        algos = []
        ha = qc_cfg.hvsr_amplitude
        if ha.enabled:
            algos.append(HVSRAmplitudeRejection(min_amplitude=ha.min_amplitude))

        fp = qc_cfg.flat_peak
        if fp.enabled:
            algos.append(FlatPeakRejection(flatness_threshold=fp.flatness_threshold))

        co = qc_cfg.curve_outlier
        if co.enabled:
            algos.append(CurveOutlierRejection(
                threshold=co.threshold,
                max_iterations=co.max_iterations,
                metric=co.metric,
            ))

        return algos
