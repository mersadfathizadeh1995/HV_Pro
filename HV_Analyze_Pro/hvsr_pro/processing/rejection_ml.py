"""
Machine Learning-Based Rejection for HVSR Pro
==============================================

Isolation Forest and other ML-based anomaly detection methods.
"""

import numpy as np
from typing import Dict, Any, List, Optional

try:
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

from hvsr_pro.processing.rejection_algorithms import BaseRejectionAlgorithm, RejectionResult
from hvsr_pro.processing.window_structures import Window, WindowCollection


class IsolationForestRejection(BaseRejectionAlgorithm):
    """
    Machine learning-based rejection using Isolation Forest.
    
    Uses unsupervised anomaly detection on quality metrics to identify
    outlier windows. Works well for detecting complex patterns.
    
    Reference: Liu et al. (2008) - Isolation Forest algorithm
    """
    
    def __init__(self,
                 contamination: float = 0.1,
                 metrics: Optional[List[str]] = None,
                 name: str = "IsolationForest"):
        """
        Initialize Isolation Forest rejection.
        
        Args:
            contamination: Expected proportion of outliers (0.0-0.5)
            metrics: List of quality metrics to use (None = all)
            name: Algorithm name
        """
        if not HAS_SKLEARN:
            raise ImportError(
                "scikit-learn is required for IsolationForest. "
                "Install it with: pip install scikit-learn"
            )
        
        super().__init__(name, threshold=0.5)
        self.contamination = contamination
        self.metrics = metrics or ['snr', 'stationarity', 'energy_consistency', 
                                   'peak_to_mean', 'zero_crossing_rate']
        
        self.model = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100
        )
        self.scaler = StandardScaler()
        self._fitted = False
    
    def evaluate_collection(self, collection: WindowCollection) -> List[RejectionResult]:
        """Train model and evaluate entire collection."""
        # Extract features from all windows
        features = self._extract_features(collection)
        
        if features.shape[0] == 0:
            return [RejectionResult(False, "No features", 0.0, {}) 
                    for _ in collection.windows]
        
        # Normalize features
        features_scaled = self.scaler.fit_transform(features)
        
        # Train model
        self.model.fit(features_scaled)
        self._fitted = True
        
        # Predict anomalies (-1 = outlier, 1 = inlier)
        predictions = self.model.predict(features_scaled)
        
        # Get anomaly scores (more negative = more anomalous)
        scores = self.model.score_samples(features_scaled)
        
        # Normalize scores to 0-1 range (higher = more anomalous)
        min_score = np.min(scores)
        max_score = np.max(scores)
        if max_score > min_score:
            normalized_scores = 1.0 - (scores - min_score) / (max_score - min_score)
        else:
            normalized_scores = np.zeros_like(scores)
        
        # Create results
        results = []
        for i, window in enumerate(collection.windows):
            is_outlier = predictions[i] == -1
            anomaly_score = float(normalized_scores[i])
            
            results.append(RejectionResult(
                should_reject=is_outlier,
                reason=f"Anomaly score: {anomaly_score:.3f}" if is_outlier else "Normal",
                score=anomaly_score,
                metadata={
                    'anomaly_score': float(scores[i]),
                    'normalized_score': anomaly_score,
                    'prediction': int(predictions[i]),
                    'contamination': self.contamination,
                    'features_used': self.metrics
                }
            ))
        
        return results
    
    def evaluate_window(self, window: Window) -> RejectionResult:
        """Evaluate single window (requires model to be fitted first)."""
        if not self._fitted:
            return RejectionResult(
                should_reject=False,
                reason="Model not fitted - use evaluate_collection first",
                score=0.0,
                metadata={}
            )
        
        # Extract features for this window
        features = self._extract_window_features(window)
        
        if features is None or len(features) == 0:
            return RejectionResult(
                should_reject=False,
                reason="Could not extract features",
                score=0.0,
                metadata={}
            )
        
        # Scale features
        features_scaled = self.scaler.transform(features.reshape(1, -1))
        
        # Predict
        prediction = self.model.predict(features_scaled)[0]
        score = self.model.score_samples(features_scaled)[0]
        
        is_outlier = prediction == -1
        
        return RejectionResult(
            should_reject=is_outlier,
            reason=f"Anomaly score: {score:.3f}" if is_outlier else "Normal",
            score=abs(score),
            metadata={
                'anomaly_score': float(score),
                'prediction': int(prediction)
            }
        )
    
    def _extract_features(self, collection: WindowCollection) -> np.ndarray:
        """Extract feature matrix from collection."""
        features_list = []
        
        for window in collection.windows:
            window_features = self._extract_window_features(window)
            if window_features is not None:
                features_list.append(window_features)
        
        if not features_list:
            return np.array([])
        
        return np.array(features_list)
    
    def _extract_window_features(self, window: Window) -> Optional[np.ndarray]:
        """Extract feature vector from single window."""
        features = []
        
        for metric in self.metrics:
            score = window.get_quality_score(metric)
            if score is None:
                return None
            features.append(score)
        
        # Add additional features from raw data
        try:
            # RMS for each component
            for comp_name in ['east', 'north', 'vertical']:
                comp = window.data.get_component(comp_name)
                rms = np.sqrt(np.mean(comp.data ** 2))
                features.append(rms)
            
            # Peak-to-RMS ratio
            for comp_name in ['east', 'north', 'vertical']:
                comp = window.data.get_component(comp_name)
                rms = np.sqrt(np.mean(comp.data ** 2))
                peak = np.max(np.abs(comp.data))
                features.append(peak / (rms + 1e-10))
        except Exception:
            pass  # Use metrics-only if data extraction fails
        
        return np.array(features)


class EnsembleRejection(BaseRejectionAlgorithm):
    """
    Ensemble rejection combining multiple algorithms.
    
    Aggregates decisions from multiple rejection algorithms using
    voting or weighted averaging.
    """
    
    def __init__(self,
                 algorithms: List[BaseRejectionAlgorithm],
                 voting_method: str = 'majority',
                 weights: Optional[List[float]] = None,
                 name: str = "Ensemble"):
        """
        Initialize ensemble rejection.
        
        Args:
            algorithms: List of rejection algorithms to ensemble
            voting_method: 'majority', 'unanimous', or 'weighted'
            weights: Weights for weighted voting (None = equal weights)
            name: Algorithm name
        """
        super().__init__(name, threshold=0.5)
        self.algorithms = algorithms
        self.voting_method = voting_method
        
        if weights is None:
            self.weights = [1.0 / len(algorithms)] * len(algorithms)
        else:
            if len(weights) != len(algorithms):
                raise ValueError("Number of weights must match number of algorithms")
            total = sum(weights)
            self.weights = [w / total for w in weights]
    
    def evaluate_window(self, window: Window) -> RejectionResult:
        """Evaluate window using ensemble of algorithms."""
        results = []
        for algo in self.algorithms:
            if algo.enabled:
                result = algo.evaluate_window(window)
                results.append(result)
        
        if not results:
            return RejectionResult(
                should_reject=False,
                reason="No enabled algorithms",
                score=0.0,
                metadata={}
            )
        
        # Aggregate results based on voting method
        if self.voting_method == 'majority':
            votes = sum(1 for r in results if r.should_reject)
            should_reject = votes > len(results) / 2
            score = votes / len(results)
            reason = f"{votes}/{len(results)} algorithms voted to reject"
        
        elif self.voting_method == 'unanimous':
            should_reject = all(r.should_reject for r in results)
            score = 1.0 if should_reject else 0.0
            reason = "All algorithms agree" if should_reject else "Not unanimous"
        
        elif self.voting_method == 'weighted':
            weighted_score = sum(w * r.score for w, r in zip(self.weights, results))
            should_reject = weighted_score > self.threshold
            score = weighted_score
            reason = f"Weighted score: {weighted_score:.3f}"
        
        else:
            raise ValueError(f"Unknown voting method: {self.voting_method}")
        
        # Collect reasons from algorithms that voted to reject
        reject_reasons = [r.reason for r in results if r.should_reject]
        
        return RejectionResult(
            should_reject=should_reject,
            reason=reason,
            score=score,
            metadata={
                'individual_results': [r.metadata for r in results],
                'voting_method': self.voting_method,
                'reject_reasons': reject_reasons
            }
        )
    
    def evaluate_collection(self, collection: WindowCollection) -> List[RejectionResult]:
        """Evaluate collection using ensemble."""
        # Get results from each algorithm
        all_results = []
        for algo in self.algorithms:
            if algo.enabled:
                algo_results = algo.evaluate_collection(collection)
                all_results.append(algo_results)
        
        if not all_results:
            return [RejectionResult(False, "No enabled algorithms", 0.0, {}) 
                    for _ in collection.windows]
        
        # Combine results for each window
        ensemble_results = []
        for window_idx in range(len(collection.windows)):
            window_results = [algo_results[window_idx] for algo_results in all_results]
            
            # Aggregate using voting method
            if self.voting_method == 'majority':
                votes = sum(1 for r in window_results if r.should_reject)
                should_reject = votes > len(window_results) / 2
                score = votes / len(window_results)
            elif self.voting_method == 'unanimous':
                should_reject = all(r.should_reject for r in window_results)
                score = 1.0 if should_reject else 0.0
            elif self.voting_method == 'weighted':
                score = sum(w * r.score for w, r in zip(self.weights, window_results))
                should_reject = score > self.threshold
            
            ensemble_results.append(RejectionResult(
                should_reject=should_reject,
                reason=f"Ensemble decision ({self.voting_method})",
                score=score,
                metadata={
                    'individual_scores': [r.score for r in window_results],
                    'voting_method': self.voting_method
                }
            ))
        
        return ensemble_results
