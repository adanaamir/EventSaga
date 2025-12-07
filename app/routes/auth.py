"""
Authentication Routes
Handles user signup, login, logout, and token management
"""
from flask import Blueprint, request, g
from app.utils.supabase_client import get_supabase
from app.utils.responses import success_response, error_response, validation_error
from app.utils.validators import (
    validate_email, 
    validate_password, 
    validate_name, 
    validate_role,
    validate_required_fields
)
from app.middleware.auth import require_auth

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/signup', methods=['POST'])
def signup():
    """
    Register a new user (attendee or organizer)
    
    Request Body:
        {
            "email": "user@example.com",
            "password": "securePassword123",
            "name": "John Doe",
            "role": "attendee"  // or "organizer"
        }
    
    Returns:
        201: User created successfully with JWT token
        400: Validation error or email already exists
    """
    try:
        data = request.get_json()
        
        if not data:
            return error_response('Request body is required', 400)
        
        # Validate required fields
        required_fields = ['email', 'password', 'name', 'role']
        field_errors = validate_required_fields(data, required_fields)
        
        if field_errors:
            return validation_error(field_errors)
        
        # Extract and validate individual fields
        email = data.get('email', '').strip()
        password = data.get('password', '')
        name = data.get('name', '').strip()
        role = data.get('role', '').strip().lower()
        
        # Validate email
        email_valid, email_error = validate_email(email)
        if not email_valid:
            return validation_error({'email': email_error})
        
        # Validate password
        password_valid, password_error = validate_password(password)
        if not password_valid:
            return validation_error({'password': password_error})
        
        # Validate name
        name_valid, name_error = validate_name(name)
        if not name_valid:
            return validation_error({'name': name_error})
        
        # Validate role
        role_valid, role_error = validate_role(role)
        if not role_valid:
            return validation_error({'role': role_error})
        
        # Create user in Supabase Auth
        supabase = get_supabase()
        
        auth_response = supabase.auth.sign_up({
            'email': email,
            'password': password,
            'options': {
                'data': {
                    'name': name,
                    'role': role
                }
            }
        })
        
        # Check if user was created
        if not auth_response.user:
            return error_response('Failed to create user account', 500)
        
        user_id = auth_response.user.id
        
        # Update the profile with the correct role (trigger creates profile with default role)
        try:
            supabase.table('profiles').update({
                'role': role,
                'name': name
            }).eq('id', user_id).execute()
        except Exception as profile_error:
            print(f"Warning: Profile update failed: {profile_error}")
            # Continue anyway - profile might have been created by trigger
        
        # Fetch complete user profile
        profile_response = supabase.table('profiles').select('*').eq('id', user_id).single().execute()
        
        # Prepare response data
        response_data = {
            'user': profile_response.data if profile_response.data else {
                'id': user_id,
                'email': email,
                'name': name,
                'role': role
            }
        }
        
        # Add session if available
        if auth_response.session:
            response_data['session'] = {
                'access_token': auth_response.session.access_token,
                'refresh_token': auth_response.session.refresh_token,
                'expires_at': auth_response.session.expires_at
            }
            message = 'User registered successfully'
        else:
            # Email confirmation might be required
            message = 'User registered successfully. Please check your email to confirm your account.'
        
        return success_response(
            data=response_data,
            message=message,
            status=201
        )
        
    except Exception as e:
        error_str = str(e)
        
        # Handle duplicate email error
        if 'already registered' in error_str.lower() or 'already exists' in error_str.lower() or 'duplicate' in error_str.lower():
            return error_response('Email already registered', 400)
        
        # Log full error for debugging
        print(f"Signup error: {error_str}")
        
        # Handle other errors
        return error_response(f'Registration failed: {error_str}', 500)

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Authenticate user and return JWT token
    
    Request Body:
        {
            "email": "user@example.com",
            "password": "securePassword123"
        }
    
    Returns:
        200: Login successful with JWT token and user data
        401: Invalid credentials
    """
    try:
        data = request.get_json()
        
        if not data:
            return error_response('Request body is required', 400)
        
        # Validate required fields
        required_fields = ['email', 'password']
        field_errors = validate_required_fields(data, required_fields)
        
        if field_errors:
            return validation_error(field_errors)
        
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        # Validate email format
        email_valid, email_error = validate_email(email)
        if not email_valid:
            return validation_error({'email': email_error})
        
        # Authenticate with Supabase
        supabase = get_supabase()
        
        auth_response = supabase.auth.sign_in_with_password({
            'email': email,
            'password': password
        })
        
        if not auth_response.user:
            return error_response('Invalid email or password', 401)
        
        # Fetch user profile
        user_id = auth_response.user.id
        profile_response = supabase.table('profiles').select('*').eq('id', user_id).single().execute()
        
        if not profile_response.data:
            return error_response('User profile not found', 404)
        
        return success_response(
            data={
                'user': profile_response.data,
                'session': {
                    'access_token': auth_response.session.access_token,
                    'refresh_token': auth_response.session.refresh_token,
                    'expires_at': auth_response.session.expires_at
                }
            },
            message='Login successful'
        )
        
    except Exception as e:
        error_str = str(e)
        
        # Handle invalid credentials
        if 'invalid' in error_str.lower() or 'credentials' in error_str.lower():
            return error_response('Invalid email or password', 401)
        
        return error_response(f'Login failed: {error_str}', 500)

@auth_bp.route('/logout', methods=['POST'])
@require_auth
def logout():
    """
    Logout user (invalidate token)
    
    Headers:
        Authorization: Bearer <jwt_token>
    
    Returns:
        200: Logout successful
    """
    try:
        supabase = get_supabase()
        supabase.auth.sign_out()
        
        return success_response(message='Logout successful')
        
    except Exception as e:
        return error_response(f'Logout failed: {str(e)}', 500)

@auth_bp.route('/me', methods=['GET'])
@require_auth
def get_current_user():
    """
    Get current logged-in user's profile
    
    Headers:
        Authorization: Bearer <jwt_token>
    
    Returns:
        200: User profile data
        401: Invalid or expired token
    """
    try:
        # User data is already attached by @require_auth decorator
        return success_response(data=g.user)
        
    except Exception as e:
        return error_response(f'Failed to fetch user: {str(e)}', 500)

@auth_bp.route('/refresh', methods=['POST'])
def refresh_token():
    """
    Refresh expired JWT token
    
    Request Body:
        {
            "refresh_token": "refresh_token_here"
        }
    
    Returns:
        200: New access token
        400: Invalid refresh token
    """
    try:
        data = request.get_json()
        
        if not data:
            return error_response('Request body is required', 400)
        
        refresh_token = data.get('refresh_token')
        
        if not refresh_token:
            return error_response('Refresh token is required', 400)
        
        # Refresh session with Supabase
        supabase = get_supabase()
        
        auth_response = supabase.auth.refresh_session(refresh_token)
        
        if not auth_response.session:
            return error_response('Invalid or expired refresh token', 400)
        
        return success_response(
            data={
                'access_token': auth_response.session.access_token,
                'refresh_token': auth_response.session.refresh_token,
                'expires_at': auth_response.session.expires_at
            },
            message='Token refreshed successfully'
        )
        
    except Exception as e:
        error_str = str(e)
        
        if 'invalid' in error_str.lower() or 'expired' in error_str.lower():
            return error_response('Invalid or expired refresh token', 400)
        
        return error_response(f'Token refresh failed: {error_str}', 500)