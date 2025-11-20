# API Documentation

## Authentication
All API endpoints require authentication via JWT tokens or API keys.

## Endpoints

### Projects
- `GET /api/projects` - List all projects
- `POST /api/projects` - Create new project
- `GET /api/projects/<id>` - Get project details
- `PUT /api/projects/<id>` - Update project
- `DELETE /api/projects/<id>` - Delete project

### Beams
- `GET /api/projects/<id>/beams` - List beams in project
- `POST /api/projects/<id>/beams` - Create new beam
- `GET /api/beams/<id>` - Get beam details
- `PUT /api/beams/<id>` - Update beam
- `DELETE /api/beams/<id>` - Delete beam

### Calculations
- `POST /api/calculations/analyze` - Run beam analysis
- `POST /api/calculations/recommend` - Get product recommendations

### Products
- `GET /api/products` - List available products
- `GET /api/products/<id>` - Get product details

## Request/Response Formats
TODO: Add detailed schemas for each endpoint
