# HVSR Pro GUI Restructuring Plan

## Overview
This document outlines the plan to restructure the HVSR Pro GUI to separate data loading from processing, improve usability, and add preview capabilities.

## Current Structure

### Main Window (HVSRMainWindow)
- **Tab Widget (mode_tabs)**:
  - "Single File" tab: Contains both file loading and processing controls
- **Right Dockable Panels**:
  - Layers Dock (WindowLayersDock)
  - Peak Picker Dock (PeakPickerDock)
  - Properties Dock (PropertiesDock)
- **Plot Management**:
  - PlotWindowManager (separate window for plots)

### Current File Loading Flow
1. User clicks "Load Data File" in Single File tab
2. DataInputDialog opens (multi-tab dialog)
3. User selects files (Single/Type1/Type2)
4. Files are loaded and processing begins

## Proposed Changes

### 1. New Tab Structure

#### Tab 1: "Data Load" (NEW)
**Purpose**: Handle all data loading, display loaded files, and provide preview capabilities

**Layout**:
```
+---------------------------------------+
| Data Load Tab                         |
+---------------------------------------+
|  Left Column (30%)  | Preview (70%)   |
|  +--------------+   | +------------+  |
|  | Loaded Files |   | | Preview    |  |
|  | List         |   | | Canvas     |  |
|  |              |   | |            |  |
|  | - File1.txt  |   | | (Dockable) |  |
|  | - File2.mseed|   | |            |  |
|  |              |   | +------------+  |
|  | [Load More]  |   |                 |
|  | [Remove]     |   | Preview Options:|
|  | [Clear All]  |   | ( ) E Signal    |
|  +--------------+   | ( ) N Signal    |
|                     | ( ) Z Signal    |
|                     | ( ) Spectrogram |
|                     | ( ) Timeseries  |
+---------------------------------------+
```

**Components**:
- **Left Column** (toggleable via View menu):
  - `QListWidget` showing loaded files with metadata
  - Each item shows: filename, size, duration, sampling rate
  - Double-click to preview
  - Right-click context menu: Remove, Show Info
  - Buttons: "Load More Files", "Remove Selected", "Clear All"

- **Preview Canvas** (dockable):
  - Matplotlib FigureCanvas showing selected data
  - Can be detached into separate window
  - Radio buttons to switch preview type:
    - E Component Signal
    - N Component Signal
    - Z Component Signal
    - Window Spectrogram
    - Window Timeseries

- **Data Loading Controls**:
  - "Load Data File" button (moved from Processing tab)
  - Recent files dropdown

#### Tab 2: "Processing" (RENAMED from "Single File")
**Purpose**: Configure processing parameters and run HVSR analysis

**Layout**:
```
+---------------------------------------+
| Processing Tab                        |
+---------------------------------------+
|  Processing Settings (scrollable)     |
|  +--------------------------------+   |
|  | Window Length: [30] s          |   |
|  | Overlap: [50] %                |   |
|  | Konno-Ohmachi: [40]            |   |
|  | Frequency Range: [0.2-20] Hz   |   |
|  | QC Mode: [Balanced]            |   |
|  | [ ] Cox FDWRA                  |   |
|  | [⚙ Advanced QC Settings]       |   |
|  |                                |   |
|  | [Process HVSR]                 |   |
|  +--------------------------------+   |
|                                       |
|  Window Management                    |
|  Actions (Export, etc.)               |
|  Info Display                         |
+---------------------------------------+
```

**Components**:
- All current processing controls (window length, overlap, smoothing, etc.)
- QC settings
- Process button
- Window management controls
- Export and actions
- **NO file loading controls** (moved to Data Load tab)

### 2. Dock Widget Management

#### Current Docks
All three docks are always visible:
- Layers Dock
- Peak Picker Dock
- Properties Dock

#### New Behavior
Docks should only be visible when in **Processing Tab**:
- When user switches to "Data Load" tab → hide all docks
- When user switches to "Processing" tab → show docks (if they were visible before)
- Use `QTabWidget.currentChanged` signal to trigger visibility changes

### 3. View Menu Restructuring

#### Current View Menu
```
View
├── Plot Window
├── ───────────
├── Layers Dock
├── Peaks Dock
└── Properties Dock
```

#### New View Menu
```
View
├── Processing Tab
│   ├── Layers Dock        [Ctrl+Shift+L]
│   ├── Peak Picker Dock   [Ctrl+Shift+P]
│   └── Properties Dock    [Ctrl+Shift+R]
├── ───────────
├── Data Load Tab
│   └── Preview Canvas     [Ctrl+Shift+V]
├── ───────────
├── Loaded Data Column     [Ctrl+Shift+D]
└── ───────────
└── Plot Window            [Ctrl+P]
```

**Implementation**:
- Use nested QMenu for organization
- Add keyboard shortcuts
- Connect to visibility toggles
- Disable "Processing Tab" items when in Data Load tab
- Disable "Data Load Tab" items when in Processing tab

### 4. Menu Bar Fixes

#### Issues to Fix
- Duplicate menu creation (two methods creating File/Edit/View menus)
- Menu items not responding to clicks
- Missing keyboard shortcuts

#### Solution
1. **Remove duplicate `setup_menu_bar()` method** (line 566-577)
2. **Keep only `create_menu_bar()` method** (line 348-432)
3. **Add missing menu items**:
   - File → Save Session
   - File → Load Session
   - Edit → Advanced QC Settings
4. **Fix keyboard shortcuts** that conflict or don't work
5. **Test all menu items** to ensure they trigger correct actions

### 5. Preview Canvas Implementation

#### New Widget: `PreviewCanvas`
**File**: `hvsr_pro/gui/preview_canvas.py`

**Features**:
- Extends matplotlib FigureCanvas
- Supports multiple view modes:
  - Component signals (E, N, Z)
  - Spectrograms
  - Time series
- Dockable (can be detached to separate window)
- Connected to loaded data list selection

**Methods**:
```python
class PreviewCanvas:
    def __init__(self, parent=None)
    def set_data(self, seismic_data: SeismicData)
    def show_component_signal(self, component: str)  # 'E', 'N', 'Z'
    def show_spectrogram(self, component: str)
    def show_timeseries(self)
    def clear_preview()
```

#### New Widget: `LoadedDataList`
**File**: `hvsr_pro/gui/loaded_data_list.py`

**Features**:
- Custom QListWidget subclass
- Each item shows file info:
  - Icon (📄 for txt, 📊 for mseed)
  - Filename
  - Duration, sampling rate
  - Status (loaded, processing, error)
- Signals:
  - `file_selected(str)`: Emitted when user clicks file
  - `file_removed(str)`: Emitted when user removes file

**Methods**:
```python
class LoadedDataList:
    def __init__(self, parent=None)
    def add_file(self, file_path: str, metadata: dict)
    def remove_file(self, file_path: str)
    def clear_all()
    def get_selected_file() -> str
```

### 6. Data Flow Changes

#### Old Flow
```
1. User opens Single File tab
2. Clicks "Load Data File"
3. DataInputDialog opens
4. Selects files
5. Processing begins immediately
```

#### New Flow
```
1. User opens Data Load tab
2. Clicks "Load Data File"
3. DataInputDialog opens
4. Selects files
5. Files added to Loaded Data List
6. User can preview in Preview Canvas
7. User switches to Processing tab
8. Clicks "Process HVSR" (processes currently loaded data)
```

### 7. Implementation Steps

#### Step 1: Create New Widget Files
- [ ] Create `hvsr_pro/gui/preview_canvas.py`
- [ ] Create `hvsr_pro/gui/loaded_data_list.py`
- [ ] Create `hvsr_pro/gui/data_load_tab.py` (container widget)

#### Step 2: Modify Main Window
- [ ] Add "Data Load" tab to mode_tabs
- [ ] Move file loading UI from create_control_panel() to data_load_tab
- [ ] Rename "Single File" tab to "Processing"
- [ ] Implement tab change handler for dock visibility

#### Step 3: Update Menu Bar
- [ ] Remove duplicate menu creation
- [ ] Restructure View menu with nested items
- [ ] Add keyboard shortcuts
- [ ] Connect all menu actions properly

#### Step 4: Implement Loaded Data Management
- [ ] Store loaded files in a data structure
- [ ] Update LoadedDataList when files are loaded
- [ ] Connect preview canvas to data list selection

#### Step 5: Testing
- [ ] Test tab switching behavior
- [ ] Test dock visibility toggling
- [ ] Test all menu items and shortcuts
- [ ] Test file loading and preview
- [ ] Test processing with loaded data

## File Modifications Required

### 1. `hvsr_pro/gui/main_window.py`
**Changes**:
- Line 348-432: Fix `create_menu_bar()` to include new View menu structure
- Line 484-564: Modify `init_ui()` to create two tabs properly
- Line 579-688: Split `create_control_panel()` - move file loading to data_load_tab
- Line 1046-1093: Update `on_files_selected()` to add to loaded data list
- Add new method: `on_tab_changed(index)` for dock visibility management
- Remove lines 566-577: Duplicate `setup_menu_bar()` method

### 2. New Files to Create
- `hvsr_pro/gui/preview_canvas.py`
- `hvsr_pro/gui/loaded_data_list.py`
- `hvsr_pro/gui/data_load_tab.py`

### 3. `hvsr_pro/gui/__init__.py`
**Changes**:
- Add exports for new widgets

## UI/UX Improvements

### Icons and Visual Feedback
- Add file type icons (📄 txt, 📊 mseed)
- Add status indicators (✓ loaded, ⚙ processing, ❌ error)
- Use color coding in loaded data list

### Keyboard Shortcuts
```
Ctrl+O         : Open file (Data Load tab)
Ctrl+Shift+O   : Load more files
Ctrl+Shift+D   : Toggle loaded data column
Ctrl+Shift+V   : Toggle preview canvas
Ctrl+Shift+L   : Toggle layers dock
Ctrl+Shift+P   : Toggle peak picker dock
Ctrl+Shift+R   : Toggle properties dock
Ctrl+1         : Switch to Data Load tab
Ctrl+2         : Switch to Processing tab
```

### Context Menus
- Right-click on loaded file → Remove, Show Info, Export
- Right-click on preview canvas → Export Image, Copy to Clipboard

## Testing Checklist

### Functional Tests
- [ ] Load single file → appears in loaded data list
- [ ] Load multiple files → all appear in list
- [ ] Select file in list → preview updates
- [ ] Switch preview modes → canvas updates correctly
- [ ] Detach preview canvas → works as separate window
- [ ] Switch to Processing tab → docks appear
- [ ] Switch to Data Load tab → docks hide
- [ ] Process loaded data → HVSR computation works
- [ ] Remove file from list → removed correctly
- [ ] Clear all files → list empties

### Menu Tests
- [ ] File → Open → works
- [ ] File → Save → works
- [ ] File → Export → works
- [ ] View → Processing Tab → all items work
- [ ] View → Data Load Tab → all items work
- [ ] View → Loaded Data Column → toggles visibility
- [ ] All keyboard shortcuts work

### Edge Cases
- [ ] Load same file twice → handle gracefully
- [ ] Remove file while processing → handle error
- [ ] Switch tabs during processing → state preserved
- [ ] Close preview window → can reopen
- [ ] No files loaded + click process → show warning

## Timeline Estimate

- **Step 1** (Create new widgets): 2-3 hours
- **Step 2** (Modify main window): 2-3 hours
- **Step 3** (Update menu bar): 1 hour
- **Step 4** (Data management): 1-2 hours
- **Step 5** (Testing): 1-2 hours

**Total**: ~8-11 hours

## Notes

1. **Backward Compatibility**: Old sessions may not have loaded file info - handle gracefully
2. **Performance**: Large file lists may slow UI - consider pagination if >100 files
3. **State Preservation**: Save loaded files list in session
4. **Error Handling**: Add try-except blocks for file operations
5. **User Feedback**: Add status messages when files load, process, or fail

## Questions/Clarifications Needed

1. ✅ Preview canvas default view? → Start with E component signal
2. ✅ Max files in loaded list? → No limit, use scrollbar
3. ✅ Auto-process on load? → No, user must click Process
4. ✅ Save loaded list in session? → Yes
5. ✅ Allow multiple file selection in list? → Yes, for batch operations
