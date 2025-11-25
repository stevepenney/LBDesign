"""
Beam repository
"""
from app.models.beam import Beam
from app.database.repositories.base_repository import BaseRepository


class BeamRepository(BaseRepository):
    """Repository for Beam operations"""
    
    model = Beam
    
    @classmethod
    def get_by_project(cls, project_id):
        """Get all beams for a specific project"""
        return Beam.query.filter_by(project_id=project_id)\
            .order_by(Beam.created_at).all()
    
    @classmethod
    def create_beam(cls, project_id, name, member_type, span, **kwargs):
        """Create new beam"""
        return cls.create(
            project_id=project_id,
            name=name,
            member_type=member_type,
            span=span,
            **kwargs
        )
    
    @classmethod
    def get_by_reference(cls, project_id, reference):
        """Get beam by reference code within a project"""
        return Beam.query.filter_by(
            project_id=project_id,
            reference=reference
        ).first()
    
    @classmethod
    def get_by_type(cls, project_id, member_type):
        """Get all beams of a specific type in a project"""
        return Beam.query.filter_by(
            project_id=project_id,
            member_type=member_type
        ).all()
    
    @classmethod
    def update_calculation_results(cls, beam, results):
        """Update beam with calculation results"""
        return cls.update(
            beam,
            calculation_standard=results.get('standard'),
            calculation_version=results.get('version'),
            max_moment=results.get('max_moment'),
            max_shear=results.get('max_shear'),
            deflection_limit=results.get('deflection_limit'),
            recommended_products=results.get('recommendations')
        )
