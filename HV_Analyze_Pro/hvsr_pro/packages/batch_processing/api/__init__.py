"""
Batch Processing API
====================

Headless API for batch HVSR analysis. Used by both the GUI and MCP server.

Quick start::

    from hvsr_pro.packages.batch_processing.api import (
        BatchConfig, BatchAnalysis,
    )

    batch = BatchAnalysis()
    batch.import_stations_from_folder(r"C:\\data\\stations")
    batch.add_time_window("W1", "2024-01-15T10:00:00", "2024-01-15T12:00:00")
    batch.set_output(output_dir=r"C:\\output")
    batch.prepare_data()
    batch.process_hvsr()
    result = batch.run_analysis()
    batch.generate_report()
"""

from .config import (
    # Core config
    BatchConfig,
    ProcessingSettings,
    PeakSettings,
    QCSettings,
    OutputSettings,
    ExecutionSettings,
    TimeConfig,
    TimeWindowDef,
    StationDef,
    SensorDef,
    # QC sub-configs
    STALTAParams,
    AmplitudeParams,
    StatisticalOutlierParams,
    FDWRAParams,
    HVSRAmplitudeParams,
    FlatPeakParams,
    CurveOutlierParams,
    # Conversion helpers
    batch_config_from_worker_settings,
    TZ_OFFSETS,
)

from .data_engine import DataResult, prepare_station_data
from .hvsr_engine import StationHVSRResult, process_station_hvsr, process_batch_hvsr
from .aggregate import (
    build_station_results,
    compute_combined_median,
    detect_combined_peaks,
    compute_peak_statistics,
    group_by_topic,
    compute_topic_medians,
    run_automatic_analysis,
)
from .batch_analysis import BatchAnalysis

__all__ = [
    # Facade
    "BatchAnalysis",
    # Config
    "BatchConfig",
    "ProcessingSettings",
    "PeakSettings",
    "QCSettings",
    "OutputSettings",
    "ExecutionSettings",
    "TimeConfig",
    "TimeWindowDef",
    "StationDef",
    "SensorDef",
    # QC params
    "STALTAParams",
    "AmplitudeParams",
    "StatisticalOutlierParams",
    "FDWRAParams",
    "HVSRAmplitudeParams",
    "FlatPeakParams",
    "CurveOutlierParams",
    # Data engine
    "DataResult",
    "prepare_station_data",
    # HVSR engine
    "StationHVSRResult",
    "process_station_hvsr",
    "process_batch_hvsr",
    # Aggregate
    "build_station_results",
    "compute_combined_median",
    "detect_combined_peaks",
    "compute_peak_statistics",
    "group_by_topic",
    "compute_topic_medians",
    "run_automatic_analysis",
    # Helpers
    "batch_config_from_worker_settings",
    "TZ_OFFSETS",
]
