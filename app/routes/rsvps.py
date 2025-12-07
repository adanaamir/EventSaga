"""
RSVP Routes - MVP Version
Handles event RSVP functionality
"""
from flask import Blueprint, request, g
from app.utils.supabase_client import get_supabase, get_supabase_admin
from app.utils.responses import success_response, error_response
from app.utils.validators import validate_uuid
from app.middleware.auth import require_auth

rsvps_bp = Blueprint('rsvps', __name__)

@rsvps_bp.route('/<event_id>', methods=['POST'])
@require_auth
def create_rsvp(event_id):
    """
    RSVP to an event
    
    Headers:
        Authorization: Bearer <jwt_token>
    
    URL Parameters:
        event_id: Event UUID
    
    Returns:
        201: RSVP created successfully
        400: Already RSVP'd or event at capacity
        404: Event not found
    """
    try:
        # Validate UUID
        uuid_valid, uuid_error = validate_uuid(event_id)
        if not uuid_valid:
            return error_response(uuid_error, 400)
        
        supabase = get_supabase()
        
        # Check if event exists and is active
        event_response = supabase.table('events').select('*').eq('id', event_id).execute()
        
        if not event_response.data or len(event_response.data) == 0:
            return error_response('Event not found', 404)
        
        event = event_response.data[0]
        
        if event['status'] != 'active':
            return error_response('Cannot RSVP to inactive event', 400)
        
        # Check if user already RSVP'd
        existing_rsvp = supabase.table('rsvps').select('id').eq('event_id', event_id).eq('user_id', g.user['id']).execute()
        
        if existing_rsvp.data and len(existing_rsvp.data) > 0:
            return error_response('You have already RSVP\'d to this event', 400)
        
        # Check capacity if set
        if event.get('capacity'):
            rsvp_count_response = supabase.table('rsvps').select('id', count='exact').eq('event_id', event_id).execute()
            current_count = rsvp_count_response.count if rsvp_count_response.count else 0
            
            if current_count >= event['capacity']:
                return error_response('Event is at full capacity', 400)
        
        # Create RSVP - USE ADMIN CLIENT to bypass RLS
        rsvp_data = {
            'event_id': event_id,
            'user_id': g.user['id']
        }
        
        supabase_admin = get_supabase_admin()
        response = supabase_admin.table('rsvps').insert(rsvp_data).execute()
        
        if not response.data:
            return error_response('Failed to create RSVP', 500)
        
        return success_response(
            data={
                'rsvp': response.data[0],
                'event': {
                    'id': event['id'],
                    'title': event['title'],
                    'datetime': event['datetime']
                }
            },
            message='RSVP successful',
            status=201
        )
        
    except Exception as e:
        error_str = str(e)
        
        # Handle duplicate RSVP error
        if 'unique' in error_str.lower() or 'duplicate' in error_str.lower():
            return error_response('You have already RSVP\'d to this event', 400)
        
        return error_response(f'Failed to create RSVP: {error_str}', 500)

@rsvps_bp.route('/<event_id>', methods=['DELETE'])
@require_auth
def cancel_rsvp(event_id):
    """
    Cancel RSVP to an event
    
    Headers:
        Authorization: Bearer <jwt_token>
    
    URL Parameters:
        event_id: Event UUID
    
    Returns:
        200: RSVP canceled successfully
        404: RSVP not found
    """
    try:
        # Validate UUID
        uuid_valid, uuid_error = validate_uuid(event_id)
        if not uuid_valid:
            return error_response(uuid_error, 400)
        
        supabase = get_supabase()
        
        # Check if RSVP exists
        existing_rsvp = supabase.table('rsvps').select('id').eq('event_id', event_id).eq('user_id', g.user['id']).execute()
        
        if not existing_rsvp.data or len(existing_rsvp.data) == 0:
            return error_response('RSVP not found', 404)
        
        # Delete RSVP - USE ADMIN CLIENT to bypass RLS
        supabase_admin = get_supabase_admin()
        supabase_admin.table('rsvps').delete().eq('event_id', event_id).eq('user_id', g.user['id']).execute()
        
        return success_response(message='RSVP canceled successfully')
        
    except Exception as e:
        return error_response(f'Failed to cancel RSVP: {str(e)}', 500)

@rsvps_bp.route('/my-rsvps', methods=['GET'])
@require_auth
def get_user_rsvps():
    """
    Get all events the current user has RSVP'd to
    
    Headers:
        Authorization: Bearer <jwt_token>
    
    Returns:
        200: List of RSVP'd events
    """
    try:
        supabase = get_supabase()
        
        # Get user's RSVPs with event details
        response = supabase.table('rsvps').select('*, events!rsvps_event_id_fkey(*, profiles!events_organizer_id_fkey(name, email))').eq('user_id', g.user['id']).order('created_at', desc=True).execute()
        
        rsvps = response.data
        
        # Format response
        events = []
        for rsvp in rsvps:
            if rsvp.get('events'):
                event = rsvp['events']
                event['rsvped_at'] = rsvp['created_at']
                
                # Add organizer info
                if event.get('profiles'):
                    event['organizer'] = event['profiles']
                    del event['profiles']
                
                # Get RSVP count
                rsvp_count_response = supabase.table('rsvps').select('id', count='exact').eq('event_id', event['id']).execute()
                event['rsvp_count'] = rsvp_count_response.count if rsvp_count_response.count else 0
                
                events.append(event)
        
        return success_response(data={'events': events})
        
    except Exception as e:
        return error_response(f'Failed to fetch RSVPs: {str(e)}', 500)