from django.conf import settings as django_settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import ProjectDocumentForm, ProjectForm
from .models import Project, ProjectDocument


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_projects_for_user(user, include_discarded=False):
    if user.is_lb_admin or user.is_lb_detailing:
        qs = Project.objects.select_related('organisation').all()
    elif user.organisation:
        qs = Project.objects.filter(organisation=user.organisation)
    else:
        return Project.objects.none()

    if not include_discarded:
        qs = qs.exclude(status=Project.Status.DISCARDED)
    return qs


def _assert_project_access(user, project):
    if user.is_lb_admin or user.is_lb_detailing:
        return True
    return user.organisation and project.organisation == user.organisation


def _send_quote_request_email(project, request):
    project_url = request.build_absolute_uri(
        reverse('projects:project_detail', args=[project.pk])
    )
    doc_count = project.documents.count()
    doc_note = (
        f'{doc_count} document(s) uploaded'
        if doc_count else
        'No documents uploaded — may be delivered separately'
    )
    body = (
        f'Quote request received.\n\n'
        f'LB Job:     {project.lb_ref}\n'
        f'Client:     {project.client_name or "Not specified"}\n'
        f'Site:       {project.site_address or "Not specified"}\n'
        f'Merchant:   {project.organisation.name}\n'
        f'Reference:  {project.merchant_reference or "—"}\n'
        f'Documents:  {doc_note}\n\n'
        f'View project: {project_url}'
    )
    try:
        send_mail(
            subject=f'Quote Request — {project.display_ref} ({project.organisation.name})',
            message=body,
            from_email=django_settings.DEFAULT_FROM_EMAIL,
            recipient_list=[django_settings.DETAILING_TEAM_EMAIL],
            fail_silently=True,
        )
    except Exception:
        pass


# ── Project CRUD ──────────────────────────────────────────────────────────────

@login_required
def project_list(request):
    show_discarded = request.GET.get('discarded') == '1'
    projects = _get_projects_for_user(request.user, include_discarded=True)
    if show_discarded:
        projects = projects.filter(status=Project.Status.DISCARDED)
    else:
        projects = projects.exclude(status__in=[Project.Status.DRAFT, Project.Status.DISCARDED])
    projects = projects.prefetch_related('estimates', 'cutlist_projects')
    discarded_count = _get_projects_for_user(request.user, include_discarded=True).filter(
        status=Project.Status.DISCARDED
    ).count()
    return render(request, 'projects/project_list.html', {
        'projects':        projects,
        'show_discarded':  show_discarded,
        'discarded_count': discarded_count,
    })


@login_required
def project_create(request):
    if not request.user.organisation and not request.user.is_lb_admin:
        messages.error(request, 'Your account is not linked to an organisation. Contact LumberBank.')
        return redirect('projects:project_list')
    project = Project.objects.create(
        organisation = request.user.organisation,
        created_by   = request.user,
        status       = Project.Status.DRAFT,
    )
    return redirect('projects:project_detail', pk=project.pk)


@login_required
def project_edit(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not _assert_project_access(request.user, project):
        messages.error(request, 'You do not have access to that project.')
        return redirect('projects:project_list')

    is_draft = project.status == Project.Status.DRAFT

    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project)
        if form.is_valid():
            saved = form.save(commit=False)
            if is_draft:
                saved.status = Project.Status.PRELIMINARY
            saved.save()
            messages.success(request, f'Project "{project.display_ref}" saved.')
            return redirect('projects:project_detail', pk=project.pk)
    else:
        form = ProjectForm(instance=project)

    return render(request, 'projects/project_form.html', {
        'form': form, 'project': project,
        'action': 'Save Project' if is_draft else 'Edit Project',
        'is_draft': is_draft,
    })


@login_required
def project_detail(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not _assert_project_access(request.user, project):
        messages.error(request, 'You do not have access to that project.')
        return redirect('projects:project_list')

    estimates = project.estimates.prefetch_related('sections').order_by('-created_at')
    cutlists  = project.cutlist_projects.order_by('-updated_at')
    documents = project.documents.select_related('uploaded_by').all()
    return render(request, 'projects/project_detail.html', {
        'project':   project,
        'estimates': estimates,
        'cutlists':  cutlists,
        'documents': documents,
    })


# ── Project actions ───────────────────────────────────────────────────────────

@login_required
@require_POST
def project_promote(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not _assert_project_access(request.user, project):
        return JsonResponse({'ok': False}, status=403)
    if project.status == Project.Status.DRAFT:
        project.status = Project.Status.PRELIMINARY
        project.save(update_fields=['status', 'updated_at'])
    return JsonResponse({'ok': True, 'redirect': f'/projects/{project.pk}/'})


@login_required
@require_POST
def project_update_field(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not _assert_project_access(request.user, project):
        return JsonResponse({'ok': False}, status=403)
    EDITABLE = {'client_name', 'site_address', 'merchant_reference'}
    field = request.POST.get('field', '')
    value = request.POST.get('value', '').strip()
    if field not in EDITABLE:
        return JsonResponse({'ok': False, 'error': 'Invalid field'}, status=400)
    setattr(project, field, value)
    project.save(update_fields=[field, 'updated_at'])
    return JsonResponse({'ok': True, 'value': value})


@login_required
@require_POST
def project_request_quote(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not _assert_project_access(request.user, project):
        messages.error(request, 'You do not have access to that project.')
        return redirect('projects:project_list')
    if project.status != Project.Status.PRELIMINARY:
        messages.error(request, 'Only preliminary projects can request a quote.')
        return redirect('projects:project_detail', pk=project.pk)
    project.status = Project.Status.QUOTING
    project.save(update_fields=['status', 'updated_at'])
    _send_quote_request_email(project, request)
    messages.success(request, 'Quote requested — the LB team has been notified.')
    return redirect('projects:project_detail', pk=project.pk)


@login_required
@require_POST
def project_discard(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not _assert_project_access(request.user, project):
        messages.error(request, 'You do not have access to that project.')
        return redirect('projects:project_list')
    project.status = Project.Status.DISCARDED
    project.save(update_fields=['status'])
    messages.success(request, f'"{project.display_ref}" discarded.')
    return_to = request.POST.get('return_to', '')
    if return_to == 'detail':
        return redirect('projects:project_detail', pk=project.pk)
    return redirect('projects:project_list')


@login_required
@require_POST
def project_undiscard(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not _assert_project_access(request.user, project):
        messages.error(request, 'You do not have access to that project.')
        return redirect('projects:project_list')
    project.status = Project.Status.PRELIMINARY
    project.save(update_fields=['status'])
    messages.success(request, f'"{project.display_ref}" restored.')
    return redirect('projects:project_detail', pk=project.pk)


# ── Document views ────────────────────────────────────────────────────────────

@login_required
@require_POST
def document_upload_ajax(request, pk):
    """Accept a raw file drop and create a ProjectDocument silently."""
    project = get_object_or_404(Project, pk=pk)
    if not _assert_project_access(request.user, project):
        return JsonResponse({'ok': False, 'error': 'Access denied'}, status=403)

    file = request.FILES.get('file')
    if not file:
        return JsonResponse({'ok': False, 'error': 'No file received'}, status=400)

    doc = ProjectDocument.objects.create(
        project=project,
        uploaded_by=request.user,
        document_type=ProjectDocument.DocumentType.DRAWING,
        file=file,
    )
    delete_url = reverse('projects:document_delete', args=[project.pk, doc.pk])
    return JsonResponse({
        'ok': True,
        'doc': {
            'pk':           doc.pk,
            'display_name': doc.display_name,
            'type_display': doc.get_document_type_display(),
            'link_url':     doc.link_url,
            'uploaded_by':  request.user.get_full_name() or request.user.username,
            'uploaded_at':  doc.uploaded_at.strftime('%-d %b %Y'),
            'delete_url':   delete_url,
        },
    })


@login_required
def document_add(request, pk):
    project = get_object_or_404(Project, pk=pk)
    if not _assert_project_access(request.user, project):
        messages.error(request, 'You do not have access to that project.')
        return redirect('projects:project_list')

    if request.method == 'POST':
        form = ProjectDocumentForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.project     = project
            doc.uploaded_by = request.user
            doc.save()
            messages.success(request, 'Document added.')
            return redirect('projects:project_detail', pk=project.pk)
    else:
        form = ProjectDocumentForm(user=request.user)

    return render(request, 'projects/document_form.html', {
        'form': form, 'project': project,
    })


@login_required
@require_POST
def document_delete(request, pk, doc_pk):
    project = get_object_or_404(Project, pk=pk)
    doc     = get_object_or_404(ProjectDocument, pk=doc_pk, project=project)

    if not _assert_project_access(request.user, project):
        messages.error(request, 'You do not have access to that project.')
        return redirect('projects:project_list')

    is_owner = doc.uploaded_by == request.user
    is_lb    = request.user.is_lb_admin or request.user.is_lb_detailing
    if not (is_owner or is_lb):
        messages.error(request, 'You can only remove your own documents.')
        return redirect('projects:project_detail', pk=project.pk)

    if doc.file:
        doc.file.delete(save=False)
    doc.delete()
    messages.success(request, 'Document removed.')
    return redirect('projects:project_detail', pk=project.pk)
