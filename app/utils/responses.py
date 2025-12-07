"""
Standard API Response Helpers
"""
from flask import jsonify
from typing import Any, Optional

def success_response(data: Any = None, message: str = "", status: int = 200):
    """
    Create a standardized success response
    
    Args:
        data: Response data (dict, list, etc.)
        message: Success message
        status: HTTP status code
    
    Returns:
        Flask JSON response tuple
    """
    response = {
        'success': True
    }
    
    if message:
        response['message'] = message
    
    if data is not None:
        response['data'] = data
    
    return jsonify(response), status

def error_response(error: str, status: int = 400, details: Optional[dict] = None):
    """
    Create a standardized error response
    
    Args:
        error: Error message
        status: HTTP status code
        details: Additional error details
    
    Returns:
        Flask JSON response tuple
    """
    response = {
        'success': False,
        'error': error
    }
    
    if details:
        response['details'] = details
    
    return jsonify(response), status

def validation_error(errors: dict):
    """
    Create a validation error response
    
    Args:
        errors: Dictionary of field-level validation errors
    
    Returns:
        Flask JSON response tuple
    """
    return jsonify({
        'success': False,
        'error': 'Validation failed',
        'validation_errors': errors
    }), 400