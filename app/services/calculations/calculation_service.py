"""
Calculation Service
Orchestrates structural mechanics and design factors to perform beam analysis
"""
from datetime import datetime
from app.services.calculations.structural_mechanics import BeamFormulas
from app.services.calculations.design_factors import DesignFactors, get_version_info


class BeamCalculationService:
    """
    Service for performing complete beam calculations
    Combines structural mechanics (demands) with design factors (capacities)
    """
    
    def __init__(self):
        self.version_info = get_version_info()
    
    def calculate_beam(self, beam, section_properties=None):
        """
        Perform complete beam calculation
        
        Args:
            beam: Beam model instance with input parameters
            section_properties: Optional dict with section properties
                               If None, uses placeholder rectangular section
            
        Returns:
            Dictionary with all calculation results
        """
        # Extract beam parameters
        span = beam.span  # meters
        dead_load = beam.dead_load or 0  # kN/m or kPa
        live_load = beam.live_load or 0  # kN/m or kPa
        spacing = beam.spacing or 1.0  # meters (for distributed loads)
        
        # Convert distributed loads to line loads if spacing is provided
        w_dead = dead_load * spacing  # kN/m
        w_live = live_load * spacing  # kN/m
        w_total = w_dead + w_live  # kN/m
        
        # Point loads
        point_loads = []
        if beam.point_load_1 and beam.point_load_1_position:
            point_loads.append((beam.point_load_1, beam.point_load_1_position))
        if beam.point_load_2 and beam.point_load_2_position:
            point_loads.append((beam.point_load_2, beam.point_load_2_position))
        
        # ========================================================================
        # STEP 1: Calculate Demands (Structural Mechanics)
        # ========================================================================
        
        # Bending moment
        if point_loads:
            M_star = BeamFormulas.moment_combined_udl_and_points(w_total, span, point_loads)
        else:
            M_star = BeamFormulas.moment_simple_udl(w_total, span)
        
        # Shear force
        if point_loads:
            V_star = BeamFormulas.shear_combined(w_total, span, point_loads)
        else:
            V_star = BeamFormulas.shear_simple_udl(w_total, span)
        
        # ========================================================================
        # STEP 2: Get Section Properties (Placeholder)
        # ========================================================================
        
        if section_properties is None:
            # PLACEHOLDER: Assume a typical 300x45 LVL section
            # In future, this will come from product database
            section_properties = DesignFactors.get_section_properties_placeholder(
                depth=300,  # mm
                width=45    # mm
            )
        
        # Material properties (PLACEHOLDER - use LVL)
        E = DesignFactors.E_LVL  # MPa
        f_b = DesignFactors.F_B_LVL  # MPa
        f_s = DesignFactors.F_S_LVL  # MPa
        
        # ========================================================================
        # STEP 3: Calculate Deflection Demand
        # ========================================================================
        
        # Deflection under live load only (typical check)
        if point_loads:
            # Simplified: use UDL formula (conservative)
            delta_demand = BeamFormulas.deflection_simple_udl(
                w_live, span, E, section_properties['I']
            )
        else:
            delta_demand = BeamFormulas.deflection_simple_udl(
                w_live, span, E, section_properties['I']
            )
        
        # Deflection limit
        member_type = beam.member_type
        if 'floor' in member_type.lower() or 'joist' in member_type.lower():
            ratio = DesignFactors.DEFLECTION_LIMIT_FLOOR
        elif 'rafter' in member_type.lower() or 'roof' in member_type.lower():
            ratio = DesignFactors.DEFLECTION_LIMIT_ROOF
        else:
            ratio = DesignFactors.DEFLECTION_LIMIT_FLOOR  # Default
        
        delta_limit = BeamFormulas.deflection_limit_span_ratio(span, ratio)
        
        # ========================================================================
        # STEP 4: Calculate Capacities (Design Factors)
        # ========================================================================
        
        # Get modification factors (assuming medium-term, dry, normal temp)
        k_factors = DesignFactors.get_modification_factors(
            load_type='medium_term',
            condition='dry',
            temperature='normal'
        )
        
        # Moment capacity
        phi_M_n = DesignFactors.moment_capacity(
            Z=section_properties['Z'],
            f_b=f_b,
            k1=k_factors['k1'],
            k4=k_factors['k4'],
            k6=k_factors['k6']
        )
        
        # Shear capacity
        phi_V_n = DesignFactors.shear_capacity(
            A=section_properties['A_shear'],
            f_s=f_s,
            k1=k_factors['k1'],
            k4=k_factors['k4'],
            k6=k_factors['k6']
        )
        
        # ========================================================================
        # STEP 5: Calculate Utilization Ratios
        # ========================================================================
        
        util_moment = BeamFormulas.utilization_ratio(M_star, phi_M_n)
        util_shear = BeamFormulas.utilization_ratio(V_star, phi_V_n)
        util_deflection = BeamFormulas.utilization_ratio(delta_demand, delta_limit)
        
        # Overall status (worst case)
        max_util = max(util_moment, util_shear, util_deflection)
        status = BeamFormulas.check_status(max_util)
        
        # ========================================================================
        # STEP 6: Package Results
        # ========================================================================
        
        results = {
            # Demands
            'demand_moment': round(M_star, 2),
            'demand_shear': round(V_star, 2),
            'demand_deflection': round(delta_demand, 2),
            
            # Capacities
            'capacity_moment': round(phi_M_n, 2),
            'capacity_shear': round(phi_V_n, 2),
            'deflection_limit': round(delta_limit, 2),
            
            # Utilization ratios
            'utilization_moment': round(util_moment, 3),
            'utilization_shear': round(util_shear, 3),
            'utilization_deflection': round(util_deflection, 3),
            
            # Status
            'calc_status': status,
            'calc_version': self.version_info['version'],
            'calc_date': datetime.utcnow(),
            
            # Section properties used (for reference)
            'section_used': {
                'depth': section_properties['depth'],
                'width': section_properties['width'],
                'material': 'LVL (placeholder)',
                'E': E,
                'f_b': f_b,
                'f_s': f_s
            }
        }
        
        return results
    
    def update_beam_with_results(self, beam, results):
        """
        Update beam model with calculation results
        
        Args:
            beam: Beam model instance
            results: Dictionary from calculate_beam()
            
        Returns:
            Updated beam instance (not yet saved to database)
        """
        # Update demands
        beam.demand_moment = results['demand_moment']
        beam.demand_shear = results['demand_shear']
        beam.demand_deflection = results['demand_deflection']
        
        # Update capacities
        beam.capacity_moment = results['capacity_moment']
        beam.capacity_shear = results['capacity_shear']
        beam.deflection_limit = results['deflection_limit']
        
        # Update utilization ratios
        beam.utilization_moment = results['utilization_moment']
        beam.utilization_shear = results['utilization_shear']
        beam.utilization_deflection = results['utilization_deflection']
        
        # Update metadata
        beam.calc_status = results['calc_status']
        beam.calc_version = results['calc_version']
        beam.calc_date = results['calc_date']
        
        return beam


# Convenience function for use in routes
def calculate_and_update_beam(beam):
    """
    Calculate beam and update with results
    
    Args:
        beam: Beam model instance
        
    Returns:
        Tuple of (updated_beam, results_dict)
    """
    service = BeamCalculationService()
    results = service.calculate_beam(beam)
    updated_beam = service.update_beam_with_results(beam, results)
    return updated_beam, results
