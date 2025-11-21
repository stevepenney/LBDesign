"""
Database initialization script
Run this to create tables and populate initial data
"""
from app import create_app
from app.extensions import db
from app.models import Role, Region, Product, User

def init_db():
    """Initialize database with tables and seed data"""
    app = create_app()
    
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("✓ Tables created")
        
        print("\nInitializing roles...")
        Role.init_roles()
        print("✓ Roles initialized")
        
        print("\nInitializing regions...")
        Region.init_regions()
        print("✓ Regions initialized")
        
        print("\nInitializing sample products...")
        Product.init_sample_products()
        print("✓ Sample products initialized")
        
        # Create a default admin user
        print("\nCreating default admin user...")
        admin_role = Role.query.filter_by(name='ADMIN').first()
        admin_user = User.query.filter_by(username='admin').first()
        
        if admin_user is None:
            admin_user = User(
                username='admin',
                email='admin@lumberbank.co.nz',
                first_name='Admin',
                last_name='User',
                role_id=admin_role.id,
                is_active=True
            )
            admin_user.set_password('admin123')  # Change this in production!
            db.session.add(admin_user)
            db.session.commit()
            print("✓ Admin user created (username: admin, password: admin123)")
        else:
            print("✓ Admin user already exists")
        
        print("\n" + "="*50)
        print("Database initialization complete!")
        print("="*50)
        print("\nDefault credentials:")
        print("  Username: admin")
        print("  Password: admin123")
        print("\n⚠️  IMPORTANT: Change the admin password in production!")

if __name__ == '__main__':
    init_db()
