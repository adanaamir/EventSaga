"""
Messages Routes - MVP Version
Handles real-time chat messaging within groups
"""
from flask import Blueprint, request, g
from app.utils.supabase_client import get_supabase, get_supabase_admin
from app.utils.responses import success_response, error_response, validation_error
from app.utils.validators import validate_required_fields, validate_uuid
from app.middleware.auth import require_auth

messages_bp = Blueprint('messages', __name__)

@messages_bp.route('/<group_id>/messages', methods=['GET'])
@require_auth
def get_messages(group_id):
    """
    Get chat history for a group (with pagination)
    
    Headers:
        Authorization: Bearer <jwt_token>
    
    URL Parameters:
        group_id: Group UUID
    
    Query Parameters:
        limit: Number of messages to fetch (default: 50, max: 100)
        before: Fetch messages before this message ID (for pagination)
    
    Returns:
        200: List of messages with sender info
        403: Not a member of this group
        404: Group not found
    """
    try:
        # Validate UUID
        uuid_valid, uuid_error = validate_uuid(group_id)
        if not uuid_valid:
            return error_response(uuid_error, 400)
        
        supabase = get_supabase()
        
        # Check if user is a member of the group
        membership = supabase.table('group_members').select('id').eq('group_id', group_id).eq('user_id', g.user['id']).execute()
        
        if not membership.data or len(membership.data) == 0:
            return error_response('You must be a member of this group to view messages', 403)
        
        # Get pagination parameters
        limit = request.args.get('limit', 50, type=int)
        before_id = request.args.get('before', None)
        
        # Validate limit
        if limit < 1:
            limit = 50
        if limit > 100:
            limit = 100
        
        # Build query
        query = supabase.table('messages').select('*, profiles!messages_user_id_fkey(id, name, avatar_url)')
        query = query.eq('group_id', group_id)
        query = query.eq('is_deleted', False)
        
        # Add pagination
        if before_id:
            # Validate before_id UUID
            before_valid, before_error = validate_uuid(before_id)
            if before_valid:
                # Get the timestamp of the before message
                before_msg = supabase.table('messages').select('created_at').eq('id', before_id).execute()
                if before_msg.data:
                    query = query.lt('created_at', before_msg.data[0]['created_at'])
        
        # Order by newest first and limit
        query = query.order('created_at', desc=True).limit(limit)
        
        # Execute query
        response = query.execute()
        messages = response.data
        
        # Reverse to show oldest first
        messages.reverse()
        
        # Format messages
        formatted_messages = []
        for msg in messages:
            message_data = {
                'id': msg['id'],
                'content': msg['content'],
                'created_at': msg['created_at'],
                'sender': msg['profiles'] if msg.get('profiles') else None
            }
            formatted_messages.append(message_data)
        
        return success_response(data={
            'messages': formatted_messages,
            'count': len(formatted_messages),
            'has_more': len(formatted_messages) == limit
        })
        
    except Exception as e:
        return error_response(f'Failed to fetch messages: {str(e)}', 500)

@messages_bp.route('/<group_id>/messages', methods=['POST'])
@require_auth
def send_message(group_id):
    """
    Send a message to a group
    
    Headers:
        Authorization: Bearer <jwt_token>
    
    URL Parameters:
        group_id: Group UUID
    
    Request Body:
        {
            "content": "Hello everyone!"
        }
    
    Returns:
        201: Message sent successfully
        400: Validation error (empty message or too long)
        403: Not a member of this group
        404: Group not found
    """
    try:
        # Validate UUID
        uuid_valid, uuid_error = validate_uuid(group_id)
        if not uuid_valid:
            return error_response(uuid_error, 400)
        
        data = request.get_json()
        
        if not data:
            return error_response('Request body is required', 400)
        
        # Validate required fields
        required_fields = ['content']
        field_errors = validate_required_fields(data, required_fields)
        
        if field_errors:
            return validation_error(field_errors)
        
        content = data['content'].strip()
        
        # Validate content
        if len(content) < 1:
            return validation_error({'content': 'Message cannot be empty'})
        
        if len(content) > 2000:
            return validation_error({'content': 'Message must not exceed 2000 characters'})
        
        supabase = get_supabase()
        
        # Check if user is a member of the group
        membership = supabase.table('group_members').select('id').eq('group_id', group_id).eq('user_id', g.user['id']).execute()
        
        if not membership.data or len(membership.data) == 0:
            return error_response('You must be a member of this group to send messages', 403)
        
        # Create message - USE ADMIN CLIENT to bypass RLS
        message_data = {
            'group_id': group_id,
            'user_id': g.user['id'],
            'content': content
        }
        
        supabase_admin = get_supabase_admin()
        response = supabase_admin.table('messages').insert(message_data).execute()
        
        if not response.data:
            return error_response('Failed to send message', 500)
        
        message = response.data[0]
        
        # Fetch sender info
        sender_response = supabase.table('profiles').select('id, name, avatar_url').eq('id', g.user['id']).execute()
        
        formatted_message = {
            'id': message['id'],
            'content': message['content'],
            'created_at': message['created_at'],
            'sender': sender_response.data[0] if sender_response.data else None
        }
        
        return success_response(
            data=formatted_message,
            message='Message sent successfully',
            status=201
        )
        
    except Exception as e:
        return error_response(f'Failed to send message: {str(e)}', 500)

@messages_bp.route('/<group_id>/messages/<message_id>', methods=['DELETE'])
@require_auth
def delete_message(group_id, message_id):
    """
    Delete a message (soft delete - marks as deleted)
    Only the message sender or group admin can delete
    
    Headers:
        Authorization: Bearer <jwt_token>
    
    URL Parameters:
        group_id: Group UUID
        message_id: Message UUID
    
    Returns:
        200: Message deleted successfully
        403: Not authorized to delete this message
        404: Message not found
    """
    try:
        # Validate UUIDs
        uuid_valid, uuid_error = validate_uuid(group_id)
        if not uuid_valid:
            return error_response(uuid_error, 400)
        
        msg_valid, msg_error = validate_uuid(message_id)
        if not msg_valid:
            return error_response(msg_error, 400)
        
        supabase = get_supabase()
        
        # Check if message exists
        message_response = supabase.table('messages').select('*').eq('id', message_id).eq('group_id', group_id).execute()
        
        if not message_response.data or len(message_response.data) == 0:
            return error_response('Message not found', 404)
        
        message = message_response.data[0]
        
        # Check if user is the sender or a group admin
        is_sender = message['user_id'] == g.user['id']
        
        membership = supabase.table('group_members').select('role').eq('group_id', group_id).eq('user_id', g.user['id']).execute()
        is_admin = membership.data and membership.data[0]['role'] == 'admin'
        
        if not is_sender and not is_admin:
            return error_response('You can only delete your own messages or if you are a group admin', 403)
        
        # Soft delete message - USE ADMIN CLIENT to bypass RLS
        supabase_admin = get_supabase_admin()
        supabase_admin.table('messages').update({'is_deleted': True}).eq('id', message_id).execute()
        
        return success_response(message='Message deleted successfully')
        
    except Exception as e:
        return error_response(f'Failed to delete message: {str(e)}', 500)