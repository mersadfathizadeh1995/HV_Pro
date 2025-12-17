# HVSR Pro - Clean Code Standards

## Naming Conventions

- **Functions/Methods**: `snake_case` (e.g., `calculate_hvsr`, `load_data`)
- **Classes**: `PascalCase` (e.g., `HVSRProcessor`, `WindowCollection`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `MAX_ITERATIONS`, `DEFAULT_FREQUENCY_RANGE`)
- **Private members**: Leading underscore `_private_method`, `_internal_data`
- **Protected members**: Leading underscore `_protected_method`

## Function Design

- **Single Responsibility**: Each function does ONE thing well
- **Maximum length**: 50 lines (prefer 20-30)
- **Maximum parameters**: 7 (use dataclass/dict for more)
- **Return early**: Use guard clauses to reduce nesting

```python
# Good
def process_window(self, window: Window) -> Optional[Result]:
    if window is None:
        return None
    if not window.is_valid():
        return None
    
    return self._compute_result(window)

# Bad - deeply nested
def process_window(self, window):
    if window is not None:
        if window.is_valid():
            result = self._compute_result(window)
            return result
    return None
```

## Type Hints

- Required for all public functions
- Use `Optional[T]` for nullable parameters
- Use `Union[T1, T2]` sparingly (prefer polymorphism)
- Import from `typing` module

```python
from typing import Optional, List, Dict, Tuple

def calculate_statistics(
    data: np.ndarray,
    method: str = "mean",
    weights: Optional[np.ndarray] = None
) -> Dict[str, float]:
    ...
```

## Documentation

- NumPy-style docstrings for all public functions
- Inline comments for complex logic only
- Module-level docstrings explaining purpose

```python
def compute_hvsr(
    horizontal: np.ndarray,
    vertical: np.ndarray,
    smoothing: float = 40.0
) -> np.ndarray:
    """
    Compute Horizontal-to-Vertical Spectral Ratio.
    
    Parameters
    ----------
    horizontal : np.ndarray
        Horizontal component spectrum, shape (n_freq,)
    vertical : np.ndarray
        Vertical component spectrum, shape (n_freq,)
    smoothing : float, optional
        Konno-Ohmachi smoothing bandwidth, default 40.0
        
    Returns
    -------
    np.ndarray
        HVSR curve, shape (n_freq,)
        
    Raises
    ------
    ValueError
        If input arrays have different shapes
    """
```

## Error Handling

- Use specific exceptions (not generic `Exception`)
- Create custom exceptions for domain-specific errors
- Log errors before raising
- Never silently swallow exceptions

```python
class HVSRProcessingError(Exception):
    """Raised when HVSR processing fails."""
    pass

class WindowRejectionError(HVSRProcessingError):
    """Raised when all windows are rejected."""
    pass
```

## Configuration

- Use dataclasses for settings groups
- Never hardcode magic numbers
- Provide sensible defaults
- Document units in comments/docstrings

```python
from dataclasses import dataclass

@dataclass
class ProcessingConfig:
    """Processing configuration parameters."""
    
    window_length: float = 60.0  # seconds
    overlap: float = 0.5  # fraction (0-1)
    freq_min: float = 0.2  # Hz
    freq_max: float = 20.0  # Hz
    smoothing_bandwidth: float = 40.0  # Konno-Ohmachi b parameter
```

## Imports

- Group imports: stdlib, third-party, local
- Sort alphabetically within groups
- Use absolute imports for clarity

```python
# Standard library
import logging
from pathlib import Path
from typing import Optional, List

# Third-party
import numpy as np
from scipy import signal

# Local
from hvsr_pro.processing.hvsr import HVSRResult
from hvsr_pro.processing.windows import Window, WindowCollection
```

## DRY Principle

- Extract repeated code into functions
- Use inheritance/mixins for shared behavior
- Create utility modules for common operations

## Testing

- Test public interfaces, not implementation details
- Use descriptive test names: `test_<function>_<scenario>_<expected>`
- One assertion per test when possible

