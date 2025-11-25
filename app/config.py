"""
Application configuration
"""
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration"""
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database configuration
    DATABASE_TYPE = os.getenv('DATABASE_TYPE', 'sqlite')
    
    # Build database URI based on type
    if DATABASE_TYPE == 'mysql':
        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{os.getenv('DATABASE_USER')}:"
            f"{os.getenv('DATABASE_PASSWORD')}@"
            f"{os.getenv('DATABASE_HOST', 'localhost')}:"
            f"{os.getenv('DATABASE_PORT', '3306')}/"
            f"{os.getenv('DATABASE_NAME', 'beam_selector')}"
        )
    elif DATABASE_TYPE == 'mssql':
        SQLALCHEMY_DATABASE_URI = (
            f"mssql+pyodbc://{os.getenv('DATABASE_USER')}:"
            f"{os.getenv('DATABASE_PASSWORD')}@"
            f"{os.getenv('DATABASE_HOST', 'localhost')}:"
            f"{os.getenv('DATABASE_PORT', '1433')}/"
            f"{os.getenv('DATABASE_NAME', 'beam_selector')}"
            f"?driver=ODBC+Driver+17+for+SQL+Server"
        )
    else:  # sqlite
        # Use absolute path for SQLite database
        basedir = os.path.abspath(os.path.dirname(__file__))
        instance_path = os.path.join(os.path.dirname(basedir), 'instance')
        db_path = os.path.join(instance_path, 'beam_selector.db')
        
        # Ensure instance directory exists
        os.makedirs(instance_path, exist_ok=True)
        
        SQLALCHEMY_DATABASE_URI = f'sqlite:///{db_path}'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Application settings
    DEFAULT_REGION = os.getenv('DEFAULT_REGION', 'new_zealand')
    ITEMS_PER_PAGE = int(os.getenv('ITEMS_PER_PAGE', 20))


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
