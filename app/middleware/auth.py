"""
Authentication Middleware and Decorators
"""
from functools import wraps
from flask import request, g
from app.utils.supabase_client import get_supabase
from app.utils.responses import error_response

def require_auth(f):
    """
    Decorator to require authentication for a route
    
    Extracts JWT from Authorization header, verifies it,
    and attaches user data to Flask's g object
    
    Usage:
        @app.route('/protected')
        @require_auth
        def protected_route():
            user_id = g.user['id']
            # ... route logic
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get authorization header
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            return error_response('Authorization header is required', 401)
        
        # Extract token from "Bearer <token>"
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            return error_response('Invalid authorization header format. Use: Bearer <token>', 401)
        
        token = parts[1]
        
        try:
            # Verify token with Supabase
            supabase = get_supabase()
            response = supabase.auth.get_user(token)
            
            if not response or not response.user:
                return error_response('Invalid or expired token', 401)
            
            # Get user profile from database
            user_id = response.user.id
            profile_response = supabase.table('profiles').select('*').eq('id', user_id).single().execute()
            
            if not profile_response.data:
                return error_response('User profile not found', 404)
            
            # Attach user to Flask g object
            g.user = profile_response.data
            g.token = token
            
            return f(*args, **kwargs)
            
        except Exception as e:
            error_message = str(e)
            if 'invalid JWT' in error_message.lower() or 'expired' in error_message.lower():
                return error_response('Invalid or expired token', 401)
            
            return error_response(f'Authentication failed: {error_message}', 401)
    
    return decorated_function

def require_organizer(f):
    """
    Decorator to require organizer role for a route
    
    Must be used AFTER @require_auth decorator
    
    Usage:
        @app.route('/organizer-only')
        @require_auth
        @require_organizer
        def organizer_route():
            # Only organizers can reach here
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is authenticated (should be set by @require_auth)
        if not hasattr(g, 'user'):
            return error_response('Authentication required', 401)
        
        # Check if user is an organizer
        if g.user.get('role') != 'organizer':
            return error_response('Organizer role required', 403)
        
        return f(*args, **kwargs)
    
    return decorated_function

def optional_auth(f):
    """
    Decorator for routes where authentication is optional
    
    If token is provided and valid, user data is attached to g.user
    If no token or invalid token, g.user is None and route continues
    
    Usage:
        @app.route('/public-or-private')
        @optional_auth
        def mixed_route():
            if g.user:
                # User is authenticated
            else:
                # User is not authenticated
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        if not auth_header:
            g.user = None
            return f(*args, **kwargs)
        
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != 'bearer':
            g.user = None
            return f(*args, **kwargs)
        
        token = parts[1]
        
        try:
            supabase = get_supabase()
            response = supabase.auth.get_user(token)
            
            if response and response.user:
                user_id = response.user.id
                profile_response = supabase.table('profiles').select('*').eq('id', user_id).single().execute()
                
                if profile_response.data:
                    g.user = profile_response.data
                else:
                    g.user = None
            else:
                g.user = None
                
        except Exception:
            g.user = None
        
        return f(*args, **kwargs)
    
    return decorated_function