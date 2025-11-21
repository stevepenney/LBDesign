"""
Web routes for the application
"""
from flask import Blueprint, render_template

bp = Blueprint('web', __name__)


@bp.route('/')
def index():
    """Landing page"""
    return render_template('index.html')
