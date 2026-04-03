# Batch QC Pipeline Reference

Detailed documentation of the quality control pipeline for batch HVSR processing.

## Pipeline Overview

```
Phase 1: Pre-HVSR Window Rejection (per station)
  |-- STA/LTA ratio check (transient detection)
  |-- Amplitude check (clipping, dead channels)
  |-- Statistical outlier check (IQR or z-score)
  v
HVSR Computation (on surviving windows, per station)
  v
Phase 2: Cox FDWRA (Frequency-Dependent Window Rejection)
  |-- Iterative outlier removal per frequency
  v
Phase 3: Post-HVSR QC
  |-- HVSR amplitude gate
  |-- Flat peak rejection
  |-- Curve outlier rejection
```

In batch mode, QC is applied **independently per station** — each station's
windows are evaluated on their own. The same QC configuration applies to all
stations unless overridden.

---

## Phase 1: Pre-HVSR Window Rejection

Each time-domain window is tested independently before spectral computation.
A window is rejected if ANY enabled algorithm flags it.

### STA/LTA Transient Detection

Detects transient energy bursts (footsteps, vehicle passes, equipment bumps)
by comparing short-term and long-term signal averages.

| Parameter | Default | MCP param name | Description |
|-----------|---------|----------------|-------------|
| `enabled` | true | `stalta_enabled` | Enable/disable |
| `sta_length` | 1.0 s | `sta_length` | Short-term average window |
| `lta_length` | 30.0 s | `lta_length` | Long-term average window |
| `min_ratio` | 0.2 | `sta_lta_min_ratio` | Min STA/LTA ratio threshold |
| `max_ratio` | 2.5 | `sta_lta_max_ratio` | Max STA/LTA ratio threshold |

Windows where STA/LTA falls outside `[min_ratio, max_ratio]` are rejected.

### Amplitude / Clipping Check

Detects clipping (signal hitting sensor limits) and dead channels (no signal).

| Parameter | Default | MCP param name | Description |
|-----------|---------|----------------|-------------|
| `enabled` | true | `amplitude_enabled` | Enable/disable |
| `clipping_threshold` | 0.95 | `clipping_threshold` | Fraction of full-scale considered clipping (0–1) |
| `min_rms` | 1e-10 | `min_rms` | Minimum RMS amplitude (rejects dead channels) |

### Statistical Outlier Detection

Detects windows that are statistical outliers in the time domain using either
interquartile range (IQR) or z-score methods.

| Parameter | Default | MCP param name | Description |
|-----------|---------|----------------|-------------|
| `enabled` | false | `statistical_enabled` | Enable/disable |
| `method` | "iqr" | `statistical_method` | Detection method: `"iqr"` or `"zscore"` |
| `threshold` | 2.0 | `statistical_threshold` | Deviation threshold |

---

## Phase 2: Cox FDWRA (Frequency-Dependent Window Rejection)

After HVSR is computed for all surviving windows, the FDWRA algorithm
iteratively removes windows whose H/V curves deviate from the ensemble
at each frequency:

1. Compute median and standard deviation of log(H/V) at each frequency
2. Flag windows where |log(H/V) - median| > `n` × std
3. Remove flagged windows
4. Repeat until convergence or `max_iterations` reached

| Parameter | Default | MCP param name | Description |
|-----------|---------|----------------|-------------|
| `enabled` | true | `fdwra_enabled` | Enable/disable FDWRA |
| `n` | 2.0 | `fdwra_n` | Std dev threshold for rejection |
| `max_iterations` | 50 | `fdwra_max_iterations` | Maximum rejection passes |
| `min_iterations` | 1 | — | Minimum passes before stopping |
| `distribution` | "lognormal" | `fdwra_distribution` | Statistical distribution (`"lognormal"` or `"normal"`) |

**Note:** Lognormal distribution is strongly recommended as H/V ratios are
naturally log-distributed.

---

## Phase 3: Post-HVSR QC

Applied after H/V spectral ratio computation to reject poor-quality curves.

### HVSR Amplitude Gate

Rejects windows where the peak H/V amplitude is below a minimum threshold.
Useful for removing windows with no clear site response.

| Parameter | Default | MCP param name | Description |
|-----------|---------|----------------|-------------|
| `enabled` | false | `hvsr_amplitude_enabled` | Enable/disable |
| `min_amplitude` | 1.0 | `hvsr_amplitude_min` | Minimum H/V amplitude to keep |

### Flat Peak Rejection

Rejects windows whose H/V peak is too flat (no distinct resonance).

| Parameter | Default | MCP param name | Description |
|-----------|---------|----------------|-------------|
| `enabled` | false | `flat_peak_enabled` | Enable/disable |
| `flatness_threshold` | 0.15 | `flatness_threshold` | Flatness threshold (lower = stricter) |

### Curve Outlier Rejection

Iteratively removes H/V curves that deviate from the ensemble median.

| Parameter | Default | MCP param name | Description |
|-----------|---------|----------------|-------------|
| `enabled` | true | `curve_outlier_enabled` | Enable/disable |
| `threshold` | 3.0 | `curve_outlier_threshold` | Outlier threshold (std devs) |
| `max_iterations` | 5 | `curve_outlier_max_iterations` | Max rejection iterations |

---

## Configuring QC via MCP

### Using `set_qc_params` (recommended)

```
# Loosen STA/LTA and enable statistical outlier detection
set_qc_params(
    sta_lta_max_ratio=3.0,
    statistical_enabled=True,
    statistical_method="zscore",
    statistical_threshold=2.5
)
```

### Tuning FDWRA

```
# Stricter FDWRA rejection
set_qc_params(
    fdwra_enabled=True,
    fdwra_n=1.5,
    fdwra_distribution="lognormal",
    fdwra_max_iterations=30
)
```

### Disabling All QC

```
set_qc_params(
    stalta_enabled=False,
    amplitude_enabled=False,
    statistical_enabled=False,
    fdwra_enabled=False,
    hvsr_amplitude_enabled=False,
    flat_peak_enabled=False,
    curve_outlier_enabled=False
)
```

### Recommended Settings

| Scenario | STA/LTA | Amplitude | FDWRA | Curve Outlier |
|----------|---------|-----------|-------|---------------|
| **Standard survey** | ✅ defaults | ✅ defaults | ✅ n=2.0 | ✅ threshold=3.0 |
| **Noisy urban site** | ✅ max_ratio=3.0 | ✅ defaults | ✅ n=1.5 | ✅ threshold=2.5 |
| **Quiet rural site** | ✅ defaults | ✅ defaults | ✅ n=2.5 | ❌ disabled |
| **Maximum data retention** | ❌ disabled | ✅ min_rms only | ❌ disabled | ❌ disabled |

---

## Interpreting QC Results

The `process_hvsr` response includes per-station window statistics:

```json
{
  "results": [
    {
      "station": "STN01",
      "success": true,
      "valid_windows": 34,
      "total_windows": 57,
      "n_peaks": 2,
      "primary_frequency": 1.05
    }
  ]
}
```

**Guidance:**
- **Acceptance > 60%**: Good data quality
- **Acceptance 40–60%**: Acceptable; check rejection reasons
- **Acceptance < 40%**: Problematic; loosen QC or check data quality
- Use `get_station_result(station_name)` to see `rejected_reasons` breakdown
- If one algorithm dominates rejections, consider tuning or disabling it

**Batch-specific tip:** If many stations have low acceptance, the QC settings
may be too strict for the deployment conditions. Adjust globally via
`set_qc_params` before re-running `process_hvsr`.
