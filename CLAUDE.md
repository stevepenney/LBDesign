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
- **CSV bulk import** (`products/admin_import.py`, no new dependency — stdlib `csv`):
  - Products: an "Import CSV" button on `/admin/products/product/` (added via
    `templates/admin/products/product/change_list_object_tools.html`, the Django-6-native
    override point for the object-tools row — resolved automatically per app/model by
    `InclusionAdminNode`, no need to override the whole `change_list.html`). Upserts by exact
    `name` match; expected columns documented on the upload page itself
    (`templates/admin/products/product_import_csv.html`).
  - PriceBook pricing: a `pricing_csv` field (declared on `PriceBookAdminForm`, not a model
    field) sits right on the PriceBook add/change form — create a blank book and upload in one
    step, or re-upload later on an existing book's change form to refresh it. A re-upload is a
    **full replace**: any existing entry for a product not present in the new file is removed,
    not left stale — this was a deliberate choice (a periodic price update is "here's the
    complete new list," not a patch).

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
- `calculateOptimization(tabId)` — First Fit Decreasing algorithm, per (tab, group)
- `optimizeGroupBins(bins, stockLengths, kerfWidth)` — unified post-FFD consolidation pass, run
  independently per (tab, group). See "Consolidation algorithm" below.
- `advancedOptimizeAll(silent)` — orchestrates `optimizeGroupBins` per group across all tabs;
  `silent=true` suppresses toasts/saves when called from the wizard
- `runOptimisation()` — the guarded entry point: if any bin is `manualOverride`d, opens the
  guardrail modal instead of running immediately; otherwise calls `performOptimisation(false)`
- `performOptimisation(clearOverrides)` — the actual FFD → advanced-optimise → render → save
  flow (was previously inlined in `runOptimisation`)
- `runFFDRespectingLocks(tabId)` — wraps `calculateOptimization` to exclude locked bins' pieces
  from FFD input, then merges the locked bins back in unchanged
- `saveProject()` — POSTs full state to `/cutlist/<pk>/save/` (does not rename the cutlist)
- `restoreProject(data)` — restores from saved state (page load or JSON import)
- `resetFromStep(n)` — clears downstream DOM + locks steps when re-processing

`CutlistProject.name` is inline-editable in the page header (like `Job.label` on the estimate
page) via `cutlist:project_update_field` — POST `field=name&value=...`, blank falls back to
`'Untitled Cutlist'`. It is no longer auto-derived from a description field.

### Member ↔ Product mapping
A cutlist tab's `memberName` is freeform text (typed or CSV-imported) — historically with no
link to the `products.Product` catalog at all (only 9 of 26 real distinct member names in the
database exactly matched a `Product.name`; formatting varies even for the same product, e.g.
"LIB 240.88s" vs "LIB240.88s"). `cutlist.MemberProductMapping` (global, not per-project) now
remembers a confirmed raw-text → `Product` link, keyed on a whitespace/case-normalized form
(`normalizeMemberName()` in cutlist.js / `_normalize_member_name()` in cutlist/views.py — keep
these two in sync). `parseCSVIntoTabs` and every other tab-construction site set `tab.productId`
via `lookupMemberProductId(memberName)`; a Product dropdown in the Step 3 review UI
(`.member-product`, next to Member Size) lets the user set/change/clear it, firing
`saveMemberMapping()` immediately (`POST cutlist:member_mapping_save`) so the choice is
remembered for future imports — this is a fire-and-forget side-channel to the global table,
separate from `tab.productId` itself which follows the same lazy-save timing as every other tab
field (only persisted to `CutlistProject.state` on the normal save flow). Mapping is optional by
design — wholesale merchant customers use this tool directly and may not want to touch the
product catalog; an unmapped tab keeps today's generic `getDefaultStockLengths()` behaviour.
`openConvertModal()` prefers `tab.productId` over its old weak timber-type-substring guess when
pre-selecting a product.

### Default stock lengths (admin-editable)
`getDefaultStockLengths(memberName, productId)` (static/js/cutlist.js) resolves in three tiers,
each admin-editable in Django admin (Products section) — no hardcoded table anymore:
1. **`Product.stock_lengths`** — comma-separated mm list on the linked product, if `productId`
   resolves to one and it has a non-blank value. Precise per-size control (e.g. two different
   LVL13 sizes can have different stock lists), addressing that the old flat per-timber-type
   table couldn't.
2. **`TimberTypeDefaultStockLengths`** (new model, `products` app) — one row per `getTimberType()`
   category (LIB/LVL8/LVL11/LVL13/GL/OTHER), used when there's no product link or it has no
   stock lengths set. This is the fallback for the common case of an unmapped member (mapping is
   optional, see above).
3. A small hardcoded `FALLBACK_STOCK_LENGTHS` constant in cutlist.js — only reached if the DB
   tables are somehow empty (fresh install before migrations run); normal operation never hits it.

Both DB tables were seeded (migration `products/0010_seed_default_stock_lengths.py`) from what
`getDefaultStockLengths()` used to hardcode, as the admin-editable starting point. `project_edit`
passes `products` (now including each one's `stock_lengths`) and a new `timber_type_defaults`
dict to the template via the same `json_script` pattern as everything else on this page.
Selecting a product for a tab does **not** retroactively rewrite `tab.stockLengths` — defaults
only apply at tab-creation time, so a merchant's manual customisation is never silently clobbered
by later linking a product.

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

### Consolidation algorithm
`optimizeGroupBins()` (static/js/cutlist.js) replaced three separate, order-dependent
heuristics (a hardcoded pattern rule, a flawed "double the stock length" rule, and a
stale-index bug in a general search loop) that used to run in sequence in `consolidateBins`/
`advancedOptimizeTab`. It runs independently per `(tab, group)` — no shared cross-group queue —
alternating two passes to a fixed point:
1. **Subset search** — recombines small clusters of existing bins onto better stock (bounded
   combinatorial search, subset size capped when the candidate pool is large).
2. **Pool repack** — re-derives a fresh Best-Fit-Decreasing packing for the whole group from
   scratch when the subset search can't reach it in one step.

Scores every candidate by `(total_material, stick_count, distinct_stock_lengths_not_already_
used_elsewhere_in_the_group)`, lexicographic, strict-improvement only. Material is minimised
first as a hard constraint; stick count is the tie-break *before* distinct-length reuse, so
folding leftovers onto an already-used stock length only wins when it doesn't cost extra
sticks. Validated against every real `CutlistProject` in the database before being ported from
a Python prototype (a from-scratch rewrite would be substantial work to re-validate — port
logic changes into both, or re-run the full-database comparison, rather than patching JS alone).

### Stick locking (Step 4)
`bin.locked` is a general-purpose, user-toggleable flag — **not** tied to whether a stick has
ever been edited. Every stick shows a padlock toggle (`toggleBinLock`, 🔓/🔒) just above it,
always visible (subtle/greyscale when unlocked, amber/opaque when locked), so a team member can
pre-emptively lock a perfectly ordinary optimiser-produced stick just to protect it, not only
ones they've changed. Editing a stick — changing its stock length (`openStickEditor`/
`saveStickEdit`), or it becoming a drag source/target (`handleCutDragStart`/`handleStickDrop`/
`handleGhostDrop`) — still auto-locks it (same trigger as before), and any lock change
auto-saves immediately (unlike Feature 3's cut editor, which leaves saving to the user).
Unlocking is **just the flag** — it does not revert a stick's contents; those only change on an
actual re-optimise (deliberate: unlocking previews nothing, re-optimising is the only thing
that recomputes anything). `runOptimisation()` checks `hasLockedSticks()` first and, if any
exist, shows `lockGuardModal` offering "keep locked, re-optimise the rest" (locked bins are
excluded from `optimizeGroupBins` per group and their pieces excluded from FFD via
`runFFDRespectingLocks`) or "unlock all & re-optimise everything". Feature 3's cut editor
(`saveCutEdit`) gets a lighter version of the same guard: editing a raw cut invalidates the
whole tab's layout, so it just confirms before unlocking everything in that tab. A locked bin
also renders with an amber stick border (`.stick-diagram.stick-locked`) reinforcing the padlock
— styling lives in `cutlist.css`, must not touch `.cut-segment`/`.cut-segment-split`
`background` (reserved for the timber-type colours above). There's deliberately no separate
"this was manually edited" indicator distinct from the lock — locked/unlocked is the only state
that matters to this workflow.

Sticks are **not** re-sorted on every render — `displayResults` renders `tab.results.bins` in
whatever order they're already in; the (group, then size) sort happens once, in
`advancedOptimizeAll`, right when a full re-optimise finishes. This is deliberate: editing a
stick (drag/drop, stick-length edit, lock toggle) only mutates a bin in place, so it keeps its
position instead of jumping elsewhere in the row on every re-render.

A full-size, dashed **ghost stick** (`generateGhostStickHTML`) sits at the end of every group as
a permanent drop target — not a real bin, nothing is added to `tab.results.bins` until a cut is
actually dropped on it. `handleGhostDrop` then materialises a real stick at
`GHOST_STICK_LENGTH` (6000mm) and receives the cut in one motion (rejects and creates nothing if
the piece is longer than that). Shares its cut-move logic with `handleStickDrop` via
`moveCutIntoBin`.

`binIdCounter` (module-level, starts at 0 each page load) must be advanced past every bin id
already present in a restored project — `restoreProject` does this — otherwise a freshly
created bin (ghost-stick drop, or any future bin-creating action) can collide with an existing
saved bin's id from a prior session, since the counter has no other way to learn which ids are
already taken.

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
