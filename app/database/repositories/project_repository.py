"""
Project repository
"""
from app.models.project import Project
from app.database.repositories.base_repository import BaseRepository


class ProjectRepository(BaseRepository):
    """Repository for Project operations"""
    
    model = Project
    
    @classmethod
    def get_by_user(cls, user_id):
        """Get all projects for a specific user"""
        return Project.query.filter_by(user_id=user_id)\
            .order_by(Project.updated_at.desc()).all()
    
    @classmethod
    def get_by_user_paginated(cls, user_id, page=1, per_page=20):
        """Get paginated projects for a user"""
        return Project.query.filter_by(user_id=user_id)\
            .order_by(Project.updated_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)
    
    @classmethod
    def create_project(cls, user_id, name, region='new_zealand', **kwargs):
        """Create new project"""
        return cls.create(user_id=user_id, name=name, region=region, **kwargs)
    
    @classmethod
    def search_by_name(cls, user_id, search_term):
        """Search projects by name"""
        return Project.query.filter_by(user_id=user_id)\
            .filter(Project.name.contains(search_term))\
            .order_by(Project.updated_at.desc()).all()
    
    @classmethod
    def get_recent(cls, user_id, limit=10):
        """Get most recently updated projects"""
        return Project.query.filter_by(user_id=user_id)\
            .order_by(Project.updated_at.desc())\
            .limit(limit).all()
