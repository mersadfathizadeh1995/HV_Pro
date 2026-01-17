# Data I/O - File Formats

## Supported File Formats (6 total)

### 1. MiniSEED (`_read_mseed`)

- **Format**: Standard seismic data format
- **Input**: Single file with 3 components OR list of 3 files (one per component)
- **Channel naming**: NEZ, XYZ, 123, or 12Z conventions
- **Uses**: ObsPy for reading

```python
from hvsrpy import read_single
record = read_single("data.miniseed")
# or
record = read_single(["data_N.mseed", "data_E.mseed", "data_Z.mseed"])
```

### 2. SAF - SESAME ASCII Format (`_read_saf`)

- **Format**: SESAME project standard text format
- **Input**: Single file with all 3 components
- **Parses**: NPTS, FS, channel ordering, NORTH_ROT
- **Reference**: http://sesame.geopsy.org

### 3. MiniShark (`_read_minishark`)

- **Format**: MiniShark instrument proprietary format
- **Input**: Single text file
- **Parses**: NPTS, FS, GAIN, CONVERSION factor
- **Auto-applies**: Gain and conversion corrections

### 4. SAC - Seismic Analysis Code (`_read_sac`)

- **Format**: SAC binary format (little or big endian)
- **Input**: List of 3 files (one per component)
- **Uses**: ObsPy with automatic endianness detection

```python
record = read_single(["data.BHN.sac", "data.BHE.sac", "data.BHZ.sac"])
```

### 5. GCF - Guralp Compressed Format (`_read_gcf`)

- **Format**: Guralp instrument proprietary format
- **Input**: Single file with all 3 components
- **Uses**: ObsPy for reading

### 6. PEER Format (`_read_peer`)

- **Format**: Pacific Earthquake Engineering Research format
- **Input**: List of 3 files (one per component)
- **Parses**: Direction, NPTS, DT from header
- **Handles**: Numeric orientation angles

## Data Reading Functions

### `read_single(fnames, ...)`

Reads file(s) for a single recording with auto-format detection.

```python
from hvsrpy import read_single

record = read_single(
    fnames="data.miniseed",           # or list of files
    obspy_read_kwargs=None,           # custom ObsPy args
    degrees_from_north=None,          # sensor orientation
    verbose=False                     # debug output
)
# Returns: SeismicRecording3C
```

### `read(fnames, ...)`

Reads multiple recordings (batch).

```python
from hvsrpy import read

records = read(
    fnames=["file1.mseed", "file2.mseed"],
    obspy_read_kwargs=None,
    degrees_from_north=None,
    verbose=False
)
# Returns: list of SeismicRecording3C
```

## Internal Format Detection

The `READ_FUNCTION_DICT` maps format names to reader functions:

```python
READ_FUNCTION_DICT = {
    "mseed": _read_mseed,
    "saf": _read_saf,
    "minishark": _read_minishark,
    "sac": _read_sac,
    "gcf": _read_gcf,
    "peer": _read_peer
}
```

Auto-detection tries each format in order until one succeeds.

## Component Orientation Handling

- Supports NEZ, XYZ, 123, 12Z channel naming
- `degrees_from_north` parameter for sensor rotation
- Automatic trimming to common time range for multi-file inputs
- Rotation applied via `orient_sensor_to()` method

## Key Implementation Details

- Uses ObsPy `Stream` and `Trace` objects internally
- Converts to `TimeSeries` objects after loading
- All readers return `SeismicRecording3C` objects
- Metadata preserved in `meta` dictionary
