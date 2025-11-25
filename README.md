# LBDesign - Lumberbank Beam Design Calculator

A Flask-based structural design calculator for floor joists, rafters, and beams. Built to replace the legacy Nelson Pine tool with a modern, standards-based approach.

## 🎯 Project Status

**Phase 1: MVP Foundation** ✅ **COMPLETE**

Full CRUD operations for projects and beams are implemented and ready to use.

## ✨ Features

- 🔐 User authentication with role-based access (USER, DETAILER, ADMIN, SUPERUSER)
- 📁 Project management with full CRUD operations
- 📏 Beam design with comprehensive load inputs
- 🗄️ Multi-database support (SQLite, MySQL, SQL Server)
- 🎨 Professional UI with Lumberbank branding
- 👥 Multi-user support with ownership controls
- 🔒 Secure password hashing and session management

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Initialize the database:**
   ```bash
   python init_db.py
   ```
   This creates a SQLite database and an admin user.

3. **Run the application:**
   ```bash
   python run.py
   ```

4. **Open your browser:**
   Navigate to http://localhost:5000

5. **Login:**
   - Username: `admin`
   - Password: `admin123`

## 📖 Documentation

- **[INDEX.md](INDEX.md)** - Complete file index and project overview
- **[IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)** - What's been built
- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Detailed setup instructions
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)** - Common commands
- **[WORKFLOW_DIAGRAM.md](WORKFLOW_DIAGRAM.md)** - Architecture diagrams

## 🏗️ Project Structure

```
├── app/
│   ├── __init__.py                 # Application factory
│   ├── config.py                   # Configuration
│   ├── extensions.py               # Flask extensions
│   ├── models/                     # Database models
│   │   ├── user.py
│   │   ├── project.py
│   │   └── beam.py
│   ├── database/
│   │   └── repositories/           # Data access layer
│   ├── routes/                     # Web routes
│   │   ├── auth.py
│   │   ├── projects.py
│   │   └── beams.py
│   └── templates/                  # HTML templates
├── instance/                       # Database location
├── .env                           # Configuration
├── init_db.py                     # Database setup
└── requirements.txt               # Dependencies
```

## 🎨 Brand Guidelines

**Lumberbank Colors:**
- Primary Blue: `#0066B3`
- Orange/Gold: `#F69321`
- Dark Navy: `#003366`

## 🔧 Configuration

Edit `.env` to change database settings:

**SQLite (Default - Development):**
```env
DATABASE_TYPE=sqlite
```

**MySQL (Production):**
```env
DATABASE_TYPE=mysql
DATABASE_HOST=localhost
DATABASE_PORT=3306
DATABASE_NAME=beam_selector
DATABASE_USER=your_username
DATABASE_PASSWORD=your_password
```

**SQL Server (Production):**
```env
DATABASE_TYPE=mssql
DATABASE_HOST=localhost
DATABASE_PORT=1433
DATABASE_NAME=beam_selector
DATABASE_USER=your_username
DATABASE_PASSWORD=your_password
```

## 👤 User Roles

1. **USER** - View only access
2. **DETAILER** - Create and edit projects/beams (default for new users)
3. **ADMIN** - User management, system access
4. **SUPERUSER** - Full system control, standards management

## 📝 Usage

### Create a Project

1. Click "New Project" from the dashboard
2. Enter project details (name, region, client, etc.)
3. Click "Create Project"

### Add Beams

1. From a project detail page, click "Add Beam"
2. Enter beam parameters:
   - Name and reference code
   - Member type (floor joist, rafter, beam, etc.)
   - Span and spacing
   - Dead and live loads
   - Optional point loads
3. Click "Create Beam"

### View and Edit

- Projects list shows all your projects
- Click any project to see its beams
- Edit or delete as needed with confirmation prompts

## 🗄️ Database Schema

**Users:**
- Authentication and authorization
- Role-based permissions

**Projects:**
- Client information
- Location and region
- Design team details

**Beams:**
- Member properties
- Loading parameters
- Calculation results (ready for Phase 2)

## 🔜 Roadmap

**Phase 2: Calculation Engine** (Next)
- AS/NZS1170 implementation
- NZS3603 timber design
- Moment, shear, deflection calculations
- Product evaluation

**Phase 3: Product Catalog**
- Lumberworx I-beams
- LVL and Glulam products
- SG8 timber options
- Recommendation engine

**Phase 4: Enhanced UI**
- Interactive SVG beam diagrams
- Real-time calculation feedback
- PDF report generation
- Mobile optimization

**Phase 5: API Development**
- RESTful API endpoints
- External integrations
- Authentication tokens

## 🧪 Testing

Reset database for testing:
```bash
rm instance/beam_selector.db
python init_db.py
```

## 🐛 Troubleshooting

**Port 5000 already in use?**
Edit `run.py` and change the port number.

**Import errors?**
```bash
pip install -r requirements.txt
```

**Database errors?**
Delete and recreate:
```bash
rm instance/beam_selector.db
python init_db.py
```

## 🔐 Security

- Passwords hashed with bcrypt
- Session-based authentication
- SQL injection prevention via ORM
- XSS protection with Jinja2
- CSRF protection ready (Flask-WTF)
- Role-based access control

## 🏢 Business Context

LBDesign replaces the legacy Nelson Pine tool which is losing support within 12 months. The application serves:

- **Internal use:** Quote generation and layout production
- **External use:** Customer design validation
- **Strategic positioning:** Including competitor products shows Lumberbank as trusted advisors

## 📊 Technology Stack

- **Backend:** Python Flask
- **Database:** SQLAlchemy ORM (SQLite/MySQL/SQL Server)
- **Authentication:** Flask-Login
- **Frontend:** Jinja2 templates, HTML5, CSS3
- **Security:** bcrypt, Werkzeug

## 🤝 Contributing

This is an internal Lumberbank project. For development:

1. Keep code clean and well-documented
2. Follow the repository pattern
3. Test all CRUD operations
4. Maintain consistent styling
5. Update documentation

## 📄 License

Internal Lumberbank project - All rights reserved.

## 👨‍💻 Developer

Built by Steve for Lumberbank, New Zealand

## 📞 Support

For questions or issues:
1. Review documentation in this folder
2. Check SETUP_GUIDE.md for common problems
3. Contact the development team

## ⚡ Performance

- Database indexing on foreign keys
- Optimized queries via repositories
- Session management
- Ready for caching in production

## 🌏 Regional Support

**Current:**
- New Zealand (AS/NZS1170, NZS3603)

**Planned:**
- Australia (AS/NZS1170, AS1684)

## 📈 Version History

- **v1.0** (November 2024) - Initial release with complete CRUD operations
- Phase 1 complete, ready for calculation engine development

---

**Built with ❤️ for Lumberbank**
