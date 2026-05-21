# LBDesign — Claude Code Guide

## Project

Lumberbank Midfloor & Rafter Estimation Tool. Django 6 / PostgreSQL multi-tenant web app
for merchant customers to generate wholesale timber framing estimates.

Virtual environment: `venv/` (Windows). Always use `venv/Scripts/python` not bare `python`.

---

## Commands

```bash
# Run dev server
venv/Scripts/python manage.py runserver

# After any model change
venv/Scripts/python manage.py makemigrations
venv/Scripts/python manage.py migrate
venv/Scripts/python manage.py check          # always run — catches FK/import errors

# Dummy data
venv/Scripts/python manage.py load_dummy_data
venv/Scripts/python manage.py load_dummy_data --reset

# Django shell
venv/Scripts/python manage.py shell
```

---

## App Structure

| App | Owns |
|-----|------|
| `accounts` | Organisation, User (AbstractUser + role + org FK) |
| `core` | FreightSettings (singleton), RoofPitch (lookup) |
| `products` | Product, PriceBook, PriceBookEntry; `pricing.py` price resolver |
| `jobs` | Job, Section, FloorRoofArea, AdditionalBeam, DrawingUpload; `calculations.py` engine |
| `cutlist` | Cutlist Optimizer (no models yet — pure JS tool served by a single view) |

Templates live in `templates/` (project-level, not per-app).
Static files: `static/css/base.css`, `static/css/admin.css`, `static/js/base.js`.

---

## Key Conventions

### Models
- `Section` is the user-facing term for what the code calls Section (DB table `jobs_section`).
  Never call it "sub-job" in UI-facing text.
- `FloorRoofArea.joist_spacing` stores **mm as PositiveIntegerField** (e.g. 400, 450, 600).
  `spacing_m` property divides by 1000.
- `RoofPitch.pitch_degrees` stores degrees. `pitch_factor` is a computed property:
  `1 / cos(radians(pitch_degrees))`. Do not add a stored pitch_factor field.
- `PriceBook.is_default` — only one default allowed; `save()` enforces it.
- `FreightSettings` is a singleton; always use `FreightSettings.get()`, never `.objects.first()`.

### Pricing
- Price lookup: `products/pricing.py → get_product_price(product, organisation)`
- Resolution order: org's price book → default price book → None
- Org with `price_book = null` uses the default book for all products.

### Calculations
- Always call `run_subjob_calculation(section)` after saving a Section and its formsets.
- `run_job_estimate(job)` recalculates all sections + freight for the whole job.
- `member_schedule` JSON shape: `{'items': [...], 'has_unpriced': bool}`

### Forms & Formsets
- `SectionForm`, `FloorRoofAreaFormSet`, `AdditionalBeamFormSet` are in `jobs/forms.py`.
- Formset prefixes: `areas` and `beams`.
- Empty form cloning for JS uses `{{ formset.empty_form }}` with `__prefix__` replacement.

### Views
- Tenancy helpers: `_get_jobs_for_user(user)` and `_assert_job_access(user, job)`.
- Always `prefetch_related('sections')` when listing jobs to avoid N+1 queries.

### URLs (app_name = 'jobs')
- `jobs:section_create`, `jobs:section_edit`, `jobs:section_delete`
- `jobs:job_recalculate`

### Admin
- `RoofPitch` and `FreightSettings` are in the **Core** admin section.
- `PriceBook` is in the **Products** admin section.
- `Section` is in the **Jobs** admin section.

### Migrations
- Write migrations manually when the change is conceptual (rename, data migration, multi-step).
- Run `manage.py check` after every migration.
- After any model change always run `makemigrations` and check the generated file before applying.

---

## CSS / Frontend

- CSS variables defined in `static/css/base.css` under `:root {}` — use these everywhere.
- Admin styles in `static/css/admin.css` — loads `base.css` variables via the admin
  `extrastyle` block in `templates/admin/base_site.html`.
- Toast messages: fixed bottom-left, handled entirely in `static/js/base.js`.
  Class structure: `<li class="toast success|error|warning|info">`.
- Hard-refresh (Ctrl+Shift+R) after CSS changes to bust browser cache.

---

## Cutlist Optimizer

A browser-based bin-packing tool for optimising timber cutting lists. Pure JS front-end —
no Django models needed in phase 1. Source files currently in `cutlist/` (standalone),
to be migrated to:

| Source file | Django destination |
|---|---|
| `cutlist/cutlist.js` | `static/js/cutlist.js` |
| `cutlist/cutlist.css` | `static/css/cutlist.css` |
| `cutlist/cutlist.html` | `templates/cutlist/cutlist.html` (extends `base.html`) |

### Architecture
State lives in a single `project` JS object (jobDetails, tabs[], activeTabId, skippedData).
DOM is always rendered from state, never read back. Key functions in `cutlist.js`:
- `parseCSVAndCreateTabs()` — parses CSV input, creates one tab per member type (max 5)
- `calculateOptimization(tabId)` — runs First Fit Decreasing algorithm
- `advancedOptimizeAll()` — post-process: offcut reuse + bin consolidation
- `saveProject()` / `loadProject()` — serialise full state to/from JSON file

### CSS Variables
`cutlist.css` defines its own `:root` variables (`--primary-brown`, `--dark-brown`,
`--beige-bg`, etc.) — a brown Lumberbank palette, separate from the green site palette in
`base.css`. Keep them in `cutlist.css`; do not merge into `base.css`.

### Integration Notes
- Django app: `cutlist` (no models, one `TemplateView`)
- URL: `cutlist:cutlist_tool` → `/cutlist/`
- Template extends `base.html` — remove the standalone logo/header from the HTML; the
  site header already provides it.
- The standalone HTML wraps everything in `<div class="container">`. This conflicts with
  the site `.container` in `base.html`. Rename to `<div class="cutlist-content">` in both
  the template and `cutlist.css` when integrating.
- Load `cutlist.css` via `{% block extra_css %}` and `cutlist.js` via `{% block extra_js %}`.
- Add a **Cutlist** nav link in `templates/base.html` for authenticated users.
- Save/Load currently writes JSON to the user's local filesystem — no server storage needed
  yet. Future phase: `CutlistProject` model stored against a Job.

### Planned Features (not yet built)
- Feature 2: Lock individual sticks (exclude from re-optimisation) — needs `locked` flag
  on each bin and a checkbox UI on each stick diagram.
- Feature 3: Click a cut segment to edit inline — needs click handler on `.cut-segment`
  and a modal that writes back to state and re-runs optimisation.
- Feature 4 (nice to have): Drag-and-drop cut segments between sticks.
- Feature 5 (nice to have): Add/remove a cut directly in the results panel with live
  re-optimisation.

---

## Do / Don't

**Do:**
- Run `manage.py check` after every model or migration change.
- Read a file before editing it.
- Use `get_or_create` in data migrations and management commands.
- Keep `CLAUDE.md` and `memory/project_lbdesign.md` up to date at the end of each session.

**Don't:**
- Use "sub-job" anywhere in user-facing text or UI labels.
- Add a stored `pitch_factor` field to RoofPitch — it's always computed.
- Call `FreightSettings.objects.first()` — use `FreightSettings.get()`.
- Create new template files when editing an existing one works.
- Add comments that describe *what* the code does — only add them when the *why* is non-obvious.
- Over-engineer: no extra abstractions, fallbacks, or validation beyond what the task requires.

---

## Phase Vision

**Phase 1 (current):** Estimation tool + cutlist optimiser.
**Phase 2 (future):** Full design tool with expanded job management. The current `jobs` and
`cutlist` apps will grow; more apps may be added. Build with this trajectory in mind —
don't over-engineer now, but don't make choices that box out phase 2 expansion.

## Still To Build (Phase 1)

- [ ] PDF estimate generation (WeasyPrint installed, not wired up)
- [ ] Drawing upload → email notification to detailing team (`DETAILING_TEAM_EMAIL` setting exists)
- [ ] Price book management UI (currently admin-only via Django admin)
- [ ] Member schedule display on job detail page
- [x] Cutlist Optimizer — integrated at `/cutlist/` with split-panel layout and DB persistence
