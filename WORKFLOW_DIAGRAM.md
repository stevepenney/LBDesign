# LBDesign Application Workflow

## User Journey

```
┌─────────────────────────────────────────────────────────────────┐
│                         START APPLICATION                        │
│                        python run.py                             │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
                   ┌──────────────┐
                   │   Login Page  │ ◄── New user? → Register
                   └──────┬───────┘
                          │ (admin/admin123)
                          ▼
            ┌─────────────────────────┐
            │   Projects Dashboard     │
            │  (List all projects)     │
            └────┬────────────────┬───┘
                 │                │
        Create   │                │   Select existing
        New      │                │   project
                 ▼                ▼
         ┌───────────────┐  ┌──────────────────┐
         │ New Project   │  │ Project Detail    │
         │   Form        │  │ • View info       │
         └──────┬────────┘  │ • List beams      │
                │           └───────┬───────────┘
                │                   │
                ▼                   │ Add Beam
         ┌────────────────┐         │
         │ Project Created│         │
         └──────┬─────────┘         │
                │                   │
                └──────────┬────────┘
                           │
                           ▼
                  ┌─────────────────┐
                  │  New Beam Form  │
                  │ • Name/Reference │
                  │ • Member Type    │
                  │ • Span/Spacing   │
                  │ • Loads          │
                  └────────┬─────────┘
                           │
                           ▼
                  ┌──────────────────┐
                  │   Beam Created    │
                  │  (Ready for calc) │
                  └────────┬──────────┘
                           │
                           ▼
                  ┌──────────────────┐
                  │   Beam Detail     │
                  │ • View parameters │
                  │ • Edit            │
                  │ • Delete          │
                  └───────────────────┘
```

## Data Flow Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                           WEB BROWSER                             │
│                     (Templates/HTML/Forms)                        │
└────────────────────────┬─────────────────────────────────────────┘
                         │ HTTP Request
                         ▼
              ┌──────────────────────┐
              │   Flask Routes       │
              │  • auth.py           │
              │  • projects.py       │
              │  • beams.py          │
              └──────────┬───────────┘
                         │ Call repository methods
                         ▼
              ┌──────────────────────┐
              │   Repositories       │
              │  • UserRepository    │
              │  • ProjectRepository │
              │  • BeamRepository    │
              └──────────┬───────────┘
                         │ ORM operations
                         ▼
              ┌──────────────────────┐
              │   SQLAlchemy ORM     │
              │  (Database models)   │
              └──────────┬───────────┘
                         │ SQL queries
                         ▼
              ┌──────────────────────┐
              │      Database        │
              │ SQLite/MySQL/MSSQL   │
              └──────────────────────┘
```

## Authentication Flow

```
User → Login Form → auth.py → UserRepository.get_by_username()
                                      ↓
                              Check password hash
                                      ↓
                            Valid? → login_user()
                                      ↓
                              Flask-Login session
                                      ↓
                              Set current_user
                                      ↓
                            Redirect to dashboard
```

## CRUD Operations Example: Creating a Beam

```
1. User fills form
   └→ POST /beams/project/1/create
      
2. beams.py: create() route
   ├→ Validate form data
   ├→ Check user permissions
   └→ Call BeamRepository.create_beam()
      
3. BeamRepository.create_beam()
   ├→ Create Beam model instance
   ├→ Set all attributes
   └→ db.session.add() & commit()
      
4. Database
   └→ INSERT INTO beams ...
      
5. Response
   ├→ Flash success message
   └→ Redirect to project detail
```

## File Organization Logic

```
app/
├── models/              ← Database tables (What we store)
│   ├── user.py         ← Users table
│   ├── project.py      ← Projects table
│   └── beam.py         ← Beams table
│
├── database/
│   └── repositories/    ← How we access data
│       ├── user_repository.py
│       ├── project_repository.py
│       └── beam_repository.py
│
├── routes/              ← Web endpoints (URLs)
│   ├── auth.py         ← /auth/login, /auth/register
│   ├── projects.py     ← /projects/*
│   └── beams.py        ← /beams/*
│
└── templates/           ← What users see
    ├── base.html       ← Common layout
    ├── auth/           ← Login/register pages
    ├── projects/       ← Project pages
    └── beams/          ← Beam pages
```

## Current vs Future State

### ✅ Current (Phase 1 - Complete)
- User authentication
- Project CRUD
- Beam CRUD with loads
- Form-based data entry
- Basic validation
- Role-based access

### 🔄 Next (Phase 2 - To Build)
- Calculation engine
  ├→ AS/NZS1170 implementation
  ├→ NZS3603 implementation
  ├→ Moment/shear/deflection calcs
  └→ Product evaluation

### 🔮 Future (Phase 3+)
- Product catalog
- Interactive SVG interface
- PDF reports
- API endpoints
- Cost estimation

## Permission Hierarchy

```
SUPERUSER (Level 3) ────────────────┐
    │                               │
    ├─ All ADMIN capabilities       │
    ├─ Manage standards             │
    └─ System configuration         │
                                    │
ADMIN (Level 2) ────────────────────┤
    │                               │
    ├─ All DETAILER capabilities    │
    ├─ Manage users                 │
    ├─ Manage products              │
    └─ View all projects            │
                                    │
DETAILER (Level 1) ─────────────────┤
    │                               │
    ├─ All USER capabilities        │
    ├─ Create projects              │
    ├─ Edit own projects            │
    └─ Create/edit beams            │
                                    │
USER (Level 0) ─────────────────────┘
    │
    ├─ View own projects
    └─ View beam details
```

## Technology Stack

```
Frontend:
├── HTML5 (Jinja2 templates)
├── CSS3 (inline in base.html)
└── JavaScript (for future enhancements)

Backend:
├── Python 3.x
├── Flask (web framework)
├── Flask-Login (authentication)
├── Flask-SQLAlchemy (ORM)
└── Werkzeug (password hashing)

Database:
├── SQLite (development)
├── MySQL (production option)
└── SQL Server (production option)

Security:
├── Bcrypt (password hashing)
├── Session management
├── CSRF protection (Flask-WTF)
└── Role-based access control
```

## Key Features Summary

```
✓ Multi-database support (SQLite/MySQL/MSSQL)
✓ Role-based access (4 levels)
✓ Project management (full CRUD)
✓ Beam management (full CRUD)
✓ Load inputs (dead, live, point loads)
✓ User authentication & sessions
✓ Lumberbank branding
✓ Form validation & feedback
✓ Owner-based permissions
✓ Cascade deletes
✓ Clean code architecture
✓ Repository pattern
✓ Ready for calculation engine
```
