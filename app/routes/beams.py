"""
Beam routes - all using secure /projects/<project_id>/beams/<beam_id> pattern
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.database.repositories import ProjectRepository, BeamRepository

beams_bp = Blueprint('beams', __name__, url_prefix='/beams')


@beams_bp.route('/projects/<int:project_id>/beams/create', methods=['GET', 'POST'])
@beams_bp.route('/projects/<int:project_id>/beams/<int:beam_id>/edit', methods=['GET', 'POST'])
@login_required
def beam_form(project_id, beam_id=None):
    """Unified create/edit form"""
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
            return render_template('beams/design_form.html', project=project, beam=beam)
        
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
            return render_template('beams/design_form.html', project=project, beam=beam)
        
        if beam_id:
            # Update existing beam
            BeamRepository.update(
                beam,
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
            flash('Beam updated successfully!', 'success')
        else:
            # Create new beam
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
        
        return redirect(url_for('beams.detail', project_id=project_id, beam_id=beam.id))
    
    return render_template('beams/design_form.html', project=project, beam=beam)


@beams_bp.route('/projects/<int:project_id>/beams/<int:beam_id>')
@login_required
def detail(project_id, beam_id):
    """Show beam details"""
    beam = BeamRepository.get_by_id(beam_id)
    
    if not beam:
        flash('Beam not found', 'error')
        return redirect(url_for('projects.list'))
    
    # SECURITY: Verify beam belongs to this project
    if beam.project_id != project_id:
        flash('Beam not found', 'error')
        return redirect(url_for('projects.detail', project_id=project_id))
    
    project = beam.project
    
    # Check ownership
    if project.user_id != current_user.id and not current_user.has_role('ADMIN'):
        flash('Access denied', 'error')
        return redirect(url_for('projects.list'))
    
    return render_template('beams/detail.html', beam=beam, project=project)


@beams_bp.route('/projects/<int:project_id>/beams/<int:beam_id>/delete', methods=['POST'])
@login_required
def delete(project_id, beam_id):
    """Delete beam"""
    beam = BeamRepository.get_by_id(beam_id)
    
    if not beam:
        flash('Beam not found', 'error')
        return redirect(url_for('projects.list'))
    
    # SECURITY: Verify beam belongs to this project
    if beam.project_id != project_id:
        flash('Beam not found', 'error')
        return redirect(url_for('projects.detail', project_id=project_id))
    
    project = beam.project
    
    # Check ownership
    if project.user_id != current_user.id and not current_user.has_role('ADMIN'):
        flash('Access denied', 'error')
        return redirect(url_for('projects.list'))
    
    beam_name = beam.name
    BeamRepository.delete(beam)
    
    flash(f'Beam "{beam_name}" deleted successfully!', 'success')
    return redirect(url_for('projects.detail', project_id=project_id))