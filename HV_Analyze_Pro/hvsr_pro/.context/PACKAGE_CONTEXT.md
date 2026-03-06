# HVSR Pro — Complete Package Context

**Version:** 0.2.0  
**Author:** OSCAR HVSR Development Team  
**Purpose:** Professional HVSR (Horizontal-to-Vertical Spectral Ratio) analysis for seismic site characterization.

---

## 1. PACKAGE ARCHITECTURE OVERVIEW

```
hvsr_pro/
├── __init__.py            # Package root — exports all public API
├── core/                  # Data structures, loading, caching, metadata
│   ├── data_structures.py # ComponentData, SeismicData dataclasses
│   ├── data_handler.py    # HVSRDataHandler — universal loader orchestrator
│   ├── data_cache.py      # LRU cache with SHA256 file hashing, memory limits
│   └── metadata.py        # MetadataManager — OSCAR header, MiniSEED, filename parsing
├── loaders/               # Format-specific data loaders (8 formats)
│   ├── base_loader.py     # BaseDataLoader ABC
│   ├── txt_loader.py      # OSCAR ASCII (4-col: Time,E,N,Z)
│   ├── miniseed_loader.py # MiniSEED via ObsPy
│   ├── saf_loader.py      # SESAME ASCII Format
│   ├── sac_loader.py      # SAC (multi-file: 3 component files)
│   ├── gcf_loader.py      # Guralp GCF
│   ├── peer_loader.py     # PEER NGA (.vt2/.at2/.dt2, multi-file)
│   ├── minishark_loader.py# MiniShark seismometer
│   ├── srecord3c_loader.py# hvsrpy JSON (SeismicRecording3C)
│   ├── config.py          # LoaderConfig, SAFConfig, SACConfig, etc.
│   ├── orientation.py     # orient_traces, rotate_horizontals, auto_assign_components
│   ├── patterns.py        # SAF/PEER header parsers
│   └── preview.py         # PreviewExtractor for channel mapper dialog
├── processing/            # Core computation engine
│   ├── windows/           # Window management
│   │   ├── structures.py  # Window, WindowState(Enum), WindowCollection
│   │   ├── manager.py     # WindowManager — create/taper/quality
│   │   ├── peaks.py       # detect_peaks, refine_peak_frequency, SESAME criteria
│   │   └── quality.py     # WindowQualityCalculator (SNR, stationarity, etc.)
│   ├── hvsr/              # HVSR computation
│   │   ├── processor.py   # HVSRProcessor — main engine, parallel support
│   │   ├── structures.py  # HVSRResult, WindowSpectrum, Peak dataclasses
│   │   └── spectral.py    # compute_fft, KO smoothing, H/V ratio, resampling
│   ├── rejection/         # QC/rejection system
│   │   ├── base.py        # BaseRejectionAlgorithm ABC, RejectionResult
│   │   ├── engine.py      # RejectionEngine — pipeline coordinator
│   │   ├── presets.py     # SESAME preset (only preset currently)
│   │   ├── settings.py    # QCSettings, per-algorithm settings dataclasses
│   │   └── algorithms/    # 8 rejection algorithms
│   │       ├── amplitude.py     # AmplitudeRejection
│   │       ├── stalta.py        # STALTARejection
│   │       ├── statistical.py   # QualityThresholdRejection, StatisticalOutlierRejection
│   │       ├── frequency.py     # FrequencyDomainRejection
│   │       ├── hvsr_qc.py       # HVSRAmplitudeRejection, FlatPeakRejection
│   │       ├── cox_fdwra.py     # CoxFDWRARejection (Cox et al. 2020)
│   │       └── ml.py            # IsolationForest (optional)
│   ├── smoothing/         # 7+1 smoothing methods
│   │   ├── methods.py     # konno_ohmachi, parzen, savitzky_golay, 4 rectangular/triangular variants, none
│   │   ├── registry.py    # SMOOTHING_OPERATORS dict, get_smoothing_function()
│   │   └── settings.py    # SmoothingMethod enum, SmoothingConfig, bandwidths
│   └── azimuthal/         # Azimuthal HVSR
│       ├── azimuthal_processor.py  # AzimuthalHVSRProcessor (rotation at N angles)
│       ├── azimuthal_result.py     # AzimuthalHVSRResult
│       └── azimuthal_plotting.py   # 2D/3D contour, polar, summary plots
├── config/                # Application settings
│   ├── settings.py        # ApplicationSettings, WindowSettings, ProcessingSettings, ExportSettings, PlotSettings, PRESETS
│   ├── schemas.py         # Validation: validate_settings, validate_processing_params, validate_qc_params
│   ├── session.py         # SessionManager, SessionState — full pickle persistence (.hvsr_session)
│   └── plot_properties.py # PlotProperties dataclass, 3 presets (publication/analysis/minimal)
├── visualization/         # Plotting
│   ├── plotter.py         # HVSRPlotter class
│   ├── hvsr_plots.py      # plot_hvsr_curve, comparison, components, peak_analysis, statistics
│   ├── window_plots.py    # time_series, spectrogram, collection_overview, quality_grid, rejection_timeline
│   ├── comparison_plot.py # Raw vs adjusted HVSR (MATLAB-style)
│   └── waveform_plot.py   # 3-component waveform, pre/post rejection
├── api/                   # Programmatic API
│   ├── analysis.py        # HVSRAnalysis (fluent API: load→configure→process→save)
│   └── batch.py           # batch_process(), HTML/MD reports
├── cli/                   # Command-line interface
│   └── main.py            # main(), cli()
├── gui/                   # PyQt5 GUI (optional, HAS_GUI flag)
│   ├── main_window.py     # HVSRMainWindow
│   ├── main_window_modules/  # Modular: menu_bar, control_panel, controllers, ui_coordinator, view_state
│   ├── canvas/            # InteractiveHVSRCanvas, PreviewCanvas, PlotWindowManager
│   ├── tabs/              # DataLoadTab, AzimuthalTab, ProcessingTab
│   ├── docks/             # ExportDock, WindowLayersDock, PeakPickerDock, PropertiesDock, AzimuthalPropertiesDock
│   ├── dialogs/           # DataInputDialog, ExportDialog, ChannelMapperDialog, AdvancedQCDialog, SmoothingDialog
│   ├── panels/            # ProcessingSettingsPanel, UnifiedQCPanel
│   ├── components/        # CollapsibleGroupBox, CollapsibleSection, ColorPickerButton
│   ├── widgets/           # LoadedDataList, LoadedDataTree, ViewModeSelector
│   ├── workers/           # ProcessingThread, DataExportWorker, PlotExportWorker, AzimuthalProcessingThread
│   ├── mixins/            # (deprecated — moved to controllers)
│   └── utils/             # GUI helpers
├── utils/                 # General utilities
│   ├── file_utils.py      # detect_file_format, validate_path
│   ├── time_utils.py      # parse_time, time_to_samples
│   ├── signal_utils.py    # detrend, taper, check_gaps
│   └── export_utils.py    # Export helpers
├── packages/              # Sub-packages
│   └── batch_processing/  # Batch processing sub-package
└── tests/                 # Test suite
    ├── gui/               # GUI tests
    └── test_qc_settings.py
```

---

## 2. CORE DATA FLOW

```
File(s) → HVSRDataHandler.load_data() → SeismicData
          ↓ (auto-detect format, use appropriate loader, cache result)
SeismicData → WindowManager.create_windows() → WindowCollection
              ↓ (split into overlapping windows, apply taper, compute quality metrics)
WindowCollection → RejectionEngine.evaluate() → WindowCollection (windows marked rejected)
                   ↓ (pipeline of pre-HVSR algorithms: Amplitude, STA/LTA, etc.)
WindowCollection → HVSRProcessor.process() → HVSRResult
                   ↓ (FFT → smooth → H/V ratio → statistics → peak detection)
HVSRResult → RejectionEngine.evaluate_fdwra() → WindowCollection (Cox FDWRA post-HVSR)
             ↓ (iterative peak frequency consistency check)
             → Re-process with HVSRProcessor if windows changed
             → Final HVSRResult
```

---

## 3. KEY DATA STRUCTURES

### 3.1 ComponentData (dataclass)
- `name`: str (E/N/Z/HNE/HNN/HNZ)
- `data`: np.ndarray (time series)
- `sampling_rate`: float (Hz)
- `start_time`: Optional[datetime]
- `units`: str (default 'm/s')
- Properties: `n_samples`, `duration`, `time_vector`, `dt`
- Method: `get_slice(start_idx, end_idx)`

### 3.2 SeismicData (dataclass)
- `east`, `north`, `vertical`: ComponentData (must have matching rates & lengths)
- `station_name`, `location`, `source_file`
- Properties: `sampling_rate`, `n_samples`, `duration`, `start_time`, `time_vector`
- Methods: `get_component(name)`, `get_horizontal_components()`, `get_slice()`, `to_dict()`

### 3.3 Window (dataclass)
- `index`, `start_sample`, `end_sample`: positional info
- `data`: SeismicData (the window's 3-component data)
- `state`: WindowState enum (ACTIVE/REJECTED_AUTO/REJECTED_MANUAL/BORDERLINE/PENDING)
- `visible`: bool — **dual state system**: `state` controls QC, `visible` controls layer display
- `quality_metrics`: Dict[str, float] (snr, stationarity, energy_consistency, peak_to_mean, zero_crossing_rate, overall)
- `rejection_reason`: Optional[str]
- Key method: `should_include_in_hvsr()` → True only if ACTIVE AND visible
- `toggle_state()`: toggles between ACTIVE and REJECTED_MANUAL

### 3.4 WindowCollection (dataclass)
- `windows`: List[Window]
- `source_data`: SeismicData (full original data)
- `window_length`, `overlap`
- Properties: `n_windows`, `n_active`, `n_rejected`, `acceptance_rate`
- Methods: `get_active_windows()`, `reject_window()`, `activate_window()`, `toggle_window()`

### 3.5 WindowSpectrum (dataclass)
- Per-window: `frequencies`, `east_spectrum`, `north_spectrum`, `vertical_spectrum`, `horizontal_spectrum`, `hvsr`
- `window_index`, `is_valid`

### 3.6 Peak (dataclass)
- `frequency`, `amplitude`, `prominence`, `width`, `left_freq`, `right_freq`, `quality`

### 3.7 HVSRResult (dataclass)
- Statistical curves: `frequencies`, `mean_hvsr`, `median_hvsr`, `std_hvsr`, `percentile_16`, `percentile_84`
- `valid_windows`, `total_windows`, `peaks`: List[Peak]
- `window_spectra`: List[WindowSpectrum] (optional, large)
- `processing_params`, `timestamp`, `metadata`
- Properties: `acceptance_rate`, `primary_peak`
- Methods: `get_hvsr_at_frequency()`, `to_dict()`, `save()`, `load()`

---

## 4. HVSRDataHandler — LOADING SYSTEM

### 4.1 Registered Loaders
| Format | Loader | Extensions | Multi-file |
|--------|--------|------------|------------|
| txt | TxtDataLoader | .txt .dat .asc | No |
| miniseed | MiniSeedLoader | .mseed .miniseed .ms | Optional |
| saf | SAFLoader | .saf | No |
| sac | SACLoader | .sac | Yes (3 files) |
| gcf | GCFLoader | .gcf | No |
| peer | PEERLoader | .vt2 .at2 .dt2 | Yes (3 files) |
| minishark | MiniSharkLoader | .minishark | No |
| srecord3c | SeismicRecording3CLoader | .json | No |

### 4.2 Loading Methods
- `load_data(filepath, format='auto')` — Single file, auto-detect
- `load_multiple(filepaths)` — Batch load
- `load_multi_component(filepaths)` — 3 separate component files (SAC/PEER)
- `load_oscar_station(station_dir, time_period, version)` — OSCAR project directory structure
- `load_oscar_miniseed_station(station_dir, ...)` — OSCAR MiniSEED station
- `load_multi_miniseed_type1(file_list)` — Multiple MiniSEED files each containing E,N,Z → merge chronologically
- `load_multi_miniseed_type2(file_groups)` — Separate E/N/Z MiniSEED files → merge
- `slice_by_time(data, start_time, end_time, timezone_offset_hours)` — Time range extraction with timezone conversion

### 4.3 Channel Detection
- Auto-detects HNE/HNN/HNZ channel codes
- Falls back to channels ending in E/1, N/2, Z/3
- Supports explicit `channel_mapping` dict
- `orientation.py`: rotate_horizontals for numeric component naming (123/12Z)

### 4.4 DataCache
- SHA256 file hash as cache key (for large files >10MB: hash first+last MB only)
- Includes file modification time in hash
- LRU eviction, configurable max memory (default 1GB), max age (24h)
- Memory estimation via pickle serialization

---

## 5. PROCESSING ENGINE

### 5.1 WindowManager
- `create_windows(data, calculate_quality=True)` → WindowCollection
- Taper types: tukey (default, alpha=0.1), hann, hamming, blackman, none
- Quality metrics auto-calculated: SNR, stationarity, energy consistency, peak-to-mean, ZCR, overall
- Partial last window handled with min_window_length check
- All windows start as PENDING, then set to ACTIVE

### 5.2 WindowQualityCalculator
- **SNR**: RMS signal / noise (last 10% of window), normalized via tanh(log10)
- **Stationarity**: Coefficient of variation of RMS across 10 sub-windows, score = exp(-avg_cv)
- **Energy consistency**: E/N energy ratio, score = exp(-|ln(ratio)|)
- **Peak-to-mean**: Gaussian penalty centered at ratio=4
- **Zero crossing rate**: Gaussian penalty centered at 0.2
- **Overall**: Weighted average (SNR=0.3, stationarity=0.3, energy=0.2, peak=0.1, ZCR=0.1)
- **STA/LTA metric**: Separate method for transient detection

### 5.3 HVSRProcessor
- Pipeline per window: FFT → Smooth → Horizontal combination → H/V ratio
- **FFT**: scipy.fft.rfft, mean-removed, with taper window
- **Smoothing**: 7 methods via registry (see §5.4)
- **Horizontal combination**: geometric_mean (SESAME default), arithmetic_mean, quadratic, maximum
- **H/V ratio**: horizontal/vertical with epsilon=1e-10 safety
- **Statistics**: mean, median, std, 16th/84th percentiles across all valid windows
- **Peak detection**: scipy.signal.find_peaks with prominence ≥1.5, amplitude ≥2.0, parabolic refinement
- Supports **parallel processing** via multiprocessing.Pool (threshold: >20 windows)
- `use_only_active = True` by default

### 5.4 Smoothing Methods
All share signature: `f(frequencies, spectrum, center_frequencies, bandwidth) → smoothed`

| Method | Bandwidth Meaning | Default | Range |
|--------|------------------|---------|-------|
| konno_ohmachi | Inverse width (higher=less smooth) | 40.0 | 1-200 |
| parzen | Window width in Hz | 0.5 | 0.01-10 |
| savitzky_golay | # points (odd integer) | 9 | 3-51 |
| linear_rectangular | Boxcar width in Hz | 0.5 | 0.01-10 |
| log_rectangular | Boxcar width in log10 | 0.05 | 0.001-1.0 |
| linear_triangular | Triangle width in Hz | 0.5 | 0.01-10 |
| log_triangular | Triangle width in log10 | 0.05 | 0.001-1.0 |
| none | N/A | 0 | 0 |

### 5.5 Peak Detection
- `detect_peaks()`: scipy find_peaks with prominence & amplitude filters, returns sorted by amplitude
- `identify_fundamental_peak()`: Scoring: freq_score×0.3 + amp_score×0.4 + prom_score×0.3
- `refine_peak_frequency()`: Parabolic interpolation for sub-sample precision
- `find_top_n_peaks()`: Top N by prominence (for "Auto Top N" mode)
- `find_multi_peaks()`: All peaks above threshold, sorted by frequency (for multi-layer sites)
- `sesame_peak_criteria()`: SESAME 2004 reliability checks (f0>10/lw, A0>2, stability)

---

## 6. REJECTION / QC SYSTEM

### 6.1 Architecture
- **RejectionEngine**: Coordinates multiple algorithms in pipeline
- **Two stages**: Pre-HVSR (time-domain) and Post-HVSR (frequency-domain)
- **BaseRejectionAlgorithm** ABC: `evaluate_window(window) → RejectionResult`
- **RejectionResult**: `should_reject: bool`, `reason: str`, `score: float`

### 6.2 Pre-HVSR Algorithms (Time-Domain)
| Algorithm | What it checks |
|-----------|---------------|
| AmplitudeRejection | Signal amplitude anomalies (spikes, clipping) |
| STALTARejection | STA/LTA ratio for transients (default: STA=1s, LTA=30s, range 0.2-2.5) |
| QualityThresholdRejection | Overall quality score < threshold (default 0.5) |
| StatisticalOutlierRejection | IQR or z-score outlier detection |
| FrequencyDomainRejection | Spectral spike detection (sigma threshold) |

### 6.3 Post-HVSR Algorithms (Frequency-Domain)
| Algorithm | What it checks |
|-----------|---------------|
| HVSRAmplitudeRejection | HVSR peak amplitude too low (min_amplitude=1.0) |
| FlatPeakRejection | HVSR peak too flat/broad (flatness_threshold=0.15) |

### 6.4 Cox FDWRA (Post-HVSR, Iterative)
- **Cox et al. (2020)** Frequency-Domain Window Rejection Algorithm
- Iteratively removes windows whose peak frequency is outside n×σ of the distribution
- Parameters: n=2.0 (std devs), max_iterations=50, min_iterations=1
- Distribution options: lognormal (default) or normal, for both fn and mean curve
- Convergence detection with configurable thresholds

### 6.5 Presets
- **sesame** (only preset): Amplitude + STA/LTA + Cox FDWRA — matches hvsrpy defaults
- **custom**: User-defined algorithm configuration
- QCSettings dataclass holds complete configuration, serializable to JSON

### 6.6 QCSettings Structure
```python
QCSettings(
    enabled=True,
    mode='sesame',        # 'sesame' or 'custom'
    phase1_enabled=True,  # Pre-HVSR
    phase2_enabled=True,  # Post-HVSR
    amplitude=AmplitudeSettings(enabled=True),
    sta_lta=STALTASettings(enabled=True, params={...}),
    quality_threshold=QualityThresholdSettings(enabled=False),
    statistical_outlier=StatisticalOutlierSettings(enabled=False),
    frequency_domain=FrequencyDomainSettings(enabled=False),
    hvsr_amplitude=HVSRAmplitudeSettings(enabled=False),
    flat_peak=FlatPeakSettings(enabled=False),
    cox_fdwra=CoxFDWRASettings(enabled=True, n=2.0, ...),
    isolation_forest=IsolationForestSettings(enabled=False),
)
```

---

## 7. AZIMUTHAL HVSR

- **AzimuthalHVSRProcessor**: Rotates horizontal components at N azimuths (default 0-180°)
- For each azimuth: `H_rotated = N*cos(θ) + E*sin(θ)`, then standard HVSR
- Supports parallel processing (Windows-aware: limits to 4 workers max)
- **AzimuthalHVSRResult**: Contains HVSR matrices indexed by [azimuth, frequency]
- **Plotting**: 2D/3D contour, polar plots, summary, individual curves

---

## 8. CONFIGURATION SYSTEM

### 8.1 ApplicationSettings (top-level)
Composed of: `WindowSettings`, `ProcessingSettings`, `QCSettings`, `ExportSettings`, `PlotSettings`

### 8.2 Processing Presets
- **default**: KO b=40, f=[0.2,20], n=100, geometric_mean
- **high_resolution**: KO b=20, f=[0.1,25], n=200
- **quick**: KO b=60, f=[0.5,15], n=50

### 8.3 Window Presets
- **default**: 30s, 50% overlap, tukey
- **short**: 15s | **long**: 60s | **high_overlap**: 30s, 75%

### 8.4 PlotProperties Dataclass
- Style presets: publication, analysis, minimal
- Y-axis modes: auto, mean_std, percentile, manual
- X-axis: log (default) or linear
- Visualization modes: statistical, windows, both
- Colors: mean=#1976D2, median=#D32F2F, std=#FF5722, percentile=#9C27B0, peak=#4CAF50
- Toggle: show_mean, show_windows, show_std_bands, show_percentile_shading, show_median
- Annotations: acceptance_badge, peak_labels (full/freq_only/amp_only/minimal), legend, grid

### 8.5 Validation
- `validate_processing_params()`: smoothing method in valid list, bandwidth in method-specific range, f_min<f_max, n_frequencies≥10, horizontal_method, taper
- `validate_window_params()`: length [1,600]s, overlap [0,0.99], taper_type
- `validate_qc_params()`: preset valid, cox_n [0.5,5.0], quality_threshold [0,1]
- Savitzky-Golay specific: bandwidth must be odd integer

---

## 9. SESSION MANAGEMENT

### 9.1 SessionState
- Stores: file_info (path, load_mode, time_range), processing settings, QC settings, window states
- Binary data file paths (relative): windows.pkl, hvsr_result.pkl, seismic_data.pkl, azimuthal_result.pkl
- Results summary: has_results, has_full_data, peak_frequency, peak_amplitude, window counts

### 9.2 SessionManager
- Creates timestamped session folders: `sessions/session_YYYYMMDD_HHMMSS/`
- `save_full_session()`: JSON settings + pickled binary data (windows, HVSR result, seismic data, azimuthal)
- `load_full_session()`: Returns tuple (state, windows, hvsr_result, seismic_data, azimuthal_result)
- `list_sessions()`: Lists all sessions with metadata
- Backward-compatible: also supports single .hvsr_session files (settings-only)

---

## 10. API LAYER

### 10.1 HVSRAnalysis (Fluent API)
```python
analysis = HVSRAnalysis()
analysis.load_data('file.mseed')         # auto-detect format
    .configure(window_length=30, overlap=0.5, qc_mode='balanced')
    .configure_smoothing('konno_ohmachi', bandwidth=40)
result = analysis.process()               # returns HVSRResult
analysis.save_results('out.json')
analysis.save_plots('plots/')
summary = analysis.get_summary()
```

### 10.2 Batch Processing
```python
results = batch_process(
    files=['a.mseed', 'b.mseed'],
    output_dir='results/',
    settings={'window_length': 30, 'qc_mode': 'balanced'},
    output_format='json',
    parallel=True
)
create_batch_report(results, 'report.html', include_plots=True)
```

---

## 11. GUI (PyQt5)

### 11.1 Main Window: HVSRMainWindow
- **Modular architecture**: menu_bar, control_panel, controllers, ui_coordinator, view_state
- **Controllers pattern**: Processing, plotting, session logic separated from UI

### 11.2 Key Components
| Component | Purpose |
|-----------|---------|
| DataLoadTab | File selection, format detection, preview |
| ProcessingTab | Processing settings configuration |
| AzimuthalTab | Azimuthal analysis configuration |
| InteractiveHVSRCanvas | Main HVSR plot with click-to-toggle windows |
| PreviewCanvas | Data preview in load dialog |
| ProcessingSettingsPanel | Window length, overlap, smoothing config |
| UnifiedQCPanel | QC algorithm configuration |
| WindowLayersDock | Checkbox-based window visibility control |
| PeakPickerDock | Manual/auto peak picking (Top N, Multi-Peak) |
| PropertiesDock | Plot properties configuration |
| ExportDock | Export results and plots |
| ChannelMapperDialog | Map channels to E/N/Z components |
| AdvancedQCDialog | Detailed QC configuration |
| ProcessingThread | Background HVSR computation |
| AzimuthalProcessingThread | Background azimuthal computation |

### 11.3 Dual Window State System
- **`state`** (WindowState enum): Controlled by QC algorithms + timeline clicks
  - ACTIVE / REJECTED_AUTO / REJECTED_MANUAL / BORDERLINE / PENDING
- **`visible`** (bool): Controlled by WindowLayersDock checkboxes
- Window included in HVSR calculation: `state==ACTIVE AND visible==True`

---

## 12. VISUALIZATION

### 12.1 HVSR Plots
- `plot_hvsr_curve()`: Mean ± std, percentile bands, peak markers
- `plot_hvsr_comparison()`: Multiple HVSR curves overlaid
- `plot_hvsr_components()`: E, N, Z spectra + H/V
- `plot_peak_analysis()`: Peak detail view
- `plot_hvsr_statistics()`: Statistical summary
- `save_hvsr_plot()`: Publication-quality export

### 12.2 Window Plots
- `plot_window_time_series()`: Single window waveform
- `plot_window_spectrogram()`: Time-frequency representation
- `plot_window_collection_overview()`: All windows summary
- `plot_quality_metrics_grid()`: Quality metrics visualization
- `plot_window_comparison()`: Before/after comparison
- `plot_rejection_timeline()`: Rejection decisions over time

### 12.3 Comparison Plots
- `plot_raw_vs_adjusted_hvsr()`: MATLAB-style raw vs. QC-adjusted comparison
- `create_comparison_figure()`: Multi-panel comparison

### 12.4 Waveform Plots
- `plot_seismic_recordings_3c()`: 3-component time series
- `plot_pre_and_post_rejection()`: Visual comparison of rejection effect

---

## 13. IMPORTANT IMPLEMENTATION DETAILS

### 13.1 Import Structure
- Package uses absolute imports: `from hvsr_pro.processing.hvsr import HVSRProcessor`
- Lazy imports in processor.py to avoid circular dependencies (windows ↔ hvsr)
- GUI module is optional: wrapped in try/except, sets `HAS_GUI` flag
- QCSettings defined in `processing/rejection/settings.py`, re-exported from `config/settings.py` for backward compatibility

### 13.2 Circular Import Avoidance
- `HVSRProcessor._detect_peaks()` uses lazy import of `processing.windows.peaks`
- `_get_window_classes()` helper for lazy WindowCollection import
- TYPE_CHECKING guard for WindowCollection/Window in processor.py

### 13.3 Parallel Processing
- HVSRProcessor: Uses `multiprocessing.Pool`, threshold >20 windows
- Module-level `_process_single_window_parallel()` function (picklable)
- Azimuthal: Windows-aware, limits to MAX_SAFE_WORKERS_WINDOWS=4
- Batch: Uses `concurrent.futures.ProcessPoolExecutor`

### 13.4 MiniSEED Channel Mapping Priority
1. Specific 3-letter codes: HNE, HNN, HNZ
2. Generic patterns: ends with E/1, N/2, Z/3
3. Earlier matches NOT overwritten (HNE takes priority over generic E)
4. Explicit `channel_mapping` dict overrides all auto-detection

### 13.5 Time Slicing
- Converts local time → GMT using timezone offset
- Calculates elapsed seconds from data start time
- Validates against data bounds
- Returns new SeismicData with copied arrays

### 13.6 Konno-Ohmachi Implementation
- Two versions: standard (O(n²) loop) and fast (vectorized broadcasting)
- Both handle DC component (f=0) separately
- Window function: `(sin(b*log10(f/fc)) / (b*log10(f/fc)))^4`
- Normalized: window sums to 1.0

### 13.7 Peak Quality Score
- `quality = min(1.0, (prominence/3.0) * (amplitude/5.0))`
- Peaks sorted by amplitude (highest first) by default
- SESAME criteria: f0>10/lw, A0>2, prominent (prom>1.5), stable flanks

### 13.8 Export Formats
- JSON (with optional window spectra)
- CSV
- MAT (MATLAB)
- PNG/SVG figures (configurable DPI)
- HTML/Markdown batch reports

---

## 14. DEPENDENCIES

- **Required**: numpy, scipy, pathlib, dataclasses, json, pickle, logging
- **Optional**: obspy (MiniSEED/SAC/GCF loading), PyQt5 (GUI), matplotlib (plotting)
- Smoothing methods are pure NumPy (no Numba dependency)
- Reference: adapted from hvsrpy (Vantassel, 2019-2025)

---

## 15. NAMING CONVENTIONS & PATTERNS

- Data structures: Python dataclasses with `to_dict()` / `from_dict()` pattern
- Enums: WindowState, SmoothingMethod
- Algorithms: Inherit from BaseRejectionAlgorithm, implement evaluate_window()
- Loaders: Inherit from BaseDataLoader, implement load_file() and can_load()
- Settings: Nested dataclasses with serialization (ApplicationSettings → WindowSettings, ProcessingSettings, etc.)
- GUI: PyQt5 signals/slots, worker threads for long operations
- Logging: Module-level `logger = logging.getLogger(__name__)` throughout
