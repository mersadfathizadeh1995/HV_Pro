"""
Base Classes for Rejection Algorithms
======================================

Defines abstract base classes and interfaces for window rejection.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import numpy as np
from dataclasses import dataclass

from hvsr_pro.processing.windows import Window, WindowCollection


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
    
    Example:
        >>> class MyRejection(BaseRejectionAlgorithm):
        ...     def evaluate_window(self, window):
        ...         # Custom logic
        ...         return RejectionResult(...)
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

