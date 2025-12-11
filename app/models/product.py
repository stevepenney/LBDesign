"""
Product model - Structural members (I-beams, timber, LVL, glulam)
"""
from datetime import datetime
from app.extensions import db


class Product(db.Model):
    """Product model for structural members with geometric and material properties"""
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # ========================================================================
    # IDENTIFICATION
    # ========================================================================
    product_code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.String(200), nullable=False)
    manufacturer = db.Column(db.String(100))  # "Lumberbank", "Nelson Pine", etc.
    product_type = db.Column(db.String(20), nullable=False)  # "I_BEAM", "SOLID_TIMBER", "LVL", "GLULAM"
    
    # ========================================================================
    # GEOMETRIC PROPERTIES - DIMENSIONS
    # ========================================================================
    depth = db.Column(db.Float, nullable=False)  # mm (overall depth)
    
    # For I-beams
    width_top = db.Column(db.Float)  # mm (top flange width)
    width_bottom = db.Column(db.Float)  # mm (bottom flange width)
    flange_thickness = db.Column(db.Float)  # mm
    web_thickness = db.Column(db.Float)  # mm
    
    # For rectangular sections (timber, LVL, glulam)
    width = db.Column(db.Float)  # mm (for rectangular sections)
    
    # ========================================================================
    # GEOMETRIC PROPERTIES - CALCULATED
    # ========================================================================
    Ixx = db.Column(db.Float, nullable=False)  # mm⁴ (second moment of area - strong axis)
    Iyy = db.Column(db.Float)  # mm⁴ (second moment of area - weak axis, optional)
    Zxx = db.Column(db.Float, nullable=False)  # mm³ (section modulus - strong axis)
    Zyy = db.Column(db.Float)  # mm³ (section modulus - weak axis, optional)
    A_gross = db.Column(db.Float, nullable=False)  # mm² (gross cross-sectional area)
    A_shear = db.Column(db.Float, nullable=False)  # mm² (effective shear area)
    
    # ========================================================================
    # MATERIAL PROPERTIES
    # ========================================================================
    E = db.Column(db.Float, nullable=False)  # MPa (modulus of elasticity)
    f_b = db.Column(db.Float, nullable=False)  # MPa (characteristic bending strength)
    f_s = db.Column(db.Float, nullable=False)  # MPa (characteristic shear strength)
    f_t = db.Column(db.Float)  # MPa (characteristic tension strength, optional)
    f_c = db.Column(db.Float)  # MPa (characteristic compression strength, optional)
    
    # ========================================================================
    # DURABILITY & AVAILABILITY
    # ========================================================================
    durability_class = db.Column(db.String(10))  # "H1.2", "H3.2", etc.
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    
    # ========================================================================
    # METADATA
    # ========================================================================
    notes = db.Column(db.Text)  # Any additional notes
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, 
                          onupdate=datetime.utcnow, nullable=False)
    
    # ========================================================================
    # PROPERTIES & VALIDATION
    # ========================================================================
    
    @property
    def is_i_beam(self):
        """Check if product is an I-beam"""
        return self.product_type == 'I_BEAM'
    
    @property
    def is_rectangular(self):
        """Check if product is a rectangular section"""
        return self.product_type in ['SOLID_TIMBER', 'LVL', 'GLULAM']
    
    @property
    def display_dimensions(self):
        """Return human-readable dimension string"""
        if self.is_i_beam:
            return f"D={self.depth}mm, Flanges={self.width_top}x{self.flange_thickness}mm, Web={self.web_thickness}mm"
        else:
            return f"{self.depth}x{self.width}mm"
    
    @property
    def material_grade(self):
        """Extract material grade from description or product type"""
        # E.g., "E8", "E11", "E13", "SG8", "GL13"
        if 'E8' in self.description or 'E8' in self.product_code:
            return 'E8'
        elif 'E11' in self.description or 'E11' in self.product_code:
            return 'E11'
        elif 'E13' in self.description or 'E13' in self.product_code:
            return 'E13'
        elif 'SG8' in self.description or 'SG8' in self.product_code:
            return 'SG8'
        elif 'GL13' in self.description or 'GL13' in self.product_code:
            return 'GL13'
        elif 'GL17' in self.description or 'GL17' in self.product_code:
            return 'GL17'
        return None
    
    def __repr__(self):
        return f'<Product {self.product_code}: {self.description}>'
