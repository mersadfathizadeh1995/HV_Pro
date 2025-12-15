# HVSR Pro - Next Steps Implementation Plan

## Overview
This document outlines the implementation plan for the remaining major enhancements to HVSR Pro.

## Completed Tasks ✅

1. ✅ Fixed detach/attach preview crash
2. ✅ Changed icons to standard Qt icons (maximize/normalize)
3. ✅ Fixed loaded data column position (stays in place when detaching)
4. ✅ Added right-click context menu for preview (Export, Copy to Clipboard, Toggle Grid, etc.)
5. ✅ Removed "No recent files" dropdown
6. ✅ Fixed menu bar click issues
7. ✅ Improved preview plots with better styling and metadata

## Remaining Tasks

### Task 1: Remove Window Management Section from Processing Tab
**Priority**: High
**Complexity**: Low
**Estimated Time**: 30 minutes

**Description**:
Remove the entire "Window Management" section that contains recompute, clear rejected, etc.

**Files to Modify**:
- `hvsr_pro/gui/main_window.py` - Remove window management group from `create_control_panel()`

**Steps**:
1. Locate the window management group creation
2. Comment out or remove the group
3. Test that Processing tab still works

---

### Task 2: Auto-Update HVSR Curve When Layers Toggled
**Priority**: High
**Complexity**: Medium
**Estimated Time**: 2-3 hours

**Description**:
When users toggle windows on/off in the Layers dock, the HVSR curve should automatically recalculate (median, mean, std curves) and update the plot.

**Current Behavior**:
- Windows can be toggled on/off
- Plot doesn't update automatically
- User must manually reprocess

**Desired Behavior**:
- Toggle window → immediate curve recalculation
- Median curve updates
- Statistics update (accepted/rejected counts)
- Plot refreshes

**Files to Modify**:
1. `hvsr_pro/gui/layers_dock.py` - Add signal when window state changes
2. `hvsr_pro/gui/main_window.py` - Connect signal to recompute handler
3. `hvsr_pro/processing/rejection_engine.py` - Add method to update masks without full reprocessing

**Implementation Plan**:
```python
# In layers_dock.py
class WindowLayersDock:
    window_state_changed = pyqtSignal()  # New signal

    def on_item_changed(self, item):
        # Existing code...
        self.window_state_changed.emit()  # Emit on toggle

# In main_window.py
def connect_signals(self):
    self.layers_dock.window_state_changed.connect(self.on_window_state_changed)

def on_window_state_changed(self):
    """Recompute HVSR curves when window states change."""
    if self.hvsr_result:
        # Update boolean mask
        self.update_window_mask_from_layers()

        # Replot with new mask
        self.plot_hvsr_with_updated_mask()
```

**Reference**:
Check hvsrpy for how they handle window toggling

---

### Task 3: Research and Implement hvsrpy 3D Outputs
**Priority**: Medium
**Complexity**: Medium
**Estimated Time**: 2-3 hours

**Description**:
hvsrpy has 3D visualization capabilities for azimuthal analysis. We should research these and add similar capabilities.

**hvsrpy 3D Outputs**:
From `postprocessing.py`:
1. **`plot_azimuthal_contour_3d()`** - 3D surface plot of HVSR vs frequency vs azimuth
2. **`plot_azimuthal_contour_2d()`** - 2D contour plot
3. **`plot_azimuthal_summary()`** - Summary panel

**Implementation Steps**:
1. Read hvsrpy's `postprocessing.py` methods
2. Create new visualization module: `hvsr_pro/visualization/advanced_plots.py`
3. Add 3D plotting capabilities:
   - Azimuthal plots (if we add azimuthal analysis)
   - Spatial plots (if we add multi-station analysis)
4. Add menu item in View → Advanced Visualizations

**Files to Create**:
- `hvsr_pro/visualization/advanced_plots.py`

**Files to Modify**:
- `hvsr_pro/gui/main_window.py` - Add menu items
- `hvsr_pro/visualization/__init__.py` - Export new functions

---

### Task 4: Copy hvstrip_progressive Core Codes
**Priority**: High
**Complexity**: High
**Estimated Time**: 3-4 hours

**Description**:
Copy the core computational codes from hvstrip_progressive package (without GUI) and integrate into HVSR Pro.

**Source Location**:
```
D:\Research\Narm_Afzar\Git_hub\HV_Pro\Codes_To_use\hvstrip_progressive\
```

**Target Location**:
```
D:\Research\Narm_Afzar\Git_hub\HV_Pro\HV_Analyze_Pro\hvsr_pro\forward\
```

**Files to Copy** (core algorithms only, no GUI):
1. Forward modeling core
2. Layer stripping algorithms
3. Diffuse field theory implementations
4. HVD file I/O

**Directory Structure to Create**:
```
hvsr_pro/
├── forward/
│   ├── __init__.py
│   ├── diffuse_field.py       # Diffuse field theory
│   ├── forward_model.py       # Forward modeling
│   ├── layer_stripping.py     # Layer stripping algorithm
│   ├── hvd_io.py             # HVD file I/O
│   └── utils.py              # Utility functions
```

**Steps**:
1. ✅ Create `hvsr_pro/forward/` directory
2. ✅ Identify non-GUI core files from hvstrip_progressive
3. ✅ Copy and adapt core algorithms
4. ✅ Create Python wrappers for hvd.exe integration
5. ✅ Test forward modeling independently
6. ✅ Test layer stripping independently

---

### Task 5: Create Forward Tab with Sub-Tabs
**Priority**: High
**Complexity**: High
**Estimated Time**: 4-5 hours

**Description**:
Add a new "Forward" tab to the main window with two sub-tabs:
1. Forward Modeling (diffuse field theory)
2. Layer Stripping

**UI Layout**:
```
Main Window
├── Data Load Tab
├── Processing Tab
└── Forward Tab ← NEW
    ├── Forward Modeling Sub-Tab
    │   ├── Layer Parameters Input
    │   ├── Compute Forward HVSR
    │   ├── Results Display
    │   └── Export Options
    └── Layer Stripping Sub-Tab
        ├── Measured HVSR Input
        ├── Initial Model Input
        ├── Inversion Parameters
        ├── Results Display
        └── Export Options
```

**Files to Create**:
1. `hvsr_pro/gui/forward_tab.py` - Main forward tab container
2. `hvsr_pro/gui/forward_modeling_tab.py` - Forward modeling sub-tab
3. `hvsr_pro/gui/layer_stripping_tab.py` - Layer stripping sub-tab

**Forward Modeling Tab Components**:
- Layer table (Thickness, Vs, Vp, Density)
- Add/Remove layer buttons
- Frequency range input
- Compute button
- Results plot (HVSR vs frequency)
- Export button

**Layer Stripping Tab Components**:
- Load measured HVSR button
- Initial model table
- Inversion parameters (iterations, tolerance, etc.)
- Run inversion button
- Results comparison plot (measured vs modeled)
- Export button

**Integration with hvd.exe**:
Both tabs should support:
- Loading .hvd files (layer models)
- Saving .hvd files
- Running hvd.exe via subprocess
- Parsing hvd.exe output

---

## Implementation Order

### Phase 1: Quick Fixes (1-2 hours)
1. ✅ Remove Window Management section
2. ✅ Fix minor UI issues

### Phase 2: Auto-Update Feature (2-3 hours)
1. ✅ Implement window state change signal
2. ✅ Add recompute logic
3. ✅ Test with various window configurations

### Phase 3: Copy hvstrip_progressive (3-4 hours)
1. ✅ Create forward module structure
2. ✅ Copy core algorithms
3. ✅ Test independently

### Phase 4: Forward Tab UI (4-5 hours)
1. ✅ Create tab structure
2. ✅ Implement Forward Modeling sub-tab
3. ✅ Implement Layer Stripping sub-tab
4. ✅ Integrate with core algorithms
5. ✅ Test end-to-end workflow

### Phase 5: Advanced Visualizations (2-3 hours)
1. ✅ Research hvsrpy 3D outputs
2. ✅ Implement selected visualizations
3. ✅ Add to View menu

**Total Estimated Time**: 12-17 hours

---

## Testing Checklist

### Window Management Removal
- [ ] Processing tab loads without errors
- [ ] All other controls still work
- [ ] No references to removed functions

### Auto-Update HVSR
- [ ] Toggle window on → curve updates
- [ ] Toggle window off → curve updates
- [ ] Statistics update correctly
- [ ] Plot refreshes automatically
- [ ] Performance is acceptable (< 1 second update)

### Forward Module
- [ ] Forward modeling computes correctly
- [ ] Layer stripping runs successfully
- [ ] HVD files load/save properly
- [ ] Results match reference implementations

### Forward Tab
- [ ] Tab appears in main window
- [ ] Forward Modeling sub-tab functional
- [ ] Layer Stripping sub-tab functional
- [ ] Plots display correctly
- [ ] Export works

### Advanced Visualizations
- [ ] 3D plots render correctly
- [ ] Menu items work
- [ ] Export functions work

---

## Notes

1. **HVD.exe Integration**: The hvd.exe executable should be bundled with the package or users should be instructed where to place it.

2. **Diffuse Field Theory**: This is based on Sánchez-Sesma et al. (2011) - ensure proper citation.

3. **Layer Stripping**: This is an inverse problem - may require optimization libraries (scipy.optimize).

4. **Performance**: Auto-updating curves could be slow for large datasets - consider:
   - Caching computed spectra
   - Only recomputing statistics (not spectra)
   - Adding progress indicator

5. **Backward Compatibility**: Ensure old sessions still load after these changes.

---

## References

1. hvsrpy documentation: https://hvsrpy.readthedocs.io/
2. Sánchez-Sesma et al. (2011): Diffuse field theory
3. hvstrip_progressive source code
4. ObsPy for seismic data handling
