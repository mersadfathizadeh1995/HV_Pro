# HVSR_old Package Analysis

## Overview
**Location:** `D:\Research\Narm_Afzar\Git_hub\HV_Pro\Codes_To_use\HVSR_old`  
**Purpose:** Legacy HVSR workflow application with tab-based PyQt5 GUI. Provides multi-station processing, circular array handling, and MiniSEED export functionality.

---

## Package Architecture

```
HVSR_old/
├── main.py                    # Application launcher (QTabWidget)
├── run.py                     # Alternative runner
├── NewTab0_Automatic.py       # Tab 0: Automatic workflow (main)
├── NewTab1_Windows.py         # Tab 1: Window definition
├── NewTab2_FsCheck.py         # Tab 2: Sampling rate check
├── NewTab3_Reduce.py          # Tab 3: Single station reduction
├── NewTab3_CircularArray.py   # Tab 3b: Circular array reduction
├── NewTab4_WriteMiniseed.py   # Tab 4: MiniSEED export for Geopsy
├── NewTab4_HVSRPicker.py      # Tab 5: HVSR peak picking
├── hvsr_making_peak.py        # Core HVSR processing
├── array_write_miniseed.py    # Array MiniSEED writing
├── circular_array_reduction.py # Circular array processing
├── miniseed_array_reduction.py # MiniSEED array reduction
├── rdmseed_py.py              # MiniSEED reading utilities
├── palette.py                 # Color palette
└── Colors.mat                 # MATLAB color data
```

---

## Key Components

### 1. Main Application (`main.py`)

```python
def main():
    app = QApplication(sys.argv)
    tabs = QTabWidget()
    tabs.addTab(NewTab0_Automatic(),  "0  Automatic")
    tabs.addTab(NewTab1_Windows(),    "1  Windows")
    tabs.addTab(NewTab2_FsCheck(),    "2  Check Fs")
    tabs.addTab(NewTab3_Reduce(),     "3  Reduce MAT (Single)")
    tabs.addTab(NewTab3_CircularArray(), "3b Circular Array")
    tabs.addTab(NewTab4_WriteMiniseed(), "4  Write MiniSEED")
    tabs.addTab(NewTab4_HVSRPicker(),    "5  HVSR Peaks")
    tabs.setWindowTitle("HVSR Workflow")
    tabs.show()
```

### 2. Automatic Workflow (`NewTab0_Automatic.py`)

Main processing tab with:
- **Station-based MiniSEED file selection** (table view)
- **CSV import/export** for time windows
- **Output directory selection**
- **Time window with timezone options** (CST, CDT, GMT+0)
- **HVSR settings popup dialog**
- **Parallel HVSR curve generation**
- **Apply same time window to all stations**

#### HVSRSettingsDialog
```python
class HVSRSettingsDialog(QDialog):
    # HVSR Parameters
    - freq_min: 0.2 Hz
    - freq_max: 30.0 Hz
    - smoothing_type: Konno-Ohmachi, Parzen, None
    - smoothing_bw: 40
    - window_length: 120s
    - averaging: geo, quad, energy, N, E
    
    # Peak Selection
    - num_peaks: 1-10
    - auto_peaks: unlimited clicks
    - peak_font: 6-30pt
    
    # Processing Options
    - start_skip: minutes
    - process_len: minutes
    - save_png/pdf
    - max_parallel: up to CPU count
```

### 3. Window Definition (`NewTab1_Windows.py`)
- Manual time window definition
- CSV-based window management
- Multi-station support

### 4. Sampling Rate Check (`NewTab2_FsCheck.py`)
- Validates sampling rates across files
- Detects mismatched rates
- Quality assurance step

### 5. Single Station Reduction (`NewTab3_Reduce.py`)
- Reduces MiniSEED to MAT format
- Single station processing
- Data compression/export

### 6. Circular Array (`NewTab3_CircularArray.py`)
- Circular array reduction algorithms
- Multi-station array processing
- Specialized for array deployments

### 7. MiniSEED Export (`NewTab4_WriteMiniseed.py`)
- Exports processed data to MiniSEED
- Geopsy-compatible format
- Standardized output

### 8. HVSR Peak Picker (`NewTab4_HVSRPicker.py`)
- Interactive peak selection
- Manual peak identification
- Peak annotation

---

## Key Features

### 1. Multi-Station Table View
- Organized station listing
- Batch selection
- Status tracking

### 2. Time Window Management
- CSV import/export
- Timezone handling (CST, CDT, GMT)
- Apply to all stations option

### 3. Parallel Processing
- ProcessPoolExecutor / ThreadPoolExecutor
- Configurable worker count
- Progress tracking

### 4. Circular Array Support
- Specialized processing for array deployments
- Array geometry handling
- Multi-component coordination

### 5. Geopsy Integration
- MiniSEED export for Geopsy
- Compatible data formats
- Standard workflow support

---

## Relevance to HVSR Pro

### Features to Consider

1. **Tab-Based Organization**: Simple workflow organization
2. **Multi-Station Support**: Batch station handling
3. **CSV Time Windows**: External time window definition
4. **Circular Array**: Specialized array processing
5. **Parallel Processing**: Worker-based parallelism
6. **Settings Dialog**: Popup configuration pattern

### Code Quality Notes

- Legacy PyQt5 code (not Fluent design)
- Functional but not modern UI
- Some MATLAB interop (Colors.mat)
- Basic error handling

### Potential Improvements

1. **Modern UI**: Migrate to qfluentwidgets
2. **Better Architecture**: Separate logic from UI
3. **Enhanced QC**: Add modern rejection algorithms
4. **Unified Processing**: Merge with hvsr_pro pipeline
5. **Documentation**: Add proper docstrings

---

## Dependencies
- PyQt5
- numpy
- scipy (implied)
- obspy (MiniSEED handling)
- concurrent.futures (parallel processing)
