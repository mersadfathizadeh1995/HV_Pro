# Batch HVSR Figure Types Reference

All figure types available via `list_figure_types`, `export_figures`,
and `generate_batch_report` in the batch processing MCP server.

## Figure Types Overview

### Per-Station Figures (15 types)

Generated individually for each station in the batch.

| # | figure_type | Description | Requires |
|---|-------------|-------------|----------|
| 1 | `hvsr_curve` | Main H/V spectral ratio curve with peaks annotated | Analysis |
| 2 | `hvsr_statistics` | H/V curve with statistical uncertainty bands (percentiles) | Analysis |
| 3 | `hvsr_with_windows` | Individual window H/V curves overlaid with median | Analysis |
| 4 | `quality_metrics` | QC metrics summary for each window | Analysis |
| 5 | `window_timeline` | Timeline showing accepted/rejected windows | Analysis |
| 6 | `peak_analysis` | Detailed peak analysis with prominence and amplitude | Analysis + Peaks |
| 7 | `complete_dashboard` | Multi-panel dashboard combining key views | Analysis |
| 8 | `mean_vs_median` | Comparison of arithmetic mean vs lognormal median H/V | Analysis |
| 9 | `quality_histogram` | Histogram of QC metric distributions | Analysis |
| 10 | `selected_metrics` | Selected QC metrics display | Analysis |
| 11 | `window_timeseries` | Raw waveform timeseries per window | Analysis + Data |
| 12 | `window_spectrogram` | Spectrogram of the seismic data | Analysis + Data |
| 13 | `raw_vs_adjusted` | Pre-QC vs post-QC H/V comparison | Analysis (auto) |
| 14 | `waveform_rejection` | Overlay of accepted vs rejected waveforms | Analysis + Data |
| 15 | `pre_post_rejection` | Side-by-side pre/post QC rejection comparison | Analysis + Data |

### Combined Figures (3 types)

Generated once for the entire batch, aggregating results across all stations.

| # | figure_type | Description | Requires |
|---|-------------|-------------|----------|
| 1 | `all_hvsr_overlay` | All station H/V curves overlaid on single plot | All stations analysed |
| 2 | `peak_frequency_map` | Map/bar chart of f₀ per station | All stations analysed + Peaks |
| 3 | `summary_table` | Tabular summary of all stations' results | All stations analysed |

---

## Per-Station Figure Details

### hvsr_curve

The primary output plot. Shows the median (and optionally mean) H/V
spectral ratio curve with confidence interval shading. Detected peaks
are annotated with frequency and amplitude labels. Peak annotations use
smart positioning to avoid overlap.

- **What it shows:** Median H/V curve, uncertainty band, peak markers
- **When to use:** Always — this is the core HVSR result for every station
- **Required:** Analysis must be complete

### hvsr_statistics

Statistical view of the H/V curve showing mean, median, standard
deviation, and percentile bands. Useful for assessing stability of the
H/V estimate across windows.

- **What it shows:** Mean/median curves with std dev and percentile bands
- **When to use:** When you need to evaluate how stable the H/V estimate is
- **Required:** Analysis must be complete

### hvsr_with_windows

Same as `hvsr_curve` but with individual window H/V curves drawn behind
the summary curve. Active windows shown in colour; rejected windows are
shown in grey if `show_rejected` is enabled.

- **What it shows:** Individual per-window H/V curves overlaid with the median
- **When to use:** To inspect window-to-window variability at a station
- **Required:** Analysis must be complete

### quality_metrics

Scatter-plot of quality metrics for each analysis window. Shows which
windows were accepted vs rejected, and by which QC algorithm.

- **What it shows:** Per-window QC metric values, accept/reject status
- **When to use:** To diagnose quality control decisions
- **Required:** Analysis must be complete

### window_timeline

Timeline bar chart showing the temporal distribution of accepted (green)
and rejected (red/grey) windows across the recording duration.

- **What it shows:** Temporal map of accepted vs rejected windows
- **When to use:** To see where in time data was rejected (e.g. noise events)
- **Required:** Analysis must be complete

### peak_analysis

Focused view of detected peaks with prominence, width, and amplitude
details. Annotates primary and secondary peaks with their characteristics.

- **What it shows:** Peak frequency, amplitude, prominence, and width
- **When to use:** When you need detailed peak characterisation beyond f₀
- **Required:** Analysis must be complete; peaks must be detected

### complete_dashboard

Comprehensive multi-panel view combining the HVSR curve, window overlay,
quality metrics, and timeline in a single figure. Best for quick visual
assessment of a station.

- **What it shows:** 4-panel composite: curve + windows + QC + timeline
- **When to use:** For a single-glance quality check of each station
- **Required:** Analysis must be complete

### mean_vs_median

Direct comparison of arithmetic mean and lognormal median H/V curves.
Differences between the two indicate skewness in the distribution.
The median is generally more robust for HVSR analysis.

- **What it shows:** Side-by-side mean vs median H/V curves
- **When to use:** To evaluate skewness and choose the best central estimator
- **Required:** Analysis must be complete

### quality_histogram

Histogram showing the distribution of QC metric values across all
analysis windows. Helps identify systematic data quality patterns.

- **What it shows:** Distribution of QC metrics (STA/LTA, amplitude, etc.)
- **When to use:** To assess overall data quality at a station
- **Required:** Analysis must be complete

### selected_metrics

Grid of selected key quality metrics (e.g. STA/LTA ratio,
zero-crossing rate, amplitude range, spectral energy).

- **What it shows:** Key QC metrics in a compact multi-panel layout
- **When to use:** For focused quality metric review
- **Required:** Analysis must be complete

### window_timeseries

Three-component (E, N, Z) waveform display with window boundaries
marked. Shows the raw seismic data that was analysed.

- **What it shows:** Raw waveform data per component with window markers
- **When to use:** To visually inspect the input seismic data
- **Required:** Analysis must be complete; raw data must be retained

### window_spectrogram

Frequency-time spectrogram of the seismic data. Shows energy
distribution across frequencies over time.

- **What it shows:** Spectrogram (frequency vs time vs amplitude)
- **When to use:** To identify transient events or frequency-dependent noise
- **Required:** Analysis must be complete; raw data must be retained

### raw_vs_adjusted

Two-panel comparison: top panel shows the HVSR curve before QC/FDWRA
adjustments; bottom panel shows the final HVSR after all processing.
Highlights the effect of quality control on the result.

- **What it shows:** Pre-QC H/V curve vs post-QC H/V curve
- **When to use:** To evaluate how much QC changed the result
- **Required:** Analysis must be complete (pre-QC curve stored automatically)

### waveform_rejection

Three-panel (E/N/Z) waveform display with window backgrounds coloured
green (accepted) or grey (rejected). Clearly shows which portions of the
recording were used vs discarded.

- **What it shows:** Waveform with accepted/rejected window overlay
- **When to use:** To verify that the correct portions of data were kept
- **Required:** Analysis must be complete; raw data must be retained

### pre_post_rejection

Five-panel composite figure. Left side: three waveform panels (E/N/Z)
with rejection overlay. Right top: pre-rejection HVSR curve. Right
bottom: post-rejection HVSR curve. The most comprehensive single view of
the entire QC process.

- **What it shows:** Waveforms + pre/post QC HVSR in one figure
- **When to use:** For the most complete QC assessment of a single station
- **Required:** Analysis must be complete; raw data must be retained

---

## Combined Figure Details

### all_hvsr_overlay

All station H/V curves plotted on a single set of axes. Each station is
drawn in a distinct colour with a legend. Useful for comparing site
response across the project area.

- **What it shows:** Overlaid H/V curves from every station
- **When to use:** To compare H/V shapes and amplitudes across stations
- **Required:** All stations must have completed analysis

### peak_frequency_map

Map or bar chart showing the fundamental frequency (f₀) for each
station. If station coordinates are available a spatial map is drawn;
otherwise a grouped bar chart is used.

- **What it shows:** f₀ per station in spatial or bar-chart format
- **When to use:** To visualise spatial variability of site frequency
- **Required:** All stations must have completed analysis with peaks detected

### summary_table

Tabular summary of all stations' key results: station name/number,
f₀, amplitude, number of windows, number of accepted windows, and
QC status. Rendered as a figure for inclusion in reports.

- **What it shows:** Table with one row per station summarising key metrics
- **When to use:** For a concise overview of the entire batch
- **Required:** All stations must have completed analysis

---

## Figure Export Configuration

Figures are controlled by `FigureExportSettings` in the batch config.

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `dpi` | int | `300` | Image resolution in dots per inch |
| `format` | str | `"png"` | Output format: `"png"`, `"pdf"`, or `"svg"` |
| `size_preset` | str | `"default"` | Figure size: `"default"` (10×6), `"compact"` (8×5), or `"large"` (14×8 in) |
| `y_limit_method` | str | `"auto"` | Y-axis scaling: `"auto"`, `"fixed"`, or `"percentile"` |
| `y_limit_value` | float | `None` | Fixed upper Y-limit (used when `y_limit_method` is `"fixed"`) |
| `show_mean` | bool | `False` | Draw the arithmetic mean H/V curve |
| `show_median` | bool | `True` | Draw the lognormal median H/V curve |
| `show_uncertainty` | bool | `True` | Show confidence interval / uncertainty band |
| `show_rejected` | bool | `False` | Draw rejected windows in grey behind accepted curves |
| `figure_types` | list | *(see below)* | Which per-station figure types to generate |

### Default Figure Types

When not overridden, the following per-station figures are generated:

```
hvsr_curve, statistics, windows, quality, dashboard,
peak_analysis, raw_vs_adjusted, waveform_rejection, pre_post_rejection
```

### Configuration Example

```python
# Via set_figure_params MCP tool
set_figure_params(
    dpi=300,
    format="png",
    show_median=True,
    show_uncertainty=True,
    show_rejected=False,
    figure_types=[
        "hvsr_curve",
        "complete_dashboard",
        "peak_analysis",
        "pre_post_rejection",
    ],
)
```

---

## Recommended Figures for Reports

### Minimal Report (3 per-station + 1 combined)

For a concise deliverable with essential information:

| Figure | Purpose |
|--------|---------|
| `hvsr_curve` | Core HVSR result with peak annotation |
| `complete_dashboard` | Quick quality overview |
| `peak_analysis` | Detailed peak characterisation |
| `summary_table` | Batch-wide results at a glance |

### Standard Report (7 per-station + 3 combined)

For a thorough project report covering results and quality assurance:

| Figure | Purpose |
|--------|---------|
| `hvsr_curve` | Core HVSR result |
| `hvsr_statistics` | Uncertainty assessment |
| `complete_dashboard` | Multi-panel quality overview |
| `peak_analysis` | Peak frequency and amplitude detail |
| `raw_vs_adjusted` | QC impact assessment |
| `waveform_rejection` | Visual verification of data selection |
| `pre_post_rejection` | Comprehensive QC documentation |
| `all_hvsr_overlay` | Cross-station comparison |
| `peak_frequency_map` | Spatial variability of f₀ |
| `summary_table` | Tabular batch summary |

### Full Report (all 15 per-station + 3 combined)

Generate every figure type for archival or detailed review:

```python
# Request all figure types
set_figure_params(
    figure_types=[
        "hvsr_curve", "hvsr_statistics", "hvsr_with_windows",
        "quality_metrics", "window_timeline", "peak_analysis",
        "complete_dashboard", "mean_vs_median", "quality_histogram",
        "selected_metrics", "window_timeseries", "window_spectrogram",
        "raw_vs_adjusted", "waveform_rejection", "pre_post_rejection",
    ],
)
# Combined figures are always generated when running generate_batch_report
```

---

## Report File Names

When using `generate_batch_report`, per-station plots are saved under
each station's output directory:

```
{output_dir}/
  Station_{num}/
    hvsr_curve.png
    hvsr_statistics.png
    hvsr_with_windows.png
    quality_metrics.png
    window_timeline.png
    peak_analysis.png
    complete_dashboard.png
    mean_vs_median.png
    quality_histogram.png
    selected_metrics.png
    window_timeseries.png
    window_spectrogram.png
    raw_vs_adjusted.png
    waveform_rejection.png
    pre_post_rejection.png
  combined/
    all_hvsr_overlay.png
    peak_frequency_map.png
    summary_table.png
```
