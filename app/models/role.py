"""
Role model for user authorization
"""
from app.extensions import db
from datetime import datetime


class Role(db.Model):
    """User roles with hierarchical permissions"""
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))
    level = db.Column(db.Integer, nullable=False)  # Hierarchy: 1=USER, 2=DETAILER, 3=ADMIN, 4=SUPERUSER
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    users = db.relationship('User', backref='role', lazy='dynamic')
    
    def __repr__(self):
        return f'<Role {self.name}>'
    
    @staticmethod
    def init_roles():
        """Initialize default roles"""
        roles = {
            'USER': {'description': 'View-only access', 'level': 1},
            'DETAILER': {'description': 'Create and edit designs', 'level': 2},
            'ADMIN': {'description': 'Manage users and products', 'level': 3},
            'SUPERUSER': {'description': 'Full system access', 'level': 4}
        }
        
        for role_name, role_data in roles.items():
            role = Role.query.filter_by(name=role_name).first()
            if role is None:
                role = Role(
                    name=role_name,
                    description=role_data['description'],
                    level=role_data['level']
                )
                db.session.add(role)
        
        db.session.commit()
