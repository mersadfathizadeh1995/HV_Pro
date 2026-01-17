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
HVSRMainWindow (main_window.py - 1204 lines) ← REFACTORED from 2886 lines (58% reduction)
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
    │   └── ProcessingTab (gui/tabs/processing_tab.py - ~350 lines)
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
gui/main_window.py (HVSRMainWindow - 1204 lines) ← REFACTORED from 2886 (58% reduction)
│
├── USES: gui/main_window_modules/
│         ├── menu_bar.py (MenuBarHelper) ← Menu creation
│         ├── view_state.py (ViewStateManager) ← View state + dock visibility
│         ├── ui_coordinator.py (UIUpdateCoordinator) ← UI update orchestration
│         ├── backward_compat.py (BackwardCompatMixin) ← Deprecated property proxies
│         ├── controllers/
│         │   ├── data_controller.py (DataController) ← Data loading
│         │   ├── processing_controller.py (ProcessingController) ← Processing logic
│         │   ├── plotting_controller.py (PlottingController) ← Plotting logic
│         │   ├── session_controller.py (SessionController) ← Session save/load
│         │   ├── window_controller.py (WindowController) ← Window management
│         │   ├── peak_controller.py (PeakController) ← Peak detection
│         │   └── export_controller.py (ExportController) ← Export operations
│         └── panels/ (ProcessingSettingsPanel, QCSettingsPanel, CoxSettingsPanel)
│
├── DEPRECATED: gui/mixins/ (removed - functionality moved to controllers)
│
├── CONTAINS: gui/tabs/
│             ├── data_load_tab.py (DataLoadTab) ← Tab 0
│             ├── processing_tab.py (ProcessingTab) ← Tab 1
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

## Controller-Based Architecture (COMPLETE)

The main_window.py uses a controller-based architecture with full delegation:

```
main_window.py ────────────────────→ controllers/
                                      │
                                      ├── DataController (data_controller.py)
                                      │   ├── load_from_dialog_result() ← Main loading entry
                                      │   ├── load_single_file()
                                      │   ├── load_multiple_files()
                                      │   └── load_file_groups()
                                      │
                                      ├── ProcessingController (processing_controller.py)
                                      │   ├── start_processing()
                                      │   ├── validate_results()
                                      │   ├── _show_qc_failure_dialog()
                                      │   └── recompute_hvsr()
                                      │
                                      ├── PlottingController (plotting_controller.py)
                                      │   ├── plot_hvsr_results()
                                      │   ├── apply_properties()
                                      │   ├── recalculate_mean_from_visible()
                                      │   └── get_window_lines() / get_stat_lines()
                                      │
                                      ├── SessionController (session_controller.py)
                                      │   ├── save_full_session() ← Complete session save
                                      │   ├── load_full_session() ← Complete session load
                                      │   ├── apply_session_state()
                                      │   └── extract_gui_state()
                                      │
                                      ├── WindowController (window_controller.py)
                                      │   ├── toggle_window()
                                      │   ├── reject_all()
                                      │   ├── accept_all()
                                      │   └── get_statistics()
                                      │
                                      ├── PeakController (peak_controller.py)
                                      │   ├── detect_peaks()
                                      │   ├── enable_manual_mode()
                                      │   ├── disable_manual_mode()
                                      │   └── on_peaks_changed()
                                      │
                                      └── ExportController (export_controller.py)
                                          ├── export_results()
                                          ├── export_plot_image()
                                          └── open_report_dialog()

Helper Classes:
├── MenuBarHelper (menu_bar.py)
│   └── build_complete_menu_bar() ← Complete menu setup
│
└── ViewStateManager (view_state.py)
    ├── toggle_plot_window()
    ├── toggle_preview_canvas()
    ├── toggle_loaded_data_column()
    ├── toggle_azimuthal_tab()
    └── handle_tab_changed()
```

### Delegation Patterns
```
Main Window Methods → Controller Methods:
├── on_files_selected() → data_ctrl.load_from_dialog_result()
├── on_window_toggled() → window_ctrl.toggle_window()
├── reject_all_windows() → window_ctrl.reject_all()
├── accept_all_windows() → window_ctrl.accept_all()
├── save_session() → session_ctrl.save_full_session()
├── load_session() → session_ctrl.load_full_session()
├── on_detect_peaks_requested() → peak_ctrl.detect_peaks()
├── on_manual_mode_requested() → peak_ctrl.toggle_manual_mode()
├── export_results() → export_ctrl.export_results()
├── export_plot_image() → export_ctrl.export_plot_image()
├── toggle_plot_window() → view_state.toggle_plot_window()
├── toggle_preview_canvas() → view_state.toggle_preview_canvas()
├── toggle_loaded_data_column() → view_state.toggle_loaded_data_column()
├── toggle_azimuthal_tab() → view_state.toggle_azimuthal_tab()
└── create_menu_bar() → menu_helper.build_complete_menu_bar()
```

### Backward Compatibility Properties (Deprecated)
```
Main window provides proxy properties to processing_tab widgets:
├── window_length_spin → self.processing_tab.window_length_spin
├── overlap_spin → self.processing_tab.overlap_spin
├── smoothing_spin → self.processing_tab.smoothing_spin
├── freq_min_spin → self.processing_tab.freq_min_spin
├── freq_max_spin → self.processing_tab.freq_max_spin
├── ... (26 total property proxies)
└── All marked for future removal
```

## Refactoring Summary

### Completed Refactoring
```
main_window.py:
├── 2886 → 2248 lines (Phase 1: ProcessingTab extraction)
├── 2248 → 1616 lines (Phase 2: Controller delegation)
├── 1616 → 1204 lines (Phase 3: UIUpdateCoordinator + BackwardCompatMixin)
└── Total reduction: 58% (1682 lines removed)

New modules created:
├── ui_coordinator.py (UIUpdateCoordinator) - Consolidates on_processing_finished/restore_session_gui
├── backward_compat.py (BackwardCompatMixin) - Holds 26 deprecated property proxies
└── view_state.py enhanced with handle_view_mode_changed()

Methods moved to controllers:
├── on_files_selected logic → DataController (~150 lines)
├── Window management → WindowController (~40 lines)
├── Session save/load → SessionController (~200 lines)
├── Peak detection → PeakController (~80 lines)
├── Export operations → ExportController (~100 lines)
├── Menu creation → MenuBarHelper (~150 lines)
├── View toggles → ViewStateManager (~80 lines)
├── Tab change handling → ViewStateManager.handle_tab_changed()
├── View mode handling → ViewStateManager.handle_view_mode_changed()
├── UI updates after processing → UIUpdateCoordinator (~200 lines)
└── Backward compat properties → BackwardCompatMixin (~130 lines)
```

### Remaining Refactoring Candidates
```
1. main_window.py (1204 lines) - PRIORITY: VERY LOW (significantly reduced)
   - Now mostly thin wrappers and signal routing
   
2. data_load_tab.py (765 lines) - PRIORITY: MEDIUM
   - Could benefit from extracting panels to submodules

3. azimuthal_tab.py (720 lines) - PRIORITY: MEDIUM
   - Could benefit from extracting settings panel
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
config/session.py       → Used by: gui/main_window.py, SessionController
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
| HVSRMainWindow | gui/main_window.py | Main application window (1204 lines) |
| DataController | gui/main_window_modules/controllers/ | Data loading operations |
| ProcessingController | gui/main_window_modules/controllers/ | Processing operations |
| PlottingController | gui/main_window_modules/controllers/ | Plot operations |
| SessionController | gui/main_window_modules/controllers/ | Session management |
| WindowController | gui/main_window_modules/controllers/ | Window management |
| PeakController | gui/main_window_modules/controllers/ | Peak detection |
| ExportController | gui/main_window_modules/controllers/ | Export operations |
| MenuBarHelper | gui/main_window_modules/menu_bar.py | Menu bar creation |
| ViewStateManager | gui/main_window_modules/view_state.py | View state + dock visibility |
| UIUpdateCoordinator | gui/main_window_modules/ui_coordinator.py | UI update orchestration |
| BackwardCompatMixin | gui/main_window_modules/backward_compat.py | Deprecated property proxies |
| DataLoadTab | gui/tabs/data_load_tab.py | Tab 0: Data loading |
| ProcessingTab | gui/tabs/processing_tab.py | Tab 1: HVSR processing |
| AzimuthalTab | gui/tabs/azimuthal_tab.py | Tab 2: Azimuthal processing |
| HVSRAnalysis | api/analysis.py | High-level API |
