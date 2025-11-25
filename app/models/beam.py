"""
Beam model
"""
from datetime import datetime
from app.extensions import db


class Beam(db.Model):
    """Beam model for structural member designs"""
    __tablename__ = 'beams'
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), 
                          nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    reference = db.Column(db.String(50))  # User's reference code (e.g., "J1", "R2")
    
    # Member properties
    member_type = db.Column(db.String(50), nullable=False)  # floor_joist, rafter, beam
    span = db.Column(db.Float, nullable=False)  # meters
    spacing = db.Column(db.Float)  # meters (for joists/rafters)
    
    # Load parameters (stored as JSON)
    # For now we'll use separate columns, can migrate to JSON later
    dead_load = db.Column(db.Float)  # kPa or kN/m
    live_load = db.Column(db.Float)  # kPa or kN/m
    point_load_1 = db.Column(db.Float)  # kN
    point_load_1_position = db.Column(db.Float)  # meters from left support
    point_load_2 = db.Column(db.Float)  # kN
    point_load_2_position = db.Column(db.Float)  # meters from left support
    
    # Calculation results (to be populated by calculation engine)
    calculation_standard = db.Column(db.String(50))
    calculation_version = db.Column(db.String(20))
    max_moment = db.Column(db.Float)  # kNm
    max_shear = db.Column(db.Float)  # kN
    deflection_limit = db.Column(db.Float)  # mm
    
    # Product selection
    recommended_products = db.Column(db.JSON)  # Store recommendations as JSON
    selected_product_code = db.Column(db.String(50))
    
    # Metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, 
                          onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    project = db.relationship('Project', back_populates='beams')
    
    @property
    def total_udl(self):
        """Calculate total uniformly distributed load"""
        dead = self.dead_load or 0
        live = self.live_load or 0
        return dead + live
    
    def __repr__(self):
        return f'<Beam {self.name} in Project {self.project_id}>'
