# HVSR Result Classes

## HvsrCurve

Base class for a single HVSR curve.

```python
from hvsrpy import HvsrCurve

curve = HvsrCurve(frequency, amplitude, meta=None)

# Properties
curve.frequency      # Frequency array
curve.amplitude      # HVSR amplitude array
curve.meta           # Metadata dict

# Methods
curve.is_similar(other)  # Compare frequency sampling
```

## HvsrTraditional

Container for multiple HVSR curves from time windows.

```python
from hvsrpy import HvsrTraditional

hvsr = HvsrTraditional(frequency, amplitude, meta=None)

# Properties
hvsr.frequency                   # Frequency array (n_freq,)
hvsr.amplitude                   # HVSR amplitudes (n_curves, n_freq)
hvsr.n_curves                    # Number of curves/windows
hvsr.valid_window_boolean_mask   # Boolean mask for valid windows
hvsr.valid_peak_boolean_mask     # Boolean mask for valid peaks
hvsr.peak_frequencies            # Valid peak frequencies
hvsr.peak_amplitudes             # Valid peak amplitudes

# Peak detection
hvsr.update_peaks_bounded(
    search_range_in_hz=(None, None),
    find_peaks_kwargs=None
)

# Statistics (distribution: "normal" or "lognormal")
hvsr.mean_fn_frequency(distribution="lognormal")
hvsr.mean_fn_amplitude(distribution="lognormal")
hvsr.std_fn_frequency(distribution="lognormal")
hvsr.std_fn_amplitude(distribution="lognormal")
hvsr.nth_std_fn_frequency(n, distribution="lognormal")

# Mean curve
hvsr.mean_curve(distribution="lognormal")
hvsr.std_curve(distribution="lognormal")
hvsr.nth_std_curve(n, distribution="lognormal")
hvsr.mean_curve_peak(distribution="lognormal")  # (freq, amp)

# Covariance
hvsr.cov_fn(distribution="lognormal")
```

## HvsrAzimuthal

HVSR computed at multiple azimuths for directional variability.

```python
from hvsrpy import HvsrAzimuthal

hvsr_az = HvsrAzimuthal(hvsrs, azimuths, meta=None)
# hvsrs: list of HvsrTraditional, one per azimuth
# azimuths: rotation angles in degrees (0-180)

# Properties
hvsr_az.hvsrs           # List of HvsrTraditional
hvsr_az.azimuths        # List of azimuth angles
hvsr_az.n_azimuths      # Number of azimuths
hvsr_az.frequency       # Common frequency array
hvsr_az.peak_frequencies  # Nested list [azimuth][window]
hvsr_az.peak_amplitudes

# Statistics (weighted by Cheng et al. 2020)
hvsr_az.mean_fn_frequency(distribution="lognormal")
hvsr_az.std_fn_frequency(distribution="lognormal")
hvsr_az.mean_curve(distribution="lognormal")
hvsr_az.std_curve(distribution="lognormal")
```

## HvsrDiffuseField

HVSR under diffuse field assumption (Sánchez-Sesma et al. 2011).

```python
from hvsrpy import HvsrDiffuseField

hvsr_df = HvsrDiffuseField(frequency, amplitude, meta=None)

# Single curve result (no window-by-window statistics)
hvsr_df.frequency
hvsr_df.amplitude
hvsr_df.peak()  # (freq, amp)
```

## HvsrSpatial

Spatial statistics combining multiple measurement locations.

```python
from hvsrpy import HvsrSpatial, montecarlo_fn

# Combine multiple HvsrTraditional from different locations
hvsr_sp = HvsrSpatial(hvsrs, coordinates, meta=None)

# Monte Carlo sampling for spatial fn statistics
fn_samples = montecarlo_fn(hvsr_sp, n_samples=1000)
```

## Distribution Options

All statistical methods support:

- `"lognormal"` (default): Assumes H/V amplitudes follow lognormal distribution
- `"normal"`: Assumes normal distribution

**Lognormal is recommended** for HVSR because:
1. Amplitudes are always positive
2. Consistent uncertainty in frequency and period
3. Follows Cox et al. (2020) methodology

## Key Statistics

| Method | Returns |
|--------|---------|
| `mean_fn_frequency()` | Mean peak frequency across valid windows |
| `std_fn_frequency()` | Std dev of peak frequency |
| `mean_curve()` | Mean HVSR curve (all frequencies) |
| `std_curve()` | Std dev curve |
| `nth_std_curve(n)` | Mean ± n*std curve |
| `mean_curve_peak()` | Peak of the mean curve |
