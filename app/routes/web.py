"""
Web routes for the application
"""
from flask import Blueprint, render_template
from flask_login import login_required, current_user

bp = Blueprint('web', __name__)


@bp.route('/')
def index():
    """Landing page"""
    return render_template('index.html')


@bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard - requires login"""
    return render_template('dashboard.html')
