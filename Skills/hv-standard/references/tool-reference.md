# Tool Reference — hvsr-pro MCP Server

Complete parameter documentation for all 22 MCP tools.

---

## Data Loading

### load_seismic_data

Load a seismic data file for HVSR analysis.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `file_path` | string | **required** | Absolute path to seismic file. For multiple files, separate with `\|` |
| `format` | string | `"auto"` | Format hint: `auto`, `miniseed`, `saf`, `sac`, `gcf`, `txt`, `peer`, `minishark`, `srecord3c` |
| `degrees_from_north` | number | null | Sensor orientation offset (degrees) |
| `start_time` | string | null | Start of time window, ISO 8601 (local time) |
| `end_time` | string | null | End of time window, ISO 8601 (local time) |
| `timezone_offset` | integer | 0 | Hours offset from UTC. Examples: CDT=-5, CST=-6, CET=+1 |
| `session_id` | string | `"default"` | Session identifier for managing multiple analyses |

**Notes:**
- Times are interpreted as local time. The server converts to UTC internally.
- When loading multiple MiniSEED files, they are merged chronologically.
- Component lengths may differ slightly; the loader trims to the shortest.

---

## Configuration

### get_analysis_defaults

Returns the default `HVSRAnalysisConfig` as a JSON dict. No parameters.

### configure_analysis

Replace the full analysis configuration.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `config_json` | string | **required** | JSON string of `HVSRAnalysisConfig` (partial OK -- missing keys keep defaults) |
| `session_id` | string | `"default"` | Session identifier |

### set_processing_params

Adjust individual processing parameters without replacing the whole config.
Only provided parameters are changed.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `window_length` | number | null | Window length in seconds (e.g., 60, 120) |
| `overlap` | number | null | Overlap fraction 0.0-1.0 (e.g., 0.5 = 50%) |
| `freq_min` | number | null | Minimum frequency in Hz |
| `freq_max` | number | null | Maximum frequency in Hz |
| `n_frequencies` | integer | null | Number of frequency points (default: 200) |
| `smoothing_method` | string | null | `"konno_ohmachi"`, `"parzen"`, `"constant_bandwidth"`, `"proportional_bandwidth"` |
| `smoothing_bandwidth` | number | null | Smoothing bandwidth (40 for Konno-Ohmachi) |
| `horizontal_method` | string | null | `"geometric_mean"`, `"arithmetic_mean"`, `"quadratic_mean"`, `"ps_RotD50"`, `"maximum_horizontal"`, `"single_azimuth"` |
| `statistics_method` | string | null | `"lognormal"` (recommended) or `"normal"` |
| `peak_basis` | string | null | `"median"` (recommended) or `"mean"` |
| `min_prominence` | number | null | Minimum peak prominence |
| `min_amplitude` | number | null | Minimum H/V amplitude to consider a peak |
| `use_parallel` | boolean | null | Enable parallel processing |
| `n_cores` | integer | null | Number of CPU cores for parallel processing |
| `session_id` | string | `"default"` | Session identifier |

### validate_config

Validate a configuration without running it.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `config_json` | string | **required** | JSON string of config to validate |

Returns `{"valid": true}` or `{"valid": false, "errors": [...]}`.

### set_qc_params

Adjust quality-control parameters without replacing the whole config.
Only provided parameters are changed. Setting any algorithm-level parameter
automatically switches `mode` to `"custom"` (unless `mode` is explicitly set).

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `session_id` | string | `"default"` | Session identifier |
| `enabled` | boolean | null | Master QC switch |
| `mode` | string | null | `"sesame"` or `"custom"` |
| `phase1_enabled` | boolean | null | Enable/disable pre-HVSR rejection |
| `phase2_enabled` | boolean | null | Enable/disable post-HVSR rejection |
| `sta_lta_enabled` | boolean | null | Enable STA/LTA transient detection |
| `sta_length` | number | null | STA window length (seconds) |
| `lta_length` | number | null | LTA window length (seconds) |
| `sta_lta_min_ratio` | number | null | Min STA/LTA ratio threshold |
| `sta_lta_max_ratio` | number | null | Max STA/LTA ratio threshold |
| `amplitude_enabled` | boolean | null | Enable amplitude/clipping check |
| `clipping_threshold` | number | null | Fraction of full-scale considered clipping (0-1) |
| `min_rms` | number | null | Minimum RMS amplitude |
| `statistical_outlier_enabled` | boolean | null | Enable statistical outlier detection |
| `statistical_outlier_method` | string | null | `"iqr"` or `"zscore"` |
| `statistical_outlier_threshold` | number | null | Deviation threshold |
| `frequency_domain_enabled` | boolean | null | Enable spectral spike detection |
| `spike_threshold` | number | null | Spectral spike threshold (std devs) |
| `curve_outlier_enabled` | boolean | null | Enable post-HVSR curve outlier rejection |
| `curve_outlier_threshold` | number | null | Outlier threshold (std devs) |
| `curve_outlier_max_iterations` | integer | null | Max rejection iterations |
| `hvsr_amplitude_enabled` | boolean | null | Enable post-HVSR amplitude check |
| `hvsr_amplitude_min` | number | null | Min H/V amplitude to keep a window |
| `flat_peak_enabled` | boolean | null | Enable flat-peak rejection |
| `flatness_threshold` | number | null | Flatness threshold |

### set_fdwra_params

Adjust Cox FDWRA (Frequency-Dependent Window Rejection) parameters.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `session_id` | string | `"default"` | Session identifier |
| `enabled` | boolean | null | Enable/disable FDWRA entirely |
| `n` | number | null | Rejection threshold in std devs (default: 2.0) |
| `max_iterations` | integer | null | Max rejection passes (default: 50) |
| `min_iterations` | integer | null | Min passes before stopping (default: 1) |
| `distribution` | string | null | `"lognormal"` or `"normal"` |

---

## Analysis

### run_hvsr_analysis

Run the complete HVSR processing pipeline. No parameters except `session_id`.

Pipeline stages:
1. **Windowing** -- split data into overlapping time windows
2. **Phase 1 QC** -- reject noisy windows (STA/LTA, zero-crossing, amplitude)
3. **HVSR computation** -- FFT, smoothing, horizontal combination, H/V ratio
4. **Cox FDWRA** -- Frequency-Dependent Window Rejection Algorithm
5. **Post-HVSR QC** -- additional quality checks on H/V curves

### run_azimuthal_analysis

Run azimuthal HVSR analysis. Requires `run_hvsr_analysis` first.
Computes HVSR at multiple azimuths (0-180 degrees) to detect directional effects.

---

## Peak Detection

### detect_peaks

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `session_id` | string | `"default"` | Session identifier |
| `mode` | string | `"auto_multi"` | Detection mode (see below) |
| `n_peaks` | integer | 3 | Number of peaks for `auto_top_n` mode |
| `min_prominence` | number | 0.3 | Minimum peak prominence |
| `min_amplitude` | number | 1.0 | Minimum H/V amplitude |
| `use_median` | boolean | true | Use median curve (recommended) |

**Modes:**
- `auto_multi` -- All peaks above `min_prominence` and `min_amplitude`
- `auto_primary` -- Single highest-amplitude peak
- `auto_top_n` -- Top N peaks ranked by prominence

---

## Results & Export

### get_analysis_results

Get full summary of last analysis. Only parameter: `session_id`.

### export_results

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `output_path` | string | **required** | Absolute path for output file |
| `format` | string | `"json"` | `"json"`, `"csv"`, or `"mat"` |
| `session_id` | string | `"default"` | Session identifier |

### export_plot

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `output_path` | string | **required** | Absolute path for image file |
| `plot_type` | string | `"hvsr"` | See `plot-types.md` for all 15 types |
| `dpi` | integer | 150 | Image resolution |
| `session_id` | string | `"default"` | Session identifier |

### generate_report

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `output_dir` | string | **required** | Absolute path for report directory |
| `base_name` | string | `"hvsr"` | Prefix for data file names |
| `dpi` | integer | 150 | Plot resolution |
| `session_id` | string | `"default"` | Session identifier |

**Output files (up to 21):**
- 6 data files: `{base}_curve_complete.csv`, `{base}_for_inversion.txt`, `{base}_peaks.csv`, `{base}_metadata.json`, `{base}_summary.json`, `analysis_config.json`
- 15 plot files: see `plot-types.md`

---

## Plot Styling

### configure_plot_style

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `dpi` | integer | null | Image resolution |
| `title_fontsize` | integer | null | Title font size |
| `axis_fontsize` | integer | null | Axis label font size |
| `legend_fontsize` | integer | null | Legend font size |
| `show_median` | boolean | null | Show median H/V curve |
| `show_mean` | boolean | null | Show mean H/V curve |
| `show_uncertainty` | boolean | null | Show confidence interval |
| `uncertainty_type` | string | null | `"percentile"` or `"std"` |
| `show_rejected_windows` | boolean | null | Show rejected windows in plots |
| `rejected_color` | string | null | Color for rejected windows (hex) |
| `rejected_alpha` | number | null | Opacity of rejected window lines |
| `rejected_linewidth` | number | null | Line width for rejected windows |
| `figure_format` | string | null | `"png"`, `"pdf"`, `"svg"` |
| `session_id` | string | `"default"` | Session identifier |

---

## Session Management

### save_session

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `session_dir` | string | **required** | Absolute path for session directory |
| `session_id` | string | `"default"` | Session identifier |

### load_session

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `session_dir` | string | **required** | Absolute path to saved session |
| `session_id` | string | `"default"` | Session identifier |

---

## Discovery Tools

These tools take no parameters (except implicit defaults) and return
reference information:

| Tool | Returns |
|------|---------|
| `list_formats` | Supported file formats with extensions and descriptions |
| `list_smoothing_methods` | Available smoothing methods with default bandwidths |
| `list_qc_presets` | QC preset names (e.g., SESAME) |
| `list_qc_algorithms` | All QC rejection algorithms with tunable parameters |
| `list_horizontal_methods` | Horizontal component combination methods |