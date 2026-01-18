# Data Loading Implementation Plan

**Objective:** Add support for all seismic data formats from hvsrpy, maintaining modular architecture with full GUI and API integration.

**Reference:** `Files/hvsrpy-main/hvsrpy/data_wrangler.py`
**Test Data:** `Files/hvsrpy-main/hvsrpy/test/data/input/`

---

## Current State

### Existing Loaders
| Format | Loader | Status |
|--------|--------|--------|
| ASCII/TXT | `TxtDataLoader` | ✅ Complete |
| MiniSEED | `MiniSeedLoader` | ✅ Complete |

### Missing Formats (from hvsrpy)
| Format | File Extension | Components | Priority |
|--------|---------------|------------|----------|
| SAF | `.saf` | Single file (V,N,E) | High |
| SAC | `.sac` | 3 separate files | High |
| GCF | `.gcf` | Single file | Medium |
| PEER | `.vt2`, `.at2` | 3 separate files | Medium |
| MiniShark | `.minishark` | Single file | Low |

---

## Phase 1: Core Loaders Package

### 1.1 Create Loader Configuration Module
**Location:** `hvsr_pro/loaders/config.py`

```python
@dataclass
class LoaderConfig:
    """Base configuration for data loaders."""
    degrees_from_north: Optional[float] = None  # Sensor orientation
    verbose: bool = False

@dataclass  
class SAFConfig(LoaderConfig):
    """SAF-specific configuration."""
    pass  # SAF extracts rotation from NORTH_ROT header

@dataclass
class SACConfig(LoaderConfig):
    """SAC-specific configuration."""
    byteorder: str = 'auto'  # 'little', 'big', 'auto'

@dataclass
class PEERConfig(LoaderConfig):
    """PEER-specific configuration."""
    pass  # PEER extracts orientation from headers

@dataclass
class GCFConfig(LoaderConfig):
    """GCF-specific configuration."""
    pass
```

### 1.2 SAF Loader
**Location:** `hvsr_pro/loaders/saf_loader.py`

**Features:**
- Parse SESAME ASCII format header
- Extract SAMP_FREQ, NDAT, NORTH_ROT
- Identify channel columns (V, N, E)
- Return SeismicData with proper component mapping

**Key Implementation:**
```python
class SAFLoader(BaseDataLoader):
    supported_extensions = ['.saf']
    loader_name = "SAFLoader"
    
    def load_file(self, filepath: str, config: SAFConfig = None) -> SeismicData:
        # 1. Read file and parse header
        # 2. Extract: NDAT, SAMP_FREQ, CH0_ID/CH1_ID/CH2_ID, NORTH_ROT
        # 3. Parse data rows (space-separated integers)
        # 4. Create ComponentData objects (V→Z, N→N, E→E)
        # 5. Return SeismicData with degrees_from_north
```

**Regex patterns (from hvsrpy):**
```python
SAF_PATTERNS = {
    'version': r"SESAME ASCII data format \(saf\) v. (\d)",
    'npts': r"NDAT = (\d+)",
    'fs': r"SAMP_FREQ = (\d+)",
    'v_ch': r"CH(\d)_ID = V",
    'n_ch': r"CH(\d)_ID = N", 
    'e_ch': r"CH(\d)_ID = E",
    'north_rot': r"NORTH_ROT = (\d+)",
    'data_row': r"^(-?\d+.?\d*)\s(-?\d+.?\d*)\s(-?\d+.?\d*)"
}
```

### 1.3 SAC Loader
**Location:** `hvsr_pro/loaders/sac_loader.py`

**Features:**
- Load 3 separate SAC files (one per component)
- Auto-detect byte order (little/big endian)
- Component identification from channel names
- Use ObsPy for actual parsing

**Key Implementation:**
```python
class SACLoader(BaseDataLoader):
    supported_extensions = ['.sac']
    loader_name = "SACLoader"
    
    def load_file(self, filepaths: List[str], config: SACConfig = None) -> SeismicData:
        # 1. Validate 3 files provided
        # 2. Try little endian, fallback to big endian
        # 3. Extract traces via ObsPy
        # 4. Orient traces (NEZ, XYZ, or 123)
        # 5. Trim to common time range
        # 6. Return SeismicData
```

### 1.4 GCF Loader
**Location:** `hvsr_pro/loaders/gcf_loader.py`

**Features:**
- Load single GCF file with all 3 components
- Use ObsPy with format="GCF"
- Component orientation handling

**Key Implementation:**
```python
class GCFLoader(BaseDataLoader):
    supported_extensions = ['.gcf']
    loader_name = "GCFLoader"
    
    def load_file(self, filepath: str, config: GCFConfig = None) -> SeismicData:
        # 1. Read with ObsPy (format="GCF")
        # 2. Validate 3 traces
        # 3. Orient traces
        # 4. Trim to common time
        # 5. Return SeismicData
```

### 1.5 PEER Loader
**Location:** `hvsr_pro/loaders/peer_loader.py`

**Features:**
- Parse PEER NGA format (3 separate files)
- Extract orientation from headers (UP, VER, numeric degrees)
- Parse fixed-width scientific notation data
- Handle different time steps

**Key Implementation:**
```python
class PEERLoader(BaseDataLoader):
    supported_extensions = ['.vt2', '.at2', '.dt2']
    loader_name = "PEERLoader"
    
    def load_file(self, filepaths: List[str], config: PEERConfig = None) -> SeismicData:
        # 1. Validate 3 files provided
        # 2. Parse headers (NPTS, DT, direction)
        # 3. Extract amplitude data (scientific notation)
        # 4. Organize components (UP/VER→Z, numeric→orientation)
        # 5. Trim to shortest length
        # 6. Return SeismicData
```

**Regex patterns (from hvsrpy):**
```python
PEER_PATTERNS = {
    'direction': r", (UP|VER|\d|\d\d|\d\d\d|[FGDCESHB][HLGMN][ENZ])[\r\n?|\n]",
    'npts': r"NPTS=\s*(\d+),",
    'dt': r"DT=\s*(\d*\.\d+)\s",
    'sample': r"(-?\d*\.\d+[eE][+-]?\d*)"
}
```

### 1.6 Component Orientation Utility
**Location:** `hvsr_pro/loaders/orientation.py`

**Features:**
- Standardize trace organization from different naming conventions
- Handle NEZ, XYZ, 123, 12Z patterns
- Apply sensor rotation (degrees_from_north)

```python
def orient_traces(traces: List[Trace], degrees_from_north: float = None) -> Tuple[Trace, Trace, Trace, float]:
    """
    Orient traces to N, E, Z components.
    
    Tries: NEZ → XYZ → 123 → 12Z
    
    Returns:
        (ns_trace, ew_trace, vt_trace, final_degrees_from_north)
    """

def arrange_traces(traces: List[Trace], pattern: str = "NEZ") -> Tuple[Trace, Trace, Trace]:
    """Sort traces by component pattern."""

def trim_traces(traces: List[Trace]) -> List[Trace]:
    """Trim traces to common time window."""
```

---

## Phase 2: Data Handler Updates

### 2.1 Update HVSRDataHandler
**Location:** `hvsr_pro/core/data_handler.py`

**Changes:**
1. Register all new loaders
2. Enhance auto-detection
3. Add unified loading interface

```python
class HVSRDataHandler:
    def __init__(self):
        self.loaders: Dict[str, BaseDataLoader] = {
            'txt': TxtDataLoader(),
            'miniseed': MiniSeedLoader(),
            'saf': SAFLoader(),      # NEW
            'sac': SACLoader(),      # NEW
            'gcf': GCFLoader(),      # NEW
            'peer': PEERLoader(),    # NEW
        }
    
    def _detect_format(self, filepath: str) -> str:
        """Enhanced auto-detection trying all loaders."""
        # 1. Extension-based quick check
        # 2. Try each loader's can_load() method
        # 3. Return first successful match
    
    def load_multi_component(
        self, 
        filepaths: List[str],
        format: str = 'auto',
        degrees_from_north: float = None,
        **kwargs
    ) -> SeismicData:
        """Load from multiple files (SAC, PEER formats)."""
```

### 2.2 Format Registry
**Location:** `hvsr_pro/loaders/__init__.py`

```python
# Format information registry
FORMAT_INFO = {
    'txt': {
        'name': 'ASCII Text',
        'extensions': ['.txt', '.dat', '.asc'],
        'multi_file': False,
        'description': 'OSCAR format text files'
    },
    'miniseed': {
        'name': 'MiniSEED',
        'extensions': ['.mseed', '.miniseed', '.ms'],
        'multi_file': 'optional',  # Single or separate files
        'description': 'Standard seismic format'
    },
    'saf': {
        'name': 'SESAME ASCII Format',
        'extensions': ['.saf'],
        'multi_file': False,
        'description': 'SESAME project standard format'
    },
    'sac': {
        'name': 'SAC',
        'extensions': ['.sac'],
        'multi_file': True,  # Always 3 files
        'description': 'Seismic Analysis Code format'
    },
    'gcf': {
        'name': 'Guralp GCF',
        'extensions': ['.gcf'],
        'multi_file': False,
        'description': 'Guralp Compressed Format'
    },
    'peer': {
        'name': 'PEER NGA',
        'extensions': ['.vt2', '.at2', '.dt2'],
        'multi_file': True,  # Always 3 files
        'description': 'Pacific Earthquake Engineering Research format'
    }
}

def get_supported_formats() -> List[str]:
    """Get list of all supported format names."""
    
def get_format_info(format_name: str) -> Dict[str, Any]:
    """Get detailed information about a format."""
    
def get_file_filter() -> str:
    """Get Qt file dialog filter string for all formats."""
```

---

## Phase 3: GUI Integration

### 3.1 Update DataInputDialog
**Location:** `hvsr_pro/gui/dialogs/data_input/data_input_dialog.py`

**Changes:**
1. Add format selector dropdown (auto-detect as default)
2. Show/hide appropriate options based on format
3. Support multi-file selection for SAC/PEER

### 3.2 New Format Tab Component
**Location:** `hvsr_pro/gui/dialogs/data_input/tabs/format_selector_tab.py`

**Features:**
- Format dropdown with descriptions
- Dynamic UI based on format:
  - Single file formats: Single file browser
  - Multi-file formats: 3-file browser with component labels
- Degrees from north input (optional)
- Format-specific options

```python
class FormatSelectorTab(DataInputTabBase):
    """Tab for selecting format and loading files."""
    
    format_changed = pyqtSignal(str)  # Emitted when format changes
    
    def __init__(self, parent=None):
        self.format_combo = QComboBox()
        self.single_file_group = QGroupBox()
        self.multi_file_group = QGroupBox()
        
    def _init_ui(self):
        # Format selector with descriptions
        # Single file input (for txt, miniseed, saf, gcf)
        # Multi-file input (for sac, peer)
        # Degrees from north spinner
        
    def _on_format_changed(self, format_name: str):
        # Show/hide appropriate input groups
        # Update file filters
```

### 3.3 Multi-File Browser Widget
**Location:** `hvsr_pro/gui/widgets/multi_file_browser.py`

**Features:**
- 3 file path inputs with labels (N/E/Z or file1/file2/file3)
- Auto-detect component from filename
- Validate all 3 files selected

```python
class MultiFileBrowser(QWidget):
    """Widget for selecting 3 component files."""
    
    files_selected = pyqtSignal(dict)  # {'N': path, 'E': path, 'Z': path}
    
    def __init__(self, component_labels: List[str] = ['N', 'E', 'Z']):
        self.file_inputs = {}  # {component: QLineEdit}
        self.browse_buttons = {}  # {component: QPushButton}
        
    def get_files(self) -> Dict[str, str]:
        """Get selected files as {component: path} dict."""
        
    def auto_detect_components(self, filepaths: List[str]) -> Dict[str, str]:
        """Try to auto-assign components from filenames."""
```

### 3.4 Format Options Dialog
**Location:** `hvsr_pro/gui/dialogs/data_input/format_options_dialog.py`

**Features:**
- Show format-specific settings
- Preview file content
- Advanced options (byte order for SAC, etc.)

```python
class FormatOptionsDialog(QDialog):
    """Dialog for format-specific loading options."""
    
    def __init__(self, format_name: str, filepath: str, parent=None):
        self.format_name = format_name
        self.filepath = filepath
        
    def _init_ui(self):
        # File preview section
        # Format-specific options
        # Degrees from north input
        
    def get_config(self) -> LoaderConfig:
        """Get loader configuration."""
```

### 3.5 Update SingleFileTab
**Location:** `hvsr_pro/gui/dialogs/data_input/tabs/single_file_tab.py`

**Changes:**
1. Add format selector (with auto-detect option)
2. Update file filters based on format
3. Show format options button when needed

### 3.6 Create SAC/PEER Tab
**Location:** `hvsr_pro/gui/dialogs/data_input/tabs/multi_component_tab.py`

**Features:**
- For formats requiring 3 separate files
- Multi-file browser widget
- Component assignment (auto or manual)

```python
class MultiComponentTab(DataInputTabBase):
    """Tab for loading formats with separate component files (SAC, PEER)."""
    
    def __init__(self, parent=None):
        self.format_combo = QComboBox()  # SAC or PEER
        self.file_browser = MultiFileBrowser()
        
    def _init_ui(self):
        # Format selector (SAC/PEER only)
        # Multi-file browser
        # Degrees from north
        # Advanced options button
```

---

## Phase 4: API Integration

### 4.1 Update HVSRAnalysis
**Location:** `hvsr_pro/api/analysis.py`

**Changes:**
```python
class HVSRAnalysis:
    def load_data(
        self,
        filepath: Union[str, List[str]],
        format: str = 'auto',
        degrees_from_north: float = None,
        **kwargs
    ) -> 'HVSRAnalysis':
        """
        Load seismic data from file(s).
        
        Args:
            filepath: Single file path or list of 3 paths (for SAC/PEER)
            format: Format name or 'auto' for detection
            degrees_from_north: Sensor orientation (optional)
            
        Returns:
            self for method chaining
        """
```

### 4.2 API Examples
```python
# Auto-detection
analysis = HVSRAnalysis()
analysis.load_data("data.saf")

# Explicit format
analysis.load_data("data.gcf", format='gcf')

# Multi-file formats
analysis.load_data([
    "file_e.sac",
    "file_n.sac", 
    "file_z.sac"
], format='sac', degrees_from_north=45.0)

# PEER format
analysis.load_data([
    "rsn942_northr_alh090.vt2",
    "rsn942_northr_alh360.vt2",
    "rsn942_northr_alh-up.vt2"
], format='peer')
```

---

## Phase 5: Testing

### 5.1 Unit Tests
**Location:** `tests/loaders/`

```
tests/loaders/
├── test_saf_loader.py      # SAF format tests
├── test_sac_loader.py      # SAC format tests
├── test_gcf_loader.py      # GCF format tests
├── test_peer_loader.py     # PEER format tests
├── test_orientation.py     # Orientation utility tests
└── test_auto_detection.py  # Format detection tests
```

**Test data:** Use files from `Files/hvsrpy-main/hvsrpy/test/data/input/`

### 5.2 Integration Tests
- Test loading through GUI dialog
- Test API data loading
- Test format auto-detection accuracy

---

## Implementation Order

### Stage 1: Core Infrastructure (Day 1-2)
1. Create `loaders/config.py` with all config dataclasses
2. Create `loaders/orientation.py` with trace utilities
3. Create `loaders/patterns.py` with regex patterns

### Stage 2: SAF Loader (Day 2-3)
1. Implement `SAFLoader` class
2. Add tests with SAF test file
3. Register in HVSRDataHandler

### Stage 3: SAC Loader (Day 3-4)
1. Implement `SACLoader` class
2. Add tests with SAC test files
3. Register in HVSRDataHandler

### Stage 4: GCF Loader (Day 4)
1. Implement `GCFLoader` class
2. Add tests with GCF test file
3. Register in HVSRDataHandler

### Stage 5: PEER Loader (Day 4-5)
1. Implement `PEERLoader` class
2. Add tests with PEER test files
3. Register in HVSRDataHandler

### Stage 6: GUI Integration (Day 5-6)
1. Create `MultiFileBrowser` widget
2. Create `MultiComponentTab`
3. Update `SingleFileTab` with format selector
4. Add format options dialogs

### Stage 7: API & Documentation (Day 6-7)
1. Update `HVSRAnalysis.load_data()`
2. Update architecture documentation
3. Update 07_GAPS_AND_IMPROVEMENTS.md

---

## File Changes Summary

### New Files
| File | Description |
|------|-------------|
| `loaders/config.py` | Loader configuration dataclasses |
| `loaders/orientation.py` | Trace orientation utilities |
| `loaders/patterns.py` | Regex patterns for parsing |
| `loaders/saf_loader.py` | SAF format loader |
| `loaders/sac_loader.py` | SAC format loader |
| `loaders/gcf_loader.py` | GCF format loader |
| `loaders/peer_loader.py` | PEER format loader |
| `gui/widgets/multi_file_browser.py` | Multi-file selection widget |
| `gui/dialogs/data_input/tabs/multi_component_tab.py` | Tab for SAC/PEER |
| `gui/dialogs/data_input/format_options_dialog.py` | Format options dialog |

### Modified Files
| File | Changes |
|------|---------|
| `loaders/__init__.py` | Add FORMAT_INFO registry, export new loaders |
| `core/data_handler.py` | Register new loaders, add load_multi_component() |
| `gui/dialogs/data_input/tabs/single_file_tab.py` | Add format selector |
| `gui/dialogs/data_input/tabs/__init__.py` | Export new tabs |
| `api/analysis.py` | Update load_data() for all formats |
| `_context/architecture_map.md` | Document new loaders |
| `_context/07_GAPS_AND_IMPROVEMENTS.md` | Mark formats as complete |

---

## Success Criteria

1. ✅ All 4 new formats load correctly (SAF, SAC, GCF, PEER)
2. ✅ Auto-detection correctly identifies all formats
3. ✅ GUI supports all formats with appropriate UI
4. ✅ API supports all formats with unified interface
5. ✅ Degrees from north is correctly applied
6. ✅ Component orientation works for all naming patterns
7. ✅ All test files from hvsrpy load successfully
