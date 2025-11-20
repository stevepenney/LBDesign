# Lumberbank Beam Selector - Design Specification

## 1. Executive Summary

### 1.1 Project Overview
Web-based structural design calculator for floor and roof members serving dual purposes:
- **Internal**: Quote generation and layout production
- **External**: Customer design validation and product selection

### 1.2 Business Context
- **Driver**: Current proprietary design tool (Nelson Pine) losing support within 1 year
- **Status**: Essential replacement (not optional development)
- **Timeline**: 12-month runway for development and validation

### 1.3 Strategic Positioning
Position Lumberbank as trusted advisor by:
- Including standard SG8 timber in recommendations even when no direct sales benefit
- Prioritizing customer needs over immediate revenue
- Providing transparent, standards-based engineering calculations

---

## 2. Product Scope

### 2.1 Product Portfolio
**Manufactured Products:**
- Lumberworx I-beams (various depths and configurations)

**Distributed Products:**
- LVL (Laminated Veneer Lumber)
- Glulam (Glued Laminated Timber)
- Standard SG8 timber (competitive products)

### 2.2 Regional Coverage
**Initial Release:**
- New Zealand (AS/NZS1170, NZS3603)

**Future Expansion:**
- Australia (AS/NZS1170, AS1684)
- Other regions as required

### 2.3 Calculation Types
**Member Types:**
- Floor joists
- Roof rafters
- Beams (various applications)
- Load-bearing members
- Cantilevers (if applicable)

**Load Cases:**
- Dead loads
- Live loads
- Wind loads (where applicable)
- Snow loads (where applicable)
- Point loads
- Distributed loads
- Combined load scenarios

---

## 3. System Architecture

### 3.1 Technology Stack
- **Backend**: Python Flask
- **Database**: SQLAlchemy ORM (supporting MySQL, SQL Server, SQLite)
- **Frontend**: Jinja2 templates, HTML5, CSS3, JavaScript
- **API**: RESTful API for future integrations

### 3.2 Database Abstraction
- Repository pattern for database independence
- Support for MySQL, SQL Server, and SQLite
- Migration framework (Alembic) for schema versioning

### 3.3 Architecture Patterns
- **MVC Pattern**: Clear separation of models, views, controllers
- **Service Layer**: Business logic isolated from routing
- **Repository Pattern**: Data access abstraction
- **Standards Registry**: Dynamic loading of calculation standards

---

## 4. User Management

### 4.1 User Roles and Hierarchy
1. **USER** (Base level)
   - View projects and results
   - Read-only access to calculations
   - Cannot create or modify designs

2. **DETAILER** (Inherits USER)
   - Create and edit projects
   - Design beams and structural members
   - Run calculations
   - Save and retrieve designs

3. **ADMIN** (Inherits DETAILER)
   - Manage users (create, edit, deactivate)
   - Manage product catalog
   - View system usage statistics
   - Configure regional settings

4. **SUPERUSER** (Inherits ADMIN)
   - Manage engineering standards
   - Activate/deactivate standard versions
   - Configure calculation parameters
   - System configuration access
   - Manage regions and locations

### 4.2 Authentication & Authorization
- Secure login system (bcrypt password hashing)
- Session management (Flask-Login)
- Role-based access control (RBAC)
- Permission decorators for route protection

---

## 5. Data Model

### 5.1 Core Entities

#### User
- user_id (PK)
- username
- email
- password_hash
- role (FK to Role)
- created_at
- last_login
- is_active

#### Role
- role_id (PK)
- role_name (USER, DETAILER, ADMIN, SUPERUSER)
- permissions (JSON or relationship to Permissions table)

#### Project
- project_id (PK)
- user_id (FK)
- project_name
- region_id (FK)
- created_at
- updated_at
- project_parameters (JSON - overall setup)
  - Location/region
  - Building type
  - Wind zone
  - Snow zone (if applicable)
  - Other environmental factors

#### Beam
- beam_id (PK)
- project_id (FK)
- beam_name/reference
- member_type (floor joist, rafter, beam, etc.)
- span
- spacing (if applicable)
- load_parameters (JSON)
  - Dead load
  - Live load
  - Point loads
  - Load locations
- calculation_standard_used
- calculation_version
- recommended_products (JSON or FK)
- selected_product (FK to Product)
- created_at
- updated_at

#### Product
- product_id (PK)
- product_code
- product_name
- manufacturer (Lumberbank, Other)
- product_type (I-beam, LVL, Glulam, SG8 timber)
- specifications (JSON)
  - Depth
  - Width
  - Grade
  - Section properties
  - Material properties
- is_active
- region_availability (JSON or relationship)

#### Region
- region_id (PK)
- region_name (New Zealand, Australia, etc.)
- standards_applicable (JSON)
  - AS/NZS1170
  - NZS3603
  - AS1684
- default_parameters (JSON)
  - Wind zones
  - Snow zones
  - Load factors

---

## 6. Calculation Engine

### 6.1 Standards Management

#### Standards Registry System
- Dynamic loading of calculation methods based on region
- Version tracking for all standards
- Ability to activate/deactivate standard versions
- Audit trail of which standard version was used for each calculation

#### Standard Version Tracking
```json
{
  "region": "new_zealand",
  "standard": "AS/NZS1170",
  "version": "2002",
  "effective_date": "2002-01-01",
  "status": "active",
  "superseded_by": null
}
```

### 6.2 Calculation Architecture

#### Base Standard Class
- Abstract base class defining standard interface
- All regional standards inherit from this
- Standard methods:
  - `calculate_loads()`
  - `calculate_moments()`
  - `calculate_shear()`
  - `calculate_deflection()`
  - `check_utilization()`
  - `recommend_products()`

#### Regional Implementation
```
services/standards/
├── base_standard.py          # Abstract base class
├── regions/
│   ├── new_zealand/
│   │   ├── as_nzs_1170.py   # Load calculations
│   │   └── nzs_3603.py      # Timber design
│   └── australia/
│       ├── as_1170.py       # Australian loads
│       └── as_1684.py       # Australian timber
└── versions/
    └── standard_versions.json
```

### 6.3 Calculation Workflow
1. **Input Validation**: Check all input parameters
2. **Load Calculation**: Calculate design loads per standard
3. **Structural Analysis**: Calculate moments, shears, deflections
4. **Product Evaluation**: Check each available product against requirements
5. **Ranking**: Rank products by suitability
6. **Output Generation**: Return ranked recommendations with utilization ratios

### 6.4 Output Format
```json
{
  "beam_id": "12345",
  "calculation_standard": "NZS3603:1993",
  "loads": {
    "dead_load": 0.5,
    "live_load": 1.5,
    "total_udl": 2.0
  },
  "demands": {
    "max_moment": 25.5,
    "max_shear": 12.3,
    "deflection_limit": 15.0
  },
  "recommendations": [
    {
      "rank": 1,
      "product_code": "LWX-300",
      "product_name": "Lumberworx 300mm I-Beam",
      "utilization_bending": 0.78,
      "utilization_shear": 0.45,
      "deflection": 12.5,
      "status": "PASS",
      "notes": "Recommended - optimal sizing"
    },
    {
      "rank": 2,
      "product_code": "LVL-400x45",
      "product_name": "LVL 400x45",
      "utilization_bending": 0.65,
      "utilization_shear": 0.38,
      "deflection": 10.2,
      "status": "PASS",
      "notes": "Conservative option"
    }
  ]
}
```

---

## 7. API Design

### 7.1 API Architecture
- RESTful design principles
- JSON request/response format
- Authentication via JWT tokens or API keys
- Rate limiting for external access
- Versioned endpoints (/api/v1/)

### 7.2 Core Endpoints

#### Authentication
```
POST   /api/v1/auth/login
POST   /api/v1/auth/logout
POST   /api/v1/auth/refresh
GET    /api/v1/auth/verify
```

#### Projects
```
GET    /api/v1/projects              # List all projects
POST   /api/v1/projects              # Create project
GET    /api/v1/projects/{id}         # Get project details
PUT    /api/v1/projects/{id}         # Update project
DELETE /api/v1/projects/{id}         # Delete project
```

#### Beams
```
GET    /api/v1/projects/{id}/beams   # List beams in project
POST   /api/v1/projects/{id}/beams   # Create beam in project
GET    /api/v1/beams/{id}            # Get beam details
PUT    /api/v1/beams/{id}            # Update beam
DELETE /api/v1/beams/{id}            # Delete beam
```

#### Calculations
```
POST   /api/v1/calculations/analyze           # Run structural analysis
POST   /api/v1/calculations/recommend         # Get product recommendations
GET    /api/v1/calculations/{beam_id}/results # Get calculation results
```

#### Products
```
GET    /api/v1/products              # List available products
GET    /api/v1/products/{id}         # Get product details
POST   /api/v1/products              # Create product (ADMIN)
PUT    /api/v1/products/{id}         # Update product (ADMIN)
DELETE /api/v1/products/{id}         # Delete product (ADMIN)
```

#### Admin
```
GET    /api/v1/admin/users           # List users
POST   /api/v1/admin/users           # Create user
PUT    /api/v1/admin/users/{id}      # Update user
GET    /api/v1/admin/standards       # List standards
PUT    /api/v1/admin/standards/{id}  # Update standard config
```

---

## 8. User Interface Design

### 8.1 Design Principles
- Clean, professional aesthetic matching Lumberbank brand
- High contrast for technical data readability
- Responsive design (mobile-first approach)
- Minimal cognitive load - progressive disclosure
- Clear visual hierarchy

### 8.2 Color Scheme (Lumberbank Brand)
- **Primary Blue**: #0066B3 (headers, navigation, structural elements)
- **Orange/Gold**: #F69321 (CTAs, highlights, recommendations)
- **Dark Navy**: #003366 (contrast elements)
- **Neutrals**: White, light grey, medium grey backgrounds
- **Status Colors**: Green (pass), Red (fail), Amber (warning)

### 8.3 Typography
- **Font Family**: Modern sans-serif (Open Sans, Lato, or Roboto)
- **Sizes**: Clear hierarchy from h1 (40px) to body (16px)
- **Weights**: Regular (400), Semi-bold (600), Bold (700)

### 8.4 Key User Flows

#### 8.4.1 Project Creation Flow
1. Dashboard → "New Project" button
2. Project setup form:
   - Project name
   - Region selection (triggers appropriate standards)
   - Building type
   - Environmental parameters (wind zone, etc.)
3. Save project → Navigate to project detail page

#### 8.4.2 Beam Design Flow
1. Project detail page → "Add Beam" button
2. Member selection (future: interactive SVG diagram)
3. Input form:
   - Beam reference/name
   - Span
   - Spacing (if applicable)
   - Load inputs (dead, live, point loads)
   - Load positions
4. "Calculate" button → Processing
5. Results page:
   - Summary of demands
   - Ranked product recommendations
   - Utilization ratios
   - Deflection values
   - Pass/fail status
6. Select product → Save to project

#### 8.4.3 Results Display
- **Card-based layout** for each recommended product
- **Visual indicators**: Color-coded utilization bars
- **Ranking**: Clear 1st, 2nd, 3rd choice indication
- **Details**: Expandable sections for full calculation details
- **Actions**: Select, Compare, Print, Export

### 8.5 Page Templates

#### Base Template
- Header with logo and navigation
- User info/logout in top right
- Main content area
- Footer with links and contact info

#### Dashboard
- Project list (cards or table)
- Quick stats (total projects, recent activity)
- "New Project" CTA button
- Search/filter functionality

#### Project Detail
- Project info header
- Beam list (table with key parameters)
- "Add Beam" button
- Edit/delete project actions

#### Calculator Interface
- Clean input form on left
- Visual member diagram (future enhancement)
- "Calculate" button (orange, prominent)
- Real-time validation feedback

#### Results Page
- Calculation summary at top
- Product recommendations as cards
- Sort/filter options
- Export functionality

---

## 9. Future Enhancements (Parked Features)

### 9.1 Interactive SVG Member Selection
- Convert structural diagrams to interactive SVG
- Click on floor joist → pre-populate calculator with typical values
- Click on rafter → different defaults
- Hover effects with Lumberbank orange highlighting
- Visual feedback for which members are already designed

**Technical Approach:**
- SVG files with unique IDs for each member type
- JavaScript click handlers
- CSS hover effects
- Navigation to calculator with query parameters

### 9.2 Additional Features to Consider
- PDF report generation
- Email sharing of designs
- Project templates for common building types
- Mobile app integration
- Batch calculation capabilities
- 3D visualization of framing
- Integration with CAD systems
- Material takeoff reports
- Cost estimation (with product pricing)

---

## 10. Development Phases

### 10.1 Phase 1: MVP Foundation (Current Focus)
**Objectives:**
- Set up project structure ✓
- Database models and migrations
- User authentication and authorization
- Basic project and beam CRUD operations
- Placeholder calculation engine (returns test values)

**Deliverables:**
- Working login system
- Create/view/edit/delete projects
- Create/view/edit/delete beams
- Mock calculation results
- Basic API endpoints

### 10.2 Phase 2: Calculation Engine
**Objectives:**
- Implement NZ standards (AS/NZS1170, NZS3603)
- Load calculations
- Structural analysis
- Product evaluation and ranking
- Validation against known results

**Deliverables:**
- Functional calculation engine
- Accurate results for standard cases
- Unit tests for calculations
- Documentation of calculation methods

### 10.3 Phase 3: Product Catalog & Recommendations
**Objectives:**
- Complete product database
- Product selector logic
- Recommendation engine
- Admin interface for product management

**Deliverables:**
- Full Lumberworx range in database
- LVL/Glulam products
- SG8 timber options
- Working recommendation system

### 10.4 Phase 4: UI Polish & Enhancement
**Objectives:**
- Professional styling (Lumberbank brand)
- Improved UX
- Responsive design
- Interactive elements

**Deliverables:**
- Branded interface
- Mobile-responsive design
- Interactive SVG member selection
- Print/export capabilities

### 10.5 Phase 5: Testing & Validation
**Objectives:**
- Compare results with current system
- Validation by engineering team
- User acceptance testing
- Bug fixes and refinement

**Deliverables:**
- Test report showing accuracy
- Sign-off from engineering
- Training materials
- Deployment-ready system

### 10.6 Phase 6: Australian Expansion (Future)
**Objectives:**
- Implement Australian standards
- Regional product catalog
- Region-specific parameters

---

## 11. Technical Considerations

### 11.1 Version Control & Documentation
- Git repository with clear branch strategy
- Calculation methodology documentation
- API documentation (consider Swagger/OpenAPI)
- Inline code comments
- User manual/help system

### 11.2 Testing Strategy
- **Unit Tests**: All calculation functions
- **Integration Tests**: API endpoints
- **Repository Tests**: Database operations
- **Validation Tests**: Compare with known solutions
- **User Acceptance Tests**: Real-world scenarios

### 11.3 Performance Considerations
- Database indexing on frequently queried fields
- Caching of calculation results
- API rate limiting
- Efficient product filtering algorithms
- Query optimization

### 11.4 Security
- HTTPS only in production
- Input validation and sanitization
- SQL injection prevention (ORM handles this)
- XSS protection
- CSRF tokens on forms
- Secure password storage (bcrypt)
- Role-based access control

### 11.5 Deployment
- Development environment (local)
- Staging environment (for testing)
- Production environment
- Database backup strategy
- Rollback procedures
- Monitoring and logging

---

## 12. Standards Documentation

### 12.1 Required Standards Documentation
For each standard implemented, maintain:
- Standard reference (e.g., "NZS3603:1993")
- Version and amendment date
- Section references used
- Assumptions made
- Limitations of implementation
- Validation test cases

### 12.2 Calculation Validation
- Known solutions from current system
- Hand calculations for simple cases
- Third-party engineering review
- Documented test cases with expected results

---

## 13. Data Migration

### 13.1 From Current System (Nelson Pine Tool)
**Note:** Original source code unavailable - reverse engineering required

**Approach:**
1. Document all calculation cases from current system
2. Run known projects through current system
3. Capture inputs and outputs
4. Use as validation test suite
5. Reverse engineer calculation methodology
6. Validate new system against captured results

**Timeline:** 12 months provides adequate runway

---

## 14. Success Criteria

### 14.1 Functional Requirements Met
- [ ] User authentication working
- [ ] Role-based access control implemented
- [ ] Projects can be created and managed
- [ ] Beam designs can be created and calculated
- [ ] Calculations produce accurate results (validated)
- [ ] Product recommendations match engineering judgment
- [ ] API endpoints functional
- [ ] Regional standards properly implemented

### 14.2 Performance Metrics
- Calculation response time < 2 seconds
- Page load time < 3 seconds
- API response time < 1 second
- Support 50+ concurrent users

### 14.3 Business Objectives
- Replace Nelson Pine tool before support ends
- Support both internal and external users
- Enable quote generation workflow
- Provide customer-facing design validation
- Position Lumberbank as trusted technical advisor

---

## 15. Risk Management

### 15.1 Technical Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Calculation accuracy issues | Medium | High | Extensive validation, engineering review |
| Database compatibility issues | Low | Medium | Repository pattern, early testing |
| Performance bottlenecks | Low | Medium | Profiling, optimization, caching |
| API security vulnerabilities | Medium | High | Security audit, penetration testing |

### 15.2 Project Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Timeline overrun | Medium | High | Phased approach, MVP first |
| Insufficient validation time | Medium | High | 12-month timeline includes buffer |
| Scope creep | Medium | Medium | Clear phase definitions, feature parking |
| Resource constraints (single dev) | High | Medium | Clear priorities, potential to add resources |

### 15.3 Business Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| User adoption resistance | Low | High | Training, gradual rollout, user involvement |
| Results differ from current system | Medium | High | Validation plan, document differences |
| Current system fails before ready | Low | Critical | Prioritize critical functionality first |

---

## 16. Open Questions & Decisions Needed

### 16.1 Technical Decisions
- [ ] Choose specific database for production (MySQL vs SQL Server)
- [ ] API authentication method (JWT vs API keys vs both)
- [ ] Hosting/deployment environment
- [ ] Email service for notifications
- [ ] Backup and disaster recovery strategy

### 16.2 Business Decisions
- [ ] External user access model (open vs approved accounts)
- [ ] Product pricing display (yes/no, to whom)
- [ ] Branding for external users vs internal
- [ ] Support and training approach
- [ ] Rollout strategy (big bang vs phased)

### 16.3 Functional Decisions
- [ ] Complete list of member types to support
- [ ] All load cases required
- [ ] Specific product catalog to include initially
- [ ] Level of detail in calculation output
- [ ] Report/export formats required

---

## 17. Next Steps (Immediate)

### 17.1 Development Tasks
1. Initialize Flask application
2. Set up database connection and models
3. Implement user authentication
4. Create basic CRUD routes for projects and beams
5. Build placeholder calculation engine
6. Create basic templates with Lumberbank styling
7. Set up API structure

### 17.2 Documentation Tasks
1. Finalize list of calculation cases
2. Document current system behavior
3. Define validation test cases
4. Create API documentation framework

### 17.3 Design Tasks
1. Wireframes for key pages
2. Define UI components library
3. Plan interactive SVG implementation (future phase)

---

## Document Control

**Version:** 1.0  
**Date:** November 2024  
**Author:** Development Team  
**Status:** Draft  
**Review Date:** TBD  

**Revision History:**
| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | Nov 2024 | Initial specification | Dev Team |

---

## Appendices

### Appendix A: Glossary
- **SG8**: Structural Grade 8 timber
- **LVL**: Laminated Veneer Lumber
- **Glulam**: Glued Laminated Timber
- **I-Beam**: Engineered wood I-shaped beam
- **UDL**: Uniformly Distributed Load
- **AS/NZS**: Australian/New Zealand Standard
- **CRUD**: Create, Read, Update, Delete

### Appendix B: References
- AS/NZS 1170 (Structural design actions)
- NZS 3603 (Timber structures standard)
- AS 1684 (Australian residential timber-framed construction)
- Lumberworx product specifications
- Nelson Pine tool documentation (if available)

### Appendix C: Contact Information
- Project Owner: [TBD]
- Lead Developer: Steve
- Engineering Review: [TBD]
- Stakeholders: [TBD]
