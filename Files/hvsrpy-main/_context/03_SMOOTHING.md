# Smoothing Methods (7 Total)

## Available Smoothing Operators

All smoothing functions are JIT-compiled using Numba for performance.

### 1. Konno and Ohmachi (1998)

**Function**: `konno_and_ohmachi(frequencies, spectrum, fcs, bandwidth=40.)`

- **Type**: Logarithmic frequency scale
- **Default bandwidth**: 40
- **Description**: Standard HVSR smoothing, window width inversely proportional to bandwidth parameter
- **Reference**: Konno & Ohmachi (1998), Bull. Seism. Soc. Am.

```python
smoothing = dict(
    operator="konno_and_ohmachi",
    bandwidth=40,
    center_frequencies_in_hz=np.geomspace(0.1, 50, 200)
)
```

### 2. Parzen

**Function**: `parzen(frequencies, spectrum, fcs, bandwidth=0.5)`

- **Type**: Linear frequency scale
- **Default bandwidth**: 0.5 Hz
- **Description**: Parzen-style smoothing with constant bandwidth in Hz
- **Reference**: Konno & Ohmachi (1995)

### 3. Savitzky-Golay (1964)

**Function**: `savitzky_and_golay(frequencies, spectrum, fcs, bandwidth=9)`

- **Type**: Polynomial smoothing
- **Default bandwidth**: 9 points (must be odd integer)
- **Requirement**: Linearly-spaced frequency samples
- **Reference**: Savitzky & Golay (1964), Anal. Chem.

### 4. Linear Rectangular

**Function**: `linear_rectangular(frequencies, spectrum, fcs, bandwidth=0.5)`

- **Type**: Linear frequency scale, boxcar window
- **Default bandwidth**: 0.5 Hz
- **Description**: Simple moving average with constant Hz width

### 5. Log Rectangular

**Function**: `log_rectangular(frequencies, spectrum, fcs, bandwidth=0.05)`

- **Type**: Logarithmic frequency scale, boxcar window
- **Default bandwidth**: 0.05 (log10 scale)
- **Description**: Moving average with constant width in log-frequency

### 6. Linear Triangular

**Function**: `linear_triangular(frequencies, spectrum, fcs, bandwidth=0.5)`

- **Type**: Linear frequency scale, triangular window
- **Default bandwidth**: 0.5 Hz
- **Description**: Weighted average with triangular weights

### 7. Log Triangular

**Function**: `log_triangular(frequencies, spectrum, fcs, bandwidth=0.05)`

- **Type**: Logarithmic frequency scale, triangular window
- **Default bandwidth**: 0.05 (log10 scale)
- **Description**: Weighted average with triangular weights in log-frequency

## Smoothing Operator Registry

```python
SMOOTHING_OPERATORS = {
    "konno_and_ohmachi": konno_and_ohmachi,
    "parzen": parzen,
    "savitzky_and_golay": savitzky_and_golay,
    "linear_rectangular": linear_rectangular,
    "log_rectangular": log_rectangular,
    "linear_triangular": linear_triangular,
    "log_triangular": log_triangular,
}
```

## Function Signature

All smoothing functions share this interface:

```python
def smoothing_function(
    frequencies: ndarray,   # Input frequency array (nfrequency,)
    spectrum: ndarray,      # Spectra to smooth (nspectrum, nfrequency)
    fcs: ndarray,           # Center frequencies for output
    bandwidth: float        # Smoothing width parameter
) -> ndarray:               # Returns (nspectrum, len(fcs))
```

## Usage in Settings

```python
from hvsrpy import HvsrTraditionalProcessingSettings
import numpy as np

settings = HvsrTraditionalProcessingSettings(
    smoothing=dict(
        operator="konno_and_ohmachi",  # or any of the 7 operators
        bandwidth=40,
        center_frequencies_in_hz=np.geomspace(0.1, 50, 200)
    )
)
```

## Performance Notes

- All operators use `@njit(cache=True)` decorator
- Smoothing applied in batch to all spectra at once
- Center frequencies (`fcs`) define output resolution
- Log-spaced `fcs` recommended for HVSR analysis
