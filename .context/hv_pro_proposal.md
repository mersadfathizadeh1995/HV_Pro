# HV_Pro New Package Proposal

## 1. Package Location
```
D:\Research\Narm_Afzar\Git_hub\HV_Pro\hv_pro\
```

---

## 2. Proposed Folder Structure

```
hv_pro/
├── __init__.py                    # Package init, version
├── __main__.py                    # Entry point: python -m hv_pro
├── app.py                         # Application launcher
│
├── core/                          # Core data structures
│   ├── __init__.py
│   ├── data_structures.py         # SeismicData, ComponentData, ThreeComponentData
│   ├── hvsr_structures.py         # HVSRResult, WindowSpectrum, PeakInfo
│   ├── window_collection.py       # WindowCollection, SeismicWindow
│   ├── metadata.py                # File/processing metadata
│   └── cache.py                   # HVSRDataCache for multi-file
│
├── loaders/                       # Data loading with mapper support
│   ├── __init__.py
│   ├── base_loader.py             # Abstract BaseLoader class
│   ├── txt_loader.py              # Text file loader (3-col or multi-col)
│   ├── miniseed_loader.py         # MiniSEED loader (obspy)
│   └── mapper.py                  # Column mapper dialog & logic (from dc_cut)
│
├── processing/                    # HVSR processing pipeline
│   ├── __init__.py
│   ├── window_manager.py          # WindowManager - windowing logic
│   ├── hvsr_processor.py          # HVSRProcessor - main computation
│   ├── spectral_processing.py     # FFT, Konno-Ohmachi, horizontal methods
│   ├── peak_detection.py          # Peak finding, SESAME criteria
│   ├── quality_metrics.py         # WindowQualityCalculator
│   │
│   ├── rejection/                 # QC algorithms (organized subfolder)
│   │   ├── __init__.py
│   │   ├── engine.py              # RejectionEngine coordinator
│   │   ├── base.py                # BaseRejectionAlgorithm, RejectionResult
│   │   ├── threshold.py           # QualityThresholdRejection
│   │   ├── statistical.py         # StatisticalOutlierRejection
│   │   ├── stalta.py              # STALTARejection
│   │   ├── frequency_domain.py    # FrequencyDomainRejection
│   │   ├── amplitude.py           # AmplitudeRejection
│   │   ├── cox_fdwra.py           # Cox et al. (2020) FDWRA
│   │   └── ml.py                  # IsolationForestRejection (optional)
│   │
│   └── statistics.py              # Lognormal stats (from hvsrpy)
│
├── gui/                           # PyQt5 + qfluentwidgets GUI
│   ├── __init__.py
│   ├── app.py                     # QApplication setup, theme
│   ├── main_window.py             # FluentWindow-based main window
│   │
│   ├── interfaces/                # Navigation interfaces (pages)
│   │   ├── __init__.py
│   │   ├── home_interface.py      # Welcome/quick start
│   │   ├── single_file_interface.py   # Single file processing
│   │   └── settings_interface.py  # Application settings
│   │
│   ├── docks/                     # Dockable panels
│   │   ├── __init__.py
│   │   ├── layers_dock.py         # Window layer visibility
│   │   ├── peak_picker_dock.py    # Peak selection/editing
│   │   ├── properties_dock.py     # Plot properties
│   │   └── qc_dock.py             # QC settings/results
│   │
│   ├── dialogs/                   # Modal dialogs
│   │   ├── __init__.py
│   │   ├── data_input_dialog.py   # File selection + mapper
│   │   ├── column_mapper_dialog.py # Column mapping (from dc_cut)
│   │   ├── qc_settings_dialog.py  # Advanced QC configuration
│   │   ├── export_dialog.py       # Export options
│   │   └── preferences_dialog.py  # App preferences
│   │
│   ├── widgets/                   # Custom widgets
│   │   ├── __init__.py
│   │   ├── interactive_canvas.py  # Matplotlib interactive canvas
│   │   ├── plot_window.py         # Separate plot window
│   │   └── view_mode_selector.py  # Timeline/HVSR/Stats toggle
│   │
│   └── figures/                   # Publication figures (menu section)
│       ├── __init__.py
│       ├── figure_generator.py    # Publication figure generator
│       ├── hvsr_curve_figure.py   # HVSR curve plots
│       ├── window_overview_figure.py  # Window timeline
│       ├── quality_figure.py      # QC visualization
│       └── statistics_figure.py   # Statistical analysis plots
│
├── visualization/                 # Non-GUI plotting
│   ├── __init__.py
│   ├── plotter.py                 # HVSRPlotter high-level interface
│   ├── hvsr_plots.py              # HVSR curve plotting functions
│   ├── window_plots.py            # Window visualization
│   └── style.py                   # Plot styles, colors
│
├── utils/                         # Utilities
│   ├── __init__.py
│   ├── export_utils.py            # CSV, JSON export
│   ├── signal_utils.py            # Detrend, taper, gap check
│   ├── file_utils.py              # Path handling
│   └── time_utils.py              # Timezone handling
│
├── cli/                           # Command-line interface
│   ├── __init__.py
│   └── main.py                    # Click/argparse CLI
│
└── resources/                     # Assets
    ├── icons/
    └── styles/
```

---

## 3. GUI Design

### 3.1 Main Window Structure (FluentWindow)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  HV Pro                                                    ─ □ ×            │
├──────┬──────────────────────────────────────────────────────────────────────┤
│      │  ┌─────────────────────────────────────────────────────────────────┐ │
│ NAV  │  │                                                                 │ │
│      │  │                     CENTRAL CONTENT AREA                        │ │
│ 🏠   │  │           (Interactive Canvas + Embedded Controls)              │ │
│ Home │  │                                                                 │ │
│      │  │  ┌─────────────────────────────────┐  ┌──────────────────────┐  │ │
│ 📂   │  │  │                                 │  │  Docked Panels       │  │ │
│ Open │  │  │    HVSR CURVE PLOT             │  │  ┌─────────────────┐  │  │ │
│      │  │  │    (matplotlib interactive)     │  │  │ Layers (toggle) │  │  │ │
│ 📊   │  │  │                                 │  │  ├─────────────────┤  │  │ │
│ Figs │  │  │                                 │  │  │ Peak Picker     │  │  │ │
│      │  │  │                                 │  │  ├─────────────────┤  │  │ │
│ ⚙️   │  │  │                                 │  │  │ Properties      │  │  │ │
│ Set  │  │  └─────────────────────────────────┘  │  └─────────────────┘  │  │ │
│      │  │                                                                 │ │
│      │  └─────────────────────────────────────────────────────────────────┘ │
├──────┴──────────────────────────────────────────────────────────────────────┤
│  Status: Ready  |  Windows: 45/50 active  |  Peak: 1.23 Hz                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Navigation Menu (Left Sidebar)

| Icon | Label | Function |
|------|-------|----------|
| 🏠 | Home | Welcome page, recent files, quick start |
| 📂 | Open Data | Data loading with mapper option |
| 📊 | **Figures** | **Publication figure generation** |
| ⚙️ | Settings | App preferences, themes |

### 3.3 Figures Menu (Submenu/Interface)

The **Figures** section is a key feature. It will contain:

| Figure Type | Description | Source |
|-------------|-------------|--------|
| HVSR Curve | Mean curve with confidence bands | hvsr_pro + hvsrpy style |
| Individual Windows | All window curves overlay | hvsr_pro |
| Window Timeline | Active/rejected status | hvsr_pro |
| Quality Metrics | SNR, stationarity, etc. | hvsr_pro |
| Peak Statistics | Peak frequency distribution | hvsr_pro |
| SESAME Report | Reliability criteria check | hvsrpy |
| Publication Figure | Combined multi-panel | New (like dc_cut) |

### 3.4 Dockable Panels

Based on hvsr_pro + dc_cut patterns:

| Dock | Purpose | Position |
|------|---------|----------|
| **Layers** | Toggle window visibility, batch ops | Right |
| **Peak Picker** | Interactive peak selection | Right (tabbed) |
| **Properties** | Plot appearance settings | Right (tabbed) |
| **QC Summary** | Rejection results, stats | Right (tabbed) |

### 3.5 Interactive Plot Window

Key features from hvsr_pro to preserve:
- **Click-to-toggle** window rejection on timeline
- **Zoom/pan** with matplotlib navigation
- **Real-time** mean recalculation when toggling
- **Separate window** option for more space
- **View mode selector**: Timeline / HVSR / Stats panels

---

## 4. Column Mapper Feature

Adapted from dc_cut's `ColumnMapperDialog`:

### 4.1 When to Show Mapper
- User checks "Map columns manually" in data input dialog
- OR automatic detection fails / user wants to override

### 4.2 Mapper Dialog Layout
```
┌─────────────────────────────────────────────────────────────────┐
│  Map Data Columns                                               │
├─────────────────────────────────────────────────────────────────┤
│  Status: ✅ Valid mapping (Time + 3 components)                 │
│                                                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────┐ │
│  │ Column 1 │ │ Column 2 │ │ Column 3 │ │ Column 4 │ │Col 5...│ │
│  ├──────────┤ ├──────────┤ ├──────────┤ ├──────────┤ ├────────┤ │
│  │[Time    ]│ │[East    ]│ │[North   ]│ │[Vertical]│ │[Skip  ]│ │
│  ├──────────┤ ├──────────┤ ├──────────┤ ├──────────┤ ├────────┤ │
│  │ 0.000    │ │ 0.00123  │ │ 0.00456  │ │ 0.00789  │ │ ...    │ │
│  │ 0.010    │ │ 0.00234  │ │ 0.00567  │ │ 0.00890  │ │ ...    │ │
│  │ ...      │ │ ...      │ │ ...      │ │ ...      │ │ ...    │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └────────┘ │
│                                                                 │
│  ☑ Remember mapping for similar files                          │
│                                           [Cancel]  [OK]        │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 Column Type Options
- Skip (ignore column)
- Time (seconds)
- East (E-W component)
- North (N-S component)
- Vertical (Z component)
- Sampling Rate (optional, if in file)

---

## 5. Script Migration Plan

### 5.1 FROM: `hvsr_pro/core/` → TO: `hv_pro/core/`

| Source File | Target File | Notes |
|-------------|-------------|-------|
| `data_structures.py` | `core/data_structures.py` | Copy directly |
| `hvsr_structures.py` | `core/hvsr_structures.py` | Copy directly |
| `data_handler.py` | `core/data_handler.py` | Copy, update imports |
| `data_cache.py` | `core/cache.py` | Copy directly |
| `metadata.py` | `core/metadata.py` | Copy directly |

### 5.2 FROM: `hvsr_pro/loaders/` → TO: `hv_pro/loaders/`

| Source File | Target File | Notes |
|-------------|-------------|-------|
| `base_loader.py` | `loaders/base_loader.py` | Copy directly |
| `txt_loader.py` | `loaders/txt_loader.py` | Copy directly |
| `miniseed_loader.py` | `loaders/miniseed_loader.py` | Copy directly |
| **NEW** | `loaders/mapper.py` | Create from dc_cut pattern |

### 5.3 FROM: `hvsr_pro/processing/` → TO: `hv_pro/processing/`

| Source File | Target File | Notes |
|-------------|-------------|-------|
| `window_manager.py` | `processing/window_manager.py` | Copy directly |
| `hvsr_processor.py` | `processing/hvsr_processor.py` | Copy directly |
| `spectral_processing.py` | `processing/spectral_processing.py` | Copy directly |
| `peak_detection.py` | `processing/peak_detection.py` | Copy directly |
| `quality_metrics.py` | `processing/quality_metrics.py` | Copy directly |
| `rejection_engine.py` | `processing/rejection/engine.py` | Reorganize |
| `rejection_algorithms.py` | `processing/rejection/base.py` + `threshold.py` + `statistical.py` | Split |
| `rejection_advanced.py` | `processing/rejection/stalta.py` + `frequency_domain.py` + `amplitude.py` | Split |
| `rejection_cox_fdwra.py` | `processing/rejection/cox_fdwra.py` | Copy directly |
| `rejection_ml.py` | `processing/rejection/ml.py` | Copy directly |
| **NEW** | `processing/statistics.py` | Add lognormal from hvsrpy |

### 5.4 FROM: `hvsr_pro/gui/` → TO: `hv_pro/gui/`

| Source File | Target File | Notes |
|-------------|-------------|-------|
| `main_window.py` | `gui/main_window.py` | **REWRITE** for FluentWindow |
| `interactive_canvas.py` | `gui/widgets/interactive_canvas.py` | Copy, update imports |
| `layers_dock.py` | `gui/docks/layers_dock.py` | Copy, update imports |
| `peak_picker_dock.py` | `gui/docks/peak_picker_dock.py` | Copy, update imports |
| `properties_dock.py` | `gui/docks/properties_dock.py` | Copy, update imports |
| `view_mode_selector.py` | `gui/widgets/view_mode_selector.py` | Copy directly |
| `data_input_dialog.py` | `gui/dialogs/data_input_dialog.py` | Copy, add mapper |
| `export_dialog.py` | `gui/dialogs/export_dialog.py` | Copy directly |
| `advanced_qc_dialog.py` | `gui/dialogs/qc_settings_dialog.py` | Copy directly |
| `plot_window_manager.py` | `gui/widgets/plot_window.py` | Simplify |
| **NEW** | `gui/dialogs/column_mapper_dialog.py` | Create from dc_cut |
| **NEW** | `gui/interfaces/home_interface.py` | Create new |
| **NEW** | `gui/interfaces/single_file_interface.py` | Create new |
| **NEW** | `gui/figures/` | Create figure generators |

### 5.5 FROM: `hvsr_pro/visualization/` → TO: `hv_pro/visualization/`

| Source File | Target File | Notes |
|-------------|-------------|-------|
| `plotter.py` | `visualization/plotter.py` | Copy directly |
| `hvsr_plots.py` | `visualization/hvsr_plots.py` | Copy directly |
| `window_plots.py` | `visualization/window_plots.py` | Copy directly |
| `statistics_plots.py` | `visualization/statistics_plots.py` | Copy directly |

### 5.6 FROM: `hvsr_pro/utils/` → TO: `hv_pro/utils/`

| Source File | Target File | Notes |
|-------------|-------------|-------|
| `export_utils.py` | `utils/export_utils.py` | Copy directly |
| `signal_utils.py` | `utils/signal_utils.py` | Copy directly |

### 5.7 NEW Files to Create

| File | Source/Inspiration |
|------|-------------------|
| `loaders/mapper.py` | dc_cut `gui/open_data.py` ColumnMapperDialog |
| `gui/dialogs/column_mapper_dialog.py` | dc_cut ColumnMapperDialog |
| `gui/figures/figure_generator.py` | dc_cut pub_figures |
| `gui/interfaces/*.py` | hvstrip_progressive pages |
| `processing/statistics.py` | hvsrpy statistics.py |
| `cli/main.py` | New CLI with argparse/click |

---

## 6. Files NOT to Copy (Batch-related)

Skip these for now (no batch processing):
- `hvsr_pro/batch/` (entire folder)
- `hvsr_pro/gui/batch_tab.py`
- `hvsr_pro/gui/batch_window.py`
- `hvsr_pro/gui/batch_panels.py`

---

## 7. Dependencies

```
# requirements.txt
numpy>=1.20
scipy>=1.7
matplotlib>=3.5
obspy>=1.3
PyQt5>=5.15
qfluentwidgets>=1.0.0
qframelesswindow
darkdetect
```

---

## 8. Next Steps

1. **Create folder structure** at `D:\Research\Narm_Afzar\Git_hub\HV_Pro\hv_pro\`
2. **Copy core files** (data structures, loaders, processing)
3. **Create new main_window.py** with FluentWindow base
4. **Implement column mapper** from dc_cut pattern
5. **Create interfaces** (home, single_file, settings)
6. **Migrate docks** with updated imports
7. **Create figures menu/interface**
8. **Add CLI skeleton**
9. **Test and iterate**
