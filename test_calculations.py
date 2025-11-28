"""
Test script for beam calculations
Run this to verify calculation engine works correctly
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.calculations import BeamFormulas, DesignFactors, get_version_info


def test_structural_mechanics():
    """Test basic structural mechanics formulas"""
    print("\n" + "="*70)
    print("STRUCTURAL MECHANICS TESTS")
    print("="*70)
    
    # Test 1: Simple UDL moment
    w = 5.0  # kN/m
    L = 6.0  # m
    M = BeamFormulas.moment_simple_udl(w, L)
    print(f"\nTest 1: Simply supported beam with UDL")
    print(f"  Load: {w} kN/m, Span: {L} m")
    print(f"  Expected M_max: {(w * L**2) / 8} kNm")
    print(f"  Calculated M_max: {M} kNm")
    print(f"  ✓ PASS" if abs(M - 22.5) < 0.01 else "  ✗ FAIL")
    
    # Test 2: Simple UDL shear
    V = BeamFormulas.shear_simple_udl(w, L)
    print(f"\nTest 2: Shear force")
    print(f"  Expected V_max: {(w * L) / 2} kN")
    print(f"  Calculated V_max: {V} kN")
    print(f"  ✓ PASS" if abs(V - 15.0) < 0.01 else "  ✗ FAIL")
    
    # Test 3: Point load at center
    P = 10.0  # kN
    M_point = BeamFormulas.moment_simple_point_center(P, L)
    print(f"\nTest 3: Point load at center")
    print(f"  Load: {P} kN, Span: {L} m")
    print(f"  Expected M_max: {(P * L) / 4} kNm")
    print(f"  Calculated M_max: {M_point} kNm")
    print(f"  ✓ PASS" if abs(M_point - 15.0) < 0.01 else "  ✗ FAIL")
    
    # Test 4: Deflection
    E = 13800  # MPa (LVL)
    I = 101_250_000  # mm⁴ (300x45 section)
    delta = BeamFormulas.deflection_simple_udl(w, L, E, I)
    print(f"\nTest 4: Deflection")
    print(f"  Load: {w} kN/m, Span: {L} m")
    print(f"  E: {E} MPa, I: {I} mm⁴")
    print(f"  Calculated δ_max: {delta:.2f} mm")
    
    # Test 5: Deflection limit
    delta_limit = BeamFormulas.deflection_limit_span_ratio(L, 300)
    print(f"\nTest 5: Deflection limit")
    print(f"  Span: {L} m, Ratio: L/300")
    print(f"  Expected limit: {L * 1000 / 300} mm")
    print(f"  Calculated limit: {delta_limit} mm")
    print(f"  ✓ PASS" if abs(delta_limit - 20.0) < 0.01 else "  ✗ FAIL")


def test_design_factors():
    """Test design factor calculations"""
    print("\n" + "="*70)
    print("DESIGN FACTORS TESTS")
    print("="*70)
    
    # Version info
    version = get_version_info()
    print(f"\nVersion Information:")
    print(f"  Version: {version['version']}")
    print(f"  Standard: {version['standard']}")
    print(f"  Certified Date: {version['certified_date']}")
    
    # Test section properties
    props = DesignFactors.get_section_properties_placeholder(300, 45)
    print(f"\nSection Properties (300x45):")
    print(f"  Area: {props['area']:,.0f} mm²")
    print(f"  I: {props['I']:,.0f} mm⁴")
    print(f"  Z: {props['Z']:,.0f} mm³")
    print(f"  A_shear: {props['A_shear']:,.0f} mm²")
    
    # Test moment capacity
    phi_M_n = DesignFactors.moment_capacity(
        Z=props['Z'],
        f_b=DesignFactors.F_B_LVL
    )
    print(f"\nMoment Capacity:")
    print(f"  f_b: {DesignFactors.F_B_LVL} MPa")
    print(f"  Z: {props['Z']:,.0f} mm³")
    print(f"  φMn: {phi_M_n:.2f} kNm")
    
    # Test shear capacity
    phi_V_n = DesignFactors.shear_capacity(
        A=props['A_shear'],
        f_s=DesignFactors.F_S_LVL
    )
    print(f"\nShear Capacity:")
    print(f"  f_s: {DesignFactors.F_S_LVL} MPa")
    print(f"  A_shear: {props['A_shear']:,.0f} mm²")
    print(f"  φVn: {phi_V_n:.2f} kN")
    
    # Test modification factors
    k_factors = DesignFactors.get_modification_factors(
        load_type='medium_term',
        condition='dry',
        temperature='normal'
    )
    print(f"\nModification Factors:")
    print(f"  k1 (load duration): {k_factors['k1']}")
    print(f"  k4 (moisture): {k_factors['k4']}")
    print(f"  k6 (temperature): {k_factors['k6']}")


def test_utilization():
    """Test utilization ratio calculations"""
    print("\n" + "="*70)
    print("UTILIZATION TESTS")
    print("="*70)
    
    # Test cases
    cases = [
        (15.0, 20.0, "PASS"),      # 0.75 utilization
        (18.5, 20.0, "WARNING"),   # 0.925 utilization
        (22.0, 20.0, "FAIL"),      # 1.1 utilization
    ]
    
    for demand, capacity, expected_status in cases:
        util = BeamFormulas.utilization_ratio(demand, capacity)
        status = BeamFormulas.check_status(util)
        
        print(f"\nDemand: {demand} kNm, Capacity: {capacity} kNm")
        print(f"  Utilization: {util:.3f}")
        print(f"  Status: {status}")
        print(f"  ✓ PASS" if status == expected_status else f"  ✗ FAIL (expected {expected_status})")


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("BEAM CALCULATION ENGINE TESTS")
    print("="*70)
    
    test_structural_mechanics()
    test_design_factors()
    test_utilization()
    
    print("\n" + "="*70)
    print("ALL TESTS COMPLETE")
    print("="*70)
    print("\nNext steps:")
    print("1. Add these calculation fields to your Beam model")
    print("2. Run database migration to add new columns")
    print("3. Add 'Calculate' button to beam forms")
    print("4. Create route to call calculation_service.calculate_and_update_beam()")
    print("5. Display results in beam detail page")


if __name__ == '__main__':
    main()
