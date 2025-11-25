"""
Admin routes for user and system management
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from functools import wraps
from app.database.repositories import UserRepository
from app.extensions import db

admin_bp = Blueprint('user_admin', __name__, url_prefix='/admin')


def admin_required(f):
    """Decorator to require ADMIN or SUPERUSER role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('auth.login'))
        if not current_user.has_role('ADMIN'):
            flash('Access denied. Admin privileges required.', 'error')
            return redirect(url_for('projects.list'))
        return f(*args, **kwargs)
    return decorated_function


@admin_bp.route('/')
@admin_required
def dashboard():
    """Admin dashboard"""
    from app.models import User, Project, Beam
    
    # Get statistics
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    total_projects = Project.query.count()
    total_beams = Beam.query.count()
    
    # Get recent users
    recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         active_users=active_users,
                         total_projects=total_projects,
                         total_beams=total_beams,
                         recent_users=recent_users)


@admin_bp.route('/users')
@admin_required
def users():
    """List all users"""
    all_users = UserRepository.get_all()
    return render_template('admin/users.html', users=all_users)


@admin_bp.route('/users/create', methods=['GET', 'POST'])
@admin_required
def create_user():
    """Create new user"""
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'USER')
        
        # Validation
        if not all([username, email, password]):
            flash('Username, email, and password are required.', 'error')
            return render_template('admin/user_form.html')
        
        if UserRepository.get_by_username(username):
            flash('Username already exists.', 'error')
            return render_template('admin/user_form.html')
        
        if UserRepository.get_by_email(email):
            flash('Email already registered.', 'error')
            return render_template('admin/user_form.html')
        
        # Create user
        UserRepository.create_user(username, email, password, role)
        flash(f'User "{username}" created successfully!', 'success')
        return redirect(url_for('admin.users'))
    
    return render_template('admin/user_form.html', user=None)


@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    """Edit user"""
    user = UserRepository.get_by_id(user_id)
    
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin.users'))
    
    if request.method == 'POST':
        email = request.form.get('email')
        role = request.form.get('role')
        is_active = request.form.get('is_active') == 'on'
        
        # Check email uniqueness (excluding current user)
        existing_user = UserRepository.get_by_email(email)
        if existing_user and existing_user.id != user_id:
            flash('Email already in use by another user.', 'error')
            return render_template('admin/user_form.html', user=user)
        
        # Update user
        UserRepository.update(user, email=email, role=role, is_active=is_active)
        
        # Update password if provided
        new_password = request.form.get('password')
        if new_password:
            user.set_password(new_password)
            db.session.commit()
        
        flash(f'User "{user.username}" updated successfully!', 'success')
        return redirect(url_for('admin.users'))
    
    return render_template('admin/user_form.html', user=user)


@admin_bp.route('/users/<int:user_id>/toggle-active', methods=['POST'])
@admin_required
def toggle_user_active(user_id):
    """Toggle user active status"""
    user = UserRepository.get_by_id(user_id)
    
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin.users'))
    
    if user.id == current_user.id:
        flash('Cannot deactivate your own account.', 'error')
        return redirect(url_for('admin.users'))
    
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'activated' if user.is_active else 'deactivated'
    flash(f'User "{user.username}" {status}.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Delete user"""
    if not current_user.has_role('SUPERUSER'):
        flash('Only SUPERUSER can delete users.', 'error')
        return redirect(url_for('admin.users'))
    
    user = UserRepository.get_by_id(user_id)
    
    if not user:
        flash('User not found.', 'error')
        return redirect(url_for('admin.users'))
    
    if user.id == current_user.id:
        flash('Cannot delete your own account.', 'error')
        return redirect(url_for('admin.users'))
    
    username = user.username
    UserRepository.delete(user)
    flash(f'User "{username}" deleted.', 'success')
    return redirect(url_for('admin.users'))
