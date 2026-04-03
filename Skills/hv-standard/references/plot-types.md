# Plot Types Reference

All 15 plot types available via `export_plot` and `generate_report`.

## Plot Types Overview

| # | plot_type | Description | Requires |
|---|-----------|-------------|----------|
| 1 | `hvsr` | Main H/V spectral ratio curve with peaks annotated | Analysis |
| 2 | `windows` | H/V curve with individual window curves overlaid | Analysis |
| 3 | `quality` | Quality metrics scatter plot (per-window) | Analysis |
| 4 | `statistics` | Statistical summary of H/V curve (std dev, percentiles) | Analysis |
| 5 | `dashboard` | Complete 4-panel dashboard combining key views | Analysis |
| 6 | `mean_vs_median` | Mean and median H/V curves side by side | Analysis |
| 7 | `quality_histogram` | Histogram of quality metric distributions | Analysis |
| 8 | `selected_metrics` | 2x2 grid of key quality metric plots | Analysis |
| 9 | `window_timeline` | Timeline showing accepted/rejected windows | Analysis |
| 10 | `window_timeseries` | 3-component (E/N/Z) waveform time series | Analysis + Data |
| 11 | `window_spectrogram` | Frequency-time spectrogram display | Analysis + Data |
| 12 | `peak_analysis` | Detailed peak analysis with secondary peaks | Analysis + Peaks |
| 13 | `raw_vs_adjusted` | Pre-QC vs post-QC HVSR comparison | Analysis (auto) |
| 14 | `waveform_rejection` | 3-panel waveform with green/gray window overlay | Analysis + Data |
| 15 | `pre_post_rejection` | 5-panel: 3 waveform panels + pre/post HVSR | Analysis + Data |

## Detailed Descriptions

### hvsr
The primary output plot. Shows the median (and optionally mean) H/V curve
with confidence interval shading. Detected peaks are annotated with
frequency and amplitude labels. Peak annotations use smart positioning
to avoid overlap.

### windows
Same as `hvsr` but with individual window H/V curves drawn behind the
summary curve. Active windows shown in color, rejected windows in gray
(if `show_rejected_windows` is enabled in plot style).

### quality
Scatter plot of quality metrics for each window. Shows which windows
were accepted vs rejected, and by which algorithm.

### statistics
Statistical view showing mean, median, standard deviation, and
percentile bands of the H/V curve. Useful for assessing stability.

### dashboard
Comprehensive 4-panel view combining HVSR curve, window overlay,
quality metrics, and timeline in a single figure. Best for quick
assessment.

### mean_vs_median
Direct comparison of arithmetic mean and lognormal median H/V curves.
Differences indicate skewness in the distribution. Median is generally
more robust for HVSR.

### quality_histogram
Histogram showing the distribution of quality metric values across
all windows. Helps identify data quality patterns.

### selected_metrics
2x2 grid showing four key quality metrics: STA/LTA ratio,
zero-crossing rate, amplitude range, and spectral energy.

### window_timeline
Timeline bar chart showing the temporal distribution of accepted
(green) and rejected (red/gray) windows across the recording.

### window_timeseries
3-component (E, N, Z) waveform display with window boundaries.
Shows the raw seismic data that was analyzed.

### window_spectrogram
Frequency-time spectrogram of the seismic data. Shows energy
distribution across frequencies over time.

### peak_analysis
Focused view of detected peaks with prominence, width, and
amplitude details for each peak.

### raw_vs_adjusted
Two-panel comparison: top shows HVSR before QC/FDWRA adjustments,
bottom shows final HVSR after all processing. Highlights the
effect of quality control.

### waveform_rejection
3-panel (E/N/Z) waveform display with window backgrounds colored
green (accepted) or gray (rejected). Clearly shows which portions
of data were used vs discarded.

### pre_post_rejection
5-panel composite figure. Left side: 3 waveform panels (E/N/Z)
with rejection overlay. Right top: pre-rejection HVSR curve.
Right bottom: post-rejection HVSR curve. The most comprehensive
single view of the entire QC process.

## Report File Names

When using `generate_report`, plots are saved with these names:

```
{output_dir}/
  hvsr_curve.png
  hvsr_with_windows.png
  hvsr_statistics.png
  quality_metrics.png
  complete_dashboard.png
  mean_vs_median.png
  quality_histogram.png
  selected_metrics.png
  window_timeline.png
  window_timeseries.png
  window_spectrogram.png
  peak_analysis.png
  raw_vs_adjusted.png
  waveform_rejection.png
  pre_post_rejection.png
```