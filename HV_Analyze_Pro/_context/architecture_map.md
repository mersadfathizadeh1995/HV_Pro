# HVSR Pro Architecture Map

## Package Structure

```
hvsr_pro/
├── __init__.py          → Exports: HVSRDataHandler, WindowManager, HVSRProcessor, HVSRPlotter
├── core/                → Data handling and structures
├── processing/          → HVSR, windows, rejection, azimuthal
├── visualization/       → Plotting functions
├── config/              → Settings, schemas, session management
├── loaders/             → Data file loaders (txt, miniseed)
├── utils/               → Helper functions
├── gui/                 → PyQt5 GUI
├── api/                 → Programmatic API
└── cli/                 → Command-line interface
```

## Module Dependencies

### Core Data Flow
```
loaders/         → core/data_handler     → core/data_structures
(TxtLoader)         (HVSRDataHandler)       (SeismicData, ComponentData)
(MiniSeedLoader)
(SAFLoader)      → load_data()
(SACLoader)      → load_multi_component()
(GCFLoader)
(PEERLoader)
```

### Data Loaders Package
```
loaders/
├── __init__.py           → FORMAT_INFO registry, exports
├── config.py             → LoaderConfig, SAFConfig, SACConfig, GCFConfig, PEERConfig
├── patterns.py           → Compiled regex for SAF/PEER/MiniShark parsing
├── orientation.py        → orient_traces(), arrange_traces(), trim_traces()
├── preview.py            → PreviewExtractor for all formats
├── base_loader.py        → BaseDataLoader abstract base
├── txt_loader.py         → ASCII/TXT format
├── miniseed_loader.py    → MiniSEED format (via ObsPy)
├── saf_loader.py         → SESAME ASCII Format
├── sac_loader.py         → SAC format (3 files, via ObsPy)
├── gcf_loader.py         → Guralp Compressed Format (via ObsPy)
├── peer_loader.py        → PEER NGA format (3 files)
├── minishark_loader.py   → MiniShark proprietary format
└── srecord3c_loader.py   → HVSRPy JSON (SeismicRecording3C)

Supported Formats:
| Format        | Extensions           | Type       | Description                    |
|---------------|---------------------|------------|--------------------------------|
| txt           | .txt, .dat, .asc    | Single     | OSCAR ASCII format             |
| miniseed      | .mseed, .miniseed   | Single/3   | Standard seismic format        |
| saf           | .saf                | Single     | SESAME ASCII Format            |
| sac           | .sac                | 3 files    | Seismic Analysis Code          |
| gcf           | .gcf                | Single     | Guralp Compressed Format       |
| peer          | .vt2, .at2, .dt2    | 3 files    | PEER ground motion             |
| minishark     | .minishark          | Single     | MiniShark proprietary format   |
| srecord3c_json| .json               | Single     | HVSRPy native JSON format      |
```

### Processing Pipeline
```
core/data_structures → processing/windows → processing/hvsr → processing/rejection
(SeismicData)           (WindowManager)      (HVSRProcessor)   (RejectionEngine)
                        (WindowCollection)   (HVSRResult)      (CoxFDWRARejection)
```

### Smoothing Methods (NEW)
```
processing/smoothing/
├── __init__.py      → Package exports
├── methods.py       → 8 smoothing functions (konno_ohmachi, parzen, etc.)
├── settings.py      → SmoothingMethod enum, SmoothingConfig dataclass
└── registry.py      → SMOOTHING_OPERATORS dict, get_smoothing_function()

Available methods: konno_ohmachi, parzen, savitzky_golay, 
                   linear_rectangular, log_rectangular,
                   linear_triangular, log_triangular, none

Usage in HVSRProcessor:
  processor = HVSRProcessor(
      smoothing_method='konno_ohmachi',  # or any method
      smoothing_bandwidth=40.0
  )
```

### Azimuthal Processing
```
core/data_structures → processing/azimuthal
                        ├── azimuthal_processor.py
                        ├── azimuthal_result.py
                        └── azimuthal_plotting.py
```

### Visualization
```
processing/hvsr/structures → visualization/
(HVSRResult)                  ├── plotter.py (HVSRPlotter)
(WindowSpectrum)              ├── hvsr_plots.py
                              ├── comparison_plot.py
processing/windows/           ├── window_plots.py
(WindowCollection)            └── waveform_plot.py
```

---

## GUI Architecture

### Main Window Tabs
```
HVSRMainWindow (main_window.py - 1204 lines)
└── mode_tabs (QTabWidget)
    ├── Tab 0: "Data Load"
    │   └── DataLoadTab (gui/tabs/data_load_tab.py)
    │       ├── Work directory controls
    │       ├── LoadedDataTree (left panel)
    │       ├── PreviewCanvas (right panel)
    │       └── File loading controls
    │
    ├── Tab 1: "Processing"
    │   └── ProcessingTab (gui/tabs/processing_tab.py)
    │       ├── CollapsibleDataPanel
    │       ├── ProcessingSettingsPanel
    │       ├── QCSettingsPanel / CoxSettingsPanel
    │       ├── Process HVSR button
    │       ├── Window Management
    │       └── Progress/Info display
    │
    └── Tab 2: "Azimuthal"
        └── AzimuthalTab (gui/tabs/azimuthal_tab.py)
            ├── CollapsibleDataPanel
            ├── Settings panel
            └── Processing controls
```

### Dock Visibility
| Dock | Data Load | Processing | Azimuthal |
|------|-----------|------------|-----------|
| layers_dock | hidden | visible | hidden |
| peak_picker_dock | hidden | visible | hidden |
| properties_dock | hidden | visible | hidden |
| export_dock | hidden | visible | hidden |
| azimuthal_properties_dock | hidden | hidden | visible |

### Controller Architecture
```
main_window.py ─────→ controllers/
                      ├── DataController        (data loading)
                      ├── ProcessingController  (HVSR processing)
                      ├── PlottingController    (plot management, window indexing)
                      ├── SessionController     (save/load sessions)
                      ├── WindowController      (window state)
                      ├── PeakController        (peak detection)
                      └── ExportController      (file export)

              ─────→ helpers/
                      ├── MenuBarHelper         (menu creation)
                      ├── ViewStateManager      (dock/tab visibility)
                      └── UIUpdateCoordinator   (post-processing updates)
```

Note: PlottingController uses spectra_by_index mapping to correctly match
      window_spectra to windows (handles active-only processing).

### Dialog Structure
```
gui/dialogs/
├── data_input/        → DataInputDialog (file loading wizard)
├── export/            → Export dialogs
├── mappers/           → Channel/Column mapping
└── qc/                → Advanced QC settings
```

### Dock Package Pattern
```
docks/dock_name/
├── __init__.py           → Exports
├── dock_name.py          → Main widget (max 300 lines)
├── sections/             → CollapsibleSection subclasses
├── dialogs/ (optional)   → Dialog classes
└── exporters/ (optional) → Pure export functions
```

### Component Library
```
gui/components/
├── CollapsibleSection        → Base for dock sections
├── CollapsibleGroupBox       → Collapsible container
├── CollapsibleDataPanel      → Loaded data display
└── ColorPickerButton         → Color selection

gui/widgets/
├── LoadedDataList/Tree       → File widgets
└── ViewModeSelector          → View mode buttons
```

### Workers (Background Threads)
```
gui/workers/
├── ProcessingThread          → HVSR processing
├── AzimuthalProcessingThread → Azimuthal processing
├── DataExportWorker          → Data export
└── PlotExportWorker          → Plot export
```

---

## Cross-Package Dependencies

```
gui/ ──────→ processing/ (all submodules)
gui/ ──────→ visualization/
gui/ ──────→ core/
gui/ ──────→ config/
gui/ ──────→ loaders/

api/ ──────→ core/
api/ ──────→ processing/
api/ ──────→ config/

cli/ ──────→ api/
cli/ ──────→ config/
```

---

## Key Classes

| Class | Location | Purpose |
|-------|----------|---------|
| SeismicData | core/data_structures.py | 3-component seismic data |
| HVSRDataHandler | core/data_handler.py | Load/manage data |
| WindowManager | processing/windows/ | Create time windows |
| WindowCollection | processing/windows/ | Window container |
| HVSRProcessor | processing/hvsr/ | Compute HVSR |
| HVSRResult | processing/hvsr/ | HVSR result container |
| SmoothingConfig | processing/smoothing/ | Smoothing configuration |
| SmoothingMethod | processing/smoothing/ | Smoothing method enum |
| RejectionEngine | processing/rejection/ | QC coordination |
| AzimuthalHVSRProcessor | processing/azimuthal/ | Azimuthal analysis |
| HVSRPlotter | visualization/ | High-level plotting |
| HVSRMainWindow | gui/main_window.py | Main application |
| HVSRAnalysis | api/analysis.py | High-level API |

---

## Config Dependencies

```
config/settings.py       → api/, gui/, cli/
config/session.py        → gui/ (session save/load)
config/schemas.py        → api/, config/
config/plot_properties.py → gui/docks/properties/
```

---

## File Size Guidelines

| Component Type | Target | Maximum |
|---------------|--------|---------|
| Core functions | 150 lines | 200 lines |
| GUI components | 200 lines | 300 lines |
| Controllers | 200 lines | 350 lines |
| Dock sections | 50-100 lines | 150 lines |

If exceeding: Split into package with sections/
