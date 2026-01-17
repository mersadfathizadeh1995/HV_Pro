# Data Structures

## TimeSeries Class

Single-component time series data container.

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `amplitude` | ndarray | Time-domain samples |
| `dt_in_seconds` | float | Sample interval |
| `n_samples` | int | Number of samples |
| `fs` | float | Sampling frequency (Hz) |
| `fnyq` | float | Nyquist frequency |

### Methods

```python
from hvsrpy import TimeSeries

ts = TimeSeries(amplitude, dt_in_seconds)

# Time operations
ts.time()                              # Returns time vector
ts.trim(start_time, end_time)          # Trim in-place
ts.split(window_length_in_seconds)     # Split into windows -> list[TimeSeries]

# Signal processing
ts.detrend(type="linear")              # "linear" or "constant"
ts.window(type="tukey", width=0.1)     # Apply taper
ts.butterworth_filter(fcs_in_hz, order=5)  # Bandpass/highpass/lowpass

# Constructors
TimeSeries.from_trace(obspy_trace)     # From ObsPy Trace
TimeSeries.from_timeseries(ts)         # Copy constructor
```

## SeismicRecording3C Class

Three-component seismic recording container.

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `ns` | TimeSeries | North-South component |
| `ew` | TimeSeries | East-West component |
| `vt` | TimeSeries | Vertical component |
| `degrees_from_north` | float | Sensor orientation |
| `meta` | dict | Metadata dictionary |

### Methods

```python
from hvsrpy import SeismicRecording3C

record = SeismicRecording3C(ns, ew, vt, degrees_from_north=0., meta=None)

# Time operations (applied to all components)
record.trim(start_time, end_time)
record.split(window_length_in_seconds)  # -> list[SeismicRecording3C]

# Signal processing (applied to all components)
record.detrend(type="linear")
record.window(type="tukey", width=0.1)
record.butterworth_filter(fcs_in_hz, order=5)

# Orientation
record.orient_sensor_to(degrees_from_north)  # Rotate horizontals

# Serialization
record.save(fname)                      # Save to JSON
SeismicRecording3C.load(fname)          # Load from JSON

# Copy
SeismicRecording3C.from_seismic_recording_3c(record)
```

### Component Validation

- All 3 components must have same `dt_in_seconds`
- All 3 components must have same `n_samples`
- Validation performed at construction

## Relationship Flow

```
File (MiniSEED, SAC, etc.)
    ↓ read_single()
SeismicRecording3C
    ├── ns: TimeSeries
    ├── ew: TimeSeries
    └── vt: TimeSeries
    ↓ preprocess() + split()
list[SeismicRecording3C]  (windows)
    ↓ process()
HvsrTraditional / HvsrAzimuthal / HvsrDiffuseField
```

## Key Design Patterns

1. **Immutable-ish**: Most operations modify in-place but return None
2. **Copy constructors**: `from_timeseries()`, `from_seismic_recording_3c()`
3. **Metadata tracking**: `meta` dict tracks all operations applied
4. **Similarity checks**: `is_similar()` for comparing objects
5. **JSON serialization**: `save()`/`load()` for persistence
