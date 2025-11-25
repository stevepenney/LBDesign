"""
Project routes
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.database.repositories import ProjectRepository, BeamRepository

projects_bp = Blueprint('projects', __name__, url_prefix='/projects')


@projects_bp.route('/')
@login_required
def list():
    """List all projects for current user"""
    projects = ProjectRepository.get_by_user(current_user.id)
    return render_template('projects/list.html', projects=projects)


@projects_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create new project"""
    if request.method == 'POST':
        name = request.form.get('name')
        region = request.form.get('region', 'new_zealand')
        
        # Optional fields
        address = request.form.get('address')
        client = request.form.get('client')
        engineer = request.form.get('engineer')
        architect = request.form.get('architect')
        merchant = request.form.get('merchant')
        project_number = request.form.get('project_number')
        project_type = request.form.get('project_type')
        
        if not name:
            flash('Project name is required', 'error')
            return render_template('projects/create.html')
        
        project = ProjectRepository.create_project(
            user_id=current_user.id,
            name=name,
            region=region,
            address=address,
            client=client,
            engineer=engineer,
            architect=architect,
            merchant=merchant,
            project_number=project_number,
            project_type=project_type
        )
        
        flash(f'Project "{name}" created successfully!', 'success')
        return redirect(url_for('projects.detail', project_id=project.id))
    
    return render_template('projects/create.html')


@projects_bp.route('/<int:project_id>')
@login_required
def detail(project_id):
    """Show project details and beams"""
    project = ProjectRepository.get_by_id(project_id)
    
    if not project:
        flash('Project not found', 'error')
        return redirect(url_for('projects.list'))
    
    # Check ownership or admin
    if project.user_id != current_user.id and not current_user.has_role('ADMIN'):
        flash('Access denied', 'error')
        return redirect(url_for('projects.list'))
    
    beams = BeamRepository.get_by_project(project_id)
    
    return render_template('projects/detail.html', project=project, beams=beams)


@projects_bp.route('/<int:project_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(project_id):
    """Edit project"""
    project = ProjectRepository.get_by_id(project_id)
    
    if not project:
        flash('Project not found', 'error')
        return redirect(url_for('projects.list'))
    
    # Check ownership or admin
    if project.user_id != current_user.id and not current_user.has_role('ADMIN'):
        flash('Access denied', 'error')
        return redirect(url_for('projects.list'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        region = request.form.get('region')
        
        if not name:
            flash('Project name is required', 'error')
            return render_template('projects/edit.html', project=project)
        
        ProjectRepository.update(
            project,
            name=name,
            region=region,
            address=request.form.get('address'),
            client=request.form.get('client'),
            engineer=request.form.get('engineer'),
            architect=request.form.get('architect'),
            merchant=request.form.get('merchant'),
            project_number=request.form.get('project_number'),
            project_type=request.form.get('project_type')
        )
        
        flash('Project updated successfully!', 'success')
        return redirect(url_for('projects.detail', project_id=project.id))
    
    return render_template('projects/edit.html', project=project)


@projects_bp.route('/<int:project_id>/delete', methods=['POST'])
@login_required
def delete(project_id):
    """Delete project"""
    project = ProjectRepository.get_by_id(project_id)
    
    if not project:
        flash('Project not found', 'error')
        return redirect(url_for('projects.list'))
    
    # Check ownership or admin
    if project.user_id != current_user.id and not current_user.has_role('ADMIN'):
        flash('Access denied', 'error')
        return redirect(url_for('projects.list'))
    
    project_name = project.name
    ProjectRepository.delete(project)
    
    flash(f'Project "{project_name}" deleted successfully!', 'success')
    return redirect(url_for('projects.list'))
