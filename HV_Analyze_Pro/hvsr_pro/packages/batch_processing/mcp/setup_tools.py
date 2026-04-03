"""
MCP tools for station/sensor/time-window management and discovery.

Registered via side-effect import in ``server.py``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .server import mcp, _get_batch


# ── Discovery tools ─────────────────────────────────────────────────


@mcp.tool()
def list_supported_formats() -> list:
    """List seismic file formats accepted for batch processing."""
    return [
        {"id": "miniseed", "extensions": [".miniseed", ".mseed"], "description": "MiniSEED seismic data"},
        {"id": "txt", "extensions": [".txt"], "description": "ASCII 3-column text (E, N, Z)"},
        {"id": "saf", "extensions": [".saf"], "description": "Seismic Analysis Format"},
        {"id": "sac", "extensions": [".sac"], "description": "SAC binary format"},
        {"id": "gcf", "extensions": [".gcf"], "description": "Guralp Compressed Format"},
        {"id": "peer", "extensions": [".peer", ".at2"], "description": "PEER NGA format"},
        {"id": "csv", "extensions": [".csv"], "description": "CSV data"},
    ]


@mcp.tool()
def get_batch_defaults(session_id: str = "default") -> Dict[str, Any]:
    """Return the default BatchConfig as a JSON-serialisable dict.

    Useful for inspecting all available configuration parameters and
    their default values before customising a batch run.
    """
    from ..api.config import BatchConfig

    return BatchConfig().to_dict()


@mcp.tool()
def list_qc_algorithms() -> Dict[str, Any]:
    """List available quality-control algorithms with tuneable parameters and defaults.

    Returns a dict keyed by algorithm name, each containing ``enabled``,
    ``description``, and ``params`` (the default parameter values).
    """
    from ..api.config import QCSettings

    qc = QCSettings()
    return {
        "stalta": {
            "enabled": qc.stalta_enabled,
            "description": "STA/LTA transient detection — rejects windows with transient energy bursts.",
            "params": qc.stalta.to_dict(),
        },
        "amplitude": {
            "enabled": qc.amplitude_enabled,
            "description": "Amplitude / clipping check — rejects clipped or dead-channel windows.",
            "params": qc.amplitude.to_dict(),
        },
        "statistical": {
            "enabled": qc.statistical_enabled,
            "description": "Statistical outlier detection (IQR or z-score) on time-domain windows.",
            "params": qc.statistical.to_dict(),
        },
        "fdwra": {
            "enabled": qc.fdwra_enabled,
            "description": "Cox Frequency-Dependent Window Rejection Algorithm — iteratively removes "
                           "windows whose H/V curves deviate from the median at each frequency.",
            "params": qc.fdwra.to_dict(),
        },
        "hvsr_amplitude": {
            "enabled": qc.hvsr_amplitude_enabled,
            "description": "Post-HVSR amplitude gate — rejects windows below a minimum H/V ratio.",
            "params": qc.hvsr_amplitude.to_dict(),
        },
        "flat_peak": {
            "enabled": qc.flat_peak_enabled,
            "description": "Flat-peak rejection — removes windows whose H/V peak is too flat.",
            "params": qc.flat_peak.to_dict(),
        },
        "curve_outlier": {
            "enabled": qc.curve_outlier_enabled,
            "description": "Post-HVSR curve outlier rejection — iteratively removes H/V curves that "
                           "deviate from the ensemble.",
            "params": qc.curve_outlier.to_dict(),
        },
    }


@mcp.tool()
def list_figure_types() -> Dict[str, Any]:
    """List available figure types for batch export.

    Returns per-station and combined (multi-station) figure categories.
    """
    return {
        "per_station": [
            "hvsr_curve",
            "hvsr_statistics",
            "hvsr_with_windows",
            "quality_metrics",
            "window_timeline",
            "peak_analysis",
            "complete_dashboard",
            "mean_vs_median",
            "quality_histogram",
            "selected_metrics",
            "window_timeseries",
            "window_spectrogram",
            "raw_vs_adjusted",
            "waveform_rejection",
            "pre_post_rejection",
        ],
        "combined": [
            "all_hvsr_overlay",
            "peak_frequency_map",
            "summary_table",
        ],
    }


# ── Station setup tools ─────────────────────────────────────────────


@mcp.tool()
def import_stations_from_folder(
    folder: str,
    recursive: bool = False,
    session_id: str = "default",
) -> Dict[str, Any]:
    """Import stations by scanning a folder for seismic data files.

    Each unique station number found in the file names becomes a station.

    Args:
        folder: Absolute path to the folder containing seismic files.
        recursive: Whether to search subfolders (reserved for future use).
        session_id: Batch session identifier.
    """
    try:
        batch = _get_batch(session_id)
        batch.import_stations_from_folder(folder)
        stations = batch.get_stations()
        return {
            "station_count": len(stations),
            "stations": [s.to_dict() for s in stations],
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def import_stations_from_csv(
    csv_path: str,
    session_id: str = "default",
) -> Dict[str, Any]:
    """Import stations from a CSV file.

    The CSV must contain columns for station number, file paths,
    and optionally sensor ID and station name.

    Args:
        csv_path: Absolute path to the CSV file.
        session_id: Batch session identifier.
    """
    try:
        batch = _get_batch(session_id)
        batch.import_stations_from_csv(csv_path)
        stations = batch.get_stations()
        return {
            "station_count": len(stations),
            "stations": [s.to_dict() for s in stations],
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def add_station(
    station_num: int,
    files: list,
    station_name: str = "",
    sensor_id: str = "",
    session_id: str = "default",
) -> Dict[str, Any]:
    """Add a single station to the batch configuration.

    Args:
        station_num: Unique integer station number.
        files: List of absolute file paths assigned to this station.
        station_name: Optional human-readable station name.
        sensor_id: Optional sensor identifier to associate.
        session_id: Batch session identifier.
    """
    try:
        batch = _get_batch(session_id)
        batch.add_station(
            station_num,
            files,
            sensor_id=sensor_id or None,
            name=station_name or None,
        )
        return {
            "status": "ok",
            "station_num": station_num,
            "file_count": len(files),
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def setup_sensors(
    folder: Optional[str] = None,
    sensor_config_path: Optional[str] = None,
    session_id: str = "default",
) -> Dict[str, Any]:
    """Configure sensors for the batch session.

    Provide **either** a data folder (auto-detect sensors from file
    names) or a JSON config path (explicit definitions).  If both are
    given, the JSON config takes precedence.

    Args:
        folder: Absolute path to a folder whose filenames contain
            sensor serial patterns (e.g. Centaur ``centaur-3_NNNN_``).
        sensor_config_path: Absolute path to a JSON file with sensor
            definitions.
        session_id: Batch session identifier.
    """
    try:
        if sensor_config_path:
            from ..api.station_ops import load_sensor_config

            sensors = load_sensor_config(sensor_config_path)
        elif folder:
            import os
            from ..api.station_ops import auto_detect_sensors

            filenames = os.listdir(folder)
            sensors = auto_detect_sensors(filenames)
        else:
            return {"error": "Provide either 'folder' or 'sensor_config_path'."}

        batch = _get_batch(session_id)
        batch._config.sensors = sensors
        return {
            "sensor_count": len(sensors),
            "sensors": [s.to_dict() for s in sensors],
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_stations(session_id: str = "default") -> Dict[str, Any]:
    """Return all stations currently configured in the batch session.

    Each station includes its number, name, file list, and sensor ID.
    """
    try:
        batch = _get_batch(session_id)
        stations = batch.get_stations()
        return {
            "station_count": len(stations),
            "stations": [s.to_dict() for s in stations],
        }
    except Exception as e:
        return {"error": str(e)}


# ── Time-window tools ────────────────────────────────────────────────


@mcp.tool()
def add_time_window(
    name: str,
    start: str,
    end: str,
    timezone: str = "UTC",
    assigned_stations: Optional[List[int]] = None,
    session_id: str = "default",
) -> Dict[str, Any]:
    """Add a named time window to the batch session.

    Args:
        name: Human-readable label for this window (e.g. ``"night_01"``).
        start: Start time in ISO 8601 format.
        end: End time in ISO 8601 format.
        timezone: Timezone string (e.g. ``"UTC"``, ``"Asia/Tehran"``).
        assigned_stations: Optional list of station numbers this window
            applies to.  ``None`` means all stations.
        session_id: Batch session identifier.
    """
    try:
        batch = _get_batch(session_id)
        batch.add_time_window(
            name, start, end,
            timezone=timezone,
            stations=assigned_stations,
        )
        return {
            "status": "ok",
            "window": name,
            "start": start,
            "end": end,
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def import_time_windows_csv(
    csv_path: str,
    timezone: str = "UTC",
    session_id: str = "default",
) -> Dict[str, Any]:
    """Import time windows from a CSV file.

    The CSV should contain columns for window name, start, and end times.

    Args:
        csv_path: Absolute path to the CSV file.
        timezone: Default timezone applied to windows without one.
        session_id: Batch session identifier.
    """
    try:
        batch = _get_batch(session_id)
        batch.import_time_windows_csv(csv_path)
        windows = batch.get_time_windows()
        return {
            "window_count": len(windows),
            "windows": [w.to_dict() for w in windows],
        }
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def set_timezone(
    timezone: str,
    session_id: str = "default",
) -> Dict[str, Any]:
    """Set the global timezone for the batch session.

    Affects how time window boundaries are interpreted.

    Args:
        timezone: IANA timezone string (e.g. ``"UTC"``, ``"US/Eastern"``).
        session_id: Batch session identifier.
    """
    try:
        batch = _get_batch(session_id)
        batch.set_timezone(timezone)
        return {"status": "ok", "timezone": timezone}
    except Exception as e:
        return {"error": str(e)}


@mcp.tool()
def get_time_windows(session_id: str = "default") -> Dict[str, Any]:
    """Return all time windows configured in the batch session.

    Each window includes its name, start/end times, timezone, and
    assigned stations.
    """
    try:
        batch = _get_batch(session_id)
        windows = batch.get_time_windows()
        return {
            "window_count": len(windows),
            "windows": [w.to_dict() for w in windows],
        }
    except Exception as e:
        return {"error": str(e)}
