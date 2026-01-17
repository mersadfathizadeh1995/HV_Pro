# Current Gaps and Planned Improvements

## Reference Package
- **hvsrpy** by Joseph P. Vantassel (Virginia Tech)
- Location: `D:\Research\Narm_Afzar\Git_hub\HV_Pro\Files\hvsrpy-main`
- Test data: `Files/hvsrpy-main/hvsrpy/gallery/data/`

---

## File Import Methods

### Currently Supported (2)
1. ✅ ASCII/TXT (OSCAR format, 4-column)
2. ✅ MiniSEED (via ObsPy)

### To Add from hvsrpy (4)
3. ❌ **SAF** (SESAME ASCII Format) - `hvsrpy/data_wrangler.py`
4. ❌ **SAC** (Seismic Analysis Code) - via ObsPy
5. ❌ **GCF** (Guralp Compressed Format) - via ObsPy
6. ❌ **PEER** (Pacific Earthquake Engineering Research) - custom parser

### Also Consider
7. ❌ **Generic CSV** - Flexible column mapping
8. ❌ **Auto-detection** - Try all formats until one succeeds

---

## Smoothing Methods

### Currently Supported (1)
1. ✅ Konno-Ohmachi (bandwidth=40)

### To Add from hvsrpy (6)
2. ❌ **Parzen** - Linear freq scale, constant Hz width
3. ❌ **Savitzky-Golay** - Polynomial filter (odd integer bandwidth)
4. ❌ **Linear Rectangular** - Boxcar window, linear scale
5. ❌ **Log Rectangular** - Boxcar window, log scale
6. ❌ **Linear Triangular** - Triangular weights, linear scale
7. ❌ **Log Triangular** - Triangular weights, log scale

### Also Consider
8. ❌ **No Smoothing** - Raw spectra option

**Implementation Note:** Each smoothing method has a `bandwidth` parameter with different meanings. Need settings dialog per method.

---

## Horizontal Combination Methods

### Currently Supported (4)
1. ✅ Geometric mean (sqrt(N*E)) - recommended
2. ✅ Arithmetic mean ((N+E)/2)
3. ✅ Quadratic mean (sqrt((N²+E²)/2))
4. ✅ Maximum envelope (max(N,E))

### To Add from hvsrpy (4)
5. ❌ **Total Horizontal Energy** - sqrt(N²+E²)
6. ❌ **Vector Summation** - Same as total_horizontal_energy
7. ❌ **Single Azimuth** - N*cos(θ) + E*sin(θ)
8. ❌ **RotDpp** - Percentile across azimuths

---

## Processing Methods

### Currently Supported
- ✅ Traditional HVSR (FFT + smoothing + combination)
- ✅ Azimuthal HVSR (multiple azimuths)

### To Add from hvsrpy
- ❌ **Diffuse Field HVSR** - PSD-based, theoretical (Sánchez-Sesma et al. 2011)
- ❌ **PSD Processing** - Power spectral density output

---

## Statistics

### Currently Supported
- ✅ Normal distribution mean/std
- ❌ Limited lognormal support

### To Enhance from hvsrpy
- ❌ **Native Lognormal Statistics** - exp(mean(log(x))), geometric std
- ❌ **nth Standard Deviation Factory** - ±nσ curves
- ❌ **Weighted Statistics** - For azimuthal weighting (Cheng et al. 2020)

---

## Quality Control

### Currently Implemented (9 algorithms)
1. ✅ Amplitude rejection
2. ✅ Quality threshold
3. ✅ STA/LTA transient
4. ✅ Frequency spike
5. ✅ Statistical outlier (IQR)
6. ✅ HVSR amplitude check
7. ✅ Flat peak detection
8. ✅ Cox FDWRA
9. ✅ Isolation Forest (ML)

### SESAME Criteria (Partial)
- ❌ Need automated reliability checks (3 criteria)
- ❌ Need automated clarity checks (6 criteria)
- ❌ Verbose pass/fail output

---

## API & CLI

### API (api/)
- ✅ HVSRAnalysis class (basic)
- ✅ batch_process function
- ❌ Need comprehensive processing options exposure
- ❌ Need all smoothing/combination methods accessible

### CLI (cli/)
- ❌ No command-line interface yet
- ❌ Need: `hvsr_pro process input.mseed --output results/`
- ❌ Need: `hvsr_pro batch folder/ --parallel 4`
- ❌ Need: Config file support

---

## Implementation Priority

### Phase A: Core Infrastructure (Start Here)
1. **Smoothing Module** - New methods with registry pattern
2. **Statistics Module** - Lognormal functions

### Phase B: Data Loading
1. New file format loaders (SAF, SAC, GCF, PEER)
2. Auto-detection utility

### Phase C: Processing Enhancement
1. Additional horizontal combination methods
2. Diffuse field HVSR

### Phase D: API & CLI
1. Enhanced HVSRAnalysis class
2. CLI implementation

---

## Reference Files for Implementation

| Feature | hvsrpy Source |
|---------|--------------|
| Smoothing | `hvsrpy/smoothing.py` |
| Processing | `hvsrpy/processing.py` |
| Statistics | `hvsrpy/statistics.py` |
| Data Loading | `hvsrpy/data_wrangler.py` |
| SESAME | `hvsrpy/sesame.py` |
| Settings | `hvsrpy/settings.py` |

**Rule:** Do NOT directly import from hvsrpy. Adapt and rewrite for hvsr_pro architecture.
