"""
Rejection Pipeline Presets
===========================

Pre-configured QC pipelines for HVSR analysis.

Presets:
    - sesame: SESAME-compliant with FDWRA (default, matches hvsrpy)
    - custom: User-defined settings (persisted across sessions)

Legacy presets (deprecated):
    - conservative, balanced, aggressive, publication, ml
    These are kept for backward compatibility but SESAME is recommended.
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# SESAME Standard configuration (matches hvsrpy defaults)
SESAME_CONFIG = {
    'description': 'SESAME standard with Peak Frequency Consistency (FDWRA)',
    'algorithms': [
        {'type': 'AmplitudeRejection', 'params': {}},
        {'type': 'STALTARejection', 'params': {
            'sta_length': 1.0,
            'lta_length': 30.0,
            'min_ratio': 0.2,
            'max_ratio': 2.5
        }},
    ],
    'post_hvsr': [],
    'use_cox_fdwra': True,
    'fdwra_params': {
        'n': 2.0,
        'max_iterations': 50,
        'min_iterations': 1,
        'distribution_fn': 'lognormal',
        'distribution_mc': 'lognormal'
    }
}

# Preset configurations (SESAME is primary, others kept for backward compatibility)
PRESET_CONFIGS = {
    'sesame': SESAME_CONFIG,
    # Legacy presets (deprecated - use SESAME or custom instead)
    'conservative': {
        'description': '[Deprecated] Only reject clear problems (use SESAME instead)',
        'algorithms': [
            {'type': 'AmplitudeRejection', 'params': {}},
        ],
        'post_hvsr': []
    },
    'balanced': {
        'description': '[Deprecated] Balanced approach (use SESAME instead)',
        'algorithms': [
            {'type': 'AmplitudeRejection', 'params': {}},
        ],
        'post_hvsr': []
    },
    'aggressive': {
        'description': '[Deprecated] Thorough quality control (use custom settings instead)',
        'algorithms': [
            {'type': 'AmplitudeRejection', 'params': {}},
            {'type': 'STALTARejection', 'params': {
                'sta_length': 1.0,
                'lta_length': 30.0,
                'min_ratio': 0.08,
                'max_ratio': 3.5
            }},
            {'type': 'FrequencyDomainRejection', 'params': {'spike_threshold': 4.0}},
            {'type': 'StatisticalOutlierRejection', 'params': {'method': 'iqr', 'threshold': 2.5}},
        ],
        'post_hvsr': []
    },
    'publication': {
        'description': '[Deprecated] Publication-quality (use SESAME with custom settings)',
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
        'description': '[Deprecated] Machine learning-based (requires sklearn)',
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

