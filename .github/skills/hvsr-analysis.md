# Skill: HVSR Seismic Analysis

> **MCP Server:** `hvsr-pro`
> **Purpose:** Perform Horizontal-to-Vertical Spectral Ratio (HVSR) analysis on
> ambient-vibration seismic recordings to identify site resonance frequencies.

---

## 1. Overview

HVSR Pro is a seismic microzonation tool. Given a 3-component (East, North,
Vertical) seismic recording, it:

1. Loads the raw data (many formats supported)
2. Optionally slices to a user-specified time window
3. Splits the record into overlapping time windows
4. Applies multi-stage quality control (QC) to reject noisy windows
5. Computes the H/V spectral ratio for each surviving window
6. Aggregates statistics (lognormal median ± percentiles)
7. Detects resonance peaks on the median H/V curve
8. Exports results (data files, plots, full reports)

The primary output is the **fundamental site frequency (f₀)** — the frequency
where the H/V ratio peaks — which indicates the resonance frequency of the
soil column above bedrock.

---

## 2. Standard Workflow

Every HVSR analysis follows this sequence. **Call the tools in this order.**

```
1. load_seismic_data     — load file(s), set time range & timezone
2. set_processing_params — configure window length, freq range, etc.
3. run_hvsr_analysis     — compute H/V spectra + QC
4. detect_peaks          — find resonance peaks on the H/V curve
5. generate_report       — export all data files + 15 plot types
   (or use export_results / export_plot for individual outputs)
```

### 2.1 Minimal Example

```
load_seismic_data(
    file_path="D:\\data\\station01.miniseed",
    start_time="2026-04-01T10:00:00",
    end_time="2026-04-01T11:00:00",
    timezone_offset=-5          # CDT = UTC-5
)
set_processing_params(window_length=120, freq_min=0.2, freq_max=50)
run_hvsr_analysis()
detect_peaks(mode="auto_multi")
generate_report(output_dir="D:\\data\\station01_report", base_name="STN01")
```

### 2.2 Important Notes

- **Time range:** Data internally uses UTC. If the user gives local time, set
  `timezone_offset` (e.g., CDT = -5, CET = +1, JST = +9). The start/end
  strings are interpreted as local time and converted internally.
- **Time range edge case:** The requested range must fit inside the actual data.
  If you get a "time too early/late" error, narrow the range by ~1-2 minutes
  on each end (the file may not cover the exact requested boundary).
- **Multiple MiniSEED files:** Separate paths with `|`:
  `file_path="file1.miniseed|file2.miniseed|file3.miniseed"`
- **Session isolation:** Use `session_id` to run multiple analyses in parallel
  without interference. Each session maintains its own data/config/result state.

---

## 3. Tool Reference

### 3.1 Introspection Tools (read-only, no session needed)

| Tool | Description |
|------|-------------|
| `list_formats()` | Supported seismic file formats (txt, miniseed, saf, sac, gcf, peer, minishark, json) |
| `list_smoothing_methods()` | Spectral smoothing options with default bandwidths |
| `list_horizontal_methods()` | H-component combination methods (geometric_mean, arithmetic_mean, quadratic, maximum) |
| `list_qc_presets()` | QC presets (currently: sesame) |
| `list_qc_algorithms()` | Every QC algorithm with tunable parameters |
| `get_analysis_defaults()` | Full default config as JSON |

### 3.2 Data Loading

#### `load_seismic_data`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `file_path` | str | *required* | Absolute path (use `\|` to join multiple files) |
| `format` | str | `"auto"` | Format hint: `auto`, `miniseed`, `saf`, `sac`, `gcf`, `peer`, `txt`, `minishark`, `srecord3c` |
| `degrees_from_north` | float? | None | Sensor orientation (0–360°) |
| `start_time` | str? | None | ISO 8601 local time (e.g., `2026-04-01T10:00:00`) |
| `end_time` | str? | None | ISO 8601 local time |
| `timezone_offset` | int | 0 | Hours from UTC (e.g., -5 for CDT, +1 for CET) |
| `session_id` | str | `"default"` | Session identifier |

**Returns:** summary dict with `duration_seconds`, `sampling_rate`, `n_samples`, `start_time`.

### 3.3 Configuration

#### `set_processing_params` (recommended — set individual params)

| Parameter | Type | Default | Valid Values |
|-----------|------|---------|--------------|
| `window_length` | float | 60 | 1–600 seconds |
| `overlap` | float | 0.5 | 0.0–0.99 |
| `smoothing_method` | str | `"konno_ohmachi"` | `konno_ohmachi`, `parzen`, `savitzky_golay`, `linear_rectangular`, `log_rectangular`, `linear_triangular`, `log_triangular`, `none` |
| `smoothing_bandwidth` | float | 40 | Depends on method (KO: 1–200, Parzen: 0.01–10) |
| `horizontal_method` | str | `"geometric_mean"` | `geometric_mean`, `arithmetic_mean`, `quadratic`, `maximum` |
| `freq_min` | float | 0.2 | > 0, in Hz |
| `freq_max` | float | 20 | > freq_min, in Hz |
| `n_frequencies` | int | 300 | ≥ 10 |
| `statistics_method` | str | `"lognormal"` | `lognormal`, `normal` |
| `peak_basis` | str | `"median"` | `median`, `mean` |
| `min_prominence` | float | 0.3 | ≥ 0 (lower = more peaks) |
| `min_amplitude` | float | 1.0 | ≥ 0 (minimum H/V ratio for a peak) |
| `use_parallel` | bool | False | Enable multi-core processing |
| `n_cores` | int? | None | Number of cores (None = auto) |

Only parameters you explicitly provide are changed; others keep current values.

#### `configure_analysis` (advanced — replace full config as JSON)

Pass a JSON string representing the full `HVSRAnalysisConfig`. Missing keys
keep their defaults. Use `get_analysis_defaults()` to see the structure first.

#### `configure_plot_style` (optional — customize figure appearance)

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `dpi` | int | 150 | Image resolution |
| `title_fontsize` | int | 12 | Title font size |
| `axis_fontsize` | int | 11 | Axis label font size |
| `legend_fontsize` | int | 10 | Legend font size |
| `show_median` | bool | True | Show median H/V curve |
| `show_mean` | bool | False | Show mean H/V curve |
| `show_uncertainty` | bool | True | Show uncertainty band |
| `uncertainty_type` | str | `"percentile"` | `percentile` (16th–84th) or `std` |
| `show_rejected_windows` | bool | False | Overlay rejected windows |
| `rejected_color` | str | `"#808080"` | Color for rejected window lines |
| `rejected_alpha` | float | 0.3 | Transparency |
| `rejected_linewidth` | float | 0.5 | Line width |
| `figure_format` | str | `"png"` | `png`, `pdf`, `svg` |

### 3.4 Processing

#### `run_hvsr_analysis`

No parameters needed (uses loaded data + current config). Returns:

```json
{
  "success": true,
  "summary": {
    "windows": { "total": 57, "active": 23, "acceptance_rate": 0.40 },
    "result": {
      "primary_peak": { "frequency": 0.98, "amplitude": 3.92 }
    },
    "qc": {
      "phase1_detail": "QC: 23/57 windows active ...",
      "fdwra_detail": "Cox FDWRA: 0 rejected, converged in 1 iterations",
      "post_hvsr_detail": "Post-HVSR: 0 rejected, 23 remaining"
    }
  }
}
```

#### `run_azimuthal_analysis`

Requires a prior `run_hvsr_analysis`. Computes HVSR at multiple azimuths to
detect directional site effects. Returns `mean_fn_frequency`, `std_fn_frequency`.

### 3.5 Peak Detection

#### `detect_peaks`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `mode` | str | `"auto_multi"` | `auto_primary` (1 peak), `auto_top_n` (top N), `auto_multi` (all above threshold) |
| `n_peaks` | int | 3 | How many peaks for `auto_top_n` mode |
| `min_prominence` | float | 0.3 | Minimum prominence (lower = more sensitive) |
| `min_amplitude` | float | 1.0 | Minimum H/V ratio to qualify as a peak |
| `use_median` | bool | True | Detect peaks on median curve (recommended) |

**Must be called after `run_hvsr_analysis`.**

Returns a list of peaks, each with `frequency`, `amplitude`, `prominence`.

### 3.6 Export

#### `export_results` — save data to file

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `output_path` | str | *required* | Absolute file path |
| `format` | str | `"json"` | `json`, `csv`, `mat` |

#### `export_plot` — save a single figure

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `output_path` | str | *required* | Absolute file path (.png) |
| `plot_type` | str | `"hvsr"` | See **Plot Types** below |
| `dpi` | int | 150 | Resolution |

#### `generate_report` — create complete report directory

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `output_dir` | str | *required* | Absolute directory path |
| `base_name` | str | `"hvsr"` | Prefix for data file names |
| `dpi` | int | 150 | Resolution for all plots |

Generates up to **20 files** (5 data + 15 plots).

### 3.7 Session Management

| Tool | Description |
|------|-------------|
| `save_session(session_dir)` | Persist full state (config + data + results) to disk |
| `load_session(session_dir)` | Restore a saved session (can be from GUI or MCP) |
| `validate_config(config_json)` | Check a config for errors without running anything |

---

## 4. Available Plot Types

| Plot Type | Description | Requires |
|-----------|-------------|----------|
| `hvsr` | Main H/V curve with peaks annotated | result |
| `windows` | H/V curve with individual window curves | result + window_spectra |
| `quality` | Quality metrics grid for all windows | windows |
| `statistics` | 4-panel statistical dashboard | result |
| `dashboard` | Complete multi-panel dashboard | result + windows |
| `mean_vs_median` | Mean vs median H/V comparison | result |
| `quality_histogram` | Quality score distribution | windows |
| `selected_metrics` | Key QC metrics comparison | windows |
| `window_timeline` | Window acceptance/rejection timeline | windows |
| `window_timeseries` | Sample window waveforms | windows + data |
| `window_spectrogram` | Sample window spectrograms | windows + data |
| `peak_analysis` | Detailed peak analysis panel | result + primary_peak |
| `raw_vs_adjusted` | Pre-QC vs post-QC H/V comparison | raw_result |
| `waveform_rejection` | 3C waveform with window rejection overlay | windows + data |
| `pre_post_rejection` | 5-panel composite (waveforms + pre/post H/V) | all |

---

## 5. Quality Control Pipeline

The QC pipeline runs automatically inside `run_hvsr_analysis`. Three stages:

### Phase 1 — Pre-HVSR (window-level rejection)

Applied before computing H/V ratios. Default-enabled algorithms:

| Algorithm | Default | What it catches |
|-----------|---------|-----------------|
| **Amplitude** | ✅ ON | Clipping, dead channels, extreme amplitudes |
| **STA/LTA** | ✅ ON | Transients (impacts, footsteps, traffic) |
| Quality Threshold | ❌ OFF | Low composite quality score |
| Frequency Domain | ❌ OFF | Narrow-band spectral spikes |
| Statistical Outlier | ❌ OFF | Windows that are statistical outliers |

### Phase 2 — Cox FDWRA (peak consistency)

| Parameter | Default | Description |
|-----------|---------|-------------|
| Enabled | ✅ ON | Cox et al. (2020) peak-frequency consistency |
| n | 2.0 | Std-dev multiplier |
| distribution | lognormal | Assumed frequency distribution |
| max_iterations | 50 | Convergence limit |

Iteratively removes windows whose peak frequency deviates from the group.

### Phase 3 — Post-HVSR (curve-level rejection)

| Algorithm | Default | What it catches |
|-----------|---------|-----------------|
| **Curve Outlier** | ✅ ON | Windows with anomalous H/V curve shape |
| HVSR Amplitude | ❌ OFF | Windows where peak H/V < threshold |
| Flat Peak | ❌ OFF | Windows with non-distinct (flat) peaks |

### Customizing QC

Use `configure_analysis` with a full QC config to enable/disable algorithms
or change their parameters:

```
configure_analysis(config_json='{
  "qc": {
    "enabled": true,
    "mode": "sesame",
    "algorithms": {
      "sta_lta": { "enabled": true, "params": { "max_ratio": 3.0 } },
      "frequency_domain": { "enabled": true, "params": { "spike_threshold": 2.5 } }
    },
    "cox_fdwra": { "enabled": true, "n": 1.5 }
  }
}')
```

---

## 6. Supported File Formats

| Format | Extensions | Multi-file | Notes |
|--------|-----------|------------|-------|
| ASCII Text (OSCAR) | `.txt`, `.dat`, `.asc` | No | 4 columns: Time, E, N, Z |
| MiniSEED | `.mseed`, `.miniseed`, `.ms` | Optional | Standard seismic (ObsPy). Join with `\|` |
| SESAME ASCII | `.saf` | No | SESAME project standard |
| SAC | `.sac` | Yes (3 files) | Separate E, N, Z component files |
| Guralp GCF | `.gcf` | No | Compressed format |
| PEER NGA | `.vt2`, `.at2`, `.dt2` | Yes (3 files) | Ground motion database format |
| MiniShark | `.minishark` | No | MiniShark seismometer |
| SeismicRecording3C | `.json` | No | hvsrpy JSON serialization |

---

## 7. Recommended Parameter Choices

### For typical ambient vibration surveys:
- **Window length:** 60–120 seconds (longer = more stable, but fewer windows)
- **Overlap:** 0.5 (50%)
- **Smoothing:** Konno-Ohmachi with bandwidth 40 (SESAME standard)
- **Horizontal method:** geometric_mean (SESAME recommended)
- **Frequency range:** 0.2–50 Hz (adjust to needs)
- **Statistics:** lognormal (always preferred over arithmetic)
- **Peak basis:** median (more robust than mean)

### For noisy urban sites:
- Increase `window_length` to 120–180 s
- Enable `frequency_domain` QC with `spike_threshold: 2.5`
- Consider enabling `statistical_outlier` QC

### For short recordings (< 20 min):
- Reduce `window_length` to 30–60 s
- Use `overlap: 0.75` to maximize window count
- Be cautious: fewer windows = less stable statistics

---

## 8. Interpreting Results

### Primary Peak (f₀)
- **Frequency:** The fundamental resonance frequency of the site
- **Amplitude:** Higher amplitude = stronger impedance contrast (bedrock vs soil)
- **Rule of thumb:** A clear peak with amplitude ≥ 2 is considered reliable

### Window Acceptance Rate
- **> 60%:** Good data quality
- **40–60%:** Acceptable, check if QC is too aggressive
- **< 40%:** Poor data quality or very noisy site; consider re-recording

### QC Summary
- **Phase 1 rejections:** Usually amplitude (clipping) and STA/LTA (transients)
- **FDWRA rejections:** Windows with inconsistent peak frequency
- **Post-HVSR rejections:** Windows with anomalous curve shape

---

## 9. Advanced: Full Config JSON Structure

```json
{
  "processing": {
    "window_length": 60,
    "overlap": 0.5,
    "smoothing_method": "konno_ohmachi",
    "smoothing_bandwidth": 40,
    "horizontal_method": "geometric_mean",
    "freq_min": 0.2,
    "freq_max": 20,
    "n_frequencies": 300,
    "manual_sampling_rate": null,
    "use_parallel": false,
    "n_cores": null,
    "statistics_method": "lognormal",
    "peak_basis": "median",
    "min_prominence": 0.3,
    "min_amplitude": 1
  },
  "time_range": {
    "enabled": false,
    "start": null,
    "end": null,
    "timezone_offset": 0,
    "timezone_name": null
  },
  "qc": {
    "enabled": true,
    "mode": "sesame",
    "phase1_enabled": true,
    "phase2_enabled": true,
    "algorithms": {
      "amplitude":           { "enabled": true,  "params": { "max_amplitude": null, "min_rms": 1e-10, "clipping_threshold": 0.95 } },
      "quality_threshold":   { "enabled": false, "params": { "threshold": 0.5 } },
      "sta_lta":             { "enabled": true,  "params": { "sta_length": 1, "lta_length": 30, "min_ratio": 0.2, "max_ratio": 2.5 } },
      "frequency_domain":    { "enabled": false, "params": { "spike_threshold": 3 } },
      "statistical_outlier": { "enabled": false, "params": { "method": "iqr", "threshold": 2 } },
      "hvsr_amplitude":      { "enabled": false, "params": { "min_amplitude": 1 } },
      "flat_peak":           { "enabled": false, "params": { "flatness_threshold": 0.15 } },
      "curve_outlier":       { "enabled": true,  "params": { "threshold": 3, "max_iterations": 5, "metric": "mean" } }
    },
    "cox_fdwra": {
      "enabled": true,
      "n": 2,
      "max_iterations": 50,
      "min_iterations": 1,
      "distribution": "lognormal"
    }
  },
  "plot_style": {
    "dpi": 150,
    "title_fontsize": 12,
    "axis_fontsize": 11,
    "legend_fontsize": 10,
    "show_median": true,
    "show_mean": false,
    "show_uncertainty": true,
    "uncertainty_type": "percentile",
    "show_rejected_windows": false,
    "rejected_color": "#808080",
    "rejected_alpha": 0.3,
    "rejected_linewidth": 0.5,
    "figure_format": "png"
  }
}
```

---

## 10. Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| "Start time is before data start" | Time range extends beyond recorded data | Narrow the range by 1-2 minutes |
| "End time exceeds data duration" | Same as above, on the end side | Move `end_time` earlier |
| "No windows passed QC (0/N)" | All windows failed quality checks | Loosen QC: disable `sta_lta` or raise `max_ratio` |
| "No results to plot" | `run_hvsr_analysis` not called yet | Run analysis before exporting |
| "Unknown plot type: X" | Plot needs data that wasn't computed | Check the "Requires" column in §4 |
| Low acceptance rate (< 30%) | Very noisy data or over-aggressive QC | Check Phase 1 breakdown; consider custom QC settings |

---

## 11. Batch Processing Workflow

To analyze multiple stations, use different `session_id` values:

```
# Station 1
load_seismic_data(file_path="...", session_id="stn01", ...)
set_processing_params(session_id="stn01", window_length=120, ...)
run_hvsr_analysis(session_id="stn01")
detect_peaks(session_id="stn01", mode="auto_multi")
generate_report(session_id="stn01", output_dir="...", base_name="STN01")

# Station 2 (can run independently)
load_seismic_data(file_path="...", session_id="stn02", ...)
# ... same sequence ...
```

Each session is fully isolated — different configs, data, and results.
