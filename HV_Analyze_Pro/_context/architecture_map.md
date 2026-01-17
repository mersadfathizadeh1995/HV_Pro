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
```

### Processing Pipeline
```
core/data_structures → processing/windows → processing/hvsr → processing/rejection
(SeismicData)           (WindowManager)      (HVSRProcessor)   (RejectionEngine)
                        (WindowCollection)   (HVSRResult)      (CoxFDWRARejection)
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
                      ├── PlottingController    (plot management)
                      ├── SessionController     (save/load sessions)
                      ├── WindowController      (window state)
                      ├── PeakController        (peak detection)
                      └── ExportController      (file export)

              ─────→ helpers/
                      ├── MenuBarHelper         (menu creation)
                      ├── ViewStateManager      (dock/tab visibility)
                      ├── UIUpdateCoordinator   (post-processing updates)
                      └── BackwardCompatMixin   (deprecated properties)
```

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
