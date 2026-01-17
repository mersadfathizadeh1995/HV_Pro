# Quality Control / Rejection Algorithms

## Location
`hvsr_pro/processing/rejection/`

## RejectionEngine
**File:** `engine.py`

Main QC coordinator.

```python
engine = RejectionEngine()

# Use preset
engine.create_default_pipeline(mode='balanced')

# Or add algorithms manually
engine.add_algorithm(AmplitudeRejection())
engine.add_algorithm(QualityThresholdRejection(threshold=0.5))

# Evaluate
results = engine.evaluate(windows, auto_apply=True)

# Cox FDWRA (post-HVSR)
fdwra_result = engine.evaluate_fdwra(windows, hvsr_result, n=2.0)
```

## Available Presets
**File:** `presets.py`

| Preset | Description | Algorithms |
|--------|-------------|------------|
| `conservative` | Lenient | Amplitude, QualityThreshold(0.2) |
| `balanced` | Recommended | Amplitude only |
| `aggressive` | Strict | Amplitude, Quality(0.35), STA/LTA, FreqSpike, Statistical |
| `sesame` | SESAME compliant | Amplitude, Quality(0.3), + Cox FDWRA |
| `publication` | Publication quality | Amplitude, HVSRAmplitude, FlatPeak, + Cox FDWRA |
| `ml` | Machine learning | Amplitude, IsolationForest |

## Rejection Algorithms
**Location:** `algorithms/`

### Pre-HVSR Algorithms

1. **AmplitudeRejection** (`amplitude.py`)
   - Rejects clipped signals
   - Default thresholds auto-calculated

2. **QualityThresholdRejection** (`amplitude.py`)
   - Overall quality score threshold
   - `threshold`: 0.0-1.0

3. **STALTARejection** (`stalta.py`)
   - STA/LTA transient detection
   - `sta_length`: 1.0s
   - `lta_length`: 30.0s
   - `min_ratio`: 0.08
   - `max_ratio`: 3.5

4. **FrequencyDomainRejection** (`frequency.py`)
   - Spectral spike detection
   - `spike_threshold`: 3.0-4.0

5. **StatisticalOutlierRejection** (`statistical.py`)
   - IQR-based outlier detection
   - `method`: 'iqr'
   - `threshold`: 2.0-2.5

6. **IsolationForestRejection** (`ml.py`)
   - ML anomaly detection
   - Requires sklearn
   - `contamination`: 0.1

### Post-HVSR Algorithms

7. **HVSRAmplitudeRejection** (`hvsr_qc.py`)
   - Minimum HVSR amplitude check
   - `min_amplitude`: 1.0

8. **FlatPeakRejection** (`hvsr_qc.py`)
   - Detects ambiguous flat peaks
   - `flatness_threshold`: 0.15

9. **CoxFDWRARejection** (`cox_fdwra.py`)
   - Cox et al. (2020) algorithm
   - Peak frequency consistency
   - `n`: 2.0 (std multiplier)
   - `max_iterations`: 50
   - `distribution_fn`: 'lognormal' or 'normal'

## Algorithm Interface
**File:** `base.py`

```python
class BaseRejectionAlgorithm(ABC):
    name: str
    threshold: float
    enabled: bool
    
    @abstractmethod
    def evaluate_window(window) -> RejectionResult
    
    def evaluate_collection(collection) -> List[RejectionResult]
```

## GAPS - Missing QC Methods
1. Cross-correlation based rejection
2. Spectral coherence checks
3. Polarization analysis
4. Zero-crossing rate checks
5. Kurtosis-based detection
6. Energy distribution checks
