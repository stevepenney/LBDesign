# LBDesign - Lumberbank Design Calculator

## Quick Start Guide

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Database

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` and choose your database type:

**Option A: SQLite (Default - for development)**
```
DATABASE_TYPE=sqlite
```

**Option B: MySQL**
```
DATABASE_TYPE=mysql
DATABASE_HOST=localhost
DATABASE_PORT=3306
DATABASE_NAME=lbdesign
DATABASE_USER=your_user
DATABASE_PASSWORD=your_password
```

**Option C: SQL Server**
```
DATABASE_TYPE=mssql
DATABASE_HOST=your_server
DATABASE_PORT=1433
DATABASE_NAME=lbdesign
DATABASE_USER=your_user
DATABASE_PASSWORD=your_password
```

### 3. Initialize Database

```bash
python init_db.py
```

This will:
- Create all database tables
- Initialize roles (USER, DETAILER, ADMIN, SUPERUSER)
- Initialize regions (New Zealand, Australia)
- Add sample products
- Create default admin user

**Default Login:**
- Username: `admin`
- Password: `admin123` (⚠️ Change in production!)

### 4. Run the Application

```bash
python run.py
```

### 5. Open in Browser

Navigate to: `http://localhost:5000`

### 6. Test the API

Click the "Test Hello World API" button on the landing page.

You can also test directly:
```bash
curl http://localhost:5000/api/v1/hello
```

## Project Structure

```
LBDesign/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Configuration with DB abstraction
│   ├── extensions.py        # Flask extensions (SQLAlchemy, etc.)
│   ├── models/              # Database models
│   │   ├── __init__.py
│   │   ├── user.py          # User model
│   │   ├── role.py          # Role model
│   │   ├── project.py       # Project model
│   │   ├── beam.py          # Beam design model
│   │   ├── product.py       # Product catalog model
│   │   └── region.py        # Region/standards model
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── web.py           # Web page routes
│   │   └── api/
│   │       └── __init__.py  # API endpoints
│   ├── templates/
│   │   ├── base.html        # Base template
│   │   └── index.html       # Landing page
│   └── static/
│       ├── css/
│       │   └── main.css     # Lumberbank styling
│       └── js/
│           ├── main.js
│           └── api-test.js  # API test functionality
├── init_db.py               # Database initialization script
├── run.py                   # Application entry point
├── requirements.txt         # Python dependencies
└── .env.example             # Environment variables template
```

## Database Models

### User Hierarchy
1. **USER** - View-only access
2. **DETAILER** - Create and edit designs
3. **ADMIN** - Manage users and products
4. **SUPERUSER** - Full system access

### Core Models
- **User**: Authentication and authorization
- **Role**: User permission levels
- **Project**: Container for beam designs
- **Beam**: Individual structural member designs
- **Product**: Catalog of available products (I-beams, LVL, etc.)
- **Region**: Geographic regions with applicable standards

## Database Abstraction

The application supports three database types:
- **SQLite** - For development (no server required)
- **MySQL/MariaDB** - For production
- **SQL Server** - For production

Switch between them by changing `DATABASE_TYPE` in `.env`

## What's Working

- ✅ Flask application running
- ✅ Landing page with Lumberbank branding
- ✅ API endpoint (`/api/v1/hello`)
- ✅ JavaScript calling API endpoint
- ✅ Database abstraction layer (SQLite, MySQL, SQL Server)
- ✅ Complete data models
- ✅ Database initialization script

## Next Steps

- Add user authentication/login
- Create project management interface
- Build beam design interface
- Implement calculation engine
- Add product recommendations

## Development Notes

### Running Migrations (when changing models)

```bash
flask db init
flask db migrate -m "Description of changes"
flask db upgrade
```

### Resetting Database

```bash
# Delete database file (SQLite)
rm lbdesign.db

# Or drop tables in MySQL/SQL Server
# Then re-run:
python init_db.py
```

### Checking Database

```bash
# For SQLite
sqlite3 lbdesign.db
.tables
.schema users

# For MySQL
mysql -u username -p
USE lbdesign;
SHOW TABLES;
DESCRIBE users;
```
