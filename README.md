# HVSR Pro — Professional HVSR Analysis Package

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)

A modern, integrated **Horizontal-to-Vertical Spectral Ratio (HVSR)** analysis workflow for seismic site characterization, featuring a full GUI, CLI, and Python API.

**Author:** Mersad Fathizadeh — Ph.D. Candidate, University of Arkansas
(email: mersadf@uark.edu · GitHub: [@mersadfathizadeh1995](https://github.com/mersadfathizadeh1995))

---

## Overview

HVSR Pro provides a complete pipeline for HVSR analysis of ambient vibration (microtremor) recordings. It handles data import from multiple seismic formats, time-domain windowing, multi-algorithm window rejection, spectral ratio computation, and publication-quality visualization — all accessible through an interactive GUI, command-line interface, or Python API.

### Key Features

- **Multi-format data import** — MiniSEED, SAC, GCF, ASCII/TXT, SAF, PEER, MiniShark, and 3-component SRecord formats
- **Advanced windowing** — Configurable window length, overlap, tapering, and STA/LTA-based selection
- **Multi-algorithm rejection** — Automated window rejection via STA/LTA, amplitude threshold, frequency-domain criteria, and ML-based clustering
- **HVSR processing** — Squared-average, geometric-mean, and individual-component ratios with Konno-Ohmachi or Parzen smoothing
- **Azimuthal analysis** — Directional HVSR computation across user-defined azimuths
- **Interactive GUI** — PyQt5-based interface with real-time HVSR updates, click-to-toggle window rejection, and color-coded visualization
- **Session management** — Save/load full analysis sessions (JSON) for reproducibility
- **Batch processing** — Process multiple stations programmatically via the API
- **CLI** — Full command-line interface for scripted workflows
- **Publication figures** — Export camera-ready plots with customizable styling
- **Integrated packages** — Bedrock depth mapping, HV strip progressive analysis, and batch QC

### Screenshots

> *Coming soon — screenshots of the main window and analysis results.*

---

## Installation

### Prerequisites

- **Python 3.8** or newer
- **pip** (included with Python)

### 1. Clone the Repository

```bash
git clone https://github.com/mersadfathizadeh1995/HV_Pro.git
cd HV_Pro/HV_Analyze_Pro
```

### 2. Create a Virtual Environment (recommended)

```bash
# Windows
python -m venv .venv
.venv\Scripts\activate

# Linux / macOS
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

Or install the package in editable mode:

```bash
pip install -e .
```

#### Core Dependencies

| Package | Purpose |
| ------- | ------- |
| NumPy | Array operations and numerical computation |
| SciPy | Signal processing, spectral analysis |
| Matplotlib | Plotting and visualization |
| Pandas | Tabular data handling |
| ObsPy | Seismic data I/O (MiniSEED, SAC, etc.) |
| PyQt5 | GUI framework |
| PyQtWebEngine | Interactive map display |
| Folium | Leaflet-based station maps |
| Plotly | Interactive 3D visualizations |
| pyproj | Coordinate system transformations |
| scikit-learn | ML-based window rejection |
| PyYAML | Settings persistence |

#### Optional (3D Bedrock Mapping)

| Package | Purpose |
| ------- | ------- |
| PyKrige | Kriging interpolation |
| Shapely | Boundary geometry operations |
| PyVista | 3D mesh visualization and export |
| Pillow | Contour image generation |

### 4. Launch the Application

```bash
# Option A — GUI launcher
python launch_gui.py

# Option B — CLI
python -m hvsr_pro.cli --help
```

---

## Usage

### GUI

```bash
python launch_gui.py
```

1. **Load Data** — Click *Load Data File* to import seismic recordings
2. **Configure** — Adjust window length, overlap, smoothing, and rejection settings
3. **Process** — Click *Process HVSR* to compute spectral ratios
4. **Reject** — Toggle individual windows on/off by clicking in the window panel
5. **Analyze** — View mean HVSR, peak frequency, amplitude, and quality metrics
6. **Export** — Save results, plots, and session files

### CLI

```bash
# Process a single file
python -m hvsr_pro.cli process data.txt --output results/

# Batch process a directory
python -m hvsr_pro.cli batch input_dir/ --output results/

# Show help
python -m hvsr_pro.cli --help
```

### Python API

```python
from hvsr_pro import HVSRDataHandler, HVSRProcessor, HVSRAnalysis

# Quick analysis
analysis = HVSRAnalysis()
results = analysis.run("data.txt", output_dir="results/")
print(f"Peak frequency: {results.peak_frequency:.2f} Hz")

# Step-by-step
handler = HVSRDataHandler()
data = handler.load_data("data.txt")

processor = HVSRProcessor()
results = processor.process(data)
```

#### Batch Processing

```python
from hvsr_pro import batch_process

results = batch_process(
    input_paths=["station1.mseed", "station2.mseed"],
    output_dir="batch_results/",
)
```

---

## Project Structure

```
HV_Pro/
└── HV_Analyze_Pro/
    ├── launch_gui.py           # GUI launcher script
    ├── install.bat             # Windows dependency installer
    ├── setup.py                # Package setup script
    ├── requirements.txt        # Pinned dependencies
    │
    └── hvsr_pro/               # Main package
        ├── __init__.py         # Package API exports
        ├── core/               # Data handling & structures
        │   ├── data_handler.py # Unified data import manager
        │   ├── data_structures.py  # Core data classes
        │   ├── data_cache.py   # Caching layer
        │   └── metadata.py     # Metadata management
        │
        ├── processing/         # HVSR computation engine
        │   ├── hvsr/           # Spectral ratio algorithms
        │   ├── windows/        # Window management
        │   ├── rejection/      # Multi-algorithm rejection
        │   ├── smoothing/      # Konno-Ohmachi, Parzen, etc.
        │   └── azimuthal/      # Directional HVSR
        │
        ├── visualization/      # Plotting tools
        │   ├── plotter.py      # Main HVSR plotter
        │   ├── hvsr_plots.py   # HVSR-specific plots
        │   ├── waveform_plot.py    # Time-series display
        │   ├── window_plots.py     # Window visualization
        │   └── comparison_plot.py  # Multi-station comparison
        │
        ├── gui/                # PyQt5 GUI
        │   ├── main_window.py  # Main application window
        │   ├── tabs/           # Analysis tab widgets
        │   ├── panels/         # Side panels
        │   ├── docks/          # Dockable widgets
        │   ├── dialogs/        # Dialog windows
        │   ├── canvas/         # Matplotlib canvas widgets
        │   ├── widgets/        # Reusable UI components
        │   ├── workers/        # Background processing threads
        │   └── utils/          # GUI utilities
        │
        ├── loaders/            # Format-specific data readers
        │   ├── miniseed_loader.py  # MiniSEED / ObsPy
        │   ├── sac_loader.py       # SAC format
        │   ├── gcf_loader.py       # GCF format
        │   ├── txt_loader.py       # ASCII / TXT
        │   ├── saf_loader.py       # SAF format
        │   ├── peer_loader.py      # PEER ground motion
        │   └── minishark_loader.py # MiniShark recorder
        │
        ├── config/             # Settings & validation
        │   ├── settings.py     # Processing parameters
        │   ├── schemas.py      # Validation schemas
        │   ├── session.py      # Session save/load
        │   └── plot_properties.py  # Plot styling config
        │
        ├── cli/                # Command-line interface
        │   └── main.py         # CLI entry point
        │
        ├── api/                # Programmatic API
        │   ├── analysis.py     # HVSRAnalysis class
        │   └── batch.py        # Batch processing
        │
        ├── packages/           # Integrated sub-packages
        │   ├── bedrock_mapping/    # Bedrock depth estimation
        │   ├── batch_processing/   # Batch QC workflows
        │   └── hvstrip-progressive/  # HV strip progressive (submodule)
        │
        ├── utils/              # Shared utilities
        └── tests/              # Unit and integration tests
```

---

## Architecture

HVSR Pro follows a **layered architecture**:

- **Core** — `core/` provides data structures and a unified data handler
- **Processing** — `processing/` implements windowing, rejection, smoothing, and HVSR computation
- **Visualization** — `visualization/` handles all plotting via Matplotlib
- **Loaders** — `loaders/` provides format-specific readers with a common base class
- **Config** — `config/` manages settings, validation, and session persistence
- **GUI** — `gui/` is a PyQt5 application with tabs, docks, and background workers
- **CLI / API** — `cli/` and `api/` offer non-GUI access to the full pipeline

---

## Supported Seismic Formats

| Format | Extension | Description |
| ------ | --------- | ----------- |
| MiniSEED | `.mseed`, `.miniseed` | Standard seismological format (via ObsPy) |
| SAC | `.sac` | Seismic Analysis Code format |
| GCF | `.gcf` | Guralp Compressed Format |
| ASCII/TXT | `.txt`, `.dat` | Column-based time series |
| SAF | `.saf` | Seismic Analysis Format |
| PEER | `.at2`, `.peer` | PEER ground motion database |
| MiniShark | various | MiniShark portable recorder |

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Commit your changes (`git commit -m "Add my feature"`)
4. Push to the branch (`git push origin feature/my-feature`)
5. Open a Pull Request

---

## Citation

If you use HVSR Pro in your research, please cite:

> Rahimi, M., Wood, C., Fathizadeh, M., & Rahimi, S. (2025). A Multi-method Geophysical Approach for Complex Shallow Landslide Characterization. *Annals of Geophysics*, 68(3), NS336. https://doi.org/10.4401/ag-9203

---

## License

Copyright (C) 2025 Mersad Fathizadeh

This program is free software: you can redistribute it and/or modify it under the terms of the **GNU General Public License v3.0** as published by the Free Software Foundation.

See the [LICENSE](LICENSE) file for details.
