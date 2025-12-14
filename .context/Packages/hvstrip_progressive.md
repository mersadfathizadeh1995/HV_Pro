# HVSR Progressive Layer Stripping Package Analysis

## Overview
**Version:** 1.0.0  
**Location:** `D:\Research\Narm_Afzar\Git_hub\HV_Pro\Codes_To_use\hvstrip_progressive`  
**Purpose:** Progressive layer stripping analysis for HVSR data - systematically removes layers from a velocity model to understand layer contributions to HVSR curves.

---

## Package Architecture

```
hvstrip_progressive/
├── __init__.py           # Package entry, exports core modules
├── run_batch_research.py # Standalone batch research script
├── bin/                  # Binary executables
│   └── exe_Linux/        # Linux HVf executables
│   └── exe_Win/          # Windows HVf.exe
├── cli/                  # Command-line interface
│   ├── __init__.py
│   └── main.py
├── config/               # Configuration files
├── core/                 # Core processing modules
│   ├── stripper.py           # Layer stripping (peeling)
│   ├── hv_forward.py         # HVf.exe wrapper
│   ├── hv_postprocess.py     # Post-processing & visualization
│   ├── batch_workflow.py     # Complete workflow orchestration
│   ├── complete_batch_workflow.py
│   ├── research_workflow.py  # Research-oriented workflow
│   ├── report_generator.py   # Report generation
│   ├── advanced_analysis.py  # Advanced analysis features
│   ├── academic_statistics.py
│   └── study_statistics.py
├── gui/                  # PySide6 + qfluentwidgets GUI
│   ├── __init__.py
│   ├── __main__.py
│   ├── app.py
│   ├── main_window.py        # MSFluentWindow-based main window
│   ├── pages/                # GUI pages
│   │   ├── workflow_page.py      # Complete workflow
│   │   ├── strip_page.py         # Layer stripping
│   │   ├── forward_page.py       # HV forward modeling
│   │   ├── postprocess_page.py   # Post-processing
│   │   ├── report_page.py        # Report generation
│   │   ├── batch_page.py         # Batch processing
│   │   ├── parallel_batch_page.py # Parallel batch (5000)
│   │   ├── analysis_page.py      # Advanced analysis
│   │   ├── research_page.py      # Research workflow
│   │   └── settings_page.py      # Settings
│   └── widgets/
│       └── plot_widget.py
├── utils/                # Utilities
│   ├── config.py
│   └── validation.py
└── visualization/        # Plotting modules
    ├── plotting.py
    ├── special_plots.py
    ├── statistics_plots.py
    └── study_figures.py
```

---

## Core Components

### 1. Layer Stripping (`core/stripper.py`)

#### Purpose
Progressive "peeling" of velocity model layers - removes deepest finite layer iteratively, promoting removed layer's properties to new half-space.

#### Key Functions
- `write_peel_sequence(model_path, output_base)`: Creates strip folder with peeled models
- `generate_peel_sequence(rows)`: Generates sequence of model row-sets
- `_read_hvf_model(filepath)`: Reads HVf-format model file

#### Model Format (HVf)
```
N               # Number of layers
thk1 vp1 vs1 rho1   # Layer 1
thk2 vp2 vs2 rho2   # Layer 2
...
0 vp_hs vs_hs rho_hs  # Half-space (thickness=0)
```

#### Output Structure
```
strip/
  Step0_{k}-layer/model_Step0_{k}-layer.txt    # Original (k finite layers)
  Step1_{k-1}-layer/model_Step1_{k-1}-layer.txt
  ...
  Step{n}_2-layer/model_Step{n}_2-layer.txt   # Terminal (2 layers)
```

### 2. HV Forward Modeling (`core/hv_forward.py`)

#### Purpose
Wrapper for HVf.exe - computes theoretical H/V spectral ratio curves from velocity models.

#### Key Functions
- `compute_hv_curve(model_path, config)`: Runs HVf.exe and returns (frequencies, amplitudes)

#### Default Configuration
```python
DEFAULT_CONFIG = {
    "exe_path": auto-detected,
    "fmin": 0.2,
    "fmax": 20.0,
    "nf": 71,
    "nmr": 10,
    "nml": 10,
    "nks": 10,
}
```

#### Platform Support
- Linux: `bin/exe_Linux/HVf` or `HVf_Serial`
- Windows: `bin/exe_Win/HVf.exe`

### 3. Batch Workflow (`core/batch_workflow.py`)

#### Purpose
Orchestrates complete progressive layer stripping workflow:
1. Layer stripping → Creates peeled models
2. HV forward → Computes curves for each model
3. Post-processing → Generates plots and summaries

#### Main Function
```python
run_complete_workflow(initial_model_path, output_base_dir, workflow_config=None)
```

#### Workflow Configuration
```python
DEFAULT_WORKFLOW_CONFIG = {
    "stripper": {"output_folder_name": "strip"},
    "hv_forward": {
        "fmin": 0.2, "fmax": 20.0, "nf": 71,
        "adaptive": {
            "enable": True,
            "max_passes": 2,
            "edge_margin_frac": 0.05,
            "fmax_expand_factor": 2.0,
            "fmin_shrink_factor": 0.5,
        }
    },
    "hv_postprocess": {
        "peak_detection": {
            "method": "find_peaks",
            "select": "leftmost",
            "prominence": 0.2,
        },
        "hv_plot": {
            "x_axis_scale": "log",
            "y_axis_scale": "log",
            "smoothing": {"enable": True, "window_length": 9}
        },
        "vs_plot": {"show": True, "annotate_f0": True},
        "output": {
            "save_combined": True,
            "hv_filename": "hv_curve.png",
            "vs_filename": "vs_profile.png"
        }
    }
}
```

#### Features
- Adaptive frequency range expansion (avoids edge peaks)
- Progress reporting
- Error handling per step
- Summary statistics

### 4. GUI (`gui/main_window.py`)

#### Technology Stack
- **PySide6** (Qt for Python)
- **qfluentwidgets** (Fluent design widgets)
- **MSFluentWindow** base class

#### Pages
| Page | Icon | Description |
|------|------|-------------|
| Complete Workflow | PLAY | Run full stripping workflow |
| Layer Stripping | CUT | Individual layer stripping |
| HV Forward | CALORIES | Forward modeling only |
| Post-processing | PIE_SINGLE | Generate plots |
| Report Generation | DOCUMENT | Create reports |
| Batch Processing | LAYOUT | Standard batch |
| Advanced Analysis | SEARCH | Analysis tools |
| Research Workflow | LIBRARY | Academic workflow |
| Parallel Batch | SPEED_HIGH | Large-scale (5000) |
| Settings | SETTING | Configuration |

---

## Key Features for Integration

### 1. Layer Stripping Algorithm
- Systematic removal of deepest layers
- Preserves physical properties for new half-space
- Useful for understanding layer contributions to HVSR

### 2. HVf Forward Modeling
- External executable wrapper
- Configurable frequency range
- Adaptive edge-peak handling

### 3. Post-Processing
- Peak detection with multiple methods
- Publication-ready plots
- Vs profile visualization with annotations

### 4. Fluent GUI Implementation
- Already uses qfluentwidgets
- MSFluentWindow navigation pattern
- Page-based architecture

---

## Relevance to HVSR Pro Enhancement

### Features to Integrate
1. **Layer Stripping Analysis**: Add capability to strip layers from inverted Vs profiles
2. **Forward Modeling**: Compare measured HVSR with theoretical curves
3. **Adaptive Frequency Scanning**: Implement edge-peak detection
4. **Research Workflow**: Academic-oriented processing pipeline
5. **Parallel Batch Processing**: Large-scale processing (5000 files)

### GUI Patterns to Adopt
1. MSFluentWindow with page navigation
2. Progress reporting UI patterns
3. Settings page organization
4. Research workflow UI

---

## Dependencies
- PySide6
- qfluentwidgets
- numpy
- scipy (for signal processing)
- matplotlib (for plotting)
- External: HVf.exe (platform-specific)
