# Results & Summary Tab — Old vs New Comparison

## 1. Architecture Overview

### Old System (NewTab0_Automatic.py, lines 90–354)

The Results tab is built inside `_build_results_tab()` with a **3-column QSplitter**:

| Column | Weight | Contents |
|--------|--------|----------|
| LEFT (32%) | `QVBoxLayout` | `ResultsTable` (checkboxes per station) + `ResultsHistogram` (F0/F1/F2 histograms) |
| CENTER (50%) | `QVBoxLayout` | `ResultsCanvas` (matplotlib: station curves, grand median, ±1σ, peak picking) + "Generate Report" button |
| RIGHT (18%) | `QVBoxLayout` | `ResultsLayerTree` (hierarchical visibility tree) |

**Signal wiring:**
- `results_table.selection_changed` → `_on_results_selection_changed()` → recomputes grand median from checked stations → refreshes canvas + histogram
- `results_canvas.manual_peaks_changed` → stores peaks in `_manual_median_peaks` list
- `results_layer_tree` → 6 visibility signals → canvas `.set_*_visible()` methods
- `report_btn.clicked` → `_generate_report()` → exports to 4 subdirectories

**Data flow:**
```
HVSR Worker → processed_results list[dict] → results_handler.load_hvsr_results()
→ list[StationResult] → results_handler.run_analysis() → AutomaticWorkflowResult
→ _populate_results_tab(result)
```

### New System (batch_window.py, lines 85–310)

**Identical 3-column splitter layout.** The new system was copied from the old one and has the same structure:
- `_build_results_tab()` — creates the same 3-column layout
- `_populate_results_tab(result)` — fills all 4 widgets
- `_on_results_selection_changed()` — same recompute logic
- `_generate_report()` — same 4-subdirectory export

---

## 2. Widget-by-Widget Comparison

### 2.1 ResultsCanvas (widgets/results_canvas.py)

| Feature | Old (791 lines) | New (same file, copied) | Status |
|---------|-----------------|------------------------|--------|
| Station curves plotting | ✅ plot_all() | ✅ Identical | **OK** |
| Grand median line | ✅ replot_grand_median() | ✅ Identical | **OK** |
| ±1σ fill_between | ✅ | ✅ | **OK** |
| Manual peak picking (click-drag) | ✅ | ✅ | **OK** |
| Marker customization toolbar | ✅ | ✅ | **OK** |
| Context menu (export PNG/PDF) | ✅ | ✅ | **OK** |
| Color per array (ARRAY_COLORS) | ✅ | ✅ | **OK** |
| Smart y-limit (_compute_smart_ylim) | ✅ | ✅ | **OK** |

**Verdict:** Exact copy, no differences.

### 2.2 ResultsTable (widgets/results_table.py)

| Feature | Old (346 lines) | New (same file, copied) | Status |
|---------|-----------------|------------------------|--------|
| Checkbox per station | ✅ | ✅ | **OK** |
| Station info columns | ✅ | ✅ | **OK** |
| CSV export | ✅ | ✅ | **OK** |
| Context menu | ✅ | ✅ | **OK** |
| Color coding | ✅ | ✅ | **OK** |
| selection_changed signal | ✅ | ✅ | **OK** |

**Verdict:** Exact copy, no differences.

### 2.3 ResultsHistogram (widgets/results_histograms.py)

| Feature | Old (226 lines) | New (same file, copied) | Status |
|---------|-----------------|------------------------|--------|
| F0/F1/F2/All selector | ✅ | ✅ | **OK** |
| Simple Count vs By Array | ✅ | ✅ | **OK** |
| Refresh on selection change | ✅ | ✅ | **OK** |

**Verdict:** Exact copy, no differences.

### 2.4 ResultsLayerTree (widgets/results_layer_tree.py)

| Feature | Old (300 lines) | New (same file, copied) | Status |
|---------|-----------------|------------------------|--------|
| Hierarchical tree | ✅ | ✅ | **OK** |
| All Medians → Arrays → Stations | ✅ | ✅ | **OK** |
| Grand Median toggle | ✅ | ✅ | **OK** |
| Peak group toggle | ✅ | ✅ | **OK** |
| 6 visibility signals | ✅ | ✅ | **OK** |

**Verdict:** Exact copy, no differences.

---

## 3. Report Generation Comparison

### 3.1 report_export.py Functions

| Function | Old | New | Status |
|----------|-----|-----|--------|
| `compute_full_median_stats()` | ✅ | ✅ | **OK** |
| `compute_median_stats()` | ✅ | ✅ | **OK** |
| `export_median_data()` (Excel/CSV/JSON/MAT) | ✅ | ✅ | **OK** |
| `export_enhanced_curve()` | ✅ | ✅ | **OK** — imports updated to `hvsr_pro.packages...` |
| `export_enhanced_histogram()` | ✅ | ✅ | **OK** — imports updated |
| `detect_median_peaks()` | ✅ | ✅ | **OK** |
| `resample_to_log_grid()` | ✅ | ✅ | **OK** |
| `export_median_json_hvsr_format()` | ✅ | ✅ | **OK** |

**Key import path fix already done in new version:**
- Old: `from dialogs.figure_export_settings import DEFAULT_SETTINGS`
- New: `from hvsr_pro.packages.batch_processing.dialogs.figure_export_settings import DEFAULT_SETTINGS`
- Old: `from widgets.results_canvas import ARRAY_COLORS, _station_color, _compute_smart_ylim`
- New: `from hvsr_pro.packages.batch_processing.widgets.results_canvas import ...`

### 3.2 _generate_report() in batch_window.py (lines 217–306)

**Report creates 4 subdirectories:**
1. `curves/` — app-size PNG+PDF + enhanced publication figure
2. `histogram/` — app-size PNG+PDF + enhanced publication figure
3. `table/` — CSV + Excel (via OutputOrganizer)
4. `median/` — Excel + CSV + JSON + MAT + HVSR_Median_Result.json

The new `_generate_report()` matches the old system's structure.

---

## 4. Data Flow Pipeline

### 4.1 Processing Dataclasses (processing/ subpackage)

| Dataclass | Location | Fields | Status |
|-----------|----------|--------|--------|
| `StationResult` | `processing/automatic_workflow.py` | topic, station_name, station_id, peaks, frequencies, mean_hvsr, std_hvsr, valid_windows, total_windows, median_hvsr, percentile_16, percentile_84, quality_score, additional_data | **OK** |
| `Peak` | `processing/structures.py` | frequency, amplitude, prominence, width, left_freq, right_freq, quality | **OK** |
| `AutomaticWorkflowResult` | `processing/automatic_workflow.py` | station_results, combined_peaks, peak_statistics, metadata, grand_median_freq, grand_median_hvsr, grand_std | **OK** |
| `PeakStatistics` | `processing/automatic_workflow.py` | per_station, combined, summary | **OK** |
| `OutputOrganizer` | `processing/output_organizer.py` | Handles Excel/CSV output organization | **OK** |

### 4.2 results_handler.py Data Loading

`load_hvsr_results()` has a 3-tier fallback:
1. **JSON first**: Looks for `HVSR_{task_label}_result.json` → `HVSRResult.load()` → extracts all HVSR data
2. **MAT fallback**: Looks for `HVSR_Median_{time_window}_*.mat` → `scipy.io.loadmat()` → extracts frequencies, mean, std, median, percentiles
3. **Peaks from MAT/CSV**: Loads interactive picks from `Peaks&Median_HVSR_*.mat` or `Peaks*{task_label}*.csv`

### 4.3 Worker → Results Flow

```
BatchHVSRWorker._process_station()
  → saves per-station HVSR data to station_dir/
  → appends result dict to processed_results
  → stores in worker.station_results

_on_hvsr_finished(success)
  ├── NOT auto_mode + station_results exist → _run_interactive_peak_picking()
  └── auto_mode OR no station_results → _run_automatic_analysis()

_run_automatic_analysis()
  → results_handler.load_hvsr_results(processed_results, settings)
  → results_handler.run_analysis(station_results, settings)
  → _populate_results_tab(result)
```

---

## 5. Identified Issues & Gaps

### 5.1 CRITICAL: processed_results Population

The `processed_results` list is populated in two places:
1. `_on_data_finished()` line 881: `self.processed_results = self.data_worker.params.get('results', [])`
2. Each dict in `processed_results` needs: `station_name`, `station_id`, `dir`, `window_name`

**Potential issue:** The HVSR worker saves data to per-station directories, but the `processed_results` list is populated during the DATA processing phase (before HVSR). The `dir` field must point to the correct directory where HVSR output was saved. This depends on whether `hvsr_worker` writes its outputs to the same directory as `data_worker`.

### 5.2 Interactive Mode Flow After Peak Picking

After `_run_interactive_peak_picking()` completes (user picks peaks for each station), the code calls `_run_automatic_analysis()` which calls `results_handler.load_hvsr_results()`. This works because the interactive dialog saves peaks to the station directories.

**Potential issue:** If the interactive dialog doesn't save peaks to disk (only returns them in memory), `load_hvsr_results()` won't find them. Need to verify that `InteractivePeakDialog` saves its results to the station directory.

### 5.3 FigureExportSettingsDialog Integration

The dialog exists at `dialogs/figure_export_settings.py` and is correctly imported in `_generate_report()` (line 230). It provides customization for enhanced curve/histogram figures.

### 5.4 Missing: Connection to HV Pro's Main UI

The old system connected figure creation to HV Pro's main UI modules. The new batch_processing package is a standalone window (`BatchProcessingWindow(QMainWindow)`). If the user wants figures to also appear in the main HV Pro interface, this would require additional signal wiring between `BatchProcessingWindow` and the main application.

### 5.5 Missing: Auto-export on Completion

In auto_mode, `_run_automatic_analysis()` calls `export_automatic_results()` which uses `OutputOrganizer` for Excel/MAT/JSON export. But it does NOT generate the enhanced figures (curves/histogram). The enhanced figures are only generated in `_generate_report()` which requires clicking the "Generate Report" button.

---

## 6. Performance Enhancement Opportunities

### 6.1 Lazy Loading
- Load station HVSR data on-demand rather than all at once
- Use memory-mapped arrays for large datasets

### 6.2 Parallel Processing
- `load_hvsr_results()` iterates sequentially — could use `concurrent.futures.ThreadPoolExecutor`
- Report generation (curves + histogram + table + median) could be parallelized

### 6.3 Caching
- Cache computed grand median/std when selection doesn't change
- Cache histogram data for rapid switching between F0/F1/F2

### 6.4 Progress Feedback
- Add progress bar during results loading (large datasets with many stations)
- Add progress during report generation

---

## 7. Summary of Status

| Component | Status | Notes |
|-----------|--------|-------|
| Results tab layout | ✅ Identical | 3-column splitter with same ratios |
| ResultsCanvas | ✅ Identical | All features including manual peak picking |
| ResultsTable | ✅ Identical | Checkboxes, CSV export, context menu |
| ResultsHistogram | ✅ Identical | F0/F1/F2 selector, Simple/By Array |
| ResultsLayerTree | ✅ Identical | Hierarchical tree with 6 visibility signals |
| Signal wiring | ✅ Identical | selection_changed → recompute, layer tree → visibility |
| Report generation | ✅ Identical | 4 subdirectories, all formats |
| FigureExportSettingsDialog | ✅ Present | Correctly imported |
| Widget imports (__init__.py) | ✅ **FIXED** | Added re-exports for all widget classes |
| Interactive peak saving | ✅ **FIXED** | Now saves updated peaks to JSON on disk |
| Auto-export figures | ✅ **ADDED** | Enhanced curve/histogram figures in auto mode |
| Progress feedback | ✅ **ADDED** | Step-by-step progress during load and report |
| Selection change caching | ✅ **ADDED** | Skips recompute when checked set unchanged |
| Parallel report export | ✅ **ADDED** | ThreadPoolExecutor for 4 independent exports |
| Data flow pipeline | ✅ Verified | Worker → processed_results → load → populate — all keys match |
| StationResult compatibility | ✅ Verified | All fields widgets access are present |
