"""
Database Migration Script - Add Calculation Fields to Beam Table
Run this to add new calculation result fields without losing existing data

Usage: python migrate_add_calculation_fields.py
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from app.extensions import db

# SQL statements to add new columns
MIGRATION_SQL = """
-- Add demand fields
ALTER TABLE beams ADD COLUMN demand_moment REAL;
ALTER TABLE beams ADD COLUMN demand_shear REAL;
ALTER TABLE beams ADD COLUMN demand_deflection REAL;

-- Add capacity fields
ALTER TABLE beams ADD COLUMN capacity_moment REAL;
ALTER TABLE beams ADD COLUMN capacity_shear REAL;
ALTER TABLE beams ADD COLUMN deflection_limit REAL;

-- Add utilization fields
ALTER TABLE beams ADD COLUMN utilization_moment REAL;
ALTER TABLE beams ADD COLUMN utilization_shear REAL;
ALTER TABLE beams ADD COLUMN utilization_deflection REAL;

-- Add metadata fields
ALTER TABLE beams ADD COLUMN calc_status VARCHAR(20);
ALTER TABLE beams ADD COLUMN calc_version VARCHAR(50);
ALTER TABLE beams ADD COLUMN calc_date DATETIME;
"""


def check_column_exists(table_name, column_name):
    """Check if a column already exists in a table"""
    query = f"PRAGMA table_info({table_name})"
    result = db.session.execute(db.text(query))
    columns = [row[1] for row in result]
    return column_name in columns


def add_column_if_not_exists(table_name, column_name, column_type):
    """Add a column only if it doesn't already exist"""
    if check_column_exists(table_name, column_name):
        print(f"  ⏭️  Column '{column_name}' already exists, skipping")
        return False
    else:
        sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
        db.session.execute(db.text(sql))
        print(f"  ✅ Added column '{column_name}'")
        return True


def migrate_database():
    """Add calculation fields to beams table"""
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*70)
        print("DATABASE MIGRATION: Add Calculation Fields to Beam Table")
        print("="*70)
        
        # Check if beams table exists
        result = db.session.execute(db.text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='beams'"
        ))
        if not result.fetchone():
            print("\n❌ Error: 'beams' table does not exist!")
            print("   Please run init_db.py first to create tables.")
            return False
        
        print("\n📊 Current beams table structure:")
        result = db.session.execute(db.text("PRAGMA table_info(beams)"))
        for row in result:
            print(f"   - {row[1]} ({row[2]})")
        
        # Count existing beams
        result = db.session.execute(db.text("SELECT COUNT(*) FROM beams"))
        beam_count = result.fetchone()[0]
        print(f"\n📦 Found {beam_count} existing beam(s) in database")
        
        if beam_count > 0:
            print("   ⚠️  Migration will preserve all existing data")
        
        print("\n🔧 Adding new calculation fields...")
        
        columns_added = 0
        
        # Add demand fields
        print("\n  Adding DEMAND fields:")
        columns_added += add_column_if_not_exists('beams', 'demand_moment', 'REAL')
        columns_added += add_column_if_not_exists('beams', 'demand_shear', 'REAL')
        columns_added += add_column_if_not_exists('beams', 'demand_deflection', 'REAL')
        
        # Add capacity fields
        print("\n  Adding CAPACITY fields:")
        columns_added += add_column_if_not_exists('beams', 'capacity_moment', 'REAL')
        columns_added += add_column_if_not_exists('beams', 'capacity_shear', 'REAL')
        columns_added += add_column_if_not_exists('beams', 'deflection_limit', 'REAL')
        
        # Add utilization fields
        print("\n  Adding UTILIZATION fields:")
        columns_added += add_column_if_not_exists('beams', 'utilization_moment', 'REAL')
        columns_added += add_column_if_not_exists('beams', 'utilization_shear', 'REAL')
        columns_added += add_column_if_not_exists('beams', 'utilization_deflection', 'REAL')
        
        # Add metadata fields
        print("\n  Adding METADATA fields:")
        columns_added += add_column_if_not_exists('beams', 'calc_status', 'VARCHAR(20)')
        columns_added += add_column_if_not_exists('beams', 'calc_version', 'VARCHAR(50)')
        columns_added += add_column_if_not_exists('beams', 'calc_date', 'DATETIME')
        
        # Commit changes
        try:
            db.session.commit()
            print("\n✅ Database migration completed successfully!")
            print(f"   Added {columns_added} new column(s)")
        except Exception as e:
            db.session.rollback()
            print(f"\n❌ Error during migration: {e}")
            return False
        
        # Verify migration
        print("\n📊 Updated beams table structure:")
        result = db.session.execute(db.text("PRAGMA table_info(beams)"))
        for row in result:
            print(f"   - {row[1]} ({row[2]})")
        
        # Verify data preservation
        result = db.session.execute(db.text("SELECT COUNT(*) FROM beams"))
        new_beam_count = result.fetchone()[0]
        print(f"\n📦 Beam count after migration: {new_beam_count}")
        
        if new_beam_count == beam_count:
            print("   ✅ All existing data preserved")
        else:
            print("   ⚠️  WARNING: Beam count changed!")
        
        print("\n" + "="*70)
        print("MIGRATION COMPLETE")
        print("="*70)
        print("\nNext steps:")
        print("1. Update your app/models/beam.py with new fields")
        print("2. Copy calculation engine files to app/services/calculations/")
        print("3. Test the calculation engine")
        print("4. Add 'Calculate' button to beam forms")
        
        return True


def rollback_migration():
    """Remove calculation fields (rollback)"""
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*70)
        print("ROLLBACK: Remove Calculation Fields")
        print("="*70)
        print("\n⚠️  SQLite doesn't support DROP COLUMN easily.")
        print("   To rollback, you would need to:")
        print("   1. Create new table without calculation fields")
        print("   2. Copy data to new table")
        print("   3. Drop old table")
        print("   4. Rename new table")
        print("\nFor now, the fields will remain but won't be used.")


if __name__ == '__main__':
    print("\nLBDesign Database Migration Tool")
    print("="*70)
    
    if len(sys.argv) > 1 and sys.argv[1] == '--rollback':
        rollback_migration()
    else:
        success = migrate_database()
        
        if success:
            print("\n✅ SUCCESS! Your database is ready for the calculation engine.")
        else:
            print("\n❌ FAILED! Please check errors above.")
            sys.exit(1)
