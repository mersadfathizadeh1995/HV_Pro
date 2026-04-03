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
    FigureExportSettings,
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
    filter_results,
    compute_selective_grand_median,
)
from .station_ops import (
    import_stations_from_folder,
    import_stations_from_csv,
    import_time_windows_from_csv,
    export_time_windows_to_csv,
    route_files_via_sensors,
    auto_detect_sensors,
    save_sensor_config,
    load_sensor_config,
    auto_distribute_stations,
    make_time_window,
)
from .batch_analysis import BatchAnalysis

# New API modules (Phase 10)
from .interactive import (
    override_station_peaks,
    pick_peaks_on_median,
    accept_peak_selection,
    recompute_statistics_with_overrides,
)
from .reporting import ReportConfig, generate_full_report
from .validation import (
    validate_batch_config,
    validate_station_files,
    validate_time_windows,
    validate_all,
)

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
    "FigureExportSettings",
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
    "filter_results",
    "compute_selective_grand_median",
    # Station ops
    "import_stations_from_folder",
    "import_stations_from_csv",
    "import_time_windows_from_csv",
    "export_time_windows_to_csv",
    "route_files_via_sensors",
    "auto_detect_sensors",
    "save_sensor_config",
    "load_sensor_config",
    "auto_distribute_stations",
    "make_time_window",
    # Helpers
    "batch_config_from_worker_settings",
    "TZ_OFFSETS",
    # Interactive peak management (Phase 10A)
    "override_station_peaks",
    "pick_peaks_on_median",
    "accept_peak_selection",
    "recompute_statistics_with_overrides",
    # Reporting (Phase 10B)
    "ReportConfig",
    "generate_full_report",
    # Validation (Phase 10D)
    "validate_batch_config",
    "validate_station_files",
    "validate_time_windows",
    "validate_all",
]
