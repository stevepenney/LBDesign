"""
Flask application factory for LBDesign (Lumberbank Design)
"""
from flask import Flask
from app.config import Config


def create_app(config_class=Config):
    """Create and configure the Flask application"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Register blueprints
    from app.routes.web import bp as web_bp
    from app.routes.api import bp as api_bp
    app.register_blueprint(web_bp)
    app.register_blueprint(api_bp, url_prefix='/api/v1')
    
    return app