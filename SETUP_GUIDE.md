# LBDesign - Setup and Usage Guide

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Initialize Database
```bash
python init_db.py
```

This will:
- Create all database tables (users, projects, beams)
- Create a test admin user:
  - Username: `admin`
  - Password: `admin123`
  - Role: SUPERUSER

### 3. Run the Application
```bash
python run.py
```

The application will be available at: http://localhost:5000

## Application Structure

```
LBDesign/
├── app/
│   ├── __init__.py              # Application factory
│   ├── config.py                # Configuration
│   ├── extensions.py            # Flask extensions
│   ├── models/                  # Database models
│   │   ├── user.py
│   │   ├── project.py
│   │   └── beam.py
│   ├── database/
│   │   └── repositories/        # Data access layer
│   │       ├── base_repository.py
│   │       ├── user_repository.py
│   │       ├── project_repository.py
│   │       └── beam_repository.py
│   ├── routes/                  # Web routes
│   │   ├── auth.py
│   │   ├── projects.py
│   │   └── beams.py
│   └── templates/               # HTML templates
│       ├── base.html
│       ├── auth/
│       ├── projects/
│       └── beams/
├── instance/                    # SQLite database location
├── .env                        # Environment configuration
├── init_db.py                  # Database initialization
├── run.py                      # Application entry point
└── requirements.txt            # Python dependencies
```

## Features Implemented

### User Management
- User registration and login
- Password hashing with bcrypt
- Role-based access control (USER, DETAILER, ADMIN, SUPERUSER)
- Session management with Flask-Login

### Project Management (CRUD)
- Create projects with client/engineer/architect details
- List all projects for logged-in user
- View project details with beam list
- Edit project information
- Delete projects (cascade deletes all beams)

### Beam Management (CRUD)
- Create beams within projects
- Specify member type (floor joist, rafter, beam, etc.)
- Input span, spacing, loads (dead, live, point loads)
- View beam details
- Edit beam parameters
- Delete beams

### Current Database Support
- **Development**: SQLite (default, no setup required)
- **Production**: MySQL or SQL Server (configure in .env)

## Usage Workflow

### 1. Login
Navigate to http://localhost:5000 and log in with:
- Username: `admin`
- Password: `admin123`

### 2. Create a Project
1. Click "New Project"
2. Enter project details:
   - Name (required)
   - Region: New Zealand or Australia
   - Optional: Client, Engineer, Architect, etc.
3. Click "Create Project"

### 3. Add Beams to Project
1. From project detail page, click "Add Beam"
2. Enter beam details:
   - Name and optional reference code
   - Member type (floor joist, rafter, beam, etc.)
   - Span in meters
   - Spacing (for joists/rafters)
   - Dead and live loads
   - Optional point loads with positions
3. Click "Create Beam"

### 4. View and Edit
- View all your projects from the main dashboard
- Click into any project to see beam list
- Edit projects or beams as needed
- Delete items with confirmation

## Database Configuration

### SQLite (Default - Development)
No configuration needed. Database file created at `instance/beam_selector.db`

### MySQL (Production)
Update `.env`:
```
DATABASE_TYPE=mysql
DATABASE_HOST=localhost
DATABASE_PORT=3306
DATABASE_NAME=beam_selector
DATABASE_USER=your_username
DATABASE_PASSWORD=your_password
```

### SQL Server (Production)
Update `.env`:
```
DATABASE_TYPE=mssql
DATABASE_HOST=localhost
DATABASE_PORT=1433
DATABASE_NAME=beam_selector
DATABASE_USER=your_username
DATABASE_PASSWORD=your_password
```

## User Roles

### USER
- View projects and beams
- Read-only access

### DETAILER (Default for new registrations)
- All USER permissions
- Create and edit projects
- Create and edit beams
- Run calculations (when implemented)

### ADMIN
- All DETAILER permissions
- Manage users
- Manage product catalog (when implemented)

### SUPERUSER
- All ADMIN permissions
- Manage engineering standards
- System configuration

## Next Steps for Development

### Phase 2: Calculation Engine
- Implement NZ standards (AS/NZS1170, NZS3603)
- Calculate moments, shears, deflections
- Product evaluation and ranking
- Results display

### Phase 3: Product Catalog
- Add Lumberworx I-beams to database
- Add LVL and Glulam products
- Include SG8 timber options
- Recommendation engine

### Phase 4: API
- RESTful API endpoints for all operations
- JWT authentication
- Rate limiting
- API documentation

### Future Enhancements
- Interactive SVG beam selection
- PDF report generation
- Email sharing
- Mobile responsive improvements
- Batch calculations
- Cost estimation

## File Locations

### Application Files
- All code in `/home/claude/app/`
- Templates in `/home/claude/app/templates/`
- Database in `/home/claude/instance/` (SQLite)

### Configuration
- Environment variables in `/home/claude/.env`
- Application config in `/home/claude/app/config.py`

## Troubleshooting

### Database Issues
If you need to reset the database:
```bash
rm instance/beam_selector.db
python init_db.py
```

### Port Already in Use
Change port in `run.py` or stop other applications using port 5000

### Import Errors
Ensure all dependencies are installed:
```bash
pip install -r requirements.txt
```

## Brand Colors (Lumberbank)
- Primary Blue: #0066B3
- Orange/Gold: #F69321  
- Dark Navy: #003366

These are used throughout the interface for consistent branding.

## Support
For questions or issues, refer to the design specification document:
`docs/beam-selector-design-spec.md`
