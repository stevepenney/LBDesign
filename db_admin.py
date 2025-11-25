"""
Database administration script
Usage: venv\Scripts\python.exe db_admin.py
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from app.extensions import db
from app.models import User, Project, Beam
from app.database.repositories import UserRepository, ProjectRepository, BeamRepository

app = create_app()

def list_users():
    """List all users"""
    with app.app_context():
        users = UserRepository.get_all()
        print(f"\n{'ID':<5} {'Username':<20} {'Email':<30} {'Role':<15} {'Active'}")
        print("-" * 80)
        for user in users:
            print(f"{user.id:<5} {user.username:<20} {user.email:<30} {user.role:<15} {'Yes' if user.is_active else 'No'}")

def list_projects():
    """List all projects"""
    with app.app_context():
        projects = Project.query.all()
        print(f"\n{'ID':<5} {'Name':<30} {'Owner':<20} {'Region':<15} {'Beams'}")
        print("-" * 80)
        for project in projects:
            print(f"{project.id:<5} {project.name:<30} {project.owner.username:<20} {project.region:<15} {project.beams.count()}")

def list_beams():
    """List all beams"""
    with app.app_context():
        beams = Beam.query.all()
        print(f"\n{'ID':<5} {'Name':<25} {'Project':<25} {'Type':<15} {'Span (m)'}")
        print("-" * 80)
        for beam in beams:
            print(f"{beam.id:<5} {beam.name:<25} {beam.project.name:<25} {beam.member_type:<15} {beam.span:.2f}")

def create_user():
    """Create a new user interactively"""
    with app.app_context():
        username = input("Username: ")
        email = input("Email: ")
        password = input("Password: ")
        role = input("Role (USER/DETAILER/ADMIN/SUPERUSER) [DETAILER]: ") or "DETAILER"
        
        user = UserRepository.create_user(username, email, password, role)
        print(f"✓ User '{username}' created successfully!")

def reset_password():
    """Reset user password"""
    with app.app_context():
        username = input("Username: ")
        user = UserRepository.get_by_username(username)
        
        if not user:
            print(f"✗ User '{username}' not found")
            return
        
        new_password = input("New password: ")
        user.set_password(new_password)
        db.session.commit()
        print(f"✓ Password for '{username}' reset successfully!")

def delete_project():
    """Delete a project and its beams"""
    with app.app_context():
        list_projects()
        project_id = int(input("\nProject ID to delete: "))
        
        project = ProjectRepository.get_by_id(project_id)
        if not project:
            print("✗ Project not found")
            return
        
        confirm = input(f"Delete '{project.name}' and all its beams? (yes/no): ")
        if confirm.lower() == 'yes':
            ProjectRepository.delete(project)
            print(f"✓ Project '{project.name}' deleted!")
        else:
            print("Cancelled")

def stats():
    """Show database statistics"""
    with app.app_context():
        total_users = User.query.count()
        active_users = User.query.filter_by(is_active=True).count()
        total_projects = Project.query.count()
        total_beams = Beam.query.count()
        
        print("\n" + "="*50)
        print("DATABASE STATISTICS")
        print("="*50)
        print(f"Total Users:       {total_users}")
        print(f"Active Users:      {active_users}")
        print(f"Total Projects:    {total_projects}")
        print(f"Total Beams:       {total_beams}")
        print(f"Avg Beams/Project: {total_beams/total_projects if total_projects > 0 else 0:.1f}")
        print("="*50)

def menu():
    """Show interactive menu"""
    while True:
        print("\n" + "="*50)
        print("LBDESIGN DATABASE ADMINISTRATION")
        print("="*50)
        print("1. List Users")
        print("2. List Projects")
        print("3. List Beams")
        print("4. Create User")
        print("5. Reset Password")
        print("6. Delete Project")
        print("7. Database Statistics")
        print("8. Exit")
        print("="*50)
        
        choice = input("\nChoice: ")
        
        if choice == '1':
            list_users()
        elif choice == '2':
            list_projects()
        elif choice == '3':
            list_beams()
        elif choice == '4':
            create_user()
        elif choice == '5':
            reset_password()
        elif choice == '6':
            delete_project()
        elif choice == '7':
            stats()
        elif choice == '8':
            print("Goodbye!")
            break
        else:
            print("Invalid choice")

if __name__ == '__main__':
    menu()
