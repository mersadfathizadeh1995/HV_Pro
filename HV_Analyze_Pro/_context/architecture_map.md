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

### Azimuthal Processing (Separate Pipeline)
```
core/data_structures → processing/azimuthal
                        ├── azimuthal_processor.py
                        ├── azimuthal_result.py
                        └── azimuthal_plotting.py
```

### Visualization Dependencies
```
processing/hvsr/structures → visualization/
(HVSRResult)                  ├── plotter.py (HVSRPlotter)
(WindowSpectrum)              ├── hvsr_plots.py
                              ├── comparison_plot.py
processing/windows/           ├── window_plots.py
(WindowCollection)            └── waveform_plot.py
```

## GUI Architecture

### Main Window Composition
```
gui/main_window.py (HVSRMainWindow)
├── USES: gui/main_window_modules/
│         ├── menu_bar.py (MenuBarHelper)
│         ├── control_panel.py (settings groups)
│         ├── controllers/ (DataController, ProcessingController, etc.)
│         └── panels/ (ProcessingSettingsPanel, QCSettingsPanel)
│
├── USES: gui/mixins/
│         ├── processing_mixin.py
│         ├── plotting_mixin.py
│         └── session_mixin.py
│
├── CONTAINS: gui/tabs/
│             ├── data_load_tab.py (DataLoadTab)
│             └── azimuthal_tab.py (AzimuthalTab)
│
├── CONTAINS: gui/docks/
│             ├── export/ (ExportDock + sections/, exporters/)
│             │   ├── sections/ (PlotExportSection, DataExportSection, StatsExportSection,
│             │   │              ComparisonFiguresSection, ReportSection, SessionSection)
│             │   └── exporters/ (data_exporter, stats_exporter, figure_exporter)
│             ├── properties/ (PropertiesDock + sections/)
│             ├── azimuthal/ (AzimuthalDock + sections/, dialogs/, exporters/)
│             ├── layers/ (WindowLayersDock)
│             └── peak_picker/ (PeakPickerDock)
│
└── USES: gui/canvas/
          ├── interactive_canvas.py
          ├── preview_canvas.py
          └── plot_window_manager.py
```

### Dialog Structure
```
gui/dialogs/
├── data_input/
│   ├── data_input_dialog.py (DataInputDialog) → Main container
│   ├── panels/ (FileInputPanel, TimeRangePanel, etc.)
│   └── tabs/ (SingleFileTab, MultiFileTab)
├── export/
│   ├── export_dialog.py
│   └── data_export_dialog.py
├── mappers/
│   ├── channel_mapper_dialog.py
│   └── column_mapper_dialog.py
└── qc/
    └── advanced_qc_dialog.py
```

### Dock Pattern (Established in properties/ and azimuthal/)
```
dock_package/
├── __init__.py                 → Exports main dock + components
├── dock_name.py                → Main dock widget (~150-300 lines)
├── sections/                   → CollapsibleSection subclasses
│   ├── __init__.py
│   └── *_section.py
├── dialogs/ (optional)         → Dialog classes
│   └── *_dialog.py
└── exporters/ (optional)       → Pure export functions (no Qt)
    └── *_exporter.py
```

### Key Connection Patterns
```
Tab → Main Window Reference:
  - Tabs stored in QTabWidget lose parent() reference to main window
  - Store main window as self._main_window in __init__ BEFORE adding to tab widget
  - Use self._main_window to access sibling docks (e.g., azimuthal_properties_dock)

Dock → Data References:
  - Docks receive data via set_references() or set_result() methods
  - Store references: self.result, self.windows, self.canvas_manager, self.data
  - Implement _get_current_result() fallback to get from sibling tabs
```

### Component Hierarchy
```
gui/components/
├── CollapsibleSection         → Base for dock sections
├── CollapsibleGroupBox        → Alternative collapsible container
├── CollapsibleDataPanel       → For loaded data display
└── ColorPickerButton          → Color selection widget

gui/widgets/
├── LoadedDataList             → File list widget
├── LoadedDataTree             → File tree widget
└── ViewModeSelector           → View mode buttons
```

### Workers (Background Threads)
```
gui/workers/
├── ProcessingThread           → HVSR processing
├── AzimuthalProcessingThread  → Azimuthal processing
├── DataExportWorker           → Data export
└── PlotExportWorker           → Plot export
```

## Cross-Package Dependencies

```
gui/ ─────────────────────────→ processing/ (all submodules)
gui/ ─────────────────────────→ visualization/
gui/ ─────────────────────────→ core/
gui/ ─────────────────────────→ config/
gui/ ─────────────────────────→ loaders/

api/ ─────────────────────────→ core/
api/ ─────────────────────────→ processing/
api/ ─────────────────────────→ config/

cli/ ─────────────────────────→ api/
cli/ ─────────────────────────→ config/
```

## Config Dependencies
```
config/settings.py      → Used by: api/, gui/, cli/
config/session.py       → Used by: gui/mixins/session_mixin.py
config/schemas.py       → Used by: api/, config/settings.py
config/plot_properties.py → Used by: gui/docks/properties/
```

## Key Classes Summary

| Class | Location | Purpose |
|-------|----------|---------|
| SeismicData | core/data_structures.py | 3-component seismic data container |
| HVSRDataHandler | core/data_handler.py | Load/manage seismic data |
| WindowManager | processing/windows/manager.py | Create time windows |
| WindowCollection | processing/windows/structures.py | Window container |
| HVSRProcessor | processing/hvsr/processor.py | Compute HVSR |
| HVSRResult | processing/hvsr/structures.py | HVSR result container |
| RejectionEngine | processing/rejection/engine.py | Coordinate rejection algorithms |
| AzimuthalHVSRProcessor | processing/azimuthal/ | Azimuthal processing |
| HVSRPlotter | visualization/plotter.py | High-level plotting |
| HVSRMainWindow | gui/main_window.py | Main application window |
| HVSRAnalysis | api/analysis.py | High-level API |
