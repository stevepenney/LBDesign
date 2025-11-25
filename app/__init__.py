"""
Flask application factory
"""
from flask import Flask, redirect, url_for
from app.config import config
from app.extensions import init_extensions, login_manager
from app.models import User


def create_app(config_name='development'):
    """Create and configure Flask application"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    init_extensions(app)
    
    # Initialize Flask-Admin (optional - for database administration)
    try:
        from app.admin_config import init_admin
        init_admin(app)
    except ImportError:
        pass  # Flask-Admin not installed
    
    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from app.database.repositories import UserRepository
        return UserRepository.get_by_id(int(user_id))
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.projects import projects_bp
    from app.routes.beams import beams_bp
    from app.routes.admin import admin_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(beams_bp)
    app.register_blueprint(admin_bp)
    
    # Root route
    @app.route('/')
    def index():
        return redirect(url_for('projects.list'))
    
    # Create tables
    with app.app_context():
        from app.extensions import db
        db.create_all()
    
    return app
