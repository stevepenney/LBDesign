from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ProjectForm
from .models import Project


def _get_projects_for_user(user):
    if user.is_lb_admin or user.is_lb_detailing:
        return Project.objects.select_related('organisation').all()
    if user.organisation:
        return Project.objects.filter(organisation=user.organisation)
    return Project.objects.none()


def _assert_project_access(user, project):
    if user.is_lb_admin or user.is_lb_detailing:
        return True
    return user.organisation and project.organisation == user.organisation


@login_required
def project_list(request):
    projects = _get_projects_for_user(request.user).prefetch_related('estimates', 'cutlist_projects')
    return render(request, 'projects/project_list.html', {'projects': projects})


@login_required
def project_create(request):
    if not request.user.organisation and not request.user.is_lb_admin:
        messages.error(request, 'Your account is not linked to an organisation. Contact LumberBank.')
        return redirect('projects:project_list')

    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.organisation = request.user.organisation
            project.created_by = request.user
            project.save()
            messages.success(request, f'Project {project.lb_ref} created.')
            return redirect('projects:project_detail', pk=project.pk)
    else:
        form = ProjectForm()

    return render(request, 'projects/project_form.html', {'form': form, 'action': 'New Project'})


@login_required
def project_edit(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not _assert_project_access(request.user, project):
        messages.error(request, 'You do not have access to that project.')
        return redirect('projects:project_list')

    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            form.save()
            messages.success(request, f'Project {project.lb_ref} updated.')
            return redirect('projects:project_detail', pk=project.pk)
    else:
        form = ProjectForm(instance=project)

    return render(request, 'projects/project_form.html', {
        'form': form, 'project': project, 'action': 'Edit Project',
    })


@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not _assert_project_access(request.user, project):
        messages.error(request, 'You do not have access to that project.')
        return redirect('projects:project_list')

    estimates = project.estimates.prefetch_related('sections').order_by('-created_at')
    cutlists  = project.cutlist_projects.order_by('-updated_at')
    return render(request, 'projects/project_detail.html', {
        'project':   project,
        'estimates': estimates,
        'cutlists':  cutlists,
    })
