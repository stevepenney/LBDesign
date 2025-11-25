"""
Project model
"""
from datetime import datetime
from app.extensions import db


class Project(db.Model):
    """Project model for organizing beam designs"""
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    region = db.Column(db.String(50), nullable=False, default='new_zealand')
    
    # Project details
    address = db.Column(db.String(500))
    client = db.Column(db.String(200))
    engineer = db.Column(db.String(200))
    architect = db.Column(db.String(200))
    merchant = db.Column(db.String(200))
    project_number = db.Column(db.String(50))
    project_type = db.Column(db.String(50))  # Midfloor/Rafters/Both
    
    # Dates
    date_received = db.Column(db.Date)
    date_designed = db.Column(db.Date)
    date_sent = db.Column(db.Date)
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, 
                          onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    owner = db.relationship('User', back_populates='projects')
    beams = db.relationship('Beam', back_populates='project', lazy='dynamic',
                          cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Project {self.name}>'
