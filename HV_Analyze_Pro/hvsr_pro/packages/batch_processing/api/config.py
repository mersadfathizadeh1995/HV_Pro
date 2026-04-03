"""
Batch Processing API — Configuration Data Model
=================================================

Defines all configuration dataclasses for headless batch HVSR processing.
Every configurable parameter from the GUI dialogs is represented here.

Design:
    - All dataclasses are pure Python (no Qt dependencies).
    - Each has ``to_dict()`` / ``from_dict()`` for JSON serialization.
    - ``BatchConfig`` is the top-level container combining all sub-configs.
    - Default values match the standard API conventions
      (overlap=0.0, freq_max=50.0, n_frequencies=200, statistics=lognormal).
    - Batch-specific defaults (window_length=120, min_prominence=0.5,
      min_amplitude=2.0) differ from single-station analysis.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


# ────────────────────────────────────────────────────────────────────
# Timezone mapping
# ────────────────────────────────────────────────────────────────────

TZ_OFFSETS = {
    "UTC": 0,
    "CST": 6,   # Central Standard Time → UTC+6h
    "CDT": 5,   # Central Daylight Time → UTC+5h
}


# ────────────────────────────────────────────────────────────────────
# Station & Sensor Definitions
# ────────────────────────────────────────────────────────────────────

@dataclass
class StationDef:
    """A single measurement station with associated files."""

    station_num: int              # 1–99
    station_name: str = ""        # e.g. "STN01"
    files: List[str] = field(default_factory=list)
    sensor_id: str = ""           # links to SensorDef.sensor_id
    sensor_name: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.station_name:
            self.station_name = f"STN{self.station_num:02d}"

    def to_dict(self) -> dict:
        return {
            "station_num": self.station_num,
            "station_name": self.station_name,
            "files": list(self.files),
            "sensor_id": self.sensor_id,
            "sensor_name": self.sensor_name,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "StationDef":
        return cls(
            station_num=d["station_num"],
            station_name=d.get("station_name", ""),
            files=d.get("files", []),
            sensor_id=d.get("sensor_id", ""),
            sensor_name=d.get("sensor_name", ""),
            metadata=d.get("metadata", {}),
        )


@dataclass
class SensorDef:
    """A sensor definition with file-matching patterns."""

    sensor_id: str               # e.g. "1", "2", …
    display_name: str = ""       # e.g. "Centaur 0655"
    file_patterns: List[str] = field(default_factory=list)  # regex patterns

    def to_dict(self) -> dict:
        return {
            "sensor_id": self.sensor_id,
            "display_name": self.display_name,
            "file_patterns": list(self.file_patterns),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SensorDef":
        return cls(
            sensor_id=d["sensor_id"],
            display_name=d.get("display_name", ""),
            file_patterns=d.get("file_patterns", []),
        )


# ────────────────────────────────────────────────────────────────────
# Time Windows
# ────────────────────────────────────────────────────────────────────

@dataclass
class TimeWindowDef:
    """A single time window for data extraction."""

    name: str                              # e.g. "Window_1"
    start_utc: str = ""                    # ISO 8601: "2024-01-15T16:30:00"
    end_utc: str = ""                      # ISO 8601: "2024-01-15T18:00:00"
    start_local: str = ""                  # "%Y-%m-%d %H:%M:%S"
    end_local: str = ""                    # "%Y-%m-%d %H:%M:%S"
    assigned_stations: Optional[List[int]] = None  # None = all stations

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "start_utc": self.start_utc,
            "end_utc": self.end_utc,
            "start_local": self.start_local,
            "end_local": self.end_local,
            "assigned_stations": self.assigned_stations,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TimeWindowDef":
        return cls(
            name=d["name"],
            start_utc=d.get("start_utc", ""),
            end_utc=d.get("end_utc", ""),
            start_local=d.get("start_local", ""),
            end_local=d.get("end_local", ""),
            assigned_stations=d.get("assigned_stations"),
        )


@dataclass
class TimeConfig:
    """Time configuration: timezone + windows + station assignment."""

    timezone: str = "UTC"                  # "UTC", "CST", "CDT"
    windows: List[TimeWindowDef] = field(default_factory=list)
    station_assignments: Dict[str, List[int]] = field(default_factory=dict)

    @property
    def timezone_offset(self) -> int:
        """Hours offset from UTC for the configured timezone."""
        return TZ_OFFSETS.get(self.timezone.upper(), 0)

    def to_dict(self) -> dict:
        return {
            "timezone": self.timezone,
            "windows": [w.to_dict() for w in self.windows],
            "station_assignments": dict(self.station_assignments),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TimeConfig":
        return cls(
            timezone=d.get("timezone", "UTC"),
            windows=[TimeWindowDef.from_dict(w) for w in d.get("windows", [])],
            station_assignments=d.get("station_assignments", {}),
        )


# ────────────────────────────────────────────────────────────────────
# Processing Settings
# ────────────────────────────────────────────────────────────────────

@dataclass
class ProcessingSettings:
    """HVSR processing parameters for batch analysis."""

    window_length: float = 120.0     # seconds (batch default: 120)
    overlap: float = 0.0             # 0.0–1.0 fraction
    freq_min: float = 0.2            # Hz
    freq_max: float = 50.0           # Hz
    n_frequencies: int = 200         # log-spaced frequency points
    smoothing_method: str = "konno_ohmachi"  # "konno_ohmachi", "parzen", "none"
    smoothing_bandwidth: float = 40.0
    horizontal_method: str = "geometric_mean"  # "geometric_mean", "quadratic_mean",
                                               # "energy_density", "north", "east"
    taper: str = "tukey"             # "tukey", "hann", "hamming", "blackman", "none"
    detrend: str = "linear"          # "linear", "mean", "none"
    statistics_method: str = "lognormal"  # "lognormal", "numpy"
    std_ddof: int = 1                # 0 or 1

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ProcessingSettings":
        known = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in d.items() if k in known})


# ────────────────────────────────────────────────────────────────────
# Peak Detection Settings
# ────────────────────────────────────────────────────────────────────

@dataclass
class PeakSettings:
    """Peak detection parameters for batch automatic mode."""

    auto_mode: bool = True
    peak_basis: str = "median"       # "median" or "mean"
    min_prominence: float = 0.5      # batch default (more conservative)
    min_amplitude: float = 2.0       # batch default
    n_peaks: int = 3                 # max peaks to detect per station
    freq_tolerance: float = 0.3      # Hz tolerance for cross-station matching

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "PeakSettings":
        known = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in d.items() if k in known})


# ────────────────────────────────────────────────────────────────────
# QC Algorithm Configs
# ────────────────────────────────────────────────────────────────────

@dataclass
class STALTAParams:
    """STA/LTA transient detection parameters."""
    sta_length: float = 1.0       # seconds
    lta_length: float = 30.0      # seconds
    min_ratio: float = 0.2
    max_ratio: float = 2.5

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "STALTAParams":
        return cls(**{k: v for k, v in d.items()
                      if k in cls.__dataclass_fields__})


@dataclass
class AmplitudeParams:
    """Amplitude / clipping check parameters."""
    preset: str = "moderate"          # "strict", "moderate", "lenient"
    max_amplitude: Optional[float] = None
    min_rms: float = 1e-10
    clipping_threshold: float = 0.95
    clipping_max_percent: float = 1.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "AmplitudeParams":
        return cls(**{k: v for k, v in d.items()
                      if k in cls.__dataclass_fields__})


@dataclass
class StatisticalOutlierParams:
    """Statistical outlier detection parameters."""
    method: str = "mad"              # "mad", "zscore", "iqr"
    threshold: float = 3.0
    metric: str = "max_deviation"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "StatisticalOutlierParams":
        return cls(**{k: v for k, v in d.items()
                      if k in cls.__dataclass_fields__})


@dataclass
class FDWRAParams:
    """Frequency-Dependent Window Rejection Algorithm parameters."""
    n: float = 2.0                   # std-dev threshold
    max_iterations: int = 50
    min_iterations: int = 1
    distribution_fn: str = "lognormal"
    distribution_mc: str = "lognormal"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "FDWRAParams":
        return cls(**{k: v for k, v in d.items()
                      if k in cls.__dataclass_fields__})


@dataclass
class HVSRAmplitudeParams:
    """Post-HVSR amplitude check parameters."""
    min_amplitude: float = 1.0
    max_amplitude: float = 15.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "HVSRAmplitudeParams":
        return cls(**{k: v for k, v in d.items()
                      if k in cls.__dataclass_fields__})


@dataclass
class FlatPeakParams:
    """Flat-peak rejection parameters."""
    flatness_threshold: float = 0.15

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "FlatPeakParams":
        return cls(**{k: v for k, v in d.items()
                      if k in cls.__dataclass_fields__})


@dataclass
class CurveOutlierParams:
    """Post-HVSR curve outlier rejection parameters."""
    threshold: float = 3.0
    max_iterations: int = 5
    metric: str = "mean"

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "CurveOutlierParams":
        return cls(**{k: v for k, v in d.items()
                      if k in cls.__dataclass_fields__})


@dataclass
class QCSettings:
    """
    Quality-control configuration for batch processing.

    Enables/disables each QC algorithm and holds its tunable parameters.
    Phase 1 (pre-HVSR): STA/LTA, amplitude, statistical outlier.
    Phase 2 (post-HVSR): FDWRA, HVSR amplitude, flat peak, curve outlier.
    """

    # Phase 1 — pre-HVSR window rejection
    stalta_enabled: bool = True
    stalta: STALTAParams = field(default_factory=STALTAParams)

    amplitude_enabled: bool = True
    amplitude: AmplitudeParams = field(default_factory=AmplitudeParams)

    statistical_enabled: bool = True
    statistical: StatisticalOutlierParams = field(
        default_factory=StatisticalOutlierParams
    )

    # Phase 2 — post-HVSR rejection
    fdwra_enabled: bool = True
    fdwra: FDWRAParams = field(default_factory=FDWRAParams)

    hvsr_amplitude_enabled: bool = False
    hvsr_amplitude: HVSRAmplitudeParams = field(
        default_factory=HVSRAmplitudeParams
    )

    flat_peak_enabled: bool = False
    flat_peak: FlatPeakParams = field(default_factory=FlatPeakParams)

    curve_outlier_enabled: bool = True
    curve_outlier: CurveOutlierParams = field(
        default_factory=CurveOutlierParams
    )

    def to_dict(self) -> dict:
        return {
            "stalta_enabled": self.stalta_enabled,
            "stalta": self.stalta.to_dict(),
            "amplitude_enabled": self.amplitude_enabled,
            "amplitude": self.amplitude.to_dict(),
            "statistical_enabled": self.statistical_enabled,
            "statistical": self.statistical.to_dict(),
            "fdwra_enabled": self.fdwra_enabled,
            "fdwra": self.fdwra.to_dict(),
            "hvsr_amplitude_enabled": self.hvsr_amplitude_enabled,
            "hvsr_amplitude": self.hvsr_amplitude.to_dict(),
            "flat_peak_enabled": self.flat_peak_enabled,
            "flat_peak": self.flat_peak.to_dict(),
            "curve_outlier_enabled": self.curve_outlier_enabled,
            "curve_outlier": self.curve_outlier.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "QCSettings":
        return cls(
            stalta_enabled=d.get("stalta_enabled", True),
            stalta=STALTAParams.from_dict(d.get("stalta", {})),
            amplitude_enabled=d.get("amplitude_enabled", True),
            amplitude=AmplitudeParams.from_dict(d.get("amplitude", {})),
            statistical_enabled=d.get("statistical_enabled", True),
            statistical=StatisticalOutlierParams.from_dict(
                d.get("statistical", {})
            ),
            fdwra_enabled=d.get("fdwra_enabled", True),
            fdwra=FDWRAParams.from_dict(d.get("fdwra", {})),
            hvsr_amplitude_enabled=d.get("hvsr_amplitude_enabled", False),
            hvsr_amplitude=HVSRAmplitudeParams.from_dict(
                d.get("hvsr_amplitude", {})
            ),
            flat_peak_enabled=d.get("flat_peak_enabled", False),
            flat_peak=FlatPeakParams.from_dict(d.get("flat_peak", {})),
            curve_outlier_enabled=d.get("curve_outlier_enabled", True),
            curve_outlier=CurveOutlierParams.from_dict(
                d.get("curve_outlier", {})
            ),
        )

    def to_worker_dict(self) -> dict:
        """
        Convert to the flat dict format expected by the current workers.

        Returns the ``qc_*`` flags and ``qc_params`` sub-dict that
        ``batch_window.py`` passes to ``hvsr_worker.py``.
        """
        return {
            "qc_stalta": self.stalta_enabled,
            "qc_amplitude": self.amplitude_enabled,
            "qc_statistical": self.statistical_enabled,
            "qc_fdwra": self.fdwra_enabled,
            "qc_hvsr_amp": self.hvsr_amplitude_enabled,
            "qc_flat_peak": self.flat_peak_enabled,
            "qc_curve_outlier": self.curve_outlier_enabled,
            "qc_params": {
                "sta_lta": self.stalta.to_dict(),
                "amplitude": self.amplitude.to_dict(),
                "statistical_outlier": self.statistical.to_dict(),
                "fdwra": self.fdwra.to_dict(),
                "hvsr_amplitude": self.hvsr_amplitude.to_dict(),
                "flat_peak": self.flat_peak.to_dict(),
                "curve_outlier": self.curve_outlier.to_dict(),
            },
        }


# ────────────────────────────────────────────────────────────────────
# Output Settings
# ────────────────────────────────────────────────────────────────────

@dataclass
class OutputSettings:
    """Control which output files and figures are generated."""

    # Per-station data files
    save_json: bool = True
    save_csv: bool = True
    save_mat: bool = True

    # Per-station figures
    save_png: bool = True
    save_pdf: bool = False
    figure_dpi: int = 300
    generate_standard_figure: bool = True
    generate_hvsr_pro_figure: bool = True
    generate_statistics_figure: bool = True

    # Combined exports
    export_excel: bool = True
    export_combined_mat: bool = True

    # Font/label config
    peak_font_size: int = 10

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "OutputSettings":
        known = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in d.items() if k in known})


# ────────────────────────────────────────────────────────────────────
# Execution Settings
# ────────────────────────────────────────────────────────────────────

@dataclass
class ExecutionSettings:
    """Control parallelism and data window trimming."""

    max_parallel: int = 4             # number of parallel workers
    start_skip_minutes: float = 0.0   # skip N minutes from start
    process_length_minutes: float = 0.0  # 0 = use full window
    full_duration: bool = True        # ignore time windows, use entire file
    per_window_process_lengths: Dict[str, float] = field(
        default_factory=dict
    )  # window_name → process_length_minutes

    def to_dict(self) -> dict:
        return {
            "max_parallel": self.max_parallel,
            "start_skip_minutes": self.start_skip_minutes,
            "process_length_minutes": self.process_length_minutes,
            "full_duration": self.full_duration,
            "per_window_process_lengths": dict(
                self.per_window_process_lengths
            ),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ExecutionSettings":
        return cls(
            max_parallel=d.get("max_parallel", 4),
            start_skip_minutes=d.get("start_skip_minutes", 0.0),
            process_length_minutes=d.get("process_length_minutes", 0.0),
            full_duration=d.get("full_duration", True),
            per_window_process_lengths=d.get(
                "per_window_process_lengths", {}
            ),
        )


# ────────────────────────────────────────────────────────────────────
# Top-Level Batch Configuration
# ────────────────────────────────────────────────────────────────────

@dataclass
class BatchConfig:
    """
    Complete batch processing configuration.

    Combines station definitions, time windows, processing parameters,
    QC settings, peak detection, output control, and execution options
    into a single serializable object.
    """

    # Station & sensor setup
    stations: List[StationDef] = field(default_factory=list)
    sensors: List[SensorDef] = field(default_factory=list)
    sensor_station_map: Dict[str, int] = field(default_factory=dict)

    # Time
    time_config: TimeConfig = field(default_factory=TimeConfig)

    # Processing
    processing: ProcessingSettings = field(default_factory=ProcessingSettings)

    # Peak detection
    peaks: PeakSettings = field(default_factory=PeakSettings)

    # Quality control
    qc: QCSettings = field(default_factory=QCSettings)

    # Output
    output: OutputSettings = field(default_factory=OutputSettings)

    # Execution
    execution: ExecutionSettings = field(default_factory=ExecutionSettings)

    # Project metadata
    site_name: str = "SITE"
    output_dir: str = ""

    # ── Serialization ──────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "stations": [s.to_dict() for s in self.stations],
            "sensors": [s.to_dict() for s in self.sensors],
            "sensor_station_map": dict(self.sensor_station_map),
            "time_config": self.time_config.to_dict(),
            "processing": self.processing.to_dict(),
            "peaks": self.peaks.to_dict(),
            "qc": self.qc.to_dict(),
            "output": self.output.to_dict(),
            "execution": self.execution.to_dict(),
            "site_name": self.site_name,
            "output_dir": self.output_dir,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "BatchConfig":
        return cls(
            stations=[
                StationDef.from_dict(s) for s in d.get("stations", [])
            ],
            sensors=[
                SensorDef.from_dict(s) for s in d.get("sensors", [])
            ],
            sensor_station_map=d.get("sensor_station_map", {}),
            time_config=TimeConfig.from_dict(d.get("time_config", {})),
            processing=ProcessingSettings.from_dict(
                d.get("processing", {})
            ),
            peaks=PeakSettings.from_dict(d.get("peaks", {})),
            qc=QCSettings.from_dict(d.get("qc", {})),
            output=OutputSettings.from_dict(d.get("output", {})),
            execution=ExecutionSettings.from_dict(d.get("execution", {})),
            site_name=d.get("site_name", "SITE"),
            output_dir=d.get("output_dir", ""),
        )

    def save(self, path: str) -> None:
        """Save configuration to a JSON file."""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, path: str) -> "BatchConfig":
        """Load configuration from a JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            return cls.from_dict(json.load(f))

    # ── Conversion helpers ─────────────────────────────────────────

    def to_worker_settings(self) -> dict:
        """
        Convert to the flat ``hvsr_settings`` dict expected by
        ``batch_window.py`` → ``hvsr_worker.py``.

        This bridges the structured config to the legacy worker format.
        """
        settings = {
            # Processing
            "freq_min": self.processing.freq_min,
            "freq_max": self.processing.freq_max,
            "smoothing_type": self.processing.smoothing_method,
            "smoothing_bw": int(self.processing.smoothing_bandwidth),
            "window_length": int(self.processing.window_length),
            "averaging": _horizontal_method_to_legacy(
                self.processing.horizontal_method
            ),
            "n_frequencies": self.processing.n_frequencies,
            "taper": self.processing.taper,
            "detrend": self.processing.detrend,
            "statistics_method": self.processing.statistics_method,
            "std_ddof": self.processing.std_ddof,
            "overlap": self.processing.overlap,

            # Peak detection
            "auto_mode": self.peaks.auto_mode,
            "peak_basis": self.peaks.peak_basis,
            "min_prominence": self.peaks.min_prominence,
            "min_amplitude": self.peaks.min_amplitude,
            "auto_npeaks": self.peaks.n_peaks,
            "freq_tolerance": self.peaks.freq_tolerance,

            # Output
            "save_png": self.output.save_png,
            "save_pdf": self.output.save_pdf,
            "auto_fig_dpi": self.output.figure_dpi,
            "auto_save_json": self.output.save_json,
            "auto_save_csv": self.output.save_csv,
            "auto_fig_standard": self.output.generate_standard_figure,
            "auto_fig_hvsr_pro": self.output.generate_hvsr_pro_figure,
            "auto_fig_statistics": self.output.generate_statistics_figure,
            "export_excel": self.output.export_excel,
            "export_mat": self.output.export_combined_mat,
            "peak_font": self.output.peak_font_size,

            # Execution
            "max_parallel": self.execution.max_parallel,
            "start_skip": self.execution.start_skip_minutes,
            "process_len": self.execution.process_length_minutes,
            "full_duration": self.execution.full_duration,
            "use_per_array": bool(
                self.execution.per_window_process_lengths
            ),
            "per_array_process_len": dict(
                self.execution.per_window_process_lengths
            ),
        }
        # QC
        settings.update(self.qc.to_worker_dict())
        return settings


# ────────────────────────────────────────────────────────────────────
# Legacy conversion helpers
# ────────────────────────────────────────────────────────────────────

_HORIZONTAL_TO_LEGACY = {
    "geometric_mean": "geo",
    "quadratic_mean": "quad",
    "energy_density": "energy",
    "north": "N",
    "east": "E",
}

_LEGACY_TO_HORIZONTAL = {v: k for k, v in _HORIZONTAL_TO_LEGACY.items()}


def _horizontal_method_to_legacy(method: str) -> str:
    """Convert API horizontal method name to legacy short code."""
    return _HORIZONTAL_TO_LEGACY.get(method, method)


def _legacy_to_horizontal_method(code: str) -> str:
    """Convert legacy short code to API horizontal method name."""
    return _LEGACY_TO_HORIZONTAL.get(code, code)


def batch_config_from_worker_settings(settings: dict) -> BatchConfig:
    """
    Create a ``BatchConfig`` from the legacy flat ``hvsr_settings`` dict.

    Useful for migrating existing GUI state to the API config format.
    """
    processing = ProcessingSettings(
        window_length=float(settings.get("window_length", 120)),
        overlap=float(settings.get("overlap", 0.0)),
        freq_min=float(settings.get("freq_min", 0.2)),
        freq_max=float(settings.get("freq_max", 50.0)),
        n_frequencies=int(settings.get("n_frequencies", 200)),
        smoothing_method=settings.get("smoothing_type", "konno_ohmachi"),
        smoothing_bandwidth=float(settings.get("smoothing_bw", 40)),
        horizontal_method=_legacy_to_horizontal_method(
            settings.get("averaging", "geo")
        ),
        taper=settings.get("taper", "tukey"),
        detrend=settings.get("detrend", "linear"),
        statistics_method=settings.get("statistics_method", "lognormal"),
        std_ddof=int(settings.get("std_ddof", 1)),
    )

    peaks = PeakSettings(
        auto_mode=settings.get("auto_mode", True),
        peak_basis=settings.get("peak_basis", "median"),
        min_prominence=float(settings.get("min_prominence", 0.5)),
        min_amplitude=float(settings.get("min_amplitude", 2.0)),
        n_peaks=int(settings.get("auto_npeaks", 3)),
        freq_tolerance=float(settings.get("freq_tolerance", 0.3)),
    )

    qc_params = settings.get("qc_params", {})
    qc = QCSettings(
        stalta_enabled=settings.get("qc_stalta", True),
        stalta=STALTAParams.from_dict(qc_params.get("sta_lta", {})),
        amplitude_enabled=settings.get("qc_amplitude", True),
        amplitude=AmplitudeParams.from_dict(qc_params.get("amplitude", {})),
        statistical_enabled=settings.get("qc_statistical", True),
        statistical=StatisticalOutlierParams.from_dict(
            qc_params.get("statistical_outlier", {})
        ),
        fdwra_enabled=settings.get("qc_fdwra", True),
        fdwra=FDWRAParams.from_dict(qc_params.get("fdwra", {})),
        hvsr_amplitude_enabled=settings.get("qc_hvsr_amp", False),
        hvsr_amplitude=HVSRAmplitudeParams.from_dict(
            qc_params.get("hvsr_amplitude", {})
        ),
        flat_peak_enabled=settings.get("qc_flat_peak", False),
        flat_peak=FlatPeakParams.from_dict(qc_params.get("flat_peak", {})),
        curve_outlier_enabled=settings.get("qc_curve_outlier", True),
        curve_outlier=CurveOutlierParams.from_dict(
            qc_params.get("curve_outlier", {})
        ),
    )

    output = OutputSettings(
        save_json=settings.get("auto_save_json", True),
        save_csv=settings.get("auto_save_csv", True),
        save_mat=settings.get("export_mat", True),
        save_png=settings.get("save_png", True),
        save_pdf=settings.get("save_pdf", False),
        figure_dpi=int(settings.get("auto_fig_dpi", 300)),
        generate_standard_figure=settings.get("auto_fig_standard", True),
        generate_hvsr_pro_figure=settings.get("auto_fig_hvsr_pro", True),
        generate_statistics_figure=settings.get(
            "auto_fig_statistics", True
        ),
        export_excel=settings.get("export_excel", True),
        export_combined_mat=settings.get("export_mat", True),
        peak_font_size=int(settings.get("peak_font", 10)),
    )

    execution = ExecutionSettings(
        max_parallel=int(settings.get("max_parallel", 4)),
        start_skip_minutes=float(settings.get("start_skip", 0)),
        process_length_minutes=float(settings.get("process_len", 0)),
        full_duration=settings.get("full_duration", True),
        per_window_process_lengths=settings.get(
            "per_array_process_len", {}
        ),
    )

    return BatchConfig(
        processing=processing,
        peaks=peaks,
        qc=qc,
        output=output,
        execution=execution,
    )
