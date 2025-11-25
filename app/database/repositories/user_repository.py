"""
User repository
"""
from datetime import datetime
from app.models.user import User
from app.database.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository):
    """Repository for User operations"""
    
    model = User
    
    @classmethod
    def get_by_username(cls, username):
        """Get user by username"""
        return User.query.filter_by(username=username).first()
    
    @classmethod
    def get_by_email(cls, email):
        """Get user by email"""
        return User.query.filter_by(email=email).first()
    
    @classmethod
    def create_user(cls, username, email, password, role='USER'):
        """Create new user with hashed password"""
        user = User(username=username, email=email, role=role)
        user.set_password(password)
        return cls.save(user)
    
    @classmethod
    def update_last_login(cls, user):
        """Update user's last login timestamp"""
        user.last_login = datetime.utcnow()
        return cls.save(user)
    
    @classmethod
    def get_active_users(cls):
        """Get all active users"""
        return User.query.filter_by(is_active=True).all()
