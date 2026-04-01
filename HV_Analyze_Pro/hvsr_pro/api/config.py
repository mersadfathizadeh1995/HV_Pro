"""
HVSR Pro API -- Configuration Types
=====================================

Canonical, JSON-serializable configuration hierarchy for the HVSR
analysis pipeline.  Every consumer (GUI, MCP server, scripts) builds
one ``HVSRAnalysisConfig`` and feeds it to ``HVSRAnalysis.process()``.

Design rules
------------
* Plain Python types only (str, float, int, bool, Optional, List, Dict).
* Every dataclass has ``to_dict()`` / ``from_dict()`` for lossless JSON
  round-trip.
* ``QCConfig.to_qc_settings()`` bridges to the existing
  ``hvsr_pro.processing.rejection.settings.QCSettings`` so that core
  processing code works unchanged.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union


# ---------------------------------------------------------------------------
# Processing
# ---------------------------------------------------------------------------

@dataclass
class ProcessingConfig:
    """Spectral-analysis and windowing parameters."""

    window_length: float = 30.0
    overlap: float = 0.5
    smoothing_method: str = "konno_ohmachi"
    smoothing_bandwidth: float = 40.0
    horizontal_method: str = "geometric_mean"
    freq_min: float = 0.2
    freq_max: float = 20.0
    n_frequencies: int = 100
    manual_sampling_rate: Optional[float] = None
    use_parallel: bool = True
    n_cores: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "window_length": self.window_length,
            "overlap": self.overlap,
            "smoothing_method": self.smoothing_method,
            "smoothing_bandwidth": self.smoothing_bandwidth,
            "horizontal_method": self.horizontal_method,
            "freq_min": self.freq_min,
            "freq_max": self.freq_max,
            "n_frequencies": self.n_frequencies,
            "manual_sampling_rate": self.manual_sampling_rate,
            "use_parallel": self.use_parallel,
            "n_cores": self.n_cores,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProcessingConfig":
        return cls(
            window_length=data.get("window_length", 30.0),
            overlap=data.get("overlap", 0.5),
            smoothing_method=data.get("smoothing_method", "konno_ohmachi"),
            smoothing_bandwidth=data.get("smoothing_bandwidth", 40.0),
            horizontal_method=data.get("horizontal_method", "geometric_mean"),
            freq_min=data.get("freq_min", 0.2),
            freq_max=data.get("freq_max", 20.0),
            n_frequencies=data.get("n_frequencies", 100),
            manual_sampling_rate=data.get("manual_sampling_rate"),
            use_parallel=data.get("use_parallel", False),
            n_cores=data.get("n_cores"),
        )


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

@dataclass
class DataLoadConfig:
    """How to load the seismic file(s)."""

    load_mode: str = "single"
    file_format: str = "auto"
    degrees_from_north: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "load_mode": self.load_mode,
            "file_format": self.file_format,
            "degrees_from_north": self.degrees_from_north,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DataLoadConfig":
        return cls(
            load_mode=data.get("load_mode", "single"),
            file_format=data.get("file_format", "auto"),
            degrees_from_north=data.get("degrees_from_north"),
        )


# ---------------------------------------------------------------------------
# Time-range filter
# ---------------------------------------------------------------------------

@dataclass
class TimeRangeConfig:
    """Optional time-range slicing (ISO-8601 strings for portability)."""

    enabled: bool = False
    start: Optional[str] = None
    end: Optional[str] = None
    timezone_offset: int = 0
    timezone_name: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "start": self.start,
            "end": self.end,
            "timezone_offset": self.timezone_offset,
            "timezone_name": self.timezone_name,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TimeRangeConfig":
        return cls(
            enabled=data.get("enabled", False),
            start=data.get("start"),
            end=data.get("end"),
            timezone_offset=data.get("timezone_offset", 0),
            timezone_name=data.get("timezone_name"),
        )

    def to_runtime_dict(self) -> Optional[Dict[str, Any]]:
        """Convert to the ``time_range`` dict that the pipeline expects.

        Returns ``None`` when the filter is disabled or incomplete.
        """
        if not self.enabled or not self.start or not self.end:
            return None
        from datetime import datetime

        return {
            "enabled": True,
            "start": datetime.fromisoformat(self.start),
            "end": datetime.fromisoformat(self.end),
            "timezone_offset": self.timezone_offset,
            "timezone_name": self.timezone_name or f"UTC{self.timezone_offset:+.0f}",
        }


# ---------------------------------------------------------------------------
# QC -- per-algorithm configs
# ---------------------------------------------------------------------------

@dataclass
class AmplitudeAlgoConfig:
    enabled: bool = True
    max_amplitude: Optional[float] = None
    min_rms: float = 1e-10
    clipping_threshold: float = 0.95

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "params": {
                "max_amplitude": self.max_amplitude,
                "min_rms": self.min_rms,
                "clipping_threshold": self.clipping_threshold,
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AmplitudeAlgoConfig":
        p = data.get("params", {})
        return cls(
            enabled=data.get("enabled", True),
            max_amplitude=p.get("max_amplitude"),
            min_rms=p.get("min_rms", 1e-10),
            clipping_threshold=p.get("clipping_threshold", 0.95),
        )


@dataclass
class QualityThresholdAlgoConfig:
    enabled: bool = False
    threshold: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {"enabled": self.enabled, "params": {"threshold": self.threshold}}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QualityThresholdAlgoConfig":
        p = data.get("params", {})
        return cls(enabled=data.get("enabled", False), threshold=p.get("threshold", 0.5))


@dataclass
class STALTAAlgoConfig:
    enabled: bool = True
    sta_length: float = 1.0
    lta_length: float = 30.0
    min_ratio: float = 0.1
    max_ratio: float = 5.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "params": {
                "sta_length": self.sta_length,
                "lta_length": self.lta_length,
                "min_ratio": self.min_ratio,
                "max_ratio": self.max_ratio,
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "STALTAAlgoConfig":
        p = data.get("params", {})
        return cls(
            enabled=data.get("enabled", True),
            sta_length=p.get("sta_length", 1.0),
            lta_length=p.get("lta_length", 30.0),
            min_ratio=p.get("min_ratio", 0.2),
            max_ratio=p.get("max_ratio", 2.5),
        )


@dataclass
class FrequencyDomainAlgoConfig:
    enabled: bool = False
    spike_threshold: float = 3.0

    def to_dict(self) -> Dict[str, Any]:
        return {"enabled": self.enabled, "params": {"spike_threshold": self.spike_threshold}}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FrequencyDomainAlgoConfig":
        p = data.get("params", {})
        return cls(
            enabled=data.get("enabled", False),
            spike_threshold=p.get("spike_threshold", 3.0),
        )


@dataclass
class StatisticalOutlierAlgoConfig:
    enabled: bool = False
    method: str = "iqr"
    threshold: float = 2.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "params": {"method": self.method, "threshold": self.threshold},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StatisticalOutlierAlgoConfig":
        p = data.get("params", {})
        return cls(
            enabled=data.get("enabled", False),
            method=p.get("method", "iqr"),
            threshold=p.get("threshold", 2.0),
        )


# ---------------------------------------------------------------------------
# Post-HVSR QC algorithms
# ---------------------------------------------------------------------------

@dataclass
class HVSRAmplitudeAlgoConfig:
    enabled: bool = False
    min_amplitude: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {"enabled": self.enabled, "params": {"min_amplitude": self.min_amplitude}}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HVSRAmplitudeAlgoConfig":
        p = data.get("params", {})
        return cls(
            enabled=data.get("enabled", False),
            min_amplitude=p.get("min_amplitude", 1.0),
        )


@dataclass
class FlatPeakAlgoConfig:
    enabled: bool = False
    flatness_threshold: float = 0.15

    def to_dict(self) -> Dict[str, Any]:
        return {"enabled": self.enabled, "params": {"flatness_threshold": self.flatness_threshold}}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FlatPeakAlgoConfig":
        p = data.get("params", {})
        return cls(
            enabled=data.get("enabled", False),
            flatness_threshold=p.get("flatness_threshold", 0.15),
        )


@dataclass
class CurveOutlierAlgoConfig:
    enabled: bool = True
    threshold: float = 3.0
    max_iterations: int = 5
    metric: str = "mean"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "params": {
                "threshold": self.threshold,
                "max_iterations": self.max_iterations,
                "metric": self.metric,
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CurveOutlierAlgoConfig":
        p = data.get("params", {})
        return cls(
            enabled=data.get("enabled", True),
            threshold=p.get("threshold", 3.0),
            max_iterations=p.get("max_iterations", 5),
            metric=p.get("metric", "mean"),
        )


# ---------------------------------------------------------------------------
# Cox FDWRA
# ---------------------------------------------------------------------------

@dataclass
class CoxFDWRAConfig:
    """Cox et al. (2020) peak-frequency consistency rejection."""

    enabled: bool = True
    n: float = 2.0
    max_iterations: int = 50
    min_iterations: int = 1
    distribution: str = "lognormal"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "n": self.n,
            "max_iterations": self.max_iterations,
            "min_iterations": self.min_iterations,
            "distribution": self.distribution,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CoxFDWRAConfig":
        return cls(
            enabled=data.get("enabled", True),
            n=data.get("n", 2.0),
            max_iterations=data.get("max_iterations", 50),
            min_iterations=data.get("min_iterations", 1),
            distribution=data.get("distribution", "lognormal"),
        )


# ---------------------------------------------------------------------------
# Composite QC config
# ---------------------------------------------------------------------------

@dataclass
class QCConfig:
    """Full quality-control configuration.

    Mirrors ``hvsr_pro.processing.rejection.settings.QCSettings`` but uses
    typed sub-configs instead of generic ``params`` dicts.
    """

    enabled: bool = True
    mode: str = "sesame"
    phase1_enabled: bool = True
    phase2_enabled: bool = True

    # Pre-HVSR (Phase 1)
    amplitude: AmplitudeAlgoConfig = field(default_factory=AmplitudeAlgoConfig)
    quality_threshold: QualityThresholdAlgoConfig = field(default_factory=QualityThresholdAlgoConfig)
    sta_lta: STALTAAlgoConfig = field(default_factory=STALTAAlgoConfig)
    frequency_domain: FrequencyDomainAlgoConfig = field(default_factory=FrequencyDomainAlgoConfig)
    statistical_outlier: StatisticalOutlierAlgoConfig = field(default_factory=StatisticalOutlierAlgoConfig)

    # Post-HVSR (Phase 2)
    hvsr_amplitude: HVSRAmplitudeAlgoConfig = field(default_factory=HVSRAmplitudeAlgoConfig)
    flat_peak: FlatPeakAlgoConfig = field(default_factory=FlatPeakAlgoConfig)
    curve_outlier: CurveOutlierAlgoConfig = field(default_factory=CurveOutlierAlgoConfig)

    # Cox FDWRA
    cox_fdwra: CoxFDWRAConfig = field(default_factory=CoxFDWRAConfig)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "mode": self.mode,
            "phase1_enabled": self.phase1_enabled,
            "phase2_enabled": self.phase2_enabled,
            "algorithms": {
                "amplitude": self.amplitude.to_dict(),
                "quality_threshold": self.quality_threshold.to_dict(),
                "sta_lta": self.sta_lta.to_dict(),
                "frequency_domain": self.frequency_domain.to_dict(),
                "statistical_outlier": self.statistical_outlier.to_dict(),
                "hvsr_amplitude": self.hvsr_amplitude.to_dict(),
                "flat_peak": self.flat_peak.to_dict(),
                "curve_outlier": self.curve_outlier.to_dict(),
            },
            "cox_fdwra": self.cox_fdwra.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QCConfig":
        algos = data.get("algorithms", {})
        cfg = cls(
            enabled=data.get("enabled", True),
            mode=data.get("mode", "sesame"),
            phase1_enabled=data.get("phase1_enabled", True),
            phase2_enabled=data.get("phase2_enabled", True),
        )
        if "amplitude" in algos:
            cfg.amplitude = AmplitudeAlgoConfig.from_dict(algos["amplitude"])
        if "quality_threshold" in algos:
            cfg.quality_threshold = QualityThresholdAlgoConfig.from_dict(algos["quality_threshold"])
        if "sta_lta" in algos:
            cfg.sta_lta = STALTAAlgoConfig.from_dict(algos["sta_lta"])
        if "frequency_domain" in algos:
            cfg.frequency_domain = FrequencyDomainAlgoConfig.from_dict(algos["frequency_domain"])
        if "statistical_outlier" in algos:
            cfg.statistical_outlier = StatisticalOutlierAlgoConfig.from_dict(algos["statistical_outlier"])
        if "hvsr_amplitude" in algos:
            cfg.hvsr_amplitude = HVSRAmplitudeAlgoConfig.from_dict(algos["hvsr_amplitude"])
        if "flat_peak" in algos:
            cfg.flat_peak = FlatPeakAlgoConfig.from_dict(algos["flat_peak"])
        if "curve_outlier" in algos:
            cfg.curve_outlier = CurveOutlierAlgoConfig.from_dict(algos["curve_outlier"])
        if "cox_fdwra" in data:
            cfg.cox_fdwra = CoxFDWRAConfig.from_dict(data["cox_fdwra"])
        return cfg

    # ------------------------------------------------------------------
    # Bridge to core rejection settings
    # ------------------------------------------------------------------

    def to_qc_settings(self):
        """Convert to ``hvsr_pro.processing.rejection.settings.QCSettings``.

        This allows the core ``RejectionEngine`` to work unchanged.
        """
        from hvsr_pro.processing.rejection.settings import (
            QCSettings,
            AmplitudeSettings,
            QualityThresholdSettings,
            STALTASettings,
            FrequencyDomainSettings,
            StatisticalOutlierSettings,
            HVSRAmplitudeSettings,
            FlatPeakSettings,
            CurveOutlierSettings,
            CoxFDWRASettings,
        )

        qs = QCSettings(
            enabled=self.enabled,
            mode=self.mode,
            preset=self.mode if self.mode == "sesame" else "custom",
            phase1_enabled=self.phase1_enabled,
            phase2_enabled=self.phase2_enabled,
        )

        qs.amplitude = AmplitudeSettings(
            enabled=self.amplitude.enabled,
            params={
                "max_amplitude": self.amplitude.max_amplitude,
                "min_rms": self.amplitude.min_rms,
                "clipping_threshold": self.amplitude.clipping_threshold,
            },
        )
        qs.quality_threshold = QualityThresholdSettings(
            enabled=self.quality_threshold.enabled,
            params={"threshold": self.quality_threshold.threshold},
        )
        qs.sta_lta = STALTASettings(
            enabled=self.sta_lta.enabled,
            params={
                "sta_length": self.sta_lta.sta_length,
                "lta_length": self.sta_lta.lta_length,
                "min_ratio": self.sta_lta.min_ratio,
                "max_ratio": self.sta_lta.max_ratio,
            },
        )
        qs.frequency_domain = FrequencyDomainSettings(
            enabled=self.frequency_domain.enabled,
            params={"spike_threshold": self.frequency_domain.spike_threshold},
        )
        qs.statistical_outlier = StatisticalOutlierSettings(
            enabled=self.statistical_outlier.enabled,
            params={
                "method": self.statistical_outlier.method,
                "threshold": self.statistical_outlier.threshold,
            },
        )
        qs.hvsr_amplitude = HVSRAmplitudeSettings(
            enabled=self.hvsr_amplitude.enabled,
            params={"min_amplitude": self.hvsr_amplitude.min_amplitude},
        )
        qs.flat_peak = FlatPeakSettings(
            enabled=self.flat_peak.enabled,
            params={"flatness_threshold": self.flat_peak.flatness_threshold},
        )
        qs.curve_outlier = CurveOutlierSettings(
            enabled=self.curve_outlier.enabled,
            params={
                "threshold": self.curve_outlier.threshold,
                "max_iterations": self.curve_outlier.max_iterations,
                "metric": self.curve_outlier.metric,
            },
        )
        qs.cox_fdwra = CoxFDWRASettings(
            enabled=self.cox_fdwra.enabled,
            n=self.cox_fdwra.n,
            max_iterations=self.cox_fdwra.max_iterations,
            min_iterations=self.cox_fdwra.min_iterations,
            distribution_fn=self.cox_fdwra.distribution,
            distribution_mc=self.cox_fdwra.distribution,
        )
        return qs

    @classmethod
    def from_qc_settings(cls, qs) -> "QCConfig":
        """Create from an existing ``QCSettings`` instance."""
        cfg = cls(
            enabled=qs.enabled,
            mode=qs.mode,
            phase1_enabled=qs.phase1_enabled,
            phase2_enabled=qs.phase2_enabled,
        )
        cfg.amplitude = AmplitudeAlgoConfig(
            enabled=qs.amplitude.enabled,
            max_amplitude=qs.amplitude.params.get("max_amplitude"),
            min_rms=qs.amplitude.params.get("min_rms", 1e-10),
            clipping_threshold=qs.amplitude.params.get("clipping_threshold", 0.95),
        )
        cfg.quality_threshold = QualityThresholdAlgoConfig(
            enabled=qs.quality_threshold.enabled,
            threshold=qs.quality_threshold.params.get("threshold", 0.5),
        )
        cfg.sta_lta = STALTAAlgoConfig(
            enabled=qs.sta_lta.enabled,
            sta_length=qs.sta_lta.params.get("sta_length", 1.0),
            lta_length=qs.sta_lta.params.get("lta_length", 30.0),
            min_ratio=qs.sta_lta.params.get("min_ratio", 0.2),
            max_ratio=qs.sta_lta.params.get("max_ratio", 2.5),
        )
        cfg.frequency_domain = FrequencyDomainAlgoConfig(
            enabled=qs.frequency_domain.enabled,
            spike_threshold=qs.frequency_domain.params.get("spike_threshold", 3.0),
        )
        cfg.statistical_outlier = StatisticalOutlierAlgoConfig(
            enabled=qs.statistical_outlier.enabled,
            method=qs.statistical_outlier.params.get("method", "iqr"),
            threshold=qs.statistical_outlier.params.get("threshold", 2.0),
        )
        cfg.hvsr_amplitude = HVSRAmplitudeAlgoConfig(
            enabled=qs.hvsr_amplitude.enabled,
            min_amplitude=qs.hvsr_amplitude.params.get("min_amplitude", 1.0),
        )
        cfg.flat_peak = FlatPeakAlgoConfig(
            enabled=qs.flat_peak.enabled,
            flatness_threshold=qs.flat_peak.params.get("flatness_threshold", 0.15),
        )
        cfg.curve_outlier = CurveOutlierAlgoConfig(
            enabled=qs.curve_outlier.enabled,
            threshold=qs.curve_outlier.params.get("threshold", 3.0),
            max_iterations=qs.curve_outlier.params.get("max_iterations", 5),
            metric=qs.curve_outlier.params.get("metric", "mean"),
        )
        cfg.cox_fdwra = CoxFDWRAConfig(
            enabled=qs.cox_fdwra.enabled,
            n=qs.cox_fdwra.n,
            max_iterations=qs.cox_fdwra.max_iterations,
            min_iterations=qs.cox_fdwra.min_iterations,
            distribution=qs.cox_fdwra.distribution_fn,
        )
        return cfg

    def to_custom_qc_dict(self) -> Dict[str, Any]:
        """Build the ``custom_qc_settings`` dict the old worker expects.

        This is the ``{'enabled': …, 'algorithms': {…}}`` shape consumed by
        ``ProcessingThread._apply_custom_qc()`` and the post-HVSR block.
        """
        return {
            "enabled": self.enabled,
            "algorithms": {
                "amplitude": self.amplitude.to_dict(),
                "quality_threshold": self.quality_threshold.to_dict(),
                "sta_lta": self.sta_lta.to_dict(),
                "frequency_domain": self.frequency_domain.to_dict(),
                "statistical_outlier": self.statistical_outlier.to_dict(),
                "hvsr_amplitude": self.hvsr_amplitude.to_dict(),
                "flat_peak": self.flat_peak.to_dict(),
                "curve_outlier": self.curve_outlier.to_dict(),
            },
        }


# ---------------------------------------------------------------------------
# Top-level config
# ---------------------------------------------------------------------------

@dataclass
class HVSRAnalysisConfig:
    """Complete configuration for a single HVSR analysis run.

    Compose one of these and pass it to ``HVSRAnalysis(config).process()``.
    """

    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    data_load: DataLoadConfig = field(default_factory=DataLoadConfig)
    time_range: TimeRangeConfig = field(default_factory=TimeRangeConfig)
    qc: QCConfig = field(default_factory=QCConfig)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "processing": self.processing.to_dict(),
            "data_load": self.data_load.to_dict(),
            "time_range": self.time_range.to_dict(),
            "qc": self.qc.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HVSRAnalysisConfig":
        return cls(
            processing=ProcessingConfig.from_dict(data.get("processing", {})),
            data_load=DataLoadConfig.from_dict(data.get("data_load", {})),
            time_range=TimeRangeConfig.from_dict(data.get("time_range", {})),
            qc=QCConfig.from_dict(data.get("qc", {})),
        )

    def save(self, path: Union[str, Path]) -> None:
        """Persist to a JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: Union[str, Path]) -> "HVSRAnalysisConfig":
        """Restore from a JSON file."""
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return cls.from_dict(data)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> List[str]:
        """Return a list of human-readable error strings (empty == valid)."""
        errors: List[str] = []

        p = self.processing

        if p.window_length < 1.0 or p.window_length > 600.0:
            errors.append(f"window_length must be 1-600 s, got {p.window_length}")
        if p.overlap < 0.0 or p.overlap >= 1.0:
            errors.append(f"overlap must be [0, 1), got {p.overlap}")

        _valid_smoothing = {
            "konno_ohmachi", "parzen", "savitzky_golay",
            "linear_rectangular", "log_rectangular",
            "linear_triangular", "log_triangular", "none",
        }
        if p.smoothing_method not in _valid_smoothing:
            errors.append(
                f"smoothing_method '{p.smoothing_method}' not in {sorted(_valid_smoothing)}"
            )

        _valid_hz = {
            "geometric_mean", "arithmetic_mean", "quadratic", "maximum",
        }
        if p.horizontal_method not in _valid_hz:
            errors.append(
                f"horizontal_method '{p.horizontal_method}' not in {sorted(_valid_hz)}"
            )

        if p.freq_min <= 0:
            errors.append("freq_min must be positive")
        if p.freq_max <= 0:
            errors.append("freq_max must be positive")
        if p.freq_min >= p.freq_max:
            errors.append("freq_min must be less than freq_max")
        if p.n_frequencies < 10:
            errors.append("n_frequencies must be >= 10")

        dl = self.data_load
        _valid_modes = {"single", "multi_type1", "multi_type2", "multi_component"}
        if dl.load_mode not in _valid_modes:
            errors.append(f"load_mode '{dl.load_mode}' not in {sorted(_valid_modes)}")

        qc = self.qc
        _valid_qc_modes = {"sesame", "custom"}
        if qc.mode not in _valid_qc_modes:
            errors.append(f"qc.mode '{qc.mode}' not in {sorted(_valid_qc_modes)}")

        return errors

    # ------------------------------------------------------------------
    # Convenience factory
    # ------------------------------------------------------------------

    @classmethod
    def sesame_default(cls) -> "HVSRAnalysisConfig":
        """Factory for the standard SESAME preset."""
        return cls()

    @classmethod
    def minimal(cls) -> "HVSRAnalysisConfig":
        """Factory with QC disabled (useful for quick previews)."""
        cfg = cls()
        cfg.qc.enabled = False
        return cfg
