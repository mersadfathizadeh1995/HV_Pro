"""
Statistical Rejection Algorithms
=================================

Quality threshold and statistical outlier detection methods.
Supports IQR, Z-score, and MAD (Median Absolute Deviation) methods.
"""

import numpy as np
from typing import Dict, Any, List

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
    Statistical outlier rejection using IQR, Z-score, or MAD methods.
    
    Rejects windows that are statistical outliers based on quality metrics.
    
    Methods:
        iqr: Interquartile Range - uses Q1 - k*IQR, Q3 + k*IQR bounds
        zscore: Z-score - uses mean +/- k*std bounds
        mad: Median Absolute Deviation - uses median +/- k*MAD bounds
    
    Metrics:
        overall: Use overall quality score (default)
        max_deviation: Use maximum deviation from collection mean
        mean_deviation: Use mean deviation from collection mean
        area: Use area under HVSR curve
    """
    
    def __init__(self,
                 metric: str = 'overall',
                 method: str = 'iqr',
                 threshold: float = 1.5,
                 name: str = "StatisticalOutlier"):
        """
        Initialize statistical outlier rejection.
        
        Args:
            metric: Quality metric to use ('overall', 'max_deviation', 'mean_deviation', 'area')
            method: Detection method ('iqr', 'zscore', 'mad')
            threshold: Multiplier for bounds (IQR multiplier, Z-score, or MAD multiplier)
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
        scores = []
        for window in collection.windows:
            score = window.get_quality_score(self.metric)
            if score is not None:
                scores.append(score)
        
        if not scores:
            return [RejectionResult(False, "No scores", 0.0, {}) 
                    for _ in collection.windows]
        
        scores_array = np.array(scores)
        
        # Compute bounds based on method
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
        elif self.method == 'mad':
            median = np.median(scores_array)
            mad = np.median(np.abs(scores_array - median))
            # Scale MAD to be consistent with std (for normal distributions)
            mad_scaled = mad * 1.4826
            self._lower_bound = median - self.threshold * mad_scaled
            self._upper_bound = median + self.threshold * mad_scaled
        else:
            raise ValueError(f"Unknown method: {self.method}. Use 'iqr', 'zscore', or 'mad'.")
        
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
        
        is_outlier = score < self._lower_bound or score > self._upper_bound
        
        if score < self._lower_bound:
            rejection_score = min(1.0, abs(self._lower_bound - score) / max(abs(self._lower_bound), 1e-10))
            reason = f"Low outlier: {score:.3f} < {self._lower_bound:.3f}"
        elif score > self._upper_bound:
            rejection_score = min(1.0, abs(score - self._upper_bound) / max(abs(self._upper_bound), 1e-10))
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
