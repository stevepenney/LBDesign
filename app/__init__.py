"""
Flask application factory for LBDesign (Lumberbank Design)
"""
from flask import Flask
from app.config import Config


def create_app(config_class=Config):
    """Create and configure the Flask application"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    from app.extensions import db, migrate
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Import models to register them with SQLAlchemy
    from app import models
    
    # Register blueprints
    from app.routes import web, api
    app.register_blueprint(web.bp)
    app.register_blueprint(api.bp, url_prefix='/api/v1')
    
    return app
