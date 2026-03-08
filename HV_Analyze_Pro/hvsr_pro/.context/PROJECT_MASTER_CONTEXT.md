# HV_Pro — Master Project Context

**Version:** 0.2.0 | **Author:** OSCAR HVSR Development Team | **Updated:** 2026-03-08

---

## 1. PROJECT GOAL

HV_Pro is a professional, cross-platform desktop application for **HVSR (Horizontal-to-Vertical Spectral Ratio)** seismic site characterization. Built in Python 3.8+ with PyQt5, it provides:

- Single-station HVSR analysis with full QC pipeline
- Azimuthal HVSR analysis
- **Batch processing** of multiple stations (sub-package)
- **3D bedrock mapping** from HVSR + borehole data (sub-package / git submodule)
- Extensible via additional sub-packages under `hvsr_pro/packages/`

The app is designed so that **new analysis packages** can be added as sub-packages (or git submodules) under `hvsr_pro/packages/`, each exposing a main QMainWindow class that gets launched from the Tools menu.

---

## 2. REPOSITORY LAYOUT

```
HV_Pro/                                 # Git root
├── .gitmodules                         # Submodule declarations
├── SKILL.md                            # Refactoring methodology (parallel build)
├── SIGNAL_FLOW_ANALYSIS.txt            # Signal architecture notes
├── Files/                              # Test data, reference old code
│   ├── HVSR_old/                       # Legacy app (reference only)
│   └── XX06/                           # Test seismic data
├── HV_Analyze_Pro/                     # Application root
│   ├── launch_gui.py                   # Entry point: creates QApp → HVSRMainWindow
│   ├── requirements.txt                # All dependencies
│   ├── setup.py                        # Package installer
│   ├── _context/                       # Architecture docs (8 files + architecture_map.md)
│   └── hvsr_pro/                       # Main Python package
│       ├── __init__.py                 # v0.2.0, exports core public API
│       ├── core/                       # Data structures + loading
│       ├── loaders/                    # 8 format-specific loaders
│       ├── processing/                 # Windows, HVSR, rejection, smoothing, azimuthal
│       ├── config/                     # Settings, schemas, session persistence
│       ├── visualization/              # Matplotlib plotting functions
│       ├── api/                        # Programmatic API (HVSRAnalysis, batch_process)
│       ├── cli/                        # Command-line interface
│       ├── gui/                        # PyQt5 GUI (main window, tabs, docks, dialogs)
│       ├── utils/                      # General utilities
│       ├── tests/                      # Test suite
│       ├── packages/                   # ★ EXTENSIBLE SUB-PACKAGES ★
│       │   ├── __init__.py             # Namespace ("Extensible packages for additional functionality")
│       │   ├── batch_processing/       # Batch HVSR processing (29 Python files)
│       │   ├── bedrock_mapping/        # 3D bedrock mapping (git submodule, ~50 files)
│       │   └── 3d_bedrock/             # Placeholder (empty)
│       └── .context/                   # Context files (this file lives here)
└── Tests/                              # External test scripts
```

---

## 3. HOW THE MAIN APP WORKS

### 3.1 Entry Point
`launch_gui.py` → `QApplication` → `HVSRMainWindow(QMainWindow)` with Fusion style.
Uses `multiprocessing.freeze_support()` for Windows. Initializes `QWebEngineView` for interactive maps.

### 3.2 Main Window Architecture (`gui/main_window.py`)

**Core State:**
```python
self.data           # Currently loaded SeismicData
self.windows        # WindowCollection from processing
self.hvsr_result    # HVSRResult from computation
self.current_file   # Active file path
self.load_mode      # 'single' or 'batch'
```

**Controllers (modular, injected):**
```python
self.processing_ctrl   # ProcessingController — HVSR computation
self.plotting_ctrl     # PlottingController — plot management, window indexing
self.session_ctrl      # SessionController — save/load .hvsr_session files
self.window_ctrl       # WindowController — window state management
self.data_ctrl         # DataController — data loading orchestration
self.peak_ctrl         # PeakController — peak detection & picking
self.export_ctrl       # ExportController — file export
self.view_state        # ViewStateManager — dock/tab visibility per mode
self.ui_coordinator    # UIUpdateCoordinator — post-processing UI updates
```

**Tabs:**
| Index | Name | Widget | Purpose |
|-------|------|--------|---------|
| 0 | Data Load | `DataLoadTab` | File loading, preview, work directory |
| 1 | Processing | `ProcessingTab` | HVSR settings, QC, processing, window management |
| 2 | Azimuthal | `AzimuthalTab` | Azimuthal HVSR analysis |

**Docks:**
| Dock | Visible In |
|------|-----------|
| layers_dock | Processing |
| peak_picker_dock | Processing |
| properties_dock | Processing |
| export_dock | Processing |
| azimuthal_properties_dock | Azimuthal |

### 3.3 How Sub-Packages Connect

Sub-packages are **lazy-imported** from the **Tools menu** in the menu bar:

```python
# In main_window.py:
def open_batch_processing(self):
    from hvsr_pro.packages.batch_processing import BatchProcessingWindow
    if not hasattr(self, '_batch_window') or self._batch_window is None:
        self._batch_window = BatchProcessingWindow(self)
    self._batch_window.show()

def open_bedrock_mapping(self):
    from hvsr_pro.packages.bedrock_mapping import BedrockMappingWindow
    if not hasattr(self, '_bedrock_window') or self._bedrock_window is None:
        self._bedrock_window = BedrockMappingWindow(self)
    self._bedrock_window.show()
```

Menu wiring in `gui/main_window_modules/menu_bar.py`:
```python
batch_action.triggered.connect(self.parent.open_batch_processing)
bedrock_action.triggered.connect(self.parent.open_bedrock_mapping)
```

**Pattern for adding a new package:**
1. Create `hvsr_pro/packages/new_package/` with `__init__.py` exporting a `QMainWindow` subclass
2. Add `open_new_package()` method to `main_window.py` (lazy import, window caching)
3. Add menu action in `menu_bar.py` under Tools menu
4. Optionally register as git submodule in `.gitmodules`

---

## 4. CORE PROCESSING PIPELINE

### 4.1 Data Flow
```
loaders/ → core/data_handler → core/data_structures
(8 formats)  (HVSRDataHandler)   (SeismicData, ComponentData)
```

**Supported formats:** txt (OSCAR ASCII), miniseed, saf, sac, gcf, peer, minishark, srecord3c_json

### 4.2 Processing Pipeline
```
SeismicData → WindowManager → HVSRProcessor → RejectionEngine → HVSRResult
              (create windows)  (FFT, smooth,    (8 QC algorithms)  (frequencies,
               (taper, quality)  H/V ratio)       (FDWRA optional)   mean/median/std,
                                                                      peaks, spectra)
```

### 4.3 Key Processing Classes

| Class | Location | Purpose |
|-------|----------|---------|
| `SeismicData` | core/data_structures.py | 3-component seismic data (E, N, Z) |
| `ComponentData` | core/data_structures.py | Single component with metadata |
| `HVSRDataHandler` | core/data_handler.py | Universal loader with cache |
| `WindowManager` | processing/windows/manager.py | Create/taper time windows |
| `WindowCollection` | processing/windows/structures.py | Window container |
| `HVSRProcessor` | processing/hvsr/processor.py | FFT → smooth → H/V → stats |
| `HVSRResult` | processing/hvsr/structures.py | Result container with peaks |
| `WindowSpectrum` | processing/hvsr/structures.py | Per-window spectral data |
| `Peak` | processing/hvsr/structures.py | Peak detection result |
| `RejectionEngine` | processing/rejection/engine.py | QC pipeline coordinator |
| `CoxFDWRARejection` | processing/rejection/algorithms/ | Frequency-dependent window rejection |

### 4.4 Smoothing Methods
8 methods in `processing/smoothing/`: konno_ohmachi, parzen, savitzky_golay, linear_rectangular, log_rectangular, linear_triangular, log_triangular, none

### 4.5 Config System
```python
ApplicationSettings   # Combines: WindowSettings + ProcessingSettings + QCSettings + ExportSettings + PlotSettings
SessionManager        # Pickle-based persistence (.hvsr_session files)
PlotProperties        # 3 presets: publication, analysis, minimal
```

---

## 5. BATCH PROCESSING PACKAGE

**Location:** `hvsr_pro/packages/batch_processing/`
**Export:** `BatchProcessingWindow(QMainWindow)`
**Files:** 29 Python files across 5 subdirectories

### 5.1 Structure
```
batch_processing/
├── batch_window.py              # Main window (1000+ lines, 2 tabs: Analysis | Results)
├── station_manager.py           # Station file table (QTableWidget)
├── data_adapter.py              # Format detection & conversion
├── results_handler.py           # Load & aggregate HVSR results
├── report_export.py             # Report generation (Excel, CSV, JSON, MAT)
├── figure_gen.py                # Publication figure generation
├── palette.py                   # Color palette
├── dialogs/                     # Settings dialogs
│   ├── hvsr_settings.py         # HVSR algorithm parameters
│   ├── qc_settings.py           # Quality control configuration
│   ├── time_windows.py          # Time window config with timezone
│   ├── interactive_peak_dialog.py
│   ├── figure_export_dialog.py
│   └── figure_export_settings.py
├── workers/                     # Background threads
│   ├── data_worker.py           # DataProcessWorker (file conversion)
│   └── hvsr_worker.py           # BatchHVSRWorker (parallel HVSR, 400+ lines)
├── widgets/                     # Results display
│   ├── results_canvas.py        # Matplotlib HVSR curves
│   ├── results_table.py         # Results data table
│   ├── results_histograms.py    # Peak frequency histogram
│   ├── results_layer_tree.py    # Layer visibility toggles
│   └── window_layers_panel.py   # Window/layer management
└── processing/                  # Core analysis
    ├── structures.py            # StationResult, PeakStatistics, AutomaticWorkflowResult
    ├── automatic_workflow.py    # Automatic peak detection (490+ lines)
    ├── peaks.py                 # Peak detection algorithms
    └── output_organizer.py      # Output directory organization
```

### 5.2 Workflow
1. **Data Loading:** User adds station files → DataProcessWorker converts to MAT
2. **HVSR Processing:** BatchHVSRWorker processes each station (FFT → smooth → H/V → QC → peaks)
3. **Analysis:** Automatic workflow aggregates results, computes statistics, detects combined peaks
4. **Results:** Table, curves, histograms, layer tree, report export

### 5.3 Key Settings
```python
{
    'window_length': 120,           # seconds
    'overlap': 0.5,
    'smoothing_method': 'konno_ohmachi',
    'konno_ohmachi_bandwidth': 40,
    'freq_min': 0.2, 'freq_max': 30.0,
    'n_frequencies': 300,
    'horizontal_method': 'geometric_mean',
    'taper': 'tukey',
    'statistics_method': 'lognormal',
    'min_prominence': 0.5,          # configurable
    'min_amplitude': 2.0,
    'peak_basis': 'median',         # 'median' or 'mean'
}
```

---

## 6. BEDROCK MAPPING PACKAGE

**Location:** `hvsr_pro/packages/bedrock_mapping/` (git submodule)
**Repo:** `https://github.com/mersadfathizadeh1995/bedrock_mapping.git`
**Export:** `BedrockMappingWindow(QMainWindow)`
**Files:** ~50 Python files

### 6.1 Structure
```
bedrock_mapping/
├── bedrock_window.py            # Main window (QMainWindow, ~340 lines)
├── state.py                     # BedrockState(QObject) — centralized state with Qt signals
├── core/                        # Computation
│   ├── bedrock.py               # Depth-to-bedrock calculations
│   ├── boundaries.py            # Boundary polygon operations (Shapely)
│   ├── coordinates.py           # Coordinate transforms (pyproj)
│   ├── interpolation.py         # 11 interpolation methods
│   ├── visualization_2d.py      # 2D contour generation
│   ├── models/                  # Data models
│   │   ├── borehole.py          # Borehole class with soil layers
│   │   ├── collection.py        # StationCollection
│   │   ├── enums.py             # StationType, StationStatus, DataSource
│   │   ├── hvsr.py              # HVSRStation (f₀, Vs → bedrock depth)
│   │   └── layers.py            # BoreholeLayer
│   ├── io/                      # File I/O
│   │   ├── kml.py               # KML/KMZ export
│   │   ├── readers.py           # CSV/Excel readers
│   │   └── kml_stations/        # Google Earth station export (7 files)
│   └── visualization/           # 3D visualization
│       ├── mesh_3d.py           # PyVista mesh
│       ├── plotter_3d.py        # 3D plotting
│       └── collada_exporter.py  # COLLADA export for Google Earth
├── utils/
│   ├── coordinate_system.py     # CRS selector & transformation
│   ├── coordinates.py           # Map coordinate utilities
│   └── hvpro_bridge.py          # ★ Integration with main HV_Pro app
└── widgets/                     # PyQt5 UI (~20 files)
    ├── data_loader.py           # Surface/bedrock data loading
    ├── data_mapper_spatial.py   # Column mapping dialog
    ├── depth_calc.py            # Depth computation widget
    ├── global_settings.py       # Global settings dialog (4 tabs)
    ├── interpolation_panel.py   # Interpolation method selector
    ├── layer_panel.py           # Layer visibility + display settings
    ├── map_widget.py            # Folium map (QWebEngineView)
    ├── station_manager.py       # HVSR station/borehole manager
    ├── view_2d.py               # 2D contour plot (Plotly)
    ├── view_3d.py               # 3D matplotlib view (rewritten: multi-layer, unit conversion)
    ├── view_3d_plotly.py        # 3D Plotly interactive view
    ├── export_map.py            # Map/Google Earth export (refactored orchestrator)
    ├── export_2d.py             # 2D export
    ├── export_3d_plotly.py      # 3D Plotly export
    ├── export_3d_view.py        # 3D view export
    ├── export_panel.py          # Generic export framework
    ├── collapsible_group.py     # Collapsible section widget
    └── export_map_modules/      # ★ Modular export (SKILL.md refactored, 9 files)
        ├── helpers.py           # unit_factor, scale maps
        ├── level_computation.py # compute_levels() pure math
        ├── csv_builder.py       # CSV station export
        ├── image_builder.py     # Contour image export
        ├── ge_builder.py        # Google Earth KML/KMZ builder (dataclasses)
        ├── layer_manager.py     # Layer checkbox management
        ├── settings_bridge.py   # ContourSettingsBridge, LevelSettingsBridge, LegendSettingsBridge
        ├── ui_sections.py       # build_*_section() UI factories
        └── _old_code/           # Archived original (1134 lines)
```

### 6.2 BedrockState — Centralized State

**Signals:**
| Signal | Type | Purpose |
|--------|------|---------|
| `surface_data_changed` | `()` | Surface elevation data loaded |
| `bedrock_data_changed` | `()` | Bedrock elevation data loaded |
| `depth_result_changed` | `()` | Depth-to-bedrock computed |
| `stations_changed` | `()` | HVSR stations or boreholes modified |
| `boundary_changed` | `()` | Project boundary polygon changed |
| `layer_visibility_changed` | `(str)` | Layer toggled, passes layer name |
| `active_tab_changed` | `(str)` | View tab changed: 'map', '2d', '3d_plotly', '3d' |
| `map_needs_refresh` | `()` | Map should refresh |
| `display_settings_changed` | `()` | Contour/legend settings changed |
| `status_message` | `(str)` | Status bar update |

**Per-Layer Contour Config:**
```python
state.contour_layer_configs = {
    'surface': {
        'colorscale': 'YlOrBr', 'opacity': 0.7, 'levels': 15,
        'level_mode': 'count',    # 'count' | 'nice' | 'fixed'
        'fixed_interval': 10.0,
        'show_lines': True, 'show_labels': True,
        'line_width': 0.5, 'label_fontsize': 8, 'decimal_places': 1,
    },
    'bedrock': {'colorscale': 'Blues', ...},
    'depth':   {'colorscale': 'RdYlGn', ...},
}
```

**Per-Layer Legend Config:**
```python
state.layer_legend_configs = {
    'surface': {'visible': True, 'position': 'Bottom Right', 'orientation': 'Vertical',
                'scale': 1.0, 'font_size': 11, 'num_ticks': 5, 'tick_mode': 'Auto'},
    # ... similar for bedrock, depth, surface_points, bedrock_points, stations
}
state.combine_legends: bool  # Combine all legends into one
```

**Unit System:**
```python
state.unit_system = 'SI'       # 'SI' or 'Imperial'
state.unit_label → 'm' or 'ft'
state.display_unit → 'meters' or 'feet'
# ALL elevations stored internally in METERS; converted at display time: z * 3.28084
```

**Per-Tab Layer Visibility:**
```python
state._tab_layer_visibility = {
    'map': {'surface_points': True, 'boundary': True, 'surface_contour': True, ...},
    '2d': {...}, '3d_plotly': {...}, '3d': {...}
}
```

### 6.3 BedrockMappingWindow Layout

```
┌──────────────────────────────────────────────────────────────────────┐
│  File | View | Tools                                                 │
├──────────┬───────────────────────────────────────┬──────────────────┤
│ LEFT     │  CENTER (view tabs)                    │ RIGHT DOCK      │
│ (control │  ┌─────────────────────────────┐      │ ┌──────────────┐│
│  tabs)   │  │ 🗺️ Map | 📊 2D | 📈 3D | 🔺3DV  │ │ Layers tab   ││
│          │  ├─────────────────────────────┤      │ │ • Tree       ││
│ 📁 Data  │  │                             │      │ │ • Display    ││
│ 📐 Interp│  │  Active view widget         │      │ │ • Legend     ││
│ 📍 Stns  │  │                             │      │ ├──────────────┤│
│ 📏 Depth │  │                             │      │ │ Export tab   ││
│          │  └─────────────────────────────┘      │ │ (per-view)   ││
├──────────┴───────────────────────────────────────┴──────────────────┤
│  Status: Surface: N pts | Bedrock: N pts | Stations: N              │
└─────────────────────────────────────────────────────────────────────┘
```

**Tab Index Mapping:**
```python
_TAB_NAMES = {0: 'map', 1: '2d', 2: '3d_plotly', 3: '3d'}
```

### 6.4 Signal Flow Example
```
User changes opacity in LayerPanel
  → state.contour_layer_configs['surface']['opacity'] = value
  → state.display_settings_changed.emit()
  → MapWidget._schedule_refresh() (300ms debounce)
  → View2DWidget._schedule_render() (checks active tab, sets _dirty if inactive)
  → View3DPlotlyWidget._schedule() (checks active tab, sets _dirty if inactive)
  → View3DWidget._schedule_render() (checks active tab, sets _dirty if inactive)
  → Tab switch: bedrock_window._on_view_tab_changed checks _dirty, calls render()
```

### 6.5 HV_Pro Bridge
`utils/hvpro_bridge.py` provides:
- `get_batch_results_from_hvpro(main_window)` — retrieves HVSR batch results
- `ImportHVProResultsDialog` — dialog to import HVSR stations into bedrock state

---

## 7. GIT & SUBMODULE STRUCTURE

### 7.1 Main repo (HV_Pro)
```
Latest commits:
  46795fa (HEAD) batch_processing
  bb8f7b7 batch_processing_added
  b274acd refactoring_update
```

### 7.2 Bedrock Mapping submodule
```
Registered in .gitmodules:
  path = HV_Analyze_Pro/hvsr_pro/packages/bedrock_mapping
  url  = https://github.com/mersadfathizadeh1995/bedrock_mapping.git

Latest commits (inside submodule):
  db5056c fix: rewrite 3D matplotlib view
  3758e2e fix: 2D plot uses raw per-layer opacity
  b46b9cb refactor: modularise export_map.py into export_map_modules/
  84af3d3 fix: render() TypeError when switching to map tab
  73ac69f feat: per-layer contour settings in Google Earth export
```

### 7.3 Adding a New Sub-Package as Submodule
```bash
# From HV_Pro root:
git submodule add <repo_url> HV_Analyze_Pro/hvsr_pro/packages/<package_name>
git commit -m "Add <package_name> submodule"
```
Or simply create the package directory locally (non-submodule).

---

## 8. DEPENDENCIES

### Core
```
numpy==2.2.4, scipy==1.15.2, matplotlib==3.10.1, pandas>=2.2
openpyxl>=3.1, obspy==1.4.2
```

### GUI
```
PyQt5==5.15.11, PyQtWebEngine>=5.15
folium>=0.17, branca>=0.7, plotly>=5.18
```

### Geospatial
```
pyproj>=3.6, shapely>=2.0
```

### 3D/Export
```
pyvista>=0.43, Pillow>=10.0, pykrige>=1.7
```

### ML/Testing
```
scikit-learn>=1.4, pytest>=8.0
```

---

## 9. REFACTORING METHODOLOGY (SKILL.md)

**Approach:** Parallel Build — never modify original during refactoring.

**Phases:**
1. **Analyze** — Map structure, trace data flow, spot code smells, find extraction candidates
2. **Plan** — Create `{script}_modules/` folder, plan extraction order (least-coupled first)
3. **Execute** — Extract → Test → Integrate → Repeat (one module at a time)
4. **Finalize** — Archive original to `_old_code/`, swap in new orchestrator

**File size guidelines:**
| Component | Target | Maximum |
|-----------|--------|---------|
| Core functions | 150 lines | 200 lines |
| GUI components | 200 lines | 300 lines |
| Controllers | 200 lines | 350 lines |
| Dock sections | 50-100 lines | 150 lines |

---

## 10. TESTING APPROACH

- **Syntax:** `py_compile` for all modified files
- **GUI headless:** `QT_QPA_PLATFORM=offscreen` for headless Qt widget instantiation
- **Import path:** `sys.path.insert(0, 'HV_Analyze_Pro')` from repo root
- **Font warnings:** Harmless (Qt no longer ships fonts in offscreen mode)

---

## 11. KNOWN ISSUES & TECHNICAL NOTES

1. **QWidget.render() ambiguity:** `hasattr(widget, 'render')` is always True for QWidget subclasses. Use explicit tab name mapping instead.
2. **Edit tool limitation:** Fails on files with Unicode box-drawing characters (U+2500). Workaround: use Python scripts with str.find/replace.
3. **webkitStorageInfo deprecation:** Cosmetic warning from Qt's Chromium engine, not actionable.
4. **Unit conversion:** ALL data stored in meters internally. Display-time conversion only.
5. **Per-layer opacity:** Do NOT use multipliers on opacity values; use raw `cfg['opacity']` directly.

---

## 12. PATTERN FOR ADDING A NEW PACKAGE

### Step-by-step:
1. Create directory: `hvsr_pro/packages/new_package/`
2. Create `__init__.py`:
   ```python
   """
   New Package
   ===========
   Description of what this package does.
   Accessible from the main app via Tools > New Package.
   """
   from .main_window import NewPackageWindow
   __all__ = ['NewPackageWindow']
   ```
3. Create main window class inheriting `QMainWindow`
4. Add launcher to `main_window.py`:
   ```python
   def open_new_package(self):
       from hvsr_pro.packages.new_package import NewPackageWindow
       if not hasattr(self, '_new_package_window') or self._new_package_window is None:
           self._new_package_window = NewPackageWindow(self)
       self._new_package_window.show()
       self._new_package_window.raise_()
       self._new_package_window.activateWindow()
   ```
5. Wire in `menu_bar.py`:
   ```python
   new_action = QAction("New Package", self.parent)
   new_action.triggered.connect(self.parent.open_new_package)
   tools_menu.addAction(new_action)
   ```
6. Optionally register as git submodule

### Architecture guidelines:
- Each package gets its own `state.py` (QObject with signals) if it has complex state
- Use `_dirty` flag pattern for lazy rendering on tab switches
- Connect to `display_settings_changed` + `map_needs_refresh` for real-time updates
- Follow SKILL.md for any file over 300 lines
