# Config Reference

Complete JSON structure for `BatchConfig` used with `configure_batch` and `run_batch_analysis`.

## Full Config Template

```json
{
  "site_name": "SITE",
  "output_dir": "",
  "stations": [
    {
      "station_num": 1,
      "station_name": "STN01",
      "files": ["/path/to/file.mseed"],
      "sensor_id": "",
      "sensor_name": "",
      "metadata": {}
    }
  ],
  "sensors": [
    {
      "sensor_id": "1",
      "display_name": "Centaur 0655",
      "file_patterns": [".*\\.mseed$"]
    }
  ],
  "sensor_station_map": {},
  "time_config": {
    "timezone": "UTC",
    "windows": [
      {
        "name": "Window_1",
        "start_utc": "2024-01-15T16:30:00",
        "end_utc": "2024-01-15T18:00:00",
        "start_local": "",
        "end_local": "",
        "assigned_stations": null
      }
    ],
    "station_assignments": {}
  },
  "processing": {
    "window_length": 120.0,
    "overlap": 0.0,
    "freq_min": 0.2,
    "freq_max": 50.0,
    "n_frequencies": 200,
    "smoothing_method": "konno_ohmachi",
    "smoothing_bandwidth": 40.0,
    "horizontal_method": "geometric_mean",
    "taper": "tukey",
    "detrend": "linear",
    "statistics_method": "lognormal",
    "std_ddof": 1
  },
  "peaks": {
    "auto_mode": true,
    "peak_basis": "median",
    "min_prominence": 0.5,
    "min_amplitude": 2.0,
    "n_peaks": 3,
    "freq_tolerance": 0.3
  },
  "qc": {
    "stalta_enabled": true,
    "stalta": {
      "sta_length": 1.0,
      "lta_length": 30.0,
      "min_ratio": 0.2,
      "max_ratio": 2.5
    },
    "amplitude_enabled": true,
    "amplitude": {
      "preset": "moderate",
      "max_amplitude": null,
      "min_rms": 1e-10,
      "clipping_threshold": 0.95,
      "clipping_max_percent": 1.0
    },
    "statistical_enabled": true,
    "statistical": {
      "method": "mad",
      "threshold": 3.0,
      "metric": "max_deviation"
    },
    "fdwra_enabled": true,
    "fdwra": {
      "n": 2.0,
      "max_iterations": 50,
      "min_iterations": 1,
      "distribution_fn": "lognormal",
      "distribution_mc": "lognormal"
    },
    "hvsr_amplitude_enabled": false,
    "hvsr_amplitude": {
      "min_amplitude": 1.0,
      "max_amplitude": 15.0
    },
    "flat_peak_enabled": false,
    "flat_peak": {
      "flatness_threshold": 0.15
    },
    "curve_outlier_enabled": true,
    "curve_outlier": {
      "threshold": 3.0,
      "max_iterations": 5,
      "metric": "mean"
    }
  },
  "output": {
    "save_json": true,
    "save_csv": true,
    "save_mat": true,
    "save_png": true,
    "save_pdf": false,
    "figure_dpi": 300,
    "generate_standard_figure": true,
    "generate_hvsr_pro_figure": true,
    "generate_statistics_figure": true,
    "export_excel": true,
    "export_combined_mat": true,
    "peak_font_size": 10
  },
  "figure_export": {
    "dpi": 300,
    "format": "png",
    "size_preset": "default",
    "y_limit_method": "auto",
    "y_limit_value": null,
    "show_mean": false,
    "show_median": true,
    "show_uncertainty": true,
    "show_rejected": false,
    "figure_types": [
      "hvsr_curve",
      "statistics",
      "windows",
      "quality",
      "dashboard",
      "peak_analysis",
      "raw_vs_adjusted",
      "waveform_rejection",
      "pre_post_rejection"
    ]
  },
  "execution": {
    "max_parallel": 4,
    "start_skip_minutes": 0.0,
    "process_length_minutes": 0.0,
    "full_duration": true,
    "per_window_process_lengths": {}
  }
}
```

## Section Details

### Top-Level Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `site_name` | string | `"SITE"` | Project / site identifier used in output file names |
| `output_dir` | string | `""` | Absolute path to the output directory |
| `stations` | array | `[]` | List of `StationDef` objects (see below) |
| `sensors` | array | `[]` | List of `SensorDef` objects (see below) |
| `sensor_station_map` | object | `{}` | Maps sensor_id → station_num for auto-assignment |

### stations (StationDef)

Each element describes a measurement station with its associated data files.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `station_num` | int | *(required)* | Station number (1–99) |
| `station_name` | string | `"STNnn"` | Display name; auto-generated from `station_num` if empty |
| `files` | array | `[]` | Absolute paths to seismic data files |
| `sensor_id` | string | `""` | Links to a `SensorDef.sensor_id` |
| `sensor_name` | string | `""` | Descriptive sensor label |
| `metadata` | object | `{}` | Arbitrary key-value metadata |

### sensors (SensorDef)

Defines a sensor type with file-matching patterns for auto-assignment.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `sensor_id` | string | *(required)* | Unique sensor identifier (e.g. `"1"`) |
| `display_name` | string | `""` | Human-readable name (e.g. `"Centaur 0655"`) |
| `file_patterns` | array | `[]` | Regex patterns to match data file names |

### time_config (TimeConfig)

Controls timezone, time windows, and station-to-window assignments.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `timezone` | string | `"UTC"` | Timezone label: `"UTC"`, `"CST"` (+6h), `"CDT"` (+5h) |
| `windows` | array | `[]` | List of `TimeWindowDef` objects |
| `station_assignments` | object | `{}` | Maps window name → list of station numbers |

#### TimeWindowDef

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | string | *(required)* | Window label (e.g. `"Window_1"`) |
| `start_utc` | string | `""` | Start time in ISO 8601 UTC |
| `end_utc` | string | `""` | End time in ISO 8601 UTC |
| `start_local` | string | `""` | Start time in local timezone (`%Y-%m-%d %H:%M:%S`) |
| `end_local` | string | `""` | End time in local timezone |
| `assigned_stations` | array\|null | `null` | Station numbers for this window; `null` = all stations |

---

### processing (ProcessingSettings)

Controls how seismic data is windowed, tapered, and transformed.

| Field | Type | Default | Range | Description |
|-------|------|---------|-------|-------------|
| `window_length` | float | **120.0** | 10–600 | Window duration in seconds (batch default is longer than single-station) |
| `overlap` | float | 0.0 | 0.0–1.0 | Overlap fraction between adjacent windows |
| `freq_min` | float | 0.2 | 0.01–10 | Lower frequency bound (Hz) |
| `freq_max` | float | 50.0 | 5–100 | Upper frequency bound (Hz) |
| `n_frequencies` | int | 200 | 50–2000 | Number of logarithmically-spaced frequency points |
| `smoothing_method` | string | `"konno_ohmachi"` | see below | Spectral smoothing algorithm |
| `smoothing_bandwidth` | float | 40.0 | 1–200 | Bandwidth parameter (meaning depends on method) |
| `horizontal_method` | string | `"geometric_mean"` | see below | How E and N components are combined |
| `taper` | string | `"tukey"` | see below | Window taper function |
| `detrend` | string | `"linear"` | see below | Detrend method applied before FFT |
| `statistics_method` | string | `"lognormal"` | `"lognormal"` / `"numpy"` | Statistical distribution for H/V curve |
| `std_ddof` | int | 1 | 0–1 | Delta degrees of freedom for standard deviation |

**Smoothing methods:**
- `konno_ohmachi` — Most common (bandwidth=40 recommended)
- `parzen` — Parzen window smoothing
- `none` — No smoothing

**Horizontal methods:**
- `geometric_mean` — sqrt(E × N), most common
- `quadratic_mean` — sqrt((E² + N²) / 2)
- `energy_density` — Energy-density approach
- `north` — North component only
- `east` — East component only

**Taper functions:**
- `tukey` — Tukey (cosine-tapered) window (default)
- `hann` — Hann window
- `hamming` — Hamming window
- `blackman` — Blackman window
- `none` — No tapering

**Detrend methods:**
- `linear` — Remove linear trend (default)
- `mean` — Remove mean only
- `none` — No detrending

---

### peaks (PeakSettings)

Controls automatic peak detection for each station.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `auto_mode` | bool | `true` | Enable automatic peak detection |
| `peak_basis` | string | `"median"` | Curve for peak detection: `"median"` or `"mean"` |
| `min_prominence` | float | **0.5** | Minimum peak prominence (batch default; more conservative than single-station) |
| `min_amplitude` | float | **2.0** | Minimum H/V amplitude to qualify as a peak |
| `n_peaks` | int | 3 | Maximum number of peaks to detect per station |
| `freq_tolerance` | float | 0.3 | Hz tolerance for cross-station peak matching |

---

### qc (QCSettings)

Quality-control configuration with 7 algorithms in two phases.

**Phase 1 — Pre-HVSR window rejection:**

Algorithms that reject raw time-domain windows before spectral computation.

#### STA/LTA (STALTAParams)

Detects transients by comparing short-term and long-term amplitude averages.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `stalta_enabled` | bool | `true` | Enable STA/LTA transient detection |
| `stalta.sta_length` | float | 1.0 | Short-term average window (seconds) |
| `stalta.lta_length` | float | 30.0 | Long-term average window (seconds) |
| `stalta.min_ratio` | float | 0.2 | Minimum STA/LTA ratio threshold |
| `stalta.max_ratio` | float | 2.5 | Maximum STA/LTA ratio threshold |

#### Amplitude (AmplitudeParams)

Checks for clipping and dead channels.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `amplitude_enabled` | bool | `true` | Enable amplitude / clipping check |
| `amplitude.preset` | string | `"moderate"` | Preset level: `"strict"`, `"moderate"`, `"lenient"` |
| `amplitude.max_amplitude` | float\|null | `null` | Absolute max amplitude; `null` = no limit |
| `amplitude.min_rms` | float | 1e-10 | Minimum RMS amplitude (rejects dead channels) |
| `amplitude.clipping_threshold` | float | 0.95 | Fraction of full-scale considered clipping (0–1) |
| `amplitude.clipping_max_percent` | float | 1.0 | Maximum percentage of clipped samples allowed |

#### Statistical Outlier (StatisticalOutlierParams)

Detects windows that deviate significantly from the population.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `statistical_enabled` | bool | `true` | Enable statistical outlier detection |
| `statistical.method` | string | `"mad"` | Detection method: `"mad"`, `"zscore"`, `"iqr"` |
| `statistical.threshold` | float | 3.0 | Deviation threshold (units depend on method) |
| `statistical.metric` | string | `"max_deviation"` | Metric used for outlier scoring |

**Phase 2 — Post-HVSR rejection:**

Algorithms that reject windows based on the computed H/V curves.

#### FDWRA (FDWRAParams)

Cox Frequency-Dependent Window Rejection Algorithm. Iteratively removes windows
whose individual H/V curves deviate from the median at each frequency.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `fdwra_enabled` | bool | `true` | Enable FDWRA |
| `fdwra.n` | float | 2.0 | Rejection threshold in standard deviations |
| `fdwra.max_iterations` | int | 50 | Maximum rejection passes |
| `fdwra.min_iterations` | int | 1 | Minimum passes before stopping |
| `fdwra.distribution_fn` | string | `"lognormal"` | Distribution for frequency-domain rejection |
| `fdwra.distribution_mc` | string | `"lognormal"` | Distribution for Monte Carlo rejection |

#### HVSR Amplitude (HVSRAmplitudeParams)

Rejects windows with H/V amplitudes outside a valid range.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `hvsr_amplitude_enabled` | bool | `false` | Enable post-HVSR amplitude check |
| `hvsr_amplitude.min_amplitude` | float | 1.0 | Minimum H/V amplitude to keep a window |
| `hvsr_amplitude.max_amplitude` | float | 15.0 | Maximum H/V amplitude to keep a window |

#### Flat Peak (FlatPeakParams)

Rejects windows with suspiciously flat HVSR peaks.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `flat_peak_enabled` | bool | `false` | Enable flat-peak rejection |
| `flat_peak.flatness_threshold` | float | 0.15 | Flatness threshold for peak rejection |

#### Curve Outlier (CurveOutlierParams)

Iteratively removes outlier H/V curves relative to the ensemble.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `curve_outlier_enabled` | bool | `true` | Enable curve outlier rejection |
| `curve_outlier.threshold` | float | 3.0 | Outlier threshold (standard deviations) |
| `curve_outlier.max_iterations` | int | 5 | Maximum rejection iterations |
| `curve_outlier.metric` | string | `"mean"` | Reference curve for comparison |

---

### output (OutputSettings)

Controls which files and figures are generated per station and combined.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `save_json` | bool | `true` | Save per-station results as JSON |
| `save_csv` | bool | `true` | Save per-station results as CSV |
| `save_mat` | bool | `true` | Save per-station results as MATLAB .mat |
| `save_png` | bool | `true` | Save per-station figures as PNG |
| `save_pdf` | bool | `false` | Save per-station figures as PDF |
| `figure_dpi` | int | 300 | DPI resolution for per-station figures |
| `generate_standard_figure` | bool | `true` | Generate the standard HVSR figure |
| `generate_hvsr_pro_figure` | bool | `true` | Generate the HV Pro detailed figure |
| `generate_statistics_figure` | bool | `true` | Generate the statistics figure |
| `export_excel` | bool | `true` | Export combined Excel workbook for all stations |
| `export_combined_mat` | bool | `true` | Export combined MATLAB .mat for all stations |
| `peak_font_size` | int | 10 | Font size for peak labels on figures |

---

### figure_export (FigureExportSettings)

Fine-grained control over the appearance and types of exported figures.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `dpi` | int | 300 | Image resolution |
| `format` | string | `"png"` | Image format: `"png"`, `"pdf"`, `"svg"` |
| `size_preset` | string | `"default"` | Figure size preset: `"default"` (10×6), `"compact"` (8×5), `"large"` (14×8) |
| `y_limit_method` | string | `"auto"` | Y-axis limit method: `"auto"`, `"fixed"`, `"percentile"` |
| `y_limit_value` | float\|null | `null` | Fixed upper Y-limit (used when `y_limit_method` is `"fixed"`) |
| `show_mean` | bool | `false` | Show mean curve on plots |
| `show_median` | bool | `true` | Show median curve on plots |
| `show_uncertainty` | bool | `true` | Show uncertainty band |
| `show_rejected` | bool | `false` | Show rejected window curves |
| `figure_types` | array | see below | List of figure types to generate |

**Default `figure_types`:**
- `hvsr_curve` — Main H/V spectral ratio curve
- `statistics` — Statistical summary plot
- `windows` — Individual window H/V curves
- `quality` — Quality metrics overview
- `dashboard` — Combined multi-panel dashboard
- `peak_analysis` — Peak detection detail
- `raw_vs_adjusted` — Raw vs. QC-adjusted comparison
- `waveform_rejection` — Waveform-level rejection detail
- `pre_post_rejection` — Before/after rejection comparison

---

### execution (ExecutionSettings)

Controls parallelism and data trimming for batch runs.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `max_parallel` | int | 4 | Number of parallel worker processes |
| `start_skip_minutes` | float | 0.0 | Skip N minutes from the start of each time window |
| `process_length_minutes` | float | 0.0 | Process only N minutes (0 = use full window) |
| `full_duration` | bool | `true` | Ignore time windows and use the entire file duration |
| `per_window_process_lengths` | object | `{}` | Per-window overrides: `{ "Window_1": 30.0 }` |

---

## Partial Config

You can provide only the sections or fields you want to change:

```json
{
  "processing": {
    "window_length": 60,
    "freq_max": 25
  },
  "peaks": {
    "min_amplitude": 1.5
  }
}
```

All other fields retain their current or default values.

## Key Differences from Single-Station Defaults

The batch config uses more conservative defaults than the standard single-station
analysis to improve reliability across multiple stations:

| Parameter | Single-Station | Batch |
|-----------|---------------|-------|
| `window_length` | 60 | **120** |
| `min_prominence` | 0.3 | **0.5** |
| `min_amplitude` | 1.0 | **2.0** |
| `statistical.method` | `"iqr"` | **`"mad"`** |
| `statistical.threshold` | 2.0 | **3.0** |
| `figure_dpi` / `dpi` | 150 | **300** |
