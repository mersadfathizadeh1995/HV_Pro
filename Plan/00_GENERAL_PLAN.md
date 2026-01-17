# HVSR Pro Enhancement Plan

## Goal
Enhance hvsr_pro to have feature parity with hvsrpy while maintaining:
- Full GUI capabilities
- Modular architecture (core functions usable via API/CLI)
- Clean separation of concerns

## Reference Package
**hvsrpy** (D:\Research\Narm_Afzar\Git_hub\HV_Pro\Files\hvsrpy-main)
- Academic HVSR package by Joseph P. Vantassel (Virginia Tech)
- Well-documented, rigorous statistical methods
- Test data available at: `Files\hvsrpy-main\hvsrpy\gallery\data`

---

## Feature Gap Analysis

### 1. Data Loading (Priority: HIGH)
| Feature | hvsrpy | hvsr_pro | Action |
|---------|--------|----------|--------|
| MiniSEED | ✅ | ✅ | None |
| ASCII/TXT | ❌ | ✅ | None |
| SAF (SESAME ASCII) | ✅ | ❌ | **Add** |
| SAC | ✅ | ❌ | **Add** |
| GCF (Guralp) | ✅ | ❌ | **Add** |
| PEER | ✅ | ❌ | **Add** |
| Auto-detection | ✅ | ❌ | **Add** |
| Multi-file mapping | ✅ | ✅ | None |

### 2. Smoothing Methods (Priority: HIGH)
| Method | hvsrpy | hvsr_pro | Action |
|--------|--------|----------|--------|
| Konno-Ohmachi | ✅ | ✅ | Enhance params |
| Parzen | ✅ | ❌ | **Add** |
| Savitzky-Golay | ✅ | ❌ | **Add** |
| Linear Rectangular | ✅ | ❌ | **Add** |
| Log Rectangular | ✅ | ❌ | **Add** |
| Linear Triangular | ✅ | ❌ | **Add** |
| Log Triangular | ✅ | ❌ | **Add** |
| No Smoothing | ❌ | ❌ | **Add** |

### 3. Horizontal Combination (Priority: MEDIUM)
| Method | hvsrpy | hvsr_pro | Action |
|--------|--------|----------|--------|
| Geometric Mean | ✅ | ✅ | None |
| Arithmetic Mean | ✅ | ✅ | None |
| Quadratic Mean | ✅ | ✅ | None |
| Maximum | ✅ | ✅ | None |
| Total Horizontal Energy | ✅ | ❌ | **Add** |
| Vector Summation | ✅ | ❌ | **Add** |
| Single Azimuth | ✅ | ❌ | **Add** |
| RotDpp (percentile) | ✅ | ❌ | **Add** |

### 4. Processing Methods (Priority: MEDIUM)
| Feature | hvsrpy | hvsr_pro | Action |
|---------|--------|----------|--------|
| Traditional HVSR | ✅ | ✅ | None |
| Azimuthal HVSR | ✅ | ✅ | Compare impl |
| Diffuse Field HVSR | ✅ | ❌ | **Add** |
| PSD Processing | ✅ | ❌ | **Add** |
| Spatial Statistics | ✅ | ❌ | Consider later |

### 5. Window Rejection (Priority: LOW - already comprehensive)
| Algorithm | hvsrpy | hvsr_pro | Action |
|-----------|--------|----------|--------|
| STA/LTA | ✅ | ✅ | None |
| Amplitude | ✅ | ✅ | None |
| Cox FDWRA | ✅ | ✅ | Compare impl |
| Isolation Forest | ✅ (beta) | ✅ | None |
| Student's t | ✅ (beta) | ❌ | Consider |
| Statistical Outlier | ❌ | ✅ | Keep |
| Multiple others | ❌ | ✅ | Keep |

### 6. Statistics & Quality (Priority: MEDIUM)
| Feature | hvsrpy | hvsr_pro | Action |
|---------|--------|----------|--------|
| Lognormal Stats | ✅ (native) | Limited | **Enhance** |
| Normal Stats | ✅ | ✅ | None |
| SESAME Criteria | ✅ (automated) | Partial | **Enhance** |
| Weighted Stats | ✅ | ❌ | **Add** |

### 7. API & CLI (Priority: HIGH)
| Feature | hvsrpy | hvsr_pro | Action |
|---------|--------|----------|--------|
| Python API | ✅ (excellent) | ✅ (basic) | **Enhance** |
| CLI | ✅ | ❌ | **Add** |
| Batch Processing | ✅ | ✅ | None |
| Config Files | ✅ | ✅ | None |

---

## Implementation Phases

### Phase A: Core Infrastructure (Foundation)
*Estimated: 3-4 sessions*

1. **Smoothing Module** (core/processing/smoothing/)
   - Create modular smoothing functions (no Numba dependency)
   - Settings dataclass with validation
   - GUI dialog for smoothing selection
   - Registry pattern for extensibility

2. **Statistics Module** (core/processing/statistics/)
   - Lognormal mean/std/nth_std functions
   - Normal statistics (existing)
   - Factory pattern for distribution selection
   - SESAME criteria functions

### Phase B: Data Loading Enhancement
*Estimated: 2-3 sessions*

1. **New Loaders** (loaders/)
   - SAF loader (SESAME ASCII Format)
   - SAC loader (via ObsPy)
   - GCF loader (via ObsPy)
   - PEER loader (custom parser)
   - Auto-detection utility

2. **GUI Integration**
   - Update DataInputDialog with format selection
   - Add format-specific options panels
   - Channel mapping for all formats

### Phase C: Horizontal Combination Methods
*Estimated: 1-2 sessions*

1. **Processing Functions** (processing/hvsr/)
   - Add remaining combination methods
   - Single azimuth processing
   - RotDpp percentile method

2. **GUI Integration**
   - Dropdown in processing settings
   - Azimuth input for single_azimuth
   - Percentile input for RotDpp

### Phase D: Advanced Processing
*Estimated: 2-3 sessions*

1. **Diffuse Field HVSR** (processing/hvsr/)
   - Port from hvsrpy
   - Adapt to hvsr_pro structures
   - Add GUI option

2. **PSD Processing** (processing/spectral/)
   - Power spectral density computation
   - Component-wise PSD output

### Phase E: API & CLI Enhancement
*Estimated: 2 sessions*

1. **Enhanced API** (api/)
   - Comprehensive HVSRAnalysis class
   - All processing options exposed
   - Result export methods

2. **CLI Implementation** (cli/)
   - Process single file
   - Batch processing
   - Config file support

---

## Architecture Guidelines

### Modular Design Pattern
```
Feature Implementation Order:
1. Core function (processing/, no GUI dependencies)
2. Settings dataclass (config/schemas.py)
3. API wrapper (api/)
4. CLI command (cli/)
5. GUI components (gui/)
```

### File Size Limits
- Core functions: Max 200 lines per file
- GUI components: Max 300 lines per file
- If exceeding: Split into package with sections/

### Signal Flow (GUI)
```
GUI Component → Signal → Controller → Core Function → Result
                                   ↓
                              Settings from Config
```

---

## Suggested Starting Point

**Recommendation: Start with Smoothing Methods (Phase A.1)**

Reasons:
1. **Foundational** - Used by all HVSR processing
2. **Self-contained** - Minimal dependencies
3. **Testable** - Easy to verify correctness
4. **High impact** - Users immediately benefit
5. **Good pattern** - Establishes modular architecture pattern

The smoothing implementation will establish:
- Registry pattern for extensible methods
- Settings dataclass pattern
- GUI dialog integration pattern
- Core → API → GUI workflow

After smoothing, recommend proceeding with:
1. Statistics enhancement (builds on smoothing testing)
2. Data loaders (independent, high user value)
3. Horizontal combination (quick wins)
4. Advanced processing (more complex)
5. API/CLI (integrates all above)

---

## Reference Files

### hvsrpy Source
- `Files/hvsrpy-main/hvsrpy/hvsrpy/smoothing.py` - All smoothing methods
- `Files/hvsrpy-main/hvsrpy/hvsrpy/processing.py` - Horizontal combination
- `Files/hvsrpy-main/hvsrpy/hvsrpy/statistics.py` - Lognormal statistics
- `Files/hvsrpy-main/hvsrpy/hvsrpy/data_wrangler.py` - File loading
- `Files/hvsrpy-main/hvsrpy/hvsrpy/sesame.py` - SESAME criteria

### Test Data
- `Files/hvsrpy-main/hvsrpy/gallery/data/` - Various format examples

### hvsr_pro Architecture
- `HV_Analyze_Pro/_context/architecture_map.md` - Current structure
- `HV_Analyze_Pro/.cursor/rules/refactor.md` - Coding guidelines
