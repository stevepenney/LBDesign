"""
Flask extensions
Initialize extensions here to avoid circular imports
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Initialize extensions (but don't bind to app yet)
db = SQLAlchemy()
migrate = Migrate()
