# Data Structures

## Location
`hvsr_pro/core/data_structures.py`

## ComponentData
Single seismic component (E, N, or Z).

```python
@dataclass
class ComponentData:
    name: str                           # 'E', 'N', 'Z'
    data: np.ndarray                    # Time series
    sampling_rate: float                # Hz
    start_time: Optional[datetime]      # Recording start
    units: str = 'm/s'                  # Data units
    metadata: Dict[str, Any]            # Additional info
    
    # Properties
    n_samples: int                      # len(data)
    duration: float                     # n_samples / sampling_rate
    time_vector: np.ndarray             # Time array
    dt: float                           # 1/sampling_rate
    
    # Methods
    get_slice(start_idx, end_idx) -> ComponentData
```

## SeismicData
Three-component seismic data container.

```python
@dataclass
class SeismicData:
    east: ComponentData                 # E component
    north: ComponentData                # N component
    vertical: ComponentData             # Z component
    station_name: str = "UNKNOWN"
    location: str = ""
    source_file: Optional[str] = None
    metadata: Dict[str, Any]
    
    # Properties
    sampling_rate: float                # Common rate
    n_samples: int                      # Common length
    duration: float                     # Duration in seconds
    start_time: Optional[datetime]
    time_vector: np.ndarray
    
    # Methods
    get_component(name) -> ComponentData
    get_horizontal_components() -> tuple[ComponentData, ComponentData]
    get_slice(start_idx, end_idx) -> SeismicData
    to_dict() -> Dict[str, Any]
```

## Validation
- Sampling rates must match across components
- Component lengths must match
- Data arrays cannot be empty
- Sampling rate must be positive

## Usage
```python
from hvsr_pro.core import HVSRDataHandler

handler = HVSRDataHandler()
data = handler.load_data('file.txt')
print(data)  # SeismicData(station='XX01', samples=3600000, rate=200.0 Hz)
```
