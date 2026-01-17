# HVSR Processing Pipeline

## Processing Methods

### 1. Traditional HVSR

Combines horizontal components using various methods.

```python
from hvsrpy import HvsrTraditionalProcessingSettings, preprocess, process

settings = HvsrTraditionalProcessingSettings(
    method_to_combine_horizontals="geometric_mean",
    window_type_and_width=["tukey", 0.1],
    smoothing=dict(
        operator="konno_and_ohmachi",
        bandwidth=40,
        center_frequencies_in_hz=np.geomspace(0.1, 50, 200)
    )
)

windows = preprocess(records, pre_settings)
hvsr = process(windows, settings)  # Returns HvsrTraditional
```

### 2. Azimuthal HVSR

Computes HVSR at multiple azimuths to assess directional variability.

```python
from hvsrpy import HvsrAzimuthalProcessingSettings

settings = HvsrAzimuthalProcessingSettings(
    azimuths_in_degrees=np.arange(0, 180, 10),
    # ... other settings
)
hvsr = process(windows, settings)  # Returns HvsrAzimuthal
```

### 3. Diffuse Field HVSR

Based on Sánchez-Sesma et al. (2011) diffuse field assumption.

```python
from hvsrpy import HvsrDiffuseFieldProcessingSettings

settings = HvsrDiffuseFieldProcessingSettings(...)
hvsr = process(windows, settings)  # Returns HvsrDiffuseField
```

### 4. PSD Processing

Power Spectral Density computation.

```python
from hvsrpy import PsdProcessingSettings

settings = PsdProcessingSettings(...)
psd = process(windows, settings)  # Returns dict with ns, ew, vt Psd objects
```

## Horizontal Combination Methods (9+)

```python
COMBINE_HORIZONTAL_REGISTER = {
    "arithmetic_mean": (ns + ew) / 2,
    "squared_average": sqrt((ns² + ew²) / 2),       # aka quadratic_mean
    "quadratic_mean": sqrt((ns² + ew²) / 2),
    "root_mean_square": sqrt((ns² + ew²) / 2),
    "effective_amplitude_spectrum": sqrt((ns² + ew²) / 2),
    "geometric_mean": sqrt(ns * ew),
    "total_horizontal_energy": sqrt(ns² + ew²),     # aka vector_summation
    "vector_summation": sqrt(ns² + ew²),
    "maximum_horizontal_value": max(ns, ew),
}

# Time-domain methods (special handling):
# - "single_azimuth": ns*cos(θ) + ew*sin(θ)
# - "rotdpp": percentile across azimuths
```

## Processing Flow

```
SeismicRecording3C
    ↓ preprocess()
list[SeismicRecording3C]  # Windows
    ↓ window()  # Apply taper
    ↓ rfft()    # FFT each component
    ↓ combine_horizontals()  # H = method(fft_ns, fft_ew)
    ↓ smooth()  # Apply smoothing operator
    ↓ hvsr = H / V
HvsrTraditional(frequencies, hvsr_spectra)
```

## Key Functions

### `preprocess(records, settings)`

Applies time-domain preprocessing:
- Sensor orientation
- Butterworth filtering
- Windowing (split into time windows)
- Detrending

### `process(records, settings)`

Applies frequency-domain processing:
- FFT computation
- Horizontal combination
- Spectral smoothing
- H/V ratio calculation

## Handling Dissimilar Time Steps

When records have different sampling rates:

```python
settings.handle_dissimilar_time_steps_by = "frequency_domain_resampling"
# or "keeping_smallest_time_step"
# or "keeping_majority_time_step"
```

## Processing Settings Classes

| Class | Purpose |
|-------|---------|
| `HvsrPreProcessingSettings` | Time-domain preprocessing |
| `PsdPreProcessingSettings` | PSD preprocessing |
| `HvsrTraditionalProcessingSettings` | Traditional HVSR |
| `HvsrTraditionalSingleAzimuthProcessingSettings` | Single azimuth |
| `HvsrTraditionalRotDppProcessingSettings` | RotDpp method |
| `HvsrAzimuthalProcessingSettings` | Multi-azimuth |
| `HvsrDiffuseFieldProcessingSettings` | Diffuse field |
| `PsdProcessingSettings` | PSD computation |
