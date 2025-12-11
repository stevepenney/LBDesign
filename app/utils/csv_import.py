"""
Product CSV Importer
Bulk load products from CSV file with automatic property calculation

CSV Format:
product_code,description,manufacturer,product_type,depth,width,width_top,width_bottom,flange_thickness,web_thickness,E,f_b,f_s,durability_class

Example rows:
90x45-SG8,"90x45 SG8 Timber",Generic,SOLID_TIMBER,90,45,,,,,10000,16,2,H3.2
LVL-E11-300x45,"E11 LVL 300x45",Lumberbank,LVL,300,45,,,,,11000,44,5.5,H1.2
LW300,"Lumberworx LW300 I-beam",Lumberbank,I_BEAM,300,,63,63,45,11,13800,48,5.5,H1.2
"""
import csv
from app.extensions import db
from app.models.product import Product
from app.utils.section_properties import calculate_rectangular_properties, calculate_i_beam_properties


def import_products_from_csv(csv_filepath, skip_header=True):
    """
    Import products from CSV file
    
    Args:
        csv_filepath: Path to CSV file
        skip_header: If True, skip first row (default True)
        
    Returns:
        Tuple of (success_count, error_list)
    """
    success_count = 0
    errors = []
    
    try:
        with open(csv_filepath, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            
            if skip_header:
                next(reader)  # Skip header row
            
            for row_num, row in enumerate(reader, start=2 if skip_header else 1):
                try:
                    # Parse row
                    (product_code, description, manufacturer, product_type, 
                     depth, width, width_top, width_bottom, flange_thickness, 
                     web_thickness, E, f_b, f_s, durability_class) = row
                    
                    # Convert to appropriate types
                    depth = float(depth) if depth else None
                    width = float(width) if width else None
                    width_top = float(width_top) if width_top else None
                    width_bottom = float(width_bottom) if width_bottom else None
                    flange_thickness = float(flange_thickness) if flange_thickness else None
                    web_thickness = float(web_thickness) if web_thickness else None
                    E = float(E)
                    f_b = float(f_b)
                    f_s = float(f_s)
                    
                    # Calculate geometric properties
                    if product_type == 'I_BEAM':
                        if not all([depth, width_top, width_bottom, flange_thickness, web_thickness]):
                            errors.append(f"Row {row_num}: I-beam missing required dimensions")
                            continue
                        
                        props, prop_errors = calculate_i_beam_properties(
                            depth, width_top, width_bottom, flange_thickness, web_thickness
                        )
                        
                        if prop_errors:
                            errors.append(f"Row {row_num}: {'; '.join(prop_errors)}")
                            continue
                    
                    else:  # Rectangular sections
                        if not all([depth, width]):
                            errors.append(f"Row {row_num}: Rectangular section missing depth or width")
                            continue
                        
                        props, prop_errors = calculate_rectangular_properties(depth, width)
                        
                        if prop_errors:
                            errors.append(f"Row {row_num}: {'; '.join(prop_errors)}")
                            continue
                    
                    # Create product
                    product = Product(
                        product_code=product_code,
                        description=description,
                        manufacturer=manufacturer or None,
                        product_type=product_type,
                        depth=depth,
                        width=width,
                        width_top=width_top,
                        width_bottom=width_bottom,
                        flange_thickness=flange_thickness,
                        web_thickness=web_thickness,
                        Ixx=props['Ixx'],
                        Iyy=props['Iyy'],
                        Zxx=props['Zxx'],
                        Zyy=props['Zyy'],
                        A_gross=props['A_gross'],
                        A_shear=props['A_shear'],
                        E=E,
                        f_b=f_b,
                        f_s=f_s,
                        durability_class=durability_class or None,
                        is_active=True
                    )
                    
                    db.session.add(product)
                    success_count += 1
                    
                except ValueError as e:
                    errors.append(f"Row {row_num}: Invalid data - {str(e)}")
                except Exception as e:
                    errors.append(f"Row {row_num}: Error - {str(e)}")
            
            # Commit all products
            db.session.commit()
            
    except FileNotFoundError:
        errors.append(f"File not found: {csv_filepath}")
    except Exception as e:
        errors.append(f"File reading error: {str(e)}")
        db.session.rollback()
    
    return success_count, errors


def create_sample_csv(output_filepath='sample_products.csv'):
    """Create a sample CSV file for reference"""
    sample_data = [
        ['product_code', 'description', 'manufacturer', 'product_type', 'depth', 'width', 
         'width_top', 'width_bottom', 'flange_thickness', 'web_thickness', 'E', 'f_b', 'f_s', 'durability_class'],
        ['90x45-SG8', '90x45 SG8 Timber', 'Generic', 'SOLID_TIMBER', '90', '45', '', '', '', '', '10000', '16', '2', 'H3.2'],
        ['140x45-SG8', '140x45 SG8 Timber', 'Generic', 'SOLID_TIMBER', '140', '45', '', '', '', '', '10000', '16', '2', 'H3.2'],
        ['LVL-E8-300x45', 'E8 LVL 300x45', 'Lumberbank', 'LVL', '300', '45', '', '', '', '', '8000', '32', '4.5', 'H1.2'],
        ['LVL-E11-300x45', 'E11 LVL 300x45', 'Lumberbank', 'LVL', '300', '45', '', '', '', '', '11000', '44', '5.5', 'H1.2'],
        ['LVL-E13-400x63', 'E13 LVL 400x63', 'Lumberbank', 'LVL', '400', '63', '', '', '', '', '13000', '48', '5.5', 'H1.2'],
        ['LW200', 'Lumberworx LW200 I-beam', 'Lumberbank', 'I_BEAM', '200', '', '63', '63', '35', '11', '13800', '48', '5.5', 'H1.2'],
        ['LW300', 'Lumberworx LW300 I-beam', 'Lumberbank', 'I_BEAM', '300', '', '63', '63', '45', '11', '13800', '48', '5.5', 'H1.2'],
        ['LW400', 'Lumberworx LW400 I-beam', 'Lumberbank', 'I_BEAM', '400', '', '89', '89', '45', '11', '13800', '48', '5.5', 'H1.2'],
    ]
    
    with open(output_filepath, 'w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        writer.writerows(sample_data)
    
    return output_filepath


# Flask CLI command (add to your app)
def register_import_command(app):
    """
    Register Flask CLI command for importing products
    
    Usage:
        flask import-products path/to/products.csv
    """
    @app.cli.command('import-products')
    @click.argument('csv_file')
    def import_products_command(csv_file):
        """Import products from CSV file"""
        click.echo(f'Importing products from {csv_file}...')
        success_count, errors = import_products_from_csv(csv_file)
        
        if errors:
            click.echo(f'\nErrors encountered:')
            for error in errors:
                click.echo(f'  - {error}')
        
        click.echo(f'\nSuccessfully imported {success_count} products')
        
        if errors:
            click.echo(f'Failed to import {len(errors)} products')
