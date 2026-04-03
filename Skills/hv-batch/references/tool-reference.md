# Tool Reference — hv-batch MCP Server

Complete parameter documentation for all 26 MCP tools in the batch HVSR
processing server.

Tools are grouped into six categories matching the typical batch workflow:

| Category | Tools | Purpose |
|----------|------:|---------|
| [A. Discovery & Introspection](#a-discovery--introspection) | 4 | Enumerate formats, defaults, QC algorithms, figure types |
| [B. Station & Sensor Setup](#b-station--sensor-setup) | 5 | Import / add stations and configure sensors |
| [C. Time Windows](#c-time-windows) | 4 | Define, import, and query time windows |
| [D. Configuration](#d-configuration) | 4 | Tune processing, QC, peak-detection, and output parameters |
| [E. Execution](#e-execution) | 4 | Validate, load data, compute HVSR, run combined analysis |
| [F. Results & Export](#f-results--export) | 5 | Retrieve results, export data, generate reports, re-detect peaks |

---

## A. Discovery & Introspection

### list_supported_formats

List seismic file formats accepted for batch processing.

**Parameters:** _none_

**Returns:** A list of dicts, each with `id`, `extensions`, and `description`.

| id | Extensions | Description |
|----|-----------|-------------|
| `miniseed` | `.miniseed`, `.mseed` | MiniSEED seismic data |
| `txt` | `.txt` | ASCII 3-column text (E, N, Z) |
| `saf` | `.saf` | Seismic Analysis Format |
| `sac` | `.sac` | SAC binary format |
| `gcf` | `.gcf` | Guralp Compressed Format |
| `peer` | `.peer`, `.at2` | PEER NGA format |
| `csv` | `.csv` | CSV data |

**Example:**

```json
// request
{ "tool": "list_supported_formats" }

// response
[
  {"id": "miniseed", "extensions": [".miniseed", ".mseed"], "description": "MiniSEED seismic data"},
  ...
]
```

---

### get_batch_defaults

Return the default `BatchConfig` as a JSON-serialisable dict. Useful for
inspecting all available configuration parameters and their default values
before customising a batch run.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `session_id` | string | No | `"default"` | Batch session identifier |

**Returns:** A dict representing the full `BatchConfig` with default values for
processing, QC, peak-detection, and output sections.

**Example:**

```json
{ "tool": "get_batch_defaults", "arguments": {} }
```

---

### list_qc_algorithms

List available quality-control algorithms with tuneable parameters and
defaults.

**Parameters:** _none_

**Returns:** A dict keyed by algorithm name. Each entry contains `enabled`
(bool), `description` (string), and `params` (dict of default parameter
values).

| Algorithm | Description |
|-----------|-------------|
| `stalta` | STA/LTA transient detection — rejects windows with transient energy bursts |
| `amplitude` | Amplitude / clipping check — rejects clipped or dead-channel windows |
| `statistical` | Statistical outlier detection (IQR or z-score) on time-domain windows |
| `fdwra` | Cox Frequency-Dependent Window Rejection Algorithm — iteratively removes windows whose H/V curves deviate from the median |
| `hvsr_amplitude` | Post-HVSR amplitude gate — rejects windows below a minimum H/V ratio |
| `flat_peak` | Flat-peak rejection — removes windows whose H/V peak is too flat |
| `curve_outlier` | Post-HVSR curve outlier rejection — iteratively removes H/V curves that deviate from the ensemble |

**Example:**

```json
{ "tool": "list_qc_algorithms" }
```

---

### list_figure_types

List available figure types for batch export, separated into per-station
and combined (multi-station) categories.

**Parameters:** _none_

**Returns:**

```json
{
  "per_station": [
    "hvsr_curve", "hvsr_statistics", "hvsr_with_windows",
    "quality_metrics", "window_timeline", "peak_analysis",
    "complete_dashboard", "mean_vs_median", "quality_histogram",
    "selected_metrics", "window_timeseries", "window_spectrogram",
    "raw_vs_adjusted", "waveform_rejection", "pre_post_rejection"
  ],
  "combined": [
    "all_hvsr_overlay", "peak_frequency_map", "summary_table"
  ]
}
```

**Example:**

```json
{ "tool": "list_figure_types" }
```

---

## B. Station & Sensor Setup

### import_stations_from_folder

Import stations by scanning a folder for seismic data files. Each unique
station number found in the file names becomes a station.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `folder` | string | **Yes** | — | Absolute path to the folder containing seismic files |
| `recursive` | boolean | No | `false` | Whether to search subfolders (reserved for future use) |
| `session_id` | string | No | `"default"` | Batch session identifier |

**Returns:**

```json
{
  "station_count": 5,
  "stations": [ { "station_num": 1, "name": "...", "files": [...], "sensor_id": "..." }, ... ]
}
```

On error: `{"error": "<message>"}`.

**Example:**

```json
{
  "tool": "import_stations_from_folder",
  "arguments": {
    "folder": "D:\\Data\\Survey_01"
  }
}
```

---

### import_stations_from_csv

Import stations from a CSV file. The CSV must contain columns for station
number, file paths, and optionally sensor ID and station name.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `csv_path` | string | **Yes** | — | Absolute path to the CSV file |
| `session_id` | string | No | `"default"` | Batch session identifier |

**Returns:**

```json
{
  "station_count": 5,
  "stations": [ { ... }, ... ]
}
```

**Example:**

```json
{
  "tool": "import_stations_from_csv",
  "arguments": {
    "csv_path": "D:\\Data\\stations.csv"
  }
}
```

---

### add_station

Add a single station to the batch configuration.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `station_num` | integer | **Yes** | — | Unique integer station number |
| `files` | list[string] | **Yes** | — | List of absolute file paths assigned to this station |
| `station_name` | string | No | `""` | Optional human-readable station name |
| `sensor_id` | string | No | `""` | Optional sensor identifier to associate |
| `session_id` | string | No | `"default"` | Batch session identifier |

**Returns:**

```json
{ "status": "ok", "station_num": 1, "file_count": 3 }
```

**Example:**

```json
{
  "tool": "add_station",
  "arguments": {
    "station_num": 1,
    "files": [
      "D:\\Data\\ST01_E.miniseed",
      "D:\\Data\\ST01_N.miniseed",
      "D:\\Data\\ST01_Z.miniseed"
    ],
    "station_name": "Bridge North",
    "sensor_id": "centaur-3_1234"
  }
}
```

---

### setup_sensors

Configure sensors for the batch session. Provide **either** a data folder
(auto-detect sensors from file names) or a JSON config path (explicit
definitions). If both are given, the JSON config takes precedence.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `folder` | string | No | `null` | Absolute path to a folder whose filenames contain sensor serial patterns (e.g. Centaur `centaur-3_NNNN_`) |
| `sensor_config_path` | string | No | `null` | Absolute path to a JSON file with sensor definitions |
| `session_id` | string | No | `"default"` | Batch session identifier |

> **Note:** At least one of `folder` or `sensor_config_path` must be provided.

**Returns:**

```json
{
  "sensor_count": 2,
  "sensors": [ { "sensor_id": "centaur-3_1234", ... }, ... ]
}
```

**Example (auto-detect):**

```json
{
  "tool": "setup_sensors",
  "arguments": {
    "folder": "D:\\Data\\Survey_01"
  }
}
```

**Example (JSON config):**

```json
{
  "tool": "setup_sensors",
  "arguments": {
    "sensor_config_path": "D:\\Config\\sensors.json"
  }
}
```

---

### get_stations

Return all stations currently configured in the batch session.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `session_id` | string | No | `"default"` | Batch session identifier |

**Returns:**

```json
{
  "station_count": 5,
  "stations": [
    { "station_num": 1, "name": "Bridge North", "files": [...], "sensor_id": "centaur-3_1234" },
    ...
  ]
}
```

**Example:**

```json
{ "tool": "get_stations" }
```

---

## C. Time Windows

### add_time_window

Add a named time window to the batch session.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `name` | string | **Yes** | — | Human-readable label for this window (e.g. `"night_01"`) |
| `start` | string | **Yes** | — | Start time in ISO 8601 format |
| `end` | string | **Yes** | — | End time in ISO 8601 format |
| `timezone` | string | No | `"UTC"` | Timezone string (e.g. `"UTC"`, `"Asia/Tehran"`) |
| `assigned_stations` | list[int] | No | `null` | Station numbers this window applies to. `null` means all stations |
| `session_id` | string | No | `"default"` | Batch session identifier |

**Returns:**

```json
{ "status": "ok", "window": "night_01", "start": "2024-01-15T22:00:00", "end": "2024-01-16T06:00:00" }
```

**Example:**

```json
{
  "tool": "add_time_window",
  "arguments": {
    "name": "night_01",
    "start": "2024-01-15T22:00:00",
    "end": "2024-01-16T06:00:00",
    "timezone": "Asia/Tehran",
    "assigned_stations": [1, 2, 3]
  }
}
```

---

### import_time_windows_csv

Import time windows from a CSV file. The CSV should contain columns for
window name, start, and end times.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `csv_path` | string | **Yes** | — | Absolute path to the CSV file |
| `timezone` | string | No | `"UTC"` | Default timezone applied to windows without one |
| `session_id` | string | No | `"default"` | Batch session identifier |

**Returns:**

```json
{
  "window_count": 4,
  "windows": [ { "name": "night_01", "start": "...", "end": "...", ... }, ... ]
}
```

**Example:**

```json
{
  "tool": "import_time_windows_csv",
  "arguments": {
    "csv_path": "D:\\Config\\time_windows.csv",
    "timezone": "Asia/Tehran"
  }
}
```

---

### set_timezone

Set the global timezone for the batch session. Affects how time window
boundaries are interpreted.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `timezone` | string | **Yes** | — | IANA timezone string (e.g. `"UTC"`, `"US/Eastern"`, `"Asia/Tehran"`) |
| `session_id` | string | No | `"default"` | Batch session identifier |

**Returns:**

```json
{ "status": "ok", "timezone": "Asia/Tehran" }
```

**Example:**

```json
{
  "tool": "set_timezone",
  "arguments": { "timezone": "Asia/Tehran" }
}
```

---

### get_time_windows

Return all time windows configured in the batch session. Each window
includes its name, start/end times, timezone, and assigned stations.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `session_id` | string | No | `"default"` | Batch session identifier |

**Returns:**

```json
{
  "window_count": 4,
  "windows": [
    { "name": "night_01", "start": "...", "end": "...", "timezone": "UTC", "assigned_stations": null },
    ...
  ]
}
```

**Example:**

```json
{ "tool": "get_time_windows" }
```

---

## D. Configuration

### set_processing_params

Adjust HVSR processing parameters. Only provided values are changed; the
rest keep their current values.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `window_length` | number | No | `null` | Window length in seconds (e.g. 60, 120) |
| `overlap` | number | No | `null` | Overlap fraction 0.0–1.0 (e.g. 0.5 = 50%) |
| `freq_min` | number | No | `null` | Minimum frequency in Hz |
| `freq_max` | number | No | `null` | Maximum frequency in Hz |
| `n_frequencies` | integer | No | `null` | Number of frequency points |
| `smoothing_method` | string | No | `null` | `"konno_ohmachi"`, `"parzen"`, `"constant_bandwidth"`, `"proportional_bandwidth"` |
| `smoothing_bandwidth` | number | No | `null` | Smoothing bandwidth (40 for Konno-Ohmachi) |
| `horizontal_method` | string | No | `null` | `"geometric_mean"`, `"arithmetic_mean"`, `"quadratic_mean"`, `"ps_RotD50"`, `"maximum_horizontal"`, `"single_azimuth"` |
| `taper` | string | No | `null` | Taper window type |
| `detrend` | string | No | `null` | Detrending method |
| `statistics_method` | string | No | `null` | `"lognormal"` (recommended) or `"normal"` |
| `session_id` | string | No | `"default"` | Batch session identifier |

**Returns:** The updated processing configuration as a dict.

**Example:**

```json
{
  "tool": "set_processing_params",
  "arguments": {
    "window_length": 60,
    "overlap": 0.5,
    "freq_min": 0.5,
    "freq_max": 20.0,
    "smoothing_method": "konno_ohmachi",
    "smoothing_bandwidth": 40,
    "statistics_method": "lognormal"
  }
}
```

---

### set_qc_params

Adjust quality-control parameters. Only provided values are changed.

Enable flags are set directly on the QC config. Sub-parameters are
forwarded with their algorithm prefix so the batch engine can route them
to the correct sub-config (e.g. `sta_length` → `stalta_sta_length`).

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| **Algorithm enable flags** | | | | |
| `stalta_enabled` | boolean | No | `null` | Enable STA/LTA transient detection |
| `amplitude_enabled` | boolean | No | `null` | Enable amplitude / clipping check |
| `statistical_enabled` | boolean | No | `null` | Enable statistical outlier detection |
| `fdwra_enabled` | boolean | No | `null` | Enable Cox FDWRA |
| `hvsr_amplitude_enabled` | boolean | No | `null` | Enable post-HVSR amplitude gate |
| `flat_peak_enabled` | boolean | No | `null` | Enable flat-peak rejection |
| `curve_outlier_enabled` | boolean | No | `null` | Enable curve outlier rejection |
| **STA/LTA sub-parameters** | | | | |
| `sta_length` | number | No | `null` | Short-term average window length (seconds) |
| `lta_length` | number | No | `null` | Long-term average window length (seconds) |
| `sta_lta_min_ratio` | number | No | `null` | Minimum STA/LTA ratio threshold |
| `sta_lta_max_ratio` | number | No | `null` | Maximum STA/LTA ratio threshold |
| **Amplitude sub-parameters** | | | | |
| `clipping_threshold` | number | No | `null` | Fraction of full-scale considered clipping (0–1) |
| `min_rms` | number | No | `null` | Minimum RMS amplitude (rejects dead channels) |
| **Statistical sub-parameters** | | | | |
| `statistical_method` | string | No | `null` | `"iqr"` or `"zscore"` |
| `statistical_threshold` | number | No | `null` | Deviation threshold |
| **FDWRA sub-parameters** | | | | |
| `fdwra_n` | number | No | `null` | Rejection threshold in std devs |
| `fdwra_max_iterations` | integer | No | `null` | Maximum rejection passes |
| `fdwra_distribution` | string | No | `null` | `"lognormal"` or `"normal"` |
| **HVSR amplitude sub-parameters** | | | | |
| `hvsr_amplitude_min` | number | No | `null` | Minimum H/V amplitude to keep a window |
| **Flat-peak sub-parameters** | | | | |
| `flatness_threshold` | number | No | `null` | Flatness threshold for peak rejection |
| **Curve-outlier sub-parameters** | | | | |
| `curve_outlier_threshold` | number | No | `null` | Outlier threshold (std devs) |
| `curve_outlier_max_iterations` | integer | No | `null` | Maximum rejection iterations |
| **Session** | | | | |
| `session_id` | string | No | `"default"` | Batch session identifier |

**Returns:** The updated QC configuration as a dict.

**Example:**

```json
{
  "tool": "set_qc_params",
  "arguments": {
    "stalta_enabled": true,
    "sta_length": 1.0,
    "lta_length": 30.0,
    "sta_lta_max_ratio": 2.5,
    "fdwra_enabled": true,
    "fdwra_n": 2.0,
    "fdwra_distribution": "lognormal"
  }
}
```

---

### set_peak_params

Adjust peak-detection parameters. Only provided values are changed.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `auto_mode` | boolean | No | `null` | Enable automatic peak detection |
| `peak_basis` | string | No | `null` | `"median"` (recommended) or `"mean"` |
| `min_prominence` | number | No | `null` | Minimum peak prominence |
| `min_amplitude` | number | No | `null` | Minimum H/V amplitude to consider a peak |
| `n_peaks` | integer | No | `null` | Maximum number of peaks to detect |
| `freq_tolerance` | number | No | `null` | Frequency tolerance for matching peaks across stations (Hz) |
| `session_id` | string | No | `"default"` | Batch session identifier |

**Returns:** The updated peak-detection configuration as a dict.

**Example:**

```json
{
  "tool": "set_peak_params",
  "arguments": {
    "peak_basis": "median",
    "min_prominence": 0.5,
    "min_amplitude": 2.0,
    "n_peaks": 3
  }
}
```

---

### set_output_params

Adjust output and export parameters. Only provided values are changed.
If `output_dir` is provided it is also propagated to the top-level batch
configuration.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `save_png` | boolean | No | `null` | Save plots as PNG |
| `save_pdf` | boolean | No | `null` | Save plots as PDF |
| `figure_dpi` | integer | No | `null` | Plot resolution (DPI) |
| `save_json` | boolean | No | `null` | Export results as JSON |
| `save_csv` | boolean | No | `null` | Export results as CSV |
| `save_mat` | boolean | No | `null` | Export results as MAT (MATLAB) |
| `export_excel` | boolean | No | `null` | Export results as Excel workbook |
| `generate_standard_figure` | boolean | No | `null` | Generate the standard HVSR figure |
| `generate_hvsr_pro_figure` | boolean | No | `null` | Generate the HVSR Pro enhanced figure |
| `generate_statistics_figure` | boolean | No | `null` | Generate the statistics figure |
| `output_dir` | string | No | `null` | Absolute path to the output directory |
| `session_id` | string | No | `"default"` | Batch session identifier |

**Returns:** The updated output configuration as a dict.

**Example:**

```json
{
  "tool": "set_output_params",
  "arguments": {
    "save_png": true,
    "save_csv": true,
    "export_excel": true,
    "figure_dpi": 300,
    "output_dir": "D:\\Results\\Survey_01"
  }
}
```

---

## E. Execution

### validate_setup

Validate the current batch configuration before running. Checks config
parameters, file paths, and time-window definitions. Call this **before**
`prepare_data` to catch problems early.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `session_id` | string | No | `"default"` | Batch session identifier |

**Returns:**

```json
{
  "valid": true,
  "errors": {
    "config": [],
    "files": [],
    "time_windows": []
  }
}
```

When invalid, the error arrays contain human-readable messages:

```json
{
  "valid": false,
  "errors": {
    "config": ["window_length must be > 0"],
    "files": ["Station 1: file not found D:\\missing.mseed"],
    "time_windows": []
  }
}
```

**Example:**

```json
{ "tool": "validate_setup" }
```

---

### prepare_data

Load and prepare seismic data for every station in the batch. This is
**Phase 1** of the batch workflow. It reads raw files, applies time-window
trimming, and writes intermediate MAT files.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `session_id` | string | No | `"default"` | Batch session identifier |

**Returns:**

```json
{
  "success": true,
  "n_stations": 5,
  "results": [
    { "station": "Station_01", "success": true, "duration_s": 3600.0, "sampling_rate": 100.0 },
    ...
  ],
  "error": null
}
```

**Example:**

```json
{ "tool": "prepare_data" }
```

---

### process_hvsr

Compute HVSR curves and detect peaks for every station. This is
**Phase 2** of the batch workflow. Each station is processed independently
(optionally in parallel) to produce H/V spectral ratios and peak
detections.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `parallel` | boolean | No | `true` | Enable multi-process execution |
| `n_workers` | integer | No | `4` | Number of parallel workers |
| `session_id` | string | No | `"default"` | Batch session identifier |

**Returns:**

```json
{
  "success": true,
  "n_stations": 5,
  "results": [
    {
      "station": "Station_01",
      "success": true,
      "n_peaks": 2,
      "primary_frequency": 1.35,
      "valid_windows": 48,
      "total_windows": 55
    },
    ...
  ]
}
```

**Example:**

```json
{
  "tool": "process_hvsr",
  "arguments": {
    "parallel": true,
    "n_workers": 8
  }
}
```

---

### run_analysis

Run the combined multi-station analysis. This is **Phase 3** of the batch
workflow. It merges per-station HVSR curves, detects combined peaks, and
computes cross-station peak statistics.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `session_id` | string | No | `"default"` | Batch session identifier |

**Returns:**

```json
{
  "success": true,
  "n_stations": 5,
  "combined_peaks": [
    { "frequency": 1.35, "amplitude": 4.2, "prominence": 2.1 },
    ...
  ],
  "peak_statistics": [
    {
      "frequency_mean": 1.37,
      "frequency_std": 0.08,
      "amplitude_mean": 4.1,
      "n_matching_stations": 4
    },
    ...
  ]
}
```

**Example:**

```json
{ "tool": "run_analysis" }
```

---

## F. Results & Export

### get_results_summary

Return a combined results overview for all stations in the batch. Includes
the combined median HVSR curve, detected peaks, and a per-station summary
with success status and primary f₀.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `session_id` | string | No | `"default"` | Batch session identifier |

**Returns:**

```json
{
  "n_stations": 5,
  "combined": { "frequencies": [...], "median_hvsr": [...], "peaks": [...] },
  "per_station": [
    {
      "name": "Station_01",
      "success": true,
      "n_peaks": 2,
      "primary_f0": 1.35,
      "valid_windows": 48,
      "total_windows": 55
    },
    ...
  ]
}
```

**Example:**

```json
{ "tool": "get_results_summary" }
```

---

### get_station_result

Return detailed HVSR result for a single station. Includes the full
frequency/HVSR arrays, detected peaks, window counts, and rejection
reasons.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `station_name` | string | **Yes** | — | Name of the station to retrieve |
| `session_id` | string | No | `"default"` | Batch session identifier |

**Returns:**

```json
{
  "station_name": "Station_01",
  "success": true,
  "frequencies": [0.5, 0.52, ...],
  "median_hvsr": [1.01, 1.03, ...],
  "mean_hvsr": [1.02, 1.04, ...],
  "std_hvsr": [0.1, 0.12, ...],
  "peaks": [
    { "frequency": 1.35, "amplitude": 4.2, "prominence": 2.1 }
  ],
  "valid_windows": 48,
  "total_windows": 55,
  "rejected_reasons": { "stalta": 3, "amplitude": 2, "fdwra": 2 }
}
```

**Example:**

```json
{
  "tool": "get_station_result",
  "arguments": { "station_name": "Station_01" }
}
```

---

### generate_report

Generate a full batch analysis report with plots and data files. Creates
a directory of plots, CSVs, and metadata at `output_dir`. Returns a
manifest listing all generated files.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `output_dir` | string | **Yes** | — | Absolute path for the report directory |
| `dpi` | integer | No | `300` | Plot resolution (DPI) |
| `session_id` | string | No | `"default"` | Batch session identifier |

**Returns:**

```json
{
  "report_dir": "D:\\Results\\Report",
  "files": { "hvsr_curve": "D:\\Results\\Report\\hvsr_curve.png", ... },
  "n_files": 18
}
```

**Example:**

```json
{
  "tool": "generate_report",
  "arguments": {
    "output_dir": "D:\\Results\\Report",
    "dpi": 300
  }
}
```

---

### export_results

Export batch results in one or more formats. Supported formats: CSV, JSON,
MAT, Excel. If `formats` is not specified, all formats are exported.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `output_dir` | string | **Yes** | — | Absolute path for the export directory |
| `formats` | list[string] | No | `null` | List of formats to export (e.g. `["csv", "json"]`). `null` exports all |
| `session_id` | string | No | `"default"` | Batch session identifier |

**Returns:**

```json
{
  "output_dir": "D:\\Results\\Export",
  "files": { "csv": "D:\\Results\\Export\\results.csv", "json": "D:\\Results\\Export\\results.json" }
}
```

**Example:**

```json
{
  "tool": "export_results",
  "arguments": {
    "output_dir": "D:\\Results\\Export",
    "formats": ["csv", "json", "excel"]
  }
}
```

---

### detect_combined_peaks

Re-detect peaks on the combined median HVSR curve. Useful for adjusting
peak-detection thresholds after an initial analysis without reprocessing
all stations.

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `min_prominence` | number | No | `0.5` | Minimum peak prominence |
| `min_amplitude` | number | No | `2.0` | Minimum H/V amplitude to consider a peak |
| `n_peaks` | integer | No | `3` | Maximum number of peaks to detect |
| `session_id` | string | No | `"default"` | Batch session identifier |

**Returns:**

```json
{
  "n_peaks": 2,
  "peaks": [
    { "frequency": 1.35, "amplitude": 4.2, "prominence": 2.1 },
    { "frequency": 5.8, "amplitude": 2.8, "prominence": 1.2 }
  ]
}
```

**Example:**

```json
{
  "tool": "detect_combined_peaks",
  "arguments": {
    "min_prominence": 0.3,
    "min_amplitude": 1.5,
    "n_peaks": 5
  }
}
```

---

## Quick Reference — All 26 Tools

| # | Tool | Category | Required Parameters |
|---|------|----------|---------------------|
| 1 | `list_supported_formats` | Discovery | _none_ |
| 2 | `get_batch_defaults` | Discovery | _none_ |
| 3 | `list_qc_algorithms` | Discovery | _none_ |
| 4 | `list_figure_types` | Discovery | _none_ |
| 5 | `import_stations_from_folder` | Station Setup | `folder` |
| 6 | `import_stations_from_csv` | Station Setup | `csv_path` |
| 7 | `add_station` | Station Setup | `station_num`, `files` |
| 8 | `setup_sensors` | Station Setup | `folder` _or_ `sensor_config_path` |
| 9 | `get_stations` | Station Setup | _none_ |
| 10 | `add_time_window` | Time Windows | `name`, `start`, `end` |
| 11 | `import_time_windows_csv` | Time Windows | `csv_path` |
| 12 | `set_timezone` | Time Windows | `timezone` |
| 13 | `get_time_windows` | Time Windows | _none_ |
| 14 | `set_processing_params` | Configuration | _none_ (all optional) |
| 15 | `set_qc_params` | Configuration | _none_ (all optional) |
| 16 | `set_peak_params` | Configuration | _none_ (all optional) |
| 17 | `set_output_params` | Configuration | _none_ (all optional) |
| 18 | `validate_setup` | Execution | _none_ |
| 19 | `prepare_data` | Execution | _none_ |
| 20 | `process_hvsr` | Execution | _none_ (all optional) |
| 21 | `run_analysis` | Execution | _none_ |
| 22 | `get_results_summary` | Results | _none_ |
| 23 | `get_station_result` | Results | `station_name` |
| 24 | `generate_report` | Results | `output_dir` |
| 25 | `export_results` | Results | `output_dir` |
| 26 | `detect_combined_peaks` | Results | _none_ (all optional) |
