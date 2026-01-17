# Window Rejection Algorithms (5 Total)

## Available Algorithms

### 1. STA/LTA Window Rejection

Time-domain method using Short-Term Average / Long-Term Average ratio.

```python
from hvsrpy import sta_lta_window_rejection

passing_records = sta_lta_window_rejection(
    records,
    sta_seconds=1,              # Short-term window
    lta_seconds=30,             # Long-term window (≈ window length)
    min_sta_lta_ratio=0.2,      # Reject if below
    max_sta_lta_ratio=2.5,      # Reject if above
    components=("ns", "ew", "vt"),
    hvsr=None                   # Optional: update HVSR mask
)
```

### 2. Maximum Value Window Rejection

Time-domain method rejecting windows with extreme amplitude values.

```python
from hvsrpy import maximum_value_window_rejection

passing_records = maximum_value_window_rejection(
    records,
    maximum_value_threshold=0.9,  # Relative threshold
    normalized=True,              # Normalize to max observed
    components=("ns", "ew", "vt"),
    hvsr=None
)
```

### 3. Frequency-Domain Window Rejection (FDWRA)

**Cox et al. (2020)** - Automated frequency-domain rejection algorithm.

```python
from hvsrpy import frequency_domain_window_rejection

iterations = frequency_domain_window_rejection(
    hvsr,                           # HvsrTraditional or HvsrAzimuthal
    n=2,                            # Std devs from mean
    max_iterations=50,
    distribution_fn="lognormal",    # Peak frequency distribution
    distribution_mc="lognormal",    # Mean curve distribution
    search_range_in_hz=(None, None),
    find_peaks_kwargs=None
)
# Updates hvsr.valid_window_boolean_mask in-place
```

**Algorithm**:
1. Find peak frequency for each window
2. Compute mean and std of peak frequencies
3. Reject windows with peaks outside n*std
4. Iterate until convergence

### 4. Manual Window Rejection

Interactive visual rejection using matplotlib.

```python
from hvsrpy import manual_window_rejection

manual_window_rejection(
    hvsr,
    distribution_mc="lognormal",
    distribution_fn="lognormal",
    plot_mean_curve=True,
    plot_frequency_std=True,
    search_range_in_hz=(None, None),
    y_limit=None
)
# Interactive: draw boxes to reject curves
```

### 5. Student's t-Distribution Rejection (Beta)

Statistical rejection using Student's t-distribution.

```python
from hvsrpy.window_rejection import student_t_window_rejection

student_t_window_rejection(
    hvsr,
    n=2,                            # Std devs
    search_range_in_hz=(None, None)
)
```

### 6. Isolation Forest Outlier Rejection (Beta)

ML-based outlier detection using scikit-learn.

```python
from hvsrpy.window_rejection import isolation_forest_outlier_rejection

isolation_forest_outlier_rejection(
    hvsr,
    contamination="auto",           # Outlier proportion
    search_range_in_hz=(None, None)
)
```

## HVSR Object Masks

Window rejection algorithms update these boolean masks:

```python
hvsr.valid_window_boolean_mask  # Windows to include in statistics
hvsr.valid_peak_boolean_mask    # Peaks to include in fn statistics
```

## Typical Workflow

```python
from hvsrpy import (
    read_single, preprocess, process,
    HvsrPreProcessingSettings, HvsrTraditionalProcessingSettings,
    sta_lta_window_rejection, frequency_domain_window_rejection
)

# Load and preprocess
record = read_single("data.miniseed")
pre_settings = HvsrPreProcessingSettings(window_length_in_seconds=60)
windows = preprocess(record, pre_settings)

# Time-domain rejection (before processing)
windows = sta_lta_window_rejection(windows)

# Process
proc_settings = HvsrTraditionalProcessingSettings()
hvsr = process(windows, proc_settings)

# Frequency-domain rejection (after processing)
frequency_domain_window_rejection(hvsr, n=2)

# Results now reflect only valid windows
print(f"Valid windows: {sum(hvsr.valid_window_boolean_mask)}/{hvsr.n_curves}")
```

## Reference

Cox, B.R., Cheng, T., Vantassel, J.P., & Manuel, L. (2020).
"A statistical representation and frequency-domain window-rejection algorithm
for single-station HVSR measurements."
Geophysical Journal International, 221(3), 2170–2183.
