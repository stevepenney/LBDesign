"""
Product model for structural members catalog
"""
from app.extensions import db
from datetime import datetime


class Product(db.Model):
    """Structural product catalog"""
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(200), nullable=False)
    
    # Product classification
    manufacturer = db.Column(db.String(100))  # 'Lumberbank', 'Other'
    product_type = db.Column(db.String(50), nullable=False)  # 'I-Beam', 'LVL', 'Glulam', 'SG8'
    
    # Specifications (JSON stored as text)
    specifications = db.Column(db.Text, nullable=False)  
    # JSON: {
    #   "depth": 300,
    #   "width": 45,
    #   "grade": "LVL11",
    #   "section_properties": {...},
    #   "material_properties": {...}
    # }
    
    # Region availability (JSON stored as text)
    region_availability = db.Column(db.Text)  # JSON: ["NZ", "AU"]
    
    # Pricing (optional)
    unit_price = db.Column(db.Numeric(10, 2))
    price_unit = db.Column(db.String(20))  # 'per_meter', 'per_unit'
    
    # Status
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Product {self.code}>'
    
    @staticmethod
    def init_sample_products():
        """Initialize sample products for testing"""
        import json
        
        sample_products = [
            {
                'code': 'LWX-300',
                'name': 'Lumberworx I-Beam 300mm',
                'manufacturer': 'Lumberbank',
                'product_type': 'I-Beam',
                'specifications': json.dumps({
                    'depth': 300,
                    'flange_width': 89,
                    'web_thickness': 11,
                    'weight': 6.8,
                    'section_modulus': 450000
                }),
                'region_availability': json.dumps(['NZ']),
                'is_active': True
            },
            {
                'code': 'LVL-400x45',
                'name': 'LVL 400x45 Grade 11',
                'manufacturer': 'Other',
                'product_type': 'LVL',
                'specifications': json.dumps({
                    'depth': 400,
                    'width': 45,
                    'grade': 'LVL11',
                    'density': 580,
                    'bending_strength': 48
                }),
                'region_availability': json.dumps(['NZ', 'AU']),
                'is_active': True
            }
        ]
        
        for product_data in sample_products:
            product = Product.query.filter_by(code=product_data['code']).first()
            if product is None:
                product = Product(**product_data)
                db.session.add(product)
        
        db.session.commit()
