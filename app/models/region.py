"""
Region model for location-based standards
"""
from app.extensions import db
from datetime import datetime


class Region(db.Model):
    """Geographic regions with applicable standards"""
    __tablename__ = 'regions'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    code = db.Column(db.String(10), unique=True, nullable=False)  # e.g., 'NZ', 'AU'
    
    # Standards applicable to this region (JSON stored as text)
    standards = db.Column(db.Text)  # JSON: ["AS/NZS1170", "NZS3603"]
    
    # Default parameters for the region (JSON stored as text)
    default_parameters = db.Column(db.Text)  # JSON: {"wind_zones": [...], "snow_zones": [...]}
    
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    projects = db.relationship('Project', backref='region', lazy='dynamic')
    
    def __repr__(self):
        return f'<Region {self.name}>'
    
    @staticmethod
    def init_regions():
        """Initialize default regions"""
        import json
        
        regions_data = [
            {
                'name': 'New Zealand',
                'code': 'NZ',
                'standards': json.dumps(['AS/NZS1170', 'NZS3603']),
                'default_parameters': json.dumps({
                    'wind_zones': ['Low', 'Medium', 'High', 'Very High', 'Extra High'],
                    'snow_zones': ['None', 'Low', 'Medium', 'High']
                })
            },
            {
                'name': 'Australia',
                'code': 'AU',
                'standards': json.dumps(['AS/NZS1170', 'AS1684']),
                'default_parameters': json.dumps({
                    'wind_zones': ['A', 'B', 'C', 'D'],
                    'cyclone_zones': ['A', 'B', 'C', 'D']
                })
            }
        ]
        
        for region_data in regions_data:
            region = Region.query.filter_by(code=region_data['code']).first()
            if region is None:
                region = Region(**region_data)
                db.session.add(region)
        
        db.session.commit()
