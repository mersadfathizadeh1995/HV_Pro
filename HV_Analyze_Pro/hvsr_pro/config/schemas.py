"""
Validation Schemas
===================

Input validation for HVSR Pro configuration.
"""

from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass


@dataclass
class ValidationError:
    """Validation error details."""
    field: str
    message: str
    value: Any


def validate_range(value: float, min_val: float, max_val: float, field_name: str) -> Optional[ValidationError]:
    """Validate a value is within range."""
    if value < min_val or value > max_val:
        return ValidationError(
            field=field_name,
            message=f"Value must be between {min_val} and {max_val}",
            value=value
        )
    return None


def validate_positive(value: float, field_name: str) -> Optional[ValidationError]:
    """Validate a value is positive."""
    if value <= 0:
        return ValidationError(
            field=field_name,
            message="Value must be positive",
            value=value
        )
    return None


def validate_choice(value: str, choices: List[str], field_name: str) -> Optional[ValidationError]:
    """Validate value is one of the allowed choices."""
    if value not in choices:
        return ValidationError(
            field=field_name,
            message=f"Value must be one of: {', '.join(choices)}",
            value=value
        )
    return None


def validate_processing_params(params: Dict[str, Any]) -> List[ValidationError]:
    """
    Validate processing parameters.
    
    Args:
        params: Dictionary of processing parameters
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Smoothing bandwidth
    if 'smoothing_bandwidth' in params:
        err = validate_range(params['smoothing_bandwidth'], 1.0, 200.0, 'smoothing_bandwidth')
        if err:
            errors.append(err)
    
    # Frequency range
    if 'f_min' in params:
        err = validate_positive(params['f_min'], 'f_min')
        if err:
            errors.append(err)
    
    if 'f_max' in params:
        err = validate_positive(params['f_max'], 'f_max')
        if err:
            errors.append(err)
    
    if 'f_min' in params and 'f_max' in params:
        if params['f_min'] >= params['f_max']:
            errors.append(ValidationError(
                field='f_min',
                message="f_min must be less than f_max",
                value=params['f_min']
            ))
    
    # Number of frequencies
    if 'n_frequencies' in params:
        if not isinstance(params['n_frequencies'], int) or params['n_frequencies'] < 10:
            errors.append(ValidationError(
                field='n_frequencies',
                message="Must be an integer >= 10",
                value=params['n_frequencies']
            ))
    
    # Horizontal method
    if 'horizontal_method' in params:
        err = validate_choice(
            params['horizontal_method'],
            ['geometric_mean', 'arithmetic_mean', 'quadratic', 'maximum'],
            'horizontal_method'
        )
        if err:
            errors.append(err)
    
    # Taper
    if 'taper' in params and params['taper']:
        err = validate_choice(
            params['taper'],
            ['hann', 'hamming', 'blackman', 'tukey'],
            'taper'
        )
        if err:
            errors.append(err)
    
    return errors


def validate_window_params(params: Dict[str, Any]) -> List[ValidationError]:
    """
    Validate window parameters.
    
    Args:
        params: Dictionary of window parameters
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Window length
    if 'window_length' in params:
        err = validate_range(params['window_length'], 1.0, 600.0, 'window_length')
        if err:
            errors.append(err)
    
    # Overlap
    if 'overlap' in params:
        err = validate_range(params['overlap'], 0.0, 0.99, 'overlap')
        if err:
            errors.append(err)
    
    # Taper type
    if 'taper_type' in params:
        err = validate_choice(
            params['taper_type'],
            ['tukey', 'hann', 'hamming', 'blackman', 'none'],
            'taper_type'
        )
        if err:
            errors.append(err)
    
    return errors


def validate_qc_params(params: Dict[str, Any]) -> List[ValidationError]:
    """
    Validate QC parameters.
    
    Args:
        params: Dictionary of QC parameters
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Preset
    if 'preset' in params:
        err = validate_choice(
            params['preset'],
            ['conservative', 'balanced', 'aggressive', 'sesame', 'publication', 'ml', 'custom'],
            'preset'
        )
        if err:
            errors.append(err)
    
    # Cox FDWRA n
    if 'cox_n' in params:
        err = validate_range(params['cox_n'], 0.5, 5.0, 'cox_n')
        if err:
            errors.append(err)
    
    # Cox max iterations
    if 'cox_max_iterations' in params:
        if not isinstance(params['cox_max_iterations'], int) or params['cox_max_iterations'] < 1:
            errors.append(ValidationError(
                field='cox_max_iterations',
                message="Must be a positive integer",
                value=params['cox_max_iterations']
            ))
    
    # Quality threshold
    if 'quality_threshold' in params:
        err = validate_range(params['quality_threshold'], 0.0, 1.0, 'quality_threshold')
        if err:
            errors.append(err)
    
    return errors


def validate_settings(settings: Dict[str, Any]) -> Dict[str, List[ValidationError]]:
    """
    Validate complete settings dictionary.
    
    Args:
        settings: Complete settings dictionary
        
    Returns:
        Dictionary mapping section names to error lists
    """
    all_errors = {}
    
    if 'processing' in settings:
        errors = validate_processing_params(settings['processing'])
        if errors:
            all_errors['processing'] = errors
    
    if 'window' in settings:
        errors = validate_window_params(settings['window'])
        if errors:
            all_errors['window'] = errors
    
    if 'qc' in settings:
        errors = validate_qc_params(settings['qc'])
        if errors:
            all_errors['qc'] = errors
    
    return all_errors


def is_valid_settings(settings: Dict[str, Any]) -> bool:
    """
    Check if settings are valid.
    
    Args:
        settings: Complete settings dictionary
        
    Returns:
        True if valid, False otherwise
    """
    errors = validate_settings(settings)
    return len(errors) == 0

