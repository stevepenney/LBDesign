"""
Application configuration
"""
import os
from datetime import timedelta


class Config:
    """Base configuration"""
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Application
    APP_NAME = 'LBDesign'
    APP_TITLE = 'Lumberbank Design Calculator'
    
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # Future: Database, email, etc. will go here
