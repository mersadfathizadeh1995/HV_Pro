"""
HVSR Pro API - Batch Processing
===============================

Utilities for batch processing multiple files.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed

logger = logging.getLogger(__name__)


def process_single_file(
    file_path: Path,
    output_dir: Path,
    settings: Dict[str, Any],
    output_format: str = 'json'
) -> Dict[str, Any]:
    """
    Process a single file (for use in multiprocessing).
    
    Args:
        file_path: Path to input file
        output_dir: Directory to save results
        settings: Processing settings dictionary
        output_format: Output format ('json', 'csv', 'mat')
        
    Returns:
        Dictionary with processing result status
    """
    from hvsr_pro.api import HVSRAnalysis
    
    result = {
        'file': str(file_path),
        'success': False,
        'error': None
    }
    
    try:
        analysis = HVSRAnalysis()
        
        # Load data
        analysis.load_data(file_path)
        
        # Configure
        analysis.configure(**settings)
        
        # Process
        hvsr_result = analysis.process()
        
        # Save results
        base_name = file_path.stem
        if output_format in ['json', 'all']:
            analysis.save_results(output_dir / f"{base_name}_results.json", format='json')
        if output_format in ['csv', 'all']:
            analysis.save_results(output_dir / f"{base_name}_results.csv", format='csv')
        if output_format in ['mat', 'all']:
            analysis.save_results(output_dir / f"{base_name}_results.mat", format='mat')
        
        result['success'] = True
        result['summary'] = analysis.get_summary()
        
        if hvsr_result.primary_peak:
            result['peak_frequency'] = hvsr_result.primary_peak.frequency
            result['peak_amplitude'] = hvsr_result.primary_peak.amplitude
        
    except Exception as e:
        result['error'] = str(e)
        logger.error(f"Failed to process {file_path}: {e}")
    
    return result


def batch_process(
    files: List[Union[str, Path]],
    output_dir: Union[str, Path],
    settings: Optional[Dict[str, Any]] = None,
    output_format: str = 'json',
    parallel: bool = False,
    n_workers: Optional[int] = None,
    progress_callback: Optional[callable] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Process multiple files in batch.
    
    Args:
        files: List of input file paths
        output_dir: Directory to save results
        settings: Processing settings dictionary. Options:
            - window_length: Window length in seconds (default: 30)
            - overlap: Window overlap as fraction (default: 0.5)
            - smoothing_bandwidth: Konno-Ohmachi b (default: 40)
            - freq_min: Minimum frequency (default: 0.2)
            - freq_max: Maximum frequency (default: 20)
            - qc_mode: Quality control mode (default: 'balanced')
        output_format: Output format ('json', 'csv', 'mat', 'all')
        parallel: Use parallel processing
        n_workers: Number of worker processes (default: CPU count - 1)
        progress_callback: Optional callback(current, total, message) for progress
        
    Returns:
        Dictionary mapping file paths to result dictionaries
    """
    # Normalize paths
    files = [Path(f) for f in files]
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Default settings
    if settings is None:
        settings = {}
    
    default_settings = {
        'window_length': 30.0,
        'overlap': 0.5,
        'smoothing_bandwidth': 40.0,
        'freq_min': 0.2,
        'freq_max': 20.0,
        'n_frequencies': 100,
        'qc_mode': 'balanced',
        'apply_cox_fdwra': False,
        'parallel': False
    }
    
    # Merge with defaults
    for key, value in default_settings.items():
        if key not in settings:
            settings[key] = value
    
    results = {}
    total = len(files)
    
    if parallel:
        # Parallel processing
        if n_workers is None:
            import os
            n_workers = max(1, os.cpu_count() - 1)
        
        with ProcessPoolExecutor(max_workers=n_workers) as executor:
            # Submit all jobs
            futures = {
                executor.submit(
                    process_single_file, 
                    f, output_dir, settings, output_format
                ): f for f in files
            }
            
            # Collect results
            for i, future in enumerate(as_completed(futures)):
                file_path = futures[future]
                try:
                    result = future.result()
                    results[str(file_path)] = result
                except Exception as e:
                    results[str(file_path)] = {
                        'file': str(file_path),
                        'success': False,
                        'error': str(e)
                    }
                
                if progress_callback:
                    progress_callback(i + 1, total, f"Processed {file_path.name}")
    else:
        # Sequential processing
        for i, file_path in enumerate(files):
            if progress_callback:
                progress_callback(i, total, f"Processing {file_path.name}")
            
            result = process_single_file(file_path, output_dir, settings, output_format)
            results[str(file_path)] = result
            
            if progress_callback:
                progress_callback(i + 1, total, f"Completed {file_path.name}")
    
    # Save summary
    summary_path = output_dir / "batch_summary.json"
    _save_batch_summary(results, summary_path)
    
    return results


def _save_batch_summary(results: Dict[str, Dict], output_path: Path) -> None:
    """Save batch processing summary."""
    import json
    from datetime import datetime
    
    n_success = sum(1 for r in results.values() if r.get('success', False))
    n_failed = len(results) - n_success
    
    summary = {
        'timestamp': datetime.now().isoformat(),
        'total_files': len(results),
        'successful': n_success,
        'failed': n_failed,
        'results': results
    }
    
    with open(output_path, 'w') as f:
        json.dump(summary, f, indent=2)


def create_batch_report(
    results: Dict[str, Dict],
    output_path: Union[str, Path],
    include_plots: bool = False
) -> None:
    """
    Create a summary report of batch processing results.
    
    Args:
        results: Results dictionary from batch_process()
        output_path: Path to save the report (HTML or Markdown)
        include_plots: Include embedded plots in HTML report
    """
    output_path = Path(output_path)
    
    if output_path.suffix == '.html':
        _create_html_report(results, output_path, include_plots)
    else:
        _create_markdown_report(results, output_path)


def _create_html_report(results: Dict, output_path: Path, include_plots: bool) -> None:
    """Create HTML report."""
    n_success = sum(1 for r in results.values() if r.get('success', False))
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>HVSR Pro Batch Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #2C3E50; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .success {{ color: green; }}
        .error {{ color: red; }}
    </style>
</head>
<body>
    <h1>HVSR Pro Batch Processing Report</h1>
    <p>Total files: {len(results)} | Successful: {n_success} | Failed: {len(results) - n_success}</p>
    
    <h2>Results Summary</h2>
    <table>
        <tr>
            <th>File</th>
            <th>Status</th>
            <th>Peak Freq (Hz)</th>
            <th>Peak Amp</th>
            <th>Details</th>
        </tr>
"""
    
    for file_path, result in results.items():
        status = '<span class="success">Success</span>' if result.get('success') else '<span class="error">Failed</span>'
        peak_freq = f"{result.get('peak_frequency', 'N/A'):.2f}" if result.get('peak_frequency') else 'N/A'
        peak_amp = f"{result.get('peak_amplitude', 'N/A'):.2f}" if result.get('peak_amplitude') else 'N/A'
        details = result.get('error', '') if not result.get('success') else ''
        
        html += f"""        <tr>
            <td>{Path(file_path).name}</td>
            <td>{status}</td>
            <td>{peak_freq}</td>
            <td>{peak_amp}</td>
            <td>{details}</td>
        </tr>
"""
    
    html += """    </table>
</body>
</html>"""
    
    with open(output_path, 'w') as f:
        f.write(html)


def _create_markdown_report(results: Dict, output_path: Path) -> None:
    """Create Markdown report."""
    n_success = sum(1 for r in results.values() if r.get('success', False))
    
    md = f"""# HVSR Pro Batch Processing Report

Total files: {len(results)} | Successful: {n_success} | Failed: {len(results) - n_success}

## Results Summary

| File | Status | Peak Freq (Hz) | Peak Amp |
|------|--------|----------------|----------|
"""
    
    for file_path, result in results.items():
        status = 'Success' if result.get('success') else 'Failed'
        peak_freq = f"{result.get('peak_frequency', 'N/A'):.2f}" if result.get('peak_frequency') else 'N/A'
        peak_amp = f"{result.get('peak_amplitude', 'N/A'):.2f}" if result.get('peak_amplitude') else 'N/A'
        
        md += f"| {Path(file_path).name} | {status} | {peak_freq} | {peak_amp} |\n"
    
    with open(output_path, 'w') as f:
        f.write(md)

