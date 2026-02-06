"""
Cox et al. (2020) Frequency-Domain Window Rejection Algorithm (FDWRA)
======================================================================

Implements the iterative peak frequency consistency algorithm from:
Cox, B.R., Cheng, T., Vantassel, J.P., & Manuel, L. (2020). 
"A statistical representation and frequency-domain window-rejection algorithm 
for single-station HVSR measurements." 
Geophysical Journal International, 221(3), 2170-2183.

This is the industry-standard algorithm used in the HVSR community.
"""

import numpy as np
from typing import List, Optional, Tuple, Dict, Any

from hvsr_pro.processing.rejection.base import BaseRejectionAlgorithm, RejectionResult
from hvsr_pro.processing.windows import WindowCollection


class CoxFDWRARejection(BaseRejectionAlgorithm):
    """
    Cox et al. (2020) Frequency-Domain Window Rejection Algorithm.
    
    Iteratively removes windows whose peak frequencies deviate from the
    group consensus until convergence is achieved. This ensures all 
    accepted windows have consistent peak frequencies (f0).
    
    Algorithm:
    1. Find peak frequency (fn) for each window's HVSR curve
    2. Calculate mean peak frequency across windows
    3. Calculate mean curve's peak frequency (mc)
    4. Remove windows where |fn - mean_fn| > n*std
    5. Recalculate statistics
    6. Check convergence (delta difference < 1%, delta std < 1%)
    7. Repeat until converged (max iterations)
    
    Reference:
        Cox et al. (2020), GJI, 221(3), 2170-2183
        https://doi.org/10.1093/gji/ggaa119
    """
    
    def __init__(self,
                 n: float = 2.0,
                 max_iterations: int = 50,
                 min_iterations: int = 1,
                 distribution_fn: str = "lognormal",
                 distribution_mc: str = "lognormal",
                 search_range_hz: Optional[Tuple[float, float]] = None,
                 convergence_threshold_diff: float = 0.01,
                 convergence_threshold_std: float = 0.01,
                 name: str = "CoxFDWRA"):
        """
        Initialize Cox FDWRA algorithm.
        
        Args:
            n: Number of standard deviations for rejection bounds (default: 2.0)
            max_iterations: Maximum iterations before stopping (default: 50)
            min_iterations: Minimum iterations to run before checking convergence (default: 1)
                           Set to higher value to force more rejections even if
                           convergence criteria are met early.
            distribution_fn: Distribution for fn statistics ("lognormal" or "normal")
            distribution_mc: Distribution for mean curve ("lognormal" or "normal")
            search_range_hz: Frequency range to search for peaks (f_min, f_max)
                           None = use full range
            convergence_threshold_diff: Convergence threshold for difference (default: 0.01)
            convergence_threshold_std: Convergence threshold for std (default: 0.01)
            name: Algorithm name
        """
        super().__init__(name, threshold=n)
        self.n = n
        self.max_iterations = max_iterations
        self.min_iterations = min(min_iterations, max_iterations)  # Can't exceed max
        self.distribution_fn = distribution_fn
        self.distribution_mc = distribution_mc
        self.search_range_hz = search_range_hz
        self.convergence_threshold_diff = convergence_threshold_diff
        self.convergence_threshold_std = convergence_threshold_std
        
        # Store iteration history for analysis
        self.iteration_history = []
        self.converged_iteration = None
    
    def evaluate_collection(self, collection: WindowCollection) -> List[RejectionResult]:
        """
        Evaluate entire window collection using iterative FDWRA.
        
        This is a COLLECTION-LEVEL algorithm - it requires all windows
        to determine which ones to reject based on peak frequency consensus.
        
        Args:
            collection: WindowCollection with window_spectra computed
            
        Returns:
            List of RejectionResult for each window
        """
        # Get HVSR result from collection metadata
        if not hasattr(collection, '_hvsr_result') or collection._hvsr_result is None:
            return [RejectionResult(
                should_reject=False,
                reason="FDWRA requires HVSR computation first",
                score=0.0,
                metadata={'error': 'No HVSR result available'}
            ) for _ in collection.windows]
        
        hvsr_result = collection._hvsr_result
        frequencies = hvsr_result.frequencies
        
        # Extract individual window HVSR curves
        window_hvsr_curves = [None] * len(collection.windows)
        
        # Map window_spectra back to original window indices
        active_window_idx = 0
        for i, window in enumerate(collection.windows):
            if window.is_active() and active_window_idx < len(hvsr_result.window_spectra):
                window_hvsr_curves[i] = hvsr_result.window_spectra[active_window_idx].hvsr
                active_window_idx += 1
        
        # Initialize masks
        n_windows = len(collection.windows)
        valid_mask = np.array([w.is_active() for w in collection.windows])
        
        # Store initial state
        initial_valid_count = np.sum(valid_mask)
        
        # Run iterative rejection
        self.iteration_history = []
        converged = False
        
        for iteration in range(1, self.max_iterations + 1):
            # Extract currently valid curves and their indices
            valid_indices = np.where(valid_mask)[0]
            
            if len(valid_indices) < 3:
                break
            
            valid_curves = [window_hvsr_curves[i] for i in valid_indices]
            
            # Step 1: Find peak frequency for each valid window
            peak_frequencies = []
            for hvsr_curve in valid_curves:
                peak_freq = self._find_peak_frequency(frequencies, hvsr_curve, self.search_range_hz)
                peak_frequencies.append(peak_freq)
            
            peak_frequencies = np.array(peak_frequencies)
            
            # Step 2: Calculate statistics BEFORE rejection
            mean_fn_before = self._calculate_mean(peak_frequencies, self.distribution_fn)
            std_fn_before = self._calculate_std(peak_frequencies, self.distribution_fn)
            
            # Step 3: Calculate mean curve peak frequency
            mean_curve = np.mean(np.array(valid_curves), axis=0)
            mc_peak_freq_before = self._find_peak_frequency(frequencies, mean_curve, self.search_range_hz)
            
            diff_before = abs(mean_fn_before - mc_peak_freq_before)
            
            # Step 4: Apply rejection based on bounds
            lower_bound = self._calculate_nth_std(peak_frequencies, -self.n, self.distribution_fn)
            upper_bound = self._calculate_nth_std(peak_frequencies, +self.n, self.distribution_fn)
            
            # Mark windows outside bounds as invalid
            new_valid_mask = valid_mask.copy()
            n_rejected_this_iteration = 0
            for i, valid_idx in enumerate(valid_indices):
                if peak_frequencies[i] < lower_bound or peak_frequencies[i] > upper_bound:
                    new_valid_mask[valid_idx] = False
                    n_rejected_this_iteration += 1
            
            # Update mask if windows were rejected
            windows_rejected = n_rejected_this_iteration > 0
            if windows_rejected:
                valid_mask = new_valid_mask
            
            # Recalculate statistics (always, to track iteration progress)
            valid_indices_after = np.where(valid_mask)[0]
            if len(valid_indices_after) < 3:
                # Not enough windows remaining
                self.converged_iteration = iteration
                break
            
            valid_curves_after = [window_hvsr_curves[i] for i in valid_indices_after]
            peak_frequencies_after = np.array([
                self._find_peak_frequency(frequencies, curve, self.search_range_hz)
                for curve in valid_curves_after
            ])
            
            mean_fn_after = self._calculate_mean(peak_frequencies_after, self.distribution_fn)
            std_fn_after = self._calculate_std(peak_frequencies_after, self.distribution_fn)
            
            mean_curve_after = np.mean(np.array(valid_curves_after), axis=0)
            mc_peak_freq_after = self._find_peak_frequency(frequencies, mean_curve_after, self.search_range_hz)
            
            diff_after = abs(mean_fn_after - mc_peak_freq_after)
            
            # Calculate convergence metrics (handle zero values)
            if diff_before == 0 or std_fn_before == 0 or std_fn_after == 0:
                d_diff = 0.0
                s_diff = 0.0
            else:
                d_diff = abs(diff_after - diff_before) / diff_before
                s_diff = abs(std_fn_after - std_fn_before)
            
            # Store iteration info
            self.iteration_history.append({
                'iteration': iteration,
                'n_valid': len(valid_indices_after),
                'n_rejected': n_rejected_this_iteration,
                'mean_fn': mean_fn_after,
                'std_fn': std_fn_after,
                'mc_peak': mc_peak_freq_after,
                'diff': diff_after,
                'd_diff': d_diff,
                's_diff': s_diff,
                'lower_bound': lower_bound,
                'upper_bound': upper_bound,
                'min_iterations_reached': iteration >= self.min_iterations
            })
            
            # Check if we should stop
            # Only allow stopping if we've completed minimum iterations
            if iteration >= self.min_iterations:
                # Check if no windows rejected this iteration (natural convergence)
                if not windows_rejected:
                    converged = True
                    self.converged_iteration = iteration
                    break
                
                # Check convergence criteria
                if d_diff < self.convergence_threshold_diff and s_diff < self.convergence_threshold_std:
                    converged = True
                    self.converged_iteration = iteration
                    break
            
            # If we haven't reached min_iterations, continue even if converged
            # This forces at least min_iterations to run
        
        # Create results for each window
        results = []
        final_valid_count = np.sum(valid_mask)
        
        for i, window in enumerate(collection.windows):
            was_initially_valid = window.is_active()
            is_final_valid = valid_mask[i]
            
            if was_initially_valid and not is_final_valid:
                should_reject = True
                reason = f"Peak frequency outside {self.n}s bounds"
                score = 1.0
            elif not was_initially_valid:
                should_reject = False
                reason = "Already rejected by previous QC"
                score = 0.0
            else:
                should_reject = False
                reason = "Peak frequency within consensus"
                score = 0.0
            
            results.append(RejectionResult(
                should_reject=should_reject,
                reason=reason,
                score=score,
                metadata={
                    'converged': converged,
                    'iterations': len(self.iteration_history),
                    'max_iterations': self.max_iterations,
                    'min_iterations': self.min_iterations,
                    'initial_valid': int(initial_valid_count),
                    'final_valid': int(final_valid_count),
                    'was_initially_valid': was_initially_valid,
                    'is_final_valid': is_final_valid,
                    'algorithm': 'Cox et al. (2020) FDWRA',
                    'n_sigma': self.n,
                    'distribution_fn': self.distribution_fn,
                    'distribution_mc': self.distribution_mc
                }
            ))
        
        return results
    
    def _find_peak_frequency(self, 
                            frequencies: np.ndarray, 
                            hvsr: np.ndarray, 
                            search_range: Optional[Tuple[float, float]] = None) -> float:
        """Find peak frequency in HVSR curve."""
        if search_range is not None:
            f_min, f_max = search_range
            mask = (frequencies >= f_min) & (frequencies <= f_max)
            freqs_search = frequencies[mask]
            hvsr_search = hvsr[mask]
        else:
            freqs_search = frequencies
            hvsr_search = hvsr
        
        if len(hvsr_search) == 0:
            return frequencies[0]
        
        peak_idx = np.argmax(hvsr_search)
        return float(freqs_search[peak_idx])
    
    def _calculate_mean(self, values: np.ndarray, distribution: str) -> float:
        """Calculate mean according to distribution assumption."""
        if distribution == "lognormal":
            log_values = np.log(values + 1e-10)
            return float(np.exp(np.mean(log_values)))
        else:
            return float(np.mean(values))
    
    def _calculate_std(self, values: np.ndarray, distribution: str) -> float:
        """
        Calculate standard deviation according to distribution assumption.
        
        Returns 0.0 if fewer than 2 values are provided (ddof=1 requires at least 2).
        """
        # Handle edge case: need at least 2 values for ddof=1
        if len(values) < 2:
            return 0.0
        
        if distribution == "lognormal":
            log_values = np.log(values + 1e-10)
            return float(np.std(log_values, ddof=1))
        else:
            return float(np.std(values, ddof=1))
    
    def _calculate_nth_std(self, values: np.ndarray, n: float, distribution: str) -> float:
        """Calculate mean +/- n*std according to distribution."""
        mean = self._calculate_mean(values, distribution)
        std = self._calculate_std(values, distribution)
        
        if distribution == "lognormal":
            log_mean = np.log(mean + 1e-10)
            result = np.exp(log_mean + n * std)
        else:
            result = mean + n * std
        
        return float(result)
    
    def evaluate_window(self, window) -> RejectionResult:
        """
        Single window evaluation not supported for FDWRA.
        
        FDWRA is a COLLECTION-LEVEL algorithm that requires analyzing
        all windows together to find peak frequency consensus.
        Use evaluate_collection() instead.
        """
        return RejectionResult(
            should_reject=False,
            reason="FDWRA requires collection-level evaluation",
            score=0.0,
            metadata={
                'error': 'Use evaluate_collection() for Cox FDWRA',
                'algorithm': 'Cox et al. (2020) FDWRA'
            }
        )


# Backward compatibility alias
CoxFDWRAejection = CoxFDWRARejection

