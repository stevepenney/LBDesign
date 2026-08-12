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
| `core` | SystemSettings (singleton), RoofPitch (lookup), HelpTopic |
| `products` | Product, PriceBook, PriceBookEntry; `pricing.py` price resolver |
| `projects` | Project (org FK, status workflow, lb_job_number), ProjectDocument |
| `jobs` | Job (an estimate, belongs to a Project), Section, FloorRoofArea, AdditionalBeam; `calculations.py` engine |
| `cutlist` | Cutlist Optimizer — `CutlistProject` model (Project FK, state JSONField) + JS wizard |

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
- `SystemSettings` is a singleton; always use `SystemSettings.get()`, never `.objects.first()`.
- `Job.label` defaults to `'Untitled Estimate'` (mirrors `CutlistProject.name` defaulting to
  `'Untitled Cutlist'`) — new estimates are never blank-labelled. Inline-editable on `job_detail.html`.
- All "quick create" entry points (`projects:project_create`, `jobs:estimate_quick`/`job_create`,
  `cutlist:project_new_quick`/`project_new`) create records directly with `status=PRELIMINARY` and
  no blocking form — every field is inline-editable afterwards. The old `DRAFT` status +
  save/discard gate is legacy; don't reintroduce it for new creation flows.

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
- `RoofPitch` and `SystemSettings` are in the **Core** admin section.
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

A browser-based bin-packing tool for optimising timber cutting lists. Integrated Django app
with `CutlistProject` model (Project FK, `name` CharField default `'Untitled Cutlist'`, state
JSONField). Template at `templates/cutlist/project_edit.html`, JS at `static/js/cutlist.js`,
CSS at `static/css/cutlist.css`.

### Architecture
State lives in a single `project` JS object (jobDetails, tabs[], activeTabId, skippedData).
`jobDetails` only holds cutlist-specific settings (`preparedBy`, `kerfWidth`) — client/site/
reference info is NOT duplicated in JS state; it lives on the shared `projects.Project` record
and is shown in a "Project Details" card at the top of the page (same inline-edit pattern as
`jobs/job_detail.html`, posting to `projects:project_update_field`).
`wizard` object tracks `reachedStep`. DOM always rendered from state, never read back.
Key functions:
- `parseCSVIntoTabs(csvText)` — parses CSV, populates `project.tabs[]`, max 5 member types
- `calculateOptimization(tabId)` — First Fit Decreasing algorithm
- `advancedOptimizeAll(silent)` — post-process: offcut reuse + bin consolidation; `silent=true` suppresses toasts/saves when called from wizard
- `runOptimisation()` — async wizard action: validates → FFD → advanced → renders tabs → saves → advances to Step 4
- `saveProject()` — POSTs full state to `/cutlist/<pk>/save/` (does not rename the cutlist)
- `restoreProject(data)` — restores from saved state (page load or JSON import)
- `resetFromStep(n)` — clears downstream DOM + locks steps when re-processing

`CutlistProject.name` is inline-editable in the page header (like `Job.label` on the estimate
page) via `cutlist:project_update_field` — POST `field=name&value=...`, blank falls back to
`'Untitled Cutlist'`. It is no longer auto-derived from a description field.

### Wizard (5 steps — vertical accordion)
1. **Cutlist Settings** — `preparedBy`, `kerfWidth` only (project/client info lives in the
   Project Details card above the wizard, not in this step)
2. **Import Cuts** — textarea (also drop zone for CSV files)
3. **Review Cuts** — per-member collapsible panels (start collapsed); cuts grouped + collapsible by group within each panel
4. **Results** — member tabs with cutting diagrams; click cut segment to edit inline (Feature 3)
5. **Summary & Export** — stock order table; Save / Export JSON / Import JSON / Print

Navigation: free to jump to any previously reached step. Actions (Optimise, Next) reset downstream steps.

Print view (`cutlist:project_print`) sources client/site/reference/lb_ref from
`window.CUTLIST_PROJECT_INFO` (rendered server-side from `project.project.*`), not from
`jobDetails` — only `preparedBy`/`kerfWidth` still come from the saved state.

### CSS
`cutlist.css` uses `base.css` variables (no separate palette). Timber bin colours are
functional and must not change: LIB=yellow, LVL8=green, LVL11=cyan, LVL13=teal, GL=pink.

### Removed
- Lock sticks feature (was Feature 2) — removed; no longer relevant to workflow
- Split-panel layout — replaced by accordion wizard

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
- Call `SystemSettings.objects.first()` — use `SystemSettings.get()`.
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
