# hvsrpy Package Analysis

## Overview
**Author:** Joseph P. Vantassel (Virginia Tech)  
**Location:** `D:\Research\Narm_Afzar\Git_hub\HV_Pro\Codes_To_use\hvsrpy-main\hvsrpy-main`  
**License:** GPLv3  
**Purpose:** Open-source Python package for HVSR processing of microtremor and earthquake recordings. Well-documented academic package with rigorous statistical methods.

---

## Package Architecture

```
hvsrpy/
├── __init__.py               # Package exports
├── cli.py                    # Command-line interface
├── constants.py              # Physical constants
├── data_wrangler.py          # Data loading (read, read_single)
├── frequency_amplitude_curve.py  # Base F-A curve class
├── hvsr_curve.py             # HvsrCurve class
├── hvsr_traditional.py       # HvsrTraditional (main class)
├── hvsr_azimuthal.py         # HvsrAzimuthal (azimuthal variability)
├── hvsr_diffuse_field.py     # HvsrDiffuseField (theoretical)
├── hvsr_spatial.py           # HvsrSpatial (spatial statistics)
├── hvsr_geopsy.py            # Geopsy format support
├── instrument_response.py    # Instrument response removal
├── interact.py               # Interactive tools
├── metadata.py               # Version metadata
├── object_io.py              # Save/load objects
├── postprocessing.py         # Plotting utilities
├── preprocessing.py          # Data preprocessing
├── processing.py             # Core HVSR processing
├── psd.py                    # Power spectral density
├── regex.py                  # Regex utilities
├── seismic_recording_3c.py   # SeismicRecording3C class
├── sesame.py                 # SESAME criteria
├── settings.py               # Configuration settings
├── smoothing.py              # Smoothing algorithms
├── statistics.py             # Statistical functions
├── timeseries.py             # TimeSeries class
└── window_rejection.py       # Window rejection algorithms
```

---

## Key Components

### 1. Core Classes

#### HvsrTraditional
- Main HVSR analysis class
- Attributes:
  - `amplitude`: 2D array (curves × frequencies)
  - `frequency`: Frequency vector
  - `valid_window_boolean_mask`: Window validity mask
  - `valid_peak_boolean_mask`: Peak validity mask
- Methods:
  - `mean_curve(distribution)`: Mean HVSR curve
  - `std_curve(distribution)`: Standard deviation curve
  - `nth_std_curve(n, distribution)`: nth std curve
  - `mean_fn_frequency(distribution)`: Mean peak frequency
  - `std_fn_frequency(distribution)`: Peak frequency std
  - `update_peaks_bounded(search_range_in_hz)`: Update peaks

#### HvsrAzimuthal
- Handles azimuthal variability in HVSR
- Contains multiple HvsrTraditional objects (one per azimuth)
- Implements Cheng et al. (2020) methodology

#### HvsrDiffuseField
- Theoretical HVSR under diffuse field assumption
- Based on Sánchez-Sesma et al. (2011)

#### HvsrSpatial
- Spatial statistics for distributed measurements
- Voronoi tessellation weighting
- Based on Cheng et al. (2021)

### 2. Window Rejection (`window_rejection.py`)

#### Available Algorithms

| Function | Description | Reference |
|----------|-------------|-----------|
| `sta_lta_window_rejection()` | STA/LTA ratio rejection | Standard |
| `maximum_value_window_rejection()` | Amplitude threshold | Standard |
| `frequency_domain_window_rejection()` | **Cox et al. (2020) FDWRA** | Key algorithm |
| `manual_window_rejection()` | Interactive rejection | SESAME-based |
| `student_t_window_rejection()` | Student's t-distribution (beta) | Novel |
| `isolation_forest_outlier_rejection()` | ML-based (sklearn, beta) | Novel |

#### Cox et al. (2020) FDWRA Implementation
```python
def frequency_domain_window_rejection(hvsr,
                                      n=2,
                                      max_iterations=50,
                                      distribution_fn="lognormal",
                                      distribution_mc="lognormal",
                                      search_range_in_hz=(None, None),
                                      find_peaks_kwargs=None):
```
- Iteratively removes windows with peaks outside ±n std
- Supports both lognormal and normal distributions
- Converges when diff < 1% and std change < 0.01

### 3. Statistics (`statistics.py`)

- **Lognormal statistics**: Primary recommendation for f0
- Support for both `normal` and `lognormal` distributions
- Weighted mean/std calculations
- nth standard deviation factory

### 4. Data Loading (`data_wrangler.py`)

Supported formats:
- MiniSEED
- SAF (SESAME ASCII Format)
- MiniShark
- SAC
- GCF
- PEER

### 5. Processing Pipeline

```python
# Typical workflow
from hvsrpy import read, preprocess, process

# Load data
records = read("data.mseed", window_length=30)

# Preprocess
preprocessed = preprocess(records)

# Process HVSR
hvsr = process(preprocessed, method="geometric_mean")

# Apply rejection
from hvsrpy import frequency_domain_window_rejection
frequency_domain_window_rejection(hvsr, n=2)
```

### 6. Horizontal Combination Methods

- `arithmetic_mean`
- `squared_average`
- `quadratic_mean`
- `geometric_mean` (recommended)
- `total_horizontal_energy`
- `vector_summation`
- `maximum_horizontal_value`
- `rotD50`
- `single_azimuth`

---

## Key Features

### 1. Lognormal Statistics
- Consistent uncertainty representation in frequency AND period
- Mean: `exp(mean(log(x)))`
- Std: geometric standard deviation

### 2. SESAME Criteria (`sesame.py`)
- Peak reliability criteria
- Peak clarity criteria
- Automated checking

### 3. CLI Support
```bash
hvsrpy process input.mseed --output results/
hvsrpy batch folder/ --parallel 4
```

### 4. Comprehensive Documentation
- ReadTheDocs documentation
- Jupyter notebook examples
- Academic citations

---

## Relevance to HVSR Pro

### Features to Adopt/Reference

1. **Cox FDWRA Algorithm**: Reference implementation
2. **Lognormal Statistics**: Proper f0 uncertainty handling
3. **SESAME Criteria**: Standard reliability checks
4. **Multiple Horizontal Methods**: Comprehensive options
5. **Azimuthal Analysis**: Advanced feature
6. **Spatial Statistics**: Multi-station analysis

### Code Quality

- Well-tested (CircleCI, codecov)
- Type hints
- Comprehensive docstrings
- Academic rigor

### Differences from hvsr_pro

| Feature | hvsrpy | hvsr_pro |
|---------|--------|----------|
| GUI | No GUI | PyQt5 GUI |
| Interactive | Matplotlib only | Full interactive canvas |
| Batch | CLI-based | GUI-based |
| Window QC | Cox FDWRA primary | Multiple pipelines |
| Peak detection | scipy.find_peaks | Multiple methods |
| Statistics | Lognormal focus | Both supported |

---

## Dependencies
- numpy
- scipy
- matplotlib
- obspy (data loading)
- scikit-learn (optional, ML rejection)
