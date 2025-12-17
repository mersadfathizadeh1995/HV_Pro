"""
Rejection Pipeline Presets
===========================

Pre-configured QC pipelines for common use cases.

Presets:
    - conservative: Only obvious problems (lenient)
    - balanced: Moderate rejection (recommended)
    - aggressive: Strict quality control
    - sesame: SESAME-compliant with Cox FDWRA
    - publication: Publication-quality 4-condition workflow
    - ml: Machine learning-based (requires sklearn)
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Preset configurations
PRESET_CONFIGS = {
    'conservative': {
        'description': 'Only reject clear problems (lenient thresholds)',
        'algorithms': [
            {'type': 'AmplitudeRejection', 'params': {}},
            {'type': 'QualityThresholdRejection', 'params': {'threshold': 0.2}},
        ],
        'post_hvsr': []
    },
    'balanced': {
        'description': 'Balanced approach (moderate quality control, recommended)',
        'algorithms': [
            {'type': 'AmplitudeRejection', 'params': {}},
        ],
        'post_hvsr': []
    },
    'aggressive': {
        'description': 'Thorough quality control with multiple checks',
        'algorithms': [
            {'type': 'AmplitudeRejection', 'params': {}},
            {'type': 'QualityThresholdRejection', 'params': {'threshold': 0.35}},  # Reduced from 0.5
            {'type': 'STALTARejection', 'params': {
                'sta_length': 1.0,
                'lta_length': 30.0,
                'min_ratio': 0.08,   # Reduced from 0.15 (allows quieter windows)
                'max_ratio': 3.5     # Increased from 2.5 (allows more transients)
            }},
            {'type': 'FrequencyDomainRejection', 'params': {'spike_threshold': 4.0}},  # Increased from 3.0
            {'type': 'StatisticalOutlierRejection', 'params': {'method': 'iqr', 'threshold': 2.5}},  # Increased from 2.0
        ],
        'post_hvsr': []
    },
    'sesame': {
        'description': 'SESAME-compliant with Cox et al. (2020) FDWRA',
        'algorithms': [
            {'type': 'AmplitudeRejection', 'params': {}},
            {'type': 'QualityThresholdRejection', 'params': {'threshold': 0.3}},
        ],
        'post_hvsr': [],
        'use_cox_fdwra': True
    },
    'publication': {
        'description': 'Publication-quality 4-condition rejection workflow',
        'algorithms': [
            {'type': 'AmplitudeRejection', 'params': {}},
        ],
        'post_hvsr': [
            {'type': 'HVSRAmplitudeRejection', 'params': {'min_amplitude': 1.0}},
            {'type': 'FlatPeakRejection', 'params': {'flatness_threshold': 0.15}},
        ],
        'use_cox_fdwra': True
    },
    'ml': {
        'description': 'Machine learning-based anomaly detection (requires sklearn)',
        'algorithms': [
            {'type': 'AmplitudeRejection', 'params': {}},
            {'type': 'IsolationForestRejection', 'params': {'contamination': 0.1}},
        ],
        'post_hvsr': [],
        'requires_sklearn': True
    }
}


def get_available_presets() -> List[str]:
    """
    Get list of available preset names.
    
    Returns:
        List of preset names
    """
    return list(PRESET_CONFIGS.keys())


def get_preset_description(preset: str) -> str:
    """
    Get description for a preset.
    
    Args:
        preset: Preset name
        
    Returns:
        Description string
    """
    if preset not in PRESET_CONFIGS:
        raise ValueError(f"Unknown preset: {preset}. Available: {get_available_presets()}")
    return PRESET_CONFIGS[preset]['description']


def get_preset_config(preset: str) -> Dict[str, Any]:
    """
    Get full configuration for a preset.
    
    Args:
        preset: Preset name
        
    Returns:
        Configuration dictionary
    """
    if preset not in PRESET_CONFIGS:
        raise ValueError(f"Unknown preset: {preset}. Available: {get_available_presets()}")
    return PRESET_CONFIGS[preset].copy()


def create_preset_pipeline(preset: str, engine=None):
    """
    Create a rejection pipeline from a preset.
    
    Args:
        preset: Preset name (conservative, balanced, aggressive, sesame, publication, ml)
        engine: Optional RejectionEngine instance to configure (creates new if None)
        
    Returns:
        Configured RejectionEngine instance
    """
    from hvsr_pro.processing.rejection.engine import RejectionEngine
    from hvsr_pro.processing.rejection.algorithms import (
        QualityThresholdRejection,
        StatisticalOutlierRejection,
        AmplitudeRejection,
        STALTARejection,
        FrequencyDomainRejection,
        HVSRAmplitudeRejection,
        FlatPeakRejection,
    )
    
    if preset not in PRESET_CONFIGS:
        raise ValueError(f"Unknown preset: {preset}. Available: {get_available_presets()}")
    
    config = PRESET_CONFIGS[preset]
    
    # Check sklearn requirement
    if config.get('requires_sklearn', False):
        try:
            from hvsr_pro.processing.rejection.algorithms.ml import IsolationForestRejection
        except ImportError:
            raise ImportError("ML preset requires scikit-learn. Install with: pip install scikit-learn")
    
    # Create or clear engine
    if engine is None:
        engine = RejectionEngine(name=f"{preset.title()}Pipeline")
    else:
        engine.clear_algorithms()
    
    # Algorithm type mapping
    algorithm_map = {
        'AmplitudeRejection': AmplitudeRejection,
        'QualityThresholdRejection': QualityThresholdRejection,
        'StatisticalOutlierRejection': StatisticalOutlierRejection,
        'STALTARejection': STALTARejection,
        'FrequencyDomainRejection': FrequencyDomainRejection,
        'HVSRAmplitudeRejection': HVSRAmplitudeRejection,
        'FlatPeakRejection': FlatPeakRejection,
    }
    
    # Add ML algorithms if available
    try:
        from hvsr_pro.processing.rejection.algorithms.ml import IsolationForestRejection
        algorithm_map['IsolationForestRejection'] = IsolationForestRejection
    except ImportError:
        pass
    
    # Add pre-HVSR algorithms
    for algo_config in config['algorithms']:
        algo_type = algo_config['type']
        algo_params = algo_config['params']
        
        if algo_type in algorithm_map:
            algo = algorithm_map[algo_type](**algo_params)
            engine.add_algorithm(algo)
        else:
            logger.warning(f"Unknown algorithm type: {algo_type}")
    
    # Store post-HVSR algorithms
    engine.post_hvsr_algorithms = []
    for algo_config in config.get('post_hvsr', []):
        algo_type = algo_config['type']
        algo_params = algo_config['params']
        
        if algo_type in algorithm_map:
            algo = algorithm_map[algo_type](**algo_params)
            engine.post_hvsr_algorithms.append(algo)
    
    # Store Cox FDWRA flag
    engine.use_cox_fdwra = config.get('use_cox_fdwra', False)
    
    logger.info(f"Created {preset} rejection pipeline with {len(engine.algorithms)} pre-HVSR algorithms")
    if engine.post_hvsr_algorithms:
        logger.info(f"  Post-HVSR algorithms: {len(engine.post_hvsr_algorithms)}")
    if engine.use_cox_fdwra:
        logger.info("  Cox FDWRA will be applied after HVSR computation")
    
    return engine

