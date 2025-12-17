"""
HVSR Pro CLI - Main Entry Point
================================

Command-line interface for HVSR processing.

Usage:
    hvsr-pro process input.mseed -o output/ --window-length 30 --qc-mode balanced
    hvsr-pro batch input_dir/ -o output/ --format csv
    hvsr-pro export results.json --format png --dpi 300
    hvsr-pro info input.mseed
"""

import argparse
import sys
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog='hvsr-pro',
        description='HVSR Pro - Professional seismic HVSR analysis tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process a single MiniSEED file
  hvsr-pro process data.mseed -o results/

  # Process with custom parameters
  hvsr-pro process data.mseed -o results/ --window-length 60 --qc-mode aggressive

  # Batch process all files in a directory
  hvsr-pro batch data_folder/ -o results/ --format csv

  # Export processing results to various formats
  hvsr-pro export results.json --format png --dpi 300

  # Get information about a data file
  hvsr-pro info data.mseed
        """
    )
    
    parser.add_argument('--version', action='version', version='%(prog)s 2.0')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Process command
    process_parser = subparsers.add_parser(
        'process',
        help='Process seismic data to compute HVSR',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    _add_process_arguments(process_parser)
    
    # Batch command
    batch_parser = subparsers.add_parser(
        'batch',
        help='Batch process multiple files',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    _add_batch_arguments(batch_parser)
    
    # Export command
    export_parser = subparsers.add_parser(
        'export',
        help='Export processing results',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    _add_export_arguments(export_parser)
    
    # Info command
    info_parser = subparsers.add_parser(
        'info',
        help='Display information about a data file',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    _add_info_arguments(info_parser)
    
    return parser


def _add_process_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments for the process command."""
    # Required arguments
    parser.add_argument(
        'input',
        type=str,
        help='Input file path (MiniSEED, ASCII, or CSV)'
    )
    
    # Output
    parser.add_argument(
        '-o', '--output',
        type=str,
        required=True,
        help='Output directory for results'
    )
    
    # Processing parameters
    parser.add_argument(
        '--window-length', '-w',
        type=float,
        default=30.0,
        help='Window length in seconds (default: 30)'
    )
    parser.add_argument(
        '--overlap',
        type=float,
        default=50.0,
        help='Window overlap percentage (default: 50)'
    )
    parser.add_argument(
        '--smoothing',
        type=float,
        default=40.0,
        help='Konno-Ohmachi smoothing bandwidth (default: 40)'
    )
    
    # Frequency range
    parser.add_argument(
        '--freq-min',
        type=float,
        default=0.2,
        help='Minimum frequency in Hz (default: 0.2)'
    )
    parser.add_argument(
        '--freq-max',
        type=float,
        default=20.0,
        help='Maximum frequency in Hz (default: 20)'
    )
    parser.add_argument(
        '--freq-points',
        type=int,
        default=100,
        help='Number of frequency points (default: 100)'
    )
    
    # Time range
    parser.add_argument(
        '--start-time',
        type=str,
        default=None,
        help='Start time (ISO format: YYYY-MM-DD HH:MM:SS)'
    )
    parser.add_argument(
        '--end-time',
        type=str,
        default=None,
        help='End time (ISO format: YYYY-MM-DD HH:MM:SS)'
    )
    parser.add_argument(
        '--timezone',
        type=int,
        default=0,
        help='Timezone offset from UTC in hours (default: 0)'
    )
    
    # Quality control
    parser.add_argument(
        '--qc-mode',
        type=str,
        choices=['none', 'conservative', 'balanced', 'aggressive', 'sesame', 'publication'],
        default='balanced',
        help='Quality control mode (default: balanced)'
    )
    parser.add_argument(
        '--cox-fdwra',
        action='store_true',
        help='Enable Cox FDWRA peak consistency check'
    )
    
    # Processing options
    parser.add_argument(
        '--parallel',
        action='store_true',
        help='Enable parallel processing'
    )
    parser.add_argument(
        '--cores',
        type=int,
        default=None,
        help='Number of CPU cores for parallel processing'
    )
    
    # Output options
    parser.add_argument(
        '--format',
        type=str,
        choices=['json', 'csv', 'mat', 'all'],
        default='json',
        help='Output format (default: json)'
    )
    parser.add_argument(
        '--save-plots',
        action='store_true',
        help='Save visualization plots'
    )
    parser.add_argument(
        '--dpi',
        type=int,
        default=150,
        help='DPI for saved plots (default: 150)'
    )


def _add_batch_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments for the batch command."""
    parser.add_argument(
        'input_dir',
        type=str,
        help='Input directory containing data files'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        required=True,
        help='Output directory for results'
    )
    parser.add_argument(
        '--pattern',
        type=str,
        default='*.mseed',
        help='File pattern to match (default: *.mseed)'
    )
    parser.add_argument(
        '--recursive',
        action='store_true',
        help='Process subdirectories recursively'
    )
    
    # Inherit common processing options
    _add_common_processing_options(parser)


def _add_export_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments for the export command."""
    parser.add_argument(
        'input',
        type=str,
        help='Input results file (JSON)'
    )
    parser.add_argument(
        '-o', '--output',
        type=str,
        default=None,
        help='Output directory (default: same as input)'
    )
    parser.add_argument(
        '--format',
        type=str,
        choices=['png', 'pdf', 'svg', 'csv', 'mat', 'all'],
        default='png',
        help='Export format (default: png)'
    )
    parser.add_argument(
        '--dpi',
        type=int,
        default=300,
        help='DPI for image exports (default: 300)'
    )
    parser.add_argument(
        '--plots',
        type=str,
        nargs='+',
        choices=['hvsr', 'windows', 'quality', 'statistics', 'comparison', 'all'],
        default=['hvsr'],
        help='Plot types to export'
    )


def _add_info_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments for the info command."""
    parser.add_argument(
        'input',
        type=str,
        help='Input file to inspect'
    )
    parser.add_argument(
        '--detailed',
        action='store_true',
        help='Show detailed information'
    )


def _add_common_processing_options(parser: argparse.ArgumentParser) -> None:
    """Add common processing options to a parser."""
    parser.add_argument(
        '--window-length', '-w',
        type=float,
        default=30.0,
        help='Window length in seconds (default: 30)'
    )
    parser.add_argument(
        '--overlap',
        type=float,
        default=50.0,
        help='Window overlap percentage (default: 50)'
    )
    parser.add_argument(
        '--qc-mode',
        type=str,
        choices=['none', 'conservative', 'balanced', 'aggressive', 'sesame', 'publication'],
        default='balanced',
        help='Quality control mode (default: balanced)'
    )
    parser.add_argument(
        '--format',
        type=str,
        choices=['json', 'csv', 'mat', 'all'],
        default='json',
        help='Output format (default: json)'
    )
    parser.add_argument(
        '--parallel',
        action='store_true',
        help='Enable parallel processing'
    )


def cmd_process(args: argparse.Namespace) -> int:
    """Execute the process command."""
    from hvsr_pro.api import HVSRAnalysis
    
    logger.info(f"Processing file: {args.input}")
    
    try:
        # Create analysis object
        analysis = HVSRAnalysis()
        
        # Load data
        analysis.load_data(
            args.input,
            start_time=args.start_time,
            end_time=args.end_time,
            timezone_offset=args.timezone
        )
        
        # Configure processing
        analysis.configure(
            window_length=args.window_length,
            overlap=args.overlap / 100.0,
            smoothing_bandwidth=args.smoothing,
            freq_min=args.freq_min,
            freq_max=args.freq_max,
            n_frequencies=args.freq_points,
            qc_mode=args.qc_mode if args.qc_mode != 'none' else None,
            apply_cox_fdwra=args.cox_fdwra,
            parallel=args.parallel,
            n_cores=args.cores
        )
        
        # Run processing
        result = analysis.process()
        
        # Create output directory
        output_dir = Path(args.output)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save results
        base_name = Path(args.input).stem
        
        if args.format in ['json', 'all']:
            analysis.save_results(output_dir / f"{base_name}_results.json", format='json')
            logger.info(f"Saved JSON results to {output_dir}")
            
        if args.format in ['csv', 'all']:
            analysis.save_results(output_dir / f"{base_name}_results.csv", format='csv')
            logger.info(f"Saved CSV results to {output_dir}")
            
        if args.format in ['mat', 'all']:
            analysis.save_results(output_dir / f"{base_name}_results.mat", format='mat')
            logger.info(f"Saved MAT results to {output_dir}")
        
        # Save plots if requested
        if args.save_plots:
            analysis.save_plots(output_dir, dpi=args.dpi)
            logger.info(f"Saved plots to {output_dir}")
        
        # Print summary
        logger.info(f"Processing complete!")
        logger.info(f"  Total windows: {result.total_windows}")
        logger.info(f"  Valid windows: {result.valid_windows}")
        if result.primary_peak:
            logger.info(f"  Peak frequency: {result.primary_peak.frequency:.2f} Hz")
            logger.info(f"  Peak amplitude: {result.primary_peak.amplitude:.2f}")
        
        return 0
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return 1
    except ValueError as e:
        logger.error(f"Invalid input: {e}")
        return 1
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def cmd_batch(args: argparse.Namespace) -> int:
    """Execute the batch command."""
    from hvsr_pro.api import HVSRAnalysis, batch_process
    
    input_dir = Path(args.input_dir)
    if not input_dir.is_dir():
        logger.error(f"Input directory not found: {input_dir}")
        return 1
    
    # Find files
    pattern = args.pattern
    if args.recursive:
        files = list(input_dir.rglob(pattern))
    else:
        files = list(input_dir.glob(pattern))
    
    if not files:
        logger.warning(f"No files matching '{pattern}' found in {input_dir}")
        return 1
    
    logger.info(f"Found {len(files)} files to process")
    
    # Create output directory
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Process each file
    settings = {
        'window_length': args.window_length,
        'overlap': args.overlap / 100.0,
        'qc_mode': args.qc_mode if args.qc_mode != 'none' else None,
        'parallel': args.parallel
    }
    
    results = batch_process(
        files,
        output_dir,
        settings=settings,
        output_format=args.format
    )
    
    # Print summary
    n_success = sum(1 for r in results.values() if r.get('success', False))
    logger.info(f"Batch processing complete: {n_success}/{len(files)} successful")
    
    return 0 if n_success == len(files) else 1


def cmd_export(args: argparse.Namespace) -> int:
    """Execute the export command."""
    from hvsr_pro.api import HVSRAnalysis
    
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"Input file not found: {input_path}")
        return 1
    
    output_dir = Path(args.output) if args.output else input_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Load results
        analysis = HVSRAnalysis()
        analysis.load_results(input_path)
        
        # Determine which plots to export
        if 'all' in args.plots:
            plot_types = ['hvsr', 'windows', 'quality', 'statistics', 'comparison']
        else:
            plot_types = args.plots
        
        # Export plots
        if args.format in ['png', 'pdf', 'svg', 'all']:
            for plot_type in plot_types:
                analysis.save_plot(
                    output_dir / f"{input_path.stem}_{plot_type}.{args.format}",
                    plot_type=plot_type,
                    dpi=args.dpi
                )
            logger.info(f"Exported {len(plot_types)} plots to {output_dir}")
        
        # Export data
        if args.format in ['csv', 'mat', 'all']:
            analysis.save_results(
                output_dir / f"{input_path.stem}_exported.{args.format}",
                format=args.format
            )
            logger.info(f"Exported data to {output_dir}")
        
        return 0
        
    except Exception as e:
        logger.error(f"Export failed: {e}")
        return 1


def cmd_info(args: argparse.Namespace) -> int:
    """Execute the info command."""
    from hvsr_pro.core import HVSRDataHandler
    
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"File not found: {input_path}")
        return 1
    
    try:
        handler = HVSRDataHandler()
        data = handler.load_data(str(input_path))
        
        print(f"\n{'='*60}")
        print(f"File: {input_path.name}")
        print(f"{'='*60}")
        print(f"Duration:      {data.duration:.2f} seconds ({data.duration/3600:.2f} hours)")
        print(f"Sampling Rate: {data.east.sampling_rate:.4f} Hz")
        print(f"Samples:       {len(data.east.data)}")
        
        if data.start_time:
            print(f"Start Time:    {data.start_time}")
        if data.station_name:
            print(f"Station:       {data.station_name}")
        
        print(f"\nComponents:")
        print(f"  East (E):     {len(data.east.data)} samples")
        print(f"  North (N):    {len(data.north.data)} samples")
        print(f"  Vertical (Z): {len(data.vertical.data)} samples")
        
        if args.detailed:
            import numpy as np
            print(f"\nStatistics:")
            for name, comp in [('E', data.east), ('N', data.north), ('Z', data.vertical)]:
                print(f"  {name}: min={np.min(comp.data):.4e}, max={np.max(comp.data):.4e}, "
                      f"mean={np.mean(comp.data):.4e}, std={np.std(comp.data):.4e}")
        
        print(f"{'='*60}\n")
        
        return 0
        
    except Exception as e:
        logger.error(f"Failed to read file: {e}")
        return 1


def cli(args: Optional[List[str]] = None) -> int:
    """Main CLI entry point."""
    parser = create_parser()
    parsed_args = parser.parse_args(args)
    
    if parsed_args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if parsed_args.command is None:
        parser.print_help()
        return 0
    
    # Dispatch to appropriate command
    if parsed_args.command == 'process':
        return cmd_process(parsed_args)
    elif parsed_args.command == 'batch':
        return cmd_batch(parsed_args)
    elif parsed_args.command == 'export':
        return cmd_export(parsed_args)
    elif parsed_args.command == 'info':
        return cmd_info(parsed_args)
    else:
        parser.print_help()
        return 1


def main() -> None:
    """Main entry point for the CLI."""
    sys.exit(cli())


if __name__ == '__main__':
    main()

