"""
Quality Metrics Calculator for HVSR Pro
========================================

Calculates various quality metrics for seismic windows.
"""

import numpy as np
from typing import Dict, Any
from scipy import stats, signal as scipy_signal

from hvsr_pro.processing.window_structures import Window


class WindowQualityCalculator:
    """
    Calculator for window quality metrics.
    
    Metrics calculated:
    - Signal-to-Noise Ratio (SNR)
    - Stationarity measure
    - Energy consistency
    - Peak-to-mean ratio
    - Zero-crossing rate
    - Overall quality score
    """
    
    def __init__(self):
        """Initialize quality calculator."""
        self.metrics = [
            'snr',
            'stationarity',
            'energy_consistency',
            'peak_to_mean',
            'zero_crossing_rate',
            'overall'
        ]
    
    def calculate_all(self, window: Window) -> Dict[str, float]:
        """
        Calculate all quality metrics for a window.
        
        Args:
            window: Window object
            
        Returns:
            Dictionary of metric names and values
        """
        metrics = {}
        
        # Calculate individual metrics
        metrics['snr'] = self.calculate_snr(window)
        metrics['stationarity'] = self.calculate_stationarity(window)
        metrics['energy_consistency'] = self.calculate_energy_consistency(window)
        metrics['peak_to_mean'] = self.calculate_peak_to_mean(window)
        metrics['zero_crossing_rate'] = self.calculate_zero_crossing_rate(window)
        
        # Calculate overall score (weighted average)
        metrics['overall'] = self._calculate_overall_score(metrics)
        
        return metrics
    
    def calculate_snr(self, window: Window) -> float:
        """
        Calculate Signal-to-Noise Ratio.
        
        Uses RMS amplitude as signal measure.
        
        Args:
            window: Window object
            
        Returns:
            SNR value (higher is better)
        """
        # Calculate RMS for each component
        east_rms = np.sqrt(np.mean(window.data.east.data ** 2))
        north_rms = np.sqrt(np.mean(window.data.north.data ** 2))
        vertical_rms = np.sqrt(np.mean(window.data.vertical.data ** 2))
        
        # Average RMS across components
        avg_rms = (east_rms + north_rms + vertical_rms) / 3.0
        
        # Estimate noise from high-frequency content
        # Use last 10% of window as noise estimate
        n_samples = window.n_samples
        noise_start = int(0.9 * n_samples)
        
        east_noise = np.std(window.data.east.data[noise_start:])
        north_noise = np.std(window.data.north.data[noise_start:])
        vertical_noise = np.std(window.data.vertical.data[noise_start:])
        
        avg_noise = (east_noise + north_noise + vertical_noise) / 3.0
        
        # Calculate SNR (avoid division by zero)
        if avg_noise > 0:
            snr = avg_rms / avg_noise
        else:
            snr = 100.0  # Very high SNR if no noise
        
        # Normalize to 0-1 range (logarithmic scale)
        snr_normalized = np.tanh(np.log10(snr + 1) / 2)
        
        return float(snr_normalized)
    
    def calculate_stationarity(self, window: Window) -> float:
        """
        Calculate stationarity measure using variance of local statistics.
        
        A stationary signal has consistent statistical properties.
        
        Args:
            window: Window object
            
        Returns:
            Stationarity score (0-1, higher is more stationary)
        """
        # Divide window into sub-windows
        n_subwindows = 10
        n_samples = window.n_samples
        subwindow_size = n_samples // n_subwindows
        
        # Calculate RMS for each sub-window
        east_rms_values = []
        north_rms_values = []
        vertical_rms_values = []
        
        for i in range(n_subwindows):
            start = i * subwindow_size
            end = start + subwindow_size
            
            if end > n_samples:
                break
            
            east_rms_values.append(np.sqrt(np.mean(window.data.east.data[start:end] ** 2)))
            north_rms_values.append(np.sqrt(np.mean(window.data.north.data[start:end] ** 2)))
            vertical_rms_values.append(np.sqrt(np.mean(window.data.vertical.data[start:end] ** 2)))
        
        # Calculate coefficient of variation (CV) for each component
        def cv(values):
            mean_val = np.mean(values)
            if mean_val > 0:
                return np.std(values) / mean_val
            return 0.0
        
        cv_east = cv(east_rms_values)
        cv_north = cv(north_rms_values)
        cv_vertical = cv(vertical_rms_values)
        
        # Average CV
        avg_cv = (cv_east + cv_north + cv_vertical) / 3.0
        
        # Convert to stationarity score (lower CV = higher stationarity)
        stationarity = np.exp(-avg_cv)
        
        return float(stationarity)
    
    def calculate_energy_consistency(self, window: Window) -> float:
        """
        Calculate energy consistency across components.
        
        Good windows have balanced energy across horizontal components.
        
        Args:
            window: Window object
            
        Returns:
            Consistency score (0-1, higher is better)
        """
        # Calculate energy for each horizontal component
        east_energy = np.sum(window.data.east.data ** 2)
        north_energy = np.sum(window.data.north.data ** 2)
        
        # Calculate ratio (should be close to 1.0 for good consistency)
        if north_energy > 0:
            ratio = east_energy / north_energy
        else:
            return 0.0
        
        # Normalize ratio (1.0 is perfect, deviations decrease score)
        consistency = np.exp(-abs(np.log(ratio)))
        
        return float(consistency)
    
    def calculate_peak_to_mean(self, window: Window) -> float:
        """
        Calculate peak-to-mean ratio.
        
        High ratios may indicate spikes or transients.
        
        Args:
            window: Window object
            
        Returns:
            Normalized score (0-1, lower ratio is better)
        """
        # Calculate for each component
        def peak_mean_ratio(data):
            peak = np.max(np.abs(data))
            mean = np.mean(np.abs(data))
            if mean > 0:
                return peak / mean
            return 0.0
        
        east_pm = peak_mean_ratio(window.data.east.data)
        north_pm = peak_mean_ratio(window.data.north.data)
        vertical_pm = peak_mean_ratio(window.data.vertical.data)
        
        avg_pm = (east_pm + north_pm + vertical_pm) / 3.0
        
        # Normalize (typical values 2-10, higher is worse)
        # Good windows have peak/mean around 3-5
        score = np.exp(-(avg_pm - 4.0) ** 2 / 16.0)
        
        return float(score)
    
    def calculate_zero_crossing_rate(self, window: Window) -> float:
        """
        Calculate zero-crossing rate.
        
        Measures frequency content and signal complexity.
        
        Args:
            window: Window object
            
        Returns:
            Normalized score (0-1)
        """
        def zcr(data):
            signs = np.sign(data)
            crossings = np.sum(np.abs(np.diff(signs))) / 2
            rate = crossings / len(data)
            return rate
        
        east_zcr = zcr(window.data.east.data)
        north_zcr = zcr(window.data.north.data)
        vertical_zcr = zcr(window.data.vertical.data)
        
        avg_zcr = (east_zcr + north_zcr + vertical_zcr) / 3.0
        
        # Normalize (typical ambient noise: 0.1-0.3)
        # Very low or very high ZCR can indicate problems
        optimal_zcr = 0.2
        score = np.exp(-(avg_zcr - optimal_zcr) ** 2 / 0.04)
        
        return float(score)
    
    def _calculate_overall_score(self, metrics: Dict[str, float]) -> float:
        """
        Calculate overall quality score from individual metrics.
        
        Args:
            metrics: Dictionary of individual metric scores
            
        Returns:
            Overall quality score (0-1)
        """
        # Weights for each metric
        weights = {
            'snr': 0.3,
            'stationarity': 0.3,
            'energy_consistency': 0.2,
            'peak_to_mean': 0.1,
            'zero_crossing_rate': 0.1
        }
        
        # Weighted sum
        score = 0.0
        for metric, weight in weights.items():
            if metric in metrics:
                score += weight * metrics[metric]
        
        return float(score)
    
    def calculate_sta_lta_metric(self, 
                                 window: Window,
                                 sta_seconds: float = 1.0,
                                 lta_seconds: float = 10.0) -> Dict[str, float]:
        """
        Calculate STA/LTA (Short-Term Average / Long-Term Average) metric.
        
        Used for transient detection.
        
        Args:
            window: Window object
            sta_seconds: Short-term window length in seconds
            lta_seconds: Long-term window length in seconds
            
        Returns:
            Dictionary with STA/LTA ratios for each component
        """
        sampling_rate = window.data.sampling_rate
        sta_samples = int(sta_seconds * sampling_rate)
        lta_samples = int(lta_seconds * sampling_rate)
        
        def compute_sta_lta(data):
            # Envelope of signal
            envelope = np.abs(data)
            
            # Calculate STA and LTA
            sta = np.convolve(envelope, np.ones(sta_samples) / sta_samples, mode='same')
            lta = np.convolve(envelope, np.ones(lta_samples) / lta_samples, mode='same')
            
            # Calculate ratio (avoid division by zero)
            ratio = np.divide(sta, lta, out=np.zeros_like(sta), where=lta != 0)
            
            # Return statistics
            return {
                'max': float(np.max(ratio)),
                'mean': float(np.mean(ratio)),
                'std': float(np.std(ratio))
            }
        
        return {
            'east': compute_sta_lta(window.data.east.data),
            'north': compute_sta_lta(window.data.north.data),
            'vertical': compute_sta_lta(window.data.vertical.data)
        }
    
    def is_quality_acceptable(self, 
                             metrics: Dict[str, float],
                             thresholds: Dict[str, float] = None) -> bool:
        """
        Check if window quality meets acceptance criteria.
        
        Args:
            metrics: Quality metrics dictionary
            thresholds: Minimum acceptable values for each metric
            
        Returns:
            True if quality is acceptable
        """
        if thresholds is None:
            # Default thresholds
            thresholds = {
                'overall': 0.5,
                'snr': 0.3,
                'stationarity': 0.4
            }
        
        for metric, threshold in thresholds.items():
            if metric in metrics:
                if metrics[metric] < threshold:
                    return False
        
        return True
