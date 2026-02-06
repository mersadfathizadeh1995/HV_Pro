# Current Gaps and Planned Improvements

## Reference Package
- **hvsrpy** by Joseph P. Vantassel (Virginia Tech)
- Location: `D:\Research\Narm_Afzar\Git_hub\HV_Pro\Files\hvsrpy-main`
- Test data: `Files/hvsrpy-main/hvsrpy/gallery/data/`

---

## File Import Methods

### All Formats Implemented (8) - COMPLETED
1. ✅ ASCII/TXT (OSCAR format, 4-column)
2. ✅ MiniSEED (via ObsPy) - single file or 3 files
3. ✅ SAF (SESAME ASCII Format) - single file
4. ✅ SAC (Seismic Analysis Code) - 3 files via ObsPy
5. ✅ GCF (Guralp Compressed Format) - single file via ObsPy
6. ✅ PEER (Pacific Earthquake Engineering Research) - 3 files custom parser
7. ✅ MiniShark - proprietary format (single file, 3 components)
8. ✅ HVSRPy JSON (SeismicRecording3C) - native JSON serialization

**Location:** `loaders/` package
- `config.py` - LoaderConfig dataclasses per format
- `patterns.py` - Compiled regex for SAF/PEER/MiniShark parsing
- `orientation.py` - Trace orientation utilities (NEZ, XYZ, 123)
- `preview.py` - PreviewExtractor for all formats
- `base_loader.py` - BaseDataLoader abstract base
- `saf_loader.py` - SESAME ASCII Format loader
- `sac_loader.py` - SAC format (3 separate files)
- `gcf_loader.py` - Guralp Compressed Format
- `peer_loader.py` - PEER NGA format (3 separate files)
- `minishark_loader.py` - MiniShark proprietary format
- `srecord3c_loader.py` - HVSRPy JSON format
- `__init__.py` - FORMAT_INFO registry, get_file_filter(), detect_format()

**GUI Integration:**
- SingleFileTab: Format selector (auto, txt, miniseed, saf, gcf, minishark, srecord3c_json)
- MultiComponentTab: SAC/PEER format selector (3-file browser)
- Degrees from north input for sensor orientation

### Also Consider (Future)
- ❌ **Generic CSV** - Flexible column mapping (basic support exists)
- ✅ **Auto-detection** - Via FORMAT_INFO registry and can_load()

---

## Smoothing Methods

### All Methods Implemented (8) - COMPLETED
1. ✅ Konno-Ohmachi (bandwidth=40, inverse width)
2. ✅ Parzen (bandwidth=0.5 Hz, linear freq scale)
3. ✅ Savitzky-Golay (bandwidth=9 points, odd integer)
4. ✅ Linear Rectangular (bandwidth=0.5 Hz, boxcar)
5. ✅ Log Rectangular (bandwidth=0.05 log10, boxcar)
6. ✅ Linear Triangular (bandwidth=0.5 Hz, weighted)
7. ✅ Log Triangular (bandwidth=0.05 log10, weighted)
8. ✅ No Smoothing (interpolation only)

**Location:** `processing/smoothing/` package
- `methods.py` - 8 smoothing functions
- `settings.py` - SmoothingMethod enum, SmoothingConfig dataclass
- `registry.py` - Dynamic method lookup

**GUI Integration:** ProcessingSettingsPanel has method selector + advanced dialog.

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
- ✅ configure_smoothing() method for smoothing selection
- ❌ Need comprehensive processing options exposure
- ❌ Need all combination methods accessible

### CLI (cli/)
- ❌ No command-line interface yet
- ❌ Need: `hvsr_pro process input.mseed --output results/`
- ❌ Need: `hvsr_pro batch folder/ --parallel 4`
- ❌ Need: Config file support

---

## Implementation Priority

### Phase A: Core Infrastructure (COMPLETED)
1. ✅ **Smoothing Module** - 8 methods with registry pattern (DONE)
2. ❌ **Statistics Module** - Lognormal functions (TODO)

### Phase B: Data Loading (COMPLETED)
1. ✅ New file format loaders (SAF, SAC, GCF, PEER, MiniShark, SeismicRecording3C)
2. ✅ Auto-detection utility
3. ✅ Orientation utilities (NEZ, XYZ, 123 patterns)
4. ✅ GUI tabs: SingleFileTab, MultiComponentTab
5. ✅ Preview extraction for all formats

### Phase C: Processing Enhancement (NEXT PRIORITY)
1. ❌ **Additional Horizontal Combination Methods**
   - Total Horizontal Energy: sqrt(N² + E²)
   - Single Azimuth: N*cos(θ) + E*sin(θ)
   - RotDpp: Percentile across azimuths
2. ❌ **Lognormal Statistics** - exp(mean(log(x))), geometric std
3. ❌ **SESAME Criteria Automation** - 3 reliability + 6 clarity checks
4. ❌ **Diffuse Field HVSR** - PSD-based method (Sánchez-Sesma et al. 2011)

### Phase D: API & CLI (FUTURE)
1. ✅ Enhanced HVSRAnalysis.load_data() with format/orientation params
2. ❌ CLI implementation (`hvsr_pro process`, `hvsr_pro batch`)
3. ❌ Config file support for batch processing

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

---

## Recommended Next Step

**Priority 1: Additional Horizontal Combination Methods**

This is the most impactful improvement because:
1. Relatively simple to implement (pure functions in `processing/hvsr/`)
2. Enables RotDpp for directional analysis
3. Aligns with hvsrpy feature parity
4. Direct user value for research applications

**Implementation approach:**
1. Add new methods to `processing/hvsr/spectral.py` or create `horizontal_methods.py`
2. Add enum values to processing settings
3. Update `HVSRProcessor` to use selected method
4. Add GUI selector in ProcessingSettingsPanel

**Priority 2: Lognormal Statistics**

Enhances statistical accuracy for HVSR which often follows lognormal distribution.

**Priority 3: SESAME Criteria Automation**

Provides automated reliability/clarity assessment - important for standardized reporting.
