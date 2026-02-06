# GUI Components

## Location
`hvsr_pro/gui/`

## Main Window
**File:** `main_window.py` (~1260 lines)

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

### Controller Architecture
Main window delegates to controllers in `main_window_modules/controllers/`:
- `DataController` - Data loading, multi-component support
- `ProcessingController` - HVSR processing coordination
- `PlottingController` - Plot rendering, window-spectra mapping
- `SessionController` - Save/load application state
- `WindowController` - Window state management
- `PeakController` - Peak detection
- `ExportController` - File export

### Helper Classes
Located in `main_window_modules/helpers/`:
- `MenuBarHelper` - Menu bar creation
- `ViewStateManager` - Dock/tab visibility management
- `UIUpdateCoordinator` - Post-processing UI updates

## Tab Structure

### Tab 0: Data Load (`gui/tabs/data_load_tab.py`)
- Work directory selection
- LoadedDataTree (left panel) - file list with metadata
- PreviewCanvas (right panel) - waveform preview
- Data loading triggers DataInputDialog

### Tab 1: Processing (`gui/tabs/processing_tab.py`)
- CollapsibleDataPanel - shows loaded data info
- ProcessingSettingsPanel - window/frequency settings
- UnifiedQCPanel - QC and Cox FDWRA settings
- Process HVSR button
- Window Management section
- Progress/Info display

### Tab 2: Azimuthal (`gui/tabs/azimuthal_tab.py`)
- CollapsibleDataPanel - shows loaded data info
- Azimuthal settings (angles, method)
- Processing controls

## Docks

### Layers Dock (`docks/layers/`)
- Window visibility checkboxes
- Color-coded icons matching plot lines
- Quality scores per window
- Batch operations: All On, All Off, Invert
- Statistical layer toggles (mean, std)

### Peak Picker Dock (`docks/peak_picker/`)
- Peak detection settings
- Manual peak addition
- Peak list management

### Properties Dock (`docks/properties/`)
Package structure:
- `properties_dock.py` - Main dock widget
- `sections/` - Collapsible sections (style, display, colors)
- `dialogs/` - Settings dialogs

### Export Dock (`docks/export/`)
Package structure:
- `export_dock.py` - Main dock widget
- `sections/` - Data, Plot, Report sections
- `exporters/` - Pure export functions

### Azimuthal Properties Dock (`docks/azimuthal_properties/`)
Package structure:
- `azimuthal_properties_dock.py` - Main dock widget
- `sections/` - Figure type, plot options, export
- `exporters/` - Azimuthal-specific export functions

## Canvas Components (`canvas/`)
- `plot_window_manager.py` - Main HVSR plot management
- `preview_canvas.py` - Data preview visualization
- `interactive_canvas.py` - Click-to-toggle windows

## Dialogs (`dialogs/`)

### Data Input Dialog (`dialogs/data_input/`)
Multi-tab wizard for file import:
- `tabs/single_file_tab.py` - Single file loading
- `tabs/multi_file_tab.py` - Type 1 multi-file
- `tabs/multi_type2_tab.py` - Type 2 grouped files
- `tabs/multi_component_tab.py` - SAC/PEER 3-file loading
- `tabs/time_range_panel.py` - Time range selection

### Mappers (`dialogs/mappers/`)
- `channel_mapper_dialog.py` - MiniSEED channel mapping
- `column_mapper_dialog.py` - ASCII column mapping

### QC Dialogs (`dialogs/qc/`)
- `advanced_qc_dialog.py` - Algorithm settings
- `algorithm_settings_dialogs.py` - Individual algorithm settings

### Export Dialogs (`dialogs/export/`)
- Export format configuration dialogs

## Workers (`workers/`)
Background threads for long operations:
- `processing_worker.py` - HVSR computation
- `azimuthal_processing_thread.py` - Azimuthal analysis
- `data_export_worker.py` - Data file export
- `plot_export_worker.py` - Plot image export

## Reusable Components (`components/`)
- `CollapsibleSection` - Base expandable section
- `CollapsibleGroupBox` - Collapsible container with header
- `CollapsibleDataPanel` - Loaded data display panel
- `ColorPickerButton` - Color selection widget

## Widgets (`widgets/`)
- `LoadedDataTree` - File list with tree structure
- `ViewModeSelector` - View mode buttons
- `MultiFileBrowser` - Multi-file selection widget

## Panels (`panels/`)
- `UnifiedQCPanel` - Combined QC and Cox settings

## Processing Settings (`main_window_modules/panels/`)
- `ProcessingSettingsPanel` - Window/frequency configuration
