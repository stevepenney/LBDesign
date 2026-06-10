from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.models import FreightSettings
from projects.models import Project
from projects.views import _assert_project_access
from .calculations import run_job_estimate, run_subjob_calculation
from .forms import JobForm, SectionForm, FloorRoofAreaFormSet, AdditionalBeamFormSet
from .models import Job, Section, FloorRoofArea, AdditionalBeam


@login_required
def estimate_quick(request):
    """Entry point with no project — silently creates a DRAFT project+job on first calculate."""
    if not request.user.organisation and not request.user.is_lb_admin:
        messages.error(request, 'Your account is not linked to an organisation. Contact LumberBank.')
        return redirect('projects:project_list')

    if request.method == 'POST':
        form    = SectionForm(request.POST)
        area_fs = FloorRoofAreaFormSet(request.POST, prefix='areas')
        beam_fs = AdditionalBeamFormSet(request.POST, prefix='beams')

        if form.is_valid() and area_fs.is_valid() and beam_fs.is_valid():
            project = Project.objects.create(
                organisation = request.user.organisation,
                created_by   = request.user,
                status       = Project.Status.DRAFT,
            )
            job = Job.objects.create(project=project, created_by=request.user)
            section = form.save(commit=False)
            section.job = job
            section.save()
            area_fs.instance = section
            area_fs.save()
            beam_fs.instance = section
            beam_fs.save()
            run_subjob_calculation(section)
            return redirect('jobs:job_detail', pk=job.pk)
    else:
        form    = SectionForm()
        area_fs = FloorRoofAreaFormSet(prefix='areas')
        beam_fs = AdditionalBeamFormSet(prefix='beams')

    return render(request, 'jobs/subjob_form.html', {
        'job': None,
        'form': form,
        'area_formset': area_fs,
        'beam_formset': beam_fs,
        'action': 'Quick Estimate',
    })


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
    if field not in {'label', 'hardware_allowance_pct'}:
        return JsonResponse({'ok': False, 'error': 'Invalid field'}, status=400)

    if field == 'hardware_allowance_pct':
        if value == '':
            job.hardware_allowance_pct = None
        else:
            try:
                pct = Decimal(value)
                if not (Decimal('0') <= pct <= Decimal('100')):
                    return JsonResponse({'ok': False, 'error': 'Enter a value between 0 and 100'}, status=400)
                job.hardware_allowance_pct = pct
            except InvalidOperation:
                return JsonResponse({'ok': False, 'error': 'Invalid percentage'}, status=400)
        job.save(update_fields=['hardware_allowance_pct', 'updated_at'])
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

    if request.method == 'POST':
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.project = project
            job.created_by = request.user
            job.save()
            messages.success(request, 'Estimate created.')
            return redirect('jobs:job_detail', pk=job.pk)
    else:
        form = JobForm()

    return render(request, 'jobs/job_form.html', {
        'form': form, 'project': project, 'action': 'New Estimate',
    })


@login_required
def job_detail(request, pk):
    job = get_object_or_404(Job, pk=pk)
    if not _assert_job_access(request.user, job):
        messages.error(request, 'You do not have access to that estimate.')
        return redirect('projects:project_list')
    sections = job.sections.prefetch_related('areas', 'additional_beams').all()
    freight_settings = FreightSettings.get()
    effective_hardware_pct = (
        job.hardware_allowance_pct
        if job.hardware_allowance_pct is not None
        else freight_settings.hardware_allowance_pct
    )
    uncertainty_display_pct = freight_settings.estimate_uncertainty_pct / 2
    return render(request, 'jobs/job_detail.html', {
        'job': job,
        'sections': sections,
        'freight_settings': freight_settings,
        'effective_hardware_pct': effective_hardware_pct,
        'uncertainty_display_pct': uncertainty_display_pct,
    })


@login_required
def job_edit(request, pk):
    job = get_object_or_404(Job, pk=pk)
    if not _assert_job_access(request.user, job):
        messages.error(request, 'You do not have access to that estimate.')
        return redirect('projects:project_list')

    if request.method == 'POST':
        form = JobForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            messages.success(request, 'Estimate updated.')
            return redirect('jobs:job_detail', pk=job.pk)
    else:
        form = JobForm(instance=job)

    return render(request, 'jobs/job_form.html', {
        'form': form, 'job': job, 'project': job.project, 'action': 'Edit Estimate',
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

    if request.method == 'POST':
        form = SectionForm(request.POST)
        area_fs = FloorRoofAreaFormSet(request.POST, prefix='areas')
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
        form = SectionForm()
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

    if request.method == 'POST':
        form = SectionForm(request.POST, instance=section)
        area_fs = FloorRoofAreaFormSet(request.POST, instance=section, prefix='areas')
        beam_fs = AdditionalBeamFormSet(request.POST, instance=section, prefix='beams')

        if form.is_valid() and area_fs.is_valid() and beam_fs.is_valid():
            form.save()
            area_fs.save()
            beam_fs.save()
            run_subjob_calculation(section)
            messages.success(request, f'"{section.label}" updated.')
            return redirect('jobs:job_detail', pk=job.pk)
    else:
        form = SectionForm(instance=section)
        area_fs = FloorRoofAreaFormSet(instance=section, prefix='areas')
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

    for section in job.sections.prefetch_related('areas', 'additional_beams').all():
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
        for beam in section.additional_beams.all():
            AdditionalBeam.objects.create(
                section=new_section,
                product_description=beam.product_description,
                product=beam.product,
                length_m=beam.length_m,
                quantity=beam.quantity,
            )

    messages.success(request, 'Estimate duplicated.')
    return redirect('jobs:job_detail', pk=new_job.pk)


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
