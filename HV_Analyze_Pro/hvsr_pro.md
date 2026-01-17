# HVSR Pro Package Analysis

## Overview
**Version:** 2.0  
**Location:** `D:\Research\Narm_Afzar\Git_hub\HV_Pro\HV_Analyze_Pro\hvsr_pro`  
**Purpose:** Comprehensive HVSR (Horizontal-to-Vertical Spectral Ratio) data analysis package with GUI and batch processing capabilities.

---

## Package Architecture

```
hvsr_pro/
├── __init__.py           # Package entry point, exports main classes
├── core/                 # Data handling and structures
│   ├── __init__.py
│   ├── data_structures.py    # ComponentData, SeismicData
│   ├── data_handler.py       # HVSRDataHandler (main loader)
│   ├── data_cache.py         # DataCache (LRU caching)
│   └── metadata.py           # MetadataManager
├── loaders/              # File format loaders
│   ├── __init__.py
│   ├── base_loader.py        # BaseDataLoader (abstract)
│   ├── txt_loader.py         # TxtDataLoader (OSCAR ASCII)
│   └── miniseed_loader.py    # MiniSeedLoader (ObsPy)
├── processing/           # HVSR computation engine
│   ├── __init__.py
│   ├── window_structures.py  # Window, WindowState, WindowCollection
│   ├── window_manager.py     # WindowManager
│   ├── hvsr_processor.py     # HVSRProcessor (core computation)
│   ├── hvsr_structures.py    # HVSRResult, WindowSpectrum, Peak
│   ├── spectral_processing.py # FFT, Konno-Ohmachi smoothing
│   ├── peak_detection.py     # Peak detection algorithms
│   ├── quality_metrics.py    # WindowQualityCalculator
│   ├── rejection_engine.py   # RejectionEngine (pipeline coordinator)
│   ├── rejection_algorithms.py # Base classes, QualityThreshold, Statistical
│   ├── rejection_advanced.py # STA/LTA, FrequencyDomain, Amplitude
│   ├── rejection_cox_fdwra.py # Cox et al. (2020) FDWRA algorithm
│   └── rejection_ml.py       # IsolationForest, Ensemble (requires sklearn)
├── visualization/        # Plotting utilities
│   ├── __init__.py
│   ├── plotter.py            # HVSRPlotter (high-level interface)
│   ├── hvsr_plots.py         # HVSR curve plotting functions
│   └── window_plots.py       # Window visualization functions
├── gui/                  # PyQt5 GUI
│   ├── __init__.py
│   ├── main_window.py        # HVSRMainWindow
│   ├── interactive_canvas.py # InteractiveHVSRCanvas (matplotlib)
│   ├── plot_window_manager.py # PlotWindowManager
│   ├── layers_dock.py        # WindowLayersDock
│   ├── peak_picker_dock.py   # PeakPickerDock
│   ├── properties_dock.py    # PropertiesDock
│   ├── view_mode_selector.py # ViewModeSelector
│   ├── data_input_dialog.py  # DataInputDialog
│   └── batch_tab.py          # BatchTab (batch processing UI)
├── batch/                # Batch processing
│   ├── __init__.py
│   ├── batch_processor.py    # BatchProcessor
│   ├── dataset_manager.py    # DatasetFile, DatasetManager
│   └── results_database.py   # ResultsDatabase, BatchResult
├── utils/                # Utility functions
│   ├── __init__.py
│   ├── export_utils.py       # CSV/TXT export functions
│   ├── file_utils.py         # File handling utilities
│   ├── signal_utils.py       # Detrend, taper, gap detection
│   └── time_utils.py         # Time/timezone utilities
└── cli/                  # Command-line interface (incomplete)
```

---

## Core Components

### 1. Data Structures (`core/data_structures.py`)

#### ComponentData
- Represents single seismic component (E, N, Z)
- Attributes: `name`, `data` (np.ndarray), `sampling_rate`, `start_time`, `units`, `metadata`
- Properties: `n_samples`, `duration`, `time_vector`
- Methods: `get_slice(start_sample, end_sample)`

#### SeismicData
- Container for three-component seismic data
- Attributes: `east`, `north`, `vertical` (all ComponentData), `station_name`, `location`, `source_file`, `metadata`
- Validation: Ensures consistent sampling rates and lengths across components
- Methods: `get_component(name)`, `get_slice(start, end)`

### 2. Data Loading (`core/data_handler.py`)

#### HVSRDataHandler
- Universal interface for loading seismic data
- Auto-detects file formats (TXT, MiniSEED)
- Features:
  - Plugin-based loader system
  - LRU caching via `DataCache`
  - Batch loading support
  - OSCAR-specific loading functions
  - Time slicing with timezone support
  - Multi-MiniSEED merging (Type 1 and Type 2)

### 3. Window Management (`processing/window_manager.py`)

#### WindowManager
- Creates windows from SeismicData
- Configurable: `window_length`, `overlap`, `taper_type`, `taper_width`
- Taper types: Tukey, Hann, Hamming, Blackman
- Integrates with `WindowQualityCalculator` for initial quality assessment

#### WindowCollection
- Manages collection of `Window` objects
- Tracks window states (active, rejected, borderline, pending)
- Statistics: `n_active`, `n_rejected`, `acceptance_rate`

### 4. HVSR Processing (`processing/hvsr_processor.py`)

#### HVSRProcessor
- Core HVSR computation engine
- Parameters:
  - `smoothing_bandwidth`: Konno-Ohmachi bandwidth (default: 40)
  - `f_min`, `f_max`: Frequency range
  - `n_frequencies`: Number of output frequencies
  - `horizontal_method`: geometric_mean, arithmetic_mean, quadratic, maximum
  - `parallel`: Enable multiprocessing

- Processing pipeline:
  1. FFT computation with optional tapering
  2. Konno-Ohmachi smoothing
  3. Horizontal spectrum combination
  4. H/V ratio calculation
  5. Statistical aggregation (mean, median, std, percentiles)
  6. Peak detection and refinement

### 5. Quality Control (`processing/rejection_engine.py`)

#### RejectionEngine
- Coordinates multiple rejection algorithms
- Pipeline modes: conservative, balanced, aggressive, sesame, ml
- Supports Cox et al. (2020) FDWRA post-HVSR

#### Rejection Algorithms:
| Algorithm | Description |
|-----------|-------------|
| `QualityThresholdRejection` | Rejects below quality threshold |
| `StatisticalOutlierRejection` | IQR or Z-score outlier detection |
| `STALTARejection` | STA/LTA ratio bounds (industry-standard) |
| `FrequencyDomainRejection` | Spectral spikes, flatness |
| `AmplitudeRejection` | Clipping, dead channels |
| `CoxFDWRAejection` | Peak frequency consistency (iterative) |
| `IsolationForestRejection` | ML-based anomaly detection |
| `EnsembleRejection` | Voting ensemble of algorithms |

### 6. Spectral Processing (`processing/spectral_processing.py`)

Key functions:
- `compute_fft()`: FFT with optional tapering
- `konno_ohmachi_smoothing()`: Standard HVSR smoothing
- `konno_ohmachi_smoothing_fast()`: Vectorized optimization
- `calculate_horizontal_spectrum()`: E/N combination methods
- `calculate_hvsr()`: H/V ratio
- `logspace_frequencies()`: Logarithmic frequency array

### 7. Peak Detection (`processing/peak_detection.py`)

- `detect_peaks()`: scipy.signal.find_peaks with prominence
- `identify_fundamental_peak()`: Score-based f0 identification
- `peak_consistency_check()`: Cross-window consistency
- `refine_peak_frequency()`: Parabolic interpolation
- `find_top_n_peaks()`: Auto Top N mode
- `find_multi_peaks()`: All peaks above threshold
- `sesame_peak_criteria()`: SESAME (2004) reliability criteria

---

## GUI Architecture

### Main Window (`gui/main_window.py`)

#### HVSRMainWindow (QMainWindow)
- Two-tab interface: Single File | Batch Processing
- Dockable panels: Layers, Peak Picker, Properties
- Processing thread for async HVSR computation

#### ProcessingThread
- Background QThread for HVSR pipeline
- Signals: `progress`, `finished`, `error`
- Supports: single file, multi-MiniSEED Type 1/2
- Time range filtering
- QC modes: conservative, balanced, aggressive, sesame, custom, ml

### Interactive Canvas (`gui/interactive_canvas.py`)

#### InteractiveHVSRCanvas
- Matplotlib embedded in PyQt5
- Multi-panel display: Timeline, HVSR curve, Statistics
- Click-to-toggle window rejection
- Color coding: green=active, gray=rejected
- Signals: `window_toggled`, `status_message`

### Visualization Panels
- **WindowLayersDock**: Layer visibility control
- **PeakPickerDock**: Manual/auto peak selection
- **PropertiesDock**: Processing properties display
- **ViewModeSelector**: View mode switching

---

## Batch Processing

### BatchProcessor (`batch/batch_processor.py`)

#### ProcessingSettings
- Configuration dataclass for batch processing
- Includes: window parameters, QC mode, Cox FDWRA settings, parallel options



## Export Capabilities

### Export Functions (`utils/export_utils.py`)

- `export_hvsr_curve_csv()`: Full statistics CSV
- `export_hvsr_curve_for_inversion()`: Two-column format for Dinver/Geopsy
- `export_peaks_csv()`: Peak information
- `export_complete_dataset()`: Package with all exports + JSON metadata

---

## Key Strengths

1. **Comprehensive Processing**: Complete HVSR workflow from data loading to peak detection
2. **Multiple QC Algorithms**: Industry-standard rejection methods including Cox FDWRA
3. **Flexible Data Loading**: Supports OSCAR TXT and MiniSEED with auto-detection
4. **Interactive GUI**: Click-to-toggle window rejection with real-time feedback
5. **Batch Processing**: Systematic processing of multiple files with consistent settings
6. **Export Options**: Multiple formats for different use cases (analysis, inversion)

## Areas for Enhancement

1. **GUI Framework**: Current PyQt5 basic styling - could benefit from modern fluent design
2. **CLI**: Incomplete command-line interface
3. **Documentation**: Inline docstrings present but no external documentation
4. **Testing**: No visible test suite
5. **Configuration**: Settings scattered - could use centralized config management
6. **Theming**: Limited dark/light mode support
7. **Real-time Processing**: Could add streaming data support
8. **Plugin System**: Loaders are modular but could be more extensible

---

## Dependencies

- **Required**: numpy, scipy, matplotlib
- **Optional**: 
  - PyQt5 (GUI)
  - ObsPy (MiniSEED support)
  - scikit-learn (ML rejection)

---

## Usage Example

```python
from hvsr_pro.core import HVSRDataHandler
from hvsr_pro.processing import WindowManager, RejectionEngine, HVSRProcessor
from hvsr_pro.visualization import HVSRPlotter

# Load data
handler = HVSRDataHandler()
data = handler.load_data("seismic_data.txt")

# Create windows
manager = WindowManager(window_length=30.0, overlap=0.5)
windows = manager.create_windows(data, calculate_quality=True)

# Apply QC
engine = RejectionEngine()
engine.create_default_pipeline(mode='balanced')
engine.evaluate(windows, auto_apply=True)

# Compute HVSR
processor = HVSRProcessor(smoothing_bandwidth=40, f_min=0.2, f_max=20.0)
result = processor.process(windows, detect_peaks_flag=True)

# Visualize
plotter = HVSRPlotter()
plotter.plot_result(result, save_path="hvsr_result.png")
```
