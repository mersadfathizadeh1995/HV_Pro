"""
Batch Processing API — BatchAnalysis Facade
============================================

Main entry point for headless batch HVSR analysis.

Ties together all API modules into a single coherent interface:
    - Station & sensor management (station_ops)
    - Time window configuration
    - Data preparation (data_engine)
    - HVSR processing (hvsr_engine)
    - Combined analysis & peak statistics (aggregate)
    - Export & figure generation (export, figures)

Usage::

    from hvsr_pro.packages.batch_processing.api import BatchAnalysis

    batch = BatchAnalysis()
    batch.import_stations_from_folder(r"D:\\Data\\Site1")
    batch.add_time_window("Morning", "2026-04-01T10:00:00", "2026-04-01T11:00:00",
                          timezone="CDT")
    batch.set_processing(window_length=120, freq_min=0.2, freq_max=50.0)
    batch.set_output(output_dir=r"D:\\Results\\Site1")

    batch.prepare_data()
    batch.process_hvsr()
    batch.run_analysis()
    batch.export_results()
    batch.generate_report()
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict
from typing import Any, Callable, Dict, List, Optional

from .config import (
    BatchConfig,
    ExecutionSettings,
    OutputSettings,
    PeakSettings,
    ProcessingSettings,
    QCSettings,
    SensorDef,
    StationDef,
    TimeConfig,
    TimeWindowDef,
)
from .data_engine import DataResult, prepare_station_data
from .hvsr_engine import StationHVSRResult, process_batch_hvsr, process_station_hvsr

from ..processing.automatic_workflow import (
    AutomaticWorkflowResult,
    PeakStatistics,
    StationResult,
)

logger = logging.getLogger(__name__)


class BatchAnalysis:
    """
    Main facade for headless batch HVSR analysis.

    Manages the full lifecycle: configuration → data preparation →
    HVSR processing → aggregation → export.
    """

    def __init__(self, config: Optional[BatchConfig] = None):
        self._config = config or BatchConfig()
        self._data_results: List[DataResult] = []
        self._hvsr_results: List[StationHVSRResult] = []
        self._station_results: List[StationResult] = []
        self._workflow_result: Optional[AutomaticWorkflowResult] = None

    # ────────────────────────────────────────────────────────────────
    # Configuration
    # ────────────────────────────────────────────────────────────────

    @property
    def config(self) -> BatchConfig:
        """Current batch configuration."""
        return self._config

    def get_config(self) -> dict:
        """Return configuration as a dict."""
        return self._config.to_dict()

    def configure(self, **kwargs):
        """
        Set top-level config fields.

        Accepted kwargs: site_name, output_dir.
        """
        if "site_name" in kwargs:
            self._config.site_name = kwargs["site_name"]
        if "output_dir" in kwargs:
            self._config.output_dir = kwargs["output_dir"]

    def set_processing(self, **kwargs):
        """
        Update processing settings.

        Accepted kwargs: window_length, overlap, freq_min, freq_max,
        n_frequencies, smoothing_method, smoothing_bandwidth,
        horizontal_method, taper, detrend, statistics_method, std_ddof.
        """
        p = self._config.processing
        for key, val in kwargs.items():
            if hasattr(p, key):
                setattr(p, key, val)
            else:
                logger.warning("Unknown processing param: %s", key)

    def set_qc(self, **kwargs):
        """
        Update QC settings.

        Accepted kwargs: stalta_enabled, amplitude_enabled,
        statistical_enabled, fdwra_enabled, hvsr_amplitude_enabled,
        flat_peak_enabled, curve_outlier_enabled, and sub-params
        prefixed by algorithm name (e.g. stalta_sta_length).
        """
        qc = self._config.qc
        for key, val in kwargs.items():
            if hasattr(qc, key):
                setattr(qc, key, val)
            else:
                # Try sub-configs: stalta_*, amplitude_*, etc.
                for prefix in ("stalta", "amplitude", "statistical",
                               "fdwra", "hvsr_amplitude", "flat_peak",
                               "curve_outlier"):
                    if key.startswith(prefix + "_"):
                        sub_key = key[len(prefix) + 1:]
                        sub_cfg = getattr(qc, f"{prefix}_params", None)
                        if sub_cfg and hasattr(sub_cfg, sub_key):
                            setattr(sub_cfg, sub_key, val)
                            break
                else:
                    logger.warning("Unknown QC param: %s", key)

    def set_peaks(self, **kwargs):
        """
        Update peak detection settings.

        Accepted kwargs: auto_mode, peak_basis, min_prominence,
        min_amplitude, n_peaks, freq_tolerance.
        """
        pk = self._config.peaks
        for key, val in kwargs.items():
            if hasattr(pk, key):
                setattr(pk, key, val)
            else:
                logger.warning("Unknown peak param: %s", key)

    def set_output(self, **kwargs):
        """
        Update output settings.

        Accepted kwargs: save_json, save_csv, save_mat, save_png,
        save_pdf, export_excel, figure_dpi, output_dir, and any
        OutputSettings field.
        """
        out = self._config.output
        for key, val in kwargs.items():
            if key == "output_dir":
                self._config.output_dir = val
            elif hasattr(out, key):
                setattr(out, key, val)
            else:
                logger.warning("Unknown output param: %s", key)

    def set_execution(self, **kwargs):
        """
        Update execution settings.

        Accepted kwargs: max_parallel, start_skip_minutes,
        process_length_minutes, full_duration.
        """
        ex = self._config.execution
        for key, val in kwargs.items():
            if hasattr(ex, key):
                setattr(ex, key, val)
            else:
                logger.warning("Unknown execution param: %s", key)

    # ────────────────────────────────────────────────────────────────
    # Station Management
    # ────────────────────────────────────────────────────────────────

    def add_station(
        self,
        station_num: int,
        files: List[str],
        sensor_id: Optional[str] = None,
        name: Optional[str] = None,
    ):
        """Add a station with files."""
        sd = StationDef(
            station_num=station_num,
            station_name=name or f"Station_{station_num:02d}",
            files=list(files),
            sensor_id=sensor_id or "",
            sensor_name="",
        )
        self._config.stations.append(sd)

    def import_stations_from_folder(
        self,
        folder: str,
        extensions: Optional[List[str]] = None,
    ):
        """Import stations by auto-detecting files in a folder."""
        from .station_ops import import_stations_from_folder
        stations = import_stations_from_folder(folder, extensions)
        self._config.stations.extend(stations)
        logger.info("Imported %d stations from %s", len(stations), folder)

    def import_stations_from_csv(self, csv_path: str):
        """Import stations from a CSV file."""
        from .station_ops import import_stations_from_csv
        stations = import_stations_from_csv(csv_path)
        self._config.stations.extend(stations)
        logger.info("Imported %d stations from %s", len(stations), csv_path)

    def clear_stations(self):
        """Remove all stations."""
        self._config.stations.clear()

    def get_stations(self) -> List[StationDef]:
        """Return current station list."""
        return list(self._config.stations)

    # ────────────────────────────────────────────────────────────────
    # Sensor Management
    # ────────────────────────────────────────────────────────────────

    def setup_sensors(
        self,
        sensors: Optional[List[SensorDef]] = None,
        auto_detect_from: Optional[List[str]] = None,
    ):
        """
        Configure sensors.

        Provide sensors explicitly, or auto-detect from filenames.
        """
        from .station_ops import auto_detect_sensors, create_default_sensors

        if sensors:
            self._config.sensors = list(sensors)
        elif auto_detect_from:
            self._config.sensors = auto_detect_sensors(auto_detect_from)
        else:
            self._config.sensors = create_default_sensors()

    def route_files_via_sensors(
        self,
        files: List[str],
        sensor_station_map: Dict[str, List[int]],
    ):
        """Route files to stations via sensor patterns."""
        from .station_ops import route_files_via_sensors

        routing = route_files_via_sensors(
            files, self._config.sensors, sensor_station_map,
        )
        # Merge into existing stations or create new ones
        existing = {s.station_num: s for s in self._config.stations}
        for stn_num, stn_files in routing.items():
            if stn_num in existing:
                existing[stn_num].files.extend(stn_files)
            else:
                sd = StationDef(
                    station_num=stn_num,
                    station_name=f"Station_{stn_num:02d}",
                    files=stn_files,
                )
                self._config.stations.append(sd)

    # ────────────────────────────────────────────────────────────────
    # Time Windows
    # ────────────────────────────────────────────────────────────────

    def add_time_window(
        self,
        name: str,
        start: str,
        end: str,
        timezone: str = "UTC",
        stations: Optional[List[int]] = None,
    ):
        """
        Add a time window.

        Parameters
        ----------
        name : str
            Window name (e.g. "Morning", "Window_1").
        start, end : str
            ISO 8601 timestamps in local time.
        timezone : str
            "UTC", "CST", or "CDT".
        stations : list[int], optional
            Station numbers this window applies to.
        """
        from .station_ops import make_time_window
        tw = make_time_window(name, start, end, timezone)
        tw.assigned_stations = stations or []
        self._config.time_config.windows.append(tw)
        self._config.time_config.timezone = timezone

        if stations:
            self._config.time_config.station_assignments[name] = stations

    def import_time_windows_csv(self, csv_path: str):
        """Import time windows from a CSV file."""
        from .station_ops import import_time_windows_from_csv
        windows = import_time_windows_from_csv(csv_path)
        self._config.time_config.windows.extend(windows)
        logger.info("Imported %d time windows from %s", len(windows), csv_path)

    def set_timezone(self, timezone: str):
        """Set timezone (UTC, CST, CDT)."""
        self._config.time_config.timezone = timezone

    def clear_time_windows(self):
        """Remove all time windows."""
        self._config.time_config.windows.clear()
        self._config.time_config.station_assignments.clear()

    def get_time_windows(self) -> List[TimeWindowDef]:
        """Return current time windows."""
        return list(self._config.time_config.windows)

    # ────────────────────────────────────────────────────────────────
    # Phase 1: Data Preparation
    # ────────────────────────────────────────────────────────────────

    def prepare_data(
        self,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> List[DataResult]:
        """
        Run Phase 1: convert raw seismic files to ArrayData.mat.

        Returns list of DataResult (one per station × window).
        """
        output_dir = self._config.output_dir
        if not output_dir:
            raise ValueError("output_dir not set in config")

        self._data_results = prepare_station_data(
            stations=self._config.stations,
            time_windows=self._config.time_config.windows,
            output_dir=output_dir,
            station_assignments=self._config.time_config.station_assignments,
            progress_callback=progress_callback,
        )

        n_ok = sum(1 for d in self._data_results if d.success)
        logger.info(
            "Data preparation: %d/%d successful",
            n_ok, len(self._data_results),
        )
        return self._data_results

    # ────────────────────────────────────────────────────────────────
    # Phase 2: HVSR Processing
    # ────────────────────────────────────────────────────────────────

    def process_hvsr(
        self,
        parallel: bool = False,
        n_workers: Optional[int] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> List[StationHVSRResult]:
        """
        Run Phase 2: process HVSR for all prepared stations.

        Parameters
        ----------
        parallel : bool
            Use parallel processing.
        n_workers : int, optional
            Max workers (default: config.execution.max_parallel).
        progress_callback : callable(int, str), optional
        """
        if not self._data_results:
            raise RuntimeError("No data results — call prepare_data() first")

        self._hvsr_results = process_batch_hvsr(
            data_results=self._data_results,
            config=self._config,
            parallel=parallel,
            n_workers=n_workers or self._config.execution.max_parallel,
            progress_callback=progress_callback,
        )

        n_ok = sum(1 for h in self._hvsr_results if h.success)
        logger.info(
            "HVSR processing: %d/%d successful",
            n_ok, len(self._hvsr_results),
        )
        return self._hvsr_results

    # ────────────────────────────────────────────────────────────────
    # Phase 3: Aggregation & Analysis
    # ────────────────────────────────────────────────────────────────

    def run_analysis(
        self,
        topic_map: Optional[Dict[str, str]] = None,
    ) -> AutomaticWorkflowResult:
        """
        Run combined analysis: median stacking + peak detection.

        Parameters
        ----------
        topic_map : dict[str, str], optional
            station_name → topic mapping for grouping.

        Returns
        -------
        AutomaticWorkflowResult
        """
        from .aggregate import run_automatic_analysis

        if not self._hvsr_results:
            raise RuntimeError("No HVSR results — call process_hvsr() first")

        self._workflow_result = run_automatic_analysis(
            hvsr_results=self._hvsr_results,
            peak_settings=self._config.peaks,
            processing=self._config.processing,
            topic_map=topic_map,
        )

        self._station_results = self._workflow_result.station_results
        return self._workflow_result

    def detect_combined_peaks(
        self,
        min_prominence: Optional[float] = None,
        min_amplitude: Optional[float] = None,
        n_peaks: Optional[int] = None,
    ):
        """Re-detect peaks on the combined median curve."""
        from .aggregate import detect_combined_peaks as _detect

        if self._workflow_result is None:
            raise RuntimeError("No workflow result — call run_analysis() first")

        return _detect(
            self._workflow_result,
            min_prominence=min_prominence or self._config.peaks.min_prominence,
            min_amplitude=min_amplitude or self._config.peaks.min_amplitude,
            n_peaks=n_peaks or self._config.peaks.n_peaks,
        )

    def set_combined_peaks(self, peaks: list):
        """Manually set combined peaks (for interactive selection)."""
        if self._workflow_result is None:
            raise RuntimeError("No workflow result — call run_analysis() first")
        self._workflow_result.combined_peaks = list(peaks)

    def get_peak_statistics(
        self, frequency_tolerance: float = 0.3,
    ) -> List[PeakStatistics]:
        """Compute cross-station peak statistics."""
        from .aggregate import compute_peak_statistics

        if self._workflow_result is None:
            raise RuntimeError("No workflow result — call run_analysis() first")

        return compute_peak_statistics(
            self._workflow_result, frequency_tolerance,
        )

    # ────────────────────────────────────────────────────────────────
    # Results Access
    # ────────────────────────────────────────────────────────────────

    def get_data_results(self) -> List[DataResult]:
        """Return Phase 1 data results."""
        return list(self._data_results)

    def get_hvsr_results(self) -> List[StationHVSRResult]:
        """Return Phase 2 HVSR results."""
        return list(self._hvsr_results)

    def get_station_results(self) -> List[StationResult]:
        """Return converted StationResult objects."""
        return list(self._station_results)

    def get_workflow_result(self) -> Optional[AutomaticWorkflowResult]:
        """Return the full workflow result."""
        return self._workflow_result

    def get_combined_result(self) -> Optional[dict]:
        """Return combined median as a summary dict."""
        if self._workflow_result is None:
            return None
        wf = self._workflow_result
        return {
            "frequencies": wf.combined_frequencies.tolist()
            if wf.combined_frequencies is not None else [],
            "median_hvsr": wf.combined_median.tolist()
            if wf.combined_median is not None else [],
            "n_stations": wf.n_stations,
            "combined_peaks": [
                {"frequency": p.frequency, "amplitude": p.amplitude}
                for p in (wf.combined_peaks or [])
            ],
            "peak_statistics": [
                {
                    "frequency": ps.frequency,
                    "amplitude": ps.amplitude,
                    "station_count": ps.station_count,
                }
                for ps in (wf.peak_statistics or [])
            ],
        }

    def get_results_by_topic(self) -> Dict[str, List[StationResult]]:
        """Group station results by topic."""
        from .aggregate import group_by_topic
        return group_by_topic(self._station_results)

    # ────────────────────────────────────────────────────────────────
    # Export & Reports
    # ────────────────────────────────────────────────────────────────

    def export_results(
        self,
        output_dir: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Export all results (tables, median data, workflow).

        Parameters
        ----------
        output_dir : str, optional
            Override config output_dir.

        Returns
        -------
        dict[str, str]
            Logical name → file path.
        """
        from .export import (
            export_median_data,
            export_results_table_csv,
            export_workflow_result,
        )

        out = output_dir or self._config.output_dir
        if not out:
            raise ValueError("output_dir not set")

        files = {}

        # Results table
        if self._station_results:
            table_dir = os.path.join(out, "table")
            try:
                files["results_table"] = export_results_table_csv(
                    self._station_results, table_dir,
                )
            except Exception as exc:
                logger.error("Results table: %s", exc)

        # Median data
        if self._station_results:
            median_dir = os.path.join(out, "median")
            try:
                median_files = export_median_data(
                    self._station_results, median_dir,
                )
                files.update({f"median_{k}": v for k, v in median_files.items()})
            except Exception as exc:
                logger.error("Median data: %s", exc)

        # Workflow result
        if self._workflow_result:
            try:
                wf_files = export_workflow_result(
                    self._workflow_result, out, self._config.site_name,
                )
                files.update(wf_files)
            except Exception as exc:
                logger.error("Workflow result: %s", exc)

        return files

    def generate_report(
        self,
        output_dir: Optional[str] = None,
        dpi: Optional[int] = None,
    ) -> Dict[str, str]:
        """
        Generate a complete batch report (tables + figures + data).

        Parameters
        ----------
        output_dir : str, optional
        dpi : int, optional

        Returns
        -------
        dict[str, str]
        """
        from .export import generate_batch_report

        out = output_dir or self._config.output_dir
        if not out:
            raise ValueError("output_dir not set")

        if self._workflow_result is None:
            raise RuntimeError("No workflow result — call run_analysis() first")

        return generate_batch_report(
            workflow_result=self._workflow_result,
            output_dir=os.path.join(out, "report"),
            site_name=self._config.site_name,
            dpi=dpi or self._config.output.figure_dpi,
        )

    def generate_station_figures(
        self,
        output_dir: Optional[str] = None,
        figure_types: Optional[List[str]] = None,
        dpi: Optional[int] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> Dict[str, Dict[str, str]]:
        """
        Generate per-station figures for all stations.

        Returns dict: station_name → {figure_type → file_path}.
        """
        from .figures import generate_batch_station_figures

        out = output_dir or self._config.output_dir
        if not out:
            raise ValueError("output_dir not set")

        return generate_batch_station_figures(
            hvsr_results=self._hvsr_results,
            output_dir=os.path.join(out, "figures"),
            figure_types=figure_types,
            dpi=dpi or self._config.output.figure_dpi,
            save_png=self._config.output.save_png,
            save_pdf=self._config.output.save_pdf,
            progress_callback=progress_callback,
        )

    def generate_combined_figures(
        self,
        output_dir: Optional[str] = None,
        figure_types: Optional[List[str]] = None,
        dpi: Optional[int] = None,
    ) -> Dict[str, str]:
        """Generate combined/batch-level figures."""
        from .figures import generate_combined_figures

        out = output_dir or self._config.output_dir
        if not out:
            raise ValueError("output_dir not set")

        if not self._station_results:
            raise RuntimeError("No station results — call run_analysis() first")

        return generate_combined_figures(
            station_results=self._station_results,
            output_dir=os.path.join(out, "combined_figures"),
            figure_types=figure_types,
            dpi=dpi or self._config.output.figure_dpi,
        )

    # ────────────────────────────────────────────────────────────────
    # Full Pipeline
    # ────────────────────────────────────────────────────────────────

    def run_full_pipeline(
        self,
        parallel: bool = False,
        topic_map: Optional[Dict[str, str]] = None,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> AutomaticWorkflowResult:
        """
        Run the complete batch pipeline: data → HVSR → analysis.

        Returns the final workflow result.
        """
        logger.info("Starting full batch pipeline for %d stations",
                     len(self._config.stations))

        self.prepare_data(progress_callback)
        self.process_hvsr(parallel=parallel, progress_callback=progress_callback)
        result = self.run_analysis(topic_map=topic_map)

        logger.info(
            "Pipeline complete: %d stations, %d peaks",
            result.n_stations,
            len(result.combined_peaks),
        )
        return result

    # ────────────────────────────────────────────────────────────────
    # State Management
    # ────────────────────────────────────────────────────────────────

    def save_state(self, path: str):
        """Save configuration to a JSON file."""
        self._config.save(path)
        logger.info("State saved to %s", path)

    def load_state(self, path: str):
        """Load configuration from a JSON file."""
        self._config = BatchConfig.load(path)
        logger.info("State loaded from %s", path)

    def to_dict(self) -> dict:
        """Serialize full state to dict."""
        return {
            "config": self._config.to_dict(),
            "n_data_results": len(self._data_results),
            "n_hvsr_results": len(self._hvsr_results),
            "n_station_results": len(self._station_results),
            "has_workflow_result": self._workflow_result is not None,
        }

    @classmethod
    def from_config(cls, config: BatchConfig) -> "BatchAnalysis":
        """Create a BatchAnalysis from an existing config."""
        return cls(config=config)

    @classmethod
    def from_json(cls, path: str) -> "BatchAnalysis":
        """Create a BatchAnalysis from a saved config JSON."""
        config = BatchConfig.load(path)
        return cls(config=config)

    def __repr__(self) -> str:
        return (
            f"BatchAnalysis("
            f"stations={len(self._config.stations)}, "
            f"windows={len(self._config.time_config.windows)}, "
            f"data_results={len(self._data_results)}, "
            f"hvsr_results={len(self._hvsr_results)})"
        )
