"""
Section Properties Calculator
Utilities for calculating geometric properties of structural sections
"""


class SectionProperties:
    """Calculate geometric properties for different section types"""
    
    # ========================================================================
    # RECTANGULAR SECTIONS (Timber, LVL, Glulam)
    # ========================================================================
    
    @staticmethod
    def rectangular_section(depth, width):
        """
        Calculate properties for rectangular section
        
        Args:
            depth: Section depth (mm)
            width: Section width (mm)
            
        Returns:
            Dictionary with geometric properties
        """
        # Cross-sectional area
        A_gross = width * depth  # mm²
        
        # Second moment of area (strong axis - bending about horizontal axis)
        Ixx = (width * depth**3) / 12  # mm⁴
        
        # Second moment of area (weak axis - bending about vertical axis)
        Iyy = (depth * width**3) / 12  # mm⁴
        
        # Section modulus (strong axis)
        Zxx = (width * depth**2) / 6  # mm³
        
        # Section modulus (weak axis)
        Zyy = (depth * width**2) / 6  # mm³
        
        # Effective shear area (2/3 of gross area for rectangular sections)
        A_shear = (2/3) * A_gross  # mm²
        
        return {
            'A_gross': round(A_gross, 2),
            'A_shear': round(A_shear, 2),
            'Ixx': round(Ixx, 2),
            'Iyy': round(Iyy, 2),
            'Zxx': round(Zxx, 2),
            'Zyy': round(Zyy, 2)
        }
    
    # ========================================================================
    # I-BEAM SECTIONS
    # ========================================================================
    
    @staticmethod
    def i_beam_section(depth, width_top, width_bottom, flange_thickness, web_thickness):
        """
        Calculate properties for I-beam section
        
        Args:
            depth: Overall depth (mm)
            width_top: Top flange width (mm)
            width_bottom: Bottom flange width (mm)
            flange_thickness: Flange thickness (mm)
            web_thickness: Web thickness (mm)
            
        Returns:
            Dictionary with geometric properties
        """
        # Component dimensions
        web_height = depth - 2 * flange_thickness
        
        # Areas
        A_top_flange = width_top * flange_thickness
        A_bottom_flange = width_bottom * flange_thickness
        A_web = web_height * web_thickness
        A_gross = A_top_flange + A_bottom_flange + A_web
        
        # Centroid (measured from bottom)
        y_top_flange = depth - flange_thickness / 2
        y_bottom_flange = flange_thickness / 2
        y_web = depth / 2
        
        y_bar = (A_top_flange * y_top_flange + 
                 A_bottom_flange * y_bottom_flange + 
                 A_web * y_web) / A_gross
        
        # Second moment of area about centroid (parallel axis theorem)
        # Top flange
        I_top_flange_own = (width_top * flange_thickness**3) / 12
        d_top = y_top_flange - y_bar
        I_top_flange = I_top_flange_own + A_top_flange * d_top**2
        
        # Bottom flange
        I_bottom_flange_own = (width_bottom * flange_thickness**3) / 12
        d_bottom = y_bottom_flange - y_bar
        I_bottom_flange = I_bottom_flange_own + A_bottom_flange * d_bottom**2
        
        # Web
        I_web_own = (web_thickness * web_height**3) / 12
        d_web = y_web - y_bar
        I_web = I_web_own + A_web * d_web**2
        
        Ixx = I_top_flange + I_bottom_flange + I_web
        
        # Section modulus (use distance to extreme fiber)
        c_top = depth - y_bar
        c_bottom = y_bar
        Z_top = Ixx / c_top
        Z_bottom = Ixx / c_bottom
        Zxx = min(Z_top, Z_bottom)  # Governing (smaller) value
        
        # Weak axis properties (simplified - assumes symmetry)
        Iyy_top = (flange_thickness * width_top**3) / 12
        Iyy_bottom = (flange_thickness * width_bottom**3) / 12
        Iyy_web = (web_height * web_thickness**3) / 12
        Iyy = Iyy_top + Iyy_bottom + Iyy_web
        
        Zyy_top = Iyy_top / (width_top / 2)
        Zyy_bottom = Iyy_bottom / (width_bottom / 2)
        Zyy = min(Zyy_top, Zyy_bottom)
        
        # Effective shear area (web area for I-beams)
        A_shear = A_web
        
        return {
            'A_gross': round(A_gross, 2),
            'A_shear': round(A_shear, 2),
            'Ixx': round(Ixx, 2),
            'Iyy': round(Iyy, 2),
            'Zxx': round(Zxx, 2),
            'Zyy': round(Zyy, 2),
            'y_bar': round(y_bar, 2)  # Centroid location from bottom
        }
    
    # ========================================================================
    # VALIDATION
    # ========================================================================
    
    @staticmethod
    def validate_rectangular(depth, width):
        """Validate rectangular section inputs"""
        errors = []
        
        if depth <= 0:
            errors.append("Depth must be positive")
        if width <= 0:
            errors.append("Width must be positive")
        if depth < width:
            errors.append("Warning: Depth is less than width (unusual for strong axis bending)")
            
        return errors
    
    @staticmethod
    def validate_i_beam(depth, width_top, width_bottom, flange_thickness, web_thickness):
        """Validate I-beam section inputs"""
        errors = []
        
        if depth <= 0:
            errors.append("Depth must be positive")
        if width_top <= 0:
            errors.append("Top flange width must be positive")
        if width_bottom <= 0:
            errors.append("Bottom flange width must be positive")
        if flange_thickness <= 0:
            errors.append("Flange thickness must be positive")
        if web_thickness <= 0:
            errors.append("Web thickness must be positive")
        
        # Check proportions
        if 2 * flange_thickness >= depth:
            errors.append("Flange thickness too large for overall depth")
        if web_thickness > min(width_top, width_bottom):
            errors.append("Web thickness exceeds flange width")
            
        return errors


# Convenience functions for use in forms/routes
def calculate_rectangular_properties(depth, width):
    """Calculate properties for rectangular section with validation"""
    errors = SectionProperties.validate_rectangular(depth, width)
    if errors:
        return None, errors
    return SectionProperties.rectangular_section(depth, width), []


def calculate_i_beam_properties(depth, width_top, width_bottom, flange_thickness, web_thickness):
    """Calculate properties for I-beam section with validation"""
    errors = SectionProperties.validate_i_beam(depth, width_top, width_bottom, 
                                              flange_thickness, web_thickness)
    if errors:
        return None, errors
    return SectionProperties.i_beam_section(depth, width_top, width_bottom, 
                                           flange_thickness, web_thickness), []
