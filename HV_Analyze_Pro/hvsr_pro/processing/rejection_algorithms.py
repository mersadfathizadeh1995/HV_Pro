"""
Rejection Algorithms for HVSR Pro
==================================

Base classes and interfaces for window rejection algorithms.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import numpy as np
from dataclasses import dataclass

from hvsr_pro.processing.window_structures import Window, WindowCollection


@dataclass
class RejectionResult:
    """
    Result from a rejection algorithm.
    
    Attributes:
        should_reject: Whether window should be rejected
        reason: Reason for rejection
        score: Rejection score (0=accept, 1=reject)
        metadata: Additional information
    """
    should_reject: bool
    reason: str
    score: float
    metadata: Dict[str, Any]
    
    def __repr__(self) -> str:
        return f"RejectionResult(reject={self.should_reject}, score={self.score:.3f}, reason='{self.reason}')"


class BaseRejectionAlgorithm(ABC):
    """
    Abstract base class for all rejection algorithms.
    
    All rejection algorithms must implement:
    - evaluate_window: Evaluate single window
    - evaluate_collection: Evaluate collection of windows
    """
    
    def __init__(self, name: str, threshold: float = 0.5):
        """
        Initialize rejection algorithm.
        
        Args:
            name: Algorithm name
            threshold: Rejection threshold (0-1)
        """
        self.name = name
        self.threshold = threshold
        self.enabled = True
    
    @abstractmethod
    def evaluate_window(self, window: Window) -> RejectionResult:
        """
        Evaluate a single window.
        
        Args:
            window: Window to evaluate
            
        Returns:
            RejectionResult with decision and details
        """
        pass
    
    def evaluate_collection(self, collection: WindowCollection) -> List[RejectionResult]:
        """
        Evaluate all windows in a collection.
        
        Args:
            collection: Window collection
            
        Returns:
            List of RejectionResult for each window
        """
        results = []
        for window in collection.windows:
            result = self.evaluate_window(window)
            results.append(result)
        return results
    
    def apply_to_collection(self, collection: WindowCollection, auto: bool = True) -> int:
        """
        Apply rejection to collection, updating window states.
        
        Args:
            collection: Window collection to process
            auto: Use automatic rejection state (vs manual)
            
        Returns:
            Number of windows rejected
        """
        results = self.evaluate_collection(collection)
        rejected_count = 0
        
        for window, result in zip(collection.windows, results):
            if result.should_reject and window.is_active():
                window.reject(
                    reason=f"{self.name}: {result.reason}",
                    manual=not auto
                )
                rejected_count += 1
        
        return rejected_count
    
    def get_statistics(self, results: List[RejectionResult]) -> Dict[str, Any]:
        """
        Get statistics from rejection results.
        
        Args:
            results: List of rejection results
            
        Returns:
            Dictionary with statistics
        """
        scores = [r.score for r in results]
        rejected = sum(1 for r in results if r.should_reject)
        
        return {
            'algorithm': self.name,
            'total_evaluated': len(results),
            'rejected': rejected,
            'rejection_rate': rejected / len(results) if results else 0.0,
            'score_mean': float(np.mean(scores)) if scores else 0.0,
            'score_std': float(np.std(scores)) if scores else 0.0,
            'score_min': float(np.min(scores)) if scores else 0.0,
            'score_max': float(np.max(scores)) if scores else 0.0,
            'threshold': self.threshold
        }
    
    def __repr__(self) -> str:
        status = "enabled" if self.enabled else "disabled"
        return f"{self.name}(threshold={self.threshold:.2f}, {status})"


class QualityThresholdRejection(BaseRejectionAlgorithm):
    """
    Simple quality threshold-based rejection.
    
    Rejects windows below a quality metric threshold.
    """
    
    def __init__(self, 
                 metric: str = 'overall',
                 threshold: float = 0.5,
                 name: str = "QualityThreshold"):
        """
        Initialize quality threshold rejection.
        
        Args:
            metric: Quality metric to use
            threshold: Minimum acceptable quality
            name: Algorithm name
        """
        super().__init__(name, threshold)
        self.metric = metric
    
    def evaluate_window(self, window: Window) -> RejectionResult:
        """Evaluate window based on quality metric."""
        score = window.get_quality_score(self.metric)
        
        if score is None:
            return RejectionResult(
                should_reject=False,
                reason=f"Metric '{self.metric}' not available",
                score=0.5,
                metadata={'metric': self.metric}
            )
        
        # Invert score (high quality = low rejection score)
        rejection_score = 1.0 - score
        should_reject = score < self.threshold
        
        return RejectionResult(
            should_reject=should_reject,
            reason=f"{self.metric} = {score:.3f} < {self.threshold:.3f}" if should_reject else "Quality OK",
            score=rejection_score,
            metadata={
                'metric': self.metric,
                'quality_score': score,
                'threshold': self.threshold
            }
        )


class StatisticalOutlierRejection(BaseRejectionAlgorithm):
    """
    Statistical outlier rejection using IQR or Z-score method.
    
    Rejects windows that are statistical outliers based on quality metrics.
    """
    
    def __init__(self,
                 metric: str = 'overall',
                 method: str = 'iqr',
                 threshold: float = 1.5,
                 name: str = "StatisticalOutlier"):
        """
        Initialize statistical outlier rejection.
        
        Args:
            metric: Quality metric to use
            method: 'iqr' (Interquartile Range) or 'zscore'
            threshold: IQR multiplier or Z-score threshold
            name: Algorithm name
        """
        super().__init__(name, threshold)
        self.metric = metric
        self.method = method
        self._stats_computed = False
        self._lower_bound = None
        self._upper_bound = None
    
    def evaluate_collection(self, collection: WindowCollection) -> List[RejectionResult]:
        """Evaluate collection with statistical outlier detection."""
        # Get all quality scores
        scores = []
        for window in collection.windows:
            score = window.get_quality_score(self.metric)
            if score is not None:
                scores.append(score)
        
        if not scores:
            return [RejectionResult(False, "No scores", 0.0, {}) 
                    for _ in collection.windows]
        
        scores_array = np.array(scores)
        
        # Compute bounds
        if self.method == 'iqr':
            q1 = np.percentile(scores_array, 25)
            q3 = np.percentile(scores_array, 75)
            iqr = q3 - q1
            self._lower_bound = q1 - self.threshold * iqr
            self._upper_bound = q3 + self.threshold * iqr
        elif self.method == 'zscore':
            mean = np.mean(scores_array)
            std = np.std(scores_array)
            self._lower_bound = mean - self.threshold * std
            self._upper_bound = mean + self.threshold * std
        else:
            raise ValueError(f"Unknown method: {self.method}")
        
        self._stats_computed = True
        
        # Evaluate each window
        results = []
        for window in collection.windows:
            result = self.evaluate_window(window)
            results.append(result)
        
        return results
    
    def evaluate_window(self, window: Window) -> RejectionResult:
        """Evaluate single window against computed bounds."""
        if not self._stats_computed:
            return RejectionResult(
                should_reject=False,
                reason="Statistics not computed - use evaluate_collection first",
                score=0.0,
                metadata={}
            )
        
        score = window.get_quality_score(self.metric)
        
        if score is None:
            return RejectionResult(
                should_reject=False,
                reason=f"Metric '{self.metric}' not available",
                score=0.5,
                metadata={'metric': self.metric}
            )
        
        # Check if outlier
        is_outlier = score < self._lower_bound or score > self._upper_bound
        
        # Rejection score based on distance from bounds
        if score < self._lower_bound:
            rejection_score = min(1.0, (self._lower_bound - score) / self._lower_bound)
            reason = f"Low outlier: {score:.3f} < {self._lower_bound:.3f}"
        elif score > self._upper_bound:
            rejection_score = min(1.0, (score - self._upper_bound) / (1.0 - self._upper_bound))
            reason = f"High outlier: {score:.3f} > {self._upper_bound:.3f}"
        else:
            rejection_score = 0.0
            reason = "Within normal range"
        
        return RejectionResult(
            should_reject=is_outlier,
            reason=reason,
            score=rejection_score,
            metadata={
                'metric': self.metric,
                'quality_score': score,
                'lower_bound': self._lower_bound,
                'upper_bound': self._upper_bound,
                'method': self.method
            }
        )
