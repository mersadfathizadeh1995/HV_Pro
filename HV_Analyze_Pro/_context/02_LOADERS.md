# Data Loaders

## Location
`hvsr_pro/loaders/`

## Current Loaders

### 1. TxtDataLoader
**File:** `txt_loader.py`

**Supported Extensions:** `.txt`, `.dat`, `.asc`

**Expected Format (OSCAR):**
```
Site: XX01
Duration[s]: 18000.00
Sensor_Type: CMG6TD
Depth[m]: 0.4
Units: m/s
Time[s]    E-W    N-S    Z
0.00000  -1.292e-06   1.638e-06  -2.523e-06
...
```

**Features:**
- Header parsing (Site, Duration, Sensor, Units)
- Automatic data start detection
- Sampling rate calculation from time column
- Column mapping: Time, E, N, Z

### 2. MiniSeedLoader
**File:** `miniseed_loader.py`

**Supported Extensions:** `.miniseed`, `.mseed`, `.ms`

**Requires:** ObsPy

**Features:**
- Single file with 3 components
- Separate files per component (E, N, Z)
- Channel code detection (HNE, HNN, HNZ, etc.)
- Custom channel mapping support

**Component Detection:**
- Channels ending with E/1 → East
- Channels ending with N/2 → North
- Channels ending with Z/3 → Vertical

## HVSRDataHandler
**File:** `hvsr_pro/core/data_handler.py`

Main interface for loading data.

```python
handler = HVSRDataHandler(use_cache=True, cache_size_mb=1000)

# Single file
data = handler.load_data('file.txt', format='auto')

# Multiple files
data_list = handler.load_multiple(['file1.txt', 'file2.txt'])

# Multi-file MiniSEED (Type 1: each file has all 3 components)
data = handler.load_multi_miniseed_type1(file_list, channel_mapping={'E': 'HNE', 'N': 'HNN', 'Z': 'HNZ'})

# Multi-file MiniSEED (Type 2: separate E, N, Z files)
data = handler.load_multi_miniseed_type2(file_groups)

# Time slicing
sliced = handler.slice_by_time(data, start_time, end_time, timezone_offset_hours=-5)
```

### 3. SAFLoader (SESAME ASCII Format)
**File:** `saf_loader.py`

**Supported Extensions:** `.saf`

**Features:**
- Single file with 3 components
- Header parsing (SESAME standard metadata)
- Automatic component detection

### 4. SACLoader (Seismic Analysis Code)
**File:** `sac_loader.py`

**Supported Extensions:** `.sac`

**Requires:** ObsPy

**Features:**
- 3 separate files (N, E, Z components)
- Big and little endian support
- Automatic component detection from filename

### 5. GCFLoader (Guralp Compressed Format)
**File:** `gcf_loader.py`

**Supported Extensions:** `.gcf`

**Requires:** ObsPy

**Features:**
- Single file with 3 components
- Automatic channel detection

### 6. PEERLoader (PEER NGA Format)
**File:** `peer_loader.py`

**Supported Extensions:** `.vt2`, `.at2`, `.dt2`

**Features:**
- 3 separate files (acceleration format)
- Custom parser (no ObsPy required)
- Supports PEER NGA database format

### 7. MiniSharkLoader
**File:** `minishark_loader.py`

**Supported Extensions:** `.minishark`

**Features:**
- Single file with 3 components (VT, NS, EW)
- Proprietary format parsing
- Gain and conversion factor correction

### 8. SeismicRecording3CLoader (HVSRPy JSON)
**File:** `srecord3c_loader.py`

**Supported Extensions:** `.json`

**Features:**
- HVSRPy native JSON serialization format
- Preserves metadata and degrees_from_north
- Direct SeismicData construction

---

## Future Formats to Consider
The following file formats could be added:

1. **SEG-Y format** - Industry standard
2. **SEGY/SGY** - Exploration seismology
3. **CSV with flexible column mapping** - User-defined columns
4. **Reftek format** - Reftek instruments
5. **Raw binary formats** - Vendor-specific
