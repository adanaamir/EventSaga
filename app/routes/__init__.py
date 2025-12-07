
from app.routes.auth import auth_bp
from app.routes.profile import profile_bp
from app.routes.events import events_bp
from app.routes.rsvps import rsvps_bp

__all__ = [
    'auth_bp',
    'profile_bp',
    'events_bp',
    'rsvps_bp'
]