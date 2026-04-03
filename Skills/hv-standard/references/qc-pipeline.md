# QC Pipeline Reference

Detailed documentation of the HVSR quality control pipeline.

## Pipeline Overview

```
Phase 1: Pre-HVSR Window Rejection
  |-- Amplitude check (clipping, dead channels)
  |-- STA/LTA ratio check (transients)
  |-- Quality threshold check (composite score)
  |-- Frequency domain check (spectral spikes)
  |-- Statistical outlier check
  v
HVSR Computation (on surviving windows)
  v
Phase 2: Cox FDWRA (Frequency-Dependent Window Rejection)
  |-- Iterative outlier removal per frequency
  v
Phase 3: Post-HVSR QC
  |-- Curve outlier rejection
  |-- HVSR amplitude check
  |-- Flat peak rejection
```

## Phase 1: Pre-HVSR Window Rejection

Each window is tested independently. A window is rejected if ANY
enabled algorithm flags it.

### Amplitude

Detects clipping and dead channels.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `enabled` | true | Enable/disable |
| `max_amplitude` | null | Max absolute amplitude (null = auto) |
| `min_rms` | 1e-10 | Minimum RMS amplitude |
| `clipping_threshold` | 0.95 | Fraction of full-scale considered clipping |

### STA/LTA (Short-Term Average / Long-Term Average)

Detects transients (footsteps, vehicle passes, equipment bumps).

| Parameter | Default | Description |
|-----------|---------|-------------|
| `enabled` | true | Enable/disable |
| `sta_length` | 1.0 s | STA window length |
| `lta_length` | 30.0 s | LTA window length |
| `min_ratio` | 0.2 | Min STA/LTA ratio threshold |
| `max_ratio` | 2.5 | Max STA/LTA ratio threshold |

### Quality Threshold

Rejects windows with low composite quality score.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `enabled` | false | Enable/disable |
| `threshold` | 0.5 | Minimum quality score to pass |

### Frequency Domain

Detects windows with spectral spikes (narrow-band noise).

| Parameter | Default | Description |
|-----------|---------|-------------|
| `enabled` | false | Enable/disable |
| `spike_threshold` | 3.0 | Spectral spike threshold (std devs) |

### Statistical Outlier

Detects windows that are statistical outliers.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `enabled` | false | Enable/disable |
| `method` | "iqr" | Detection method: "iqr" or "zscore" |
| `threshold` | 2.0 | Deviation threshold |

## Phase 2: Cox FDWRA

After HVSR is computed for all surviving windows, the FDWRA algorithm
checks each window's H/V curve at each frequency point:

1. Compute median and std dev of log(H/V) at each frequency
2. Flag windows where log(H/V) deviates > `n` * std
3. Remove flagged windows
4. Repeat until convergence or `max_iterations`

| Parameter | Default | Description |
|-----------|---------|-------------|
| `enabled` | true | Enable/disable FDWRA |
| `n` | 2.0 | Std dev threshold for rejection |
| `max_iterations` | 50 | Maximum rejection passes |
| `min_iterations` | 1 | Minimum passes before stopping |
| `distribution` | "lognormal" | Statistical distribution |

## Phase 3: Post-HVSR QC

### Curve Outlier

Rejects windows whose H/V curves are outliers compared to the group.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `enabled` | true | Enable/disable |
| `threshold` | 3.0 | Outlier threshold (std devs) |
| `max_iterations` | 5 | Max rejection iterations |
| `metric` | "mean" | Comparison metric |

### HVSR Amplitude

Rejects windows where peak H/V amplitude is below threshold.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `enabled` | false | Enable/disable |
| `min_amplitude` | 1.0 | Minimum H/V amplitude |

### Flat Peak

Rejects windows with non-distinct (flat) peaks.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `enabled` | false | Enable/disable |
| `flatness_threshold` | 0.15 | Flatness threshold |

## Customizing QC via MCP

### Using `set_qc_params` (recommended)

```
# Loosen STA/LTA and enable frequency domain check
set_qc_params(
    sta_lta_max_ratio=3.0,
    frequency_domain_enabled=True,
    spike_threshold=2.5
)
```

Setting any algorithm-level parameter auto-switches to "custom" mode.
To explicitly stay in SESAME mode, pass `mode="sesame"`.

### Using `set_fdwra_params`

```
# Disable FDWRA entirely
set_fdwra_params(enabled=False)

# Or tune it
set_fdwra_params(n=1.5, distribution="lognormal", max_iterations=30)
```

### Disabling all QC

```
set_qc_params(enabled=False)
set_fdwra_params(enabled=False)
```

### Using `configure_analysis` (advanced)

```
configure_analysis(config_json='{"qc": {"enabled": true, "mode": "custom"}}')
```

## Interpreting QC Results

The `run_hvsr_analysis` response includes:

```json
{
  "windows": {
    "total": 57,
    "active": 34,
    "rejected": 23,
    "acceptance_rate": 59.6
  },
  "qc": {
    "phase1_detail": "QC: 34/57 windows active ...",
    "fdwra_detail": "Cox FDWRA: 5 rejected, converged in 3 iterations",
    "post_hvsr_detail": "Post-HVSR: 2 rejected, 32 remaining"
  }
}
```

**Guidance:**
- Acceptance > 60%: Good data quality
- Acceptance 40-60%: Acceptable, check for patterns
- Acceptance < 40%: Problematic; consider re-recording or loosening QC
- If one algorithm dominates rejections, investigate that specific issue