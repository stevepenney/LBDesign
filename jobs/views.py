from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

from core.models import FreightSettings
from .calculations import run_job_estimate, run_subjob_calculation
from .forms import JobForm, SectionForm, FloorRoofAreaFormSet, AdditionalBeamFormSet
from .models import Job, Section


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_jobs_for_user(user):
    if user.is_lb_admin or user.is_lb_detailing:
        return Job.objects.select_related('organisation').all()
    if user.organisation:
        return Job.objects.filter(organisation=user.organisation)
    return Job.objects.none()


def _assert_job_access(user, job):
    if user.is_lb_admin or user.is_lb_detailing:
        return True
    return user.organisation and job.organisation == user.organisation


# ── Job views ─────────────────────────────────────────────────────────────────

@login_required
def job_list(request):
    jobs = _get_jobs_for_user(request.user).prefetch_related('sections').order_by('-created_at')
    return render(request, 'jobs/job_list.html', {'jobs': jobs})


@login_required
def job_create(request):
    if not request.user.organisation and not request.user.is_lb_admin:
        messages.error(request, 'Your account is not linked to an organisation. Contact LumberBank.')
        return redirect('jobs:job_list')

    if request.method == 'POST':
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.organisation = request.user.organisation
            job.created_by = request.user
            job.save()
            messages.success(request, f'Job "{job.job_reference}" created.')
            return redirect('jobs:job_detail', pk=job.pk)
    else:
        form = JobForm()

    return render(request, 'jobs/job_form.html', {'form': form, 'action': 'New Job'})


@login_required
def job_detail(request, pk):
    job = get_object_or_404(Job, pk=pk)
    if not _assert_job_access(request.user, job):
        messages.error(request, 'You do not have access to that job.')
        return redirect('jobs:job_list')
    sections = job.sections.prefetch_related('areas', 'additional_beams').all()
    return render(request, 'jobs/job_detail.html', {
        'job': job,
        'sections': sections,
        'freight_settings': FreightSettings.get(),
    })


@login_required
def job_edit(request, pk):
    job = get_object_or_404(Job, pk=pk)
    if not _assert_job_access(request.user, job):
        messages.error(request, 'You do not have access to that job.')
        return redirect('jobs:job_list')

    if request.method == 'POST':
        form = JobForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            messages.success(request, f'Job "{job.job_reference}" updated.')
            return redirect('jobs:job_detail', pk=job.pk)
    else:
        form = JobForm(instance=job)

    return render(request, 'jobs/job_form.html', {'form': form, 'job': job, 'action': 'Edit Job'})


# ── Section views ─────────────────────────────────────────────────────────────

@login_required
def job_recalculate(request, pk):
    job = get_object_or_404(Job, pk=pk)
    if not _assert_job_access(request.user, job):
        messages.error(request, 'You do not have access to that job.')
        return redirect('jobs:job_list')
    if request.method == 'POST':
        run_job_estimate(job)
        messages.success(request, 'Estimate recalculated.')
    return redirect('jobs:job_detail', pk=job.pk)


@login_required
def section_create(request, job_pk):
    job = get_object_or_404(Job, pk=job_pk)
    if not _assert_job_access(request.user, job):
        messages.error(request, 'You do not have access to that job.')
        return redirect('jobs:job_list')

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
        messages.error(request, 'You do not have access to that job.')
        return redirect('jobs:job_list')

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
def section_delete(request, job_pk, pk):
    job = get_object_or_404(Job, pk=job_pk)
    section = get_object_or_404(Section, pk=pk, job=job)
    if not _assert_job_access(request.user, job):
        messages.error(request, 'You do not have access to that job.')
        return redirect('jobs:job_list')

    if request.method == 'POST':
        label = section.label
        section.delete()
        messages.success(request, f'"{label}" deleted.')
        return redirect('jobs:job_detail', pk=job.pk)

    return render(request, 'jobs/subjob_confirm_delete.html', {'job': job, 'section': section})
