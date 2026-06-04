import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import CutlistProject


def _assert_project_access(user, project):
    if project.organisation != user.organisation:
        raise PermissionDenied


@login_required
def project_list(request):
    projects = CutlistProject.objects.filter(
        organisation=request.user.organisation
    ).select_related('job', 'created_by')
    return render(request, 'cutlist/project_list.html', {'projects': projects})


@login_required
@require_POST
def project_new(request):
    project = CutlistProject.objects.create(
        organisation=request.user.organisation,
        created_by=request.user,
    )
    return redirect('cutlist:project_edit', pk=project.pk)


@login_required
def project_edit(request, pk):
    project = get_object_or_404(CutlistProject, pk=pk)
    _assert_project_access(request.user, project)
    return render(request, 'cutlist/project_edit.html', {'project': project})


@login_required
@require_POST
def project_save(request, pk):
    project = get_object_or_404(CutlistProject, pk=pk)
    _assert_project_access(request.user, project)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)

    job_details = data.get('jobDetails', {})
    name_parts = [
        job_details.get('jobNumber', '').strip(),
        job_details.get('jobDescription', '').strip(),
    ]
    name = ' — '.join(p for p in name_parts if p) or 'Untitled Cutlist'

    project.name = name[:100]
    project.state = data
    project.save()

    return JsonResponse({'ok': True, 'name': project.name})


@login_required
@require_POST
def project_duplicate(request, pk):
    project = get_object_or_404(CutlistProject, pk=pk)
    _assert_project_access(request.user, project)

    new_project = CutlistProject.objects.create(
        organisation=project.organisation,
        created_by=request.user,
        job=project.job,
        name=f'Copy of {project.name}'[:100],
        state=project.state,
    )
    return redirect('cutlist:project_edit', pk=new_project.pk)


@login_required
def project_print(request, pk):
    project = get_object_or_404(CutlistProject, pk=pk)
    _assert_project_access(request.user, project)
    return render(request, 'cutlist/print_view.html', {'project': project})


@login_required
@require_POST
def project_delete(request, pk):
    project = get_object_or_404(CutlistProject, pk=pk)
    _assert_project_access(request.user, project)
    project.delete()
    return redirect('cutlist:project_list')
