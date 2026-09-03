import json
import math
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
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
from .calculations import run_job_estimate, run_subjob_calculation
from .forms import (
    SectionForm, FloorRoofAreaFormSet, FloorRoofAreaOptionalFormSet, AdditionalBeamFormSet,
    CladdingSectionForm, CladdingAreaFormSet,
)
from .models import Job, Section, FloorRoofArea, CladdingArea, AdditionalBeam, CutlistImportLine


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
    """Return the right area formset class — Other sections have optional areas."""
    if system_type == Section.SystemType.OTHER:
        return FloorRoofAreaOptionalFormSet
    return FloorRoofAreaFormSet


def _job_allows_framing(job):
    """A job locks to one category on its first section — framing and cladding never mix."""
    return not job.sections.filter(system_type=Section.SystemType.CLADDING).exists()


def _job_allows_cladding(job):
    return not job.sections.exclude(system_type=Section.SystemType.CLADDING).exists()


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
            run_job_estimate(job)
        return JsonResponse({'ok': True, 'reload': True})

    setattr(job, field, value)
    job.save(update_fields=[field, 'updated_at'])
    return JsonResponse({'ok': True, 'value': value})


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
        wastage_pct=wastage_pct,
        estimate_uncertainty_pct=Decimal('0'),
        source_cutlist=cutlist,
    )
    section = Section.objects.create(
        job=job,
        label=cutlist.name,
        system_type=Section.SystemType.OTHER,
    )
    CutlistImportLine.objects.bulk_create([
        CutlistImportLine(
            section=section, product=product, length_m=length_m,
            tab_index=tab_index, product_description=member_name,
        )
        for product, length_m, tab_index, member_name in lines
    ])
    run_job_estimate(job)

    return JsonResponse({'ok': True, 'redirect': reverse('jobs:job_detail', args=[job.pk])})


@login_required
def job_detail(request, pk):
    job = get_object_or_404(Job, pk=pk)
    if not _assert_job_access(request.user, job):
        messages.error(request, 'You do not have access to that estimate.')
        return redirect('projects:project_list')
    sections = list(job.sections.prefetch_related(
        'areas', 'cladding_areas', 'additional_beams', 'cutlist_import_lines',
    ).all())
    if job.source_cutlist_id:
        for sj in sections:
            if sj.cutlist_import_lines.all():
                sj.priced_cutlist_lines = _priced_cutlist_lines(sj)
    system_settings = SystemSettings.get()
    effective_hardware_pct = (
        job.hardware_allowance_pct
        if job.hardware_allowance_pct is not None
        else system_settings.hardware_allowance_pct
    )
    effective_uncertainty_pct = (
        job.estimate_uncertainty_pct
        if job.estimate_uncertainty_pct is not None
        else system_settings.estimate_uncertainty_pct
    )
    effective_wastage_pct = (
        job.wastage_pct
        if job.wastage_pct is not None
        else system_settings.wastage_pct
    )
    total = float(job.total)
    band  = float(effective_uncertainty_pct) / 100
    estimate_low  = int(total * (1 - band * 0.30) // 50) * 50
    estimate_high = math.ceil(total * (1 + band * 0.70) / 50) * 50
    return render(request, 'jobs/job_detail.html', {
        'job': job,
        'sections': sections,
        'system_settings': system_settings,
        'effective_hardware_pct':     effective_hardware_pct,
        'effective_wastage_pct':      effective_wastage_pct,
        'effective_uncertainty_pct':  effective_uncertainty_pct,
        'estimate_low':  f'{estimate_low:,}',
        'estimate_high': f'{estimate_high:,}',
        'can_add_framing':  _job_allows_framing(job),
        'can_add_cladding': _job_allows_cladding(job),
    })


# ── Section views ─────────────────────────────────────────────────────────────

@login_required
def job_recalculate(request, pk):
    job = get_object_or_404(Job, pk=pk)
    if not _assert_job_access(request.user, job):
        messages.error(request, 'You do not have access to that estimate.')
        return redirect('projects:project_list')
    if request.method == 'POST':
        run_job_estimate(job)
        messages.success(request, 'Estimate recalculated.')
    return redirect('jobs:job_detail', pk=job.pk)


@login_required
def section_create(request, job_pk):
    job = get_object_or_404(Job, pk=job_pk)
    if not _assert_job_access(request.user, job):
        messages.error(request, 'You do not have access to that estimate.')
        return redirect('projects:project_list')
    if not _job_allows_framing(job):
        messages.error(request, "This estimate already contains a Cladding section — cladding "
                                 "and framing can't be mixed in one estimate. Start a new "
                                 "estimate for framing.")
        return redirect('jobs:job_detail', pk=job.pk)

    if request.method == 'POST':
        form    = SectionForm(request.POST)
        AreaFS  = _area_formset_cls(request.POST.get('system_type'))
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
            run_subjob_calculation(section)
            messages.success(request, f'"{section.label}" added.')
            return redirect('jobs:job_detail', pk=job.pk)
    else:
        form    = SectionForm()
        area_fs = FloorRoofAreaFormSet(prefix='areas')
        beam_fs = AdditionalBeamFormSet(prefix='beams')

    return render(request, 'jobs/subjob_form.html', {
        'job': job,
        'form': form,
        'area_formset': area_fs,
        'beam_formset': beam_fs,
        'action': 'Add Section',
    })


@login_required
def section_edit(request, job_pk, pk):
    job = get_object_or_404(Job, pk=job_pk)
    section = get_object_or_404(Section, pk=pk, job=job)
    if not _assert_job_access(request.user, job):
        messages.error(request, 'You do not have access to that estimate.')
        return redirect('projects:project_list')
    if section.is_cladding:
        return redirect('jobs:cladding_section_edit', job_pk=job.pk, pk=section.pk)

    if request.method == 'POST':
        form    = SectionForm(request.POST, instance=section)
        AreaFS  = _area_formset_cls(request.POST.get('system_type'))
        area_fs = AreaFS(request.POST, instance=section, prefix='areas')
        beam_fs = AdditionalBeamFormSet(request.POST, instance=section, prefix='beams')

        if form.is_valid() and area_fs.is_valid() and beam_fs.is_valid():
            form.save()
            area_fs.save()
            beam_fs.save()
            run_subjob_calculation(section)
            messages.success(request, f'"{section.label}" updated.')
            return redirect('jobs:job_detail', pk=job.pk)
    else:
        form    = SectionForm(instance=section)
        AreaFS  = _area_formset_cls(section.system_type)
        area_fs = AreaFS(instance=section, prefix='areas')
        beam_fs = AdditionalBeamFormSet(instance=section, prefix='beams')

    return render(request, 'jobs/subjob_form.html', {
        'job': job,
        'section': section,
        'form': form,
        'area_formset': area_fs,
        'beam_formset': beam_fs,
        'action': 'Edit Section',
    })


@login_required
def cladding_section_create(request, job_pk):
    job = get_object_or_404(Job, pk=job_pk)
    if not _assert_job_access(request.user, job):
        messages.error(request, 'You do not have access to that estimate.')
        return redirect('projects:project_list')
    if not _job_allows_cladding(job):
        messages.error(request, "This estimate already contains framing sections — cladding "
                                 "and framing can't be mixed in one estimate. Start a new "
                                 "estimate for cladding.")
        return redirect('jobs:job_detail', pk=job.pk)

    if request.method == 'POST':
        form    = CladdingSectionForm(request.POST)
        area_fs = CladdingAreaFormSet(request.POST, prefix='areas')

        if form.is_valid() and area_fs.is_valid():
            section = form.save(commit=False)
            section.job = job
            section.system_type = Section.SystemType.CLADDING
            section.save()
            area_fs.instance = section
            area_fs.save()
            if job.hardware_allowance_pct is None:
                job.hardware_allowance_pct = Decimal('0')
                job.save(update_fields=['hardware_allowance_pct', 'updated_at'])
            run_subjob_calculation(section)
            messages.success(request, f'"{section.label}" added.')
            return redirect('jobs:job_detail', pk=job.pk)
    else:
        form    = CladdingSectionForm()
        area_fs = CladdingAreaFormSet(prefix='areas')

    return render(request, 'jobs/cladding_section_form.html', {
        'job': job,
        'form': form,
        'area_formset': area_fs,
        'action': 'Add Cladding Section',
    })


@login_required
def cladding_section_edit(request, job_pk, pk):
    job = get_object_or_404(Job, pk=job_pk)
    section = get_object_or_404(Section, pk=pk, job=job, system_type=Section.SystemType.CLADDING)
    if not _assert_job_access(request.user, job):
        messages.error(request, 'You do not have access to that estimate.')
        return redirect('projects:project_list')

    if request.method == 'POST':
        form    = CladdingSectionForm(request.POST, instance=section)
        area_fs = CladdingAreaFormSet(request.POST, instance=section, prefix='areas')

        if form.is_valid() and area_fs.is_valid():
            form.save()
            area_fs.save()
            run_subjob_calculation(section)
            messages.success(request, f'"{section.label}" updated.')
            return redirect('jobs:job_detail', pk=job.pk)
    else:
        form    = CladdingSectionForm(instance=section)
        area_fs = CladdingAreaFormSet(instance=section, prefix='areas')

    return render(request, 'jobs/cladding_section_form.html', {
        'job': job,
        'section': section,
        'form': form,
        'area_formset': area_fs,
        'action': 'Edit Cladding Section',
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
    )

    for section in job.sections.prefetch_related('areas', 'cladding_areas', 'additional_beams').all():
        new_section = Section.objects.create(
            job=new_job,
            label=section.label,
            system_type=section.system_type,
            include_boundary_joists=section.include_boundary_joists,
            boundary_perimeter_lm=section.boundary_perimeter_lm,
            boundary_joist_description=section.boundary_joist_description,
            boundary_joist_product=section.boundary_joist_product,
            include_stair_void_trimmers=section.include_stair_void_trimmers,
            stair_void_trimmer_description=section.stair_void_trimmer_description,
            stair_void_trimmer_product=section.stair_void_trimmer_product,
            roof_pitch=section.roof_pitch,
        )
        for area in section.areas.all():
            FloorRoofArea.objects.create(
                section=new_section,
                area_label=area.area_label,
                area_m2=area.area_m2,
                product_description=area.product_description,
                joist_product=area.joist_product,
                joist_spacing=area.joist_spacing,
            )
        for area in section.cladding_areas.all():
            CladdingArea.objects.create(
                section=new_section,
                area_label=area.area_label,
                area_m2=area.area_m2,
                cladding_product=area.cladding_product,
            )
        for beam in section.additional_beams.all():
            AdditionalBeam.objects.create(
                section=new_section,
                product_description=beam.product_description,
                product=beam.product,
                length_m=beam.length_m,
                quantity=beam.quantity,
            )

    run_job_estimate(new_job)
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

    sections = job.sections.prefetch_related('areas', 'additional_beams').all()
    return render(request, 'jobs/job_breakdown.html', {
        'job': job,
        'sections': sections,
    })
