"""
Statistical Rejection Algorithms
=================================

Quality threshold and statistical outlier detection methods.
"""

import numpy as np
from typing import Dict, Any

from hvsr_pro.processing.rejection.base import BaseRejectionAlgorithm, RejectionResult
from hvsr_pro.processing.windows import Window, WindowCollection


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
    
    def evaluate_collection(self, collection: WindowCollection):
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

