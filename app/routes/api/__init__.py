"""
API routes for the application
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/hello', methods=['GET'])
def hello():
    """Hello World API endpoint"""
    return jsonify({
        'message': 'Hello World from LBDesign!',
        'status': 'success',
        'app': 'Lumberbank Design Calculator'
    })


@api_bp.route('/calculate-preview', methods=['POST'])
@login_required
def calculate_preview():
    """
    AJAX endpoint for real-time beam calculation preview
    PLACEHOLDER - returns dummy data until calculation engine is integrated
    """
    try:
        data = request.get_json()
        
        # Just return a simple response for now with CORRECT structure
        return jsonify({
            'status': 'PASS',
            'demand_moment': 25.5,
            'demand_shear': 12.3,
            'demand_deflection': 8.5,
            'capacity_moment': 45.0,
            'capacity_shear': 30.0,
            'deflection_limit': 15.0,
            'utilization_moment': 0.567,
            'utilization_shear': 0.410,
            'utilization_deflection': 0.567,
            'max_utilization': 0.567,
            'controlling_factor': 'Bending',
            'calc_version': 'PLACEHOLDER v0.1',
            'calc_date': '2024-11-30'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500