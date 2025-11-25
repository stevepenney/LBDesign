"""
Flask-Admin setup for database administration (SUPERUSER only)
"""
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user
from flask import redirect, url_for, request
from app.extensions import db
from app.models import User, Project, Beam


class CustomAdminIndexView(AdminIndexView):
    """Custom index view for database admin with tile layout"""
    
    def is_accessible(self):
        """Only allow SUPERUSER access"""
        return current_user.is_authenticated and current_user.has_role('SUPERUSER')
    
    def inaccessible_callback(self, name, **kwargs):
        """Redirect to login if not accessible"""
        return redirect(url_for('auth.login', next=request.url))
    
    @expose('/')
    def index(self):
        """Custom index page with tiles"""
        return self.render('admin/database_index.html')


class SecureModelView(ModelView):
    """Base ModelView with SUPERUSER authentication"""
    
    def _handle_view(self, name, **kwargs):
        """Override to inject custom CSS"""
        # Add our custom CSS file to extra_css
        if not hasattr(self, 'extra_css'):
            self.extra_css = []
        if '/static/css/admin.css' not in self.extra_css:
            self.extra_css.append('/static/css/admin.css')
        
        return super(SecureModelView, self)._handle_view(name, **kwargs)
    
    def is_accessible(self):
        """Only allow SUPERUSER access"""
        return current_user.is_authenticated and current_user.has_role('SUPERUSER')
    
    def inaccessible_callback(self, name, **kwargs):
        """Redirect to login if not accessible"""
        return redirect(url_for('auth.login', next=request.url))


class UserAdminView(SecureModelView):
    """Admin view for User model"""
    column_list = ['id', 'username', 'email', 'role', 'is_active', 'created_at', 'last_login']
    column_searchable_list = ['username', 'email']
    column_filters = ['role', 'is_active', 'created_at']
    column_editable_list = ['role', 'is_active']
    form_excluded_columns = ['password_hash', 'projects']
    
    # Don't display password hash
    column_exclude_list = ['password_hash']
    
    def on_model_change(self, form, model, is_created):
        """Hash password if it's being set"""
        if hasattr(form, 'password') and form.password.data:
            model.set_password(form.password.data)


class ProjectAdminView(SecureModelView):
    """Admin view for Project model"""
    column_list = ['id', 'name', 'owner.username', 'region', 'project_type', 'created_at', 'updated_at']
    column_searchable_list = ['name', 'client', 'project_number']
    column_filters = ['region', 'project_type', 'created_at', 'user_id']
    column_labels = {'owner.username': 'Owner'}
    
    # Show relationships
    column_display_pk = True


class BeamAdminView(SecureModelView):
    """Admin view for Beam model"""
    column_list = ['id', 'name', 'project.name', 'member_type', 'span', 'spacing', 'created_at']
    column_searchable_list = ['name', 'reference']
    column_filters = ['member_type', 'created_at', 'project_id']
    column_labels = {'project.name': 'Project'}
    
    # Show numeric fields with formatting
    column_formatters = {
        'span': lambda v, c, m, p: f"{m.span:.2f} m" if m.span else '-',
        'spacing': lambda v, c, m, p: f"{m.spacing:.2f} m" if m.spacing else '-',
    }


def init_admin(app):
    """Initialize Flask-Admin at /admin/database/"""
    admin = Admin(
        app, 
        name='LBDesign Database Admin',
        url='/admin/database',
        endpoint='database_admin',
        index_view=CustomAdminIndexView(
            name='Database Admin',
            url='/admin/database',
            endpoint='database_admin'
        )
    )
    
    # Add model views - remove category to hide dropdown menu
    admin.add_view(UserAdminView(User, db.session, name='Users', endpoint='user'))
    admin.add_view(ProjectAdminView(Project, db.session, name='Projects', endpoint='project'))
    admin.add_view(BeamAdminView(Beam, db.session, name='Beams', endpoint='beam'))
    
    return admin