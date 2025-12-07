"""
Profile Routes
Handles user profile viewing and updates
"""
from flask import Blueprint, request, g
from app.utils.supabase_client import get_supabase
from app.utils.responses import success_response, error_response, validation_error
from app.utils.validators import validate_uuid, validate_name, validate_role
from app.middleware.auth import require_auth

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/<user_id>', methods=['GET'])
def get_profile(user_id):
    """
    Get any user's public profile by their ID
    
    URL Parameters:
        user_id: User UUID
    
    Returns:
        200: User profile data
        404: User not found
    """
    try:
        # Validate UUID format
        uuid_valid, uuid_error = validate_uuid(user_id)
        if not uuid_valid:
            return error_response(uuid_error, 400)
        
        # Fetch profile from database - DON'T use .single()
        supabase = get_supabase()
        response = supabase.table('profiles').select('*').eq('id', user_id).execute()
        
        # Check if any data returned
        if not response.data or len(response.data) == 0:
            return error_response('User not found', 404)
        
        # Return first (and only) profile
        profile = response.data[0]
        
        return success_response(data=profile)
        
    except Exception as e:
        error_str = str(e)
        
        # Handle "Cannot coerce" error or other "not found" errors
        if any(keyword in error_str.lower() for keyword in ['cannot coerce', 'not found', 'no rows', '0 rows', 'pgrst116']):
            return error_response('User not found', 404)
        
        return error_response(f'Failed to fetch profile: {error_str}', 500)

@profile_bp.route('', methods=['PUT'])
@require_auth
def update_profile():
    """
    Update current user's own profile
    
    Headers:
        Authorization: Bearer <jwt_token>
    
    Request Body (all fields optional):
        {
            "name": "John Doe Updated",
            "bio": "I love attending music festivals",
            "location": "Karachi, Pakistan",
            "avatar_url": "https://supabase.storage/.../avatar.jpg"
        }
    
    Returns:
        200: Profile updated successfully
        400: Validation error
    """
    try:
        data = request.get_json()
        
        if not data:
            return error_response('Request body is required', 400)
        
        # Get current user ID from auth decorator
        user_id = g.user['id']
        
        # Build update payload with only provided fields
        update_data = {}
        
        # Validate and add name if provided
        if 'name' in data:
            name = data['name'].strip()
            name_valid, name_error = validate_name(name)
            if not name_valid:
                return validation_error({'name': name_error})
            update_data['name'] = name
        
        # Add bio if provided
        if 'bio' in data:
            bio = data['bio']
            if bio is not None:
                bio = bio.strip()
                if len(bio) > 500:
                    return validation_error({'bio': 'Bio must not exceed 500 characters'})
                update_data['bio'] = bio
            else:
                update_data['bio'] = None
        
        # Add location if provided
        if 'location' in data:
            location = data['location']
            if location is not None:
                location = location.strip()
                if len(location) > 100:
                    return validation_error({'location': 'Location must not exceed 100 characters'})
                update_data['location'] = location
            else:
                update_data['location'] = None
        
        # Add avatar_url if provided
        if 'avatar_url' in data:
            avatar_url = data['avatar_url']
            if avatar_url is not None:
                avatar_url = avatar_url.strip()
                # Basic URL validation
                if not avatar_url.startswith(('http://', 'https://')):
                    return validation_error({'avatar_url': 'Avatar URL must be a valid HTTP/HTTPS URL'})
                update_data['avatar_url'] = avatar_url
            else:
                update_data['avatar_url'] = None
        
        # Check if there's anything to update
        if not update_data:
            return error_response('No fields to update', 400)
        
        # Update profile in database
        supabase = get_supabase()
        response = supabase.table('profiles').update(update_data).eq('id', user_id).execute()
        
        if not response.data:
            return error_response('Failed to update profile', 500)
        
        # Fetch updated profile
        updated_profile = supabase.table('profiles').select('*').eq('id', user_id).single().execute()
        
        return success_response(
            data=updated_profile.data,
            message='Profile updated successfully'
        )
        
    except Exception as e:
        return error_response(f'Failed to update profile: {str(e)}', 500)

@profile_bp.route('/role', methods=['PATCH'])
@require_auth
def update_role():
    """
    Switch user role between 'attendee' and 'organizer'
    
    Headers:
        Authorization: Bearer <jwt_token>
    
    Request Body:
        {
            "role": "organizer"  // or "attendee"
        }
    
    Returns:
        200: Role updated successfully
        400: Invalid role value
    """
    try:
        data = request.get_json()
        
        if not data:
            return error_response('Request body is required', 400)
        
        role = data.get('role', '').strip().lower()
        
        # Validate role
        role_valid, role_error = validate_role(role)
        if not role_valid:
            return validation_error({'role': role_error})
        
        # Get current user ID
        user_id = g.user['id']
        
        # Update role in database
        supabase = get_supabase()
        response = supabase.table('profiles').update({
            'role': role
        }).eq('id', user_id).execute()
        
        if not response.data:
            return error_response('Failed to update role', 500)
        
        # Fetch updated profile
        updated_profile = supabase.table('profiles').select('*').eq('id', user_id).single().execute()
        
        return success_response(
            data=updated_profile.data,
            message=f'Role updated to {role}'
        )
        
    except Exception as e:
        return error_response(f'Failed to update role: {str(e)}', 500)