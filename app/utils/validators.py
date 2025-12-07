"""
Input Validation Utilities
"""
import re
from email_validator import validate_email as email_validate, EmailNotValidError
from typing import Dict, List, Any

def validate_email(email: str) -> tuple[bool, str]:
    """
    Validate email format
    
    Args:
        email: Email string to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email:
        return False, "Email is required"
    
    try:
        email_validate(email)
        return True, ""
    except EmailNotValidError as e:
        return False, str(e)

def validate_password(password: str) -> tuple[bool, str]:
    """
    Validate password strength
    
    Requirements:
    - At least 8 characters
    - Contains at least one letter
    - Contains at least one number
    
    Args:
        password: Password string to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not password:
        return False, "Password is required"
    
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[a-zA-Z]', password):
        return False, "Password must contain at least one letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    return True, ""

def validate_name(name: str) -> tuple[bool, str]:
    """
    Validate name
    
    Args:
        name: Name string to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not name:
        return False, "Name is required"
    
    if len(name.strip()) < 2:
        return False, "Name must be at least 2 characters long"
    
    if len(name) > 100:
        return False, "Name must not exceed 100 characters"
    
    return True, ""

def validate_role(role: str) -> tuple[bool, str]:
    """
    Validate user role
    
    Args:
        role: Role string to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    valid_roles = ['attendee', 'organizer']
    
    if not role:
        return False, "Role is required"
    
    if role not in valid_roles:
        return False, f"Role must be one of: {', '.join(valid_roles)}"
    
    return True, ""

def validate_uuid(uuid_string: str) -> tuple[bool, str]:
    """
    Validate UUID format
    
    Args:
        uuid_string: UUID string to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not uuid_string:
        return False, "UUID is required"
    
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )
    
    if not uuid_pattern.match(uuid_string):
        return False, "Invalid UUID format"
    
    return True, ""

def validate_phone(phone: str) -> tuple[bool, str]:
    """
    Validate phone number format
    
    Args:
        phone: Phone number string to validate
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not phone:
        return False, "Phone number is required"
    
    # Remove common formatting characters
    cleaned_phone = re.sub(r'[\s\-\(\)\+]', '', phone)
    
    # Check if it contains only digits (after removing formatting)
    if not cleaned_phone.isdigit():
        return False, "Phone number must contain only digits"
    
    # Check length (typically 10-15 digits for international numbers)
    if len(cleaned_phone) < 10 or len(cleaned_phone) > 15:
        return False, "Phone number must be between 10 and 15 digits"
    
    return True, ""

def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> Dict[str, str]:
    """
    Validate that required fields are present in data
    
    Args:
        data: Dictionary of data to validate
        required_fields: List of required field names
    
    Returns:
        Dictionary of validation errors (empty if valid)
    """
    errors = {}
    
    for field in required_fields:
        if field not in data or data[field] is None or str(data[field]).strip() == '':
            errors[field] = f"{field.replace('_', ' ').title()} is required"
    
    return errors

def validate_event_data(data: Dict[str, Any]) -> tuple[bool, Dict[str, str]]:
    """
    Validate event data
    
    Args:
        data: Dictionary containing event data
    
    Returns:
        Tuple of (is_valid, errors_dict)
    """
    errors = {}
    
    # Validate required fields - updated to match API expectations
    required_fields = ['title', 'description', 'datetime', 'location']
    
    # Check for required fields (allow empty string check only for string fields)
    for field in required_fields:
        if field not in data or data[field] is None:
            errors[field] = f"{field.replace('_', ' ').title()} is required"
        elif isinstance(data[field], str) and data[field].strip() == '':
            errors[field] = f"{field.replace('_', ' ').title()} is required"
    
    # Validate title length
    if 'title' in data and data['title']:
        if len(data['title']) < 3:
            errors['title'] = "Title must be at least 3 characters long"
        elif len(data['title']) > 200:
            errors['title'] = "Title must not exceed 200 characters"
    
    # Validate description length
    if 'description' in data and data['description']:
        if len(data['description']) < 10:
            errors['description'] = "Description must be at least 10 characters long"
        elif len(data['description']) > 5000:
            errors['description'] = "Description must not exceed 5000 characters"
    
    # Validate location
    if 'location' in data and data['location']:
        if len(data['location']) < 3:
            errors['location'] = "Location must be at least 3 characters long"
        elif len(data['location']) > 500:
            errors['location'] = "Location must not exceed 500 characters"
    
    # Validate capacity if provided
    if 'capacity' in data and data['capacity'] is not None:
        try:
            capacity = int(data['capacity'])
            if capacity < 1:
                errors['capacity'] = "Capacity must be at least 1"
            elif capacity > 1000000:
                errors['capacity'] = "Capacity must not exceed 1,000,000"
        except (ValueError, TypeError):
            errors['capacity'] = "Capacity must be a valid number"
    
    return len(errors) == 0, errors