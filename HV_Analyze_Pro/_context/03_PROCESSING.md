# HVSR Processing Pipeline

## Location
`hvsr_pro/processing/`

## Processing Flow
```
SeismicData
    ↓
WindowManager.create_windows()
    ↓
WindowCollection
    ↓
RejectionEngine.evaluate() [QC]
    ↓
HVSRProcessor.process()
    ↓
HVSRResult
```

## WindowManager
**File:** `processing/windows/manager.py`

```python
manager = WindowManager(
    window_length=30.0,      # seconds
    overlap=0.5,             # 0-1
    taper_type='tukey',      # 'tukey', 'hann', 'hamming', 'blackman', 'none'
    taper_width=0.1
)
windows = manager.create_windows(data, calculate_quality=True)
```

**Taper Types Supported:**
- `tukey` (default)
- `hann`
- `hamming`
- `blackman`
- `none`

## WindowCollection & Window
**File:** `processing/windows/structures.py`

```python
class WindowState(Enum):
    ACTIVE = "active"
    REJECTED_AUTO = "rejected_auto"
    REJECTED_MANUAL = "rejected_manual"
    BORDERLINE = "borderline"
    PENDING = "pending"

@dataclass
class Window:
    index: int
    start_sample: int
    end_sample: int
    data: SeismicData
    state: WindowState
    visible: bool  # Layer visibility
    quality_metrics: Dict[str, float]
    rejection_reason: Optional[str]
```

## HVSRProcessor
**File:** `processing/hvsr/processor.py`

```python
processor = HVSRProcessor(
    smoothing_bandwidth=40,          # Konno-Ohmachi b
    f_min=0.2,                       # Hz
    f_max=20.0,                      # Hz
    n_frequencies=100,               # log-spaced points
    parallel=False,
    horizontal_method='geometric_mean',
    taper='hann'
)
result = processor.process(windows, detect_peaks_flag=True, save_window_spectra=True)
```

**Horizontal Combination Methods:**
- `geometric_mean` - sqrt(E * N) - **SESAME recommended**
- `arithmetic_mean` - (E + N) / 2
- `quadratic` - sqrt(E² + N²)
- `maximum` - max(E, N)

## Spectral Functions
**File:** `processing/hvsr/spectral.py`

```python
# FFT computation
frequencies, spectrum = compute_fft(data, sampling_rate, taper='hann')

# Konno-Ohmachi smoothing
smoothed = konno_ohmachi_smoothing_fast(frequencies, spectrum, bandwidth=40, fc_array=target_freqs)

# Horizontal spectrum
horizontal = calculate_horizontal_spectrum(east_spec, north_spec, method='geometric_mean')

# H/V ratio
hvsr = calculate_hvsr(horizontal, vertical)
```

## HVSRResult
**File:** `processing/hvsr/structures.py`

```python
@dataclass
class HVSRResult:
    frequencies: np.ndarray
    mean_hvsr: np.ndarray
    median_hvsr: np.ndarray
    std_hvsr: np.ndarray
    percentile_16: np.ndarray
    percentile_84: np.ndarray
    valid_windows: int
    total_windows: int
    peaks: List[Peak]
    window_spectra: List[WindowSpectrum]
    processing_params: Dict
    
    # Properties
    acceptance_rate: float
    primary_peak: Optional[Peak]
```

## GAPS - Missing Processing Features

### Smoothing Methods (Currently only Konno-Ohmachi)
Need to add:
1. Parzen smoothing
2. Constant bandwidth smoothing
3. Log-normal smoothing
4. Triangular smoothing
5. Savitzky-Golay smoothing
6. No smoothing option
7. Butterworth filter smoothing

### Pre-processing Methods
Need to add:
1. Detrending (linear, polynomial)
2. Bandpass filtering
3. Highpass/Lowpass filtering
4. Decimation/Resampling
5. Baseline correction
6. Instrument response removal
7. Unit conversion
