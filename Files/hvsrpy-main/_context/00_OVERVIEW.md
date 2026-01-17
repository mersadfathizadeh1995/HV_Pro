# hvsrpy Package Overview

## Basic Information

- **Package Name**: hvsrpy
- **Version**: Latest (2025)
- **Author**: Joseph P. Vantassel (Virginia Tech)
- **License**: GPL-3.0
- **Repository**: https://github.com/jpvantassel/hvsrpy
- **Documentation**: https://hvsrpy.readthedocs.io

## Purpose

Open-source Python package for horizontal-to-vertical spectral ratio (HVSR) processing of microtremor and earthquake recordings.

## Package Structure

```
hvsrpy/
├── __init__.py              # Main exports
├── cli.py                   # Command-line interface
├── constants.py             # Package constants
├── data_wrangler.py         # Multi-format file I/O (6 formats)
├── frequency_amplitude_curve.py
├── hvsr_azimuthal.py        # Azimuthal HVSR analysis
├── hvsr_curve.py            # Base HVSR curve class
├── hvsr_diffuse_field.py    # Diffuse field HVSR
├── hvsr_geopsy.py           # Geopsy compatibility
├── hvsr_spatial.py          # Spatial variability analysis
├── hvsr_traditional.py      # Traditional HVSR processing
├── instrument_response.py   # Instrument response removal
├── interact.py              # Interactive plotting utilities
├── metadata.py              # Version info
├── object_io.py             # Serialization/deserialization
├── postprocessing.py        # Plotting and visualization
├── preprocessing.py         # Time-domain preprocessing
├── processing.py            # Core HVSR processing engine
├── psd.py                   # Power spectral density
├── regex.py                 # File parsing regex patterns
├── seismic_recording_3c.py  # 3-component seismic record class
├── sesame.py                # SESAME (2004) criteria
├── settings.py              # Processing settings classes
├── smoothing.py             # 7 smoothing operators
├── statistics.py            # Statistical functions
├── timeseries.py            # TimeSeries class
└── window_rejection.py      # Window rejection algorithms
```

## Key Features

1. **6 File Formats**: MiniSEED, SAF, MiniShark, SAC, GCF, PEER
2. **7 Smoothing Methods**: Konno-Ohmachi, Parzen, Savitzky-Golay, Linear/Log Rectangular, Linear/Log Triangular
3. **9+ Horizontal Combination Methods**: arithmetic_mean, geometric_mean, squared_average, total_horizontal_energy, maximum_horizontal_value, single_azimuth, rotDpp, etc.
4. **4 Processing Types**: Traditional, Azimuthal, Diffuse Field, PSD
5. **5 Window Rejection Algorithms**: STA/LTA, Maximum Value, FDWRA (Cox et al. 2020), Student-t, Isolation Forest
6. **SESAME Criteria**: Automated reliability and clarity checks
7. **CLI Support**: Batch processing with multiprocessing

## Technology Stack

- Python 3.8+
- NumPy, SciPy
- ObsPy (seismic data I/O)
- Matplotlib (visualization)
- Numba (JIT compilation for smoothing)
- scikit-learn (ML-based rejection)

## Main Exports

```python
from hvsrpy import (
    # Data I/O
    read, read_single,
    
    # Data structures
    TimeSeries, SeismicRecording3C,
    
    # HVSR classes
    HvsrCurve, HvsrTraditional, HvsrAzimuthal,
    HvsrDiffuseField, HvsrSpatial,
    
    # Processing
    preprocess, process,
    
    # Window rejection
    sta_lta_window_rejection,
    maximum_value_window_rejection,
    frequency_domain_window_rejection,
    manual_window_rejection,
    
    # Settings
    HvsrPreProcessingSettings,
    HvsrTraditionalProcessingSettings,
    HvsrAzimuthalProcessingSettings,
    # ... more settings classes
)
```

## Documentation Index

| File | Content |
|------|---------|
| 01_DATA_IO.md | File formats and data loading |
| 02_DATA_STRUCTURES.md | TimeSeries, SeismicRecording3C |
| 03_PREPROCESSING.md | Time-domain preprocessing |
| 04_PROCESSING.md | HVSR computation methods |
| 05_SMOOTHING.md | 7 smoothing operators |
| 06_WINDOW_REJECTION.md | QC algorithms |
| 07_HVSR_CLASSES.md | Result container classes |
| 08_SESAME.md | SESAME criteria |
| 09_SETTINGS.md | Configuration classes |
