"""
Beam model for structural member designs
"""
from app.extensions import db
from datetime import datetime


class Beam(db.Model):
    """Individual beam design within a project"""
    __tablename__ = 'beams'
    
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(100), nullable=False)  # User's reference (e.g., "B1", "Floor Joist 1")
    
    # Foreign keys
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    selected_product_id = db.Column(db.Integer, db.ForeignKey('products.id'))
    
    # Beam type and dimensions
    member_type = db.Column(db.String(50), nullable=False)  # 'floor_joist', 'rafter', 'beam', etc.
    span = db.Column(db.Numeric(10, 3), nullable=False)  # meters
    spacing = db.Column(db.Numeric(10, 3))  # meters (if applicable)
    
    # Load parameters (JSON stored as text)
    load_parameters = db.Column(db.Text, nullable=False)
    # JSON: {
    #   "dead_load": 0.5,
    #   "live_load": 1.5,
    #   "point_loads": [{"location": 2.5, "magnitude": 5.0}],
    #   "distributed_loads": [...]
    # }
    
    # Calculation results (JSON stored as text)
    calculation_results = db.Column(db.Text)
    # JSON: {
    #   "standard_used": "NZS3603:1993",
    #   "standard_version": "1993",
    #   "max_moment": 25.5,
    #   "max_shear": 12.3,
    #   "deflection": 12.5,
    #   "recommended_products": [...]
    # }
    
    # Calculation metadata
    calculation_standard = db.Column(db.String(50))
    calculation_version = db.Column(db.String(20))
    calculated_at = db.Column(db.DateTime)
    
    # Status and timestamps
    is_complete = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    selected_product = db.relationship('Product', backref='beams')
    
    def __repr__(self):
        return f'<Beam {self.reference}>'
    
    @property
    def has_results(self):
        """Check if beam has calculation results"""
        return self.calculation_results is not None
