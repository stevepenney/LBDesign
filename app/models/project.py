"""
Project model for organizing beam designs
"""
from app.extensions import db
from datetime import datetime


class Project(db.Model):
    """Project containing multiple beam designs"""
    __tablename__ = 'projects'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    region_id = db.Column(db.Integer, db.ForeignKey('regions.id'), nullable=False)
    
    # Project parameters (JSON stored as text)
    parameters = db.Column(db.Text)  # JSON: {"building_type": "residential", "wind_zone": "Medium", etc.}
    
    # Status and timestamps
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    beams = db.relationship('Beam', backref='project', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Project {self.name}>'
    
    @property
    def beam_count(self):
        """Return count of beams in project"""
        return self.beams.count()
