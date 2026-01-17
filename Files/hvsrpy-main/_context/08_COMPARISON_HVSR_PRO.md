# Comparison: hvsrpy vs hvsr_pro

## Feature Comparison

| Feature | hvsrpy | hvsr_pro |
|---------|--------|----------|
| **File Formats** | 6 (MiniSEED, SAF, MiniShark, SAC, GCF, PEER) | 2 (TXT/ASCII, MiniSEED) |
| **Smoothing Methods** | 7 | 1 (Konno-Ohmachi) |
| **Horizontal Combination** | 9+ methods | 4 methods |
| **Window Rejection** | 5 algorithms | 9 algorithms |
| **SESAME Criteria** | Yes (automated) | Partial |
| **Azimuthal Analysis** | Yes (HvsrAzimuthal) | Yes (separate tab) |
| **Spatial Analysis** | Yes (HvsrSpatial) | No |
| **Diffuse Field** | Yes (HvsrDiffuseField) | No |
| **GUI** | No | Yes (PyQt5) |
| **CLI** | Yes | No |
| **Lognormal Statistics** | Native support | Limited |
| **Numba JIT** | Yes (smoothing) | No |

## Capabilities to Adopt from hvsrpy

### 1. File Formats (Add 4 more)

- **SAF** (SESAME ASCII Format)
- **SAC** (Seismic Analysis Code)
- **GCF** (Guralp Compressed Format)
- **PEER** (Pacific Earthquake Engineering Research)

### 2. Smoothing Methods (Add 6 more)

```python
# From hvsrpy.smoothing
- parzen
- savitzky_and_golay
- linear_rectangular
- log_rectangular
- linear_triangular
- log_triangular
```

### 3. Horizontal Combination Methods (Add 5+ more)

```python
# From hvsrpy.processing
- rotdpp (percentile across azimuths)
- single_azimuth (directional)
- total_horizontal_energy / vector_summation
- effective_amplitude_spectrum
```

### 4. Processing Types

- **Diffuse Field HVSR** (Sánchez-Sesma et al. 2011)
- **PSD Processing** (Power Spectral Density)

### 5. Window Rejection

- **STA/LTA** time-domain rejection
- **Maximum Value** threshold rejection
- **Isolation Forest** ML-based (scikit-learn)
- **Student's t** statistical rejection

### 6. SESAME Criteria

- Automated reliability checks (3 criteria)
- Automated clarity checks (6 criteria)
- Verbose output with pass/fail

### 7. Statistics

- Native lognormal distribution support
- Weighted statistics for azimuthal (Cheng et al. 2020)
- Covariance computation

## Architecture Differences

| Aspect | hvsrpy | hvsr_pro |
|--------|--------|----------|
| Data Container | `SeismicRecording3C` | `SeismicData` |
| Result Container | `HvsrTraditional` | `HVSRResult` |
| Settings | Dataclass-based `Settings` | `ProcessingConfig` dataclass |
| Processing | Functional (`preprocess`, `process`) | Class-based (`HVSRProcessor`) |
| File Loading | Auto-detect with `read_single` | Explicit loader selection |

## Integration Strategy

1. **Do NOT directly import** from hvsrpy
2. **Rewrite and adapt** functions to hvsr_pro architecture
3. **Maintain** hvsr_pro's class-based design
4. **Add** missing file loaders following `BaseDataLoader` pattern
5. **Extend** `HVSRProcessor` with new smoothing/combination methods
6. **Add** SESAME criteria as separate utility module
7. **Integrate** new rejection algorithms into `RejectionEngine`

## Priority Features to Add

1. **Smoothing methods** (6 new) - High impact, moderate effort
2. **File formats** (4 new) - High value for users
3. **SESAME criteria** - Standard validation
4. **Horizontal combination methods** - Processing flexibility
5. **Lognormal statistics** - Scientific correctness
6. **Diffuse field HVSR** - Advanced capability
