import json
import math
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.models import Organisation
from core.models import SystemSettings
from cutlist.models import CutlistProject
from products.models import Product
from products.pricing import get_product_price
from projects.models import Project
from projects.views import _assert_project_access
from .calculations import run_job_estimate, run_section_calculation
from .forms import (
    SectionForm, FloorRoofAreaFormSet, FloorRoofAreaOptionalFormSet, AdditionalBeamFormSet,
    CladdingAreaFormSet, CladdingExtraItemFormSet,
)
from .models import (
    Job, Section, FloorRoofArea, CladdingArea, CladdingExtraItem, AdditionalBeam,
    CutlistImportLine, CladdingCutlistLine,
)


def _priced_cutlist_lines(section):
    """
    Per-stick pricing breakdown for a cutlist-derived section: one row per
    actual stock line (zone, product, length, qty, cost), priced via the same
    get_product_price resolver the calculation engine uses. This is purely a
    display breakdown of the section's existing calculated_subtotal — it
    doesn't feed back into pricing.
    """
    cutlist = section.job.source_cutlist
    if not cutlist:
        return []
    product_by_tab = {
        line.tab_index: line.product
        for line in section.cutlist_import_lines.select_related('product').all()
        if line.tab_index is not None
    }
    organisation = section.job.project.organisation
    rows = []
    for row in cutlist.stock_order():
        product = product_by_tab.get(row['tab_index'])
        length_m = Decimal(str(row['length_m']))
        if product:
            price = get_product_price(product, organisation)
            line_total = (length_m * row['qty'] * price).quantize(Decimal('0.01')) if price else None
        else:
            # No product was matched during conversion — zero-cost placeholder, flagged elsewhere via has_unpriced.
            line_total = Decimal('0.00')
        rows.append({
            'group': row['group'] or '—',
            'product': product or row['product'],
            'length_m': length_m,
            'qty': row['qty'],
            'line_total': line_total,
        })
    return rows


def _area_formset_cls(system_type):
    """Return the right area formset class for a framing part — Other parts have optional areas."""
    if system_type == Section.SystemType.OTHER:
        return FloorRoofAreaOptionalFormSet
    return FloorRoofAreaFormSet


@login_required
def estimate_quick(request):
    """Create a project + blank estimate in one step and go straight to it."""
    is_lb_staff = request.user.is_lb_admin or request.user.is_lb_detailing

    if is_lb_staff:
        org_pk = request.GET.get('org')
        if not org_pk:
            return redirect(f"{reverse('projects:select_merchant')}?next=estimate")
        org = get_object_or_404(Organisation, pk=org_pk)
    else:
        if not request.user.organisation:
            messages.error(request, 'Your account is not linked to an organisation. Contact LumberBank.')
            return redirect('projects:project_list')
        org = request.user.organisation

    project = Project.objects.create(
        organisation = org,
        created_by   = request.user,
        status       = Project.Status.PRELIMINARY,
    )
    job = Job.objects.create(project=project, created_by=request.user)
    return redirect('jobs:job_detail', pk=job.pk)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_jobs_for_user(user):
    if user.is_lb_admin or user.is_lb_detailing:
        return Job.objects.select_related('project__organisation').all()
    if user.organisation:
        return Job.objects.filter(project__organisation=user.organisation)
    return Job.objects.none()


def _assert_job_access(user, job):
    return _assert_project_access(user, job.project)


@login_required
@require_POST
def job_update_field(request, pk):
    job = get_object_or_404(Job, pk=pk)
    if not _assert_job_access(request.user, job):
        return JsonResponse({'ok': False}, status=403)
    field = request.POST.get('field', '')
    value = request.POST.get('value', '').strip()

    # hardware_allowance_pct/wastage_pct are now just the default new Parts start from —
    # changing them here still recalculates the whole job, since any Part without its own
    # override picks up the new default automatically.
    PCT_FIELDS = {'hardware_allowance_pct', 'wastage_pct', 'estimate_uncertainty_pct'}
    if field not in {'label'} | PCT_FIELDS:
        return JsonResponse({'ok': False, 'error': 'Invalid field'}, status=400)

    if field in PCT_FIELDS:
        if value == '':
            setattr(job, field, None)
        else:
            try:
                pct = Decimal(value)
                if not (Decimal('0') <= pct <= Decimal('200')):
                    return JsonResponse({'ok': False, 'error': 'Enter a value between 0 and 200'}, status=400)
                setattr(job, field, pct)
            except InvalidOperation:
                return JsonResponse({'ok': False, 'error': 'Invalid percentage'}, status=400)
        job.save(update_fields=[field, 'updated_at'])
        if field in {'hardware_allowance_pct', 'wastage_pct'}:
            run_job_estimate(job, user=request.user)
        return JsonResponse({'ok': True, 'reload': True})

    setattr(job, field, value)
    job.save(update_fields=[field, 'updated_at'])
    return JsonResponse({'ok': True, 'value': value})


@login_required
@require_POST
def section_update_field(request, job_pk, pk):
    """Mirrors job_update_field, for a Part's own wastage_pct/hardware_allowance_pct override."""
    job = get_object_or_404(Job, pk=job_pk)
    section = get_object_or_404(Section, pk=pk, job=job)
    if not _assert_job_access(request.user, job):
        return JsonResponse({'ok': False}, status=403)
    field = request.POST.get('field', '')
    value = request.POST.get('value', '').strip()

    PCT_FIELDS = {'wastage_pct', 'hardware_allowance_pct'}
    if field not in PCT_FIELDS:
        return JsonResponse({'ok': False, 'error': 'Invalid field'}, status=400)

    if value == '':
        setattr(section, field, None)
    else:
        try:
            pct = Decimal(value)
            if not (Decimal('0') <= pct <= Decimal('200')):
                return JsonResponse({'ok': False, 'error': 'Enter a value between 0 and 200'}, status=400)
            setattr(section, field, pct)
        except InvalidOperation:
            return JsonResponse({'ok': False, 'error': 'Invalid percentage'}, status=400)
    section.save(update_fields=[field, 'updated_at'])
    run_section_calculation(section, user=request.user)
    return JsonResponse({'ok': True, 'reload': True})


# ── Job views ─────────────────────────────────────────────────────────────────


@login_required
def job_create(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)
    if not _assert_project_access(request.user, project):
        messages.error(request, 'You do not have access to that project.')
        return redirect('projects:project_list')

    job = Job.objects.create(project=project, created_by=request.user)
    messages.success(request, 'Estimate created.')
    return redirect('jobs:job_detail', pk=job.pk)


@login_required
@require_POST
def cutlist_convert_to_estimate(request, cutlist_pk):
    """
    Convert a completed cutlist stock order into a priced estimate.

    Members are mapped to real products client-side; the net lineal metres
    and blended real wastage % come from the cutlist's own optimizer results
    (totalCutLength / totalStockUsed), not recalculated here.
    """
    cutlist = get_object_or_404(CutlistProject, pk=cutlist_pk)
    if not _assert_project_access(request.user, cutlist.project):
        return JsonResponse({'ok': False, 'error': 'No access'}, status=403)

    try:
        mapping = json.loads(request.body).get('mapping', {})
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)

    tabs = (cutlist.state or {}).get('tabs', [])
    product_ids = [v for v in mapping.values() if v]
    products = Product.objects.filter(pk__in=product_ids, is_active=True).in_bulk()

    lines = []  # (product, net_length_m, tab_index, member_name)
    net_total = Decimal('0')
    gross_total = Decimal('0')
    for idx, tab in enumerate(tabs):
        results = tab.get('results')
        if not results:
            continue
        net_mm = Decimal(str(results.get('totalCutLength', 0)))
        gross_mm = Decimal(str(results.get('totalStockUsed', 0)))
        if net_mm <= 0:
            continue
        net_total += net_mm
        gross_total += gross_mm
        product = products.get(mapping.get(str(idx)))
        lines.append((
            product,
            (net_mm / Decimal('1000')).quantize(Decimal('0.01')),
            idx,
            tab.get('memberName', ''),
        ))

    if not lines or net_total == 0:
        return JsonResponse(
            {'ok': False, 'error': 'Optimise at least one member before converting.'}, status=400
        )

    wastage_pct = ((gross_total - net_total) / net_total * 100).quantize(Decimal('0.01'))

    job = Job.objects.create(
        project=cutlist.project,
        created_by=request.user,
        label=cutlist.name,
        estimate_uncertainty_pct=Decimal('0'),
        source_cutlist=cutlist,
    )
    section = Section.objects.create(
        job=job,
        label=cutlist.name,
        system_type=Section.SystemType.OTHER,
        wastage_pct=wastage_pct,
    )
    CutlistImportLine.objects.bulk_create([
        CutlistImportLine(
            section=section, product=product, length_m=length_m,
            tab_index=tab_index, product_description=member_name,
        )
        for product, length_m, tab_index, member_name in lines
    ])
    run_job_estimate(job, user=request.user)

    return JsonResponse({'ok': True, 'redirect': reverse('jobs:job_detail', args=[job.pk])})


def _estimate_price_range(job, system_settings):
    """
    Indicative low/high range around job.total, driven by Estimate Uncertainty %
    (job override, else global default). Shared by job_detail's summary card and
    estimate_report so the two never drift apart. Returns
    (effective_uncertainty_pct, low_str, high_str), the low/high already
    comma-formatted for display.
    """
    effective_uncertainty_pct = (
        job.estimate_uncertainty_pct
        if job.estimate_uncertainty_pct is not None
        else system_settings.estimate_uncertainty_pct
    )
    total = float(job.total)
    band  = float(effective_uncertainty_pct) / 100
    low   = int(total * (1 - band * 0.30) // 50) * 50
    high  = math.ceil(total * (1 + band * 0.70) / 50) * 50
    return effective_uncertainty_pct, f'{low:,}', f'{high:,}'


@login_required
def job_detail(request, pk):
    job = get_object_or_404(Job, pk=pk)
    if not _assert_job_access(request.user, job):
        messages.error(request, 'You do not have access to that estimate.')
        return redirect('projects:project_list')
    sections = list(job.sections.prefetch_related(
        Prefetch('areas', queryset=FloorRoofArea.objects.select_related('joist_product', 'roof_pitch')),
        'additional_beams', 'cutlist_import_lines',
        Prefetch('cladding_areas', queryset=CladdingArea.objects.select_related('cladding_product')),
        Prefetch('cladding_extra_items', queryset=CladdingExtraItem.objects.select_related('product')),
    ).all())
    if job.source_cutlist_id:
        for sj in sections:
            if sj.cutlist_import_lines.all():
                sj.priced_cutlist_lines = _priced_cutlist_lines(sj)
    for sj in sections:
        if sj.is_cladding:
            sj.has_vertical_cladding_areas = any(
                a.orientation == CladdingArea.Orientation.VERTICAL for a in sj.cladding_areas.all()
            )
            sj.cladding_cutlist_has_results = bool(
                sj.cladding_cutlist_id
                and any(t.get('results') for t in (sj.cladding_cutlist.state or {}).get('tabs', []))
            )
    system_settings = SystemSettings.get()
    effective_hardware_pct = (
        job.hardware_allowance_pct
        if job.hardware_allowance_pct is not None
        else system_settings.hardware_allowance_pct
    )
    effective_wastage_pct = (
        job.wastage_pct
        if job.wastage_pct is not None
        else system_settings.wastage_pct
    )
    for sj in sections:
        sj.effective_wastage_pct = (
            sj.wastage_pct if sj.wastage_pct is not None else effective_wastage_pct
        )
        sj.effective_hardware_pct = (
            sj.hardware_allowance_pct if sj.hardware_allowance_pct is not None else effective_hardware_pct
        )
    effective_uncertainty_pct, estimate_low, estimate_high = _estimate_price_range(job, system_settings)
    return render(request, 'jobs/job_detail.html', {
        'job': job,
        'sections': sections,
        'system_settings': system_settings,
        'effective_hardware_pct':     effective_hardware_pct,
        'effective_wastage_pct':      effective_wastage_pct,
        'effective_uncertainty_pct':  effective_uncertainty_pct,
        'estimate_low':  estimate_low,
        'estimate_high': estimate_high,
    })


# ── Section (Part) views ──────────────────────────────────────────────────────

@login_required
def job_recalculate(request, pk):
    job = get_object_or_404(Job, pk=pk)
    if not _assert_job_access(request.user, job):
        messages.error(request, 'You do not have access to that estimate.')
        return redirect('projects:project_list')
    if request.method == 'POST':
        run_job_estimate(job, user=request.user)
        messages.success(request, 'Estimate recalculated.')
    return redirect('jobs:job_detail', pk=job.pk)


@login_required
def section_create(request, job_pk):
    """
    Add a new Part to an estimate. The type is the first thing chosen — for a
    Cladding part this renders a differently-shaped form (elevations + extra
    items, no boundary-joist/stair-void/beam fields) since CladdingArea's shape
    has nothing in common with FloorRoofArea's. Picking Cladding in the type
    dropdown reloads this same view with ?system_type=cladding (a real page
    load, not a client-side show/hide, because the formsets themselves differ).
    """
    job = get_object_or_404(Job, pk=job_pk)
    if not _assert_job_access(request.user, job):
        messages.error(request, 'You do not have access to that estimate.')
        return redirect('projects:project_list')

    if request.method == 'POST':
        posted_type = request.POST.get('system_type')
        if posted_type == Section.SystemType.CLADDING:
            form = SectionForm(request.POST)
            area_fs = CladdingAreaFormSet(request.POST, prefix='areas')
            extra_fs = CladdingExtraItemFormSet(request.POST, prefix='extras')
            if form.is_valid() and area_fs.is_valid() and extra_fs.is_valid():
                section = form.save(commit=False)
                section.job = job
                # A fresh cladding part defaults to no hardware allowance rather than
                # inheriting the framing-oriented job/global default.
                section.hardware_allowance_pct = Decimal('0')
                section.save()
                area_fs.instance = section
                area_fs.save()
                extra_fs.instance = section
                extra_fs.save()
                run_section_calculation(section, user=request.user)
                messages.success(request, f'"{section.label}" added.')
                return redirect('jobs:job_detail', pk=job.pk)
            return render(request, 'jobs/cladding_areas_form.html', {
                'job': job, 'form': form, 'area_formset': area_fs, 'extra_formset': extra_fs,
                'action': 'Add Part',
            })

        form    = SectionForm(request.POST)
        AreaFS  = _area_formset_cls(posted_type)
        area_fs = AreaFS(request.POST, prefix='areas')
        beam_fs = AdditionalBeamFormSet(request.POST, prefix='beams')

        if form.is_valid() and area_fs.is_valid() and beam_fs.is_valid():
            section = form.save(commit=False)
            section.job = job
            section.save()
            area_fs.instance = section
            area_fs.save()
            beam_fs.instance = section
            beam_fs.save()
            run_section_calculation(section, user=request.user)
            messages.success(request, f'"{section.label}" added.')
            return redirect('jobs:job_detail', pk=job.pk)
        return render(request, 'jobs/subjob_form.html', {
            'job': job, 'form': form, 'area_formset': area_fs, 'beam_formset': beam_fs,
            'action': 'Add Part',
        })

    requested_type = request.GET.get('system_type', Section.SystemType.MIDFLOOR)
    if requested_type == Section.SystemType.CLADDING:
        form = SectionForm(initial={'system_type': Section.SystemType.CLADDING})
        area_fs = CladdingAreaFormSet(prefix='areas')
        extra_fs = CladdingExtraItemFormSet(prefix='extras')
        return render(request, 'jobs/cladding_areas_form.html', {
            'job': job, 'form': form, 'area_formset': area_fs, 'extra_formset': extra_fs,
            'action': 'Add Part',
        })

    form    = SectionForm(initial={'system_type': requested_type})
    area_fs = FloorRoofAreaFormSet(prefix='areas')
    beam_fs = AdditionalBeamFormSet(prefix='beams')
    return render(request, 'jobs/subjob_form.html', {
        'job': job, 'form': form, 'area_formset': area_fs, 'beam_formset': beam_fs,
        'action': 'Add Part',
    })


@login_required
def section_edit(request, job_pk, pk):
    job = get_object_or_404(Job, pk=job_pk)
    section = get_object_or_404(Section, pk=pk, job=job)
    if not _assert_job_access(request.user, job):
        messages.error(request, 'You do not have access to that estimate.')
        return redirect('projects:project_list')

    if request.method == 'POST':
        posted_type = request.POST.get('system_type')
        if posted_type == Section.SystemType.CLADDING:
            form = SectionForm(request.POST, instance=section)
            area_fs = CladdingAreaFormSet(request.POST, instance=section, prefix='areas')
            extra_fs = CladdingExtraItemFormSet(request.POST, instance=section, prefix='extras')
            if form.is_valid() and area_fs.is_valid() and extra_fs.is_valid():
                form.save()
                area_fs.save()
                extra_fs.save()
                run_section_calculation(section, user=request.user)
                messages.success(request, f'"{section.label}" updated.')
                return redirect('jobs:job_detail', pk=job.pk)
            return render(request, 'jobs/cladding_areas_form.html', {
                'job': job, 'section': section, 'form': form,
                'area_formset': area_fs, 'extra_formset': extra_fs, 'action': 'Edit Part',
            })

        form    = SectionForm(request.POST, instance=section)
        AreaFS  = _area_formset_cls(posted_type)
        area_fs = AreaFS(request.POST, instance=section, prefix='areas')
        beam_fs = AdditionalBeamFormSet(request.POST, instance=section, prefix='beams')

        if form.is_valid() and area_fs.is_valid() and beam_fs.is_valid():
            form.save()
            area_fs.save()
            beam_fs.save()
            run_section_calculation(section, user=request.user)
            messages.success(request, f'"{section.label}" updated.')
            return redirect('jobs:job_detail', pk=job.pk)
        return render(request, 'jobs/subjob_form.html', {
            'job': job, 'section': section, 'form': form,
            'area_formset': area_fs, 'beam_formset': beam_fs, 'action': 'Edit Part',
        })

    if section.is_cladding:
        form = SectionForm(instance=section)
        area_fs = CladdingAreaFormSet(instance=section, prefix='areas')
        extra_fs = CladdingExtraItemFormSet(instance=section, prefix='extras')
        return render(request, 'jobs/cladding_areas_form.html', {
            'job': job, 'section': section, 'form': form,
            'area_formset': area_fs, 'extra_formset': extra_fs, 'action': 'Edit Part',
        })

    form    = SectionForm(instance=section)
    AreaFS  = _area_formset_cls(section.system_type)
    area_fs = AreaFS(instance=section, prefix='areas')
    beam_fs = AdditionalBeamFormSet(instance=section, prefix='beams')
    return render(request, 'jobs/subjob_form.html', {
        'job': job, 'section': section, 'form': form,
        'area_formset': area_fs, 'beam_formset': beam_fs, 'action': 'Edit Part',
    })


@login_required
@require_POST
def cladding_generate_cutlist(request, job_pk, pk):
    """
    Build a cutlist from a cladding Part's vertical elevations — one tab per
    product, one cut per area via CladdingArea.cut_piece(). Horizontal areas have
    no fixed piece length (joins are acceptable) so they're never included; they
    stay on the area-based estimate. Elevation labels go on each cut's `mark`,
    not `group` — `group` is a hard packing partition in the optimizer, and we
    want pieces from different elevations free to share a stick.
    """
    job = get_object_or_404(Job, pk=job_pk)
    section = get_object_or_404(Section, pk=pk, job=job)
    if not _assert_job_access(request.user, job):
        messages.error(request, 'You do not have access to that estimate.')
        return redirect('projects:project_list')

    vertical_areas = section.cladding_areas.filter(
        orientation=CladdingArea.Orientation.VERTICAL
    ).select_related('cladding_product')

    tabs_by_product = {}
    skipped = 0
    for area in vertical_areas:
        piece = area.cut_piece()
        if piece is None:
            skipped += 1
            continue
        length_mm, qty = piece
        product = area.cladding_product
        tab = tabs_by_product.get(product.id)
        if tab is None:
            tab = {
                'memberName': product.name,
                'productId': product.id,
                'cuts': [],
                'stockLengths': product.stock_lengths_list(),
                'cutTolerance': 50,
                'overlengthSplitStock': 6000,
                'results': None,
            }
            tabs_by_product[product.id] = tab
        tab['cuts'].append({
            'length': length_mm, 'quantity': qty,
            'mark': area.area_label or '', 'group': '',
        })

    if not tabs_by_product:
        messages.error(
            request,
            'No vertical elevations with a priced cladding product were found — '
            'add at least one before generating a cutlist.',
        )
        return redirect('jobs:job_detail', pk=job.pk)

    if skipped:
        messages.warning(
            request,
            f'{skipped} vertical area(s) were skipped (no cladding product or '
            f'cover width set).',
        )

    cutlist = CutlistProject.objects.create(
        project=job.project,
        created_by=request.user,
        name=f'{section.label} — Cladding Cutlist'[:100],
        state={
            'jobDetails': {'systemType': 'cladding', 'preparedBy': '', 'kerfWidth': 3},
            'tabs': list(tabs_by_product.values()),
            'activeTabId': None,
            'skippedData': [],
        },
    )
    section.cladding_cutlist = cutlist
    section.save(update_fields=['cladding_cutlist', 'updated_at'])

    return redirect('cutlist:project_edit', pk=cutlist.pk)


@login_required
@require_POST
def cladding_import_cutlist_results(request, job_pk, pk):
    """
    Pull real optimized stock quantities from the Part's generated cutlist back
    into pricing, replacing the rough area-based estimate for each product the
    cutlist covers (see _calc_cladding's per-product merge). Gross stock length
    (not net cut length) is used as the base, since a contingency % for on-site
    mis-cuts/breakage is meant to pad the actual quantity ordered, not just the
    cutting waste already inherent in the optimizer's own result.
    """
    job = get_object_or_404(Job, pk=job_pk)
    section = get_object_or_404(Section, pk=pk, job=job)
    if not _assert_job_access(request.user, job):
        messages.error(request, 'You do not have access to that estimate.')
        return redirect('projects:project_list')

    cutlist = section.cladding_cutlist
    if not cutlist:
        messages.error(request, 'Generate a cutlist for this part before importing results.')
        return redirect('jobs:job_detail', pk=job.pk)

    freight_settings = SystemSettings.get()
    contingency_pct = (
        section.stock_contingency_pct if section.stock_contingency_pct is not None
        else freight_settings.stock_contingency_pct
    )
    contingency_factor = Decimal('1') + Decimal(str(contingency_pct)) / Decimal('100')

    tabs = (cutlist.state or {}).get('tabs', [])
    products = Product.objects.filter(
        pk__in=[t.get('productId') for t in tabs if t.get('productId')], is_active=True
    ).in_bulk()

    lines = []
    for tab in tabs:
        results = tab.get('results')
        if not results:
            continue
        gross_mm = Decimal(str(results.get('totalStockUsed', 0)))
        if gross_mm <= 0:
            continue
        length_m = (
            (gross_mm / Decimal('1000')) * contingency_factor
        ).quantize(Decimal('0.01'))
        product = products.get(tab.get('productId'))
        lines.append(CladdingCutlistLine(
            section=section, product=product, length_m=length_m,
            product_description=tab.get('memberName', ''),
        ))

    if not lines:
        messages.error(request, 'Optimise at least one tab in the cutlist before importing.')
        return redirect('jobs:job_detail', pk=job.pk)

    section.cladding_cutlist_lines.all().delete()
    CladdingCutlistLine.objects.bulk_create(lines)
    run_section_calculation(section, user=request.user)
    messages.success(request, 'Cutlist results imported into pricing.')
    return redirect('jobs:job_detail', pk=job.pk)


@login_required
def estimate_report(request, pk):
    """
    The client-facing estimate report — every Part's priced order sheet (plus
    elevations and, once a cutlist has been generated, optimised cutting
    diagrams for any Cladding part), topped with a whole-estimate summary
    (materials, hardware, freight, and the indicative price range from
    Estimate Uncertainty %). Job-level rather than per-Part: freight and the
    uncertainty band are already Job-level concepts (see CLAUDE.md), so a
    report that applies them has to be too. Every dollar figure comes
    straight from each Part's already-computed member_schedule (the same
    data job_breakdown.html shows) — nothing is recalculated on this page.
    Cutlist state is only ever read for its raw cutting geometry (bins/cuts),
    never for pricing; cutlist stays a pure, estimate-agnostic bin-packing
    tool (see templates/cutlist/print_view.html).
    """
    job = get_object_or_404(Job, pk=pk)
    if not _assert_job_access(request.user, job):
        messages.error(request, 'You do not have access to that estimate.')
        return redirect('projects:project_list')

    sections = list(job.sections.select_related('cladding_cutlist').prefetch_related(
        Prefetch('cladding_areas', queryset=CladdingArea.objects.select_related('cladding_product')),
    ).all())

    system_settings = SystemSettings.get()
    effective_uncertainty_pct, estimate_low, estimate_high = _estimate_price_range(job, system_settings)

    report_cutlists = [
        {'label': s.label, 'state': s.cladding_cutlist.state}
        for s in sections
        if s.is_cladding and s.cladding_cutlist_id
        and any(t.get('results') for t in (s.cladding_cutlist.state or {}).get('tabs', []))
    ]

    return render(request, 'jobs/estimate_report.html', {
        'job': job,
        'sections': sections,
        'report_cutlists': report_cutlists,
        'effective_uncertainty_pct': effective_uncertainty_pct,
        'estimate_low':  estimate_low,
        'estimate_high': estimate_high,
    })


@login_required
def job_duplicate(request, pk):
    job = get_object_or_404(Job, pk=pk)
    if not _assert_job_access(request.user, job):
        messages.error(request, 'You do not have access to that estimate.')
        return redirect('projects:project_list')

    if request.method != 'POST':
        return redirect('jobs:job_detail', pk=pk)

    new_job = Job.objects.create(
        project                = job.project,
        created_by             = request.user,
        label                  = f'Copy of {job.label}' if job.label else 'Copy',
        hardware_allowance_pct = job.hardware_allowance_pct,
        wastage_pct            = job.wastage_pct,
    )

    for section in job.sections.prefetch_related(
        'areas', 'additional_beams', 'cladding_areas', 'cladding_extra_items',
    ).all():
        new_section = Section.objects.create(
            job=new_job,
            label=section.label,
            system_type=section.system_type,
            wastage_pct=section.wastage_pct,
            hardware_allowance_pct=section.hardware_allowance_pct,
            stock_contingency_pct=section.stock_contingency_pct,
            include_boundary_joists=section.include_boundary_joists,
            boundary_perimeter_lm=section.boundary_perimeter_lm,
            boundary_joist_description=section.boundary_joist_description,
            boundary_joist_product=section.boundary_joist_product,
            include_stair_void_trimmers=section.include_stair_void_trimmers,
            stair_void_trimmer_description=section.stair_void_trimmer_description,
            stair_void_trimmer_product=section.stair_void_trimmer_product,
        )
        for area in section.areas.all():
            FloorRoofArea.objects.create(
                section=new_section,
                area_label=area.area_label,
                area_m2=area.area_m2,
                product_description=area.product_description,
                joist_product=area.joist_product,
                joist_spacing=area.joist_spacing,
                roof_pitch=area.roof_pitch,
            )
        for beam in section.additional_beams.all():
            AdditionalBeam.objects.create(
                section=new_section,
                product_description=beam.product_description,
                product=beam.product,
                length_m=beam.length_m,
                quantity=beam.quantity,
            )
        for area in section.cladding_areas.all():
            CladdingArea.objects.create(
                section=new_section,
                area_label=area.area_label,
                orientation=area.orientation,
                width_m=area.width_m,
                height_m=area.height_m,
                cladding_product=area.cladding_product,
            )
        for item in section.cladding_extra_items.all():
            CladdingExtraItem.objects.create(
                section=new_section,
                product_description=item.product_description,
                product=item.product,
                length_m=item.length_m,
                quantity=item.quantity,
            )
        # Cutlist-derived lines (CutlistImportLine/CladdingCutlistLine) and any generated
        # cutlist link are deliberately not copied — those represent a specific optimizer
        # run against the original part, not something a duplicate should inherit blind.

    run_job_estimate(new_job, user=request.user)
    messages.success(request, 'Estimate duplicated.')
    return redirect('jobs:job_detail', pk=new_job.pk)


@login_required
@require_POST
def job_delete(request, pk):
    job = get_object_or_404(Job, pk=pk)
    if not _assert_job_access(request.user, job):
        messages.error(request, 'You do not have access to that estimate.')
        return redirect('projects:project_list')

    project_pk = job.project.pk
    job.delete()
    messages.success(request, 'Estimate deleted.')
    return redirect('projects:project_detail', pk=project_pk)


@login_required
def section_delete(request, job_pk, pk):
    job = get_object_or_404(Job, pk=job_pk)
    section = get_object_or_404(Section, pk=pk, job=job)
    if not _assert_job_access(request.user, job):
        messages.error(request, 'You do not have access to that estimate.')
        return redirect('projects:project_list')

    if request.method == 'POST':
        label = section.label
        section.delete()
        messages.success(request, f'"{label}" deleted.')
        return redirect('jobs:job_detail', pk=job.pk)

    return render(request, 'jobs/subjob_confirm_delete.html', {'job': job, 'section': section})


@login_required
def job_breakdown(request, pk):
    if not (request.user.is_lb_admin or request.user.is_lb_detailing):
        messages.error(request, 'Access denied.')
        return redirect('jobs:job_detail', pk=pk)

    job = get_object_or_404(Job, pk=pk)
    if not _assert_job_access(request.user, job):
        messages.error(request, 'You do not have access to that estimate.')
        return redirect('projects:project_list')

    sections = job.sections.prefetch_related(
        'areas', 'additional_beams', 'cladding_areas', 'cladding_extra_items',
    ).all()
    return render(request, 'jobs/job_breakdown.html', {
        'job': job,
        'sections': sections,
    })
