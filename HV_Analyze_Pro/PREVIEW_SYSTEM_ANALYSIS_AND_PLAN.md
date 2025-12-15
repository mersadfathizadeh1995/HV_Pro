# Preview System - Complete Analysis & Implementation Plan

**Date:** December 15, 2025
**Purpose:** Comprehensive analysis of current preview system and detailed implementation plan for tree view and data reduction features

---

## 1. CURRENT IMPLEMENTATION ANALYSIS

### 1.1 Current Architecture

```
Main Window
    └── Data Load Tab (data_load_tab.py)
        ├── Loaded Data List (loaded_data_list.py) - LEFT SIDE (30%)
        │   └── QListWidget with LoadedDataListItem
        │       - Stores: file_path -> metadata dict
        │       - Displays: single flat list of files
        │       - Selection: ExtendedSelection mode
        │
        └── Preview Canvas (preview_canvas.py) - RIGHT SIDE (70%)
            ├── Components: E, N, Z, Spectrogram, Time Series (All)
            ├── Time Range Filter: DateTime pickers with apply button
            └── Matplotlib figure with toolbar
```

### 1.2 Current Data Flow

```
1. User clicks "Load Data File"
   ↓
2. DataInputDialog opens (file selection)
   ↓
3. main_window.py::load_data_file() loads data
   ↓
4. Creates SeismicData object
   ↓
5. data_load_tab.add_loaded_file()
   ├── Stores in data_cache: {file_path: {'data': SeismicData, 'time_range': dict}}
   └── Adds to LoadedDataList: file_path + metadata
   ↓
6. User clicks file in LoadedDataList
   ↓
7. on_file_selected_from_list() emits file_selected signal
   ↓
8. preview_canvas.set_data(data, time_range)
   ↓
9. Shows selected component view
```

### 1.3 Problems Identified

#### Problem #1: No Hierarchical Organization
**Current State:**
- Flat list: `[file1.mseed, file2.mseed, file3.mseed, ...]`
- When user loads 16 files, they see 16 separate items
- No way to group files or view them as a collection

**User Requirements:**
- Tree structure with parent-child hierarchy
- Parent node = group of loaded files (collapsible)
- Child nodes = individual files
- Clicking parent should preview ALL files with combined time range
- Clicking child should preview single file

#### Problem #2: No Multi-File Preview Support
**Current State:**
- `preview_canvas.set_data(seismic_data, time_range)` expects SINGLE SeismicData object
- Cannot preview multiple files simultaneously
- Cannot apply time range across multiple files

**User Requirements:**
- Click parent node → preview data from all child files combined
- Apply time range filter across all files
- Show aggregated time series from multiple files

#### Problem #3: No Data Reduction Capability
**Current State:**
- No way to export time-reduced data
- No .mat file export functionality
- Cannot create "cut" files based on time windows

**User Requirements:**
- Select output directory for reduced data
- Apply time window selection to loaded files
- Export reduced data as .mat files (MATLAB compatible)
- Format similar to HVSR_old package:
  ```python
  # .mat structure (based on miniseed_array_reduction.py):
  {
      'E': array,  # East component
      'N': array,  # North component
      'Z': array,  # Vertical component
      'Fs': sampling_rate,
      't': time_vector,
      'starttime_matlab': matlab_datenum,
      'metadata': {...}
  }
  ```

#### Problem #4: Component Switching Issues
**Status:** ✅ FIXED
- Figure now clears completely when switching from multi-subplot to single views
- Proper subplot recreation

#### Problem #5: Time Window Not Applied
**Status:** ✅ FIXED
- Time slicing now works in all preview modes
- DateTime pickers properly connected
- Time range properly calculated

#### Problem #6: Spectrogram Display
**Status:** ✅ FIXED
- Proper NFFT calculation
- Time slicing support
- Better frequency range (0-50 Hz)
- Error handling

---

## 2. PROPOSED SOLUTION ARCHITECTURE

### 2.1 Tree View Structure

```
📁 Session 2025-12-15_14-30 (16 files) ← PARENT NODE (clickable)
├── 📊 station01_001.mseed
├── 📊 station01_002.mseed
├── 📊 station01_003.mseed
├── 📊 station01_004.mseed
...
└── 📊 station01_016.mseed

Features:
- Parent node shows: total file count, total duration, time span
- Clicking parent: previews ALL files with time range applied
- Clicking child: previews individual file
- Collapsible/expandable
- Multiple parent groups supported
```

### 2.2 New Data Model

```python
# Old (current):
data_cache = {
    'file1.mseed': {'data': SeismicData, 'time_range': dict},
    'file2.mseed': {'data': SeismicData, 'time_range': dict},
}

# New (proposed):
data_groups = {
    'group_id_1': {
        'name': 'Session 2025-12-15_14-30',
        'files': {
            'file1.mseed': {'data': SeismicData, 'time_range': dict},
            'file2.mseed': {'data': SeismicData, 'time_range': dict},
            ...
        },
        'metadata': {
            'total_duration': 3600.0,
            'time_span': ('2025-12-15 14:30:00', '2025-12-15 15:30:00'),
            'file_count': 16,
            'common_sampling_rate': 100.0
        }
    },
    'group_id_2': {...}
}
```

### 2.3 Multi-File Preview Strategy

**Option A: Concatenate Data (Simpler)**
```python
def preview_group(group_files):
    # Concatenate E, N, Z components
    all_e = np.concatenate([f['data'].E.data for f in group_files])
    all_n = np.concatenate([f['data'].N.data for f in group_files])
    all_z = np.concatenate([f['data'].Z.data for f in group_files])

    # Create combined SeismicData object
    combined = SeismicData(e=all_e, n=all_n, z=all_z, ...)

    # Preview as normal
    preview_canvas.set_data(combined, time_range)
```

**Option B: Overlay Multiple Traces (More Complex)**
```python
def preview_group(group_files):
    # Plot each file's trace on same axes
    for file_data in group_files:
        ax.plot(file_data.time, file_data.E.data, alpha=0.3)

    # Show aggregate/mean
    mean_trace = calculate_mean_across_files(group_files)
    ax.plot(mean_time, mean_trace, linewidth=2, label='Mean')
```

**Recommended: Option A** (simpler, matches existing preview_canvas interface)

### 2.4 Data Reduction Workflow

```
User Workflow:
1. Load multiple files (they appear as group in tree)
2. Select time range using DateTime pickers
3. Click "Export Reduced Data" button
4. Dialog opens:
   - Output directory selector
   - Format selector: [.mat | .mseed | .csv]
   - Options:
     ☑ Apply time window
     ☑ Preserve original sampling rate
     ☑ Export each file separately
     ☑ Export as combined file
5. Click "Export"
6. Progress bar shows export status
7. Success message with output location
```

### 2.5 .mat File Export Format

```python
# Based on HVSR_old/miniseed_array_reduction.py

def export_to_mat(seismic_data, output_path, time_window=None):
    """
    Export seismic data to MATLAB .mat file.

    Args:
        seismic_data: SeismicData object
        output_path: Path to output .mat file
        time_window: Optional dict {'start': datetime, 'end': datetime}
    """
    from scipy.io import savemat
    from datetime import datetime

    # Apply time window if specified
    if time_window:
        data = apply_time_window(seismic_data, time_window)
    else:
        data = seismic_data

    # Convert to MATLAB datenum
    start_dt = data.start_time
    matlab_datenum = start_dt.toordinal() + 366 + (
        start_dt - datetime(start_dt.year, start_dt.month, start_dt.day)
    ).total_seconds() / 86400.0

    # Prepare data structure
    mat_data = {
        'E': data.E.data,
        'N': data.N.data,
        'Z': data.Z.data,
        'Fs': data.E.sampling_rate,
        't': data.E.time_vector,
        'starttime_matlab': matlab_datenum,
        'starttime_iso': start_dt.isoformat(),
        'duration': data.duration,
        'nsamples': len(data.E.data),
        'metadata': {
            'original_file': data.metadata.get('file_path', ''),
            'export_time': datetime.now().isoformat(),
            'time_window_applied': time_window is not None
        }
    }

    # Save
    savemat(output_path, mat_data, do_compression=True)
```

---

## 3. IMPLEMENTATION PLAN

### Phase 1: Convert to Tree View (High Priority)

#### Step 1.1: Create TreeView Widget
**File:** `loaded_data_tree.py` (NEW)
```python
from PyQt5.QtWidgets import QTreeWidget, QTreeWidgetItem

class LoadedDataTree(QTreeWidget):
    """Tree widget for hierarchical file organization"""

    # Signals
    file_selected = pyqtSignal(str)  # Single file
    group_selected = pyqtSignal(list)  # List of files in group

    # Structure:
    # - Root items = groups
    # - Child items = individual files
```

#### Step 1.2: Modify Data Load Tab
**File:** `data_load_tab.py`
- Replace `LoadedDataList` with `LoadedDataTree`
- Update `data_cache` to `data_groups` structure
- Handle group selection vs file selection

#### Step 1.3: Update Preview Canvas for Multi-File
**File:** `preview_canvas.py`
- Add `set_data_group(files_list, time_range)` method
- Implement data concatenation for multiple files
- Update all preview modes to handle concatenated data

#### Step 1.4: Update Main Window Integration
**File:** `main_window.py`
- Handle group selection signals
- Update load_data_file() to create groups
- Support both single-file and multi-file workflows

### Phase 2: Data Reduction & Export (Medium Priority)

#### Step 2.1: Create Export Dialog
**File:** `data_export_dialog.py` (NEW)
```python
class DataExportDialog(QDialog):
    """Dialog for exporting reduced/filtered data"""

    # Options:
    # - Output directory
    # - Format: .mat, .mseed, .csv
    # - Apply time window checkbox
    # - Export mode: individual files | combined file
```

#### Step 2.2: Implement .mat Export
**File:** `data_exporters.py` (NEW)
```python
def export_to_mat(data, output_path, time_window=None)
def export_to_mseed(data, output_path, time_window=None)
def export_to_csv(data, output_path, time_window=None)
```

#### Step 2.3: Add Export Button to Data Load Tab
**File:** `data_load_tab.py`
- Add "Export Reduced Data" button
- Connect to export dialog
- Show progress during export

#### Step 2.4: Integration with Tree View
- Export selected files or entire group
- Apply time range from preview canvas
- Generate appropriate output filenames

### Phase 3: Testing & Polish (Low Priority)

#### Step 3.1: Unit Tests
- Test tree view selection
- Test multi-file concatenation
- Test .mat export format
- Test time window application

#### Step 3.2: User Experience Enhancements
- Progress indicators for long operations
- Error handling and validation
- Helpful tooltips
- Keyboard shortcuts

---

## 4. DETAILED IMPLEMENTATION STEPS

### Step-by-Step: Tree View Implementation

**STEP 1:** Create `loaded_data_tree.py`
```python
class LoadedDataTree(QTreeWidget):
    def __init__(self, parent=None):
        # Initialize with 2 columns: Name | Info
        self.setColumnCount(2)
        self.setHeaderLabels(['File/Group', 'Details'])

    def add_file_group(self, group_name, files_dict):
        """Add a group of files as tree"""
        parent_item = QTreeWidgetItem([group_name, f"{len(files_dict)} files"])
        self.addTopLevelItem(parent_item)

        for file_path, data in files_dict.items():
            child_item = QTreeWidgetItem([
                Path(file_path).name,
                f"{data['metadata']['duration']:.1f}s"
            ])
            child_item.setData(0, Qt.UserRole, file_path)
            parent_item.addChild(child_item)

    def on_item_clicked(self, item, column):
        if item.parent() is None:
            # Parent clicked = group
            files = self.get_group_files(item)
            self.group_selected.emit(files)
        else:
            # Child clicked = single file
            file_path = item.data(0, Qt.UserRole)
            self.file_selected.emit(file_path)
```

**STEP 2:** Modify `data_load_tab.py`
```python
# OLD:
self.loaded_list = LoadedDataList(self)

# NEW:
self.loaded_tree = LoadedDataTree(self)
self.loaded_tree.file_selected.connect(self.on_file_selected)
self.loaded_tree.group_selected.connect(self.on_group_selected)

def on_group_selected(self, file_paths):
    """Handle group selection - preview all files"""
    combined_data = self.combine_files(file_paths)
    self.preview_canvas.set_data(combined_data, time_range=None)
```

**STEP 3:** Update `preview_canvas.py`
```python
def set_data_from_files(self, file_data_list, time_range=None):
    """
    Set data from multiple files (concatenated).

    Args:
        file_data_list: List of SeismicData objects
        time_range: Optional time range to apply to combined data
    """
    # Concatenate components
    combined_data = self.concatenate_seismic_data(file_data_list)

    # Use existing set_data method
    self.set_data(combined_data, time_range)

def concatenate_seismic_data(self, data_list):
    """Concatenate multiple SeismicData objects"""
    # Implementation...
```

**STEP 4:** Add export functionality
```python
# In data_load_tab.py, add button:
self.export_btn = QPushButton("Export Reduced Data")
self.export_btn.clicked.connect(self.on_export_data)

def on_export_data(self):
    """Open export dialog"""
    dialog = DataExportDialog(
        files=self.get_selected_files_or_group(),
        time_range=self.preview_canvas.get_current_time_range(),
        parent=self
    )
    dialog.exec_()
```

---

## 5. RISK ANALYSIS

### Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Memory issues with large concatenated data | High | Medium | Implement lazy loading, show warnings for large datasets |
| Incorrect time alignment across files | High | Medium | Validate sampling rates match, add time gap detection |
| .mat format incompatibility | Medium | Low | Test with MATLAB, follow scipy.io.savemat conventions |
| Tree view performance with many files | Medium | Low | Use virtual scrolling, pagination |
| User confusion with new UI | Low | Medium | Add helpful tooltips, documentation |

---

## 6. SUCCESS CRITERIA

✅ User can load multiple files and see them organized in tree view
✅ Clicking parent node previews all files combined
✅ Clicking child node previews individual file
✅ Time range filter works on both single and multi-file previews
✅ Export dialog allows selection of output directory
✅ .mat export creates MATLAB-compatible files
✅ Exported files can be loaded back into application
✅ All existing functionality remains working

---

## 7. TIMELINE ESTIMATE

- **Phase 1 (Tree View):** 4-6 hours
- **Phase 2 (Export):** 3-4 hours
- **Phase 3 (Testing):** 2-3 hours
- **Total:** 9-13 hours of focused development

---

## 8. DEPENDENCIES

**Python Packages:**
- `scipy` (for .mat file export) - REQUIRED
- `numpy` (already present)
- `PyQt5` (already present)
- `obspy` (if using miniseed export)

**External:**
- MATLAB (for testing .mat files) - OPTIONAL

---

## CONCLUSION

This is a significant but manageable enhancement. The tree view provides much better organization for multi-file workflows, and the data reduction feature adds professional-grade export capabilities. Implementation should proceed in phases to minimize risk and allow for iterative testing.

**Recommended Approach:** Start with Phase 1 (Tree View) as it provides immediate value and is a prerequisite for Phase 2.
