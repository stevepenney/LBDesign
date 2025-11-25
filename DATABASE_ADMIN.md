# Database Administration Guide

There are several ways to administer the LBDesign database. Choose the one that fits your needs:

## Option 1: Flask-Admin (Integrated Web Interface) ⭐ RECOMMENDED

**Best for:** Quick data management, bulk edits, exploring relationships

### Setup:
```powershell
# Install Flask-Admin
venv\Scripts\pip.exe install flask-admin

# Restart your app
venv\Scripts\python.exe run.py
```

### Access:
- Navigate to: `http://localhost:5000/admin/`
- **Login required:** Only SUPERUSER role can access
- Already configured in your app!

### Features:
- ✅ Browse all Users, Projects, and Beams
- ✅ Search and filter data
- ✅ Inline editing (click to edit)
- ✅ Bulk operations
- ✅ Export to CSV
- ✅ Relationship visualization
- ✅ Safe password handling
- ✅ Full CRUD operations

### URLs:
```
/admin/                    - Admin home
/admin/user/               - Manage users
/admin/project/            - Manage projects  
/admin/beam/               - Manage beams
```

---

## Option 2: DB Browser for SQLite (Standalone GUI)

**Best for:** Direct database access, SQL queries, schema inspection

### Download:
https://sqlitebrowser.org/dl/

### Usage:
1. Download and install DB Browser for SQLite
2. Open the database file: `C:\Users\steve\OneDrive\python projects\lbdesign\instance\beam_selector.db`
3. Browse data, run SQL queries, modify records

### Features:
- ✅ Visual schema designer
- ✅ SQL query builder
- ✅ Direct table editing
- ✅ Import/export data
- ✅ Database structure viewer
- ✅ Execute custom SQL

### Safety Note:
- Close DB Browser before running your Flask app (SQLite doesn't handle concurrent writes well)
- Or open in read-only mode

---

## Option 3: Python Script (Command Line)

**Best for:** Automated tasks, bulk operations, scripting

### Create a management script:

**File: `db_admin.py`**
```python
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
        print(f"Total Users:      {total_users}")
        print(f"Active Users:     {active_users}")
        print(f"Total Projects:   {total_projects}")
        print(f"Total Beams:      {total_beams}")
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
```

### Usage:
```powershell
venv\Scripts\python.exe db_admin.py
```

---

## Option 4: Flask Shell (Interactive Python)

**Best for:** Quick queries, testing, debugging

### Usage:
```powershell
# Start Flask shell
venv\Scripts\python.exe -c "from app import create_app; app = create_app(); app.app_context().push(); from app.models import *; from app.database.repositories import *"
```

### Examples:
```python
# Get all users
users = User.query.all()

# Find a user
user = User.query.filter_by(username='admin').first()

# Update user role
user.role = 'SUPERUSER'
db.session.commit()

# Count projects
Project.query.count()

# Get user's projects
user = User.query.filter_by(username='steve').first()
user.projects.all()

# Delete a beam
beam = Beam.query.get(5)
db.session.delete(beam)
db.session.commit()
```

---

## Option 5: DBeaver (Professional Tool)

**Best for:** Advanced users, complex queries, multiple databases

### Download:
https://dbeaver.io/download/

### Setup:
1. Download DBeaver Community Edition
2. Create new connection → SQLite
3. Point to: `C:\Users\steve\OneDrive\python projects\lbdesign\instance\beam_selector.db`

### Features:
- ✅ ER diagrams
- ✅ SQL editor with autocomplete
- ✅ Data export/import
- ✅ Query history
- ✅ Visual query builder
- ✅ Compare databases

---

## Comparison Table

| Tool | Setup | UI | Power | Safety | Best For |
|------|-------|----|----|--------|----------|
| **Flask-Admin** | Easy | Web | Medium | ✅ Safe | Quick edits, role-protected |
| **DB Browser** | Easy | Desktop | High | ⚠️ Direct | Schema work, SQL queries |
| **Python Script** | Medium | CLI | High | ✅ Safe | Automation, bulk ops |
| **Flask Shell** | Easy | CLI | High | ⚠️ Direct | Quick queries, testing |
| **DBeaver** | Medium | Desktop | Very High | ⚠️ Direct | Professional use |

---

## Recommendations

### For Daily Use:
**Flask-Admin** - Built into your app, safe, convenient

### For Development:
**DB Browser for SQLite** - Visual, direct access

### For Automation:
**Python Script** (`db_admin.py`) - Scriptable, safe

### For Quick Tasks:
**Your existing `/admin/users` interface** - Already working!

---

## Safety Tips

1. **Backup before direct edits:**
   ```powershell
   copy instance\beam_selector.db instance\beam_selector.db.backup
   ```

2. **Don't edit while app is running** (for external tools)

3. **Use transactions:**
   - Flask-Admin and scripts handle this automatically
   - In Flask Shell: always `db.session.commit()`

4. **Test on a copy first** for bulk operations

---

## Quick Commands Reference

```powershell
# List users via Python
venv\Scripts\python.exe -c "from app import create_app; app = create_app(); app.app_context().push(); from app.models import User; [print(f'{u.username} - {u.role}') for u in User.query.all()]"

# Count projects
venv\Scripts\python.exe -c "from app import create_app; app = create_app(); app.app_context().push(); from app.models import Project; print(f'Projects: {Project.query.count()}')"

# Backup database
copy instance\beam_selector.db instance\backup_%date:~-4,4%%date:~-10,2%%date:~-7,2%.db
```

---

## Next Steps

1. **Install Flask-Admin** (recommended):
   ```powershell
   venv\Scripts\pip.exe install flask-admin
   ```

2. **Create db_admin.py** (copy the script above)

3. **Download DB Browser** for deeper access

All three can work together - use the right tool for each task!
