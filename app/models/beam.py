"""
Beam model - UPDATED with calculation result fields
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
    
    # Load parameters
    dead_load = db.Column(db.Float)  # kPa or kN/m
    live_load = db.Column(db.Float)  # kPa or kN/m
    point_load_1 = db.Column(db.Float)  # kN
    point_load_1_position = db.Column(db.Float)  # meters from left support
    point_load_2 = db.Column(db.Float)  # kN
    point_load_2_position = db.Column(db.Float)  # meters from left support
    support_config = db.Column(db.JSON)
    
    # ========================================================================
    # CALCULATION RESULTS - DEMANDS
    # ========================================================================
    demand_moment = db.Column(db.Float)  # M* (kNm)
    demand_shear = db.Column(db.Float)  # V* (kN)
    demand_deflection = db.Column(db.Float)  # δ (mm)
    
    # ========================================================================
    # CALCULATION RESULTS - CAPACITIES
    # ========================================================================
    capacity_moment = db.Column(db.Float)  # φMn (kNm)
    capacity_shear = db.Column(db.Float)  # φVn (kN)
    deflection_limit = db.Column(db.Float)  # δ_limit (mm)
    
    # ========================================================================
    # CALCULATION RESULTS - UTILIZATION RATIOS
    # ========================================================================
    utilization_moment = db.Column(db.Float)  # M*/φMn
    utilization_shear = db.Column(db.Float)  # V*/φVn
    utilization_deflection = db.Column(db.Float)  # δ/δ_limit
    
    # ========================================================================
    # CALCULATION METADATA
    # ========================================================================
    calc_status = db.Column(db.String(20))  # "PASS", "WARNING", "FAIL"
    calc_version = db.Column(db.String(50))  # Version of calculation used
    calc_date = db.Column(db.DateTime)  # When calculation was performed
    
    # Legacy fields (kept for compatibility)
    calculation_standard = db.Column(db.String(50))  # e.g., "NZS3603:1993"
    calculation_version = db.Column(db.String(20))  # Deprecated - use calc_version
    max_moment = db.Column(db.Float)  # Deprecated - use demand_moment
    max_shear = db.Column(db.Float)  # Deprecated - use demand_shear
    
    # Product selection
    recommended_products = db.Column(db.JSON)  # Store recommendations as JSON
    selected_product_code = db.Column(db.String(50))
    
    # Record metadata
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
    
    @property
    def is_calculated(self):
        """Check if beam has been calculated"""
        return self.calc_date is not None
    
    @property
    def max_utilization(self):
        """Get maximum utilization ratio (worst case)"""
        utils = [
            self.utilization_moment or 0,
            self.utilization_shear or 0,
            self.utilization_deflection or 0
        ]
        return max(utils) if any(utils) else None
    
    @property
    def controlling_factor(self):
        """Get which factor controls the design"""
        if not self.is_calculated:
            return None
        
        utils = {
            'Bending': self.utilization_moment or 0,
            'Shear': self.utilization_shear or 0,
            'Deflection': self.utilization_deflection or 0
        }
        return max(utils, key=utils.get)
    
    def __repr__(self):
        return f'<Beam {self.name} in Project {self.project_id}>'
