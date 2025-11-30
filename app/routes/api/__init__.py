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
        
        # Just return a simple response for now
        return jsonify({
            'status': 'PASS',
            'demands': {
                'moment': 25.5,
                'shear': 12.3,
                'deflection': 8.5
            },
            'capacities': {
                'moment': 45.0,
                'shear': 30.0,
                'deflection': 15.0
            },
            'utilizations': {
                'bending': 0.567,
                'shear': 0.410,
                'deflection': 0.567
            },
            'max_utilization': 0.567,
            'controlling_factor': 'Bending',
            'recommended_member': 'LVL 300x45 Grade 11',
            'calculation_version': 'PLACEHOLDER',
            'calculation_date': '2024-11-30'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500