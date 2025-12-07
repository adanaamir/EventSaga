"""
Flask Application Factory
"""
from flask import Flask
from flask_cors import CORS
from app.config import Config
from app.errors.handlers import register_error_handlers

def create_app(config_class=Config):
    """Create and configure Flask application"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Enable CORS for all routes
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Register error handlers
    register_error_handlers(app)
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.profile import profile_bp
    from app.routes.events import events_bp
    from app.routes.rsvps import rsvps_bp
    from app.routes.groups import groups_bp
    from app.routes.chat import messages_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(profile_bp, url_prefix='/api/profile')
    app.register_blueprint(events_bp, url_prefix='/api/events')
    app.register_blueprint(rsvps_bp, url_prefix='/api/rsvps')
    app.register_blueprint(groups_bp, url_prefix='/api/groups')
    app.register_blueprint(messages_bp, url_prefix='/api/groups')
    
    # Health check route
    @app.route('/api/health')
    def health_check():
        return {
            'success': True,
            'message': 'EventSaga API is running',
            'version': '1.0.0'
        }, 200
    
    return app