"""
Window Rejection Engine for HVSR Pro
=====================================

High-level interface for window rejection workflows.
"""

import logging
from typing import Dict, Any, List, Optional
import json
from pathlib import Path
from datetime import datetime
import numpy as np

from hvsr_pro.processing.window_structures import Window, WindowCollection, WindowState
from hvsr_pro.processing.rejection_algorithms import (
    BaseRejectionAlgorithm,
    QualityThresholdRejection,
    StatisticalOutlierRejection,
    RejectionResult
)
from hvsr_pro.processing.rejection_advanced import (
    STALTARejection,
    FrequencyDomainRejection,
    AmplitudeRejection,
    HVSRAmplitudeRejection,
    FlatPeakRejection
)
from hvsr_pro.processing.rejection_cox_fdwra import CoxFDWRAejection

try:
    from hvsr_pro.processing.rejection_ml import IsolationForestRejection, EnsembleRejection
    HAS_ML = True
except ImportError:
    HAS_ML = False

logger = logging.getLogger(__name__)


class RejectionEngine:
    """
    Coordinates multiple rejection algorithms for window quality control.
    
    Features:
    - Multiple rejection strategies (quality, statistical, STA/LTA, frequency, ML)
    - Configurable algorithm pipeline
    - Rejection history and statistics
    - Save/load rejection results
    
    Example:
        >>> engine = RejectionEngine()
        >>> engine.add_algorithm(QualityThresholdRejection(threshold=0.5))
        >>> engine.add_algorithm(STALTARejection(threshold=3.0))
        >>> results = engine.evaluate(windows)
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
        self.history: List[Dict[str, Any]] = []
        
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
        logger.info("All algorithms cleared")
    
    def evaluate(self, 
                 windows: WindowCollection,
                 auto_apply: bool = True) -> Dict[str, Any]:
        """
        Evaluate window collection with all algorithms.
        
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
        
        # Track active windows before and after each algorithm
        initial_active = windows.n_active
        
        # Store results for each algorithm
        algorithm_results = []
        
        for algo in self.algorithms:
            active_before = windows.n_active
            
            results = algo.evaluate_collection(windows)
            
            # Count rejections by THIS algorithm
            n_rejected_by_algo = sum(1 for r in results if r.should_reject)
            
            algorithm_results.append({
                'algorithm': algo.name,
                'n_rejected': n_rejected_by_algo,
                'results': results
            })
            
            # Apply rejections if requested
            if auto_apply:
                for window, result in zip(windows.windows, results):
                    if result.should_reject and window.is_active():
                        window.reject(result.reason, manual=False)
            
            active_after = windows.n_active
            actually_rejected = active_before - active_after
            
            # Enhanced logging with before/after counts
            logger.info(f"  {algo.name}: {n_rejected_by_algo} flagged, {actually_rejected} actually rejected ({active_after}/{windows.n_windows} active now)")
            
            # WARNING if algorithm rejects too many
            if actually_rejected > windows.n_windows * 0.5:
                logger.warning(f"  ⚠️  {algo.name} rejected >50% of windows - may be too strict!")
            
            # CRITICAL if all windows rejected
            if active_after == 0:
                logger.error(f"  ❌ {algo.name} rejected ALL remaining windows!")
                break  # Stop evaluating more algorithms
        
        # Store in history
        history_entry = {
            'timestamp': datetime.now().isoformat(),
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
    
    def apply_rejections_from_results(self, 
                                     collection: WindowCollection,
                                     results_by_algorithm: Dict[str, Any]) -> int:
        """
        Apply rejections to collection based on evaluation results.
        
        Uses OR logic: window is rejected if ANY algorithm rejects it.
        
        Args:
            collection: Window collection
            results_by_algorithm: Results from evaluate()
            
        Returns:
            Number of windows rejected
        """
        rejected_count = 0
        
        for window_idx, window in enumerate(collection.windows):
            if not window.is_active():
                continue  # Skip already rejected windows
            
            # Check if any algorithm rejects this window
            rejection_reasons = []
            
            for algo_name, data in results_by_algorithm.items():
                result = data['results'][window_idx]
                if result.should_reject:
                    rejection_reasons.append(f"{algo_name}: {result.reason}")
            
            # Reject if any algorithm flagged it
            if rejection_reasons:
                combined_reason = " | ".join(rejection_reasons)
                window.reject(combined_reason, manual=False)
                rejected_count += 1
        
        logger.info(f"Applied rejections: {rejected_count} windows rejected")
        return rejected_count
    
    def apply_rejections(self, collection: WindowCollection) -> int:
        """
        Evaluate and apply rejections in one step.
        
        Args:
            collection: Window collection
            
        Returns:
            Number of windows rejected
        """
        evaluation = self.evaluate(collection, auto_apply=True)
        return evaluation['aggregate_statistics']['total_rejected']
    
    def _calculate_aggregate_stats(self, 
                                   results_by_algorithm: Dict[str, Any],
                                   collection: WindowCollection) -> Dict[str, Any]:
        """Calculate aggregate statistics across all algorithms."""
        # Find windows rejected by any algorithm
        rejected_by_any = set()
        rejected_by_all = None
        
        for algo_name, data in results_by_algorithm.items():
            algo_rejected = {
                i for i, result in enumerate(data['results']) 
                if result.should_reject
            }
            rejected_by_any.update(algo_rejected)
            
            if rejected_by_all is None:
                rejected_by_all = algo_rejected.copy()
            else:
                rejected_by_all.intersection_update(algo_rejected)
        
        return {
            'total_windows': collection.n_windows,
            'total_rejected': len(rejected_by_any),
            'rejection_rate': len(rejected_by_any) / collection.n_windows if collection.n_windows > 0 else 0.0,
            'rejected_by_all_algorithms': len(rejected_by_all) if rejected_by_all else 0,
            'agreement_rate': len(rejected_by_all) / len(rejected_by_any) if rejected_by_any else 1.0
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
        
        # Count rejection reasons
        reason_counts = {}
        for window in rejected_windows:
            if window.rejection_reason:
                # Extract algorithm name from reason
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
            'history': self.history
        }
        
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, 'w') as f:
            json.dump(output, f, indent=2)
        
        logger.info(f"Saved rejection results to {filepath}")
    
    def create_default_pipeline(self, mode: str = 'balanced') -> None:
        """
        Create a default rejection pipeline (industry-standard compatible).
        
        Args:
            mode: Pipeline mode:
                - 'conservative': Only obvious problems
                - 'balanced': Moderate rejection (default, recommended)
                - 'aggressive': Strict quality control
                - 'sesame': SESAME-compliant with Cox FDWRA (publication quality)
                - 'ml': Machine learning-based (requires sklearn)
        """
        self.clear_algorithms()
        
        if mode == 'conservative':
            # Only reject clear problems (lenient thresholds)
            self.add_algorithm(AmplitudeRejection())
            self.add_algorithm(QualityThresholdRejection(threshold=0.2))  # Very lenient
        
        elif mode == 'balanced':
            # Balanced approach (moderate quality control)
            # Start with only amplitude rejection - most reliable
            self.add_algorithm(AmplitudeRejection())
            # Note: QualityThresholdRejection removed - often rejects too much
            # Note: STA/LTA moved to Aggressive mode
        
        elif mode == 'aggressive':
            # Strict quality control for high-quality datasets
            self.add_algorithm(AmplitudeRejection())
            self.add_algorithm(QualityThresholdRejection(threshold=0.5))  # Strict but not excessive
            self.add_algorithm(STALTARejection(
                sta_length=1.0,
                lta_length=30.0,
                min_ratio=0.15,
                max_ratio=2.5
            ))
            self.add_algorithm(FrequencyDomainRejection(spike_threshold=3.0))  # More lenient
            self.add_algorithm(StatisticalOutlierRejection(method='iqr', threshold=2.0))  # IQR more robust
        
        elif mode == 'sesame':
            # SESAME-compliant with Cox et al. (2020) FDWRA
            # Conservative time-domain QC, let Cox FDWRA do the main rejection
            self.add_algorithm(AmplitudeRejection())
            self.add_algorithm(QualityThresholdRejection(threshold=0.3))  # Lenient - Cox FDWRA will refine
            # NOTE: Cox FDWRA must be applied AFTER HVSR computation
            # It will be called separately via evaluate_fdwra()
            logger.info("SESAME mode: Lenient time-domain QC, Cox FDWRA will ensure peak consistency")
        
        elif mode == 'ml':
            # Machine learning-based
            if not HAS_ML:
                logger.error("ML mode requires scikit-learn")
                raise ImportError("scikit-learn required for ML mode")
            
            self.add_algorithm(AmplitudeRejection())
            self.add_algorithm(IsolationForestRejection(contamination=0.1))
        
        elif mode == 'publication':
            # Publication-quality 4-condition rejection workflow
            # 
            # This mode implements a comprehensive rejection workflow:
            # - Pre-HVSR: Amplitude rejection (dead channels, clipping)
            # - Post-HVSR: HVSR amplitude < 1, peak frequency consistency, flat peak detection
            #
            # Conditions:
            # 1. HVSR peak amplitude > 1.0 (HVSRAmplitudeRejection)
            # 2. Peak frequency consistency (CoxFDWRAejection)
            # 3. Flat peak detection (FlatPeakRejection)
            # 4. Manual rejection (handled by GUI)
            
            # Pre-HVSR algorithm
            self.add_algorithm(AmplitudeRejection())
            
            # Store post-HVSR algorithms for later application
            self.post_hvsr_algorithms = [
                HVSRAmplitudeRejection(min_amplitude=1.0),  # Condition 1
                FlatPeakRejection(flatness_threshold=0.15),  # Condition 3
            ]
            # NOTE: Condition 2 (Cox FDWRA) will be applied via evaluate_fdwra()
            # Condition 4 (Manual) is handled by the GUI
            
            logger.info("Publication mode: Pre-HVSR + Post-HVSR rejection pipeline")
            logger.info("  - Pre-HVSR: Amplitude rejection")
            logger.info("  - Post-HVSR: HVSR amplitude check, flat peak detection")
            logger.info("  - Post-HVSR: Cox FDWRA will be applied separately for peak consistency")
        
        else:
            raise ValueError(f"Unknown mode: {mode}. Valid modes: conservative, balanced, aggressive, sesame, publication, ml")
        
        logger.info(f"Created {mode} rejection pipeline with {len(self.algorithms)} algorithms")
    
    def evaluate_fdwra(self,
                      collection: WindowCollection,
                      hvsr_result,
                      n: float = 2.0,
                      max_iterations: int = 50,
                      distribution_fn: str = "lognormal",
                      distribution_mc: str = "lognormal",
                      search_range_hz: Optional[tuple] = None,
                      auto_apply: bool = True) -> Dict[str, Any]:
        """
        Apply Cox et al. (2020) FDWRA algorithm after HVSR computation.
        
        This must be called AFTER HVSR processing to ensure peak frequency
        consistency across windows. It's a separate step because it requires
        the computed HVSR curves.
        
        Args:
            collection: WindowCollection to evaluate
            hvsr_result: HVSRResult from processor
            n: Number of standard deviations for rejection (default: 2.0)
            max_iterations: Maximum iterations (default: 50)
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
        cox_algo = CoxFDWRAejection(
            n=n,
            max_iterations=max_iterations,
            distribution_fn=distribution_fn,
            distribution_mc=distribution_mc,
            search_range_hz=search_range_hz
        )
        
        # Evaluate collection
        results = cox_algo.evaluate_collection(collection)
        
        # Count rejections
        n_rejected = sum(1 for r in results if r.should_reject)
        n_windows = len(results)
        
        logger.info(f"Cox FDWRA: {n_rejected}/{n_windows} windows rejected")
        logger.info(f"Converged: {cox_algo.converged_iteration is not None}")
        if cox_algo.converged_iteration:
            logger.info(f"Iterations: {cox_algo.converged_iteration}")
        
        # Apply rejections if requested
        if auto_apply:
            for window, result in zip(collection.windows, results):
                if result.should_reject and window.is_active():
                    window.reject(f"Cox FDWRA: {result.reason}")
                    logger.debug(f"Window {window.index} rejected by Cox FDWRA")
        
        # Store in history
        history_entry = {
            'timestamp': datetime.now().isoformat(),
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
    
    def evaluate_post_hvsr(self,
                           collection: WindowCollection,
                           hvsr_result,
                           auto_apply: bool = True) -> Dict[str, Any]:
        """
        Apply post-HVSR rejection algorithms (HVSR amplitude, flat peak).
        
        This must be called AFTER HVSR processing. It applies the post-HVSR
        algorithms stored during matlab_style pipeline creation.
        
        Args:
            collection: WindowCollection to evaluate
            hvsr_result: HVSRResult from processor
            auto_apply: Apply rejections immediately (default: True)
            
        Returns:
            Dictionary with evaluation results
        """
        if not hasattr(self, 'post_hvsr_algorithms') or not self.post_hvsr_algorithms:
            logger.debug("No post-HVSR algorithms configured")
            return {
                'n_algorithms': 0,
                'n_rejected': 0,
                'n_windows': collection.n_windows
            }
        
        logger.info(f"Applying {len(self.post_hvsr_algorithms)} post-HVSR rejection algorithms...")
        
        # Attach HVSR data to windows for algorithms to access
        if hasattr(hvsr_result, 'window_spectra') and hvsr_result.window_spectra:
            for i, window in enumerate(collection.windows):
                if i < len(hvsr_result.window_spectra):
                    spectrum = hvsr_result.window_spectra[i]
                    window.hvsr_curve = spectrum.hvsr
                    window.hvsr_frequencies = hvsr_result.frequencies
        
        # Calculate collection-level peak statistics for FlatPeakRejection
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
                
                # Attach to windows for FlatPeakRejection
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
            'algorithm': 'Post-HVSR Rejection',
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
    
    def __repr__(self) -> str:
        return f"RejectionEngine(algorithms={len(self.algorithms)}, history={len(self.history)})"
