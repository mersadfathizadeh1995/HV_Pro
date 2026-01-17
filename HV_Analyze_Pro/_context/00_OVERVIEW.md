# HVSR Pro Package Context Overview

## Package Location
`D:\Research\Narm_Afzar\Git_hub\HV_Pro\HV_Analyze_Pro\hvsr_pro`

## Version
- Current: `0.2.0`
- Author: OSCAR HVSR Development Team

## Purpose
HVSR Pro is a comprehensive open-source, cross-platform graphical software for Horizontal-to-Vertical Spectral Ratio (HVSR) analysis of ambient seismic noise. Built with Python and PyQt5.

## Package Structure
```
hvsr_pro/
├── __init__.py              # Main package exports
├── api/                     # High-level API (HVSRAnalysis, batch_process)
├── cli/                     # Command-line interface
├── config/                  # Settings, schemas, session management
├── core/                    # Data structures (SeismicData, ComponentData)
├── gui/                     # PyQt5 GUI components
│   ├── components/          # Reusable UI components
│   ├── dialogs/             # Dialog windows
│   ├── mixins/              # Mixin classes for main window
│   ├── panels/              # QC panel, settings panel
│   └── workers/             # Background processing threads
├── loaders/                 # Data loaders (txt, miniseed)
├── processing/              # Core processing algorithms
│   ├── azimuthal/           # Azimuthal HVSR analysis
│   ├── hvsr/                # HVSR processor, spectral functions
│   ├── rejection/           # QC algorithms
│   │   └── algorithms/      # Individual rejection algorithms
│   └── windows/             # Window management
├── utils/                   # Utility functions
└── visualization/           # Plotting functions
```

## Key Exports (from `__init__.py`)
- `HVSRDataHandler` - Data loading
- `WindowManager`, `Window`, `WindowState`, `WindowCollection` - Window management
- `RejectionEngine` - Quality control
- `HVSRProcessor`, `HVSRResult` - HVSR computation
- `HVSRPlotter` - Visualization
- `HVSRAnalysis`, `batch_process` - High-level API

## Technology Stack
| Component | Technology |
|-----------|------------|
| Language | Python 3.8+ |
| GUI | PyQt5 |
| Numerics | NumPy, SciPy |
| Visualization | Matplotlib |
| Seismic I/O | ObsPy (optional) |

## Context Files Index
1. `00_OVERVIEW.md` - This file
2. `01_DATA_STRUCTURES.md` - Core data structures
3. `02_LOADERS.md` - File loading capabilities
4. `03_PROCESSING.md` - HVSR processing pipeline
5. `04_REJECTION.md` - Quality control algorithms
6. `05_GUI.md` - GUI components
7. `06_API.md` - Programmatic API
8. `07_GAPS_AND_IMPROVEMENTS.md` - Current gaps and planned improvements
