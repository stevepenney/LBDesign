"""
Beam routes
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.database.repositories import ProjectRepository, BeamRepository

beams_bp = Blueprint('beams', __name__, url_prefix='/beams')

@beams_bp.route('/projects/<int:project_id>/beams/create', methods=['GET', 'POST'])
@beams_bp.route('/projects/<int:project_id>/beams/<int:beam_id>/edit', methods=['GET', 'POST'])
@login_required
def beam_form(project_id, beam_id=None):
    """Show beam design form (create or edit)"""
    project = ProjectRepository.get_by_id(project_id)
    
    if not project:
        flash('Project not found', 'error')
        return redirect(url_for('projects.list'))
    
    # Check ownership
    if project.user_id != current_user.id and not current_user.has_role('ADMIN'):
        flash('Access denied', 'error')
        return redirect(url_for('projects.list'))
    
    beam = None
    if beam_id:
        beam = BeamRepository.get_by_id(beam_id)
        if not beam or beam.project_id != project_id:
            flash('Beam not found', 'error')
            return redirect(url_for('projects.detail', project_id=project_id))
    
    if request.method == 'POST':
        # Handle form submission
        # ... existing save logic ...
        pass
    
    return render_template('beams/design_form.html', 
                         project=project, 
                         beam=beam)

'''
@beams_bp.route('/project/<int:project_id>/create', methods=['GET', 'POST'])
@login_required
def create(project_id):
    """Create new beam in project"""
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
        reference = request.form.get('reference')
        member_type = request.form.get('member_type')
        span = request.form.get('span')
        spacing = request.form.get('spacing')
        
        # Load parameters
        dead_load = request.form.get('dead_load')
        live_load = request.form.get('live_load')
        point_load_1 = request.form.get('point_load_1')
        point_load_1_position = request.form.get('point_load_1_position')
        point_load_2 = request.form.get('point_load_2')
        point_load_2_position = request.form.get('point_load_2_position')
        
        # Validation
        if not all([name, member_type, span]):
            flash('Name, member type, and span are required', 'error')
            return render_template('beams/create.html', project=project)
        
        try:
            span = float(span)
            spacing = float(spacing) if spacing else None
            dead_load = float(dead_load) if dead_load else None
            live_load = float(live_load) if live_load else None
            point_load_1 = float(point_load_1) if point_load_1 else None
            point_load_1_position = float(point_load_1_position) if point_load_1_position else None
            point_load_2 = float(point_load_2) if point_load_2 else None
            point_load_2_position = float(point_load_2_position) if point_load_2_position else None
        except ValueError:
            flash('Invalid numeric values', 'error')
            return render_template('beams/create.html', project=project)
        
        beam = BeamRepository.create_beam(
            project_id=project_id,
            name=name,
            reference=reference,
            member_type=member_type,
            span=span,
            spacing=spacing,
            dead_load=dead_load,
            live_load=live_load,
            point_load_1=point_load_1,
            point_load_1_position=point_load_1_position,
            point_load_2=point_load_2,
            point_load_2_position=point_load_2_position
        )
        
        flash(f'Beam "{name}" created successfully!', 'success')
        return redirect(url_for('projects.detail', project_id=project_id))
    
    return render_template('beams/create.html', project=project)
'''
@beams_bp.route('/<int:beam_id>/calculate', methods=['POST'])
@login_required
def calculate(beam_id):
    """Calculate beam and update results"""
    from app.services.calculations import calculate_and_update_beam
    from app.extensions import db
    
    beam = BeamRepository.get_by_id(beam_id)
    
    if not beam:
        flash('Beam not found', 'error')
        return redirect(url_for('projects.list'))
    
    project = beam.project
    
    # Check ownership or admin
    if project.user_id != current_user.id and not current_user.has_role('ADMIN'):
        flash('Access denied', 'error')
        return redirect(url_for('projects.list'))
    
    try:
        # Run calculation
        updated_beam, results = calculate_and_update_beam(beam)
        db.session.commit()
        
        # Flash message based on status
        if results['calc_status'] == 'PASS':
            flash(f'✓ Calculation complete: {results["calc_status"]} - All checks passed!', 'success')
        elif results['calc_status'] == 'WARNING':
            flash(f'⚠ Calculation complete: {results["calc_status"]} - Some utilizations are high', 'warning')
        else:
            flash(f'✗ Calculation complete: {results["calc_status"]} - Member is overstressed', 'error')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Calculation error: {str(e)}', 'error')
    
    return redirect(url_for('beams.detail', beam_id=beam.id))

@beams_bp.route('/<int:beam_id>')
@login_required
def detail(beam_id):
    """Show beam details"""
    beam = BeamRepository.get_by_id(beam_id)
    
    if not beam:
        flash('Beam not found', 'error')
        return redirect(url_for('projects.list'))
    
    project = beam.project
    
    # Check ownership or admin
    if project.user_id != current_user.id and not current_user.has_role('ADMIN'):
        flash('Access denied', 'error')
        return redirect(url_for('projects.list'))
    
    return render_template('beams/detail.html', beam=beam, project=project)


@beams_bp.route('/<int:beam_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(beam_id):
    """Edit beam"""
    beam = BeamRepository.get_by_id(beam_id)
    
    if not beam:
        flash('Beam not found', 'error')
        return redirect(url_for('projects.list'))
    
    project = beam.project
    
    # Check ownership or admin
    if project.user_id != current_user.id and not current_user.has_role('ADMIN'):
        flash('Access denied', 'error')
        return redirect(url_for('projects.list'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        member_type = request.form.get('member_type')
        span = request.form.get('span')
        
        if not all([name, member_type, span]):
            flash('Name, member type, and span are required', 'error')
            return render_template('beams/edit.html', beam=beam, project=project)
        
        try:
            span = float(span)
            spacing = float(request.form.get('spacing')) if request.form.get('spacing') else None
            dead_load = float(request.form.get('dead_load')) if request.form.get('dead_load') else None
            live_load = float(request.form.get('live_load')) if request.form.get('live_load') else None
            point_load_1 = float(request.form.get('point_load_1')) if request.form.get('point_load_1') else None
            point_load_1_position = float(request.form.get('point_load_1_position')) if request.form.get('point_load_1_position') else None
            point_load_2 = float(request.form.get('point_load_2')) if request.form.get('point_load_2') else None
            point_load_2_position = float(request.form.get('point_load_2_position')) if request.form.get('point_load_2_position') else None
        except ValueError:
            flash('Invalid numeric values', 'error')
            return render_template('beams/edit.html', beam=beam, project=project)
        
        BeamRepository.update(
            beam,
            name=name,
            reference=request.form.get('reference'),
            member_type=member_type,
            span=span,
            spacing=spacing,
            dead_load=dead_load,
            live_load=live_load,
            point_load_1=point_load_1,
            point_load_1_position=point_load_1_position,
            point_load_2=point_load_2,
            point_load_2_position=point_load_2_position
        )
        
        flash('Beam updated successfully!', 'success')
        return redirect(url_for('beams.detail', beam_id=beam.id))
    
    return render_template('beams/edit.html', beam=beam, project=project)


@beams_bp.route('/<int:beam_id>/delete', methods=['POST'])
@login_required
def delete(beam_id):
    """Delete beam"""
    beam = BeamRepository.get_by_id(beam_id)
    
    if not beam:
        flash('Beam not found', 'error')
        return redirect(url_for('projects.list'))
    
    project = beam.project
    
    # Check ownership or admin
    if project.user_id != current_user.id and not current_user.has_role('ADMIN'):
        flash('Access denied', 'error')
        return redirect(url_for('projects.list'))
    
    project_id = project.id
    beam_name = beam.name
    BeamRepository.delete(beam)
    
    flash(f'Beam "{beam_name}" deleted successfully!', 'success')
    return redirect(url_for('projects.detail', project_id=project_id))
