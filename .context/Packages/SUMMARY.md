# HV_Pro Codebase Summary & Integration Plan

## Overview

This document summarizes the analysis of all packages in the HV_Pro workspace and provides recommendations for integration and restructuring.

---

## Package Inventory

| Package | Purpose | GUI | Status |
|---------|---------|-----|--------|
| **hvsr_pro** | Main HVSR processing engine | PyQt5 (basic) | Active development |
| **PyQt-Fluent-Widgets** | Modern UI framework | Fluent Design | Reference library |
| **hvstrip_progressive** | Layer stripping analysis | PySide6 + qfluentwidgets | Complete |
| **hvsrpy-main** | Academic HVSR package | None (CLI) | Reference |
| **HVSR_old** | Legacy workflow app | PyQt5 (tabs) | Legacy |

---

## Feature Matrix

| Feature | hvsr_pro | hvstrip | hvsrpy | HVSR_old |
|---------|----------|---------|--------|----------|
| Data Loading (TXT) | ✅ | ❌ | ❌ | ❌ |
| Data Loading (MiniSEED) | ✅ | ❌ | ✅ | ✅ |
| Window Management | ✅ | ❌ | ✅ | ✅ |
| Quality Metrics | ✅ | ❌ | ❌ | ❌ |
| Cox FDWRA | ✅ | ❌ | ✅ | ❌ |
| STA/LTA Rejection | ✅ | ❌ | ✅ | ❌ |
| ML Rejection | ✅ | ❌ | ✅ (beta) | ❌ |
| Konno-Ohmachi | ✅ | ❌ | ✅ | ✅ |
| Peak Detection | ✅ | ✅ | ✅ | ✅ |
| SESAME Criteria | ✅ | ❌ | ✅ | ❌ |
| Lognormal Stats | ✅ | ❌ | ✅ | ❌ |
| Interactive Plot | ✅ | ❌ | ❌ | ❌ |
| Layer Stripping | ❌ | ✅ | ❌ | ❌ |
| Forward Modeling | ❌ | ✅ | ✅ | ❌ |
| Batch Processing | ✅ | ✅ | ✅ | ✅ |
| Parallel Processing | ✅ | ✅ | ✅ | ✅ |
| Fluent UI | ❌ | ✅ | ❌ | ❌ |
| Circular Array | ❌ | ❌ | ❌ | ✅ |
| Azimuthal Analysis | ❌ | ❌ | ✅ | ❌ |
| Spatial Statistics | ❌ | ❌ | ✅ | ❌ |

---

## Recommended Architecture

### Target: Unified HVSR Pro with Fluent UI

```
hvsr_pro_v3/
├── core/                     # From hvsr_pro (enhanced)
│   ├── data_structures.py
│   ├── data_handler.py
│   ├── data_cache.py
│   └── metadata.py
├── loaders/                  # From hvsr_pro + hvsrpy formats
│   ├── base_loader.py
│   ├── txt_loader.py
│   ├── miniseed_loader.py
│   ├── saf_loader.py         # NEW: from hvsrpy
│   └── geopsy_loader.py      # NEW: from hvsrpy
├── processing/               # From hvsr_pro (enhanced)
│   ├── window_manager.py
│   ├── hvsr_processor.py
│   ├── spectral_processing.py
│   ├── peak_detection.py
│   ├── quality_metrics.py
│   ├── rejection_engine.py
│   ├── rejection_algorithms.py
│   ├── rejection_advanced.py
│   ├── rejection_cox_fdwra.py
│   ├── rejection_ml.py
│   ├── sesame_criteria.py    # NEW: from hvsrpy
│   └── statistics.py         # NEW: lognormal from hvsrpy
├── forward/                  # NEW: from hvstrip_progressive
│   ├── layer_stripping.py
│   ├── hv_forward.py
│   └── hv_postprocess.py
├── analysis/                 # NEW: advanced features
│   ├── azimuthal.py          # from hvsrpy
│   ├── spatial.py            # from hvsrpy
│   └── circular_array.py     # from HVSR_old
├── visualization/            # From hvsr_pro
│   ├── plotter.py
│   ├── hvsr_plots.py
│   └── window_plots.py
├── gui/                      # NEW: Fluent-based
│   ├── app.py
│   ├── main_window.py        # FluentWindow/MSFluentWindow
│   ├── interfaces/           # Page-based navigation
│   │   ├── home_interface.py
│   │   ├── single_file_interface.py
│   │   ├── batch_interface.py
│   │   ├── settings_interface.py
│   │   ├── forward_interface.py
│   │   └── analysis_interface.py
│   ├── widgets/
│   │   ├── interactive_canvas.py
│   │   ├── plot_widget.py
│   │   └── settings_cards.py
│   └── dialogs/
│       ├── data_input_dialog.py
│       ├── qc_settings_dialog.py
│       └── export_dialog.py
├── batch/                    # From hvsr_pro
│   ├── batch_processor.py
│   ├── dataset_manager.py
│   └── results_database.py
├── utils/                    # From hvsr_pro
│   ├── export_utils.py
│   ├── file_utils.py
│   ├── signal_utils.py
│   └── time_utils.py
└── cli/                      # Enhanced CLI
    └── main.py
```

---

## Integration Priorities

### Phase 1: GUI Modernization (High Priority)
1. **Migrate to qfluentwidgets**
   - Replace QMainWindow with FluentWindow/MSFluentWindow
   - Implement page-based navigation (like hvstrip_progressive)
   - Use CardWidget for settings groups
   - Add InfoBar for status messages
   - Implement dark/light theme support

2. **Keep Processing Engine**
   - hvsr_pro's processing is comprehensive
   - Maintain existing rejection algorithms
   - Keep interactive canvas functionality

### Phase 2: Feature Enhancement (Medium Priority)
3. **Add Layer Stripping**
   - Integrate hvstrip_progressive's stripping algorithm
   - Add HVf forward modeling capability
   - Create Forward Modeling interface

4. **Enhance Statistics**
   - Add proper lognormal statistics from hvsrpy
   - Implement SESAME criteria checking
   - Add uncertainty visualization

### Phase 3: Advanced Features (Lower Priority)
5. **Add Azimuthal Analysis**
   - Port HvsrAzimuthal from hvsrpy
   - Multiple azimuth support

6. **Add Spatial Statistics**
   - Port HvsrSpatial from hvsrpy
   - Voronoi tessellation

7. **Circular Array Support**
   - Port from HVSR_old
   - Array geometry handling

---

## GUI Migration Guide

### From PyQt5 to qfluentwidgets

```python
# Before (hvsr_pro)
class HVSRMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

# After (Fluent)
from qfluentwidgets import FluentWindow, NavigationItemPosition, FluentIcon

class HVSRMainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.homeInterface = HomeInterface(self)
        self.addSubInterface(
            self.homeInterface,
            FluentIcon.HOME,
            "Home",
            NavigationItemPosition.TOP
        )
```

### Interface Pattern (from hvstrip_progressive)
```python
class SingleFileInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("singleFileInterface")  # Required!
        # ... build UI with CardWidgets
```

---

## Key Files to Reference

### For GUI Migration
- `hvstrip_progressive/gui/main_window.py` - FluentWindow example
- `hvstrip_progressive/gui/pages/*.py` - Page implementations
- `PyQt-Fluent-Widgets/qfluentwidgets/window/fluent_window.py` - Base classes

### For Processing Enhancement
- `hvsrpy/window_rejection.py` - Cox FDWRA reference
- `hvsrpy/statistics.py` - Lognormal statistics
- `hvsrpy/sesame.py` - SESAME criteria

### For Layer Stripping
- `hvstrip_progressive/core/stripper.py` - Peeling algorithm
- `hvstrip_progressive/core/hv_forward.py` - HVf wrapper
- `hvstrip_progressive/core/batch_workflow.py` - Workflow orchestration

---

## Immediate Action Items

1. **Create new GUI branch** for Fluent migration
2. **Design interface layout** (navigation structure)
3. **Implement base FluentWindow** with navigation
4. **Migrate single-file processing** to first interface
5. **Add settings interface** with CardWidgets
6. **Migrate batch processing** to batch interface
7. **Integrate interactive canvas** into Fluent interface
8. **Add forward modeling** interface (from hvstrip)
9. **Implement SESAME criteria** display
10. **Add export/report** interface

---

## Dependencies to Add

```
# requirements.txt additions
qfluentwidgets>=1.0.0
qframelesswindow
darkdetect
```

---

## Notes

- **hvsr_pro** has the most complete HVSR processing pipeline
- **hvsrpy** is the academic reference for algorithms (Cox FDWRA, SESAME)
- **hvstrip_progressive** demonstrates proper qfluentwidgets usage
- **HVSR_old** has circular array support not found elsewhere
- **PyQt-Fluent-Widgets** is the UI framework to adopt
