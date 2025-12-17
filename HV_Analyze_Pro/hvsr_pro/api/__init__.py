"""
HVSR Pro API
============

High-level programmatic API for HVSR analysis.

Example usage:
    from hvsr_pro.api import HVSRAnalysis
    
    # Create analysis
    analysis = HVSRAnalysis()
    
    # Load data
    analysis.load_data('seismic_data.mseed')
    
    # Configure parameters
    analysis.configure(
        window_length=30,
        overlap=0.5,
        qc_mode='balanced'
    )
    
    # Process
    result = analysis.process()
    
    # Access results
    print(f"Peak frequency: {result.primary_peak.frequency} Hz")
    
    # Save results
    analysis.save_results('results.json')
    analysis.save_plots('plots/')
"""

from .analysis import HVSRAnalysis
from .batch import batch_process

__all__ = [
    'HVSRAnalysis',
    'batch_process',
]

