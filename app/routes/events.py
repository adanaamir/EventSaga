"""
Event Routes - MVP Version
Handles event discovery, creation, and management
"""
from flask import Blueprint, request, g
from datetime import datetime
from app.utils.supabase_client import get_supabase, get_supabase_admin
from app.utils.responses import success_response, error_response, validation_error
from app.utils.validators import (
    validate_required_fields,
    validate_uuid,
    validate_event_data
)
from app.middleware.auth import require_auth, require_organizer, optional_auth

events_bp = Blueprint('events', __name__)

@events_bp.route('', methods=['GET'])
@optional_auth
def list_events():
    """
    List all active events with optional filters
    
    Query Parameters:
        city: Filter by city
        category: Filter by category
        search: Search in title/description
    
    Returns:
        200: List of events
    """
    try:
        supabase = get_supabase()
        
        # Get query parameters
        city = request.args.get('city', '').strip()
        category = request.args.get('category', '').strip().lower()
        search = request.args.get('search', '').strip()
        
        # Start query - only active, future events
        query = supabase.table('events').select('*, profiles!events_organizer_id_fkey(name, email)')
        query = query.eq('status', 'active')
        query = query.gte('datetime', datetime.utcnow().isoformat())
        
        # Apply filters
        if city:
            query = query.ilike('city', f'%{city}%')
        
        if category:
            valid_categories = ['music', 'tech', 'sports', 'food', 'arts', 'business', 'workshop', 'networking', 'entertainment', 'other']
            if category in valid_categories:
                query = query.eq('category', category)
        
        if search:
            query = query.or_(f'title.ilike.%{search}%,description.ilike.%{search}%')
        
        # Order by date (upcoming first)
        query = query.order('datetime', desc=False)
        
        # Execute query
        response = query.execute()
        
        # Get RSVP counts for each event
        events = response.data
        for event in events:
            rsvp_response = supabase.table('rsvps').select('id', count='exact').eq('event_id', event['id']).execute()
            event['rsvp_count'] = rsvp_response.count if rsvp_response.count else 0
            
            # Check if current user has RSVP'd
            if g.user:
                user_rsvp = supabase.table('rsvps').select('id').eq('event_id', event['id']).eq('user_id', g.user['id']).execute()
                event['user_has_rsvped'] = len(user_rsvp.data) > 0
            else:
                event['user_has_rsvped'] = False
            
            # Format organizer data
            if event.get('profiles'):
                event['organizer'] = event['profiles']
                del event['profiles']
        
        return success_response(data={'events': events})
        
    except Exception as e:
        return error_response(f'Failed to fetch events: {str(e)}', 500)

@events_bp.route('/<event_id>', methods=['GET'])
@optional_auth
def get_event(event_id):
    """
    Get single event details by ID
    
    URL Parameters:
        event_id: Event UUID
    
    Returns:
        200: Event details with organizer info and RSVP count
        404: Event not found
    """
    try:
        # Validate UUID
        uuid_valid, uuid_error = validate_uuid(event_id)
        if not uuid_valid:
            return error_response(uuid_error, 400)
        
        supabase = get_supabase()
        
        # Fetch event with organizer info
        response = supabase.table('events').select('*, profiles!events_organizer_id_fkey(id, name, email, avatar_url)').eq('id', event_id).execute()
        
        if not response.data or len(response.data) == 0:
            return error_response('Event not found', 404)
        
        event = response.data[0]
        
        # Check if event is active or user is the organizer
        if event['status'] != 'active':
            if not g.user or g.user['id'] != event['organizer_id']:
                return error_response('Event not found', 404)
        
        # Get RSVP count
        rsvp_response = supabase.table('rsvps').select('id', count='exact').eq('event_id', event_id).execute()
        event['rsvp_count'] = rsvp_response.count if rsvp_response.count else 0
        
        # Check if current user has RSVP'd
        if g.user:
            user_rsvp = supabase.table('rsvps').select('id').eq('event_id', event_id).eq('user_id', g.user['id']).execute()
            event['user_has_rsvped'] = len(user_rsvp.data) > 0
        else:
            event['user_has_rsvped'] = False
        
        # Format organizer data
        if event.get('profiles'):
            event['organizer'] = event['profiles']
            del event['profiles']
        
        return success_response(data=event)
        
    except Exception as e:
        error_str = str(e)
        if any(keyword in error_str.lower() for keyword in ['not found', 'no rows', '0 rows']):
            return error_response('Event not found', 404)
        return error_response(f'Failed to fetch event: {error_str}', 500)

@events_bp.route('/trending', methods=['GET'])
def get_trending_events():
    """
    Get trending events (most RSVPs or marked as trending)
    
    Returns:
        200: List of trending events
    """
    try:
        supabase = get_supabase()
        
        # Get events marked as trending or with most RSVPs
        response = supabase.table('events').select('*, profiles!events_organizer_id_fkey(name, email)').eq('status', 'active').gte('datetime', datetime.utcnow().isoformat()).order('is_trending', desc=True).limit(10).execute()
        
        events = response.data
        
        # Add RSVP counts
        for event in events:
            rsvp_response = supabase.table('rsvps').select('id', count='exact').eq('event_id', event['id']).execute()
            event['rsvp_count'] = rsvp_response.count if rsvp_response.count else 0
            
            if event.get('profiles'):
                event['organizer'] = event['profiles']
                del event['profiles']
        
        # Sort by RSVP count
        events.sort(key=lambda x: x['rsvp_count'], reverse=True)
        
        return success_response(data={'events': events[:10]})
        
    except Exception as e:
        return error_response(f'Failed to fetch trending events: {str(e)}', 500)

@events_bp.route('', methods=['POST'])
@require_auth
@require_organizer
def create_event():
    """
    Create a new event (organizer only)
    
    Headers:
        Authorization: Bearer <jwt_token>
    
    Request Body:
        {
            "title": "Tech Conference 2025",
            "description": "Annual tech conference...",
            "datetime": "2025-06-15T10:00:00Z",
            "end_datetime": "2025-06-15T18:00:00Z",  // optional
            "location": "Convention Center",
            "city": "Karachi",
            "address": "123 Main St",  // optional
            "category": "tech",
            "image_url": "https://...",  // optional
            "capacity": 500  // optional
        }
    
    Returns:
        201: Event created successfully
        400: Validation error
        403: User is not an organizer
    """
    try:
        data = request.get_json()
        
        if not data:
            return error_response('Request body is required', 400)
        
        # Validate required fields
        required_fields = ['title', 'description', 'datetime', 'location', 'city', 'category']
        field_errors = validate_required_fields(data, required_fields)
        
        if field_errors:
            return validation_error(field_errors)
        
        # Validate event data
        is_valid, errors = validate_event_data(data)
        if not is_valid:
            return validation_error(errors)
        
        # Prepare event data
        event_data = {
            'organizer_id': g.user['id'],
            'title': data['title'].strip(),
            'description': data['description'].strip(),
            'datetime': data['datetime'],
            'location': data['location'].strip(),
            'city': data['city'].strip(),
            'category': data['category'].lower().strip(),
            'status': 'active'
        }
        
        # Add optional fields
        if data.get('end_datetime'):
            event_data['end_datetime'] = data['end_datetime']
        
        if data.get('address'):
            event_data['address'] = data['address'].strip()
        
        if data.get('image_url'):
            event_data['image_url'] = data['image_url'].strip()
        
        if data.get('capacity'):
            try:
                capacity = int(data['capacity'])
                if capacity < 1:
                    return validation_error({'capacity': 'Capacity must be at least 1'})
                event_data['capacity'] = capacity
            except (ValueError, TypeError):
                return validation_error({'capacity': 'Capacity must be a valid number'})
        
        # Create event - USE ADMIN CLIENT to bypass RLS
        supabase = get_supabase_admin()
        response = supabase.table('events').insert(event_data).execute()
        
        if not response.data:
            return error_response('Failed to create event', 500)
        
        event = response.data[0]
        event['rsvp_count'] = 0
        event['user_has_rsvped'] = False
        
        return success_response(
            data=event,
            message='Event created successfully',
            status=201
        )
        
    except Exception as e:
        return error_response(f'Failed to create event: {str(e)}', 500)

@events_bp.route('/<event_id>', methods=['PUT'])
@require_auth
@require_organizer
def update_event(event_id):
    """
    Update an event (own events only)
    
    Headers:
        Authorization: Bearer <jwt_token>
    
    URL Parameters:
        event_id: Event UUID
    
    Request Body: (all fields optional)
        {
            "title": "Updated Title",
            "description": "Updated description",
            ...
        }
    
    Returns:
        200: Event updated successfully
        403: Not the event organizer
        404: Event not found
    """
    try:
        # Validate UUID
        uuid_valid, uuid_error = validate_uuid(event_id)
        if not uuid_valid:
            return error_response(uuid_error, 400)
        
        data = request.get_json()
        if not data:
            return error_response('Request body is required', 400)
        
        supabase = get_supabase()
        
        # Check if event exists and user is the organizer
        event_response = supabase.table('events').select('*').eq('id', event_id).execute()
        
        if not event_response.data or len(event_response.data) == 0:
            return error_response('Event not found', 404)
        
        event = event_response.data[0]
        
        if event['organizer_id'] != g.user['id']:
            return error_response('You can only update your own events', 403)
        
        # Build update data
        update_data = {}
        
        if 'title' in data:
            title = data['title'].strip()
            if len(title) < 3:
                return validation_error({'title': 'Title must be at least 3 characters'})
            update_data['title'] = title
        
        if 'description' in data:
            description = data['description'].strip()
            if len(description) < 10:
                return validation_error({'description': 'Description must be at least 10 characters'})
            update_data['description'] = description
        
        if 'datetime' in data:
            update_data['datetime'] = data['datetime']
        
        if 'end_datetime' in data:
            update_data['end_datetime'] = data['end_datetime']
        
        if 'location' in data:
            update_data['location'] = data['location'].strip()
        
        if 'city' in data:
            update_data['city'] = data['city'].strip()
        
        if 'address' in data:
            update_data['address'] = data['address'].strip() if data['address'] else None
        
        if 'category' in data:
            category = data['category'].lower().strip()
            valid_categories = ['music', 'tech', 'sports', 'food', 'arts', 'business', 'workshop', 'networking', 'entertainment', 'other']
            if category not in valid_categories:
                return validation_error({'category': f'Category must be one of: {", ".join(valid_categories)}'})
            update_data['category'] = category
        
        if 'image_url' in data:
            update_data['image_url'] = data['image_url'].strip() if data['image_url'] else None
        
        if 'capacity' in data:
            try:
                capacity = int(data['capacity'])
                if capacity < 1:
                    return validation_error({'capacity': 'Capacity must be at least 1'})
                update_data['capacity'] = capacity
            except (ValueError, TypeError):
                return validation_error({'capacity': 'Capacity must be a valid number'})
        
        if 'status' in data:
            status = data['status'].lower().strip()
            if status not in ['active', 'canceled', 'completed']:
                return validation_error({'status': 'Status must be active, canceled, or completed'})
            update_data['status'] = status
        
        if not update_data:
            return error_response('No fields to update', 400)
        
        # Update event - USE ADMIN CLIENT to bypass RLS
        supabase_admin = get_supabase_admin()
        response = supabase_admin.table('events').update(update_data).eq('id', event_id).execute()
        
        if not response.data:
            return error_response('Failed to update event', 500)
        
        return success_response(
            data=response.data[0],
            message='Event updated successfully'
        )
        
    except Exception as e:
        return error_response(f'Failed to update event: {str(e)}', 500)

@events_bp.route('/<event_id>', methods=['DELETE'])
@require_auth
@require_organizer
def delete_event(event_id):
    """
    Delete/cancel an event (own events only)
    
    Headers:
        Authorization: Bearer <jwt_token>
    
    URL Parameters:
        event_id: Event UUID
    
    Returns:
        200: Event deleted successfully
        403: Not the event organizer
        404: Event not found
    """
    try:
        # Validate UUID
        uuid_valid, uuid_error = validate_uuid(event_id)
        if not uuid_valid:
            return error_response(uuid_error, 400)
        
        supabase = get_supabase()
        
        # Check if event exists and user is the organizer
        event_response = supabase.table('events').select('*').eq('id', event_id).execute()
        
        if not event_response.data or len(event_response.data) == 0:
            return error_response('Event not found', 404)
        
        event = event_response.data[0]
        
        if event['organizer_id'] != g.user['id']:
            return error_response('You can only delete your own events', 403)
        
        # Soft delete - mark as canceled - USE ADMIN CLIENT to bypass RLS
        supabase_admin = get_supabase_admin()
        supabase_admin.table('events').update({'status': 'canceled'}).eq('id', event_id).execute()
        
        return success_response(message='Event canceled successfully')
        
    except Exception as e:
        return error_response(f'Failed to delete event: {str(e)}', 500)

@events_bp.route('/organizer/my-events', methods=['GET'])
@require_auth
@require_organizer
def get_organizer_events():
    """
    Get all events created by the current organizer
    
    Headers:
        Authorization: Bearer <jwt_token>
    
    Returns:
        200: List of organizer's events
    """
    try:
        supabase = get_supabase()
        
        # Get organizer's events - ALL statuses (active, canceled, completed)
        query = supabase.table('events').select('*').eq('organizer_id', g.user['id'])
        query = query.order('created_at', desc=True)
        
        response = query.execute()
        events = response.data
        
        # Add RSVP counts
        for event in events:
            rsvp_response = supabase.table('rsvps').select('id', count='exact').eq('event_id', event['id']).execute()
            event['rsvp_count'] = rsvp_response.count if rsvp_response.count else 0
        
        return success_response(data={'events': events})
        
    except Exception as e:
        return error_response(f'Failed to fetch events: {str(e)}', 500)