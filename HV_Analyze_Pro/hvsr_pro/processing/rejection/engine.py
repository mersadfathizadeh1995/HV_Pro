"""
Window Rejection Engine
========================

High-level interface for window rejection workflows.
Coordinates multiple rejection algorithms for quality control.
"""

import logging
from typing import Dict, Any, List, Optional
import json
from pathlib import Path
from datetime import datetime
import numpy as np

from hvsr_pro.processing.windows import Window, WindowCollection, WindowState
from hvsr_pro.processing.rejection.base import BaseRejectionAlgorithm, RejectionResult
from hvsr_pro.processing.rejection.algorithms.cox_fdwra import CoxFDWRARejection

logger = logging.getLogger(__name__)


class RejectionEngine:
    """
    Coordinates multiple rejection algorithms for window quality control.
    
    Features:
    - Multiple rejection strategies (quality, statistical, STA/LTA, frequency, ML)
    - Configurable algorithm pipeline
    - Rejection history and statistics
    - Save/load rejection results
    - Pre-HVSR and post-HVSR rejection stages
    
    Example:
        >>> from hvsr_pro.processing.rejection import RejectionEngine, create_preset_pipeline
        >>> engine = create_preset_pipeline('balanced')
        >>> results = engine.evaluate(windows)
        
        >>> # Or build custom pipeline
        >>> engine = RejectionEngine()
        >>> engine.add_algorithm(QualityThresholdRejection(threshold=0.5))
        >>> engine.add_algorithm(STALTARejection(threshold=3.0))
        >>> engine.apply_rejections(windows)
    """
    
    def __init__(self, name: str = "RejectionEngine"):
        """
        Initialize rejection engine.
        
        Args:
            name: Engine name for logging
        """
        self.name = name
        self.algorithms: List[BaseRejectionAlgorithm] = []
        self.post_hvsr_algorithms: List[BaseRejectionAlgorithm] = []
        self.history: List[Dict[str, Any]] = []
        self.use_cox_fdwra: bool = False
        
        logger.info(f"{self.name} initialized")
    
    def add_algorithm(self, algorithm: BaseRejectionAlgorithm) -> None:
        """
        Add a rejection algorithm to the pipeline.
        
        Args:
            algorithm: Rejection algorithm instance
        """
        self.algorithms.append(algorithm)
        logger.info(f"Added algorithm: {algorithm.name}")
    
    def remove_algorithm(self, name: str) -> bool:
        """
        Remove algorithm by name.
        
        Args:
            name: Algorithm name
            
        Returns:
            True if algorithm was found and removed
        """
        for i, algo in enumerate(self.algorithms):
            if algo.name == name:
                removed = self.algorithms.pop(i)
                logger.info(f"Removed algorithm: {removed.name}")
                return True
        return False
    
    def clear_algorithms(self) -> None:
        """Remove all algorithms."""
        self.algorithms.clear()
        self.post_hvsr_algorithms.clear()
        logger.info("All algorithms cleared")
    
    def evaluate(self, 
                 windows: WindowCollection,
                 auto_apply: bool = True) -> Dict[str, Any]:
        """
        Evaluate window collection with all pre-HVSR algorithms.
        
        Args:
            windows: Window collection to evaluate
            auto_apply: Apply rejections immediately (default: True)
            
        Returns:
            Dictionary with evaluation summary
        """
        if not self.algorithms:
            logger.warning("No algorithms configured - skipping rejection")
            return {
                'n_algorithms': 0,
                'n_windows': windows.n_windows,
                'n_rejected': 0,
                'n_active': windows.n_windows
            }
        
        logger.info(f"Evaluating {windows.n_windows} windows with {len(self.algorithms)} algorithms")
        
        initial_active = windows.n_active
        algorithm_results = []
        
        for algo in self.algorithms:
            active_before = windows.n_active
            
            results = algo.evaluate_collection(windows)
            
            n_rejected_by_algo = sum(1 for r in results if r.should_reject)
            
            algorithm_results.append({
                'algorithm': algo.name,
                'n_rejected': n_rejected_by_algo,
                'results': results
            })
            
            if auto_apply:
                for window, result in zip(windows.windows, results):
                    if result.should_reject and window.is_active():
                        window.reject(result.reason, manual=False)
            
            active_after = windows.n_active
            actually_rejected = active_before - active_after
            
            logger.info(f"  {algo.name}: {n_rejected_by_algo} flagged, {actually_rejected} actually rejected ({active_after}/{windows.n_windows} active now)")
            
            if actually_rejected > windows.n_windows * 0.5:
                logger.warning(f"  {algo.name} rejected >50% of windows - may be too strict!")
            
            if active_after == 0:
                logger.error(f"  {algo.name} rejected ALL remaining windows!")
                break
        
        # Store in history
        history_entry = {
            'timestamp': datetime.now().isoformat(),
            'stage': 'pre_hvsr',
            'n_algorithms': len(self.algorithms),
            'n_windows': windows.n_windows,
            'initial_active': initial_active,
            'final_active': windows.n_active,
            'n_rejected': windows.n_rejected,
            'algorithms': [a['algorithm'] for a in algorithm_results]
        }
        self.history.append(history_entry)
        
        return {
            'n_algorithms': len(self.algorithms),
            'n_windows': windows.n_windows,
            'n_rejected': windows.n_rejected,
            'n_active': windows.n_active,
            'algorithm_results': algorithm_results
        }
    
    def evaluate_post_hvsr(self,
                           collection: WindowCollection,
                           hvsr_result,
                           auto_apply: bool = True) -> Dict[str, Any]:
        """
        Apply post-HVSR rejection algorithms (HVSR amplitude, flat peak).
        
        This must be called AFTER HVSR processing.
        
        Args:
            collection: WindowCollection to evaluate
            hvsr_result: HVSRResult from processor
            auto_apply: Apply rejections immediately (default: True)
            
        Returns:
            Dictionary with evaluation results
        """
        if not self.post_hvsr_algorithms:
            logger.debug("No post-HVSR algorithms configured")
            return {
                'n_algorithms': 0,
                'n_rejected': 0,
                'n_windows': collection.n_windows
            }
        
        logger.info(f"Applying {len(self.post_hvsr_algorithms)} post-HVSR rejection algorithms...")
        
        # Attach HVSR data to windows
        if hasattr(hvsr_result, 'window_spectra') and hvsr_result.window_spectra:
            for i, window in enumerate(collection.windows):
                if i < len(hvsr_result.window_spectra):
                    spectrum = hvsr_result.window_spectra[i]
                    window.hvsr_curve = spectrum.hvsr
                    window.hvsr_frequencies = hvsr_result.frequencies
        
        # Calculate collection-level peak statistics
        if hasattr(hvsr_result, 'window_spectra') and hvsr_result.window_spectra:
            peak_frequencies = []
            for spectrum in hvsr_result.window_spectra:
                if hasattr(spectrum, 'hvsr') and spectrum.hvsr is not None:
                    peak_idx = np.argmax(spectrum.hvsr)
                    peak_freq = hvsr_result.frequencies[peak_idx]
                    peak_frequencies.append(peak_freq)
            
            if peak_frequencies:
                mean_fn = np.mean(peak_frequencies)
                std_fn = np.std(peak_frequencies)
                
                for window in collection.windows:
                    window.collection_mean_fn = mean_fn
                    window.collection_std_fn = std_fn
        
        # Apply each post-HVSR algorithm
        total_rejected = 0
        algorithm_results = []
        
        for algo in self.post_hvsr_algorithms:
            results = algo.evaluate_collection(collection)
            n_rejected_by_algo = sum(1 for r in results if r.should_reject)
            
            algorithm_results.append({
                'algorithm': algo.name,
                'n_rejected': n_rejected_by_algo,
                'results': results
            })
            
            if auto_apply:
                for window, result in zip(collection.windows, results):
                    if result.should_reject and window.is_active():
                        window.reject(f"{algo.name}: {result.reason}")
                        total_rejected += 1
            
            logger.info(f"  {algo.name}: {n_rejected_by_algo} flagged")
        
        # Store in history
        history_entry = {
            'timestamp': datetime.now().isoformat(),
            'stage': 'post_hvsr',
            'n_algorithms': len(self.post_hvsr_algorithms),
            'n_windows': collection.n_windows,
            'n_rejected': total_rejected
        }
        self.history.append(history_entry)
        
        return {
            'n_algorithms': len(self.post_hvsr_algorithms),
            'n_rejected': total_rejected,
            'n_windows': collection.n_windows,
            'algorithm_results': algorithm_results
        }
    
    def evaluate_fdwra(self,
                      collection: WindowCollection,
                      hvsr_result,
                      n: float = 2.0,
                      max_iterations: int = 50,
                      min_iterations: int = 1,
                      distribution_fn: str = "lognormal",
                      distribution_mc: str = "lognormal",
                      search_range_hz: Optional[tuple] = None,
                      auto_apply: bool = True) -> Dict[str, Any]:
        """
        Apply Cox et al. (2020) FDWRA algorithm after HVSR computation.
        
        This ensures peak frequency consistency across windows.
        
        Args:
            collection: WindowCollection to evaluate
            hvsr_result: HVSRResult from processor
            n: Number of standard deviations for rejection (default: 2.0)
            max_iterations: Maximum iterations (default: 50)
            min_iterations: Minimum iterations before checking convergence (default: 1)
            distribution_fn: Distribution for fn ("lognormal" or "normal")
            distribution_mc: Distribution for mean curve ("lognormal" or "normal")
            search_range_hz: Frequency range for peak search (f_min, f_max) or None
            auto_apply: Apply rejections immediately (default: True)
            
        Returns:
            Dictionary with evaluation results
        """
        logger.info("Applying Cox et al. (2020) FDWRA algorithm...")
        
        # Store HVSR result in collection for algorithm access
        collection._hvsr_result = hvsr_result
        
        # Create Cox FDWRA algorithm
        cox_algo = CoxFDWRARejection(
            n=n,
            max_iterations=max_iterations,
            min_iterations=min_iterations,
            distribution_fn=distribution_fn,
            distribution_mc=distribution_mc,
            search_range_hz=search_range_hz
        )
        
        # Evaluate collection
        results = cox_algo.evaluate_collection(collection)
        
        n_rejected = sum(1 for r in results if r.should_reject)
        n_windows = len(results)
        
        logger.info(f"Cox FDWRA: {n_rejected}/{n_windows} windows rejected")
        logger.info(f"Converged: {cox_algo.converged_iteration is not None}")
        if cox_algo.converged_iteration:
            logger.info(f"Iterations: {cox_algo.converged_iteration}")
        
        if auto_apply:
            for window, result in zip(collection.windows, results):
                if result.should_reject and window.is_active():
                    window.reject(f"Cox FDWRA: {result.reason}")
                    logger.debug(f"Window {window.index} rejected by Cox FDWRA")
        
        # Store in history
        history_entry = {
            'timestamp': datetime.now().isoformat(),
            'stage': 'cox_fdwra',
            'algorithm': 'Cox FDWRA',
            'n_windows': n_windows,
            'n_rejected': n_rejected,
            'converged': cox_algo.converged_iteration is not None,
            'iterations': len(cox_algo.iteration_history),
            'parameters': {
                'n': n,
                'max_iterations': max_iterations,
                'distribution_fn': distribution_fn,
                'distribution_mc': distribution_mc,
                'search_range_hz': search_range_hz
            }
        }
        self.history.append(history_entry)
        
        return {
            'algorithm': 'Cox FDWRA',
            'n_rejected': n_rejected,
            'n_windows': n_windows,
            'rejection_rate': n_rejected / n_windows if n_windows > 0 else 0.0,
            'converged': cox_algo.converged_iteration is not None,
            'iterations': len(cox_algo.iteration_history),
            'iteration_history': cox_algo.iteration_history,
            'results': results
        }
    
    def get_rejection_summary(self, collection: WindowCollection) -> Dict[str, Any]:
        """
        Get summary of current rejection state.
        
        Args:
            collection: Window collection
            
        Returns:
            Dictionary with rejection summary
        """
        rejected_windows = collection.get_rejected_windows()
        
        reason_counts = {}
        for window in rejected_windows:
            if window.rejection_reason:
                if ':' in window.rejection_reason:
                    algo = window.rejection_reason.split(':')[0]
                    reason_counts[algo] = reason_counts.get(algo, 0) + 1
        
        return {
            'total_windows': collection.n_windows,
            'active_windows': collection.n_active,
            'rejected_windows': collection.n_rejected,
            'acceptance_rate': collection.acceptance_rate,
            'rejection_by_algorithm': reason_counts
        }
    
    def save_results(self, filepath: str) -> None:
        """
        Save rejection history to file.
        
        Args:
            filepath: Output file path (JSON)
        """
        output = {
            'engine_name': self.name,
            'algorithms': [
                {
                    'name': algo.name,
                    'type': type(algo).__name__,
                    'threshold': algo.threshold,
                    'enabled': algo.enabled
                }
                for algo in self.algorithms
            ],
            'post_hvsr_algorithms': [
                {
                    'name': algo.name,
                    'type': type(algo).__name__,
                    'threshold': algo.threshold,
                    'enabled': algo.enabled
                }
                for algo in self.post_hvsr_algorithms
            ],
            'use_cox_fdwra': self.use_cox_fdwra,
            'history': self.history
        }
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(output, f, indent=2)
        
        logger.info(f"Saved rejection results to {filepath}")
    
    def create_default_pipeline(self, mode: str = 'balanced') -> None:
        """
        Create a default rejection pipeline.
        
        This is a convenience method that wraps create_preset_pipeline.
        
        Args:
            mode: Pipeline mode (conservative, balanced, aggressive, sesame, publication, ml)
        """
        from hvsr_pro.processing.rejection.presets import create_preset_pipeline
        
        # Configure this engine using preset
        preset_engine = create_preset_pipeline(mode)
        
        # Copy configuration
        self.algorithms = preset_engine.algorithms
        self.post_hvsr_algorithms = preset_engine.post_hvsr_algorithms
        self.use_cox_fdwra = preset_engine.use_cox_fdwra
        
        logger.info(f"Created {mode} rejection pipeline with {len(self.algorithms)} algorithms")
    
    def __repr__(self) -> str:
        return f"RejectionEngine(algorithms={len(self.algorithms)}, post_hvsr={len(self.post_hvsr_algorithms)}, history={len(self.history)})"

