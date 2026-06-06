import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from projects.models import Project
from projects.views import _assert_project_access, _get_projects_for_user
from .models import CutlistProject


def _assert_cutlist_access(user, cutlist):
    if cutlist.project.organisation != user.organisation:
        if not (user.is_lb_admin or user.is_lb_detailing):
            raise PermissionDenied


@login_required
def project_list(request):
    projects = _get_projects_for_user(request.user)
    cutlists = CutlistProject.objects.filter(
        project__in=projects
    ).select_related('project', 'created_by')
    return render(request, 'cutlist/project_list.html', {'cutlists': cutlists})


@login_required
@require_POST
def project_new_quick(request):
    """Create a cutlist with a silently-created DRAFT project — no project selection needed."""
    if not request.user.organisation and not request.user.is_lb_admin:
        raise PermissionDenied
    project = Project.objects.create(
        organisation = request.user.organisation,
        created_by   = request.user,
        status       = Project.Status.DRAFT,
    )
    cutlist = CutlistProject.objects.create(project=project, created_by=request.user)
    return redirect('cutlist:project_edit', pk=cutlist.pk)


@login_required
@require_POST
def project_new(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)
    if not _assert_project_access(request.user, project):
        raise PermissionDenied
    cutlist = CutlistProject.objects.create(
        project    = project,
        created_by = request.user,
    )
    return redirect('cutlist:project_edit', pk=cutlist.pk)


@login_required
def project_edit(request, pk):
    cutlist = get_object_or_404(CutlistProject, pk=pk)
    _assert_cutlist_access(request.user, cutlist)
    return render(request, 'cutlist/project_edit.html', {'project': cutlist})


@login_required
@require_POST
def project_save(request, pk):
    cutlist = get_object_or_404(CutlistProject, pk=pk)
    _assert_cutlist_access(request.user, cutlist)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'ok': False, 'error': 'Invalid JSON'}, status=400)

    job_details = data.get('jobDetails', {})
    name_parts = [
        cutlist.project.lb_ref,
        job_details.get('jobDescription', '').strip(),
    ]
    name = ' — '.join(p for p in name_parts if p) or 'Untitled Cutlist'

    cutlist.name  = name[:100]
    cutlist.state = data
    cutlist.save()

    return JsonResponse({'ok': True, 'name': cutlist.name})


@login_required
@require_POST
def project_duplicate(request, pk):
    cutlist = get_object_or_404(CutlistProject, pk=pk)
    _assert_cutlist_access(request.user, cutlist)

    new_cutlist = CutlistProject.objects.create(
        project    = cutlist.project,
        created_by = request.user,
        name       = f'Copy of {cutlist.name}'[:100],
        state      = cutlist.state,
    )
    return redirect('cutlist:project_edit', pk=new_cutlist.pk)


@login_required
def project_print(request, pk):
    cutlist = get_object_or_404(CutlistProject, pk=pk)
    _assert_cutlist_access(request.user, cutlist)
    return render(request, 'cutlist/print_view.html', {'project': cutlist})


@login_required
@require_POST
def project_delete(request, pk):
    cutlist = get_object_or_404(CutlistProject, pk=pk)
    _assert_cutlist_access(request.user, cutlist)
    cutlist.delete()
    return redirect('cutlist:project_list')
