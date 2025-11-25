"""
Authentication routes
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.database.repositories import UserRepository

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('projects.list'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = UserRepository.get_by_username(username)
        
        if user and user.check_password(password):
            if not user.is_active:
                flash('Account is deactivated. Please contact administrator.', 'error')
                return redirect(url_for('auth.login'))
            
            login_user(user)
            UserRepository.update_last_login(user)
            
            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('projects.list')
            
            return redirect(next_page)
        
        flash('Invalid username or password', 'error')
    
    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if current_user.is_authenticated:
        return redirect(url_for('projects.list'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validation
        if not all([username, email, password, confirm_password]):
            flash('All fields are required', 'error')
            return render_template('auth/register.html')
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('auth/register.html')
        
        if UserRepository.get_by_username(username):
            flash('Username already exists', 'error')
            return render_template('auth/register.html')
        
        if UserRepository.get_by_email(email):
            flash('Email already registered', 'error')
            return render_template('auth/register.html')
        
        # Create user
        UserRepository.create_user(username, email, password, role='DETAILER')
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')
