"""
Base repository providing common CRUD operations
"""
from app.extensions import db


class BaseRepository:
    """Base repository with generic CRUD operations"""
    
    model = None  # Override in subclasses
    
    @classmethod
    def get_by_id(cls, id):
        """Get record by ID"""
        return cls.model.query.get(id)
    
    @classmethod
    def get_all(cls):
        """Get all records"""
        return cls.model.query.all()
    
    @classmethod
    def count_all(cls):
        """Count all records"""
        return cls.model.query.count()
    
    @classmethod
    def create(cls, **kwargs):
        """Create new record"""
        instance = cls.model(**kwargs)
        db.session.add(instance)
        db.session.commit()
        return instance
    
    @classmethod
    def update(cls, instance, **kwargs):
        """Update existing record"""
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        db.session.commit()
        return instance
    
    @classmethod
    def delete(cls, instance):
        """Delete record"""
        db.session.delete(instance)
        db.session.commit()
    
    @classmethod
    def save(cls, instance):
        """Save instance (add if new, commit if existing)"""
        if not instance.id:
            db.session.add(instance)
        db.session.commit()
        return instance
