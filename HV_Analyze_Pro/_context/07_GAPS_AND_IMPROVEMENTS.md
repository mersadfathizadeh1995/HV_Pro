# Current Gaps and Planned Improvements

## File Import Methods (Need 7 total)

### Currently Supported (2)
1. ✅ ASCII/TXT (OSCAR format, 4-column)
2. ✅ MiniSEED (via ObsPy)

### Needed (5 more)
3. ❌ **SAC format** - Common seismology format
4. ❌ **GCF format** - Güralp instruments
5. ❌ **SEG-Y format** - Exploration seismology
6. ❌ **Generic CSV** - Flexible column mapping
7. ❌ **Raw binary** - Various vendor formats

---

## Smoothing Methods (Need 7 total)

### Currently Supported (1)
1. ✅ Konno-Ohmachi smoothing

### Needed (6 more)
2. ❌ **Parzen smoothing** - Window-based
3. ❌ **Constant bandwidth** - Fixed Hz width
4. ❌ **Log-normal smoothing** - Statistical
5. ❌ **Triangular smoothing** - Simple average
6. ❌ **Savitzky-Golay** - Polynomial filter
7. ❌ **No smoothing** - Raw spectra option

---

## Processing Methods (Comprehensive)

### Pre-processing (Currently Missing)
- ❌ Linear detrending
- ❌ Polynomial detrending
- ❌ Bandpass filtering
- ❌ Highpass filtering
- ❌ Lowpass filtering
- ❌ Decimation/Resampling
- ❌ Baseline correction
- ❌ Instrument response removal
- ❌ Unit conversion

### Spectral Methods (Currently: FFT only)
- ✅ FFT with tapering
- ❌ Welch's method (PWELCH)
- ❌ Multitaper method
- ❌ Lomb-Scargle (irregular sampling)

### Horizontal Combination (4 supported)
- ✅ Geometric mean (sqrt(E*N))
- ✅ Arithmetic mean
- ✅ Quadratic (sqrt(E²+N²))
- ✅ Maximum envelope

### Missing Features
- ❌ Diffuse field correction
- ❌ Site-to-reference spectral ratio (SSR)
- ❌ Earthquake HVSR (eHVSR)
- ❌ Phase velocity extraction

---

## QC Algorithms

### Currently Implemented (9)
1. ✅ Amplitude rejection
2. ✅ Quality threshold
3. ✅ STA/LTA transient
4. ✅ Frequency spike
5. ✅ Statistical outlier (IQR)
6. ✅ HVSR amplitude check
7. ✅ Flat peak detection
8. ✅ Cox FDWRA
9. ✅ Isolation Forest (ML)

### Needed
- ❌ Cross-correlation rejection
- ❌ Spectral coherence
- ❌ Polarization analysis
- ❌ Zero-crossing checks
- ❌ Kurtosis-based
- ❌ Energy distribution

---

## Structural Improvements Needed

### Package Architecture
```
hvsr_pro/
├── api/              # ✅ Exists
├── cli/              # ⚠️ Basic, needs expansion
├── gui/              # ✅ Exists, needs modularization
├── core/             # ✅ Exists
├── io/               # ❌ Should consolidate loaders/writers
│   ├── readers/      # All file readers
│   └── writers/      # All export formats
├── processing/       # ✅ Good structure
│   ├── spectral/     # ❌ Separate from hvsr/
│   ├── filters/      # ❌ Pre-processing filters
│   └── ...
├── models/           # ❌ Consolidate data models
├── utils/            # ✅ Exists
└── visualization/    # ✅ Exists
```

### GUI Modularization
- Separate business logic from UI
- Use MVC/MVP pattern
- Signals/slots for communication
- Plugin architecture for extensions

### CLI Enhancement
- Complete command-line interface
- Config file support
- Scripting capabilities

---

## Reference Package for Methods

Will receive another package (`hvsrpy` or similar) to reference for:
- Additional import formats
- Smoothing algorithms
- Processing methods
- QC algorithms

**Note:** Do NOT directly import from reference package. Rewrite and adapt methods.
