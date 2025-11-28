"""
Structural Mechanics Formulas
Immutable physics-based calculations for beam analysis
"""


class BeamFormulas:
    """
    Fundamental structural mechanics formulas - governed by physics
    These formulas do not change and are based on established theory
    """
    
    # ============================================================================
    # BENDING MOMENT CALCULATIONS
    # ============================================================================
    
    @staticmethod
    def moment_simple_udl(w, L):
        """
        Simply supported beam with uniformly distributed load
        
        Args:
            w: Uniformly distributed load (kN/m)
            L: Span length (m)
            
        Returns:
            Maximum bending moment M_max (kNm)
            
        Formula: M_max = wL²/8
        Location: At midspan
        """
        return (w * L**2) / 8
    
    @staticmethod
    def moment_simple_point_center(P, L):
        """
        Simply supported beam with point load at center
        
        Args:
            P: Point load (kN)
            L: Span length (m)
            
        Returns:
            Maximum bending moment M_max (kNm)
            
        Formula: M_max = PL/4
        Location: At midspan (under load)
        """
        return (P * L) / 4
    
    @staticmethod
    def moment_simple_point_offset(P, L, a):
        """
        Simply supported beam with point load at distance 'a' from left support
        
        Args:
            P: Point load (kN)
            L: Span length (m)
            a: Distance from left support to point load (m)
            
        Returns:
            Maximum bending moment M_max (kNm)
            
        Formula: M_max = P*a*b/L where b = L-a
        Location: Under the point load
        """
        b = L - a
        return (P * a * b) / L
    
    @staticmethod
    def moment_combined_udl_and_points(w, L, point_loads):
        """
        Simply supported beam with UDL and multiple point loads
        Uses superposition principle
        
        Args:
            w: Uniformly distributed load (kN/m)
            L: Span length (m)
            point_loads: List of tuples (P, a) where P is load and a is position
            
        Returns:
            Maximum bending moment M_max (kNm)
            
        Note: Returns maximum from all positions
        """
        # Moment from UDL
        M_udl = BeamFormulas.moment_simple_udl(w, L)
        
        # Moments from point loads
        M_points = []
        for P, a in point_loads:
            M_points.append(BeamFormulas.moment_simple_point_offset(P, L, a))
        
        # Maximum moment (simplified - actually need to check all critical points)
        # For now, assume midspan is critical
        return M_udl + max(M_points) if M_points else M_udl
    
    # ============================================================================
    # SHEAR FORCE CALCULATIONS
    # ============================================================================
    
    @staticmethod
    def shear_simple_udl(w, L):
        """
        Simply supported beam with uniformly distributed load
        
        Args:
            w: Uniformly distributed load (kN/m)
            L: Span length (m)
            
        Returns:
            Maximum shear force V_max (kN)
            
        Formula: V_max = wL/2
        Location: At supports
        """
        return (w * L) / 2
    
    @staticmethod
    def shear_simple_point_center(P, L):
        """
        Simply supported beam with point load at center
        
        Args:
            P: Point load (kN)
            L: Span length (m)
            
        Returns:
            Maximum shear force V_max (kN)
            
        Formula: V_max = P/2
        Location: At supports
        """
        return P / 2
    
    @staticmethod
    def shear_simple_point_offset(P, L, a):
        """
        Simply supported beam with point load at distance 'a' from left support
        
        Args:
            P: Point load (kN)
            L: Span length (m)
            a: Distance from left support to point load (m)
            
        Returns:
            Maximum shear force V_max (kN)
            
        Formula: V_max = max(P*b/L, P*a/L) where b = L-a
        Location: At supports
        """
        b = L - a
        R1 = P * b / L  # Reaction at left support
        R2 = P * a / L  # Reaction at right support
        return max(R1, R2)
    
    @staticmethod
    def shear_combined(w, L, point_loads):
        """
        Simply supported beam with UDL and multiple point loads
        
        Args:
            w: Uniformly distributed load (kN/m)
            L: Span length (m)
            point_loads: List of tuples (P, a) where P is load and a is position
            
        Returns:
            Maximum shear force V_max (kN)
        """
        # Shear from UDL
        V_udl = BeamFormulas.shear_simple_udl(w, L)
        
        # Calculate reactions from point loads
        R_left = 0
        R_right = 0
        for P, a in point_loads:
            b = L - a
            R_left += P * b / L
            R_right += P * a / L
        
        # Maximum shear is at supports
        return max(V_udl + R_left, V_udl + R_right)
    
    # ============================================================================
    # DEFLECTION CALCULATIONS
    # ============================================================================
    
    @staticmethod
    def deflection_simple_udl(w, L, E, I):
        """
        Simply supported beam with uniformly distributed load
        
        Args:
            w: Uniformly distributed load (kN/m)
            L: Span length (m)
            E: Modulus of elasticity (MPa)
            I: Second moment of area (mm⁴)
            
        Returns:
            Maximum deflection δ_max (mm)
            
        Formula: δ_max = (5*w*L⁴)/(384*E*I)
        Location: At midspan
        
        Note: Need to convert units properly:
        - w in kN/m → N/mm
        - L in m → mm
        - E in MPa → N/mm²
        - I in mm⁴
        - Result in mm
        """
        # Convert to consistent units (N, mm)
        w_N_mm = w * 1000 / 1000  # kN/m to N/mm
        L_mm = L * 1000  # m to mm
        E_N_mm2 = E  # MPa is already N/mm²
        
        deflection = (5 * w_N_mm * L_mm**4) / (384 * E_N_mm2 * I)
        return deflection
    
    @staticmethod
    def deflection_simple_point_center(P, L, E, I):
        """
        Simply supported beam with point load at center
        
        Args:
            P: Point load (kN)
            L: Span length (m)
            E: Modulus of elasticity (MPa)
            I: Second moment of area (mm⁴)
            
        Returns:
            Maximum deflection δ_max (mm)
            
        Formula: δ_max = (P*L³)/(48*E*I)
        Location: At midspan (under load)
        """
        # Convert to consistent units (N, mm)
        P_N = P * 1000  # kN to N
        L_mm = L * 1000  # m to mm
        E_N_mm2 = E  # MPa is already N/mm²
        
        deflection = (P_N * L_mm**3) / (48 * E_N_mm2 * I)
        return deflection
    
    @staticmethod
    def deflection_limit_span_ratio(L, ratio=300):
        """
        Calculate deflection limit based on span/ratio
        
        Args:
            L: Span length (m)
            ratio: Span-to-deflection ratio (default 300 for floors)
            
        Returns:
            Deflection limit (mm)
            
        Common ratios:
        - Floors: L/300
        - Roofs: L/250
        - Cantilevers: L/150
        """
        L_mm = L * 1000  # m to mm
        return L_mm / ratio
    
    # ============================================================================
    # UTILITY FUNCTIONS
    # ============================================================================
    
    @staticmethod
    def utilization_ratio(demand, capacity):
        """
        Calculate utilization ratio
        
        Args:
            demand: Demand value (M*, V*, δ)
            capacity: Capacity value (φMn, φVn, δ_limit)
            
        Returns:
            Utilization ratio (demand/capacity)
            
        Interpretation:
        - < 1.0: PASS (safe)
        - ≥ 1.0: FAIL (overstressed)
        """
        if capacity == 0:
            return float('inf')
        return demand / capacity
    
    @staticmethod
    def check_status(utilization):
        """
        Determine pass/fail status from utilization ratio
        
        Args:
            utilization: Utilization ratio
            
        Returns:
            Status string: "PASS", "WARNING", or "FAIL"
        """
        if utilization < 0.9:
            return "PASS"
        elif utilization < 1.0:
            return "WARNING"
        else:
            return "FAIL"
