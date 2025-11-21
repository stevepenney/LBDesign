"""
Application configuration
"""
import os
from datetime import timedelta


def get_database_uri():
    """Generate database URI based on DATABASE_TYPE environment variable"""
    db_type = os.environ.get('DATABASE_TYPE', 'sqlite').lower()
    
    if db_type == 'sqlite':
        # SQLite - for development
        return 'sqlite:///lbdesign.db'
    
    elif db_type == 'mysql':
        # MySQL/MariaDB
        user = os.environ.get('DATABASE_USER', '')
        password = os.environ.get('DATABASE_PASSWORD', '')
        host = os.environ.get('DATABASE_HOST', 'localhost')
        port = os.environ.get('DATABASE_PORT', '3306')
        name = os.environ.get('DATABASE_NAME', 'lbdesign')
        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}"
    
    elif db_type == 'mssql':
        # Microsoft SQL Server
        user = os.environ.get('DATABASE_USER', '')
        password = os.environ.get('DATABASE_PASSWORD', '')
        host = os.environ.get('DATABASE_HOST', 'localhost')
        port = os.environ.get('DATABASE_PORT', '1433')
        name = os.environ.get('DATABASE_NAME', 'lbdesign')
        driver = 'ODBC+Driver+17+for+SQL+Server'
        return f"mssql+pyodbc://{user}:{password}@{host}:{port}/{name}?driver={driver}"
    
    else:
        raise ValueError(f"Unsupported database type: {db_type}")


class Config:
    """Base configuration"""
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Application
    APP_NAME = 'LBDesign'
    APP_TITLE = 'Lumberbank Design Calculator'
    
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # Database Configuration
    DATABASE_TYPE = os.environ.get('DATABASE_TYPE', 'sqlite')
    DATABASE_HOST = os.environ.get('DATABASE_HOST', 'localhost')
    DATABASE_PORT = os.environ.get('DATABASE_PORT', '3306')
    DATABASE_NAME = os.environ.get('DATABASE_NAME', 'lbdesign')
    DATABASE_USER = os.environ.get('DATABASE_USER', '')
    DATABASE_PASSWORD = os.environ.get('DATABASE_PASSWORD', '')
    
    # SQLAlchemy
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_DATABASE_URI = get_database_uri()