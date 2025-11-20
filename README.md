# Beam Selector Application

Engineering calculation and product selection system for structural beams.

## Features

- Multi-region support (New Zealand, Australia)
- Standards-based calculations (AS/NZS1170, NZS3603, etc.)
- User role hierarchy (User, Detailer, Admin, Superuser)
- RESTful API for integrations
- Database agnostic (MySQL, SQL Server, SQLite)

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your database credentials
```

3. Initialize database:
```bash
flask db upgrade
```

4. Run application:
```bash
python run.py
```

## Project Structure

- `app/` - Main application code
- `app/models/` - Database models
- `app/routes/` - Web and API routes
- `app/services/` - Business logic and calculation engine
- `app/database/` - Database abstraction layer
- `app/auth/` - Authentication and authorization
- `tests/` - Test suite

## Development

See `docs/` for detailed documentation on:
- API endpoints
- Standards implementation
- Database schema
