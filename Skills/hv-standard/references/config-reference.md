# Config Reference

Complete JSON structure for `HVSRAnalysisConfig` used with `configure_analysis`.

## Full Config Template

```json
{
  "processing": {
    "window_length": 60,
    "overlap": 0.0,
    "freq_min": 0.2,
    "freq_max": 50.0,
    "n_frequencies": 200,
    "smoothing_method": "konno_ohmachi",
    "smoothing_bandwidth": 40,
    "horizontal_method": "geometric_mean",
    "statistics_method": "lognormal",
    "peak_basis": "median",
    "min_prominence": 0.3,
    "min_amplitude": 1.0,
    "use_parallel": false,
    "n_cores": 4
  },
  "qc": {
    "enabled": true,
    "mode": "sesame",
    "phase1_enabled": true,
    "phase2_enabled": true,
    "amplitude": {
      "enabled": true,
      "max_amplitude": null,
      "min_rms": 1e-10,
      "clipping_threshold": 0.95
    },
    "quality_threshold": {
      "enabled": false,
      "threshold": 0.5
    },
    "sta_lta": {
      "enabled": true,
      "sta_length": 1.0,
      "lta_length": 30.0,
      "min_ratio": 0.2,
      "max_ratio": 2.5
    },
    "frequency_domain": {
      "enabled": false,
      "spike_threshold": 3.0
    },
    "statistical_outlier": {
      "enabled": false,
      "method": "iqr",
      "threshold": 2.0
    },
    "hvsr_amplitude": {
      "enabled": false,
      "min_amplitude": 1.0
    },
    "flat_peak": {
      "enabled": false,
      "flatness_threshold": 0.15
    },
    "curve_outlier": {
      "enabled": true,
      "threshold": 3.0,
      "max_iterations": 5,
      "metric": "mean"
    },
    "cox_fdwra": {
      "enabled": true,
      "n": 2.0,
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

## Section Details

### processing

Controls how the seismic data is processed.

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `window_length` | float | 10-600 | Window duration in seconds |
| `overlap` | float | 0.0-0.99 | Overlap fraction between windows |
| `freq_min` | float | 0.01-10 | Lower frequency bound (Hz) |
| `freq_max` | float | 5-100 | Upper frequency bound (Hz) |
| `n_frequencies` | int | 50-2000 | Number of logarithmically-spaced frequency points |
| `smoothing_method` | string | see below | Spectral smoothing algorithm |
| `smoothing_bandwidth` | float | 1-200 | Bandwidth parameter (meaning depends on method) |
| `horizontal_method` | string | see below | How E and N components are combined |
| `statistics_method` | string | `"lognormal"` / `"normal"` | Statistical distribution for H/V curve |
| `peak_basis` | string | `"median"` / `"mean"` | Which statistical curve to use for peak detection |
| `min_prominence` | float | 0.01-5.0 | Minimum peak prominence for detection |
| `min_amplitude` | float | 0.5-20.0 | Minimum H/V amplitude to be considered a peak |
| `use_parallel` | bool | - | Enable multi-core processing |
| `n_cores` | int | 1-32 | CPU cores (only if use_parallel=true) |

**Smoothing methods:**
- `konno_ohmachi` -- Most common (bandwidth=40 recommended)
- `parzen` -- Parzen window smoothing
- `constant_bandwidth` -- Fixed Hz bandwidth
- `proportional_bandwidth` -- Proportional to frequency

**Horizontal methods:**
- `geometric_mean` -- sqrt(E * N), most common
- `arithmetic_mean` -- (E + N) / 2
- `quadratic_mean` -- sqrt((E^2 + N^2) / 2)
- `ps_RotD50` -- Rotation-dependent 50th percentile
- `maximum_horizontal` -- max(E, N)
- `single_azimuth` -- Single direction (use with degrees_from_north)

### qc

Quality control settings with 8 algorithms in two phases plus Cox FDWRA.

- **mode:** `"sesame"` uses hardcoded SESAME pipeline; `"custom"` uses
  per-algorithm settings below. The `set_qc_params` tool auto-switches
  to "custom" when any algorithm-level parameter is changed.
- **phase1_enabled / phase2_enabled:** Master switches for pre-HVSR and
  post-HVSR rejection phases.

Phase 1 algorithms (pre-HVSR): amplitude, quality_threshold, sta_lta,
frequency_domain, statistical_outlier.

Phase 2 algorithms (post-HVSR): hvsr_amplitude, flat_peak, curve_outlier.

Each algorithm has `enabled` plus its own parameters (see full config above).

### cox_fdwra

Cox Frequency-Dependent Window Rejection Algorithm. Iteratively removes
windows whose individual H/V curves deviate from the median at each frequency.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | bool | true | Enable/disable FDWRA |
| `n` | float | 2.0 | Rejection threshold in std deviations |
| `max_iterations` | int | 50 | Maximum rejection passes |
| `min_iterations` | int | 1 | Minimum passes before stopping |
| `distribution` | string | "lognormal" | Statistical distribution |

### plot_style

Controls appearance of all generated plots. See `configure_plot_style`
in tool-reference.md for parameter details.

## Partial Config

You can provide only the sections/fields you want to change:

```json
{
  "processing": {
    "window_length": 120,
    "freq_max": 50
  }
}
```

All other fields retain their current or default values.