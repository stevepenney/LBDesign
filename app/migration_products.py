"""
Database migration: Create products table
Run this to add the products table to your database

To create migration:
flask db migrate -m "Add products table"

To apply migration:
flask db upgrade
"""

# Manual SQL for reference (if not using Flask-Migrate)
SQL_CREATE_PRODUCTS = """
CREATE TABLE products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Identification
    product_code VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(200) NOT NULL,
    manufacturer VARCHAR(100),
    product_type VARCHAR(20) NOT NULL,
    
    -- Geometric dimensions
    depth FLOAT NOT NULL,
    width_top FLOAT,
    width_bottom FLOAT,
    flange_thickness FLOAT,
    web_thickness FLOAT,
    width FLOAT,
    
    -- Calculated geometric properties
    Ixx FLOAT NOT NULL,
    Iyy FLOAT,
    Zxx FLOAT NOT NULL,
    Zyy FLOAT,
    A_gross FLOAT NOT NULL,
    A_shear FLOAT NOT NULL,
    
    -- Material properties
    E FLOAT NOT NULL,
    f_b FLOAT NOT NULL,
    f_s FLOAT NOT NULL,
    f_t FLOAT,
    f_c FLOAT,
    
    -- Durability & availability
    durability_class VARCHAR(10),
    is_active BOOLEAN NOT NULL DEFAULT 1,
    
    -- Metadata
    notes TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_product_code ON products(product_code);
CREATE INDEX idx_is_active ON products(is_active);
"""
