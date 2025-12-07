"""
Groups Routes - MVP Version
Handles community group creation, discovery, and membership
"""
from flask import Blueprint, request, g
from app.utils.supabase_client import get_supabase, get_supabase_admin
from app.utils.responses import success_response, error_response, validation_error
from app.utils.validators import (
    validate_required_fields,
    validate_uuid,
    validate_group_data
)
from app.middleware.auth import require_auth, optional_auth

groups_bp = Blueprint('groups', __name__)

@groups_bp.route('', methods=['GET'])
@optional_auth
def list_groups():
    """
    List all public groups with optional filters
    
    Query Parameters:
        category: Filter by category
        search: Search in name/description
    
    Returns:
        200: List of public groups with member counts
    """
    try:
        supabase = get_supabase()
        
        # Get query parameters
        category = request.args.get('category', '').strip()
        search = request.args.get('search', '').strip()
        
        # Start query - only public groups
        query = supabase.table('groups').select('*, profiles!groups_creator_id_fkey(name, email, avatar_url)')
        query = query.eq('is_public', True)
        
        # Apply filters
        if category:
            query = query.eq('category', category.lower())
        
        if search:
            query = query.or_(f'name.ilike.%{search}%,description.ilike.%{search}%')
        
        # Order by creation date (newest first)
        query = query.order('created_at', desc=True)
        
        # Execute query
        response = query.execute()
        groups = response.data
        
        # Get member counts and check if current user is a member
        for group in groups:
            member_response = supabase.table('group_members').select('id', count='exact').eq('group_id', group['id']).execute()
            group['member_count'] = member_response.count if member_response.count else 0
            
            # Check if current user is a member
            if g.user:
                user_membership = supabase.table('group_members').select('id, role').eq('group_id', group['id']).eq('user_id', g.user['id']).execute()
                group['user_is_member'] = len(user_membership.data) > 0
                group['user_role'] = user_membership.data[0]['role'] if user_membership.data else None
            else:
                group['user_is_member'] = False
                group['user_role'] = None
            
            # Format creator data
            if group.get('profiles'):
                group['creator'] = group['profiles']
                del group['profiles']
        
        return success_response(data={'groups': groups})
        
    except Exception as e:
        return error_response(f'Failed to fetch groups: {str(e)}', 500)

@groups_bp.route('/<group_id>', methods=['GET'])
@optional_auth
def get_group(group_id):
    """
    Get single group details by ID
    
    URL Parameters:
        group_id: Group UUID
    
    Returns:
        200: Group details with creator info and member count
        404: Group not found
    """
    try:
        # Validate UUID
        uuid_valid, uuid_error = validate_uuid(group_id)
        if not uuid_valid:
            return error_response(uuid_error, 400)
        
        supabase = get_supabase()
        
        # Fetch group with creator info
        response = supabase.table('groups').select('*, profiles!groups_creator_id_fkey(id, name, email, avatar_url)').eq('id', group_id).execute()
        
        if not response.data or len(response.data) == 0:
            return error_response('Group not found', 404)
        
        group = response.data[0]
        
        # Check if group is public or user is a member
        if not group['is_public']:
            if not g.user:
                return error_response('Group not found', 404)
            
            # Check if user is a member
            member_check = supabase.table('group_members').select('id').eq('group_id', group_id).eq('user_id', g.user['id']).execute()
            if not member_check.data:
                return error_response('Group not found', 404)
        
        # Get member count
        member_response = supabase.table('group_members').select('id', count='exact').eq('group_id', group_id).execute()
        group['member_count'] = member_response.count if member_response.count else 0
        
        # Check if current user is a member
        if g.user:
            user_membership = supabase.table('group_members').select('id, role').eq('group_id', group_id).eq('user_id', g.user['id']).execute()
            group['user_is_member'] = len(user_membership.data) > 0
            group['user_role'] = user_membership.data[0]['role'] if user_membership.data else None
        else:
            group['user_is_member'] = False
            group['user_role'] = None
        
        # Format creator data
        if group.get('profiles'):
            group['creator'] = group['profiles']
            del group['profiles']
        
        return success_response(data=group)
        
    except Exception as e:
        error_str = str(e)
        if any(keyword in error_str.lower() for keyword in ['not found', 'no rows', '0 rows']):
            return error_response('Group not found', 404)
        return error_response(f'Failed to fetch group: {error_str}', 500)

@groups_bp.route('', methods=['POST'])
@require_auth
def create_group():
    """
    Create a new community group
    
    Headers:
        Authorization: Bearer <jwt_token>
    
    Request Body:
        {
            "name": "Tech Enthusiasts Karachi",
            "description": "A group for tech lovers in Karachi",
            "category": "tech",  // optional
            "avatar_url": "https://...",  // optional
            "is_public": true  // optional, defaults to true
        }
    
    Returns:
        201: Group created successfully (creator automatically becomes admin)
        400: Validation error
    """
    try:
        data = request.get_json()
        
        if not data:
            return error_response('Request body is required', 400)
        
        # Validate required fields
        required_fields = ['name', 'description']
        field_errors = validate_required_fields(data, required_fields)
        
        if field_errors:
            return validation_error(field_errors)
        
        # Validate group data
        is_valid, errors = validate_group_data(data)
        if not is_valid:
            return validation_error(errors)
        
        # Prepare group data
        group_data = {
            'creator_id': g.user['id'],
            'name': data['name'].strip(),
            'description': data['description'].strip(),
            'is_public': data.get('is_public', True)
        }
        
        # Add optional fields
        if data.get('category'):
            group_data['category'] = data['category'].lower().strip()
        
        if data.get('avatar_url'):
            group_data['avatar_url'] = data['avatar_url'].strip()
        
        # Create group - USE ADMIN CLIENT to bypass RLS
        supabase = get_supabase_admin()
        response = supabase.table('groups').insert(group_data).execute()
        
        if not response.data:
            return error_response('Failed to create group', 500)
        
        group = response.data[0]
        
        # Trigger should automatically add creator as admin
        # Fetch updated group with member count
        group['member_count'] = 1
        group['user_is_member'] = True
        group['user_role'] = 'admin'
        
        return success_response(
            data=group,
            message='Group created successfully',
            status=201
        )
        
    except Exception as e:
        return error_response(f'Failed to create group: {str(e)}', 500)

@groups_bp.route('/<group_id>/join', methods=['POST'])
@require_auth
def join_group(group_id):
    """
    Join a public group
    
    Headers:
        Authorization: Bearer <jwt_token>
    
    URL Parameters:
        group_id: Group UUID
    
    Returns:
        201: Successfully joined group
        400: Already a member or group is private
        404: Group not found
    """
    try:
        # Validate UUID
        uuid_valid, uuid_error = validate_uuid(group_id)
        if not uuid_valid:
            return error_response(uuid_error, 400)
        
        supabase = get_supabase()
        
        # Check if group exists and is public
        group_response = supabase.table('groups').select('*').eq('id', group_id).execute()
        
        if not group_response.data or len(group_response.data) == 0:
            return error_response('Group not found', 404)
        
        group = group_response.data[0]
        
        if not group['is_public']:
            return error_response('Cannot join private group', 400)
        
        # Check if user is already a member
        existing_member = supabase.table('group_members').select('id').eq('group_id', group_id).eq('user_id', g.user['id']).execute()
        
        if existing_member.data and len(existing_member.data) > 0:
            return error_response('You are already a member of this group', 400)
        
        # Add user as member - USE ADMIN CLIENT to bypass RLS
        member_data = {
            'group_id': group_id,
            'user_id': g.user['id'],
            'role': 'member'
        }
        
        supabase_admin = get_supabase_admin()
        response = supabase_admin.table('group_members').insert(member_data).execute()
        
        if not response.data:
            return error_response('Failed to join group', 500)
        
        return success_response(
            data={
                'membership': response.data[0],
                'group': {
                    'id': group['id'],
                    'name': group['name']
                }
            },
            message='Successfully joined group',
            status=201
        )
        
    except Exception as e:
        error_str = str(e)
        
        # Handle duplicate membership error
        if 'unique' in error_str.lower() or 'duplicate' in error_str.lower():
            return error_response('You are already a member of this group', 400)
        
        return error_response(f'Failed to join group: {error_str}', 500)

@groups_bp.route('/<group_id>/leave', methods=['DELETE'])
@require_auth
def leave_group(group_id):
    """
    Leave a group
    
    Headers:
        Authorization: Bearer <jwt_token>
    
    URL Parameters:
        group_id: Group UUID
    
    Returns:
        200: Successfully left group
        400: Cannot leave (you're the only admin)
        404: Not a member or group not found
    """
    try:
        # Validate UUID
        uuid_valid, uuid_error = validate_uuid(group_id)
        if not uuid_valid:
            return error_response(uuid_error, 400)
        
        supabase = get_supabase()
        
        # Check if user is a member
        membership = supabase.table('group_members').select('id, role').eq('group_id', group_id).eq('user_id', g.user['id']).execute()
        
        if not membership.data or len(membership.data) == 0:
            return error_response('You are not a member of this group', 404)
        
        user_role = membership.data[0]['role']
        
        # If user is admin, check if they're the only admin
        if user_role == 'admin':
            admin_count = supabase.table('group_members').select('id', count='exact').eq('group_id', group_id).eq('role', 'admin').execute()
            
            if admin_count.count == 1:
                return error_response('Cannot leave group: you are the only admin. Please assign another admin first or delete the group.', 400)
        
        # Remove membership - USE ADMIN CLIENT to bypass RLS
        supabase_admin = get_supabase_admin()
        supabase_admin.table('group_members').delete().eq('group_id', group_id).eq('user_id', g.user['id']).execute()
        
        return success_response(message='Successfully left group')
        
    except Exception as e:
        return error_response(f'Failed to leave group: {str(e)}', 500)

@groups_bp.route('/<group_id>/members', methods=['GET'])
@require_auth
def get_group_members(group_id):
    """
    Get all members of a group
    
    Headers:
        Authorization: Bearer <jwt_token>
    
    URL Parameters:
        group_id: Group UUID
    
    Returns:
        200: List of group members with their profiles
        403: Not a member of this group
        404: Group not found
    """
    try:
        # Validate UUID
        uuid_valid, uuid_error = validate_uuid(group_id)
        if not uuid_valid:
            return error_response(uuid_error, 400)
        
        supabase = get_supabase()
        
        # Check if group exists
        group_response = supabase.table('groups').select('id, name, is_public').eq('id', group_id).execute()
        
        if not group_response.data or len(group_response.data) == 0:
            return error_response('Group not found', 404)
        
        group = group_response.data[0]
        
        # Check if user is a member (unless group is public)
        if not group['is_public']:
            membership = supabase.table('group_members').select('id').eq('group_id', group_id).eq('user_id', g.user['id']).execute()
            
            if not membership.data:
                return error_response('You must be a member to view group members', 403)
        
        # Fetch all members with their profile info
        response = supabase.table('group_members').select('*, profiles!group_members_user_id_fkey(id, name, email, avatar_url, bio, location)').eq('group_id', group_id).order('joined_at', desc=False).execute()
        
        members = response.data
        
        # Format response
        formatted_members = []
        for member in members:
            if member.get('profiles'):
                member_data = {
                    'membership_id': member['id'],
                    'role': member['role'],
                    'joined_at': member['joined_at'],
                    'user': member['profiles']
                }
                formatted_members.append(member_data)
        
        return success_response(data={
            'group': {
                'id': group['id'],
                'name': group['name']
            },
            'members': formatted_members,
            'total': len(formatted_members)
        })
        
    except Exception as e:
        return error_response(f'Failed to fetch group members: {str(e)}', 500)

@groups_bp.route('/my-groups', methods=['GET'])
@require_auth
def get_user_groups():
    """
    Get all groups the current user is a member of
    
    Headers:
        Authorization: Bearer <jwt_token>
    
    Returns:
        200: List of user's groups
    """
    try:
        supabase = get_supabase()
        
        # Get user's group memberships with group details
        response = supabase.table('group_members').select('*, groups!group_members_group_id_fkey(*, profiles!groups_creator_id_fkey(name, email))').eq('user_id', g.user['id']).order('joined_at', desc=True).execute()
        
        memberships = response.data
        
        # Format response
        groups = []
        for membership in memberships:
            if membership.get('groups'):
                group = membership['groups']
                group['user_role'] = membership['role']
                group['joined_at'] = membership['joined_at']
                
                # Add creator info
                if group.get('profiles'):
                    group['creator'] = group['profiles']
                    del group['profiles']
                
                # Get member count
                member_count = supabase.table('group_members').select('id', count='exact').eq('group_id', group['id']).execute()
                group['member_count'] = member_count.count if member_count.count else 0
                
                groups.append(group)
        
        return success_response(data={'groups': groups})
        
    except Exception as e:
        return error_response(f'Failed to fetch user groups: {str(e)}', 500)