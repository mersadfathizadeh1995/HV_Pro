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

## GAPS - Missing Loaders
The following file formats are NOT currently supported:

1. **SAC format** - Common seismic format
2. **GCF format** - Güralp format
3. **SEG-Y format** - Industry standard
4. **SEGY/SGY** - Exploration seismology
5. **CSV with flexible column mapping** - User-defined columns
6. **Reftek format** - Reftek instruments
7. **Raw binary formats** - Vendor-specific
