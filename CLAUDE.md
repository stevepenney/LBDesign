# LBDesign — Claude Code Guide

## Project

Lumberbank Midfloor & Rafter Estimation Tool. Django 6 / PostgreSQL multi-tenant web app
for merchant customers to generate wholesale timber framing estimates.

Virtual environment: `venv/` (Windows). Always use `venv/Scripts/python` not bare `python`.

Steve often already has a dev server running on port 8000 — check for that before starting a new
`runserver` process, and reuse it rather than spinning up a second instance. Only start one if
port 8000 isn't already bound.

---

## Commands

```bash
# Run dev server (skip if one's already running on :8000 — see above)
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
| `jobs` | Job (an estimate, belongs to a Project), Section ("Part" user-facing — Midfloor/Roof/Other/Cladding), FloorRoofArea, AdditionalBeam, CladdingArea, CladdingExtraItem, CladdingCutlistLine; `calculations.py` engine |
| `cutlist` | Cutlist Optimizer — `CutlistProject` model (Project FK, state JSONField) + JS wizard |

Templates live in `templates/` (project-level, not per-app).
Static files: `static/css/base.css`, `static/css/admin.css`, `static/js/base.js`,
`static/js/cutting_report.js` (shared report-rendering helpers — see "Cladding Estimator").

---

## Key Conventions

### Models
- `Section` is the user-facing term **"Part"** for what the code calls Section (DB table
  `jobs_section`) — never call it "sub-job" or "Section" in UI-facing text. A `Job` (estimate)
  is just a collection of Parts; `Section.SystemType` is `midfloor`/`roof`/`other`/`cladding`,
  all peers — a job can freely mix framing and cladding Parts, and hold more than one cladding
  Part (e.g. two product options as separate Parts). See "Cladding Estimator" below for how
  cladding folds into this rather than being a separate structure.
- `FloorRoofArea.joist_spacing` stores **mm as PositiveIntegerField** (e.g. 400, 450, 600).
  `spacing_m` property divides by 1000.
- `RoofPitch.pitch_degrees` stores degrees. `pitch_factor` is a computed property:
  `1 / cos(radians(pitch_degrees))`. Do not add a stored pitch_factor field.
- `FloorRoofArea.roof_pitch` is **per-area, not per-part** — a roof `Section` (e.g.
  "Unit 1 Roof") can span multiple pitches (main roof vs porch, hips, etc.) because each
  area picks its own pitch, same as each area already picks its own `joist_spacing`. Only
  meaningful when the parent `Section.is_roof`; harmless-but-unused if set on a midfloor/other
  area. `_calc_subjob` in `jobs/calculations.py` computes `pitch_factor` per area, guarded by
  `sub_job.is_roof`.
- `PriceBook.is_default` — only one default allowed; `save()` enforces it.
- `Product.unit_of_measure` (`lm`/`each`) only affects pricing on `AdditionalBeam` and
  `CladdingExtraItem` (via `jobs/calculations.py`'s `_priced_quantity()`) — every other
  calculation site derives its lineal metres from an area or a real cut length, with no
  independent piece count to price "each" against, so a product marked `each` there is simply
  priced as if it were `lm` (not a bug — those sites were never designed to support "each").
- `SystemSettings` is a singleton; always use `SystemSettings.get()`, never `.objects.first()`.
- `Job.label` defaults to `'Untitled Estimate'` (mirrors `CutlistProject.name` defaulting to
  `'Untitled Cutlist'`) — new estimates are never blank-labelled. Inline-editable on `job_detail.html`.
- `wastage_pct`/`hardware_allowance_pct` resolve **three-tier**: `Section`'s own override →
  `Job`'s override (the default new Parts start from) → `SystemSettings` global default. See
  `jobs/calculations.py::_effective_pct()`. `estimate_uncertainty_pct` and freight stay
  Job-level only — genuinely whole-estimate concepts, not per-Part.
- All "quick create" entry points (`projects:project_create`, `jobs:estimate_quick`/`job_create`,
  `cutlist:project_new_quick`/`project_new`) create records directly with `status=PRELIMINARY` and
  no blocking form — every field is inline-editable afterwards. The old `DRAFT` status +
  save/discard gate is legacy; don't reintroduce it for new creation flows.

### Pricing
- Price lookup: `products/pricing.py → get_product_price(product, organisation)`
- Resolution order: org's price book → default price book → None
- Org with `price_book = null` uses the default book for all products.

### Calculations
- Always call `run_section_calculation(section)` after saving any Part (framing or cladding) and
  its formsets — dispatches internally on `section.is_cladding` to `_calc_subjob`/`_calc_cladding`,
  then stores that Part's own `hardware_allowance_amount` and refreshes job freight.
- `run_job_estimate(job)` recalculates every Part in the job, then freight, once. No more
  `is_cladding` branch at the Job level — a cladding Part is just another Part in the loop.
- `member_schedule` JSON shape: `{'items': [...], 'has_unpriced': bool}` — lives on `Section`
  for every Part type (same for `calculated_subtotal`/`hardware_allowance_amount`). `Job` has no
  schedule/subtotal fields of its own any more — `Job.subtotal`/`Job.hardware_allowance_amount`
  are properties summing across `job.sections.all()`.

### Forms & Formsets
- `SectionForm`, `FloorRoofAreaFormSet`, `AdditionalBeamFormSet`, `CladdingAreaFormSet`,
  `CladdingExtraItemFormSet` are all in `jobs/forms.py` — the cladding formsets are now
  `inlineformset_factory(Section, ...)`, not `Job`.
- Formset prefixes: `areas`/`beams` (framing), `areas`/`extras` (cladding).
- `SectionForm.clean()` refuses changing `system_type` into/out of `CLADDING` once the Part
  already has areas — `CladdingArea`'s shape has nothing in common with `FloorRoofArea`'s, unlike
  switching among Midfloor/Roof/Other which already works today since they share `FloorRoofArea`.
- Empty form cloning for JS uses `{{ formset.empty_form }}` with `__prefix__` replacement.

### Views
- Tenancy helpers: `_get_jobs_for_user(user)` and `_assert_job_access(user, job)`.
- Always `prefetch_related('sections')` when listing jobs to avoid N+1 queries.
- `jobs:section_create`/`section_edit` dispatch on `system_type` to pick framing
  (`subjob_form.html` + `FloorRoofAreaFormSet`/`AdditionalBeamFormSet`) or cladding
  (`cladding_areas_form.html` + `CladdingAreaFormSet`/`CladdingExtraItemFormSet`) shapes — picking
  "Cladding" in the create form's type dropdown reloads via `?system_type=cladding` (a real page
  load, not client-side show/hide, since the formsets themselves differ).

### URLs (app_name = 'jobs')
- `jobs:section_create`, `jobs:section_edit`, `jobs:section_delete`, `jobs:section_update_field`
- `jobs:job_recalculate`
- `jobs:estimate_report` — `<job_pk>/report/`, Job-level (see "Cladding Estimator" below); not
  scoped to a Part.
- `jobs:cladding_generate_cutlist`, `jobs:cladding_import_cutlist` — nested
  `<job_pk>/sections/<pk>/cladding/...`, scoped to one cladding Part (a job can have more than
  one).

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

### Usage tracking
- `core.UsageEvent` (`user`, `organisation`, `event_type`, `created_at`) — deliberately lightweight:
  one row per meaningful action, not a full audit log of every click/save. Answers "who's using
  the system and how often" (and who isn't) for follow-up/promotion, without a massive table.
- Three event types: `login` (via a `user_logged_in` signal receiver in `core/signals.py`,
  wired up in `core/apps.py`'s `ready()`), `estimate_calculated`, `cutlist_saved`.
- `core.usage.log_usage_event(user, event_type)` is the only way rows get written — it no-ops
  silently if `user` is `None`/unauthenticated, so it's safe to call from anywhere.
- `run_section_calculation`/`run_job_estimate` (`jobs/calculations.py`) both take an optional
  `user=None` kwarg that logs `estimate_calculated` when provided. Real views pass
  `user=request.user`; `load_dummy_data` deliberately doesn't pass one, so seed data never
  pollutes real usage stats. `run_job_estimate` logs at most once per call even though it
  recalculates every Part underneath via the internal `_calc_and_store_section()` helper (not
  `run_section_calculation`, which would log/refresh freight once per Part — no double-counting).
- `cutlist:project_save` (`cutlist/views.py`) logs `cutlist_saved` directly — named for what's
  actually observable server-side (a state save), not `cutlist_optimised`, since optimisation
  itself runs client-side in JS and only reaches the server as a save.
- Admin-only for now (`core.UsageEventAdmin`, list/filter/search, read-only) — no reporting
  dashboard yet; add one if/when a concrete question needs it.

---

## CSS / Frontend

- CSS variables defined in `static/css/base.css` under `:root {}` — use these everywhere.
- Admin styles in `static/css/admin.css` — loads `base.css` variables via the admin
  `extrastyle` block in `templates/admin/base_site.html`.
- Toast messages: fixed bottom-left, handled entirely in `static/js/base.js`.
  Class structure: `<li class="toast success|error|warning|info">`.
- Hard-refresh (Ctrl+Shift+R) after CSS changes to bust browser cache.

---

## Cladding Estimator

A second estimation module alongside framing (midfloor/roof), sharing the `jobs` app rather
than a new one. Converts m² to lineal metres by dividing by a product's fixed **cover** width,
instead of a user-chosen joist/rafter **spacing** — mathematically the same division
(`jobs/calculations.py`'s `_area_lm()` helper is shared by both), but cover is a fixed property
of the product (`Product.cover_mm`, `Product.use_as_cladding`) rather than a per-area design
choice, so it can't reuse `FloorRoofArea.joist_spacing`.

**Cladding is a `Section` type, not a separate structure.** It was originally built attached
directly to `Job` (no `Section` layer, reasoning: cladding has no boundary-joist/stair-void-style
per-instance settings for a `Section` to hold). That turned out to be the wrong call: it meant
`wastage_pct`/`hardware_allowance_pct` living on `Job` couldn't vary between a framing part and a
cladding part, which was the actual reason a job got locked to one category or the other. Once
those factors moved to `Section` (see "Models" above), cladding became just a fourth
`Section.SystemType` — `CLADDING`, alongside `MIDFLOOR`/`ROOF`/`OTHER` — with no boundary-joist/
stair-void fields used (simply left at their defaults), same as those fields are already
meaningless-but-harmless on an `OTHER` section. This also means a job can now hold **more than
one** cladding Part (e.g. "Oak Option"/"Kwila Option" as two Parts in the same estimate, instead
of needing two separate `Job`s via Duplicate).
- `jobs.CladdingArea` FKs to `Section` (`related_name='cladding_areas'`), same as
  `FloorRoofArea` does. `orientation` (`vertical`/`horizontal`) matters beyond display: a
  vertical board can't have joins, so `CladdingArea.cut_piece()` can derive discrete cut pieces
  from it for the cutlist optimizer (see below); horizontal tolerates joins, so it has no single
  fixed piece length and never produces discrete pieces — it always stays on the area-based lm
  estimate. `area_m2` is a computed property (`width_m * height_m`), not stored.
- `jobs.CladdingExtraItem` FKs to `Section` too — mirrors `AdditionalBeam`'s shape (product +
  length + quantity) for flat, freely-added lines that aren't derived from an area (scribers,
  corner mouldings, flashings).
- `jobs.CladdingCutlistLine` FKs to `Section` — mirrors `CutlistImportLine`'s shape. Written by
  `jobs:cladding_import_cutlist` (see below) with the real optimized gross stock length once a
  generated cutlist has been optimized, contingency % already applied.
- `jobs/views.py::section_create`/`section_edit` dispatch on `system_type` to render either the
  framing formsets/template or `CladdingAreaFormSet`/`CladdingExtraItemFormSet` +
  `cladding_areas_form.html` — one Part-creation flow, type chosen inside the form (see "Views"
  above). A fresh cladding Part seeds its own `hardware_allowance_pct` to `0` at creation
  (defaults to no hardware allowance rather than inheriting the framing-oriented job/global
  default) — inline-editable per-Part afterwards on `job_detail.html`, same `est-row` pattern
  Job's own Advanced Settings panel already used, just pointed at `jobs:section_update_field`.
- Calculation: `_calc_cladding(section)` (`jobs/calculations.py`) loops `section.cladding_areas`,
  `section.cladding_cutlist_lines`, and `section.cladding_extra_items`, merging **per product**:
  a vertical area whose product already has an imported `CladdingCutlistLine` is priced from
  that real stock quantity instead of its rough area estimate; every other area (horizontal, or
  vertical but not yet imported) keeps the area-based estimate. This is what lets a job mix
  orientations without double-counting.
- `job_detail.html` renders every Part — framing or cladding — through the same
  `{% for sj in sections %}` loop, branching the card body on `sj.is_cladding`. One "+ Add Part"
  toolbar action; type is chosen inside the form.
- **Cutlist hand-off** (`jobs:cladding_generate_cutlist`/`cladding_import_cutlist`, both scoped
  to one `Section`): builds a `CutlistProject` from a cladding Part's vertical elevations
  (`CladdingArea.cut_piece()` per area; elevation labels go on each cut's `mark`, not `group` —
  `group` is a hard packing partition in the optimizer, and pieces from different elevations
  should be free to share a stick), then later pulls the optimized `totalStockUsed` back as
  `CladdingCutlistLine`s (contingency % applied — `Section.stock_contingency_pct`, three-tier
  same as wastage/hardware). A "Return to Estimate" button in the cutlist editor
  (`templates/cutlist/project_edit.html`, shown when `cutlist.cladding_source_sections.exists()`)
  does the import and navigates back in one click.
- **The report is a `jobs` page, not a `cutlist` one, and lives at the estimate level, not the
  Part level** (`jobs:estimate_report`, `templates/jobs/estimate_report.html` — one "Report"
  button in `job_detail.html`'s top toolbar, not a per-Part icon). It was originally a per-Part
  report (`jobs:cladding_report`, one per cladding Part) but freight, hardware allowance, and
  Estimate Uncertainty % are Job-level concepts (see "Models" above) — a report that applies them
  has to be Job-level too. `estimate_report` loops every Part in the job (framing and cladding
  alike), rendering each one's elevations (cladding only) and priced order sheet exactly as the
  old per-Part report did, ahead of a whole-estimate summary card (materials/hardware/freight
  totals + the indicative price range, using the same `_estimate_price_range()` helper
  `job_detail`'s own summary card uses — kept in one place, in `jobs/views.py`, so the two never
  disagree) and then, for every cladding Part with a generated cutlist, that Part's cutting
  diagram pages. `cutlist` stays a pure, estimate-agnostic bin-packing tool — its own print view
  (`cutlist:project_print`) never shows pricing or elevations, just cutting diagrams/pattern
  summary/unpriced stock quantities, for any cutlist. The report reads each Part's already-priced
  `member_schedule` for every dollar figure (same data `job_breakdown.html` shows — nothing
  recalculated on the report page) and its `CladdingArea`s for the elevations table; it only
  reads each linked `CutlistProject.state` for raw cutting geometry (bins/cuts), via the shared
  `static/js/cutting_report.js` module (repetition-grouped horizontal stick diagrams + a
  per-pattern summary table — see "Consolidation algorithm" for why physical sticks collapse into
  patterns). That module is deliberately standalone (plain `(bins, kerfWidth)` functions, no
  dependency on `cutlist.js`'s globals) so both `cutlist:project_print` and `jobs:estimate_report`
  can use it without either pulling in the whole interactive editor.
- Products: a `Cladding` `ProductType` (seeded via `products/migrations/0012_seed_
  cladding_producttype.py`, same `get_or_create` pattern as the original product-type seed).
  CSV bulk import (`products/admin_import.py`) supports `use_as_cladding`, `cover_mm`, and
  `unit_of_measure` columns.

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
1. **Cutlist Settings** — `systemType` (Framing / Cladding), `preparedBy`, `kerfWidth`
   (project/client info lives in the Project Details card above the wizard, not in this step)
2. **Import Cuts** — textarea (also drop zone for CSV files)
3. **Review Cuts** — per-member collapsible panels (start collapsed); cuts grouped + collapsible by group within each panel
4. **Results** — member tabs with cutting diagrams; click cut segment to edit inline (Feature 3)
5. **Summary & Export** — stock order table; Save / Export JSON / Import JSON / Print

Navigation: free to jump to any previously reached step. Actions (Optimise, Next) reset downstream steps.

Print view (`cutlist:project_print`) sources client/site/reference/lb_ref from
`window.CUTLIST_PROJECT_INFO` (rendered server-side from `project.project.*`), not from
`jobDetails` — only `systemType`/`preparedBy`/`kerfWidth` still come from the saved state.

### Framing vs Cladding (`project.jobDetails.systemType`)
A cutlist project is one or the other, chosen via a Step 1 dropdown (`'framing'` default —
old saved cutlists with no `systemType` key keep behaving as framing via `Object.assign`'s
merge-over-defaults in `restoreProject`, no migration needed since it lives in `state`).
Deliberately freely switchable, unlike the estimator's per-`Job` framing/cladding lock — it's
just a presentation flag (bin colour + stock-length defaults), so nothing breaks by flipping
it; it only takes effect on the next Optimise for tabs already computed.
- `calculateOptimization()` and `getDefaultStockLengths()` both use
  `project.jobDetails.systemType === 'cladding' ? 'CLADDING' : getTimberType(tab.memberName)`
  instead of always guessing from the member name. This is deliberately **not** a
  `getTimberType(memberName, productId)` signature change consulting `Product.use_as_cladding`
  — cladding profile names (e.g. "Weatherboard 180", "Rusticator") have no shared substring to
  guess from the way LIB/LVL8/LVL11/LVL13/GL do, so per-tab guessing would be unreliable;
  the project-level toggle sidesteps guessing entirely. `openConvertModal()`'s weak
  timber-type-substring product guess is unchanged — it only ever runs when a tab has no
  confirmed `productId` yet, so there's nothing for it to check either way.
- `TimberTypeDefaultStockLengths.TimberType.CLADDING` (`products` app) seeded with the same
  generic default as LVL11/LVL13/GL/OTHER (`products/migrations/0014_seed_cladding_stock_
  lengths.py`) — real cladding products should set their own `Product.stock_lengths`, which
  takes precedence anyway (same tiering as every other timber type).
- **Do not confuse this with `products.ProductType`** (the real catalog category —
  I-Joist/LVL/Glulam/Cladding, admin-managed). The two "type" concepts are unrelated: cutlist.js
  only ever reads `product_type__name` as display text next to a product name in a dropdown —
  it has no effect on classification, bin colour, or stock-length resolution.
- `cutlist_convert_to_estimate` (`jobs/views.py`) is unrelated to cladding — it's the generic
  "convert any cutlist into a brand-new framing `Section` (`OTHER` type) +
  `CutlistImportLine`s" path, still framing-only by design. Cladding has its own dedicated,
  tighter hand-off instead (`jobs:cladding_generate_cutlist`/`cladding_import_cutlist` — see
  "Cladding Estimator") that feeds back into the *same* Part rather than creating a new Job.

### CSS
`cutlist.css` uses `base.css` variables (no separate palette). Timber bin colours are
functional and must not change: LIB=yellow, LVL8=green, LVL11=cyan, LVL13=teal, GL=pink,
CLADDING=orange (added alongside them, free to restyle).

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

The stick-length editor (`openStickEditor`) isn't limited to the tab's configured
`stockLengths` — its dropdown always has a "Custom length…" option that reveals a plain number
input (`onStickEditorLengthChange`), for the occasional one-off stock length a merchant would
normally avoid (e.g. extra freight cost) but is willing to use for a specific stick.

**Overlength split → single custom stick**: the "Overlength Cuts Split" summary panel
(`displayResults`) lets the user route one specific split occurrence onto a single whole custom
stick instead of the standard split, via `unsplitOverlengthCut`. Matching is by `splitGroupId`
— a `` `${cutIndex}-${i}` `` id stamped on both the `overlengthSplits` entry and its resulting
piece(s) at FFD time (`calculateOptimization`), unique per **physical instance** rather than
per raw cut row, since a `quantity > 1` row produces several otherwise-indistinguishable
splits. `unsplitOverlengthCut` refuses to act if `splitGroupId` is missing (results saved
before this field existed, e.g. from a JSON import/export predating it) rather than risk
matching on `undefined` and sweeping up pieces from unrelated splits — confirmed by hand this
is a real failure mode, not theoretical: it deleted 65 of 66 bins in one tab during testing
before the guard was added. The resulting single-stick bin is `locked` like any other manual
construct.

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
- Use "sub-job" or "Section" anywhere in user-facing text or UI labels — it's "Part".
- Add a stored `pitch_factor` field to RoofPitch — it's always computed.
- Call `SystemSettings.objects.first()` — use `SystemSettings.get()`.
- Create new template files when editing an existing one works.
- Add comments that describe *what* the code does — only add them when the *why* is non-obvious.
- Over-engineer: no extra abstractions, fallbacks, or validation beyond what the task requires.
- Let `cutlist` app code import/reach into `jobs`/`products` pricing concerns — it stays a pure,
  estimate-agnostic bin-packing tool (see "The report is a `jobs` page, not a `cutlist` one").

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
- [x] Member schedule display on job detail page (`job_breakdown.html`, LB-staff only)
- [x] Cladding folded into `Section` as a Part type; per-Part wastage/hardware; cladding
      cutlist hand-off feeds back into the same Part; cladding report moved to `jobs`
- [x] Cutlist Optimizer — integrated at `/cutlist/` with split-panel layout and DB persistence
