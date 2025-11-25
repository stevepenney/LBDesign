"""
Database initialization script
Creates tables and adds a test user
"""
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from app.extensions import db
from app.database.repositories import UserRepository

app = create_app()

with app.app_context():
    # Create all tables
    print("Creating database tables...")
    db.create_all()
    print("Tables created successfully!")
    
    # Check if test user exists
    test_user = UserRepository.get_by_username('admin')
    
    if not test_user:
        # Create test user
        print("\nCreating test user...")
        UserRepository.create_user(
            username='admin',
            email='admin@lumberbank.co.nz',
            password='admin123',
            role='SUPERUSER'
        )
        print("Test user created!")
        print("  Username: admin")
        print("  Password: admin123")
        print("  Role: SUPERUSER")
    else:
        print("\nTest user already exists.")
    
    print("\nDatabase initialization complete!")
    print("\nYou can now run the application with: python run.py")
