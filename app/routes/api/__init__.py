
"""
API routes for the application
"""
from flask import Blueprint, jsonify

bp = Blueprint('api', __name__)


@bp.route('/db-test', methods=['GET'])
def db_test():
    """Test database connection"""
    from app.extensions import db
    from app.models import User, Role, Product, Region
    
    try:
        # Try to query the database
        user_count = User.query.count()
        role_count = Role.query.count()
        product_count = Product.query.count()
        region_count = Region.query.count()
        
        return jsonify({
            'status': 'success',
            'message': 'Database connection successful!',
            'database_type': db.engine.name,
            'counts': {
                'users': user_count,
                'roles': role_count,
                'products': product_count,
                'regions': region_count
            }
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Database error: {str(e)}'
        }), 500