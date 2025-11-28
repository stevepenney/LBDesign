"""
Design Factors - Version 1.0
Based on NZS3603:1993 and AS/NZS1170

These factors can be updated as standards change.
Each version is tracked for certification purposes.
"""

VERSION = "1.0.0"
STANDARD = "NZS3603:1993"
CERTIFIED_DATE = "2024-11-27"
CERTIFIED_BY = "Pending CPEng Certification"


class DesignFactors:
    """
    Design factors and capacity calculations
    These may be updated when standards change - version controlled
    """
    
    # ============================================================================
    # CAPACITY REDUCTION FACTORS (φ)
    # ============================================================================
    
    # NZS3603 Table 2.2 - Capacity reduction factors
    PHI_BENDING = 0.90      # φ for bending
    PHI_SHEAR = 0.90        # φ for shear
    PHI_COMPRESSION = 0.80  # φ for compression
    PHI_TENSION = 0.85      # φ for tension
    
    # ============================================================================
    # MODIFICATION FACTORS
    # ============================================================================
    
    # Load duration factor (k1) - NZS3603 Clause 2.4.1.1
    K1_PERMANENT = 0.57     # Dead load
    K1_LONG_TERM = 0.57     # Long-term live load
    K1_MEDIUM_TERM = 0.80   # Medium-term (floors, imposed loads)
    K1_SHORT_TERM = 1.00    # Short-term (wind, earthquake)
    K1_VERY_SHORT = 1.15    # Very short-term (impact)
    
    # Moisture condition factor (k4) - NZS3603 Clause 2.4.1.4
    K4_DRY = 1.00           # Moisture content ≤ 15%
    K4_WET = 0.80           # Moisture content > 15%
    
    # Temperature factor (k6) - NZS3603 Clause 2.4.1.6
    K6_NORMAL = 1.00        # Temperature ≤ 65°C
    K6_HIGH = 0.85          # Temperature > 65°C
    
    # Bearing factor (k12) - NZS3603 Clause 2.4.1.12
    K12_BEARING = 1.00      # Default bearing factor
    
    # ============================================================================
    # MATERIAL PROPERTIES (PLACEHOLDER - TO BE REPLACED WITH PRODUCT DATABASE)
    # ============================================================================
    
    # Characteristic strengths for SG8 timber (MPa)
    # These are placeholders - actual values should come from product database
    F_B_SG8 = 16.0          # Bending strength (MPa)
    F_S_SG8 = 2.0           # Shear strength (MPa)
    F_T_SG8 = 11.0          # Tension strength (MPa)
    F_C_SG8 = 18.0          # Compression strength (MPa)
    E_SG8 = 10000.0         # Modulus of elasticity (MPa)
    
    # Characteristic strengths for LVL (MPa)
    F_B_LVL = 48.0          # Bending strength (MPa)
    F_S_LVL = 5.5           # Shear strength (MPa)
    E_LVL = 13800.0         # Modulus of elasticity (MPa)
    
    # ============================================================================
    # DEFLECTION LIMITS
    # ============================================================================
    
    # Span-to-deflection ratios - NZS3603 Table 2.3
    DEFLECTION_LIMIT_FLOOR = 300        # L/300 for floors
    DEFLECTION_LIMIT_ROOF = 250         # L/250 for roofs
    DEFLECTION_LIMIT_CANTILEVER = 150   # L/150 for cantilevers
    
    # ============================================================================
    # CAPACITY CALCULATIONS
    # ============================================================================
    
    @staticmethod
    def moment_capacity(Z, f_b, k1=K1_MEDIUM_TERM, k4=K4_DRY, k6=K6_NORMAL, phi=PHI_BENDING):
        """
        Calculate design moment capacity
        
        Args:
            Z: Section modulus (mm³)
            f_b: Characteristic bending strength (MPa)
            k1: Load duration factor
            k4: Moisture factor
            k6: Temperature factor
            phi: Capacity reduction factor
            
        Returns:
            Design moment capacity φMn (kNm)
            
        Formula: φMn = φ * k1 * k4 * k6 * f_b * Z
        
        Note: Z in mm³, f_b in MPa → Result in Nmm → Convert to kNm
        """
        # Calculate capacity in Nmm
        M_n_Nmm = k1 * k4 * k6 * f_b * Z
        
        # Apply capacity reduction factor
        phi_M_n_Nmm = phi * M_n_Nmm
        
        # Convert Nmm to kNm
        phi_M_n_kNm = phi_M_n_Nmm / 1_000_000
        
        return phi_M_n_kNm
    
    @staticmethod
    def shear_capacity(A, f_s, k1=K1_MEDIUM_TERM, k4=K4_DRY, k6=K6_NORMAL, phi=PHI_SHEAR):
        """
        Calculate design shear capacity
        
        Args:
            A: Shear area (mm²) - typically 2/3 of gross area for rectangular sections
            f_s: Characteristic shear strength (MPa)
            k1: Load duration factor
            k4: Moisture factor
            k6: Temperature factor
            phi: Capacity reduction factor
            
        Returns:
            Design shear capacity φVn (kN)
            
        Formula: φVn = φ * k1 * k4 * k6 * f_s * A
        
        Note: A in mm², f_s in MPa → Result in N → Convert to kN
        """
        # Calculate capacity in N
        V_n_N = k1 * k4 * k6 * f_s * A
        
        # Apply capacity reduction factor
        phi_V_n_N = phi * V_n_N
        
        # Convert N to kN
        phi_V_n_kN = phi_V_n_N / 1000
        
        return phi_V_n_kN
    
    @staticmethod
    def get_section_properties_placeholder(depth, width):
        """
        Calculate section properties for rectangular section
        
        PLACEHOLDER: In future, this will query product database
        
        Args:
            depth: Section depth (mm)
            width: Section width (mm)
            
        Returns:
            Dictionary with section properties
        """
        # Rectangular section properties
        A = width * depth  # mm²
        I = (width * depth**3) / 12  # mm⁴ (second moment of area)
        Z = (width * depth**2) / 6  # mm³ (section modulus)
        A_shear = (2/3) * A  # mm² (effective shear area)
        
        return {
            'area': A,
            'I': I,
            'Z': Z,
            'A_shear': A_shear,
            'depth': depth,
            'width': width
        }
    
    @staticmethod
    def get_modification_factors(load_type='medium_term', condition='dry', temperature='normal'):
        """
        Get appropriate modification factors based on conditions
        
        Args:
            load_type: 'permanent', 'long_term', 'medium_term', 'short_term', 'very_short'
            condition: 'dry' or 'wet'
            temperature: 'normal' or 'high'
            
        Returns:
            Dictionary with k factors
        """
        # Load duration factor
        k1_map = {
            'permanent': DesignFactors.K1_PERMANENT,
            'long_term': DesignFactors.K1_LONG_TERM,
            'medium_term': DesignFactors.K1_MEDIUM_TERM,
            'short_term': DesignFactors.K1_SHORT_TERM,
            'very_short': DesignFactors.K1_VERY_SHORT
        }
        k1 = k1_map.get(load_type, DesignFactors.K1_MEDIUM_TERM)
        
        # Moisture factor
        k4 = DesignFactors.K4_DRY if condition == 'dry' else DesignFactors.K4_WET
        
        # Temperature factor
        k6 = DesignFactors.K6_NORMAL if temperature == 'normal' else DesignFactors.K6_HIGH
        
        return {
            'k1': k1,
            'k4': k4,
            'k6': k6
        }


def get_version_info():
    """
    Get version information for this design factors module
    
    Returns:
        Dictionary with version details
    """
    return {
        'version': VERSION,
        'standard': STANDARD,
        'certified_date': CERTIFIED_DATE,
        'certified_by': CERTIFIED_BY
    }
