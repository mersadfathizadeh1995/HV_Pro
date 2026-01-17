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

### Main Window Tab Structure

```
HVSRMainWindow (main_window.py - 2511 lines) ← REFACTORED from 2886 lines
└── mode_tabs (QTabWidget)
    │
    ├── Tab 0: "Data Load" ─────────────────────────────────────────────────────
    │   └── DataLoadTab (gui/tabs/data_load_tab.py - 765 lines)
    │       ├── Work directory controls
    │       ├── LoadedDataTree (left panel)
    │       ├── PreviewCanvas (right panel)
    │       └── File loading controls
    │
    ├── Tab 1: "Processing" ────────────────────────────────────────────────────
    │   └── ProcessingTab (gui/tabs/processing_tab.py - ~350 lines) ← NEW!
    │       ├── CollapsibleDataPanel (self.data_panel)
    │       ├── ProcessingSettingsPanel (from main_window_modules/panels/)
    │       ├── QCSettingsPanel (from main_window_modules/panels/)
    │       ├── CoxSettingsPanel (from main_window_modules/panels/)
    │       ├── Parallel Processing controls
    │       ├── Process HVSR button
    │       ├── Window Management (reject/accept all, recompute)
    │       └── Progress/Info display
    │       └── Uses PlotWindowManager (separate window for HVSR plot)
    │
    │   Associated Docks (visible when on Processing tab):
    │       ├── layers_dock (WindowLayersDock)
    │       ├── peak_picker_dock (PeakPickerDock)
    │       ├── properties_dock (PropertiesDock)
    │       └── export_dock (ExportDock)
    │
    └── Tab 2: "Azimuthal" ─────────────────────────────────────────────────────
        └── AzimuthalTab (gui/tabs/azimuthal_tab.py - 720 lines)
            ├── CollapsibleDataPanel
            ├── Settings panel (azimuth range, step, windowing)
            ├── Embedded FigureCanvas (not PlotWindowManager)
            └── Processing controls

        Associated Dock:
            └── azimuthal_properties_dock (AzimuthalDock)
```

### Main Window Composition (Detail)
```
gui/main_window.py (HVSRMainWindow - 2248 lines) ← REFACTORED from 2886
│
├── USES: gui/main_window_modules/
│         ├── menu_bar.py (MenuBarHelper)
│         ├── controllers/
│         │   ├── processing_controller.py (ProcessingController) ← processing logic
│         │   ├── plotting_controller.py (PlottingController) ← plotting logic
│         │   ├── session_controller.py (SessionController) ← session logic
│         │   └── data_controller.py (DataController)
│         └── panels/ (ProcessingSettingsPanel, QCSettingsPanel, CoxSettingsPanel)
│
├── DEPRECATED: gui/mixins/ (removed - functionality moved to controllers)
│
├── CONTAINS: gui/tabs/
│             ├── data_load_tab.py (DataLoadTab) ← Tab 0
│             ├── processing_tab.py (ProcessingTab) ← Tab 1 (NEW!)
│             └── azimuthal_tab.py (AzimuthalTab) ← Tab 2
│
├── CONTAINS: gui/docks/
│             ├── export/ (ExportDock + sections/, exporters/)
│             ├── properties/ (PropertiesDock + sections/)
│             ├── azimuthal/ (AzimuthalDock + sections/, dialogs/, exporters/)
│             ├── layers/ (WindowLayersDock)
│             └── peak_picker/ (PeakPickerDock)
│
└── USES: gui/canvas/
          ├── interactive_canvas.py (InteractiveHVSRCanvas)
          ├── preview_canvas.py (PreviewCanvas - for Data Load tab)
          └── plot_window_manager.py (PlotWindowManager - for Processing tab)
```

### Dock Visibility by Tab
```
                          | Data Load | Processing | Azimuthal |
--------------------------|-----------|------------|-----------|
layers_dock               |  hidden   |  visible   |  hidden   |
peak_picker_dock          |  hidden   |  visible   |  hidden   |
properties_dock           |  hidden   |  visible   |  hidden   |
export_dock               |  hidden   |  visible   |  hidden   |
azimuthal_properties_dock |  hidden   |  hidden    |  visible  |
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

### Dock Package Pattern (Established in properties/, azimuthal/, export/)
```
docks/dock_name/
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

## Processing Tab Content (EXTRACTED to processing_tab.py)

The Processing tab UI has been extracted to `gui/tabs/processing_tab.py`. Key changes:

```
ProcessingTab (gui/tabs/processing_tab.py - ~350 lines):
├── Uses modular panels from main_window_modules/panels/
│   ├── ProcessingSettingsPanel (window, overlap, smoothing, frequency)
│   ├── QCSettingsPanel (preset/custom modes)
│   └── CoxSettingsPanel (Cox FDWRA parameters)
├── Emits signals: process_requested, recompute_requested, settings_changed
├── Provides backward compatibility properties (window_length_spin, etc.)
└── FullProcessingSettings dataclass for bundling all settings

main_window.py changes:
├── Removed: create_control_panel(), create_settings_group(), create_window_group()
├── Removed: toggle handlers (_on_qc_enable_toggled, etc.)
├── Added: _on_process_requested() handler for ProcessingTab signal
├── Added: backward compatibility properties (proxy to processing_tab)
└── Uses PlottingController for plot operations
```

## Controller-Based Architecture (NEW)

The main_window.py has been refactored to delegate functionality to controllers:

```
main_window.py ────────────────────→ controllers/
                                      ├── ProcessingController
                                      │   ├── start_processing()
                                      │   ├── validate_results()
                                      │   ├── _show_qc_failure_dialog()
                                      │   └── recompute_hvsr()
                                      │
                                      ├── PlottingController  
                                      │   ├── plot_hvsr_results()
                                      │   ├── apply_properties()
                                      │   ├── recalculate_mean_from_visible()
                                      │   └── get_window_lines() / get_stat_lines()
                                      │
                                      └── SessionController
                                          ├── save_session()
                                          ├── load_session()
                                          ├── extract_gui_state()
                                          └── apply_gui_state()

Deprecated Methods in main_window.py:
├── process_hvsr() → Use ProcessingTab.process_requested signal
├── _validate_processing_results() → Delegates to ProcessingController
├── _show_qc_failure_dialog() → Delegates to ProcessingController
├── _generate_qc_diagnostic_report() → Delegates to ProcessingController
├── plot_results_separate_window() → Delegates to PlottingController
└── replot_with_properties() → Delegates to PlottingController

Backward Compatibility Properties (deprecated):
├── window_length_spin → self.processing_tab.window_length_spin
├── overlap_spin → self.processing_tab.overlap_spin
├── ... (26 total property proxies)
└── All marked for future removal
```

## Refactoring Candidates (Updated)

1. **main_window.py (2511 lines)** - PRIORITY: MEDIUM (reduced from HIGH)
   - ✅ Processing tab extracted to `gui/tabs/processing_tab.py`
   - ✅ Plotting delegated to PlottingController
   - Could still benefit from moving more callbacks to controllers
   - Session save/load could be fully delegated to SessionController

2. **data_load_tab.py (765 lines)** - PRIORITY: MEDIUM
   - Could benefit from extracting panels to submodules

3. **azimuthal_tab.py (720 lines)** - PRIORITY: MEDIUM
   - Could benefit from extracting settings panel

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
config/session.py       → Used by: gui/main_window.py, gui/main_window_modules/controllers/session_controller.py
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
| DataLoadTab | gui/tabs/data_load_tab.py | Tab 0: Data loading |
| ProcessingTab | gui/tabs/processing_tab.py | Tab 1: HVSR processing (NEW) |
| AzimuthalTab | gui/tabs/azimuthal_tab.py | Tab 2: Azimuthal processing |
| FullProcessingSettings | gui/tabs/processing_tab.py | Combined processing settings |
| HVSRAnalysis | api/analysis.py | High-level API |
