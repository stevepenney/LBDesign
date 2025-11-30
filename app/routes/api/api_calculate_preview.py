"""
API endpoint for beam calculation preview
Add this to app/routes/api.py or create as new blueprint
"""

from flask import Blueprint, request, jsonify
from flask_login import login_required
from app.services.calculations.calculation_service import calculate_beam_preview

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/calculate-preview', methods=['POST'])
@login_required
def calculate_preview():
    """
    AJAX endpoint for real-time beam calculation preview
    Does NOT save to database - just returns results
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required = ['member_type', 'span', 'dead_load', 'live_load']
        for field in required:
            if field not in data:
                return jsonify({
                    'error': f'Missing required field: {field}'
                }), 400
        
        # Extract parameters
        member_type = data['member_type']
        span = float(data['span'])
        spacing = float(data.get('spacing', 0.4))
        dead_load = float(data['dead_load'])
        live_load = float(data['live_load'])
        point_loads = data.get('point_loads', [])
        supports = data.get('supports', [
            {'position': 0.0, 'type': 'pinned'},
            {'position': span, 'type': 'pinned'}
        ])
        
        # Build beam parameters dictionary
        beam_params = {
            'member_type': member_type,
            'span': span,
            'spacing': spacing,
            'dead_load': dead_load,
            'live_load': live_load,
            'supports': supports,
            'point_loads': point_loads
        }
        
        # Calculate
        results = calculate_beam_preview(beam_params)
        
        # Return results
        return jsonify(results), 200
        
    except ValueError as e:
        return jsonify({
            'error': f'Invalid input: {str(e)}'
        }), 400
        
    except Exception as e:
        return jsonify({
            'error': f'Calculation error: {str(e)}'
        }), 500


def calculate_beam_preview(params):
    """
    Calculate beam without saving to database
    
    Args:
        params: Dict with all beam parameters
        
    Returns:
        Dict with calculation results
    """
    from app.services.calculations.structural_mechanics import BeamFormulas
    from app.services.calculations.design_factors import NZS3603
    from datetime import datetime
    
    # Extract parameters
    span = params['span']
    spacing = params.get('spacing', 0.4)
    dead_load = params['dead_load']
    live_load = params['live_load']
    point_loads = params.get('point_loads', [])
    supports = params.get('supports', [])
    
    # Calculate UDL
    total_kPa = dead_load + live_load
    udl = total_kPa * spacing  # kN/m
    
    # Determine beam configuration
    num_supports = len(supports)
    
    if num_supports == 2:
        # Simply supported
        # Calculate demands
        M_udl = BeamFormulas.moment_simple_udl(udl, span)
        V_udl = BeamFormulas.shear_simple_udl(udl, span)
        
        # Add point loads
        M_total = M_udl
        V_total = V_udl
        
        for pl in point_loads:
            mag = pl['magnitude']
            pos = pl['position']
            M_total += BeamFormulas.moment_point_offset(mag, span, pos)
            V_total = max(V_total, BeamFormulas.shear_point_load(mag, span, pos))
        
    elif num_supports > 2:
        # Continuous beam - use conservative approximation
        # TODO: Implement proper continuous beam analysis
        # For now, treat as simply supported with 0.8 factor
        M_simple = BeamFormulas.moment_simple_udl(udl, span)
        M_total = M_simple * 0.8
        V_total = BeamFormulas.shear_simple_udl(udl, span)
        
    else:
        return {
            'error': 'Invalid support configuration',
            'status': 'FAIL'
        }
    
    # Get section properties (PLACEHOLDER - 300x45 LVL)
    section_props = NZS3603.get_section_properties('300x45_LVL')
    
    # Calculate capacities
    phi_M = NZS3603.moment_capacity(
        section_props['f_b'],
        section_props['Z'],
        k1=1.0,  # TODO: Get from load duration
        k4=1.0,
        k6=1.0
    )
    
    phi_V = NZS3603.shear_capacity(
        section_props['f_s'],
        section_props['A'],
        k1=1.0,
        k4=1.0,
        k6=1.0
    )
    
    # Calculate deflection (simplified - live load only)
    E = section_props['E']
    I = section_props['I']
    
    delta_live = BeamFormulas.deflection_simple_udl(
        live_load * spacing,  # Live load component only
        span,
        E,
        I
    )
    
    # Get deflection limit
    delta_limit = NZS3603.get_deflection_limit(span, 'floor')
    
    # Calculate utilization ratios
    util_M = M_total / phi_M if phi_M > 0 else 999
    util_V = V_total / phi_V if phi_V > 0 else 999
    util_delta = delta_live / delta_limit if delta_limit > 0 else 999
    
    # Determine status
    max_util = max(util_M, util_V, util_delta)
    
    if max_util > 1.0:
        status = 'FAIL'
    elif max_util > 0.9:
        status = 'WARNING'
    else:
        status = 'PASS'
    
    # Find controlling factor
    if util_M == max_util:
        controlling = 'Bending'
    elif util_V == max_util:
        controlling = 'Shear'
    else:
        controlling = 'Deflection'
    
    # Return results
    return {
        'status': status,
        'demand_moment': M_total,
        'demand_shear': V_total,
        'demand_deflection': delta_live,
        'capacity_moment': phi_M,
        'capacity_shear': phi_V,
        'deflection_limit': delta_limit,
        'utilization_moment': util_M,
        'utilization_shear': util_V,
        'utilization_deflection': util_delta,
        'max_utilization': max_util,
        'controlling_factor': controlling,
        'calc_version': NZS3603.VERSION,
        'calc_date': datetime.now().isoformat()
    }
