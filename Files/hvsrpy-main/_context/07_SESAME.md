# SESAME (2004) Criteria

## Overview

Implementation of SESAME (2004) reliability and clarity criteria for validating HVSR peak quality.

**Reference**: SESAME (2004). "Guidelines for the Implementation of the H/V Spectral Ratio Technique on Ambient Vibrations Measurements, Processing, and Interpretation."

## Reliability Criteria (3 total)

Tests whether the peak is reliably identified.

```python
from hvsrpy.sesame import reliability

criteria = reliability(
    windowlength,           # Window length in seconds
    passing_window_count,   # Number of valid windows
    frequency,              # Frequency array
    mean_curve,             # Mean HVSR curve (lognormal)
    std_curve,              # Std curve (lognormal)
    search_range_in_hz=(None, None),
    verbose=1               # 0, 1, or 2
)
# Returns: ndarray of shape (3,), 0=fail, 1=pass
```

### Criteria i)

```
f0 > 10 / windowlength
```

Peak frequency must be greater than 10 divided by window length.

### Criteria ii)

```
nc(f0) > 200
```

Number of significant cycles: `nc = windowlength × n_windows × f0 > 200`

### Criteria iii)

```
σA(f) < 2  for f0 > 0.5 Hz
σA(f) < 3  for f0 ≤ 0.5 Hz
```

Standard deviation of amplitude in range `[0.5*f0, 2*f0]` must be below threshold.

## Clarity Criteria (6 total)

Tests whether the peak is clearly defined.

```python
from hvsrpy.sesame import clarity

criteria = clarity(
    frequency,
    mean_curve,
    std_curve,
    fn_std,                 # Std of fn from windows (normal dist)
    search_range_in_hz=(None, None),
    verbose=1
)
# Returns: ndarray of shape (6,), 0=fail, 1=pass
# Peak is clear if ≥5 of 6 criteria pass
```

### Criteria i)

Amplitude below peak (in range `[f0/4, f0]`) drops below `A0/2`.

### Criteria ii)

Amplitude above peak (in range `[f0, 4*f0]`) drops below `A0/2`.

### Criteria iii)

Peak amplitude `A0 > 2`.

### Criteria iv)

Peak frequency of upper and lower std curves within 5% of mean curve peak.

### Criteria v)

```
σf < ε × f0
```

Standard deviation of peak frequency less than threshold (ε depends on f0).

| f0 range | ε |
|----------|---|
| < 0.2 Hz | 0.25 |
| 0.2-0.5 Hz | 0.20 |
| 0.5-1.0 Hz | 0.15 |
| 1.0-2.0 Hz | 0.10 |
| > 2.0 Hz | 0.05 |

### Criteria vi)

```
σA(f0) < θ
```

Amplitude std at peak less than threshold (θ depends on f0).

| f0 range | θ |
|----------|---|
| < 0.2 Hz | 3.0 |
| 0.2-0.5 Hz | 2.5 |
| 0.5-1.0 Hz | 2.0 |
| 1.0-2.0 Hz | 1.78 |
| > 2.0 Hz | 1.58 |

## Usage Example

```python
from hvsrpy.sesame import reliability, clarity

# After processing HVSR
mean = hvsr.mean_curve("lognormal")
std = hvsr.std_curve("lognormal")
fn_std = hvsr.std_fn_frequency("normal")  # Normal for SESAME

rel = reliability(
    windowlength=60,
    passing_window_count=sum(hvsr.valid_window_boolean_mask),
    frequency=hvsr.frequency,
    mean_curve=mean,
    std_curve=std,
    verbose=2
)

clar = clarity(
    frequency=hvsr.frequency,
    mean_curve=mean,
    std_curve=std,
    fn_std=fn_std,
    verbose=2
)

print(f"Reliability: {sum(rel)}/3")
print(f"Clarity: {sum(clar)}/6 (need ≥5)")
```

## Helper Functions

```python
from hvsrpy.sesame import peak_index, trim_curve

# Find peak index
idx = peak_index(mean_curve)

# Trim to frequency range
freq, mean, std = trim_curve(
    search_range_in_hz,
    frequency, mean_curve, std_curve
)
```
