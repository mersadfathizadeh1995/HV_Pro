---
name: hv-batch
description: >-
  Perform batch HVSR (Horizontal-to-Vertical Spectral Ratio) analysis on
  multiple seismic stations using the hvsr-batch-pro MCP server. Use when the
  user asks to process multiple stations, run a microzonation survey, import
  stations from a folder or CSV, define time windows, generate combined median
  curves, export multi-station reports, or perform batch quality control.
  Supports MiniSEED, SAC, SAF, GCF, TXT, and other seismic formats. Produces
  per-station H/V curves, combined median analysis, peak statistics, and
  comprehensive batch reports with data exports and plots.
  Keywords: batch HVSR, multi-station, microzonation, survey, combined median,
  station import, time windows, batch report, multi-file, parallel processing,
  seismic array, site characterization, ambient vibration survey.
metadata:
  author: HV-Pro-Team
  version: '1.0'
  mcp-server: hvsr-batch-pro
---

# HVSR Batch Processing

Perform batch Horizontal-to-Vertical Spectral Ratio (HVSR) analysis on
multiple seismic stations simultaneously using the `hvsr-batch-pro` MCP server.
Designed for microzonation surveys, seismic arrays, and any workflow requiring
consistent processing across many recording locations.

## When to Use This Skill

Use this skill when the user asks you to:

- Process multiple seismic stations in a single workflow (batch HVSR)
- Run a microzonation survey or seismic site characterization campaign
- Import stations from a folder of seismic files or a CSV manifest
- Define per-station or shared time windows for analysis
- Compute a combined median HVSR curve across multiple stations
- Generate a batch report with per-station and combined results
- Detect peaks and compute peak statistics across a station set
- Export multi-station results to JSON, CSV, MAT, or Excel
- Configure sensors for a set of recording instruments
- Run parallel HVSR processing across many stations

## Instructions

### Step 1: Import Stations

Choose one of three import methods depending on your data layout.

**Option A — Import from folder (recommended for organized data):**

```
import_stations_from_folder(
    folder="D:\\Data\\Survey_2026",
    recursive=True
)
```

Scans the folder for recognized seismic files and auto-creates one station
per file (or per file group). Set `recursive=True` to include subfolders.

**Option B — Import from CSV manifest:**

```
import_stations_from_csv(
    csv_path="D:\\Data\\stations.csv"
)
```

The CSV must contain columns for station number, file paths, and optionally
station name and sensor ID. See `references/csv-format.md` for the schema.

**Option C — Add stations manually:**

```
add_station(
    station_num=1,
    files=["D:\\Data\\STN01_Z.miniseed", "D:\\Data\\STN01_N.miniseed", "D:\\Data\\STN01_E.miniseed"],
    station_name="STN01",
    sensor_id="TC4"
)
```

Repeat for each station. Use absolute paths with backslashes on Windows.

**Key rules:**
- Always use **absolute paths**.
- File paths use backslashes (`\`) on Windows.
- After import, call `get_stations()` to verify the station list.

### Step 2: Configure Sensors (Optional)

If your stations use different sensor types, configure them:

```
setup_sensors(
    folder="D:\\Data\\Survey_2026",
    sensor_config_path="D:\\Config\\sensors.json"
)
```

Provide either `folder` (auto-detect from headers) or `sensor_config_path`
(explicit mapping). Returns the sensor list with response curves applied.

### Step 3: Configure Time Windows

Define the time ranges for analysis. All times are interpreted in the
specified timezone and converted to UTC internally.

**Option A — Add individual time windows:**

```
add_time_window(
    name="Morning",
    start="2026-04-01T06:00:00",
    end="2026-04-01T08:00:00",
    timezone="Asia/Tehran",
    assigned_stations=["STN01", "STN02", "STN03"]
)
```

If `assigned_stations` is omitted, the window applies to **all** stations.

**Option B — Import time windows from CSV:**

```
import_time_windows_csv(
    csv_path="D:\\Data\\time_windows.csv",
    timezone="Asia/Tehran"
)
```

**Set default timezone:**

```
set_timezone(timezone="Asia/Tehran")
```

Call `get_time_windows()` to verify after configuration.

### Step 4: Set Processing Parameters

Call `set_processing_params` to adjust analysis settings. Only provide the
parameters you want to change; the rest keep their defaults.

```
set_processing_params(
    window_length=120,
    overlap=0.0,
    freq_min=0.2,
    freq_max=50,
    n_frequencies=200,
    smoothing_method="konno_ohmachi",
    smoothing_bandwidth=40,
    horizontal_method="geometric_mean",
    statistics_method="lognormal"
)
```

**Recommended defaults** (SESAME standard):

| Parameter | Default | Description |
|-----------|---------|-------------|
| `window_length` | 120 s | FFT window length |
| `overlap` | 0.0 | Window overlap fraction (0 = no overlap) |
| `freq_min` | 0.2 Hz | Minimum analysis frequency |
| `freq_max` | 50 Hz | Maximum analysis frequency |
| `n_frequencies` | 200 | Number of frequency samples |
| `smoothing_method` | `konno_ohmachi` | Spectral smoothing method |
| `smoothing_bandwidth` | 40 | Konno-Ohmachi bandwidth parameter |
| `horizontal_method` | `geometric_mean` | H-component combination method |
| `taper` | `cosine` | Window taper function |
| `detrend` | `linear` | Detrend method before FFT |
| `statistics_method` | `lognormal` | Statistical method (log-space median ± percentiles) |

### Step 5: Configure Quality Control (Optional)

Call `set_qc_params` to tune or disable individual QC algorithms.

```
set_qc_params(
    stalta_enabled=True,
    amplitude_enabled=True,
    statistical_enabled=True,
    fdwra_enabled=True,
    hvsr_amplitude_enabled=True,
    flat_peak_enabled=False,
    curve_outlier_enabled=True
)
```

Each algorithm has sub-parameters (thresholds, window lengths, etc.).
Use `list_qc_algorithms()` to discover all tuneable parameters and their
default values.

### Step 6: Configure Peak Detection (Optional)

```
set_peak_params(
    auto_mode="auto_multi",
    peak_basis="median",
    min_prominence=0.5,
    min_amplitude=2.0,
    n_peaks=3,
    freq_tolerance=0.1
)
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `auto_mode` | `auto_multi` | Detection mode: `auto_primary`, `auto_top_n`, `auto_multi` |
| `peak_basis` | `median` | Use median curve (recommended) or mean |
| `min_prominence` | 0.5 | Minimum peak prominence |
| `min_amplitude` | 2.0 | Minimum H/V ratio to consider a peak |
| `n_peaks` | 3 | Number of peaks for `auto_top_n` mode |
| `freq_tolerance` | 0.1 Hz | Frequency grouping tolerance for combined peaks |

### Step 7: Configure Output (Optional)

```
set_output_params(
    save_png=True,
    save_pdf=False,
    figure_dpi=300,
    save_json=True,
    save_csv=True,
    save_mat=False,
    export_excel=True,
    generate_standard_figure=True,
    generate_hvsr_pro_figure=True,
    generate_statistics_figure=True,
    output_dir="D:\\Output\\Survey_2026"
)
```

### Step 8: Validate Setup

Before running the analysis, validate the configuration:

```
validate_setup()
```

Returns `{"valid": true}` or `{"valid": false, "errors": [...]}`.
Fix any errors before proceeding. Common checks:
- At least one station is imported
- Each station has valid file paths
- Time windows fall within data bounds
- Processing parameters are within valid ranges

### Step 9: Prepare Data (Phase 1)

```
prepare_data()
```

Phase 1 loads seismic data for all stations, applies time windowing,
and performs initial signal conditioning (detrend, taper). Returns:
- `success`: overall success flag
- `n_stations`: number of stations processed
- `results`: per-station preparation status

### Step 10: Process HVSR (Phase 2 — Parallel)

```
process_hvsr(
    parallel=True,
    n_workers=4
)
```

Phase 2 computes HVSR for each station: FFT, smoothing, H/V ratio,
QC rejection, and FDWRA. Set `parallel=True` to process stations
concurrently. Returns per-station results with peak detection and
QC summaries.

**Acceptance rate guidance:**
- Greater than 60%: Good data quality
- 40–60%: Acceptable; review QC breakdown
- Less than 40%: Noisy data; consider adjusting QC or re-recording

### Step 11: Run Combined Analysis (Phase 3)

```
run_analysis()
```

Phase 3 computes the combined median HVSR curve across all stations,
detects combined peaks, and calculates peak statistics (mean f0,
standard deviation, coefficient of variation). Returns:
- `combined_peaks`: peaks on the combined curve
- `peak_statistics`: statistical summary across stations

### Step 12: Export Results & Generate Report

**Option A — Full batch report (recommended):**

```
generate_report(
    output_dir="D:\\Output\\Survey_2026\\Report",
    dpi=300
)
```

Generates a comprehensive report directory with per-station plots,
combined curves, data exports, and summary files.

**Option B — Export data files only:**

```
export_results(
    output_dir="D:\\Output\\Survey_2026\\Data",
    formats=["json", "csv", "excel"]
)
```

**Option C — Inspect results programmatically:**

```
get_results_summary()
```

Returns the full batch summary without exporting files. For individual
station details:

```
get_station_result(station_name="STN01")
```

**Option D — Detect combined peaks with custom thresholds:**

```
detect_combined_peaks(
    min_prominence=0.5,
    min_amplitude=2.0,
    n_peaks=3
)
```

## Tool Quick Reference

### Setup Tools (13 tools)

| Tool | Purpose |
|------|---------|
| `list_supported_formats` | List supported seismic file formats |
| `get_batch_defaults` | Get default batch configuration as JSON |
| `list_qc_algorithms` | List all QC rejection algorithms and parameters |
| `list_figure_types` | List available per-station and combined plot types |
| `import_stations_from_folder` | Auto-import stations from a data folder |
| `import_stations_from_csv` | Import stations from a CSV manifest |
| `add_station` | Manually add a single station |
| `setup_sensors` | Configure sensor response curves |
| `get_stations` | List all imported stations |
| `add_time_window` | Add a named time window (with optional station assignment) |
| `import_time_windows_csv` | Import time windows from CSV |
| `set_timezone` | Set default timezone for time interpretation |
| `get_time_windows` | List all configured time windows |

### Configuration Tools (4 tools)

| Tool | Purpose |
|------|---------|
| `set_processing_params` | Set spectral processing parameters |
| `set_qc_params` | Tune quality-control algorithms |
| `set_peak_params` | Configure peak detection settings |
| `set_output_params` | Configure export formats and plot options |

### Analysis Tools (4 tools)

| Tool | Purpose |
|------|---------|
| `validate_setup` | Validate station + config before running |
| `prepare_data` | Phase 1: load, window, and condition data |
| `process_hvsr` | Phase 2: compute HVSR per station (parallel) |
| `run_analysis` | Phase 3: combined analysis and peak statistics |

### Results Tools (5 tools)

| Tool | Purpose |
|------|---------|
| `get_results_summary` | Get full batch summary (combined + per-station) |
| `get_station_result` | Get detailed results for one station |
| `generate_report` | Generate full batch report with plots and data |
| `export_results` | Export data files (JSON, CSV, MAT, Excel) |
| `detect_combined_peaks` | Detect peaks on combined median curve |

## Defaults

### Processing Defaults

```json
{
  "window_length": 120,
  "overlap": 0.0,
  "freq_min": 0.2,
  "freq_max": 50,
  "n_frequencies": 200,
  "smoothing_method": "konno_ohmachi",
  "smoothing_bandwidth": 40,
  "horizontal_method": "geometric_mean",
  "taper": "cosine",
  "detrend": "linear",
  "statistics_method": "lognormal"
}
```

### Peak Detection Defaults

```json
{
  "auto_mode": "auto_multi",
  "peak_basis": "median",
  "min_prominence": 0.5,
  "min_amplitude": 2.0,
  "n_peaks": 3,
  "freq_tolerance": 0.1
}
```

### Output Defaults

```json
{
  "save_png": true,
  "save_pdf": false,
  "figure_dpi": 300,
  "save_json": true,
  "save_csv": true,
  "save_mat": false,
  "export_excel": false,
  "generate_standard_figure": true,
  "generate_hvsr_pro_figure": true,
  "generate_statistics_figure": true,
  "output_dir": null
}
```

## Interpreting Batch Results

- **Combined median curve:** The median H/V ratio across all stations at each
  frequency. Represents the "typical" site response for the survey area.
- **Peak statistics:** Mean f0, standard deviation, and coefficient of
  variation across stations. Low CV (<15%) indicates consistent site conditions.
- **Per-station peaks:** Individual station f0 values. Outliers may indicate
  localized geological features or data quality issues.
- **Peak amplitude ≥ 2:** Generally considered a reliable, clear impedance
  contrast between soil and bedrock.
- **Multiple peaks:** May indicate layered subsurface (e.g., soil over
  weathered rock over bedrock).

## Troubleshooting

| Error | Fix |
|-------|-----|
| No stations imported | Check folder path or CSV format |
| Station has no valid files | Verify file paths are absolute and files exist |
| Time window outside data bounds | Narrow time range or check timezone setting |
| No windows passed QC | Loosen QC thresholds via `set_qc_params` |
| Validation failed | Call `validate_setup` and fix reported errors |
| Parallel processing fails | Set `parallel=False` or reduce `n_workers` |
| Empty combined curve | Ensure `process_hvsr` completed successfully first |
| Low acceptance rate across stations | Review Phase 1 QC breakdown; adjust STA/LTA or amplitude thresholds |

## Examples

### Example 1: Folder Import with Auto-Detected Sensors

Process 5 stations from a survey folder with automatic sensor detection
and default processing parameters.

```
# Step 1: Import stations from folder
import_stations_from_folder(
    folder="D:\\Data\\Microzonation_2026",
    recursive=True
)

# Step 2: Auto-detect sensors
setup_sensors(folder="D:\\Data\\Microzonation_2026")

# Step 3: Set a shared time window for all stations
add_time_window(
    name="Night_Recording",
    start="2026-04-01T23:00:00",
    end="2026-04-02T05:00:00",
    timezone="Asia/Tehran"
)

# Step 4: Processing with defaults (lognormal, 120 s windows)
set_processing_params(
    window_length=120,
    freq_min=0.2,
    freq_max=50,
    n_frequencies=200,
    smoothing_method="konno_ohmachi",
    smoothing_bandwidth=40,
    statistics_method="lognormal"
)

# Step 5: Validate
validate_setup()

# Step 6: Run three-phase pipeline
prepare_data()
process_hvsr(parallel=True, n_workers=4)
run_analysis()

# Step 7: Export full report
generate_report(
    output_dir="D:\\Output\\Microzonation_2026\\Report",
    dpi=300
)
```

### Example 2: CSV Import with Per-Station Time Windows

Import stations and time windows from separate CSV files, apply custom
QC settings, and export results in multiple formats.

```
# Step 1: Import stations from CSV
import_stations_from_csv(
    csv_path="D:\\Data\\Survey\\stations.csv"
)

# Step 2: Import per-station time windows
import_time_windows_csv(
    csv_path="D:\\Data\\Survey\\time_windows.csv",
    timezone="Europe/Berlin"
)

# Step 3: Custom processing
set_processing_params(
    window_length=60,
    overlap=0.0,
    freq_min=0.5,
    freq_max=30,
    n_frequencies=150,
    smoothing_method="konno_ohmachi",
    smoothing_bandwidth=40,
    horizontal_method="geometric_mean",
    statistics_method="lognormal"
)

# Step 4: Tune QC — loosen STA/LTA, enable FDWRA
set_qc_params(
    stalta_enabled=True,
    fdwra_enabled=True,
    curve_outlier_enabled=True,
    flat_peak_enabled=True
)

# Step 5: Custom peak detection
set_peak_params(
    auto_mode="auto_top_n",
    peak_basis="median",
    min_prominence=0.3,
    min_amplitude=1.5,
    n_peaks=5,
    freq_tolerance=0.2
)

# Step 6: Configure output formats
set_output_params(
    save_png=True,
    save_pdf=True,
    figure_dpi=300,
    save_json=True,
    save_csv=True,
    export_excel=True,
    output_dir="D:\\Output\\Survey"
)

# Step 7: Validate and run
validate_setup()
prepare_data()
process_hvsr(parallel=True, n_workers=8)
run_analysis()

# Step 8: Export
generate_report(output_dir="D:\\Output\\Survey\\Report", dpi=300)
export_results(
    output_dir="D:\\Output\\Survey\\Data",
    formats=["json", "csv", "excel"]
)
```

### Example 3: Quick Single-Station Analysis

Use the batch server to process a single station with minimal configuration.

```
# Add one station manually
add_station(
    station_num=1,
    files=["D:\\Data\\STN01.miniseed"],
    station_name="STN01"
)

# Use defaults for everything — just validate and run
validate_setup()
prepare_data()
process_hvsr(parallel=False)
run_analysis()

# Check results without exporting
get_results_summary()
get_station_result(station_name="STN01")

# Detect combined peaks with custom thresholds
detect_combined_peaks(min_prominence=0.3, min_amplitude=1.5, n_peaks=3)
```

## References

See the `references/` subfolder for detailed documentation:

- `references/tool-reference.md` — Full parameter details for all 26 tools
- `references/csv-format.md` — CSV schema for station and time window imports
- `references/figure-types.md` — All available per-station and combined plot types
- `references/qc-pipeline.md` — QC algorithm details and tuning guide
- `references/config-reference.md` — Complete batch configuration JSON structure
