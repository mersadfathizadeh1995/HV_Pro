---
name: hv-standard
description: >-
  Perform HVSR (Horizontal-to-Vertical Spectral Ratio) seismic analysis using
  the hvsr-pro MCP server. Use when the user asks to analyze seismic data,
  find site resonance frequency, compute H/V ratios, run HVSR, detect peaks,
  generate HVSR reports, or process ambient vibration recordings. Supports
  MiniSEED, SAC, SAF, GCF, TXT, and other seismic formats. Produces annotated
  H/V curves, QC dashboards, waveform rejection overlays, and 21-file reports.
  Keywords: HVSR, seismic, site response, resonance frequency, microzonation,
  ambient vibration, H/V ratio, bedrock depth, f0, fundamental frequency.
metadata:
  author: HV-Pro-Team
  version: '1.0'
  mcp-server: hvsr-pro
---

# HVSR Standard Analysis

Perform Horizontal-to-Vertical Spectral Ratio (HVSR) analysis on 3-component
seismic recordings to identify site resonance frequencies using the `hvsr-pro`
MCP server.

## When to Use This Skill

Use this skill when the user asks you to:

- Analyze seismic ambient vibration data
- Find the fundamental site frequency (f0) or resonance frequency
- Compute H/V spectral ratios from 3-component recordings
- Run HVSR processing on MiniSEED, SAC, TXT, or other seismic files
- Detect peaks on an H/V curve
- Generate HVSR analysis reports with plots
- Perform quality control on seismic windows
- Compare pre-QC vs post-QC HVSR results
- Process multiple seismic stations (batch HVSR)

## Instructions

### Step 1: Load Seismic Data

Call `load_seismic_data` with the file path and optional time range.

```
load_seismic_data(
    file_path="<absolute path to seismic file>",
    start_time="2026-04-01T10:00:00",   # local time, ISO 8601
    end_time="2026-04-01T11:00:00",
    timezone_offset=-5                    # hours from UTC (CDT=-5, CET=+1)
)
```

**Key rules:**
- Always use **absolute paths**.
- Times are interpreted as **local time**; set `timezone_offset` accordingly.
- For multiple MiniSEED files, join with `|`:
  `file_path="file1.miniseed|file2.miniseed"`
- If you get a "time outside data bounds" error, **narrow the range by 1-2
  minutes** on each end.

### Step 2: Configure Processing Parameters

Call `set_processing_params` to adjust analysis settings. Only provide the
parameters you want to change; the rest keep their defaults.

```
set_processing_params(
    window_length=120,       # seconds (default: 60)
    freq_min=0.2,            # Hz (default: 0.2)
    freq_max=50              # Hz (default: 50)
)
```

**Recommended defaults** (SESAME standard):
- `window_length`: 60-120 s
- `overlap`: 0.0 (no overlap)
- `freq_max`: 50 Hz
- `n_frequencies`: 200
- `smoothing_method`: "konno_ohmachi", `smoothing_bandwidth`: 40
- `horizontal_method`: "geometric_mean"
- `statistics_method`: "lognormal"
- `peak_basis`: "median"

### Step 2b (Optional): Tune Quality Control

Call `set_qc_params` to adjust individual QC algorithms. Setting any
algorithm-level parameter automatically switches to "custom" mode.

```
set_qc_params(
    sta_lta_max_ratio=3.0,         # loosen STA/LTA
    frequency_domain_enabled=True,  # enable spectral spike detection
    spike_threshold=2.5
)
```

### Step 2c (Optional): Tune FDWRA

Call `set_fdwra_params` to enable/disable or adjust Cox FDWRA.

```
set_fdwra_params(enabled=True, n=1.5, distribution="lognormal")
```

### Step 3: Run HVSR Analysis

```
run_hvsr_analysis()
```

This executes the full pipeline: windowing, Phase 1 QC, HVSR computation,
Cox FDWRA, Post-HVSR QC. Check the response for:
- `windows.total` / `windows.active` -- how many windows survived QC
- `result.primary_peak` -- the dominant peak frequency and amplitude
- `qc` details -- which algorithms rejected how many windows

**Acceptance rate guidance:**
- Greater than 60%: Good data
- 40-60%: Acceptable
- Less than 40%: Noisy; consider adjusting QC or re-recording

### Step 3b (Optional): Azimuthal Analysis

Call `run_azimuthal_analysis` to compute HVSR at multiple azimuths
(0–180°) and detect directional site effects.

```
run_azimuthal_analysis()
```

Must be called **after** `run_hvsr_analysis`. Returns azimuth count,
mean/std of f0 across azimuths.

### Step 4: Detect Peaks

```
detect_peaks(mode="auto_multi", min_prominence=0.3, min_amplitude=1.0)
```

Modes:
- `auto_multi` -- all peaks above threshold (recommended)
- `auto_primary` -- single highest peak only
- `auto_top_n` -- top N peaks by prominence

Must be called **after** `run_hvsr_analysis`.

### Step 5: Export Results

**Option A -- Full report (recommended):**
```
generate_report(
    output_dir="<absolute path to output directory>",
    base_name="STN01",
    dpi=200
)
```
Generates up to 21 files: 6 data exports + 15 plots.

**Option B -- Single plot:**
```
export_plot(output_path="<path>.png", plot_type="hvsr", dpi=200)
```

**Option C -- Data only:**
```
export_results(output_path="<path>.json", format="json")
```

See `references/plot-types.md` for all 15 available plot types.

### Optional: Inspect Results Programmatically

```
get_analysis_results()
```

Returns the full analysis summary (peak frequencies, window counts, QC
breakdown) without exporting to a file. Useful for multi-step workflows.

### Optional: Validate Configuration

```
validate_config(config_json='{"processing": {"window_length": 120}}')
```

Returns `{"valid": true}` or `{"valid": false, "errors": [...]}`.
Use before `run_hvsr_analysis` to catch config errors early.

### Optional: Replace Full Configuration (Advanced)

```
configure_analysis(config_json='{"processing": {...}, "qc": {...}}')
```

Replaces the entire analysis config at once. Partial JSON is accepted
(missing keys keep defaults). Prefer `set_processing_params` /
`set_qc_params` for individual tweaks.

### Batch Processing (Multiple Stations)

Use different `session_id` values for each station:

```
load_seismic_data(file_path="...", session_id="stn01", ...)
set_processing_params(session_id="stn01", window_length=120, ...)
run_hvsr_analysis(session_id="stn01")
detect_peaks(session_id="stn01", mode="auto_multi")
generate_report(session_id="stn01", output_dir="...", base_name="STN01")
```

Sessions are fully isolated -- each has its own data, config, and results.

### Optional: Customize Plot Appearance

```
configure_plot_style(dpi=200, show_mean=True, figure_format="pdf")
```

### Optional: Save / Restore Sessions

```
save_session(session_dir="<path>")    # persist state to disk
load_session(session_dir="<path>")    # restore later
```

## Interpreting Results

- **Primary Peak (f0):** The fundamental resonance frequency. Higher amplitude
  = stronger impedance contrast between soil and bedrock.
- **Peak amplitude >= 2:** Generally considered a reliable, clear peak.
- **Multiple peaks:** May indicate layered subsurface (e.g., soil over
  weathered rock over bedrock).

## Troubleshooting

| Error | Fix |
|-------|-----|
| Start time is before data start | Narrow time range by 1-2 min on each end |
| End time exceeds data duration | Move end_time earlier |
| No windows passed QC | Loosen QC via configure_analysis |
| No results to plot | Run run_hvsr_analysis first |
| Unknown plot type | Check plot-types.md for requirements |
| Very low acceptance rate | Check Phase 1 breakdown; consider custom QC |

## Examples

### Minimal Single-Station Analysis

```
load_seismic_data(file_path="/data/STN01.miniseed")
run_hvsr_analysis()
detect_peaks(mode="auto_primary")
export_results(output_path="/output/STN01_results.json")
```

### Full Analysis with Custom Config

```
load_seismic_data(
    file_path="/data/STN01.miniseed",
    start_time="2026-04-01T10:00:00",
    end_time="2026-04-01T11:00:00",
    timezone_offset=-5
)
set_processing_params(
    window_length=120,
    overlap=0.0,
    freq_min=0.2,
    freq_max=50,
    smoothing_method="konno_ohmachi",
    smoothing_bandwidth=40,
    statistics_method="lognormal",
    peak_basis="median",
    n_frequencies=200
)
run_hvsr_analysis()
detect_peaks(mode="auto_multi", min_prominence=0.3, min_amplitude=1.0)
configure_plot_style(dpi=200, show_median=True, show_mean=False)
generate_report(output_dir="/output/STN01", base_name="STN01", dpi=200)
```

## Available MCP Tools (Summary)

| Tool | Purpose |
|------|---------|
| `list_formats` | List supported seismic file formats |
| `list_smoothing_methods` | List spectral smoothing methods |
| `list_qc_presets` | List QC presets (e.g., SESAME) |
| `list_qc_algorithms` | List all QC rejection algorithms |
| `list_horizontal_methods` | List horizontal combination methods |
| `get_analysis_defaults` | Get default config as JSON |
| `load_seismic_data` | Load a seismic data file |
| `configure_analysis` | Replace full analysis config |
| `set_processing_params` | Adjust individual parameters |
| `set_qc_params` | Tune QC algorithms (auto-switches to custom mode) |
| `set_fdwra_params` | Tune Cox FDWRA parameters |
| `run_hvsr_analysis` | Run the full processing pipeline |
| `run_azimuthal_analysis` | Run azimuthal HVSR |
| `detect_peaks` | Detect peaks on HVSR curve |
| `get_analysis_results` | Get full result summary |
| `export_results` | Save results (JSON, CSV, MAT) |
| `export_plot` | Save a single plot |
| `generate_report` | Generate full report (20 files) |
| `configure_plot_style` | Customize plot appearance |
| `save_session` | Persist session to disk |
| `load_session` | Restore saved session |
| `validate_config` | Validate config JSON |

See `references/tool-reference.md` for full parameter details.
See `references/plot-types.md` for all 15 plot types with descriptions.
See `references/config-reference.md` for the complete config JSON structure.
See `references/qc-pipeline.md` for QC algorithm details.