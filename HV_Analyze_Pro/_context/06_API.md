# Programmatic API

## Location
`hvsr_pro/api/`

## HVSRAnalysis Class
**File:** `analysis.py`

High-level interface for HVSR analysis.

```python
from hvsr_pro.api import HVSRAnalysis

# Create analysis
analysis = HVSRAnalysis()

# Load data
analysis.load_data('data.mseed', start_time='2024-01-01T10:00:00', end_time='2024-01-01T12:00:00')

# Configure
analysis.configure(
    window_length=30,
    overlap=0.5,
    smoothing_bandwidth=40,
    freq_min=0.2,
    freq_max=20.0,
    n_frequencies=100,
    qc_mode='balanced',       # 'conservative', 'balanced', 'aggressive', 'sesame', 'publication'
    apply_cox_fdwra=False,
    parallel=False
)

# Process
result = analysis.process()

# Access results
print(f"Peak: {result.primary_peak.frequency} Hz")
print(f"Windows: {result.valid_windows}/{result.total_windows}")

# Save results
analysis.save_results('results.json', format='json')  # or 'csv', 'mat'

# Save plots
analysis.save_plots('plots/', plot_types=['hvsr', 'quality'])
analysis.save_plot('hvsr_curve.png', plot_type='hvsr', dpi=300)

# Get summary
summary = analysis.get_summary()
```

## ProcessingConfig
```python
@dataclass
class ProcessingConfig:
    window_length: float = 30.0
    overlap: float = 0.5
    smoothing_bandwidth: float = 40.0
    freq_min: float = 0.2
    freq_max: float = 20.0
    n_frequencies: int = 100
    qc_mode: Optional[str] = 'balanced'
    apply_cox_fdwra: bool = False
    parallel: bool = False
    n_cores: Optional[int] = None
```

## Batch Processing
**File:** `batch.py`

```python
from hvsr_pro.api import batch_process

# Process multiple files
results = batch_process(
    files=['file1.mseed', 'file2.mseed', 'file3.mseed'],
    output_dir='output/',
    settings={
        'window_length': 30,
        'overlap': 0.5,
        'qc_mode': 'balanced'
    },
    output_format='all',     # 'json', 'csv', 'mat', 'all'
    parallel=True,
    n_workers=4,
    progress_callback=lambda curr, total, msg: print(f"{curr}/{total}: {msg}")
)

# Results dictionary
for file_path, result in results.items():
    if result['success']:
        print(f"{file_path}: {result['peak_frequency']:.2f} Hz")
    else:
        print(f"{file_path}: FAILED - {result['error']}")
```

## Direct Component Access

For more control, use components directly:

```python
from hvsr_pro import HVSRDataHandler, WindowManager, RejectionEngine, HVSRProcessor

# Load
handler = HVSRDataHandler()
data = handler.load_data('file.txt')

# Windows
manager = WindowManager(window_length=30, overlap=0.5)
windows = manager.create_windows(data)

# QC
engine = RejectionEngine()
engine.create_default_pipeline(mode='balanced')
engine.evaluate(windows)

# Process
processor = HVSRProcessor(smoothing_bandwidth=40, f_min=0.2, f_max=20)
result = processor.process(windows)

# Cox FDWRA (optional, after HVSR)
engine.evaluate_fdwra(windows, result, n=2.0)
result = processor.process(windows)  # Reprocess with updated windows
```
