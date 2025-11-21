# LBDesign - Lumberbank Design Calculator

## Quick Start Guide

### 1. Install Dependencies

```bash
pip install Flask
```

(Or use the full requirements.txt when ready)

### 2. Run the Application

```bash
python run.py
```

### 3. Open in Browser

Navigate to: `http://localhost:5000`

### 4. Test the API

Click the "Test Hello World API" button on the landing page. You should see a JSON response appear below the button.

You can also test the API directly:
```bash
curl http://localhost:5000/api/v1/hello
```

## Project Structure

```
LBDesign/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── config.py            # Configuration
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── web.py           # Web page routes
│   │   └── api.py           # API endpoints
│   ├── templates/
│   │   ├── base.html        # Base template
│   │   └── index.html       # Landing page
│   └── static/
│       ├── css/
│       │   └── main.css     # Lumberbank styling
│       └── js/
│           ├── main.js
│           └── api-test.js  # API test functionality
└── run.py                   # Application entry point
```

## What's Working

- ✅ Flask application running
- ✅ Landing page with Lumberbank branding
- ✅ API endpoint (`/api/v1/hello`)
- ✅ JavaScript calling API endpoint
- ✅ Response displayed on page

## Next Steps

- Add database connection
- Implement user authentication
- Create project management
- Build calculation engine
- Add beam design interface
