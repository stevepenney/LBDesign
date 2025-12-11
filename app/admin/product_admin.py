"""
Product Admin View
Flask-Admin interface for managing structural products (SUPERUSER only)
"""
from flask import flash, redirect, url_for
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from wtforms import SelectField, FloatField, TextAreaField, BooleanField, StringField
from wtforms.validators import DataRequired, Optional
from app.models.product import Product
from app.utils.section_properties import calculate_rectangular_properties, calculate_i_beam_properties


class ProductAdminView(ModelView):
    """Admin view for Product model with SUPERUSER access only"""
    
    # ========================================================================
    # FORM FIELD OVERRIDES
    # ========================================================================
    
    form_overrides = {
        'product_type': SelectField
    }
    
    # ========================================================================
    # ACCESS CONTROL
    # ========================================================================
    
    def is_accessible(self):
        """Only SUPERUSER can access product management"""
        return current_user.is_authenticated and current_user.has_role('SUPERUSER')
    
    def inaccessible_callback(self, name, **kwargs):
        """Redirect if user doesn't have access"""
        flash('Access denied. SUPERUSER role required.', 'error')
        return redirect(url_for('main.index'))
    
    # ========================================================================
    # LIST VIEW CONFIGURATION
    # ========================================================================
    
    column_list = [
        'product_code', 
        'description', 
        'manufacturer',
        'product_type',
        'display_dimensions',
        'E',
        'f_b',
        'is_active'
    ]
    
    column_searchable_list = ['product_code', 'description', 'manufacturer']
    column_filters = ['product_type', 'manufacturer', 'is_active', 'durability_class']
    column_sortable_list = ['product_code', 'manufacturer', 'product_type', 'E', 'f_b']
    
    column_labels = {
        'product_code': 'Product Code',
        'description': 'Description',
        'product_type': 'Type',
        'display_dimensions': 'Dimensions',
        'E': 'E (MPa)',
        'f_b': 'f_b (MPa)',
        'is_active': 'Active'
    }
    
    column_descriptions = {
        'product_code': 'Unique product identifier',
        'E': 'Modulus of Elasticity',
        'f_b': 'Characteristic Bending Strength'
    }
    
    # ========================================================================
    # FORM CONFIGURATION
    # ========================================================================
    
    form_columns = [
        'product_code',
        'description',
        'manufacturer',
        'product_type',
        'depth',
        'width',
        'width_top',
        'width_bottom',
        'flange_thickness',
        'web_thickness',
        'E',
        'f_b',
        'f_s',
        'f_t',
        'f_c',
        'durability_class',
        'is_active',
        'notes'
    ]
    
    form_args = {
        'product_code': {
            'validators': [DataRequired()],
            'description': 'Unique product code (e.g., "LW300", "90x45-SG8")'
        },
        'description': {
            'validators': [DataRequired()],
            'description': 'Full product description'
        },
        'product_type': {
            'validators': [DataRequired()],
            'description': 'Section type',
            'choices': [
                ('', 'Select type...'),
                ('LVL', 'LVL'),
                ('SOLID_TIMBER', 'SG8/SG10 Timber'),
                ('GLULAM', 'Glulam'),
                ('I_BEAM', 'I-Beam')
            ]
        },
        'depth': {
            'validators': [DataRequired()],
            'description': 'Overall depth in mm'
        },
        'width': {
            'validators': [Optional()],
            'description': 'Width in mm (for rectangular sections)'
        },
        'width_top': {
            'validators': [Optional()],
            'description': 'Top flange width in mm (for I-beams)'
        },
        'width_bottom': {
            'validators': [Optional()],
            'description': 'Bottom flange width in mm (for I-beams)'
        },
        'flange_thickness': {
            'validators': [Optional()],
            'description': 'Flange thickness in mm (for I-beams)'
        },
        'web_thickness': {
            'validators': [Optional()],
            'description': 'Web thickness in mm (for I-beams)'
        },
        'E': {
            'validators': [DataRequired()],
            'description': 'Modulus of Elasticity in MPa'
        },
        'f_b': {
            'validators': [DataRequired()],
            'description': 'Characteristic bending strength in MPa'
        },
        'f_s': {
            'validators': [DataRequired()],
            'description': 'Characteristic shear strength in MPa'
        },
        'f_t': {
            'validators': [Optional()],
            'description': 'Characteristic tension strength in MPa (optional)'
        },
        'f_c': {
            'validators': [Optional()],
            'description': 'Characteristic compression strength in MPa (optional)'
        },
        'durability_class': {
            'validators': [Optional()],
            'description': 'Durability class (e.g., H1.2, H3.2)'
        }
    }
    
    # Custom form template with interactive SVG diagram
    create_template = 'admin/product_form.html'
    edit_template = 'admin/product_form.html'
    
    # ========================================================================
    # FORM PROCESSING
    # ========================================================================
    
    def _list_thumbnail(view, context, model, name):
        """Display product type icon in list"""
        icons = {
            'I_BEAM': '🏗️',
            'LVL': '📐',
            'GLULAM': '🪵',
            'SOLID_TIMBER': '🌲'
        }
        return icons.get(model.product_type, '❓')
    
    column_formatters = {
        'product_type': _list_thumbnail
    }
    
    # Add form field wrapper classes for conditional display
    def create_form(self, obj=None):
        """Customize form with field wrapper classes"""
        form = super().create_form(obj)
        
        # Add wrapper classes to rectangular fields
        if hasattr(form, 'width'):
            form.width.render_kw = {'class': 'rectangular-fields'}
        
        # Add wrapper classes to I-beam fields  
        for field_name in ['width_top', 'width_bottom', 'flange_thickness', 'web_thickness']:
            if hasattr(form, field_name):
                field = getattr(form, field_name)
                field.render_kw = {'class': 'i-beam-fields'}
        
        return form
    
    def edit_form(self, obj=None):
        """Customize edit form with field wrapper classes"""
        return self.create_form(obj)
    
    # ========================================================================
    # FORM PROCESSING
    # ========================================================================
    
    def on_model_change(self, form, model, is_created):
        """
        Calculate geometric properties before saving
        Called when creating or updating a product
        """
        try:
            # Debug: log what we received
            print(f"\n=== Product Form Submission ===")
            print(f"Product Type: {model.product_type}")
            print(f"Depth: {model.depth}")
            print(f"Width: {model.width}")
            print(f"Width Top: {model.width_top}")
            print(f"Width Bottom: {model.width_bottom}")
            print(f"Flange Thickness: {model.flange_thickness}")
            print(f"Web Thickness: {model.web_thickness}")
            
            if model.product_type == 'I_BEAM':
                # Validate I-beam inputs
                if not all([model.depth, model.width_top, model.width_bottom, 
                           model.flange_thickness, model.web_thickness]):
                    missing = []
                    if not model.depth: missing.append('depth')
                    if not model.width_top: missing.append('width_top')
                    if not model.width_bottom: missing.append('width_bottom')
                    if not model.flange_thickness: missing.append('flange_thickness')
                    if not model.web_thickness: missing.append('web_thickness')
                    raise ValueError(f'I-beam requires all flange and web dimensions. Missing: {", ".join(missing)}')
                
                # Calculate properties
                props, errors = calculate_i_beam_properties(
                    float(model.depth),
                    float(model.width_top),
                    float(model.width_bottom),
                    float(model.flange_thickness),
                    float(model.web_thickness)
                )
                
                if errors:
                    raise ValueError('; '.join(errors))
                
            else:  # Rectangular section (SOLID_TIMBER, LVL, GLULAM)
                # Validate rectangular inputs
                if not model.depth:
                    raise ValueError('Depth is required')
                if not model.width:
                    raise ValueError('Width is required for rectangular sections')
                
                # Calculate properties
                props, errors = calculate_rectangular_properties(
                    float(model.depth),
                    float(model.width)
                )
                
                if errors:
                    raise ValueError('; '.join(errors))
            
            # Update model with calculated properties
            model.A_gross = props['A_gross']
            model.A_shear = props['A_shear']
            model.Ixx = props['Ixx']
            model.Iyy = props['Iyy']
            model.Zxx = props['Zxx']
            model.Zyy = props['Zyy']
            
            print(f"Calculated properties successfully")
            print(f"A_gross: {model.A_gross}, Ixx: {model.Ixx}, Zxx: {model.Zxx}\n")
            
            if is_created:
                flash(f'Product "{model.product_code}" created with calculated properties', 'success')
            else:
                flash(f'Product "{model.product_code}" updated with recalculated properties', 'success')
                
        except ValueError as e:
            flash(f'Validation error: {str(e)}', 'error')
            raise
        except Exception as e:
            flash(f'Error calculating properties: {str(e)}', 'error')
            raise
    
    def after_model_change(self, form, model, is_created):
        """Display calculated properties to user"""
        action = 'created' if is_created else 'updated'
        flash(f'Calculated properties: A={model.A_gross:.0f}mm², '
              f'Ixx={model.Ixx:.0f}mm⁴, Zxx={model.Zxx:.0f}mm³', 'info')