"""
API routes for the application
"""
from flask import Blueprint, jsonify

bp = Blueprint('api', __name__)


@bp.route('/hello', methods=['GET'])
def hello():
    """Hello World API endpoint"""
    return jsonify({
        'message': 'Hello World from LBDesign!',
        'status': 'success',
        'app': 'Lumberbank Design Calculator'
    })
