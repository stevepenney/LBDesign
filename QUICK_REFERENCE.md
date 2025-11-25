# Quick Command Reference

## Initial Setup (First Time Only)

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database and create admin user
python init_db.py
```

## Running the Application

```bash
# Start the development server
python run.py
```

Then open: http://localhost:5000

## Test Login

- **Username:** admin
- **Password:** admin123

## Database Reset (if needed)

```bash
# Remove database
rm instance/beam_selector.db

# Recreate with init script
python init_db.py
```

## Project Structure Quick Reference

```
app/
├── models/          # Database models (User, Project, Beam)
├── routes/          # Web routes (auth, projects, beams)
├── database/        # Repositories for data access
└── templates/       # HTML templates

init_db.py          # Create database and admin user
run.py              # Start application
.env                # Configuration
```

## Common Tasks

### Create New User via Code
```python
from app.database.repositories import UserRepository

UserRepository.create_user(
    username='newuser',
    email='user@example.com',
    password='password123',
    role='DETAILER'  # or USER, ADMIN, SUPERUSER
)
```

### Query Database
```python
from app.database.repositories import ProjectRepository, BeamRepository

# Get all projects for a user
projects = ProjectRepository.get_by_user(user_id)

# Get all beams in a project
beams = BeamRepository.get_by_project(project_id)
```

## URLs Reference

- `/` - Redirects to projects list
- `/auth/login` - Login page
- `/auth/register` - Registration page
- `/auth/logout` - Logout
- `/projects/` - List projects
- `/projects/create` - New project form
- `/projects/<id>` - Project detail with beams
- `/projects/<id>/edit` - Edit project
- `/beams/project/<id>/create` - New beam form
- `/beams/<id>` - Beam detail
- `/beams/<id>/edit` - Edit beam

## File Locations

- **Application Code:** `/mnt/user-data/outputs/app/`
- **Database:** `instance/beam_selector.db` (created on first run)
- **Configuration:** `.env`
- **Templates:** `app/templates/`

## Troubleshooting

**Port 5000 in use?**
Edit `run.py` and change port number

**Import errors?**
```bash
pip install -r requirements.txt
```

**Fresh start?**
```bash
rm instance/beam_selector.db
python init_db.py
python run.py
```
