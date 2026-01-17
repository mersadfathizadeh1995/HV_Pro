# GUI Components

## Location
`hvsr_pro/gui/`

## Main Window
**File:** `main_window.py`

```python
class HVSRMainWindow(QMainWindow):
    # State
    data: SeismicData
    windows: WindowCollection
    hvsr_result: HVSRResult
    
    # Key components
    mode_tabs: QTabWidget          # Data Load, Processing, Azimuthal
    plot_manager: PlotWindowManager
    layers_dock: WindowLayersDock
    peak_picker_dock: PeakPickerDock
    properties_dock: PropertiesDock
    export_dock: ExportDock
    azimuthal_properties_dock: AzimuthalPropertiesDock
```

## Tab Structure

### Tab 1: Data Load (`data_load_tab.py`)
- File browser
- Multi-file selection (Type 1, Type 2)
- Waveform preview canvas
- Time range selection
- Column mapping for CSV/ASCII

### Tab 2: Processing
- Processing settings (window length, overlap, smoothing)
- Frequency range settings
- QC mode selection (preset/custom)
- Cox FDWRA configuration
- Process button
- Info display

### Tab 3: Azimuthal (`azimuthal_tab.py`)
- Azimuthal analysis configuration
- Angle settings
- Visualization options

## Docks

### Layers Dock (`layers_dock.py`)
- Window visibility toggles
- Statistical layer toggles (mean, std, percentiles)
- Quick accept/reject all

### Peak Picker Dock (`peak_picker_dock.py`)
- Peak detection settings
- Manual peak addition
- Peak list management

### Properties Dock (`properties_dock.py`)
- Visualization mode selector
- Plot customization
- Display options

### Export Dock (`export_dock.py`)
- Export format selection
- Save results/figures

### Azimuthal Properties Dock (`azimuthal_properties_dock.py`)
- Azimuthal plot options
- Colormap selection
- Export options

## Interactive Canvas (`interactive_canvas.py`)
Matplotlib-based interactive plot:
- Click windows to toggle state
- Real-time HVSR updates
- Hover tooltips
- Timeline visualization

## Dialogs

### Data Input Dialog (`data_input_dialog.py`)
Multi-tab dialog for file import:
- Single file tab
- Multi-file Type 1 tab
- Multi-file Type 2 tab

### Channel Mapper (`channel_mapper_dialog.py`)
Map MiniSEED channels to E, N, Z

### Column Mapper (`column_mapper_dialog.py`)
Map CSV/ASCII columns to components

### Advanced QC Dialog (`advanced_qc_dialog.py`)
Fine-tune QC algorithm parameters

## Workers (`workers/`)
Background threads for:
- `processing_worker.py` - HVSR computation
- `azimuthal_worker.py` - Azimuthal analysis
- `export_worker.py` - File export

## Reusable Components (`components/`)
- `collapsible_box.py` - Collapsible group box
- `collapsible_section.py` - Expandable section
- `color_picker.py` - Color selection widget
